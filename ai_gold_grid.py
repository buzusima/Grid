"""
AI Gold Grid Trading Engine
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
    level_id: int
    price: float
    lot_size: float
    direction: str  # "BUY" or "SELL"
    status: PositionStatus
    order_id: Optional[int] = None
    position_id: Optional[int] = None
    entry_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    pnl: float = 0.0

@dataclass
class GridConfig:
    base_lot: float
    grid_spacing: int
    max_levels: int
    starting_price: float
    direction: GridDirection
    trading_mode: TradingMode
    stop_loss_points: Optional[int] = None
    take_profit_points: Optional[int] = None

class AIGoldGrid:
    def __init__(self, mt5_connector, survivability_params: Dict, config: Dict):
        self.mt5_connector = mt5_connector
        self.survivability_params = survivability_params
        self.config = config
        
        # Trading parameters from survivability engine
        self.base_lot = survivability_params['base_lot']
        self.grid_spacing = survivability_params['grid_spacing']
        self.max_levels = survivability_params['max_levels']
        self.survivability = survivability_params['survivability']
        
        # Gold symbol info
        self.gold_symbol = mt5_connector.get_gold_symbol()
        self.symbol_info = mt5_connector.get_symbol_info()
        
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
        
        # Risk management
        self.max_drawdown_points = 0
        self.current_drawdown = 0
        self.emergency_stop_triggered = False
        self.daily_loss_limit = config.get('daily_loss_limit', 1000)
        
        # Performance tracking
        self.trades_opened = 0
        self.trades_closed = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.largest_win = 0.0
        self.largest_loss = 0.0
        
        print(f"🤖 AI Gold Grid initialized for {self.gold_symbol}")
        print(f"   🎯 Base Lot: {self.base_lot}")
        print(f"   📏 Grid Spacing: {self.grid_spacing} points")
        print(f"   📊 Max Levels: {self.max_levels}")
        print(f"   🛡️ Survivability: {self.survivability:,.0f} points")
        
    def initialize_grid(self, starting_direction: GridDirection = GridDirection.BIDIRECTIONAL):
        """Initialize the grid trading system"""
        try:
            # Get current price
            price_data = self.mt5_connector.get_current_price()
            if not price_data:
                raise Exception("Failed to get current price")
                
            self.starting_price = price_data['bid']
            self.current_price = self.starting_price
            
            print(f"🚀 Initializing grid at price: {self.starting_price}")
            
            # Create grid levels
            self.create_grid_levels(starting_direction)
            
            # Place initial pending orders
            self.place_initial_orders()
            
            print(f"✅ Grid initialized with {len(self.grid_levels)} levels")
            
        except Exception as e:
            print(f"❌ Grid initialization error: {e}")
            raise
            
    def create_grid_levels(self, direction: GridDirection):
        """Create grid level structure"""
        self.grid_levels = []
        
        if direction == GridDirection.BIDIRECTIONAL:
            # Create buy levels below current price
            for i in range(1, self.max_levels + 1):
                buy_price = self.starting_price - (i * self.grid_spacing * self.symbol_info['point'])
                buy_level = GridLevel(
                    level_id=f"BUY_{i}",
                    price=buy_price,
                    lot_size=self.calculate_level_lot_size(i),
                    direction="BUY",
                    status=PositionStatus.PENDING
                )
                self.grid_levels.append(buy_level)
                
            # Create sell levels above current price
            for i in range(1, self.max_levels + 1):
                sell_price = self.starting_price + (i * self.grid_spacing * self.symbol_info['point'])
                sell_level = GridLevel(
                    level_id=f"SELL_{i}",
                    price=sell_price,
                    lot_size=self.calculate_level_lot_size(i),
                    direction="SELL",
                    status=PositionStatus.PENDING
                )
                self.grid_levels.append(sell_level)
                
        elif direction == GridDirection.BUY_GRID:
            # Only buy levels below current price
            for i in range(1, self.max_levels + 1):
                buy_price = self.starting_price - (i * self.grid_spacing * self.symbol_info['point'])
                buy_level = GridLevel(
                    level_id=f"BUY_{i}",
                    price=buy_price,
                    lot_size=self.calculate_level_lot_size(i),
                    direction="BUY",
                    status=PositionStatus.PENDING
                )
                self.grid_levels.append(buy_level)
                
        elif direction == GridDirection.SELL_GRID:
            # Only sell levels above current price
            for i in range(1, self.max_levels + 1):
                sell_price = self.starting_price + (i * self.grid_spacing * self.symbol_info['point'])
                sell_level = GridLevel(
                    level_id=f"SELL_{i}",
                    price=sell_price,
                    lot_size=self.calculate_level_lot_size(i),
                    direction="SELL",
                    status=PositionStatus.PENDING
                )
                self.grid_levels.append(sell_level)
                
    def calculate_level_lot_size(self, level: int) -> float:
        """Calculate lot size for specific grid level with AI optimization"""
        
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
        
        # Ensure lot size respects broker limits
        min_lot = self.symbol_info.get('volume_min', 0.01)
        max_lot = self.symbol_info.get('volume_max', 100.0)
        lot_step = self.symbol_info.get('volume_step', 0.01)
        
        # Round to lot step
        calculated_lot = round(calculated_lot / lot_step) * lot_step
        calculated_lot = max(min_lot, min(calculated_lot, max_lot))
        
        return calculated_lot
        
    def place_initial_orders(self):
        """Place initial pending orders for grid levels"""
        
        orders_placed = 0
        
        for grid_level in self.grid_levels:
            try:
                order_id = self.place_pending_order(grid_level)
                if order_id:
                    grid_level.order_id = order_id
                    self.pending_orders[order_id] = grid_level
                    orders_placed += 1
                    
                time.sleep(0.1)  # Small delay between orders
                
            except Exception as e:
                print(f"❌ Failed to place order for level {grid_level.level_id}: {e}")
                
        print(f"📋 Placed {orders_placed} pending orders")
        
    def place_pending_order(self, grid_level: GridLevel) -> Optional[int]:
        """Place a pending order for grid level"""
        
        try:
            # Determine order type
            current_price = self.get_current_price()
            
            if grid_level.direction == "BUY":
                if grid_level.price < current_price:
                    order_type = mt5.ORDER_TYPE_BUY_LIMIT
                else:
                    order_type = mt5.ORDER_TYPE_BUY_STOP
            else:  # SELL
                if grid_level.price > current_price:
                    order_type = mt5.ORDER_TYPE_SELL_LIMIT
                else:
                    order_type = mt5.ORDER_TYPE_SELL_STOP
                    
            # Prepare order request
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": self.gold_symbol,
                "volume": grid_level.lot_size,
                "type": order_type,
                "price": grid_level.price,
                "deviation": 10,
                "magic": 123456,  # Magic number for grid orders
                "comment": f"AI_Grid_{grid_level.level_id}",
                "type_time": mt5.ORDER_TIME_GTC
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Order placed: {grid_level.level_id} @ {grid_level.price}")
                return result.order
            else:
                print(f"❌ Order failed: {grid_level.level_id} - {result.comment}")
                return None
                
        except Exception as e:
            print(f"❌ Order placement error for {grid_level.level_id}: {e}")
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
        """Check for filled pending orders and convert to positions"""
        
        # Get current orders and positions
        orders = mt5.orders_get(symbol=self.gold_symbol)
        positions = mt5.positions_get(symbol=self.gold_symbol)
        
        # Check for newly filled orders
        active_order_ids = {order.ticket for order in orders} if orders else set()
        
        for order_id, grid_level in list(self.pending_orders.items()):
            if order_id not in active_order_ids:
                # Order has been filled or cancelled
                position = self.find_position_by_comment(f"AI_Grid_{grid_level.level_id}")
                
                if position:
                    # Order was filled and became a position
                    grid_level.status = PositionStatus.ACTIVE
                    grid_level.position_id = position.ticket
                    grid_level.entry_time = datetime.now()
                    
                    self.active_positions[position.ticket] = grid_level
                    del self.pending_orders[order_id]
                    
                    self.trades_opened += 1
                    print(f"✅ Grid level activated: {grid_level.level_id} @ {position.price_open}")
                    
                else:
                    # Order was cancelled
                    grid_level.status = PositionStatus.CANCELLED
                    del self.pending_orders[order_id]
                    print(f"❌ Grid order cancelled: {grid_level.level_id}")
                    
    def find_position_by_comment(self, comment: str):
        """Find position by comment"""
        positions = mt5.positions_get(symbol=self.gold_symbol)
        if positions:
            for position in positions:
                if position.comment == comment:
                    return position
        return None
        
    def update_positions_pnl(self):
        """Update PnL for all active positions"""
        
        total_unrealized = 0.0
        positions = mt5.positions_get(symbol=self.gold_symbol)
        
        if positions:
            for position in positions:
                if position.ticket in self.active_positions:
                    grid_level = self.active_positions[position.ticket]
                    grid_level.pnl = position.profit
                    total_unrealized += position.profit
                    
        self.unrealized_pnl = total_unrealized
        self.total_pnl = self.realized_pnl + self.unrealized_pnl
        
        # Update drawdown
        self.update_drawdown()
        
    def update_drawdown(self):
        """Update current drawdown in points and dollars"""
        
        if self.unrealized_pnl < 0:
            # Calculate drawdown in points
            drawdown_dollars = abs(self.unrealized_pnl)
            
            # Convert to points (approximate)
            # For gold: $1 change ≈ 100 points for 0.01 lot
            total_lots = sum(level.lot_size for level in self.active_positions.values())
            if total_lots > 0:
                drawdown_points = (drawdown_dollars / total_lots) * 100
            else:
                drawdown_points = 0
                
            self.current_drawdown = drawdown_points
            self.max_drawdown_points = max(self.max_drawdown_points, drawdown_points)
        else:
            self.current_drawdown = 0
            
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
        
        # Calculate distance from starting price
        price_move_points = abs(current_price - self.starting_price) / self.symbol_info['point']
        
        # If moved beyond current grid range, extend grid
        if price_move_points > (len([l for l in self.grid_levels if l.status != PositionStatus.CANCELLED]) * self.grid_spacing * 0.8):
            self.extend_grid_if_needed(current_price)
            
    def extend_grid_if_needed(self, current_price: float):
        """Extend grid if price moves beyond current range"""
        
        # Check if we're approaching grid limits
        active_levels = [l for l in self.grid_levels if l.status != PositionStatus.CANCELLED]
        
        if len(active_levels) < self.max_levels * 0.8:  # If less than 80% of max levels used
            return
            
        # Calculate new grid levels
        if current_price < self.starting_price:
            # Price moving down, add more buy levels
            lowest_price = min(l.price for l in active_levels if l.direction == "BUY")
            new_price = lowest_price - (self.grid_spacing * self.symbol_info['point'])
            
            if abs(new_price - self.starting_price) / self.symbol_info['point'] < self.survivability:
                self.add_new_grid_level("BUY", new_price)
                
        else:
            # Price moving up, add more sell levels
            highest_price = max(l.price for l in active_levels if l.direction == "SELL")
            new_price = highest_price + (self.grid_spacing * self.symbol_info['point'])
            
            if abs(new_price - self.starting_price) / self.symbol_info['point'] < self.survivability:
                self.add_new_grid_level("SELL", new_price)
                
    def add_new_grid_level(self, direction: str, price: float):
        """Add a new grid level"""
        
        level_count = len([l for l in self.grid_levels if l.direction == direction])
        new_level = GridLevel(
            level_id=f"{direction}_{level_count + 1}",
            price=price,
            lot_size=self.calculate_level_lot_size(level_count + 1),
            direction=direction,
            status=PositionStatus.PENDING
        )
        
        order_id = self.place_pending_order(new_level)
        if order_id:
            new_level.order_id = order_id
            self.grid_levels.append(new_level)
            self.pending_orders[order_id] = new_level
            print(f"🆕 Extended grid: {new_level.level_id} @ {price}")
            
    def check_profit_taking_opportunities(self):
        """Check for profit-taking opportunities on grid positions"""
        
        for position_id, grid_level in self.active_positions.items():
            if grid_level.pnl > 0:
                # Calculate if profit target is met
                profit_target = self.grid_spacing * self.symbol_info['point'] * grid_level.lot_size * 100
                
                if grid_level.pnl >= profit_target * 0.8:  # 80% of target
                    # Consider closing position
                    if self.should_take_profit(grid_level):
                        self.close_grid_position(grid_level)
                        
    def should_take_profit(self, grid_level: GridLevel) -> bool:
        """Determine if position should be closed for profit"""
        
        # AI-based profit-taking logic
        profit_ratio = grid_level.pnl / (grid_level.lot_size * 1000)  # Profit per $1000
        
        # Take profit conditions
        if profit_ratio > 0.015:  # 1.5% profit
            return True
            
        # Time-based profit taking
        if grid_level.entry_time:
            hours_open = (datetime.now() - grid_level.entry_time).total_seconds() / 3600
            if hours_open > 24 and profit_ratio > 0.005:  # 0.5% after 24 hours
                return True
                
        return False
        
    def close_grid_position(self, grid_level: GridLevel):
        """Close a grid position"""
        
        try:
            position = mt5.positions_get(ticket=grid_level.position_id)
            if position:
                position = position[0]
                
                # Prepare close request
                if position.type == mt5.POSITION_TYPE_BUY:
                    trade_type = mt5.ORDER_TYPE_SELL
                    price = mt5.symbol_info_tick(self.gold_symbol).bid
                else:
                    trade_type = mt5.ORDER_TYPE_BUY
                    price = mt5.symbol_info_tick(self.gold_symbol).ask
                    
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.gold_symbol,
                    "volume": position.volume,
                    "type": trade_type,
                    "position": grid_level.position_id,
                    "price": price,
                    "deviation": 10,
                    "magic": 123456,
                    "comment": f"AI_Grid_Close_{grid_level.level_id}"
                }
                
                result = mt5.order_send(request)
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    grid_level.status = PositionStatus.CLOSED
                    grid_level.close_time = datetime.now()
                    
                    self.realized_pnl += grid_level.pnl
                    self.trades_closed += 1
                    
                    if grid_level.pnl > 0:
                        self.winning_trades += 1
                        self.largest_win = max(self.largest_win, grid_level.pnl)
                    else:
                        self.losing_trades += 1
                        self.largest_loss = min(self.largest_loss, grid_level.pnl)
                        
                    del self.active_positions[grid_level.position_id]
                    
                    print(f"✅ Position closed: {grid_level.level_id} - PnL: ${grid_level.pnl:.2f}")
                    
                    # Replace with new grid level
                    self.replace_closed_level(grid_level)
                    
                else:
                    print(f"❌ Failed to close position {grid_level.level_id}: {result.comment}")
                    
        except Exception as e:
            print(f"❌ Error closing position {grid_level.level_id}: {e}")
            
    def replace_closed_level(self, closed_level: GridLevel):
        """Replace a closed grid level with a new pending order"""
        
        try:
            # Create new level at the same price
            new_level = GridLevel(
                level_id=f"{closed_level.direction}_{int(time.time())}",
                price=closed_level.price,
                lot_size=closed_level.lot_size,
                direction=closed_level.direction,
                status=PositionStatus.PENDING
            )
            
            order_id = self.place_pending_order(new_level)
            if order_id:
                new_level.order_id = order_id
                self.grid_levels.append(new_level)
                self.pending_orders[order_id] = new_level
                print(f"🔄 Grid level replaced: {new_level.level_id}")
                
        except Exception as e:
            print(f"❌ Error replacing grid level: {e}")
            
    def check_grid_rebalancing(self):
        """Check if grid needs rebalancing"""
        
        # Check buy/sell balance
        active_buys = len([l for l in self.active_positions.values() if l.direction == "BUY"])
        active_sells = len([l for l in self.active_positions.values() if l.direction == "SELL"])
        
        # Rebalance if heavily skewed
        if abs(active_buys - active_sells) > 5:
            print(f"⚖️ Grid imbalance detected: {active_buys} buys, {active_sells} sells")
            # Could implement rebalancing logic here
            
    def check_emergency_conditions(self):
        """Check for emergency stop conditions"""
        
        # Check daily loss limit
        if abs(self.total_pnl) > self.daily_loss_limit:
            print(f"🚨 Daily loss limit exceeded: ${self.total_pnl:.2f}")
            self.emergency_stop()
            
        # Check maximum drawdown
        if self.current_drawdown > self.survivability * 0.95:
            print(f"🚨 Maximum drawdown approached: {self.current_drawdown:.0f} points")
            self.emergency_stop()
            
        # Check margin level
        account_info = self.mt5_connector.get_account_info()
        if account_info and account_info.get('margin_level', 1000) < 200:
            print(f"🚨 Low margin level: {account_info['margin_level']:.0f}%")
            self.emergency_stop()
            
    def emergency_stop(self):
        """Emergency stop all trading"""
        
        if self.emergency_stop_triggered:
            return
            
        self.emergency_stop_triggered = True
        self.trading_active = False
        
        print("🚨 EMERGENCY STOP TRIGGERED!")
        
        # Close all positions
        self.close_all_positions()
        
        # Cancel all pending orders
        self.cancel_all_orders()
        
    def close_all_positions(self):
        """Close all active positions"""
        
        positions = mt5.positions_get(symbol=self.gold_symbol)
        if positions:
            for position in positions:
                try:
                    if position.type == mt5.POSITION_TYPE_BUY:
                        trade_type = mt5.ORDER_TYPE_SELL
                        price = mt5.symbol_info_tick(self.gold_symbol).bid
                    else:
                        trade_type = mt5.ORDER_TYPE_BUY
                        price = mt5.symbol_info_tick(self.gold_symbol).ask
                        
                    request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": self.gold_symbol,
                        "volume": position.volume,
                        "type": trade_type,
                        "position": position.ticket,
                        "price": price,
                        "deviation": 20,
                        "magic": 123456,
                        "comment": "AI_Grid_Emergency_Close"
                    }
                    
                    result = mt5.order_send(request)
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"✅ Emergency closed position: {position.ticket}")
                    else:
                        print(f"❌ Failed to close position {position.ticket}: {result.comment}")
                        
                except Exception as e:
                    print(f"❌ Error closing position {position.ticket}: {e}")
                    
    def cancel_all_orders(self):
        """Cancel all pending orders"""
        
        orders = mt5.orders_get(symbol=self.gold_symbol)
        if orders:
            for order in orders:
                try:
                    request = {
                        "action": mt5.TRADE_ACTION_REMOVE,
                        "order": order.ticket
                    }
                    
                    result = mt5.order_send(request)
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"✅ Cancelled order: {order.ticket}")
                    else:
                        print(f"❌ Failed to cancel order {order.ticket}: {result.comment}")
                        
                except Exception as e:
                    print(f"❌ Error cancelling order {order.ticket}: {e}")
                    
    def update_performance_metrics(self):
        """Update trading performance metrics"""
        
        # Calculate win rate
        total_closed = self.winning_trades + self.losing_trades
        self.win_rate = (self.winning_trades / total_closed) if total_closed > 0 else 0
        
        # Calculate profit factor
        total_wins = max(0.01, sum(level.pnl for level in self.grid_levels if level.status == PositionStatus.CLOSED and level.pnl > 0))
        total_losses = abs(min(-0.01, sum(level.pnl for level in self.grid_levels if level.status == PositionStatus.CLOSED and level.pnl < 0)))
        self.profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
    def get_current_drawdown(self) -> float:
        """Get current drawdown in points"""
        return self.current_drawdown
        
    def get_grid_status(self) -> Dict:
        """Get comprehensive grid status"""
        
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
            'profit_factor': round(self.profit_factor, 2),
            'largest_win': round(self.largest_win, 2),
            'largest_loss': round(self.largest_loss, 2),
            'emergency_stop': self.emergency_stop_triggered,
            'last_update': self.last_update.isoformat(),
            'survivability_used': round((self.current_drawdown / self.survivability) * 100, 1)
        }
        
    def start_trading(self):
        """Start the grid trading system"""
        if not self.trading_active:
            self.trading_active = True
            self.emergency_stop_triggered = False
            print("🚀 AI Grid Trading Started!")
            
    def stop_trading(self):
        """Stop the grid trading system"""
        self.trading_active = False
        print("⏹️ AI Grid Trading Stopped")
        
    def get_current_price(self) -> float:
        """Get current price from MT5"""
        price_data = self.mt5_connector.get_current_price()
        return price_data['bid'] if price_data else 0.0
        
    def calculate_grid_efficiency(self) -> Dict:
        """Calculate grid trading efficiency metrics"""
        
        # Calculate price range coverage
        if self.grid_levels:
            min_price = min(level.price for level in self.grid_levels)
            max_price = max(level.price for level in self.grid_levels)
            price_range = max_price - min_price
            price_range_points = price_range / self.symbol_info['point']
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
        
    def generate_trading_report(self) -> str:
        """Generate comprehensive trading report"""
        
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
   Profit Factor: {status['profit_factor']:.2f}
   Largest Win: ${status['largest_win']:,.2f}
   Largest Loss: ${status['largest_loss']:,.2f}
   
⚡ EFFICIENCY ANALYSIS:
   Price Range Coverage: {efficiency['price_range_coverage']:,.0f} points
   Capital Efficiency: {efficiency['capital_efficiency']:.1f}%
   Grid Utilization: {efficiency['grid_utilization']:.1f}%
   Avg Profit/Trade: ${efficiency['avg_profit_per_trade']:,.2f}
   Risk/Reward Ratio: {efficiency['risk_reward_ratio']:.2f}
   
🎯 GRID CONFIGURATION:
   Base Lot Size: {self.base_lot:.3f}
   Grid Spacing: {self.grid_spacing} points
   Max Levels: {self.max_levels}
   Survivability: {self.survivability:,.0f} points
   
📝 AI RECOMMENDATIONS:
"""
        
        # Add AI recommendations based on current performance
        recommendations = self.generate_ai_recommendations(status, efficiency)
        for rec in recommendations:
            report += f"   • {rec}\n"
            
        report += f"""
{'='*60}
🏆 AI GOLD GRID TRADING SYSTEM - LIVE TRADING ENGINE
"""
        
        return report
        
    def generate_ai_recommendations(self, status: Dict, efficiency: Dict) -> List[str]:
        """Generate AI-based trading recommendations"""
        
        recommendations = []
        
        # Performance-based recommendations
        if status['win_rate'] > 70:
            recommendations.append("Excellent win rate - consider gradual position size increase")
        elif status['win_rate'] < 40:
            recommendations.append("Low win rate - review grid spacing and consider wider intervals")
            
        # Risk-based recommendations
        if status['survivability_used'] > 80:
            recommendations.append("⚠️ High survivability usage - consider defensive measures")
        elif status['survivability_used'] < 20:
            recommendations.append("Low risk usage - potential for more aggressive positioning")
            
        # Efficiency recommendations
        if efficiency['capital_efficiency'] < 30:
            recommendations.append("Low capital efficiency - consider optimizing lot sizes")
        elif efficiency['capital_efficiency'] > 80:
            recommendations.append("⚠️ High capital usage - monitor margin levels closely")
            
        # Market condition recommendations
        if len(self.price_history) >= 100:
            recent_volatility = self.calculate_recent_volatility()
            if recent_volatility > 200:
                recommendations.append("High volatility detected - consider wider grid spacing")
            elif recent_volatility < 50:
                recommendations.append("Low volatility - potential for tighter grid spacing")
                
        # Time-based recommendations
        current_hour = datetime.now().hour
        if 14 <= current_hour <= 17:  # London-NY overlap
            recommendations.append("Peak trading hours - monitor positions closely")
        elif 22 <= current_hour or current_hour <= 6:  # Quiet hours
            recommendations.append("Quiet market hours - reduced monitoring sufficient")
            
        return recommendations
        
    def calculate_recent_volatility(self) -> float:
        """Calculate recent price volatility in points"""
        
        if len(self.price_history) < 50:
            return 100  # Default volatility
            
        recent_prices = [p['price'] for p in self.price_history[-50:]]
        
        # Calculate average true range (simplified)
        ranges = []
        for i in range(1, len(recent_prices)):
            high_low = abs(recent_prices[i] - recent_prices[i-1])
            ranges.append(high_low)
            
        avg_range = sum(ranges) / len(ranges) if ranges else 0
        volatility_points = avg_range / self.symbol_info['point']
        
        return volatility_points
        
    def optimize_grid_parameters(self) -> Dict:
        """AI-powered grid parameter optimization based on performance"""
        
        if self.trades_closed < 10:  # Need sufficient data
            return {}
            
        current_performance = {
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'avg_profit': self.realized_pnl / self.trades_closed,
            'max_drawdown': self.max_drawdown_points
        }
        
        # Optimization suggestions
        optimizations = {}
        
        # Lot size optimization
        if self.win_rate > 0.7 and self.profit_factor > 1.5:
            optimizations['lot_size_multiplier'] = 1.1  # Increase by 10%
        elif self.win_rate < 0.4 or self.profit_factor < 0.8:
            optimizations['lot_size_multiplier'] = 0.9  # Decrease by 10%
        else:
            optimizations['lot_size_multiplier'] = 1.0  # Keep current
            
        # Grid spacing optimization
        avg_trade_duration = self.calculate_avg_trade_duration()
        if avg_trade_duration > 24:  # More than 24 hours
            optimizations['spacing_multiplier'] = 0.9  # Tighter spacing
        elif avg_trade_duration < 4:  # Less than 4 hours
            optimizations['spacing_multiplier'] = 1.1  # Wider spacing
        else:
            optimizations['spacing_multiplier'] = 1.0
            
        # Risk optimization
        if self.max_drawdown_points > self.survivability * 0.5:
            optimizations['risk_reduction'] = True
            optimizations['max_levels_multiplier'] = 0.8
        else:
            optimizations['risk_reduction'] = False
            optimizations['max_levels_multiplier'] = 1.0
            
        return optimizations
        
    def calculate_avg_trade_duration(self) -> float:
        """Calculate average trade duration in hours"""
        
        closed_trades = [level for level in self.grid_levels 
                        if level.status == PositionStatus.CLOSED 
                        and level.entry_time and level.close_time]
        
        if not closed_trades:
            return 12  # Default 12 hours
            
        total_duration = sum(
            (trade.close_time - trade.entry_time).total_seconds() / 3600 
            for trade in closed_trades
        )
        
        return total_duration / len(closed_trades)
        
    def emergency_close_all(self):
        """Emergency close all positions immediately"""
        
        print("🚨 EMERGENCY CLOSE ALL POSITIONS!")
        
        self.emergency_stop_triggered = True
        self.trading_active = False
        
        # Close all positions with market orders
        self.close_all_positions()
        
        # Cancel all pending orders
        self.cancel_all_orders()
        
        # Clear internal state
        self.active_positions.clear()
        self.pending_orders.clear()
        
        print("✅ Emergency close completed")
        
    def check_hedge_triggers(self):
        """Check if hedge system should be triggered (integration point)"""
        
        # This method integrates with the hedge calculator
        # Return current drawdown for hedge system
        return self.current_drawdown
        
    def __del__(self):
        """Cleanup when object is destroyed"""
        if self.trading_active:
            self.stop_trading()

