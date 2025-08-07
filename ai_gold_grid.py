"""
AI Gold Grid Trading Engine - Complete Real Trading System
ai_gold_grid.py
Intelligent grid trading system specifically designed for gold (XAUUSD) with AI management
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
        
        # Gold symbol info with error handling
        self.gold_symbol = mt5_connector.get_gold_symbol()
        self.symbol_info = mt5_connector.get_symbol_info()
        
        # Validate symbol info
        if not self.symbol_info or not isinstance(self.symbol_info, dict):
            print("⚠️ Warning: Symbol info not available, using defaults")
            self.symbol_info = {
                'volume_min': 0.01,
                'volume_max': 100.0,
                'volume_step': 0.01,
                'point': 0.01
            }
        
        # Detect broker filling modes
        self.detect_broker_filling_modes()
        
        # Grid state management
        self.grid_levels = []
        self.active_positions = {}
        self.pending_orders = {}
        self.starting_price = 0.0
        self.current_price = 0.0
        self.total_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
        
        # AI trading parameters
        self.trading_active = False
        self.last_update = datetime.now()
        self.update_interval = 1.0  # seconds
        self.price_history = []
        self.volatility_buffer = 50  # points
        
        # Fixed Magic Number based on account (for recovery system)
        account_info = mt5_connector.get_account_info()
        if account_info:
            account_login = str(account_info.get('login', 12345))
            # Create consistent magic number: 777 + last 5 digits of account
            self.magic_number = int(f"777{account_login[-5:]}")
        else:
            self.magic_number = 777888999  # fallback
        
        # Risk management
        self.max_drawdown_points = 0
        self.current_drawdown = 0
        self.emergency_stop_triggered = False
        self.daily_loss_limit = config.get('daily_loss_limit', 500)
        
        # Performance tracking
        self.trades_opened = 0
        self.trades_closed = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.largest_win = 0.0
        self.largest_loss = 0.0
        self.win_rate = 0.0
        self.profit_factor = 0.0
        
        # Get broker constraints with safe defaults
        self.min_lot = self.symbol_info.get('volume_min', 0.01)
        self.lot_step = self.symbol_info.get('volume_step', 0.01)
        self.point_value = self.symbol_info.get('point', 0.01)

        self.near_zone_levels = 5      
        self.medium_zone_levels = 15   
        self.far_zone_levels = 30      
        
        # Target order distribution
        self.calculate_rebalancing_targets()
        
        # Rebalancing control
        self.last_rebalance = datetime.now()
        self.last_cleanup = datetime.now()

        # Initialize Smart Profit Manager
        if SMART_PROFIT_AVAILABLE:
            try:
                self.smart_profit_manager = SmartProfitManager(self, config)
                self.last_profit_check = datetime.now()
                self.smart_profit_enabled = True
                print("🧠 Smart Profit Manager initialized successfully")
            except Exception as e:
                print(f"❌ Smart Profit Manager init error: {e}")
                self.smart_profit_enabled = False
        else:
            self.smart_profit_enabled = False
        
        # print(f"🤖 AI Gold Grid initialized for {self.gold_symbol}")
        # print(f"   🎯 Base Lot: {self.base_lot}")
        # print(f"   📏 Grid Spacing: {self.grid_spacing} points")
        # print(f"   📊 Max Levels: {self.max_levels}")
        # print(f"   🛡️ Realistic Survivability: {self.survivability:,.0f} points")
        # print(f"   ⚙️ Broker Min Lot: {self.min_lot}")
        # print(f"   🔄 Filling Mode: {self.filling_mode_name}")
        # print(f"   🎯 Fixed Magic Number: {self.magic_number} (Account-based)")
# เพิ่มใน class AIGoldGrid หลัง __init__

    def analyze_portfolio_exposure(self) -> Dict:
        """วิเคราะห์ portfolio exposure แบบ real-time"""
        try:
            buy_positions = [pos for pos in self.active_positions.values() if pos.direction == "BUY"]
            sell_positions = [pos for pos in self.active_positions.values() if pos.direction == "SELL"]
            
            buy_exposure = sum(pos.lot_size for pos in buy_positions)
            sell_exposure = sum(pos.lot_size for pos in sell_positions)
            
            balance_ratio = buy_exposure / sell_exposure if sell_exposure > 0 else 999
            
            return {
                'buy_exposure': round(buy_exposure, 3),
                'sell_exposure': round(sell_exposure, 3),
                'net_exposure': round(buy_exposure - sell_exposure, 3),
                'balance_ratio': round(balance_ratio, 2),
                'total_positions': len(self.active_positions),
                'is_balanced': 0.7 <= balance_ratio <= 1.43  # ±30% tolerance
            }
        except Exception as e:
            print(f"❌ Portfolio analysis error: {e}")
            return {}



    def add_strategic_sell_orders(self, current_price: float, imbalance_size: float):
        """เพิ่ม SELL orders เพื่อ balance portfolio"""
        try:
            # คำนวณจำนวน SELL ที่ต้องเพิ่ม
            needed_sell_exposure = abs(imbalance_size) * 0.6  # ปรับ 60%
            
            # Grid spacing ใหม่ (ถี่ขึ้น)
            tight_spacing = 150  # จาก 333 เป็น 150
            
            # วาง SELL orders ในระยะใกล้-กลาง
            levels_to_add = [
                current_price + tight_spacing,
                current_price + tight_spacing * 2,
                current_price + tight_spacing * 3,
            ]
            
            lot_per_level = max(self.min_lot, needed_sell_exposure / len(levels_to_add))
            
            added_count = 0
            for price in levels_to_add:
                if not self.has_nearby_order(price, "SELL") and added_count < 3:
                    if self.place_smart_rebalance_order("SELL", price, lot_per_level):
                        added_count += 1
                        
            print(f"✅ Added {added_count} strategic SELL orders")
            
        except Exception as e:
            print(f"❌ Strategic SELL error: {e}")

    def add_strategic_buy_orders(self, current_price: float, imbalance_size: float):
        """เพิ่ม BUY orders เพื่อ balance portfolio"""
        try:
            needed_buy_exposure = abs(imbalance_size) * 0.6
            tight_spacing = 150
            
            levels_to_add = [
                current_price - tight_spacing,
                current_price - tight_spacing * 2,
                current_price - tight_spacing * 3,
            ]
            
            lot_per_level = max(self.min_lot, needed_buy_exposure / len(levels_to_add))
            
            added_count = 0
            for price in levels_to_add:
                if not self.has_nearby_order(price, "BUY") and added_count < 3:
                    if self.place_smart_rebalance_order("BUY", price, lot_per_level):
                        added_count += 1
                        
            print(f"✅ Added {added_count} strategic BUY orders")
            
        except Exception as e:
            print(f"❌ Strategic BUY error: {e}")

    def add_balanced_grid_orders(self, current_price: float):
        """เพิ่ม orders ทั้งสองด้านแบบสมดุล"""
        try:
            tight_spacing = 150
            lot_size = self.calculate_level_lot_size(1)
            
            # เพิ่ม BUY และ SELL คู่กัน
            buy_price = current_price - tight_spacing
            sell_price = current_price + tight_spacing
            
            if not self.has_nearby_order(buy_price, "BUY"):
                self.place_smart_rebalance_order("BUY", buy_price, lot_size)
                
            if not self.has_nearby_order(sell_price, "SELL"):
                self.place_smart_rebalance_order("SELL", sell_price, lot_size)
                
            print(f"✅ Added balanced grid orders @ ±{tight_spacing}")
            
        except Exception as e:
            print(f"❌ Balanced grid error: {e}")

    def place_smart_rebalance_order(self, direction: str, price: float, lot_size: float) -> bool:
        """วาง order สำหรับ rebalancing - FIXED VERSION with validation"""
        try:
            # ✅ FIX: เพิ่มการตรวจสอบราคาให้สมเหตุสมผล
            current_price = self.get_current_price()
            distance_points = abs(price - current_price) / 0.01
            
            # ตรวจสอบระยะห่างสูงสุด
            max_distance = 1000  # ไม่เกิน 1000 points
            if distance_points > max_distance:
                print(f"   ⚠️ Order too far: {distance_points:.0f} points > limit {max_distance}")
                return False
            
            # ตรวจสอบทิศทางที่ถูกต้อง
            if direction == "BUY" and price >= current_price:
                print(f"   ⚠️ Invalid BUY price: ${price:.2f} >= current ${current_price:.2f}")
                return False
            elif direction == "SELL" and price <= current_price:
                print(f"   ⚠️ Invalid SELL price: ${price:.2f} <= current ${current_price:.2f}")
                return False
            
            # สร้าง grid level
            new_level = GridLevel(
                level_id=f"SMART_{direction}_{int(time.time())}",
                price=round(price, 2),  # ปัดเป็น 2 ทศนิยม
                lot_size=round(lot_size, 3),  # ปัดเป็น 3 ทศนิยม
                direction=direction,
                status=PositionStatus.PENDING,
                entry_time=datetime.now()
            )
            
            # วาง order
            order_result = self.place_pending_order(new_level)
            if order_result:
                new_level.order_id = order_result
                self.grid_levels.append(new_level)
                self.pending_orders[order_result] = new_level
                
                print(f"   🎯 Order placed: {direction} {lot_size:.3f} @ ${price:.2f} ({distance_points:.0f} points)")
                return True
            else:
                print(f"   ❌ Failed to place {direction} order @ ${price:.2f}")
                return False
                    
        except Exception as e:
            print(f"❌ Smart rebalance order error: {e}")
            return False

    # ✅ เพิ่ม method ตรวจสอบระบบ
    def validate_grid_orders(self):
        """ตรวจสอบและแสดงสถานะ orders ปัจจุบัน"""
        try:
            current_price = self.get_current_price()
            print(f"\n📊 === GRID ORDERS VALIDATION ===")
            print(f"💰 Current Price: ${current_price:.2f}")
            
            buy_orders = []
            sell_orders = []
            
            for order_id, grid_level in self.pending_orders.items():
                distance_points = abs(grid_level.price - current_price) / 0.01
                
                order_info = {
                    'id': grid_level.level_id,
                    'price': grid_level.price,
                    'lot': grid_level.lot_size,
                    'distance': distance_points
                }
                
                if grid_level.direction == "BUY":
                    buy_orders.append(order_info)
                else:
                    sell_orders.append(order_info)
            
            print(f"\n📈 BUY ORDERS ({len(buy_orders)}):")
            for order in sorted(buy_orders, key=lambda x: x['distance']):
                status = "✅" if order['distance'] <= 500 else "⚠️"
                print(f"   {status} ${order['price']:.2f} | {order['lot']:.3f} lots | {order['distance']:.0f} points")
            
            print(f"\n📉 SELL ORDERS ({len(sell_orders)}):")
            for order in sorted(sell_orders, key=lambda x: x['distance']):
                status = "✅" if order['distance'] <= 500 else "⚠️"
                print(f"   {status} ${order['price']:.2f} | {order['lot']:.3f} lots | {order['distance']:.0f} points")
                
            # สรุป
            far_orders = len([o for o in buy_orders + sell_orders if o['distance'] > 1000])
            if far_orders > 0:
                print(f"\n⚠️ WARNING: {far_orders} orders are >1000 points away!")
            else:
                print(f"\n✅ All orders within reasonable distance")
                
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"❌ Validation error: {e}")

    # ✅ เพิ่ม method ลบ orders ไกลเกินไป
    def cleanup_far_orders_emergency(self):
        """ลบ orders ที่ไกลเกิน 1000 points ทันที"""
        try:
            current_price = self.get_current_price()
            removed_count = 0
            max_distance = 1000  # 1000 points limit
            
            print(f"🧹 Emergency cleanup: removing orders >1000 points from ${current_price:.2f}")
            
            for order_id, grid_level in list(self.pending_orders.items()):
                distance_points = abs(grid_level.price - current_price) / 0.01
                
                if distance_points > max_distance:
                    if self.cancel_single_order(order_id):
                        del self.pending_orders[order_id]
                        grid_level.status = PositionStatus.CANCELLED
                        removed_count += 1
                        print(f"   🗑️ Removed: {grid_level.level_id} @ ${grid_level.price:.2f} ({distance_points:.0f}pts)")
            
            print(f"✅ Emergency cleanup completed: {removed_count} far orders removed")
            return removed_count
            
        except Exception as e:
            print(f"❌ Emergency cleanup error: {e}")
            return 0
    
    def save_grid_state(self):
        """Save current grid state for recovery"""
        try:
            state = {
                'magic_number': self.magic_number,
                'account_login': self.mt5_connector.get_account_info().get('login') if self.mt5_connector.get_account_info() else None,
                'base_lot': self.base_lot,
                'grid_spacing': self.grid_spacing,
                'max_levels': self.max_levels,
                'starting_price': self.starting_price,
                'survivability': self.survivability,
                'gold_symbol': self.gold_symbol,
                'created_timestamp': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            filename = f"grid_state_{self.magic_number}.json"
            with open(filename, 'w') as f:
                json.dump(state, f, indent=2)
                
            print(f"💾 Grid state saved to {filename}")
            
        except Exception as e:
            print(f"❌ Save state error: {e}")

    def load_grid_state(self) -> bool:
        """Load grid state for recovery"""
        try:
            filename = f"grid_state_{self.magic_number}.json"
            
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    state = json.load(f)
                    
                # Verify it's the same account
                saved_login = state.get('account_login')
                current_account = self.mt5_connector.get_account_info()
                current_login = current_account.get('login') if current_account else None
                
                if saved_login == current_login:
                    print(f"📂 Grid state loaded from {filename}")
                    print(f"🔗 Account verified: {current_login}")
                    return True
                else:
                    print(f"⚠️ Account mismatch: saved={saved_login}, current={current_login}")
                    
        except Exception as e:
            print(f"❌ Load state error: {e}")
            
        return False

    def recover_existing_orders_and_positions(self) -> bool:
        """Recover existing orders and positions after restart"""
        try:
            print("🔄 Scanning MT5 for existing orders/positions...")
            
            recovered_orders = 0
            recovered_positions = 0
            
            # Recover pending orders
            orders = mt5.orders_get(symbol=self.gold_symbol)
            if orders:
                our_orders = [order for order in orders if order.magic == self.magic_number]
                
                for order in our_orders:
                    try:
                        # Determine direction
                        if order.type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP]:
                            direction = "BUY"
                        else:
                            direction = "SELL"
                            
                        # Create grid level from existing order
                        grid_level = GridLevel(
                            level_id=f"RECOVERED_ORD_{order.ticket}",
                            price=order.price_open,
                            lot_size=order.volume_initial,
                            direction=direction,
                            status=PositionStatus.PENDING,
                            order_id=order.ticket,
                            entry_time=datetime.fromtimestamp(order.time_setup) if hasattr(order, 'time_setup') else datetime.now()
                        )
                        
                        self.grid_levels.append(grid_level)
                        self.pending_orders[order.ticket] = grid_level
                        recovered_orders += 1
                        
                        print(f"   📋 Recovered order: {direction} {order.volume_initial:.3f} @ {order.price_open}")
                        
                    except Exception as e:
                        print(f"   ⚠️ Failed to recover order {order.ticket}: {e}")
                        
            # Recover active positions (exclude hedge positions)
            positions = mt5.positions_get(symbol=self.gold_symbol)
            if positions:
                our_positions = [pos for pos in positions 
                            if pos.magic == self.magic_number and "HEDGE" not in pos.comment]
                
                for position in our_positions:
                    try:
                        # Determine direction
                        direction = "BUY" if position.type == mt5.POSITION_TYPE_BUY else "SELL"
                        
                        # Create grid level from existing position
                        grid_level = GridLevel(
                            level_id=f"RECOVERED_POS_{position.ticket}",
                            price=position.price_open,
                            lot_size=position.volume,
                            direction=direction,
                            status=PositionStatus.ACTIVE,
                            position_id=position.ticket,
                            entry_time=datetime.fromtimestamp(position.time) if hasattr(position, 'time') else datetime.now(),
                            pnl=position.profit
                        )
                        
                        self.grid_levels.append(grid_level)
                        self.active_positions[position.ticket] = grid_level
                        recovered_positions += 1
                        
                        print(f"   💼 Recovered position: {direction} {position.volume:.3f} @ {position.price_open} (PnL: ${position.profit:.2f})")
                        
                    except Exception as e:
                        print(f"   ⚠️ Failed to recover position {position.ticket}: {e}")
                        
            # Update current price
            price_data = self.mt5_connector.get_current_price()
            if price_data:
                self.current_price = price_data['bid']
                
                # If no starting price from state, use current
                if not hasattr(self, 'starting_price') or self.starting_price == 0:
                    self.starting_price = self.current_price
                    
            print(f"✅ Recovery completed:")
            print(f"   📋 Orders: {recovered_orders}")
            print(f"   💼 Positions: {recovered_positions}")
            print(f"   💰 Current Price: {self.current_price}")
            
            return recovered_orders > 0 or recovered_positions > 0
            
        except Exception as e:
            print(f"❌ Recovery error: {e}")
            return False

    def clean_orphaned_orders(self):
        """Clean up orders that might be left from old versions"""
        try:
            print("🧹 Checking for orphaned orders...")
            
            # Get all orders for this symbol
            orders = mt5.orders_get(symbol=self.gold_symbol)
            if not orders:
                print("✅ No orders found to clean")
                return
                
            current_time = datetime.now()
            cleaned_count = 0
            
            for order in orders:
                try:
                    # Calculate order age
                    order_time = datetime.fromtimestamp(order.time_setup) if hasattr(order, 'time_setup') else current_time
                    order_age_hours = (current_time - order_time).total_seconds() / 3600
                    
                    # Clean conditions:
                    should_clean = False
                    reason = ""
                    
                    # 1. Old magic numbers (not current account-based format)
                    if order.magic != self.magic_number and str(order.magic).startswith(('999', '777')):
                        should_clean = True
                        reason = f"old magic {order.magic}"
                        
                    # 2. Very old orders (>7 days)
                    elif order_age_hours > 168:  # 7 days
                        should_clean = True
                        reason = f"age {order_age_hours:.1f}h"
                        
                    # 3. Orders with old comment format
                    elif "AIGrid_" in order.comment and order.magic != self.magic_number:
                        should_clean = True
                        reason = f"old version"
                        
                    if should_clean:
                        # Cancel the orphaned order
                        request = {
                            "action": mt5.TRADE_ACTION_REMOVE,
                            "order": order.ticket
                        }
                        
                        result = mt5.order_send(request)
                        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                            cleaned_count += 1
                            print(f"   🗑️ Cleaned order {order.ticket} ({reason})")
                        else:
                            print(f"   ⚠️ Failed to clean order {order.ticket}: {result.comment if result else 'No response'}")
                            
                except Exception as e:
                    print(f"   ⚠️ Error processing order {order.ticket}: {e}")
                    
            if cleaned_count > 0:
                print(f"✅ Cleaned {cleaned_count} orphaned orders")
            else:
                print("✅ No orphaned orders found")
                
        except Exception as e:
            print(f"❌ Cleanup error: {e}")

    def detect_broker_filling_modes(self):
        """Detect and set appropriate filling modes for the broker"""
        
        try:
            # Get account info to detect broker type
            account_info = self.mt5_connector.get_account_info()
            broker_name = account_info.get('company', '').lower() if account_info else ''
            
            # Test different filling modes to see what works
            symbol_info = mt5.symbol_info(self.gold_symbol)
            
            if symbol_info:
                filling_mode = symbol_info.filling_mode
                
                # Analyze filling mode flags
                if filling_mode & 1:  # FOK supported
                    self.order_filling_mode = mt5.ORDER_FILLING_FOK
                    self.close_filling_mode = mt5.ORDER_FILLING_FOK
                    self.filling_mode_name = "FOK (Fill or Kill)"
                elif filling_mode & 2:  # IOC supported  
                    self.order_filling_mode = mt5.ORDER_FILLING_IOC
                    self.close_filling_mode = mt5.ORDER_FILLING_IOC
                    self.filling_mode_name = "IOC (Immediate or Cancel)"
                else:  # Default/Return
                    self.order_filling_mode = mt5.ORDER_FILLING_RETURN
                    self.close_filling_mode = mt5.ORDER_FILLING_RETURN
                    self.filling_mode_name = "RETURN (Partial fills allowed)"
            else:
                # Fallback for unknown symbol
                self.order_filling_mode = mt5.ORDER_FILLING_RETURN
                self.close_filling_mode = mt5.ORDER_FILLING_RETURN
                self.filling_mode_name = "RETURN (Default)"
                
            # Broker-specific adjustments
            if any(x in broker_name for x in ['exness', 'ic markets', 'alpari']):
                # These brokers usually support FOK
                self.order_filling_mode = mt5.ORDER_FILLING_FOK
                self.close_filling_mode = mt5.ORDER_FILLING_FOK
                self.filling_mode_name = "FOK (Broker optimized)"
            elif any(x in broker_name for x in ['forex.com', 'oanda']):
                # These brokers prefer IOC
                self.order_filling_mode = mt5.ORDER_FILLING_IOC  
                self.close_filling_mode = mt5.ORDER_FILLING_IOC
                self.filling_mode_name = "IOC (Broker optimized)"
                
        except Exception as e:
            print(f"⚠️ Error detecting filling modes: {e}")
            # Safe fallback
            self.order_filling_mode = mt5.ORDER_FILLING_RETURN
            self.close_filling_mode = mt5.ORDER_FILLING_RETURN
            self.filling_mode_name = "RETURN (Safe fallback)"
        
    def initialize_grid(self, starting_direction: GridDirection = GridDirection.BIDIRECTIONAL):
        """Initialize the grid trading system with smart recovery"""
        try:
            print("🚀 Starting AI Grid System...")
            
            # Step 1: Load saved state if available
            state_loaded = self.load_grid_state()
            
            # Step 2: Clean orphaned orders from old versions
            self.clean_orphaned_orders()
            
            # Step 3: Try to recover existing orders/positions
            recovery_success = self.recover_existing_orders_and_positions()
            
            if recovery_success:
                print("🔄 ✅ RECOVERY MODE: Continuing with existing orders/positions")
                print(f"📊 Status: {len(self.pending_orders)} orders, {len(self.active_positions)} positions")
                
                # Ensure grid coverage is sufficient
                self.ensure_sufficient_grid_coverage()
                
                return True
                
            # Step 4: No existing orders/positions found - initialize new grid
            print("🆕 ✅ FRESH START: Initializing new grid system")
            
            # Check market status
            if not self.is_market_open():
                print("⚠️ Warning: Market appears to be closed")
                print("   Grid will be initialized but orders may fail until market opens")
            
            # Get current price
            price_data = self.mt5_connector.get_current_price()
            if not price_data:
                raise Exception("Failed to get current price - market may be closed")
                
            self.starting_price = price_data['bid']
            self.current_price = self.starting_price
            
            print(f"💰 Grid starting price: {self.starting_price}")
            
            # Create grid levels
            self.create_grid_levels(starting_direction)
            
            # Place initial pending orders
            placed_orders = self.place_initial_orders()
            
            # Save current state
            self.save_grid_state()
            
            print(f"✅ NEW GRID INITIALIZED:")
            print(f"   📋 Grid levels: {len(self.grid_levels)}")
            print(f"   📋 Orders placed: {placed_orders}")
            print(f"   💾 State saved for future recovery")
            
            return True
            
        except Exception as e:
            print(f"❌ Grid initialization error: {e}")
            return False
                
    def is_market_open(self) -> bool:
        """Check if market is currently open for trading"""
        try:
            # Get current time
            current_time = datetime.now()
            
            # Check if it's weekend (Saturday = 5, Sunday = 6)
            if current_time.weekday() >= 5:
                return False
                
            # Simple check - try to get tick data
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                return False
                
            # Check if price is updating (very basic check)
            return tick.time > 0
            
        except Exception as e:
            print(f"❌ Error checking market status: {e}")
            return False
            
    def create_grid_levels(self, direction):
        """สร้าง grid levels แบบ ultra-tight - วางใกล้ราคาปัจจุบันมาก"""
        self.grid_levels = []
        current_time = datetime.now()
        
        current_price = self.get_current_price()
        if not current_price:
            print("❌ Cannot get current price")
            return
            
        self.starting_price = current_price
        print(f"🧠 AI Ultra-Tight Grid: Starting at ${current_price:.2f}")
        
        # 🚀 Ultra-tight spacing (ใกล้มาก)
        ultra_tight_spacing = 50  # เพียง 50 points แทน 300
        
        if direction == GridDirection.BIDIRECTIONAL:
            # สร้างไม้หลายตัวใกล้ๆ ราคาปัจจุบัน
            positions_to_create = [
                # BUY positions (ใกล้ๆ)
                (current_price - (50 * 0.01), "BUY", "ULTRA_BUY_1"),   # -50 points
                (current_price - (100 * 0.01), "BUY", "ULTRA_BUY_2"),  # -100 points
                (current_price - (150 * 0.01), "BUY", "ULTRA_BUY_3"),  # -150 points
                
                # SELL positions (ใกล้ๆ)
                (current_price + (50 * 0.01), "SELL", "ULTRA_SELL_1"),   # +50 points
                (current_price + (100 * 0.01), "SELL", "ULTRA_SELL_2"),  # +100 points
                (current_price + (150 * 0.01), "SELL", "ULTRA_SELL_3"),  # +150 points
            ]
            
            for price, direction, level_id in positions_to_create:
                level = GridLevel(
                    level_id=level_id,
                    price=round(price, 2),
                    lot_size=self.base_lot,
                    direction=direction,
                    status=PositionStatus.PENDING,
                    entry_time=current_time
                )
                self.grid_levels.append(level)
                
                distance = abs(price - current_price) / 0.01
                print(f"   📍 {direction}: ${price:.2f} (distance: {distance:.0f} points)")
        
        print(f"🚀 Ultra-Tight Grid initialized: {len(self.grid_levels)} positions")
        print(f"   🎯 Closest orders at ±50 points from current price")


    def calculate_level_lot_size(self, level: int) -> float:
        """Calculate lot size for specific grid level with broker validation"""
        
        # Base lot size
        lot_size = self.base_lot
        
        # AI-enhanced lot sizing based on level
        if level <= 3:
            multiplier = 1.0
        elif level <= 6:
            multiplier = 1.1
        elif level <= 10:
            multiplier = 1.2
        else:
            multiplier = 1.3
            
        calculated_lot = lot_size * multiplier
        
        # 🚀 เพิ่มการตรวจสอบ broker constraints
        # Get broker info safely
        min_lot = self.symbol_info.get('volume_min', 0.01)
        max_lot = self.symbol_info.get('volume_max', 100.0)
        lot_step = self.symbol_info.get('volume_step', 0.01)
        
        # Apply minimum lot constraint
        calculated_lot = max(calculated_lot, min_lot)
        
        # 🚀 Round to broker lot step
        import math
        calculated_lot = math.ceil(calculated_lot / lot_step) * lot_step
        
        # Apply maximum lot constraint
        calculated_lot = min(calculated_lot, max_lot)
        
        # 🚀 Final validation
        final_lot = round(calculated_lot, 3)
        
        # Debug info
        if level == 1:  # แสดงแค่ level แรก
            print(f"🔍 Lot Size Calculation:")
            print(f"   Base Lot: {self.base_lot}")
            print(f"   Level {level} Multiplier: {multiplier}")
            print(f"   Broker Min: {min_lot}, Max: {max_lot}, Step: {lot_step}")
            print(f"   Calculated: {calculated_lot:.3f} → Final: {final_lot:.3f}")
        
        return final_lot
        
    def place_initial_orders(self) -> int:
        """Place initial pending orders for grid levels"""
        
        orders_placed = 0
        failed_orders = 0
        
        print(f"📋 Placing {len(self.grid_levels)} pending orders...")
        
        # Check market status first
        market_open = self.is_market_open()
        if not market_open:
            print("🕒 Market is closed - orders will be placed when market reopens")
            print("📊 Grid levels prepared and ready for market open")
            # Don't place orders, but return success to continue system initialization
            return 0
        
        for grid_level in self.grid_levels:
            try:
                order_result = self.place_pending_order(grid_level)
                if order_result:
                    grid_level.order_id = order_result
                    self.pending_orders[order_result] = grid_level
                    orders_placed += 1
                    print(f"   ✅ {grid_level.level_id}: {grid_level.lot_size} lots @ {grid_level.price}")
                else:
                    failed_orders += 1
                    
                time.sleep(0.05)  # Small delay between orders to avoid overwhelming broker
                
            except Exception as e:
                failed_orders += 1
                print(f"   ❌ Error placing {grid_level.level_id}: {e}")
                
        print(f"📊 Order placement summary: {orders_placed} placed, {failed_orders} failed")
        return orders_placed
        
    def place_pending_order(self, grid_level: GridLevel) -> Optional[int]:
        """Place a pending order with enhanced lot validation"""
        
        try:
            # 🚀 Double-check lot size before placing order
            min_lot = self.symbol_info.get('volume_min', 0.01)
            max_lot = self.symbol_info.get('volume_max', 100.0)
            lot_step = self.symbol_info.get('volume_step', 0.01)
            
            # Validate lot size
            if grid_level.lot_size < min_lot:
                print(f"❌ Lot size {grid_level.lot_size} < minimum {min_lot}")
                grid_level.lot_size = min_lot
                
            if grid_level.lot_size > max_lot:
                print(f"❌ Lot size {grid_level.lot_size} > maximum {max_lot}")
                grid_level.lot_size = max_lot
                
            # Check lot step
            remainder = grid_level.lot_size % lot_step
            if remainder != 0:
                import math
                grid_level.lot_size = math.ceil(grid_level.lot_size / lot_step) * lot_step
                print(f"⚠️ Adjusted lot size to step: {grid_level.lot_size}")
            
            # เหลือเหมือนเดิม...
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"❌ Cannot get tick data for {self.gold_symbol}")
                return None
                
            current_bid = tick.bid
            current_ask = tick.ask
            
            # Determine order type
            if grid_level.direction == "BUY":
                if grid_level.price < current_bid:
                    order_type = mt5.ORDER_TYPE_BUY_LIMIT
                    price = grid_level.price
                else:
                    order_type = mt5.ORDER_TYPE_BUY_STOP
                    price = grid_level.price
            else:  # SELL
                if grid_level.price > current_ask:
                    order_type = mt5.ORDER_TYPE_SELL_LIMIT
                    price = grid_level.price
                else:
                    order_type = mt5.ORDER_TYPE_SELL_STOP
                    price = grid_level.price
                    
            # 🚀 Final lot validation
            validated_lot = round(grid_level.lot_size, 3)
            
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": self.gold_symbol,
                "volume": validated_lot,  # ใช้ validated lot
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": self.magic_number,
                "comment": f"AIGrid_{grid_level.level_id}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": self.order_filling_mode
            }
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return result.order
            else:
                if result:
                    print(f"❌ Order failed {grid_level.level_id} - Code: {result.retcode}, Comment: {result.comment}")
                return None
                
        except Exception as e:
            print(f"❌ Order placement exception: {e}")
            return None
                
    def retry_order_with_different_filling(self, grid_level: GridLevel, original_request: dict) -> Optional[int]:
        """Retry order with different filling modes if the first one fails"""
        
        filling_modes = [
            (mt5.ORDER_FILLING_RETURN, "RETURN"),
            (mt5.ORDER_FILLING_IOC, "IOC"), 
            (mt5.ORDER_FILLING_FOK, "FOK")
        ]
        
        for filling_mode, mode_name in filling_modes:
            if filling_mode == self.order_filling_mode:
                continue  # Skip the one we already tried
                
            try:
                retry_request = original_request.copy()
                retry_request["type_filling"] = filling_mode
                
                result = mt5.order_send(retry_request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ Order {grid_level.level_id} succeeded with {mode_name} filling")
                    # Update our preferred filling mode for future orders
                    self.order_filling_mode = filling_mode
                    self.filling_mode_name = mode_name
                    return result.order
                    
            except Exception as e:
                print(f"⚠️ Retry with {mode_name} failed: {e}")
                continue
                
        print(f"❌ All filling modes failed for {grid_level.level_id}")
        return None
            
    def update_grid(self):
        """Main grid update function - called continuously during trading"""
        
        if not self.trading_active:
            return
            
        try:
            # Update current price
            self.update_current_price()
            
            # Check for filled orders
            self.check_filled_orders()
            
            # Update position PnL
            self.update_positions_pnl()
            
            # Check for grid level triggers
            self.check_grid_triggers()
            
            # Update performance metrics
            self.update_performance_metrics()
            
            # Check emergency conditions
            self.check_emergency_conditions()
            
            self.last_update = datetime.now()
            
        except Exception as e:
            print(f"❌ Grid update error: {e}")
    

    def create_buy_hedge_protection(self, buy_positions: List):
        """สร้าง Hedge Protection สำหรับ BUY positions เยอะ"""
        try:
            # หา BUY position ที่ราคาต่ำสุด (ขาดทุนมากสุด)
            worst_buy = min(buy_positions, key=lambda x: x.price)
            current_price = self.get_current_price()
            
            # คำนวณระยะห่างและขาดทุน
            distance_points = (current_price - worst_buy.price) / self.point_value
            potential_loss = worst_buy.lot_size * distance_points
            
            print(f"🔴 BUY Heavy - Worst BUY: ${worst_buy.price:.2f} ({distance_points:.0f} pts, Loss: ${potential_loss:.2f})")
            
            # เงื่อนไข: ต้องขาดทุนเกิน $10 หรือ 500 points
            if distance_points > 500 or potential_loss > 10:
                
                # สร้าง SELL Hedge ที่ราคาปัจจุบัน + buffer
                hedge_price = current_price + (50 * self.point_value)  # +50 points buffer
                hedge_lot = worst_buy.lot_size * 0.8  # 80% ของ lot ที่แย่สุด
                
                # ตรวจสอบว่ามี Hedge ใกล้ๆ แล้วไหม
                if not self.has_nearby_hedge("SELL", hedge_price):
                    success = self.place_hedge_protection_order("SELL", hedge_price, hedge_lot, f"BUY_HEDGE_{worst_buy.level_id}")
                    
                    if success:
                        print(f"🛡️ BUY Hedge placed: SELL {hedge_lot:.3f} @ ${hedge_price:.2f}")
                        print(f"   Protecting worst BUY @ ${worst_buy.price:.2f}")
                    else:
                        print("❌ Failed to place BUY hedge")
            else:
                print("💚 BUY positions healthy - no hedge needed")
                
        except Exception as e:
            print(f"❌ BUY hedge protection error: {e}")

    def create_sell_hedge_protection(self, sell_positions: List):
        """สร้าง Hedge Protection สำหรับ SELL positions เยอะ"""
        try:
            # หา SELL position ที่ราคาสูงสุด (ขาดทุนมากสุด)
            worst_sell = max(sell_positions, key=lambda x: x.price)
            current_price = self.get_current_price()
            
            # คำนวณระยะห่างและขาดทุน
            distance_points = (worst_sell.price - current_price) / self.point_value
            potential_loss = worst_sell.lot_size * distance_points
            
            print(f"🔴 SELL Heavy - Worst SELL: ${worst_sell.price:.2f} ({distance_points:.0f} pts, Loss: ${potential_loss:.2f})")
            
            # เงื่อนไข: ต้องขาดทุนเกิน $10 หรือ 500 points
            if distance_points > 500 or potential_loss > 10:
                
                # สร้าง BUY Hedge ที่ราคาปัจจุบัน - buffer
                hedge_price = current_price - (50 * self.point_value)  # -50 points buffer
                hedge_lot = worst_sell.lot_size * 0.8  # 80% ของ lot ที่แย่สุด
                
                # ตรวจสอบว่ามี Hedge ใกล้ๆ แล้วไหม
                if not self.has_nearby_hedge("BUY", hedge_price):
                    success = self.place_hedge_protection_order("BUY", hedge_price, hedge_lot, f"SELL_HEDGE_{worst_sell.level_id}")
                    
                    if success:
                        print(f"🛡️ SELL Hedge placed: BUY {hedge_lot:.3f} @ ${hedge_price:.2f}")
                        print(f"   Protecting worst SELL @ ${worst_sell.price:.2f}")
                    else:
                        print("❌ Failed to place SELL hedge")
            else:
                print("💚 SELL positions healthy - no hedge needed")
                
        except Exception as e:
            print(f"❌ SELL hedge protection error: {e}")

    def has_nearby_hedge(self, direction: str, price: float) -> bool:
        """เช็คว่ามี Hedge Order ใกล้ๆ แล้วไหม"""
        try:
            min_distance = 200 * self.point_value  # 200 points distance
            
            # เช็ค pending orders
            for grid_level in self.pending_orders.values():
                if (grid_level.direction == direction and 
                    "HEDGE" in grid_level.level_id and
                    abs(grid_level.price - price) < min_distance):
                    return True
                    
            # เช็ค active positions ที่เป็น hedge
            for grid_level in self.active_positions.values():
                if (grid_level.direction == direction and 
                    "HEDGE" in grid_level.level_id and
                    abs(grid_level.price - price) < min_distance):
                    return True
                    
            return False
            
        except Exception as e:
            print(f"❌ Hedge check error: {e}")
            return True  # ถ้า error ให้ถือว่ามี hedge แล้ว (ป้องกัน)

    def place_hedge_protection_order(self, direction: str, price: float, lot_size: float, hedge_id: str) -> bool:
        """วาง Hedge Protection Order - Enhanced Version"""
        try:
            print(f"🛡️ Attempting hedge: {direction} {lot_size:.3f} @ ${price:.2f}")
            
            # ✅ 1. ตรวจสอบและปรับ lot size
            original_lot = lot_size
            lot_size = max(lot_size, self.min_lot)
            lot_size = round(lot_size / self.lot_step) * self.lot_step
            
            if lot_size != original_lot:
                print(f"   📏 Lot adjusted: {original_lot:.3f} → {lot_size:.3f}")
            
            # ✅ 2. ตรวจสอบราคาปัจจุบันและปรับ hedge price
            current_price = self.get_current_price()
            if not current_price:
                print("   ❌ Cannot get current price")
                return False
            
            # ปรับราคา hedge ให้เหมาะสมกับตลาดปัจจุบัน
            min_distance = 30 * self.point_value  # อย่างน้อย 30 points จาก current
            
            if direction == "BUY":
                # BUY hedge ต้องต่ำกว่า current price
                max_buy_price = current_price - min_distance
                if price > max_buy_price:
                    price = max_buy_price
                    print(f"   📉 BUY price adjusted to ${price:.2f}")
            else:
                # SELL hedge ต้องสูงกว่า current price  
                min_sell_price = current_price + min_distance
                if price < min_sell_price:
                    price = min_sell_price
                    print(f"   📈 SELL price adjusted to ${price:.2f}")
            
            # ✅ 3. ลองวาง Market Order แทน Pending Order (สำหรับ hedge)
            success = self.place_hedge_market_order(direction, lot_size, hedge_id)
            if success:
                return True
            
            # ✅ 4. ถ้า Market Order ไม่ได้ ลอง Pending Order
            print("   🔄 Market order failed, trying pending order...")
            
            # สร้าง Grid Level สำหรับ Hedge
            hedge_level = GridLevel(
                level_id=hedge_id,
                price=round(price, 2),
                lot_size=lot_size,
                direction=direction,
                status=PositionStatus.PENDING,
                entry_time=datetime.now()
            )
            
            # ✅ 5. วาง Pending Order พร้อม retry logic
            order_result = self.place_pending_order_with_retry(hedge_level)
            if order_result:
                hedge_level.order_id = order_result
                self.grid_levels.append(hedge_level)
                self.pending_orders[order_result] = hedge_level
                
                print(f"   ✅ Hedge pending order: {hedge_id} (Order #{order_result})")
                return True
            else:
                print(f"   ❌ All hedge order attempts failed: {hedge_id}")
                return False
                
        except Exception as e:
            print(f"❌ Hedge order placement error: {e}")
            return False
    
    def place_hedge_market_order(self, direction: str, lot_size: float, hedge_id: str) -> bool:
        """วาง Market Order สำหรับ Hedge (ได้ราคาทันที)"""
        try:
            # Get current tick
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print("   ❌ No tick data for market hedge")
                return False
            
            # Determine order type and price
            if direction == "BUY":
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                order_type = mt5.ORDER_TYPE_SELL  
                price = tick.bid
            
            # Market order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.gold_symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "deviation": 50,  # Higher deviation for hedge
                "magic": self.magic_number,
                "comment": f"HEDGE_MARKET_{hedge_id}",
                "type_filling": self.order_filling_mode
            }
            
            print(f"   🎯 Market hedge: {direction} {lot_size:.3f} @ ${price:.2f}")
            
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"   ✅ Market hedge executed: Position #{result.order}")
                
                # สร้าง grid level สำหรับ track market hedge
                hedge_level = GridLevel(
                    level_id=hedge_id,
                    price=price,
                    lot_size=lot_size,
                    direction=direction,
                    status=PositionStatus.ACTIVE,
                    position_id=result.order,
                    entry_time=datetime.now()
                )
                
                self.grid_levels.append(hedge_level)
                self.active_positions[result.order] = hedge_level
                
                return True
            else:
                error_msg = f"Market hedge failed - Code: {result.retcode if result else 'None'}"
                if result:
                    error_msg += f", Comment: {result.comment}"
                print(f"   ⚠️ {error_msg}")
                return False
                
        except Exception as e:
            print(f"   ❌ Market hedge error: {e}")
            return False

    def place_pending_order_with_retry(self, grid_level: GridLevel) -> Optional[int]:
        """วาง Pending Order พร้อม retry หลายครั้ง"""
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"   🔄 Hedge order attempt {retry_count + 1}/{max_retries}")
                
                # ใช้ method เดิมที่มีอยู่แล้ว
                order_result = self.place_pending_order(grid_level)
                
                if order_result:
                    print(f"   ✅ Hedge order successful on attempt {retry_count + 1}")
                    return order_result
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"   ⚠️ Attempt {retry_count} failed, retrying...")
                        time.sleep(1)  # รอ 1 วินาทีก่อน retry
                        
                        # ปรับราคาเล็กน้อยสำหรับ retry
                        if grid_level.direction == "BUY":
                            grid_level.price -= 10 * self.point_value  # ลดราคา 10 points
                        else:
                            grid_level.price += 10 * self.point_value  # เพิ่มราคา 10 points
                            
                        grid_level.price = round(grid_level.price, 2)
                        print(f"   📝 Price adjusted to ${grid_level.price:.2f} for retry")
                        
            except Exception as e:
                print(f"   ❌ Retry {retry_count + 1} error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(2)  # รอนานขึ้นถ้า error
        
        print(f"   ❌ All {max_retries} hedge order attempts failed")
        return None

    def monitor_hedge_effectiveness(self):
        """ตรวจสอบประสิทธิภาพของ Hedge"""
        try:
            hedge_positions = []
            normal_positions = []
            
            # แยก positions
            for grid_level in self.active_positions.values():
                if "HEDGE" in grid_level.level_id:
                    hedge_positions.append(grid_level)
                else:
                    normal_positions.append(grid_level)
            
            if hedge_positions:
                total_hedge_pnl = sum(pos.pnl for pos in hedge_positions)
                total_normal_pnl = sum(pos.pnl for pos in normal_positions)
                net_pnl = total_hedge_pnl + total_normal_pnl
                
                print(f"🛡️ Hedge Status: {len(hedge_positions)} hedges")
                print(f"   Hedge PnL: ${total_hedge_pnl:.2f}")
                print(f"   Normal PnL: ${total_normal_pnl:.2f}")
                print(f"   Net PnL: ${net_pnl:.2f}")
                
                # ถ้า hedge ทำกำไรแล้ว และ normal positions ลดขาดทุน -> ปิด hedge
                if total_hedge_pnl > 5 and total_normal_pnl > -50:
                    self.close_profitable_hedges(hedge_positions)
            
        except Exception as e:
            print(f"❌ Hedge monitoring error: {e}")

    def close_profitable_hedges(self, hedge_positions: List):
        """ปิด Hedge ที่ทำกำไรแล้ว"""
        try:
            for hedge_pos in hedge_positions:
                if hedge_pos.pnl > 3:  # กำไรเกิน $3
                    if self.close_grid_position(hedge_pos):
                        print(f"💰 Closed profitable hedge: {hedge_pos.level_id} (+${hedge_pos.pnl:.2f})")
                        
        except Exception as e:
            print(f"❌ Close hedge error: {e}")

    def update_current_price(self):
        """Update current gold price and store history"""
        
        price_data = self.mt5_connector.get_current_price()
        if price_data:
            self.current_price = price_data['bid']
            
            # Store price history for AI analysis
            self.price_history.append({
                'time': datetime.now(),
                'price': self.current_price,
                'bid': price_data['bid'],
                'ask': price_data['ask']
            })
            
            # Keep only recent history (last 1000 entries)
            if len(self.price_history) > 1000:
                self.price_history = self.price_history[-1000:]
                
    def check_filled_orders(self):
        """Check for filled pending orders and convert to positions - ENHANCED VERSION"""
        
        try:
            # Get current orders and positions with our magic number
            orders = mt5.orders_get(symbol=self.gold_symbol)
            positions = mt5.positions_get(symbol=self.gold_symbol)
            
            # Filter orders by our magic number
            our_orders = [order for order in orders if order.magic == self.magic_number] if orders else []
            our_positions = [pos for pos in positions if pos.magic == self.magic_number] if positions else []
            
            # Get active order IDs
            active_order_ids = {order.ticket for order in our_orders}
            
            # Check for newly filled orders
            for order_id, grid_level in list(self.pending_orders.items()):
                if order_id not in active_order_ids:
                    # Order has been filled or cancelled - enhanced detection
                    
                    # Method 1: Find by comment (original method)
                    position = self.find_position_by_magic_and_comment(f"AIGrid_{grid_level.level_id}")
                    
                    # Method 2: If not found, try broader search by magic + timing
                    if not position:
                        time.sleep(0.2)  # Wait for MT5 to update
                        recent_positions = [pos for pos in our_positions 
                                            if abs(pos.price_open - grid_level.price) < 0.5 and  # Close price match
                                            abs(pos.volume - grid_level.lot_size) < 0.001 and  # Exact volume match
                                            datetime.fromtimestamp(pos.time) > (datetime.now() - timedelta(seconds=30))]  # Recent
                        
                        if recent_positions:
                            position = recent_positions[0]  # Take the first match
                            print(f"🔍 Position found by price/volume matching: {position.ticket}")
                    
                    # Method 3: Check if position exists by price range (most lenient)
                    if not position:
                        price_tolerance = 1.0  # 1 dollar tolerance for slippage
                        matching_positions = [pos for pos in our_positions 
                                            if abs(pos.price_open - grid_level.price) <= price_tolerance and
                                                pos.volume == grid_level.lot_size and
                                                "HEDGE" not in pos.comment]  # Exclude hedge positions
                        
                        if matching_positions:
                            position = matching_positions[0]
                            print(f"🔍 Position found by price tolerance: {position.ticket}")
                    
                    if position:
                        # Order was filled and became a position
                        grid_level.status = PositionStatus.ACTIVE
                        grid_level.position_id = position.ticket
                        grid_level.entry_time = datetime.now()
                        
                        # Store actual entry price (may differ from order price due to slippage)
                        actual_entry = position.price_open
                        slippage = abs(actual_entry - grid_level.price)
                        grid_level.price = actual_entry
                        
                        self.active_positions[position.ticket] = grid_level
                        del self.pending_orders[order_id]
                        
                        self.trades_opened += 1
                        
                        if slippage > 0.1:
                            print(f"✅ Grid level activated: {grid_level.level_id} @ {actual_entry:.2f} ({grid_level.lot_size} lots) [Slippage: ${slippage:.2f}]")
                        else:
                            print(f"✅ Grid level activated: {grid_level.level_id} @ {actual_entry:.2f} ({grid_level.lot_size} lots)")
                        
                        # Place replacement order for this level
                        self.replace_filled_level(grid_level)
                        
                    else:
                        # Order was truly cancelled or rejected - ENHANCED HANDLING
                        current_price = self.get_current_price()
                        price_distance = abs(grid_level.price - current_price)
                        
                        grid_level.status = PositionStatus.CANCELLED
                        del self.pending_orders[order_id]
                        
                        print(f"❌ Grid order cancelled/rejected: {grid_level.level_id} @ {grid_level.price:.2f}")
                        print(f"   Current price: {current_price:.2f}, Distance: {price_distance:.2f}")
                        
                        # 🔥 CRITICAL FIX: Don't retry at same price - it will fail again!
                        # Only retry if price is still reasonable distance from market
                        min_safe_distance = self.grid_spacing * self.point_value * 0.5  # 50% of grid spacing
                        
                        if price_distance >= min_safe_distance:
                            print(f"🔄 Price still valid - will be handled by grid extension logic")
                            # Let the grid extension system handle this later
                            # Don't immediate retry to avoid "Invalid price" errors
                        else:
                            print(f"⚠️ Price too close to market - skipping retry (will extend grid elsewhere)")
                            # Mark as cancelled and let system create new levels elsewhere
                        
                        # Remove from grid_levels if it's no longer viable
                        if price_distance < min_safe_distance:
                            self.grid_levels = [gl for gl in self.grid_levels if gl.level_id != grid_level.level_id]
                            print(f"🗑️ Removed unviable grid level: {grid_level.level_id}")
                            
        except Exception as e:
            print(f"❌ Error checking filled orders: {e}")

    def find_position_by_magic_and_comment(self, comment: str):
        """Find position by magic number and comment"""
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            if positions:
                for position in positions:
                    if position.magic == self.magic_number and comment in position.comment:
                        return position
        except Exception as e:
            print(f"❌ Error finding position: {e}")
        return None
        
    def replace_filled_level(self, filled_level: GridLevel):
        """Enhanced replacement with smart positioning"""
        self.smart_replacement_on_close(filled_level)

    def place_opposite_profit_order(self, filled_level: GridLevel, lot_multiplier: float):
        """Place opposite order for profit-taking"""
        try:
            opposite_direction = "BUY" if filled_level.direction == "SELL" else "SELL"
            profit_points = self.grid_spacing * 0.8  # 80% of grid spacing
            
            if filled_level.direction == "SELL":
                opposite_price = filled_level.price - (profit_points * self.point_value)
            else:
                opposite_price = filled_level.price + (profit_points * self.point_value)
            
            # Adjust lot size
            lot_size = filled_level.lot_size * lot_multiplier
            lot_size = max(lot_size, self.min_lot)
            
            print(f"💰 Placing {opposite_direction} @ {opposite_price} for profit (lot: {lot_size:.3f})")
            
            opposite_level = GridLevel(
                level_id=f"{opposite_direction}_PROFIT_{int(time.time())}",
                price=round(opposite_price, 5),
                lot_size=lot_size,
                direction=opposite_direction,
                status=PositionStatus.PENDING,
                entry_time=datetime.now()
            )
            
            order_result = self.place_pending_order(opposite_level)
            if order_result:
                opposite_level.order_id = order_result
                self.grid_levels.append(opposite_level)
                self.pending_orders[order_result] = opposite_level
                print(f"✅ {opposite_direction} profit order placed @ {opposite_price}")
            else:
                print(f"❌ Failed {opposite_direction} profit order")
                
        except Exception as e:
            print(f"❌ Opposite order error: {e}")

    def place_extension_order(self, filled_level: GridLevel, current_price: float):
        """Place extension order in same direction"""
        try:
            # Count existing orders in same direction
            if filled_level.direction == "SELL":
                existing_orders = [l for l in self.grid_levels 
                                if l.direction == "SELL" and 
                                l.status == PositionStatus.PENDING and
                                l.price > current_price]
                if existing_orders:
                    extension_price = max(l.price for l in existing_orders) + (self.grid_spacing * self.point_value)
                else:
                    extension_price = filled_level.price + (self.grid_spacing * self.point_value)
            else:
                existing_orders = [l for l in self.grid_levels 
                                if l.direction == "BUY" and 
                                l.status == PositionStatus.PENDING and
                                l.price < current_price]
                if existing_orders:
                    extension_price = min(l.price for l in existing_orders) - (self.grid_spacing * self.point_value)
                else:
                    extension_price = filled_level.price - (self.grid_spacing * self.point_value)
            
            print(f"🔄 Extending {filled_level.direction} grid @ {extension_price}")
            
            extension_level = GridLevel(
                level_id=f"{filled_level.direction}_EXT_{int(time.time())}",
                price=round(extension_price, 5),
                lot_size=filled_level.lot_size,
                direction=filled_level.direction,
                status=PositionStatus.PENDING,
                entry_time=datetime.now()
            )
            
            order_result = self.place_pending_order(extension_level)
            if order_result:
                extension_level.order_id = order_result
                self.grid_levels.append(extension_level)
                self.pending_orders[order_result] = extension_level
                print(f"✅ {filled_level.direction} extension @ {extension_price}")
            else:
                print(f"❌ Failed extension order")
                
        except Exception as e:
            print(f"❌ Extension error: {e}")

    def update_positions_pnl(self):
        """Update PnL for all active positions - REAL DATA"""
        
        try:
            total_unrealized = 0.0
            positions = mt5.positions_get(symbol=self.gold_symbol)
            
            if positions:
                our_positions = [pos for pos in positions if pos.magic == self.magic_number]
                
                for position in our_positions:
                    if position.ticket in self.active_positions:
                        grid_level = self.active_positions[position.ticket]
                        grid_level.pnl = position.profit
                        total_unrealized += position.profit
                        
            self.unrealized_pnl = total_unrealized
            self.total_pnl = self.realized_pnl + self.unrealized_pnl
            
            # Update drawdown
            self.update_drawdown()
            
        except Exception as e:
            print(f"❌ Error updating PnL: {e}")
            
    def update_drawdown(self):
        """Update current drawdown in points and dollars"""
        
        try:
            if self.unrealized_pnl < 0:
                # Calculate drawdown in points
                drawdown_dollars = abs(self.unrealized_pnl)
                
                # Convert to points (for gold: approximately $1 = 100 points for 0.01 lot)
                total_lots = sum(level.lot_size for level in self.active_positions.values())
                if total_lots > 0:
                    # More accurate calculation: drawdown_points = drawdown_dollars / (total_lots * point_value_in_dollars)
                    point_value_per_lot = 100  # $100 per point for 1 lot gold
                    drawdown_points = drawdown_dollars / (total_lots * point_value_per_lot)
                else:
                    drawdown_points = 0
                    
                self.current_drawdown = drawdown_points
                self.max_drawdown_points = max(self.max_drawdown_points, drawdown_points)
            else:
                self.current_drawdown = 0
                
        except Exception as e:
            print(f"❌ Error updating drawdown: {e}")
            
    def check_grid_triggers(self):
        """Check if any grid levels should be activated or modified"""
        
        # Check for price-based triggers
        current_price = self.current_price
        
        # Activate new grid levels if price moves significantly
        self.check_new_level_activation(current_price)
        
        # Check for profit-taking opportunities
        self.check_profit_taking_opportunities()
        
        # Check for grid rebalancing needs
        self.check_grid_rebalancing()
        
    def check_new_level_activation(self, current_price: float):
        """Check if new grid levels should be activated"""
        
        try:
            # Calculate distance from starting price in points
            price_move_points = abs(current_price - self.starting_price) / self.point_value
            
            # If moved beyond 70% of current grid range, consider extending
            current_range = len([l for l in self.grid_levels if l.status in [PositionStatus.PENDING, PositionStatus.ACTIVE]]) * self.grid_spacing
            
            if price_move_points > (current_range * 0.7):
                self.extend_grid_if_needed(current_price)
                
        except Exception as e:
            print(f"❌ Error checking new level activation: {e}")
            
    def extend_grid_if_needed(self, current_price: float):
        """Extend grid if price moves beyond current range"""
        
        try:
            active_levels = [l for l in self.grid_levels if l.status != PositionStatus.CANCELLED]
            
            # Don't extend if we're already at maximum levels
            if len(active_levels) >= self.max_levels:
                return
                
            # Calculate new grid levels
            if current_price < self.starting_price:
                # Price moving down, add more buy levels
                buy_levels = [l for l in active_levels if l.direction == "BUY"]
                if buy_levels:
                    lowest_price = min(l.price for l in buy_levels)
                    new_price = lowest_price - (self.grid_spacing * self.point_value)
                    
                    # Check if within survivability range
                    if abs(new_price - self.starting_price) / self.point_value < self.survivability * 0.8:
                        self.add_new_grid_level("BUY", new_price)
                        
            else:
                # Price moving up, add more sell levels
                sell_levels = [l for l in active_levels if l.direction == "SELL"]
                if sell_levels:
                    highest_price = max(l.price for l in sell_levels)
                    new_price = highest_price + (self.grid_spacing * self.point_value)
                    
                    # Check if within survivability range
                    if abs(new_price - self.starting_price) / self.point_value < self.survivability * 0.8:
                        self.add_new_grid_level("SELL", new_price)
                        
        except Exception as e:
            print(f"❌ Error extending grid: {e}")
            
    def add_new_grid_level(self, direction: str, price: float):
        """Add a new grid level"""
        
        try:
            level_count = len([l for l in self.grid_levels if l.direction == direction])
            new_level = GridLevel(
                level_id=f"{direction}_EXT_{level_count + 1}_{int(time.time())}",
                price=round(price, 5),  # Round to 5 decimal places for gold
                lot_size=self.calculate_level_lot_size(level_count + 1),
                direction=direction,
                status=PositionStatus.PENDING
            )
            
            order_result = self.place_pending_order(new_level)
            if order_result:
                new_level.order_id = order_result
                self.grid_levels.append(new_level)
                self.pending_orders[order_result] = new_level
                print(f"🆕 Extended grid: {new_level.level_id} @ {price} ({new_level.lot_size} lots)")
            else:
                print(f"❌ Failed to extend grid at {price}")
                
        except Exception as e:
            print(f"❌ Error adding new grid level: {e}")
            
    def check_profit_taking_opportunities(self):
        """Check for profit-taking opportunities on grid positions"""
        
        try:
            for position_id, grid_level in list(self.active_positions.items()):
                if grid_level.pnl > 0:
                    # Calculate profit target based on grid spacing
                    profit_target = self.grid_spacing * 0.8  # 80% of grid spacing in dollars
                    
                    if grid_level.pnl >= profit_target:
                        # Take profit on this position
                        if self.close_grid_position(grid_level):
                            print(f"💰 Profit taken: {grid_level.level_id} - ${grid_level.pnl:.2f}")
                            
        except Exception as e:
            print(f"❌ Error checking profit opportunities: {e}")
            
    def close_grid_position(self, grid_level: GridLevel) -> bool:
        """Close a grid position - REAL TRADING with Smart Filling"""
        
        try:
            # Get current position
            positions = mt5.positions_get(ticket=grid_level.position_id)
            if not positions:
                print(f"❌ Position {grid_level.position_id} not found")
                return False
                
            position = positions[0]
            
            # Get current market prices
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"❌ Cannot get tick data for {self.gold_symbol}")
                return False
                
            # Determine close parameters
            if position.type == mt5.POSITION_TYPE_BUY:
                trade_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                trade_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
                
            # Prepare close request with smart filling mode
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.gold_symbol,
                "volume": position.volume,
                "type": trade_type,
                "position": grid_level.position_id,
                "price": price,
                "deviation": 20,
                "magic": self.magic_number,
                "comment": f"AIGrid_Close_{grid_level.level_id}",
                "type_filling": self.close_filling_mode  # Smart filling mode
            }
            
            # Execute close
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                grid_level.status = PositionStatus.CLOSED
                grid_level.close_time = datetime.now()
                
                # Update statistics
                self.realized_pnl += grid_level.pnl
                self.trades_closed += 1
                
                if grid_level.pnl > 0:
                    self.winning_trades += 1
                    self.largest_win = max(self.largest_win, grid_level.pnl)
                else:
                    self.losing_trades += 1
                    self.largest_loss = min(self.largest_loss, grid_level.pnl)
                    
                # Remove from active positions
                if grid_level.position_id in self.active_positions:
                    del self.active_positions[grid_level.position_id]
                
                self.smart_replacement_on_close(grid_level)

                return True
                
            else:
                # Handle filling mode errors and retry
                if result and result.retcode == 10030:  # Unsupported filling mode
                    print(f"🔄 Retrying close {grid_level.level_id} with different filling mode")
                    return self.retry_close_with_different_filling(grid_level, request)
                else:
                    error_msg = f"Close failed - Code: {result.retcode if result else 'None'}"
                    if result:
                        error_msg += f", Comment: {result.comment}"
                    print(f"❌ {error_msg}")
                    return False
                
        except Exception as e:
            print(f"❌ Error closing position {grid_level.level_id}: {e}")
            return False
            
    def retry_close_with_different_filling(self, grid_level: GridLevel, original_request: dict) -> bool:
        """Retry close with different filling modes if the first one fails"""
        
        filling_modes = [
            (mt5.ORDER_FILLING_RETURN, "RETURN"),
            (mt5.ORDER_FILLING_IOC, "IOC"), 
            (mt5.ORDER_FILLING_FOK, "FOK")
        ]
        
        for filling_mode, mode_name in filling_modes:
            if filling_mode == self.close_filling_mode:
                continue  # Skip the one we already tried
                
            try:
                retry_request = original_request.copy()
                retry_request["type_filling"] = filling_mode
                
                result = mt5.order_send(retry_request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ Close {grid_level.level_id} succeeded with {mode_name} filling")
                    # Update our preferred filling mode for future closes
                    self.close_filling_mode = filling_mode
                    
                    # Update position status
                    grid_level.status = PositionStatus.CLOSED
                    grid_level.close_time = datetime.now()
                    
                    # Update statistics
                    self.realized_pnl += grid_level.pnl
                    self.trades_closed += 1
                    
                    if grid_level.pnl > 0:
                        self.winning_trades += 1
                        self.largest_win = max(self.largest_win, grid_level.pnl)
                    else:
                        self.losing_trades += 1
                        self.largest_loss = min(self.largest_loss, grid_level.pnl)
                        
                    # Remove from active positions
                    if grid_level.position_id in self.active_positions:
                        del self.active_positions[grid_level.position_id]
                    
                    return True
                    
            except Exception as e:
                print(f"⚠️ Close retry with {mode_name} failed: {e}")
                continue
                
        print(f"❌ All filling modes failed for closing {grid_level.level_id}")
        return False
            
    def check_grid_rebalancing(self):
        """Check if grid needs rebalancing"""
        
        try:
            active_buys = len([l for l in self.active_positions.values() if l.direction == "BUY"])
            active_sells = len([l for l in self.active_positions.values() if l.direction == "SELL"])
            
            # Log significant imbalances
            if abs(active_buys - active_sells) > 5:
                print(f"⚖️ Grid imbalance: {active_buys} buys, {active_sells} sells")
                
                # Could implement automatic rebalancing here
                # For now, just log the imbalance
                
        except Exception as e:
            print(f"❌ Error checking grid rebalancing: {e}")
            
    def check_emergency_conditions(self):
        """Monitor conditions only - No automatic emergency stop"""
        
        try:
            # Monitor daily loss - แจ้งเตือนอย่างเดียว ไม่หยุด
            if self.total_pnl < -abs(self.daily_loss_limit):
                print(f"⚠️ Daily loss alert: ${self.total_pnl:.2f} (Limit: -${self.daily_loss_limit}) - Consider manual stop")
                
            # Monitor drawdown - แจ้งเตือนอย่างเดียว ไม่หยุด
            survivability_limit = self.survivability * 0.9
            if self.current_drawdown > survivability_limit:
                print(f"⚠️ High drawdown alert: {self.current_drawdown:.0f} > {survivability_limit:.0f} points - Consider manual stop")
                
            # Monitor margin level - เฉพาะเมื่อมี positions
            account_info = self.mt5_connector.get_account_info()
            if account_info:
                margin_level = account_info.get('margin_level', 0)
                current_margin = account_info.get('margin', 0)
                
                # เช็ค margin level เฉพาะเมื่อมี positions (margin > 0)
                if current_margin > 0:  # มี positions อยู่จริง
                    if margin_level < 150:  # Critical margin level
                        print(f"⚠️ Critical margin level: {margin_level:.0f}% - Consider adding funds or manual stop")
                    elif margin_level < 200:  # Warning level
                        print(f"ℹ️ Low margin level: {margin_level:.0f}%")
                # ถ้าไม่มี positions (margin = 0) ไม่แสดงอะไร
                    
            # Monitor account equity vs balance - แจ้งเตือนอย่างเดียว ไม่หยุด
            if account_info:
                equity = account_info.get('equity', 0)
                balance = account_info.get('balance', 0)
                if balance > 0:
                    equity_ratio = equity / balance
                    if equity_ratio < 0.5:  # Lost 50% of account
                        print(f"⚠️ Account equity low: {equity_ratio*100:.1f}% - Consider manual stop or add funds")
                        
        except Exception as e:
            print(f"❌ Error monitoring conditions: {e}")

    def emergency_stop(self, reason: str = "Emergency condition triggered"):
        """Emergency stop all trading - REAL EMERGENCY SYSTEM"""
        
        if self.emergency_stop_triggered:
            return
            
        self.emergency_stop_triggered = True
        self.trading_active = False
        
        print(f"🚨 EMERGENCY STOP: {reason}")
        
        try:
            # Close all positions immediately
            closed_positions = self.close_all_positions()
            print(f"🔴 Closed {closed_positions} positions")
            
            # Cancel all pending orders
            cancelled_orders = self.cancel_all_orders()
            print(f"🔴 Cancelled {cancelled_orders} orders")
            
            # Log emergency stop
            self.log_emergency_stop(reason)
            
        except Exception as e:
            print(f"❌ Error during emergency stop: {e}")
            
    def close_all_positions(self) -> int:
        """Close all active positions - EMERGENCY FUNCTION with Smart Filling"""
        
        closed_count = 0
        
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            if positions:
                our_positions = [pos for pos in positions if pos.magic == self.magic_number]
                
                for position in our_positions:
                    try:
                        # Get current market prices
                        tick = mt5.symbol_info_tick(self.gold_symbol)
                        if not tick:
                            continue
                            
                        if position.type == mt5.POSITION_TYPE_BUY:
                            trade_type = mt5.ORDER_TYPE_SELL
                            price = tick.bid
                        else:
                            trade_type = mt5.ORDER_TYPE_BUY
                            price = tick.ask
                            
                        # Try multiple filling modes for emergency close
                        filling_modes = [
                            (mt5.ORDER_FILLING_RETURN, "RETURN"),
                            (mt5.ORDER_FILLING_IOC, "IOC"),
                            (mt5.ORDER_FILLING_FOK, "FOK")
                        ]
                        
                        success = False
                        for filling_mode, mode_name in filling_modes:
                            request = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "symbol": self.gold_symbol,
                                "volume": position.volume,
                                "type": trade_type,
                                "position": position.ticket,
                                "price": price,
                                "deviation": 50,  # Higher deviation for emergency
                                "magic": self.magic_number,
                                "comment": "AIGrid_Emergency_Close",
                                "type_filling": filling_mode
                            }
                            
                            result = mt5.order_send(request)
                            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                                closed_count += 1
                                print(f"   ✅ Emergency closed: {position.ticket} ({position.volume} lots) with {mode_name}")
                                success = True
                                break
                                
                        if not success:
                            error_msg = f"Failed to close {position.ticket}"
                            if result:
                                error_msg += f" - {result.comment}"
                            print(f"   ❌ {error_msg}")
                            
                    except Exception as e:
                        print(f"   ❌ Error closing position {position.ticket}: {e}")
                        
        except Exception as e:
            print(f"❌ Error in close_all_positions: {e}")
            
        return closed_count
        
    def cancel_all_orders(self) -> int:
        """Cancel all pending orders - EMERGENCY FUNCTION"""
        
        cancelled_count = 0
        
        try:
            orders = mt5.orders_get(symbol=self.gold_symbol)
            if orders:
                our_orders = [order for order in orders if order.magic == self.magic_number]
                
                for order in our_orders:
                    try:
                        request = {
                            "action": mt5.TRADE_ACTION_REMOVE,
                            "order": order.ticket
                        }
                        
                        result = mt5.order_send(request)
                        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                            cancelled_count += 1
                            print(f"   ✅ Cancelled order: {order.ticket}")
                        else:
                            error_msg = f"Failed to cancel {order.ticket}"
                            if result:
                                error_msg += f" - {result.comment}"
                            print(f"   ❌ {error_msg}")
                            
                    except Exception as e:
                        print(f"   ❌ Error cancelling order {order.ticket}: {e}")
                        
        except Exception as e:
            print(f"❌ Error in cancel_all_orders: {e}")
            
        return cancelled_count
        
    def log_emergency_stop(self, reason: str):
        """Log emergency stop event"""
        
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "EMERGENCY_STOP",
                "reason": reason,
                "account_balance": self.mt5_connector.get_account_info().get('balance', 0),
                "total_pnl": self.total_pnl,
                "current_drawdown": self.current_drawdown,
                "active_positions": len(self.active_positions),
                "pending_orders": len(self.pending_orders)
            }
            
            # Could save to file or database
            print(f"📝 Emergency stop logged: {log_entry}")
            
        except Exception as e:
            print(f"❌ Error logging emergency stop: {e}")
            
    def update_performance_metrics(self):
        """Update trading performance metrics"""
        
        try:
            # Calculate win rate
            total_closed = self.winning_trades + self.losing_trades
            self.win_rate = (self.winning_trades / total_closed) if total_closed > 0 else 0
            
            # Calculate profit factor
            total_wins = max(0.01, sum(level.pnl for level in self.grid_levels if level.status == PositionStatus.CLOSED and level.pnl > 0))
            total_losses = abs(min(-0.01, sum(level.pnl for level in self.grid_levels if level.status == PositionStatus.CLOSED and level.pnl < 0)))
            self.profit_factor = total_wins / total_losses if total_losses > 0 else 0
            
        except Exception as e:
            print(f"❌ Error updating performance metrics: {e}")
            
    def get_grid_status(self) -> Dict:
        """Get comprehensive grid status - ENHANCED with Recovery Info"""
        
        try:
            # Original status data (keep existing code)
            base_status = {
                'trading_active': self.trading_active,
                'gold_symbol': self.gold_symbol,
                'current_price': self.current_price,
                'starting_price': self.starting_price,
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
                'market_open': self.is_market_open()
            }
            
            # ✅ เพิ่มข้อมูล Recovery System
            if (hasattr(self, 'smart_profit_enabled') and self.smart_profit_enabled and
                hasattr(self, 'smart_profit_manager')):
                try:
                    recovery_status = self.smart_profit_manager.get_recovery_status()
                    base_status['recovery_system'] = recovery_status
                except Exception as recovery_error:
                    base_status['recovery_system'] = {'error': str(recovery_error)}
            else:
                base_status['recovery_system'] = {'enabled': False, 'active': False}
                
            return base_status
            
        except Exception as e:
            print(f"❌ Error getting grid status: {e}")
            return {'error': str(e)} 
                
    def start_trading(self):
        """Start the grid trading system"""
        if not self.trading_active and not self.emergency_stop_triggered:
            self.trading_active = True
            print("🚀 AI Grid Trading Started!")
            return True
        return False
        
    def stop_trading(self):
        """Stop the grid trading system gracefully"""
        self.trading_active = False
        print("⏹️ AI Grid Trading Stopped")
        
    def get_current_drawdown(self) -> float:
        """Get current drawdown in points for hedge system integration"""
        return self.current_drawdown
        
    def check_hedge_triggers(self):
        """Integration point for hedge system"""
        return self.current_drawdown
        
    def emergency_close_all(self):
        """Public method for emergency close - called from GUI"""
        self.emergency_stop("Manual emergency stop from GUI")
        
    def cleanup_far_orders(self):
        """ลบ orders ที่ไกลเกินไปและเก่าเกินไป"""
        try:
            current_price = self.get_current_price()
            orders_to_remove = []
            removed_count = 0
            
            print(f"🔍 Checking orders cleanup at price: ${current_price:.2f}")
            
            # คำนวณระยะห่างที่ควรลบ (ขึ้นกับ grid spacing)
            far_distance = self.calculate_cleanup_distance()
            old_age_hours = 24 * 7  # 7 วัน
            
            # ตรวจสอบ pending orders
            for order_id, grid_level in list(self.pending_orders.items()):
                try:
                    distance_points = abs(grid_level.price - current_price) / self.point_value
                    age_hours = 0
                    
                    # คำนวณอายุ order
                    if grid_level.entry_time:
                        age_hours = (datetime.now() - grid_level.entry_time).total_seconds() / 3600
                    
                    # เงื่อนไขลับ orders
                    should_remove = (
                        distance_points > far_distance and age_hours > old_age_hours
                    ) or (
                        distance_points > far_distance * 2  # ห่างมากเกินไป
                    ) or (
                        age_hours > 24 * 30  # เก่าเกิน 30 วัน
                    )
                    
                    if should_remove:
                        if self.cancel_single_order(order_id):
                            del self.pending_orders[order_id]
                            grid_level.status = PositionStatus.CANCELLED
                            removed_count += 1
                            print(f"🗑️ Removed: {grid_level.level_id} @ ${grid_level.price:.2f} (Distance: {distance_points:.0f}pts, Age: {age_hours/24:.1f}d)")
                        
                except Exception as e:
                    print(f"⚠️ Error processing order {order_id}: {e}")
                    continue
            
            if removed_count > 0:
                print(f"✅ Cleanup completed: {removed_count} orders removed")
            else:
                print("📋 No orders need cleanup")
                
            return removed_count
            
        except Exception as e:
            print(f"❌ Error in cleanup_far_orders: {e}")
            return 0
    
    def calculate_cleanup_distance(self):
        """คำนวณระยะห่างที่ควรลบ orders"""
        try:
            # Base distance = 15-20x grid spacing
            base_distance = self.grid_spacing * 15
            
            # ปรับตาม account size
            if self.base_lot >= 0.1:
                # Account ใหญ่ = เก็บ orders ไว้นานกว่า
                distance_multiplier = 1.5
            elif self.base_lot >= 0.05:
                # Account กลาง = ปกติ
                distance_multiplier = 1.0
            else:
                # Account เล็ก = ลบเร็วกว่า
                distance_multiplier = 0.8
                
            cleanup_distance = base_distance * distance_multiplier
            
            # ขั้นต่ำ 3000 points, สูงสุด 15000 points
            cleanup_distance = max(3000, min(cleanup_distance, 15000))
            
            print(f"📏 Cleanup distance: {cleanup_distance:.0f} points (Grid: {self.grid_spacing}, Lot: {self.base_lot})")
            return cleanup_distance
            
        except Exception as e:
            print(f"❌ Error calculating cleanup distance: {e}")
            return 5000  # Default fallback
    
    def cancel_single_order(self, order_id: int) -> bool:
        """ยกเลิก order เดียว"""
        try:
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order_id
            }
            
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return True
            else:
                error_msg = f"Failed to cancel order {order_id}"
                if result:
                    error_msg += f" - Code: {result.retcode}, Comment: {result.comment}"
                print(f"⚠️ {error_msg}")
                return False
                
        except Exception as e:
            print(f"❌ Error cancelling order {order_id}: {e}")
            return False
    
    def ensure_sufficient_grid_coverage(self):
        """ตรวจสอบและเพิ่ม grid coverage ใกล้ราคาปัจจุบัน"""
        try:
            current_price = self.get_current_price()
            coverage_range = self.grid_spacing * 10  # ครอบคลุม ±10 levels
            
            # นับ orders ใกล้ราคาปัจจุบัน
            nearby_buy_orders = []
            nearby_sell_orders = []
            
            for grid_level in self.pending_orders.values():
                distance = abs(grid_level.price - current_price)
                if distance <= coverage_range * self.point_value:
                    if grid_level.direction == "BUY":
                        nearby_buy_orders.append(grid_level)
                    else:
                        nearby_sell_orders.append(grid_level)
            
            print(f"📊 Current coverage: {len(nearby_buy_orders)} BUY, {len(nearby_sell_orders)} SELL orders nearby")
            
            # เพิ่ม orders ถ้าไม่เพียงพอ
            min_coverage = 5  # อย่างน้อย 5 orders แต่ละด้าน
            
            if len(nearby_buy_orders) < min_coverage:
                needed = min_coverage - len(nearby_buy_orders)
                self.add_nearby_buy_orders(needed, current_price)
                
            if len(nearby_sell_orders) < min_coverage:
                needed = min_coverage - len(nearby_sell_orders)
                self.add_nearby_sell_orders(needed, current_price)
                
        except Exception as e:
            print(f"❌ Error ensuring grid coverage: {e}")
    
    def add_nearby_sell_orders(self, current_price: float, imbalance_size: float):
        """เพิ่ม SELL orders ใกล้ราคาปัจจุบัน - FIXED VERSION"""
        try:
            # ✅ FIX: ใช้ระยะห่างใกล้ๆ
            nearby_distances = [100, 200, 300, 400, 500]  # 100-500 จุด
            
            # คำนวณจำนวน SELL ที่ต้องเพิ่ม
            needed_sell_exposure = min(abs(imbalance_size) * 0.6, 0.1)  # ไม่เกิน 0.1 lot
            lot_per_order = max(self.min_lot, needed_sell_exposure / 3)  # แบ่ง 3 orders
            
            print(f"   🎯 Adding SELL orders near ${current_price:.2f}")
            
            added_count = 0
            for distance_points in nearby_distances:
                if added_count >= 3:  # จำกัดไม่เกิน 3 orders
                    break
                    
                # ✅ FIX: คำนวณราคาจาก points อย่างถูกต้อง
                sell_price = current_price + (distance_points * 0.01)  # 1 point = $0.01
                
                print(f"   📍 Checking SELL @ ${sell_price:.2f} (distance: {distance_points} points)")
                
                # เช็คว่าไม่มี order ใกล้ๆ และไม่ไกลเกินไป
                if (not self.has_nearby_order(sell_price, "SELL", 50) and  # ห่าง 50 points
                    distance_points <= 500):  # ไม่เกิน 500 points
                    
                    if self.place_smart_rebalance_order("SELL", sell_price, lot_per_order):
                        added_count += 1
                        print(f"   ✅ Added SELL: {lot_per_order:.3f} lots @ ${sell_price:.2f}")
                            
            print(f"✅ Added {added_count} nearby SELL orders")
            
        except Exception as e:
            print(f"❌ Nearby SELL orders error: {e}")

    def add_nearby_buy_orders(self, current_price: float, imbalance_size: float):
        """เพิ่ม BUY orders ใกล้ราคาปัจจุบัน - FIXED VERSION"""
        try:
            # ✅ FIX: ใช้ระยะห่างใกล้ๆ
            nearby_distances = [100, 200, 300, 400, 500]  # 100-500 จุด
            
            needed_buy_exposure = min(abs(imbalance_size) * 0.6, 0.1)  # ไม่เกิน 0.1 lot
            lot_per_order = max(self.min_lot, needed_buy_exposure / 3)  # แบ่ง 3 orders
            
            print(f"   🎯 Adding BUY orders near ${current_price:.2f}")
            
            added_count = 0
            for distance_points in nearby_distances:
                if added_count >= 3:  # จำกัดไม่เกิน 3 orders
                    break
                    
                # ✅ FIX: คำนวณราคาจาก points อย่างถูกต้อง
                buy_price = current_price - (distance_points * 0.01)  # 1 point = $0.01
                
                print(f"   📍 Checking BUY @ ${buy_price:.2f} (distance: {distance_points} points)")
                
                # เช็คว่าไม่มี order ใกล้ๆ และไม่ไกลเกินไป
                if (not self.has_nearby_order(buy_price, "BUY", 50) and  # ห่าง 50 points
                    distance_points <= 500):  # ไม่เกิน 500 points
                    
                    if self.place_smart_rebalance_order("BUY", buy_price, lot_per_order):
                        added_count += 1
                        print(f"   ✅ Added BUY: {lot_per_order:.3f} lots @ ${buy_price:.2f}")
                            
            print(f"✅ Added {added_count} nearby BUY orders")
            
        except Exception as e:
            print(f"❌ Nearby BUY orders error: {e}")
    
    def weekly_maintenance(self):
        """การบำรุงรักษาประจำสัปดาห์"""
        try:
            print("🔧 === WEEKLY MAINTENANCE STARTED ===")
            
            # 1. ลบ orders เก่าและไกล
            removed = self.cleanup_far_orders()
            
            # 2. ตรวจสอบ grid coverage
            self.ensure_sufficient_grid_coverage()
            
            # 3. แสดงสถิติ orders
            self.display_order_statistics()
            
            print("✅ === WEEKLY MAINTENANCE COMPLETED ===")
            
        except Exception as e:
            print(f"❌ Weekly maintenance error: {e}")
    
    def display_order_statistics(self):
        """แสดงสถิติ orders"""
        try:
            current_price = self.get_current_price()
            
            buy_orders = [l for l in self.pending_orders.values() if l.direction == "BUY"]
            sell_orders = [l for l in self.pending_orders.values() if l.direction == "SELL"]
            
            if buy_orders:
                buy_distances = [abs(l.price - current_price) / self.point_value for l in buy_orders]
                avg_buy_distance = sum(buy_distances) / len(buy_distances)
                max_buy_distance = max(buy_distances)
            else:
                avg_buy_distance = 0
                max_buy_distance = 0
                
            if sell_orders:
                sell_distances = [abs(l.price - current_price) / self.point_value for l in sell_orders]
                avg_sell_distance = sum(sell_distances) / len(sell_distances)
                max_sell_distance = max(sell_distances)
            else:
                avg_sell_distance = 0
                max_sell_distance = 0
            
            print(f"📊 === ORDER STATISTICS ===")
            print(f"   📈 BUY Orders: {len(buy_orders)} (Avg: {avg_buy_distance:.0f}pts, Max: {max_buy_distance:.0f}pts)")
            print(f"   📉 SELL Orders: {len(sell_orders)} (Avg: {avg_sell_distance:.0f}pts, Max: {max_sell_distance:.0f}pts)")
            print(f"   📋 Total Pending: {len(self.pending_orders)}")
            print(f"   🎯 Active Positions: {len(self.active_positions)}")
            print(f"   💰 Current Price: ${current_price:.2f}")
            
        except Exception as e:
            print(f"❌ Error displaying statistics: {e}")

    def run_trading_loop(self):
        """AI Portfolio Trading Loop - เรียบง่าย"""
        
        loop_count = 0
        market_check_interval = 60
        last_market_status = self.is_market_open()
        last_cleanup = datetime.now()
        last_recovery_check = datetime.now()

        while self.trading_active and not self.emergency_stop_triggered:
            try:
                loop_count += 1
                
                # Recovery system check
                if (datetime.now() - last_recovery_check).total_seconds() >= 120:
                    self.check_recovery_system_status()
                    last_recovery_check = datetime.now()

                # Market status check
                if loop_count % market_check_interval == 0:
                    current_market_status = self.is_market_open()
                    
                    if current_market_status != last_market_status:
                        if current_market_status:
                            print("🟢 Market opened - AI portfolio active")
                        else:
                            print("🔴 Market closed - monitoring mode")
                        last_market_status = current_market_status

                # 🧹 Simple cleanup (ทุก 24 ชั่วโมง)
                if (datetime.now() - last_cleanup).total_seconds() >= 24 * 3600:
                    removed = self.cleanup_far_orders()
                    print(f"🧹 Daily cleanup: {removed} far orders removed")
                    last_cleanup = datetime.now()
                
                # 🚀 Core AI Portfolio Management
                self.update_current_price()
                
                if last_market_status:
                    # 1. Check filled orders (every loop)
                    self.check_filled_orders()
                    
                    # 2. Update PnL (every loop)
                    self.update_positions_pnl()
                    
                    # 3. 🧠 AI PORTFOLIO MANAGEMENT (ทุก 10 วินาที)
                    if (hasattr(self, 'smart_profit_enabled') and self.smart_profit_enabled and 
                        loop_count % 10 == 0):
                        try:
                            self.smart_profit_manager.run_smart_profit_management()
                        except Exception as smart_error:
                            print(f"❌ AI Portfolio error: {smart_error}")
                    
                    # 4. Performance metrics (ทุก 30 วินาที)
                    if loop_count % 30 == 0:
                        self.update_performance_metrics()
                        
                    # 5. Emergency monitoring (ทุก 60 วินาที)
                    if loop_count % 60 == 0:
                        self.check_emergency_conditions()
                        
                else:
                    # Market closed - อัพเดท PnL อย่างเดียว
                    self.update_positions_pnl()
                    
                    # AI Portfolio ยังทำงานได้แม้ตลาดปิด
                    if (hasattr(self, 'smart_profit_enabled') and self.smart_profit_enabled and 
                        loop_count % 30 == 0):
                        try:
                            self.smart_profit_manager.run_smart_profit_management()
                        except Exception as smart_error:
                            print(f"❌ AI Portfolio error (market closed): {smart_error}")
                
                # Status logging (ทุก 5 นาที)
                if loop_count % 300 == 0:
                    self.log_ai_portfolio_status(last_market_status)
                
                self.last_update = datetime.now()
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ AI Portfolio loop error: {e}")
                time.sleep(5)
                
        print("🔴 AI Portfolio trading loop ended")

    def log_ai_portfolio_status(self, market_open):
        """Log AI Portfolio status"""
        try:
            status = self.get_grid_status()
            market_emoji = "🟢" if market_open else "🔴"
            
            # AI Portfolio specific metrics
            active_positions = status['active_positions']
            pending_orders = status['pending_orders']
            total_pnl = status['total_pnl']
            drawdown = status['current_drawdown']
            
            # Smart Profit Status
            smart_status = ""
            if (hasattr(self, 'smart_profit_enabled') and self.smart_profit_enabled):
                try:
                    ai_status = self.smart_profit_manager.get_profit_management_status()
                    health = ai_status.get('portfolio_health', 50)
                    pairs_found = ai_status.get('profitable_pairs_found', 0)
                    hedges = ai_status.get('hedge_opportunities', 0)
                    smart_status = f", AI Health: {health}%, Pairs: {pairs_found}, Hedges: {hedges}"
                except Exception as e:
                    smart_status = ", AI: Error"
            
            print(f"🧠 AI Portfolio: {market_emoji} Market, {active_positions} positions, {pending_orders} pending, PnL: ${total_pnl:.2f}{smart_status}")
            
        except Exception as e:
            print(f"❌ AI Portfolio status log error: {e}")


    def check_recovery_system_status(self):
        """ตรวจสอบสถานะ Recovery System และแจ้งเตือน"""
        try:
            if (hasattr(self, 'smart_profit_enabled') and self.smart_profit_enabled and
                hasattr(self, 'smart_profit_manager')):
                
                recovery_status = self.smart_profit_manager.get_recovery_status()
                
                # แจ้งเตือนเมื่อ recovery ทำงานนาน
                if recovery_status.get('active') and 'elapsed_minutes' in recovery_status:
                    elapsed = recovery_status['elapsed_minutes']
                    
                    if elapsed >= 20:  # 20 นาที
                        print(f"💊 Recovery System: Running for {elapsed:.1f} minutes")
                        
                    elif elapsed >= 30:  # 30 นาที (timeout warning)
                        print(f"⚠️ Recovery System: Long running ({elapsed:.1f}min) - Consider manual intervention")
                
                # แจ้งเตือนเมื่อ portfolio ขาดทุนใกล้ trigger
                if not recovery_status.get('active'):
                    portfolio_analysis = self.smart_profit_manager.analyze_portfolio_positions()
                    total_pnl = portfolio_analysis.get('total_pnl', 0)
                    trigger_loss = recovery_status.get('trigger_loss', -50)
                    
                    # แจ้งเตือนที่ 80% ของ trigger
                    warning_threshold = trigger_loss * 0.8
                    if total_pnl <= warning_threshold:
                        print(f"⚠️ Portfolio approaching recovery trigger: ${total_pnl:.2f} (Trigger: ${trigger_loss})")
                        
        except Exception as e:
            print(f"❌ Recovery status check error: {e}")

    # 3. เพิ่ม method สำหรับ hedge order (ที่ recovery system ใช้)
    def place_hedge_order(self, direction: str, hedge_size: float) -> bool:
        """Place hedge order - สำหรับ Recovery System"""
        try:
            # Validate hedge size
            if hedge_size < self.min_lot:
                hedge_size = self.min_lot
                
            hedge_size = round(hedge_size / self.lot_step) * self.lot_step
            
            # Get current market price
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"❌ Cannot get tick data for recovery hedge")
                return False
                
            # Determine order type and price
            if direction == "BUY":
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
                
            # Prepare hedge request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.gold_symbol,
                "volume": hedge_size,
                "type": order_type,
                "price": price,
                "deviation": 30,  # Higher deviation for hedge
                "magic": self.magic_number,
                "comment": f"RECOVERY_HEDGE_{direction}_{int(time.time())}",
                "type_filling": self.order_filling_mode
            }
            
            # Execute hedge order
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"💊 Recovery hedge placed: {direction} {hedge_size:.3f} lots @ {price}")
                return True
            else:
                error_msg = f"Recovery hedge failed - Code: {result.retcode if result else 'None'}"
                if result:
                    error_msg += f", Comment: {result.comment}"
                print(f"❌ {error_msg}")
                return False
                
        except Exception as e:
            print(f"❌ Recovery hedge placement error: {e}")
            return False

    # 4. เพิ่ม method สำหรับปิด position (ที่ recovery system ใช้)
    def close_position_by_id(self, position_id: int) -> bool:
        """Close position by ID - สำหรับ Recovery System"""
        try:
            # Get position info
            positions = mt5.positions_get(ticket=position_id)
            if not positions:
                print(f"❌ Position {position_id} not found for recovery close")
                return False
                
            position = positions[0]
            
            # Verify it's our position
            if position.magic != self.magic_number:
                print(f"❌ Position {position_id} not owned by this system")
                return False
                
            # Get current market prices
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"❌ Cannot get tick data for recovery close")
                return False
                
            # Determine close parameters
            if position.type == mt5.POSITION_TYPE_BUY:
                trade_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                trade_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
                
            # Prepare close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.gold_symbol,
                "volume": position.volume,
                "type": trade_type,
                "position": position_id,
                "price": price,
                "deviation": 20,
                "magic": self.magic_number,
                "comment": f"RECOVERY_CLOSE_{position_id}",
                "type_filling": self.close_filling_mode
            }
            
            # Execute close
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"💊 Recovery close: Position {position_id} - PnL: ${position.profit:.2f}")
                
                # Update our tracking
                if position_id in self.active_positions:
                    del self.active_positions[position_id]
                    
                return True
            else:
                error_msg = f"Recovery close failed - Code: {result.retcode if result else 'None'}"
                if result:
                    error_msg += f", Comment: {result.comment}"
                print(f"❌ {error_msg}")
                return False
                
        except Exception as e:
            print(f"❌ Recovery close error: {e}")
            return False

    # 5. เพิ่ม method ดึงข้อมูล positions สำหรับ recovery
    def get_positions_for_recovery(self) -> List[Dict]:
        """ดึงข้อมูล positions สำหรับ Recovery System"""
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            if not positions:
                return []
                
            our_positions = [pos for pos in positions if pos.magic == self.magic_number]
            
            position_list = []
            for pos in our_positions:
                position_info = {
                    'position_id': pos.ticket,
                    'symbol': pos.symbol,
                    'direction': "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                    'lot_size': pos.volume,
                    'entry_price': pos.price_open,
                    'current_price': pos.price_current,
                    'pnl': pos.profit,
                    'entry_time': datetime.fromtimestamp(pos.time) if hasattr(pos, 'time') else datetime.now(),
                    'comment': pos.comment if hasattr(pos, 'comment') else ""
                }
                position_list.append(position_info)
                
            return position_list
            
        except Exception as e:
            print(f"❌ Get positions for recovery error: {e}")

    def check_critical_emergency_conditions(self):
        """Check only critical emergency conditions when market is closed"""
        
        try:
            # Check daily loss limit
            if self.total_pnl < -abs(self.daily_loss_limit):
                print(f"🚨 Daily loss limit exceeded: ${self.total_pnl:.2f} < -${self.daily_loss_limit}")
                self.emergency_stop("Daily loss limit exceeded")
                return
                
            # Check maximum drawdown (90% of survivability)
            survivability_limit = self.survivability * 0.9
            if self.current_drawdown > survivability_limit:
                print(f"🚨 Maximum drawdown approached: {self.current_drawdown:.0f} > {survivability_limit:.0f} points")
                self.emergency_stop("Maximum drawdown reached")
                return
                
            # Check account equity vs balance (critical loss)
            account_info = self.mt5_connector.get_account_info()
            if account_info:
                equity = account_info.get('equity', 0)
                balance = account_info.get('balance', 0)
                if balance > 0:
                    equity_ratio = equity / balance
                    if equity_ratio < 0.5:  # Lost 50% of account
                        print(f"🚨 Account equity critical: {equity_ratio*100:.1f}%")
                        self.emergency_stop("Critical account equity")
                        return
                        
        except Exception as e:
            print(f"❌ Error checking critical emergency conditions: {e}")
        
    def place_pending_orders_for_inactive_levels(self):
        """Place orders for grid levels that don't have active orders"""
        
        orders_placed = 0
        
        for grid_level in self.grid_levels:
            # Skip levels that already have orders or positions
            if (grid_level.status == PositionStatus.PENDING and grid_level.order_id in self.pending_orders) or \
               (grid_level.status == PositionStatus.ACTIVE):
                continue
                
            # Try to place order for inactive levels
            if grid_level.status in [PositionStatus.CANCELLED, PositionStatus.CLOSED] or not grid_level.order_id:
                order_result = self.place_pending_order(grid_level)
                if order_result:
                    grid_level.order_id = order_result
                    grid_level.status = PositionStatus.PENDING
                    self.pending_orders[order_result] = grid_level
                    orders_placed += 1
                    
        if orders_placed > 0:
            print(f"🆕 Placed {orders_placed} pending orders after market reopened")

    def calculate_net_exposure(self):
        """Calculate net exposure from active positions"""
        try:
            sell_exposure = sum(pos.lot_size for pos in self.active_positions.values() 
                            if pos.direction == "SELL")
            buy_exposure = sum(pos.lot_size for pos in self.active_positions.values() 
                            if pos.direction == "BUY")
            
            net_exposure = sell_exposure - buy_exposure
            
            print(f"📊 Exposure: SELL {sell_exposure:.3f}, BUY {buy_exposure:.3f}, NET {net_exposure:.3f}")
            return net_exposure
            
        except Exception as e:
            print(f"❌ Error calculating exposure: {e}")
            return 0.0
            
    def has_active_hedge(self):
        """Check if there's already an active hedge position"""
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            if positions:
                hedge_positions = [pos for pos in positions 
                                if pos.magic == self.magic_number and 
                                "HEDGE" in pos.comment]
                return len(hedge_positions) > 0
            return False
            
        except Exception as e:
            print(f"❌ Error checking hedge: {e}")
            return False
            
    def place_hedge_order(self, direction: str, hedge_size: float):
        """Place hedge order - REAL TRADING"""
        try:
            # Validate hedge size
            if hedge_size < self.min_lot:
                hedge_size = self.min_lot
                
            hedge_size = round(hedge_size / self.lot_step) * self.lot_step
            
            # Get current market price
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"❌ Cannot get tick data for hedge")
                return False
                
            # Determine order type and price
            if direction == "BUY":
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
                
            # Prepare hedge request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.gold_symbol,
                "volume": hedge_size,
                "type": order_type,
                "price": price,
                "deviation": 30,  # Higher deviation for hedge
                "magic": self.magic_number,
                "comment": f"HEDGE_{direction}_{int(time.time())}",
                "type_filling": self.order_filling_mode
            }
            
            # Execute hedge order
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"🛡️ Hedge placed: {direction} {hedge_size:.3f} lots @ {price}")
                return True
            else:
                error_msg = f"Hedge failed - Code: {result.retcode if result else 'None'}"
                if result:
                    error_msg += f", Comment: {result.comment}"
                print(f"❌ {error_msg}")
                return False
                
        except Exception as e:
            print(f"❌ Hedge placement error: {e}")
            return False
            
    def get_ai_portfolio_summary(self) -> Dict:
        """สรุป AI Portfolio performance"""
        
        try:
            if not hasattr(self, 'smart_profit_manager'):
                return {'error': 'AI Portfolio not initialized'}
                
            # Get AI status
            ai_status = self.smart_profit_manager.get_profit_management_status()
            grid_status = self.get_grid_status()
            
            return {
                'ai_mode': 'ACTIVE' if self.smart_profit_enabled else 'INACTIVE',
                'portfolio_health': ai_status.get('portfolio_health', 50),
                'total_positions': grid_status['active_positions'],
                'total_pnl': grid_status['total_pnl'],
                'profitable_pairs_available': ai_status.get('profitable_pairs_found', 0),
                'hedge_opportunities': ai_status.get('hedge_opportunities', 0),
                'ai_actions_today': getattr(self, 'ai_actions_count', 0),
                'last_ai_action': getattr(self, 'last_ai_action_time', 'None'),
                'performance_score': self.calculate_ai_performance_score(ai_status, grid_status)
            }
            
        except Exception as e:
            return {'error': str(e)}

    def calculate_ai_performance_score(self, ai_status, grid_status) -> int:
        """คำนวณ AI performance score (0-100)"""
        
        try:
            health = ai_status.get('portfolio_health', 50)
            pnl = grid_status.get('total_pnl', 0)
            positions = grid_status.get('active_positions', 0)
            
            # Base score from portfolio health
            score = health
            
            # Bonus for positive PnL
            if pnl > 0:
                score += min(20, pnl)  # Max 20 bonus points
            
            # Penalty for too many positions (inefficient)
            if positions > 10:
                score -= (positions - 10) * 2  # -2 points per excess position
                
            # Bounds
            return max(0, min(int(score), 100))
            
        except Exception as e:
            print(f"❌ AI performance score error: {e}")
            return 50
                
    def close_hedge_positions(self):
        """Close all hedge positions"""
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            if not positions:
                return
                
            hedge_positions = [pos for pos in positions 
                            if pos.magic == self.magic_number and 
                            "HEDGE" in pos.comment]
            
            closed_count = 0
            for position in hedge_positions:
                
                # Get current market prices
                tick = mt5.symbol_info_tick(self.gold_symbol)
                if not tick:
                    continue
                    
                # Determine close parameters
                if position.type == mt5.POSITION_TYPE_BUY:
                    trade_type = mt5.ORDER_TYPE_SELL
                    price = tick.bid
                else:
                    trade_type = mt5.ORDER_TYPE_BUY
                    price = tick.ask
                    
                # Close hedge position
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.gold_symbol,
                    "volume": position.volume,
                    "type": trade_type,
                    "position": position.ticket,
                    "price": price,
                    "deviation": 30,
                    "magic": self.magic_number,
                    "comment": "HEDGE_CLOSE",
                    "type_filling": self.close_filling_mode
                }
                
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    closed_count += 1
                    print(f"✅ Hedge closed: {position.ticket} - PnL: ${position.profit:.2f}")
                    
            print(f"🔄 Closed {closed_count} hedge positions")
            
        except Exception as e:
            print(f"❌ Error closing hedge positions: {e}")

    def calculate_rebalancing_targets(self):
        """คำนวณเป้าหมาย orders ตามขนาดเงินทุน"""
        
        account_info = self.mt5_connector.get_account_info()
        balance = account_info.get('balance', 1000) if account_info else 1000
        
        # Base targets
        if balance >= 50000:
            # เงินทุนใหญ่มาก - coverage เยอะ
            self.target_orders = {
                'near_buy': 10, 'near_sell': 10,
                'medium_buy': 8, 'medium_sell': 8, 
                'far_buy': 4, 'far_sell': 4
            }
        elif balance >= 25000:
            # เงินทุนใหญ่ - coverage ปานกลาง
            self.target_orders = {
                'near_buy': 8, 'near_sell': 8,
                'medium_buy': 6, 'medium_sell': 6,
                'far_buy': 3, 'far_sell': 3
            }
        elif balance >= 10000:
            # เงินทุนกลาง - coverage มาตรฐาน
            self.target_orders = {
                'near_buy': 6, 'near_sell': 6,
                'medium_buy': 4, 'medium_sell': 4,
                'far_buy': 2, 'far_sell': 2
            }
        elif balance >= 5000:
            # เงินทุนเล็ก - coverage น้อย
            self.target_orders = {
                'near_buy': 4, 'near_sell': 4,
                'medium_buy': 3, 'medium_sell': 3,
                'far_buy': 2, 'far_sell': 2
            }
        else:
            # เงินทุนจิ๋ว - coverage ขั้นต่ำ
            self.target_orders = {
                'near_buy': 3, 'near_sell': 3,
                'medium_buy': 2, 'medium_sell': 2,
                'far_buy': 1, 'far_sell': 1
            }
        
        print(f"🎯 Rebalancing targets for ${balance:,.0f}: {self.target_orders}")

    def analyze_current_grid_distribution(self) -> Dict:
        """วิเคราะห์การกระจายตัวของ orders ปัจจุบัน"""
        
        current_price = self.get_current_price()
        
        # Smart percentage-based zones
        if current_price >= 3000:  # Gold high range
            near_pct, medium_pct, far_pct = 0.004, 0.02, 0.06
        elif current_price >= 2000:  # Gold medium range  
            near_pct, medium_pct, far_pct = 0.005, 0.025, 0.07
        else:  # Gold low range
            near_pct, medium_pct, far_pct = 0.006, 0.03, 0.08
        
        # Convert to points
        near_zone = (current_price * near_pct) / self.point_value
        medium_zone = (current_price * medium_pct) / self.point_value
        far_zone = (current_price * far_pct) / self.point_value
        
        # Count orders in each zone
        distribution = {
            'near_buy': 0, 'near_sell': 0,
            'medium_buy': 0, 'medium_sell': 0,
            'far_buy': 0, 'far_sell': 0,
            'very_far_buy': 0, 'very_far_sell': 0  # >far_zone
        }
        
        for grid_level in self.pending_orders.values():
            distance = abs(grid_level.price - current_price)
            distance_points = distance / self.point_value
            
            # Categorize by distance and direction
            if grid_level.direction == "BUY":
                if distance_points <= near_zone:
                    distribution['near_buy'] += 1
                elif distance_points <= medium_zone:
                    distribution['medium_buy'] += 1
                elif distance_points <= far_zone:
                    distribution['far_buy'] += 1
                else:
                    distribution['very_far_buy'] += 1
            else:  # SELL
                if distance_points <= near_zone:
                    distribution['near_sell'] += 1
                elif distance_points <= medium_zone:
                    distribution['medium_sell'] += 1
                elif distance_points <= far_zone:
                    distribution['far_sell'] += 1
                else:
                    distribution['very_far_sell'] += 1
        
        return {
            'distribution': distribution,
            'current_price': current_price,
            'total_orders': len(self.pending_orders),
            'zones': {
                'near': near_zone,
                'medium': medium_zone, 
                'far': far_zone
            }
        }


    def remove_very_far_orders(self, current_price: float) -> int:
        """ลบ orders ที่ไกลมากๆ (>far_zone)"""
        
        removed_count = 0
        very_far_threshold = self.far_zone_levels * self.grid_spacing  # 9000 points
        
        for order_id, grid_level in list(self.pending_orders.items()):
            distance = abs(grid_level.price - current_price)
            distance_points = distance / self.point_value
            
            # ลบถ้าไกลเกิน threshold และเก่าเกิน 1 ชั่วโมง
            if (distance_points > very_far_threshold and 
                hasattr(grid_level, 'entry_time') and grid_level.entry_time and
                (datetime.now() - grid_level.entry_time).total_seconds() > 3600):
                
                if self.cancel_single_order(order_id):
                    del self.pending_orders[order_id]
                    grid_level.status = PositionStatus.CANCELLED
                    removed_count += 1
                    print(f"   🗑️ Removed very far order: {grid_level.level_id} @ {grid_level.price:.2f} ({distance_points:.0f}pts)")
        
        return removed_count

    def add_near_zone_orders(self, current_price: float, distribution: Dict) -> int:
        """เพิ่ม orders ในโซนใกล้ถ้าไม่เพียงพอ"""
        
        added_count = 0
        near_zone = self.near_zone_levels * self.grid_spacing
        
        # เช็ค BUY orders ในโซนใกล้
        buy_deficit = self.target_orders['near_buy'] - distribution['near_buy']
        if buy_deficit > 0:
            # เพิ่ม BUY orders ทีละ 1-2 ตัว
            to_add = min(buy_deficit, 2)  # ไม่เกิน 2 orders ต่อรอบ
            
            for i in range(to_add):
                # หาตำแหน่งที่เหมาะสม
                level = i + distribution['near_buy'] + 1
                buy_price = current_price - (level * self.grid_spacing * self.point_value)
                
                if self.add_single_grid_order("BUY", buy_price, f"NEAR_BUY_{int(time.time())}_{i}"):
                    added_count += 1
        
        # เช็ค SELL orders ในโซนใกล้  
        sell_deficit = self.target_orders['near_sell'] - distribution['near_sell']
        if sell_deficit > 0:
            to_add = min(sell_deficit, 2)
            
            for i in range(to_add):
                level = i + distribution['near_sell'] + 1
                sell_price = current_price + (level * self.grid_spacing * self.point_value)
                
                if self.add_single_grid_order("SELL", sell_price, f"NEAR_SELL_{int(time.time())}_{i}"):
                    added_count += 1
        
        return added_count

    def adjust_medium_zone_orders(self, current_price: float, distribution: Dict) -> int:
        """ปรับ orders ในโซน medium ถ้าจำเป็น"""
        
        adjusted_count = 0
        
        # ถ้า medium zone มี orders น้อยเกินไป และ near zone เต็มแล้ว
        buy_medium_deficit = self.target_orders['medium_buy'] - distribution['medium_buy']
        sell_medium_deficit = self.target_orders['medium_sell'] - distribution['medium_sell']
        
        if (buy_medium_deficit > 0 and distribution['near_buy'] >= self.target_orders['near_buy']):
            # เพิ่ม 1 BUY order ใน medium zone
            level = distribution['near_buy'] + distribution['medium_buy'] + 5  # ห่างจาก near zone
            buy_price = current_price - (level * self.grid_spacing * self.point_value)
            
            if self.add_single_grid_order("BUY", buy_price, f"MED_BUY_{int(time.time())}"):
                adjusted_count += 1
        
        if (sell_medium_deficit > 0 and distribution['near_sell'] >= self.target_orders['near_sell']):
            level = distribution['near_sell'] + distribution['medium_sell'] + 5
            sell_price = current_price + (level * self.grid_spacing * self.point_value)
            
            if self.add_single_grid_order("SELL", sell_price, f"MED_SELL_{int(time.time())}"):
                adjusted_count += 1
        
        return adjusted_count

    def add_single_grid_order(self, direction: str, price: float, level_id: str) -> bool:
        """เพิ่ม order เดียว"""
        
        try:
            # เช็คว่าไม่ใกล้ orders อื่นเกินไป
            min_distance = self.grid_spacing * self.point_value * 0.8  # 80% ของ grid spacing
            
            for existing_level in self.pending_orders.values():
                if (existing_level.direction == direction and 
                    abs(existing_level.price - price) < min_distance):
                    return False  # ใกล้เกินไป
            
            # สร้าง grid level ใหม่
            new_level = GridLevel(
                level_id=level_id,
                price=round(price, 5),
                lot_size=self.calculate_level_lot_size(1),  # ใช้ lot size พื้นฐาน
                direction=direction,
                status=PositionStatus.PENDING,
                entry_time=datetime.now()
            )
            
            # วาง order
            order_result = self.place_pending_order(new_level)
            if order_result:
                new_level.order_id = order_result
                self.grid_levels.append(new_level)
                self.pending_orders[order_result] = new_level
                print(f"   ✅ Added {direction} order: {level_id} @ {price:.2f}")
                return True
            
        except Exception as e:
            print(f"   ❌ Failed to add order: {e}")
            
        return False

    def smart_replacement_on_close(self, closed_position: GridLevel):
        """Smart Replacement เมื่อปิด position - วางใกล้ราคาปัจจุบัน"""
        
        try:
            current_price = self.get_current_price()
            
            # แทนที่จะวาง order ที่ราคาเดิม
            # วางในโซนใกล้ราคาปัจจุบัน
            
            if closed_position.direction == "BUY":
                # BUY position ปิดแล้ว -> วาง BUY order ใหม่ใกล้ current price
                # หาตำแหน่งที่เหมาะสมใกล้ราคาปัจจุบัน
                target_levels = [2, 3, 4, 5]  # ลองวางที่ level 2-5 ใกล้ current
                
                for level in target_levels:
                    new_price = current_price - (level * self.grid_spacing * self.point_value)
                    
                    # เช็คว่าไม่มี order ใกล้ๆ แล้ว
                    if not self.has_nearby_order("BUY", new_price):
                        self.add_single_grid_order("BUY", new_price, f"REPL_BUY_{int(time.time())}")
                        print(f"🔄 Smart replacement: BUY @ {new_price:.2f} (was @ {closed_position.price:.2f})")
                        break
                        
            else:  # SELL position
                target_levels = [2, 3, 4, 5]
                
                for level in target_levels:
                    new_price = current_price + (level * self.grid_spacing * self.point_value)
                    
                    if not self.has_nearby_order("SELL", new_price):
                        self.add_single_grid_order("SELL", new_price, f"REPL_SELL_{int(time.time())}")
                        print(f"🔄 Smart replacement: SELL @ {new_price:.2f} (was @ {closed_position.price:.2f})")
                        break
        
        except Exception as e:
            print(f"❌ Smart replacement error: {e}")
    
    def add_balanced_nearby_orders(self, current_price: float):
        """เพิ่ม orders ใกล้ราคาปัจจุบัน - FIXED VERSION (ใกล้มาก)"""
        try:
            # 🚀 ใช้ระยะห่างใกล้มากๆ
            nearby_distances = [50, 80, 120, 160, 200]  # ลดจาก [150, 250, 350] เป็นใกล้มาก
            lot_size = max(self.min_lot, self.base_lot * 0.5)
            
            print(f"   🎯 Adding ULTRA-CLOSE orders near ${current_price:.2f}")
            
            added_count = 0
            for distance_points in nearby_distances:
                if added_count >= 3:  # จำกัด 3 orders
                    break
                    
                # คำนวณราคา BUY และ SELL
                buy_price = current_price - (distance_points * 0.01)   # ใกล้มาก
                sell_price = current_price + (distance_points * 0.01)  # ใกล้มาก
                
                print(f"   📍 Checking ULTRA-CLOSE pair @ BUY ${buy_price:.2f} / SELL ${sell_price:.2f}")
                
                # เพิ่ม BUY order
                if not self.has_nearby_order(buy_price, "BUY", 25):  # ลดจาก 50 เป็น 25
                    if self.place_smart_rebalance_order("BUY", buy_price, lot_size):
                        added_count += 1
                        print(f"   ✅ Added ULTRA-CLOSE BUY: {lot_size:.3f} lots @ ${buy_price:.2f}")
                    
                # เพิ่ม SELL order
                if not self.has_nearby_order(sell_price, "SELL", 25):  # ลดจาก 50 เป็น 25
                    if self.place_smart_rebalance_order("SELL", sell_price, lot_size):
                        added_count += 1
                        print(f"   ✅ Added ULTRA-CLOSE SELL: {lot_size:.3f} lots @ ${sell_price:.2f}")
                    
            print(f"✅ Added {added_count} ULTRA-CLOSE orders")
            
        except Exception as e:
            print(f"❌ ULTRA-CLOSE orders error: {e}")

    def has_nearby_order(self, price: float, direction: str, min_distance_points: int = 80) -> bool:
        """แก้ไข method ให้รองรับ 2-3 parameters"""
        try:
            # ✅ แก้ไข: รองรับทั้ง 2 และ 3 parameters
            min_distance = min_distance_points * 0.01  # แปลง points เป็น dollars
            
            # เช็ค pending orders
            for grid_level in self.pending_orders.values():
                if (grid_level.direction == direction and 
                    abs(grid_level.price - price) < min_distance):
                    return True
                    
            # เช็ค active positions
            for grid_level in self.active_positions.values():
                if (grid_level.direction == direction and 
                    abs(grid_level.price - price) < min_distance):
                    return True
                    
            return False
            
        except Exception as e:
            print(f"❌ Nearby order check error: {e}")
            return True  # ถ้า error ให้ถือว่ามี order แล้ว (ป้องกัน)

    # แก้ไขใน ai_gold_grid.py - เพิ่ม method ใหม่
    def force_create_tight_grid(self):
        """สร้าง grid แน่นๆ ใกล้ราคาปัจจุบัน"""
        try:
            current_price = self.get_current_price()
            tight_spacing = 100  # แน่นมาก 100 จุด
            
            print(f"🚀 Force creating tight grid @ ${current_price:.2f}")
            
            # สร้าง 4 คู่ใกล้ๆ
            for i in range(1, 5):  # 1, 2, 3, 4
                # BUY orders
                buy_price = current_price - (tight_spacing * i * 0.01)
                if not self.has_nearby_order(buy_price, "BUY"):
                    self.place_smart_rebalance_order("BUY", buy_price, self.base_lot)
                
                # SELL orders  
                sell_price = current_price + (tight_spacing * i * 0.01)
                if not self.has_nearby_order(sell_price, "SELL"):
                    self.place_smart_rebalance_order("SELL", sell_price, self.base_lot)
                    
            print(f"✅ Tight grid created with {tight_spacing} points spacing")
            
        except Exception as e:
            print(f"❌ Force tight grid error: {e}")

    def get_current_price(self) -> float:
        """Get current price from MT5"""
        try:
            price_data = self.mt5_connector.get_current_price()
            return price_data['bid'] if price_data else self.current_price
        except:
            return self.current_price
            
    def calculate_grid_efficiency(self) -> Dict:
        """Calculate grid trading efficiency metrics"""
        
        try:
            # Calculate price range coverage
            if self.grid_levels:
                min_price = min(level.price for level in self.grid_levels)
                max_price = max(level.price for level in self.grid_levels)
                price_range = max_price - min_price
                price_range_points = price_range / self.point_value
            else:
                price_range_points = 0
                
            # Calculate capital efficiency
            total_margin_used = sum(
                self.mt5_connector.calculate_margin_required(level.lot_size) 
                for level in self.active_positions.values()
            )
            
            account_info = self.mt5_connector.get_account_info()
            capital_efficiency = (total_margin_used / account_info['balance']) * 100 if account_info else 0
            
            # Calculate profit per trade efficiency
            avg_profit_per_trade = (self.realized_pnl / self.trades_closed) if self.trades_closed > 0 else 0
            
            return {
                'price_range_coverage': round(price_range_points, 0),
                'capital_efficiency': round(capital_efficiency, 1),
                'avg_profit_per_trade': round(avg_profit_per_trade, 2),
                'grid_utilization': round((len(self.active_positions) / len(self.grid_levels)) * 100, 1) if self.grid_levels else 0,
                'survivability_usage': round((self.current_drawdown / self.survivability) * 100, 1),
                'risk_reward_ratio': round(abs(self.largest_win / self.largest_loss), 2) if self.largest_loss < 0 else 0
            }
        except Exception as e:
            print(f"❌ Error calculating efficiency: {e}")
            return {}
            
    def generate_trading_report(self) -> str:
        """Generate comprehensive trading report"""
        
        try:
            status = self.get_grid_status()
            efficiency = self.calculate_grid_efficiency()
            
            report = f"""
🤖 AI GOLD GRID TRADING REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

📊 CURRENT STATUS:
   Trading Active: {'✅ YES' if status['trading_active'] else '❌ NO'}
   Symbol: {status['gold_symbol']}
   Current Price: ${status['current_price']:.2f}
   Starting Price: ${status['starting_price']:.2f}
   
💰 PROFIT & LOSS:
   Total PnL: ${status['total_pnl']:,.2f}
   Unrealized PnL: ${status['unrealized_pnl']:,.2f}
   Realized PnL: ${status['realized_pnl']:,.2f}
   
📈 POSITION OVERVIEW:
   Active Positions: {status['active_positions']}
   Pending Orders: {status['pending_orders']}
   Total Grid Levels: {status['total_grid_levels']}
   
⚠️ RISK METRICS:
   Current Drawdown: {status['current_drawdown']:,.0f} points
   Maximum Drawdown: {status['max_drawdown']:,.0f} points
   Survivability Used: {status['survivability_used']:.1f}%
   Emergency Stop: {'🚨 TRIGGERED' if status['emergency_stop'] else '✅ NORMAL'}
   
📊 PERFORMANCE METRICS:
   Trades Opened: {status['trades_opened']}
   Trades Closed: {status['trades_closed']}
   Win Rate: {status['win_rate']:.1f}%
   Largest Win: ${status['largest_win']:,.2f}
   Largest Loss: ${status['largest_loss']:,.2f}
   
⚡ EFFICIENCY ANALYSIS:
   Price Range Coverage: {efficiency.get('price_range_coverage', 0):,.0f} points
   Capital Efficiency: {efficiency.get('capital_efficiency', 0):.1f}%
   Grid Utilization: {efficiency.get('grid_utilization', 0):.1f}%
   Avg Profit/Trade: ${efficiency.get('avg_profit_per_trade', 0):,.2f}
   Risk/Reward Ratio: {efficiency.get('risk_reward_ratio', 0):.2f}
   
🎯 GRID CONFIGURATION:
   Base Lot Size: {self.base_lot:.3f}
   Grid Spacing: {self.grid_spacing} points
   Max Levels: {self.max_levels}
   Survivability: {self.survivability:,.0f} points
   Magic Number: {self.magic_number}
   
{'='*60}
🏆 AI GOLD GRID TRADING SYSTEM - LIVE TRADING ENGINE
"""
            
            return report
            
        except Exception as e:
            return f"❌ Error generating report: {e}"
            
    def get_real_time_stats(self) -> Dict:
        """Get real-time trading statistics"""
        
        try:
            # Get current account info
            account_info = self.mt5_connector.get_account_info()
            
            # Calculate real-time metrics
            total_exposure = sum(pos.lot_size for pos in self.active_positions.values())
            avg_entry_price = sum(pos.price * pos.lot_size for pos in self.active_positions.values()) / total_exposure if total_exposure > 0 else 0
            
            return {
                'account_balance': account_info.get('balance', 0) if account_info else 0,
                'account_equity': account_info.get('equity', 0) if account_info else 0,
                'margin_level': account_info.get('margin_level', 0) if account_info else 0,
                'free_margin': account_info.get('free_margin', 0) if account_info else 0,
                'total_exposure_lots': round(total_exposure, 3),
                'average_entry_price': round(avg_entry_price, 2),
                'unrealized_pnl_percentage': round((self.unrealized_pnl / account_info.get('balance', 1)) * 100, 2) if account_info else 0,
                'grid_coverage_points': len(self.grid_levels) * self.grid_spacing if self.grid_levels else 0,
                'system_uptime_minutes': (datetime.now() - self.last_update).total_seconds() / 60
            }
        except Exception as e:
            print(f"❌ Error getting real-time stats: {e}")
            return {}
            
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            if self.trading_active:
                print("🛑 Grid system cleanup - stopping trading")
                self.stop_trading()
        except:
            pass

