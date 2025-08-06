"""
Smart Profit Management System
smart_profit_manager.py
Advanced profit taking with portfolio analysis, trailing stops, and intelligent closing
"""

import math
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import MetaTrader5 as mt5

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
    def __init__(self, gold_grid_system, config: dict):
        self.grid_system = gold_grid_system
        self.config = config
        
        # Smart profit parameters
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
        account_info = gold_grid_system.mt5_connector.get_account_info()
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
        
        print(f"💊 Portfolio Recovery System:")
        print(f"   Enabled: {self.recovery_enabled}")
        print(f"   Trigger Loss: ${abs(self.recovery_trigger_loss)}")
        print(f"   Auto Mode: {self.recovery_auto_mode}")    
        print(f"🧠 Smart Profit Manager initialized:")
        print(f"   💰 Balance: ${balance:,.0f}")
        print(f"   🎯 Strategy: {self.default_strategy.value}")
        print(f"   📈 Trailing Stop: {self.trailing_stop_distance} points")
        
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
            'partial_close_target': round(base_target * 0.5, 2),  # Close 50% early
            'min_profit_lock': round(base_target * 0.3, 2),       # Lock minimum 30%
            'strategy': strategy.value
        }
    
    def auto_reposition_after_close(self, closed_position):
        """วางไม้ใหม่หลังปิดกำไร - เก็บกำไรต่อเนื่อง"""
        try:
            if not self.auto_reposition_enabled:
                return
                
            current_price = self.grid_system.get_current_price()
            
            # หาตำแหน่งใหม่ที่เหมาะสม
            direction = closed_position.direction
            position_id = f"REPO_{direction}_{int(time.time())}"
            
            if direction == "BUY":
                # วาง BUY ใหม่ต่ำกว่าราคาปัจจุบัน
                new_price = current_price - (self.min_gap_for_reposition * 0.01)
            else:
                # วาง SELL ใหม่สูงกว่าราคาปัจจุบัน  
                new_price = current_price + (self.min_gap_for_reposition * 0.01)
                
            # เช็คว่าไม่ซ้ำกับไม้เดิม
            if not self.is_too_close_to_existing(new_price, direction):
                success = self.place_replacement_position(direction, new_price, closed_position.lot_size)
                if success:
                    self.positions_turned_today += 1
                    print(f"🔄 Auto repositioned: {direction} @ {new_price:.2f}")
                    
        except Exception as e:
            print(f"❌ Auto reposition error: {e}")

    def is_too_close_to_existing(self, price: float, direction: str) -> bool:
        """เช็คว่าตำแหน่งใหม่ใกล้ไม้เดิมเกินไปไหม"""
        min_distance = self.min_gap_for_reposition * 0.01
        
        for grid_level in self.grid_system.pending_orders.values():
            if (grid_level.direction == direction and 
                abs(grid_level.price - price) < min_distance):
                return True
        return False

    def place_replacement_position(self, direction: str, price: float, lot_size: float) -> bool:
        """วางไม้ทดแทน"""
        try:
            from ai_gold_grid import GridLevel, PositionStatus
            
            new_level = GridLevel(
                level_id=f"FAST_{direction}_{int(time.time())}",
                price=round(price, 5),
                lot_size=lot_size,
                direction=direction,
                status=PositionStatus.PENDING,
                entry_time=datetime.now()
            )
            
            order_result = self.grid_system.place_pending_order(new_level)
            if order_result:
                new_level.order_id = order_result
                self.grid_system.grid_levels.append(new_level)
                self.grid_system.pending_orders[order_result] = new_level
                return True
                
        except Exception as e:
            print(f"❌ Replacement position error: {e}")
        return False
    
    def analyze_portfolio_positions(self) -> Dict:
        """Analyze entire portfolio including hedge positions"""
        
        try:
            # Get all positions from MT5
            positions = mt5.positions_get(symbol=self.grid_system.gold_symbol)
            if not positions:
                return {'total_positions': 0, 'analysis': 'No positions'}
                
            # Filter our positions
            our_positions = [pos for pos in positions if pos.magic == self.grid_system.magic_number]
            
            # Categorize positions
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
                    is_hedge="HEDGE" in pos.comment
                )
                
                if smart_pos.is_hedge:
                    hedge_positions.append(smart_pos)
                else:
                    grid_positions.append(smart_pos)
                    
            # Calculate portfolio metrics
            total_pnl = sum(pos.pnl for pos in grid_positions + hedge_positions)
            total_lots = sum(pos.lot_size for pos in grid_positions)
            hedge_lots = sum(pos.lot_size for pos in hedge_positions)
            
            # Net exposure calculation
            buy_lots = sum(pos.lot_size for pos in grid_positions if pos.direction == "BUY")
            sell_lots = sum(pos.lot_size for pos in grid_positions if pos.direction == "SELL")
            net_exposure = buy_lots - sell_lots
            
            # Hedge effectiveness
            hedge_coverage = min(abs(hedge_lots / net_exposure) if net_exposure != 0 else 0, 1.0)
            
            # Risk assessment
            account_info = self.grid_system.mt5_connector.get_account_info()
            balance = account_info.get('balance', 1000) if account_info else 1000
            risk_percentage = abs(total_pnl / balance) * 100 if balance > 0 else 0
            
            return {
                'total_positions': len(grid_positions),
                'hedge_positions': len(hedge_positions),
                'total_pnl': round(total_pnl, 2),
                'total_lots': round(total_lots, 3),
                'hedge_lots': round(hedge_lots, 3),
                'net_exposure': round(net_exposure, 3),
                'hedge_coverage': round(hedge_coverage * 100, 1),
                'risk_percentage': round(risk_percentage, 2),
                'grid_positions': grid_positions,
                'hedge_positions': hedge_positions,
                'balance': balance
            }
            
        except Exception as e:
            print(f"❌ Portfolio analysis error: {e}")
            return {'error': str(e)}
            
    def update_trailing_stops(self, portfolio_analysis: Dict):
        """Update trailing stops for profitable positions"""
        
        if 'grid_positions' not in portfolio_analysis:
            return
            
        for position in portfolio_analysis['grid_positions']:
            try:
                # Skip if not profitable enough for trailing
                if position.pnl < self.min_profit_for_trailing:
                    continue
                    
                # Calculate trailing stop price
                current_price = position.current_price
                
                if position.direction == "BUY":
                    # BUY position - trailing stop below current price
                    proposed_stop = current_price - (self.trailing_stop_distance * 0.01)
                    
                    # Update trailing stop if price moved favorably
                    if (position.trailing_stop_price is None or 
                        proposed_stop > position.trailing_stop_price):
                        position.trailing_stop_price = proposed_stop
                        print(f"📈 Updated BUY trailing stop: {position.position_id} @ {proposed_stop:.2f}")
                        
                else:  # SELL position
                    # SELL position - trailing stop above current price
                    proposed_stop = current_price + (self.trailing_stop_distance * 0.01)
                    
                    # Update trailing stop if price moved favorably
                    if (position.trailing_stop_price is None or 
                        proposed_stop < position.trailing_stop_price):
                        position.trailing_stop_price = proposed_stop
                        print(f"📉 Updated SELL trailing stop: {position.position_id} @ {proposed_stop:.2f}")
                        
                # Track maximum profit seen
                position.max_profit_seen = max(position.max_profit_seen, position.pnl)
                
            except Exception as e:
                print(f"❌ Trailing stop update error for {position.position_id}: {e}")
                
    def check_trailing_stop_triggers(self, portfolio_analysis: Dict) -> List[Tuple[SmartPosition, CloseReason]]:
        """Check if any trailing stops should be triggered"""
        
        positions_to_close = []
        
        if 'grid_positions' not in portfolio_analysis:
            return positions_to_close
            
        current_price = self.grid_system.get_current_price()
        
        for position in portfolio_analysis['grid_positions']:
            try:
                if position.trailing_stop_price is None:
                    continue
                    
                should_close = False
                
                if position.direction == "BUY":
                    # BUY position - close if price falls below trailing stop
                    if current_price <= position.trailing_stop_price:
                        should_close = True
                        
                else:  # SELL position
                    # SELL position - close if price rises above trailing stop
                    if current_price >= position.trailing_stop_price:
                        should_close = True
                        
                if should_close:
                    positions_to_close.append((position, CloseReason.TRAILING_STOP))
                    print(f"🎯 Trailing stop triggered: {position.position_id} @ {current_price:.2f}")
                    
            except Exception as e:
                print(f"❌ Trailing stop check error for {position.position_id}: {e}")
                
        return positions_to_close
        
    def identify_profit_opportunities(self, portfolio_analysis: Dict) -> List[Tuple[SmartPosition, CloseReason, Dict]]:
        """Identify positions ready for profit taking"""
        
        opportunities = []
        
        if 'grid_positions' not in portfolio_analysis:
            return opportunities
            
        for position in portfolio_analysis['grid_positions']:
            try:
                # Calculate profit targets for this position
                targets = self.calculate_smart_profit_target(position.lot_size)
                
                # Check various profit-taking conditions
                close_decision = self.evaluate_close_decision(position, targets, portfolio_analysis)
                
                if close_decision['should_close']:
                    opportunities.append((
                        position, 
                        close_decision['reason'], 
                        close_decision['details']
                    ))
                    
            except Exception as e:
                print(f"❌ Profit opportunity analysis error for {position.position_id}: {e}")
                
        return opportunities
        
    def evaluate_close_decision(self, position: SmartPosition, targets: Dict, portfolio_analysis: Dict) -> Dict:
        """Evaluate whether a position should be closed"""
        
        # Position age
        position_age = (datetime.now() - position.entry_time).total_seconds() / 60  # minutes
        
        # Portfolio risk
        portfolio_risk = portfolio_analysis.get('risk_percentage', 0)
        
        # 1. Quick profit target reached
        if position.pnl >= targets['profit_target']:
            return {
                'should_close': True,
                'reason': CloseReason.PROFIT_TARGET,
                'details': {
                    'target_reached': targets['profit_target'],
                    'actual_profit': position.pnl,
                    'close_percentage': 100
                }
            }
            
        # 2. Partial profit taking
        if position.pnl >= targets['partial_close_target']:
            return {
                'should_close': True,
                'reason': CloseReason.PROFIT_TARGET,
                'details': {
                    'target_reached': targets['partial_close_target'],
                    'actual_profit': position.pnl,
                    'close_percentage': 50  # Close 50% only
                }
            }
            
        # 3. Portfolio risk too high - take any profit
        if portfolio_risk > self.max_portfolio_risk_pct and position.pnl > 1.0:
            return {
                'should_close': True,
                'reason': CloseReason.PORTFOLIO_RISK,
                'details': {
                    'portfolio_risk': portfolio_risk,
                    'max_allowed': self.max_portfolio_risk_pct,
                    'close_percentage': 100
                }
            }
            
        # 4. Time-based profit taking
        if (position_age > self.max_position_age_minutes and 
            position.pnl >= targets['min_profit_lock']):
            return {
                'should_close': True,
                'reason': CloseReason.TIME_BASED,
                'details': {
                    'position_age': position_age,
                    'max_age': self.max_position_age_minutes,
                    'profit_locked': position.pnl,
                    'close_percentage': 100
                }
            }
            
        # 5. Market reversal detection (simplified)
        if self.detect_market_reversal(position):
            return {
                'should_close': True,
                'reason': CloseReason.MARKET_REVERSAL,
                'details': {
                    'reversal_detected': True,
                    'close_percentage': 75  # Close 75% on reversal
                }
            }
            
        # 6. Emergency conditions
        if portfolio_analysis.get('total_pnl', 0) < -portfolio_analysis.get('balance', 1000) * 0.1:
            # If portfolio losing more than 10% of balance, close any profit
            if position.pnl > 0:
                return {
                    'should_close': True,
                    'reason': CloseReason.EMERGENCY,
                    'details': {
                        'emergency_triggered': True,
                        'portfolio_loss': portfolio_analysis.get('total_pnl', 0),
                        'close_percentage': 100
                    }
                }
                
        return {'should_close': False}
        
    def detect_market_reversal(self, position: SmartPosition) -> bool:
        """Simple market reversal detection"""
        
        try:
            # Get recent price history from grid system
            if not hasattr(self.grid_system, 'price_history') or len(self.grid_system.price_history) < 10:
                return False
                
            recent_prices = [p['price'] for p in self.grid_system.price_history[-10:]]
            
            # Calculate price trend
            price_change = recent_prices[-1] - recent_prices[0]
            
            # If position is BUY and price dropping fast
            if position.direction == "BUY" and price_change < -20:  # 20 point drop
                return True
                
            # If position is SELL and price rising fast  
            if position.direction == "SELL" and price_change > 20:   # 20 point rise
                return True
                
            return False
            
        except Exception as e:
            print(f"❌ Reversal detection error: {e}")
            return False
            
    def execute_smart_close(self, position: SmartPosition, reason: CloseReason, details: Dict) -> bool:
        """Execute intelligent position closing"""
        
        try:
            close_percentage = details.get('close_percentage', 100)
            
            if close_percentage >= 100:
                # Close entire position
                success = self.close_entire_position(position)
                if success:
                    print(f"✅ FULL CLOSE: {position.position_id} - Reason: {reason.value}")
                    print(f"   💰 Profit: ${position.pnl:.2f} | Lot: {position.lot_size}")
                    
                    # 🔄 เพิ่มส่วนนี้ - Auto reposition หลังปิดเต็ม
                    self.auto_reposition_after_close(position)
                    self.daily_profit_harvested += position.pnl
                    
                return success
                
            else:
                # Partial close
                close_volume = position.lot_size * (close_percentage / 100)
                success = self.partial_close_position(position, close_volume)
                if success:
                    print(f"✅ PARTIAL CLOSE: {position.position_id} - {close_percentage}% - Reason: {reason.value}")
                    print(f"   💰 Estimated Profit: ${position.pnl * (close_percentage/100):.2f}")
                    
                    # 🔄 เพิ่มส่วนนี้ - Track partial profit
                    partial_profit = position.pnl * (close_percentage / 100)
                    self.daily_profit_harvested += partial_profit
                    
                    # ถ้าปิดมากกว่า 50% ให้ reposition ใหม่
                    if close_percentage >= 50:
                        self.auto_reposition_after_close(position)
                    
                return success
                
        except Exception as e:
            print(f"❌ Smart close execution error: {e}")
            return False
                
    def close_entire_position(self, position: SmartPosition) -> bool:
        """Close entire position"""
        
        try:
            # Get current tick
            tick = mt5.symbol_info_tick(self.grid_system.gold_symbol)
            if not tick:
                return False
                
            # Determine close parameters
            if position.direction == "BUY":
                trade_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                trade_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
                
            # Close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.grid_system.gold_symbol,
                "volume": position.lot_size,
                "type": trade_type,
                "position": position.position_id,
                "price": price,
                "deviation": 20,
                "magic": self.grid_system.magic_number,
                "comment": "SmartProfit_FullClose",
                "type_filling": self.grid_system.close_filling_mode
            }
            
            result = mt5.order_send(request)
            return result and result.retcode == mt5.TRADE_RETCODE_DONE
            
        except Exception as e:
            print(f"❌ Full close error: {e}")
            return False
            
    def partial_close_position(self, position: SmartPosition, close_volume: float) -> bool:
        """Partially close position"""
        
        try:
            # Round close volume to valid step
            symbol_info = self.grid_system.symbol_info
            volume_step = symbol_info.get('volume_step', 0.01)
            close_volume = round(close_volume / volume_step) * volume_step
            
            # Ensure minimum volume
            if close_volume < symbol_info.get('volume_min', 0.01):
                close_volume = symbol_info.get('volume_min', 0.01)
                
            # Don't close more than available
            close_volume = min(close_volume, position.lot_size)
            
            # Get current tick
            tick = mt5.symbol_info_tick(self.grid_system.gold_symbol)
            if not tick:
                return False
                
            # Determine close parameters
            if position.direction == "BUY":
                trade_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                trade_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
                
            # Partial close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.grid_system.gold_symbol,
                "volume": close_volume,
                "type": trade_type,
                "position": position.position_id,
                "price": price,
                "deviation": 20,
                "magic": self.grid_system.magic_number,
                "comment": f"SmartProfit_Partial_{close_volume}",
                "type_filling": self.grid_system.close_filling_mode
            }
            
            result = mt5.order_send(request)
            return result and result.retcode == mt5.TRADE_RETCODE_DONE
            
        except Exception as e:
            print(f"❌ Partial close error: {e}")
            return False
            
    def run_smart_profit_management(self):
        """Main function to run smart profit management"""
        
        try:
            # 1. Analyze entire portfolio
            portfolio_analysis = self.analyze_portfolio_positions()
            
            if 'error' in portfolio_analysis:
                return
                
            # 2. Update trailing stops
            self.update_trailing_stops(portfolio_analysis)
            
            # 3. Check trailing stop triggers
            trailing_stops = self.check_trailing_stop_triggers(portfolio_analysis)
            
            # 4. Execute trailing stop closes
            for position, reason in trailing_stops:
                self.execute_smart_close(position, reason, {'close_percentage': 100})
                
            # 5. Identify profit opportunities
            profit_opportunities = self.identify_profit_opportunities(portfolio_analysis)
            
            # 6. Execute profit taking
            for position, reason, details in profit_opportunities:
                self.execute_smart_close(position, reason, details)
                
            # 7. Log portfolio status periodically
            if len(portfolio_analysis.get('grid_positions', [])) > 0:
                self.log_portfolio_status(portfolio_analysis)
            
            # ✅Portfolio Recovery (Optional)
            if self.recovery_enabled:
                self.check_and_run_recovery(portfolio_analysis)    
        
        except Exception as e:
            print(f"❌ Smart profit management error: {e}")
            
    def log_portfolio_status(self, portfolio_analysis: Dict):
        """Log current portfolio status"""
        
        try:
            total_pnl = portfolio_analysis.get('total_pnl', 0)
            total_positions = portfolio_analysis.get('total_positions', 0)
            hedge_positions = portfolio_analysis.get('hedge_positions', 0)
            risk_pct = portfolio_analysis.get('risk_percentage', 0)
            
            status_emoji = "📈" if total_pnl >= 0 else "📉"
            risk_emoji = "🟢" if risk_pct < 10 else "🟡" if risk_pct < 20 else "🔴"
            
        except Exception as e:
            print(f"❌ Portfolio logging error: {e}")
            
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
            print(f"      Losing: {len(losing_positions)} positions (${total_loss:.2f})")
            print(f"      Profitable: {len(profitable_positions)} positions (+${total_profit:.2f})")
            print(f"      Neutral: {len(neutral_positions)} positions")
            print(f"      Net PnL: ${net_pnl:.2f}")
            
            # หาคู่ positions ที่สามารถปิดพร้อมกันได้กำไร
            optimal_pairs = self.find_optimal_pairs(losing_positions, profitable_positions)
            
            # คำนวณ hedge opportunities
            hedge_opportunities = self.calculate_hedge_recovery(losing_positions)
            
            recovery_plan = {
                'viable': len(optimal_pairs) > 0 or len(hedge_opportunities) > 0,
                'optimal_pairs': optimal_pairs,
                'hedge_opportunities': hedge_opportunities,
                'total_recovery_potential': sum(pair['net_profit'] for pair in optimal_pairs),
                'losing_positions': losing_positions,
                'profitable_positions': profitable_positions
            }
            
            print(f"   🎯 Recovery Plan:")
            print(f"      Optimal pairs: {len(optimal_pairs)}")
            print(f"      Recovery potential: ${recovery_plan['total_recovery_potential']:.2f}")
            print(f"      Viable: {recovery_plan['viable']}")
            
            return recovery_plan
            
        except Exception as e:
            print(f"❌ Recovery analysis error: {e}")
            return {'viable': False}

    def find_optimal_pairs(self, losing_positions: List, profitable_positions: List) -> List[Dict]:
        """หาคู่ positions ที่ปิดแล้วได้กำไรสุทธิ"""
        try:
            optimal_pairs = []
            
            # สำเนา list เพื่อไม่ให้กระทบต้นฉบับ
            remaining_losing = losing_positions.copy()
            remaining_profitable = profitable_positions.copy()
            
            for losing_pos in remaining_losing:
                for profitable_pos in remaining_profitable:
                    # คำนวณกำไรสุทธิถ้าปิดคู่นี้
                    net_profit = losing_pos.pnl + profitable_pos.pnl
                    
                    # เลือกเฉพาะคู่ที่ได้กำไรสุทธิ > $2
                    if net_profit > 2:
                        pair_info = {
                            'losing_position': losing_pos,
                            'profitable_position': profitable_pos,
                            'losing_pnl': losing_pos.pnl,
                            'profitable_pnl': profitable_pos.pnl,
                            'net_profit': net_profit,
                            'priority_score': net_profit + abs(losing_pos.pnl)  # ยิ่งขาดทุนมาก priority สูง
                        }
                        optimal_pairs.append(pair_info)
            
            # เรียงตาม priority score (สูงสุดก่อน)
            optimal_pairs.sort(key=lambda x: x['priority_score'], reverse=True)
            
            # เลือกเฉพาะคู่ที่ไม่ซ้ำกัน (greedy selection)
            selected_pairs = []
            used_positions = set()
            
            for pair in optimal_pairs:
                losing_id = pair['losing_position'].position_id
                profitable_id = pair['profitable_position'].position_id
                
                if losing_id not in used_positions and profitable_id not in used_positions:
                    selected_pairs.append(pair)
                    used_positions.add(losing_id)
                    used_positions.add(profitable_id)
            
            print(f"      Found {len(selected_pairs)} optimal pairs:")
            for i, pair in enumerate(selected_pairs[:3]):  # แสดง 3 อันดับแรก
                print(f"         {i+1}. Loss ${pair['losing_pnl']:.2f} + Profit ${pair['profitable_pnl']:.2f} = Net +${pair['net_profit']:.2f}")
            
            return selected_pairs
            
        except Exception as e:
            print(f"❌ Pair finding error: {e}")
            return []

    def calculate_hedge_recovery(self, losing_positions: List) -> List[Dict]:
        """คำนวณโอกาสใช้ hedge เพื่อ recovery"""
        try:
            hedge_opportunities = []
            
            # จัดกลุ่มตาม direction
            losing_buys = [p for p in losing_positions if p.direction == "BUY"]
            losing_sells = [p for p in losing_positions if p.direction == "SELL"]
            
            current_price = self.grid_system.get_current_price()
            
            # Hedge สำหรับ BUY positions ที่ขาดทุน
            if losing_buys:
                total_buy_loss = sum(p.pnl for p in losing_buys)
                total_buy_lots = sum(p.lot_size for p in losing_buys)
                
                # คำนวณ SELL hedge ที่ต้องการ
                hedge_lot_size = total_buy_lots * 0.8  # 80% hedge
                hedge_price = current_price + (50 * 0.01)  # +50 points
                
                hedge_opportunity = {
                    'type': 'SELL_HEDGE',
                    'target_positions': losing_buys,
                    'hedge_direction': 'SELL',
                    'hedge_lot_size': hedge_lot_size,
                    'hedge_price': hedge_price,
                    'target_loss': total_buy_loss,
                    'estimated_recovery': abs(total_buy_loss) * 0.7  # คาดว่าได้คืน 70%
                }
                hedge_opportunities.append(hedge_opportunity)
            
            # Hedge สำหรับ SELL positions ที่ขาดทุน
            if losing_sells:
                total_sell_loss = sum(p.pnl for p in losing_sells)
                total_sell_lots = sum(p.lot_size for p in losing_sells)
                
                hedge_lot_size = total_sell_lots * 0.8
                hedge_price = current_price - (50 * 0.01)  # -50 points
                
                hedge_opportunity = {
                    'type': 'BUY_HEDGE',
                    'target_positions': losing_sells,
                    'hedge_direction': 'BUY',
                    'hedge_lot_size': hedge_lot_size,
                    'hedge_price': hedge_price,
                    'target_loss': total_sell_loss,
                    'estimated_recovery': abs(total_sell_loss) * 0.7
                }
                hedge_opportunities.append(hedge_opportunity)
            
            if hedge_opportunities:
                print(f"      Found {len(hedge_opportunities)} hedge opportunities:")
                for opp in hedge_opportunities:
                    print(f"         {opp['type']}: {opp['hedge_lot_size']:.3f} lots @ ${opp['hedge_price']:.2f}")
                    print(f"            Target recovery: ${opp['estimated_recovery']:.2f}")
            
            return hedge_opportunities
            
        except Exception as e:
            print(f"❌ Hedge calculation error: {e}")
            return []

    def execute_recovery_plan(self, recovery_plan: Dict):
        """ดำเนินการตาม recovery plan"""
        try:
            executed_actions = 0
            
            # 1. ดำเนินการ optimal pairs ก่อน (ความเสี่ยงต่ำ)
            for pair in recovery_plan['optimal_pairs'][:2]:  # ทำ 2 คู่แรกก่อน
                success = self.execute_pair_close(pair)
                if success:
                    executed_actions += 1
                    print(f"   ✅ Executed pair close: Net +${pair['net_profit']:.2f}")
                else:
                    print(f"   ❌ Failed to close pair")
            
            # 2. ถ้า pairs ไม่พอ ใช้ hedge strategy
            if executed_actions == 0 and recovery_plan['hedge_opportunities']:
                hedge_opp = recovery_plan['hedge_opportunities'][0]  # เลือกตัวแรก
                success = self.execute_hedge_recovery(hedge_opp)
                if success:
                    executed_actions += 1
                    print(f"   ✅ Executed hedge recovery: {hedge_opp['type']}")
            
            if executed_actions > 0:
                print(f"   🎯 Recovery actions executed: {executed_actions}")
            else:
                print(f"   ⚠️ No recovery actions could be executed")
                self.recovery_active = False
                
        except Exception as e:
            print(f"❌ Recovery execution error: {e}")
            self.recovery_active = False

    def execute_pair_close(self, pair: Dict) -> bool:
        """ปิด position คู่พร้อมกัน"""
        try:
            losing_pos = pair['losing_position']
            profitable_pos = pair['profitable_position']
            
            # ปิด position แรก
            success1 = self.close_single_position(losing_pos)
            if not success1:
                return False
            
            # รอสักครู่
            time.sleep(0.5)
            
            # ปิด position ที่สอง
            success2 = self.close_single_position(profitable_pos)
            if not success2:
                print(f"   ⚠️ Warning: First position closed but second failed")
                return False
            
            print(f"   💰 Pair closed: ${losing_pos.pnl:.2f} + ${profitable_pos.pnl:.2f} = +${pair['net_profit']:.2f}")
            return True
            
        except Exception as e:
            print(f"❌ Pair close error: {e}")
            return False

    def close_single_position(self, position) -> bool:
        """ปิด position เดียว (ใช้ function เดิม)"""
        try:
            # ใช้ method เดิมจาก smart profit manager
            return self.execute_smart_close(
                position, 
                CloseReason.PORTFOLIO_RISK,  # ใช้ reason ที่มีอยู่แล้ว
                {'close_percentage': 100}
            )
        except Exception as e:
            print(f"❌ Single position close error: {e}")
            return False

    def execute_hedge_recovery(self, hedge_opp: Dict) -> bool:
        """วาง hedge order เพื่อ recovery"""
        try:
            # ใช้ method ที่มีอยู่แล้วใน grid system
            success = self.grid_system.place_hedge_order(
                hedge_opp['hedge_direction'],
                hedge_opp['hedge_lot_size']
            )
            
            if success:
                print(f"   🛡️ Hedge placed: {hedge_opp['hedge_direction']} {hedge_opp['hedge_lot_size']:.3f} lots")
                return True
            else:
                print(f"   ❌ Failed to place hedge")
                return False
                
        except Exception as e:
            print(f"❌ Hedge execution error: {e}")
            return False

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

    def manual_trigger_recovery(self):
        """Manual trigger สำหรับ GUI"""
        try:
            if self.recovery_active:
                print(f"💊 Recovery already active")
                return False
                
            portfolio_analysis = self.analyze_portfolio_positions()
            if 'error' in portfolio_analysis:
                print(f"💊 Cannot analyze portfolio for recovery")
                return False
                
            self.start_portfolio_recovery(portfolio_analysis)
            return True
            
        except Exception as e:
            print(f"❌ Manual recovery trigger error: {e}")
            return False

    def get_recovery_status(self) -> Dict:
        """ดึงสถานะ recovery สำหรับ GUI"""
        try:
            status = {
                'enabled': self.recovery_enabled,
                'active': self.recovery_active,
                'trigger_loss': self.recovery_trigger_loss,
                'auto_mode': self.recovery_auto_mode
            }
            
            if self.recovery_active and self.recovery_start_time:
                elapsed = (datetime.now() - self.recovery_start_time).total_seconds() / 60
                status.update({
                    'start_time': self.recovery_start_time.isoformat(),
                    'elapsed_minutes': round(elapsed, 1),
                    'initial_pnl': self.recovery_initial_pnl
                })
                
            return status
            
        except Exception as e:
            return {'error': str(e)}

