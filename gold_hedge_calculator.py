"""
Gold Hedge Calculator - Multi-Layer Hedge Protection System
gold_hedge_calculator.py
Advanced hedge calculation system for grid trading risk protection
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class HedgeType(Enum):
    PROTECTIVE = "PROTECTIVE"    # Basic protection hedge
    AGGRESSIVE = "AGGRESSIVE"    # Counter-trend hedge
    EMERGENCY = "EMERGENCY"      # Emergency stop-loss hedge
    PROFIT_LOCK = "PROFIT_LOCK"  # Profit protection hedge

class HedgeStatus(Enum):
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"

@dataclass
class HedgeLevel:
    trigger_points: float
    hedge_size: float
    hedge_type: HedgeType
    direction: str  # "BUY" or "SELL"
    priority: int
    status: HedgeStatus
    activation_price: Optional[float] = None
    close_price: Optional[float] = None
    pnl: float = 0.0

@dataclass
class GridPosition:
    level: int
    lot_size: float
    entry_price: float
    direction: str
    pnl: float
    is_active: bool

class GoldHedgeCalculator:
    def __init__(self, config: dict):
        self.config = config
        self.hedge_triggers = config.get('hedge_triggers', [0.15, 0.30, 0.45, 0.60])
        self.hedge_multipliers = config.get('hedge_multipliers', [0.5, 1.0, 1.5, 2.0])
        
        # Hedge calculation parameters
        self.hedge_effectiveness = 0.8  # 80% hedge effectiveness
        self.hedge_cost_factor = 0.02   # 2% cost for hedge execution
        self.min_hedge_size = 0.001     # Minimum hedge size
        self.max_hedge_ratio = 3.0      # Maximum hedge ratio to base position
        
        # Dynamic hedge parameters
        self.volatility_factor = 1.2    # Adjust for market volatility
        self.correlation_factor = 0.95  # Gold hedge correlation
        self.time_decay_factor = 0.98   # Time decay for hedge effectiveness
        
        # Current state tracking
        self.active_hedges = []
        self.hedge_history = []
        self.total_grid_exposure = 0.0
        self.current_drawdown = 0.0
        
    def calculate_hedge_plan(self, survivability_params: Dict) -> List[Tuple[float, float]]:
        """
        Calculate comprehensive hedge plan based on survivability parameters
        Returns list of (trigger_points, hedge_size) tuples
        """
        try:
            base_lot = survivability_params['base_lot']
            grid_spacing = survivability_params['grid_spacing']
            max_levels = survivability_params['max_levels']
            survivability = survivability_params['survivability']
            
            print(f"🛡️ Calculating hedge plan for {survivability:,.0f} points survivability...")
            
            hedge_plan = []
            
            # Calculate hedge levels based on survivability
            for i, trigger_ratio in enumerate(self.hedge_triggers):
                trigger_points = survivability * trigger_ratio
                
                # Calculate optimal hedge size for this level
                hedge_size = self.calculate_optimal_hedge_size(
                    base_lot, 
                    trigger_points, 
                    grid_spacing,
                    i + 1  # Hedge level
                )
                
                hedge_plan.append((trigger_points, hedge_size))
                
            # Add emergency hedge levels for extreme scenarios
            emergency_hedges = self.calculate_emergency_hedges(
                base_lot, survivability, max_levels
            )
            hedge_plan.extend(emergency_hedges)
            
            # Sort by trigger points
            hedge_plan.sort(key=lambda x: x[0])
            
            print(f"✅ Hedge plan calculated with {len(hedge_plan)} levels")
            for i, (trigger, size) in enumerate(hedge_plan):
                print(f"   Level {i+1}: @{trigger:,.0f} points → {size:.3f} lots")
                
            return hedge_plan
            
        except Exception as e:
            print(f"❌ Hedge calculation error: {e}")
            raise
            
    def calculate_optimal_hedge_size(self, base_lot: float, trigger_points: float, 
                                   grid_spacing: int, hedge_level: int) -> float:
        """Calculate optimal hedge size for specific trigger level"""
        
        # Estimate grid exposure at trigger point
        levels_activated = trigger_points / grid_spacing
        estimated_exposure = base_lot * levels_activated
        
        # Base hedge calculation using multipliers
        if hedge_level <= len(self.hedge_multipliers):
            base_multiplier = self.hedge_multipliers[hedge_level - 1]
        else:
            # For emergency levels, use progressive scaling
            base_multiplier = self.hedge_multipliers[-1] * (hedge_level - len(self.hedge_multipliers) + 1)
            
        # Calculate hedge size
        hedge_size = base_lot * base_multiplier
        
        # Adjust for market conditions
        hedge_size *= self.volatility_factor
        
        # Ensure hedge doesn't exceed exposure
        max_reasonable_hedge = estimated_exposure * 1.5  # 150% of exposure max
        hedge_size = min(hedge_size, max_reasonable_hedge)
        
        # Apply minimum and maximum limits
        hedge_size = max(hedge_size, self.min_hedge_size)
        hedge_size = min(hedge_size, base_lot * self.max_hedge_ratio)
        
        return round(hedge_size, 3)
        
    def calculate_emergency_hedges(self, base_lot: float, survivability: float, 
                                 max_levels: int) -> List[Tuple[float, float]]:
        """Calculate emergency hedge levels beyond normal plan"""
        
        emergency_hedges = []
        
        # Emergency hedge at 80% of survivability
        emergency_trigger_1 = survivability * 0.8
        emergency_size_1 = base_lot * 2.5
        emergency_hedges.append((emergency_trigger_1, emergency_size_1))
        
        # Critical hedge at 90% of survivability
        critical_trigger = survivability * 0.9
        critical_size = base_lot * 3.0
        emergency_hedges.append((critical_trigger, critical_size))
        
        # Final hedge at 95% of survivability
        final_trigger = survivability * 0.95
        final_size = base_lot * 4.0
        emergency_hedges.append((final_trigger, final_size))
        
        return emergency_hedges
        
    def create_detailed_hedge_levels(self, hedge_plan: List[Tuple[float, float]], 
                                   base_lot: float) -> List[HedgeLevel]:
        """Create detailed hedge level objects"""
        
        hedge_levels = []
        
        for i, (trigger_points, hedge_size) in enumerate(hedge_plan):
            # Determine hedge type based on level
            if i < 2:
                hedge_type = HedgeType.PROTECTIVE
            elif i < 4:
                hedge_type = HedgeType.AGGRESSIVE
            else:
                hedge_type = HedgeType.EMERGENCY
                
            # Create hedge level
            hedge_level = HedgeLevel(
                trigger_points=trigger_points,
                hedge_size=hedge_size,
                hedge_type=hedge_type,
                direction="OPPOSITE",  # Will be determined dynamically
                priority=i + 1,
                status=HedgeStatus.INACTIVE
            )
            
            hedge_levels.append(hedge_level)
            
        return hedge_levels
        
    def check_hedge_triggers(self, current_drawdown: float, grid_positions: List[GridPosition],
                           current_price: float) -> List[HedgeLevel]:
        """Check which hedge levels should be triggered"""
        
        self.current_drawdown = abs(current_drawdown)
        triggered_hedges = []
        
        # Update total grid exposure
        self.total_grid_exposure = sum(pos.lot_size for pos in grid_positions if pos.is_active)
        
        # Check each hedge level
        for hedge_level in self.active_hedges:
            if (hedge_level.status == HedgeStatus.INACTIVE and 
                self.current_drawdown >= hedge_level.trigger_points):
                
                # Determine hedge direction based on grid bias
                hedge_direction = self.determine_hedge_direction(grid_positions)
                hedge_level.direction = hedge_direction
                hedge_level.status = HedgeStatus.PENDING
                hedge_level.activation_price = current_price
                
                triggered_hedges.append(hedge_level)
                
        return triggered_hedges
        
    def determine_hedge_direction(self, grid_positions: List[GridPosition]) -> str:
        """Determine optimal hedge direction based on grid positions"""
        
        buy_exposure = sum(pos.lot_size for pos in grid_positions 
                          if pos.is_active and pos.direction == "BUY")
        sell_exposure = sum(pos.lot_size for pos in grid_positions 
                           if pos.is_active and pos.direction == "SELL")
        
        # Hedge opposite to dominant exposure
        if buy_exposure > sell_exposure:
            return "SELL"  # Hedge long positions with short
        else:
            return "BUY"   # Hedge short positions with long
            
    def calculate_hedge_effectiveness(self, hedge_level: HedgeLevel, 
                                    market_move: float) -> float:
        """Calculate hedge effectiveness for given market move"""
        
        base_effectiveness = self.hedge_effectiveness
        
        # Adjust for hedge type
        type_multipliers = {
            HedgeType.PROTECTIVE: 1.0,
            HedgeType.AGGRESSIVE: 1.1,
            HedgeType.EMERGENCY: 0.9,
            HedgeType.PROFIT_LOCK: 1.2
        }
        
        effectiveness = base_effectiveness * type_multipliers[hedge_level.hedge_type]
        
        # Adjust for correlation (gold hedges are highly correlated)
        effectiveness *= self.correlation_factor
        
        # Adjust for time decay
        if hedge_level.activation_price:
            time_active = 1  # Simplified - would calculate actual time
            effectiveness *= (self.time_decay_factor ** time_active)
            
        return min(effectiveness, 1.0)
        
    def calculate_hedge_cost(self, hedge_size: float, entry_price: float) -> float:
        """Calculate cost of executing hedge"""
        
        # Base cost calculation
        position_value = hedge_size * entry_price * 100  # Contract size
        base_cost = position_value * self.hedge_cost_factor
        
        # Add spread cost (typical gold spread)
        spread_cost = hedge_size * 30 * 0.01  # 30 points spread
        
        total_cost = base_cost + spread_cost
        return round(total_cost, 2)
        
    def optimize_hedge_timing(self, hedge_level: HedgeLevel, 
                            market_volatility: float) -> Dict:
        """Optimize hedge execution timing"""
        
        # Calculate optimal timing based on volatility
        if market_volatility > 2.0:  # High volatility
            timing_score = 0.9
            recommendation = "EXECUTE_IMMEDIATELY"
        elif market_volatility > 1.5:  # Medium volatility
            timing_score = 0.7
            recommendation = "EXECUTE_SOON"
        else:  # Low volatility
            timing_score = 0.5
            recommendation = "WAIT_FOR_CONFIRMATION"
            
        return {
            'timing_score': timing_score,
            'recommendation': recommendation,
            'optimal_delay_minutes': max(0, int((1 - timing_score) * 30)),
            'volatility_factor': market_volatility
        }
        
    def calculate_portfolio_hedge_ratio(self, grid_positions: List[GridPosition]) -> float:
        """Calculate overall portfolio hedge ratio"""
        
        total_long_exposure = sum(pos.lot_size for pos in grid_positions 
                                if pos.is_active and pos.direction == "BUY")
        total_short_exposure = sum(pos.lot_size for pos in grid_positions 
                                 if pos.is_active and pos.direction == "SELL")
        
        total_hedge_exposure = sum(hedge.hedge_size for hedge in self.active_hedges 
                                 if hedge.status == HedgeStatus.ACTIVE)
        
        total_exposure = total_long_exposure + total_short_exposure
        
        if total_exposure > 0:
            hedge_ratio = total_hedge_exposure / total_exposure
        else:
            hedge_ratio = 0.0
            
        return round(hedge_ratio, 3)
        
    def simulate_hedge_scenarios(self, hedge_plan: List[Tuple[float, float]], 
                               base_lot: float) -> Dict:
        """Simulate various market scenarios with hedge protection"""
        
        scenarios = {}
        
        # Test scenarios: market moves of different magnitudes
        test_moves = [2000, 5000, 10000, 15000, 20000, 25000]
        
        for move in test_moves:
            scenario_result = self.simulate_single_scenario(move, hedge_plan, base_lot)
            scenarios[f"{move}_points"] = scenario_result
            
        return scenarios
        
    def simulate_single_scenario(self, market_move: float, 
                               hedge_plan: List[Tuple[float, float]], 
                               base_lot: float) -> Dict:
        """Simulate single market scenario"""
        
        # Calculate grid losses without hedge
        levels_hit = market_move / 300  # Assuming 300 point spacing
        grid_lots = base_lot * levels_hit
        unhedged_loss = grid_lots * market_move
        
        # Calculate hedge protection
        total_hedge_protection = 0.0
        hedge_costs = 0.0
        
        for trigger_points, hedge_size in hedge_plan:
            if market_move >= trigger_points:
                # This hedge would be triggered
                hedge_protection = hedge_size * (market_move - trigger_points) * self.hedge_effectiveness
                hedge_cost = self.calculate_hedge_cost(hedge_size, 2000)  # Assume $2000 gold price
                
                total_hedge_protection += hedge_protection
                hedge_costs += hedge_cost
                
        net_protection = total_hedge_protection - hedge_costs
        final_loss = unhedged_loss - net_protection
        protection_ratio = net_protection / unhedged_loss if unhedged_loss > 0 else 0
        
        return {
            'market_move': market_move,
            'unhedged_loss': round(unhedged_loss, 2),
            'hedge_protection': round(total_hedge_protection, 2),
            'hedge_costs': round(hedge_costs, 2),
            'net_protection': round(net_protection, 2),
            'final_loss': round(final_loss, 2),
            'protection_ratio': round(protection_ratio * 100, 1)
        }
        
    def get_next_hedge_trigger(self, current_drawdown: float) -> Optional[float]:
        """Get next hedge trigger level"""
        
        for hedge_level in self.active_hedges:
            if (hedge_level.status == HedgeStatus.INACTIVE and 
                hedge_level.trigger_points > current_drawdown):
                return hedge_level.trigger_points
                
        return None
        
    def update_hedge_status(self, hedge_level: HedgeLevel, new_status: HedgeStatus, 
                          current_price: float = None):
        """Update hedge status and track performance"""
        
        old_status = hedge_level.status
        hedge_level.status = new_status
        
        if new_status == HedgeStatus.ACTIVE and current_price:
            hedge_level.activation_price = current_price
            
        elif new_status == HedgeStatus.CLOSED and current_price:
            hedge_level.close_price = current_price
            
            # Calculate hedge PnL
            if hedge_level.activation_price:
                price_diff = current_price - hedge_level.activation_price
                if hedge_level.direction == "SELL":
                    price_diff = -price_diff
                    
                hedge_level.pnl = hedge_level.hedge_size * price_diff * 100
                
        # Log status change
        print(f"🔄 Hedge Level {hedge_level.priority}: {old_status.value} → {new_status.value}")
        
    def generate_hedge_report(self, hedge_plan: List[Tuple[float, float]], 
                            survivability_params: Dict) -> str:
        """Generate comprehensive hedge protection report"""
        
        scenarios = self.simulate_hedge_scenarios(hedge_plan, survivability_params['base_lot'])
        
        report = f"""
