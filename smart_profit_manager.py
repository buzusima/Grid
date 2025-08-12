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
        """🧠 AI MASTER CONTROLLER - แก้ไข method name errors"""
        try:
            print("🧠 AI MASTER CONTROLLER - ANALYZING PORTFOLIO")
            
            # 1. วิเคราะห์ positions ปัจจุบัน
            portfolio = self.analyze_portfolio_positions()
            if 'error' in portfolio or portfolio.get('total_positions', 0) == 0:
                print("🔄 No positions detected - AI creating intelligent grid")
                self.create_grid_immediately()  # ✅ ใช้ AI version
                return
                
            positions = portfolio.get('grid_positions', [])
            total_pnl = portfolio.get('total_pnl', 0)
            
            print(f"📊 Portfolio Status: {len(positions)} positions, PnL: ${total_pnl:.2f}")
            
            # 🧠 AI ตรวจสอบ survivability ปัจจุบัน
            if hasattr(self, 'ai_grid_config'):
                target_survivability = self.ai_grid_config.get('target_survivability', 10000)
                current_coverage = self.estimate_current_survivability(positions)
                survivability_ratio = current_coverage / target_survivability
                
                print(f"🛡️ AI SURVIVABILITY CHECK: {current_coverage:,}/{target_survivability:,} points ({survivability_ratio:.1%})")
                
                if survivability_ratio < 0.6:  # น้อยกว่า 60% ของ target
                    print("🚨 AI: SURVIVABILITY CRITICAL - Adding protective positions")
                    # ✅ แก้ไข: ใช้ method ที่มีอยู่จริง
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
                    # ✅ แก้ไข: ใช้ method ที่มีอยู่จริง
                    self.rebalance_portfolio_if_needed(positions)
            
            # 3. 🧠 AI Portfolio Health Check
            buy_count = len([p for p in positions if p.direction == "BUY"])
            sell_count = len([p for p in positions if p.direction == "SELL"])
            
            if buy_count == 0 or sell_count == 0:
                print(f"🚨 AI: CRITICAL IMBALANCE {buy_count}:{sell_count}")
                current_price = self.grid_system.get_current_price()
                self.smart_rebalance_immediately(current_price, buy_count, sell_count)
            elif abs(buy_count - sell_count) >= 3:
                print(f"⚖️ AI: REBALANCING NEEDED {buy_count}:{sell_count}")
                # ✅ แก้ไข: ใช้ method ที่มีอยู่จริง
                self.rebalance_portfolio_if_needed(positions)
            else:
                print(f"✅ AI: Portfolio healthy {buy_count}:{sell_count}")
            
        except Exception as e:
            print(f"❌ AI Master Controller error: {e}")

    def rebalance_portfolio_if_needed(self, positions):
        """แก้ไข method เดิม - เพิ่ม AI Intelligence"""
        try:
            current_price = self.grid_system.get_current_price()
            buy_count = len([p for p in positions if p.direction == "BUY"])
            sell_count = len([p for p in positions if p.direction == "SELL"])
            
            # 🧠 ใช้ AI config ถ้ามี
            if hasattr(self, 'ai_grid_config'):
                spacing = self.ai_grid_config.get('optimal_spacing', 500)
                base_lot = self.ai_grid_config.get('base_lot', 0.01)
                target_survivability = self.ai_grid_config.get('target_survivability', 10000)
                print(f"🧠 AI REBALANCING: Using AI config - spacing {spacing}, lot {base_lot:.3f}")
            else:
                # Fallback ถ้าไม่มี AI config
                account_info = self.grid_system.mt5_connector.get_account_info()
                balance = account_info.get('balance', 5000) if account_info else 5000
                spacing = 500 if balance < 10000 else 400
                base_lot = self.grid_system.base_lot
                target_survivability = 10000
                print(f"🔧 FALLBACK REBALANCING: spacing {spacing}, lot {base_lot:.3f}")
            
            print(f"📊 Portfolio: {buy_count} BUY, {sell_count} SELL @ ${current_price:.2f}")
            
            # 🧠 AI ตรวจสอบ coverage ก่อน
            total_positions = buy_count + sell_count
            if total_positions > 0:
                estimated_coverage = total_positions * spacing
                coverage_ratio = estimated_coverage / target_survivability
                
                print(f"🛡️ Coverage Analysis: {estimated_coverage:,} points ({coverage_ratio:.1%} of target)")
                
                # ถ้า coverage ต่ำมาก ให้เพิ่ม orders
                if coverage_ratio < 0.6:  # น้อยกว่า 60% ของ target
                    print("🔧 AI: Coverage too low, adding protective orders")
                    needed_orders = min(3, int((target_survivability - estimated_coverage) / spacing / 2))
                    
                    for i in range(1, needed_orders + 1):
                        buy_price = current_price - (spacing * (buy_count + i) * 0.01)
                        sell_price = current_price + (spacing * (sell_count + i) * 0.01)
                        
                        if self.grid_system.place_smart_rebalance_order("BUY", buy_price, base_lot):
                            print(f"   ✅ Protective BUY: @ ${buy_price:.2f}")
                        if self.grid_system.place_smart_rebalance_order("SELL", sell_price, base_lot):
                            print(f"   ✅ Protective SELL: @ ${sell_price:.2f}")
                        time.sleep(0.5)
                    
                    return
            
            # 🎯 Normal imbalance rebalancing
            imbalance = abs(buy_count - sell_count)
            if imbalance >= 2:  # เฉพาะ imbalance มากเกินไป
                if buy_count > sell_count:  # BUY เยอะ
                    needed = min(imbalance, 2)  # จำกัดไม่เกิน 2
                    print(f"⚖️ Adding {needed} SELL orders to balance")
                    for i in range(needed):
                        sell_price = current_price + (spacing * (i + 1) * 0.01)
                        if self.grid_system.place_smart_rebalance_order("SELL", sell_price, base_lot):
                            print(f"   ✅ Balance SELL: @ ${sell_price:.2f}")
                            time.sleep(0.5)
                
                elif sell_count > buy_count:  # SELL เยอะ
                    needed = min(imbalance, 2)  # จำกัดไม่เกิน 2
                    print(f"⚖️ Adding {needed} BUY orders to balance")
                    for i in range(needed):
                        buy_price = current_price - (spacing * (i + 1) * 0.01)
                        if self.grid_system.place_smart_rebalance_order("BUY", buy_price, base_lot):
                            print(f"   ✅ Balance BUY: @ ${buy_price:.2f}")
                            time.sleep(0.5)
                
                print(f"✅ Portfolio rebalanced with {target_survivability:,} point protection")
            else:
                print("✅ Portfolio balance within acceptable range")
                
        except Exception as e:
            print(f"❌ Rebalance error: {e}")

    def create_grid_immediately(self):
        """แก้ไข method เดิม - เปลี่ยนชื่อจาก create_safe_initial_grid"""
        try:
            current_price = self.grid_system.get_current_price()
            if not current_price:
                print("❌ Cannot get current price")
                return
            
            # 🧠 ดึงข้อมูล Account และคำนวณ AI parameters
            account_info = self.grid_system.mt5_connector.get_account_info()
            balance = account_info.get('balance', 5000) if account_info else 5000
            margin_level = account_info.get('margin_level', 300) if account_info else 300
            
            print(f"🧠 AI GRID CREATION @ ${current_price:.2f}")
            print(f"   💰 Balance: ${balance:,.0f}, Margin: {margin_level:.1f}%")
            
            # 🎯 AI คำนวณ parameters ตามเงินทุน
            if balance >= 50000:
                target_survivability = 20000
                base_lot = round(balance * 0.6 / 150000, 3)
                spacing = 600
            elif balance >= 20000:
                target_survivability = 15000
                base_lot = round(balance * 0.6 / 120000, 3)
                spacing = 500
            elif balance >= 5000:
                target_survivability = 10000
                base_lot = round(balance * 0.6 / 100000, 3)
                spacing = 400
            else:
                target_survivability = 8000
                base_lot = round(balance * 0.6 / 80000, 3)
                spacing = 350
            
            # ปรับให้เป็น minimum lot
            base_lot = max(base_lot, 0.01)
            
            print(f"🎯 AI TARGET: {target_survivability:,} points survivability")
            print(f"💎 Calculated: Lot {base_lot:.3f}, Spacing {spacing} points")
            
            # สร้าง grid แบบ layered
            orders_to_create = [
                # Near layer
                ("BUY", current_price - (spacing * 0.5 * 0.01), base_lot),
                ("SELL", current_price + (spacing * 0.5 * 0.01), base_lot),
                # Medium layer  
                ("BUY", current_price - (spacing * 1.0 * 0.01), base_lot),
                ("SELL", current_price + (spacing * 1.0 * 0.01), base_lot),
                # Far layer
                ("BUY", current_price - (spacing * 2.0 * 0.01), base_lot),
                ("SELL", current_price + (spacing * 2.0 * 0.01), base_lot)
            ]
            
            orders_placed = 0
            for direction, price, lot_size in orders_to_create:
                if self.grid_system.place_smart_rebalance_order(direction, price, lot_size):
                    orders_placed += 1
                    distance = abs(price - current_price) / 0.01
                    print(f"   ✅ {direction}: {lot_size:.3f} @ ${price:.2f} ({distance:.0f} pts)")
                    time.sleep(0.3)
                else:
                    print(f"   ❌ Failed {direction} @ ${price:.2f}")
            
            # 🧠 บันทึก AI config
            self.ai_grid_config = {
                'target_survivability': target_survivability,
                'optimal_spacing': spacing,
                'base_lot': base_lot,
                'last_calculated': datetime.now()
            }
            
            print(f"✅ AI GRID COMPLETE: {orders_placed}/6 orders")
            print(f"🛡️ Target survivability: {target_survivability:,} points")
            
        except Exception as e:
            print(f"❌ Grid creation error: {e}")

    def estimate_current_survivability(self, positions) -> int:
        """🧠 ประเมิน survivability ปัจจุบัน"""
        try:
            if not positions:
                return 0
            
            current_price = self.grid_system.get_current_price()
            
            # หาไม้ที่ไกลที่สุดในแต่ละทิศทาง
            buy_positions = [p for p in positions if p.direction == "BUY"]
            sell_positions = [p for p in positions if p.direction == "SELL"]
            
            max_buy_distance = 0
            max_sell_distance = 0
            
            if buy_positions:
                farthest_buy = min(buy_positions, key=lambda x: x.entry_price)
                max_buy_distance = abs(current_price - farthest_buy.entry_price) / 0.01
            
            if sell_positions:
                farthest_sell = max(sell_positions, key=lambda x: x.entry_price)
                max_sell_distance = abs(farthest_sell.entry_price - current_price) / 0.01
            
            # ประเมิน survivability จากระยะไกลสุด
            estimated_survivability = int(max(max_buy_distance, max_sell_distance) * 1.5)  # เผื่อไว้
            
            return estimated_survivability
            
        except Exception as e:
            print(f"❌ Estimate survivability error: {e}")
            return 0
        
    def smart_rebalance_immediately(self, current_price, buy_count, sell_count):
        """🧠 AI INTELLIGENT REBALANCE - แก้ไขจาก method เดิม"""
        try:
            # 🧠 ใช้ค่าที่ AI คำนวณไว้แล้ว
            if hasattr(self, 'ai_grid_config'):
                spacing = self.ai_grid_config.get('optimal_spacing', 500)
                base_lot = self.ai_grid_config.get('base_lot', 0.01)
                risk_tolerance = self.ai_grid_config.get('risk_tolerance', 'MODERATE')
            else:
                # Fallback calculation
                account_info = self.grid_system.mt5_connector.get_account_info()
                balance = account_info.get('balance', 5000) if account_info else 5000
                spacing = 500 if balance < 10000 else 400
                base_lot = 0.01
                risk_tolerance = 'MODERATE'
            
            print(f"🧠 AI REBALANCE: Using spacing {spacing} points, lot {base_lot:.3f}")
            
            orders_added = 0
            max_orders = 3 if risk_tolerance == 'AGGRESSIVE' else 2
            
            if buy_count == 0 and sell_count > 0:  # ไม่มี BUY เลย
                print("🚀 AI: Adding strategic BUY orders")
                for i in range(1, max_orders + 1):
                    buy_price = current_price - (spacing * i * 0.01)
                    if self.grid_system.place_smart_rebalance_order("BUY", buy_price, base_lot):
                        orders_added += 1
                        print(f"   ✅ Strategic BUY: @ ${buy_price:.2f} ({spacing * i} pts)")
                        time.sleep(0.3)
            
            elif sell_count == 0 and buy_count > 0:  # ไม่มี SELL เลย
                print("🚀 AI: Adding strategic SELL orders")
                for i in range(1, max_orders + 1):
                    sell_price = current_price + (spacing * i * 0.01)
                    if self.grid_system.place_smart_rebalance_order("SELL", sell_price, base_lot):
                        orders_added += 1
                        print(f"   ✅ Strategic SELL: @ ${sell_price:.2f} ({spacing * i} pts)")
                        time.sleep(0.3)
            
            print(f"🧠 AI REBALANCE COMPLETE: {orders_added} strategic orders added")
            
        except Exception as e:
            print(f"❌ AI rebalance error: {e}")

    def smart_rebalance_immediately(self, current_price, buy_count, sell_count):
            """🧠 AI INTELLIGENT REBALANCE - แก้ไขจาก method เดิม"""
            try:
                # 🧠 ใช้ค่าที่ AI คำนวณไว้แล้ว
                if hasattr(self, 'ai_grid_config'):
                    spacing = self.ai_grid_config.get('optimal_spacing', 500)
                    base_lot = self.ai_grid_config.get('base_lot', 0.01)
                    risk_tolerance = self.ai_grid_config.get('risk_tolerance', 'MODERATE')
                else:
                    # Fallback calculation
                    account_info = self.grid_system.mt5_connector.get_account_info()
                    balance = account_info.get('balance', 5000) if account_info else 5000
                    spacing = 500 if balance < 10000 else 400
                    base_lot = 0.01
                    risk_tolerance = 'MODERATE'
                
                print(f"🧠 AI REBALANCE: Using spacing {spacing} points, lot {base_lot:.3f}")
                
                orders_added = 0
                max_orders = 3 if risk_tolerance == 'AGGRESSIVE' else 2
                
                if buy_count == 0 and sell_count > 0:  # ไม่มี BUY เลย
                    print("🚀 AI: Adding strategic BUY orders")
                    for i in range(1, max_orders + 1):
                        buy_price = current_price - (spacing * i * 0.01)
                        if self.grid_system.place_smart_rebalance_order("BUY", buy_price, base_lot):
                            orders_added += 1
                            print(f"   ✅ Strategic BUY: @ ${buy_price:.2f} ({spacing * i} pts)")
                            time.sleep(0.3)
                
                elif sell_count == 0 and buy_count > 0:  # ไม่มี SELL เลย
                    print("🚀 AI: Adding strategic SELL orders")
                    for i in range(1, max_orders + 1):
                        sell_price = current_price + (spacing * i * 0.01)
                        if self.grid_system.place_smart_rebalance_order("SELL", sell_price, base_lot):
                            orders_added += 1
                            print(f"   ✅ Strategic SELL: @ ${sell_price:.2f} ({spacing * i} pts)")
                            time.sleep(0.3)
                
                print(f"🧠 AI REBALANCE COMPLETE: {orders_added} strategic orders added")
                
            except Exception as e:
                print(f"❌ AI rebalance error: {e}")

    def is_safe_to_manage(self) -> bool:
            """แก้ไข method เดิม - เอา Safety โง่ๆ ออก"""
            try:
                # ✅ แก้ไข: ลบเงื่อนไข market hours โง่ๆ (ทองคำเทรดได้ 24 ชม.)
                # ✅ แก้ไข: ลด margin requirement จาก 200% เป็น 100%
                account_info = self.grid_system.mt5_connector.get_account_info()
                if account_info:
                    margin_level = account_info.get('margin_level', 0)
                    if margin_level < 100:  # ลดจาก 200% เป็น 100%
                        print(f"🛡️ Margin level too low: {margin_level:.1f}%")
                        return False
                    else:
                        print(f"✅ Margin OK: {margin_level:.1f}%")
                
                # ✅ แก้ไข: เพิ่ม daily loss limit แต่ไม่โง่จนเกินไป
                daily_pnl = getattr(self.grid_system, 'daily_pnl', 0)
                if daily_pnl < -(self.grid_system.daily_loss_limit * 2):  # เพิ่มเป็น 2 เท่า
                    print(f"🛡️ Daily loss limit reached: ${daily_pnl:.2f}")
                    return False
                
                print("✅ All safety checks passed")
                return True
                
            except Exception as e:
                print(f"❌ Safety check error: {e}")
                return True  # ✅ แก้ไข: ถ้า error ให้ผ่านแทน (ไม่โง่)

    def should_rebuild_grid(self) -> bool:
        """แก้ไข method เดิม - ลบเงื่อนไขโง่ๆ ออก"""
        # ✅ แก้ไข: ให้สร้าง grid ได้เสมอ ไม่ต้องรอ
        return True

    def is_safe_to_add_positions(self) -> bool:
        """แก้ไข method เดิม - ผ่อนปรนเงื่อนไข"""
        try:
            account_info = self.grid_system.mt5_connector.get_account_info()
            if account_info:
                free_margin = account_info.get('free_margin', 0)
                margin_level = account_info.get('margin_level', 0)
                
                # ✅ แก้ไข: ลดเงื่อนไขจาก $1000 เป็น $300, และ 300% เป็น 150%
                if free_margin < 300 or margin_level < 150:
                    print(f"⚠️ Limited margin: ${free_margin:.2f}, Level: {margin_level:.1f}%")
                    return False
            
            # ✅ แก้ไข: เพิ่ม max positions จาก 15 เป็น 25
            current_positions = len(self.grid_system.active_positions)
            if current_positions >= 25:
                print(f"⚠️ Too many positions: {current_positions}/25")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Safe to add check error: {e}")
            return True  # ✅ แก้ไข: ถ้า error ให้ผ่าน

    def is_safe_to_rebalance(self) -> bool:
        """แก้ไข method เดิม - ให้ rebalance ได้บ่อยขึ้น"""
        # ✅ แก้ไข: ลดเวลารอจาก 3 นาที เป็น 30 วินาที
        if not hasattr(self, 'last_rebalance_time'):
            self.last_rebalance_time = datetime.now() - timedelta(minutes=10)
        
        time_since_rebalance = (datetime.now() - self.last_rebalance_time).total_seconds()
        if time_since_rebalance < 30:  # ลดจาก 180 เป็น 30 วินาที
            return False
        
        return True
    def create_safe_initial_grid(self):
        """สร้าง grid เริ่มต้นอย่างปลอดภัย - แก้ไขจาก method เดิม"""
        try:
            current_price = self.grid_system.get_current_price()
            if not current_price:
                return
            
            print(f"🏗️ Creating SAFE initial grid @ ${current_price:.2f}")
            
            base_lot = self.grid_system.base_lot
            spacing = 250  # ✅ เพิ่มจาก 150 เป็น 250 points (ห่างกว่าเดิม)
            
            # ✅ สร้างแค่ 4 orders เท่านั้น (แทน 6)
            orders_to_create = [
                ("BUY", current_price - (spacing * 0.01), base_lot),
                ("BUY", current_price - (spacing * 2 * 0.01), base_lot), 
                ("SELL", current_price + (spacing * 0.01), base_lot),
                ("SELL", current_price + (spacing * 2 * 0.01), base_lot)
            ]
            
            orders_placed = 0
            for direction, price, lot_size in orders_to_create:
                if self.grid_system.place_smart_rebalance_order(direction, price, lot_size):
                    orders_placed += 1
                    print(f"   ✅ Safe {direction}: {lot_size:.3f} @ ${price:.2f}")
                    time.sleep(1)  # ✅ เพิ่มเวลารอจาก 0.5 เป็น 1 วินาที
                else:
                    print(f"   ❌ Failed {direction} @ ${price:.2f}")
            
            # ✅ บันทึกเวลาที่สร้าง grid
            self.last_grid_rebuild = datetime.now()
            self.daily_rebuild_count = getattr(self, 'daily_rebuild_count', 0) + 1
            
            print(f"✅ Safe grid created: {orders_placed}/4 orders (Conservative spacing: {spacing} pts)")
            
        except Exception as e:
            print(f"❌ Safe grid creation error: {e}")

    def safe_emergency_rebalance(self, current_price, buy_count, sell_count):
        """Emergency rebalancing อย่างปลอดภัย - แก้ไขจาก method เดิม"""
        try:
            base_lot = self.grid_system.base_lot
            safe_spacing = 300  # ✅ เพิ่มจาก 120 เป็น 300 points (ปลอดภัยกว่า)
            
            orders_added = 0
            max_orders = 2  # ✅ จำกัดไม่เกิน 2 orders ต่อครั้ง
            
            if buy_count == 0 and sell_count >= 3:  # ไม่มี BUY เลย
                print("🚀 SAFE: Adding BUY orders with conservative spacing")
                for i in range(1, max_orders + 1):
                    buy_price = current_price - (safe_spacing * i * 0.01)
                    if self.grid_system.place_smart_rebalance_order("BUY", buy_price, base_lot):
                        orders_added += 1
                        print(f"   ✅ Safe BUY {i}: @ ${buy_price:.2f} ({safe_spacing * i} pts)")
                        time.sleep(2)  # ✅ รอ 2 วินาทีระหว่าง orders
            
            elif sell_count == 0 and buy_count >= 3:  # ไม่มี SELL เลย
                print("🚀 SAFE: Adding SELL orders with conservative spacing")
                for i in range(1, max_orders + 1):
                    sell_price = current_price + (safe_spacing * i * 0.01)
                    if self.grid_system.place_smart_rebalance_order("SELL", sell_price, base_lot):
                        orders_added += 1
                        print(f"   ✅ Safe SELL {i}: @ ${sell_price:.2f} ({safe_spacing * i} pts)")
                        time.sleep(2)  # ✅ รอ 2 วินาทีระหว่าง orders
            
            # ✅ บันทึกเวลา rebalance
            self.last_rebalance_time = datetime.now()
            self.daily_rebalance_count = getattr(self, 'daily_rebalance_count', 0) + 1
            
            print(f"✅ Safe emergency rebalance: {orders_added} orders added")
            
        except Exception as e:
            print(f"❌ Safe emergency rebalance error: {e}")

    def add_conservative_sell_orders(self, current_price, count):
        """เพิ่ม SELL orders แบบระมัดระวัง - แก้ไขจาก method เดิม"""
        try:
            conservative_spacing = 350  # ✅ เพิ่มจาก 150 เป็น 350 points
            
            for i in range(count):
                price = current_price + (conservative_spacing * (i + 1) * 0.01)
                
                if not self.grid_system.has_nearby_order(price, "SELL", 1.0):  # เพิ่ม tolerance
                    if self.grid_system.place_smart_rebalance_order("SELL", price, self.grid_system.base_lot):
                        print(f"   ✅ Conservative SELL: @ ${price:.2f} ({conservative_spacing * (i+1)} pts)")
                        time.sleep(3)  # ✅ รอ 3 วินาที (เดิม 0.5)
                        
        except Exception as e:
            print(f"❌ Conservative SELL error: {e}")

    def add_conservative_buy_orders(self, current_price, count):
        """เพิ่ม BUY orders แบบระมัดระวัง - แก้ไขจาก method เดิม"""
        try:
            conservative_spacing = 350  # ✅ เพิ่มจาก 150 เป็น 350 points
            
            for i in range(count):
                price = current_price - (conservative_spacing * (i + 1) * 0.01)
                
                if not self.grid_system.has_nearby_order(price, "BUY", 1.0):  # เพิ่ม tolerance
                    if self.grid_system.place_smart_rebalance_order("BUY", price, self.grid_system.base_lot):
                        print(f"   ✅ Conservative BUY: @ ${price:.2f} ({conservative_spacing * (i+1)} pts)")
                        time.sleep(3)  # ✅ รอ 3 วินาที (เดิม 0.5)
                        
        except Exception as e:
            print(f"❌ Conservative BUY error: {e}")

    def rebuild_grid_after_cleanup(self):
        """แก้ไข create_initial_grid_smart - ใช้ชื่อใหม่"""
        try:
            current_price = self.grid_system.get_current_price()
            if not current_price:
                print("❌ Cannot get current price for rebuilding")
                return
            
            print(f"🏗️ Rebuilding grid @ ${current_price:.2f}")
            
            base_lot = self.grid_system.base_lot
            spacing = 150  # 150 points
            orders_placed = 0
            
            # สร้าง 3 คู่ orders
            for i in range(1, 4):
                buy_price = current_price - (spacing * i * 0.01)
                sell_price = current_price + (spacing * i * 0.01)
                
                # BUY order
                if self.grid_system.place_smart_rebalance_order("BUY", buy_price, base_lot):
                    orders_placed += 1
                    time.sleep(0.5)
                
                # SELL order
                if self.grid_system.place_smart_rebalance_order("SELL", sell_price, base_lot):
                    orders_placed += 1
                    time.sleep(0.5)
            
            print(f"✅ Grid rebuilt: {orders_placed}/6 orders placed")
            
        except Exception as e:
            print(f"❌ Rebuild grid error: {e}")

    def force_rebalance_immediately(self, current_price, buy_count, sell_count):
        """แก้ไข method - Force rebalancing ทันที"""
        try:
            base_lot = self.grid_system.base_lot
            spacing = 120  # 120 points spacing (เร็วกว่า)
            
            if buy_count == 0:  # ไม่มี BUY เลย
                print("🚀 Force adding BUY orders")
                for i in range(1, min(sell_count + 1, 4)):  # เพิ่ม BUY ให้สมดุล
                    buy_price = current_price - (spacing * i * 0.01)
                    self.grid_system.place_smart_rebalance_order("BUY", buy_price, base_lot)
                    time.sleep(0.3)
            
            if sell_count == 0:  # ไม่มี SELL เลย
                print("🚀 Force adding SELL orders")
                for i in range(1, min(buy_count + 1, 4)):  # เพิ่ม SELL ให้สมดุล
                    sell_price = current_price + (spacing * i * 0.01)
                    self.grid_system.place_smart_rebalance_order("SELL", sell_price, base_lot)
                    time.sleep(0.3)
                    
        except Exception as e:
            print(f"❌ Force rebalance error: {e}")

    def add_coverage_orders(self, current_price, needed_count):
        """แก้ไข method - เพิ่ม orders เพื่อให้ coverage เพียงพอ"""
        try:
            base_lot = self.grid_system.base_lot
            spacing = 130  # 130 points
            orders_added = 0
            
            # เพิ่มสลับ BUY/SELL
            for i in range(1, (needed_count // 2) + 2):
                if orders_added >= needed_count:
                    break
                    
                # BUY order
                buy_price = current_price - (spacing * i * 0.01)
                if not self.grid_system.has_nearby_order(buy_price, "BUY", 0.5):
                    if self.grid_system.place_smart_rebalance_order("BUY", buy_price, base_lot):
                        orders_added += 1
                        time.sleep(0.3)
                
                if orders_added >= needed_count:
                    break
                
                # SELL order
                sell_price = current_price + (spacing * i * 0.01)
                if not self.grid_system.has_nearby_order(sell_price, "SELL", 0.5):
                    if self.grid_system.place_smart_rebalance_order("SELL", sell_price, base_lot):
                        orders_added += 1
                        time.sleep(0.3)
            
            print(f"🔧 Coverage orders added: {orders_added}/{needed_count}")
            
        except Exception as e:
            print(f"❌ Add coverage orders error: {e}")

    def execute_critical_cleanup(self, positions):
        """🚨 โหมดแก้ไข Portfolio วิกฤติ"""
        try:
            print("🚨 Executing critical cleanup...")
            
            # ปิดไม้ที่อยู่ผิดข้างตลาดทันที
            current_price = self.grid_system.get_current_price()
            wrong_side_pairs = self.find_wrong_side_pairs(
                [p for p in positions if p.direction == "BUY"],
                [p for p in positions if p.direction == "SELL"],
                current_price
            )
            
            if wrong_side_pairs:
                for pair in wrong_side_pairs[:2]:  # ปิดสูงสุด 2 คู่
                    self.execute_pair_close(pair)
                    time.sleep(1)
            
            # ปิดคู่ที่ช่วยลด margin load
            margin_pairs = self.find_margin_efficient_pairs(
                [p for p in positions if p.direction == "BUY"],
                [p for p in positions if p.direction == "SELL"]
            )
            
            if margin_pairs:
                for pair in margin_pairs[:1]:  # ปิดแค่ 1 คู่
                    if pair['net_profit'] > -5:  # ยอมขาดทุนไม่เกิน $5
                        self.execute_pair_close(pair)
                        time.sleep(1)
                        
        except Exception as e:
            print(f"❌ Critical cleanup error: {e}")
    
    def execute_balanced_management(self, positions):
        """⚡ โหมดจัดการแบบสมดุล"""
        try:
            print("⚡ Executing balanced management...")
            
            # หาคู่ที่มีกำไรดีและไม่กระทบ portfolio
            safe_profitable_pairs = []
            
            for pair_type_func in [self.find_balanced_pairs, self.find_margin_efficient_pairs]:
                pairs = pair_type_func(
                    [p for p in positions if p.direction == "BUY"],
                    [p for p in positions if p.direction == "SELL"]
                )
                
                # กรองเฉพาะคู่ที่ปลอดภัย
                for pair in pairs:
                    if pair['net_profit'] > 3 and self.is_safe_to_close(pair, positions):
                        safe_profitable_pairs.append(pair)
            
            # เรียงตาม profit และปิด
            safe_profitable_pairs.sort(key=lambda x: x['net_profit'], reverse=True)
            
            for pair in safe_profitable_pairs[:2]:  # ปิดสูงสุด 2 คู่
                self.execute_pair_close(pair)
                time.sleep(2)  # หน่วงนานขึ้นเพื่อความปลอดภัย
                
        except Exception as e:
            print(f"❌ Balanced management error: {e}")
    
    def execute_profit_optimization(self, positions):
        """✅ โหมดเพิ่มประสิทธิภาพกำไร"""
        try:
            print("✅ Executing profit optimization...")
            
            # หาคู่กำไรที่ดีที่สุด
            high_profit_pairs = []
            
            all_pairs = self.find_profitable_pairs(positions)
            
            for pair in all_pairs:
                # เฉพาะคู่ที่กำไรสูงและไม่กระทบ portfolio
                if pair['net_profit'] > 5 and self.is_optimal_close_timing(pair):
                    high_profit_pairs.append(pair)
            
            # ปิดเฉพาะคู่ที่คุ้มค่าจริงๆ
            for pair in high_profit_pairs[:3]:  # ปิดสูงสุด 3 คู่
                if self.confirm_optimal_close(pair):
                    self.execute_pair_close(pair)
                    time.sleep(1.5)
                    
        except Exception as e:
            print(f"❌ Profit optimization error: {e}")
    
    def is_safe_to_close(self, pair, all_positions) -> bool:
        """ตรวจสอบว่าปิดคู่นี้แล้วจะปลอดภัยไหม"""
        try:
            # ตรวจสอบว่าหลังปิดแล้ว portfolio จะยังสมดุลไหม
            remaining_positions = [p for p in all_positions 
                                 if p.position_id not in pair['position_ids']]
            
            if len(remaining_positions) < 4:  # ไม่ให้เหลือน้อยเกินไป
                return False
            
            buy_remaining = len([p for p in remaining_positions if p.direction == "BUY"])
            sell_remaining = len([p for p in remaining_positions if p.direction == "SELL"])
            
            # ตรวจสอบอัตราส่วน
            if buy_remaining == 0 or sell_remaining == 0:
                return False
                
            ratio = max(buy_remaining, sell_remaining) / min(buy_remaining, sell_remaining)
            
            return ratio <= 2.5  # อัตราส่วนไม่เกิน 2.5:1
            
        except:
            return False
    
    def is_optimal_close_timing(self, pair) -> bool:
        """ตรวจสอบว่าเป็นจังหวะที่ดีในการปิดไหม"""
        try:
            # ตรวจสอบ market volatility
            volatility = self.get_current_volatility()
            
            # ถ้า volatility สูง ให้รอ
            if volatility > 15:  # มากกว่า 15 points per minute
                return False
            
            # ตรวจสอบ profit stability
            for pos in pair.get('profitable_positions', []):
                if hasattr(pos, 'max_profit_seen'):
                    # ถ้ากำไรลดลงจาก peak มากกว่า 30%
                    if pos.pnl < pos.max_profit_seen * 0.7:
                        return False
            
            # ตรวจสอบเวลา - หลีกเลี่ยงช่วงข่าวสำคัญ
            current_hour = datetime.now().hour
            if current_hour in [8, 9, 14, 15, 21, 22]:  # ช่วงข่าวหลัก
                return False
            
            return True
            
        except:
            return True  # default ให้ปิดได้
    
    def confirm_optimal_close(self, pair) -> bool:
        """ยืนยันครั้งสุดท้ายก่อนปิด"""
        try:
            # อัพเดทราคาล่าสุด
            current_price = self.grid_system.get_current_price()
            
            # คำนวณกำไรใหม่ด้วยราคาปัจจุบัน
            updated_pnl = 0
            for pos in pair.get('profitable_positions', []) + pair.get('losing_positions', []):
                if pos.direction == "BUY":
                    updated_pnl += (current_price - pos.entry_price) * pos.lot_size * 100
                else:
                    updated_pnl += (pos.entry_price - current_price) * pos.lot_size * 100
            
            # ตรวจสอบว่ายังคุ้มค่าไหม
            if updated_pnl < pair['net_profit'] * 0.8:  # ลดลงมากกว่า 20%
                print(f"   ⚠️ Profit reduced, skipping close: ${updated_pnl:.2f} vs ${pair['net_profit']:.2f}")
                return False
            
            return True
            
        except:
            return True
    
    def analyze_market_timing(self) -> Dict:
        """วิเคราะห์สภาวะตลาดสำหรับ timing"""
        try:
            current_price = self.grid_system.get_current_price()
            
            # ดึงประวัติราคา 10 นาทีล่าสุด
            price_history = self.grid_system.price_history[-10:] if hasattr(self.grid_system, 'price_history') else []
            
            if len(price_history) < 5:
                return {'condition': 'UNKNOWN', 'volatility': 0, 'trend': 'SIDEWAYS'}
            
            # คำนวณ volatility
            price_changes = [abs(price_history[i] - price_history[i-1]) for i in range(1, len(price_history))]
            avg_volatility = sum(price_changes) / len(price_changes) if price_changes else 0
            
            # คำนวณ trend
            price_diff = price_history[-1] - price_history[0]
            if price_diff > 0.5:
                trend = 'UPTREND'
            elif price_diff < -0.5:
                trend = 'DOWNTREND'
            else:
                trend = 'SIDEWAYS'
            
            # กำหนดสภาวะ
            if avg_volatility > 1.0:
                condition = 'HIGH_VOLATILITY'
            elif avg_volatility < 0.3:
                condition = 'LOW_VOLATILITY'
            else:
                condition = 'NORMAL'
            
            return {
                'condition': condition,
                'volatility': avg_volatility,
                'trend': trend,
                'recommendation': self.get_timing_recommendation(condition, trend)
            }
            
        except:
            return {'condition': 'UNKNOWN', 'volatility': 0, 'trend': 'SIDEWAYS', 'recommendation': 'NORMAL'}
    
    def get_timing_recommendation(self, condition, trend) -> str:
        """แนะนำ timing strategy"""
        if condition == 'HIGH_VOLATILITY':
            return 'WAIT'  # รอให้ volatility ลดลง
        elif condition == 'LOW_VOLATILITY' and trend == 'SIDEWAYS':
            return 'AGGRESSIVE'  # เหมาะปิดเก็บกำไร
        elif trend in ['UPTREND', 'DOWNTREND']:
            return 'SELECTIVE'  # เลือกปิดเฉพาะที่คุ้มค่า
        else:
            return 'NORMAL'
    
    def adjust_close_timing_by_market(self, market_condition, positions):
        """ปรับ timing การปิดตามสภาวะตลาด"""
        try:
            recommendation = market_condition.get('recommendation', 'NORMAL')
            
            if recommendation == 'WAIT':
                print("⏸️ Market timing: Waiting for better conditions")
                return
            elif recommendation == 'AGGRESSIVE':
                print("🚀 Market timing: Aggressive profit taking")
                # ลด threshold การปิด
                self.temporary_profit_threshold = 1.5
            elif recommendation == 'SELECTIVE':
                print("🎯 Market timing: Selective closing")
                # เพิ่ม threshold การปิด
                self.temporary_profit_threshold = 4.0
            else:
                print("📊 Market timing: Normal operations")
                self.temporary_profit_threshold = 2.5
                
        except Exception as e:
            print(f"❌ Market timing adjustment error: {e}")
    
    def get_current_volatility(self) -> float:
        """คำนวณ volatility ปัจจุบัน"""
        try:
            if not hasattr(self.grid_system, 'price_history'):
                return 5.0  # default volatility
                
            recent_prices = self.grid_system.price_history[-5:]  # 5 ราคาล่าสุด
            
            if len(recent_prices) < 2:
                return 5.0
                
            price_changes = [abs(recent_prices[i] - recent_prices[i-1]) / 0.01 
                           for i in range(1, len(recent_prices))]
            
            return sum(price_changes) / len(price_changes) if price_changes else 5.0
            
        except:
            return 5.0
        
    def find_critical_gaps_near_market(self, current_price) -> Dict:
        """หาช่องว่างใกล้ราคาตลาดที่ต้องเติม - แก้ไข Method"""
        try:
            # ✅ ใช้ method ที่มีอยู่จริงใน AIGoldGrid
            pending_orders = self.grid_system.get_pending_orders()
            
            if not pending_orders:
                print("📋 No pending orders found, creating default gaps")
                return {
                    'buy_gaps': [{
                        'price': current_price - (200 * 0.01),
                        'gap_size': 999,
                        'reason': 'No pending orders exist'
                    }],
                    'sell_gaps': [{
                        'price': current_price + (200 * 0.01),
                        'gap_size': 999,
                        'reason': 'No pending orders exist'
                    }]
                }
            
            buy_orders = [o for o in pending_orders if o.get('direction') == 'BUY']
            sell_orders = [o for o in pending_orders if o.get('direction') == 'SELL']
            
            gaps = {'buy_gaps': [], 'sell_gaps': []}
            critical_distance = 200  # 200 points จากตลาด
            
            # หาช่องว่าง BUY ใกล้ตลาด
            if buy_orders:
                buy_prices = sorted([o['price'] for o in buy_orders], reverse=True)
                nearest_buy = buy_prices[0]
                gap_distance = (current_price - nearest_buy) / 0.01
                
                if gap_distance > critical_distance:
                    gaps['buy_gaps'].append({
                        'price': current_price - (critical_distance * 0.01),
                        'gap_size': gap_distance,
                        'reason': f'Critical gap: {gap_distance:.0f} points from nearest BUY'
                    })
            else:
                # ไม่มี BUY orders เลย
                gaps['buy_gaps'].append({
                    'price': current_price - (critical_distance * 0.01),
                    'gap_size': 999,
                    'reason': 'No BUY orders exist'
                })
            
            # หาช่องว่าง SELL ใกล้ตลาด
            if sell_orders:
                sell_prices = sorted([o['price'] for o in sell_orders])
                nearest_sell = sell_prices[0]
                gap_distance = (nearest_sell - current_price) / 0.01
                
                if gap_distance > critical_distance:
                    gaps['sell_gaps'].append({
                        'price': current_price + (critical_distance * 0.01),
                        'gap_size': gap_distance,
                        'reason': f'Critical gap: {gap_distance:.0f} points from nearest SELL'
                    })
            else:
                # ไม่มี SELL orders เลย
                gaps['sell_gaps'].append({
                    'price': current_price + (critical_distance * 0.01),
                    'gap_size': 999,
                    'reason': 'No SELL orders exist'
                })
            
            print(f"🔍 Found gaps: {len(gaps['buy_gaps'])} BUY, {len(gaps['sell_gaps'])} SELL")
            return gaps
            
        except Exception as e:
            print(f"❌ Find critical gaps error: {e}")
            # Return safe default gaps
            return {
                'buy_gaps': [{
                    'price': current_price - (200 * 0.01),
                    'gap_size': 200,
                    'reason': 'Error fallback - default BUY gap'
                }],
                'sell_gaps': [{
                    'price': current_price + (200 * 0.01),
                    'gap_size': 200,
                    'reason': 'Error fallback - default SELL gap'
                }]
            }
    
    def add_sell_orders_for_balance(self, current_price, count):
        """แก้ไข method - ใช้ฟังก์ชันที่มีอยู่จริง"""
        try:
            tight_spacing = 150  # 150 จุด
            
            for i in range(min(count, 3)):  # เพิ่มสูงสุด 3 ตัว
                price = current_price + (tight_spacing * (i + 1) * 0.01)
                
                # ✅ ใช้ method ที่มีอยู่จริง
                if not self.grid_system.has_nearby_order(price, "SELL"):
                    lot_size = self.grid_system.base_lot
                    success = self.grid_system.place_smart_rebalance_order("SELL", price, lot_size)
                    if success:
                        print(f"   ✅ Balance SELL: {lot_size:.3f} @ ${price:.2f}")
                        
        except Exception as e:
            print(f"❌ Balance SELL orders error: {e}")

    def add_buy_orders_for_balance(self, current_price, count):
        """แก้ไข method - ใช้ฟังก์ชันที่มีอยู่จริง"""
        try:
            tight_spacing = 150  # 150 จุด
            
            for i in range(min(count, 3)):  # เพิ่มสูงสุด 3 ตัว
                price = current_price - (tight_spacing * (i + 1) * 0.01)
                
                # ✅ ใช้ method ที่มีอยู่จริง
                if not self.grid_system.has_nearby_order(price, "BUY"):
                    lot_size = self.grid_system.base_lot
                    success = self.grid_system.place_smart_rebalance_order("BUY", price, lot_size)
                    if success:
                        print(f"   ✅ Balance BUY: {lot_size:.3f} @ ${price:.2f}")
                        
        except Exception as e:
            print(f"❌ Balance BUY orders error: {e}")


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
        """🧠 AI INTELLIGENT CLOSING - แก้ไขจาก method เดิม"""
        try:
            if not positions:
                return []
                
            current_price = self.grid_system.get_current_price()
            account_info = self.grid_system.mt5_connector.get_account_info()
            current_margin_level = account_info.get('margin_level', 0) if account_info else 0
            
            print(f"🧠 AI ANALYSIS: {len(positions)} positions @ ${current_price:.2f} (Margin: {current_margin_level:.1f}%)")
            
            # 🎯 จัดหมวดหมู่ไม้อย่างฉลาด
            buy_positions = [p for p in positions if p.direction == "BUY"]
            sell_positions = [p for p in positions if p.direction == "SELL"]
            
            hedging_positions = []      # ไม้ค้ำพอร์ต
            profit_generators = []      # ไม้กำไรดี  
            losing_positions = []       # ไม้ขาดทุน
            dead_weight = []           # ไม้ไม่มีประโยชน์
            
            # 🧠 วิเคราะห์ไม้แต่ละตัว
            for pos in positions:
                distance_from_market = abs(pos.entry_price - current_price) / 0.01  # points
                
                # 🛡️ ไม้ค้ำพอร์ต = อยู่ห่างจากตลาด > 500 points และมี potential กำไร
                if distance_from_market > 500:
                    potential_profit = 0
                    if pos.direction == "BUY" and current_price < pos.entry_price:
                        potential_profit = (pos.entry_price - current_price) * pos.lot_size * 100
                    elif pos.direction == "SELL" and current_price > pos.entry_price:
                        potential_profit = (current_price - pos.entry_price) * pos.lot_size * 100
                    
                    if potential_profit > 5:  # มี potential > $5
                        hedging_positions.append(pos)
                        print(f"   🛡️ HEDGE: {pos.direction} @ ${pos.entry_price:.2f} (${pos.pnl:.2f}) - Potential: +${potential_profit:.2f}")
                        continue
                
                # 💰 ไม้กำไรดี = กำไร > $2 และอยู่ใกล้ตลาด
                if pos.pnl > 2 and distance_from_market < 300:
                    profit_generators.append(pos)
                    print(f"   💰 PROFIT GEN: {pos.direction} @ ${pos.entry_price:.2f} (+${pos.pnl:.2f})")
                    continue
                
                # 📉 ไม้ขาดทุน = ขาดทุน > $1
                elif pos.pnl < -1:
                    losing_positions.append(pos)
                    print(f"   📉 LOSING: {pos.direction} @ ${pos.entry_price:.2f} (${pos.pnl:.2f})")
                    continue
                
                # 🗑️ ไม้ไม่มีประโยชน์ = กำไรน้อย และไม่ค้ำพอร์ต
                else:
                    dead_weight.append(pos)
                    print(f"   🗑️ DEAD WEIGHT: {pos.direction} @ ${pos.entry_price:.2f} (${pos.pnl:.2f})")
            
            print(f"📊 Classification: 🛡️{len(hedging_positions)} 💰{len(profit_generators)} 📉{len(losing_positions)} 🗑️{len(dead_weight)}")
            
            smart_pairs = []
            
            # 🎯 STRATEGY 1: ใช้ไม้กำไรดีปิดไม้ขาดทุน (สำคัญที่สุด)
            for profit_pos in profit_generators:
                for loss_pos in losing_positions:
                    net_pnl = profit_pos.pnl + loss_pos.pnl
                    margin_freed = (profit_pos.lot_size + loss_pos.lot_size) * 500  # ประมาณการ margin
                    
                    if net_pnl > -1:  # ยอมขาดทุนสุทธิไม่เกิน $1
                        smart_pairs.append({
                            'losing_positions': [loss_pos],
                            'profitable_positions': [profit_pos],
                            'net_profit': net_pnl,
                            'total_positions': 2,
                            'pair_type': "SMART_RECOVERY",
                            'priority_score': 2000 + abs(loss_pos.pnl) + margin_freed/100,  # Priority สูงสุด
                            'position_ids': {profit_pos.position_id, loss_pos.position_id},
                            'margin_impact': f"+${margin_freed:.0f} freed",
                            'reason': f"Use profit ${profit_pos.pnl:.2f} to close loss ${loss_pos.pnl:.2f}"
                        })
                        print(f"   🎯 SMART RECOVERY: Use +${profit_pos.pnl:.2f} to close ${loss_pos.pnl:.2f} = ${net_pnl:.2f}")
            
            # 🎯 STRATEGY 2: ปิด Dead Weight ที่มีกำไรเล็กน้อย
            for dead_pos in dead_weight:
                if dead_pos.pnl > 0.5:  # กำไรเล็กๆ
                    smart_pairs.append({
                        'losing_positions': [],
                        'profitable_positions': [dead_pos],
                        'net_profit': dead_pos.pnl,
                        'total_positions': 1,
                        'pair_type': "CLEANUP_PROFIT",
                        'priority_score': 1500 + dead_pos.pnl,
                        'position_ids': {dead_pos.position_id},
                        'margin_impact': f"+${dead_pos.lot_size * 500:.0f} freed",
                        'reason': f"Clean small profit ${dead_pos.pnl:.2f} + free margin"
                    })
                    print(f"   🧹 CLEANUP: Small profit ${dead_pos.pnl:.2f} + margin free")
            
            # 🎯 STRATEGY 3: ปิดคู่กำไรปกติ (ถ้าไม่มี recovery opportunities)
            if len(smart_pairs) < 2:  # ถ้ายังไม่มีคู่ดีๆ
                for buy_pos in buy_positions:
                    for sell_pos in sell_positions:
                        # ✅ ตรวจสอบว่าไม่ใช่ไม้ค้ำพอร์ต
                        if buy_pos in hedging_positions or sell_pos in hedging_positions:
                            continue
                            
                        net_pnl = buy_pos.pnl + sell_pos.pnl
                        
                        if net_pnl > 1.2:  # threshold ปกติ
                            margin_freed = (buy_pos.lot_size + sell_pos.lot_size) * 500
                            
                            smart_pairs.append({
                                'losing_positions': [buy_pos if buy_pos.pnl < 0 else sell_pos] if min(buy_pos.pnl, sell_pos.pnl) < 0 else [],
                                'profitable_positions': [buy_pos if buy_pos.pnl > 0 else sell_pos] if max(buy_pos.pnl, sell_pos.pnl) > 0 else [buy_pos, sell_pos],
                                'net_profit': net_pnl,
                                'total_positions': 2,
                                'pair_type': "STANDARD_PROFIT",
                                'priority_score': 1000 + net_pnl,
                                'position_ids': {buy_pos.position_id, sell_pos.position_id},
                                'margin_impact': f"+${margin_freed:.0f} freed",
                                'reason': f"Standard pair profit"
                            })
                            print(f"   💰 STANDARD: {buy_pos.direction}(${buy_pos.pnl:.2f}) + {sell_pos.direction}(${sell_pos.pnl:.2f}) = +${net_pnl:.2f}")
            
            # 🎯 STRATEGY 4: Emergency margin relief (ถ้า margin ต่ำ)
            if current_margin_level < 200:
                print(f"🚨 LOW MARGIN ({current_margin_level:.1f}%) - Emergency margin relief")
                
                # หาไม้ที่ใช้ margin มากที่สุด
                high_margin_positions = sorted(positions, key=lambda x: x.lot_size, reverse=True)[:3]
                
                for pos in high_margin_positions:
                    if pos not in hedging_positions and pos.pnl > -2:  # ไม่ใช่ hedge และไม่เสียมาก
                        margin_freed = pos.lot_size * 500
                        
                        smart_pairs.append({
                            'losing_positions': [pos] if pos.pnl < 0 else [],
                            'profitable_positions': [pos] if pos.pnl > 0 else [],
                            'net_profit': pos.pnl,
                            'total_positions': 1,
                            'pair_type': "EMERGENCY_MARGIN",
                            'priority_score': 2500 + margin_freed/100,  # Priority สูงมาก
                            'position_ids': {pos.position_id},
                            'margin_impact': f"+${margin_freed:.0f} CRITICAL margin relief",
                            'reason': f"Emergency: Free {margin_freed:.0f} margin"
                        })
                        print(f"   🚨 EMERGENCY: Close {pos.direction}(${pos.pnl:.2f}) to free ${margin_freed:.0f} margin")
            
            # เรียงตาม priority
            smart_pairs.sort(key=lambda x: x['priority_score'], reverse=True)
            
            # กรองไม่ให้ซ้ำ
            final_pairs = self.select_non_overlapping_pairs(smart_pairs)
            
            # แสดงผลการวิเคราะห์
            if final_pairs:
                print(f"🎯 AI DECISION: {len(final_pairs)} intelligent actions selected")
                for i, pair in enumerate(final_pairs[:3]):
                    print(f"   {i+1}. {pair['pair_type']}: {pair['reason']} → {pair['margin_impact']}")
                    
                # 🛡️ เตือนถ้าจะปิดไม้ค้ำพอร์ต
                hedging_ids = {pos.position_id for pos in hedging_positions}
                for pair in final_pairs:
                    if hedging_ids.intersection(pair['position_ids']):
                        print(f"   ⚠️ WARNING: Pair contains hedging position - reconsider!")
            else:
                print("🤔 AI DECISION: No intelligent closing opportunities found")
                print(f"   💡 Keeping {len(hedging_positions)} hedge positions")
                print(f"   💡 Monitoring {len(profit_generators)} profit generators")
            
            return final_pairs
            
        except Exception as e:
            print(f"❌ AI analysis error: {e}")
            return []

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
                        'position_ids': {wrong_pos.position_id, good_pos.position_id}
                    })
        
        return wrong_pairs
    
    def find_margin_efficient_pairs(self, buy_positions, sell_positions):
        """💪 หาคู่ที่ปิดแล้วลด margin load มากที่สุด"""
        margin_pairs = []
        
        # คำนวณ margin impact ของแต่ละ position  
        for buy_pos in buy_positions:
            for sell_pos in sell_positions:
                net_pnl = buy_pos.pnl + sell_pos.pnl
                
                # คำนวณ margin ที่จะได้คืน
                margin_released = (buy_pos.lot_size + sell_pos.lot_size) * 1000  # ประมาณการ
                
                # ต้องมีกำไรสุทธิ หรือ margin efficiency ดี
                efficiency_score = (net_pnl + 5) + (margin_released * 0.01)  # bonus สำหรับ margin release
                
                if net_pnl > -2 and efficiency_score > 8:  # threshold ปรับได้
                    margin_pairs.append({
                        'losing_positions': [buy_pos if buy_pos.pnl < 0 else sell_pos] if min(buy_pos.pnl, sell_pos.pnl) < 0 else [],
                        'profitable_positions': [buy_pos if buy_pos.pnl > 0 else sell_pos] if max(buy_pos.pnl, sell_pos.pnl) > 0 else [],
                        'net_profit': net_pnl,
                        'total_positions': 2,
                        'pair_type': "MARGIN_EFFICIENT",
                        'priority_score': 1500 + efficiency_score,
                        'position_ids': {buy_pos.position_id, sell_pos.position_id},
                        'margin_released': margin_released
                    })
        
        return margin_pairs
    
    def find_balanced_pairs(self, buy_positions, sell_positions):
        """🎯 คู่กำไรปกติ (threshold สูงขึ้นเพื่อไม่ปิดรัว)"""
        balanced_pairs = []
        
        for buy_pos in buy_positions:
            for sell_pos in sell_positions:
                net_pnl = buy_pos.pnl + sell_pos.pnl
                
                # เพิ่ม threshold จาก $0.1 เป็น $2.5 (ไม่ปิดรัว)
                if net_pnl > 2.5:
                    # คำนวณคุณภาพของคู่
                    pair_quality = net_pnl
                    if min(buy_pos.pnl, sell_pos.pnl) > 0:  # ทั้งคู่กำไร
                        pair_quality *= 1.5
                    
                    balanced_pairs.append({
                        'losing_positions': [buy_pos if buy_pos.pnl < sell_pos.pnl else sell_pos],
                        'profitable_positions': [sell_pos if buy_pos.pnl < sell_pos.pnl else buy_pos],
                        'net_profit': net_pnl,
                        'total_positions': 2,
                        'pair_type': "BALANCED_PROFIT",
                        'priority_score': 800 + pair_quality,
                        'position_ids': {buy_pos.position_id, sell_pos.position_id}
                    })
        
        return balanced_pairs
    
    def find_balance_correction_pairs(self, buy_positions, sell_positions):
        """⚖️ แก้ไข BUY:SELL ratio ให้สมดุล"""
        balance_pairs = []
        
        buy_count = len(buy_positions)
        sell_count = len(sell_positions)
        imbalance = abs(buy_count - sell_count)
        
        # ถ้าไม่สมดุลเกิน 3 positions
        if imbalance <= 3:
            return []
        
        # หาคู่ที่ช่วยปรับสมดุล
        if buy_count > sell_count:  # BUY เยอะเกิน
            # หาคู่ที่มี BUY หลายตัว + SELL น้อยตัว
            excess_buys = sorted(buy_positions, key=lambda x: x.pnl, reverse=True)[:imbalance//2]
            for buy_pos in excess_buys:
                for sell_pos in sell_positions:
                    net_pnl = buy_pos.pnl + sell_pos.pnl
                    if net_pnl > 1.0:  # threshold ต่ำกว่าปกติเพื่อปรับสมดุล
                        balance_pairs.append({
                            'losing_positions': [buy_pos if buy_pos.pnl < 0 else sell_pos] if min(buy_pos.pnl, sell_pos.pnl) < 0 else [],
                            'profitable_positions': [buy_pos if buy_pos.pnl > 0 else sell_pos] if max(buy_pos.pnl, sell_pos.pnl) > 0 else [],
                            'net_profit': net_pnl,
                            'total_positions': 2,
                            'pair_type': "BALANCE_CORRECTION",
                            'priority_score': 600 + net_pnl + imbalance,  # bonus สำหรับ balance
                            'position_ids': {buy_pos.position_id, sell_pos.position_id}
                        })
        
        return balance_pairs
    
    def get_portfolio_health_score(self, positions) -> Dict:
        """📊 คำนวณ Portfolio Health Score"""
        try:
            if not positions:
                return {'score': 0, 'status': 'NO_POSITIONS', 'issues': []}
            
            current_price = self.grid_system.get_current_price()
            buy_positions = [p for p in positions if p.direction == "BUY"]
            sell_positions = [p for p in positions if p.direction == "SELL"]
            
            health_score = 100  # เริ่มที่ 100
            issues = []
            
            # 1. Balance Score (20 points)
            balance_ratio = len(buy_positions) / len(sell_positions) if sell_positions else 999
            if balance_ratio > 2 or balance_ratio < 0.5:
                health_score -= 20
                issues.append(f"Imbalanced BUY:SELL ratio ({len(buy_positions)}:{len(sell_positions)})")
            elif balance_ratio > 1.5 or balance_ratio < 0.67:
                health_score -= 10
                issues.append("Slightly imbalanced positions")
            
            # 2. Wrong Side Score (30 points)
            wrong_buys = len([b for b in buy_positions if b.entry_price > current_price])
            wrong_sells = len([s for s in sell_positions if s.entry_price < current_price])
            wrong_percentage = (wrong_buys + wrong_sells) / len(positions) * 100
            
            if wrong_percentage > 30:
                health_score -= 30
                issues.append(f"{wrong_percentage:.1f}% positions on wrong side")
            elif wrong_percentage > 15:
                health_score -= 15
                issues.append(f"{wrong_percentage:.1f}% positions need adjustment")
            
            # 3. PnL Distribution Score (25 points)
            total_pnl = sum(p.pnl for p in positions)
            losing_positions = len([p for p in positions if p.pnl < -2])
            losing_percentage = losing_positions / len(positions) * 100
            
            if losing_percentage > 70:
                health_score -= 25
                issues.append(f"{losing_percentage:.1f}% positions losing significantly")
            elif losing_percentage > 50:
                health_score -= 15
                issues.append("High percentage of losing positions")
            
            # 4. Margin Efficiency Score (25 points)
            large_positions = len([p for p in positions if p.lot_size > self.grid_system.base_lot * 2])
            if large_positions > len(positions) * 0.3:  # มากกว่า 30%
                health_score -= 15
                issues.append("High margin usage from large positions")
            
            # กำหนด status
            if health_score >= 80:
                status = "EXCELLENT"
            elif health_score >= 60:
                status = "GOOD"
            elif health_score >= 40:
                status = "FAIR"
            elif health_score >= 20:
                status = "POOR"
            else:
                status = "CRITICAL"
            
            return {
                'score': max(0, health_score),
                'status': status,
                'total_pnl': total_pnl,
                'wrong_side_percentage': wrong_percentage,
                'balance_ratio': f"{len(buy_positions)}:{len(sell_positions)}",
                'losing_percentage': losing_percentage,
                'issues': issues,
                'recommendations': self.get_health_recommendations(health_score, issues)
            }
            
        except Exception as e:
            return {'score': 0, 'status': 'ERROR', 'issues': [f"Calculation error: {e}"]}
    
    def get_health_recommendations(self, score, issues) -> List[str]:
        """💡 แนะนำการปรับปรุง Portfolio"""
        recommendations = []
        
        if score < 40:
            recommendations.append("🚨 Consider emergency portfolio cleanup")
            recommendations.append("🔄 Close wrong-side positions immediately")
        elif score < 60:
            recommendations.append("⚖️ Focus on balancing BUY:SELL ratio")
            recommendations.append("💰 Close small profitable pairs to reduce load")
        elif score < 80:
            recommendations.append("🎯 Optimize position placement")
            recommendations.append("📊 Monitor margin usage")
        else:
            recommendations.append("✅ Portfolio in good condition")
            recommendations.append("🔍 Continue regular monitoring")
        
        return recommendations

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
        """เลือกคู่ที่ไม่ซ้ำกัน (greedy selection)"""
        selected_pairs = []
        used_position_ids = set()
        
        for pair in all_pairs:
            # เช็คว่า position ใดๆ ในคู่นี้ถูกใช้แล้วไหม
            if not pair['position_ids'].intersection(used_position_ids):
                selected_pairs.append(pair)
                used_position_ids.update(pair['position_ids'])
                
                # จำกัดจำนวนคู่สูงสุด (ไม่ให้ปิดครั้งละเยอะเกินไป)
                if len(selected_pairs) >= 5:  # สูงสุด 5 คู่ต่อครั้ง
                    break
        
        return selected_pairs
    
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

    def run_portfolio_cleanup(self) -> Dict:
        """🧹 Smart Portfolio Cleanup - ระบบทำความสะอาด Portfolio อัจฉริยะ"""
        try:
            print("🧹 Starting Smart Portfolio Cleanup...")
            
            # 1. วิเคราะห์ portfolio ปัจจุบัน
            portfolio = self.analyze_portfolio_positions()
            if 'error' in portfolio or not portfolio.get('grid_positions'):
                return {'success': False, 'error': 'No positions to cleanup'}
            
            positions = portfolio['grid_positions']
            initial_count = len(positions)
            initial_margin = self.calculate_total_margin_used(positions)
            
            print(f"📊 Initial Portfolio: {initial_count} positions, ${initial_margin:.2f} margin")
            
            # 2. ประเมิน Portfolio Health
            health_data = self.get_portfolio_health_score(positions)
            print(f"🏥 Portfolio Health: {health_data['score']:.0f}/100 ({health_data['status']})")
            
            cleanup_actions = []
            total_closed = 0
            total_margin_freed = 0
            
            # 3. Phase 1: ปิดไม้ที่อยู่ผิดข้างตลาด (Priority สูงสุด)
            wrong_side_pairs = self.find_wrong_side_pairs(
                [p for p in positions if p.direction == "BUY"],
                [p for p in positions if p.direction == "SELL"],
                self.grid_system.get_current_price()
            )
            
            if wrong_side_pairs:
                print(f"🚨 Phase 1: Closing {len(wrong_side_pairs)} wrong-side pairs...")
                for pair in wrong_side_pairs[:3]:  # จำกัดไม่เกิน 3 คู่ต่อครั้ง
                    if self.execute_pair_close(pair):
                        cleanup_actions.append(f"Closed wrong-side pair: +${pair['net_profit']:.2f}")
                        total_closed += pair['total_positions']
                        total_margin_freed += self.estimate_margin_freed(pair)
                        time.sleep(0.5)  # หน่วงเพื่อไม่ให้ระบบล้น
            
            # 4. Phase 2: ปิดคู่ที่ช่วยลด margin load
            margin_efficient_pairs = self.find_margin_efficient_pairs(
                [p for p in positions if p.direction == "BUY" and p.position_id not in self.get_closed_position_ids()],
                [p for p in positions if p.direction == "SELL" and p.position_id not in self.get_closed_position_ids()]
            )
            
            if margin_efficient_pairs:
                print(f"💪 Phase 2: Closing {len(margin_efficient_pairs)} margin-efficient pairs...")
                for pair in margin_efficient_pairs[:2]:  # จำกัด 2 คู่
                    if self.execute_pair_close(pair):
                        cleanup_actions.append(f"Closed margin-efficient pair: +${pair['net_profit']:.2f}")
                        total_closed += pair['total_positions']
                        total_margin_freed += self.estimate_margin_freed(pair)
                        time.sleep(0.5)
            
            # 5. Phase 3: ปรับสมดุล BUY:SELL (ถ้าจำเป็น)
            remaining_positions = self.get_remaining_positions(positions)
            balance_pairs = self.find_balance_correction_pairs(
                [p for p in remaining_positions if p.direction == "BUY"],
                [p for p in remaining_positions if p.direction == "SELL"]
            )
            
            if balance_pairs:
                print(f"⚖️ Phase 3: Balancing {len(balance_pairs)} position pairs...")
                for pair in balance_pairs[:1]:  # จำกัด 1 คู่เพื่อไม่ปิดมากเกินไป
                    if self.execute_pair_close(pair):
                        cleanup_actions.append(f"Balanced portfolio: +${pair['net_profit']:.2f}")
                        total_closed += pair['total_positions']
                        total_margin_freed += self.estimate_margin_freed(pair)
                        time.sleep(0.5)
            
            # 6. Phase 4: วางไม้ใหม่ตำแหน่งที่ดีกว่า (ถ้าจำเป็น)
            self.reposition_critical_orders()
            
            # 7. สรุปผลการ cleanup
            final_positions = self.get_remaining_positions(positions)
            final_health = self.get_portfolio_health_score(final_positions)
            
            cleanup_summary = {
                'success': True,
                'positions_closed': total_closed,
                'margin_freed': total_margin_freed,
                'health_improvement': final_health['score'] - health_data['score'],
                'initial_health': health_data['score'],
                'final_health': final_health['score'],
                'actions_taken': cleanup_actions,
                'final_position_count': len(final_positions)
            }
            
            print(f"✅ Cleanup Complete:")
            print(f"   • Positions closed: {total_closed}")
            print(f"   • Margin freed: ${total_margin_freed:.2f}")
            print(f"   • Health improved: {cleanup_summary['health_improvement']:.1f} points")
            print(f"   • Final health: {final_health['score']:.0f}/100")
            
            return cleanup_summary
            
        except Exception as e:
            print(f"❌ Portfolio cleanup error: {e}")
            return {'success': False, 'error': str(e)}
    
    def execute_pair_close(self, pair) -> bool:
        """ปิดคู่ positions อย่างปลอดภัย"""
        try:
            success_count = 0
            
            # ปิด losing positions ก่อน
            for pos in pair.get('losing_positions', []):
                if self.close_position_safely(pos):
                    success_count += 1
                    
            # ปิด profitable positions
            for pos in pair.get('profitable_positions', []):
                if self.close_position_safely(pos):
                    success_count += 1
            
            # ถือว่าสำเร็จถ้าปิดได้มากกว่าครึ่ง
            return success_count >= (pair['total_positions'] * 0.6)
            
        except Exception as e:
            print(f"❌ Pair close error: {e}")
            return False
    
    def close_position_safely(self, position) -> bool:
        """ปิด position เดี่ยวอย่างปลอดภัย พร้อม retry"""
        try:
            # ลองปิดด้วย fill mode ต่างๆ
            fill_modes = [
                ("IOC", mt5.ORDER_FILLING_IOC),
                ("FOK", mt5.ORDER_FILLING_FOK), 
                ("Return", mt5.ORDER_FILLING_RETURN)
            ]
            
            tick = mt5.symbol_info_tick(self.grid_system.gold_symbol)
            if not tick:
                return False
            
            # กำหนดพารามิเตอร์การปิด
            if position.direction == "BUY":
                trade_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                trade_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            
            # ลอง fill mode ต่างๆ
            for mode_name, fill_mode in fill_modes:
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.grid_system.gold_symbol,
                    "volume": position.lot_size,
                    "type": trade_type,
                    "position": position.position_id,
                    "price": price,
                    "deviation": 30,
                    "magic": self.grid_system.magic_number,
                    "comment": f"SmartCleanup_{mode_name}",
                    "type_filling": fill_mode
                }
                
                result = mt5.order_send(request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   ✅ Closed position {position.position_id} ({mode_name})")
                    return True
                elif result:
                    print(f"   ❌ {mode_name} failed: {result.retcode}")
            
            return False
            
        except Exception as e:
            print(f"❌ Safe close error: {e}")
            return False
    
    def estimate_margin_freed(self, pair) -> float:
        """ประเมิน margin ที่จะได้คืนจากการปิดคู่"""
        try:
            total_lots = 0
            for pos_list in [pair.get('losing_positions', []), pair.get('profitable_positions', [])]:
                for pos in pos_list:
                    total_lots += pos.lot_size
            
            # ประมาณการ margin per lot (สำหรับทองคำ)
            margin_per_lot = 1000  # ประมาณ $1000 per lot
            return total_lots * margin_per_lot
            
        except:
            return 0
    
    def get_closed_position_ids(self) -> Set[int]:
        """ดึง ID ของ positions ที่ปิดไปแล้วในการ cleanup นี้"""
        if not hasattr(self, '_cleanup_closed_ids'):
            self._cleanup_closed_ids = set()
        return self._cleanup_closed_ids
    
    def get_remaining_positions(self, original_positions):
        """ดึง positions ที่เหลือหลังการ cleanup"""
        try:
            # อัพเดท portfolio ใหม่
            portfolio = self.analyze_portfolio_positions()
            return portfolio.get('grid_positions', [])
        except:
            # fallback: กรอง positions ที่ปิดไปแล้ว
            closed_ids = self.get_closed_position_ids()
            return [p for p in original_positions if p.position_id not in closed_ids]
    
    def reposition_critical_orders(self):
        """วางไม้ใหม่ตำแหน่งที่ดีกว่า"""
        try:
            current_price = self.grid_system.get_current_price()
            
            # หาช่องว่างใกล้ราคาปัจจุบันที่ควรมีไม้
            gaps = self.find_critical_gaps_near_market(current_price)
            
            if gaps['buy_gaps']:
                for gap in gaps['buy_gaps'][:2]:  # วางสูงสุด 2 ไม้
                    if gap['gap_size'] > 200:  # ช่องว่างใหญ่กว่า 200 points
                        self.grid_system.place_smart_rebalance_order("BUY", gap['price'], self.grid_system.base_lot)
                        print(f"   🔧 Repositioned BUY @ ${gap['price']:.2f}")
            
            if gaps['sell_gaps']:
                for gap in gaps['sell_gaps'][:2]:  # วางสูงสุด 2 ไม้
                    if gap['gap_size'] > 200:  # ช่องว่างใหญ่กว่า 200 points
                        self.grid_system.place_smart_rebalance_order("SELL", gap['price'], self.grid_system.base_lot)
                        print(f"   🔧 Repositioned SELL @ ${gap['price']:.2f}")
                        
        except Exception as e:
            print(f"❌ Reposition error: {e}")
    
    
    def calculate_total_margin_used(self, positions) -> float:
        """คำนวณ margin ที่ใช้ทั้งหมด"""
        try:
            total_margin = 0
            for pos in positions:
                # ประมาณการ margin ต่อ lot สำหรับทองคำ
                margin_per_lot = 1000
                total_margin += pos.lot_size * margin_per_lot
            return total_margin
        except:
            return 0

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