# Integration example for ai_gold_grid.py
def integrate_smart_profit_manager(ai_gold_grid_instance):
    """Integrate smart profit manager into existing grid system"""
    
    # Create smart profit manager
    ai_gold_grid_instance.smart_profit_manager = SmartProfitManager(
        ai_gold_grid_instance, 
        ai_gold_grid_instance.config
    )
    
    # Add to main trading loop
    def enhanced_update_grid(self):
        """Enhanced grid update with smart profit management"""
        
        # Original grid update logic
        if not self.trading_active:
            return
            
        try:
            # Update current price
            self.update_current_price()
            
            # Check for filled orders
            self.check_filled_orders()
            
            # Update position PnL
            self.update_positions_pnl()
            
            # 🧠 NEW: Run smart profit management every 5 seconds
            if hasattr(self, 'smart_profit_manager') and hasattr(self, 'last_profit_check'):
                if (datetime.now() - self.last_profit_check).total_seconds() >= 5:
                    self.smart_profit_manager.run_smart_profit_management()
                    self.last_profit_check = datetime.now()
            elif hasattr(self, 'smart_profit_manager'):
                self.smart_profit_manager.run_smart_profit_management()
                self.last_profit_check = datetime.now()
            
            # Continue with original logic...
            self.check_grid_triggers()
            self.update_performance_metrics()
            self.check_emergency_conditions()
            
            self.last_update = datetime.now()
            
        except Exception as e:
            print(f"❌ Enhanced grid update error: {e}")
    
    # Replace the original method
    ai_gold_grid_instance.update_grid = enhanced_update_grid.__get__(ai_gold_grid_instance, type(ai_gold_grid_instance))
    
    print("✅ Smart Profit Manager integrated successfully!")
    
    return ai_gold_grid_instance.smart_profit_manager