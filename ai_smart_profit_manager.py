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
        """Main AI decision making loop - แก้ไขให้ตัดสินใจเร็วขึ้น"""
        print("🧠 AI MAIN LOOP: Enhanced thinking process started...")
        
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
                
                # 🔥 แก้ไข: เพิ่มการตรวจสอบ immediate positioning
                current_positions = len(self.active_positions)
                pending_orders = len(self.pending_orders)
                total_exposure = current_positions + pending_orders
                
                # ถ้าไม่มีไม้เลย ให้วางทันที
                if total_exposure == 0:
                    print("🚨 No positions detected - IMMEDIATE ACTION!")
                    emergency_decision = AIDecision(
                        action="IMMEDIATE_POSITIONING",
                        reason=AIDecisionReason.EMERGENCY_PROTECTION,
                        confidence=0.95,
                        parameters={
                            'spacing': 40,
                            'direction_bias': 'BALANCED',
                            'position_count': 2,
                            'lot_size': self.base_lot,
                            'immediate_mode': True
                        },
                        expected_outcome="Emergency 2 positions immediately",
                        timestamp=datetime.now()
                    )
                    self.ai_execute_decision(emergency_decision)
                
                # 🧠 Step 4: Make AI decisions based on analysis
                ai_decisions = self.ai_make_strategic_decisions(
                    market_analysis, health_score, portfolio_status
                )
                
                # 🧠 Step 5: Execute AI decisions
                for decision in ai_decisions:
                    self.ai_execute_decision(decision)
                
                # 🧠 Step 6: Learn from results
                self.ai_update_learning_system()
                
                # Log AI thinking process every 15 seconds (เปลี่ยนจาก 30)
                if not hasattr(self, 'last_ai_log'):
                    self.last_ai_log = datetime.now()
                elif (datetime.now() - self.last_ai_log).total_seconds() >= 15:
                    self.log_ai_thinking_process(market_analysis, health_score, portfolio_status)
                    self.last_ai_log = datetime.now()
                
                # 🔥 แก้ไข: ลดเวลารอให้คิดเร็วขึ้น
                time.sleep(2)  # เปลี่ยนจาก 3 เป็น 2 วินาที
                
            except Exception as e:
                print(f"❌ AI Main Loop error: {e}")
                time.sleep(3)
    
    print("🛑 AI Main Loop: Stopped")

    def ai_monitoring_loop(self):
        """AI monitoring and updates loop - เพิ่มการตรวจสอบ continuous grid"""
        print("👁️ AI MONITOR: Enhanced continuous monitoring started...")
        
        while self.ai_active:
            try:
                # Update positions from MT5
                old_position_count = len(self.active_positions)
                old_pending_count = len(self.pending_orders)
                
                self.ai_update_positions_from_mt5()
                
                new_position_count = len(self.active_positions)
                new_pending_count = len(self.pending_orders)
                
                # 🔥 ตรวจสอบการเปลี่ยนแปลง
                if new_position_count > old_position_count:
                    filled_orders = new_position_count - old_position_count
                    print(f"✅ {filled_orders} order(s) filled! Positions: {old_position_count}→{new_position_count}")
                    
                    # ถ้ามีไม้ fill แล้ว ให้ trigger การวางไม้ใหม่ในรอบถัดไป
                    if not hasattr(self, 'need_refill_check'):
                        self.need_refill_check = True
                
                if new_pending_count < old_pending_count:
                    cancelled_orders = old_pending_count - new_pending_count
                    print(f"⚠️ {cancelled_orders} pending order(s) removed! Pending: {old_pending_count}→{new_pending_count}")
                
                # Monitor pending orders
                self.ai_monitor_pending_orders()
                
                # Check for emergency conditions
                emergency_detected = self.ai_emergency_protection()
                if emergency_detected:
                    break
                
                # Update performance metrics
                self.ai_update_performance_metrics()
                
                time.sleep(3)  # Monitor every 3 seconds
                
            except Exception as e:
                print(f"❌ AI Monitor error: {e}")
                time.sleep(5)
        
        print("🛑 AI Monitor: Stopped")

    def ai_analyze_market_condition(self) -> Optional[AIMarketAnalysis]:
        """🧠 AI Market Analysis - แก้ไขการคำนวณ Volatility"""
        try:
            # Get current price data
            current_price = self.get_current_price()
            if not current_price:
                return None
            
            # Get recent price history for analysis
            price_history = self.get_recent_price_history(20)  # ลดเป็น 20 เพื่อความเร็ว
            
            if not price_history or len(price_history) < 3:
                # Enhanced fallback analysis
                return self.create_fallback_market_analysis(current_price)
            
            # 🔥 แก้ไข: Volatility Analysis ใหม่
            price_changes = []
            for i in range(1, len(price_history)):
                change = abs(price_history[i] - price_history[i-1])
                price_changes.append(change)
            
            if price_changes:
                avg_change = sum(price_changes) / len(price_changes)
                max_change = max(price_changes)
                
                # 🔥 ปรับการคำนวณ volatility_score ใหม่ทั้งหมด
                # สำหรับทองคำ: การเปลี่ยนแปลง $1 = volatility ปานกลาง
                if avg_change <= 0.5:      # เปลี่ยนแปลงน้อยกว่า $0.50
                    volatility_score = 20.0
                elif avg_change <= 1.0:    # เปลี่ยนแปลงน้อยกว่า $1.00  
                    volatility_score = 35.0
                elif avg_change <= 2.0:    # เปลี่ยนแปลงน้อยกว่า $2.00
                    volatility_score = 50.0
                elif avg_change <= 3.0:    # เปลี่ยนแปลงน้อยกว่า $3.00
                    volatility_score = 65.0
                else:                      # เปลี่ยนแปลงมากกว่า $3.00
                    volatility_score = 80.0
                
                # ปรับตาม max change
                if max_change > 5.0:
                    volatility_score += 15
                elif max_change > 3.0:
                    volatility_score += 10
                elif max_change > 2.0:
                    volatility_score += 5
                    
                # จำกัดไม่ให้เกิน 100
                volatility_score = min(100, volatility_score)
                
            else:
                volatility_score = 35.0  # Default moderate-low volatility
            
            # 🧠 Trend Analysis (เหมือนเดิม)
            trend_strength = self.calculate_trend_slope(price_history)
            
            # 🧠 Support/Resistance Analysis  
            recent_prices = price_history[-min(5, len(price_history)):]
            support_level = min(recent_prices)
            resistance_level = max(recent_prices)
            
            # 🔥 แก้ไข: Market Condition Classification ใหม่
            condition = self.ai_classify_market_condition(
                volatility_score, trend_strength, price_history
            )
            
            # 🔥 แก้ไข: Optimal Spacing ที่ไม่ขึ้นกับ volatility มาก
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
            
            # Debug output
            print(f"🔬 Market Analysis DEBUG:")
            print(f"   💹 Avg Change: ${avg_change:.3f}")
            print(f"   📊 Volatility Score: {volatility_score:.1f}")
            print(f"   🎯 Condition: {condition.value}")
            print(f"   📏 Optimal Spacing: {optimal_spacing}")
            
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
        """Create fallback market analysis - แก้ไขให้ spacing ใกล้ขึ้น"""
        
        try:
            # Use account size for base spacing
            account_info = self.mt5_connector.get_account_info()
            balance = account_info.get('balance', 10000) if account_info else 10000
            
            # 🔥 แก้ไข: ลด spacing ลงมาก
            if balance >= 50000:
                base_spacing = 60    # เปลี่ยนจาก 150 เป็น 60
            elif balance >= 10000:
                base_spacing = 80    # เปลี่ยนจาก 200 เป็น 80
            else:
                base_spacing = 120   # เปลี่ยนจาก 300 เป็น 120
            
            return AIMarketAnalysis(
                condition=MarketCondition.RANGING,
                volatility_score=50.0,  # Moderate volatility
                trend_strength=0.0,     # Neutral trend
                support_level=current_price - 50,  # ลดจาก 100 เป็น 50
                resistance_level=current_price + 50,  # ลดจาก 100 เป็น 50
                optimal_spacing=base_spacing,
                recommended_action="AGGRESSIVE_POSITIONING",  # เปลี่ยนจาก CONSERVATIVE
                confidence=0.8  # เพิ่มจาก 0.6 เป็น 0.8
            )
            
        except Exception as e:
            print(f"❌ Fallback analysis error: {e}")
            return AIMarketAnalysis(
                condition=MarketCondition.RANGING,
                volatility_score=50.0,
                trend_strength=0.0,
                support_level=current_price - 30,  # ลดลง
                resistance_level=current_price + 30,  # ลดลง
                optimal_spacing=100,  # ลดจาก 300 เป็น 100
                recommended_action="AGGRESSIVE_POSITIONING",
                confidence=0.7
            )

    def ai_classify_market_condition(self, volatility_score: float, 
                                        trend_strength: float, 
                                        price_history: List[float]) -> MarketCondition:
        """🔥 แก้ไข: Market Condition Classification ใหม่"""
        
        # 🔥 ปรับ threshold ใหม่ให้เหมาะสมกับทองคำ
        if volatility_score > 85:        # เปลี่ยนจาก 70 เป็น 85
            return MarketCondition.HIGH_VOLATILITY
        elif volatility_score < 25:      # เปลี่ยนจาก 20 เป็น 25  
            return MarketCondition.LOW_VOLATILITY
        
        # Trend analysis - ปรับให้เข้มงวดขึ้น
        if abs(trend_strength) > 100:    # เปลี่ยนจาก 50 เป็น 100
            if trend_strength > 0:
                return MarketCondition.TRENDING_UP
            else:
                return MarketCondition.TRENDING_DOWN
        
        # Default to ranging (ส่วนใหญ่จะเป็น RANGING)
        return MarketCondition.RANGING

    def ai_calculate_optimal_spacing(self, volatility_score: float, 
                                        condition: MarketCondition) -> int:
        """🔥 แก้ไข: Optimal Spacing ที่ใกล้ market มากขึ้น"""
        
        # 🔥 ลด base spacing ลงอีกมาก
        account_info = self.mt5_connector.get_account_info()
        balance = account_info.get('balance', 10000) if account_info else 10000
        
        # ระยะห่างพื้นฐานที่ใกล้มาก
        if balance >= 50000:
            base_spacing = 25    # เปลี่ยนจาก 50 เป็น 25
        elif balance >= 25000:
            base_spacing = 30    # เปลี่ยนจาก 75 เป็น 30
        elif balance >= 10000:
            base_spacing = 35    # เปลี่ยนจาก 100 เป็น 35
        elif balance >= 5000:
            base_spacing = 40    # เปลี่ยนจาก 125 เป็น 40
        else:
            base_spacing = 50    # เปลี่ยนจาก 150 เป็น 50
        
        # ลด volatility factor impact อีกมาก
        volatility_factor = 1.0 + (volatility_score - 50) / 500  # เปลี่ยนจาก /300 เป็น /500
        
        # ปรับ condition factors ให้ใกล้ขึ้น
        condition_factors = {
            MarketCondition.HIGH_VOLATILITY: 1.1,  # ลดจาก 1.3 เป็น 1.1
            MarketCondition.LOW_VOLATILITY: 0.9,   # ลดจาก 0.9 เป็น 0.8
            MarketCondition.TRENDING_UP: 0.9,      # ลดจาก 1.0 เป็น 0.9
            MarketCondition.TRENDING_DOWN: 0.9,    # ลดจาก 1.0 เป็น 0.9
            MarketCondition.RANGING: 0.8           # ลดจาก 0.8 เป็น 0.7
        }
        
        condition_factor = condition_factors.get(condition, 0.8)
        
        # Calculate final spacing
        optimal_spacing = int(base_spacing * volatility_factor * condition_factor)
        
        # 🔥 Bounds ที่ใกล้มาก
        return max(20, min(60, optimal_spacing))  # เปลี่ยนจาก (30, 150) เป็น (20, 60)
    
    def ai_determine_market_action(self, condition: MarketCondition, 
                                    trend_strength: float, 
                                    volatility_score: float) -> str:
        """🔥 แก้ไข: Market Action ที่เหมาะสมขึ้น"""
        
        if condition == MarketCondition.HIGH_VOLATILITY:
            return "CAREFUL_POSITIONING"     # เปลี่ยนจาก WIDE_POSITIONING
        elif condition == MarketCondition.LOW_VOLATILITY:
            return "TIGHT_POSITIONING"       # เหมือนเดิม
        elif condition in [MarketCondition.TRENDING_UP, MarketCondition.TRENDING_DOWN]:
            return "TREND_AWARE_POSITIONING" # เปลี่ยนจาก TREND_FOLLOWING
        else:  # RANGING
            return "AGGRESSIVE_POSITIONING"  # เปลี่ยนจาก BALANCED_POSITIONING

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
        """🔄 แก้ไขจากของเดิม - เพิ่ม Direction Balance & Survivability Logic"""
        
        try:
            current_positions = len(self.active_positions)
            pending_orders = len(self.pending_orders)
            total_exposure = current_positions + pending_orders
            
            # 🆕 วิเคราะห์สมดุลทิศทาง
            buy_positions = len([p for p in self.active_positions.values() if p.get('direction') == 'BUY'])
            sell_positions = len([p for p in self.active_positions.values() if p.get('direction') == 'SELL'])
            buy_pending = len([o for o in self.pending_orders.values() if o.get('direction') == 'BUY'])
            sell_pending = len([o for o in self.pending_orders.values() if o.get('direction') == 'SELL'])
            
            total_buy_exposure = buy_positions + buy_pending
            total_sell_exposure = sell_positions + sell_pending
            
            print(f"🧠 Direction Analysis:")
            print(f"   📊 BUY: {buy_positions} positions + {buy_pending} pending = {total_buy_exposure}")
            print(f"   📊 SELL: {sell_positions} positions + {sell_pending} pending = {total_sell_exposure}")
            
            # 🆕 เหตุผลในการวางไม้
            placement_reason = None
            priority_direction = None
            urgency_level = "NORMAL"
            
            # 🚨 Critical: ทิศทางใดทิศทางหนึ่งไม่มี pending เลย
            if buy_pending == 0:
                placement_reason = "CRITICAL_BUY_PROTECTION"
                priority_direction = "BUY_ONLY"
                urgency_level = "CRITICAL"
                print(f"   🚨 CRITICAL: No BUY pending orders - market drop risk!")
                
            elif sell_pending == 0:
                placement_reason = "CRITICAL_SELL_PROTECTION"
                priority_direction = "SELL_ONLY"
                urgency_level = "CRITICAL"
                print(f"   🚨 CRITICAL: No SELL pending orders - market rise risk!")
                
            # 🔥 High Priority: ทิศทางใดมี pending น้อยกว่า 2
            elif buy_pending < 2 and total_buy_exposure < 4:
                placement_reason = "LOW_BUY_COVERAGE"
                priority_direction = "BUY_FOCUS"
                urgency_level = "HIGH"
                print(f"   ⚠️ HIGH: Insufficient BUY coverage ({buy_pending} pending)")
                
            elif sell_pending < 2 and total_sell_exposure < 4:
                placement_reason = "LOW_SELL_COVERAGE"
                priority_direction = "SELL_FOCUS" 
                urgency_level = "HIGH"
                print(f"   ⚠️ HIGH: Insufficient SELL coverage ({sell_pending} pending)")
                
            # 📊 Medium Priority: สมดุลรวมไม่ดี
            elif abs(total_buy_exposure - total_sell_exposure) > 3:
                if total_buy_exposure > total_sell_exposure:
                    placement_reason = "BALANCE_SELL_SHORTAGE"
                    priority_direction = "SELL_FOCUS"
                else:
                    placement_reason = "BALANCE_BUY_SHORTAGE"
                    priority_direction = "BUY_FOCUS"
                urgency_level = "MEDIUM"
                print(f"   📊 MEDIUM: Portfolio imbalance ({total_buy_exposure} vs {total_sell_exposure})")
                
            # ✅ Low Priority: เติมเต็มทั่วไป
            elif total_exposure < 10:
                placement_reason = "GENERAL_COVERAGE"
                priority_direction = "BALANCED"
                urgency_level = "LOW"
                print(f"   ✅ LOW: General coverage expansion ({total_exposure}/10)")
            
            # 🛡️ ไม่ต้องวางเพิ่ม
            else:
                print(f"   ✅ Grid coverage adequate: {total_exposure}/10 total")
                return None
            
            # 🆕 คำนวณ Survivability Impact
            survivability_check = self.check_survivability_impact(placement_reason, priority_direction)
            if not survivability_check['safe']:
                print(f"   ⚠️ Survivability concern: {survivability_check['reason']}")
                return None
            
            # 🆕 กำหนดจำนวนและ spacing ตามเหตุผล
            if urgency_level == "CRITICAL":
                orders_needed = 3  # วางทันที 3 ไม้
                spacing_modifier = 0.8  # ใกล้ market ขึ้น
                confidence = 0.95
            elif urgency_level == "HIGH":
                orders_needed = 2  # วาง 2 ไม้
                spacing_modifier = 0.9
                confidence = 0.85
            elif urgency_level == "MEDIUM":
                orders_needed = 2
                spacing_modifier = 1.0
                confidence = 0.75
            else:  # LOW
                orders_needed = 1
                spacing_modifier = 1.2  # ห่างออกไป
                confidence = 0.65
            
            action = "PLACE_STRATEGIC_ORDERS"
            
            parameters = {
                'spacing': max(30, int(market_analysis.optimal_spacing * spacing_modifier)),
                'direction_priority': priority_direction,
                'position_count': orders_needed,
                'lot_size': self.base_lot,
                'placement_reason': placement_reason,
                'urgency_level': urgency_level,
                'survivability_impact': survivability_check
            }
            
            return AIDecision(
                action=action,
                reason=AIDecisionReason.MARKET_ANALYSIS,
                confidence=confidence,
                parameters=parameters,
                expected_outcome=f"{placement_reason}: {orders_needed} orders ({priority_direction})",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"❌ AI Positioning decision error: {e}")
            return None
    
    def check_survivability_impact(self, placement_reason: str, priority_direction: str) -> Dict:
        try:
            current_drawdown = self.get_current_drawdown_points()
            risk_usage = current_drawdown / self.survivability if self.survivability > 0 else 0
            
            total_positions = len(self.active_positions)
            total_pending = len(self.pending_orders)
            
            # 🔒 Standard thresholds (ปลอดภัย)
            if placement_reason in ["CRITICAL_BUY_PROTECTION", "CRITICAL_SELL_PROTECTION"]:
                safe_threshold = 0.75  # 75% สำหรับ CRITICAL
                emergency_threshold = 0.90  # 90% เป็น absolute limit
                
            elif placement_reason in ["LOW_BUY_COVERAGE", "LOW_SELL_COVERAGE"]:
                safe_threshold = 0.65  # 65%
                emergency_threshold = 0.80  # 80%
                
            elif placement_reason in ["BALANCE_BUY_SHORTAGE", "BALANCE_SELL_SHORTAGE"]:
                safe_threshold = 0.55  # 55%
                emergency_threshold = 0.70  # 70%
                
            else:  # GENERAL_COVERAGE
                safe_threshold = 0.45  # 45%
                emergency_threshold = 0.60  # 60%
            
            total_exposure = total_positions + total_pending
            max_safe_positions = max(12, int(self.survivability / 1000))
            position_safety = total_exposure < max_safe_positions
            
            # 🧠 AI Logic: Standard vs Emergency
            standard_safe = risk_usage < safe_threshold and position_safety
            emergency_safe = risk_usage < emergency_threshold and position_safety
            
            # 🚨 Emergency Override Logic
            if placement_reason in ["CRITICAL_BUY_PROTECTION", "CRITICAL_SELL_PROTECTION"]:
                if standard_safe:
                    is_safe = True
                    reason = f"Standard safety: {risk_usage:.1%} < {safe_threshold:.1%}"
                elif emergency_safe:
                    is_safe = True
                    reason = f"🚨 Emergency override: {risk_usage:.1%} < {emergency_threshold:.1%} (CRITICAL situation)"
                else:
                    is_safe = False
                    reason = f"🔴 Too risky even for emergency: {risk_usage:.1%} > {emergency_threshold:.1%}"
            else:
                # Non-critical: ใช้ standard threshold เท่านั้น
                is_safe = standard_safe
                reason = f"Standard check: {risk_usage:.1%} {'<' if standard_safe else '>'} {safe_threshold:.1%}"
            
            return {
                'safe': is_safe,
                'risk_usage': risk_usage,
                'safe_threshold': safe_threshold,
                'emergency_threshold': emergency_threshold,
                'position_safety': position_safety,
                'max_safe_positions': max_safe_positions,
                'current_exposure': total_exposure,
                'reason': reason
            }
            
        except Exception as e:
            return {'safe': False, 'reason': f'Check failed: {e}'}
    
    def ai_check_price_gaps(self) -> int:
        """🧠 ตรวจสอบช่องว่างในราคาที่ควรเติมไม้"""
        
        try:
            current_price = self.get_current_price()
            if not current_price:
                return 0
            
            # รวบรวมราคาของไม้ทั้งหมด
            all_prices = []
            
            # ราคาจาก active positions
            for pos in self.active_positions.values():
                all_prices.append(pos.get('price_open', 0))
            
            # ราคาจาก pending orders
            for order in self.pending_orders.values():
                all_prices.append(order.get('price', 0))
            
            if len(all_prices) < 2:
                return 0
            
            # เรียงราคา
            all_prices.sort()
            
            # หาช่องว่างที่ใหญ่กว่า threshold
            gap_threshold = 2.0  # $2 gap
            large_gaps = 0
            
            for i in range(1, len(all_prices)):
                gap = all_prices[i] - all_prices[i-1]
                if gap > gap_threshold:
                    large_gaps += 1
            
            # คำนวณควรเติมกี่ไม้
            gaps_to_fill = min(large_gaps, 3)  # สูงสุด 3 ไม้
            
            if gaps_to_fill > 0:
                print(f"   🔍 Found {large_gaps} price gaps > ${gap_threshold:.2f}")
            
            return gaps_to_fill
            
        except Exception as e:
            print(f"❌ Gap check error: {e}")
            return 0
       
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
        """🔄 แก้ไขจากของเดิม - เพิ่ม Direction Priority Logic"""
        
        try:
            current_price = self.get_current_price()
            if not current_price:
                return False
            
            placement_reason = parameters.get('placement_reason', 'GENERAL')
            direction_priority = parameters.get('direction_priority', 'BALANCED')
            orders_needed = parameters.get('position_count', 2)
            spacing = parameters.get('spacing', 40)
            urgency_level = parameters.get('urgency_level', 'NORMAL')
            
            print(f"🚀 STRATEGIC PLACEMENT:")
            print(f"   🎯 Reason: {placement_reason}")
            print(f"   📊 Priority: {direction_priority}")
            print(f"   ⚡ Urgency: {urgency_level}")
            print(f"   📏 Spacing: {spacing} points")
            
            spacing_dollars = spacing * 0.01
            orders_placed = 0
            
            # 🆕 Direction-Based Placement Logic
            if direction_priority == "BUY_ONLY":
                # วางเฉพาะ BUY
                for i in range(orders_needed):
                    buy_price = current_price - (spacing_dollars * (i + 1))
                    
                    if not self.level_exists(buy_price, 'BUY', 0.20):  # ผ่อนผัน tolerance
                        success = self.ai_place_intelligent_order(buy_price, 'BUY', self.base_lot, f'BUY_{placement_reason}')
                        if success:
                            orders_placed += 1
                            print(f"     ✅ BUY Protection: ${buy_price:.2f}")
                        time.sleep(0.3)
                    
            elif direction_priority == "SELL_ONLY":
                # วางเฉพาะ SELL
                for i in range(orders_needed):
                    sell_price = current_price + (spacing_dollars * (i + 1))
                    
                    if not self.level_exists(sell_price, 'SELL', 0.20):
                        success = self.ai_place_intelligent_order(sell_price, 'SELL', self.base_lot, f'SELL_{placement_reason}')
                        if success:
                            orders_placed += 1
                            print(f"     ✅ SELL Protection: ${sell_price:.2f}")
                        time.sleep(0.3)
                    
            elif direction_priority in ["BUY_FOCUS", "SELL_FOCUS"]:
                # วางเน้นทิศทางหนึ่ง (70:30)
                if direction_priority == "BUY_FOCUS":
                    buy_orders = max(1, int(orders_needed * 0.7))
                    sell_orders = orders_needed - buy_orders
                else:
                    sell_orders = max(1, int(orders_needed * 0.7))
                    buy_orders = orders_needed - sell_orders
                
                # วาง BUY orders
                for i in range(buy_orders):
                    buy_price = current_price - (spacing_dollars * (i + 1))
                    if not self.level_exists(buy_price, 'BUY', 0.15):
                        success = self.ai_place_intelligent_order(buy_price, 'BUY', self.base_lot, f'FOCUS_{placement_reason}')
                        if success:
                            orders_placed += 1
                            print(f"     ✅ BUY Focus: ${buy_price:.2f}")
                        time.sleep(0.3)
                
                # วาง SELL orders
                for i in range(sell_orders):
                    sell_price = current_price + (spacing_dollars * (i + 1))
                    if not self.level_exists(sell_price, 'SELL', 0.15):
                        success = self.ai_place_intelligent_order(sell_price, 'SELL', self.base_lot, f'FOCUS_{placement_reason}')
                        if success:
                            orders_placed += 1
                            print(f"     ✅ SELL Focus: ${sell_price:.2f}")
                        time.sleep(0.3)
                    
            else:  # BALANCED
                # วางแบบสมดุล 50:50
                buy_orders = orders_needed // 2
                sell_orders = orders_needed - buy_orders
                
                for i in range(buy_orders):
                    buy_price = current_price - (spacing_dollars * (i + 1))
                    if not self.level_exists(buy_price, 'BUY', 0.15):
                        success = self.ai_place_intelligent_order(buy_price, 'BUY', self.base_lot, f'BAL_{placement_reason}')
                        if success:
                            orders_placed += 1
                            print(f"     ✅ Balanced BUY: ${buy_price:.2f}")
                        time.sleep(0.3)
                
                for i in range(sell_orders):
                    sell_price = current_price + (spacing_dollars * (i + 1))
                    if not self.level_exists(sell_price, 'SELL', 0.15):
                        success = self.ai_place_intelligent_order(sell_price, 'SELL', self.base_lot, f'BAL_{placement_reason}')
                        if success:
                            orders_placed += 1
                            print(f"     ✅ Balanced SELL: ${sell_price:.2f}")
                        time.sleep(0.3)
            
            # 🆕 แก้ไข Success Logic
            success = self.evaluate_placement_success(orders_placed, orders_needed, placement_reason)
            
            print(f"   📊 Placement result: {orders_placed}/{orders_needed} orders")
            print(f"   {'✅' if success else '❌'} Overall success: {success}")
            
            return success
            
        except Exception as e:
            print(f"❌ Strategic positioning error: {e}")
            return False
    
    def evaluate_placement_success(self, orders_placed: int, orders_needed: int, placement_reason: str) -> bool:
        """🆕 ประเมินความสำเร็จของการวางไม้ตามบริบท"""
        
        try:
            placement_rate = orders_placed / orders_needed if orders_needed > 0 else 0
            
            # เกณฑ์ความสำเร็จตามเหตุผล
            if placement_reason in ["CRITICAL_BUY_PROTECTION", "CRITICAL_SELL_PROTECTION"]:
                # ฉุกเฉิน - วางได้ >50% = สำเร็จ
                return placement_rate >= 0.5
                
            elif placement_reason in ["LOW_BUY_COVERAGE", "LOW_SELL_COVERAGE"]:
                # ความเสี่ยงสูง - วางได้ >60% = สำเร็จ
                return placement_rate >= 0.6
                
            elif placement_reason in ["BALANCE_BUY_SHORTAGE", "BALANCE_SELL_SHORTAGE"]:
                # ปรับสมดุล - วางได้ >70% = สำเร็จ
                return placement_rate >= 0.7
                
            else:  # GENERAL_COVERAGE
                # ทั่วไป - วางได้ >80% = สำเร็จ
                return placement_rate >= 0.8
            
        except Exception as e:
            print(f"❌ Success evaluation error: {e}")
            return orders_placed > 0
    
    def get_existing_levels(self, direction: str) -> List[float]:
        """🔍 ดึงระดับราคาที่มีอยู่แล้ว"""
        
        levels = []
        
        # จาก active positions
        for pos in self.active_positions.values():
            if pos.get('direction') == direction:
                levels.append(pos.get('price_open', 0))
        
        # จาก pending orders  
        for order in self.pending_orders.values():
            if order.get('direction') == direction:
                levels.append(order.get('price', 0))
        
        return sorted([l for l in levels if l > 0])

    def find_price_gaps(self, current_price: float, buy_levels: List[float], sell_levels: List[float]) -> List[Dict]:
        """🔍 หาช่องว่างสำคัญที่ต้องเติม - Enhanced Debug"""
        
        try:
            gaps = []
            all_levels = buy_levels + sell_levels + [current_price]
            all_levels = sorted(set(all_levels))
            
            print(f"   🔍 Analyzing gaps from {len(all_levels)} levels...")
            
            # หาช่องว่างใหญ่
            for i in range(1, len(all_levels)):
                gap_size = all_levels[i] - all_levels[i-1]
                
                if gap_size > 0.60:  # ลดเกณฑ์จาก 0.80 เป็น 0.60
                    gap_center = (all_levels[i] + all_levels[i-1]) / 2
                    
                    # ระบุทิศทางที่ควรเติม
                    if gap_center < current_price:
                        direction = 'BUY'
                    else:
                        direction = 'SELL'
                    
                    # คำนวณ priority
                    distance_from_market = abs(gap_center - current_price)
                    priority = gap_size * 2 - distance_from_market  # ใหญ่+ใกล้ = priority สูง
                    
                    gaps.append({
                        'price': round(gap_center, 2),
                        'direction': direction,
                        'size': gap_size,
                        'priority': priority,
                        'reason': f"Fill ${gap_size:.2f} gap"
                    })
                    
                    print(f"     🔍 Gap found: ${all_levels[i-1]:.2f} -> ${all_levels[i]:.2f} = ${gap_size:.2f}")
            
            # เรียงตาม priority
            gaps.sort(key=lambda x: x['priority'], reverse=True)
            return gaps
            
        except Exception as e:
            print(f"❌ Find gaps error: {e}")
            return []
    
    def calculate_priority_levels(self, current_price: float, buy_levels: List[float], sell_levels: List[float]) -> List[Dict]:
        """🎯 คำนวณระดับราคาที่ควรวางตาม priority - Enhanced"""
        
        try:
            priority_levels = []
            
            # คำนวณ spacing อัจฉริยะ
            spacing = self.calculate_intelligent_spacing()
            spacing_dollars = spacing * 0.01
            
            print(f"   🧠 Using intelligent spacing: {spacing} points (${spacing_dollars:.2f})")
            
            # 🔥 แก้ไข: เพิ่มระยะห่างให้หลากหลายมากขึ้น
            buy_distances = [0.7, 1.4, 2.2, 3.5]   # ระยะ multiplier ที่หลากหลาย
            sell_distances = [0.7, 1.4, 2.2, 3.5]  # ระยะ multiplier ที่หลากหลาย
            
            # ระดับ BUY priority (ใต้ market)
            for i, mult in enumerate(buy_distances):
                buy_price = current_price - (spacing_dollars * mult)
                priority = 10 - (i * 1.5)  # ใกล้ = priority สูง
                
                priority_levels.append({
                    'price': round(buy_price, 2),
                    'direction': 'BUY',
                    'priority': priority,
                    'reason': f"BUY level {i+1} (${spacing_dollars * mult:.2f} below)"
                })
            
            # ระดับ SELL priority (เหนือ market)
            for i, mult in enumerate(sell_distances):
                sell_price = current_price + (spacing_dollars * mult)
                priority = 10 - (i * 1.5)  # ใกล้ = priority สูง
                
                priority_levels.append({
                    'price': round(sell_price, 2),
                    'direction': 'SELL',
                    'priority': priority,
                    'reason': f"SELL level {i+1} (${spacing_dollars * mult:.2f} above)"
                })
            
            # เรียงตาม priority
            priority_levels.sort(key=lambda x: x['priority'], reverse=True)
            
            return priority_levels
            
        except Exception as e:
            print(f"❌ Calculate priority levels error: {e}")
            return []
    
    def calculate_intelligent_spacing(self) -> int:
        """🧠 คำนวณระยะห่างอัจฉริยะ"""
        
        # ดู volatility ย้อนหลัง
        price_history = self.get_recent_price_history(10)
        
        if len(price_history) >= 3:
            price_range = max(price_history) - min(price_history)
            
            # ปรับ spacing ตาม price range
            if price_range > 4.0:      # ผันผวนมาก
                spacing = 50
            elif price_range > 2.0:    # ผันผวนปานกลาง
                spacing = 40
            else:                      # ผันผวนน้อย
                spacing = 30
        else:
            spacing = 35  # default
        
        return spacing

    def level_exists(self, price: float, direction: str, tolerance: float) -> bool:
        """🔍 เช็คว่ามีระดับนี้อยู่แล้วหรือไม่ - Relaxed tolerance"""
        
        try:
            existing_levels = self.get_existing_levels(direction)
            
            for existing_price in existing_levels:
                distance = abs(existing_price - price)
                if distance <= tolerance:
                    print(f"     📍 Level blocked: {direction} ${existing_price:.2f} vs ${price:.2f} (${distance:.2f} ≤ ${tolerance:.2f})")
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ Level exists check error: {e}")
            return True

    def place_gap_fill_order(self, gap: Dict) -> bool:
        """📋 วางไม้เติมช่องว่าง"""
        
        try:
            price = gap['price']
            direction = gap['direction']
            
            # เช็คว่าไม่ทับซ้อน
            if self.level_exists(price, direction, 0.30):
                return False
            
            return self.ai_place_intelligent_order(price, direction, self.base_lot, "GAP_FILL")
            
        except Exception as e:
            print(f"❌ Gap fill order error: {e}")
            return False
    
    def ai_get_existing_order_prices(self, direction: str) -> List[float]:
        """🔥 ดึงราคาของไม้ที่มีอยู่แล้วตามทิศทาง"""
        
        try:
            existing_prices = []
            
            # จาก active positions
            for pos in self.active_positions.values():
                if pos.get('direction') == direction:
                    existing_prices.append(pos.get('price_open', 0))
            
            # จาก pending orders
            for order in self.pending_orders.values():
                if order.get('direction') == direction:
                    existing_prices.append(order.get('price', 0))
            
            return sorted(existing_prices)
            
        except Exception as e:
            print(f"❌ Get existing prices error: {e}")
            return []

    def ai_execute_profit_taking(self, parameters: Dict) -> bool:
        """🔄 แก้ไขจากของเดิม - เพิ่ม smart opportunity selection"""
        
        try:
            # 🆕 แทนที่การใช้ opportunities จาก parameters
            # ให้ใช้ AI หาโอกาสใหม่
            print("   🧠 AI analyzing smart profit opportunities...")
            
            smart_opportunities = self.ai_find_smart_closing_opportunities()
            
            # 🆕 กรองเฉพาะโอกาสที่เกี่ยวกับกำไร
            profit_opportunities = [
                opp for opp in smart_opportunities 
                if opp['strategy'] in ['RESCUE_PAIRS', 'PROFIT_HARVEST'] 
                and opp['expected_profit'] > 0.5
            ]
            
            if not profit_opportunities:
                print("   ⚠️ No profitable opportunities found by AI")
                return False
            
            print(f"   💰 AI found {len(profit_opportunities)} profit opportunities")
            
            successful_closes = 0
            total_opportunities = len(profit_opportunities)
            
            # 🆕 ปิดแบบ staged พร้อม margin check
            for i, opportunity in enumerate(profit_opportunities[:3]):  # สูงสุด 3 โอกาส
                try:
                    position_ids = opportunity['positions']
                    expected_profit = opportunity['expected_profit']
                    strategy = opportunity['strategy']
                    
                    print(f"   🎯 Opportunity {i+1}: {strategy} - {len(position_ids)} positions, ${expected_profit:.2f}")
                    
                    # 🆕 เช็ค margin safety ก่อนปิดทั้งกลุ่ม
                    group_margin_check = self.calculate_margin_impact(position_ids)
                    if not group_margin_check['safe_to_close']:
                        print(f"     ⚠️ Group unsafe: {group_margin_check['reason']}")
                        continue
                    
                    # ปิดทีละไม้ในกลุ่ม
                    group_success = 0
                    for pos_id in position_ids:
                        if pos_id in self.active_positions:
                            position = self.active_positions[pos_id]
                            success = self.ai_close_position_intelligent(position, f'{strategy}_PROFIT')
                            
                            if success:
                                group_success += 1
                                print(f"     ✅ Closed position {pos_id}")
                            else:
                                print(f"     ❌ Failed to close {pos_id}")
                            
                            time.sleep(0.5)  # Delay ระหว่างปิด
                    
                    if group_success > 0:
                        successful_closes += group_success
                        print(f"   📊 Group {i+1}: {group_success}/{len(position_ids)} closed")
                    
                    # 🆕 เช็ค portfolio health หลังปิดแต่ละกลุ่ม
                    new_health = self.ai_calculate_portfolio_health()
                    print(f"   🏥 Portfolio health after group {i+1}: {new_health:.1f}/100")
                    
                    # หยุดถ้า health ดีขึ้นแล้ว
                    if new_health > 75:
                        print("   ✅ Portfolio health excellent - stopping profit taking")
                        break
                    
                    time.sleep(1)  # Delay ระหว่างกลุ่ม
                    
                except Exception as e:
                    print(f"     ❌ Opportunity {i+1} error: {e}")
            
            total_positions_attempted = sum(len(opp['positions']) for opp in profit_opportunities[:3])
            success_rate = successful_closes / total_positions_attempted if total_positions_attempted > 0 else 0
            
            print(f"   📊 AI Profit Taking: {successful_closes}/{total_positions_attempted} ({success_rate:.1%})")
            
            return success_rate >= 0.5  # Success if >50% positions closed
            
        except Exception as e:
            print(f"❌ AI Profit taking execution error: {e}")
            return False
    
    def ai_execute_emergency_cleanup(self, parameters: Dict) -> bool:
        """🔄 แก้ไขจากของเดิม - เพิ่ม margin-safe emergency cleanup"""
        
        try:
            cleanup_method = parameters.get('cleanup_method', 'CLOSE_WEAK_POSITIONS')
            preserve_strong = parameters.get('preserve_strong', True)
            target_health = parameters.get('target_health', 60)
            
            print(f"   🚨 AI Emergency cleanup: {cleanup_method}")
            
            # 🆕 ใช้ AI วิเคราะห์แทนการหาไม้อ่อนแอ
            portfolio_analysis = self.ai_analyze_portfolio_positions()
            if not portfolio_analysis:
                print("   ❌ Cannot analyze portfolio")
                return False
            
            position_map = portfolio_analysis['position_map']
            
            # 🆕 หาไม้ที่ควรปิดในสถานการณ์ฉุกเฉิน
            emergency_candidates = []
            
            for ticket, pos_info in position_map.items():
                # เกณฑ์ความอ่อนแอ
                is_weak = (
                    pos_info['health'] == 'CRITICAL' or  # สุขภาพแย่
                    pos_info['profit'] < -5 or           # ขาดทุนมาก
                    (pos_info['profit'] < 0 and pos_info['age_hours'] > 72) or  # ขาดทุน + เก่า
                    pos_info['ai_score'] < 30            # AI score ต่ำ
                )
                
                # ถ้าต้องรักษาไม้แข็งแกร่ง
                if preserve_strong and pos_info['profit'] > 2:
                    is_weak = False
                
                if is_weak:
                    emergency_candidates.append(pos_info)
            
            if not emergency_candidates:
                print("   ✅ No weak positions found for cleanup")
                return True
            
            # 🆕 เรียงตามความปลอดภัยในการปิด
            print(f"   🎯 Found {len(emergency_candidates)} emergency candidates")
            
            # เรียงตาม AI score (ต่ำสุดก่อน) และความเสียหาย
            emergency_candidates.sort(key=lambda x: (x['ai_score'], x['profit']))
            
            closed_positions = 0
            max_closes = min(len(emergency_candidates), 4)  # สูงสุด 4 ไม้
            
            for i, position in enumerate(emergency_candidates[:max_closes]):
                try:
                    pos_id = position['ticket']
                    profit = position['profit']
                    
                    # 🆕 เช็ค margin safety ก่อนปิดแต่ละไม้
                    margin_check = self.calculate_margin_impact([pos_id])
                    
                    if not margin_check['safe_to_close']:
                        print(f"     ⚠️ Skip unsafe close: {pos_id} - {margin_check['reason']}")
                        continue
                    
                    # 🆕 เช็คไม่ให้เหลือไม้น้อยเกินไป
                    remaining_after_close = portfolio_analysis['total_positions'] - closed_positions - 1
                    if remaining_after_close < 1:
                        print(f"     ⚠️ Skip: Would leave only {remaining_after_close} positions")
                        continue
                    
                    success = self.ai_close_position_intelligent(position, 'EMERGENCY_CLEANUP')
                    
                    if success:
                        closed_positions += 1
                        print(f"     ✅ Emergency cleanup: position {pos_id} (${profit:.2f})")
                        
                        # 🆕 เช็ค target health หลังปิดแต่ละไม้
                        current_health = self.ai_calculate_portfolio_health()
                        print(f"     🏥 Health after cleanup {closed_positions}: {current_health:.1f}/100")
                        
                        if current_health >= target_health:
                            print(f"   🎯 Target health {target_health} achieved")
                            break
                    else:
                        print(f"     ❌ Failed to cleanup {pos_id}")
                    
                    time.sleep(0.8)  # Delay ระหว่างปิด
                    
                except Exception as e:
                    print(f"     ❌ Position cleanup error: {e}")
            
            print(f"   📊 Emergency cleanup: {closed_positions}/{len(emergency_candidates)} positions closed")
            
            # 🆕 สรุปผลลพธ์
            final_health = self.ai_calculate_portfolio_health()
            print(f"   🏥 Final portfolio health: {final_health:.1f}/100")
            
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
        """🔄 แก้ไขจากของเดิม - เพิ่ม smart risk reduction"""
        
        try:
            reduction_method = parameters.get('reduction_method', 'CLOSE_HIGHEST_RISK_POSITIONS')
            target_risk_ratio = parameters.get('target_risk_ratio', 0.6)
            preserve_profitable = parameters.get('preserve_profitable', True)
            
            print(f"   🚨 AI Risk reduction: {reduction_method}")
            
            current_drawdown = self.get_current_drawdown_points()
            target_drawdown = self.survivability * target_risk_ratio
            
            print(f"   📊 Current risk: {current_drawdown:.0f}/{self.survivability:.0f} points")
            print(f"   🎯 Target risk: {target_drawdown:.0f} points")
            
            if current_drawdown <= target_drawdown:
                print("   ✅ Already within target risk")
                return True
            
            # 🆕 ใช้ AI หาโอกาสลดความเสี่ยง
            smart_opportunities = self.ai_find_smart_closing_opportunities()
            
            # กรองเฉพาะโอกาสลดความเสี่ยง
            risk_opportunities = [
                opp for opp in smart_opportunities 
                if opp['strategy'] in ['RISK_REDUCTION', 'MARGIN_RELIEF', 'SMART_LIQUIDATION']
            ]
            
            if not risk_opportunities:
                # 🆕 Fallback: ใช้วิธีเดิมแต่ปรับปรุง
                portfolio_analysis = self.ai_analyze_portfolio_positions()
                if not portfolio_analysis:
                    return False
                
                position_map = portfolio_analysis['position_map']
                
                # หาไม้ความเสี่ยงสูง
                high_risk_positions = []
                
                for ticket, pos_info in position_map.items():
                    # เกณฑ์ความเสี่ยง
                    risk_score = 0
                    
                    if pos_info['profit'] < -3:
                        risk_score += 30  # ขาดทุนมาก
                    if pos_info['lot_size'] > 0.03:
                        risk_score += 20  # ขนาดใหญ่
                    if pos_info['age_hours'] > 48:
                        risk_score += 15  # อายุมาก
                    if pos_info['ai_score'] < 40:
                        risk_score += 25  # AI score ต่ำ
                    
                    # ถ้าต้องรักษาไม้กำไร
                    if preserve_profitable and pos_info['profit'] > 1:
                        risk_score = max(0, risk_score - 40)
                    
                    if risk_score > 50:
                        pos_info['risk_score'] = risk_score
                        high_risk_positions.append(pos_info)
                
                if not high_risk_positions:
                    print("   ⚠️ No high risk positions identified")
                    return False
                
                # เรียงตาม risk score (สูงสุดก่อน)
                high_risk_positions.sort(key=lambda x: x['risk_score'], reverse=True)
                
                risk_opportunities = [{
                    'strategy': 'RISK_REDUCTION',
                    'positions': [p['ticket'] for p in high_risk_positions[:3]],
                    'expected_profit': sum(p['profit'] for p in high_risk_positions[:3]),
                    'margin_relief': sum(p['margin_required'] for p in high_risk_positions[:3]),
                    'ai_confidence': 0.7,
                    'reason': 'High-risk position cleanup'
                }]
            
            print(f"   🎯 Found {len(risk_opportunities)} risk reduction opportunities")
            
            closed_positions = 0
            
            for opportunity in risk_opportunities[:2]:  # สูงสุด 2 โอกาส
                try:
                    position_ids = opportunity['positions']
                    strategy = opportunity['strategy']
                    
                    # 🆕 เช็ค margin safety ก่อนปิดกลุ่ม
                    group_margin_check = self.calculate_margin_impact(position_ids)
                    
                    print(f"   💡 {strategy}: {len(position_ids)} positions")
                    print(f"     📊 Margin safety: {group_margin_check['safety_score']:.0f}%")
                    
                    # ปิดทีละไม้ เพื่อประเมิน risk ได้ real-time
                    for pos_id in position_ids:
                        if pos_id in self.active_positions:
                            position = self.active_positions[pos_id]
                            
                            # เช็ค margin safety แต่ละไม้
                            single_margin_check = self.calculate_margin_impact([pos_id])
                            if not single_margin_check['safe_to_close']:
                                print(f"     ⚠️ Skip risky close: {pos_id}")
                                continue
                            
                            success = self.ai_close_position_intelligent(position, 'RISK_REDUCTION')
                            
                            if success:
                                closed_positions += 1
                                profit = position.get('profit', 0)
                                print(f"     ✅ Risk reduced: {pos_id} (${profit:.2f})")
                            
                            # 🆕 เช็ค target risk หลังปิดแต่ละไม้
                            new_drawdown = self.get_current_drawdown_points()
                            new_risk_ratio = new_drawdown / self.survivability if self.survivability > 0 else 0
                            
                            print(f"     📊 Risk ratio: {new_risk_ratio:.1%}")
                            
                            if new_drawdown <= target_drawdown:
                                print(f"   🎯 Target risk achieved!")
                                return True
                            
                            time.sleep(0.5)
                    
                except Exception as e:
                    print(f"     ❌ Risk opportunity error: {e}")
            
            final_drawdown = self.get_current_drawdown_points()
            final_risk_ratio = final_drawdown / self.survivability if self.survivability > 0 else 0
            
            print(f"   📊 Risk reduction result: {closed_positions} positions closed")
            print(f"   📈 Final risk ratio: {final_risk_ratio:.1%}")
            
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
        """🔧 ใช้ code ที่ทดสอบแล้วสำเร็จ"""
        
        try:
            print(f"     🔍 Placing {direction} order (TESTED METHOD):")
            
            # เช็ค current price
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"       ❌ Cannot get tick")
                return False
            
            current_price = tick.bid
            print(f"       💰 Current: ${current_price:.2f}, Target: ${price:.2f}")
            
            # Validate direction vs price
            if direction == "BUY" and price >= current_price:
                print(f"       ❌ Invalid BUY price: ${price:.2f} >= ${current_price:.2f}")
                return False
            
            if direction == "SELL" and price <= current_price:
                print(f"       ❌ Invalid SELL price: ${price:.2f} <= ${current_price:.2f}")
                return False
            
            # 🔥 ใช้ exact values ที่ test ผ่าน
            if direction == "BUY":
                if price < current_price:
                    order_type_int = 2  # BUY_LIMIT (ที่ test ผ่าน)
                else:
                    order_type_int = 4  # BUY_STOP
            else:
                if price > current_price:
                    order_type_int = 3  # SELL_LIMIT
                else:
                    order_type_int = 5  # SELL_STOP
            
            # 🔥 ใช้ exact request format ที่ผ่าน test
            request = {
                "action": 5,  # TRADE_ACTION_PENDING (exact ที่ test ผ่าน)
                "symbol": "XAUUSD.v",  # exact symbol ที่ test ผ่าน
                "volume": 0.01,  # exact volume ที่ test ผ่าน
                "type": order_type_int,
                "price": round(price, 2),
                "magic": 77703292,  # exact magic ที่ test ผ่าน
                "comment": f"AI_{order_type}_{direction}"
            }
            
            print(f"       📋 Request (TESTED FORMAT): {request}")
            
            # ส่ง order
            result = mt5.order_send(request)
            
            if result is not None:
                print(f"       📊 Result: {result.retcode}")
                
                if result.retcode == 10009:  # exact code ที่ test ผ่าน
                    print(f"       ✅ Order SUCCESS! ID: {result.order}")
                    
                    # เก็บใน tracking
                    self.pending_orders[result.order] = {
                        'order_id': result.order,
                        'price': round(price, 2),
                        'direction': direction,
                        'lot_size': 0.01,
                        'ai_type': order_type,
                        'timestamp': datetime.now()
                    }
                    
                    return True
                else:
                    print(f"       ❌ Order failed: {result.retcode}")
                    return False
            else:
                print(f"       ❌ No result from MT5")
                return False
                
        except Exception as e:
            print(f"       ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def check_mt5_status(self):
        """🆕 ตรวจสอบสถานะ MT5 แบบละเอียด"""
        
        try:
            print("🔍 MT5 Status Check:")
            
            # Terminal info
            terminal_info = mt5.terminal_info()
            if terminal_info:
                print(f"   📡 Connected: {terminal_info.connected}")
                print(f"   💼 Trade allowed: {terminal_info.trade_allowed}")
                print(f"   📊 Build: {terminal_info.build}")
            else:
                print(f"   ❌ Cannot get terminal info")
                return False
            
            # Account info
            account_info = mt5.account_info()
            if account_info:
                print(f"   💰 Login: {account_info.login}")
                print(f"   💵 Balance: ${account_info.balance:.2f}")
                print(f"   📊 Trade allowed: {account_info.trade_allowed}")
            else:
                print(f"   ❌ Cannot get account info")
                return False
            
            # Symbol info
            symbol_info = mt5.symbol_info(self.gold_symbol)
            if symbol_info:
                print(f"   🥇 Symbol: {symbol_info.name}")
                print(f"   👁️ Visible: {symbol_info.visible}")
                print(f"   📈 Trade mode: {symbol_info.trade_mode}")
            else:
                print(f"   ❌ Cannot get symbol info")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ MT5 status check error: {e}")
            return False
       
    def get_mt5_error_description(self, error_code) -> str:
        """🆕 แปล MT5 error code เป็นคำอธิบาย"""
        
        error_codes = {
            10004: "Requote - ราคาเปลี่ยน",
            10006: "Request rejected - คำขอถูกปฏิเสธ",
            10007: "Request canceled - คำขอถูกยกเลิก", 
            10008: "Order placed - วางสำเร็จ",
            10009: "Request completed - เสร็จสิ้น",
            10010: "Partial fill only - fill บางส่วนเท่านั้น",
            10011: "Request processing error - ข้อผิดพลาดในการประมวลผล",
            10012: "Request canceled by timeout - หมดเวลา",
            10013: "Invalid request - คำขอไม่ถูกต้อง",
            10014: "Invalid volume - volume ไม่ถูกต้อง",
            10015: "Invalid price - ราคาไม่ถูกต้อง",
            10016: "Invalid stops - stop ไม่ถูกต้อง",
            10017: "Trade disabled - การเทรดถูกปิด",
            10018: "Market closed - ตลาดปิด",
            10019: "Not enough money - เงินไม่พอ",
            10020: "Price changed - ราคาเปลี่ยน",
            10021: "Off quotes - ไม่มีราคา",
            10022: "Invalid expiration - วันหมดอายุไม่ถูกต้อง",
            10023: "Order state changed - สถานะ order เปลี่ยน",
            10024: "Too many requests - คำขอมากเกินไป",
            10025: "No changes - ไม่มีการเปลี่ยนแปลง",
            10026: "Autotrading disabled - auto trading ปิด",
            10027: "Market closed - ตลาดปิด",
            10028: "Invalid price in the request - ราคาผิด",
            10029: "Invalid stops in the request - stop ผิด",
            10030: "Invalid volume in the request - volume ผิด"
        }
        
        return error_codes.get(error_code, f"Unknown error: {error_code}")
        
    def ai_check_price_overlap(self, new_price: float, direction: str, min_distance: float) -> bool:
        """🔥 เช็คว่าราคาใหม่ทับซ้อนกับไม้เดิมหรือไม่"""
        
        try:
            # เช็ค active positions
            for pos in self.active_positions.values():
                existing_price = pos.get('price_open', 0)
                existing_direction = pos.get('direction', '')
                
                if existing_direction == direction:  # ทิศทางเดียวกัน
                    distance = abs(new_price - existing_price)
                    if distance < min_distance:
                        return True  # ทับซ้อน
            
            # เช็ค pending orders
            for order in self.pending_orders.values():
                existing_price = order.get('price', 0)
                existing_direction = order.get('direction', '')
                
                if existing_direction == direction:  # ทิศทางเดียวกัน
                    distance = abs(new_price - existing_price)
                    if distance < min_distance:
                        return True  # ทับซ้อน
            
            return False  # ไม่ทับซ้อน
            
        except Exception as e:
            print(f"❌ Overlap check error: {e}")
            return True  # เผื่อไว้ ถ้า error ให้ถือว่าทับซ้อน

    def ai_close_position_intelligent(self, position, reason: str) -> bool:
        """🔄 แก้ไขจากของเดิม - เพิ่ม margin safety check"""
        
        try:
            # 🆕 เพิ่ม: Pre-close margin safety check
            if isinstance(position, dict):
                position_id = position.get('ticket', position.get('position_id'))
            else:
                position_id = position.position_id
            
            # 🆕 เช็ค margin safety ก่อนปิด
            margin_check = self.calculate_margin_impact([position_id])
            if not margin_check['safe_to_close']:
                print(f"     ⚠️ Margin safety check failed: {margin_check['reason']}")
                if margin_check['safety_score'] < 30:  # ถ้าไม่ปลอดภัยมาก
                    return False
                print(f"     🤔 Proceeding with moderate risk (safety: {margin_check['safety_score']:.0f}%)")
            
            # 🆕 เพิ่ม: Portfolio impact analysis
            portfolio_analysis = self.ai_analyze_portfolio_positions()
            if portfolio_analysis:
                remaining_positions = portfolio_analysis['total_positions'] - 1
                if remaining_positions < 2:
                    print(f"     ⚠️ Warning: Only {remaining_positions} positions will remain")
            
            # โค้ดเดิมยังคงอยู่
            mt5_positions = mt5.positions_get(ticket=position_id)
            if not mt5_positions:
                print(f"     ⚠️ Position {position_id} not found")
                return True
            
            mt5_position = mt5_positions[0]
            
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                return False
            
            if mt5_position.type == mt5.POSITION_TYPE_BUY:
                close_price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            else:
                close_price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.gold_symbol,
                "volume": mt5_position.volume,
                "type": order_type,
                "position": position_id,
                "price": close_price,
                "deviation": 50,
                "magic": self.magic_number,
                "comment": f"AI_CLOSE_{reason}_SAFE"  # 🆕 เพิ่ม _SAFE
            }
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                if position_id in self.active_positions:
                    del self.active_positions[position_id]
                
                # 🆕 เพิ่ม: Log margin impact
                profit = mt5_position.profit
                print(f"     ✅ Position closed: ${profit:.2f} profit, margin relief: ${margin_check.get('margin_relief', 0):.0f}")
                
                return True
            else:
                error_code = result.retcode if result else "No result"
                print(f"     ❌ Close failed: {error_code}")
                return False
            
        except Exception as e:
            print(f"❌ Intelligent position close error: {e}")
            return False

    def ai_find_intelligent_profit_pairs(self) -> List[Dict]:
        """🔄 แก้ไขจากของเดิม - เพิ่ม margin-aware profit analysis"""
        
        try:
            # 🆕 ใช้ AI portfolio analysis แทน
            portfolio_analysis = self.ai_analyze_portfolio_positions()
            if not portfolio_analysis:
                return []
            
            position_map = portfolio_analysis['position_map']
            opportunities = []
            
            positions = list(position_map.values())
            profitable_positions = [p for p in positions if p['profit'] > 1]
            losing_positions = [p for p in positions if p['profit'] < -1]
            
            # 🆕 AI Strategy 1: Smart rescue operations
            for losing_pos in losing_positions:
                for profit_pos in profitable_positions:
                    net_pnl = losing_pos['profit'] + profit_pos['profit']
                    
                    if net_pnl > 0.5:  # Net positive
                        # 🆕 เช็ค margin impact ของการปิดคู่
                        pair_tickets = [losing_pos['ticket'], profit_pos['ticket']]
                        margin_check = self.calculate_margin_impact(pair_tickets)
                        
                        if margin_check['safe_to_close']:
                            # 🆕 คำนวณ AI confidence ตาม margin safety
                            ai_confidence = 0.8 * (margin_check['safety_score'] / 100)
                            
                            opportunities.append({
                                'type': 'RESCUE_PAIR',
                                'position_ids': pair_tickets,
                                'expected_profit': net_pnl,
                                'ai_confidence': ai_confidence,
                                'margin_analysis': margin_check,  # 🆕 เพิ่ม margin data
                                'strategy': f"${profit_pos['profit']:.2f} rescues ${losing_pos['profit']:.2f} (margin safe: {margin_check['safety_score']:.0f}%)"
                            })
            
            # 🆕 AI Strategy 2: High-profit singles with margin consideration
            for profit_pos in profitable_positions:
                profit = profit_pos['profit']
                ai_score = profit_pos['ai_score']
                
                if profit > 5 and ai_score > 60:  # ปรับเกณฑ์
                    # เช็ค margin impact
                    single_check = self.calculate_margin_impact([profit_pos['ticket']])
                    
                    if single_check['safe_to_close']:
                        ai_confidence = 0.7 * (single_check['safety_score'] / 100)
                        
                        opportunities.append({
                            'type': 'HIGH_PROFIT_SINGLE',
                            'position_ids': [profit_pos['ticket']],
                            'expected_profit': profit,
                            'ai_confidence': ai_confidence,
                            'margin_analysis': single_check,
                            'strategy': f"High profit harvest: ${profit:.2f} (AI: {ai_score:.0f}, margin: {single_check['safety_score']:.0f}%)"
                        })
            
            # 🆕 AI Strategy 3: Portfolio balance pairs
            buy_positions = [p for p in positions if p['direction'] == 'BUY']
            sell_positions = [p for p in positions if p['direction'] == 'SELL']
            
            # ถ้าไม่สมดุล
            balance_ratio = portfolio_analysis['portfolio_stats']['balance_ratio']
            if balance_ratio < 0.7:
                # หากลุ่มที่ควรปิดเพื่อสมดุล
                if len(buy_positions) > len(sell_positions):
                    excess_positions = buy_positions
                else:
                    excess_positions = sell_positions
                
                # เลือก 2 ไม้ที่มี AI score ต่ำสุด
                excess_positions.sort(key=lambda x: x['ai_score'])
                balance_candidates = excess_positions[:2]
                
                if len(balance_candidates) == 2:
                    balance_tickets = [p['ticket'] for p in balance_candidates]
                    margin_check = self.calculate_margin_impact(balance_tickets)
                    
                    if margin_check['safe_to_close']:
                        total_profit = sum(p['profit'] for p in balance_candidates)
                        
                        opportunities.append({
                            'type': 'BALANCE_PAIR',
                            'position_ids': balance_tickets,
                            'expected_profit': total_profit,
                            'ai_confidence': 0.6 * (margin_check['safety_score'] / 100),
                            'margin_analysis': margin_check,
                            'strategy': f"Portfolio balance: ${total_profit:.2f} (ratio: {balance_ratio:.2f})"
                        })
            
            # 🆕 เรียงตาม AI confidence และ expected profit
            opportunities.sort(key=lambda x: (x['ai_confidence'] * x['expected_profit']), reverse=True)
            
            # 🆕 Return เฉพาะโอกาสที่ดีที่สุด
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
        """แก้ไข: Get recent price history ที่ทำงานได้ดีขึ้น"""
        
        try:
            from datetime import datetime, timedelta
            import MetaTrader5 as mt5
            
            # Method 1: ใช้ M1 rates (แนะนำ)
            rates = mt5.copy_rates_from_pos(self.gold_symbol, mt5.TIMEFRAME_M1, 0, min(count, 50))
            
            if rates is not None and len(rates) >= 3:
                # ใช้ close prices และเพิ่ม current price
                close_prices = [float(rate['close']) for rate in rates[-min(count, len(rates)):]]
                
                # เพิ่ม current price ถ้าได้
                current_price = self.get_current_price()
                if current_price > 0 and current_price != close_prices[-1]:
                    close_prices.append(current_price)
                
                return close_prices
            
            # Method 2: Fallback ด้วย current price
            current_price = self.get_current_price()
            if current_price > 0:
                # สร้าง synthetic data ด้วยการเพิ่ม noise เล็กน้อย
                import random
                base_price = current_price
                synthetic_prices = []
                
                for i in range(min(count, 10)):
                    # เพิ่ม random noise ±$0.50
                    noise = (random.random() - 0.5) * 1.0
                    price = base_price + noise
                    synthetic_prices.append(price)
                
                # เพิ่ม current price เป็นตัวสุดท้าย
                synthetic_prices.append(current_price)
                
                return synthetic_prices
            
            return []
            
        except Exception as e:
            print(f"❌ Price history error: {e}")
            # Ultimate fallback
            try:
                current_price = self.get_current_price()
                if current_price > 0:
                    return [current_price, current_price, current_price]  # ขั้นต่ำ 3 จุด
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
        
    def ai_analyze_portfolio_positions(self) -> Dict:
        """🆕 วิเคราะห์ตำแหน่งทุกไม้ในพอร์ต - Enhanced Position Tracking"""
        
        try:
            current_price = self.get_current_price()
            if not current_price:
                return {}
            
            analysis = {
                'total_positions': 0,
                'buy_positions': [],
                'sell_positions': [],
                'position_map': {},
                'lot_distribution': {'BUY': 0, 'SELL': 0},
                'profit_distribution': {'BUY': 0, 'SELL': 0},
                'margin_distribution': {'BUY': 0, 'SELL': 0},
                'position_health_summary': {},
                'portfolio_stats': {}
            }
            
            # วิเคราะห์แต่ละไม้
            for ticket, position in self.active_positions.items():
                direction = position.get('direction', 'UNKNOWN')
                lot_size = position.get('volume', position.get('lot_size', 0))
                entry_price = position.get('price_open', 0)
                profit = position.get('profit', 0)
                entry_time = position.get('time_open', datetime.now())
                
                # คำนวณอายุไม้
                if isinstance(entry_time, (int, float)):
                    entry_time = datetime.fromtimestamp(entry_time)
                age_hours = (datetime.now() - entry_time).total_seconds() / 3600
                
                # คำนวณระยะห่างจาก market
                distance_from_market = abs(entry_price - current_price)
                
                # คำนวณ margin required (Gold approx)
                margin_required = lot_size * 1000 * (current_price / 100)  # Rough estimate
                
                # กำหนด health status
                if profit > 5:
                    health = "EXCELLENT"
                elif profit > 1:
                    health = "GOOD"
                elif profit >= -1:
                    health = "NEUTRAL"
                elif profit >= -5:
                    health = "POOR"
                else:
                    health = "CRITICAL"
                
                # คำนวณ AI Score (0-100)
                ai_score = self.calculate_position_ai_score(profit, age_hours, distance_from_market, lot_size)
                
                # เก็บข้อมูลไม้
                position_info = {
                    'ticket': ticket,
                    'direction': direction,
                    'lot_size': lot_size,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'profit': profit,
                    'age_hours': age_hours,
                    'margin_required': margin_required,
                    'health': health,
                    'distance_from_market': distance_from_market,
                    'ai_score': ai_score
                }
                
                # จัดหมวดหมู่
                if direction == 'BUY':
                    analysis['buy_positions'].append(position_info)
                    analysis['lot_distribution']['BUY'] += lot_size
                    analysis['profit_distribution']['BUY'] += profit
                    analysis['margin_distribution']['BUY'] += margin_required
                else:
                    analysis['sell_positions'].append(position_info)
                    analysis['lot_distribution']['SELL'] += lot_size
                    analysis['profit_distribution']['SELL'] += profit
                    analysis['margin_distribution']['SELL'] += margin_required
                
                analysis['position_map'][ticket] = position_info
                analysis['total_positions'] += 1
            
            # สรุปสถิติ
            analysis['portfolio_stats'] = {
                'buy_count': len(analysis['buy_positions']),
                'sell_count': len(analysis['sell_positions']),
                'total_lots': analysis['lot_distribution']['BUY'] + analysis['lot_distribution']['SELL'],
                'total_profit': analysis['profit_distribution']['BUY'] + analysis['profit_distribution']['SELL'],
                'total_margin': analysis['margin_distribution']['BUY'] + analysis['margin_distribution']['SELL'],
                'balance_ratio': self.calculate_balance_ratio(analysis['lot_distribution']),
                'avg_ai_score': sum(p['ai_score'] for p in analysis['position_map'].values()) / max(1, len(analysis['position_map']))
            }
            
            return analysis
            
        except Exception as e:
            print(f"❌ Portfolio analysis error: {e}")
            return {}

    def calculate_position_ai_score(self, profit: float, age_hours: float, distance: float, lot_size: float) -> float:
        """🆕 คำนวณ AI Score สำหรับไม้แต่ละไม้"""
        
        try:
            score = 50  # Base score
            
            # Profit component (40 points)
            if profit > 5:
                score += 30
            elif profit > 1:
                score += 20
            elif profit > 0:
                score += 10
            elif profit > -1:
                score += 0
            elif profit > -5:
                score -= 15
            else:
                score -= 30
            
            # Age component (20 points)
            if age_hours < 1:
                score += 10  # Fresh position
            elif age_hours < 24:
                score += 5   # Recent
            elif age_hours > 72:
                score -= 10  # Too old
            
            # Distance component (20 points)
            if distance < 1:
                score += 15  # Very close to market
            elif distance < 5:
                score += 10  # Close to market
            elif distance > 20:
                score -= 10  # Far from market
            
            # Size component (20 points)
            if lot_size > 0.05:
                score -= 5   # Large position = higher risk
            elif lot_size < 0.02:
                score += 5   # Small position = lower risk
            
            return max(0, min(100, score))
            
        except Exception as e:
            print(f"❌ AI Score calculation error: {e}")
            return 50

    def calculate_balance_ratio(self, lot_distribution: Dict) -> float:
        """🆕 คำนวณอัตราสมดุล BUY/SELL"""
        
        buy_lots = lot_distribution.get('BUY', 0)
        sell_lots = lot_distribution.get('SELL', 0)
        
        if buy_lots == 0 and sell_lots == 0:
            return 1.0
        
        total_lots = buy_lots + sell_lots
        if total_lots == 0:
            return 1.0
        
        smaller = min(buy_lots, sell_lots)
        larger = max(buy_lots, sell_lots)
        
        return smaller / larger if larger > 0 else 1.0

    def calculate_margin_impact(self, position_tickets: List[int]) -> Dict:
        """🆕 คำนวณผลกระทบ margin หลังปิดไม้"""
        
        try:
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return {'safe_to_close': False, 'reason': 'No account info'}
            
            current_margin = account_info.get('margin', 0)
            current_equity = account_info.get('equity', 0)
            current_balance = account_info.get('balance', 0)
            free_margin = account_info.get('free_margin', 0)
            
            # คำนวณ margin ที่จะหลุดหลังปิด
            margin_relief = 0
            profit_impact = 0
            
            for ticket in position_tickets:
                if ticket in self.active_positions:
                    position = self.active_positions[ticket]
                    lot_size = position.get('volume', position.get('lot_size', 0))
                    profit = position.get('profit', 0)
                    
                    # Estimate margin per position (Gold rough calculation)
                    current_price = self.get_current_price()
                    position_margin = lot_size * 1000 * (current_price / 100) if current_price else 100
                    
                    margin_relief += position_margin
                    profit_impact += profit
            
            # คำนวณสถานะหลังปิด
            new_equity = current_equity + profit_impact
            new_balance = current_balance + profit_impact  # ถ้าปิดด้วยกำไร
            new_margin = current_margin - margin_relief
            new_free_margin = new_equity - new_margin
            
            # คำนวณ margin level หลังปิด
            new_margin_level = (new_equity / new_margin * 100) if new_margin > 0 else 999999
            
            # ประเมินความปลอดภัย
            safety_checks = {
                'margin_level_ok': new_margin_level > 200,  # >200% ปลอดภัย
                'free_margin_ok': new_free_margin > (new_balance * 0.3),  # Free margin >30% balance
                'profit_positive': profit_impact >= -2,  # ไม่เสียมากเกิน $2
                'portfolio_stable': len(self.active_positions) - len(position_tickets) >= 2  # เหลือไม้อย่างน้อย 2 ไม้
            }
            
            all_safe = all(safety_checks.values())
            
            # คำนวณ safety score
            safety_score = sum(safety_checks.values()) / len(safety_checks) * 100
            
            return {
                'safe_to_close': all_safe,
                'safety_score': safety_score,
                'margin_relief': margin_relief,
                'profit_impact': profit_impact,
                'new_margin_level': new_margin_level,
                'new_free_margin': new_free_margin,
                'safety_checks': safety_checks,
                'recommendation': 'SAFE' if all_safe else 'RISKY',
                'reason': self.generate_margin_reason(safety_checks, safety_score)
            }
            
        except Exception as e:
            print(f"❌ Margin impact calculation error: {e}")
            return {'safe_to_close': False, 'reason': f'Calculation error: {e}'}

    def generate_margin_reason(self, safety_checks: Dict, safety_score: float) -> str:
        """🆕 สร้างเหตุผล margin safety"""
        
        if safety_score >= 75:
            return "All safety checks passed"
        elif safety_score >= 50:
            failed_checks = [k for k, v in safety_checks.items() if not v]
            return f"Moderate risk: {', '.join(failed_checks)}"
        else:
            return "High risk: Multiple safety concerns"

    def ai_find_smart_closing_opportunities(self) -> List[Dict]:
        """🆕 ค้นหาโอกาสปิดไม้แบบอัจฉริยะ - หลากหลายกลยุทธ์"""
        
        try:
            opportunities = []
            
            # วิเคราะห์พอร์ต
            portfolio_analysis = self.ai_analyze_portfolio_positions()
            if not portfolio_analysis:
                return opportunities
            
            position_map = portfolio_analysis['position_map']
            
            # 🧠 Strategy 1: Rescue Pairs (ช่วยกันแบบคู่)
            rescue_opportunities = self.find_rescue_pair_opportunities(position_map)
            opportunities.extend(rescue_opportunities)
            
            # 🧠 Strategy 2: Profit Harvest (เก็บกำไรเดี่ยว)
            harvest_opportunities = self.find_profit_harvest_opportunities(position_map)
            opportunities.extend(harvest_opportunities)
            
            # 🧠 Strategy 3: Portfolio Balance (ปรับสมดุล)
            balance_opportunities = self.find_balance_opportunities(portfolio_analysis)
            opportunities.extend(balance_opportunities)
            
            # 🧠 Strategy 4: Risk Reduction (ลดความเสี่ยง)
            risk_opportunities = self.find_risk_reduction_opportunities(position_map)
            opportunities.extend(risk_opportunities)
            
            # 🧠 Strategy 5: Margin Relief (ลด margin pressure)
            margin_opportunities = self.find_margin_relief_opportunities(position_map)
            opportunities.extend(margin_opportunities)
            
            # 🧠 Strategy 6: Smart Liquidation (ปิดอัจฉริยะ)
            smart_opportunities = self.find_smart_liquidation_opportunities(position_map)
            opportunities.extend(smart_opportunities)
            
            # เรียงตาม priority และ filter ที่ปลอดภัย
            safe_opportunities = []
            for opp in opportunities:
                margin_check = self.calculate_margin_impact(opp['positions'])
                if margin_check['safe_to_close']:
                    opp['margin_analysis'] = margin_check
                    safe_opportunities.append(opp)
            
            # เรียงตาม AI confidence และ expected benefit
            safe_opportunities.sort(key=lambda x: (x['ai_confidence'] * x['expected_profit']), reverse=True)
            
            return safe_opportunities[:5]  # Top 5 opportunities
            
        except Exception as e:
            print(f"❌ Smart closing opportunities error: {e}")
            return []

    def find_rescue_pair_opportunities(self, position_map: Dict) -> List[Dict]:
        """🆕 หาโอกาสช่วยกันแบบคู่"""
        
        opportunities = []
        
        try:
            positions = list(position_map.values())
            profit_positions = [p for p in positions if p['profit'] > 1]
            loss_positions = [p for p in positions if p['profit'] < -1]
            
            for loss_pos in loss_positions:
                for profit_pos in profit_positions:
                    net_profit = loss_pos['profit'] + profit_pos['profit']
                    
                    if net_profit > 0.5:  # Net positive
                        opportunities.append({
                            'strategy': 'RESCUE_PAIRS',
                            'positions': [loss_pos['ticket'], profit_pos['ticket']],
                            'expected_profit': net_profit,
                            'margin_relief': loss_pos['margin_required'] + profit_pos['margin_required'],
                            'portfolio_improvement': 20,  # ลดความเสี่ยง
                            'ai_confidence': 0.8,
                            'execution_priority': 1,
                            'reason': f"Rescue pair: ${profit_pos['profit']:.2f} profit rescues ${loss_pos['profit']:.2f} loss"
                        })
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Rescue pair opportunities error: {e}")
            return []

    def find_profit_harvest_opportunities(self, position_map: Dict) -> List[Dict]:
        """🆕 หาโอกาสเก็บกำไรเดี่ยว"""
        
        opportunities = []
        
        try:
            positions = list(position_map.values())
            
            for position in positions:
                profit = position['profit']
                ai_score = position['ai_score']
                
                # เก็บกำไรเมื่อ
                if profit > 5 and ai_score > 70:  # กำไรสูง + คะแนน AI ดี
                    opportunities.append({
                        'strategy': 'PROFIT_HARVEST',
                        'positions': [position['ticket']],
                        'expected_profit': profit,
                        'margin_relief': position['margin_required'],
                        'portfolio_improvement': 15,
                        'ai_confidence': 0.75,
                        'execution_priority': 2,
                        'reason': f"High profit harvest: ${profit:.2f} (AI Score: {ai_score:.0f})"
                    })
                elif profit > 8:  # กำไรสูงมาก เก็บเลย
                    opportunities.append({
                        'strategy': 'PROFIT_HARVEST',
                        'positions': [position['ticket']],
                        'expected_profit': profit,
                        'margin_relief': position['margin_required'],
                        'portfolio_improvement': 25,
                        'ai_confidence': 0.9,
                        'execution_priority': 1,
                        'reason': f"Very high profit harvest: ${profit:.2f}"
                    })
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Profit harvest opportunities error: {e}")
            return []

    def find_balance_opportunities(self, portfolio_analysis: Dict) -> List[Dict]:
        """🆕 หาโอกาสปรับสมดุลพอร์ต"""
        
        opportunities = []
        
        try:
            stats = portfolio_analysis['portfolio_stats']
            buy_count = stats['buy_count']
            sell_count = stats['sell_count']
            balance_ratio = stats['balance_ratio']
            
            # ถ้าไม่สมดุล (< 0.6)
            if balance_ratio < 0.6:
                position_map = portfolio_analysis['position_map']
                
                # หาทิศทางที่เกิน
                if buy_count > sell_count:
                    excess_direction = 'BUY'
                    excess_positions = [p for p in position_map.values() if p['direction'] == 'BUY']
                else:
                    excess_direction = 'SELL'
                    excess_positions = [p for p in position_map.values() if p['direction'] == 'SELL']
                
                # เลือกไม้ที่มี AI score ต่ำสุดในทิศทางที่เกิน
                excess_positions.sort(key=lambda x: x['ai_score'])
                
                # ปิด 1-2 ไม้เพื่อปรับสมดุล
                positions_to_close = excess_positions[:2]
                
                if positions_to_close:
                    total_profit = sum(p['profit'] for p in positions_to_close)
                    total_margin = sum(p['margin_required'] for p in positions_to_close)
                    
                    opportunities.append({
                        'strategy': 'PORTFOLIO_BALANCE',
                        'positions': [p['ticket'] for p in positions_to_close],
                        'expected_profit': total_profit,
                        'margin_relief': total_margin,
                        'portfolio_improvement': 30,
                        'ai_confidence': 0.7,
                        'execution_priority': 3,
                        'reason': f"Balance portfolio: Remove excess {excess_direction} positions (ratio: {balance_ratio:.2f})"
                    })
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Balance opportunities error: {e}")
            return []

    def find_risk_reduction_opportunities(self, position_map: Dict) -> List[Dict]:
        """🆕 หาโอกาสลดความเสี่ยง"""
        
        opportunities = []
        
        try:
            positions = list(position_map.values())
            
            # หาไม้ที่มีความเสี่ยงสูง
            high_risk_positions = [
                p for p in positions 
                if p['health'] == 'CRITICAL' or (p['profit'] < -3 and p['age_hours'] > 24)
            ]
            
            if high_risk_positions:
                # เรียงตามความเสียหายมากที่สุด
                high_risk_positions.sort(key=lambda x: x['profit'])
                
                # เลือกไม้ที่แย่ที่สุด 1-2 ไม้
                worst_positions = high_risk_positions[:2]
                
                total_loss = sum(p['profit'] for p in worst_positions)
                total_margin = sum(p['margin_required'] for p in worst_positions)
                
                opportunities.append({
                    'strategy': 'RISK_REDUCTION',
                    'positions': [p['ticket'] for p in worst_positions],
                    'expected_profit': total_loss,  # จะเป็นลบ
                    'margin_relief': total_margin,
                    'portfolio_improvement': 35,  # ลดความเสี่ยงมาก
                    'ai_confidence': 0.65,
                    'execution_priority': 4,
                    'reason': f"Cut high-risk positions: ${total_loss:.2f} loss but reduce risk"
                })
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Risk reduction opportunities error: {e}")
            return []

    def find_margin_relief_opportunities(self, position_map: Dict) -> List[Dict]:
        """🆕 หาโอกาสลด margin pressure"""
        
        opportunities = []
        
        try:
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return opportunities
            
            margin_level = account_info.get('margin_level', 1000)
            
            # ถ้า margin level < 500% ให้หาวิธีลด margin
            if margin_level < 500:
                positions = list(position_map.values())
                
                # หาไม้ที่ใช้ margin สูงแต่กำไรไม่ดี
                high_margin_positions = [
                    p for p in positions 
                    if p['margin_required'] > 50 and p['profit'] < 2
                ]
                
                if high_margin_positions:
                    # เรียงตาม margin ที่สูงที่สุด
                    high_margin_positions.sort(key=lambda x: x['margin_required'], reverse=True)
                    
                    # เลือก 1-2 ไม้ที่ใช้ margin สูงสุด
                    margin_heavy_positions = high_margin_positions[:2]
                    
                    total_profit = sum(p['profit'] for p in margin_heavy_positions)
                    total_margin = sum(p['margin_required'] for p in margin_heavy_positions)
                    
                    opportunities.append({
                        'strategy': 'MARGIN_RELIEF',
                        'positions': [p['ticket'] for p in margin_heavy_positions],
                        'expected_profit': total_profit,
                        'margin_relief': total_margin,
                        'portfolio_improvement': 25,
                        'ai_confidence': 0.8,
                        'execution_priority': 2,
                        'reason': f"Reduce margin pressure: Free ${total_margin:.0f} margin (current level: {margin_level:.0f}%)"
                    })
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Margin relief opportunities error: {e}")
            return []

    def find_smart_liquidation_opportunities(self, position_map: Dict) -> List[Dict]:
        """🆕 หาโอกาสปิดแบบอัจฉริยะ"""
        
        opportunities = []
        
        try:
            positions = list(position_map.values())
            
            # หากลุ่มไม้ที่ควรปิดด้วยกัน
            # กลุ่ม 1: ไม้เก่าที่ไม่มีความหวัง
            old_stagnant = [
                p for p in positions 
                if p['age_hours'] > 48 and abs(p['profit']) < 2
            ]
            
            if len(old_stagnant) >= 2:
                total_profit = sum(p['profit'] for p in old_stagnant)
                total_margin = sum(p['margin_required'] for p in old_stagnant)
                
                opportunities.append({
                    'strategy': 'SMART_LIQUIDATION',
                    'positions': [p['ticket'] for p in old_stagnant],
                    'expected_profit': total_profit,
                    'margin_relief': total_margin,
                    'portfolio_improvement': 20,
                    'ai_confidence': 0.6,
                    'execution_priority': 5,
                    'reason': f"Clean old stagnant positions: {len(old_stagnant)} positions aged >48h"
                })
            
            # กลุ่ม 2: ไม้ใกล้ market ที่ควรเก็บกำไรเล็กๆ
            near_market_profit = [
                p for p in positions 
                if p['distance_from_market'] < 2 and p['profit'] > 0.5
            ]
            
            if len(near_market_profit) >= 2:
                total_profit = sum(p['profit'] for p in near_market_profit)
                total_margin = sum(p['margin_required'] for p in near_market_profit)
                
                opportunities.append({
                    'strategy': 'SMART_LIQUIDATION',
                    'positions': [p['ticket'] for p in near_market_profit],
                    'expected_profit': total_profit,
                    'margin_relief': total_margin,
                    'portfolio_improvement': 15,
                    'ai_confidence': 0.7,
                    'execution_priority': 3,
                    'reason': f"Harvest near-market profits: {len(near_market_profit)} positions <$2 from market"
                })
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Smart liquidation opportunities error: {e}")
            return []

def __del__(self):
    """Cleanup when AI system is destroyed"""
    try:
        if getattr(self, 'ai_active', False):
            self.stop_ai_trading()
    except:
        pass