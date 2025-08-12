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
import itertools

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
        """แก้ไขจากเดิม - เพิ่ม Strategic Reposition Logic"""
        try:
            if not self.auto_reposition_enabled:
                return
                
            current_price = self.grid_system.get_current_price()
            direction = closed_position.direction
            
            # 🔄 เพิ่ม: Portfolio Context Analysis
            current_positions = self.analyze_portfolio_positions().get('grid_positions', [])
            buy_count = len([p for p in current_positions if p.direction == "BUY"])
            sell_count = len([p for p in current_positions if p.direction == "SELL"])
            
            # 🔄 เพิ่ม: Strategic Gap Analysis
            same_direction_positions = [p for p in current_positions if p.direction == direction]
            
            if not same_direction_positions:
                # ไม่มีไม้ทิศทางเดียวกันเลย = ต้องวางใหม่ทันที URGENT
                fast_gap = 60  # ใช้ gap เล็กสำหรับ urgent case
                print(f"🚨 URGENT: No {direction} positions left!")
            else:
                # 🔄 เพิ่ม: วิเคราะห์ gap ที่เหมาะสม
                same_direction_positions.sort(key=lambda x: x.entry_price)
                
                if direction == "BUY":
                    # หา gap ใหญ่สุดด้านล่าง current price
                    below_current = [p for p in same_direction_positions if p.entry_price < current_price]
                    if below_current:
                        nearest_below = max(below_current, key=lambda x: x.entry_price)
                        gap_size = (current_price - nearest_below.entry_price) / 0.01
                        if gap_size > 200:  # gap ใหญ่
                            # วางตรงกลาง gap
                            new_price = (current_price + nearest_below.entry_price) / 2
                            distance = (current_price - new_price) / 0.01
                            print(f"🎯 Fill BUY gap: {gap_size:.0f}pts → place @ -{distance:.0f}pts")
                            fast_gap = distance
                        else:
                            fast_gap = 80  # ใช้ gap ปกติ
                    else:
                        fast_gap = 80  # ไม่มีไม้ด้านล่าง
                else:  # SELL
                    # หา gap ใหญ่สุดด้านบน current price
                    above_current = [p for p in same_direction_positions if p.entry_price > current_price]
                    if above_current:
                        nearest_above = min(above_current, key=lambda x: x.entry_price)
                        gap_size = (nearest_above.entry_price - current_price) / 0.01
                        if gap_size > 200:  # gap ใหญ่
                            # วางตรงกลาง gap
                            new_price = (current_price + nearest_above.entry_price) / 2
                            distance = (new_price - current_price) / 0.01
                            print(f"🎯 Fill SELL gap: {gap_size:.0f}pts → place @ +{distance:.0f}pts")
                            fast_gap = distance
                        else:
                            fast_gap = 80  # ใช้ gap ปกติ
                    else:
                        fast_gap = 80  # ไม่มีไม้ด้านบน
            
            # คำนวณราคาใหม่
            if direction == "BUY":
                new_price = current_price - (fast_gap * 0.01)
            else:
                new_price = current_price + (fast_gap * 0.01)
                
            # เช็คว่าไม่ซ้ำกับไม้เดิม
            min_distance = 60 * 0.01  # logic เดิม
            too_close = False
            for grid_level in self.grid_system.pending_orders.values():
                if (grid_level.direction == direction and 
                    abs(grid_level.price - new_price) < min_distance):
                    too_close = True
                    break
            
            if not too_close:
                success = self.place_replacement_position(direction, new_price, closed_position.lot_size)
                if success:
                    self.positions_turned_today += 1
                    distance = abs(new_price - current_price) / 0.01
                    print(f"🎯 STRATEGIC Reposition: {direction} @ ${new_price:.2f} ({distance:.0f}pts)")
                    
                    # 🔄 เพิ่ม: Portfolio Balance Check หลัง reposition
                    if direction == "BUY":
                        new_buy_count = buy_count + 1
                        if new_buy_count > sell_count + 2:  # BUY เยอะเกิน
                            print(f"⚖️ Post-reposition: Consider SELL orders (B:{new_buy_count} vs S:{sell_count})")
                    else:
                        new_sell_count = sell_count + 1
                        if new_sell_count > buy_count + 2:  # SELL เยอะเกิน
                            print(f"⚖️ Post-reposition: Consider BUY orders (B:{buy_count} vs S:{new_sell_count})")
                    
        except Exception as e:
            print(f"❌ Strategic reposition error: {e}")

    def is_too_close_to_existing_fast(self, price: float, direction: str) -> bool:
        """เช็คว่าตำแหน่งใหม่ใกล้ไม้เดิมเกินไป - ใช้ระยะใหม่"""
        # ✅ แก้ไขจาก 100 → 60 points (อนุญาตให้ใกล้ขึ้น)
        min_distance = 60 * 0.01  # จาก 100 → 60 points
        
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
        """AI Portfolio Analysis - ทับของเดิมเลย"""
        
        try:
            # Get all positions from MT5
            positions = mt5.positions_get(symbol=self.grid_system.gold_symbol)
            if not positions:
                return {'total_positions': 0, 'grid_positions': [], 'total_pnl': 0}
                
            # Filter our positions
            our_positions = [pos for pos in positions if pos.magic == self.grid_system.magic_number]
            
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
                'total_positions': len(grid_positions),
                'hedge_positions': len(hedge_positions), 
                'total_pnl': round(total_pnl, 2),
                'grid_positions': grid_positions,
                'hedge_positions': hedge_positions,
                'profitable_count': len(profitable_positions),
                'losing_count': len(losing_positions),
                'balance': self.get_account_balance(),
                'analysis_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Portfolio analysis error: {e}")
            return {'error': str(e)}
    
    def get_account_balance(self) -> float:
        """ดึง account balance"""
        try:
            account_info = self.grid_system.mt5_connector.get_account_info()
            return account_info.get('balance', 1000) if account_info else 1000
        except:
            return 1000

    def get_profit_management_status(self) -> Dict:
        """AI Portfolio Status - ทับของเดิมเลย"""
        
        try:
            portfolio = self.analyze_portfolio_positions()
            
            if 'error' in portfolio:
                return {'error': portfolio['error']}
            
            positions = portfolio.get('grid_positions', [])
            
            # AI Portfolio metrics
            buy_positions = [p for p in positions if p.direction == "BUY"]
            sell_positions = [p for p in positions if p.direction == "SELL"]
            
            # Find best opportunities
            profitable_pairs = self.find_profitable_pairs(positions)
            hedge_opportunities = self.find_hedge_opportunities(positions)
            
            # Portfolio health score (0-100)
            health_score = self.calculate_portfolio_health_score(portfolio)
            
            return {
                'strategy': f"AI_PORTFOLIO_{self.default_strategy.value}",
                'total_positions': portfolio.get('total_positions', 0),
                'buy_positions': len(buy_positions),
                'sell_positions': len(sell_positions),
                'hedge_positions': portfolio.get('hedge_positions', 0),
                'total_pnl': portfolio.get('total_pnl', 0),
                'profitable_pairs_found': len(profitable_pairs),
                'hedge_opportunities': len(hedge_opportunities),
                'portfolio_health': health_score,
                'trailing_stops_active': 0,  # ไม่ใช้ trailing stops แล้ว
                'risk_percentage': abs(portfolio.get('total_pnl', 0)) / portfolio.get('balance', 1000) * 100,
                'ai_mode': 'ACTIVE',
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}

    def calculate_portfolio_health_score(self, portfolio) -> int:
        """คำนวณ portfolio health score (0-100)"""
        
        try:
            total_pnl = portfolio.get('total_pnl', 0)
            total_positions = portfolio.get('total_positions', 0)
            profitable_count = portfolio.get('profitable_count', 0)
            losing_count = portfolio.get('losing_count', 0)
            balance = portfolio.get('balance', 1000)
            
            # Base score
            health_score = 50
            
            # PnL factor
            pnl_ratio = total_pnl / balance * 100
            if pnl_ratio > 5:
                health_score += 30  # Very good
            elif pnl_ratio > 0:
                health_score += 15  # Good
            elif pnl_ratio > -5:
                health_score += 0   # Neutral
            elif pnl_ratio > -15:
                health_score -= 20  # Bad
            else:
                health_score -= 40  # Very bad
            
            # Position balance factor
            if total_positions > 0:
                balance_ratio = abs(profitable_count - losing_count) / total_positions
                if balance_ratio < 0.3:
                    health_score += 20  # Well balanced
                elif balance_ratio < 0.6:
                    health_score += 10  # Moderately balanced
                else:
                    health_score -= 10  # Imbalanced
            
            # Bounds
            health_score = max(0, min(health_score, 100))
            
            return int(health_score)
            
        except Exception as e:
            print(f"❌ Health score calculation error: {e}")
            return 50

    def identify_profit_opportunities(self, portfolio_analysis: Dict) -> List:
        """AI หาโอกาสทำกำไร - ทับของเดิมเลย"""
        
        opportunities = []
        
        try:
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
                self.place_smart_replacement_after_close(position)
                
                return True
            else:
                print(f"❌ AI Close failed: {position.position_id}")
                return False
                
        except Exception as e:
            print(f"❌ Smart close error: {e}")
            return False

    def place_smart_replacement_after_close(self, closed_position):
        """วางไม้ใหม่อัจฉริยะหลังปิด"""
        
        try:
            current_price = self.grid_system.get_current_price()
            
            # AI ตัดสินใจตำแหน่งใหม่
            if closed_position.pnl > 0:
                # ปิดได้กำไร = วางใกล้ๆ เดิม (คาดว่าจะได้กำไรต่อ)
                distance = 150  # 150 points
            else:
                # ปิดขาดทุน = วางไกลออกไปหน่อย (ให้เวลา market ปรับตัว)
                distance = 250  # 250 points
                
            if closed_position.direction == "BUY":
                new_price = current_price - (distance * 0.01)
                new_direction = "BUY"
            else:
                new_price = current_price + (distance * 0.01) 
                new_direction = "SELL"
            
            # วางไม้ใหม่
            success = self.place_single_replacement_order(new_direction, new_price, closed_position.lot_size)
            if success:
                print(f"   🔄 AI Replacement: {new_direction} @ ${new_price:.2f} (distance: {distance}pts)")
            
        except Exception as e:
            print(f"❌ Smart replacement error: {e}")
        
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
                        
    def run_smart_profit_management(self):
        """แก้ไขจากเดิม - เพิ่ม Smart Override เมื่อกำไรดี"""
        try:
            # 1. วิเคราะห์ positions ทั้งหมด (logic เดิม)
            portfolio = self.analyze_portfolio_positions()
            if 'error' in portfolio or portfolio.get('total_positions', 0) == 0:
                print("🔄 No positions - creating initial grid")
                self.create_initial_grid_smart()
                return
                
            positions = portfolio.get('grid_positions', [])
            total_pnl = portfolio.get('total_pnl', 0)
            
            print(f"🧠 AI Portfolio: {len(positions)} positions, Total PnL: ${total_pnl:.2f}")
            
            # 🔄 เพิ่ม: Portfolio Health Check ก่อนทำอะไร
            buy_positions = [p for p in positions if p.direction == "BUY"]
            sell_positions = [p for p in positions if p.direction == "SELL"]
            
            buy_pnl = sum(p.pnl for p in buy_positions)
            sell_pnl = sum(p.pnl for p in sell_positions)
            
            print(f"📈 Directional PnL: BUY ${buy_pnl:.2f} ({len(buy_positions)}), SELL ${sell_pnl:.2f} ({len(sell_positions)})")
            
            # 🔄 เพิ่ม: Smart Override Logic
            portfolio_imbalance = abs(len(buy_positions) - len(sell_positions))
            
            # ✅ OVERRIDE CONDITIONS - ปล่อยให้เก็บกำไรได้
            should_override_portfolio_first = False
            override_reason = ""
            
            # Override 1: Total profit ดีมาก
            if total_pnl > 100:
                should_override_portfolio_first = True
                override_reason = f"Total profit ${total_pnl:.2f} > $100"
                
            # Override 2: มีไม้เยอะแล้ว
            elif len(positions) > 80:
                should_override_portfolio_first = True
                override_reason = f"High coverage ({len(positions)} positions)"
                
            # Override 3: Imbalance ไม่รุนแรง
            elif portfolio_imbalance <= 6:
                should_override_portfolio_first = True
                override_reason = f"Moderate imbalance ({portfolio_imbalance})"
                
            # Override 4: มีไม้กำไรเยอะ
            profitable_count = len([p for p in positions if p.pnl > 0])
            if profitable_count > 20:
                should_override_portfolio_first = True
                override_reason = f"Many profitable positions ({profitable_count})"
            
            # 🎯 DECISION MAKING
            if should_override_portfolio_first:
                print(f"🚀 OVERRIDE Portfolio-First: {override_reason}")
                print("💰 Proceeding with selective profit taking...")
                
                # 2. หาคู่ที่ปิดได้ (ใช้ smart retention ที่มีอยู่)
                profitable_pairs = self.find_profitable_pairs(positions)
                
                if profitable_pairs:
                    print(f"💰 Found {len(profitable_pairs)} profitable pairs (with smart retention)")
                    self.execute_pair_closes(profitable_pairs)  # ใช้ method ที่แก้แล้ว
                    time.sleep(1)
                    portfolio = self.analyze_portfolio_positions()
                    positions = portfolio.get('grid_positions', [])
                    total_pnl = portfolio.get('total_pnl', 0)
                    print(f"🔄 After pair closing: {len(positions)} positions, PnL: ${total_pnl:.2f}")
                
            elif portfolio_imbalance > 6:  # เฉพาะ imbalance สูงมากถึงจะ block
                print(f"⚖️ PORTFOLIO-FIRST: Critical imbalance ({portfolio_imbalance}) - Prioritizing balance over profit")
                # ทำ rebalance ก่อน profit taking แต่ FIX LOGIC
                self.smart_portfolio_rebalancing(buy_positions, sell_positions, total_pnl)
                return  # skip profit taking ในรอบนี้เฉพาะ critical cases
                
            else:
                print(f"⚖️ Balanced enough ({portfolio_imbalance}) - Normal profit taking")
                # 2. หาคู่ที่ปิดได้ (logic ปกติ)
                profitable_pairs = self.find_profitable_pairs(positions)
                
                if profitable_pairs:
                    print(f"💰 Found {len(profitable_pairs)} profitable pairs")
                    self.execute_pair_closes(profitable_pairs)
                    time.sleep(1)
                    portfolio = self.analyze_portfolio_positions()
                    positions = portfolio.get('grid_positions', [])
                    total_pnl = portfolio.get('total_pnl', 0)
                    print(f"🔄 After pair closing: {len(positions)} positions, PnL: ${total_pnl:.2f}")
            
            # 3. Portfolio rebalancing (ทำเสมอ แต่ไม่ block profit)
            if len(positions) > 0:
                self.rebalance_portfolio_if_needed(positions)
            
            # ✅ existing logic ต่อไป...
            self.check_and_fill_gaps_fast(self.grid_system.get_current_price())
            
        except Exception as e:
            print(f"❌ Smart override profit management error: {e}")

    def smart_portfolio_rebalancing(self, buy_positions, sell_positions, total_pnl):
        """Smart rebalancing ที่ไม่ทำให้ imbalance แย่ลง - ปรับปรุงแล้ว"""
        try:
            buy_count = len(buy_positions)
            sell_count = len(sell_positions)
            current_price = self.grid_system.get_current_price()
            
            print(f"🔧 Enhanced Smart Rebalancing: {buy_count}B vs {sell_count}S")
            
            # ✅ เพิ่ม: เรียก gap filling ทุกครั้ง (ไม่รออะไร)
            self.check_and_fill_gaps_fast(current_price)
            
            # วิเคราะห์ว่าด้านไหนเสียหนัก
            buy_pnl = sum(p.pnl for p in buy_positions)
            sell_pnl = sum(p.pnl for p in sell_positions)
            
            # ✅ ปรับ: ลดระยะการตรวจสอบ
            orders_needed = max(0, 50 - (buy_count + sell_count))  # เป้าหมาย 50 positions รวม
            
            if orders_needed > 0:
                # ✅ ปรับ: สมดุลที่ดีขึ้น
                if buy_count < sell_count - 2:
                    # ต้องการ BUY มากกว่า
                    buy_needed = min(orders_needed, 4)  # เพิ่มจาก 2 เป็น 4
                    sell_needed = orders_needed - buy_needed
                    print(f"🎯 Priority: {buy_needed} BUY, {sell_needed} SELL")
                    
                    # ✅ ปรับ: ใช้ spacing แคบขึ้น
                    for i in range(buy_needed):
                        spacing = 80 + (i * 30)  # 80, 110, 140, 170 จุด
                        buy_price = current_price - (spacing * 0.01)
                        if not self.grid_system.has_nearby_order("BUY", buy_price, 50):
                            self.grid_system.place_smart_rebalance_order("BUY", buy_price, self.grid_system.base_lot)
                            
                elif sell_count < buy_count - 2:
                    # ต้องการ SELL มากกว่า
                    sell_needed = min(orders_needed, 4)  # เพิ่มจาก 2 เป็น 4
                    buy_needed = orders_needed - sell_needed
                    print(f"🎯 Priority: {buy_needed} BUY, {sell_needed} SELL")
                    
                    # ✅ ปรับ: ใช้ spacing แคบขึ้น
                    for i in range(sell_needed):
                        spacing = 80 + (i * 30)  # 80, 110, 140, 170 จุด
                        sell_price = current_price + (spacing * 0.01)
                        if not self.grid_system.has_nearby_order("SELL", sell_price, 50):
                            self.grid_system.place_smart_rebalance_order("SELL", sell_price, self.grid_system.base_lot)
                else:
                    # วางเท่ากัน
                    buy_needed = sell_needed = orders_needed // 2
                    print(f"🎯 Balanced: {buy_needed} BUY, {sell_needed} SELL")
                    
                    for i in range(buy_needed):
                        spacing = 80 + (i * 30)  # 80, 110, 140, 170 จุด
                        buy_price = current_price - (spacing * 0.01)
                        if not self.grid_system.has_nearby_order("BUY", buy_price, 50):
                            self.grid_system.place_smart_rebalance_order("BUY", buy_price, self.grid_system.base_lot)
                            
                    for i in range(sell_needed):
                        spacing = 80 + (i * 30)  # 80, 110, 140, 170 จุด
                        sell_price = current_price + (spacing * 0.01)
                        if not self.grid_system.has_nearby_order("SELL", sell_price, 50):
                            self.grid_system.place_smart_rebalance_order("SELL", sell_price, self.grid_system.base_lot)
            
            # ✅ เพิ่ม: Hot zone maintenance
            self.maintain_hot_zone(current_price)
            
            # เดิม: logic ปกติสำหรับ losing sides
            if buy_count > sell_count:  # BUY เยอะ
                if buy_pnl < -50:  # BUY เสียหนัก
                    print(f"🔧 BUY heavy + losing ${abs(buy_pnl):.1f} → Add SELL hedge (limited)")
                    self.add_sell_orders_for_balance(current_price, min(2, abs(buy_count - sell_count) // 2))
                else:
                    print(f"🔧 BUY heavy but not losing much → Reduce BUY bias")
                    
            elif sell_count > buy_count:  # SELL เยอะ  
                if sell_pnl < -50:  # SELL เสียหนัก
                    print(f"🔧 SELL heavy + losing ${abs(sell_pnl):.1f} → Add BUY hedge (limited)")
                    self.add_buy_orders_for_balance(current_price, min(2, abs(sell_count - buy_count) // 2))
                else:
                    print(f"🔧 SELL heavy but not losing much → Reduce SELL bias")
            
            # ถ้า total profit ดี ให้ปิดไม้เสียหนักๆ บ้าง
            if total_pnl > 50:
                heavy_losing = [p for p in buy_positions + sell_positions if p.pnl < -20]
                if heavy_losing:
                    print(f"💡 Total profit good (${total_pnl:.2f}) → Consider closing heavy losses")
                    
        except Exception as e:
            print(f"❌ Enhanced smart portfolio rebalancing error: {e}")


    def maintain_hot_zone(self, current_price):
        """รักษาโซนร้อนให้มีไม้อยู่เสมอ - Method ใหม่"""
        try:
            hot_zone = 400  # ±400 จุด
            
            # เช็คว่ามีไม้ในโซนร้อนไหม
            buy_in_zone = False
            sell_in_zone = False
            
            for order in self.grid_system.pending_orders.values():
                distance = abs(order.price - current_price) / 0.01
                
                if distance <= hot_zone:
                    if order.direction == "BUY" and order.price < current_price:
                        buy_in_zone = True
                    elif order.direction == "SELL" and order.price > current_price:
                        sell_in_zone = True
            
            # วางไม้ในโซนร้อนถ้าไม่มี
            if not buy_in_zone:
                buy_price = current_price - (200 * 0.01)  # 200 จุดด้านล่าง
                # ✅ แก้ไข: ใช้ parameter order ที่ถูกต้อง
                if not self.grid_system.has_nearby_order("BUY", buy_price, 100):
                    self.grid_system.place_smart_rebalance_order("BUY", buy_price, self.grid_system.base_lot)
                    print(f"🔥 Hot zone BUY: @ ${buy_price:.2f}")
            
            if not sell_in_zone:
                sell_price = current_price + (200 * 0.01)  # 200 จุดด้านบน
                # ✅ แก้ไข: ใช้ parameter order ที่ถูกต้อง
                if not self.grid_system.has_nearby_order("SELL", sell_price, 100):
                    self.grid_system.place_smart_rebalance_order("SELL", sell_price, self.grid_system.base_lot)
                    print(f"🔥 Hot zone SELL: @ ${sell_price:.2f}")
                    
        except Exception as e:
            print(f"❌ Hot zone maintenance error: {e}")

    def create_initial_grid_smart(self):
        """สร้าง grid เริ่มต้นอย่างฉลาด - ไม่มั่ว"""
        try:
            current_price = self.grid_system.get_current_price()
            
            spacing = 150  # Fixed spacing
            
            print(f"🚀 Creating smart initial grid @ ${current_price:.2f}")
            
            # ✅ เช็คก่อนว่ามี orders อยู่แล้วไหม
            existing_orders = self.get_all_existing_orders()
            
            if len(existing_orders) > 0:
                print(f"   ⚠️ Found {len(existing_orders)} existing orders - skipping initial creation")
                return
            
            # สร้างแค่ 3 คู่ที่ระยะห่างชัดเจน
            orders_created = 0
            for i in range(1, 4):  # 1, 2, 3
                buy_price = round(current_price - (spacing * i * 0.01), 2)
                sell_price = round(current_price + (spacing * i * 0.01), 2)
                
                # วาง BUY order
                if self.grid_system.place_smart_rebalance_order("BUY", buy_price, self.grid_system.base_lot):
                    orders_created += 1
                    
                # วาง SELL order  
                if self.grid_system.place_smart_rebalance_order("SELL", sell_price, self.grid_system.base_lot):
                    orders_created += 1
                    
            print(f"✅ Created {orders_created} initial orders with {spacing} points spacing")
            
        except Exception as e:
            print(f"❌ Smart initial grid error: {e}")

    def smart_rebalance_with_checks(self, positions):
        """Rebalancing อย่างฉลาด - แก้ไขให้ aggressive กว่าเดิม"""
        try:
            current_price = self.grid_system.get_current_price()
            buy_count = len([p for p in positions if p.direction == "BUY"])
            sell_count = len([p for p in positions if p.direction == "SELL"])
            
            print(f"📊 Smart Check: {buy_count} BUY, {sell_count} SELL @ ${current_price:.2f}")
            
            # ✅ เช็ค existing orders ก่อน
            existing_orders = self.get_all_existing_orders()
            buy_orders = [o for o in existing_orders if o['direction'] == "BUY"]
            sell_orders = [o for o in existing_orders if o['direction'] == "SELL"]
            
            total_coverage = len(buy_orders) + len(sell_orders) + len(positions)
            print(f"📋 Total coverage: {total_coverage} ({len(positions)} positions + {len(existing_orders)} orders)")
            
            # ✅ แก้ไข: ลดเงื่อนไข coverage จาก 8 เป็น 6
            if total_coverage >= 6 and abs(buy_count - sell_count) <= 1:
                print("   ✅ Sufficient coverage - no rebalancing needed")
                return
                
            # ✅ แก้ไข: Balance check ไวขึ้น - ถ้าต่างกัน > 1 (แทน > 2)
            if abs(buy_count - sell_count) > 1:
                imbalance = buy_count - sell_count
                print(f"⚖️ Portfolio imbalance detected: {imbalance}")
                self.fix_portfolio_imbalance_aggressive(current_price, imbalance, existing_orders)
                return
                
            # ✅ เพิ่ม: เช็ค extreme imbalance (เช่น 0 BUY vs 3 SELL)
            if buy_count == 0 and sell_count > 0:
                print(f"🚨 EXTREME: No BUY positions vs {sell_count} SELL - Force adding BUY orders")
                self.force_add_buy_orders(current_price, min(sell_count, 3))
                return
                
            if sell_count == 0 and buy_count > 0:
                print(f"🚨 EXTREME: No SELL positions vs {buy_count} BUY - Force adding SELL orders")
                self.force_add_sell_orders(current_price, min(buy_count, 3))
                return
            
            # ✅ เช็ค gaps ก่อนเพิ่ม orders
            gaps = self.find_significant_gaps(current_price, existing_orders + positions)
            
            if gaps['buy_gaps']:
                print(f"🔍 Found BUY gaps: {len(gaps['buy_gaps'])} locations")
                self.fill_specific_gaps(gaps['buy_gaps'], "BUY")
                
            if gaps['sell_gaps']:
                print(f"🔍 Found SELL gaps: {len(gaps['sell_gaps'])} locations")
                self.fill_specific_gaps(gaps['sell_gaps'], "SELL")
                
        except Exception as e:
            print(f"❌ Smart rebalance error: {e}")

    def fix_portfolio_imbalance_aggressive(self, current_price, imbalance, existing_orders):
        """แก้ไข portfolio imbalance แบบ aggressive"""
        try:
            if imbalance < 0:  # SELL มากกว่า BUY
                needed_buy = abs(imbalance)
                print(f"🔄 Adding {needed_buy} BUY orders to balance SELL heavy portfolio")
                self.force_add_buy_orders(current_price, needed_buy)
            else:  # BUY มากกว่า SELL  
                needed_sell = abs(imbalance)
                print(f"🔄 Adding {needed_sell} SELL orders to balance BUY heavy portfolio")
                self.force_add_sell_orders(current_price, needed_sell)
                
        except Exception as e:
            print(f"❌ Aggressive imbalance fix error: {e}")

    def force_add_buy_orders(self, current_price, count):
        """บังคับเพิ่ม BUY orders"""
        try:
            spacing = 120  # ใช้ spacing เล็ก 120 จุด
            
            for i in range(min(count, 4)):  # เพิ่มสูงสุด 4 ตัว
                price = current_price - (spacing * (i + 1) * 0.01)
                
                # ตรวจสอบว่าไกลเกินไปไหม
                distance = (current_price - price) / 0.01
                if distance > 600:  # ไม่เกิน 600 จุด
                    print(f"   ⚠️ BUY order too far: {distance:.0f} points")
                    continue
                    
                if not self.grid_system.has_nearby_order(price, "BUY"):
                    success = self.grid_system.place_smart_rebalance_order("BUY", price, self.grid_system.base_lot)
                    if success:
                        print(f"   🚀 Force BUY: 0.01 @ ${price:.2f} ({distance:.0f} pts)")
                        
        except Exception as e:
            print(f"❌ Force BUY orders error: {e}")

    def force_add_sell_orders(self, current_price, count):
        """บังคับเพิ่ม SELL orders"""
        try:
            spacing = 120  # ใช้ spacing เล็ก 120 จุด
            
            for i in range(min(count, 4)):  # เพิ่มสูงสุด 4 ตัว
                price = current_price + (spacing * (i + 1) * 0.01)
                
                # ตรวจสอบว่าไกลเกินไปไหม
                distance = (price - current_price) / 0.01
                if distance > 600:  # ไม่เกิน 600 จุด
                    print(f"   ⚠️ SELL order too far: {distance:.0f} points")
                    continue
                    
                if not self.grid_system.has_nearby_order(price, "SELL"):
                    success = self.grid_system.place_smart_rebalance_order("SELL", price, self.grid_system.base_lot)
                    if success:
                        print(f"   🚀 Force SELL: 0.01 @ ${price:.2f} ({distance:.0f} pts)")
                        
        except Exception as e:
            print(f"❌ Force SELL orders error: {e}")


    def get_all_existing_orders(self):
        """รวบรวม orders ทั้งหมดที่มีอยู่"""
        try:
            all_orders = []
            
            # Pending orders
            for order in self.grid_system.pending_orders.values():
                all_orders.append({
                    'price': order.price,
                    'direction': order.direction,
                    'type': 'pending',
                    'lot_size': order.lot_size
                })
                
            # Active positions
            for pos in self.grid_system.active_positions.values():
                all_orders.append({
                    'price': pos.price,
                    'direction': pos.direction,
                    'type': 'active',
                    'lot_size': pos.lot_size
                })
                
            return all_orders
            
        except Exception as e:
            print(f"❌ Get existing orders error: {e}")
            return []

    def find_significant_gaps(self, current_price, existing_orders):
        """หา gaps ที่สำคัญจริงๆ"""
        try:
            buy_orders = [o for o in existing_orders if o['direction'] == "BUY"]
            sell_orders = [o for o in existing_orders if o['direction'] == "SELL"]
            
            gaps = {'buy_gaps': [], 'sell_gaps': []}
            significant_gap = 250  # ช่องว่างที่ใหญ่จริงๆ (250 จุด)
            
            # เช็ค BUY gaps
            if buy_orders:
                buy_prices = sorted([o['price'] for o in buy_orders], reverse=True)
                
                # เช็คช่องว่างระหว่าง current price กับ order ที่ใกล้ที่สุด
                nearest_buy = buy_prices[0]
                gap_to_current = (current_price - nearest_buy) / 0.01
                
                if gap_to_current > significant_gap:
                    target_price = current_price - (150 * 0.01)  # วางที่ 150 จุด
                    gaps['buy_gaps'].append({
                        'price': target_price,
                        'gap_size': gap_to_current,
                        'reason': f'Gap to current: {gap_to_current:.0f} points'
                    })
            else:
                # ไม่มี BUY orders เลย
                gaps['buy_gaps'].append({
                    'price': current_price - (150 * 0.01),
                    'gap_size': 999,
                    'reason': 'No BUY orders exist'
                })
                
            # เช็ค SELL gaps
            if sell_orders:
                sell_prices = sorted([o['price'] for o in sell_orders])
                
                nearest_sell = sell_prices[0]
                gap_to_current = (nearest_sell - current_price) / 0.01
                
                if gap_to_current > significant_gap:
                    target_price = current_price + (150 * 0.01)
                    gaps['sell_gaps'].append({
                        'price': target_price,
                        'gap_size': gap_to_current,
                        'reason': f'Gap to current: {gap_to_current:.0f} points'
                    })
            else:
                # ไม่มี SELL orders เลย
                gaps['sell_gaps'].append({
                    'price': current_price + (150 * 0.01),
                    'gap_size': 999,
                    'reason': 'No SELL orders exist'
                })
                
            return gaps
            
        except Exception as e:
            print(f"❌ Find gaps error: {e}")
            return {'buy_gaps': [], 'sell_gaps': []}

    def fill_specific_gaps(self, gaps, direction):
        """เติมช่องว่างเฉพาะที่จำเป็น"""
        try:
            for gap in gaps[:2]:  # เติมสูงสุด 2 ช่องว่าง
                price = gap['price']
                
                # ✅ เช็คอีกครั้งก่อนวาง
                if not self.grid_system.has_nearby_order(price, direction):
                    success = self.grid_system.place_smart_rebalance_order(direction, price, self.grid_system.base_lot)
                    if success:
                        print(f"   🔧 Filled {direction} gap @ ${price:.2f} ({gap['reason']})")
                        
        except Exception as e:
            print(f"❌ Fill specific gaps error: {e}")


    def find_profitable_pairs(self, positions):
        """🚀 ENHANCED Multi-Position Pairing - แก้ไข Over-Protection"""
        try:
            # 🔧 Safe check for positions
            if not positions or len(positions) == 0:
                print("⚠️ No positions provided")
                return []
            
            all_profitable_pairs = []
            buy_positions = [p for p in positions if hasattr(p, 'direction') and p.direction == "BUY"]
            sell_positions = [p for p in positions if hasattr(p, 'direction') and p.direction == "SELL"]
            
            print(f"🔍 Multi-Position Analysis: {len(buy_positions)} BUY, {len(sell_positions)} SELL")
            
            if len(buy_positions) == 0 and len(sell_positions) == 0:
                print("⚠️ No valid positions found")
                return []
            
            # 🧠 SMART RETENTION: กรองไม้ที่ควรเก็บไว้ hedge ก่อน
            print(f"🧠 === RELAXED POSITION RETENTION ===")
            
            # แยกไม้กำไรและไม้เสีย (safe check)
            profitable_positions = [p for p in positions if hasattr(p, 'pnl') and p.pnl > 0]
            losing_positions = [p for p in positions if hasattr(p, 'pnl') and p.pnl < -1]  # เสีย > $1
            
            print(f"💰 Profitable positions: {len(profitable_positions)}")
            print(f"🔴 Losing positions: {len(losing_positions)}")
            
            if len(profitable_positions) == 0:
                print("⚠️ No profitable positions found")
                return []
            
            # 🎯 RELAXED RETENTION LOGIC: ลดการป้องกันลง
            protected_positions = set()  # ไม้ที่ห้ามปิด
            closeable_positions = []     # ไม้ที่ปิดได้
            
            # ✅ แก้ไข: ลดการ protection ลงมาก
            protection_count = 0
            max_protection_count = min(15, len(profitable_positions) // 3)  # ป้องกันสูงสุด 15 ตัว หรือ 1/3
            
            print(f"🔧 Max protection limit: {max_protection_count} positions")
            
            for profit_pos in profitable_positions:
                try:
                    # ✅ แก้ไข: เพิ่มเงื่อนไขการ skip protection
                    if protection_count >= max_protection_count:
                        # เกินจำนวนที่ป้องกันได้แล้ว → ปิดได้ทุกตัว
                        closeable_positions.append(profit_pos)
                        print(f"✅ CLOSEABLE (quota exceeded): {profit_pos.direction} ${profit_pos.pnl:.2f}")
                        continue
                    
                    should_keep = self.should_keep_for_hedge(profit_pos, losing_positions, positions)
                    
                    # Safe check for should_keep result
                    if should_keep and isinstance(should_keep, dict):
                        protection_score = should_keep.get('protection_score', 0)
                        keep_decision = should_keep.get('keep', False)
                        
                        # ✅ แก้ไข: เข้มงวดมากขึ้นในการ protect
                        if (keep_decision and 
                            protection_score > 80 and  # เพิ่มจาก 50 เป็น 80 (ป้องกันเฉพาะที่สำคัญมาก)
                            protection_count < max_protection_count):
                            
                            protected_positions.add(profit_pos.position_id)
                            protection_count += 1
                            reason = should_keep.get('reason', 'Unknown reason')
                            print(f"🛡️ PROTECTED ({protection_count}/{max_protection_count}): {profit_pos.direction} ${profit_pos.pnl:.2f} - {reason} (Score: {protection_score:.1f})")
                        else:
                            closeable_positions.append(profit_pos)
                            if keep_decision:
                                print(f"✅ CLOSEABLE (low score): {profit_pos.direction} ${profit_pos.pnl:.2f} (Score: {protection_score:.1f})")
                            else:
                                print(f"✅ CLOSEABLE: {profit_pos.direction} ${profit_pos.pnl:.2f}")
                    else:
                        # Fallback if should_keep_for_hedge fails
                        closeable_positions.append(profit_pos)
                        print(f"✅ CLOSEABLE (fallback): {profit_pos.direction} ${profit_pos.pnl:.2f}")
                        
                except Exception as e:
                    print(f"⚠️ Error checking position {profit_pos.position_id}: {e}")
                    # Fallback: make it closeable
                    closeable_positions.append(profit_pos)
            
            print(f"🛡️ Protected positions: {len(protected_positions)}")
            print(f"✅ Closeable positions: {len(closeable_positions)}")
            
            # 📊 ใช้เฉพาะไม้ที่ปิดได้ในการจับคู่
            filtered_buy_positions = [p for p in buy_positions if hasattr(p, 'position_id') and p.position_id not in protected_positions]
            filtered_sell_positions = [p for p in sell_positions if hasattr(p, 'position_id') and p.position_id not in protected_positions]
            
            print(f"🎯 After filtering - BUY: {len(filtered_buy_positions)}, SELL: {len(filtered_sell_positions)}")
            
            # ✅ แก้ไข: ลด threshold สำหรับ emergency override
            if len(filtered_buy_positions) == 0 and len(filtered_sell_positions) == 0:
                if len(profitable_positions) > 10:  # ลดจาก 30 เป็น 10
                    print("🔄 Too many protected positions - AGGRESSIVE emergency override...")
                    
                    # ✅ แก้ไข: ลด protection score threshold อย่างรุนแรง
                    relaxed_positions = []
                    for profit_pos in profitable_positions:
                        try:
                            retention_check = self.should_keep_for_hedge(profit_pos, losing_positions, positions)
                            if retention_check and isinstance(retention_check, dict):
                                protection_score = retention_check.get('protection_score', 100)
                                # ✅ ลด threshold จาก 50 เป็น 20 (เปิดกว้างมาก)
                                if protection_score < 20 or len(relaxed_positions) < 8:  # บังคับเอา 8 ตัวแรก
                                    relaxed_positions.append(profit_pos)
                                    print(f"   🟡 RELAXED: {profit_pos.direction} ${profit_pos.pnl:.2f} (Score: {protection_score:.1f})")
                        except Exception as e:
                            # ใส่เข้าไปเลยถ้า error
                            relaxed_positions.append(profit_pos)
                            print(f"   🟡 RELAXED (error): {profit_pos.direction} ${profit_pos.pnl:.2f}")
                            continue
                    
                    if relaxed_positions:
                        # แยก BUY/SELL ที่ปิดได้
                        relaxed_buy = [p for p in relaxed_positions if p.direction == "BUY"]
                        relaxed_sell = [p for p in relaxed_positions if p.direction == "SELL"]
                        
                        print(f"🎯 AGGRESSIVE override - BUY: {len(relaxed_buy)}, SELL: {len(relaxed_sell)}")
                        
                        # อัพเดต filtered positions
                        filtered_buy_positions = relaxed_buy[:8]  # เพิ่มจาก 5 เป็น 8 ตัว
                        filtered_sell_positions = relaxed_sell[:8]  # เพิ่มจาก 5 เป็น 8 ตัว
                    else:
                        print("🛡️ All profitable positions have high protection scores")
                        
                        # ✅ เพิ่ม: FORCE OVERRIDE สำหรับกรณีฉุกเฉิน
                        print("💥 FORCE OVERRIDE: Taking top profit positions anyway...")
                        
                        # เรียงตาม PnL และเอาที่กำไรมากสุด
                        top_profitable = sorted(profitable_positions, key=lambda x: x.pnl, reverse=True)[:6]
                        
                        force_buy = [p for p in top_profitable if p.direction == "BUY"][:3]
                        force_sell = [p for p in top_profitable if p.direction == "SELL"][:3]
                        
                        print(f"💥 FORCE - BUY: {len(force_buy)}, SELL: {len(force_sell)}")
                        
                        filtered_buy_positions = force_buy
                        filtered_sell_positions = force_sell
                else:
                    print("🛡️ All profitable positions are protected for hedge purposes")
                    return []
            
            # ถ้าไม่มีคู่ให้จับ → ลองปิดทีละตัว
            if len(filtered_buy_positions) == 0 or len(filtered_sell_positions) == 0:
                print("💡 Trying INDIVIDUAL profitable positions...")
                
                individual_profits = []
                all_filtered = filtered_buy_positions + filtered_sell_positions
                
                # ✅ แก้ไข: ลด threshold จาก 1.0 เป็น 0.3
                min_profit_threshold = 0.3  # ลดจาก 1.0 เป็น 0.3
                
                print(f"   🔍 Checking {len(all_filtered)} positions (min profit: ${min_profit_threshold})")
                
                for i, pos in enumerate(all_filtered):
                    try:
                        if hasattr(pos, 'pnl'):
                            print(f"   Position {i+1}: {pos.direction} PnL=${pos.pnl:.2f}")
                            
                            if pos.pnl > min_profit_threshold:
                                individual_profits.append({
                                    'losing_positions': [],
                                    'profitable_positions': [pos],
                                    'net_profit': pos.pnl,
                                    'total_positions': 1,
                                    'pair_type': "SINGLE",
                                    'priority_score': pos.pnl,
                                    'position_ids': {pos.position_id}
                                })
                                print(f"   ✅ Added individual: {pos.direction} +${pos.pnl:.2f}")
                            else:
                                print(f"   ❌ Too small profit: {pos.direction} +${pos.pnl:.2f} < ${min_profit_threshold}")
                        else:
                            print(f"   ⚠️ Position {i+1} has no PnL attribute")
                    except Exception as e:
                        print(f"   ❌ Error checking position {i+1}: {e}")
                
                if individual_profits:
                    individual_profits.sort(key=lambda x: x['net_profit'], reverse=True)
                    print(f"💰 Found {len(individual_profits)} profitable singles")
                    return individual_profits[:5]  # เพิ่มจาก 3 เป็น 5 ตัว
                else:
                    print("❌ No individual profitable positions found!")
                    
                    # ✅ เพิ่ม: EMERGENCY - ปิดอะไรก็ได้ที่มีกำไร
                    if all_filtered:
                        print("🚨 EMERGENCY: Taking ANY positive PnL...")
                        emergency_profits = []
                        
                        for pos in all_filtered:
                            if hasattr(pos, 'pnl') and pos.pnl > 0:  # แค่ให้มีกำไรมากกว่า 0
                                emergency_profits.append({
                                    'losing_positions': [],
                                    'profitable_positions': [pos],
                                    'net_profit': pos.pnl,
                                    'total_positions': 1,
                                    'pair_type': "EMERGENCY_SINGLE",
                                    'priority_score': pos.pnl + 1000,  # High priority
                                    'position_ids': {pos.position_id}
                                })
                                print(f"   🚨 Emergency single: {pos.direction} +${pos.pnl:.2f}")
                        
                        if emergency_profits:
                            emergency_profits.sort(key=lambda x: x['net_profit'], reverse=True)
                            print(f"🚨 EMERGENCY: Found {len(emergency_profits)} ANY profit singles")
                            return emergency_profits[:3]  # ปิดแค่ 3 ตัว
                    
                    return []
            
            # ✅ เพิ่ม: จำกัดจำนวน positions ก่อนสร้างคู่ (แก้ปัญหาหลัก)
            max_positions_per_side = 8  # จำกัดสูงสุด 8 ตัวแต่ละด้าน
            if len(filtered_buy_positions) > max_positions_per_side:
                filtered_buy_positions = sorted(filtered_buy_positions, key=lambda x: x.pnl, reverse=True)[:max_positions_per_side]
                print(f"🔧 Limited BUY positions to {max_positions_per_side} (best PnL)")
                
            if len(filtered_sell_positions) > max_positions_per_side:
                filtered_sell_positions = sorted(filtered_sell_positions, key=lambda x: x.pnl, reverse=True)[:max_positions_per_side]
                print(f"🔧 Limited SELL positions to {max_positions_per_side} (best PnL)")
            
            # 🎯 Multi-Position Pairing (with safe checks and limits)
            pairs_1_1 = []
            pairs_1_to_n = []  
            pairs_n_to_1 = []
            pairs_complex = []
            
            # ✅ เพิ่ม: จำกัดจำนวนคู่สูงสุดต่อประเภท
            max_pairs_per_type = 15  # จำกัดสูงสุด 15 คู่ต่อประเภท
            
            try:
                pairs_1_1 = (self.find_1_to_1_pairs(filtered_buy_positions, filtered_sell_positions) or [])[:max_pairs_per_type]
                all_profitable_pairs.extend(pairs_1_1)
                print(f"   💰 1:1 pairs: {len(pairs_1_1)} (limited to {max_pairs_per_type})")
            except Exception as e:
                print(f"⚠️ Error in 1:1 pairs: {e}")
            
            try:
                pairs_1_to_n = (self.find_1_to_n_pairs(filtered_buy_positions, filtered_sell_positions) or [])[:max_pairs_per_type]
                all_profitable_pairs.extend(pairs_1_to_n)
                print(f"   💰 1:N pairs: {len(pairs_1_to_n)} (limited to {max_pairs_per_type})")
            except Exception as e:
                print(f"⚠️ Error in 1:N pairs: {e}")
            
            try:
                pairs_n_to_1 = (self.find_n_to_1_pairs(filtered_buy_positions, filtered_sell_positions) or [])[:max_pairs_per_type]
                all_profitable_pairs.extend(pairs_n_to_1)
                print(f"   💰 N:1 pairs: {len(pairs_n_to_1)} (limited to {max_pairs_per_type})")
            except Exception as e:
                print(f"⚠️ Error in N:1 pairs: {e}")
            
            if len(filtered_buy_positions) >= 2 and len(filtered_sell_positions) >= 2:
                try:
                    pairs_complex = (self.find_complex_pairs(filtered_buy_positions, filtered_sell_positions) or [])[:max_pairs_per_type]
                    all_profitable_pairs.extend(pairs_complex)
                    print(f"   💰 Complex pairs: {len(pairs_complex)} (limited to {max_pairs_per_type})")
                except Exception as e:
                    print(f"⚠️ Error in complex pairs: {e}")
            
            # ✅ เพิ่ม: จำกัดจำนวนคู่รวมก่อนส่งไป select
            max_total_pairs = 50  # จำกัดสูงสุด 50 คู่รวม
            if len(all_profitable_pairs) > max_total_pairs:
                all_profitable_pairs.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
                all_profitable_pairs = all_profitable_pairs[:max_total_pairs]
                print(f"🔧 Limited total pairs to {max_total_pairs} (best scores)")
            
            # เรียงลำดับและเลือกคู่ที่ไม่ซ้ำ
            if all_profitable_pairs:
                all_profitable_pairs.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
                final_pairs = self.select_non_overlapping_pairs(all_profitable_pairs) or []
            else:
                final_pairs = []
            
            print(f"💰 Multi-Position Results:")
            print(f"   • 1:1 pairs: {len(pairs_1_1)}")
            print(f"   • 1:N pairs: {len(pairs_1_to_n)}")  
            print(f"   • N:1 pairs: {len(pairs_n_to_1)}")
            print(f"   • Complex: {len(pairs_complex)}")
            print(f"   • Total generated: {len(all_profitable_pairs)}")
            print(f"   • 🏆 Final selected: {len(final_pairs)} pairs")
            
            # แสดง top 3 pairs
            for i, pair in enumerate(final_pairs[:3]):
                try:
                    pair_type = pair.get('pair_type', 'Unknown')
                    total_pos = pair.get('total_positions', 0)
                    net_profit = pair.get('net_profit', 0)
                    priority_score = pair.get('priority_score', 0)
                    print(f"   {i+1}. {pair_type}: {total_pos} pos = +${net_profit:.2f} (Score: {priority_score:.1f})")
                except Exception as e:
                    print(f"   {i+1}. Error displaying pair: {e}")
            
            return final_pairs
            
        except Exception as e:
            print(f"❌ Multi-position pairing error: {e}")
            import traceback
            print(f"🔧 Traceback: {traceback.format_exc()}")
            return []
        
    # 🧠 แก้ Smart Retention Logic ให้ยืดหยุ่นขึ้น
    def should_keep_for_hedge(self, profit_pos, losing_positions, all_positions):
        """ตัดสินใจว่าควรเก็บไม้กำไรไว้หรือไม่ - FLEXIBLE VERSION"""
        try:
            # เหตุผลที่ควรเก็บไว้
            reasons = []
            protection_score = 0  # คะแนนการป้องกัน (0-100)
            
            # 1. ไม้กำไรที่อยู่ใกล้ไม้เสีย (hedge natural)
            nearby_losing = [p for p in losing_positions 
                            if abs(p.entry_price - profit_pos.entry_price) < 300]  # 300 points
            
            if nearby_losing:
                total_nearby_loss = sum(abs(p.pnl) for p in nearby_losing)
                hedge_ratio = total_nearby_loss / profit_pos.pnl if profit_pos.pnl > 0 else 0
                
                if hedge_ratio > 3:  # ไม้เสียใกล้ๆ มากกว่า 3 เท่า
                    protection_score += 40
                    reasons.append(f"Critical hedge: {len(nearby_losing)} losing (${total_nearby_loss:.1f})")
                elif hedge_ratio > 1.5:  # ไม้เสียใกล้ๆ มากกว่า 1.5 เท่า
                    protection_score += 20
                    reasons.append(f"Moderate hedge: {len(nearby_losing)} losing (${total_nearby_loss:.1f})")
            
            # 2. Portfolio balance protection (ยืดหยุ่นขึ้น)
            buy_count = len([p for p in all_positions if p.direction == "BUY"])
            sell_count = len([p for p in all_positions if p.direction == "SELL"])
            imbalance = abs(buy_count - sell_count)
            
            if imbalance > 8:  # imbalance สูงมาก
                minority_side = "BUY" if buy_count < sell_count else "SELL"
                if profit_pos.direction == minority_side:
                    protection_score += 30
                    reasons.append(f"Critical balance ({buy_count}B:{sell_count}S)")
            elif imbalance > 4:  # imbalance ปานกลาง
                minority_side = "BUY" if buy_count < sell_count else "SELL"
                if profit_pos.direction == minority_side:
                    protection_score += 15
                    reasons.append(f"Balance help ({buy_count}B:{sell_count}S)")
            
            # 3. เก็บไม้กำไรใหญ่ไว้ hedge ไม้เสียใหญ่ (เฉพาะกรณีพิเศษ)
            big_losing = [p for p in losing_positions if p.pnl < -15]  # เสีย > $15
            if big_losing and profit_pos.pnl > 10:  # กำไร > $10
                protection_score += 25
                reasons.append(f"Big profit hedge: vs {len(big_losing)} big losses")
            
            # 4. Directional profit balance (ใหม่)
            buy_profitable = [p for p in all_positions if p.direction == "BUY" and p.pnl > 0]
            sell_profitable = [p for p in all_positions if p.direction == "SELL" and p.pnl > 0]
            
            if profit_pos.direction == "BUY" and len(buy_profitable) <= 3:  # BUY กำไรน้อย
                protection_score += 10
                reasons.append(f"Rare BUY profit ({len(buy_profitable)} total)")
            elif profit_pos.direction == "SELL" and len(sell_profitable) <= 3:  # SELL กำไรน้อย  
                protection_score += 10
                reasons.append(f"Rare SELL profit ({len(sell_profitable)} total)")
            
            # 🎯 DECISION LOGIC (ยืดหยุ่น)
            total_pnl = sum(p.pnl for p in all_positions)
            total_positions = len(all_positions)
            
            # ถ้า portfolio ดีมาก ลด protection
            if total_pnl > 100 and total_positions > 80:
                protection_score *= 0.6  # ลดการป้องกัน 40%
                reasons.append("Portfolio healthy - reduced protection")
            
            # ถ้า profit เล็ก ลด protection  
            if profit_pos.pnl < 2:
                protection_score *= 0.7  # ลดการป้องกัน 30%
                reasons.append("Small profit - reduced protection")
            
            # Threshold ยืดหยุ่น
            should_keep = protection_score >= 30  # จาก 0 เป็น 30 points
            primary_reason = reasons[0] if reasons else "No protection needed"
            
            # 📊 Debug info
            if protection_score > 0:
                print(f"   🔍 {profit_pos.direction} ${profit_pos.pnl:.2f}: Score {protection_score:.1f} - {primary_reason}")
            
            return {
                'keep': should_keep,
                'reason': primary_reason,
                'protection_score': protection_score,
                'all_reasons': reasons
            }
            
        except Exception as e:
            print(f"❌ Flexible retention logic error: {e}")
            return {'keep': False, 'reason': 'Error in logic', 'protection_score': 0, 'all_reasons': []}

    def find_1_to_1_pairs(self, buy_positions, sell_positions):
        """หาคู่ 1:1 แบบเดิม (เร็วที่สุด)"""
        pairs_1_1 = []
        
        for buy_pos in buy_positions:
            for sell_pos in sell_positions:
                net_pnl = buy_pos.pnl + sell_pos.pnl
                
                if net_pnl > 0.3:  # threshold ต่ำมากสำหรับ 1:1
                    priority_score = net_pnl + abs(min(buy_pos.pnl, sell_pos.pnl))
                    
                    pairs_1_1.append({
                        'losing_positions': [buy_pos if buy_pos.pnl < sell_pos.pnl else sell_pos],
                        'profitable_positions': [sell_pos if buy_pos.pnl < sell_pos.pnl else buy_pos],
                        'net_profit': net_pnl,
                        'total_positions': 2,
                        'pair_type': "1:1",
                        'priority_score': priority_score,
                        'position_ids': {buy_pos.position_id, sell_pos.position_id}
                    })
        
        return pairs_1_1

    def find_1_to_n_pairs(self, buy_positions, sell_positions):
        """หาคู่ 1 เสีย + 2-3 ได้กำไร"""
        pairs_1_to_n = []
        
        # รวม losing positions (ทั้ง BUY และ SELL ที่เสีย)
        losing_positions = [p for p in buy_positions + sell_positions if p.pnl < -0.5]  # เสียอย่างน้อย $0.5
        profitable_positions = [p for p in buy_positions + sell_positions if p.pnl > 0.2]  # กำไรอย่างน้อย $0.2
        
        # 1 เสีย + 2 ได้กำไร - ใช้ nested loops แทน itertools
        for losing_pos in losing_positions:
            # ลองจับคู่กับ 2 ไม้กำไร
            for i, profit1 in enumerate(profitable_positions):
                for profit2 in profitable_positions[i+1:]:  # หลีกเลี่ยงการซ้ำ
                    net_pnl = losing_pos.pnl + profit1.pnl + profit2.pnl
                    
                    if net_pnl > 0.5:  # threshold ต่ำขึ้นสำหรับ multi-pos
                        priority_score = net_pnl + abs(losing_pos.pnl) * 0.8  # bonus สำหรับการปิดไม้เสียใหญ่
                        
                        pairs_1_to_n.append({
                            'losing_positions': [losing_pos],
                            'profitable_positions': [profit1, profit2],
                            'net_profit': net_pnl,
                            'total_positions': 3,
                            'pair_type': "1:2",
                            'priority_score': priority_score,
                            'position_ids': {losing_pos.position_id, profit1.position_id, profit2.position_id}
                        })
            
            # 1 เสีย + 3 ได้กำไร (เฉพาะไม้เสียใหญ่ > $3)
            if losing_pos.pnl < -3 and len(profitable_positions) >= 3:
                for i, profit1 in enumerate(profitable_positions[:5]):  # จำกัด 5 ตัวแรก
                    for j, profit2 in enumerate(profitable_positions[i+1:5]):
                        for profit3 in profitable_positions[i+j+2:5]:
                            net_pnl = losing_pos.pnl + profit1.pnl + profit2.pnl + profit3.pnl
                            
                            if net_pnl > 0.8:
                                priority_score = net_pnl + abs(losing_pos.pnl) * 0.9
                                
                                pairs_1_to_n.append({
                                    'losing_positions': [losing_pos],
                                    'profitable_positions': [profit1, profit2, profit3],
                                    'net_profit': net_pnl,
                                    'total_positions': 4,
                                    'pair_type': "1:3",
                                    'priority_score': priority_score,
                                    'position_ids': {losing_pos.position_id, profit1.position_id, profit2.position_id, profit3.position_id}
                                })
        
        return pairs_1_to_n

    def find_n_to_1_pairs(self, buy_positions, sell_positions):
        """หา 2-3 เสีย + 1 ได้กำไรใหญ่"""
        pairs_n_to_1 = []
        
        losing_positions = [p for p in buy_positions + sell_positions if p.pnl < -0.3]
        profitable_positions = [p for p in buy_positions + sell_positions if p.pnl > 1.5]  # กำไรใหญ่ > $1.5
        
        # 2 เสีย + 1 กำไรใหญ่ - ใช้ nested loops
        for profit_pos in profitable_positions:
            for i, losing1 in enumerate(losing_positions):
                for losing2 in losing_positions[i+1:]:  # หลีกเลี่ยงการซ้ำ
                    net_pnl = profit_pos.pnl + losing1.pnl + losing2.pnl
                    
                    if net_pnl > 0.5:
                        priority_score = net_pnl + profit_pos.pnl * 0.7  # bonus สำหรับกำไรใหญ่
                        
                        pairs_n_to_1.append({
                            'losing_positions': [losing1, losing2],
                            'profitable_positions': [profit_pos],
                            'net_profit': net_pnl,
                            'total_positions': 3,
                            'pair_type': "2:1",
                            'priority_score': priority_score,
                            'position_ids': {profit_pos.position_id, losing1.position_id, losing2.position_id}
                        })
            
            # 3 เสีย + 1 กำไรใหญ่ (เฉพาะกำไร > $5)
            if profit_pos.pnl > 5 and len(losing_positions) >= 3:
                for i, losing1 in enumerate(losing_positions[:3]):  # จำกัด 3 ตัวแรก
                    for j, losing2 in enumerate(losing_positions[i+1:3]):
                        for losing3 in losing_positions[i+j+2:3]:
                            total_loss = losing1.pnl + losing2.pnl + losing3.pnl
                            if total_loss > -4:  # ไม่ให้เสียรวมเกิน $4
                                net_pnl = profit_pos.pnl + total_loss
                                
                                if net_pnl > 0.8:
                                    priority_score = net_pnl + profit_pos.pnl * 0.8
                                    
                                    pairs_n_to_1.append({
                                        'losing_positions': [losing1, losing2, losing3],
                                        'profitable_positions': [profit_pos],
                                        'net_profit': net_pnl,
                                        'total_positions': 4,
                                        'pair_type': "3:1",
                                        'priority_score': priority_score,
                                        'position_ids': {profit_pos.position_id, losing1.position_id, losing2.position_id, losing3.position_id}
                                    })
        
        return pairs_n_to_1

    def find_complex_pairs(self, buy_positions, sell_positions):
        """หาคู่แบบผสม 2:2, 2:3 (advanced)"""
        pairs_complex = []
        
        losing_positions = [p for p in buy_positions + sell_positions if p.pnl < -0.5]
        profitable_positions = [p for p in buy_positions + sell_positions if p.pnl > 1]
        
        # 2 เสีย + 2 กำไร - ใช้ nested loops
        if len(losing_positions) >= 2 and len(profitable_positions) >= 2:
            for i, losing1 in enumerate(losing_positions[:3]):  # จำกัด 3 ตัวแรก
                for losing2 in losing_positions[i+1:3]:
                    for j, profit1 in enumerate(profitable_positions[:3]):
                        for profit2 in profitable_positions[j+1:3]:
                            net_pnl = losing1.pnl + losing2.pnl + profit1.pnl + profit2.pnl
                            
                            if net_pnl > 0.8:  # threshold ต่ำลงสำหรับ complex
                                priority_score = net_pnl + abs(losing1.pnl + losing2.pnl) * 0.6
                                
                                pairs_complex.append({
                                    'losing_positions': [losing1, losing2],
                                    'profitable_positions': [profit1, profit2],
                                    'net_profit': net_pnl,
                                    'total_positions': 4,
                                    'pair_type': "2:2",
                                    'priority_score': priority_score,
                                    'position_ids': {losing1.position_id, losing2.position_id, profit1.position_id, profit2.position_id}
                                })
        
        return pairs_complex

    def select_non_overlapping_pairs(self, all_pairs):
        """เลือกคู่ที่ไม่ซ้ำกัน (greedy selection) - แก้ไข Infinite Loop เท่านั้น"""
        try:
            if not all_pairs or len(all_pairs) == 0:
                print("⚠️ No pairs to select from")
                return []
            
            print(f"🔍 Selecting from {len(all_pairs)} total pairs...")
            
            selected_pairs = []
            used_position_ids = set()
            
            # เรียงตาม priority_score สูงสุดก่อน
            sorted_pairs = sorted(all_pairs, key=lambda x: x.get('priority_score', 0), reverse=True)
            
            # ✅ เพิ่ม: ตัวแปรสำหรับ limit debug messages
            overlap_message_count = 0
            max_overlap_messages = 10  # แสดงแค่ 10 ข้อความแรก
            
            for i, pair in enumerate(sorted_pairs):
                try:
                    # Safe check for pair structure
                    if not isinstance(pair, dict):
                        continue
                    
                    # ดึง position_ids อย่างปลอดภัย
                    pair_position_ids = set()
                    
                    # เพิ่ม IDs จาก losing_positions
                    losing_positions = pair.get('losing_positions', [])
                    if losing_positions:
                        for pos in losing_positions:
                            if hasattr(pos, 'position_id'):
                                pair_position_ids.add(pos.position_id)
                    
                    # เพิ่ม IDs จาก profitable_positions  
                    profitable_positions = pair.get('profitable_positions', [])
                    if profitable_positions:
                        for pos in profitable_positions:
                            if hasattr(pos, 'position_id'):
                                pair_position_ids.add(pos.position_id)
                    
                    # ถ้าไม่มี position_ids ใน pair object ให้ลองดึงจาก key อื่น
                    if not pair_position_ids and 'position_ids' in pair:
                        position_ids_from_key = pair.get('position_ids', set())
                        if isinstance(position_ids_from_key, (set, list)):
                            pair_position_ids.update(position_ids_from_key)
                    
                    # เช็คว่ามี position_ids ให้ใช้งานไหม
                    if not pair_position_ids:
                        print(f"   ⚠️ Pair {i+1} has no position IDs - skipping")
                        continue
                    
                    # เช็คว่า position ใดๆ ในคู่นี้ถูกใช้แล้วไหม
                    if not pair_position_ids.intersection(used_position_ids):
                        selected_pairs.append(pair)
                        used_position_ids.update(pair_position_ids)
                        
                        pair_type = pair.get('pair_type', 'Unknown')
                        net_profit = pair.get('net_profit', 0)
                        priority_score = pair.get('priority_score', 0)
                        
                        print(f"   ✅ Selected: {pair_type} (+${net_profit:.2f}, Score: {priority_score:.1f})")
                        
                        # จำกัดจำนวนคู่สูงสุด (ไม่ให้ปิดครั้งละเยอะเกินไป)
                        if len(selected_pairs) >= 5:  # สูงสุด 5 คู่ต่อครั้ง
                            print(f"   🛑 Reached maximum pairs limit (5)")
                            break
                    else:
                        # ✅ แก้ไข: จำกัดการแสดง overlap messages
                        if overlap_message_count < max_overlap_messages:
                            overlapping_ids = pair_position_ids.intersection(used_position_ids)
                            print(f"   ❌ Pair {i+1} overlaps with used positions: {overlapping_ids}")
                            overlap_message_count += 1
                        elif overlap_message_count == max_overlap_messages:
                            print(f"   ... (suppressing further {len(sorted_pairs) - i - 1} overlap messages)")
                            overlap_message_count += 1
                    
                    # ✅ เพิ่ม: Emergency break ถ้าเจอ overlap เยอะเกินไป
                    if overlap_message_count > 1000:  # ถ้า overlap มากกว่า 1000 คู่
                        print(f"🚨 Too many overlaps detected - emergency break!")
                        break
                        
                except Exception as e:
                    print(f"   ⚠️ Error processing pair {i+1}: {e}")
                    continue
            
            print(f"🏆 Final selection: {len(selected_pairs)} pairs from {len(all_pairs)} candidates")
            
            # ✅ เพิ่ม: แสดงสถิติ overlap
            if overlap_message_count > 0:
                print(f"📊 Overlap statistics: {overlap_message_count} overlapping pairs detected")
            
            return selected_pairs
            
        except Exception as e:
            print(f"❌ Select non-overlapping pairs error: {e}")
            import traceback
            print(f"🔧 Traceback: {traceback.format_exc()}")
            return []
            
    def close_single_profitable_position(self, position):
        """ปิด position เดี่ยวที่กำไรดี"""
        try:
            success = self.close_entire_position(position)
            if success:
                print(f"   ✅ Closed single position: ${position.pnl:.2f} profit")
                
                # วาง order ใหม่ทดแทนทันที
                current_price = self.grid_system.get_current_price()
                if position.direction == "BUY":
                    new_price = current_price - (150 * 0.01)  # วาง BUY ใหม่
                    self.grid_system.place_smart_rebalance_order("BUY", new_price, position.lot_size)
                else:
                    new_price = current_price + (150 * 0.01)  # วาง SELL ใหม่
                    self.grid_system.place_smart_rebalance_order("SELL", new_price, position.lot_size)
                    
        except Exception as e:
            print(f"❌ Close single position error: {e}")

    def analyze_pair_opportunities(self, positions):
        """วิเคราะห์โอกาส pair closing แบบละเอียด"""
        try:
            losing_positions = [p for p in positions if p.pnl < 0]
            profit_positions = [p for p in positions if p.pnl > 0]
            
            print(f"\n📊 === PAIR ANALYSIS ===")
            print(f"🔴 Losing positions: {len(losing_positions)}")
            for pos in losing_positions[:5]:  # แสดง 5 ตัวแรก
                print(f"   • {pos.direction} ${pos.pnl:.2f} @ ${pos.entry_price:.2f}")
                
            print(f"🟢 Profitable positions: {len(profit_positions)}")
            for pos in profit_positions[:5]:  # แสดง 5 ตัวแรก
                print(f"   • {pos.direction} +${pos.pnl:.2f} @ ${pos.entry_price:.2f}")
            
            # หาคู่ที่ดีที่สุด
            best_pairs = []
            for losing_pos in losing_positions[:3]:  # เช็ค 3 ตัวที่ขาดทุนมากสุด
                for profit_pos in profit_positions:
                    net_pnl = losing_pos.pnl + profit_pos.pnl
                    if net_pnl > 0:
                        best_pairs.append({
                            'net_profit': net_pnl,
                            'losing': f"{losing_pos.direction}(${losing_pos.pnl:.2f})",
                            'profit': f"{profit_pos.direction}(+${profit_pos.pnl:.2f})"
                        })
            
            best_pairs.sort(key=lambda x: x['net_profit'], reverse=True)
            
            print(f"🎯 Best potential pairs:")
            for i, pair in enumerate(best_pairs[:3]):
                print(f"   {i+1}. {pair['losing']} + {pair['profit']} = +${pair['net_profit']:.2f}")
                
            print(f"{'='*40}\n")
            
        except Exception as e:
            print(f"❌ Pair analysis error: {e}")


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
                
                # ใช้ method ที่มีอยู่แล้ว
                success = self.grid_system.place_hedge_order(direction, lot_size)
                if success:
                    print(f"   ✅ {direction} hedge placed successfully")
                else:
                    print(f"   ❌ Failed to place {direction} hedge")
                    
            except Exception as e:
                print(f"❌ Execute hedge error: {e}")

    def place_replacement_orders_after_pair_close(self, closed_pos1, closed_pos2):
        """วางไม้ใหม่หลังปิดคู่"""
        
        try:
            current_price = self.grid_system.get_current_price()
            
            # วางไม้ BUY และ SELL ใหม่ใกล้ current price
            buy_price = current_price - (200 * 0.01)   # 200 points ลง
            sell_price = current_price + (200 * 0.01)  # 200 points ขึ้น
            
            avg_lot = (closed_pos1.lot_size + closed_pos2.lot_size) / 2
            
            # วางไม้ทดแทน
            self.place_single_replacement_order("BUY", buy_price, avg_lot)
            self.place_single_replacement_order("SELL", sell_price, avg_lot)
            
            print(f"   🔄 Replacement orders placed: BUY @ ${buy_price:.2f}, SELL @ ${sell_price:.2f}")
            
        except Exception as e:
            print(f"❌ Replacement orders error: {e}")

    def place_single_replacement_order(self, direction, price, lot_size):
        """วางไม้เดียวทดแทน"""
        
        try:
            from ai_gold_grid import GridLevel, PositionStatus
            
            new_level = GridLevel(
                level_id=f"AI_REPLACE_{direction}_{int(time.time())}",
                price=round(price, 2),
                lot_size=round(lot_size, 3),
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
            print(f"❌ Place replacement error: {e}")
        return False
    
    def handle_buy_heavy_situation(self, buy_positions, sell_positions):
        """จัดการเมื่อ BUY positions เยอะเกิน"""
        try:
            # 1. หาคู่ที่ปิดแล้วได้กำไรสุทธิ
            best_pairs = self.find_best_closing_pairs(buy_positions, sell_positions)
            
            if best_pairs:
                print(f"💰 Closing {len(best_pairs)} profitable pairs")
                for pair in best_pairs:
                    self.close_position_pair(pair['buy_pos'], pair['sell_pos'], pair['net_profit'])
                    
            # 2. เพิ่ม SELL orders ใกล้ราคาปัจจุบัน
            current_price = self.grid_system.get_current_price()
            self.add_sell_orders_for_balance(current_price, min(2, len(buy_positions) - len(sell_positions)))
            
        except Exception as e:
            print(f"❌ BUY heavy handling error: {e}")

    def handle_sell_heavy_situation(self, buy_positions, sell_positions):
        """จัดการเมื่อ SELL positions เยอะเกิน"""  
        try:
            # 1. หาคู่ที่ปิดแล้วได้กำไรสุทธิ
            best_pairs = self.find_best_closing_pairs(sell_positions, buy_positions)
            
            if best_pairs:
                print(f"💰 Closing {len(best_pairs)} profitable pairs")
                for pair in best_pairs:
                    self.close_position_pair(pair['sell_pos'], pair['buy_pos'], pair['net_profit'])
                    
            # 2. เพิ่ม BUY orders ใกล้ราคาปัจจุบัน  
            current_price = self.grid_system.get_current_price()
            self.add_buy_orders_for_balance(current_price, min(2, len(sell_positions) - len(buy_positions)))
            
        except Exception as e:
            print(f"❌ SELL heavy handling error: {e}")

    def find_best_closing_pairs(self, heavy_positions, light_positions):
        """หาคู่ positions ที่ปิดแล้วได้กำไรสุทธิ"""
        try:
            profitable_pairs = []
            
            for heavy_pos in heavy_positions:
                for light_pos in light_positions:
                    net_pnl = heavy_pos.pnl + light_pos.pnl
                    
                    # ต้องได้กำไรสุทธิ > $3 ถึงจะปิด
                    if net_pnl > 3:
                        profitable_pairs.append({
                            'heavy_pos': heavy_pos,
                            'light_pos': light_pos,  
                            'buy_pos': heavy_pos if heavy_pos.direction == "BUY" else light_pos,
                            'sell_pos': heavy_pos if heavy_pos.direction == "SELL" else light_pos,
                            'net_profit': net_pnl,
                            'priority': net_pnl + abs(min(heavy_pos.pnl, light_pos.pnl))
                        })
            
            # เรียงตาม priority และเลือกที่ไม่ซ้ำ
            profitable_pairs.sort(key=lambda x: x['priority'], reverse=True)
            
            selected_pairs = []
            used_positions = set()
            
            for pair in profitable_pairs:
                heavy_id = pair['heavy_pos'].position_id  
                light_id = pair['light_pos'].position_id
                
                if heavy_id not in used_positions and light_id not in used_positions:
                    selected_pairs.append(pair)
                    used_positions.add(heavy_id)
                    used_positions.add(light_id)
                    
                    if len(selected_pairs) >= 1:  # จำกัดแค่ 1 คู่ต่อครั้ง
                        break
                        
            return selected_pairs
            
        except Exception as e:
            print(f"❌ Find pairs error: {e}")
            return []

    def close_position_pair(self, pos1, pos2, expected_profit):
        """ปิด positions คู่พร้อมกัน"""
        try:
            print(f"🎯 Closing pair: {pos1.direction} ${pos1.pnl:.2f} + {pos2.direction} ${pos2.pnl:.2f} = +${expected_profit:.2f}")
            
            # ปิด position แรก
            success1 = self.close_single_position(pos1)
            if success1:
                time.sleep(0.3)  # รอสักครู่
                
                # ปิด position ที่สอง
                success2 = self.close_single_position(pos2)
                if success2:
                    print(f"   ✅ Pair closed successfully: +${expected_profit:.2f}")
                    return True
                else:
                    print(f"   ⚠️ Second position failed to close")
            else:
                print(f"   ❌ First position failed to close")
                
            return False
            
        except Exception as e:
            print(f"❌ Close pair error: {e}")
            return False

    def close_single_position(self, position):
        """ปิด position เดียว - ใช้ MT5 API โดยตรง (แก้ไขแล้ว)"""
        try:
            import MetaTrader5 as mt5
            
            # ✅ เพิ่ม: Detailed logging
            print(f"🎯 Attempting to close position: {position.position_id}")
            print(f"   Direction: {position.direction}, PnL: ${position.pnl:.2f}")
            print(f"   Lot Size: {position.lot_size}, Entry: ${position.entry_price:.2f}")
            
            # ✅ เพิ่ม: ตรวจสอบว่า position ยังเปิดอยู่ไหม
            existing_position = mt5.positions_get(ticket=position.position_id)
            if not existing_position:
                print(f"   ⚠️ Position {position.position_id} not found - already closed?")
                return True  # ถือว่าสำเร็จ เพราะไม้ปิดแล้ว
                
            # Get current symbol info and tick
            symbol_info = mt5.symbol_info(self.grid_system.gold_symbol)
            if not symbol_info:
                print(f"   ❌ Cannot get symbol info for {self.grid_system.gold_symbol}")
                return False
                
            tick = mt5.symbol_info_tick(self.grid_system.gold_symbol)
            if not tick:
                print(f"   ❌ Cannot get tick data for {self.grid_system.gold_symbol}")
                return False
            
            # ✅ แก้ไข: ใช้ MT5 API โดยตรง
            if position.direction == "BUY":
                trade_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
                print(f"   📉 Closing BUY with SELL at ${price:.2f}")
            else:
                trade_type = mt5.ORDER_TYPE_BUY  
                price = tick.ask
                print(f"   📈 Closing SELL with BUY at ${price:.2f}")
            
            # ✅ เพิ่ม: ตรวจสอบ lot size
            min_volume = symbol_info.volume_min
            volume_step = symbol_info.volume_step
            
            # Validate และปรับ lot size
            lot_size = position.lot_size
            if lot_size < min_volume:
                lot_size = min_volume
                print(f"   🔧 Adjusted lot size: {position.lot_size} → {lot_size}")
            
            # Round to volume step
            lot_size = round(lot_size / volume_step) * volume_step
            
            # ✅ สร้าง close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.grid_system.gold_symbol,
                "volume": lot_size,
                "type": trade_type,
                "position": position.position_id,  # ใช้ position ticket
                "price": price,
                "deviation": 50,  # เพิ่ม deviation
                "magic": self.grid_system.magic_number,
                "comment": "SmartClose_Direct",
                "type_filling": mt5.ORDER_FILLING_IOC  # ใช้ IOC แทน
            }
            
            print(f"   📤 Sending close request: {lot_size} lots @ ${price:.2f}")
            
            # ✅ ส่งคำสั่งปิด
            result = mt5.order_send(request)
            
            if result:
                print(f"   📨 MT5 Response: Code={result.retcode}, Comment='{result.comment}'")
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   ✅ Successfully closed position {position.position_id}")
                    
                    # ✅ เพิ่ม: อัพเดต position tracking
                    if hasattr(self, 'mark_recently_closed'):
                        self.mark_recently_closed(position.position_id)
                    
                    return True
                
                elif result.retcode == mt5.TRADE_RETCODE_REQUOTE:
                    print(f"   🔄 Requote received, retrying with market execution...")
                    return self.retry_close_at_market(position)
                    
                elif result.retcode == mt5.TRADE_RETCODE_INVALID_FILL:
                    print(f"   🔄 Invalid fill mode, trying different modes...")
                    return self.retry_close_different_fill_mode(position)
                    
                else:
                    print(f"   ❌ Close failed: {result.retcode} - {result.comment}")
                    return False
            else:
                print(f"   ❌ No response from MT5")
                return False
                
        except Exception as e:
            print(f"❌ Close single position error: {e}")
            import traceback
            print(f"🔧 Traceback: {traceback.format_exc()}")
            return False

    def retry_close_at_market(self, position):
        """ลองปิดด้วย market execution"""
        try:
            import MetaTrader5 as mt5
            
            tick = mt5.symbol_info_tick(self.grid_system.gold_symbol)
            if not tick:
                return False
                
            if position.direction == "BUY":
                trade_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                trade_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.grid_system.gold_symbol,
                "volume": position.lot_size,
                "type": trade_type,
                "position": position.position_id,
                "price": price,
                "deviation": 100,  # เพิ่ม deviation มาก
                "magic": self.grid_system.magic_number,
                "comment": "SmartClose_Market",
                "type_filling": mt5.ORDER_FILLING_IOC
            }
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"   ✅ Market close successful")
                return True
            else:
                print(f"   ❌ Market close failed: {result.retcode if result else 'No response'}")
                return False
                
        except Exception as e:
            print(f"❌ Market close retry error: {e}")
            return False

    def retry_close_different_fill_mode(self, position):
        """ลองปิดด้วย fill mode ต่างๆ"""
        try:
            import MetaTrader5 as mt5
            
            fill_modes = [
                (mt5.ORDER_FILLING_RETURN, "RETURN"),
                (mt5.ORDER_FILLING_IOC, "IOC"),
                (mt5.ORDER_FILLING_FOK, "FOK")
            ]
            
            tick = mt5.symbol_info_tick(self.grid_system.gold_symbol)
            if not tick:
                return False
                
            if position.direction == "BUY":
                trade_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                trade_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            
            for fill_mode, mode_name in fill_modes:
                print(f"   🔄 Trying {mode_name} fill mode...")
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.grid_system.gold_symbol,
                    "volume": position.lot_size,
                    "type": trade_type,
                    "position": position.position_id,
                    "price": price,
                    "deviation": 50,
                    "magic": self.grid_system.magic_number,
                    "comment": f"SmartClose_{mode_name}",
                    "type_filling": fill_mode
                }
                
                result = mt5.order_send(request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   ✅ {mode_name} fill mode successful")
                    return True
                elif result:
                    print(f"   ❌ {mode_name} failed: {result.retcode}")
            
            print(f"   ❌ All fill modes failed")
            return False
            
        except Exception as e:
            print(f"❌ Fill mode retry error: {e}")
            return False
    
    def add_sell_orders_for_balance(self, current_price, count):
        """แก้ไข method เดิม - ใช้ spacing เล็กลงมาก"""
        try:
            # ✅ แก้ไขจาก 150 เป็น 100 จุด (เร็วขึ้น 33%)
            tight_spacing = 100  # จาก 150 → 100 points
            
            for i in range(min(count, 4)):  # เพิ่มจาก 3 → 4 ตัว
                price = current_price + (tight_spacing * (i + 1) * 0.01)
                
                # เช็คระยะห่าง max 500 points
                distance = (price - current_price) / 0.01
                if distance > 500:
                    print(f"   ⚠️ SELL too far: {distance:.0f} points")
                    continue
                    
                if not self.grid_system.has_nearby_order(price, "SELL"):
                    lot_size = self.grid_system.base_lot
                    success = self.grid_system.place_smart_rebalance_order("SELL", price, lot_size)
                    if success:
                        print(f"   🚀 Fast SELL: {lot_size:.3f} @ ${price:.2f} (+{distance:.0f}pts)")
                        
        except Exception as e:
            print(f"❌ Fast SELL orders error: {e}")

    def add_buy_orders_for_balance(self, current_price, count):
        """แก้ไข method เดิม - ใช้ spacing เล็กลงมาก"""
        try:
            # ✅ แก้ไขจาก 150 เป็น 100 จุด (เร็วขึ้น 33%)
            tight_spacing = 100  # จาก 150 → 100 points
            
            for i in range(min(count, 4)):  # เพิ่มจาก 3 → 4 ตัว
                price = current_price - (tight_spacing * (i + 1) * 0.01)
                
                # เช็คระยะห่าง max 500 points
                distance = (current_price - price) / 0.01
                if distance > 500:
                    print(f"   ⚠️ BUY too far: {distance:.0f} points")
                    continue
                    
                if not self.grid_system.has_nearby_order(price, "BUY"):
                    lot_size = self.grid_system.base_lot
                    success = self.grid_system.place_smart_rebalance_order("BUY", price, lot_size)
                    if success:
                        print(f"   🚀 Fast BUY: {lot_size:.3f} @ ${price:.2f} (-{distance:.0f}pts)")
                        
        except Exception as e:
            print(f"❌ Fast BUY orders error: {e}")

    def rebalance_portfolio_if_needed(self, positions):
        """แก้ไขจากเดิม - เพิ่ม Strategic Portfolio Balance"""
        try:
            current_price = self.grid_system.get_current_price()
            buy_count = len([p for p in positions if p.direction == "BUY"])
            sell_count = len([p for p in positions if p.direction == "SELL"])
            total_positions = len(positions)
            
            print(f"📊 Portfolio: {buy_count}B, {sell_count}S, Total: {total_positions} @ ${current_price:.2f}")
            
            # ✅ logic เดิม: imbalance > 1
            if abs(buy_count - sell_count) > 1:
                imbalance = buy_count - sell_count
                
                # 🔄 เพิ่ม: Strategic Directional Analysis
                buy_positions = [p for p in positions if p.direction == "BUY"]
                sell_positions = [p for p in positions if p.direction == "SELL"]
                
                buy_avg_pnl = sum(p.pnl for p in buy_positions) / len(buy_positions) if buy_positions else 0
                sell_avg_pnl = sum(p.pnl for p in sell_positions) / len(sell_positions) if sell_positions else 0
                
                print(f"📈 Directional PnL: BUY avg ${buy_avg_pnl:.2f}, SELL avg ${sell_avg_pnl:.2f}")
                
                if imbalance > 0:  # BUY เยอะ
                    # 🔄 เพิ่ม: เช็คว่า BUY กำลังขาดทุนหนักไหม
                    buy_heavy_loss = sum(p.pnl for p in buy_positions if p.pnl < 0)
                    if buy_heavy_loss < -15:  # BUY เสียหนัก > $15
                        print(f"⚖️ BUY heavy BUT losing ${abs(buy_heavy_loss):.1f} - Adding SELL hedge")
                        self.add_sell_orders_for_balance(current_price, abs(imbalance))
                    else:
                        print(f"⚖️ BUY heavy (+{imbalance}) - Adding moderate SELL orders")
                        self.add_sell_orders_for_balance(current_price, min(abs(imbalance), 2))  # จำกัดแค่ 2 ตัว
                        
                else:  # SELL เยอะ
                    # 🔄 เพิ่ม: เช็คว่า SELL กำลังขาดทุนหนักไหม
                    sell_heavy_loss = sum(p.pnl for p in sell_positions if p.pnl < 0)
                    if sell_heavy_loss < -15:  # SELL เสียหนัก > $15
                        print(f"⚖️ SELL heavy BUT losing ${abs(sell_heavy_loss):.1f} - Adding BUY hedge")
                        self.add_buy_orders_for_balance(current_price, abs(imbalance))
                    else:
                        print(f"⚖️ SELL heavy ({imbalance}) - Adding moderate BUY orders")
                        self.add_buy_orders_for_balance(current_price, min(abs(imbalance), 2))  # จำกัดแค่ 2 ตัว
            
            # ✅ logic เดิม: positions < 8
            if total_positions < 8:
                orders_needed = 8 - total_positions
                print(f"🎯 Too few positions ({total_positions}) - Adding {orders_needed} more")
                
                # 🔄 เพิ่ม: Smart Priority Placement
                # วิเคราะห์ว่าควรเน้นทิศทางไหน
                if buy_count < sell_count - 1:  # ต้องการ BUY มากกว่า
                    # วาง BUY มากกว่า SELL
                    buy_needed = (orders_needed + 1) // 2 + 1
                    sell_needed = orders_needed - buy_needed
                    print(f"🎯 Priority: {buy_needed} BUY, {sell_needed} SELL")
                elif sell_count < buy_count - 1:  # ต้องการ SELL มากกว่า
                    # วาง SELL มากกว่า BUY
                    sell_needed = (orders_needed + 1) // 2 + 1
                    buy_needed = orders_needed - sell_needed
                    print(f"🎯 Priority: {buy_needed} BUY, {sell_needed} SELL")
                else:
                    # วางเท่ากัน
                    buy_needed = sell_needed = orders_needed // 2
                    print(f"🎯 Balanced: {buy_needed} BUY, {sell_needed} SELL")
                
                # วาง orders ตาม priority
                for i in range(buy_needed):
                    buy_price = current_price - (100 * (i + 1) * 0.01)
                    if not self.grid_system.has_nearby_order(buy_price, "BUY"):
                        self.grid_system.place_smart_rebalance_order("BUY", buy_price, self.grid_system.base_lot)
                        
                for i in range(sell_needed):
                    sell_price = current_price + (100 * (i + 1) * 0.01)
                    if not self.grid_system.has_nearby_order(sell_price, "SELL"):
                        self.grid_system.place_smart_rebalance_order("SELL", sell_price, self.grid_system.base_lot)
            
            # ✅ logic เดิม: gap filling
            self.check_and_fill_gaps_fast(current_price)
                
        except Exception as e:
            print(f"❌ Strategic portfolio rebalance error: {e}")

    def auto_reposition_after_close(self, closed_position):
        """แก้ไขจากเดิม - เพิ่ม Instant Refill Logic - ปรับปรุงแล้ว"""
        try:
            if not self.auto_reposition_enabled:
                return
                
            current_price = self.grid_system.get_current_price()
            direction = closed_position.direction
            
            # ✅ เพิ่ม: Instant gap check และ refill ทันที
            self.instant_gap_refill(current_price, direction)
            
            # 🔄 เพิ่ม: Portfolio Context Analysis
            current_positions = self.analyze_portfolio_positions().get('grid_positions', [])
            buy_count = len([p for p in current_positions if p.direction == "BUY"])
            sell_count = len([p for p in current_positions if p.direction == "SELL"])
            
            # ✅ ปรับ: ลด gap distance
            base_gap = 60  # ลดจาก 120 เป็น 60 จุด
            
            # 🔄 เพิ่ม: Strategic Gap Analysis
            same_direction_positions = [p for p in current_positions if p.direction == direction]
            
            if len(same_direction_positions) <= 1:
                # เหลือไม้ทิศทางเดียวกันน้อยมาก = URGENT
                urgent_gap = 40  # ใช้ gap เล็กสำหรับ urgent case
                print(f"🚨 URGENT: Only {len(same_direction_positions)} {direction} positions left!")
                
                # วางไม้ใหม่ใกล้ๆ ทันที
                if direction == "BUY":
                    new_price = current_price - (urgent_gap * 0.01)
                else:
                    new_price = current_price + (urgent_gap * 0.01)
                    
                # ✅ แก้ไข: ใช้ parameter order ที่ถูกต้อง
                if not self.grid_system.has_nearby_order(direction, new_price, 30):
                    success = self.grid_system.place_smart_rebalance_order(direction, new_price, self.grid_system.base_lot)
                    if success:
                        print(f"⚡ URGENT refill: {direction} @ ${new_price:.2f}")
            
            # เดิม: logic ปกติ
            elif direction == "BUY":
                new_buy_price = current_price - (base_gap * 0.01)
                
                # ✅ แก้ไข: ใช้ parameter order ที่ถูกต้อง
                if not self.grid_system.has_nearby_order("BUY", new_buy_price, 50):
                    success = self.grid_system.place_smart_rebalance_order("BUY", new_buy_price, self.grid_system.base_lot)
                    if success:
                        print(f"🔄 BUY reposition: @ ${new_buy_price:.2f} (B:{buy_count} vs S:{sell_count})")
            
            else:  # SELL
                new_sell_price = current_price + (base_gap * 0.01)
                
                # ✅ แก้ไข: ใช้ parameter order ที่ถูกต้อง
                if not self.grid_system.has_nearby_order("SELL", new_sell_price, 50):
                    success = self.grid_system.place_smart_rebalance_order("SELL", new_sell_price, self.grid_system.base_lot)
                    if success:
                        print(f"🔄 SELL reposition: @ ${new_sell_price:.2f} (B:{buy_count} vs S:{sell_count})")
                        
        except Exception as e:
            print(f"❌ Enhanced reposition error: {e}")


    def instant_gap_refill(self, current_price, just_closed_direction):
        """ทันทีที่ไม้ถูกเก็บ ให้เติมช่องว่างทันที - Method ใหม่"""
        try:
            # เช็คระยะห่างไม้ใกล้ที่สุด
            orders = list(self.grid_system.pending_orders.values())
            
            if just_closed_direction == "BUY":
                # เพิ่งปิด BUY = เช็ค BUY orders ที่เหลือ
                buy_orders = [o for o in orders if o.direction == "BUY" and o.price < current_price]
                
                if buy_orders:
                    nearest_buy = max(buy_orders, key=lambda x: x.price)
                    gap = (current_price - nearest_buy.price) / 0.01
                    
                    if gap > 100:  # มีช่องว่างเกิน 100 จุด
                        fill_price = current_price - (70 * 0.01)  # วางที่ 70 จุด
                        # ✅ แก้ไข: ใช้ parameter order ที่ถูกต้อง
                        if not self.grid_system.has_nearby_order("BUY", fill_price, 50):
                            self.grid_system.place_smart_rebalance_order("BUY", fill_price, self.grid_system.base_lot)
                            print(f"⚡ Instant BUY refill: @ ${fill_price:.2f} (gap was {gap:.0f}pts)")
                else:
                    # ไม่มี BUY orders เลย!
                    emergency_price = current_price - (50 * 0.01)
                    self.grid_system.place_smart_rebalance_order("BUY", emergency_price, self.grid_system.base_lot)
                    print(f"🚨 Emergency BUY: @ ${emergency_price:.2f}")
            
            else:  # SELL
                sell_orders = [o for o in orders if o.direction == "SELL" and o.price > current_price]
                
                if sell_orders:
                    nearest_sell = min(sell_orders, key=lambda x: x.price)
                    gap = (nearest_sell.price - current_price) / 0.01
                    
                    if gap > 100:  # มีช่องว่างเกิน 100 จุด
                        fill_price = current_price + (70 * 0.01)  # วางที่ 70 จุด
                        # ✅ แก้ไข: ใช้ parameter order ที่ถูกต้อง
                        if not self.grid_system.has_nearby_order("SELL", fill_price, 50):
                            self.grid_system.place_smart_rebalance_order("SELL", fill_price, self.grid_system.base_lot)
                            print(f"⚡ Instant SELL refill: @ ${fill_price:.2f} (gap was {gap:.0f}pts)")
                else:
                    # ไม่มี SELL orders เลย!
                    emergency_price = current_price + (50 * 0.01)
                    self.grid_system.place_smart_rebalance_order("SELL", emergency_price, self.grid_system.base_lot)
                    print(f"🚨 Emergency SELL: @ ${emergency_price:.2f}")
                    
        except Exception as e:
            print(f"❌ Instant gap refill error: {e}")
                
    def check_and_fill_gaps_fast(self, current_price):
        """เช็คและเติมช่องว่างราคาแบบเร็ว - ปรับปรุงแล้ว"""
        try:
            all_orders = list(self.grid_system.pending_orders.values())
            if not all_orders:
                return
                
            buy_orders = [o for o in all_orders if o.direction == "BUY"]
            sell_orders = [o for o in all_orders if o.direction == "SELL"]
            
            # ✅ เช็คช่องว่าง BUY ด้าน (ลดจาก 200 → 120 points)
            if buy_orders:
                nearest_buy = max(buy_orders, key=lambda x: x.price)
                buy_gap = (current_price - nearest_buy.price) / 0.01  # points
                
                if buy_gap > 120:  # ลดจาก 200 → 120 จุด (ไวขึ้น 40%)
                    fill_price = current_price - (80 * 0.01)  # วางที่ 80 จุด (จาก 100)
                    # ✅ แก้ไข: เปลี่ยน parameter order (direction ก่อน, price หลัง)
                    if not self.grid_system.has_nearby_order("BUY", fill_price, 50):
                        self.grid_system.place_smart_rebalance_order("BUY", fill_price, self.grid_system.base_lot)
                        print(f"⚡ Fill BUY gap: @ ${fill_price:.2f} (was {buy_gap:.0f}pts)")
            else:
                # ไม่มี BUY orders เลย - วางทันที!
                fill_price = current_price - (60 * 0.01)  # วางที่ 60 จุด
                # ✅ แก้ไข: เปลี่ยน parameter order (direction ก่อน, price หลัง)
                if not self.grid_system.has_nearby_order("BUY", fill_price, 50):
                    self.grid_system.place_smart_rebalance_order("BUY", fill_price, self.grid_system.base_lot)
                    print(f"🚨 Emergency BUY placement: @ ${fill_price:.2f}")
            
            # ✅ เช็คช่องว่าง SELL ด้าน (ลดจาก 200 → 120 points)
            if sell_orders:
                nearest_sell = min(sell_orders, key=lambda x: x.price)
                sell_gap = (nearest_sell.price - current_price) / 0.01  # points
                
                if sell_gap > 120:  # ลดจาก 200 → 120 จุด (ไวขึ้น 40%)
                    fill_price = current_price + (80 * 0.01)  # วางที่ 80 จุด (จาก 100)
                    # ✅ แก้ไข: เปลี่ยน parameter order (direction ก่อน, price หลัง)
                    if not self.grid_system.has_nearby_order("SELL", fill_price, 50):
                        self.grid_system.place_smart_rebalance_order("SELL", fill_price, self.grid_system.base_lot)
                        print(f"⚡ Fill SELL gap: @ ${fill_price:.2f} (was {sell_gap:.0f}pts)")
            else:
                # ไม่มี SELL orders เลย - วางทันที!
                fill_price = current_price + (60 * 0.01)  # วางที่ 60 จุด
                # ✅ แก้ไข: เปลี่ยน parameter order (direction ก่อน, price หลัง)
                if not self.grid_system.has_nearby_order("SELL", fill_price, 50):
                    self.grid_system.place_smart_rebalance_order("SELL", fill_price, self.grid_system.base_lot)
                    print(f"🚨 Emergency SELL placement: @ ${fill_price:.2f}")
                    
        except Exception as e:
            print(f"❌ Fast gap filling error: {e}")

    def check_and_fill_gaps(self, current_price):
        """เช็คและเติมช่องว่างราคา - ปรับปรุงแล้ว"""
        try:
            all_orders = list(self.grid_system.pending_orders.values())
            if not all_orders:
                return
                
            buy_orders = [o for o in all_orders if o.direction == "BUY"]
            sell_orders = [o for o in all_orders if o.direction == "SELL"]
            
            # ✅ เช็คช่องว่าง BUY ด้าน (ลดจาก 300 → 150 points)
            if buy_orders:
                nearest_buy = max(buy_orders, key=lambda x: x.price)
                buy_gap = (current_price - nearest_buy.price) / 0.01  # points
                
                if buy_gap > 150:  # ลดจาก 300 → 150 จุด (ไวขึ้น 50%)
                    fill_price = current_price - (100 * 0.01)  # วางที่ 100 จุด (จาก 150)
                    # ✅ แก้ไข: ใช้ parameter order ที่ถูกต้อง (direction ก่อน, price หลัง)
                    if not self.grid_system.has_nearby_order("BUY", fill_price, 50):
                        self.grid_system.place_smart_rebalance_order("BUY", fill_price, self.grid_system.base_lot)
                        print(f"🔧 Fill BUY gap: @ ${fill_price:.2f} (was {buy_gap:.0f} points)")
            else:
                # ไม่มี BUY orders เลย - วางทันที!
                fill_price = current_price - (80 * 0.01)  # วางที่ 80 จุด
                if not self.grid_system.has_nearby_order("BUY", fill_price, 50):
                    self.grid_system.place_smart_rebalance_order("BUY", fill_price, self.grid_system.base_lot)
                    print(f"🚨 Emergency BUY: @ ${fill_price:.2f}")
            
            # ✅ เช็คช่องว่าง SELL ด้าน (ลดจาก 300 → 150 points)
            if sell_orders:
                nearest_sell = min(sell_orders, key=lambda x: x.price)
                sell_gap = (nearest_sell.price - current_price) / 0.01  # points
                
                if sell_gap > 150:  # ลดจาก 300 → 150 จุด (ไวขึ้น 50%)
                    fill_price = current_price + (100 * 0.01)  # วางที่ 100 จุด (จาก 150)
                    # ✅ แก้ไข: ใช้ parameter order ที่ถูกต้อง (direction ก่อน, price หลัง)
                    if not self.grid_system.has_nearby_order("SELL", fill_price, 50):
                        self.grid_system.place_smart_rebalance_order("SELL", fill_price, self.grid_system.base_lot)
                        print(f"🔧 Fill SELL gap: @ ${fill_price:.2f} (was {sell_gap:.0f} points)")
            else:
                # ไม่มี SELL orders เลย - วางทันที!
                fill_price = current_price + (80 * 0.01)  # วางที่ 80 จุด
                if not self.grid_system.has_nearby_order("SELL", fill_price, 50):
                    self.grid_system.place_smart_rebalance_order("SELL", fill_price, self.grid_system.base_lot)
                    print(f"🚨 Emergency SELL: @ ${fill_price:.2f}")
                        
        except Exception as e:
            print(f"❌ Gap filling error: {e}")


    def place_market_rebalance_order(self, direction: str) -> bool:
        """เพิ่ม method ใหม่ - วาง Market Order เพื่อ Balance"""
        try:
            # Get current tick
            tick = mt5.symbol_info_tick(self.grid_system.gold_symbol)
            if not tick:
                print(f"❌ Cannot get tick for market rebalance")
                return False
                
            # ใช้ lot size พื้นฐาน
            lot_size = self.grid_system.base_lot
            
            # Determine price and order type
            if direction == "BUY":
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
                
            # Market order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.grid_system.gold_symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "deviation": 30,  # Allow slippage for market order
                "magic": self.grid_system.magic_number,
                "comment": f"REBALANCE_{direction}",
                "type_filling": self.grid_system.order_filling_mode
            }
            
            print(f"   🎯 Market {direction}: {lot_size:.3f} @ ${price:.2f}")
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"   ✅ Market rebalance: {direction} executed!")
                
                # Track ใน grid system
                from ai_gold_grid import GridLevel, PositionStatus
                
                market_level = GridLevel(
                    level_id=f"REBALANCE_{direction}_{int(time.time())}",
                    price=price,
                    lot_size=lot_size,
                    direction=direction,
                    status=PositionStatus.ACTIVE,
                    position_id=result.order,
                    entry_time=datetime.now()
                )
                
                self.grid_system.grid_levels.append(market_level)
                self.grid_system.active_positions[result.order] = market_level
                
                return True
            else:
                print(f"   ❌ Market rebalance failed: {result.comment if result else 'No response'}")
                return False
                
        except Exception as e:
            print(f"❌ Market rebalance order error: {e}")
            return False

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