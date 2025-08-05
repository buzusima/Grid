"""
AI Money Manager - Intelligent Capital Management System
ai_money_manager.py
Advanced money management with auto-adjustment, risk control, and performance optimization
"""

import math
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from survivability_engine import TradingMode

class RiskLevel(Enum):
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"
    CUSTOM = "CUSTOM"

class AccountTier(Enum):
    MICRO = "MICRO"      # $100 - $1,000
    MINI = "MINI"        # $1,000 - $5,000
    STANDARD = "STANDARD" # $5,000 - $25,000
    PREMIUM = "PREMIUM"   # $25,000 - $100,000
    VIP = "VIP"          # $100,000+

@dataclass
class MoneyManagementProfile:
    risk_level: RiskLevel
    max_risk_percentage: float
    base_lot_multiplier: float
    grid_spacing_factor: float
    safety_margin: float
    compound_factor: float
    stop_loss_percentage: float
    take_profit_percentage: float

@dataclass
class AccountMetrics:
    balance: float
    equity: float
    free_margin: float
    margin_level: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    max_drawdown: float
    win_rate: float
    profit_factor: float

class AIMoneyManager:
    def __init__(self, config: dict):
        self.config = config
        self.risk_profiles = self.initialize_risk_profiles()
        self.account_history = []
        self.performance_metrics = {}
        
        # AI learning parameters
        self.learning_rate = 0.1
        self.adaptation_threshold = 0.05
        self.performance_window = 30  # days
        
        # Safety limits
        self.max_daily_loss = config.get('max_daily_loss_percentage', 5.0)
        self.max_weekly_loss = config.get('max_weekly_loss_percentage', 15.0)
        self.max_monthly_loss = config.get('max_monthly_loss_percentage', 25.0)
        
        # Auto-adjustment settings
        self.auto_adjust_enabled = config.get('auto_adjust_enabled', True)
        self.adjustment_frequency = config.get('adjustment_frequency_hours', 24)
        self.last_adjustment = datetime.now()
        self.mode_adjustments = {
        TradingMode.SAFE: {
            'risk_multiplier': 0.7,      # ลดความเสี่ยง 30%
            'lot_adjustment': 0.8,       # ลดไม้ 20%
            'profit_target_adj': 0.8,    # เป้ากำไรต่ำลง 20%
            'compound_factor_adj': 0.8   # compound ช้าลง
        },
        TradingMode.BALANCED: {
            'risk_multiplier': 1.0,      # ปกติ
            'lot_adjustment': 1.0,       # ปกติ
            'profit_target_adj': 1.0,    # ปกติ
            'compound_factor_adj': 1.0   # ปกติ
        },
        TradingMode.AGGRESSIVE: {
            'risk_multiplier': 1.4,      # เพิ่มความเสี่ยง 40%
            'lot_adjustment': 1.3,       # เพิ่มไม้ 30%
            'profit_target_adj': 1.4,    # เป้ากำไรสูงขึ้น 40%
            'compound_factor_adj': 1.3   # compound เร็วขึ้น
        },
        TradingMode.TURBO: {
            'risk_multiplier': 1.8,      # เพิ่มความเสี่ยง 80%
            'lot_adjustment': 1.6,       # เพิ่มไม้ 60%
            'profit_target_adj': 1.8,    # เป้ากำไรสูงขึ้น 80%
            'compound_factor_adj': 1.6   # compound เร็วมาก
        }
    }
        
    def initialize_risk_profiles(self) -> Dict[RiskLevel, MoneyManagementProfile]:
        """Initialize predefined risk management profiles"""
        return {
            RiskLevel.CONSERVATIVE: MoneyManagementProfile(
                risk_level=RiskLevel.CONSERVATIVE,
                max_risk_percentage=30.0,    # Max 30% of account at risk
                base_lot_multiplier=0.5,     # Conservative lot sizing
                grid_spacing_factor=1.5,     # Wider grids
                safety_margin=0.7,           # Keep 70% as safety
                compound_factor=0.25,        # 25% of profits reinvested
                stop_loss_percentage=15.0,   # Stop at 15% account loss
                take_profit_percentage=10.0  # Take profit at 10% gain
            ),
            RiskLevel.MODERATE: MoneyManagementProfile(
                risk_level=RiskLevel.MODERATE,
                max_risk_percentage=50.0,
                base_lot_multiplier=0.75,
                grid_spacing_factor=1.0,
                safety_margin=0.6,
                compound_factor=0.5,
                stop_loss_percentage=25.0,
                take_profit_percentage=15.0
            ),
            RiskLevel.AGGRESSIVE: MoneyManagementProfile(
                risk_level=RiskLevel.AGGRESSIVE,
                max_risk_percentage=70.0,
                base_lot_multiplier=1.0,
                grid_spacing_factor=0.75,
                safety_margin=0.5,
                compound_factor=0.75,
                stop_loss_percentage=35.0,
                take_profit_percentage=20.0
            )
        }
        
    def determine_account_tier(self, balance: float) -> AccountTier:
        """Determine account tier based on balance"""
        if balance >= 100000:
            return AccountTier.VIP
        elif balance >= 25000:
            return AccountTier.PREMIUM
        elif balance >= 5000:
            return AccountTier.STANDARD
        elif balance >= 1000:
            return AccountTier.MINI
        else:
            return AccountTier.MICRO
            
    def calculate_optimal_money_management(self, 
                                        account_balance: float,
                                        current_equity: float,
                                        risk_level: RiskLevel = RiskLevel.MODERATE,
                                        trading_mode: TradingMode = TradingMode.BALANCED) -> Dict:
        """
        Calculate optimal money management parameters using AI with trading mode support
        """
        try:
            print(f"🧠 AI Money Manager calculating for ${account_balance:,.2f}...")
            print(f"🎯 Trading Mode: {trading_mode.value}")
            
            # Determine account tier and adjust parameters
            account_tier = self.determine_account_tier(account_balance)
            profile = self.risk_profiles[risk_level]
            
            # ⭐ เพิ่มส่วนนี้ - Get mode adjustments
            mode_adj = self.mode_adjustments[trading_mode]
            
            # Tier-based adjustments
            tier_adjustments = self.get_tier_adjustments(account_tier)
            
            # Calculate base parameters with mode adjustments
            max_risk_amount = account_balance * (profile.max_risk_percentage / 100) * mode_adj['risk_multiplier']
            usable_capital = account_balance * (1 - profile.safety_margin)
            
            # AI-enhanced lot sizing with mode
            base_lot = self.calculate_ai_lot_size_with_mode(
                usable_capital, 
                account_tier, 
                profile.base_lot_multiplier,
                mode_adj
            )
            
            # Dynamic grid parameters with mode
            grid_params = self.calculate_dynamic_grid_parameters_with_mode(
                usable_capital,
                base_lot,
                profile.grid_spacing_factor,
                tier_adjustments,
                mode_adj
            )
            
            # Risk management parameters with mode
            risk_params = self.calculate_risk_parameters_with_mode(
                account_balance,
                current_equity,
                profile,
                mode_adj
            )
            
            # Performance-based adjustments
            if self.auto_adjust_enabled:
                performance_adjustments = self.calculate_performance_adjustments()
                base_lot *= performance_adjustments.get('lot_multiplier', 1.0)
                grid_params['spacing'] *= performance_adjustments.get('spacing_multiplier', 1.0)
                
            # Compile results with mode information
            money_mgmt_result = {
                'trading_mode': trading_mode.value,  # ⭐ เพิ่ม
                'mode_adjustments': mode_adj,        # ⭐ เพิ่ม
                'account_tier': account_tier.value,
                'risk_level': risk_level.value,
                'account_balance': account_balance,
                'current_equity': current_equity,
                'max_risk_amount': max_risk_amount,
                'usable_capital': usable_capital,
                'safety_reserve': account_balance - usable_capital,
                'base_lot_size': round(base_lot, 3),
                'grid_spacing': int(grid_params['spacing']),
                'max_positions': grid_params['max_positions'],
                'position_sizing': self.calculate_position_sizing_ladder_with_mode(base_lot, mode_adj),
                'risk_parameters': risk_params,
                'stop_loss_level': account_balance * (1 - profile.stop_loss_percentage / 100),
                'take_profit_level': account_balance * (1 + profile.take_profit_percentage / 100 * mode_adj['profit_target_adj']),
                'daily_loss_limit': account_balance * (self.max_daily_loss / 100),
                'weekly_loss_limit': account_balance * (self.max_weekly_loss / 100),
                'monthly_loss_limit': account_balance * (self.max_monthly_loss / 100),
                'compound_settings': self.calculate_compound_settings_with_mode(account_balance, profile, mode_adj),
                'adjustment_recommendations': self.generate_adjustment_recommendations_with_mode(account_balance, current_equity, trading_mode),
                'ai_confidence': self.calculate_ai_confidence(),
                'timestamp': datetime.now().isoformat()
            }
            
            # Store for learning
            self.store_calculation(money_mgmt_result)
            
            print(f"✅ AI Money Management completed:")
            print(f"   🎯 Mode: {trading_mode.value}")
            print(f"   🏦 Tier: {account_tier.value}")
            print(f"   💰 Base Lot: {base_lot:.3f}")
            print(f"   📏 Grid Spacing: {grid_params['spacing']} points")
            print(f"   🛡️ Max Risk: ${max_risk_amount:,.2f}")
            print(f"   💪 Safety Reserve: ${account_balance - usable_capital:,.2f}")
            
            return money_mgmt_result
            
        except Exception as e:
            print(f"❌ AI Money Management error: {e}")
            raise

    def calculate_ai_lot_size_with_mode(self, usable_capital: float, tier: AccountTier, 
                                    base_multiplier: float, mode_adj: Dict) -> float:
        """AI-enhanced lot size calculation with trading mode adjustments"""
        
        # Base calculation (same as before)
        tier_adj = self.get_tier_adjustments(tier)
        
        # Account for gold point value ($1 per point for 1 lot)
        target_risk_per_level = 0.015  # 1.5% risk per level
        
        # Calculate lot size based on target risk
        avg_grid_spacing = 300
        max_affordable_lot = (usable_capital * target_risk_per_level) / avg_grid_spacing
        
        # Apply tier, profile, and mode multipliers
        calculated_lot = (max_affordable_lot * 
                        base_multiplier * 
                        tier_adj['lot_multiplier'] * 
                        mode_adj['lot_adjustment'])  # ⭐ เพิ่ม mode adjustment
        
        # Ensure minimum and maximum bounds
        min_lot = 0.001
        max_lot = min(10.0, usable_capital / 5000)  # Conservative maximum
        
        final_lot = max(min_lot, min(calculated_lot, max_lot))
        
        # Round to appropriate step
        if final_lot >= 1.0:
            return round(final_lot, 1)
        elif final_lot >= 0.1:
            return round(final_lot, 2)
        else:
            return round(final_lot, 3)
        
    def calculate_dynamic_grid_parameters_with_mode(self, usable_capital: float, base_lot: float, 
                                                spacing_factor: float, tier_adjustments: Dict, 
                                                mode_adj: Dict) -> Dict:
        """Calculate dynamic grid parameters with trading mode adjustments"""
        
        # Base spacing calculation (same as before)
        if usable_capital >= 50000:
            base_spacing = 200
        elif usable_capital >= 20000:
            base_spacing = 250
        elif usable_capital >= 10000:
            base_spacing = 300
        elif usable_capital >= 5000:
            base_spacing = 400
        else:
            base_spacing = 500
            
        # Apply factors including mode adjustments
        # Mode with higher risk = tighter spacing = more frequent trades
        mode_spacing_factor = 1.0
        if 'risk_multiplier' in mode_adj:
            # Higher risk = tighter spacing (inverse relationship)
            mode_spacing_factor = 1.0 / mode_adj['risk_multiplier']
        
        adjusted_spacing = (base_spacing * 
                        spacing_factor * 
                        tier_adjustments['spacing_multiplier'] * 
                        mode_spacing_factor)  # ⭐ เพิ่ม mode factor
        
        # Calculate maximum positions based on capital and spacing
        cost_per_position = base_lot * adjusted_spacing * 1.0
        max_affordable_positions = usable_capital / (cost_per_position * 2)
        
        # Adjust max positions by mode
        mode_max_positions = tier_adjustments['max_positions']
        if 'risk_multiplier' in mode_adj:
            mode_max_positions = int(mode_max_positions * mode_adj['risk_multiplier'])
        
        max_positions = min(
            int(max_affordable_positions),
            mode_max_positions,
            100  # Absolute maximum
        )
        
        return {
            'spacing': int(adjusted_spacing),
            'max_positions': max_positions,
            'total_grid_range': int(adjusted_spacing) * max_positions
        }

    def calculate_position_sizing_ladder_with_mode(self, base_lot: float, mode_adj: Dict) -> Dict:
        """Calculate position sizing ladder with mode adjustments"""
        ladder = {}
        
        # Base multipliers
        base_multipliers = [1.0, 1.0, 1.2, 1.2, 1.5, 1.5, 1.8, 1.8, 2.0, 2.0]
        
        # Adjust multipliers based on mode
        lot_adjustment = mode_adj['lot_adjustment']
        adjusted_multipliers = [mult * lot_adjustment for mult in base_multipliers]
        
        for i, mult in enumerate(adjusted_multipliers):
            level = i + 1
            lot_size = base_lot * mult
            ladder[f"level_{level}"] = {
                'lot_size': round(lot_size, 3),
                'multiplier': mult,
                'cumulative_lots': round(sum(base_lot * adjusted_multipliers[j] for j in range(i + 1)), 3),
                'mode_adjusted': True  # ⭐ เพิ่มข้อมูลว่าถูก adjust แล้ว
            }
            
        return ladder
    
    def generate_adjustment_recommendations_with_mode(self, balance: float, equity: float, 
                                                    trading_mode: TradingMode) -> List[str]:
        """Generate AI-powered adjustment recommendations with mode consideration"""
        recommendations = []
        
        # Balance vs Equity analysis
        drawdown_pct = ((balance - equity) / balance) * 100 if balance > 0 else 0
        
        # Mode-specific recommendations
        mode_thresholds = {
            TradingMode.SAFE: {'warning': 10, 'critical': 20},
            TradingMode.BALANCED: {'warning': 15, 'critical': 25},
            TradingMode.AGGRESSIVE: {'warning': 20, 'critical': 30},
            TradingMode.TURBO: {'warning': 25, 'critical': 35}
        }
        
        thresholds = mode_thresholds[trading_mode]
        
        if drawdown_pct > thresholds['critical']:
            recommendations.append(f"🚨 CRITICAL: Drawdown {drawdown_pct:.1f}% exceeds {trading_mode.value} mode limit")
            recommendations.append("Consider switching to SAFE mode or emergency stop")
        elif drawdown_pct > thresholds['warning']:
            recommendations.append(f"⚠️ WARNING: High drawdown {drawdown_pct:.1f}% for {trading_mode.value} mode")
            recommendations.append("Monitor closely or consider more conservative mode")
        elif drawdown_pct < 5:
            if trading_mode == TradingMode.SAFE:
                recommendations.append("Performance stable - consider BALANCED mode for faster growth")
            elif trading_mode == TradingMode.BALANCED:
                recommendations.append("Good performance - consider AGGRESSIVE mode if comfortable with risk")
            
        # Account growth recommendations with mode context
        if equity > balance * 1.1:
            recommendations.append(f"📈 Strong growth in {trading_mode.value} mode - consider compounding gains")
            if trading_mode in [TradingMode.SAFE, TradingMode.BALANCED]:
                recommendations.append("Account ready for higher risk mode if desired")
        elif equity < balance * 0.9:
            recommendations.append(f"📉 Account pressure in {trading_mode.value} mode")
            if trading_mode in [TradingMode.AGGRESSIVE, TradingMode.TURBO]:
                recommendations.append("Consider switching to more conservative mode")
                
        # Mode-specific advice
        mode_advice = {
            TradingMode.SAFE: "Focus on capital preservation and steady growth",
            TradingMode.BALANCED: "Monitor for opportunities to optimize risk/reward",
            TradingMode.AGGRESSIVE: "Watch for quick profit opportunities and manage risk actively",
            TradingMode.TURBO: "Requires constant monitoring and quick decision making"
        }
        
        recommendations.append(f"💡 {trading_mode.value} Mode Tip: {mode_advice[trading_mode]}")
        
        return recommendations

    def get_tier_adjustments(self, tier: AccountTier) -> Dict:
        """Get tier-specific adjustments"""
        adjustments = {
            AccountTier.MICRO: {
                'lot_multiplier': 0.3,
                'spacing_multiplier': 1.5,
                'safety_boost': 0.2,
                'max_positions': 20
            },
            AccountTier.MINI: {
                'lot_multiplier': 0.5,
                'spacing_multiplier': 1.2,
                'safety_boost': 0.15,
                'max_positions': 40
            },
            AccountTier.STANDARD: {
                'lot_multiplier': 0.75,
                'spacing_multiplier': 1.0,
                'safety_boost': 0.1,
                'max_positions': 60
            },
            AccountTier.PREMIUM: {
                'lot_multiplier': 1.0,
                'spacing_multiplier': 0.9,
                'safety_boost': 0.05,
                'max_positions': 80
            },
            AccountTier.VIP: {
                'lot_multiplier': 1.2,
                'spacing_multiplier': 0.8,
                'safety_boost': 0.0,
                'max_positions': 100
            }
        }
        return adjustments.get(tier, adjustments[AccountTier.STANDARD])
        
    def calculate_ai_lot_size(self, usable_capital: float, tier: AccountTier, base_multiplier: float) -> float:
        """AI-enhanced lot size calculation"""
        
        # Base calculation
        tier_adj = self.get_tier_adjustments(tier)
        
        # Account for gold point value ($1 per point for 1 lot)
        # Target: risk 1-2% per grid level
        target_risk_per_level = 0.015  # 1.5% risk per level
        
        # Calculate lot size based on target risk
        # Assuming average grid spacing of 300 points
        avg_grid_spacing = 300
        max_affordable_lot = (usable_capital * target_risk_per_level) / avg_grid_spacing
        
        # Apply tier and profile multipliers
        calculated_lot = max_affordable_lot * base_multiplier * tier_adj['lot_multiplier']
        
        # Ensure minimum and maximum bounds
        min_lot = 0.001
        max_lot = min(10.0, usable_capital / 5000)  # Conservative maximum
        
        final_lot = max(min_lot, min(calculated_lot, max_lot))
        
        # Round to appropriate step
        if final_lot >= 1.0:
            return round(final_lot, 1)
        elif final_lot >= 0.1:
            return round(final_lot, 2)
        else:
            return round(final_lot, 3)
            
    def calculate_dynamic_grid_parameters(self, usable_capital: float, base_lot: float, 
                                        spacing_factor: float, tier_adjustments: Dict) -> Dict:
        """Calculate dynamic grid parameters"""
        
        # Base spacing calculation
        if usable_capital >= 50000:
            base_spacing = 200
        elif usable_capital >= 20000:
            base_spacing = 250
        elif usable_capital >= 10000:
            base_spacing = 300
        elif usable_capital >= 5000:
            base_spacing = 400
        else:
            base_spacing = 500
            
        # Apply factors
        adjusted_spacing = base_spacing * spacing_factor * tier_adjustments['spacing_multiplier']
        
        # Calculate maximum positions based on capital and spacing
        cost_per_position = base_lot * adjusted_spacing * 1.0  # $1 per point for 1 lot
        max_affordable_positions = usable_capital / (cost_per_position * 2)  # 50% safety factor
        
        max_positions = min(
            int(max_affordable_positions),
            tier_adjustments['max_positions'],
            100  # Absolute maximum
        )
        
        return {
            'spacing': int(adjusted_spacing),
            'max_positions': max_positions,
            'total_grid_range': int(adjusted_spacing) * max_positions
        }
        
    def calculate_risk_parameters(self, balance: float, equity: float, profile: MoneyManagementProfile) -> Dict:
        """Calculate comprehensive risk parameters"""
        
        current_drawdown = ((balance - equity) / balance) * 100 if balance > 0 else 0
        
        return {
            'max_risk_percentage': profile.max_risk_percentage,
            'current_drawdown': round(current_drawdown, 2),
            'remaining_risk_capacity': profile.max_risk_percentage - current_drawdown,
            'stop_loss_triggered': current_drawdown >= profile.stop_loss_percentage,
            'daily_loss_limit': balance * (self.max_daily_loss / 100),
            'weekly_loss_limit': balance * (self.max_weekly_loss / 100),
            'monthly_loss_limit': balance * (self.max_monthly_loss / 100),
            'risk_level_status': self.assess_current_risk_level(current_drawdown, profile),
            'recommended_action': self.get_risk_recommendation(current_drawdown, profile)
        }
        
    def calculate_position_sizing_ladder(self, base_lot: float) -> Dict:
        """Calculate position sizing ladder for different grid levels"""
        ladder = {}
        
        # Martingale-style progression with safety limits
        multipliers = [1.0, 1.0, 1.2, 1.2, 1.5, 1.5, 1.8, 1.8, 2.0, 2.0]
        
        for i, mult in enumerate(multipliers):
            level = i + 1
            lot_size = base_lot * mult
            ladder[f"level_{level}"] = {
                'lot_size': round(lot_size, 3),
                'multiplier': mult,
                'cumulative_lots': round(sum(base_lot * multipliers[j] for j in range(i + 1)), 3)
            }
            
        return ladder
        
    def calculate_compound_settings(self, balance: float, profile: MoneyManagementProfile) -> Dict:
        """Calculate compounding settings"""
        
        # Determine compounding frequency based on account size
        if balance >= 50000:
            compound_frequency = "weekly"
            compound_threshold = 0.05  # 5% gain
        elif balance >= 10000:
            compound_frequency = "bi-weekly"
            compound_threshold = 0.08  # 8% gain
        else:
            compound_frequency = "monthly"
            compound_threshold = 0.10  # 10% gain
            
        return {
            'compound_enabled': True,
            'compound_factor': profile.compound_factor,
            'compound_frequency': compound_frequency,
            'compound_threshold': compound_threshold,
            'next_compound_target': balance * (1 + compound_threshold),
            'reinvestment_percentage': profile.compound_factor * 100
        }
        
    def assess_current_risk_level(self, current_drawdown: float, profile: MoneyManagementProfile) -> str:
        """Assess current risk level status"""
        if current_drawdown <= profile.max_risk_percentage * 0.3:
            return "LOW"
        elif current_drawdown <= profile.max_risk_percentage * 0.6:
            return "MODERATE"
        elif current_drawdown <= profile.max_risk_percentage * 0.8:
            return "HIGH"
        else:
            return "CRITICAL"
            
    def get_risk_recommendation(self, current_drawdown: float, profile: MoneyManagementProfile) -> str:
        """Get risk management recommendation"""
        if current_drawdown >= profile.stop_loss_percentage:
            return "STOP_TRADING"
        elif current_drawdown >= profile.max_risk_percentage * 0.8:
            return "REDUCE_EXPOSURE"
        elif current_drawdown >= profile.max_risk_percentage * 0.6:
            return "MONITOR_CLOSELY"
        elif current_drawdown <= profile.max_risk_percentage * 0.2:
            return "INCREASE_EXPOSURE"
        else:
            return "MAINTAIN_CURRENT"
            
    def calculate_performance_adjustments(self) -> Dict:
        """Calculate performance-based adjustments using AI learning"""
        
        if len(self.account_history) < 7:  # Need at least a week of data
            return {'lot_multiplier': 1.0, 'spacing_multiplier': 1.0}
            
        # Analyze recent performance
        recent_performance = self.analyze_recent_performance()
        
        adjustments = {
            'lot_multiplier': 1.0,
            'spacing_multiplier': 1.0
        }
        
        # Win rate adjustments
        win_rate = recent_performance.get('win_rate', 0.5)
        if win_rate > 0.7:
            adjustments['lot_multiplier'] *= 1.1  # Increase lot size for good performance
        elif win_rate < 0.3:
            adjustments['lot_multiplier'] *= 0.9  # Decrease lot size for poor performance
            
        # Drawdown adjustments
        max_drawdown = recent_performance.get('max_drawdown', 0)
        if max_drawdown > 20:
            adjustments['spacing_multiplier'] *= 1.2  # Wider spacing for high drawdown
        elif max_drawdown < 5:
            adjustments['spacing_multiplier'] *= 0.9  # Tighter spacing for low drawdown
            
        return adjustments
        
    def analyze_recent_performance(self) -> Dict:
        """Analyze recent trading performance"""
        if not self.account_history:
            return {}
            
        recent_data = self.account_history[-7:]  # Last 7 entries
        
        # Calculate metrics
        total_trades = len(recent_data)
        winning_trades = sum(1 for entry in recent_data if entry.get('pnl', 0) > 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(entry.get('pnl', 0) for entry in recent_data)
        max_drawdown = max(entry.get('drawdown', 0) for entry in recent_data)
        
        return {
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades
        }
        
    def generate_adjustment_recommendations(self, balance: float, equity: float) -> List[str]:
        """Generate AI-powered adjustment recommendations"""
        recommendations = []
        
        # Balance vs Equity analysis
        drawdown_pct = ((balance - equity) / balance) * 100 if balance > 0 else 0
        
        if drawdown_pct > 15:
            recommendations.append("Consider reducing position sizes due to high drawdown")
        elif drawdown_pct < 2:
            recommendations.append("Performance is good - consider gradual position size increase")
            
        # Account growth recommendations
        if equity > balance * 1.1:
            recommendations.append("Account showing strong growth - consider compounding gains")
        elif equity < balance * 0.9:
            recommendations.append("Account under pressure - focus on capital preservation")
            
        # Time-based recommendations
        current_hour = datetime.now().hour
        if 8 <= current_hour <= 17:  # Market hours
            recommendations.append("Active market hours - monitor positions closely")
        else:
            recommendations.append("Quiet market hours - consider tighter risk management")
            
        return recommendations
        
    def calculate_ai_confidence(self) -> float:
        """Calculate AI confidence level in recommendations"""
        base_confidence = 0.75
        
        # Adjust based on data availability
        if len(self.account_history) >= 30:
            data_confidence = 0.95
        elif len(self.account_history) >= 7:
            data_confidence = 0.85
        else:
            data_confidence = 0.6
            
        # Adjust based on market conditions (simplified)
        market_confidence = 0.8  # Would be dynamic in real implementation
        
        final_confidence = (base_confidence + data_confidence + market_confidence) / 3
        return round(final_confidence, 2)
        
    def store_calculation(self, calculation_result: Dict):
        """Store calculation for AI learning"""
        self.account_history.append({
            'timestamp': datetime.now(),
            'balance': calculation_result['account_balance'],
            'equity': calculation_result['current_equity'],
            'base_lot': calculation_result['base_lot_size'],
            'grid_spacing': calculation_result['grid_spacing'],
            'risk_level': calculation_result['risk_level']
        })
        
        # Keep only recent history (last 100 entries)
        if len(self.account_history) > 100:
            self.account_history = self.account_history[-100:]
            
    def should_auto_adjust(self) -> bool:
        """Check if auto-adjustment should be performed"""
        if not self.auto_adjust_enabled:
            return False
            
        time_since_last = datetime.now() - self.last_adjustment
        return time_since_last.total_seconds() >= (self.adjustment_frequency * 3600)
        
    def perform_auto_adjustment(self, current_balance: float, current_equity: float) -> Dict:
        """Perform automatic parameter adjustment"""
        if not self.should_auto_adjust():
            return {}
            
        print("🔄 Performing AI auto-adjustment...")
        
        # Analyze performance and adjust risk level if needed
        performance = self.analyze_recent_performance()
        
        current_risk_level = RiskLevel.MODERATE  # Default
        
        # Adjust risk level based on performance
        if performance.get('win_rate', 0.5) > 0.7 and performance.get('max_drawdown', 0) < 10:
            current_risk_level = RiskLevel.AGGRESSIVE
        elif performance.get('win_rate', 0.5) < 0.4 or performance.get('max_drawdown', 0) > 25:
            current_risk_level = RiskLevel.CONSERVATIVE
            
        # Recalculate with new risk level
        new_params = self.calculate_optimal_money_management(
            current_balance, current_equity, current_risk_level
        )
        
        self.last_adjustment = datetime.now()
        
        print(f"✅ Auto-adjustment completed - Risk Level: {current_risk_level.value}")
        
        return new_params
        
    def generate_money_management_report(self, params: Dict) -> str:
        """Generate comprehensive money management report"""
        
        report = f"""
💰 AI MONEY MANAGEMENT REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

🏦 ACCOUNT OVERVIEW:
   Account Tier: {params['account_tier']}
   Risk Level: {params['risk_level']}
   Balance: ${params['account_balance']:,.2f}
   Equity: ${params['current_equity']:,.2f}
   Usable Capital: ${params['usable_capital']:,.2f}
   Safety Reserve: ${params['safety_reserve']:,.2f}

📊 POSITION SIZING:
   Base Lot Size: {params['base_lot_size']:.3f}
   Grid Spacing: {params['grid_spacing']} points
   Maximum Positions: {params['max_positions']}
   
⚠️ RISK MANAGEMENT:
   Max Risk Amount: ${params['max_risk_amount']:,.2f}
   Daily Loss Limit: ${params['daily_loss_limit']:,.2f}
   Weekly Loss Limit: ${params['weekly_loss_limit']:,.2f}
   Monthly Loss Limit: ${params['monthly_loss_limit']:,.2f}
   Stop Loss Level: ${params['stop_loss_level']:,.2f}
   Take Profit Level: ${params['take_profit_level']:,.2f}

🔄 COMPOUNDING SETTINGS:
   Compound Factor: {params['compound_settings']['compound_factor']*100:.0f}%
   Frequency: {params['compound_settings']['compound_frequency']}
   Next Target: ${params['compound_settings']['next_compound_target']:,.2f}

🤖 AI ANALYSIS:
   Confidence Level: {params['ai_confidence']*100:.0f}%
   Risk Status: {params['risk_parameters']['risk_level_status']}
   Recommendation: {params['risk_parameters']['recommended_action']}

💡 ADJUSTMENTS:
"""
        
        for rec in params['adjustment_recommendations']:
            report += f"   • {rec}\n"
            
        report += f"""
{'='*60}
🏆 AI GOLD GRID TRADING SYSTEM - MONEY MANAGER
"""
        
        return report

# Test function
def test_ai_money_manager():
    """Test the AI Money Manager"""
    config = {
        'max_daily_loss_percentage': 5.0,
        'auto_adjust_enabled': True,
        'adjustment_frequency_hours': 24
    }
    
    manager = AIMoneyManager(config)
    
    test_accounts = [
        (1000, 950),
        (5000, 5200),
        (10000, 9800),
        (25000, 26500),
        (50000, 48000),
        (100000, 105000)
    ]
    
    print("🧪 Testing AI Money Manager...")
    print("="*80)
    
    for balance, equity in test_accounts:
        print(f"\n💰 Testing ${balance:,.2f} Account (Equity: ${equity:,.2f}):")
        print("-" * 60)
        
        try:
            result = manager.calculate_optimal_money_management(balance, equity)
            
            print(f"🏦 Tier: {result['account_tier']}")
            print(f"🎯 Base Lot: {result['base_lot_size']:.3f}")
            print(f"📏 Grid Spacing: {result['grid_spacing']} points")
            print(f"🛡️ Max Risk: ${result['max_risk_amount']:,.2f}")
            print(f"💪 Safety Reserve: ${result['safety_reserve']:,.2f}")
            print(f"⭐ AI Confidence: {result['ai_confidence']*100:.0f}%")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
    print("\n" + "="*80)
    print("✅ AI Money Manager Test Completed")

if __name__ == "__main__":
    test_ai_money_manager()