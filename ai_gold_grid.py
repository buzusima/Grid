"""
AI Gold Grid Trading Engine - Smart Profit Integration Version
ai_gold_grid.py
Intelligent grid trading system with full Smart Profit Manager integration
"""

import MetaTrader5 as mt5
import math
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import threading
import json
import os
import random 

try:
    from smart_profit_manager import SmartProfitManager
    SMART_PROFIT_AVAILABLE = True
    print("✅ Smart Profit Manager imported successfully")
except ImportError as e:
    print(f"⚠️ Smart Profit Manager not available: {e}")
    SMART_PROFIT_AVAILABLE = False

class GridDirection(Enum):
    BUY_GRID = "BUY_GRID"
    SELL_GRID = "SELL_GRID"
    BIDIRECTIONAL = "BIDIRECTIONAL"

class PositionStatus(Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class TradingMode(Enum):
    CONSERVATIVE = "CONSERVATIVE"
    STANDARD = "STANDARD"
    AGGRESSIVE = "AGGRESSIVE"

@dataclass
class GridLevel:
    level_id: str
    price: float
    lot_size: float
    direction: str  # "BUY" or "SELL"
    status: PositionStatus
    order_id: Optional[int] = None
    position_id: Optional[int] = None
    entry_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    pnl: float = 0.0

class AIGoldGrid:
    def __init__(self, mt5_connector, survivability_params: Dict, config: Dict):
        self.mt5_connector = mt5_connector
        self.survivability_params = survivability_params
        self.config = config
                
        # Trading parameters from survivability engine
        self.base_lot = survivability_params['base_lot']
        self.grid_spacing = survivability_params['grid_spacing']
        self.max_levels = survivability_params['max_levels']
        self.survivability = survivability_params.get('realistic_survivability', survivability_params['survivability'])
        
        # Gold symbol info
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
        
        # Initialize AI Smart Profit Manager - เป็นหลัก
        if SMART_PROFIT_AVAILABLE:
            try:
                self.smart_profit_manager = SmartProfitManager(self, config)
                self.smart_profit_enabled = True
                self.ai_control_mode = True  # AI เป็นคนควบคุมหลัก
                self.last_profit_check = datetime.now()
                
                print("🧠 AI SMART PROFIT: Full control mode activated")
                print("   🎯 Grid decisions: AI-powered")
                print("   💰 Profit management: AI-optimized") 
                print("   🛡️ Risk management: AI-protected")
                print("   ⚡ Mode: Intelligent automation")
                
            except Exception as e:
                print(f"❌ Smart Profit Manager init error: {e}")
                self.smart_profit_enabled = False
                self.ai_control_mode = False
        else:
            self.smart_profit_enabled = False
            self.ai_control_mode = False
            print("⚠️ Running in basic grid mode - Smart Profit unavailable")
        
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
        
        # Detection and auto-config
        self.detect_broker_filling_modes()
        
        print(f"🤖 AI Gold Grid initialized for {self.gold_symbol}")
        print(f"   🎯 Base Lot: {self.base_lot}")
        print(f"   📏 Grid Spacing: {self.grid_spacing} points")
        print(f"   📊 Max Levels: {self.max_levels}")
        print(f"   🛡️ Survivability: {self.survivability:,.0f} points")
        print(f"   🧠 AI Control: {'ENABLED' if self.ai_control_mode else 'DISABLED'}")
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
            
            if self.smart_profit_enabled and self.ai_control_mode:
                print("🚀 ACTIVATING FULL AI CONTROL MODE")
                print("   🧠 Smart Profit Manager: PRIMARY CONTROL")
                print("   🎯 Grid System: AI-GUIDED SUPPORT")
                print("   💰 All decisions: AI-OPTIMIZED")
                
                self.trading_active = True
                
                # Start AI management as primary
                self.start_ai_management_loop()
                
                # Start support monitoring
                self.start_support_monitoring()
                
                print("✅ AI Smart Profit System FULLY OPERATIONAL!")
                print(f"📊 Configuration:")
                print(f"   • AI Control: FULL CONTROL")
                print(f"   • Base Lot: {self.base_lot}")
                print(f"   • Grid Spacing: {self.grid_spacing} points")
                print(f"   • Survivability: {self.survivability:,} points")
                print(f"   • Magic Number: {self.magic_number}")
                
                return True
            else:
                # Fallback to basic grid
                print("⚠️ Smart Profit unavailable - Starting basic grid mode")
                return self.start_basic_grid_trading()
                
        except Exception as e:
            print(f"❌ Failed to start AI trading: {e}")
            self.trading_active = False
            return False

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
                if self.smart_profit_enabled:
                    # ✅ หลัก: Smart Profit ทำงานเต็มที่
                    self.smart_profit_manager.run_smart_profit_management()
                    
                    # ✅ เพิ่ม: AI Portfolio Health Check
                    self.ai_portfolio_health_check()
                    
                    # ✅ เพิ่ม: AI Performance Optimization
                    if hasattr(self, 'last_optimization') and (datetime.now() - self.last_optimization).total_seconds() > 300:  # ทุก 5 นาที
                        self.ai_performance_optimization()
                        self.last_optimization = datetime.now()
                    elif not hasattr(self, 'last_optimization'):
                        self.last_optimization = datetime.now()
                    
                    # เช็คทุก 3 วินาที - AI ทำงานถี่
                    time.sleep(3)
                else:
                    # Fallback mode
                    time.sleep(10)
                    
            except Exception as e:
                print(f"❌ AI Management error: {e}")
                time.sleep(5)
                
        print("🛑 AI Management stopped")

    def ai_portfolio_health_check(self):
        """AI ตรวจสอบสุขภาพ portfolio"""
        try:
            if hasattr(self, 'smart_profit_manager'):
                portfolio = self.smart_profit_manager.analyze_portfolio_positions()
                
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
            if hasattr(self, 'smart_profit_manager'):
                print("🧠 AI OPTIMIZATION: Analyzing performance...")
                
                # รัน optimization ใน Smart Profit Manager
                opportunities = self.smart_profit_manager.identify_profit_opportunities()
                
                if opportunities:
                    print(f"💡 AI found {len(opportunities)} optimization opportunities")
                else:
                    print("✅ AI: Portfolio optimally configured")
                    
        except Exception as e:
            print(f"❌ AI Optimization error: {e}")

    def start_support_monitoring(self):
        """Start support monitoring thread"""
        if not hasattr(self, 'support_thread') or not self.support_thread.is_alive():
            self.support_thread = threading.Thread(target=self.support_monitoring_loop, daemon=True)
            self.support_thread.start()
            print("📊 Support Monitor started")

    def support_monitoring_loop(self):
        """Support monitoring - เสริม AI หลัก"""
        print("📊 AI Support Monitor active...")
        
        while self.trading_active and not self.emergency_stop_triggered:
            try:
                if self.smart_profit_enabled and self.ai_control_mode:
                    # AI เป็นหลัก - monitor แค่สนับสนุน
                    self.support_ai_operations()
                else:
                    # Fallback เป็น manual grid
                    self.manual_grid_operations()
                    
                time.sleep(10)  # เช็คช้าลง เพราะ AI จัดการแล้ว
                
            except Exception as e:
                print(f"❌ Support Monitor error: {e}")
                time.sleep(15)
                
        print("🛑 Support Monitor stopped")

    def support_ai_operations(self):
        """สนับสนุนการทำงานของ AI"""
        try:
            # อัพเดทข้อมูลให้ AI
            self.update_positions_for_ai()
            
            # เช็ค emergency conditions (แต่ให้ AI รู้)
            emergency_level = self.check_emergency_level()
            if emergency_level > 0:
                if hasattr(self, 'smart_profit_manager'):
                    print(f"⚠️ Emergency Level {emergency_level} - AI notified")
                    
            # อัพเดท statistics
            self.update_trading_statistics()
                    
        except Exception as e:
            print(f"❌ AI Support error: {e}")

    def update_positions_for_ai(self):
        """อัพเดทข้อมูล positions ให้ AI ใช้"""
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            
            if positions:
                # อัพเดท active_positions ให้ AI
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
                            'time_open': datetime.fromtimestamp(position.time)
                        }
                        total_pnl += position.profit
                
                self.active_positions = current_positions
                self.total_pnl = total_pnl
                self.unrealized_pnl = total_pnl
                
        except Exception as e:
            print(f"❌ Position update error: {e}")

    def check_emergency_level(self) -> int:
        """ตรวจสอบระดับฉุกเฉิน (0=ปกติ, 1=เตือน, 2=อันตราย, 3=วิกฤติ)"""
        try:
            emergency_level = 0
            
            # เช็ค drawdown
            current_drawdown = self.get_current_drawdown()
            if current_drawdown > self.survivability * 0.8:
                emergency_level = 3  # วิกฤติ
            elif current_drawdown > self.survivability * 0.6:
                emergency_level = 2  # อันตราย
            elif current_drawdown > self.survivability * 0.4:
                emergency_level = 1  # เตือน
                
            # เช็ค margin level
            account_info = self.mt5_connector.get_account_info() if self.mt5_connector else None
            if account_info:
                margin_level = account_info.get('margin_level', 100)
                margin = account_info.get('margin', 0)
                
                if margin > 0:  # มี positions เปิดอยู่
                    if margin_level < 100:
                        emergency_level = max(emergency_level, 3)
                    elif margin_level < 150:
                        emergency_level = max(emergency_level, 2)
                    elif margin_level < 200:
                        emergency_level = max(emergency_level, 1)
                        
            return emergency_level
            
        except Exception as e:
            print(f"❌ Emergency level check error: {e}")
            return 0

    def manual_grid_operations(self):
        """Fallback manual grid operations"""
        try:
            # Basic grid maintenance
            self.check_pending_orders()
            self.monitor_active_positions()
            self.maintain_basic_grid_coverage()
            
        except Exception as e:
            print(f"❌ Manual grid error: {e}")

    def start_basic_grid_trading(self):
        """Fallback basic grid trading"""
        try:
            print("🔄 Starting basic grid mode...")
            
            # Initialize basic grid
            self.trading_active = True
            grid_initialized = self.initialize_basic_grid()
            
            if grid_initialized:
                self.start_support_monitoring()
                print("✅ Basic grid trading started")
                return True
            else:
                print("❌ Failed to initialize basic grid")
                self.trading_active = False
                return False
                
        except Exception as e:
            print(f"❌ Basic grid start error: {e}")
            return False

    def initialize_basic_grid(self):
        """Initialize basic grid system"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                return False
                
            self.starting_price = current_price
            spacing_dollars = self.grid_spacing * 0.01
            
            # Create basic grid levels
            orders_placed = 0
            
            # BUY orders below market
            for i in range(1, 4):
                buy_price = current_price - (spacing_dollars * i)
                if self.place_pending_order(buy_price, 'BUY', self.base_lot):
                    orders_placed += 1
                    
            # SELL orders above market  
            for i in range(1, 4):
                sell_price = current_price + (spacing_dollars * i)
                if self.place_pending_order(sell_price, 'SELL', self.base_lot):
                    orders_placed += 1
                    
            print(f"✅ Basic grid initialized: {orders_placed} orders placed")
            return orders_placed > 0
            
        except Exception as e:
            print(f"❌ Basic grid init error: {e}")
            return False

    def place_pending_order(self, price: float, direction: str, lot_size: float):
        """Place a single pending order"""
        try:
            if direction == "BUY":
                order_type = mt5.ORDER_TYPE_BUY_STOP if price > self.get_current_price() else mt5.ORDER_TYPE_BUY_LIMIT
            else:
                order_type = mt5.ORDER_TYPE_SELL_STOP if price < self.get_current_price() else mt5.ORDER_TYPE_SELL_LIMIT
                
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": self.gold_symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "magic": self.magic_number,
                "comment": f"AI_GRID_{direction}",
                "type_filling": self.order_filling_mode
            }
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.pending_orders[result.order] = {
                    'order_id': result.order,
                    'price': price,
                    'direction': direction,
                    'lot_size': lot_size,
                    'time': datetime.now()
                }
                return True
            else:
                print(f"❌ Order failed: {result.comment if result else 'No response'}")
                return False
                
        except Exception as e:
            print(f"❌ Place order error: {e}")
            return False

    def validate_account_before_trading(self):
        """Validate account before starting"""
        try:
            account_info = self.mt5_connector.get_account_info() if self.mt5_connector else None
            
            if not account_info:
                print("❌ Cannot validate account - Missing account info")
                return False
                
            balance = account_info.get('balance', 0)
            equity = account_info.get('equity', 0)
            free_margin = account_info.get('margin_free', 0)
            
            print(f"✅ Account Validation:")
            print(f"   Balance: ${balance:,.2f}")
            print(f"   Equity: ${equity:,.2f}")
            print(f"   Free Margin: ${free_margin:,.2f}")
            
            if balance < 100:
                print(f"❌ Insufficient balance: ${balance:.2f}")
                return False
                
            if free_margin < balance * 0.3:
                print(f"❌ Low free margin: ${free_margin:.2f}")
                return False
                
            print(f"✅ Account validation passed - Ready for AI trading")
            return True
            
        except Exception as e:
            print(f"❌ Account validation error: {e}")
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

    def check_pending_orders(self):
        """Check for filled pending orders"""
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            if positions is None:
                return
                
            for position in positions:
                if position.magic != self.magic_number:
                    continue
                    
                position_id = position.ticket
                
                if position_id not in self.active_positions:
                    self.handle_new_position(position)
                    
        except Exception as e:
            print(f"❌ Error checking pending orders: {e}")

    def handle_new_position(self, position):
        """Handle new position"""
        try:
            print(f"🎯 NEW POSITION: {position.ticket} | {'BUY' if position.type == mt5.POSITION_TYPE_BUY else 'SELL'} | {position.volume} | ${position.price_open:.2f}")
            
            self.active_positions[position.ticket] = {
                'ticket': position.ticket,
                'type': position.type,
                'volume': position.volume,
                'price_open': position.price_open,
                'profit': position.profit,
                'symbol': position.symbol,
                'time_open': datetime.fromtimestamp(position.time)
            }
            
            self.trades_opened += 1
            
            # Remove corresponding pending order
            self.remove_filled_pending_order(position)
            
        except Exception as e:
            print(f"❌ Error handling new position: {e}")

    def remove_filled_pending_order(self, position):
        """Remove filled pending order"""
        try:
            position_price = position.price_open
            position_type = 'BUY' if position.type == mt5.POSITION_TYPE_BUY else 'SELL'
            
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

    def monitor_active_positions(self):
        """Monitor active positions"""
        try:
            total_pnl = 0
            
            for ticket, pos_info in list(self.active_positions.items()):
                positions = mt5.positions_get(ticket=ticket)
                
                if positions is None or len(positions) == 0:
                    self.handle_closed_position(ticket)
                    continue
                    
                position = positions[0]
                pos_info['profit'] = position.profit
                total_pnl += position.profit
                
            self.total_pnl = total_pnl
            self.unrealized_pnl = total_pnl
            
            self.update_drawdown()
            
        except Exception as e:
            print(f"❌ Error monitoring positions: {e}")

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
                del self.active_positions[ticket]
                
                if self.trades_closed > 0:
                    self.win_rate = self.winning_trades / self.trades_closed
                    
        except Exception as e:
            print(f"❌ Error handling closed position: {e}")

    def maintain_basic_grid_coverage(self):
        """Maintain basic grid coverage"""
        try:
            if len(self.pending_orders) < 4:
                print(f"🔧 Grid maintenance: Adding orders (current: {len(self.pending_orders)})")
                self.place_additional_basic_orders()
                
        except Exception as e:
            print(f"❌ Error maintaining grid: {e}")

    def place_additional_basic_orders(self):
        """Place additional basic orders"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                return
                
            spacing_dollars = self.grid_spacing * 0.01
            
            # Check and place BUY orders
            for i in range(1, 3):
                buy_price = current_price - (spacing_dollars * i)
                if not self.has_order_near_price(buy_price, 'BUY'):
                    self.place_pending_order(buy_price, 'BUY', self.base_lot)
                    
            # Check and place SELL orders
            for i in range(1, 3):
                sell_price = current_price + (spacing_dollars * i)
                if not self.has_order_near_price(sell_price, 'SELL'):
                    self.place_pending_order(sell_price, 'SELL', self.base_lot)
                    
        except Exception as e:
            print(f"❌ Error placing additional orders: {e}")

    def has_order_near_price(self, target_price, direction):
        """Check if there's an order near this price"""
        tolerance = 0.25
        
        for order_info in self.pending_orders.values():
            if (order_info['direction'] == direction and 
                abs(order_info['price'] - target_price) < tolerance):
                return True
        return False

    def update_drawdown(self):
        """Update drawdown calculation"""
        try:
            current_drawdown = self.get_current_drawdown()
            
            max_allowed_drawdown = self.survivability * 0.8
            
            if current_drawdown > max_allowed_drawdown:
                print(f"🚨 WARNING: High drawdown detected!")
                print(f"   Current: {current_drawdown:,.0f} points")
                print(f"   Max allowed: {max_allowed_drawdown:,.0f} points")
                print(f"   Survivability used: {(current_drawdown/self.survivability)*100:.1f}%")
                
            return current_drawdown
            
        except Exception as e:
            print(f"❌ Error updating drawdown: {e}")
            return 0

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
                if self.smart_profit_enabled:
                    print(f"🧠 AI STATS: {len(self.active_positions)} pos | ${self.total_pnl:.2f} PnL | {len(self.pending_orders)} pending")
                else:
                    print(f"📊 BASIC STATS: {len(self.active_positions)} pos | ${self.total_pnl:.2f} PnL | {len(self.pending_orders)} pending")
                self.last_stats_log = datetime.now()
                
        except Exception as e:
            print(f"❌ Error updating statistics: {e}")

    def stop_trading(self):
        """Stop the trading system"""
        try:
            print("🛑 AI Trading System Stopping...")
            
            self.trading_active = False
            
            if hasattr(self, 'ai_thread') and self.ai_thread.is_alive():
                print("   🧠 Stopping AI Management...")
                
            if hasattr(self, 'support_thread') and self.support_thread.is_alive():
                print("   📊 Stopping Support Monitor...")
                
            # Final statistics
            final_stats = self.get_final_statistics()
            print("📊 FINAL STATISTICS:")
            print(f"   💰 Total PnL: ${final_stats['total_pnl']:.2f}")
            print(f"   📈 Trades: {final_stats['trades_opened']} opened, {final_stats['trades_closed']} closed")
            print(f"   🎯 Win Rate: {final_stats['win_rate']:.1f}%")
            print(f"   🛡️ Max Drawdown: {final_stats['max_drawdown']:,.0f} points")
            
            print("✅ AI Trading System Stopped Successfully")
            
        except Exception as e:
            print(f"❌ Error stopping trading: {e}")

    def emergency_stop(self):
        """Emergency stop with full cleanup"""
        try:
            print("🚨 EMERGENCY STOP TRIGGERED!")
            
            self.emergency_stop_triggered = True
            self.trading_active = False
            
            # Emergency close all positions
            self.emergency_close_all_positions()
            
            # Cancel all pending orders
            self.cancel_all_pending_orders()
            
            print("🚨 Emergency stop completed")
            
        except Exception as e:
            print(f"❌ Emergency stop error: {e}")

    def emergency_close_all_positions(self):
        """Emergency close all positions"""
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
        """Cancel all pending orders"""
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

    def get_grid_status(self):
        """Get comprehensive grid status"""
        try:
            base_status = {
                'trading_active': self.trading_active,
                'gold_symbol': self.gold_symbol,
                'current_price': self.get_current_price(),
                'starting_price': getattr(self, 'starting_price', 0),
                'total_pnl': round(self.total_pnl, 2),
                'unrealized_pnl': round(self.unrealized_pnl, 2),
                'realized_pnl': round(self.realized_pnl, 2),
                'current_drawdown': round(self.current_drawdown, 0),
                'max_drawdown': round(self.max_drawdown_points, 0),
                'active_positions': len(self.active_positions),
                'pending_orders': len(self.pending_orders),
                'total_grid_levels': len(self.grid_levels),
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
                'ai_control_mode': getattr(self, 'ai_control_mode', False),
                'smart_profit_enabled': getattr(self, 'smart_profit_enabled', False)
            }
            
            # Add Smart Profit status
            if (hasattr(self, 'smart_profit_enabled') and self.smart_profit_enabled and
                hasattr(self, 'smart_profit_manager')):
                try:
                    smart_status = self.smart_profit_manager.get_profit_management_status()
                    base_status['smart_profit_status'] = smart_status
                    
                    recovery_status = self.smart_profit_manager.get_recovery_status()
                    base_status['recovery_system'] = recovery_status
                    
                    ai_health = self.calculate_ai_health_score({'total_pnl': self.total_pnl, 'total_positions': len(self.active_positions)})
                    base_status['ai_health_score'] = ai_health
                    
                except Exception as smart_error:
                    base_status['smart_profit_status'] = {'error': str(smart_error)}
                    base_status['recovery_system'] = {'enabled': False, 'active': False}
                    base_status['ai_health_score'] = 50
            else:
                base_status['smart_profit_status'] = {'enabled': False}
                base_status['recovery_system'] = {'enabled': False, 'active': False}
                base_status['ai_health_score'] = 50
                
            return base_status
            
        except Exception as e:
            print(f"❌ Error getting grid status: {e}")
            return {'error': str(e)}

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
                'ai_control_enabled': getattr(self, 'ai_control_mode', False),
                'smart_profit_enabled': getattr(self, 'smart_profit_enabled', False)
            }
            
        except Exception as e:
            print(f"❌ Error getting final statistics: {e}")
            return {}

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
                print("🛑 AI Grid system cleanup - stopping trading")
                self.stop_trading()
        except:
            pass

# Test function for AI Smart Profit mode
def test_ai_smart_profit_mode():
    """Test the AI Smart Profit integration"""
    
    print("🧠 AI SMART PROFIT MODE TEST")
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
        'daily_loss_limit': 500,
        'target_survivability': 20000,
        'portfolio_recovery': {
            'enabled': True,
            'trigger_loss': -50,
            'auto_mode': True
        }
    }
    
    
    print(f"\n📊 Test Parameters:")
    print(f"   AI Control Mode: ENABLED")
    print(f"   Base Lot: {test_params['base_lot']}")
    print(f"   Grid Spacing: {test_params['grid_spacing']} points")
    print(f"   Survivability: {test_params['survivability']:,} points")
    print(f"   Recovery Trigger: ${test_config['portfolio_recovery']['trigger_loss']}")
    
    print("\n" + "="*60)
    print("🚀 Ready for AI SMART PROFIT TRADING!")
    print("🧠 Full AI intelligence activated!")

if __name__ == "__main__":
    test_ai_smart_profit_mode()
