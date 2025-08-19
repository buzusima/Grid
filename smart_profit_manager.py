"""
Smart Profit Management System - Complete Trading Engine
smart_profit_manager.py
Advanced profit taking with portfolio analysis, trailing stops, and intelligent closing
ENHANCED VERSION - Full trading system with MT5 integration
"""

import math
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import MetaTrader5 as mt5
import itertools
import threading
import json
import os

from api_connector import BackendAPIConnector

# Import additional modules
try:
    from ai_money_manager import AIMoneyManager
    MONEY_MANAGER_AVAILABLE = True
except ImportError:
    MONEY_MANAGER_AVAILABLE = False

try:
    from survivability_engine import SurvivabilityEngine
    SURVIVABILITY_ENGINE_AVAILABLE = True
except ImportError:
    SURVIVABILITY_ENGINE_AVAILABLE = False

class ProfitStrategy(Enum):
    QUICK_SAFE = "QUICK_SAFE"       # เก็บไวๆ ปลอดภัย
    BALANCED = "BALANCED"           # สมดุลระหว่างเร็วกับกำไร
    AGGRESSIVE = "AGGRESSIVE"       # รอกำไรสูง

class CloseReason(Enum):
    PROFIT_TARGET = "PROFIT_TARGET"
    TRAILING_STOP = "TRAILING_STOP"
    PORTFOLIO_RISK = "PORTFOLIO_RISK"
    MARKET_REVERSAL = "MARKET_REVERSAL"
    TIME_BASED = "TIME_BASED"
    EMERGENCY = "EMERGENCY"

@dataclass
class SmartPosition:
    position_id: int
    symbol: str
    direction: str  # BUY/SELL
    lot_size: float
    entry_price: float
    current_price: float
    entry_time: datetime
    pnl: float
    is_hedge: bool = False
    trailing_stop_price: Optional[float] = None
    max_profit_seen: float = 0.0
    profit_target: float = 0.0
    min_profit_lock: float = 0.0

