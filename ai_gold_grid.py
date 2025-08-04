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
        
        # Magic number for identifying our orders
        self.magic_number = 999888777  # Unique magic number
        
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
        
        print(f"🤖 AI Gold Grid initialized for {self.gold_symbol}")
        print(f"   🎯 Base Lot: {self.base_lot}")
        print(f"   📏 Grid Spacing: {self.grid_spacing} points")
        print(f"   📊 Max Levels: {self.max_levels}")
        print(f"   🛡️ Realistic Survivability: {self.survivability:,.0f} points")
        print(f"   ⚙️ Broker Min Lot: {self.min_lot}")
        print(f"   🔄 Filling Mode: {self.filling_mode_name}")
        
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
        """Initialize the grid trading system"""
        try:
            # Check if market is open
            if not self.is_market_open():
                print("⚠️ Warning: Market appears to be closed")
                print("   Grid will be initialized but orders may fail until market opens")
            
            # Get current price
            price_data = self.mt5_connector.get_current_price()
            if not price_data:
                raise Exception("Failed to get current price - market may be closed")
                
            self.starting_price = price_data['bid']
            self.current_price = self.starting_price
            
            print(f"🚀 Initializing grid at price: {self.starting_price}")
            
            # Create grid levels
            self.create_grid_levels(starting_direction)
            
            # Place initial pending orders
            placed_orders = self.place_initial_orders()
            
            if placed_orders == 0:
                print("⚠️ Warning: No orders were placed successfully")
                print("   This is normal if the market is closed")
                print("   Orders will be placed when market reopens")
            
            print(f"✅ Grid initialized with {len(self.grid_levels)} levels")
            print(f"📋 Successfully placed {placed_orders} orders")
            
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
            
    def create_grid_levels(self, direction: GridDirection):
        """Create grid level structure"""
        self.grid_levels = []
        current_time = datetime.now()
        
        if direction == GridDirection.BIDIRECTIONAL:
            # Create buy levels below current price
            for i in range(1, self.max_levels + 1):
                buy_price = self.starting_price - (i * self.grid_spacing * self.point_value)
                buy_level = GridLevel(
                    level_id=f"BUY_{i}",
                    price=round(buy_price, 5),
                    lot_size=self.calculate_level_lot_size(i),
                    direction="BUY",
                    status=PositionStatus.PENDING,
                    entry_time=current_time  # เพิ่ม timestamp
                )
                self.grid_levels.append(buy_level)
                
            # Create sell levels above current price
            for i in range(1, self.max_levels + 1):
                sell_price = self.starting_price + (i * self.grid_spacing * self.point_value)
                sell_level = GridLevel(
                    level_id=f"SELL_{i}",
                    price=round(sell_price, 5),
                    lot_size=self.calculate_level_lot_size(i),
                    direction="SELL",
                    status=PositionStatus.PENDING,
                    entry_time=current_time  # เพิ่ม timestamp
                )
                self.grid_levels.append(sell_level)
                
        elif direction == GridDirection.BUY_GRID:
            # Only buy levels below current price
            for i in range(1, self.max_levels + 1):
                buy_price = self.starting_price - (i * self.grid_spacing * self.point_value)
                buy_level = GridLevel(
                    level_id=f"BUY_{i}",
                    price=round(buy_price, 5),
                    lot_size=self.calculate_level_lot_size(i),
                    direction="BUY",
                    status=PositionStatus.PENDING,
                    entry_time=current_time
                )
                self.grid_levels.append(buy_level)
                
        elif direction == GridDirection.SELL_GRID:
            # Only sell levels above current price
            for i in range(1, self.max_levels + 1):
                sell_price = self.starting_price + (i * self.grid_spacing * self.point_value)
                sell_level = GridLevel(
                    level_id=f"SELL_{i}",
                    price=round(sell_price, 5),
                    lot_size=self.calculate_level_lot_size(i),
                    direction="SELL",
                    status=PositionStatus.PENDING,
                    entry_time=current_time
                )
                self.grid_levels.append(sell_level)
                
    def calculate_level_lot_size(self, level: int) -> float:
        """Calculate lot size for specific grid level with AI optimization and broker constraints"""
        
        # Base lot size
        lot_size = self.base_lot
        
        # AI-enhanced lot sizing based on level
        if level <= 3:
            # First 3 levels - standard size
            multiplier = 1.0
        elif level <= 6:
            # Levels 4-6 - slight increase
            multiplier = 1.1
        elif level <= 10:
            # Levels 7-10 - moderate increase
            multiplier = 1.2
        else:
            # Higher levels - conservative increase
            multiplier = 1.3
            
        calculated_lot = lot_size * multiplier
        
        # Apply broker constraints
        calculated_lot = max(calculated_lot, self.min_lot)
        
        # Round to lot step
        calculated_lot = round(calculated_lot / self.lot_step) * self.lot_step
        
        # Ensure within broker limits
        max_lot = self.symbol_info.get('volume_max', 100.0)
        calculated_lot = min(calculated_lot, max_lot)
        
        return calculated_lot
        
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
        """Place a pending order for grid level - REAL TRADING with Smart Filling"""
        
        try:
            # Get current market price for order type determination
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"❌ Cannot get tick data for {self.gold_symbol} - market may be closed")
                return None
                
            current_bid = tick.bid
            current_ask = tick.ask
            
            # Check if market is open
            if not self.is_market_open():
                print(f"⚠️ Market closed - order {grid_level.level_id} will be retried when market opens")
                return None
            
            # Determine order type based on direction and price
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
                    
            # Prepare order request with smart filling mode
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": self.gold_symbol,
                "volume": grid_level.lot_size,
                "type": order_type,
                "price": price,
                "deviation": 20,  # 20 point deviation
                "magic": self.magic_number,
                "comment": f"AIGrid_{grid_level.level_id}",
                "type_time": mt5.ORDER_TIME_GTC,  # Good Till Cancelled
                "type_filling": self.order_filling_mode  # Smart filling mode
            }
            
            # Send order to broker
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return result.order
            else:
                # Handle specific error codes and retry with different filling modes
                if result and result.retcode == 10030:  # Unsupported filling mode
                    print(f"🔄 Retrying {grid_level.level_id} with different filling mode")
                    return self.retry_order_with_different_filling(grid_level, request)
                elif result:
                    if result.retcode == 10018:  # Market closed
                        print(f"🕒 Market closed - {grid_level.level_id} will be placed when market opens")
                    elif result.retcode == 10004:  # Requote
                        print(f"📈 Price changed - retrying {grid_level.level_id}")
                    elif result.retcode == 10006:  # Invalid price
                        print(f"💰 Invalid price for {grid_level.level_id} - {grid_level.price}")
                    else:
                        print(f"❌ Order failed {grid_level.level_id} - Code: {result.retcode}, Comment: {result.comment}")
                else:
                    print(f"❌ No response for order {grid_level.level_id}")
                return None
                
        except Exception as e:
            print(f"❌ Order placement exception for {grid_level.level_id}: {e}")
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
        """Check for filled pending orders and convert to positions - REAL TRADING"""
        
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
                    # Order has been filled or cancelled
                    position = self.find_position_by_magic_and_comment(f"AIGrid_{grid_level.level_id}")
                    
                    if position:
                        # Order was filled and became a position
                        grid_level.status = PositionStatus.ACTIVE
                        grid_level.position_id = position.ticket
                        grid_level.entry_time = datetime.now()
                        
                        # Store actual entry price (may differ from order price due to slippage)
                        grid_level.price = position.price_open
                        
                        self.active_positions[position.ticket] = grid_level
                        del self.pending_orders[order_id]
                        
                        self.trades_opened += 1
                        print(f"✅ Grid level activated: {grid_level.level_id} @ {position.price_open} ({grid_level.lot_size} lots)")
                        
                        # Immediately place replacement order for this level
                        self.replace_filled_level(grid_level)
                        
                    else:
                        # Order was cancelled or rejected
                        grid_level.status = PositionStatus.CANCELLED
                        del self.pending_orders[order_id]
                        print(f"❌ Grid order cancelled/rejected: {grid_level.level_id}")
                        
                        # Try to place the order again
                        retry_result = self.place_pending_order(grid_level)
                        if retry_result:
                            grid_level.order_id = retry_result
                            grid_level.status = PositionStatus.PENDING
                            self.pending_orders[retry_result] = grid_level
                            print(f"🔄 Retried placing order: {grid_level.level_id}")
                        
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
        """Replace a filled grid level with a new pending order at the same level"""
        
        try:
            # Calculate new price for the replacement order
            # Place it at the opposite side to create a "bracket" effect
            if filled_level.direction == "BUY":
                # Original buy filled, place new buy order further down
                new_price = filled_level.price - (self.grid_spacing * self.point_value)
                new_direction = "BUY"
            else:
                # Original sell filled, place new sell order further up  
                new_price = filled_level.price + (self.grid_spacing * self.point_value)
                new_direction = "SELL"
                
            # Create new grid level
            new_level = GridLevel(
                level_id=f"{new_direction}_{int(time.time())}_{len(self.grid_levels)}",
                price=round(new_price, 5),
                lot_size=filled_level.lot_size,
                direction=new_direction,
                status=PositionStatus.PENDING
            )
            
            # Place the new order
            order_result = self.place_pending_order(new_level)
            if order_result:
                new_level.order_id = order_result
                self.grid_levels.append(new_level)
                self.pending_orders[order_result] = new_level
                print(f"🔄 Replacement order placed: {new_level.level_id} @ {new_price}")
            else:
                print(f"❌ Failed to place replacement order for {filled_level.level_id}")
                
        except Exception as e:
            print(f"❌ Error replacing filled level: {e}")
            
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
        """Check for emergency stop conditions - REAL RISK MANAGEMENT"""
        
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
                
            # Check margin level
            account_info = self.mt5_connector.get_account_info()
            if account_info:
                margin_level = account_info.get('margin_level', 1000)
                if margin_level < 150:  # Critical margin level
                    print(f"🚨 Critical margin level: {margin_level:.0f}%")
                    self.emergency_stop("Low margin level")
                    return
                elif margin_level < 200:  # Warning level
                    print(f"⚠️ Low margin level warning: {margin_level:.0f}%")
                    
            # Check account equity vs balance
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
            print(f"❌ Error checking emergency conditions: {e}")
            
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
        """Get comprehensive grid status for GUI display"""
        
        try:
            return {
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
                'daily_pnl': round(self.total_pnl, 2),  # Simplified daily PnL
                'magic_number': self.magic_number
            }
        except Exception as e:
            print(f"❌ Error getting grid status: {e}")
            return {}
            
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
    
    def add_nearby_buy_orders(self, count: int, current_price: float):
        """เพิ่ม BUY orders ใกล้ราคาปัจจุบัน"""
        try:
            for i in range(count):
                # หา BUY level ที่ใกล้ที่สุดที่ยังไม่มี order
                level_price = current_price - ((i + 1) * self.grid_spacing * self.point_value)
                
                # ตรวจสอบว่ามี order ใกล้ๆ แล้วหรือไม่
                too_close = False
                for existing_level in self.pending_orders.values():
                    if (existing_level.direction == "BUY" and 
                        abs(existing_level.price - level_price) < self.grid_spacing * self.point_value * 0.5):
                        too_close = True
                        break
                
                if not too_close:
                    new_level = GridLevel(
                        level_id=f"BUY_NEAR_{int(time.time())}_{i}",
                        price=round(level_price, 5),
                        lot_size=self.calculate_level_lot_size(i + 1),
                        direction="BUY",
                        status=PositionStatus.PENDING,
                        entry_time=datetime.now()
                    )
                    
                    order_result = self.place_pending_order(new_level)
                    if order_result:
                        new_level.order_id = order_result
                        self.grid_levels.append(new_level)
                        self.pending_orders[order_result] = new_level
                        print(f"🆕 Added nearby BUY: {new_level.level_id} @ ${level_price:.2f}")
                        
        except Exception as e:
            print(f"❌ Error adding nearby BUY orders: {e}")
    
    def add_nearby_sell_orders(self, count: int, current_price: float):
        """เพิ่ม SELL orders ใกล้ราคาปัจจุบัน"""
        try:
            for i in range(count):
                # หา SELL level ที่ใกล้ที่สุดที่ยังไม่มี order
                level_price = current_price + ((i + 1) * self.grid_spacing * self.point_value)
                
                # ตรวจสอบว่ามี order ใกล้ๆ แล้วหรือไม่
                too_close = False
                for existing_level in self.pending_orders.values():
                    if (existing_level.direction == "SELL" and 
                        abs(existing_level.price - level_price) < self.grid_spacing * self.point_value * 0.5):
                        too_close = True
                        break
                
                if not too_close:
                    new_level = GridLevel(
                        level_id=f"SELL_NEAR_{int(time.time())}_{i}",
                        price=round(level_price, 5),
                        lot_size=self.calculate_level_lot_size(i + 1),
                        direction="SELL",
                        status=PositionStatus.PENDING,
                        entry_time=datetime.now()
                    )
                    
                    order_result = self.place_pending_order(new_level)
                    if order_result:
                        new_level.order_id = order_result
                        self.grid_levels.append(new_level)
                        self.pending_orders[order_result] = new_level
                        print(f"🆕 Added nearby SELL: {new_level.level_id} @ ${level_price:.2f}")
                        
        except Exception as e:
            print(f"❌ Error adding nearby SELL orders: {e}")
    
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
        """Main trading loop - called continuously while trading is active"""
        
        loop_count = 0
        market_check_interval = 60  # Check market every 60 loops (1 minute)
        last_market_status = self.is_market_open()
        last_maintenance = datetime.now()
        last_cleanup = datetime.now()
        
        while self.trading_active and not self.emergency_stop_triggered:
            try:
                loop_count += 1
                
                # Check market status periodically
                if loop_count % market_check_interval == 0:
                    current_market_status = self.is_market_open()
                    
                    # Market status changed
                    if current_market_status != last_market_status:
                        if current_market_status:
                            print("🟢 Market opened - resuming order placement")
                            self.place_pending_orders_for_inactive_levels()
                        else:
                            print("🔴 Market closed - pausing new orders (keeping positions)")
                            
                        last_market_status = current_market_status
                    elif loop_count % (market_check_interval * 10) == 0:  # Every 10 minutes
                        if not current_market_status:
                            print("🕒 Market still closed - monitoring existing positions only")

                # ===== MAINTENANCE SCHEDULES =====
                
                # Daily cleanup (ทุก 24 ชั่วโมง)
                if (datetime.now() - last_cleanup).total_seconds() >= 24 * 3600:
                    print("🧹 Running daily cleanup...")
                    removed = self.cleanup_far_orders()
                    if removed > 0:
                        self.ensure_sufficient_grid_coverage()
                    last_cleanup = datetime.now()
                
                # Weekly maintenance (ทุก 7 วัน)
                if (datetime.now() - last_maintenance).total_seconds() >= 7 * 24 * 3600:
                    self.weekly_maintenance()
                    last_maintenance = datetime.now()
                
                # Grid extension check (ทุก 5 นาที)
                if loop_count % 300 == 0:  # 5 minutes
                    self.check_grid_triggers()
                
                # ===== REGULAR TRADING LOGIC =====
                
                # Update current price and price history
                self.update_current_price()
                
                # Only process trading logic if market is open
                if last_market_status:
                    # Check for filled orders (every loop)
                    self.check_filled_orders()
                    
                    # Update position PnL (every loop)
                    self.update_positions_pnl()
                    
                    # Update performance metrics (every 10 loops = ~10 seconds)
                    if loop_count % 10 == 0:
                        self.update_performance_metrics()
                        
                    # Check emergency conditions only when market is open
                    self.check_emergency_conditions()
                else:
                    # Market closed - still update PnL for existing positions
                    self.update_positions_pnl()
                    
                    # Only check critical emergency conditions (not margin-related)
                    self.check_critical_emergency_conditions()
                
                # Log status periodically (every 300 loops = ~5 minutes)
                if loop_count % 300 == 0:
                    status = self.get_grid_status()
                    market_emoji = "🟢" if last_market_status else "🔴"
                    pending_count = len(self.pending_orders)
                    print(f"📊 Status: {market_emoji} Market, {status['active_positions']} positions, {pending_count} pending, PnL: ${status['total_pnl']:.2f}, Drawdown: {status['current_drawdown']:.0f}pts")
                
                self.last_update = datetime.now()
                time.sleep(1)  # 1 second intervals
                
            except Exception as e:
                print(f"❌ Trading loop error: {e}")
                time.sleep(5)  # Wait longer on error
                
        print("🔴 Trading loop ended")
        
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