🛡️ HEDGE PROTECTION ANALYSIS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

📊 HEDGE PLAN OVERVIEW:
   Base Lot Size: {survivability_params['base_lot']:.3f}
   Grid Spacing: {survivability_params['grid_spacing']} points
   Survivability: {survivability_params['survivability']:,.0f} points
   Total Hedge Levels: {len(hedge_plan)}

🛡️ HEDGE TRIGGER LEVELS:
"""
        
        for i, (trigger, size) in enumerate(hedge_plan):
            report += f"   Level {i+1}: @{trigger:,.0f} points → {size:.3f} lots\n"
            
        report += f"""
🧪 SCENARIO ANALYSIS:
"""
        
        for scenario_name, result in scenarios.items():
            move = result['market_move']
            protection = result['protection_ratio']
            final_loss = result['final_loss']
            
            report += f"   {move:,} points: {protection:.1f}% protection, Final Loss: ${final_loss:,.2f}\n"
            
        report += f"""
⚖️ HEDGE EFFECTIVENESS:
   Base Effectiveness: {self.hedge_effectiveness*100:.0f}%
   Correlation Factor: {self.correlation_factor*100:.0f}%
   Average Cost Factor: {self.hedge_cost_factor*100:.1f}%

💡 HEDGE RECOMMENDATIONS:
   1. Monitor grid exposure vs hedge ratio
   2. Adjust hedge timing based on volatility
   3. Consider profit-taking on successful hedges
   4. Review hedge effectiveness monthly