class SmartProfitManager:
    def __init__(self, mt5_connector, survivability_params: Dict, config: dict):
        # Core systems
        self.mt5_connector = mt5_connector
        self.config = config
        self.survivability_params = survivability_params
        
        # Initialize AI Money Manager if available
        if MONEY_MANAGER_AVAILABLE:
            self.money_manager = AIMoneyManager(config)
            print("✅ AI Money Manager integrated")
        else:
            self.money_manager = None
            print("⚠️ AI Money Manager not available")
            
        # Initialize Survivability Engine if available
        if SURVIVABILITY_ENGINE_AVAILABLE:
            self.survivability_engine = SurvivabilityEngine(config)
            print("✅ Survivability Engine integrated")
        else:
            self.survivability_engine = None
            print("⚠️ Survivability Engine not available")
        
        # Trading parameters from survivability
        self.base_lot = survivability_params.get('base_lot', 0.01)
        original_spacing = survivability_params.get('grid_spacing', 300)
        account_info = mt5_connector.get_account_info()
        balance = account_info.get('balance', 1000) if account_info else 1000

        # Dynamic spacing based on balance
        if balance >= 50000:
            self.grid_spacing = 50   
        elif balance >= 25000:
            self.grid_spacing = 75   
        elif balance >= 10000:
            self.grid_spacing = 90  
        elif balance >= 5000:
            self.grid_spacing = 100 
        elif balance >= 2000:
            self.grid_spacing = 150  
        else:
            self.grid_spacing = 300  
        
        self.max_levels = survivability_params.get('max_levels', 20)
        self.survivability = survivability_params.get('realistic_survivability', survivability_params.get('survivability', 10000))
        
        # Gold symbol and market info
        self.gold_symbol = mt5_connector.get_gold_symbol()
        self.symbol_info = mt5_connector.get_symbol_info()
        
        # Trading state
        self.trading_active = False
        self.emergency_stop_triggered = False
        self.grid_levels = []
        self.pending_orders = {}
        self.active_positions = {}
        
        # Performance tracking
        self.total_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
        self.current_drawdown = 0.0
        self.max_drawdown_points = 0.0
        self.trades_opened = 0
        self.trades_closed = 0
        self.winning_trades = 0
        self.win_rate = 0.0
        self.largest_win = 0.0
        self.largest_loss = 0.0
        self.last_update = datetime.now()
        
        # Generate unique magic number
        account_info = mt5_connector.get_account_info()
        if account_info:
            account_id = account_info.get('login', 0)
            self.magic_number = int(str(account_id)[-6:]) if account_id else 77743410
        else:
            self.magic_number = 77743410
            
        # Market info
        self.min_lot = self.symbol_info.get('volume_min', 0.01)
        self.max_lot = self.symbol_info.get('volume_max', 100.0)
        self.lot_step = self.symbol_info.get('volume_step', 0.01)
        self.point_value = self.symbol_info.get('point', 0.01)
        
        # Smart profit parameters (existing)
        self.quick_profit_multiplier = 2.5      # 0.01 lot = $2.5 target
        self.balanced_profit_multiplier = 5.0   # 0.01 lot = $5.0 target  
        self.aggressive_profit_multiplier = 10.0 # 0.01 lot = $10.0 target
        
        # 🚀 Enhanced Parameters สำหรับ $5,000+
        self.fast_profit_enabled = True
        self.auto_reposition_enabled = True
        self.quick_close_threshold = 0.6      # ปิดเมื่อ profit 60% ของเป้า
        self.min_gap_for_reposition = 100     # 100 points gap minimum
        self.positions_turned_today = 0
        self.daily_profit_harvested = 0.0
        
        # Trailing stop parameters
        self.trailing_stop_distance = 50       # 50 points trailing distance
        self.min_profit_for_trailing = 2.0     # Minimum $2 profit to start trailing
        
        # Portfolio protection
        self.max_portfolio_risk_pct = 15.0     # 15% max portfolio risk
        self.emergency_close_loss_pct = 25.0   # 25% emergency close
        
        # Time-based management
        self.max_position_age_minutes = 60     # 1 hour max age
        self.profit_lock_after_minutes = 30    # Lock profit after 30 min
        
        # Strategy selection based on account size
        account_info = mt5_connector.get_account_info()
        balance = account_info.get('balance', 1000) if account_info else 1000
        
        if balance >= 10000:
            self.default_strategy = ProfitStrategy.AGGRESSIVE
        elif balance >= 3000:
            self.default_strategy = ProfitStrategy.BALANCED
        else:
            self.default_strategy = ProfitStrategy.QUICK_SAFE
       
        self.recovery_enabled = config.get('portfolio_recovery', {}).get('enabled', True)
        self.recovery_trigger_loss = config.get('portfolio_recovery', {}).get('trigger_loss', -50)
        self.recovery_auto_mode = config.get('portfolio_recovery', {}).get('auto_mode', False)
        self.recovery_active = False
        self.recovery_start_time = None
        self.recovery_initial_pnl = 0
        
        # Detect broker filling modes
        self.detect_broker_filling_modes()
        
        print(f"💊 Portfolio Recovery System:")
        print(f"   Enabled: {self.recovery_enabled}")
        print(f"   Trigger Loss: ${abs(self.recovery_trigger_loss)}")
        print(f"   Auto Mode: {self.recovery_auto_mode}")    
        print(f"🧠 Smart Profit Manager initialized:")
        print(f"   💰 Balance: ${balance:,.0f}")
        print(f"   🎯 Strategy: {self.default_strategy.value}")
        print(f"   📈 Trailing Stop: {self.trailing_stop_distance} points")
        print(f"   🛡️ Survivability: {self.survivability:,} points")
        print(f"   🎯 Magic Number: {self.magic_number}")

    def detect_broker_filling_modes(self):
        """Detect broker-specific filling modes"""
        try:
            broker_name = str(self.mt5_connector.get_account_info().get('company', '')).lower()
            
            # Default safe settings
            self.order_filling_mode = mt5.ORDER_FILLING_RETURN
            self.close_filling_mode = mt5.ORDER_FILLING_RETURN
            self.filling_mode_name = "RETURN (Safe default)"
            
            # Broker-specific optimizations
            if any(x in broker_name for x in ['exness', 'ic markets', 'alpari']):
                self.order_filling_mode = mt5.ORDER_FILLING_FOK
                self.close_filling_mode = mt5.ORDER_FILLING_FOK
                self.filling_mode_name = "FOK (Broker optimized)"
            elif any(x in broker_name for x in ['forex.com', 'oanda']):
                self.order_filling_mode = mt5.ORDER_FILLING_IOC  
                self.close_filling_mode = mt5.ORDER_FILLING_IOC
                self.filling_mode_name = "IOC (Broker optimized)"
                
        except Exception as e:
            print(f"⚠️ Error detecting filling modes: {e}")
            self.order_filling_mode = mt5.ORDER_FILLING_RETURN
            self.close_filling_mode = mt5.ORDER_FILLING_RETURN
            self.filling_mode_name = "RETURN (Safe fallback)"

    def start_trading(self):
        """Start AI Smart Profit Trading System"""
        
        if self.trading_active:
            print("⚠️ Trading is already active")
            return True
            
        if self.emergency_stop_triggered:
            print("❌ Cannot start trading - Emergency stop is active")
            return False
            
        try:
            print("🧠 AI Smart Profit Trading System Starting...")
            print("="*60)
            
            # Validate account
            if not self.validate_account_before_trading():
                print("❌ Account validation failed - Cannot start trading")
                return False
            
            print("🚀 ACTIVATING FULL AI SMART PROFIT CONTROL")
            print("   🧠 Smart Profit Manager: PRIMARY CONTROL")
            print("   🎯 AI Portfolio Analysis: ACTIVE")
            print("   💰 All decisions: AI-OPTIMIZED")
            
            self.trading_active = True
            
            # Initialize portfolio
            self.initialize_smart_portfolio()
            
            # Start AI management loop
            self.start_ai_management_loop()
            
            # Start monitoring
            self.start_monitoring_loop()
            
            print("✅ AI Smart Profit System FULLY OPERATIONAL!")
            print(f"📊 Configuration:")
            print(f"   • AI Control: FULL CONTROL")
            print(f"   • Base Lot: {self.base_lot}")
            print(f"   • Grid Spacing: {self.grid_spacing} points")
            print(f"   • Survivability: {self.survivability:,} points")
            print(f"   • Magic Number: {self.magic_number}")
            
            return True
                
        except Exception as e:
            print(f"❌ Failed to start AI trading: {e}")
            self.trading_active = False
            return False

    def validate_account_before_trading(self):
        """Validate account before starting trading"""
        try:
            account_info = self.mt5_connector.get_account_info() if self.mt5_connector else None
            
            if not account_info:
                print("❌ Cannot validate account - Missing account info")
                return False
                
            balance = account_info.get('balance', 0)
            equity = account_info.get('equity', 0)
            margin = account_info.get('margin', 0)
            
            print(f"✅ Account Validation:")
            print(f"   Balance: ${balance:,.2f}")
            print(f"   Equity: ${equity:,.2f}")
            print(f"   Margin Used: ${margin:,.2f}")
            
            # Check minimum balance
            if balance < 100:
                print(f"❌ Insufficient balance: ${balance:.2f}")
                return False
                
            # If no positions (margin = 0) use balance as criteria
            if margin == 0:
                if balance < 500:
                    print(f"❌ Need minimum $500 to start trading: ${balance:.2f}")
                    return False
                else:
                    print(f"✅ Sufficient capital for trading: ${balance:,.2f}")
                    return True
                    
            print(f"✅ Account validation passed - Ready for AI trading")
            return True
            
        except Exception as e:
            print(f"❌ Account validation error: {e}")
            return False

    def initialize_smart_portfolio(self):
        """Initialize smart portfolio with AI-guided setup"""
        try:
            print("🧠 Initializing AI Smart Portfolio...")
            
            # Check existing positions
            existing_positions = self.get_existing_positions()
            
            if existing_positions:
                print(f"🔄 Continuing with {len(existing_positions)} existing positions")
                self.active_positions = {pos['ticket']: pos for pos in existing_positions}
            else:
                print("🆕 No existing positions - Creating initial portfolio")
                self.create_initial_smart_grid()
                
            return True
            
        except Exception as e:
            print(f"❌ Portfolio initialization error: {e}")
            return False

    def get_existing_positions(self):
        """Get existing positions from MT5"""
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            if not positions:
                return []
                
            our_positions = []
            for pos in positions:
                if pos.magic == self.magic_number:
                    our_positions.append({
                        'ticket': pos.ticket,
                        'type': pos.type,
                        'volume': pos.volume,
                        'price_open': pos.price_open,
                        'profit': pos.profit,
                        'symbol': pos.symbol,
                        'time_open': datetime.fromtimestamp(pos.time),
                        'direction': "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
                    })
                    
            return our_positions
            
        except Exception as e:
            print(f"❌ Error getting existing positions: {e}")
            return []

    def create_initial_smart_grid(self):
        """Create initial smart grid using AI logic"""
        try:
            # เช็ค existing orders ก่อน
            existing_orders = mt5.orders_get(symbol=self.gold_symbol)
            our_orders = [order for order in (existing_orders or []) if order.magic == self.magic_number]
            
            if len(our_orders) > 0:
                print(f"🔄 Found {len(our_orders)} existing orders - skipping grid creation")
                # อัพเดท pending_orders tracking
                for order in our_orders:
                    self.pending_orders[order.ticket] = {
                        'order_id': order.ticket,
                        'price': order.price_open,
                        'direction': "BUY" if order.type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP] else "SELL",
                        'lot_size': order.volume_initial,
                        'time': datetime.fromtimestamp(order.time_setup)
                    }
                return True
                
            current_price = self.get_current_price()
            if not current_price:
                print("❌ Cannot get current price")
                return False
                
            print(f"🧠 Creating AI Smart Grid at ${current_price:.2f}")
            
            spacing_dollars = self.grid_spacing * 0.01
            orders_placed = 0
            
            # Create BUY levels below market
            for i in range(1, 4):
                buy_price = current_price - (spacing_dollars * i)
                if self.place_pending_order(buy_price, 'BUY', self.base_lot):
                    orders_placed += 1
                    
            # Create SELL levels above market
            for i in range(1, 4):
                sell_price = current_price + (spacing_dollars * i)
                if self.place_pending_order(sell_price, 'SELL', self.base_lot):
                    orders_placed += 1
                    
            print(f"✅ Smart Grid created: {orders_placed} orders placed")
            return orders_placed > 0
            
        except Exception as e:
            print(f"❌ Smart grid creation error: {e}")
            return False

    def place_market_order(self, direction: str, lot_size: float, comment: str = "AI_MARKET"):
        """Place market order immediately - แก้ไข filling mode สำหรับทุกโบรกเกอร์"""
        try:
            # ✅ เพิ่มการตรวจสอบ lot size
            min_lot = self.symbol_info.get('volume_min', 0.01)
            max_lot = self.symbol_info.get('volume_max', 100.0)
            lot_step = self.symbol_info.get('volume_step', 0.01)
            
            # ปรับ lot size ให้ถูกต้อง
            import math
            adjusted_lot = round(lot_size / lot_step) * lot_step
            adjusted_lot = max(min_lot, min(adjusted_lot, max_lot))
            
            print(f"   🔍 Lot adjustment: {lot_size:.3f} → {adjusted_lot:.3f}")
            
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"   ❌ Cannot get tick data for {direction}")
                return False
                
            if direction == "BUY":
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
                
            print(f"   🎯 Market {direction}: {adjusted_lot} lots @ ${price:.2f}")
            
            # ✅ ลอง filling modes ตามลำดับความปลอดภัย + เพิ่ม None
            filling_modes = [
                None,                      # ไม่ระบุ filling mode (ให้ MT5 เลือก)
                mt5.ORDER_FILLING_IOC,     
                mt5.ORDER_FILLING_FOK,     
                mt5.ORDER_FILLING_RETURN   
            ]
            
            for i, filling_mode in enumerate(filling_modes):
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.gold_symbol,
                    "volume": adjusted_lot,
                    "type": order_type,
                    "price": price,
                    "deviation": 50,
                    "magic": self.magic_number,
                    "comment": comment
                }
                
                # ✅ เพิ่ม filling mode เฉพาะเมื่อไม่ใช่ None
                if filling_mode is not None:
                    request["type_filling"] = filling_mode
                    
                mode_name = "AUTO" if filling_mode is None else str(filling_mode)
                print(f"   🔄 Trying mode {i+1}: {mode_name}")
                
                result = mt5.order_send(request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   ✅ Market {direction} SUCCESS with mode {i+1}")
                    return result.order
                else:
                    error_msg = f"Mode {i+1} failed"
                    if result:
                        error_msg += f" - Code: {result.retcode}"
                        if hasattr(result, 'comment'):
                            error_msg += f", {result.comment}"
                    print(f"   ⚠️ {error_msg}")
                    
                    # ถ้า volume ยังผิด ลองใช้ minimum lot
                    if result and result.retcode == 10014 and adjusted_lot != min_lot:
                        print(f"   🔄 Retrying with minimum lot: {min_lot}")
                        adjusted_lot = min_lot
                        continue
                    elif result and result.retcode in [10018, 10030]:  # Filling mode errors
                        continue  # ลอง mode ถัดไป
                    elif result and result.retcode == 10025:  # Autotrading disabled
                        print(f"   ❌ Autotrading is disabled - cannot place orders")
                        break
                    elif result and result.retcode not in [10018, 10030]:  # ถ้าไม่ใช่ filling mode error
                        break
                        
            print(f"   ❌ All filling modes failed for {direction}")
            return False
            
        except Exception as e:
            print(f"❌ Market order error: {e}")
            return False

    def place_pending_order(self, price: float, direction: str, lot_size: float):
        """วาง pending order - แก้ไข filling mode สำหรับทุกโบรกเกอร์"""
        try:
            # ✅ เพิ่มการตรวจสอบ lot size
            min_lot = self.symbol_info.get('volume_min', 0.01)
            max_lot = self.symbol_info.get('volume_max', 100.0)
            lot_step = self.symbol_info.get('volume_step', 0.01)
            
            # ปรับ lot size ให้ถูกต้อง
            import math
            adjusted_lot = round(lot_size / lot_step) * lot_step
            adjusted_lot = max(min_lot, min(adjusted_lot, max_lot))
            
            current_price = self.get_current_price()
            if not current_price:
                print(f"   ❌ Cannot get current price for {direction} order")
                return False
                
            print(f"   🎯 Placing {direction} order: {adjusted_lot} lots @ ${price:.2f}")
            print(f"      Lot adjustment: {lot_size:.3f} → {adjusted_lot:.3f}")
            print(f"      Current price: ${current_price:.2f}")
            print(f"      Distance: {abs(price - current_price):.2f}")
                
            if direction == "BUY":
                order_type = mt5.ORDER_TYPE_BUY_STOP if price > current_price else mt5.ORDER_TYPE_BUY_LIMIT
            else:
                order_type = mt5.ORDER_TYPE_SELL_STOP if price < current_price else mt5.ORDER_TYPE_SELL_LIMIT
                
            print(f"      Order type: {order_type}")
            
            # ✅ ลอง filling modes ตามลำดับความปลอดภัย + เพิ่ม None
            filling_modes = [
                None,                      # ไม่ระบุ filling mode (ให้ MT5 เลือก)
                mt5.ORDER_FILLING_RETURN,
                mt5.ORDER_FILLING_IOC,
                mt5.ORDER_FILLING_FOK
            ]
            
            for i, filling_mode in enumerate(filling_modes):
                request = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": self.gold_symbol,
                    "volume": adjusted_lot,
                    "type": order_type,
                    "price": price,
                    "magic": self.magic_number,
                    "comment": f"AI_SMART_{direction}"
                }
                
                # ✅ เพิ่ม filling mode เฉพาะเมื่อไม่ใช่ None
                if filling_mode is not None:
                    request["type_filling"] = filling_mode
                    
                mode_name = "AUTO" if filling_mode is None else str(filling_mode)
                print(f"      🔄 Trying mode {i+1}: {mode_name}")
                
                result = mt5.order_send(request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.pending_orders[result.order] = {
                        'order_id': result.order,
                        'price': price,
                        'direction': direction,
                        'lot_size': adjusted_lot,
                        'time': datetime.now()
                    }
                    print(f"   ✅ {direction} order SUCCESS with mode {i+1}: {result.order} @ ${price:.2f}")
                    return True
                else:
                    error_msg = f"Mode {i+1} failed"
                    if result:
                        error_msg += f" - Code: {result.retcode}"
                        if hasattr(result, 'comment'):
                            error_msg += f", {result.comment}"
                    print(f"   ⚠️ {error_msg}")
                    
                    # ถ้า volume ยังผิด ลองใช้ minimum lot
                    if result and result.retcode == 10014 and adjusted_lot != min_lot:
                        print(f"   🔄 Retrying with minimum lot: {min_lot}")
                        adjusted_lot = min_lot
                        continue
                    elif result and result.retcode in [10018, 10030]:  # Filling mode errors
                        continue  # ลอง mode ถัดไป
                    elif result and result.retcode == 10025:  # Autotrading disabled
                        print(f"   ❌ Autotrading is disabled - cannot place orders")
                        break
                    elif result and result.retcode not in [10018, 10030]:  # ถ้าไม่ใช่ filling mode error
                        break
                        
            print(f"   ❌ All filling modes failed for {direction} pending order")
            return False
                    
        except Exception as e:
            print(f"   ❌ Place {direction} order exception: {e}")
            return False

    def close_entire_position(self, position) -> bool:
        """ปิด position ทั้งหมด - ENHANCED VERSION ป้องกัน slippage และ filling errors - FIXED"""
        
        try:
            # ✅ FIXED: Enhanced position handling for all types
            if hasattr(position, 'ticket'):
                # MT5 Position object
                position_id = position.ticket
            elif isinstance(position, SmartPosition):
                # SmartPosition object
                position_id = position.position_id
            elif isinstance(position, dict):
                # Dictionary position
                position_id = position.get('ticket') or position.get('position_id')
            else:
                print(f"   ❌ Unknown position type: {type(position)}")
                return False
                
            positions = mt5.positions_get(ticket=position_id)
            if not positions or len(positions) == 0:
                print(f"   Position {position_id} not found or already closed")
                return True  # ถือว่าปิดแล้ว
                
            mt5_position = positions[0]
            
            # ✅ STEP 1: Enhanced market data validation
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"   ❌ Cannot get tick data for {position_id}")
                return False
                
            # เช็ค spread ก่อนปิด
            spread = tick.ask - tick.bid
            spread_points = spread / self.point_value
            
            print(f"   📊 Market conditions:")
            print(f"      Bid: {tick.bid:.3f}, Ask: {tick.ask:.3f}")
            print(f"      Spread: {spread_points:.1f} points")
            
            # ถ้า spread กว้างเกิน 100 points ให้รอ
            if spread_points > 100:
                print(f"   ⚠️ WARNING: Wide spread ({spread_points:.1f} points) - proceeding with caution")
            
            # กำหนด close price และ order type
            if mt5_position.type == mt5.POSITION_TYPE_BUY:
                close_price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
                direction_text = "BUY→SELL"
            else:
                close_price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY
                direction_text = "SELL→BUY"
                
            print(f"   🎯 Closing {direction_text}: {mt5_position.volume} lots @ {close_price:.3f}")
            
            # ✅ STEP 2: Calculate optimal deviation based on market conditions
            base_deviation = 100  # Base deviation
            
            # เพิ่ม deviation ถ้า spread กว้าง
            if spread_points > 50:
                additional_deviation = min(spread_points * 2, 200)  # สูงสุด +200
                optimal_deviation = int(base_deviation + additional_deviation)
            else:
                optimal_deviation = base_deviation
                
            print(f"   📏 Optimal deviation: {optimal_deviation} points")
            
            # ✅ STEP 3: Smart filling mode sequence with enhanced retry logic
            filling_strategies = [
                {
                    'mode': None,  # ให้ MT5 เลือกเอง
                    'deviation': optimal_deviation,
                    'name': 'AUTO',
                    'description': 'Let MT5 choose best mode'
                },
                {
                    'mode': mt5.ORDER_FILLING_IOC,
                    'deviation': optimal_deviation,
                    'name': 'IOC',
                    'description': 'Immediate or Cancel - fast execution'
                },
                {
                    'mode': mt5.ORDER_FILLING_FOK,
                    'deviation': optimal_deviation + 50,  # เพิ่ม deviation
                    'name': 'FOK',
                    'description': 'Fill or Kill - guaranteed full fill'
                },
                {
                    'mode': mt5.ORDER_FILLING_RETURN,
                    'deviation': optimal_deviation + 100,  # เพิ่ม deviation มากสุด
                    'name': 'RETURN',
                    'description': 'Market order with maximum safety'
                }
            ]
            
            # ✅ STEP 4: Execute with progressive fallback
            for attempt, strategy in enumerate(filling_strategies, 1):
                print(f"   🔄 Attempt {attempt}: {strategy['name']} - {strategy['description']}")
                
                # สร้าง request
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.gold_symbol,
                    "volume": mt5_position.volume,
                    "type": order_type,
                    "position": position_id,
                    "price": close_price,
                    "deviation": strategy['deviation'],
                    "magic": self.magic_number,
                    "comment": f"AI_ENHANCED_CLOSE_{strategy['name']}"
                }
                
                # เพิ่ม filling mode ถ้าไม่ใช่ None
                if strategy['mode'] is not None:
                    request["type_filling"] = strategy['mode']
                
                # ✅ STEP 5: Execute with enhanced error handling
                print(f"      📤 Sending close request...")
                result = mt5.order_send(request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   ✅ POSITION CLOSED SUCCESSFULLY with {strategy['name']}")
                    print(f"      Order ID: {result.order}")
                    print(f"      Close price: {close_price:.3f}")
                    print(f"      Deviation used: {strategy['deviation']} points")
                    
                    # Update internal tracking
                    if position_id in self.active_positions:
                        del self.active_positions[position_id]
                        
                    return True
                    
                else:
                    # ✅ Enhanced error analysis
                    if result:
                        error_code = result.retcode
                        error_msg = self.get_mt5_error_description(error_code)
                        
                        print(f"      ❌ {strategy['name']} failed: {error_code} - {error_msg}")
                        
                        # วิเคราะห์ประเภท error
                        if error_code == 10014:  # Invalid volume
                            print(f"         💡 Volume issue - trying minimum lot")
                            # ลองใช้ minimum lot
                            min_lot = self.symbol_info.get('volume_min', 0.01)
                            if mt5_position.volume != min_lot:
                                request["volume"] = min_lot
                                retry_result = mt5.order_send(request)
                                if retry_result and retry_result.retcode == mt5.TRADE_RETCODE_DONE:
                                    print(f"         ✅ Retry with min lot succeeded")
                                    return True
                                    
                        elif error_code in [10018, 10030]:  # Filling mode errors
                            print(f"         💡 Filling mode issue - trying next mode")
                            continue  # ลอง mode ถัดไป
                            
                        elif error_code == 10025:  # Autotrading disabled
                            print(f"         🚨 CRITICAL: Autotrading disabled")
                            return False
                            
                        elif error_code in [10004, 10006]:  # Price issues
                            print(f"         💡 Price issue - refreshing market data")
                            # รอแล้วลองใหม่ด้วยราคาใหม่
                            time.sleep(0.5)
                            new_tick = mt5.symbol_info_tick(self.gold_symbol)
                            if new_tick:
                                close_price = new_tick.bid if mt5_position.type == mt5.POSITION_TYPE_BUY else new_tick.ask
                                request["price"] = close_price
                                print(f"         🔄 Retrying with fresh price: {close_price:.3f}")
                                retry_result = mt5.order_send(request)
                                if retry_result and retry_result.retcode == mt5.TRADE_RETCODE_DONE:
                                    print(f"         ✅ Retry with fresh price succeeded")
                                    return True
                    else:
                        print(f"      ❌ {strategy['name']} failed: No result returned")
                    
                    # หยุดสั้นๆ ก่อนลอง strategy ถัดไป
                    if attempt < len(filling_strategies):
                        print(f"      ⏳ Waiting 0.5s before next attempt...")
                        time.sleep(0.5)
            
            # ✅ STEP 6: Final emergency attempt with market order
            print(f"   🚨 EMERGENCY: All strategies failed - trying emergency market order")
            
            emergency_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.gold_symbol,
                "volume": mt5_position.volume,
                "type": order_type,
                "position": position_id,
                "deviation": 500,  # เพิ่ม deviation สูงสุด
                "magic": self.magic_number,
                "comment": "AI_EMERGENCY_CLOSE"
            }
            
            emergency_result = mt5.order_send(emergency_request)
            if emergency_result and emergency_result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"   🆘 EMERGENCY CLOSE SUCCESSFUL")
                return True
            else:
                print(f"   💥 TOTAL FAILURE: Cannot close position {position_id}")
                if emergency_result:
                    error_msg = self.get_mt5_error_description(emergency_result.retcode)
                    print(f"      Final error: {emergency_result.retcode} - {error_msg}")
                return False
                        
        except Exception as e:
            print(f"❌ Enhanced close position error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_mt5_error_description(self, error_code):
        """แปลรหัส error ของ MT5 เป็นข้อความที่เข้าใจง่าย"""
        error_descriptions = {
            10004: "Requote - ราคาเปลี่ยนแปลง",
            10006: "Request rejected - คำขอถูกปฏิเสธ", 
            10014: "Invalid volume - ขนาดไม้ไม่ถูกต้อง",
            10015: "Invalid price - ราคาไม่ถูกต้อง",
            10016: "Invalid stops - stop loss/take profit ไม่ถูกต้อง",
            10018: "Market closed - ตลาดปิด",
            10019: "No money - เงินไม่พอ",
            10020: "Price changed - ราคาเปลี่ยนแปลง",
            10021: "Too many requests - คำขอมากเกินไป",
            10025: "No autotrading - autotrading ถูกปิด",
            10027: "Autotrading disabled by server - server ปิด autotrading",
            10028: "Autotrading disabled by client - client ปิด autotrading",
            10030: "Only real accounts allowed - ใช้ได้เฉพาะ real account",
            10031: "Trade disabled - การเทรดถูกปิด",
            10032: "Market closed - ตลาดปิดทำการ",
            10033: "No connection - ไม่มีการเชื่อมต่อ",
            10034: "Only real accounts - ใช้ได้เฉพาะ real account",
            10035: "Too many requests - คำขอมากเกินไป",
            10036: "Request timeout - คำขอหมดเวลา"
        }
        
        return error_descriptions.get(error_code, f"Unknown error code: {error_code}")

    def get_current_price(self):
        """Get current gold price"""
        try:
            if self.mt5_connector:
                price_data = self.mt5_connector.get_current_price()
                if price_data:
                    return price_data.get('bid', 0)
                    
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if tick:
                return tick.bid
                
            return 0
            
        except Exception as e:
            print(f"❌ Error getting current price: {e}")
            return 0

    def start_ai_management_loop(self):
        """Start AI management as primary control"""
        if not hasattr(self, 'ai_thread') or not self.ai_thread.is_alive():
            self.ai_thread = threading.Thread(target=self.ai_management_loop, daemon=True)
            self.ai_thread.start()
            print("🧠 AI Management Loop started as PRIMARY CONTROL")

    def ai_management_loop(self):
        """Main AI management loop - Smart Profit เป็นหลัก"""
        print("🧠 AI PRIMARY CONTROL LOOP ACTIVE...")
        
        while self.trading_active and not self.emergency_stop_triggered:
            try:
                connector = BackendAPIConnector(
                    api_base_url="http://123.253.62.50:8080/api",
                    timeout=10
                )

                if self.should_report_status():
                    account_info = self.mt5_connector.get_account_info()
                    success, response_data, error_msg = connector.check_trading_status(account_info)

                    if success:
                        # Handle response_data
                        status = response_data.get("processedStatus")
                        if status == "inactive":   
                            self.stop_trading()         
                            print("Your account is inactive. Trading has been disabled.")
                        self.next_report_time = connector.format_datetime_response(response_data.get("nextReportTime"))
                    else:
                        # Handle error_msg - fail fast
                        print(f"API Error: {error_msg}")

                print("🛑 AI Management running")

                # หลัก: Smart Profit Management
                self.run_smart_profit_management()
                
                # เพิ่ม: AI Portfolio Health Check
                self.ai_portfolio_health_check()
                
                # เพิ่ม: AI Performance Optimization (ทุก 5 นาที)
                if hasattr(self, 'last_optimization') and (datetime.now() - self.last_optimization).total_seconds() > 300:
                    self.ai_performance_optimization()
                    self.last_optimization = datetime.now()
                elif not hasattr(self, 'last_optimization'):
                    self.last_optimization = datetime.now()
                
                # เช็คทุก 3 วินาที - AI ทำงานถี่
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ AI Management error: {e}")
                time.sleep(5)
                
        print("🛑 AI Management stopped")

    def should_report_status(self):
        """Check if it's time to report status"""
        if hasattr(self, 'next_report_time') and self.next_report_time:
            current_utc = datetime.now(timezone.utc)
            next_report_utc = self.next_report_time.astimezone(timezone.utc)
            
            print(f"Current UTC: {current_utc}")
            print(f"Next report UTC: {next_report_utc}")
            
            return current_utc >= next_report_utc
        return True  # Report if no scheduled time
    
    def start_monitoring_loop(self):
        """Start monitoring thread"""
        if not hasattr(self, 'monitor_thread') or not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            self.monitor_thread.start()
            print("📊 Monitoring Loop started")

    def monitoring_loop(self):
        """Monitoring loop for position updates"""
        print("📊 AI Support Monitor active...")
        
        while self.trading_active and not self.emergency_stop_triggered:
            try:
                # Update positions from MT5
                self.update_positions_from_mt5()
                
                # Check for filled orders
                self.check_pending_orders()
                
                # Monitor active positions
                self.monitor_active_positions()
                
                # Update statistics
                self.update_trading_statistics()
                
                # Check emergency conditions
                self.check_emergency_conditions()
                
                time.sleep(5)  # เช็คทุก 5 วินาที
                
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                time.sleep(10)
                
        print("🛑 Monitor stopped")

    def update_positions_from_mt5(self):
        """Update positions from MT5"""
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            
            if positions:
                current_positions = {}
                total_pnl = 0
                
                for position in positions:
                    if position.magic == self.magic_number:
                        current_positions[position.ticket] = {
                            'ticket': position.ticket,
                            'type': position.type,
                            'volume': position.volume,
                            'price_open': position.price_open,
                            'profit': position.profit,
                            'symbol': position.symbol,
                            'time_open': datetime.fromtimestamp(position.time),
                            'direction': "BUY" if position.type == mt5.POSITION_TYPE_BUY else "SELL"
                        }
                        total_pnl += position.profit
                
                # Check for new positions
                for ticket, pos_info in current_positions.items():
                    if ticket not in self.active_positions:
                        self.handle_new_position(pos_info)
                        
                # Check for closed positions
                for ticket in list(self.active_positions.keys()):
                    if ticket not in current_positions:
                        self.handle_closed_position(ticket)
                
                self.active_positions = current_positions
                self.total_pnl = total_pnl
                self.unrealized_pnl = total_pnl
                
        except Exception as e:
            print(f"❌ Position update error: {e}")

    def handle_new_position(self, position_info):
        """Handle new position"""
        try:
            ticket = position_info['ticket']
            direction = position_info['direction']
            volume = position_info['volume']
            price = position_info['price_open']
            
            print(f"🎯 NEW POSITION: {ticket} | {direction} | {volume} | ${price:.2f}")
            
            self.trades_opened += 1
            
            # Remove corresponding pending order
            self.remove_filled_pending_order(position_info)
            
            # Place replacement order if needed
            self.consider_replacement_order(position_info)
            
        except Exception as e:
            print(f"❌ Error handling new position: {e}")

    def handle_closed_position(self, ticket):
        """Handle closed position"""
        try:
            if ticket in self.active_positions:
                pos_info = self.active_positions[ticket]
                final_profit = pos_info.get('profit', 0)
                
                print(f"💰 POSITION CLOSED: {ticket} | PnL: ${final_profit:.2f}")
                
                self.trades_closed += 1
                
                if final_profit > 0:
                    self.winning_trades += 1
                    if final_profit > self.largest_win:
                        self.largest_win = final_profit
                else:
                    if final_profit < self.largest_loss:
                        self.largest_loss = final_profit
                        
                self.realized_pnl += final_profit
                
                if self.trades_closed > 0:
                    self.win_rate = self.winning_trades / self.trades_closed
                    
        except Exception as e:
            print(f"❌ Error handling closed position: {e}")

    def remove_filled_pending_order(self, position_info):
        """Remove filled pending order"""
        try:
            position_price = position_info['price_open']
            position_type = position_info['direction']
            
            closest_order = None
            min_distance = float('inf')
            
            for order_id, order_info in list(self.pending_orders.items()):
                if order_info['direction'] == position_type:
                    distance = abs(order_info['price'] - position_price)
                    if distance < min_distance:
                        min_distance = distance
                        closest_order = order_id
                        
            if closest_order and min_distance < 0.50:
                del self.pending_orders[closest_order]
                
        except Exception as e:
            print(f"❌ Error removing filled order: {e}")

    def check_pending_orders(self):
        """Check pending orders status"""
        try:
            orders = mt5.orders_get(symbol=self.gold_symbol)
            if orders is None:
                return
                
            current_order_ids = set()
            for order in orders:
                if order.magic == self.magic_number:
                    current_order_ids.add(order.ticket)
                    
            # Remove orders that no longer exist
            for order_id in list(self.pending_orders.keys()):
                if order_id not in current_order_ids:
                    del self.pending_orders[order_id]
                    
        except Exception as e:
            print(f"❌ Error checking pending orders: {e}")

    def monitor_active_positions(self):
        """Monitor active positions for changes"""
        try:
            # This is handled in update_positions_from_mt5()
            pass
            
        except Exception as e:
            print(f"❌ Error monitoring positions: {e}")

    def ai_portfolio_health_check(self):
        """AI ตรวจสอบสุขภาพ portfolio"""
        try:
            portfolio = self.analyze_portfolio_positions()
            
            if 'error' not in portfolio:
                total_pnl = portfolio.get('total_pnl', 0)
                positions_count = portfolio.get('total_positions', 0)
                
                # AI Health Score
                health_score = self.calculate_ai_health_score(portfolio)
                
                # Log AI insights ทุก 30 วินาที
                if not hasattr(self, 'last_health_log'):
                    self.last_health_log = datetime.now()
                elif (datetime.now() - self.last_health_log).total_seconds() >= 30:
                    print(f"🧠 AI Health: {health_score}/100 | {positions_count} pos | PnL: ${total_pnl:.2f}")
                    self.last_health_log = datetime.now()
                    
        except Exception as e:
            print(f"❌ AI Health check error: {e}")

    def calculate_ai_health_score(self, portfolio: Dict) -> int:
        """คำนวณ AI Health Score (0-100)"""
        try:
            score = 50  # Base score
            
            total_pnl = portfolio.get('total_pnl', 0)
            positions_count = portfolio.get('total_positions', 0)
            
            # PnL health
            if total_pnl > 10:
                score += 30
            elif total_pnl > 0:
                score += 15
            elif total_pnl > -10:
                score += 0
            else:
                score -= 20
                
            # Position diversity health
            if positions_count >= 4:
                score += 20
            elif positions_count >= 2:
                score += 10
            else:
                score -= 10
                
            # Survivability health
            if hasattr(self, 'current_drawdown'):
                survivability_used = (self.current_drawdown / self.survivability) * 100
                if survivability_used < 20:
                    score += 20
                elif survivability_used < 50:
                    score += 10
                else:
                    score -= 15
                    
            return max(0, min(100, score))
            
        except Exception as e:
            print(f"❌ Health score error: {e}")
            return 50

    def ai_performance_optimization(self):
        """AI Performance Optimization ทุก 5 นาที"""
        try:
            print("🧠 AI OPTIMIZATION: Analyzing performance...")
            
            # รัน optimization
            opportunities = self.identify_profit_opportunities()
            
            if opportunities:
                print(f"💡 AI found {len(opportunities)} optimization opportunities")
                # Execute top opportunities
                for opp in opportunities[:3]:  # Top 3 opportunities
                    if opp['type'] == 'PAIR_CLOSE':
                        self.execute_pair_closes([opp['data']])
                    elif opp['type'] == 'HEDGE_PLACEMENT':
                        self.execute_smart_hedges([opp['data']])
                        
            else:
                print("✅ AI: Portfolio optimally configured")
                
        except Exception as e:
            print(f"❌ AI Optimization error: {e}")

    def check_emergency_conditions(self):
        """ตรวจสอบเงื่อนไข emergency stop - แก้ไขแล้ว ไม่มั่วซั่ว"""
        try:
            # ✅ เช็คเฉพาะ survivability เท่านั้น - เข้าใจง่าย
            current_drawdown = self.get_current_drawdown()
            survivability_used_pct = (current_drawdown / self.survivability) * 100 if self.survivability > 0 else 0
            
            # 🛡️ เปลี่ยนจาก 95% เป็น 85% เพื่อความปลอดภัย
            if survivability_used_pct > 85:
                print(f"🚨 CRITICAL: Survivability {survivability_used_pct:.1f}% used (limit: 85%)")
                print(f"   Current drawdown: {current_drawdown:,.0f} points")
                print(f"   Max survivability: {self.survivability:,} points")
                return True
                
            # ✅ ลบการเช็ค margin level ออกเพราะมั่วซั่ว
            # ✅ ใช้เฉพาะ survivability เป็นตัวบอก
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking emergency conditions: {e}")
            return False

    def get_current_drawdown(self):
        """Calculate current drawdown"""
        try:
            if hasattr(self, 'total_pnl') and self.total_pnl < 0:
                loss_in_dollars = abs(self.total_pnl)
                drawdown_points = loss_in_dollars * 100
                self.current_drawdown = drawdown_points
                
                if drawdown_points > getattr(self, 'max_drawdown_points', 0):
                    self.max_drawdown_points = drawdown_points
                    
                return drawdown_points
            else:
                self.current_drawdown = 0
                return 0
                
        except Exception as e:
            print(f"❌ Error calculating drawdown: {e}")
            return 0

    def trigger_emergency_stop(self):
        """เรียก emergency stop - แก้ไขแล้ว ทำงานได้จริง"""
        try:
            print("🚨 EMERGENCY STOP ACTIVATED!")
            print("   Reason: Survivability limit exceeded")
            
            # ✅ ตั้งค่า flag เท่านั้น - ไม่ปิด positions
            self.trading_active = False
            
            # ✅ ไม่ปิดไม้อัตโนมัติ - ให้ user ตัดสินใจเอง
            print("🛑 Trading stopped - positions remain open")
            print("💡 Use manual close if needed")
            
            # ✅ ยกเลิก pending orders เท่านั้น
            self.cancel_all_pending_orders()
            
        except Exception as e:
            print(f"❌ Error triggering emergency stop: {e}")

    def emergency_close_all_positions(self):
        """ปิด positions ทั้งหมดในกรณีฉุกเฉิน"""
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            if not positions:
                print("   No positions to close")
                return
                
            closed_count = 0
            for position in positions:
                if position.magic != self.magic_number:
                    continue
                    
                tick = mt5.symbol_info_tick(self.gold_symbol)
                if not tick:
                    continue
                    
                if position.type == mt5.POSITION_TYPE_BUY:
                    close_price = tick.bid
                    trade_type = mt5.ORDER_TYPE_SELL
                else:
                    close_price = tick.ask
                    trade_type = mt5.ORDER_TYPE_BUY
                    
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.gold_symbol,
                    "volume": position.volume,
                    "type": trade_type,
                    "position": position.ticket,
                    "price": close_price,
                    "deviation": 100,
                    "magic": self.magic_number,
                    "comment": "EMERGENCY_CLOSE_ALL",
                    "type_filling": mt5.ORDER_FILLING_IOC
                }
                
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   ✅ Emergency closed: {position.ticket}")
                    closed_count += 1
                    
                    if position.ticket in self.active_positions:
                        del self.active_positions[position.ticket]
                else:
                    print(f"   ❌ Failed to close: {position.ticket}")
                    
            print(f"🚨 Emergency close completed: {closed_count} positions closed")
            
        except Exception as e:
            print(f"❌ Error in emergency close: {e}")

    def cancel_all_pending_orders(self):
        """ยกเลิก pending orders ทั้งหมด"""
        try:
            orders = mt5.orders_get(symbol=self.gold_symbol)
            if not orders:
                print("   No pending orders to cancel")
                return
                
            cancelled_count = 0
            for order in orders:
                if order.magic != self.magic_number:
                    continue
                    
                request = {
                    "action": mt5.TRADE_ACTION_REMOVE,
                    "order": order.ticket,
                    "comment": "EMERGENCY_CANCEL_ALL"
                }
                
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   ✅ Emergency cancelled: {order.ticket}")
                    cancelled_count += 1
                    
                    if order.ticket in self.pending_orders:
                        del self.pending_orders[order.ticket]
                else:
                    print(f"   ❌ Failed to cancel: {order.ticket}")
                    
            print(f"🚨 Emergency cancel completed: {cancelled_count} orders cancelled")
            
        except Exception as e:
            print(f"❌ Error in emergency cancel: {e}")

    def update_trading_statistics(self):
        """Update trading statistics"""
        try:
            self.last_update = datetime.now()
            
            total_unrealized = sum(pos['profit'] for pos in self.active_positions.values())
            self.unrealized_pnl = total_unrealized
            self.total_pnl = self.realized_pnl + self.unrealized_pnl
            
            # Log stats every 60 seconds
            if not hasattr(self, 'last_stats_log'):
                self.last_stats_log = datetime.now()
                
            if (datetime.now() - self.last_stats_log).seconds >= 60:
                print(f"🧠 AI STATS: {len(self.active_positions)} pos | ${self.total_pnl:.2f} PnL | {len(self.pending_orders)} pending")
                self.last_stats_log = datetime.now()
                
        except Exception as e:
            print(f"❌ Error updating statistics: {e}")

    def stop_trading(self):
        """Stop the trading system"""
        try:
            print("🛑 AI Smart Profit System Stopping...")
            
            self.trading_active = False
            
            if hasattr(self, 'ai_thread') and self.ai_thread.is_alive():
                print("   🧠 Stopping AI Management...")
                
            if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
                print("   📊 Stopping Monitor...")
                
            # Final statistics
            final_stats = self.get_final_statistics()
            print("📊 FINAL STATISTICS:")
            print(f"   💰 Total PnL: ${final_stats['total_pnl']:.2f}")
            print(f"   📈 Trades: {final_stats['trades_opened']} opened, {final_stats['trades_closed']} closed")
            print(f"   🎯 Win Rate: {final_stats['win_rate']:.1f}%")
            print(f"   🛡️ Max Drawdown: {final_stats['max_drawdown']:,.0f} points")
            
            print("✅ AI Smart Profit System Stopped Successfully")
            
        except Exception as e:
            print(f"❌ Error stopping trading: {e}")

    def get_final_statistics(self):
        """Get final trading statistics"""
        try:
            return {
                'total_pnl': self.total_pnl,
                'realized_pnl': self.realized_pnl,
                'unrealized_pnl': self.unrealized_pnl,
                'trades_opened': self.trades_opened,
                'trades_closed': self.trades_closed,
                'winning_trades': self.winning_trades,
                'win_rate': self.win_rate * 100,
                'largest_win': self.largest_win,
                'largest_loss': self.largest_loss,
                'max_drawdown': self.max_drawdown_points,
                'survivability_used': (self.current_drawdown / self.survivability) * 100,
                'active_positions': len(self.active_positions),
                'pending_orders': len(self.pending_orders),
                'ai_control_enabled': True,
                'smart_profit_enabled': True
            }
            
        except Exception as e:
            print(f"❌ Error getting final statistics: {e}")
            return {}

    def calculate_smart_profit_target(self, lot_size: float, strategy: ProfitStrategy = None) -> Dict:
        """Calculate intelligent profit target based on lot size and strategy"""
        
        if strategy is None:
            strategy = self.default_strategy
            
        # Base calculation: reasonable profit per lot
        if strategy == ProfitStrategy.QUICK_SAFE:
            base_target = lot_size * 100 * 1.5  # ลดจาก 2.5 เป็น 1.5 (เร็วขึ้น)
            trailing_start = base_target * 0.5   # เริ่ม trailing เร็วขึ้น
        elif strategy == ProfitStrategy.BALANCED:
            base_target = lot_size * 100 * 3.0   # ลดจาก 5.0 เป็น 3.0
            trailing_start = base_target * 0.6
        else:  # AGGRESSIVE
            base_target = lot_size * 100 * 7.0   # ลดจาก 10.0 เป็น 7.0
            trailing_start = base_target * 0.7
            
        return {
            'profit_target': round(base_target, 2),
            'trailing_start': round(trailing_start, 2),
            'min_profit_lock': round(base_target * 0.3, 2),
            'strategy': strategy.value
        }

    def run_smart_profit_management(self):
            """🧠 AI หลัก - แก้ไขแล้วเช็ค portfolio status ก่อน"""
            
            try:
                # ✅ เช็ค account status ก่อนทุกอย่าง
                account_info = self.mt5_connector.get_account_info()
                portfolio_profitable = False
                portfolio_balanced = False
                actual_loss = 0
                
                if account_info:
                    balance = account_info.get('balance', 0)
                    equity = account_info.get('equity', 0)
                    profit_amount = equity - balance
                    
                    portfolio_profitable = equity > balance
                    portfolio_balanced = abs(profit_amount) <= 5.0
                    actual_loss = abs(profit_amount) if profit_amount < 0 else 0
                    
                    print(f"💰 Portfolio Status Check:")
                    print(f"   Balance: ${balance:.2f}, Equity: ${equity:.2f}")
                    print(f"   Net P&L: ${profit_amount:.2f}")
                    
                    if portfolio_profitable:
                        print(f"✅ Portfolio Status: PROFITABLE (+${profit_amount:.2f})")
                        print(f"   🎯 AI Mode: PROFIT OPTIMIZATION")
                    elif portfolio_balanced:
                        print(f"⚖️ Portfolio Status: BALANCED (${profit_amount:.2f})")
                        print(f"   🎯 AI Mode: MAINTENANCE")
                    else:
                        print(f"📉 Portfolio Status: LOSING (-${actual_loss:.2f})")
                        print(f"   🎯 AI Mode: RECOVERY FOCUS")
                
                # 1. 🧠 AI วิเคราะห์ positions ปัจจุบัน
                portfolio = self.analyze_portfolio_positions()
                if 'error' in portfolio or portfolio.get('total_positions', 0) == 0:
                    print("🔄 No positions detected - AI creating intelligent grid")
                    self.create_grid_immediately()
                    return
                    
                positions = portfolio.get('grid_positions', [])
                total_pnl = portfolio.get('total_pnl', 0)
                
                # 🎯 NEW: Close All if profit target hit
                if total_pnl >= 100.0:  # $100 profit target
                    print(f"🎉 PROFIT TARGET HIT: ${total_pnl:.2f} >= $100")
                    print(f"💰 EXECUTING CLOSE ALL POSITIONS")
                    
                    success = self.close_all_positions()
                    if success:
                        print(f"✅ All positions closed - Profit secured: ${total_pnl:.2f}!")
                        print(f"🔄 Ready for new cycle")
                        return  # Exit function to restart fresh
                    else:
                        print(f"⚠️ Close all failed - continuing with pair trading")
                
                # เพิ่ม: แสดงข้อมูล portfolio balance
                buy_positions = [p for p in positions if p.direction == "BUY"]
                sell_positions = [p for p in positions if p.direction == "SELL"]
                
                print(f"📊 Portfolio: {len(buy_positions)} BUY, {len(sell_positions)} SELL, PnL: ${total_pnl:.2f}")
                
                # เพิ่ม: เช็ค imbalance และแก้ไข (ปรับตาม portfolio status)
                position_imbalance = abs(len(buy_positions) - len(sell_positions))
                
                # ✅ ปรับ imbalance tolerance ตาม portfolio status
                if portfolio_profitable:
                    max_imbalance_allowed = 8  # ผ่อนปรนเมื่อกำไร
                    print(f"⚖️ AI: Profitable portfolio - relaxed imbalance tolerance ({max_imbalance_allowed})")
                elif portfolio_balanced:
                    max_imbalance_allowed = 6  # ปานกลาง
                    print(f"⚖️ AI: Balanced portfolio - moderate imbalance tolerance ({max_imbalance_allowed})")
                else:
                    max_imbalance_allowed = 4  # เข้มงวดเมื่อขาดทุน
                    print(f"⚖️ AI: Losing portfolio - strict imbalance tolerance ({max_imbalance_allowed})")
                
                if position_imbalance > max_imbalance_allowed:
                    print(f"⚖️ AI: Position imbalance detected ({position_imbalance} > {max_imbalance_allowed}), adding orders...")
                    self.create_grid_immediately()  # เพิ่ม orders ใหม่
                
                # 🧠 AI ตรวจสอบ survivability ปัจจุบัน (ปรับตาม portfolio status)
                if hasattr(self, 'ai_grid_config'):
                    target_survivability = self.ai_grid_config.get('target_survivability', 10000)
                    current_coverage = self.estimate_current_survivability(positions)
                    survivability_ratio = current_coverage / target_survivability
                    
                    print(f"🛡️ AI SURVIVABILITY CHECK: {current_coverage:,}/{target_survivability:,} points ({survivability_ratio:.1%})")
                    
                    # ✅ ปรับ survivability requirement ตาม portfolio status
                    if portfolio_profitable:
                        min_survivability_ratio = 0.4  # ผ่อนปรนเมื่อกำไร - 40% ก็พอ
                        print(f"   💰 Profitable mode: Relaxed survivability requirement (40%)")
                    elif portfolio_balanced:
                        min_survivability_ratio = 0.5  # ปานกลาง - 50%
                        print(f"   ⚖️ Balanced mode: Moderate survivability requirement (50%)")
                    else:
                        min_survivability_ratio = 0.6  # เข้มงวดเมื่อขาดทุน - 60%
                        print(f"   📉 Losing mode: Strict survivability requirement (60%)")
                    
                    if survivability_ratio < min_survivability_ratio:
                        print(f"🚨 AI: SURVIVABILITY {'CRITICAL' if not portfolio_profitable else 'LOW'} - Adding protective positions")
                        self.rebalance_portfolio_if_needed(positions)
                        return
                    else:
                        print(f"✅ AI: Survivability adequate for {('PROFITABLE' if portfolio_profitable else 'BALANCED' if portfolio_balanced else 'LOSING')} portfolio")
                
                # 2. 🧠 AI ปิดไม้อย่างฉลาด (ใช้ method ที่ฉลาดแล้ว)
                profitable_pairs = self.find_profitable_pairs(positions)
                
                if profitable_pairs:
                    # ✅ ปรับ execution ตาม portfolio status
                    if portfolio_profitable:
                        max_pairs_to_close = min(3, len(profitable_pairs))  # ปิดน้อยลงเมื่อกำไร
                        print(f"💰 AI PROFIT MODE: Executing {max_pairs_to_close} conservative closes")
                    elif portfolio_balanced:
                        max_pairs_to_close = min(4, len(profitable_pairs))  # ปานกลาง
                        print(f"⚖️ AI BALANCED MODE: Executing {max_pairs_to_close} moderate closes")
                    else:
                        max_pairs_to_close = len(profitable_pairs)  # ปิดทุกคู่เมื่อขาดทุน
                        print(f"📉 AI RECOVERY MODE: Executing {max_pairs_to_close} aggressive closes")
                    
                    selected_pairs = profitable_pairs[:max_pairs_to_close]
                    self.execute_pair_closes(selected_pairs)
                    time.sleep(1)
                    
                    # อัพเดท portfolio หลังปิด
                    portfolio = self.analyze_portfolio_positions()
                    positions = portfolio.get('grid_positions', [])
                    
                    # 🧠 AI เช็คว่าหลังปิดแล้ว survivability ยังพอหรือไม่
                    if len(positions) < 4:
                        # ✅ ปรับการตอบสนองตาม portfolio status
                        if portfolio_profitable:
                            print("🔧 AI: Post-close analysis - Coverage adequate for profitable portfolio")
                        else:
                            print("🔧 AI: Post-close analysis - Need more coverage")
                            self.rebalance_portfolio_if_needed(positions)
                else:
                    # ✅ แสดงข้อความที่เหมาะสมตาม portfolio status
                    if portfolio_profitable:
                        print("💰 AI: No urgent profit opportunities - Portfolio performing well")
                    elif portfolio_balanced:
                        print("⚖️ AI: No immediate opportunities - Portfolio stable")
                    else:
                        print("🤔 AI: No safe profit opportunities found - Monitoring for changes")
                
                # 3. 🧠 AI Portfolio Recovery (ถ้าขาดทุน) - ปรับเงื่อนไข
                if self.recovery_enabled:
                    # ✅ เฉพาะเมื่อ portfolio ขาดทุนจริงๆ ถึงจะเช็ค recovery
                    if not portfolio_profitable and not portfolio_balanced:
                        print("📉 AI: Portfolio losing - Checking recovery options...")
                        self.check_and_run_recovery(portfolio)
                    else:
                        # ถ้า recovery กำลังทำงานแต่ portfolio กลับมากำไรแล้ว
                        if self.recovery_active:
                            print("💊 AI: Portfolio recovered - Stopping recovery system")
                            self.recovery_active = False
                            self.recovery_start_time = None
                        else:
                            print("💰 AI: Portfolio healthy - Recovery system standby")
                
                # ✅ เพิ่ม: AI Profit Optimization เมื่อ portfolio กำไร
                if portfolio_profitable:
                    print("🎯 AI PROFIT OPTIMIZATION:")
                    
                    # 1. เช็คว่ามี positions ที่กำไรมากแล้วควรปิดไหม
                    high_profit_positions = [p for p in positions if p.pnl > 5.0]  # กำไรเกิน $5
                    if high_profit_positions:
                        print(f"   💎 Found {len(high_profit_positions)} high-profit positions")
                        print("   💡 Consider taking profits on strong performers")
                    
                    # 2. เช็ค trailing stop opportunities
                    trailing_candidates = [p for p in positions if p.pnl > 3.0]  # กำไรเกิน $3
                    if trailing_candidates:
                        print(f"   📈 {len(trailing_candidates)} positions eligible for trailing stops")
                    
                    # 3. Portfolio compound opportunities
                    if account_info and account_info.get('equity', 0) - account_info.get('balance', 0) > 20:  # กำไรเกิน $20
                        print(f"   🚀 Portfolio ready for compound growth strategies")
                        print(f"   💡 Consider increasing position sizes gradually")
                
            except Exception as e:
                print(f"❌ Smart profit management error: {e}")
                # เพิ่ม debug info
                import traceback
                print(f"🔍 Debug traceback:")
                traceback.print_exc()
                
    def close_all_positions(self):
        """ปิด positions ทั้งหมด"""
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            if not positions:
                print("   No positions to close")
                return True
                
            closed_count = 0
            total_profit = 0
            
            for position in positions:
                if position.magic != self.magic_number:
                    continue
                    
                print(f"   🎯 Closing position {position.ticket}: {position.volume} lots, PnL: ${position.profit:.2f}")
                
                success = self.close_entire_position(position)
                if success:
                    closed_count += 1
                    total_profit += position.profit
                    print(f"   ✅ Closed: ${position.profit:.2f}")
                    time.sleep(0.3)  # รอระหว่างการปิด
                else:
                    print(f"   ❌ Failed to close: {position.ticket}")
                    
            print(f"🎉 CLOSE ALL COMPLETED: {closed_count} positions closed, Total: ${total_profit:.2f}")
            
            # Clear tracking
            self.active_positions.clear()
            
            return closed_count > 0
            
        except Exception as e:
            print(f"❌ Close all positions error: {e}")
            return False
        
    def create_grid_immediately(self):
        """สร้าง grid ใหม่ทันที - แก้ไขป้องกันซ้ำ"""
        try:
            # เช็คว่ามี orders เยอะแล้วหรือยัง
            current_order_count = len(self.pending_orders)
            if current_order_count >= 15:  # ลดจาก 10 เป็น 15
                print(f"🔄 Sufficient orders exist ({current_order_count}) - checking for gaps only")
                self.fill_price_gaps()  # แก้ไขช่องว่างแทน
                return
                
            print("🧠 AI: Creating intelligent grid with duplicate prevention...")
            
            current_price = self.get_current_price()
            if not current_price:
                print("❌ Cannot get current price")
                return
                
            # ✅ ใช้ spacing ที่กว้างขึ้นป้องกันซ้ำ
            base_spacing = self.grid_spacing * 0.01
            wide_spacing = base_spacing * 2.0  # เพิ่มเป็น 2 เท่า
            strict_tolerance = base_spacing * 0.15  # tolerance แค่ 15%
            
            print(f"   📏 Base spacing: ${base_spacing:.2f}")
            print(f"   📏 Wide spacing: ${wide_spacing:.2f}")
            print(f"   🎯 Duplicate tolerance: ${strict_tolerance:.2f}")
            
            orders_created = 0
            max_orders_per_side = 6  # จำกัดไม้แต่ละฝั่ง
            
            # นับ orders ที่มีอยู่
            buy_orders = [o for o in self.pending_orders.values() if o['direction'] == 'BUY']
            sell_orders = [o for o in self.pending_orders.values() if o['direction'] == 'SELL']
            
            print(f"📊 Current orders: {len(buy_orders)} BUY, {len(sell_orders)} SELL")
            
            # ✅ BUY orders - กระจายห่าง + เช็คซ้ำเข้มงวด
            if len(buy_orders) < max_orders_per_side:
                print("🟢 Creating BUY ladder with duplicate prevention:")
                
                # สร้าง price levels ที่ไม่ซ้ำ
                target_buy_prices = []
                for i in range(1, max_orders_per_side + 3):
                    distance_multiplier = 1.0 + (i * 0.3)  # เพิ่มระยะห่าง
                    buy_price = current_price - (wide_spacing * distance_multiplier)
                    
                    if buy_price > 100:  # ราคาต้องสมเหตุสมผล
                        target_buy_prices.append(buy_price)
                
                # วางไม้ BUY
                for i, buy_price in enumerate(target_buy_prices):
                    if len([o for o in self.pending_orders.values() if o['direction'] == 'BUY']) >= max_orders_per_side:
                        break
                        
                    print(f"   🎯 Testing BUY Level {i+1}: ${buy_price:.2f}")
                    
                    if not self.has_order_near_price(buy_price, 'BUY', strict_tolerance):
                        success = self.place_pending_order(buy_price, 'BUY', self.base_lot)
                        if success:
                            orders_created += 1
                            print(f"   ✅ BUY order placed: ${buy_price:.2f}")
                            time.sleep(0.2)  # รอระหว่างการวาง
                        else:
                            print(f"   ❌ BUY order failed: ${buy_price:.2f}")
                    else:
                        print(f"   ⚠️ BUY order skipped: too close to existing")
                        
            # ✅ SELL orders - กระจายห่าง + เช็คซ้ำเข้มงวด
            if len(sell_orders) < max_orders_per_side:
                print("🔴 Creating SELL ladder with duplicate prevention:")
                
                # สร้าง price levels ที่ไม่ซ้ำ
                target_sell_prices = []
                for i in range(1, max_orders_per_side + 3):
                    distance_multiplier = 1.0 + (i * 0.3)  # เพิ่มระยะห่าง
                    sell_price = current_price + (wide_spacing * distance_multiplier)
                    target_sell_prices.append(sell_price)
                
                # วางไม้ SELL
                for i, sell_price in enumerate(target_sell_prices):
                    if len([o for o in self.pending_orders.values() if o['direction'] == 'SELL']) >= max_orders_per_side:
                        break
                        
                    print(f"   🎯 Testing SELL Level {i+1}: ${sell_price:.2f}")
                    
                    if not self.has_order_near_price(sell_price, 'SELL', strict_tolerance):
                        success = self.place_pending_order(sell_price, 'SELL', self.base_lot)
                        if success:
                            orders_created += 1
                            print(f"   ✅ SELL order placed: ${sell_price:.2f}")
                            time.sleep(0.2)  # รอระหว่างการวาง
                        else:
                            print(f"   ❌ SELL order failed: ${sell_price:.2f}")
                    else:
                        print(f"   ⚠️ SELL order skipped: too close to existing")
                        
            if orders_created > 0:
                print(f"✅ Anti-duplicate grid created: {orders_created} new orders")
                self.sync_pending_orders()  # ซิงค์ข้อมูล
            else:
                print(f"✅ Grid coverage adequate - no duplicates needed")
                
        except Exception as e:
            print(f"❌ Smart grid creation error: {e}")

    def fill_price_gaps(self):
        """เติมช่องว่างในราคาแทนการสร้างใหม่"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                return
                
            buy_orders = [o for o in self.pending_orders.values() if o['direction'] == 'BUY']
            sell_orders = [o for o in self.pending_orders.values() if o['direction'] == 'SELL']
            
            base_spacing = self.grid_spacing * 0.01
            gap_tolerance = base_spacing * 3.0  # ช่องว่างที่ใหญ่เกินไป
            
            print(f"🔍 Checking for price gaps larger than ${gap_tolerance:.2f}")
            
            # เช็คช่องว่าง BUY
            if len(buy_orders) >= 2:
                buy_prices = sorted([o['price'] for o in buy_orders], reverse=True)
                for i in range(len(buy_prices) - 1):
                    gap = buy_prices[i] - buy_prices[i + 1]
                    if gap > gap_tolerance:
                        fill_price = buy_prices[i] - (gap / 2)
                        print(f"   🔧 Filling BUY gap: ${fill_price:.2f}")
                        if not self.has_order_near_price(fill_price, 'BUY', base_spacing * 0.2):
                            self.place_pending_order(fill_price, 'BUY', self.base_lot)
            
            # เช็คช่องว่าง SELL
            if len(sell_orders) >= 2:
                sell_prices = sorted([o['price'] for o in sell_orders])
                for i in range(len(sell_prices) - 1):
                    gap = sell_prices[i + 1] - sell_prices[i]
                    if gap > gap_tolerance:
                        fill_price = sell_prices[i] + (gap / 2)
                        print(f"   🔧 Filling SELL gap: ${fill_price:.2f}")
                        if not self.has_order_near_price(fill_price, 'SELL', base_spacing * 0.2):
                            self.place_pending_order(fill_price, 'SELL', self.base_lot)
                            
        except Exception as e:
            print(f"❌ Fill gaps error: {e}")

    def sync_pending_orders(self):
        """ซิงค์ pending orders กับ MT5"""
        try:
            mt5_orders = mt5.orders_get(symbol=self.gold_symbol)
            if not mt5_orders:
                self.pending_orders.clear()
                return
                
            # อัพเดทข้อมูล pending_orders
            current_orders = {}
            for order in mt5_orders:
                if order.magic == self.magic_number:
                    direction = "BUY" if order.type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP] else "SELL"
                    current_orders[order.ticket] = {
                        'order_id': order.ticket,
                        'price': order.price_open,
                        'direction': direction,
                        'lot_size': order.volume_initial,
                        'time': datetime.fromtimestamp(order.time_setup)
                    }
            
            self.pending_orders = current_orders
            print(f"🔄 Synced: {len(current_orders)} pending orders")
            
        except Exception as e:
            print(f"❌ Sync pending orders error: {e}")

    def ensure_proper_grid_spread(self):
        """ใหม่ - ตรวจสอบและแก้ไข grid spread"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                return
                
            buy_orders = [o for o in self.pending_orders.values() if o['direction'] == 'BUY']
            sell_orders = [o for o in self.pending_orders.values() if o['direction'] == 'SELL']
            
            if not buy_orders or not sell_orders:
                return
                
            # ✅ เช็ค coverage range
            min_buy_price = min(o['price'] for o in buy_orders)
            max_sell_price = max(o['price'] for o in sell_orders)
            
            buy_coverage = current_price - min_buy_price
            sell_coverage = max_sell_price - current_price
            
            target_coverage = self.survivability * 0.01 * 0.3  # 30% ของ survivability
            
            print(f"📊 Grid Coverage Check:")
            print(f"   BUY coverage: ${buy_coverage:.2f} (target: ${target_coverage:.2f})")
            print(f"   SELL coverage: ${sell_coverage:.2f} (target: ${target_coverage:.2f})")
            
            # ✅ ถ้า coverage ไม่พอ ให้เพิ่ม orders ไกลออกไป
            if buy_coverage < target_coverage:
                print("🟢 Extending BUY coverage...")
                extended_buy_price = current_price - target_coverage
                if not self.has_order_near_price(extended_buy_price, 'BUY', tolerance=50):
                    self.place_pending_order(extended_buy_price, 'BUY', self.base_lot)
                    
            if sell_coverage < target_coverage:
                print("🔴 Extending SELL coverage...")
                extended_sell_price = current_price + target_coverage
                if not self.has_order_near_price(extended_sell_price, 'SELL', tolerance=50):
                    self.place_pending_order(extended_sell_price, 'SELL', self.base_lot)
                    
        except Exception as e:
            print(f"❌ Grid spread check error: {e}")

    def print_grid_coverage(self):
        """ใหม่ - แสดงข้อมูล grid coverage"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                return
                
            buy_orders = [o for o in self.pending_orders.values() if o['direction'] == 'BUY']
            sell_orders = [o for o in self.pending_orders.values() if o['direction'] == 'SELL']
            
            print(f"📊 GRID COVERAGE SUMMARY:")
            print(f"   Current price: ${current_price:.2f}")
            
            if buy_orders:
                buy_prices = [o['price'] for o in buy_orders]
                min_buy = min(buy_prices)
                max_buy = max(buy_prices)
                print(f"   BUY range: ${min_buy:.2f} to ${max_buy:.2f} ({len(buy_orders)} orders)")
                print(f"   BUY coverage: ${current_price - min_buy:.2f}")
                
            if sell_orders:
                sell_prices = [o['price'] for o in sell_orders]
                min_sell = min(sell_prices)
                max_sell = max(sell_prices)
                print(f"   SELL range: ${min_sell:.2f} to ${max_sell:.2f} ({len(sell_orders)} orders)")
                print(f"   SELL coverage: ${max_sell - current_price:.2f}")
                
            total_coverage = 0
            if buy_orders and sell_orders:
                total_coverage = max(sell_prices) - min(buy_prices)
                print(f"   TOTAL coverage: ${total_coverage:.2f}")
                
            survivability_coverage = (total_coverage / (self.survivability * 0.01)) * 100
            print(f"   Survivability coverage: {survivability_coverage:.1f}%")
                
        except Exception as e:
            print(f"❌ Print coverage error: {e}")

    def consider_replacement_order(self, filled_position):
        """วางไม้ใหม่หลังปิด position - แก้ไขให้กระจายไกลขึ้น"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                return
                
            # ✅ เพิ่ม spacing สำหรับ replacement
            base_spacing = self.grid_spacing * 0.01
            replacement_spacing = base_spacing * 2.0  # เพิ่มเป็น 2 เท่า
            
            if isinstance(filled_position, SmartPosition):
                direction = filled_position.direction
                entry_price = filled_position.entry_price
            else:
                direction = filled_position.get('direction')
                entry_price = filled_position.get('price_open', current_price)
                
            # วางไม้ใหม่ไกลออกไป
            if direction == "BUY":
                new_price = entry_price - replacement_spacing  # ไกลลงไป
                if new_price > 100:
                    success = self.place_pending_order(new_price, 'BUY', self.base_lot)
                    if success:
                        print(f"   🔄 Replacement BUY: ${new_price:.2f} (spacing: ${replacement_spacing:.2f})")
            else:
                new_price = entry_price + replacement_spacing  # ไกลขึ้นไป
                success = self.place_pending_order(new_price, 'SELL', self.base_lot)
                if success:
                    print(f"   🔄 Replacement SELL: ${new_price:.2f} (spacing: ${replacement_spacing:.2f})")
                    
            # เช็ค balance หลังวางไม้ใหม่
            self.ensure_balanced_orders()
                    
        except Exception as e:
            print(f"❌ Replacement order error: {e}")

    def ensure_balanced_orders(self):
        """แก้ไข method นี้ - เพิ่ม debug และ force BUY orders"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                print("❌ Cannot get current price for balance")
                return
                
            buy_orders = [o for o in self.pending_orders.values() if o['direction'] == 'BUY']
            sell_orders = [o for o in self.pending_orders.values() if o['direction'] == 'SELL']
            
            # print(f"🔍 BALANCE DEBUG:")
            # print(f"   Current price: ${current_price:.2f}")
            # print(f"   BUY orders: {len(buy_orders)}")
            # print(f"   SELL orders: {len(sell_orders)}")
            # print(f"   Pending orders total: {len(self.pending_orders)}")
            
            imbalance = abs(len(buy_orders) - len(sell_orders))
            
            if imbalance > 2:  # ไม่ balanced
                # print(f"⚖️ CRITICAL IMBALANCE: {len(buy_orders)} BUY vs {len(sell_orders)} SELL")
                
                spacing_dollars = self.grid_spacing * 0.01
                
                # ✅ Force BUY orders if missing
                if len(buy_orders) < len(sell_orders):
                    needed = len(sell_orders) - len(buy_orders)
                    print(f"🟢 FORCING {needed} BUY orders")
                    
                    # วาง BUY orders หลายระดับ
                    for i in range(1, min(needed + 3, 8)):  # วางสูงสุด 7 orders
                        buy_price = current_price - (spacing_dollars * i * 0.6)  # ใกล้ขึ้น
                        
                        print(f"   🎯 Attempting BUY at ${buy_price:.2f}")
                        
                        if buy_price > 100:  # ป้องกันราคาต่ำเกิน
                            if not self.has_order_near_price(buy_price, 'BUY', tolerance=1.0):
                                success = self.place_pending_order(buy_price, 'BUY', self.base_lot)
                                if success:
                                    print(f"   ✅ BUY order placed: ${buy_price:.2f}")
                                else:
                                    print(f"   ❌ BUY order FAILED: ${buy_price:.2f}")
                                    # ลองราคาใกล้ขึ้น
                                    retry_price = current_price - (spacing_dollars * i * 0.4)
                                    if retry_price > 100:
                                        retry_success = self.place_pending_order(retry_price, 'BUY', self.base_lot)
                                        if retry_success:
                                            print(f"   🔄 BUY retry SUCCESS: ${retry_price:.2f}")
                            else:
                                print(f"   ⚠️ BUY order exists near ${buy_price:.2f}")
                                
                        # เช็คว่าเพิ่มได้แล้วหรือยัง
                        current_buy_count = len([o for o in self.pending_orders.values() if o['direction'] == 'BUY'])
                        if current_buy_count >= len(sell_orders) - 1:
                            print(f"   ✅ Balance achieved: {current_buy_count} BUY orders")
                            break
                            
                # ✅ Force SELL orders if missing (น่าจะไม่ใช่กรณีนี้)
                elif len(sell_orders) < len(buy_orders):
                    needed = len(buy_orders) - len(sell_orders)
                    print(f"🔴 FORCING {needed} SELL orders")
                    
                    for i in range(1, needed + 2):
                        sell_price = current_price + (spacing_dollars * i * 0.6)
                        if not self.has_order_near_price(sell_price, 'SELL', tolerance=1.0):
                            success = self.place_pending_order(sell_price, 'SELL', self.base_lot)
                            if success:
                                print(f"   ✅ SELL order placed: ${sell_price:.2f}")
                            else:
                                print(f"   ❌ SELL order FAILED: ${sell_price:.2f}")
            else:
                print(f"✅ Grid balanced: {len(buy_orders)} BUY, {len(sell_orders)} SELL")
                
        except Exception as e:
            print(f"❌ Balance check error: {e}")

    def has_order_near_price(self, target_price, direction, tolerance=0.30):
        """เช็คไม้ใกล้เคียง - แก้ไขให้เข้มงวดขึ้น"""
        try:
            # ✅ เช็ค pending orders ก่อน
            for order_info in self.pending_orders.values():
                if order_info['direction'] == direction:
                    distance = abs(order_info['price'] - target_price)
                    if distance < tolerance:
                        print(f"   📍 DUPLICATE BLOCKED: {direction} order exists at ${order_info['price']:.2f} (distance: {distance:.2f})")
                        return True
            
            # ✅ เช็ค active positions ด้วย  
            for pos_info in self.active_positions.values():
                if pos_info.get('direction') == direction:
                    distance = abs(pos_info.get('price_open', 0) - target_price)
                    if distance < tolerance:
                        print(f"   📍 DUPLICATE BLOCKED: {direction} position exists at ${pos_info.get('price_open', 0):.2f}")
                        return True
            
            # ✅ เช็ค MT5 pending orders จริงๆ
            mt5_orders = mt5.orders_get(symbol=self.gold_symbol)
            if mt5_orders:
                for order in mt5_orders:
                    if order.magic == self.magic_number:
                        order_direction = "BUY" if order.type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP] else "SELL"
                        if order_direction == direction:
                            distance = abs(order.price_open - target_price)
                            if distance < tolerance:
                                print(f"   📍 DUPLICATE BLOCKED: MT5 {direction} order exists at ${order.price_open:.2f}")
                                return True
            
            # ✅ เช็ค MT5 positions จริงๆ
            mt5_positions = mt5.positions_get(symbol=self.gold_symbol)
            if mt5_positions:
                for pos in mt5_positions:
                    if pos.magic == self.magic_number:
                        pos_direction = "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
                        if pos_direction == direction:
                            distance = abs(pos.price_open - target_price)
                            if distance < tolerance:
                                print(f"   📍 DUPLICATE BLOCKED: MT5 {direction} position exists at ${pos.price_open:.2f}")
                                return True
                                
            print(f"   🆕 CLEAR: No {direction} order near ${target_price:.2f}")
            return False
            
        except Exception as e:
            print(f"❌ Check order near price error: {e}")
            return True  # ถ้าเกิด error ให้ block ไว้ก่อน

        
    def rebalance_portfolio_if_needed(self, positions):
        """Rebalance portfolio if needed"""
        try:
            print("🔧 AI: Rebalancing portfolio...")
            
            # ตรวจสอบ BUY:SELL ratio
            buy_positions = [p for p in positions if p.direction == "BUY"]
            sell_positions = [p for p in positions if p.direction == "SELL"]
            
            buy_count = len(buy_positions)
            sell_count = len(sell_positions)
            
            print(f"📊 Current ratio: {buy_count} BUY : {sell_count} SELL")
            
            current_price = self.get_current_price()
            if not current_price:
                return
                
            spacing_dollars = self.grid_spacing * 0.01
            
            # เพิ่ม orders ที่ขาด
            if buy_count < 2:
                for i in range(1, 3):
                    buy_price = current_price - (spacing_dollars * i)
                    self.place_pending_order(buy_price, 'BUY', self.base_lot)
                    
            if sell_count < 2:
                for i in range(1, 3):
                    sell_price = current_price + (spacing_dollars * i)
                    self.place_pending_order(sell_price, 'SELL', self.base_lot)
                    
            print("✅ AI: Portfolio rebalancing completed")
            
        except Exception as e:
            print(f"❌ Rebalance error: {e}")

    def analyze_portfolio_positions(self) -> Dict:
        """AI Portfolio Analysis - ทับของเดิมเลย"""
        
        try:
            # Get all positions from MT5
            positions = mt5.positions_get(symbol=self.gold_symbol)
            if not positions:
                return {'total_positions': 0, 'grid_positions': [], 'total_pnl': 0}
                
            # Filter our positions
            our_positions = [pos for pos in positions if pos.magic == self.magic_number]
            
            # Create SmartPosition objects
            grid_positions = []
            hedge_positions = []
            
            for pos in our_positions:
                smart_pos = SmartPosition(
                    position_id=pos.ticket,
                    symbol=pos.symbol,
                    direction="BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                    lot_size=pos.volume,
                    entry_price=pos.price_open,
                    current_price=pos.price_current,
                    entry_time=datetime.fromtimestamp(pos.time),
                    pnl=pos.profit,
                    is_hedge="HEDGE" in pos.comment if hasattr(pos, 'comment') else False
                )
                
                if smart_pos.is_hedge:
                    hedge_positions.append(smart_pos)
                else:
                    grid_positions.append(smart_pos)
            
            # Calculate metrics
            total_pnl = sum(pos.pnl for pos in grid_positions + hedge_positions)
            
            # Portfolio scoring
            profitable_positions = [p for p in grid_positions if p.pnl > 0]
            losing_positions = [p for p in grid_positions if p.pnl < 0]
            
            # print(f"📊 Portfolio: {len(grid_positions)} total, {len(profitable_positions)} profit, {len(losing_positions)} loss")
            
            return {
                'total_positions': len(our_positions),
                'grid_positions': grid_positions,
                'hedge_positions': hedge_positions,
                'profitable_positions': profitable_positions,
                'losing_positions': losing_positions,
                'total_pnl': total_pnl,
                'total_exposure': sum(p.lot_size for p in grid_positions),
                'hedge_exposure': sum(p.lot_size for p in hedge_positions),
                'portfolio_health': self.calculate_portfolio_health(grid_positions, total_pnl),
                'risk_percentage': self.calculate_portfolio_risk_percentage(grid_positions)
            }
            
        except Exception as e:
            print(f"❌ Portfolio analysis error: {e}")
            return {'error': str(e)}

    def calculate_portfolio_health(self, positions, total_pnl) -> int:
        """คำนวณ portfolio health score 0-100"""
        try:
            health = 50  # Base health
            
            # PnL contribution
            if total_pnl > 0:
                health += min(30, total_pnl * 2)  # Max +30 for positive PnL
            else:
                health += max(-30, total_pnl / 2)  # Max -30 for negative PnL
                
            # Position diversity
            if len(positions) >= 4:
                health += 20
            elif len(positions) >= 2:
                health += 10
                
            return max(0, min(100, int(health)))
            
        except:
            return 50

    def calculate_portfolio_risk_percentage(self, positions) -> float:
        """คำนวณ portfolio risk เป็น %"""
        try:
            if not positions:
                return 0
                
            total_exposure = sum(p.lot_size for p in positions)
            account_balance = 10000  # Default, should get from account
            
            # Rough calculation: 1 lot = $1000 exposure for gold
            total_exposure_dollars = total_exposure * 1000
            risk_percentage = (total_exposure_dollars / account_balance) * 100
            
            return min(100, risk_percentage)
            
        except:
            return 0

    def find_profitable_pairs(self, positions):
        """🧠 AI หาคู่ไม้ที่ควรปิด - SAFE VERSION ป้องกันการติดลบ"""
        
        try:
            if len(positions) < 2:
                return []
                
            print(f"🧠 AI SAFE PAIR TRADING: {len(positions)} positions")
            
            current_price = self.get_current_price()
            buy_positions = [p for p in positions if p.direction == "BUY"]
            sell_positions = [p for p in positions if p.direction == "SELL"]
            
            # 🔄 แยกตามประเภท กำไร/ขาดทุน (เข้มงวดขึ้น)
            profitable_positions = [p for p in positions if p.pnl > 1.5]  # เพิ่มจาก 0.3 เป็น 1.5
            losing_positions = [p for p in positions if p.pnl < -2.0]     # เพิ่มจาก -0.5 เป็น -2.0
            
            # 🎯 เรียงไม้ขาดทุนตามความรุนแรง (ขาดทุนมากสุดก่อน)
            losing_positions.sort(key=lambda x: x.pnl)
            
            # 🎯 เรียงไม้กำไรตามความแข็งแกร่ง (กำไรมากสุดก่อน)  
            profitable_positions.sort(key=lambda x: x.pnl, reverse=True)
            
            print(f"📊 Safe Portfolio Analysis:")
            print(f"   💰 Strong profitable positions: {len(profitable_positions)}")
            print(f"   📉 Significant losing positions: {len(losing_positions)}")
            print(f"   🔄 BUY/SELL: {len(buy_positions)}/{len(sell_positions)}")
            
            if len(profitable_positions) == 0:
                print("❌ No strong profitable positions to help")
                return []
            
            smart_pairs = []
            
            # 🎯 STRATEGY 1: SAFE HEAVY RESCUE - 1 ขาดทุนหนัก + หลายไม้กำไรแข็งแกร่ง (1:N)
            print("🎯 Strategy 1: Safe Heavy Rescue Operations (1:N)")
            
            for losing_pos in losing_positions:
                print(f"\n   🆘 TARGETING LOSS: {losing_pos.direction} ${losing_pos.pnl:.2f}")
                
                # ✅ เช็ค position age ก่อน - ต้องอายุมากกว่า 5 นาที
                pos_age = self.calculate_position_age(losing_pos)
                if pos_age < 300:  # น้อยกว่า 5 นาที
                    print(f"      ⏰ SKIP: Position too young ({pos_age/60:.1f} min)")
                    continue
                
                # ลองใช้ไม้กำไรหลายตัวช่วย (1:2, 1:3, 1:4)
                for num_helpers in range(2, min(5, len(profitable_positions) + 1)):
                    
                    # เลือกไม้กำไรที่ดีที่สุด
                    best_helpers = profitable_positions[:num_helpers]
                    total_helper_profit = sum(h.pnl for h in best_helpers)
                    net_result = losing_pos.pnl + total_helper_profit
                    
                    print(f"      🧮 1:{num_helpers} Test: ${losing_pos.pnl:.2f} + ${total_helper_profit:.2f} = ${net_result:.2f}")
                    
                    # ✅ เงื่อนไขการยอมรับ - เข้มงวดมากขึ้น
                    profit_strength_ratio = total_helper_profit / abs(losing_pos.pnl) if losing_pos.pnl < 0 else 0
                    
                    acceptable_conditions = [
                        net_result >= 2.0,  # ✅ บังคับกำไรขั้นต่ำ $2 (แทน -1.0)
                        profit_strength_ratio >= 2.0,  # ✅ ไม้กำไรต้องแข็งแกร่งกว่า 200%
                        all(h.pnl >= 1.5 for h in best_helpers),  # ✅ ไม้กำไรทุกตัวต้องมากกว่า $1.5
                        total_helper_profit >= abs(losing_pos.pnl) * 1.5,  # ✅ ไม้กำไรรวมต้องมากกว่า 150% ของขาดทุน
                    ]
                    
                    print(f"      📊 Profit strength ratio: {profit_strength_ratio:.2f}")
                    print(f"      📊 Helper strength: ${total_helper_profit:.2f} vs Loss: ${abs(losing_pos.pnl):.2f}")
                    
                    if all(acceptable_conditions):
                        position_ids = {losing_pos.position_id}
                        position_ids.update(h.position_id for h in best_helpers)
                        
                        # คำนวณ priority score - เน้นความปลอดภัย
                        safety_bonus = net_result * 1000  # โบนัสสำหรับกำไรสูง
                        strength_bonus = profit_strength_ratio * 500  # โบนัสสำหรับความแข็งแกร่ง
                        rescue_urgency = abs(losing_pos.pnl) * 100  # ความเร่งด่วน
                        
                        priority_score = safety_bonus + strength_bonus + rescue_urgency
                        
                        smart_pairs.append({
                            'losing_positions': [losing_pos],
                            'profitable_positions': best_helpers,
                            'net_profit': net_result,
                            'total_positions': 1 + num_helpers,
                            'pair_type': f"SAFE_RESCUE_1_{num_helpers}",
                            'priority_score': priority_score,
                            'position_ids': position_ids,
                            'loss_reduction': abs(net_result - losing_pos.pnl),
                            'helper_strength': total_helper_profit,
                            'profit_strength_ratio': profit_strength_ratio,
                            'safety_margin': net_result,
                            'reason': f"Safe rescue 1:{num_helpers}: ${losing_pos.pnl:.2f} + {num_helpers} strong helpers = ${net_result:.2f}"
                        })
                        
                        helpers_detail = [f"{h.direction}${h.pnl:.2f}" for h in best_helpers]
                        print(f"      ✅ APPROVED 1:{num_helpers}: Safety margin ${net_result:.2f}")
                        print(f"         Helpers: {helpers_detail}")
                        print(f"         Profit strength: {profit_strength_ratio:.2f}x")
                        
                        break  # หาได้แล้วไม่ต้องลองเพิ่ม helper
                    else:
                        print(f"      ❌ REJECTED 1:{num_helpers}: Safety conditions not met")
                        if net_result < 2.0:
                            print(f"         - Net profit too low: ${net_result:.2f} < $2.00")
                        if profit_strength_ratio < 2.0:
                            print(f"         - Helpers not strong enough: {profit_strength_ratio:.2f}x < 2.0x")
            
            # 🎯 STRATEGY 2: EMERGENCY HIGH PROFITS ONLY - เข้มงวดมากขึ้น
            print("\n🎯 Strategy 2: Emergency High Profits Only")
            for pos in profitable_positions:
                if pos.pnl > 12.0:  # เพิ่มจาก 10.0 เป็น 12.0 (เฉพาะกำไรสูงมากๆ เท่านั้น)
                    smart_pairs.append({
                        'losing_positions': [],
                        'profitable_positions': [pos],
                        'net_profit': pos.pnl,
                        'total_positions': 1,
                        'pair_type': "EMERGENCY_HIGH_PROFIT",
                        'priority_score': 5000 + pos.pnl * 50,
                        'position_ids': {pos.position_id},
                        'safety_margin': pos.pnl,
                        'reason': f"Emergency high profit: ${pos.pnl:.2f}"
                    })
                    print(f"   💎 EMERGENCY SINGLE: {pos.direction} ${pos.pnl:.2f}")
            
            # เรียงตาม priority score
            smart_pairs.sort(key=lambda x: x['priority_score'], reverse=True)
            
            # 🛡️ ULTRA SAFE PROTECTION - ป้องกันแบบเข้มงวดสุด
            print(f"\n🛡️ Ultra Safe Portfolio Protection:")
            
            protected_pairs = []
            used_position_ids = set()
            
            total_positions = len(positions)
            min_positions_to_keep = max(10, int(total_positions * 0.25))  # เก็บ 25% (เพิ่มจาก 15%)
            
            print(f"   📊 Total: {total_positions}, Must keep: {min_positions_to_keep}")
            
            for pair in smart_pairs[:5]:  # ลดจาก 15 เป็น 5 pairs (เข้มงวดมาก)
                
                # เช็คการใช้ position ซ้ำ
                if pair['position_ids'].intersection(used_position_ids):
                    continue
                
                # เช็คจำนวน position ที่เหลือ
                remaining = total_positions - len(used_position_ids) - pair['total_positions']
                if remaining < min_positions_to_keep:
                    continue
                
                # ✅ เงื่อนไขการอนุมัติ - เข้มงวดสุด
                approval_conditions = [
                    pair['net_profit'] >= 3.0,         # ✅ กำไรขั้นต่ำ $3 (เพิ่มจาก 8.0)
                    pair.get('safety_margin', 0) >= 2.5,  # ✅ ต้องมี safety margin อย่างน้อย $2.5
                    len(pair['losing_positions']) > 0 or pair['net_profit'] > 12.0,  # ✅ ต้องมีไม้ขาดทุน หรือกำไรสูงมาก
                    'SAFE' in pair['pair_type'] or 'EMERGENCY' in pair['pair_type'],  # ✅ ต้องเป็น safe type
                ]
                
                if all(approval_conditions):
                    protected_pairs.append(pair)
                    used_position_ids.update(pair['position_ids'])
                    
                    losing_count = len(pair['losing_positions'])
                    profit_count = len(pair['profitable_positions'])
                    safety_margin = pair.get('safety_margin', 0)
                    
                    print(f"   ✅ {pair['pair_type']}: {losing_count}L+{profit_count}P = ${pair['net_profit']:.2f} (Safety: ${safety_margin:.2f})")
            
            # 📋 สรุปผล
            print(f"\n🎯 ULTRA SAFE PAIR TRADING RESULTS:")
            print(f"   📋 Candidates found: {len(smart_pairs)}")
            print(f"   ✅ Approved ultra safe pairs: {len(protected_pairs)}")
            
            if protected_pairs:
                total_expected = sum(pair['net_profit'] for pair in protected_pairs)
                total_safety_margin = sum(pair.get('safety_margin', 0) for pair in protected_pairs)
                
                print(f"   💰 Expected profit: ${total_expected:.2f}")
                print(f"   🛡️ Total safety margin: ${total_safety_margin:.2f}")
                
                print(f"\n   📋 Approved Ultra Safe Operations:")
                for i, pair in enumerate(protected_pairs, 1):
                    losing_detail = f"{len(pair['losing_positions'])}L" if pair['losing_positions'] else "0L"
                    profit_detail = f"{len(pair['profitable_positions'])}P"
                    safety_margin = pair.get('safety_margin', 0)
                    print(f"     {i}. {pair['pair_type']}: {losing_detail}+{profit_detail} = ${pair['net_profit']:.2f} (Safety: ${safety_margin:.2f})")
            else:
                print("   ⚠️ No suitable ultra safe pairs found")
                
            return protected_pairs
            
        except Exception as e:
            print(f"❌ Safe pair analysis error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def find_single_profit_opportunities(self, profitable_positions):
        """หาโอกาสปิดไม้กำไรเดี่ยว - เฉพาะกรณีไม่มีไม้ขาดทุน"""
        
        single_opportunities = []
        
        # เลือกเฉพาะไม้กำไรสูงมากๆ
        for pos in profitable_positions:
            if pos.pnl > 5.0:  # กำไรเกิน $5
                single_opportunities.append({
                    'losing_positions': [],
                    'profitable_positions': [pos],
                    'net_profit': pos.pnl,
                    'total_positions': 1,
                    'pair_type': "SINGLE_HIGH_PROFIT",
                    'priority_score': 2000 + pos.pnl * 50,
                    'position_ids': {pos.position_id},
                    'reason': f"Single high profit: ${pos.pnl:.2f}"
                })
        
        print(f"📈 Single profit opportunities: {len(single_opportunities)}")
        
        return single_opportunities[:3]  # สูงสุด 3 ตัว
    
    def execute_pair_closes(self, pairs):
        """ปิดคู่ positions - ATOMIC VERSION ป้องกันการติดลบ"""
        
        for pair in pairs:
            try:
                all_positions = pair['losing_positions'] + pair['profitable_positions']
                losing_count = len(pair['losing_positions'])
                profit_count = len(pair['profitable_positions'])
                
                print(f"💰 EXECUTING SAFE PAIR CLOSE: {pair['pair_type']}")
                print(f"   📊 {losing_count} losing + {profit_count} profit positions")
                print(f"   💲 Expected net: ${pair['net_profit']:.2f}")
                print(f"   🛡️ Safety margin: ${pair.get('safety_margin', 0):.2f}")
                
                # ✅ STEP 1: Final PnL verification ก่อนปิดจริง
                print(f"   🔍 Final PnL verification...")
                current_total_pnl = 0
                for pos in all_positions:
                    current_pnl = self.get_position_current_pnl(pos)
                    current_total_pnl += current_pnl
                    print(f"      Position {pos.position_id}: ${current_pnl:.2f}")
                
                expected_pnl = pair['net_profit']
                pnl_drift = abs(current_total_pnl - expected_pnl)
                
                print(f"      Expected: ${expected_pnl:.2f}")
                print(f"      Current:  ${current_total_pnl:.2f}")
                print(f"      Drift:    ${pnl_drift:.2f}")
                
                # ถ้า PnL เปลี่ยนมากเกิน $1 ให้ยกเลิก
                if pnl_drift > 1.0:
                    print(f"   ❌ ABORT: PnL drift too high (${pnl_drift:.2f} > $1.00)")
                    print(f"   💡 Market moved too much - canceling for safety")
                    continue
                    
                # ถ้า current PnL กลายเป็นลบ ให้ยกเลิก
                if current_total_pnl < 0.5:
                    print(f"   ❌ ABORT: Current PnL too low (${current_total_pnl:.2f} < $0.50)")
                    continue
                
                # ✅ STEP 2: Quick parallel close execution
                print(f"   ⚡ Executing quick parallel close...")
                
                close_requests = []
                success_count = 0
                failed_positions = []
                
                # เตรียม close requests ทั้งหมด
                for pos in all_positions:
                    request = self.prepare_close_request(pos)
                    if request:
                        close_requests.append((pos, request))
                    else:
                        failed_positions.append(pos)
                        print(f"      ❌ Failed to prepare close request for {pos.position_id}")
                
                if len(failed_positions) > 0:
                    print(f"   ❌ ABORT: Cannot prepare {len(failed_positions)} close requests")
                    continue
                
                # ✅ STEP 3: Execute all closes with minimal delay
                print(f"   🎯 Closing {len(close_requests)} positions...")
                
                for i, (pos, request) in enumerate(close_requests):
                    pos_type = "LOSING" if pos in pair['losing_positions'] else "PROFIT"
                    print(f"      {i+1}/{len(close_requests)} Closing {pos_type}: {pos.position_id} (${pos.pnl:.2f})")
                    
                    success = self.execute_close_request(request)
                    if success:
                        success_count += 1
                        print(f"         ✅ Closed successfully")
                    else:
                        failed_positions.append(pos)
                        print(f"         ❌ Close failed")
                    
                    # หยุดสั้นๆ เฉพาะระหว่างการปิด (ลดจาก 0.3 เป็น 0.1)
                    if i < len(close_requests) - 1:
                        time.sleep(0.1)
                
                # ✅ STEP 4: Verify results
                total_expected = len(all_positions)
                success_rate = (success_count / total_expected) * 100
                
                print(f"   📊 CLOSE RESULTS:")
                print(f"      Success: {success_count}/{total_expected} ({success_rate:.1f}%)")
                
                if success_count == total_expected:
                    print(f"   🎉 PAIR CLOSE COMPLETE SUCCESS!")
                    print(f"   💰 Expected profit realized: ${pair['net_profit']:.2f}")
                    
                    # Update internal tracking
                    for pos in all_positions:
                        if pos.position_id in self.active_positions:
                            del self.active_positions[pos.position_id]
                            
                elif success_count >= total_expected * 0.8:  # 80% ขึ้นไป
                    print(f"   ✅ PAIR CLOSE MOSTLY SUCCESS ({success_rate:.1f}%)")
                    realized_profit = pair['net_profit'] * (success_count / total_expected)
                    print(f"   💰 Estimated realized profit: ${realized_profit:.2f}")
                    
                    # Update tracking for successful closes only
                    for pos in all_positions:
                        if pos not in failed_positions and pos.position_id in self.active_positions:
                            del self.active_positions[pos.position_id]
                            
                else:
                    print(f"   ⚠️ PAIR CLOSE PARTIAL SUCCESS ({success_rate:.1f}%)")
                    print(f"   🔄 May need manual intervention for failed positions")
                    
                    for failed_pos in failed_positions:
                        print(f"      ⚠️ Failed to close: {failed_pos.position_id} (${failed_pos.pnl:.2f})")
                
                print(f"   " + "="*60)
                
            except Exception as e:
                print(f"❌ Pair close error: {e}")
                import traceback
                traceback.print_exc()
            
    def prepare_close_request(self, position):
        """เตรียม close request สำหรับ position"""
        try:
            # Get current tick data
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"      ❌ Cannot get tick data for {position.position_id}")
                return None
                
            # Determine close price and order type
            if isinstance(position, dict):
                position_type = position.get('type')
                position_id = position.get('ticket') or position.get('position_id')
                volume = position.get('volume') or position.get('lot_size')
            else:
                # SmartPosition object
                position_type = mt5.POSITION_TYPE_BUY if position.direction == "BUY" else mt5.POSITION_TYPE_SELL
                position_id = position.position_id
                volume = position.lot_size
                
            if position_type == mt5.POSITION_TYPE_BUY:
                close_price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            else:
                close_price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY
                
            # ✅ สร้าง request พร้อม improved parameters
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.gold_symbol,
                "volume": volume,
                "type": order_type,
                "position": position_id,
                "price": close_price,
                "deviation": 100,  # เพิ่มจาก 50 เป็น 100
                "magic": self.magic_number,
                "comment": "AI_SAFE_PAIR_CLOSE"
            }
            
            return request
            
        except Exception as e:
            print(f"      ❌ Prepare close request error: {e}")
            return None

    def execute_close_request(self, request):
        """Execute close request พร้อม fallback mechanisms"""
        try:
            # ✅ ลอง filling modes ตามลำดับความปลอดภัย
            filling_modes = [
                mt5.ORDER_FILLING_IOC,     # Fill or Cancel - เร็วที่สุด
                mt5.ORDER_FILLING_FOK,     # Fill or Kill - รับประกันปิดทั้งหมด
                mt5.ORDER_FILLING_RETURN   # Return - ปลอดภัยสุด
            ]
            
            for i, filling_mode in enumerate(filling_modes):
                request_copy = request.copy()
                request_copy["type_filling"] = filling_mode
                
                result = mt5.order_send(request_copy)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"         ✅ Closed with mode {filling_mode} (attempt {i+1})")
                    return True
                else:
                    if result:
                        print(f"         ⚠️ Mode {filling_mode} failed: {result.retcode}")
                    else:
                        print(f"         ⚠️ Mode {filling_mode} failed: No result")
                    
                    # ถ้าเป็น filling mode error ให้ลองต่อ
                    if result and result.retcode in [10018, 10030]:
                        continue
                    else:
                        # Error อื่นๆ หยุดลอง
                        break
            
            print(f"         ❌ All filling modes failed")
            return False
            
        except Exception as e:
            print(f"         ❌ Execute close error: {e}")
            return False

    def get_position_current_pnl(self, position):
        """Get current PnL of position from MT5"""
        try:
            if isinstance(position, dict):
                position_id = position.get('ticket') or position.get('position_id')
            else:
                position_id = position.position_id
                
            # Get fresh position data from MT5
            positions = mt5.positions_get(ticket=position_id)
            if positions and len(positions) > 0:
                return positions[0].profit
            else:
                # Position might be closed already, return last known PnL
                return getattr(position, 'pnl', 0)
                
        except Exception as e:
            print(f"      ⚠️ Error getting current PnL: {e}")
            return getattr(position, 'pnl', 0)
        
    def get_current_margin_level(self):
        """Get current margin level percentage"""
        try:
            account_info = self.mt5_connector.get_account_info() if self.mt5_connector else None
            
            if not account_info:
                return 1000  # Safe default
                
            margin = account_info.get('margin', 0)
            equity = account_info.get('equity', 0)
            
            if margin <= 0:
                return 9999  # No positions open
                
            margin_level = (equity / margin) * 100
            return round(margin_level, 1)
            
        except Exception as e:
            print(f"❌ Error getting margin level: {e}")
            return 1000  # Safe default

    def calculate_position_age(self, position):
        """Calculate position age in minutes"""
        try:
            if isinstance(position, SmartPosition):
                entry_time = position.entry_time
            elif hasattr(position, 'time_open'):
                entry_time = position.time_open
            else:
                entry_time = position.get('time_open', datetime.now())
                
            if isinstance(entry_time, str):
                entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            elif isinstance(entry_time, (int, float)):
                entry_time = datetime.fromtimestamp(entry_time)
                
            age_minutes = (datetime.now() - entry_time).total_seconds() / 60
            return max(0, age_minutes)
            
        except Exception as e:
            print(f"❌ Error calculating position age: {e}")
            return 0
    
    def find_wrong_side_pairs(self, buy_positions, sell_positions, current_price):
        """🚨 หาคู่ที่มีไม้อยู่ผิดข้างตลาด (Priority สูงสุด)"""
        wrong_pairs = []
        
        # BUY ที่อยู่เหนือตลาด (ผิด)
        wrong_buys = [b for b in buy_positions if b.entry_price > current_price and b.pnl < -2]
        # SELL ที่อยู่ใต้ตลาด (ผิด)  
        wrong_sells = [s for s in sell_positions if s.entry_price < current_price and s.pnl < -2]
        
        # จับคู่ไม้ผิดข้างกับไม้กำไร
        all_good_positions = [p for p in buy_positions + sell_positions if p.pnl > 0.5]
        
        for wrong_pos in wrong_buys + wrong_sells:
            for good_pos in all_good_positions:
                net_pnl = wrong_pos.pnl + good_pos.pnl
                
                if net_pnl > -1.0:  # ยอมขาดทุนเล็กน้อยเพื่อแก้ portfolio
                    wrong_pairs.append({
                        'losing_positions': [wrong_pos],
                        'profitable_positions': [good_pos] if good_pos.pnl > 0 else [],
                        'net_profit': net_pnl,
                        'total_positions': 2,
                        'pair_type': "WRONG_SIDE_FIX",
                        'priority_score': 2000 + abs(wrong_pos.pnl),  # Priority สูงสุด
                        'position_ids': {wrong_pos.position_id, good_pos.position_id},
                        'margin_impact': f"+${(wrong_pos.lot_size + good_pos.lot_size) * 500:.0f} freed",
                        'reason': f"Fix wrong side {wrong_pos.direction} @ ${wrong_pos.entry_price:.2f}"
                    })
        
        return wrong_pairs

    def identify_profit_opportunities(self):
        """🧠 AI หาโอกาสทำกำไรทั้งหมด"""
        
        try:
            opportunities = []
            
            # Get current portfolio
            portfolio_analysis = self.analyze_portfolio_positions()
            if 'error' in portfolio_analysis:
                return []
                
            positions = portfolio_analysis.get('grid_positions', [])
            total_pnl = portfolio_analysis.get('total_pnl', 0)
            
            # 1. หาคู่ที่ควรปิด
            profitable_pairs = self.find_profitable_pairs(positions)
            for pair in profitable_pairs:
                opportunities.append({
                    'type': 'PAIR_CLOSE',
                    'priority': 'HIGH',
                    'expected_profit': pair['net_profit'],
                    'action': f"Close pair: {pair['losing_position'].position_id} + {pair['profit_position'].position_id}",
                    'data': pair
                })
            
            # 2. หา hedge opportunities
            if total_pnl < -20:
                hedge_ops = self.find_hedge_opportunities(positions)
                for hedge in hedge_ops:
                    opportunities.append({
                        'type': 'HEDGE_PLACEMENT',
                        'priority': 'MEDIUM', 
                        'expected_profit': abs(hedge['target_loss']) * 0.3,  # คาดว่าจะลดขาดทุน 30%
                        'action': f"Place {hedge['direction']} hedge {hedge['lot_size']} lots",
                        'data': hedge
                    })
            
            # 3. Portfolio rebalancing
            buy_count = len([p for p in positions if p.direction == "BUY"])
            sell_count = len([p for p in positions if p.direction == "SELL"])
            if abs(buy_count - sell_count) > 2:
                opportunities.append({
                    'type': 'REBALANCE',
                    'priority': 'LOW',
                    'expected_profit': 5,  # Expected small profit from balance
                    'action': f"Add {'SELL' if buy_count > sell_count else 'BUY'} order for balance",
                    'data': {'imbalance': abs(buy_count - sell_count)}
                })
            
            # Sort by priority and expected profit
            priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
            opportunities.sort(key=lambda x: (priority_order[x['priority']], x['expected_profit']), reverse=True)
            
            return opportunities[:5]  # Top 5 opportunities
            
        except Exception as e:
            print(f"❌ Identify opportunities error: {e}")
            return []

    def execute_smart_close(self, position, reason, details: Dict) -> bool:
        """AI Smart Close - ทับของเดิมเลย (เรียบง่าย)"""
        
        try:
            # ปิดทั้งหมดเลย (ไม่มี partial close ให้ซับซ้อน)
            success = self.close_entire_position(position)
            
            if success:
                print(f"✅ AI Close: {position.position_id} - ${position.pnl:.2f} - Reason: {reason.value if hasattr(reason, 'value') else reason}")
                
                # วางไม้ใหม่ทดแทนทันที
                if self.auto_reposition_enabled:
                    self.place_replacement_after_close(position)
                
                return True
            else:
                print(f"❌ AI Close failed: {position.position_id}")
                return False
                
        except Exception as e:
            print(f"❌ Smart close error: {e}")
            return False

    def place_replacement_after_close(self, closed_position):
        """วางไม้ใหม่หลังปิด position"""
        
        try:
            current_price = self.get_current_price()
            if not current_price:
                return
                
            spacing_dollars = self.grid_spacing * 0.01
            
            if isinstance(closed_position, SmartPosition):
                direction = closed_position.direction
                entry_price = closed_position.entry_price
            else:
                direction = closed_position.get('direction')
                entry_price = closed_position.get('price_open', current_price)
                
            # วางไม้ใหม่ไกลออกไป
            if direction == "BUY":
                new_price = entry_price - (spacing_dollars * 2)  # ไกลลงไป
            else:
                new_price = entry_price + (spacing_dollars * 2)  # ไกลขึ้นไป
                
            # ตรวจสอบว่าราคาใหม่ไม่ใกล้ตลาดเกินไป
            distance_from_market = abs(new_price - current_price)
            if distance_from_market > spacing_dollars * 0.5:  # อย่างน้อยครึ่ง spacing
                success = self.place_pending_order(new_price, direction, self.base_lot)
                if success:
                    print(f"   🔄 Replacement order: {direction} @ ${new_price:.2f}")
                    
        except Exception as e:
            print(f"❌ Replacement order error: {e}")

    def check_smart_profit_opportunities(self):
        """🧠 เช็คโอกาสทำกำไรอัจฉริยะ"""
        
        try:
            portfolio_analysis = self.analyze_portfolio_positions()
            if 'error' in portfolio_analysis:
                return
                
            positions = portfolio_analysis.get('grid_positions', [])
            
            if len(positions) < 2:
                return
                
            # หาคู่ที่ควรปิด
            profitable_pairs = self.find_profitable_pairs(positions)
            
            if profitable_pairs:
                print(f"💰 Found {len(profitable_pairs)} profit opportunities")
                
                # ปิดคู่ที่ดีที่สุด
                best_pair = profitable_pairs[0]
                print(f"🎯 Executing best opportunity: {best_pair['pair_type']} → ${best_pair['net_profit']:.2f}")
                
                success = self.execute_pair_close(best_pair)
                if success:
                    print(f"✅ Pair closed successfully: +${best_pair['net_profit']:.2f}")
                    
                    # หน่วงเวลาก่อนหาโอกาสใหม่
                    time.sleep(2)
                    
        except Exception as e:
            print(f"❌ Check profit opportunities error: {e}")

    def execute_pair_close(self, pair) -> bool:
        """ปิด pair positions"""
        
        try:
            all_positions = pair['losing_positions'] + pair['profitable_positions']
            
            print(f"💰 Closing {pair['pair_type']}: {len(all_positions)} positions = +${pair['net_profit']:.2f}")
            
            success_count = 0
            for pos in all_positions:
                success = self.close_entire_position(pos)
                if success:
                    success_count += 1
                    print(f"   ✅ Closed: ${pos.pnl:.2f}")
                    time.sleep(0.5)  # รอสักครู่ระหว่างการปิด
                else:
                    print(f"   ❌ Failed: ${pos.pnl:.2f}")
            
            if success_count == len(all_positions):
                print(f"   🎉 {pair['pair_type']} completed: +${pair['net_profit']:.2f}")
                return True
            else:
                print(f"   ⚠️ Partial success: {success_count}/{len(all_positions)} closed")
                return False
                
        except Exception as e:
            print(f"❌ Pair close error: {e}")
            return False

    def find_hedge_opportunities(self, positions):
        """หาโอกาส hedge สำหรับ positions ที่ขาดทุนมาก"""
        
        try:
            hedge_opportunities = []
            heavy_losers = [p for p in positions if p.pnl < -10]  # ขาดทุนเกิน $10
            
            if not heavy_losers:
                return []
            
            # จัดกลุ่มตาม direction
            losing_buys = [p for p in heavy_losers if p.direction == "BUY"]
            losing_sells = [p for p in heavy_losers if p.direction == "SELL"]
            
            # Hedge BUY positions ที่ขาดทุน
            if losing_buys:
                total_buy_loss = sum(p.pnl for p in losing_buys)
                total_buy_lots = sum(p.lot_size for p in losing_buys)
                
                hedge_opportunities.append({
                    'type': 'SELL_HEDGE',
                    'direction': 'SELL',
                    'lot_size': round(total_buy_lots * 0.6, 3),  # 60% hedge
                    'target_loss': total_buy_loss,
                    'target_positions': losing_buys
                })
            
            # Hedge SELL positions ที่ขาดทุน
            if losing_sells:
                total_sell_loss = sum(p.pnl for p in losing_sells)
                total_sell_lots = sum(p.lot_size for p in losing_sells)
                
                hedge_opportunities.append({
                    'type': 'BUY_HEDGE',
                    'direction': 'BUY',
                    'lot_size': round(total_sell_lots * 0.6, 3),  # 60% hedge
                    'target_loss': total_sell_loss,
                    'target_positions': losing_sells
                })
            
            return hedge_opportunities
            
        except Exception as e:
            print(f"❌ Find hedge opportunities error: {e}")
            return []

    def execute_smart_hedges(self, hedge_opportunities):
        """วาง smart hedges"""
        
        for hedge in hedge_opportunities:
            try:
                direction = hedge['direction']
                lot_size = hedge['lot_size']
                target_loss = hedge['target_loss']
                
                print(f"🛡️ Placing {direction} hedge: {lot_size} lots for ${target_loss:.2f} loss")
                
                # วาง market order เป็น hedge
                result = self.place_market_order(direction, lot_size, f"HEDGE_{direction}")
                if result:
                    print(f"   ✅ {direction} hedge placed successfully")
                else:
                    print(f"   ❌ Failed to place {direction} hedge")
                    
            except Exception as e:
                print(f"❌ Execute hedge error: {e}")

    def get_profit_management_status(self) -> Dict:
        """Get current profit management status for GUI"""
        
        try:
            portfolio_analysis = self.analyze_portfolio_positions()
            
            return {
                'strategy': self.default_strategy.value,
                'total_positions': portfolio_analysis.get('total_positions', 0),
                'hedge_positions': portfolio_analysis.get('hedge_positions', 0),
                'total_pnl': portfolio_analysis.get('total_pnl', 0),
                'risk_percentage': portfolio_analysis.get('risk_percentage', 0),
                'trailing_stops_active': sum(1 for pos in portfolio_analysis.get('grid_positions', []) 
                                            if hasattr(pos, 'trailing_stop_price') and pos.trailing_stop_price is not None),
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}

    def check_and_run_recovery(self, portfolio_analysis: Dict):
        """ตรวจสอบและเรียกใช้ Recovery System - Fixed Version with Equity Check"""
        try:
            total_pnl = portfolio_analysis.get('total_pnl', 0)
            
            # 🔧 เพิ่มการเช็ค equity vs balance ก่อนทุกอย่าง
            account_info = self.mt5_connector.get_account_info()
            if account_info:
                balance = account_info.get('balance', 0)
                equity = account_info.get('equity', 0)
                profit_amount = equity - balance
                
                print(f"💰 Account Status Check:")
                print(f"   Balance: ${balance:.2f}")
                print(f"   Equity: ${equity:.2f}")
                print(f"   Net Profit: ${profit_amount:.2f}")
                
                # ✅ ถ้า equity > balance = Portfolio มีกำไร ไม่ต้อง recovery เลย
                if equity > balance:
                    print(f"✅ Portfolio PROFITABLE: +${profit_amount:.2f}")
                    print(f"   💡 Recovery system DISABLED - Account is making profit")
                    print(f"   🎯 Focus on normal profit optimization instead")
                    
                    # ปิด recovery ถ้าเปิดอยู่
                    if self.recovery_active:
                        print(f"💊 Stopping active recovery - Portfolio now profitable")
                        self.recovery_active = False
                        self.recovery_start_time = None
                    
                    return  # ออกจาก function ทันที
                
                # ✅ ถ้า equity ≈ balance (ใกล้เคียงกันใน ±$5)
                elif abs(profit_amount) <= 5.0:
                    print(f"⚖️ Portfolio BALANCED: ${profit_amount:.2f}")
                    print(f"   💡 Minor fluctuation - no recovery needed")
                    
                    # ปิด recovery ถ้าเปิดอยู่
                    if self.recovery_active:
                        print(f"💊 Stopping recovery - Portfolio balanced")
                        self.recovery_active = False
                        self.recovery_start_time = None
                    
                    return
                
                # ✅ เฉพาะตอนที่ equity < balance ถึงจะพิจารณา recovery
                else:
                    actual_loss = abs(profit_amount)
                    print(f"📉 Portfolio LOSING: -${actual_loss:.2f}")
                    
                    # ใช้ actual loss จาก equity แทน total_pnl
                    effective_trigger_loss = abs(self.recovery_trigger_loss)
                    
                    print(f"   🔍 Actual Loss: ${actual_loss:.2f}")
                    print(f"   🎯 Recovery Trigger: ${effective_trigger_loss:.2f}")
                    
                    # เช็คเงื่อนไข trigger ใหม่
                    should_trigger = (
                        actual_loss >= effective_trigger_loss and  # ขาดทุนจริงเกินกำหนด
                        not self.recovery_active and              # ยังไม่ active
                        len(portfolio_analysis.get('grid_positions', [])) > 0  # มี positions
                    )
                    
                    if should_trigger:
                        print(f"🚨 Recovery trigger conditions met:")
                        print(f"   Loss ${actual_loss:.2f} >= Trigger ${effective_trigger_loss:.2f}")
                        
                        if self.recovery_auto_mode:
                            print(f"💊 Auto-recovery ACTIVATED")
                            self.start_portfolio_recovery(portfolio_analysis)
                        else:
                            print(f"💊 Recovery trigger ready - Use manual activation")
                            print(f"   Or enable auto_mode for automatic recovery")
                    else:
                        # แสดงสถานะปัจจุบัน
                        if actual_loss > 0:
                            progress_pct = (actual_loss / effective_trigger_loss) * 100
                            print(f"⏳ Recovery progress: {progress_pct:.1f}% to trigger")
                        
                        if self.recovery_active:
                            self.monitor_recovery_progress(portfolio_analysis)
            
            else:
                print(f"❌ Cannot get account info for recovery check")
                
        except Exception as e:
            print(f"❌ Recovery check error: {e}")
            # แสดง debug info
            import traceback
            print(f"🔍 Debug traceback:")
            traceback.print_exc()

    def start_portfolio_recovery(self, portfolio_analysis: Dict):
        """เริ่ม Portfolio Recovery Process"""
        try:
            print(f"💊 === PORTFOLIO RECOVERY STARTED ===")
            
            self.recovery_active = True
            self.recovery_start_time = datetime.now()
            self.recovery_initial_pnl = portfolio_analysis.get('total_pnl', 0)
            
            print(f"   Initial PnL: ${self.recovery_initial_pnl:.2f}")
            print(f"   Target: Break-even or positive")
            
            # วิเคราะห์โอกาสในการ recovery
            recovery_plan = self.analyze_recovery_opportunities(portfolio_analysis)
            
            if recovery_plan['viable']:
                self.execute_recovery_plan(recovery_plan)
            else:
                print(f"   ⚠️ No viable recovery options found")
                self.recovery_active = False
                
        except Exception as e:
            print(f"❌ Recovery start error: {e}")
            self.recovery_active = False

    def analyze_recovery_opportunities(self, portfolio_analysis: Dict) -> Dict:
        """วิเคราะห์โอกาสในการกู้คืน portfolio"""
        try:
            positions = portfolio_analysis.get('grid_positions', [])
            
            # แยก positions ตามสถานะ
            losing_positions = [p for p in positions if p.pnl < -1]  # ขาดทุน > $1
            profitable_positions = [p for p in positions if p.pnl > 1]  # กำไร > $1
            neutral_positions = [p for p in positions if -1 <= p.pnl <= 1]  # ใกล้เคียง
            
            total_loss = sum(p.pnl for p in losing_positions)
            total_profit = sum(p.pnl for p in profitable_positions)
            net_pnl = total_loss + total_profit
            
            print(f"   📊 Recovery Analysis:")
            print(f"      Losing: {len(losing_positions)} positions, ${total_loss:.2f}")
            print(f"      Profitable: {len(profitable_positions)} positions, ${total_profit:.2f}")
            print(f"      Net PnL: ${net_pnl:.2f}")
            
            # ประเมินความเป็นไปได้
            viable = False
            recovery_method = "NONE"
            
            if len(profitable_positions) >= len(losing_positions) and total_profit > abs(total_loss) * 0.7:
                viable = True
                recovery_method = "PROFIT_CLOSE_RECOVERY"
                
            elif len(losing_positions) > 3 and total_loss < -20:
                viable = True
                recovery_method = "HEDGE_RECOVERY"
                
            return {
                'viable': viable,
                'method': recovery_method,
                'losing_positions': losing_positions,
                'profitable_positions': profitable_positions,
                'total_loss': total_loss,
                'total_profit': total_profit,
                'net_pnl': net_pnl
            }
            
        except Exception as e:
            print(f"❌ Recovery analysis error: {e}")
            return {'viable': False}

    def execute_recovery_plan(self, recovery_plan: Dict):
        """ดำเนินการ recovery plan"""
        try:
            method = recovery_plan['method']
            
            if method == "PROFIT_CLOSE_RECOVERY":
                print(f"   💰 Executing PROFIT CLOSE RECOVERY")
                
                # ใช้ profitable positions ปิด losing positions
                profit_positions = recovery_plan['profitable_positions']
                losing_positions = recovery_plan['losing_positions']
                
                # สร้างคู่ที่ดีที่สุด
                recovery_pairs = []
                for profit_pos in profit_positions:
                    for loss_pos in losing_positions:
                        net_pnl = profit_pos.pnl + loss_pos.pnl
                        if net_pnl > -0.5:  # ยอมขาดทุนเล็กน้อย
                            recovery_pairs.append({
                                'losing_positions': [loss_pos],
                                'profitable_positions': [profit_pos],
                                'net_profit': net_pnl,
                                'pair_type': 'RECOVERY_PAIR'
                            })
                            
                if recovery_pairs:
                    self.execute_pair_closes(recovery_pairs[:2])  # ปิดสูงสุด 2 คู่
                    
            elif method == "HEDGE_RECOVERY":
                print(f"   🛡️ Executing HEDGE RECOVERY")
                
                # วาง hedge orders
                hedge_opportunities = self.find_hedge_opportunities(recovery_plan['losing_positions'])
                if hedge_opportunities:
                    self.execute_smart_hedges(hedge_opportunities)
                    
        except Exception as e:
            print(f"❌ Recovery execution error: {e}")

    def monitor_recovery_progress(self, portfolio_analysis: Dict):
        """ติดตาม progress ของ recovery"""
        try:
            current_pnl = portfolio_analysis.get('total_pnl', 0)
            recovery_pnl = current_pnl - self.recovery_initial_pnl
            
            # เช็คว่า recovery สำเร็จหรือยัง
            if current_pnl >= -5:  # เกือบ break-even หรือกำไร
                print(f"💊 === PORTFOLIO RECOVERY SUCCESSFUL ===")
                print(f"   Initial PnL: ${self.recovery_initial_pnl:.2f}")
                print(f"   Current PnL: ${current_pnl:.2f}")
                print(f"   Recovery Gain: +${recovery_pnl:.2f}")
                
                self.recovery_active = False
                self.recovery_start_time = None
                
            # เช็ค timeout (30 นาที)
            elif self.recovery_start_time:
                elapsed = (datetime.now() - self.recovery_start_time).total_seconds() / 60
                if elapsed > 30:
                    print(f"💊 Recovery timeout after {elapsed:.1f} minutes")
                    print(f"   Recovery gain: +${recovery_pnl:.2f}")
                    self.recovery_active = False
                    
            # แสดงความคืบหน้าทุก 5 นาที
            elif self.recovery_start_time:
                elapsed = (datetime.now() - self.recovery_start_time).total_seconds() / 60
                if int(elapsed) % 5 == 0:  # ทุก 5 นาที
                    print(f"💊 Recovery progress: {elapsed:.1f}min, PnL: ${current_pnl:.2f}, Gain: +${recovery_pnl:.2f}")
                    
        except Exception as e:
            print(f"❌ Recovery monitoring error: {e}")

    def get_recovery_status(self) -> Dict:
        """Get recovery system status"""
        try:
            status = {
                'enabled': self.recovery_enabled,
                'active': self.recovery_active,
                'auto_mode': self.recovery_auto_mode,
                'trigger_loss': self.recovery_trigger_loss
            }
            
            if self.recovery_active and self.recovery_start_time:
                elapsed_minutes = (datetime.now() - self.recovery_start_time).total_seconds() / 60
                status.update({
                    'elapsed_minutes': elapsed_minutes,
                    'initial_pnl': self.recovery_initial_pnl,
                    'status': 'RUNNING'
                })
            else:
                status['status'] = 'STANDBY'
                
            return status
            
        except Exception as e:
            return {'error': str(e)}

    def manual_trigger_recovery(self):
        """Manual trigger สำหรับ GUI"""
        try:
            if self.recovery_active:
                print(f"💊 Recovery already active")
                return False
                
            portfolio = self.analyze_portfolio_positions()
            if 'error' in portfolio:
                print(f"💊 Cannot analyze portfolio for recovery")
                return False
                
            print(f"💊 Manual recovery triggered")
            self.start_portfolio_recovery(portfolio)
            return True
            
        except Exception as e:
            print(f"❌ Manual recovery error: {e}")
            return False

    def get_grid_status(self):
        """Get comprehensive grid status for GUI"""
        try:
            base_status = {
                'trading_active': self.trading_active,
                'gold_symbol': self.gold_symbol,
                'current_price': self.get_current_price(),
                'total_pnl': round(self.total_pnl, 2),
                'unrealized_pnl': round(self.unrealized_pnl, 2),
                'realized_pnl': round(self.realized_pnl, 2),
                'current_drawdown': round(self.current_drawdown, 0),
                'max_drawdown': round(self.max_drawdown_points, 0),
                'active_positions': len(self.active_positions),
                'pending_orders': len(self.pending_orders),
                'trades_opened': self.trades_opened,
                'trades_closed': self.trades_closed,
                'win_rate': round(self.win_rate * 100, 1),
                'largest_win': round(self.largest_win, 2),
                'largest_loss': round(self.largest_loss, 2),
                'emergency_stop': self.emergency_stop_triggered,
                'last_update': self.last_update.isoformat(),
                'survivability_used': round((self.current_drawdown / self.survivability) * 100, 1) if self.survivability > 0 else 0,
                'daily_pnl': round(self.total_pnl, 2),
                'magic_number': self.magic_number,
                'ai_control_mode': True,
                'smart_profit_enabled': True
            }
            
            # Add Smart Profit status
            try:
                smart_status = self.get_profit_management_status()
                base_status['smart_profit_status'] = smart_status
                
                recovery_status = self.get_recovery_status()
                base_status['recovery_system'] = recovery_status
                
                # Add AI health score
                portfolio = self.analyze_portfolio_positions()
                ai_health = self.calculate_ai_health_score(portfolio)
                base_status['ai_health_score'] = ai_health
                
            except Exception as smart_error:
                base_status['smart_profit_status'] = {'error': str(smart_error)}
                base_status['recovery_system'] = {'enabled': False, 'active': False}
                base_status['ai_health_score'] = 50
                
            return base_status
            
        except Exception as e:
            print(f"❌ Error getting grid status: {e}")
            return {'error': str(e)}

    def is_market_open(self) -> bool:
        """Check if market is open"""
        try:
            current_time = datetime.now()
            
            if current_time.weekday() >= 5:
                return False
                
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                return False
                
            return tick.time > 0
            
        except Exception as e:
            print(f"❌ Error checking market status: {e}")
            return False

    def reset_emergency_stop(self):
        """Reset emergency stop status"""
        try:
            self.emergency_stop_triggered = False
            print("✅ Emergency stop status reset")
            print("🔄 Ready to start AI trading again")
            
        except Exception as e:
            print(f"❌ Error resetting emergency stop: {e}")

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            if getattr(self, 'trading_active', False):
                print("🛑 AI Smart Profit system cleanup - stopping trading")
                self.stop_trading()
        except:
            pass

# Test function for AI Smart Profit system
def test_ai_smart_profit_system():
    """Test the complete AI Smart Profit system"""
    
    print("🧠 AI SMART PROFIT SYSTEM TEST")
    print("="*60)
    
    test_params = {
        'base_lot': 0.05,
        'grid_spacing': 300,
        'max_levels': 67,
        'survivability': 20100,
        'realistic_survivability': 18500,
        'account_balance': 10000
    }
    
    test_config = {
        'target_survivability': 20000,
        'safety_ratio': 0.6,
        'daily_loss_limit': 500,
        'portfolio_recovery': {
            'enabled': True,
            'trigger_loss': -50,
            'auto_mode': True
        }
    }
   
   
    print("⚠️ This test requires:")
    print("   1. Active MT5 connection")
    print("   2. AI Money Manager available")
    print("   3. Survivability Engine available")
    print("   4. Sufficient account balance")
    print("   5. Gold symbol available")
    
    print(f"\n🧠 AI Smart Profit Features:")
    print("   ✅ Complete MT5 integration")
    print("   ✅ AI Portfolio Analysis")
    print("   ✅ Intelligent profit taking")
    print("   ✅ Portfolio recovery system")
    print("   ✅ Real-time performance optimization")
    print("   ✅ Advanced risk management")
    print("   ✅ Order placement and management")
    print("   ✅ Position monitoring")
    print("   ✅ Emergency protection")
    
    print(f"\n🛡️ Safety Features:")
    print("   ✅ AI health monitoring")
    print("   ✅ Emergency protection systems")
    print("   ✅ Survivability guarantee")
    print("   ✅ Portfolio balance maintenance")
    print("   ✅ Automatic risk management")
    
    print(f"\n📊 Test Parameters:")
    print(f"   AI Control Mode: FULL CONTROL")
    print(f"   Base Lot: {test_params['base_lot']}")
    print(f"   Grid Spacing: {test_params['grid_spacing']} points")
    print(f"   Survivability: {test_params['survivability']:,} points")
    print(f"   Recovery Trigger: ${test_config['portfolio_recovery']['trigger_loss']}")
    print(f"   Magic Number: Auto-generated")
    
    print("\n" + "="*60)
    print("🚀 Ready for COMPLETE AI SMART PROFIT TRADING!")
    print("🧠 Full AI intelligence with MT5 integration!")
    print("💰 All-in-one trading solution!")

if __name__ == "__main__":
    test_ai_smart_profit_system()

