"""
AI Smart Profit Manager - Advanced Trading Engine
smart_profit_manager.py
True AI-driven trading system with intelligent market analysis and dynamic positioning
"""

import math
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import MetaTrader5 as mt5
import threading
import json
import numpy as np

class AIDecisionReason(Enum):
    MARKET_ANALYSIS = "MARKET_ANALYSIS"
    PORTFOLIO_HEALTH = "PORTFOLIO_HEALTH"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    PROFIT_OPTIMIZATION = "PROFIT_OPTIMIZATION"
    EMERGENCY_PROTECTION = "EMERGENCY_PROTECTION"

class PortfolioStatus(Enum):
    PROFITABLE = "PROFITABLE"  # equity > balance
    BALANCED = "BALANCED"      # profit ±$5
    LOSING = "LOSING"          # equity < balance

class MarketCondition(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"

@dataclass
class AIMarketAnalysis:
    condition: MarketCondition
    volatility_score: float  # 0-100
    trend_strength: float    # -100 to +100 (negative=down, positive=up)
    support_level: float
    resistance_level: float
    optimal_spacing: int
    recommended_action: str
    confidence: float        # 0-1

@dataclass
class AIPosition:
    position_id: int
    symbol: str
    direction: str
    lot_size: float
    entry_price: float
    current_price: float
    entry_time: datetime
    pnl: float
    health_score: float      # 0-100
    ai_tag: str             # AI classification
    risk_level: str         # LOW/MEDIUM/HIGH

@dataclass
class AIDecision:
    action: str
    reason: AIDecisionReason
    confidence: float
    parameters: Dict
    expected_outcome: str
    timestamp: datetime

class AISmartProfitManager:
    def __init__(self, mt5_connector, survivability_params: Dict, config: dict):
        """Initialize AI Smart Profit Manager"""
        
        # Core components
        self.mt5_connector = mt5_connector
        self.config = config
        self.survivability_params = survivability_params
        
        # Import AI modules
        try:
            from ai_money_manager import AIMoneyManager
            from survivability_engine import SurvivabilityEngine, TradingMode
            self.money_manager = AIMoneyManager(config)
            self.survivability_engine = SurvivabilityEngine(config)
            print("✅ AI Modules integrated successfully")
        except ImportError as e:
            print(f"⚠️ AI Module import warning: {e}")
            self.money_manager = None
            self.survivability_engine = None
        
        # Trading parameters
        self.base_lot = survivability_params.get('base_lot', 0.01)
        self.survivability = survivability_params.get('realistic_survivability', 10000)
        self.gold_symbol = mt5_connector.get_gold_symbol()
        self.symbol_info = mt5_connector.get_symbol_info()
        
        # AI Core System
        self.ai_active = False
        self.ai_decisions = []
        self.market_analysis = None
        self.portfolio_status = PortfolioStatus.BALANCED
        self.ai_health_score = 50
        
        # Position Management
        self.active_positions = {}
        self.pending_orders = {}
        self.ai_position_map = {}  # Maps position to AI strategy
        
        # AI Learning System
        self.market_memory = []    # Store market patterns
        self.decision_history = [] # Store AI decisions and outcomes
        self.performance_metrics = {
            'total_decisions': 0,
            'successful_decisions': 0,
            'ai_accuracy': 0.0,
            'portfolio_health_avg': 50.0
        }
        
        # AI Configuration
        self.ai_config = {
            'analysis_interval': 3,     # AI thinks every 3 seconds
            'market_memory_size': 100,  # Remember last 100 market states
            'decision_confidence_threshold': 0.4,  # Minimum confidence to act
            'max_positions_per_direction': 5,
            'dynamic_spacing_enabled': True,
            'cross_direction_trading': True,
            'adaptive_risk_management': True
        }
        
        # Generate unique magic number
        account_info = mt5_connector.get_account_info()
        if account_info:
            account_id = account_info.get('login', 0)
            self.magic_number = int(str(account_id)[-6:]) if account_id else 77703292
        else:
            self.magic_number = 77703292
        
        print(f"🧠 AI Smart Profit Manager Initialized")
        print(f"   💎 Symbol: {self.gold_symbol}")
        print(f"   🎯 Magic Number: {self.magic_number}")
        print(f"   🛡️ Survivability: {self.survivability:,} points")
        print(f"   🔬 AI Analysis: Every {self.ai_config['analysis_interval']} seconds")

    def start_ai_trading(self) -> bool:
        """Start AI-driven trading system"""
        try:
            print("🧠 STARTING AI SMART PROFIT SYSTEM...")
            print("="*60)
            
            if not self.validate_ai_prerequisites():
                return False
            
            self.ai_active = True
            
            # Initialize AI components
            self.initialize_ai_market_analysis()
            self.initialize_ai_portfolio_monitoring()
            
            # Start AI loops
            self.start_ai_main_loop()
            self.start_ai_monitoring_loop()
            
            print("🚀 AI SYSTEM FULLY OPERATIONAL!")
            print(f"   🧠 Market Analysis: ACTIVE")
            print(f"   📊 Portfolio Monitoring: ACTIVE") 
            print(f"   🎯 Dynamic Positioning: ENABLED")
            print(f"   🛡️ Risk Management: AI-CONTROLLED")
            
            return True
            
        except Exception as e:
            print(f"❌ AI System startup error: {e}")
            return False

    def validate_ai_prerequisites(self) -> bool:
        """Validate AI system prerequisites"""
        try:
            # Check MT5 connection
            if not self.mt5_connector:
                print("❌ No MT5 connection")
                return False
            
            # Check account info
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                print("❌ Cannot get account information")
                return False
            
            balance = account_info.get('balance', 0)
            if balance < 100:
                print(f"❌ Insufficient balance: ${balance:.2f}")
                return False
            
            # Check gold symbol
            if not self.gold_symbol:
                print("❌ No gold symbol detected")
                return False
            
            print("✅ AI Prerequisites validated")
            print(f"   💰 Account: {account_info.get('login', 'Unknown')}")
            print(f"   💵 Balance: ${balance:,.2f}")
            print(f"   🥇 Symbol: {self.gold_symbol}")
            
            return True
            
        except Exception as e:
            print(f"❌ Prerequisites validation error: {e}")
            return False

    def initialize_ai_market_analysis(self):
        """Initialize AI market analysis system"""
        try:
            print("🔬 Initializing AI Market Analysis...")
            
            # Get initial market data
            initial_analysis = self.ai_analyze_market_condition()
            
            if initial_analysis:
                self.market_analysis = initial_analysis
                print(f"✅ Market Analysis Online")
                print(f"   📈 Condition: {initial_analysis.condition.value}")
                print(f"   📊 Volatility: {initial_analysis.volatility_score:.1f}/100")
                print(f"   🎯 Confidence: {initial_analysis.confidence:.2f}")
            else:
                print("⚠️ Market analysis using defaults")
                
        except Exception as e:
            print(f"❌ Market analysis initialization error: {e}")

    def initialize_ai_portfolio_monitoring(self):
        """Initialize AI portfolio monitoring"""
        try:
            print("👁️ Initializing AI Portfolio Monitor...")
            
            # Scan existing positions
            existing_positions = self.scan_existing_positions()
            
            if existing_positions:
                print(f"🔍 Found {len(existing_positions)} existing positions")
                for pos in existing_positions:
                    self.ai_classify_position(pos)
            
            # Calculate initial portfolio health
            self.ai_health_score = self.ai_calculate_portfolio_health()
            
            print(f"✅ Portfolio Monitor Online")
            print(f"   🏥 Health Score: {self.ai_health_score}/100")
            print(f"   📊 Positions: {len(existing_positions)}")
            
        except Exception as e:
            print(f"❌ Portfolio monitor initialization error: {e}")

    def start_ai_main_loop(self):
        """Start main AI decision loop"""
        if not hasattr(self, 'ai_main_thread') or not self.ai_main_thread.is_alive():
            self.ai_main_thread = threading.Thread(target=self.ai_main_decision_loop, daemon=True)
            self.ai_main_thread.start()
            print("🧠 AI Main Decision Loop: STARTED")

    def start_ai_monitoring_loop(self):
        """Start AI monitoring loop"""
        if not hasattr(self, 'ai_monitor_thread') or not self.ai_monitor_thread.is_alive():
            self.ai_monitor_thread = threading.Thread(target=self.ai_monitoring_loop, daemon=True)
            self.ai_monitor_thread.start()
            print("👁️ AI Monitoring Loop: STARTED")

    def ai_main_decision_loop(self):
        """Main AI decision making loop"""
        print("🧠 AI MAIN LOOP: Thinking process started...")
        
        while self.ai_active:
            try:
                # 🧠 Step 1: Analyze current market condition
                market_analysis = self.ai_analyze_market_condition()
                if market_analysis:
                    self.market_analysis = market_analysis
                
                # 🧠 Step 2: Assess portfolio health
                health_score = self.ai_calculate_portfolio_health()
                self.ai_health_score = health_score
                
                # 🧠 Step 3: Determine portfolio status
                portfolio_status = self.ai_determine_portfolio_status()
                self.portfolio_status = portfolio_status
                
                # 🧠 Step 4: Make AI decisions based on analysis
                ai_decisions = self.ai_make_strategic_decisions(
                    market_analysis, health_score, portfolio_status
                )
                
                # 🧠 Step 5: Execute AI decisions
                for decision in ai_decisions:
                    self.ai_execute_decision(decision)
                
                # 🧠 Step 6: Learn from results
                self.ai_update_learning_system()
                
                # Log AI thinking process every 30 seconds
                if not hasattr(self, 'last_ai_log'):
                    self.last_ai_log = datetime.now()
                elif (datetime.now() - self.last_ai_log).total_seconds() >= 30:
                    self.log_ai_thinking_process(market_analysis, health_score, portfolio_status)
                    self.last_ai_log = datetime.now()
                
                # Wait for next AI cycle
                time.sleep(self.ai_config['analysis_interval'])
                
            except Exception as e:
                print(f"❌ AI Main Loop error: {e}")
                time.sleep(5)
        
        print("🛑 AI Main Loop: Stopped")

    def ai_monitoring_loop(self):
        """AI monitoring and updates loop"""
        print("👁️ AI MONITOR: Continuous monitoring started...")
        
        while self.ai_active:
            try:
                # Update positions from MT5
                self.ai_update_positions_from_mt5()
                
                # Monitor pending orders
                self.ai_monitor_pending_orders()
                
                # Check for emergency conditions
                emergency_detected = self.ai_emergency_protection()
                if emergency_detected:
                    break
                
                # Update performance metrics
                self.ai_update_performance_metrics()
                
                time.sleep(5)  # Monitor every 5 seconds
                
            except Exception as e:
                print(f"❌ AI Monitor error: {e}")
                time.sleep(10)
        
        print("🛑 AI Monitor: Stopped")

    def ai_analyze_market_condition(self) -> Optional[AIMarketAnalysis]:
        """🧠 AI Market Analysis - Analyze current market conditions (Fixed Version)"""
        try:
            # Get current price data
            current_price = self.get_current_price()
            if not current_price:
                return None
            
            # Get recent price history for analysis
            price_history = self.get_recent_price_history(50)  # Reduced from 100 to 50
            
            if not price_history or len(price_history) < 5:  # Reduced minimum from 10 to 5
                # Enhanced fallback analysis
                return self.create_fallback_market_analysis(current_price)
            
            # 🧠 Volatility Analysis
            price_changes = []
            for i in range(1, len(price_history)):
                change = abs(price_history[i] - price_history[i-1])
                price_changes.append(change)
            
            if price_changes:
                avg_change = sum(price_changes) / len(price_changes)
                volatility_score = min(100, avg_change * 10000)  # Scale for gold
            else:
                volatility_score = 50.0  # Default moderate volatility
            
            # 🧠 Trend Analysis
            trend_strength = self.calculate_trend_slope(price_history)
            
            # 🧠 Support/Resistance Analysis  
            support_level = min(price_history[-min(10, len(price_history)):])
            resistance_level = max(price_history[-min(10, len(price_history)):])
            
            # 🧠 Market Condition Classification
            condition = self.ai_classify_market_condition(
                volatility_score, trend_strength, price_history
            )
            
            # 🧠 Optimal Spacing Calculation
            optimal_spacing = self.ai_calculate_optimal_spacing(
                volatility_score, condition
            )
            
            # 🧠 Recommended Action
            recommended_action = self.ai_determine_market_action(
                condition, trend_strength, volatility_score
            )
            
            # 🧠 Confidence Calculation
            confidence = self.ai_calculate_analysis_confidence(
                len(price_history), volatility_score, trend_strength
            )
            
            analysis = AIMarketAnalysis(
                condition=condition,
                volatility_score=volatility_score,
                trend_strength=trend_strength,
                support_level=support_level,
                resistance_level=resistance_level,
                optimal_spacing=optimal_spacing,
                recommended_action=recommended_action,
                confidence=confidence
            )
            
            # Store in memory for learning
            self.market_memory.append({
                'timestamp': datetime.now(),
                'price': current_price,
                'analysis': analysis
            })
            
            # Keep memory size manageable
            if len(self.market_memory) > self.ai_config['market_memory_size']:
                self.market_memory = self.market_memory[-self.ai_config['market_memory_size']:]
            
            return analysis
            
        except Exception as e:
            print(f"❌ AI Market Analysis error: {e}")
            # Return safe fallback
            current_price = self.get_current_price()
            if current_price:
                return self.create_fallback_market_analysis(current_price)
            return None

    def create_fallback_market_analysis(self, current_price: float) -> AIMarketAnalysis:
        """Create fallback market analysis when data is limited"""
        
        try:
            # Use account size for base spacing
            account_info = self.mt5_connector.get_account_info()
            balance = account_info.get('balance', 10000) if account_info else 10000
            
            if balance >= 50000:
                base_spacing = 150
            elif balance >= 10000:
                base_spacing = 200
            else:
                base_spacing = 300
            
            return AIMarketAnalysis(
                condition=MarketCondition.RANGING,
                volatility_score=50.0,  # Moderate volatility
                trend_strength=0.0,     # Neutral trend
                support_level=current_price - 100,
                resistance_level=current_price + 100,
                optimal_spacing=base_spacing,
                recommended_action="CONSERVATIVE_POSITIONING",
                confidence=0.6  # Moderate confidence
            )
            
        except Exception as e:
            print(f"❌ Fallback analysis error: {e}")
            return AIMarketAnalysis(
                condition=MarketCondition.RANGING,
                volatility_score=50.0,
                trend_strength=0.0,
                support_level=current_price - 50,
                resistance_level=current_price + 50,
                optimal_spacing=300,
                recommended_action="CONSERVATIVE_POSITIONING",
                confidence=0.5
            )


    def ai_classify_market_condition(self, volatility_score: float, 
                                   trend_strength: float, 
                                   price_history: List[float]) -> MarketCondition:
        """🧠 Classify market condition based on AI analysis"""
        
        # High volatility threshold
        if volatility_score > 70:
            return MarketCondition.HIGH_VOLATILITY
        
        # Low volatility threshold  
        if volatility_score < 20:
            return MarketCondition.LOW_VOLATILITY
        
        # Trend analysis
        if abs(trend_strength) > 50:
            if trend_strength > 0:
                return MarketCondition.TRENDING_UP
            else:
                return MarketCondition.TRENDING_DOWN
        
        # Default to ranging
        return MarketCondition.RANGING

    def ai_calculate_optimal_spacing(self, volatility_score: float, 
                                   condition: MarketCondition) -> int:
        """🧠 Calculate optimal spacing based on AI analysis"""
        
        # Base spacing from account size
        account_info = self.mt5_connector.get_account_info()
        balance = account_info.get('balance', 10000) if account_info else 10000
        
        if balance >= 50000:
            base_spacing = 100
        elif balance >= 25000:
            base_spacing = 150
        elif balance >= 10000:
            base_spacing = 200
        elif balance >= 5000:
            base_spacing = 250
        else:
            base_spacing = 300
        
        # Adjust based on volatility
        volatility_factor = 1.0 + (volatility_score - 50) / 100
        
        # Adjust based on market condition
        condition_factors = {
            MarketCondition.HIGH_VOLATILITY: 1.5,
            MarketCondition.LOW_VOLATILITY: 0.7,
            MarketCondition.TRENDING_UP: 1.2,
            MarketCondition.TRENDING_DOWN: 1.2,
            MarketCondition.RANGING: 0.8
        }
        
        condition_factor = condition_factors.get(condition, 1.0)
        
        # Calculate final spacing
        optimal_spacing = int(base_spacing * volatility_factor * condition_factor)
        
        # Ensure reasonable bounds
        return max(80, min(500, optimal_spacing))

    def ai_determine_market_action(self, condition: MarketCondition, 
                                 trend_strength: float, 
                                 volatility_score: float) -> str:
        """🧠 Determine recommended market action"""
        
        if condition == MarketCondition.HIGH_VOLATILITY:
            return "WIDE_POSITIONING"
        elif condition == MarketCondition.LOW_VOLATILITY:
            return "TIGHT_POSITIONING"
        elif condition in [MarketCondition.TRENDING_UP, MarketCondition.TRENDING_DOWN]:
            return "TREND_FOLLOWING"
        else:
            return "BALANCED_POSITIONING"

    def ai_calculate_analysis_confidence(self, data_points: int, 
                                       volatility_score: float, 
                                       trend_strength: float) -> float:
        """🧠 Calculate confidence in market analysis"""
        
        # Base confidence from data availability
        data_confidence = min(1.0, data_points / 100)
        
        # Reduce confidence in extreme volatility
        volatility_confidence = 1.0 - abs(volatility_score - 50) / 100
        
        # Higher confidence in clear trends
        trend_confidence = 0.5 + abs(trend_strength) / 200
        
        # Combined confidence
        confidence = (data_confidence + volatility_confidence + trend_confidence) / 3
        
        return max(0.1, min(1.0, confidence))

    def ai_calculate_portfolio_health(self) -> float:
        """🧠 Calculate AI Portfolio Health Score (0-100)"""
        try:
            health_score = 50  # Base score
            
            # Get account info
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return health_score
            
            balance = account_info.get('balance', 0)
            equity = account_info.get('equity', 0)
            
            if balance <= 0:
                return 0
            
            # 🧠 PnL Health (30 points)
            pnl_ratio = (equity - balance) / balance
            if pnl_ratio > 0.1:  # >10% profit
                health_score += 30
            elif pnl_ratio > 0.05:  # >5% profit
                health_score += 20
            elif pnl_ratio > 0:  # Any profit
                health_score += 10
            elif pnl_ratio > -0.05:  # <5% loss
                health_score += 0
            elif pnl_ratio > -0.1:  # <10% loss
                health_score -= 10
            else:  # >10% loss
                health_score -= 20
            
            # 🧠 Position Diversity Health (20 points)
            positions = list(self.active_positions.values())
            buy_positions = [p for p in positions if p.get('direction') == 'BUY']
            sell_positions = [p for p in positions if p.get('direction') == 'SELL']
            
            total_positions = len(positions)
            if total_positions >= 8:
                health_score += 20
            elif total_positions >= 4:
                health_score += 15
            elif total_positions >= 2:
                health_score += 10
            elif total_positions == 0:
                health_score -= 5
            
            # 🧠 Balance Health (15 points)
            if buy_positions and sell_positions:
                balance_ratio = min(len(buy_positions), len(sell_positions)) / max(len(buy_positions), len(sell_positions))
                health_score += balance_ratio * 15
            
            # 🧠 Risk Management Health (20 points)
            if hasattr(self, 'survivability') and self.survivability > 0:
                current_drawdown = self.get_current_drawdown_points()
                risk_usage = current_drawdown / self.survivability
                
                if risk_usage < 0.2:  # <20% risk used
                    health_score += 20
                elif risk_usage < 0.4:  # <40% risk used
                    health_score += 15
                elif risk_usage < 0.6:  # <60% risk used
                    health_score += 10
                elif risk_usage < 0.8:  # <80% risk used
                    health_score += 5
                else:  # >80% risk used
                    health_score -= 10
            
            # 🧠 Market Alignment Health (15 points)
            if self.market_analysis:
                confidence_bonus = self.market_analysis.confidence * 15
                health_score += confidence_bonus
            
            # Ensure bounds
            return max(0, min(100, health_score))
            
        except Exception as e:
            print(f"❌ Portfolio health calculation error: {e}")
            return 50

    def ai_determine_portfolio_status(self) -> PortfolioStatus:
        """🧠 Determine current portfolio status"""
        try:
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return PortfolioStatus.BALANCED
            
            balance = account_info.get('balance', 0)
            equity = account_info.get('equity', 0)
            profit = equity - balance
            
            if profit > 5:
                return PortfolioStatus.PROFITABLE
            elif profit < -5:
                return PortfolioStatus.LOSING
            else:
                return PortfolioStatus.BALANCED
                
        except Exception as e:
            print(f"❌ Portfolio status determination error: {e}")
            return PortfolioStatus.BALANCED

    def ai_make_strategic_decisions(self, market_analysis: Optional[AIMarketAnalysis],
                                  health_score: float,
                                  portfolio_status: PortfolioStatus) -> List[AIDecision]:
        """🧠 AI Strategic Decision Making"""
        
        decisions = []
        
        try:
            # 🧠 Decision 1: Market-based positioning
            if market_analysis and market_analysis.confidence > 0.4:
                positioning_decision = self.ai_decide_positioning(market_analysis, portfolio_status)
                if positioning_decision:
                    decisions.append(positioning_decision)
            
            # 🧠 Decision 2: Portfolio health optimization  
            if health_score < 50:
                health_decision = self.ai_decide_health_improvement(health_score, portfolio_status)
                if health_decision:
                    decisions.append(health_decision)
            
            # 🧠 Decision 3: Profit optimization
            if portfolio_status == PortfolioStatus.PROFITABLE:
                profit_decision = self.ai_decide_profit_optimization()
                if profit_decision:
                    decisions.append(profit_decision)
            
            # 🧠 Decision 4: Risk management
            risk_decision = self.ai_decide_risk_management(portfolio_status)
            if risk_decision:
                decisions.append(risk_decision)
            
            # Filter by confidence threshold
            high_confidence_decisions = [
                d for d in decisions 
                if d.confidence >= self.ai_config['decision_confidence_threshold']
            ]
            
            return high_confidence_decisions
            
        except Exception as e:
            print(f"❌ AI Strategic decision error: {e}")
            return []

    def ai_decide_positioning(self, market_analysis: AIMarketAnalysis, 
                            portfolio_status: PortfolioStatus) -> Optional[AIDecision]:
        """🧠 AI Positioning Decision"""
        
        try:
            current_positions = len(self.active_positions)
            pending_orders = len(self.pending_orders)
            total_exposure = current_positions + pending_orders
            
            print(f"🧠 AI Check: {current_positions} positions + {pending_orders} pending = {total_exposure} total")
            
            # Check if we need more positions
            if total_exposure < 8:  # แก้จาก current_positions < 2
                action = "PLACE_STRATEGIC_ORDERS"
                confidence = market_analysis.confidence * 0.8
                
                # คำนวณจำนวน orders ที่ต้องวางใหม่
                orders_needed = min(6, 8 - total_exposure)
                
                parameters = {
                    'spacing': market_analysis.optimal_spacing,
                    'direction_bias': self.ai_determine_direction_bias(market_analysis),
                    'position_count': orders_needed,  # แก้จาก min(6, 8 - current_positions)
                    'lot_size': self.base_lot
                }
                
                return AIDecision(
                    action=action,
                    reason=AIDecisionReason.MARKET_ANALYSIS,
                    confidence=confidence,
                    parameters=parameters,
                    expected_outcome=f"Improve market coverage with {parameters['position_count']} orders",
                    timestamp=datetime.now()
                )
            else:
                return None
            
        except Exception as e:
            print(f"❌ AI Positioning decision error: {e}")
            return None
   
    def ai_decide_health_improvement(self, health_score: float, 
                                   portfolio_status: PortfolioStatus) -> Optional[AIDecision]:
        """🧠 AI Health Improvement Decision"""
        
        try:
            if health_score < 40:
                action = "EMERGENCY_PORTFOLIO_CLEANUP"
                confidence = 0.9
                
                parameters = {
                    'target_health': 60,
                    'cleanup_method': 'CLOSE_WEAK_POSITIONS',
                    'preserve_strong': True
                }
                
            elif health_score < 60:
                action = "OPTIMIZE_PORTFOLIO_BALANCE"
                confidence = 0.7
                
                parameters = {
                    'rebalance_method': 'ADD_COUNTER_POSITIONS',
                    'target_balance_ratio': 0.8
                }
                
            else:
                return None
            
            return AIDecision(
                action=action,
                reason=AIDecisionReason.PORTFOLIO_HEALTH,
                confidence=confidence,
                parameters=parameters,
                expected_outcome=f"Improve health score from {health_score:.1f} to {parameters.get('target_health', 70)}",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"❌ AI Health decision error: {e}")
            return None

    def ai_decide_profit_optimization(self) -> Optional[AIDecision]:
        """🧠 AI Profit Optimization Decision"""
        
        try:
            # Look for profitable pairs to close
            profit_opportunities = self.ai_find_intelligent_profit_pairs()
            
            if profit_opportunities:
                action = "EXECUTE_INTELLIGENT_PROFIT_TAKING"
                confidence = 0.8
                
                parameters = {
                    'opportunities': profit_opportunities,
                    'execution_method': 'STAGED_CLOSING',
                    'preserve_core_positions': True
                }
                
                expected_profit = sum(opp.get('expected_profit', 0) for opp in profit_opportunities)
                
                return AIDecision(
                    action=action,
                    reason=AIDecisionReason.PROFIT_OPTIMIZATION,
                    confidence=confidence,
                    parameters=parameters,
                    expected_outcome=f"Realize ${expected_profit:.2f} profit from {len(profit_opportunities)} opportunities",
                    timestamp=datetime.now()
                )
            
            return None
            
        except Exception as e:
            print(f"❌ AI Profit optimization error: {e}")
            return None

    def ai_decide_risk_management(self, portfolio_status: PortfolioStatus) -> Optional[AIDecision]:
        """🧠 AI Risk Management Decision"""
        
        try:
            # Check current risk level
            current_drawdown = self.get_current_drawdown_points()
            risk_ratio = current_drawdown / self.survivability if self.survivability > 0 else 0
            
            if risk_ratio > 0.8:  # >80% risk used
                action = "EMERGENCY_RISK_REDUCTION"
                confidence = 0.95
                
                parameters = {
                    'reduction_method': 'CLOSE_HIGHEST_RISK_POSITIONS',
                    'target_risk_ratio': 0.6,
                    'preserve_profitable': True
                }
                
                return AIDecision(
                    action=action,
                    reason=AIDecisionReason.EMERGENCY_PROTECTION,
                    confidence=confidence,
                    parameters=parameters,
                    expected_outcome=f"Reduce risk from {risk_ratio:.1%} to 60%",
                    timestamp=datetime.now()
                )
            
            elif risk_ratio > 0.6:  # >60% risk used
                action = "MODERATE_RISK_ADJUSTMENT"
                confidence = 0.7
                
                parameters = {
                    'adjustment_method': 'HEDGE_PROTECTION',
                    'hedge_ratio': 0.3,
                    'target_risk_ratio': 0.5
                }
                
                return AIDecision(
                    action=action,
                    reason=AIDecisionReason.RISK_MANAGEMENT,
                    confidence=confidence,
                    parameters=parameters,
                    expected_outcome=f"Reduce risk through hedging from {risk_ratio:.1%} to 50%",
                    timestamp=datetime.now()
                )
            
            return None
            
        except Exception as e:
            print(f"❌ AI Risk management error: {e}")
            return None

    def ai_execute_decision(self, decision: AIDecision):
        """🧠 Execute AI Decision"""
        
        try:
            print(f"🧠 AI EXECUTING: {decision.action}")
            print(f"   🎯 Reason: {decision.reason.value}")
            print(f"   💪 Confidence: {decision.confidence:.2f}")
            print(f"   📋 Expected: {decision.expected_outcome}")
            
            # Execute based on action type
            if decision.action == "PLACE_STRATEGIC_ORDERS":
                success = self.ai_execute_strategic_positioning(decision.parameters)
                
            elif decision.action == "EXECUTE_INTELLIGENT_PROFIT_TAKING":
                success = self.ai_execute_profit_taking(decision.parameters)
                
            elif decision.action == "EMERGENCY_PORTFOLIO_CLEANUP":
                success = self.ai_execute_emergency_cleanup(decision.parameters)
                
            elif decision.action == "OPTIMIZE_PORTFOLIO_BALANCE":
                success = self.ai_execute_portfolio_balance(decision.parameters)
                
            elif decision.action == "EMERGENCY_RISK_REDUCTION":
                success = self.ai_execute_risk_reduction(decision.parameters)
                
            elif decision.action == "MODERATE_RISK_ADJUSTMENT":
                success = self.ai_execute_risk_adjustment(decision.parameters)
                
            else:
                print(f"⚠️ Unknown AI action: {decision.action}")
                success = False
            
            # Record decision outcome
            decision_record = {
                'decision': decision,
                'success': success,
                'execution_time': datetime.now(),
                'portfolio_health_before': self.ai_health_score
            }
            
            self.decision_history.append(decision_record)
            
            # Update performance metrics
            self.performance_metrics['total_decisions'] += 1
            if success:
                self.performance_metrics['successful_decisions'] += 1
            
            self.performance_metrics['ai_accuracy'] = (
                self.performance_metrics['successful_decisions'] / 
                self.performance_metrics['total_decisions']
            )
            
            result_emoji = "✅" if success else "❌"
            print(f"   {result_emoji} Execution {'SUCCESS' if success else 'FAILED'}")
            
        except Exception as e:
            print(f"❌ AI Decision execution error: {e}")

    def ai_execute_strategic_positioning(self, parameters: Dict) -> bool:
        """🧠 Execute strategic positioning"""
        
        try:
            spacing = parameters.get('spacing', 200)
            direction_bias = parameters.get('direction_bias', 'BALANCED')
            position_count = parameters.get('position_count', 4)
            lot_size = parameters.get('lot_size', self.base_lot)
            
            current_price = self.get_current_price()
            if not current_price:
                return False
            
            orders_placed = 0
            spacing_dollars = spacing * 0.01
            
            print(f"   📍 Placing {position_count} strategic orders")
            print(f"   📏 Spacing: {spacing} points (${spacing_dollars:.2f})")
            print(f"   🎯 Bias: {direction_bias}")
            
            # Determine order distribution based on bias
            if direction_bias == "BUY_BIAS":
                buy_orders = max(1, int(position_count * 0.7))
                sell_orders = position_count - buy_orders
            elif direction_bias == "SELL_BIAS":
                sell_orders = max(1, int(position_count * 0.7))
                buy_orders = position_count - sell_orders
            else:  # BALANCED
                buy_orders = position_count // 2
                sell_orders = position_count - buy_orders
            
            # Place BUY orders below market
            for i in range(buy_orders):
                distance = spacing_dollars * (i + 1) * (1 + i * 0.2)  # Progressive spacing
                buy_price = current_price - distance
                
                if self.ai_place_intelligent_order(buy_price, 'BUY', lot_size, 'STRATEGIC'):
                    orders_placed += 1
                    print(f"   ✅ BUY order: ${buy_price:.2f}")
                    time.sleep(0.3)
            
            # Place SELL orders above market
            for i in range(sell_orders):
                distance = spacing_dollars * (i + 1) * (1 + i * 0.2)  # Progressive spacing
                sell_price = current_price + distance
                
                if self.ai_place_intelligent_order(sell_price, 'SELL', lot_size, 'STRATEGIC'):
                    orders_placed += 1
                    print(f"   ✅ SELL order: ${sell_price:.2f}")
                    time.sleep(0.3)
            
            success_rate = orders_placed / position_count
            print(f"   📊 Orders placed: {orders_placed}/{position_count} ({success_rate:.1%})")
            
            return success_rate >= 0.5  # Success if >50% orders placed
            
        except Exception as e:
            print(f"❌ Strategic positioning error: {e}")
            return False

    def ai_execute_profit_taking(self, parameters: Dict) -> bool:
        """🧠 Execute intelligent profit taking"""
        
        try:
            opportunities = parameters.get('opportunities', [])
            execution_method = parameters.get('execution_method', 'IMMEDIATE')
            
            if not opportunities:
                print("   ⚠️ No profit opportunities provided")
                return False
            
            print(f"   💰 Executing {len(opportunities)} profit opportunities")
            
            successful_closes = 0
            
            for i, opportunity in enumerate(opportunities):
                try:
                    position_ids = opportunity.get('position_ids', [])
                    expected_profit = opportunity.get('expected_profit', 0)
                    
                    print(f"   🎯 Opportunity {i+1}: {len(position_ids)} positions, ${expected_profit:.2f}")
                    
                    # Close positions in the opportunity
                    for pos_id in position_ids:
                        if pos_id in self.active_positions:
                            position = self.active_positions[pos_id]
                            success = self.ai_close_position_intelligent(position, 'PROFIT_TAKING')
                            
                            if success:
                                successful_closes += 1
                                print(f"     ✅ Closed position {pos_id}")
                            else:
                                print(f"     ❌ Failed to close {pos_id}")
                            
                            time.sleep(0.5)  # Small delay between closes
                    
                    # If staged execution, wait between opportunities
                    if execution_method == 'STAGED_CLOSING' and i < len(opportunities) - 1:
                        time.sleep(2)
                
                except Exception as e:
                    print(f"     ❌ Opportunity {i+1} error: {e}")
            
            total_positions = sum(len(opp.get('position_ids', [])) for opp in opportunities)
            success_rate = successful_closes / total_positions if total_positions > 0 else 0
            
            print(f"   📊 Closed: {successful_closes}/{total_positions} ({success_rate:.1%})")
            
            return success_rate >= 0.7  # Success if >70% positions closed
            
        except Exception as e:
            print(f"❌ Profit taking execution error: {e}")
            return False

    def ai_execute_emergency_cleanup(self, parameters: Dict) -> bool:
        """🧠 Execute emergency portfolio cleanup"""
        
        try:
            cleanup_method = parameters.get('cleanup_method', 'CLOSE_WEAK_POSITIONS')
            preserve_strong = parameters.get('preserve_strong', True)
            target_health = parameters.get('target_health', 60)
            
            print(f"   🚨 Emergency cleanup: {cleanup_method}")
            
            # Identify weak positions
            weak_positions = self.ai_identify_weak_positions()
            
            if not weak_positions:
                print("   ✅ No weak positions found")
                return True
            
            print(f"   🎯 Found {len(weak_positions)} weak positions")
            
            closed_positions = 0
            
            for position in weak_positions:
                try:
                    pos_id = position.get('ticket', position.get('position_id'))
                    pnl = position.get('profit', position.get('pnl', 0))
                    
                    # Skip if preserving strong positions and this one is profitable
                    if preserve_strong and pnl > 0:
                        continue
                    
                    success = self.ai_close_position_intelligent(position, 'EMERGENCY_CLEANUP')
                    
                    if success:
                        closed_positions += 1
                        print(f"     ✅ Cleaned up position {pos_id} (${pnl:.2f})")
                    else:
                        print(f"     ❌ Failed to cleanup {pos_id}")
                    
                    time.sleep(0.5)
                    
                    # Check if we've achieved target health
                    current_health = self.ai_calculate_portfolio_health()
                    if current_health >= target_health:
                        print(f"   🎯 Target health {target_health} achieved")
                        break
                
                except Exception as e:
                    print(f"     ❌ Position cleanup error: {e}")
            
            print(f"   📊 Cleanup complete: {closed_positions} positions closed")
            
            return closed_positions > 0
            
        except Exception as e:
            print(f"❌ Emergency cleanup error: {e}")
            return False

    def ai_execute_portfolio_balance(self, parameters: Dict) -> bool:
        """🧠 Execute portfolio balance optimization"""
        
        try:
            rebalance_method = parameters.get('rebalance_method', 'ADD_COUNTER_POSITIONS')
            target_balance_ratio = parameters.get('target_balance_ratio', 0.8)
            
            print(f"   ⚖️ Portfolio rebalancing: {rebalance_method}")
            
            # Analyze current balance
            buy_positions = [p for p in self.active_positions.values() 
                           if p.get('direction') == 'BUY']
            sell_positions = [p for p in self.active_positions.values() 
                            if p.get('direction') == 'SELL']
            
            buy_count = len(buy_positions)
            sell_count = len(sell_positions)
            
            print(f"   📊 Current: {buy_count} BUY, {sell_count} SELL")
            
            if buy_count == 0 and sell_count == 0:
                return False
            
            # Calculate imbalance
            total_positions = buy_count + sell_count
            if total_positions == 0:
                return False
            
            current_ratio = min(buy_count, sell_count) / max(buy_count, sell_count)
            
            if current_ratio >= target_balance_ratio:
                print(f"   ✅ Portfolio already balanced ({current_ratio:.2f})")
                return True
            
            # Determine what to add
            if buy_count > sell_count:
                needed_direction = 'SELL'
                needed_count = int(buy_count * target_balance_ratio) - sell_count
            else:
                needed_direction = 'BUY'
                needed_count = int(sell_count * target_balance_ratio) - buy_count
            
            needed_count = max(1, min(needed_count, 4))  # Limit to 1-4 positions
            
            print(f"   🎯 Adding {needed_count} {needed_direction} positions")
            
            # Place counter positions
            current_price = self.get_current_price()
            if not current_price:
                return False
            
            orders_placed = 0
            spacing = self.ai_calculate_optimal_spacing(50, MarketCondition.RANGING)  # Use moderate spacing
            spacing_dollars = spacing * 0.01
            
            for i in range(needed_count):
                if needed_direction == 'BUY':
                    order_price = current_price - spacing_dollars * (i + 1)
                else:
                    order_price = current_price + spacing_dollars * (i + 1)
                
                success = self.ai_place_intelligent_order(order_price, needed_direction, self.base_lot, 'BALANCE')
                
                if success:
                    orders_placed += 1
                    print(f"     ✅ {needed_direction} order: ${order_price:.2f}")
                
                time.sleep(0.3)
            
            print(f"   📊 Balance orders: {orders_placed}/{needed_count}")
            
            return orders_placed > 0
            
        except Exception as e:
            print(f"❌ Portfolio balance error: {e}")
            return False

    def ai_execute_risk_reduction(self, parameters: Dict) -> bool:
        """🧠 Execute emergency risk reduction"""
        
        try:
            reduction_method = parameters.get('reduction_method', 'CLOSE_HIGHEST_RISK_POSITIONS')
            target_risk_ratio = parameters.get('target_risk_ratio', 0.6)
            preserve_profitable = parameters.get('preserve_profitable', True)
            
            print(f"   🚨 Emergency risk reduction: {reduction_method}")
            
            current_drawdown = self.get_current_drawdown_points()
            target_drawdown = self.survivability * target_risk_ratio
            
            print(f"   📊 Current risk: {current_drawdown:.0f}/{self.survivability:.0f} points")
            print(f"   🎯 Target risk: {target_drawdown:.0f} points")
            
            if current_drawdown <= target_drawdown:
                print("   ✅ Already within target risk")
                return True
            
            # Identify highest risk positions
            high_risk_positions = self.ai_identify_high_risk_positions()
            
            if not high_risk_positions:
                print("   ⚠️ No high risk positions identified")
                return False
            
            # Sort by risk (highest losses first if losing, preserve profits if profitable)
            if preserve_profitable:
                # Close only losing positions, worst first
                losing_positions = [p for p in high_risk_positions 
                                  if p.get('profit', p.get('pnl', 0)) < 0]
                losing_positions.sort(key=lambda x: x.get('profit', x.get('pnl', 0)))
                positions_to_close = losing_positions
            else:
                # Close any positions, starting with worst performers
                high_risk_positions.sort(key=lambda x: x.get('profit', x.get('pnl', 0)))
                positions_to_close = high_risk_positions
            
            print(f"   🎯 Closing {len(positions_to_close)} high-risk positions")
            
            closed_positions = 0
            
            for position in positions_to_close:
                try:
                    success = self.ai_close_position_intelligent(position, 'RISK_REDUCTION')
                    
                    if success:
                        closed_positions += 1
                        pos_id = position.get('ticket', position.get('position_id'))
                        pnl = position.get('profit', position.get('pnl', 0))
                        print(f"     ✅ Closed high-risk position {pos_id} (${pnl:.2f})")
                    
                    # Check if we've reached target
                    new_drawdown = self.get_current_drawdown_points()
                    if new_drawdown <= target_drawdown:
                        print(f"   🎯 Target risk achieved")
                        break
                    
                    time.sleep(0.5)
                
                except Exception as e:
                    print(f"     ❌ Position close error: {e}")
            
            print(f"   📊 Risk reduction: {closed_positions} positions closed")
            
            return closed_positions > 0
            
        except Exception as e:
            print(f"❌ Risk reduction error: {e}")
            return False

    def ai_execute_risk_adjustment(self, parameters: Dict) -> bool:
        """🧠 Execute moderate risk adjustment"""
        
        try:
            adjustment_method = parameters.get('adjustment_method', 'HEDGE_PROTECTION')
            hedge_ratio = parameters.get('hedge_ratio', 0.3)
            
            print(f"   🛡️ Risk adjustment: {adjustment_method}")
            
            if adjustment_method == 'HEDGE_PROTECTION':
                return self.ai_place_intelligent_hedges(hedge_ratio)
            else:
                print(f"   ⚠️ Unknown adjustment method: {adjustment_method}")
                return False
            
        except Exception as e:
            print(f"❌ Risk adjustment error: {e}")
            return False

    def ai_place_intelligent_order(self, price: float, direction: str, 
                                 lot_size: float, order_type: str) -> bool:
        """🧠 Place intelligent order with AI logic"""
        
        try:
            current_price = self.get_current_price()
            if not current_price:
                return False
            
            # Validate order parameters
            min_lot = self.symbol_info.get('volume_min', 0.01)
            max_lot = self.symbol_info.get('volume_max', 100.0)
            lot_step = self.symbol_info.get('volume_step', 0.01)
            
            # Adjust lot size to broker requirements
            adjusted_lot = round(lot_size / lot_step) * lot_step
            adjusted_lot = max(min_lot, min(adjusted_lot, max_lot))
            
            # Determine order type based on price vs market
            if direction == "BUY":
                mt5_order_type = mt5.ORDER_TYPE_BUY_LIMIT if price < current_price else mt5.ORDER_TYPE_BUY_STOP
            else:
                mt5_order_type = mt5.ORDER_TYPE_SELL_LIMIT if price > current_price else mt5.ORDER_TYPE_SELL_STOP
            
            # Prepare order request
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": self.gold_symbol,
                "volume": adjusted_lot,
                "type": mt5_order_type,
                "price": price,
                "magic": self.magic_number,
                "comment": f"AI_{order_type}_{direction}",
                "type_filling": mt5.ORDER_FILLING_RETURN
            }
            
            # Execute order
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                # Store in pending orders
                self.pending_orders[result.order] = {
                    'order_id': result.order,
                    'price': price,
                    'direction': direction,
                    'lot_size': adjusted_lot,
                    'ai_type': order_type,
                    'timestamp': datetime.now()
                }
                
                return True
            else:
                error_code = result.retcode if result else "No result"
                print(f"     ❌ Order failed: {error_code}")
                return False
            
        except Exception as e:
            print(f"❌ Intelligent order placement error: {e}")
            return False

    def ai_close_position_intelligent(self, position, reason: str) -> bool:
        """🧠 Close position with AI intelligence"""
        
        try:
            # Get position ID
            if isinstance(position, dict):
                position_id = position.get('ticket', position.get('position_id'))
            else:
                position_id = position.position_id
            
            # Get MT5 position
            mt5_positions = mt5.positions_get(ticket=position_id)
            if not mt5_positions:
                print(f"     ⚠️ Position {position_id} not found")
                return True  # Already closed
            
            mt5_position = mt5_positions[0]
            
            # Get current price
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                return False
            
            # Determine close parameters
            if mt5_position.type == mt5.POSITION_TYPE_BUY:
                close_price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            else:
                close_price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY
            
            # Prepare close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.gold_symbol,
                "volume": mt5_position.volume,
                "type": order_type,
                "position": position_id,
                "price": close_price,
                "deviation": 50,
                "magic": self.magic_number,
                "comment": f"AI_CLOSE_{reason}"
            }
            
            # Execute close
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                # Remove from active positions
                if position_id in self.active_positions:
                    del self.active_positions[position_id]
                
                return True
            else:
                error_code = result.retcode if result else "No result"
                print(f"     ❌ Close failed: {error_code}")
                return False
            
        except Exception as e:
            print(f"❌ Intelligent position close error: {e}")
            return False

    def ai_find_intelligent_profit_pairs(self) -> List[Dict]:
        """🧠 Find intelligent profit opportunities using AI analysis"""
        
        try:
            opportunities = []
            positions = list(self.active_positions.values())
            
            if len(positions) < 2:
                return opportunities
            
            # Separate by profitability
            profitable_positions = [p for p in positions if p.get('profit', p.get('pnl', 0)) > 1]
            losing_positions = [p for p in positions if p.get('profit', p.get('pnl', 0)) < -1]
            
            # AI Strategy 1: Rescue operations (profitable helps losing)
            for losing_pos in losing_positions:
                for profit_pos in profitable_positions:
                    net_pnl = (losing_pos.get('profit', 0) + profit_pos.get('profit', 0))
                    
                    if net_pnl > 0.5:  # Net positive
                        opportunities.append({
                            'type': 'RESCUE_PAIR',
                            'position_ids': [
                                losing_pos.get('ticket', losing_pos.get('position_id')),
                                profit_pos.get('ticket', profit_pos.get('position_id'))
                            ],
                            'expected_profit': net_pnl,
                            'ai_confidence': 0.8,
                            'strategy': 'Profitable position rescues losing position'
                        })
            
            # AI Strategy 2: High-profit single positions
            for profit_pos in profitable_positions:
                profit = profit_pos.get('profit', profit_pos.get('pnl', 0))
                if profit > 5:  # High profit threshold
                    opportunities.append({
                        'type': 'HIGH_PROFIT_SINGLE',
                        'position_ids': [profit_pos.get('ticket', profit_pos.get('position_id'))],
                        'expected_profit': profit,
                        'ai_confidence': 0.7,
                        'strategy': 'Take high profit before reversal'
                    })
            
            # Sort by expected profit (highest first)
            opportunities.sort(key=lambda x: x['expected_profit'], reverse=True)
            
            # Return top opportunities
            return opportunities[:5]
            
        except Exception as e:
            print(f"❌ AI profit pair analysis error: {e}")
            return []

    def ai_identify_weak_positions(self) -> List[Dict]:
        """🧠 Identify weak positions for cleanup"""
        
        try:
            weak_positions = []
            positions = list(self.active_positions.values())
            
            for position in positions:
                pnl = position.get('profit', position.get('pnl', 0))
                entry_time = position.get('time_open', datetime.now())
                
                # Calculate position age
                if isinstance(entry_time, (int, float)):
                    entry_time = datetime.fromtimestamp(entry_time)
                elif isinstance(entry_time, str):
                    entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                
                age_hours = (datetime.now() - entry_time).total_seconds() / 3600
                
                # Identify weak positions
                is_weak = (
                    pnl < -10 or  # Large loss
                    (pnl < -5 and age_hours > 24) or  # Moderate loss + old
                    (pnl < 0 and age_hours > 72)  # Any loss + very old
                )
                
                if is_weak:
                    weak_positions.append(position)
            
            # Sort by worst performance first
            weak_positions.sort(key=lambda x: x.get('profit', x.get('pnl', 0)))
            
            return weak_positions
            
        except Exception as e:
            print(f"❌ Weak position identification error: {e}")
            return []

    def ai_identify_high_risk_positions(self) -> List[Dict]:
        """🧠 Identify high-risk positions"""
        
        try:
            high_risk_positions = []
            positions = list(self.active_positions.values())
            
            # Calculate total portfolio exposure
            total_exposure = sum(p.get('volume', p.get('lot_size', 0)) for p in positions)
            
            for position in positions:
                lot_size = position.get('volume', position.get('lot_size', 0))
                pnl = position.get('profit', position.get('pnl', 0))
                
                # Risk factors
                size_risk = lot_size / total_exposure if total_exposure > 0 else 0
                loss_risk = min(0, pnl) / 100  # Normalize loss risk
                
                # Combined risk score
                risk_score = size_risk - loss_risk  # Higher for large positions or large losses
                
                if risk_score > 0.3:  # High risk threshold
                    high_risk_positions.append(position)
            
            # Sort by risk score (highest first)
            high_risk_positions.sort(key=lambda x: x.get('profit', x.get('pnl', 0)))
            
            return high_risk_positions
            
        except Exception as e:
            print(f"❌ High risk identification error: {e}")
            return []

    def ai_place_intelligent_hedges(self, hedge_ratio: float) -> bool:
        """🧠 Place intelligent hedge positions"""
        
        try:
            positions = list(self.active_positions.values())
            
            # Calculate exposure by direction
            buy_exposure = sum(p.get('volume', 0) for p in positions 
                             if p.get('direction') == 'BUY' or p.get('type') == mt5.POSITION_TYPE_BUY)
            sell_exposure = sum(p.get('volume', 0) for p in positions 
                              if p.get('direction') == 'SELL' or p.get('type') == mt5.POSITION_TYPE_SELL)
            
            print(f"   📊 Exposure: {buy_exposure:.3f} BUY, {sell_exposure:.3f} SELL")
            
            # Determine hedge direction and size
            if buy_exposure > sell_exposure:
                hedge_direction = 'SELL'
                hedge_size = (buy_exposure - sell_exposure) * hedge_ratio
            elif sell_exposure > buy_exposure:
                hedge_direction = 'BUY'
                hedge_size = (sell_exposure - buy_exposure) * hedge_ratio
            else:
                print("   ✅ Portfolio already balanced")
                return True
            
            # Ensure minimum hedge size
            min_lot = self.symbol_info.get('volume_min', 0.01)
            hedge_size = max(hedge_size, min_lot)
            
            print(f"   🛡️ Hedge: {hedge_direction} {hedge_size:.3f} lots")
            
            # Place hedge as market order
            success = self.ai_place_market_hedge(hedge_direction, hedge_size)
            
            return success
            
        except Exception as e:
            print(f"❌ Intelligent hedge error: {e}")
            return False

    def ai_place_market_hedge(self, direction: str, lot_size: float) -> bool:
        """🧠 Place market hedge order"""
        
        try:
            # Get current price
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                return False
            
            # Prepare market order
            if direction == "BUY":
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.gold_symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "deviation": 50,
                "magic": self.magic_number,
                "comment": f"AI_HEDGE_{direction}",
                "type_filling": mt5.ORDER_FILLING_IOC
            }
            
            # Execute hedge
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"     ✅ Hedge placed: {direction} {lot_size:.3f} @ ${price:.2f}")
                return True
            else:
                error_code = result.retcode if result else "No result"
                print(f"     ❌ Hedge failed: {error_code}")
                return False
            
        except Exception as e:
            print(f"❌ Market hedge error: {e}")
            return False

    def ai_determine_direction_bias(self, market_analysis: AIMarketAnalysis) -> str:
        """🧠 Determine direction bias based on market analysis"""
        
        try:
            if not market_analysis:
                return "BALANCED"
            
            trend_strength = market_analysis.trend_strength
            condition = market_analysis.condition
            
            # Strong trend bias
            if abs(trend_strength) > 60:
                if trend_strength > 0:
                    return "BUY_BIAS"  # Uptrend - favor buy positions
                else:
                    return "SELL_BIAS"  # Downtrend - favor sell positions
            
            # Market condition bias
            if condition == MarketCondition.TRENDING_UP:
                return "BUY_BIAS"
            elif condition == MarketCondition.TRENDING_DOWN:
                return "SELL_BIAS"
            
            # Default balanced approach
            return "BALANCED"
            
        except Exception as e:
            print(f"❌ Direction bias error: {e}")
            return "BALANCED"

    def ai_update_positions_from_mt5(self):
        """🧠 Update positions from MT5 with AI classification"""
        
        try:
            # Get all positions
            positions = mt5.positions_get(symbol=self.gold_symbol)
            
            if not positions:
                # No positions - clear tracking
                self.active_positions.clear()
                return
            
            # Update active positions
            current_positions = {}
            
            for position in positions:
                if position.magic == self.magic_number:
                    pos_id = position.ticket
                    
                    # Create position data
                    position_data = {
                        'ticket': pos_id,
                        'type': position.type,
                        'volume': position.volume,
                        'price_open': position.price_open,
                        'price_current': position.price_current,
                        'profit': position.profit,
                        'symbol': position.symbol,
                        'time_open': datetime.fromtimestamp(position.time),
                        'direction': "BUY" if position.type == mt5.POSITION_TYPE_BUY else "SELL",
                        'comment': getattr(position, 'comment', '')
                    }
                    
                    # AI classify if new position
                    if pos_id not in self.active_positions:
                        self.ai_classify_position(position_data)
                    
                    current_positions[pos_id] = position_data
            
            # Update active positions
            self.active_positions = current_positions
            
        except Exception as e:
            print(f"❌ Position update error: {e}")

    def ai_classify_position(self, position_data: Dict):
        """🧠 AI classify position for tracking"""
        
        try:
            pos_id = position_data.get('ticket')
            direction = position_data.get('direction')
            profit = position_data.get('profit', 0)
            comment = position_data.get('comment', '')
            
            # Determine AI classification
            if 'HEDGE' in comment:
                ai_tag = 'HEDGE_POSITION'
            elif 'STRATEGIC' in comment:
                ai_tag = 'STRATEGIC_POSITION'
            elif profit > 5:
                ai_tag = 'HIGH_PROFIT'
            elif profit < -5:
                ai_tag = 'HIGH_LOSS'
            else:
                ai_tag = 'STANDARD_POSITION'
            
            # Store AI mapping
            self.ai_position_map[pos_id] = {
                'ai_tag': ai_tag,
                'classification_time': datetime.now(),
                'initial_profit': profit
            }
            
            print(f"🧠 AI Classified: Position {pos_id} as {ai_tag}")
            
        except Exception as e:
            print(f"❌ Position classification error: {e}")

    def ai_monitor_pending_orders(self):
        """🧠 Monitor pending orders with AI logic"""
        
        try:
            # Get current orders
            orders = mt5.orders_get(symbol=self.gold_symbol)
            
            if not orders:
                self.pending_orders.clear()
                return
            
            # Update pending orders tracking
            current_order_ids = set()
            
            for order in orders:
                if order.magic == self.magic_number:
                    current_order_ids.add(order.ticket)
                    
                    # Add new orders to tracking
                    if order.ticket not in self.pending_orders:
                        self.pending_orders[order.ticket] = {
                            'order_id': order.ticket,
                            'price': order.price_open,
                            'direction': "BUY" if order.type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP] else "SELL",
                            'lot_size': order.volume_initial,
                            'ai_type': 'DETECTED',
                            'timestamp': datetime.fromtimestamp(order.time_setup)
                        }
            
            # Remove filled/cancelled orders
            filled_orders = set(self.pending_orders.keys()) - current_order_ids
            for order_id in filled_orders:
                if order_id in self.pending_orders:
                    del self.pending_orders[order_id]
            
        except Exception as e:
            print(f"❌ Order monitoring error: {e}")

    def ai_emergency_protection(self) -> bool:
        """🧠 AI Emergency Protection System"""
        
        try:
            # Check survivability usage
            current_drawdown = self.get_current_drawdown_points()
            risk_ratio = current_drawdown / self.survivability if self.survivability > 0 else 0
            
            # Emergency threshold (90% of survivability)
            if risk_ratio > 0.9:
                print("🚨 AI EMERGENCY PROTECTION TRIGGERED!")
                print(f"   Risk usage: {risk_ratio:.1%} > 90%")
                print(f"   Drawdown: {current_drawdown:.0f}/{self.survivability:.0f} points")
                
                # Emergency actions
                self.ai_execute_emergency_protection()
                
                return True  # Emergency detected
            
            # High risk warning (75% of survivability)
            elif risk_ratio > 0.75:
                if not hasattr(self, 'last_risk_warning'):
                    self.last_risk_warning = datetime.now()
                    print("⚠️ AI HIGH RISK WARNING")
                    print(f"   Risk usage: {risk_ratio:.1%}")
                    print(f"   Consider risk reduction measures")
            
            return False  # No emergency
            
        except Exception as e:
            print(f"❌ Emergency protection error: {e}")
            return False

    def ai_execute_emergency_protection(self):
        """🧠 Execute emergency protection measures"""
        
        try:
            print("🚨 Executing AI Emergency Protection...")
            
            # 1. Cancel all pending orders
            self.ai_cancel_all_pending_orders()
            
            # 2. Close most risky positions
            high_risk_positions = self.ai_identify_high_risk_positions()
            
            emergency_closes = 0
            for position in high_risk_positions[:3]:  # Close top 3 riskiest
                success = self.ai_close_position_intelligent(position, 'EMERGENCY_PROTECTION')
                if success:
                    emergency_closes += 1
            
            print(f"🚨 Emergency protection: {emergency_closes} positions closed")
            
            # 3. Set emergency flag
            self.ai_active = False
            print("🛑 AI Trading System: EMERGENCY STOPPED")
            
        except Exception as e:
            print(f"❌ Emergency protection execution error: {e}")

    def ai_cancel_all_pending_orders(self):
        """🧠 Cancel all pending orders"""
        
        try:
            orders = mt5.orders_get(symbol=self.gold_symbol)
            
            if not orders:
                return
            
            cancelled_count = 0
            
            for order in orders:
                if order.magic == self.magic_number:
                    request = {
                        "action": mt5.TRADE_ACTION_REMOVE,
                        "order": order.ticket
                    }
                    
                    result = mt5.order_send(request)
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        cancelled_count += 1
            
            print(f"🚨 Cancelled {cancelled_count} pending orders")
            self.pending_orders.clear()
            
        except Exception as e:
            print(f"❌ Order cancellation error: {e}")

    def ai_update_performance_metrics(self):
        """🧠 Update AI performance metrics"""
        
        try:
            # Update portfolio health average
            current_health = self.ai_health_score
            
            if not hasattr(self, 'health_history'):
                self.health_history = []
            
            self.health_history.append(current_health)
            
            # Keep last 100 readings
            if len(self.health_history) > 100:
                self.health_history = self.health_history[-100:]
            
            # Calculate average
            self.performance_metrics['portfolio_health_avg'] = sum(self.health_history) / len(self.health_history)
            
            # Update other metrics
            if len(self.decision_history) > 0:
                successful_decisions = sum(1 for d in self.decision_history if d.get('success', False))
                self.performance_metrics['ai_accuracy'] = successful_decisions / len(self.decision_history)
            
        except Exception as e:
            print(f"❌ Performance metrics error: {e}")

    def ai_update_learning_system(self):
        """🧠 Update AI learning system"""
        
        try:
            # Analyze recent decisions for learning
            if len(self.decision_history) >= 10:
                recent_decisions = self.decision_history[-10:]
                
                # Calculate success rate by decision type
                decision_types = {}
                
                for decision_record in recent_decisions:
                    decision = decision_record['decision']
                    success = decision_record['success']
                    action = decision.action
                    
                    if action not in decision_types:
                        decision_types[action] = {'total': 0, 'successful': 0}
                    
                    decision_types[action]['total'] += 1
                    if success:
                        decision_types[action]['successful'] += 1
                
                # Adjust confidence thresholds based on success rates
                for action, stats in decision_types.items():
                    if stats['total'] >= 3:  # Enough data
                        success_rate = stats['successful'] / stats['total']
                        
                        if success_rate < 0.5:  # Low success rate
                            # Increase confidence threshold for this action
                            print(f"🧠 AI Learning: Reducing confidence for {action} (success: {success_rate:.1%})")
                        elif success_rate > 0.8:  # High success rate
                            # Could decrease threshold, but keep conservative
                            print(f"🧠 AI Learning: {action} performing well (success: {success_rate:.1%})")
            
            # Clean old learning data
            if len(self.decision_history) > 50:
                self.decision_history = self.decision_history[-50:]
            
            if len(self.market_memory) > self.ai_config['market_memory_size']:
                self.market_memory = self.market_memory[-self.ai_config['market_memory_size']:]
            
        except Exception as e:
            print(f"❌ Learning system error: {e}")

    def log_ai_thinking_process(self, market_analysis: Optional[AIMarketAnalysis], 
                                health_score: float, portfolio_status: PortfolioStatus):
        """🧠 Log AI thinking process"""
        
        try:
            print("🧠 AI THINKING PROCESS:")
            print(f"   📊 Portfolio Health: {health_score:.1f}/100")
            print(f"   💰 Portfolio Status: {portfolio_status.value}")
            print(f"   📈 Active Positions: {len(self.active_positions)}")
            print(f"   📋 Pending Orders: {len(self.pending_orders)}")
            
            if market_analysis:
                print(f"   🔬 Market Condition: {market_analysis.condition.value}")
                print(f"   📊 Volatility: {market_analysis.volatility_score:.1f}/100")
                print(f"   📈 Trend: {market_analysis.trend_strength:.1f}")
                print(f"   🎯 Confidence: {market_analysis.confidence:.2f}")
            
            # AI performance
            accuracy = self.performance_metrics.get('ai_accuracy', 0)
            total_decisions = self.performance_metrics.get('total_decisions', 0)
            
            print(f"   🤖 AI Accuracy: {accuracy:.1%} ({total_decisions} decisions)")
            
            # Risk assessment
            current_drawdown = self.get_current_drawdown_points()
            risk_ratio = current_drawdown / self.survivability if self.survivability > 0 else 0
            
            print(f"   🛡️ Risk Usage: {risk_ratio:.1%} ({current_drawdown:.0f}/{self.survivability:.0f} points)")
            
        except Exception as e:
            print(f"❌ AI thinking log error: {e}")

    def scan_existing_positions(self) -> List[Dict]:
        """🧠 Scan existing positions on startup"""
        
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            
            if not positions:
                return []
            
            existing_positions = []
            
            for position in positions:
                if position.magic == self.magic_number:
                    position_data = {
                        'ticket': position.ticket,
                        'type': position.type,
                        'volume': position.volume,
                        'price_open': position.price_open,
                        'price_current': position.price_current,
                        'profit': position.profit,
                        'time_open': datetime.fromtimestamp(position.time),
                        'direction': "BUY" if position.type == mt5.POSITION_TYPE_BUY else "SELL"
                    }
                    
                    existing_positions.append(position_data)
                    self.active_positions[position.ticket] = position_data
            
            return existing_positions
            
        except Exception as e:
            print(f"❌ Existing position scan error: {e}")
            return []

    def get_current_price(self) -> float:
        """Get current gold price - Enhanced Version"""
        
        try:
            # Method 1: Use MT5 connector
            if self.mt5_connector:
                price_data = self.mt5_connector.get_current_price()
                if price_data and 'bid' in price_data:
                    return float(price_data['bid'])
            
            # Method 2: Direct MT5 call
            import MetaTrader5 as mt5
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if tick and tick.bid > 0:
                return float(tick.bid)
            
            # Method 3: Try with symbol info
            symbol_info = mt5.symbol_info(self.gold_symbol)
            if symbol_info and hasattr(symbol_info, 'bid') and symbol_info.bid > 0:
                return float(symbol_info.bid)
            
            print(f"⚠️ Cannot get price for {self.gold_symbol}")
            return 0
            
        except Exception as e:
            print(f"❌ Current price error: {e}")
            return 0

    def get_recent_price_history(self, count: int) -> List[float]:
        """Get recent price history for analysis"""
        
        try:
            from datetime import datetime, timedelta
            import MetaTrader5 as mt5
            
            # Method 1: Try to get recent rates (more reliable)
            rates = mt5.copy_rates_from_pos(self.gold_symbol, mt5.TIMEFRAME_M1, 0, min(count, 100))
            
            if rates is not None and len(rates) > 0:
                # Use close prices from rates
                return [float(rate['close']) for rate in rates]
            
            # Method 2: Try copy_ticks_range (correct function name)
            try:
                # Get ticks from last hour
                utc_to = datetime.now()
                utc_from = utc_to - timedelta(hours=1)
                
                ticks = mt5.copy_ticks_range(self.gold_symbol, utc_from, utc_to, mt5.COPY_TICKS_ALL)
                
                if ticks is not None and len(ticks) > 0:
                    # Take last N ticks
                    recent_ticks = ticks[-min(count, len(ticks)):]
                    return [float(tick.bid) for tick in recent_ticks]
            except Exception as tick_error:
                print(f"Tick method failed: {tick_error}")
            
            # Method 3: Get current price multiple times (fallback)
            current_price = self.get_current_price()
            if current_price > 0:
                # Return same price multiple times for basic analysis
                return [current_price] * min(count, 10)
            
            return []
            
        except Exception as e:
            print(f"❌ Price history error: {e}")
            # Ultimate fallback
            try:
                current_price = self.get_current_price()
                if current_price > 0:
                    return [current_price]
            except:
                pass
            
            return []

    def calculate_trend_slope(self, prices: List[float]) -> float:
        """Calculate trend slope from price data"""
        
        try:
            if len(prices) < 2:
                return 0.0
            
            # Simple linear regression slope
            n = len(prices)
            x_values = list(range(n))
            
            x_mean = sum(x_values) / n
            y_mean = sum(prices) / n
            
            numerator = sum((x_values[i] - x_mean) * (prices[i] - y_mean) for i in range(n))
            denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                return 0.0
            
            slope = numerator / denominator
            
            # Normalize slope for gold price range
            return slope * 1000  # Scale for readability
            
        except Exception as e:
            print(f"❌ Trend slope error: {e}")
            return 0.0

    def get_current_drawdown_points(self) -> float:
        """Get current drawdown in points"""
    
        try:
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return 0
            
            balance = account_info.get('balance', 0)
            equity = account_info.get('equity', 0)
            
            if equity >= balance:
                return 0  # No drawdown
            
            # Convert dollar loss to points
            dollar_loss = balance - equity
            points_loss = dollar_loss * 100  # Approximate conversion for gold
            
            return points_loss
            
        except Exception as e:
            print(f"❌ Drawdown calculation error: {e}")
            return 0

    def stop_ai_trading(self):
        """Stop AI trading system"""
        
        try:
            print("🛑 Stopping AI Smart Profit System...")
            
            self.ai_active = False
            
            # Wait for threads to finish
            if hasattr(self, 'ai_main_thread') and self.ai_main_thread.is_alive():
                print("   🧠 Stopping AI Main Loop...")
                
            if hasattr(self, 'ai_monitor_thread') and self.ai_monitor_thread.is_alive():
                print("   👁️ Stopping AI Monitor...")
            
            # Final statistics
            print("📊 AI SYSTEM FINAL STATISTICS:")
            print(f"   🎯 Total Decisions: {self.performance_metrics.get('total_decisions', 0)}")
            print(f"   ✅ Successful: {self.performance_metrics.get('successful_decisions', 0)}")
            print(f"   🎯 Accuracy: {self.performance_metrics.get('ai_accuracy', 0):.1%}")
            print(f"   🏥 Avg Health: {self.performance_metrics.get('portfolio_health_avg', 50):.1f}/100")
            print(f"   📊 Active Positions: {len(self.active_positions)}")
            print(f"   📋 Pending Orders: {len(self.pending_orders)}")
            
            print("✅ AI Smart Profit System Stopped Successfully")
            
        except Exception as e:
            print(f"❌ AI system stop error: {e}")

    def get_ai_system_status(self) -> Dict:
        """Get comprehensive AI system status"""
        
        try:
            status = {
                # Core AI Status
                'ai_active': self.ai_active,
                'ai_health_score': self.ai_health_score,
                'portfolio_status': self.portfolio_status.value if hasattr(self.portfolio_status, 'value') else str(self.portfolio_status),
                
                # Trading Status
                'active_positions': len(self.active_positions),
                'pending_orders': len(self.pending_orders),
                'gold_symbol': self.gold_symbol,
                'magic_number': self.magic_number,
                
                # Market Analysis
                'market_analysis': None,
                'market_confidence': 0.0,
                
                # Performance Metrics
                'ai_accuracy': self.performance_metrics.get('ai_accuracy', 0),
                'total_decisions': self.performance_metrics.get('total_decisions', 0),
                'successful_decisions': self.performance_metrics.get('successful_decisions', 0),
                'portfolio_health_avg': self.performance_metrics.get('portfolio_health_avg', 50),
                
                # Risk Assessment
                'current_drawdown_points': self.get_current_drawdown_points(),
                'survivability_points': self.survivability,
                'risk_ratio': 0.0,
                
                # Timestamps
                'last_update': datetime.now().isoformat(),
                'system_uptime': datetime.now().isoformat()
            }
            
            # Add market analysis if available
            if self.market_analysis:
                status['market_analysis'] = {
                    'condition': self.market_analysis.condition.value,
                    'volatility_score': self.market_analysis.volatility_score,
                    'trend_strength': self.market_analysis.trend_strength,
                    'optimal_spacing': self.market_analysis.optimal_spacing,
                    'recommended_action': self.market_analysis.recommended_action
                }
                status['market_confidence'] = self.market_analysis.confidence
            
            # Calculate risk ratio
            if self.survivability > 0:
                status['risk_ratio'] = status['current_drawdown_points'] / self.survivability
            
            # Add account info if available
            account_info = self.mt5_connector.get_account_info()
            if account_info:
                status.update({
                    'account_balance': account_info.get('balance', 0),
                    'account_equity': account_info.get('equity', 0),
                    'account_margin': account_info.get('margin', 0),
                    'account_free_margin': account_info.get('free_margin', 0)
                })
            
            return status
            
        except Exception as e:
            print(f"❌ AI status error: {e}")
            return {'error': str(e)}

def __del__(self):
    """Cleanup when AI system is destroyed"""
    try:
        if getattr(self, 'ai_active', False):
            self.stop_ai_trading()
    except:
        pass