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
        """แก้ไข method เดิม - เพิ่มการเช็คก่อนสร้าง orders"""
        try:
            # 1. วิเคราะห์ positions ทั้งหมด
            portfolio = self.analyze_portfolio_positions()
            if 'error' in portfolio or portfolio.get('total_positions', 0) == 0:
                print("🔄 No positions - creating initial grid")
                self.create_initial_grid_smart()  # ใช้ method ใหม่ที่เช็คดีกว่า
                return
                
            positions = portfolio.get('grid_positions', [])
            total_pnl = portfolio.get('total_pnl', 0)
            
            print(f"🧠 AI Portfolio: {len(positions)} positions, Total PnL: ${total_pnl:.2f}")
            
            # 2. หาคู่ที่ปิดได้ - ลด threshold จาก $3 เป็น $1.5
            profitable_pairs = self.find_profitable_pairs(positions)
            
            if profitable_pairs:
                print(f"💰 Found {len(profitable_pairs)} profitable pairs")
                self.execute_pair_closes(profitable_pairs)
                time.sleep(1)
                portfolio = self.analyze_portfolio_positions()
                positions = portfolio.get('grid_positions', [])
                total_pnl = portfolio.get('total_pnl', 0)
                print(f"🔄 After pair closing: {len(positions)} positions, PnL: ${total_pnl:.2f}")
            
            # 3. ✅ เช็คและ rebalance อย่างระมัดระวัง
            self.smart_rebalance_with_checks(positions)
            
        except Exception as e:
            print(f"❌ Smart profit management error: {e}")

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

    # แก้ไขใน smart_profit_manager.py - find_profitable_pairs() เดิม
    def find_profitable_pairs(self, positions):
        """แก้ไข method เดิม - ลด threshold"""
        try:
            profitable_pairs = []
            buy_positions = [p for p in positions if p.direction == "BUY"]
            sell_positions = [p for p in positions if p.direction == "SELL"]
            
            for buy_pos in buy_positions:
                for sell_pos in sell_positions:
                    net_pnl = buy_pos.pnl + sell_pos.pnl
                    
                    # ✅ แก้ไขจาก $3 เป็น $1.5 เพื่อเก็บกำไรไวขึ้น
                    if net_pnl > 1.5:  # เดิมเป็น 3.0
                        profitable_pairs.append({
                            'losing_position': buy_pos if buy_pos.pnl < sell_pos.pnl else sell_pos,
                            'profit_position': sell_pos if buy_pos.pnl < sell_pos.pnl else buy_pos,
                            'net_profit': net_pnl,
                            'priority': net_pnl + abs(min(buy_pos.pnl, sell_pos.pnl))
                        })
            
            profitable_pairs.sort(key=lambda x: x['priority'], reverse=True)
            
            # ✅ ไม่จำกัดจำนวนคู่ที่ปิด (เดิมจำกัด)
            return profitable_pairs  # เดิม return profitable_pairs[:2]
            
        except Exception as e:
            print(f"❌ Profitable pairs finding error: {e}")
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
        """ปิดคู่ positions ที่ได้กำไรสุทธิ"""
        
        for pair in pairs:
            try:
                losing_pos = pair['losing_position']
                profit_pos = pair['profit_position']
                net_profit = pair['net_profit']
                
                print(f"💰 Closing pair: Loss ${losing_pos.pnl:.2f} + Profit ${profit_pos.pnl:.2f} = +${net_profit:.2f}")
                
                # ปิด position แรก
                success1 = self.close_entire_position(losing_pos)
                if success1:
                    time.sleep(0.5)  # รอสักครู่
                    
                    # ปิด position ที่สอง
                    success2 = self.close_entire_position(profit_pos)
                    if success2:
                        print(f"   ✅ Pair closed successfully: +${net_profit:.2f}")
                        
                        # วางไม้ใหม่ทดแทน
                        self.place_replacement_orders_after_pair_close(losing_pos, profit_pos)
                    else:
                        print(f"   ⚠️ Second position failed to close")
                else:
                    print(f"   ❌ First position failed to close")
                    
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
        """ปิด position เดียว - ใช้ method ที่มีอยู่แล้ว"""
        try:
            return self.grid_system.close_position_by_id(position.position_id)
        except Exception as e:
            print(f"❌ Close single position error: {e}")
            return False

    def add_sell_orders_for_balance(self, current_price, count):
        """แก้ไข method เดิม - ใช้ spacing เล็กลง"""
        try:
            # ✅ แก้ไขจาก spacing ใหญ่เป็น 150 จุด
            tight_spacing = 150  # เดิมอาจเป็น 300+ จุด
            
            for i in range(min(count, 3)):  # เพิ่มสูงสุด 3 ตัว
                price = current_price + (tight_spacing * (i + 1) * 0.01)
                
                if not self.grid_system.has_nearby_order(price, "SELL"):
                    lot_size = self.grid_system.base_lot
                    success = self.grid_system.place_smart_rebalance_order("SELL", price, lot_size)
                    if success:
                        print(f"   ✅ Balance SELL: {lot_size:.3f} @ ${price:.2f}")
                        
        except Exception as e:
            print(f"❌ Balance SELL orders error: {e}")

    def add_buy_orders_for_balance(self, current_price, count):
        """แก้ไข method เดิม - ใช้ spacing เล็กลง"""
        try:
            # ✅ แก้ไขจาก spacing ใหญ่เป็น 150 จุด
            tight_spacing = 150  # เดิมอาจเป็น 300+ จุด
            
            for i in range(min(count, 3)):
                price = current_price - (tight_spacing * (i + 1) * 0.01)
                
                if not self.grid_system.has_nearby_order(price, "BUY"):
                    lot_size = self.grid_system.base_lot
                    success = self.grid_system.place_smart_rebalance_order("BUY", price, lot_size)
                    if success:
                        print(f"   ✅ Balance BUY: {lot_size:.3f} @ ${price:.2f}")
                        
        except Exception as e:
            print(f"❌ Balance BUY orders error: {e}")

    def rebalance_portfolio_if_needed(self, positions):
        """แก้ไข method เดิม - Rebalancing ไวขึ้น"""
        try:
            current_price = self.grid_system.get_current_price()
            buy_count = len([p for p in positions if p.direction == "BUY"])
            sell_count = len([p for p in positions if p.direction == "SELL"])
            
            print(f"📊 Portfolio: {buy_count} BUY, {sell_count} SELL @ ${current_price:.2f}")
            
            # ✅ แก้ไขจาก imbalance > 2 เป็น > 1 (ไวขึ้น)
            if abs(buy_count - sell_count) > 1:  # เดิมเป็น > 2
                imbalance = buy_count - sell_count
                
                if imbalance > 0:  # BUY เยอะ
                    print(f"⚖️ BUY heavy (+{imbalance}) - Adding SELL orders")
                    self.add_sell_orders_for_balance(current_price, abs(imbalance))
                else:  # SELL เยอะ
                    print(f"⚖️ SELL heavy ({imbalance}) - Adding BUY orders")  
                    self.add_buy_orders_for_balance(current_price, abs(imbalance))
            
            # ✅ เพิ่มการเช็คว่า positions น้อยเกินไป
            total_positions = len(positions)
            if total_positions < 6:  # น้อยกว่า 6 ตัว
                orders_needed = 6 - total_positions
                print(f"🎯 Too few positions ({total_positions}) - Adding {orders_needed} more")
                # เพิ่ม orders ทั้งสองด้าน
                pairs_needed = (orders_needed + 1) // 2
                for i in range(pairs_needed):
                    buy_price = current_price - (150 * (i + 1) * 0.01)  # 150 จุด
                    sell_price = current_price + (150 * (i + 1) * 0.01)
                    if not self.grid_system.has_nearby_order(buy_price, "BUY"):
                        self.grid_system.place_smart_rebalance_order("BUY", buy_price, self.grid_system.base_lot)
                    if not self.grid_system.has_nearby_order(sell_price, "SELL"):
                        self.grid_system.place_smart_rebalance_order("SELL", sell_price, self.grid_system.base_lot)
            
            # ✅ เติมช่องว่างถ้าใหญ่เกินไป
            self.check_and_fill_gaps(current_price)
                
        except Exception as e:
            print(f"❌ Portfolio rebalance error: {e}")

    def check_and_fill_gaps(self, current_price):
        """เช็คและเติมช่องว่างราคา - method ใหม่"""
        try:
            all_orders = list(self.grid_system.pending_orders.values())
            if not all_orders:
                return
                
            buy_orders = [o for o in all_orders if o.direction == "BUY"]
            sell_orders = [o for o in all_orders if o.direction == "SELL"]
            
            # เช็คช่องว่าง BUY ด้าน
            if buy_orders:
                nearest_buy = max(buy_orders, key=lambda x: x.price)
                buy_gap = (current_price - nearest_buy.price) / 0.01  # points
                
                if buy_gap > 300:  # ช่องว่างเกิน 300 จุด
                    fill_price = current_price - (150 * 0.01)  # วางที่ 150 จุด
                    if not self.grid_system.has_nearby_order(fill_price, "BUY"):
                        self.grid_system.place_smart_rebalance_order("BUY", fill_price, self.grid_system.base_lot)
                        print(f"🔧 Fill BUY gap: @ ${fill_price:.2f} (was {buy_gap:.0f} points)")
            
            # เช็คช่องว่าง SELL ด้าน
            if sell_orders:
                nearest_sell = min(sell_orders, key=lambda x: x.price)
                sell_gap = (nearest_sell.price - current_price) / 0.01  # points
                
                if sell_gap > 300:  # ช่องว่างเกิน 300 จุด
                    fill_price = current_price + (150 * 0.01)  # วางที่ 150 จุด
                    if not self.grid_system.has_nearby_order(fill_price, "SELL"):
                        self.grid_system.place_smart_rebalance_order("SELL", fill_price, self.grid_system.base_lot)
                        print(f"🔧 Fill SELL gap: @ ${fill_price:.2f} (was {sell_gap:.0f} points)")
                    
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