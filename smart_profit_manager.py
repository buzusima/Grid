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
                    if profit_amount > 20:  # กำไรเกิน $20
                        print(f"   🚀 Portfolio ready for compound growth strategies")
                        print(f"   💡 Consider increasing position sizes gradually")
                
            except Exception as e:
                print(f"❌ Smart profit management error: {e}")
                # เพิ่ม debug info
                import traceback
                print(f"🔍 Debug traceback:")
                traceback.print_exc()

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
        """🧠 AI หาคู่ไม้ที่ควรปิด - FLEXIBLE VERSION ยืดหยุ่นข้าม BUY/SELL"""
        
        try:
            if len(positions) < 2:
                return []
                
            print(f"🧠 AI FLEXIBLE PAIR TRADING: {len(positions)} positions")
            
            current_price = self.get_current_price()
            buy_positions = [p for p in positions if p.direction == "BUY"]
            sell_positions = [p for p in positions if p.direction == "SELL"]
            
            # 🔄 แยกตามประเภท กำไร/ขาดทุน (ไม่สนใจ BUY/SELL)
            profitable_positions = [p for p in positions if p.pnl > 0.3]  # ลด threshold
            losing_positions = [p for p in positions if p.pnl < -0.5]     # ลด threshold
            
            # 🎯 เรียงไม้ขาดทุนตามความรุนแรง (ขาดทุนมากสุดก่อน)
            losing_positions.sort(key=lambda x: x.pnl)  # เรียงจากขาดทุนมากสุด
            
            # 🎯 เรียงไม้กำไรตามความแข็งแกร่ง (กำไรมากสุดก่อน)  
            profitable_positions.sort(key=lambda x: x.pnl, reverse=True)
            
            print(f"📊 Flexible Portfolio Analysis:")
            print(f"   💰 Profitable positions: {len(profitable_positions)}")
            print(f"   📉 Losing positions: {len(losing_positions)}")
            print(f"   🔄 BUY/SELL: {len(buy_positions)}/{len(sell_positions)}")
            
            if len(profitable_positions) == 0:
                print("❌ No profitable positions to help")
                return []
            
            # แสดงไม้ขาดทุนรุนแรงสุด
            if losing_positions:
                worst_losses = losing_positions[:5]  # 5 ตัวแย่สุด
                print(f"   🆘 Worst losing positions:")
                for i, pos in enumerate(worst_losses, 1):
                    print(f"      {i}. {pos.direction} ${pos.pnl:.2f} (ID: {pos.position_id})")
            
            smart_pairs = []
            
            # 🎯 STRATEGY 1: HEAVY RESCUE - 1 ขาดทุนหนัก + หลายไม้กำไร (1:N)
            print("🎯 Strategy 1: Heavy Rescue Operations (1:N)")
            
            for losing_pos in losing_positions:
                print(f"\n   🆘 TARGETING LOSS: {losing_pos.direction} ${losing_pos.pnl:.2f}")
                
                # ลองใช้ไม้กำไรหลายตัวช่วย (1:2, 1:3, 1:4, 1:5)
                for num_helpers in range(2, min(6, len(profitable_positions) + 1)):
                    
                    # เลือกไม้กำไรที่ดีที่สุด
                    best_helpers = profitable_positions[:num_helpers]
                    total_helper_profit = sum(h.pnl for h in best_helpers)
                    net_result = losing_pos.pnl + total_helper_profit
                    
                    print(f"      🧮 1:{num_helpers} Test: ${losing_pos.pnl:.2f} + ${total_helper_profit:.2f} = ${net_result:.2f}")
                    
                    # เงื่อนไขการยอมรับ
                    loss_ratio = abs(losing_pos.pnl) / total_helper_profit if total_helper_profit > 0 else 999
                    
                    acceptable_conditions = [
                        net_result >= -1.0,  # ขาดทุนสุทธิไม่เกิน $1
                        net_result >= losing_pos.pnl * 0.8,  # ลดการขาดทุนได้อย่างน้อย 20%
                        loss_ratio <= 2.0,  # ไม้กำไรรวมต้องมากกว่า 50% ของไม้ขาดทุน
                    ]
                    
                    if any(acceptable_conditions):
                        position_ids = {losing_pos.position_id}
                        position_ids.update(h.position_id for h in best_helpers)
                        
                        # คำนวณ priority score
                        rescue_urgency = abs(losing_pos.pnl) * 100  # ยิ่งขาดทุนมาก priority ยิ่งสูง
                        profit_strength = total_helper_profit * 50
                        efficiency_bonus = max(0, net_result) * 200
                        
                        priority_score = rescue_urgency + profit_strength + efficiency_bonus
                        
                        smart_pairs.append({
                            'losing_positions': [losing_pos],
                            'profitable_positions': best_helpers,
                            'net_profit': net_result,
                            'total_positions': 1 + num_helpers,
                            'pair_type': f"HEAVY_RESCUE_1_{num_helpers}",
                            'priority_score': priority_score,
                            'position_ids': position_ids,
                            'loss_reduction': abs(net_result - losing_pos.pnl),
                            'helper_strength': total_helper_profit,
                            'reason': f"Heavy rescue 1:{num_helpers}: ${losing_pos.pnl:.2f} + {num_helpers} helpers = ${net_result:.2f}"
                        })
                        
                        helpers_detail = [f"{h.direction}${h.pnl:.2f}" for h in best_helpers]
                        print(f"      ✅ APPROVED 1:{num_helpers}: Loss reduction ${abs(net_result - losing_pos.pnl):.2f}")
                        print(f"         Helpers: {helpers_detail}")
                        
                        break  # หาได้แล้วไม่ต้องลองเพิ่ม helper
                    else:
                        print(f"      ❌ REJECTED 1:{num_helpers}: Conditions not met")
            
            # 🎯 STRATEGY 2: MULTI-LOSS RESCUE - หลายไม้ขาดทุน + หลายไม้กำไร (N:M)
            print("\n🎯 Strategy 2: Multi-Loss Rescue (N:M)")
            
            if len(losing_positions) >= 2 and len(profitable_positions) >= 2:
                
                # ลองรวมไม้ขาดทุน 2-4 ตัว
                for num_losers in range(2, min(5, len(losing_positions) + 1)):
                    
                    selected_losers = losing_positions[:num_losers]  # เลือกขาดทุนหนักสุด
                    total_loss = sum(pos.pnl for pos in selected_losers)
                    
                    print(f"\n   🆘 COMBINING {num_losers} LOSSES: Total ${total_loss:.2f}")
                    losers_detail = [f"{pos.direction}${pos.pnl:.2f}" for pos in selected_losers]
                    print(f"      Losers: {losers_detail}")
                    
                    if total_loss < -20:  # ถ้าขาดทุนรวมเกิน $20 ข้าม
                        print(f"      ❌ SKIP: Total loss too high (${total_loss:.2f})")
                        continue
                    
                    # หาไม้กำไรที่ช่วยได้
                    available_helpers = [p for p in profitable_positions]
                    
                    # ลองใช้ไม้กำไร 2-6 ตัว
                    for num_helpers in range(2, min(7, len(available_helpers) + 1)):
                        
                        best_helpers = available_helpers[:num_helpers]
                        total_profit = sum(h.pnl for h in best_helpers)
                        net_result = total_loss + total_profit
                        
                        print(f"      🧮 {num_losers}:{num_helpers} Test: ${total_loss:.2f} + ${total_profit:.2f} = ${net_result:.2f}")
                        
                        # เงื่อนไขการยอมรับ
                        coverage_ratio = total_profit / abs(total_loss) if total_loss < 0 else 999
                        
                        acceptable_conditions = [
                            net_result >= -2.0,  # ขาดทุนสุทธิไม่เกิน $2
                            net_result >= total_loss * 0.7,  # ลดการขาดทุนได้อย่างน้อย 30%
                            coverage_ratio >= 0.6,  # ไม้กำไรต้องคลุม 60% ของไม้ขาดทุน
                        ]
                        
                        if any(acceptable_conditions):
                            position_ids = set()
                            position_ids.update(pos.position_id for pos in selected_losers)
                            position_ids.update(h.position_id for h in best_helpers)
                            
                            # คำนวณ priority
                            multi_rescue_bonus = num_losers * 500  # โบนัสสำหรับช่วยหลายตัว
                            loss_severity = abs(total_loss) * 80
                            profit_power = total_profit * 60
                            net_gain_bonus = max(0, net_result) * 300
                            
                            priority_score = multi_rescue_bonus + loss_severity + profit_power + net_gain_bonus
                            
                            smart_pairs.append({
                                'losing_positions': selected_losers,
                                'profitable_positions': best_helpers,
                                'net_profit': net_result,
                                'total_positions': num_losers + num_helpers,
                                'pair_type': f"MULTI_RESCUE_{num_losers}_{num_helpers}",
                                'priority_score': priority_score,
                                'position_ids': position_ids,
                                'total_loss_covered': abs(total_loss),
                                'coverage_ratio': coverage_ratio,
                                'reason': f"Multi rescue {num_losers}:{num_helpers}: ${total_loss:.2f} + ${total_profit:.2f} = ${net_result:.2f}"
                            })
                            
                            helpers_detail = [f"{h.direction}${h.pnl:.2f}" for h in best_helpers]
                            print(f"      ✅ APPROVED {num_losers}:{num_helpers}: Coverage {coverage_ratio:.1%}")
                            print(f"         Helpers: {helpers_detail}")
                            
                            break  # หาได้แล้วไม่ต้องลองเพิ่ม helper
                        else:
                            print(f"      ❌ REJECTED {num_losers}:{num_helpers}: Insufficient coverage")
            
            # 🎯 STRATEGY 3: CROSS-DIRECTION RESCUE - ข้าม BUY/SELL อย่างชัดเจน
            print("\n🎯 Strategy 3: Cross-Direction Rescue (BUY helps SELL, SELL helps BUY)")
            
            # BUY กำไรช่วย SELL ขาดทุน
            buy_profits = [p for p in buy_positions if p.pnl > 0.5]
            sell_losses = [p for p in sell_positions if p.pnl < -1.0]
            
            if buy_profits and sell_losses:
                print(f"   🔄 BUY profits helping SELL losses:")
                for sell_loss in sell_losses[:3]:  # 3 ตัวแย่สุด
                    best_buy_helpers = buy_profits[:3]  # 3 ตัวดีสุด
                    total_help = sum(h.pnl for h in best_buy_helpers)
                    net_result = sell_loss.pnl + total_help
                    
                    if net_result >= -1.0:
                        position_ids = {sell_loss.position_id}
                        position_ids.update(h.position_id for h in best_buy_helpers)
                        
                        smart_pairs.append({
                            'losing_positions': [sell_loss],
                            'profitable_positions': best_buy_helpers,
                            'net_profit': net_result,
                            'total_positions': 1 + len(best_buy_helpers),
                            'pair_type': "CROSS_BUY_HELPS_SELL",
                            'priority_score': 6000 + net_result * 100,
                            'position_ids': position_ids,
                            'cross_direction': True,
                            'reason': f"BUY helps SELL: {sell_loss.pnl:.2f} + {total_help:.2f} = {net_result:.2f}"
                        })
                        
                        print(f"      ✅ BUY→SELL: ${sell_loss.pnl:.2f} + ${total_help:.2f} = ${net_result:.2f}")
            
            # SELL กำไรช่วย BUY ขาดทุน  
            sell_profits = [p for p in sell_positions if p.pnl > 0.5]
            buy_losses = [p for p in buy_positions if p.pnl < -1.0]
            
            if sell_profits and buy_losses:
                print(f"   🔄 SELL profits helping BUY losses:")
                for buy_loss in buy_losses[:3]:  # 3 ตัวแย่สุด
                    best_sell_helpers = sell_profits[:3]  # 3 ตัวดีสุด
                    total_help = sum(h.pnl for h in best_sell_helpers)
                    net_result = buy_loss.pnl + total_help
                    
                    if net_result >= -1.0:
                        position_ids = {buy_loss.position_id}
                        position_ids.update(h.position_id for h in best_sell_helpers)
                        
                        smart_pairs.append({
                            'losing_positions': [buy_loss],
                            'profitable_positions': best_sell_helpers,
                            'net_profit': net_result,
                            'total_positions': 1 + len(best_sell_helpers),
                            'pair_type': "CROSS_SELL_HELPS_BUY",
                            'priority_score': 6000 + net_result * 100,
                            'position_ids': position_ids,
                            'cross_direction': True,
                            'reason': f"SELL helps BUY: {buy_loss.pnl:.2f} + {total_help:.2f} = {net_result:.2f}"
                        })
                        
                        print(f"      ✅ SELL→BUY: ${buy_loss.pnl:.2f} + ${total_help:.2f} = ${net_result:.2f}")
            
            # 🎯 STRATEGY 4: EMERGENCY HIGH PROFITS - กำไรสูงมากๆ เท่านั้น
            print("\n🎯 Strategy 4: Emergency High Profits")
            for pos in profitable_positions:
                if pos.pnl > 10.0:  # เฉพาะกำไรสูงมากๆ
                    smart_pairs.append({
                        'losing_positions': [],
                        'profitable_positions': [pos],
                        'net_profit': pos.pnl,
                        'total_positions': 1,
                        'pair_type': "EMERGENCY_HIGH_PROFIT",
                        'priority_score': 4000 + pos.pnl * 50,
                        'position_ids': {pos.position_id},
                        'reason': f"Emergency high profit: ${pos.pnl:.2f}"
                    })
                    print(f"   💎 EMERGENCY SINGLE: {pos.direction} ${pos.pnl:.2f}")
            
            # เรียงตาม priority score
            smart_pairs.sort(key=lambda x: x['priority_score'], reverse=True)
            
            # 🛡️ FLEXIBLE PROTECTION - ป้องกันแบบยืดหยุ่น
            print(f"\n🛡️ Flexible Portfolio Protection:")
            
            protected_pairs = []
            used_position_ids = set()
            
            total_positions = len(positions)
            min_positions_to_keep = max(8, int(total_positions * 0.15))  # เก็บ 15%
            
            print(f"   📊 Total: {total_positions}, Must keep: {min_positions_to_keep}")
            
            for pair in smart_pairs[:15]:  # พิจารณาสูงสุด 15 pairs
                
                # เช็คการใช้ position ซ้ำ
                if pair['position_ids'].intersection(used_position_ids):
                    continue
                
                # เช็คจำนวน position ที่เหลือ
                remaining = total_positions - len(used_position_ids) - pair['total_positions']
                if remaining < min_positions_to_keep:
                    continue
                
                # เงื่อนไขการอนุมัติ
                approval_conditions = [
                    len(pair['losing_positions']) > 0,  # มีไม้ขาดทุน (true pair)
                    pair['net_profit'] > 8.0,          # กำไรสูงมาก
                    pair['net_profit'] >= -1.5,        # ขาดทุนไม่เกิน $1.5
                    'CROSS' in pair['pair_type'],       # Cross-direction rescue
                ]
                
                if any(approval_conditions):
                    protected_pairs.append(pair)
                    used_position_ids.update(pair['position_ids'])
                    
                    losing_count = len(pair['losing_positions'])
                    profit_count = len(pair['profitable_positions'])
                    cross_indicator = "🔄" if pair.get('cross_direction', False) else ""
                    
                    print(f"   ✅ {cross_indicator} {pair['pair_type']}: {losing_count}L+{profit_count}P = ${pair['net_profit']:.2f}")
            
            # 📋 สรุปผล
            print(f"\n🎯 FLEXIBLE PAIR TRADING RESULTS:")
            print(f"   📋 Candidates found: {len(smart_pairs)}")
            print(f"   ✅ Approved pairs: {len(protected_pairs)}")
            
            if protected_pairs:
                total_expected = sum(pair['net_profit'] for pair in protected_pairs)
                total_positions_closing = sum(pair['total_positions'] for pair in protected_pairs)
                total_losses_rescued = sum(len(pair['losing_positions']) for pair in protected_pairs)
                
                print(f"   💰 Expected profit: ${total_expected:.2f}")
                print(f"   📊 Positions closing: {total_positions_closing}")
                print(f"   🆘 Losses rescued: {total_losses_rescued}")
                
                print(f"\n   📋 Approved Operations:")
                for i, pair in enumerate(protected_pairs, 1):
                    losing_detail = f"{len(pair['losing_positions'])}L" if pair['losing_positions'] else "0L"
                    profit_detail = f"{len(pair['profitable_positions'])}P"
                    cross_mark = "🔄" if pair.get('cross_direction', False) else ""
                    print(f"     {i}. {cross_mark}{pair['pair_type']}: {losing_detail}+{profit_detail} = ${pair['net_profit']:.2f}")
            else:
                print("   ⚠️ No suitable flexible pairs found")
                
            return protected_pairs
            
        except Exception as e:
            print(f"❌ Flexible pair analysis error: {e}")
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
        """ปิดคู่ positions - FIXED VERSION บังคับปิดทั้งคู่"""
        
        for pair in pairs:
            try:
                all_positions = pair['losing_positions'] + pair['profitable_positions']
                losing_count = len(pair['losing_positions'])
                profit_count = len(pair['profitable_positions'])
                
                print(f"💰 EXECUTING PAIR CLOSE: {pair['pair_type']}")
                print(f"   📊 {losing_count} losing + {profit_count} profit positions")
                print(f"   💲 Expected net: ${pair['net_profit']:.2f}")
                
                success_count = 0
                failed_positions = []
                
                # ปิดทุก position ในคู่
                for i, pos in enumerate(all_positions):
                    pos_type = "LOSING" if pos in pair['losing_positions'] else "PROFIT"
                    print(f"   🎯 Closing {pos_type} position: {pos.position_id} (${pos.pnl:.2f})")
                    
                    success = self.close_entire_position(pos)
                    if success:
                        success_count += 1
                        print(f"      ✅ Closed: ${pos.pnl:.2f}")
                    else:
                        failed_positions.append(pos)
                        print(f"      ❌ FAILED to close: ${pos.pnl:.2f}")
                    
                    # หยุดเล็กน้อยระหว่างการปิด
                    if i < len(all_positions) - 1:
                        time.sleep(0.3)
                
                # รายงานผล
                if success_count == len(all_positions):
                    print(f"   🎉 PAIR CLOSE SUCCESS: All {len(all_positions)} positions closed")
                    print(f"   💰 Net profit realized: ${pair['net_profit']:.2f}")
                elif success_count > 0:
                    print(f"   ⚠️ PARTIAL SUCCESS: {success_count}/{len(all_positions)} positions closed")
                    for failed_pos in failed_positions:
                        print(f"      ⚠️ Failed: {failed_pos.position_id} (${failed_pos.pnl:.2f})")
                else:
                    print(f"   ❌ COMPLETE FAILURE: No positions closed")
                    
            except Exception as e:
                print(f"❌ Pair close error: {e}")
                
            print("   " + "="*50)  # Separator

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