🚨 EMERGENCY PROTOCOLS:
   • Emergency hedge triggers at 80%+ of survivability
   • Critical hedge at 90%+ requires immediate attention
   • Final hedge at 95%+ indicates system stress

{'='*60}
🏆 AI GOLD GRID TRADING SYSTEM - HEDGE CALCULATOR
"""
        
        return report
        
    def get_real_time_hedge_status(self) -> Dict:
        """Get current hedge status for GUI display"""
        
        active_count = sum(1 for h in self.active_hedges if h.status == HedgeStatus.ACTIVE)
        pending_count = sum(1 for h in self.active_hedges if h.status == HedgeStatus.PENDING)
        
        total_hedge_exposure = sum(h.hedge_size for h in self.active_hedges 
                                 if h.status == HedgeStatus.ACTIVE)
        
        return {
            'total_hedge_levels': len(self.active_hedges),
            'active_hedges': active_count,
            'pending_hedges': pending_count,
            'total_hedge_exposure': round(total_hedge_exposure, 3),
            'current_drawdown': self.current_drawdown,
            'next_trigger': self.get_next_hedge_trigger(self.current_drawdown),
            'portfolio_hedge_ratio': self.calculate_portfolio_hedge_ratio([]),
            'last_update': datetime.now().isoformat()
        }

# Test function
def test_hedge_calculator():
    """Test the hedge calculator"""
    
    config = {
        'hedge_triggers': [0.15, 0.30, 0.45, 0.60],
        'hedge_multipliers': [0.5, 1.0, 1.5, 2.0]
    }
    
    calculator = GoldHedgeCalculator(config)
    
    # Test with sample survivability parameters
    survivability_params = {
        'base_lot': 0.05,
        'grid_spacing': 300,
        'max_levels': 67,
        'survivability': 20100
    }
    
    print("🧪 Testing Gold Hedge Calculator...")
    print("="*80)
    
    try:
        # Calculate hedge plan
        hedge_plan = calculator.calculate_hedge_plan(survivability_params)
        
        print(f"\n🛡️ Hedge Plan Summary:")
        print("-" * 40)
        for i, (trigger, size) in enumerate(hedge_plan):
            print(f"Level {i+1}: @{trigger:,.0f} points → {size:.3f} lots")
            
        # Test scenario simulation
        print(f"\n🧪 Scenario Analysis:")
        print("-" * 40)
        scenarios = calculator.simulate_hedge_scenarios(hedge_plan, survivability_params['base_lot'])
        
        for scenario_name, result in list(scenarios.items())[:3]:  # Show first 3
            print(f"{result['market_move']:,} points: {result['protection_ratio']:.1f}% protection")
            
        # Generate full report
        report = calculator.generate_hedge_report(hedge_plan, survivability_params)
        print(f"\n📋 Full Report Generated ({len(report)} characters)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    print("\n" + "="*80)
    print("✅ Hedge Calculator Test Completed")

if __name__ == "__main__":
    test_hedge_calculator()