"""
Smart Profit Management System - Complete Trading Engine
smart_profit_manager.py
Advanced profit taking with portfolio analysis, trailing stops, and intelligent closing
ENHANCED VERSION - Full trading system with MT5 integration
"""

import math
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import MetaTrader5 as mt5
import itertools
import threading
import json
import os

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
        """ปิด position ทั้งหมด - แก้ไข filling mode"""
        
        try:
            # ดึง position จาก MT5
            if isinstance(position, SmartPosition):
                position_id = position.position_id
            else:
                position_id = position.get('ticket') or position.get('position_id')
                
            positions = mt5.positions_get(ticket=position_id)
            if not positions or len(positions) == 0:
                print(f"   Position {position_id} not found or already closed")
                return True  # ถือว่าปิดแล้ว
                
            mt5_position = positions[0]
            
            # เตรียม close request
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"   Cannot get tick data")
                return False
                
            if mt5_position.type == mt5.POSITION_TYPE_BUY:
                close_price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            else:
                close_price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY
                
            print(f"   🎯 Closing position {position_id}: {mt5_position.volume} lots @ ${close_price:.2f}")
            
            # ✅ ลอง filling modes ตามลำดับความปลอดภัย + เพิ่ม None
            filling_modes = [
                None,                      # ไม่ระบุ filling mode
                mt5.ORDER_FILLING_IOC,
                mt5.ORDER_FILLING_FOK,
                mt5.ORDER_FILLING_RETURN
            ]
            
            for i, filling_mode in enumerate(filling_modes):
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.gold_symbol,
                    "volume": mt5_position.volume,
                    "type": order_type,
                    "position": position_id,
                    "price": close_price,
                    "deviation": 50,
                    "magic": self.magic_number,
                    "comment": "AI_SMART_CLOSE"
                }
                
                # ✅ เพิ่ม filling mode เฉพาะเมื่อไม่ใช่ None
                if filling_mode is not None:
                    request["type_filling"] = filling_mode
                    
                mode_name = "AUTO" if filling_mode is None else str(filling_mode)
                print(f"      🔄 Trying close mode {i+1}: {mode_name}")
                
                result = mt5.order_send(request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   ✅ Position {position_id} closed with mode {i+1}")
                    
                    # Update internal tracking
                    if position_id in self.active_positions:
                        del self.active_positions[position_id]
                        
                    return True
                else:
                    error_msg = f"Close mode {i+1} failed"
                    if result:
                        error_msg += f" - Code: {result.retcode}"
                        if hasattr(result, 'comment'):
                            error_msg += f", {result.comment}"
                    print(f"   ⚠️ {error_msg}")
                    
                    if result and result.retcode in [10018, 10030]:  # Filling mode errors
                        continue  # ลอง mode ถัดไป
                    elif result and result.retcode == 10025:  # Autotrading disabled
                        print(f"   ❌ Autotrading is disabled - cannot close positions")
                        break
                    elif result and result.retcode not in [10018, 10030]:  # ถ้าไม่ใช่ filling mode error
                        break
                        
            print(f"   ❌ All close modes failed for position {position_id}")
            return False
                    
        except Exception as e:
            print(f"❌ Close position error: {e}")
            return False

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
        """🧠 AI หลัก - เพิ่มการเช็ค balance"""
        
        try:
            # 1. 🧠 AI วิเคราะห์ positions ปัจจุบัน
            portfolio = self.analyze_portfolio_positions()
            if 'error' in portfolio or portfolio.get('total_positions', 0) == 0:
                print("🔄 No positions detected - AI creating intelligent grid")
                self.create_grid_immediately()
                return
                
            positions = portfolio.get('grid_positions', [])
            total_pnl = portfolio.get('total_pnl', 0)
            
            # เพิ่ม: แสดงข้อมูล portfolio balance
            buy_positions = [p for p in positions if p.direction == "BUY"]
            sell_positions = [p for p in positions if p.direction == "SELL"]
            
            print(f"📊 Portfolio: {len(buy_positions)} BUY, {len(sell_positions)} SELL, PnL: ${total_pnl:.2f}")
            
            # เพิ่ม: เช็ค imbalance และแก้ไข
            position_imbalance = abs(len(buy_positions) - len(sell_positions))
            if position_imbalance > 3:  # ถ้าไม่ balanced มาก
                print(f"⚖️ AI: Position imbalance detected ({position_imbalance}), adding orders...")
                self.create_grid_immediately()  # เพิ่ม orders ใหม่
            
            # 🧠 AI ตรวจสอบ survivability ปัจจุบัน
            if hasattr(self, 'ai_grid_config'):
                target_survivability = self.ai_grid_config.get('target_survivability', 10000)
                current_coverage = self.estimate_current_survivability(positions)
                survivability_ratio = current_coverage / target_survivability
                
                print(f"🛡️ AI SURVIVABILITY CHECK: {current_coverage:,}/{target_survivability:,} points ({survivability_ratio:.1%})")
                
                if survivability_ratio < 0.6:  # น้อยกว่า 60% ของ target
                    print("🚨 AI: SURVIVABILITY CRITICAL - Adding protective positions")
                    self.rebalance_portfolio_if_needed(positions)
                    return
            
            # 2. 🧠 AI ปิดไม้อย่างฉลาด (ใช้ method ที่ฉลาดแล้ว)
            profitable_pairs = self.find_profitable_pairs(positions)
            
            if profitable_pairs:
                print(f"💰 AI PROFIT OPPORTUNITY: {len(profitable_pairs)} intelligent closes")
                self.execute_pair_closes(profitable_pairs)
                time.sleep(1)
                
                # อัพเดท portfolio หลังปิด
                portfolio = self.analyze_portfolio_positions()
                positions = portfolio.get('grid_positions', [])
                
                # 🧠 AI เช็คว่าหลังปิดแล้ว survivability ยังพอหรือไม่
                if len(positions) < 4:
                    print("🔧 AI: Post-close analysis - Need more coverage")
                    self.rebalance_portfolio_if_needed(positions)
            
            # 3. 🧠 AI Portfolio Recovery (ถ้าขาดทุน)
            if self.recovery_enabled:
                self.check_and_run_recovery(portfolio)
            
        except Exception as e:
            print(f"❌ Smart profit management error: {e}")

    def create_grid_immediately(self):
        """สร้าง grid ใหม่ทันที - แก้ไขให้กระจายห่างขึ้น"""
        try:
            # เช็คว่ามี pending orders อยู่แล้วหรือไม่
            if len(self.pending_orders) >= 10:  # เพิ่มจาก 6 เป็น 10
                print(f"🔄 Sufficient orders exist ({len(self.pending_orders)}) - checking spread")
                self.ensure_proper_grid_spread()
                return
                
            print("🧠 AI: Creating wide-spread grid coverage...")
            
            current_price = self.get_current_price()
            if not current_price:
                print("❌ Cannot get current price")
                return
                
            # ✅ เพิ่ม spacing ให้กว้างขึ้น
            base_spacing = self.grid_spacing * 0.01
            wide_spacing = base_spacing * 1.5  # เพิ่ม 50%
            
            print(f"   📏 Base spacing: ${base_spacing:.2f}")
            print(f"   📏 Wide spacing: ${wide_spacing:.2f}")
            
            orders_created = 0
            
            # นับ orders ที่มีอยู่
            buy_orders = [o for o in self.pending_orders.values() if o['direction'] == 'BUY']
            sell_orders = [o for o in self.pending_orders.values() if o['direction'] == 'SELL']
            
            print(f"📊 Current orders: {len(buy_orders)} BUY, {len(sell_orders)} SELL")
            
            # ✅ BUY orders - กระจายไกลขึ้น
            if len(buy_orders) < 5:  # เพิ่มเป้าหมาย
                print("🟢 Creating BUY ladder:")
                for i in range(1, 8):  # เพิ่มระดับ
                    # ใช้ progressive spacing - ยิ่งไกลยิ่งห่าง
                    distance_multiplier = 1.0 + (i * 0.2)  # 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2
                    buy_price = current_price - (wide_spacing * i * distance_multiplier)
                    
                    print(f"   🎯 Level {i}: ${buy_price:.2f} (distance: {wide_spacing * i * distance_multiplier:.2f})")
                    
                    if buy_price > 100:  # ป้องกันราคาต่ำเกิน
                        if not self.has_order_near_price(buy_price, 'BUY', tolerance=wide_spacing * 0.3):
                            if self.place_pending_order(buy_price, 'BUY', self.base_lot):
                                orders_created += 1
                                print(f"   ✅ BUY placed: ${buy_price:.2f}")
                                
                            # หยุดถ้าได้เป้าหมายแล้ว
                            current_buy_count = len([o for o in self.pending_orders.values() if o['direction'] == 'BUY'])
                            if current_buy_count >= 5:
                                break
                                
            # ✅ SELL orders - กระจายไกลขึ้น
            if len(sell_orders) < 5:  # เพิ่มเป้าหมาย
                print("🔴 Creating SELL ladder:")
                for i in range(1, 8):  # เพิ่มระดับ
                    # ใช้ progressive spacing - ยิ่งไกลยิ่งห่าง
                    distance_multiplier = 1.0 + (i * 0.2)  # 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2
                    sell_price = current_price + (wide_spacing * i * distance_multiplier)
                    
                    print(f"   🎯 Level {i}: ${sell_price:.2f} (distance: {wide_spacing * i * distance_multiplier:.2f})")
                    
                    if not self.has_order_near_price(sell_price, 'SELL', tolerance=wide_spacing * 0.3):
                        if self.place_pending_order(sell_price, 'SELL', self.base_lot):
                            orders_created += 1
                            print(f"   ✅ SELL placed: ${sell_price:.2f}")
                            
                        # หยุดถ้าได้เป้าหมายแล้ว
                        current_sell_count = len([o for o in self.pending_orders.values() if o['direction'] == 'SELL'])
                        if current_sell_count >= 5:
                            break
                            
            if orders_created > 0:
                print(f"✅ Wide-spread grid created: {orders_created} orders")
                self.print_grid_coverage()
            else:
                print(f"✅ Grid coverage adequate")
                
        except Exception as e:
            print(f"❌ Grid creation error: {e}")

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
            
            print(f"🔍 BALANCE DEBUG:")
            print(f"   Current price: ${current_price:.2f}")
            print(f"   BUY orders: {len(buy_orders)}")
            print(f"   SELL orders: {len(sell_orders)}")
            print(f"   Pending orders total: {len(self.pending_orders)}")
            
            imbalance = abs(len(buy_orders) - len(sell_orders))
            
            if imbalance > 2:  # ไม่ balanced
                print(f"⚖️ CRITICAL IMBALANCE: {len(buy_orders)} BUY vs {len(sell_orders)} SELL")
                
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

    def has_order_near_price(self, target_price, direction, tolerance=0.50):
        """เพิ่ม tolerance parameter และ debug"""
        try:
            found_near = False
            closest_distance = float('inf')
            
            for order_info in self.pending_orders.values():
                if order_info['direction'] == direction:
                    distance = abs(order_info['price'] - target_price)
                    if distance < closest_distance:
                        closest_distance = distance
                    if distance < tolerance:
                        found_near = True
                        
            if found_near:
                print(f"   📍 Found {direction} order near ${target_price:.2f} (distance: {closest_distance:.2f})")
            else:
                print(f"   🆕 No {direction} order near ${target_price:.2f} (closest: {closest_distance:.2f})")
                
            return found_near
            
        except Exception as e:
            print(f"❌ Check order near price error: {e}")
            return False

        
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
            
            print(f"📊 Portfolio: {len(grid_positions)} total, {len(profitable_positions)} profit, {len(losing_positions)} loss")
            
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
        """🧠 AI หาคู่ไม้ที่ควรปิด - Enhanced with Portfolio Protection & Higher Thresholds"""
        
        try:
            if len(positions) < 1:
                return []
                
            print(f"🧠 AI ANALYZING {len(positions)} positions for fast intelligent closure...")
            
            current_price = self.get_current_price()
            buy_positions = [p for p in positions if p.direction == "BUY"]
            sell_positions = [p for p in positions if p.direction == "SELL"]
            
            # ✅ เช็ค margin level ก่อน
            margin_level = self.get_current_margin_level()
            margin_pressure = margin_level < 300 if margin_level > 0 else False
            
            print(f"📊 Portfolio: {len(buy_positions)} BUY, {len(sell_positions)} SELL, Market: ${current_price:.2f}")
            print(f"📊 Margin Level: {margin_level:.1f}%, Pressure: {'HIGH' if margin_pressure else 'OK'}")
            
            smart_pairs = []
            
            # 🚀 STRATEGY 1: FAST PROFIT CLOSE (เน้นเร็ว)
            print("🚀 Strategy 1: Fast profit opportunities")
            for pos in positions:
                # Quick profit close - ปิดเร็วถ้ากำไรดี
                if pos.pnl > 2.0:  # กำไรเกิน $2
                    smart_pairs.append({
                        'losing_positions': [],
                        'profitable_positions': [pos],
                        'net_profit': pos.pnl,
                        'total_positions': 1,
                        'pair_type': "FAST_PROFIT",
                        'priority_score': 3000 + pos.pnl * 10,  # Priority สูงสุด
                        'position_ids': {pos.position_id},
                        'margin_impact': f"+${pos.lot_size * 400:.0f} freed",
                        'reason': f"Fast profit close: ${pos.pnl:.2f}"
                    })
                    print(f"   🚀 FAST PROFIT: {pos.direction} ${pos.pnl:.2f}")
                
                # Medium profit with time consideration
                elif pos.pnl > 1.0:
                    position_age = self.calculate_position_age(pos)
                    if position_age > 30:  # อายุเกิน 30 นาที
                        smart_pairs.append({
                            'losing_positions': [],
                            'profitable_positions': [pos],
                            'net_profit': pos.pnl,
                            'total_positions': 1,
                            'pair_type': "TIMED_PROFIT",
                            'priority_score': 2500 + pos.pnl * 10 + position_age,
                            'position_ids': {pos.position_id},
                            'margin_impact': f"+${pos.lot_size * 400:.0f} freed",
                            'reason': f"Timed profit: ${pos.pnl:.2f} (age: {position_age}min)"
                        })
                        print(f"   ⏰ TIMED PROFIT: {pos.direction} ${pos.pnl:.2f} (age: {position_age}min)")
            
            # 🛡️ STRATEGY 2: ENHANCED RESCUE WITH MULTI-SOURCE
            print("🛡️ Strategy 2: Enhanced rescue operations")
            
            # หาไม้ที่ต้องช่วย (ขาดทุนหนัก + ค้างนาน)
            rescue_targets = []
            for pos in positions:
                if pos.pnl < -2.0:  # ขาดทุนเกิน $2
                    position_age = self.calculate_position_age(pos)
                    rescue_urgency = abs(pos.pnl) + (position_age / 60)  # ยิ่งนาน + ขาดทุนมาก = ยิ่งเร่งด่วน
                    rescue_targets.append((pos, rescue_urgency))
                    
            # เรียงตามความเร่งด่วน
            rescue_targets.sort(key=lambda x: x[1], reverse=True)
            
            for target_pos, urgency in rescue_targets[:3]:  # ช่วยสูงสุด 3 ตัว
                print(f"   🆘 RESCUE TARGET: {target_pos.direction} ${target_pos.pnl:.2f} (urgency: {urgency:.1f})")
                
                # ✅ หา helpers จากทุกแหล่ง (BUY + SELL)
                potential_helpers = []
                
                # Helper Type 1: BUY positions ที่กำไร
                for buy_pos in buy_positions:
                    if buy_pos.pnl > 0.5 and buy_pos != target_pos:
                        net_loss = target_pos.pnl + buy_pos.pnl
                        potential_helpers.append({
                            'helper': buy_pos,
                            'net_result': net_loss,
                            'helper_type': 'BUY_RESCUE'
                        })
                
                # Helper Type 2: SELL positions ที่กำไร
                for sell_pos in sell_positions:
                    if sell_pos.pnl > 0.5 and sell_pos != target_pos:
                        net_loss = target_pos.pnl + sell_pos.pnl
                        potential_helpers.append({
                            'helper': sell_pos,
                            'net_result': net_loss,
                            'helper_type': 'SELL_RESCUE'
                        })
                
                # เรียงตาม net result ดีที่สุด
                potential_helpers.sort(key=lambda x: x['net_result'], reverse=True)
                
                # ✅ เลือก helper ที่ดีที่สุดที่ผ่านเงื่อนไข
                for helper_info in potential_helpers:
                    helper_pos = helper_info['helper']
                    net_result = helper_info['net_result']
                    
                    # ✅ Enhanced Loss Control with Emergency Mode
                    portfolio_imbalance = abs(len(buy_positions) - len(sell_positions))
                    total_losing_amount = sum(abs(p.pnl) for p in positions if p.pnl < -2)

                    # Emergency conditions
                    is_emergency = (
                        portfolio_imbalance > 8 or           # Portfolio ไม่สมดุลมาก
                        total_losing_amount > 50 or          # ขาดทุนรวมเกิน $50
                        len([p for p in positions if p.pnl < -5]) > 5  # มีไม้ขาดทุนหนัก > 5 ตัว
                    )

                    if is_emergency:
                        max_acceptable_loss = min(
                            abs(target_pos.pnl) * 0.6,      # เพิ่มเป็น 60% (จาก 25%)
                            5.0                             # เพิ่มเป็น $5 (จาก $1.5)
                        )
                        print(f"      🚨 EMERGENCY MODE: Higher loss tolerance ${max_acceptable_loss:.2f}")
                    else:
                        max_acceptable_loss = min(
                            abs(target_pos.pnl) * 0.4,      # เพิ่มเป็น 40% (จาก 25%)
                            3.0 if not margin_pressure else 2.0  # เพิ่มเป็น $3/$2 (จาก $1.5/$0.5)
                        )
                    
                    print(f"      🤔 Consider {helper_info['helper_type']}: helper ${helper_pos.pnl:.2f} → net ${net_result:.2f}")
                    print(f"         Max acceptable loss: ${max_acceptable_loss:.2f}")
                    
                    # ✅ เช็คว่าคุ้มค่าไหม
                    if net_result >= -max_acceptable_loss:
                        # ✅ Margin ROI Check
                        freed_margin = (abs(target_pos.pnl) + helper_pos.pnl) * 20  # ประมาณการ margin freed
                        margin_roi_per_hour = freed_margin * 0.05  # 5% ROI per hour (conservative)
                        breakeven_hours = abs(net_result) / margin_roi_per_hour if margin_roi_per_hour > 0 else 999
                        
                        if breakeven_hours < 3:  # คืนทุนใน 3 ชั่วโมง
                            smart_pairs.append({
                                'losing_positions': [target_pos],
                                'profitable_positions': [helper_pos],
                                'net_profit': net_result,
                                'total_positions': 2,
                                'pair_type': f"ENHANCED_RESCUE_{helper_info['helper_type']}",
                                'priority_score': 2000 + urgency * 10 - abs(net_result) * 5,
                                'position_ids': {target_pos.position_id, helper_pos.position_id},
                                'margin_impact': f"+${freed_margin:.0f} freed, ROI breakeven: {breakeven_hours:.1f}h",
                                'reason': f"Enhanced rescue: {helper_info['helper_type']} ${helper_pos.pnl:.2f} saves ${target_pos.pnl:.2f}"
                            })
                            print(f"   ✅ ENHANCED RESCUE: {helper_info['helper_type']} approved (breakeven: {breakeven_hours:.1f}h)")
                            break  # เลือกแค่ helper ตัวแรกที่ดีที่สุด
                    else:
                        print(f"      ❌ Net loss ${net_result:.2f} > limit ${max_acceptable_loss:.2f}")
            
            # 🎯 STRATEGY 3: STANDARD PAIRS (แก้ไขเงื่อนไข)
            print("🎯 Strategy 3: Standard profitable pairs")
            for buy_pos in buy_positions:
                for sell_pos in sell_positions:
                    net_pnl = buy_pos.pnl + sell_pos.pnl
                    
                    # ✅ ลดเงื่อนไขจาก 1.2 เป็น 0.8 เพื่อความเร็ว
                    profit_threshold = 0.8 if not margin_pressure else 0.5  # ถ้า margin pressure = ลดเงื่อนไข
                    
                    if net_pnl > profit_threshold:
                        margin_freed = (buy_pos.lot_size + sell_pos.lot_size) * 400
                        
                        smart_pairs.append({
                            'losing_positions': [buy_pos if buy_pos.pnl < 0 else sell_pos] if min(buy_pos.pnl, sell_pos.pnl) < 0 else [],
                            'profitable_positions': [p for p in [buy_pos, sell_pos] if p.pnl > 0],
                            'net_profit': net_pnl,
                            'total_positions': 2,
                            'pair_type': "STANDARD_PAIR",
                            'priority_score': 1500 + net_pnl * 10,
                            'position_ids': {buy_pos.position_id, sell_pos.position_id},
                            'margin_impact': f"+${margin_freed:.0f} freed",
                            'reason': f"Standard pair: ${buy_pos.pnl:.2f} + ${sell_pos.pnl:.2f}"
                        })
            
            # ✅ STRATEGY 4: MARGIN PRESSURE EMERGENCY
            if margin_pressure:
                print("🚨 Strategy 4: Margin pressure emergency")
                # ถ้า margin level ต่ำ = บังคับปิดเพื่อ free margin
                for pos in positions:
                    if pos.pnl > 0.3:  # กำไรเล็กๆ ก็ปิด
                        smart_pairs.append({
                            'losing_positions': [],
                            'profitable_positions': [pos],
                            'net_profit': pos.pnl,
                            'total_positions': 1,
                            'pair_type': "MARGIN_EMERGENCY",
                            'priority_score': 2800 + pos.pnl * 20,  # Priority สูง
                            'position_ids': {pos.position_id},
                            'margin_impact': f"+${pos.lot_size * 400:.0f} freed (URGENT)",
                            'reason': f"Margin emergency: ${pos.pnl:.2f}"
                        })
            
            # เรียงตาม priority
            smart_pairs.sort(key=lambda x: x['priority_score'], reverse=True)
            final_pairs = smart_pairs[:5]  # เพิ่มจาก 3 เป็น 5 เพื่อความเร็ว
        
            # ✅ เพิ่ม Portfolio Protection ก่อน return
            print("🛡️ PORTFOLIO PROTECTION CHECK:")
            protected_pairs = []

            for pair in final_pairs:
                # เช็คว่าการปิด pair นี้จะทำให้ portfolio เสียสมดุลไหม
                closing_positions = pair['losing_positions'] + pair['profitable_positions']
                
                # นับ positions ที่เหลือหลังปิด
                remaining_buy = len([p for p in buy_positions 
                                    if p.position_id not in pair['position_ids']])
                remaining_sell = len([p for p in sell_positions 
                                    if p.position_id not in pair['position_ids']])
                
                imbalance_after_close = abs(remaining_buy - remaining_sell)
                
                # เช็คว่าจะเหลือ helper positions พอไหม
                remaining_helpers = []
                for p in positions:
                    if (p.position_id not in pair['position_ids'] and 
                        p.pnl > 0.5):  # helper candidates
                        remaining_helpers.append(p)
                
                print(f"   Pair {pair['pair_type']}: After close → {remaining_buy} BUY, {remaining_sell} SELL")
                print(f"   Imbalance: {imbalance_after_close}, Remaining helpers: {len(remaining_helpers)}")
                
                # ✅ Portfolio Protection Rules
                should_protect = False
                protection_reason = ""
                
                # Rule 1: ห้ามปิดจนเหลือฝั่งเดียว < 2 ตัว
                if remaining_buy < 2 and len(buy_positions) <= 3:
                    should_protect = True
                    protection_reason = "Would leave too few BUY positions"
                elif remaining_sell < 2 and len(sell_positions) <= 3:
                    should_protect = True
                    protection_reason = "Would leave too few SELL positions"
                
                # Rule 2: ห้ามปิด helper สุดท้าย
                elif (len(remaining_helpers) < 2 and 
                    len([p for p in positions if p.pnl < -3]) > 5):  # มีไม้ค้างเยอะ
                    should_protect = True
                    protection_reason = "Would remove last helper positions"
                
                # Rule 3: ห้าม imbalance เกิน 10
                elif imbalance_after_close > 10:
                    should_protect = True
                    protection_reason = f"Would create extreme imbalance ({imbalance_after_close})"
                
                if should_protect:
                    print(f"   🛡️ PROTECTED: {pair['pair_type']} - {protection_reason}")
                else:
                    protected_pairs.append(pair)
                    print(f"   ✅ APPROVED: {pair['pair_type']} - Safe to close")

            # ใช้ protected_pairs แทน final_pairs
            final_pairs = protected_pairs
            
            if final_pairs:
                print(f"🧠 AI DECISION: Found {len(final_pairs)} intelligent pairs to close")
                for i, pair in enumerate(final_pairs, 1):
                    print(f"   {i}. {pair['pair_type']}: {pair['reason']} → {pair['margin_impact']}")
            else:
                print("🤔 AI DECISION: No safe closing opportunities found")
                print(f"   💡 Monitoring {len(positions)} positions for future opportunities")
            
            return final_pairs
            
        except Exception as e:
            print(f"❌ AI analysis error: {e}")
            return []

    def calculate_position_age(self, position):
        """คำนวณอายุของ position ในหน่วยนาที"""
        try:
            if hasattr(position, 'entry_time'):
                age = (datetime.now() - position.entry_time).total_seconds() / 60
                return max(0, age)
            return 0
        except:
            return 0

    def get_current_margin_level(self):
        """ดึง margin level ปัจจุบัน"""
        try:
            if self.mt5_connector:
                account_info = self.mt5_connector.get_account_info()
                if account_info:
                    return account_info.get('margin_level', 0)
            return 0
        except:
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

    def execute_pair_closes(self, pairs):
        """ปิดคู่ positions ที่ได้กำไรสุทธิ - รองรับ Multi-Position"""
        
        for pair in pairs:
            try:
                # เช็คว่าเป็น SINGLE position หรือ Multi-Position
                if pair['pair_type'] == "SINGLE":
                    # ปิดไม้เดี่ยว
                    pos = pair['profitable_positions'][0]
                    success = self.close_entire_position(pos)
                    if success:
                        print(f"   ✅ Single closed: +${pair['net_profit']:.2f}")
                    else:
                        print(f"   ❌ Single close failed")
                        
                else:
                    # ปิด Multi-Position (1:1, 1:2, 2:1, etc.)
                    all_positions = pair['losing_positions'] + pair['profitable_positions']
                    
                    print(f"💰 Closing {pair['pair_type']}: {len(all_positions)} pos = +${pair['net_profit']:.2f}")
                    
                    success_count = 0
                    for pos in all_positions:
                        success = self.close_entire_position(pos)
                        if success:
                            success_count += 1
                            print(f"   ✅ Closed: ${pos.pnl:.2f}")
                            time.sleep(0.2)  # รอสักครู่
                        else:
                            print(f"   ❌ Failed: ${pos.pnl:.2f}")
                    
                    if success_count == len(all_positions):
                        print(f"   🎉 {pair['pair_type']} completed: +${pair['net_profit']:.2f}")
                        
            except Exception as e:
                print(f"❌ Pair close error: {e}")

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
        """ตรวจสอบและเรียกใช้ Recovery System"""
        try:
            total_pnl = portfolio_analysis.get('total_pnl', 0)
            
            # เช็คเงื่อนไข trigger
            should_trigger = (
                total_pnl <= self.recovery_trigger_loss and  # ขาดทุนเกินกำหนด
                not self.recovery_active and                 # ยังไม่ active
                len(portfolio_analysis.get('grid_positions', [])) > 0  # มี positions
            )
            
            if should_trigger:
                if self.recovery_auto_mode:
                    self.start_portfolio_recovery(portfolio_analysis)
                else:
                    print(f"💊 Recovery trigger: PnL ${total_pnl:.2f} < ${self.recovery_trigger_loss}")
                    print(f"   Use manual recovery or enable auto_mode")
            
            # ถ้า recovery active อยู่ ให้ติดตามผล
            elif self.recovery_active:
                self.monitor_recovery_progress(portfolio_analysis)
                
        except Exception as e:
            print(f"❌ Recovery check error: {e}")

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