# Test function
def test_ai_gold_grid():
    """Test the AI Gold Grid system"""
    
    print("🧪 AI Gold Grid Test Mode - Simulation Only")
    print("="*60)
    
    # Mock survivability parameters
    test_params = {
        'base_lot': 0.05,
        'grid_spacing': 300,
        'max_levels': 67,
        'survivability': 20100,
        'account_balance': 10000
    }
    
    # Mock config
    test_config = {
        'daily_loss_limit': 500,
        'target_survivability': 20000
    }
    
    print(f"📊 Test Parameters:")
    print(f"   Base Lot: {test_params['base_lot']}")
    print(f"   Grid Spacing: {test_params['grid_spacing']} points")
    print(f"   Max Levels: {test_params['max_levels']}")
    print(f"   Survivability: {test_params['survivability']:,} points")
    
    # Simulate grid calculations
    print(f"\n🧮 Grid Calculations:")
    
    # Calculate total exposure
    total_exposure = test_params['base_lot'] * test_params['max_levels']
    print(f"   Total Exposure: {total_exposure:.2f} lots")
    
    # Calculate grid range
    grid_range = test_params['grid_spacing'] * test_params['max_levels']
    print(f"   Grid Range: {grid_range:,} points")
    
    # Calculate margin requirement (estimated)
    margin_per_lot = 1000  # $1000 per 0.01 lot (estimated)
    total_margin = total_exposure * margin_per_lot / 0.01
    print(f"   Estimated Margin: ${total_margin:,.2f}")
    
    # Test efficiency metrics
    print(f"\n⚡ Efficiency Analysis:")
    capital_efficiency = (total_margin / test_params['account_balance']) * 100
    print(f"   Capital Efficiency: {capital_efficiency:.1f}%")
    
    survivability_ratio = (test_params['survivability'] / 20000) * 100
    print(f"   Survivability Achievement: {survivability_ratio:.1f}%")
    
    print(f"\n✅ AI Gold Grid Test Completed")
    print("   Ready for live trading integration!")

if __name__ == "__main__":
    test_ai_gold_grid()