# Test function for real trading mode
def test_ai_gold_grid_real():
    """Test the AI Gold Grid system in REAL mode"""
    
    print("🚨 AI Gold Grid REAL TRADING MODE - USE WITH CAUTION!")
    print("="*60)
    
    # Test survivability parameters
    test_params = {
        'base_lot': 0.05,
        'grid_spacing': 300,
        'max_levels': 67,
        'survivability': 20100,
        'realistic_survivability': 18500,
        'account_balance': 10000
    }
    
    # Test config
    test_config = {
        'daily_loss_limit': 500,
        'target_survivability': 20000
    }
    
    print("⚠️ This test requires:")
    print("   1. Active MT5 connection")
    print("   2. Sufficient account balance")  
    print("   3. Gold symbol available")
    print("   4. Trading permissions enabled")
    
    print(f"\n🔧 Real Trading Features:")
    print("   ✅ Place actual pending orders")
    print("   ✅ Monitor real position fills")
    print("   ✅ Calculate real PnL")
    print("   ✅ Emergency stop system")
    print("   ✅ Real-time risk management")
    
    print(f"\n🛡️ Safety Features:")
    print("   ✅ Magic number isolation")
    print("   ✅ Daily loss limits")
    print("   ✅ Margin level monitoring")
    print("   ✅ Emergency close all")
    
    print(f"\n📊 Test Parameters:")
    print(f"   Base Lot: {test_params['base_lot']}")
    print(f"   Grid Spacing: {test_params['grid_spacing']} points")
    print(f"   Max Levels: {test_params['max_levels']}")
    print(f"   Survivability: {test_params['survivability']:,} points")
    print(f"   Daily Loss Limit: ${test_config['daily_loss_limit']}")
    
    print("\n" + "="*60)
    print("🚀 Ready for LIVE TRADING!")
    print("⚠️ Remember: This will place REAL orders with REAL money!")

if __name__ == "__main__":
    test_ai_gold_grid_real()