"""
AI Smart Profit Manager - Enhanced Grid Trading System
ai_smart_profit_manager.py
Dynamic spacing, zero-loss philosophy, intelligent grid management
Updated for $1000+ accounts with 100+ points dynamic spacing
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
from smart_enhancements import SmartEnhancements

class AIDecisionReason(Enum):
    MARKET_ANALYSIS = "MARKET_ANALYSIS"
    PORTFOLIO_HEALTH = "PORTFOLIO_HEALTH"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    PROFIT_OPTIMIZATION = "PROFIT_OPTIMIZATION"
    EMERGENCY_PROTECTION = "EMERGENCY_PROTECTION"

class PortfolioStatus(Enum):
    PROFITABLE = "PROFITABLE"
    BALANCED = "BALANCED"
    LOSING = "LOSING"

class MarketCondition(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
class OrderCommentManager:
    """🏷️ จัดการ Comment ในออเดอร์เพื่อ Track Source"""
    
    @staticmethod
    def generate_comment(source_function: str, enhancement_data: dict = None, extra_info: str = "") -> str:
        """สร้าง comment ที่มีข้อมูลครบถ้วน"""
        
        # Base comment with function source
        comment_parts = [source_function]
        
        # Add enhancement info if available
        if enhancement_data:
            tier = enhancement_data.get('tier', 'UNKNOWN')
            confidence = enhancement_data.get('confidence', 0)
            comment_parts.append(f"{tier}")
            comment_parts.append(f"C{confidence:.0f}")  # C = Confidence
        
        # Add extra info
        if extra_info:
            comment_parts.append(extra_info)
        
        # Join with underscores and limit length (MT5 limit = 31 chars)
        comment = "_".join(comment_parts)
        return comment[:31]  # MT5 comment limit
    
@dataclass
class AIMarketAnalysis:
    condition: MarketCondition
    volatility_score: float
    trend_strength: float
    support_level: float
    resistance_level: float
    optimal_spacing: int
    recommended_action: str
    confidence: float

@dataclass
class AIDecision:
    action: str
    reason: AIDecisionReason
    confidence: float
    parameters: Dict
    expected_outcome: str
    timestamp: datetime

class AISmartProfitManager:
    def __init__(self, mt5_connector, survivability_config, config):
        print("🧠 AI SMART PROFIT MANAGER - Enhanced Grid System")
        print("=" * 60)
        
        # Core connections
        self.mt5_connector = mt5_connector
        self.survivability_config = survivability_config
        self.config = config
        
        # Gold symbol detection
        self.gold_symbol = mt5_connector.get_gold_symbol()
        if not self.gold_symbol:
            self.gold_symbol = "XAUUSD.v"  # Default fallback
        
        # Trading parameters
        self.base_lot = survivability_config.get('base_lot', 0.01)
        self.survivability = survivability_config.get('realistic_survivability', 15000)
        self.magic_number = 77703292
        
        # 🛡️ NEW: Portfolio Support System
        self.portfolio_support_positions = {}  # เก็บไม้ที่อยู่ใน support mode
        self.support_trailing_data = {}        # เก็บข้อมูล trailing ของแต่ละไม้
        self.ignore_trailing_protection = True
        # AI State
        self.ai_active = False
        self.ai_health_score = 50.0
        self.portfolio_status = PortfolioStatus.BALANCED
        self.market_analysis = None
        
        # Trading state
        self.active_positions = {}
        self.pending_orders = {}
        self.market_memory = []
        self.decision_history = []
        
        # ⭐ เพิ่มส่วนนี้ - Portfolio Balance Protection Settings
        self.portfolio_balance_protection = config.get('portfolio_balance_protection', True)
        self.balance_protection_mode = config.get('balance_protection_mode', 'STANDARD')  # DISABLED, STANDARD, STRICT
        self.max_imbalance_ratio = config.get('max_imbalance_ratio', 2.3)  # 70:30
        self.critical_imbalance_ratio = config.get('critical_imbalance_ratio', 3.0)  # 75:25

        # Performance tracking
        self.performance_metrics = {
            'total_decisions': 0,
            'successful_decisions': 0,
            'ai_accuracy': 0.0,
            'portfolio_health_avg': 50.0
        }
        
        # Enhanced Grid Settings
        self.grid_config = {
            'min_spacing': 80,           # Minimum 80 points
            'normal_spacing': 100,       # Normal 100 points  
            'max_spacing': 300,          # Maximum 300 points
            'initial_orders_per_side': 5, # Start with 5 each side
            'gap_threshold': 200,        # Fill gaps >200 points
            'rebalance_threshold': 2     # Rebalance when diff >2 orders
        }
        # AI configuration
        self.ai_config = config.get('ai_smart_profit', {
            'analysis_interval': 3,
            'market_memory_size': 100,
            'decision_confidence_threshold': 0.6,
            'max_positions_per_direction': 8,
            'dynamic_spacing_enabled': True,
            'profit_only_mode': True
        })
        self.smart_enhancer = SmartEnhancements(self.gold_symbol, {
            'min_confidence': config.get('min_confidence', 30),
            'quality_confidence': config.get('quality_confidence', 60),
            'rebate_per_lot': config.get('rebate_per_lot', 35.0),
            'spread_cost': config.get('spread_cost', 4.0),
            'enabled': config.get('smart_enhancement_enabled', True)
        })  

        print(f"✅ Initialized for {self.gold_symbol}")
        print(f"💰 Base Lot: {self.base_lot}")
        print(f"🛡️ Survivability: {self.survivability:,} points")
        print(f"📏 Dynamic Spacing: {self.grid_config['min_spacing']}-{self.grid_config['max_spacing']} points")
        print("🚀 Ready for enhanced grid trading!")

    def start_ai_trading(self) -> bool:
        """Start enhanced AI trading system"""
        try:
            print("🧠 STARTING ENHANCED AI GRID SYSTEM...")
            
            # Validate prerequisites
            if not self.validate_ai_prerequisites():
                return False
            
            if not self.validate_symbol_and_account():
                print("❌ Pre-trading validation failed")
                return False
            
            # Validate prerequisites
            if not self.validate_ai_prerequisites():
                return False
            # Initialize market analysis
            self.initialize_ai_market_analysis()
            
            # Set active flag
            self.ai_active = True
            
            # Start AI loops
            self.start_ai_main_loop()
            self.start_ai_monitoring_loop()
            
            print("🎉 AI ENHANCED GRID SYSTEM OPERATIONAL!")
            print(f"   🧠 Market Analysis: ACTIVE")
            print(f"   📊 Grid Management: DYNAMIC") 
            print(f"   💰 Profit-Only Mode: ENABLED")
            print(f"   🛡️ Zero-Loss Protection: ACTIVE")
            
            return True
            
        except Exception as e:
            print(f"❌ AI System startup error: {e}")
            return False

    def validate_ai_prerequisites(self) -> bool:
        """Validate system prerequisites"""
        try:
            # Check MT5 connection
            if not self.mt5_connector:
                print("❌ No MT5 connection")
                return False
            
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                print("❌ Cannot get account information")
                return False
            
            balance = account_info.get('balance', 0)
            if balance < 100:
                print(f"❌ Insufficient balance: ${balance:.2f}")
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
        """Initialize enhanced market analysis"""
        try:
            print("🔬 Initializing Enhanced Market Analysis...")
            
            # Get initial market data
            initial_analysis = self.ai_analyze_market_condition()
            if initial_analysis:
                self.market_analysis = initial_analysis
                print(f"   📊 Initial Condition: {initial_analysis.condition.value}")
                print(f"   📏 Optimal Spacing: {initial_analysis.optimal_spacing} points")
                print(f"   🎯 Confidence: {initial_analysis.confidence:.2f}")
            
            # Place initial grid
            self.place_initial_enhanced_grid()
            
        except Exception as e:
            print(f"❌ Market analysis initialization error: {e}")

    def place_initial_enhanced_grid(self):
        """Place initial enhanced grid with validation"""
        try:
            print("🎯 PLACING INITIAL ENHANCED GRID...")
            
            # 🔧 Add validation before placing orders
            if not self.validate_symbol_and_account():
                print("❌ Symbol/Account validation failed")
                return
            
            current_price = self.get_current_price()
            if not current_price:
                print("❌ Cannot get current price")
                return
            
            # Calculate dynamic spacing
            spacing = self.calculate_dynamic_spacing()
            spacing_dollars = spacing * 0.01
            
            orders_per_side = self.grid_config['initial_orders_per_side']
            
            print(f"   💰 Current Price: ${current_price:.2f}")
            print(f"   📏 Dynamic Spacing: {spacing} points (${spacing_dollars:.2f})")
            print(f"   📊 Orders per side: {orders_per_side}")
            
            orders_placed = 0
            max_orders_per_side = 3  # 🔧 Limit orders to prevent spam
            
            # Place BUY orders (below market) - Limited quantity
            print(f"   📍 Placing BUY orders...")
            for i in range(1, min(orders_per_side + 1, max_orders_per_side + 1)):
                buy_price = current_price - (spacing_dollars * i)
                
                if not self.level_exists_enhanced(buy_price, 'BUY', spacing_dollars * 0.5):
                    print(f"     🔍 Attempting BUY Level {i}: ${buy_price:.2f}")
                    success = self.place_enhanced_order(buy_price, 'BUY', 'INITIAL_GRID')
                    if success:
                        orders_placed += 1
                        print(f"     ✅ BUY Level {i}: ${buy_price:.2f} - SUCCESS")
                    else:
                        print(f"     ❌ BUY Level {i}: ${buy_price:.2f} - FAILED")
                    time.sleep(0.5)  # Wait between orders
                else:
                    print(f"     ⏭️ BUY Level {i}: ${buy_price:.2f} - SKIPPED (too close)")
                    
            # Place SELL orders (above market) - Limited quantity
            print(f"   📍 Placing SELL orders...")
            for i in range(1, min(orders_per_side + 1, max_orders_per_side + 1)):
                sell_price = current_price + (spacing_dollars * i)
                
                if not self.level_exists_enhanced(sell_price, 'SELL', spacing_dollars * 0.5):
                    print(f"     🔍 Attempting SELL Level {i}: ${sell_price:.2f}")
                    success = self.place_enhanced_order(sell_price, 'SELL', 'INITIAL_GRID')
                    if success:
                        orders_placed += 1
                        print(f"     ✅ SELL Level {i}: ${sell_price:.2f} - SUCCESS")
                    else:
                        print(f"     ❌ SELL Level {i}: ${sell_price:.2f} - FAILED")
                    time.sleep(0.5)  # Wait between orders
                else:
                    print(f"     ⏭️ SELL Level {i}: ${sell_price:.2f} - SKIPPED (too close)")
            
            print(f"🎉 Initial Grid Complete: {orders_placed} orders placed successfully")
            
            if orders_placed == 0:
                print("⚠️ No orders placed - check symbol permissions and account settings")
            
        except Exception as e:
            print(f"❌ Initial grid placement error: {e}")
            import traceback
            traceback.print_exc()

    def calculate_dynamic_spacing(self) -> int:
        """Calculate dynamic spacing based on market conditions"""
        try:
            # Get account balance
            account_info = self.mt5_connector.get_account_info()
            balance = account_info.get('balance', 1000) if account_info else 1000
            
            # Base spacing by account size
            if balance >= 50000:
                base_spacing = 80
            elif balance >= 10000:
                base_spacing = 90
            elif balance >= 5000:
                base_spacing = 100
            elif balance >= 1000:
                base_spacing = 110
            else:
                base_spacing = 120
            
            # Get current drawdown
            drawdown_points = self.get_current_drawdown_points()
            drawdown_ratio = drawdown_points / self.survivability if self.survivability > 0 else 0
            
            # Adjust for market conditions
            if self.market_analysis:
                volatility_factor = 1.0 + (self.market_analysis.volatility_score - 50) / 200
                base_spacing = int(base_spacing * volatility_factor)
            
            # Adjust for drawdown (increase spacing when in drawdown)
            if drawdown_ratio > 0.5:
                drawdown_factor = 1.5
            elif drawdown_ratio > 0.3:
                drawdown_factor = 1.3
            elif drawdown_ratio > 0.1:
                drawdown_factor = 1.1
            else:
                drawdown_factor = 1.0
            
            final_spacing = int(base_spacing * drawdown_factor)
            
            # Apply limits
            final_spacing = max(self.grid_config['min_spacing'], 
                              min(final_spacing, self.grid_config['max_spacing']))
            
            print(f"   🧮 Spacing Calculation:")
            print(f"      💰 Balance: ${balance:,.0f}")
            print(f"      📊 Base: {base_spacing} points")
            print(f"      🌊 Drawdown Factor: {drawdown_factor:.2f}")
            print(f"      ✅ Final: {final_spacing} points")
            
            return final_spacing
            
        except Exception as e:
            print(f"❌ Dynamic spacing calculation error: {e}")
            return self.grid_config['normal_spacing']

    def level_exists_enhanced(self, price: float, direction: str, tolerance: float) -> bool:
        """Enhanced level existence check"""
        try:
            # Check active positions
            for pos in self.active_positions.values():
                if pos.get('direction') == direction:
                    existing_price = pos.get('price_open', 0)
                    if abs(existing_price - price) <= tolerance:
                        return True
            
            # Check pending orders
            for order in self.pending_orders.values():
                if order.get('direction') == direction:
                    existing_price = order.get('price', 0)
                    if abs(existing_price - price) <= tolerance:
                        return True
            
            return False
            
        except Exception as e:
            print(f"❌ Level exists check error: {e}")
            return True  # Safe mode

    def place_enhanced_order(self, price: float, direction: str, order_type: str) -> bool:
        """Enhanced order placement with detailed comments"""
        try:
            print(f"🔍 Analyzing {direction} order @${price:.2f}...")
            
            # 🧠 Smart Enhancement Analysis
            enhancement = self.smart_enhancer.enhance_grid_order({
                'price': price,
                'direction': direction,
                'base_lot': self.base_lot,
                'market_condition': self.get_current_market_condition()
            })
            
            # Display analysis results
            print(f"   📊 Technical Analysis Complete:")
            print(f"      Confidence: {enhancement.confidence:.1f}%")
            print(f"      Tier: {enhancement.tier.value}")
            print(f"      Lot Size: {enhancement.lot_size} (vs base {self.base_lot})")
            
            if enhancement.should_place:
                # 🏷️ Generate detailed comment
                comment = OrderCommentManager.generate_comment(
                    source_function="ENHANCED_GRID",
                    enhancement_data={
                        'tier': enhancement.tier.value,
                        'confidence': enhancement.confidence
                    },
                    extra_info=direction
                )
                
                # 📍 Place order with enhanced parameters
                success = self.execute_enhanced_order_with_comment(
                    price, direction, enhancement, comment
                )
                
                if success:
                    print(f"   ✅ Enhanced {direction} Order Placed!")
                    print(f"   🏷️ Comment: {comment}")
                    return True
                else:
                    print(f"   ❌ Order placement failed")
                    return False
            else:
                print(f"   ⏭️ Order SKIPPED - Low Quality Signal")
                return False
                
        except Exception as e:
            print(f"❌ Enhanced order placement error: {e}")
            # Fallback with comment
            return self.fallback_order_with_comment(price, direction, "FALLBACK_ERROR")

    def execute_enhanced_order_with_comment(self, price: float, direction: str, 
                                        enhancement, comment: str) -> bool:
        """Execute order with enhanced parameters and custom comment"""
        try:
            # Get symbol and price validation (same as before)
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                return False
            
            current_price = (tick.ask + tick.bid) / 2
            
            # Validate price vs direction
            if direction == "BUY" and price >= current_price:
                price = current_price - 1.00
            elif direction == "SELL" and price <= current_price:
                price = current_price + 1.00
            
            # Get symbol info for validation
            symbol_info = mt5.symbol_info(self.gold_symbol)
            if not symbol_info:
                return False
            
            # Validate enhanced lot size
            volume = max(symbol_info.volume_min, enhancement.lot_size)
            volume = min(volume, symbol_info.volume_max)
            volume = round(volume / symbol_info.volume_step) * symbol_info.volume_step
            volume = round(volume, 3)
            
            # Determine order type
            order_type_int = 2 if direction == "BUY" else 3
            
            # 🏷️ Create enhanced order request with detailed comment
            request = {
                "action": 5,  # TRADE_ACTION_PENDING
                "symbol": self.gold_symbol,
                "volume": volume,
                "type": order_type_int,
                "price": round(price, 2),
                "magic": self.magic_number,
                "comment": comment  # 🏷️ Custom comment with source tracking
            }
            
            print(f"       📋 Order: {comment} | Vol: {volume}")
            
            # Send order
            result = mt5.order_send(request)
            
            if result and result.retcode == 10009:
                # Store with enhanced tracking
                self.pending_orders[result.order] = {
                    'order_id': result.order,
                    'price': round(price, 2),
                    'direction': direction,
                    'lot_size': volume,
                    'ai_type': enhancement.tier.value,
                    'confidence': enhancement.confidence,
                    'source_function': 'ENHANCED_GRID',
                    'comment': comment,  # 🏷️ Store comment for tracking
                    'enhancement_used': True,
                    'timestamp': datetime.now()
                }
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Enhanced order execution error: {e}")
            return False

    def execute_enhanced_order(self, price: float, direction: str, enhancement) -> bool:
        """Execute order with enhanced parameters"""
        try:
            # Get current price for validation
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"       ❌ Cannot get tick for {self.gold_symbol}")
                return False
            
            current_price = (tick.ask + tick.bid) / 2
            
            # Validate price vs direction (same as before)
            if direction == "BUY" and price >= current_price:
                price = current_price - 1.00
                print(f"       🔧 Adjusted BUY price to: ${price:.2f}")
            elif direction == "SELL" and price <= current_price:
                price = current_price + 1.00
                print(f"       🔧 Adjusted SELL price to: ${price:.2f}")
            
            # Get symbol info for validation
            symbol_info = mt5.symbol_info(self.gold_symbol)
            if not symbol_info:
                print(f"       ❌ Cannot get symbol info for {self.gold_symbol}")
                return False
            
            # Validate enhanced lot size
            min_volume = symbol_info.volume_min
            max_volume = symbol_info.volume_max
            volume_step = symbol_info.volume_step
            
            # Use enhanced lot size
            volume = max(min_volume, enhancement.lot_size)
            volume = min(volume, max_volume)
            volume = round(volume / volume_step) * volume_step
            volume = round(volume, 3)
            
            print(f"       📊 Enhanced Volume: {volume} (confidence-adjusted)")
            
            # Determine order type
            order_type_int = 2 if direction == "BUY" else 3  # LIMIT orders
            
            # Create enhanced order request
            request = {
                "action": 5,  # TRADE_ACTION_PENDING
                "symbol": self.gold_symbol,
                "volume": volume,
                "type": order_type_int,
                "price": round(price, 2),
                "magic": self.magic_number,
                "comment": f"SMART_{enhancement.tier.value}_{direction}"
            }
            
            print(f"       📋 Enhanced Order Request: Tier={enhancement.tier.value}, Vol={volume}")
            
            # Send order
            result = mt5.order_send(request)
            
            if result and result.retcode == 10009:
                # Store in tracking with enhancement data
                self.pending_orders[result.order] = {
                    'order_id': result.order,
                    'price': round(price, 2),
                    'direction': direction,
                    'lot_size': volume,
                    'ai_type': enhancement.tier.value,
                    'confidence': enhancement.confidence,
                    'expected_profit': enhancement.expected_profit,
                    'rebate_value': enhancement.rebate_value,
                    'enhancement_used': True,
                    'timestamp': datetime.now()
                }
                print(f"       ✅ Enhanced Order SUCCESS! ID: {result.order}")
                return True
            else:
                error_code = result.retcode if result else "No result"
                print(f"       ❌ Enhanced Order failed: {error_code}")
                if result and hasattr(result, 'comment'):
                    print(f"       💬 Comment: {result.comment}")
                return False
                
        except Exception as e:
            print(f"❌ Enhanced order execution error: {e}")
            return False
    
    def start_ai_main_loop(self):
        """Start main AI decision loop"""
        if not hasattr(self, 'ai_main_thread') or not self.ai_main_thread.is_alive():
            self.ai_main_thread = threading.Thread(target=self.ai_enhanced_main_loop, daemon=True)
            self.ai_main_thread.start()
            print("🧠 Enhanced AI Main Loop: STARTED")

    def start_ai_monitoring_loop(self):
        """Start AI monitoring loop"""
        if not hasattr(self, 'ai_monitor_thread') or not self.ai_monitor_thread.is_alive():
            self.ai_monitor_thread = threading.Thread(target=self.ai_enhanced_monitoring_loop, daemon=True)
            self.ai_monitor_thread.start()
            print("👁️ Enhanced AI Monitoring Loop: STARTED")

    def ai_enhanced_main_loop(self):
        """Enhanced main AI decision loop with Trailing Support Detection"""
        print("🧠 AI ENHANCED MAIN LOOP: Starting intelligent grid management...")
        
        while self.ai_active:
            try:
                # Update market analysis
                if hasattr(self, 'smart_enhancer'):
                    try:
                        # Update market analysis with enhancement
                        pass
                    except Exception as e:
                        print(f"⚠️ Enhancement market analysis error: {e}")
                
                # Update positions from MT5
                self.ai_update_positions_from_mt5()
                
                self.update_position_trailing()
                self.detect_existing_positions()
                time.sleep(3)
                
                # Calculate portfolio health
                health_score = self.ai_calculate_portfolio_health()
                self.ai_health_score = health_score
                
                # 🛡️ NEW: Detect and Manage Support Positions
                try:
                    self._detect_and_manage_support_positions()
                except Exception as e:
                    print(f"⚠️ Support detection error: {e}")
                
                # 🔄 NEW: Update Trailing Stops
                try:
                    self._update_all_trailing_stops()
                except Exception as e:
                    print(f"⚠️ Trailing update error: {e}")
                
                # 🚨 NEW: Check Trailing Hits
                try:
                    self._check_trailing_stop_hits()
                except Exception as e:
                    print(f"⚠️ Trailing check error: {e}")
                
                # Enhanced Grid Management
                if hasattr(self, 'smart_enhancer') and self.smart_enhancer.enabled:
                    try:
                        self.manage_enhanced_grid()
                    except Exception as e:
                        print(f"⚠️ Enhanced grid management error: {e}")
                        self.manage_original_grid()
                else:
                    self.manage_original_grid()
                
                # Enhanced Profit Taking
                try:
                    self.execute_enhanced_profit_taking()
                except Exception as e:
                    print(f"⚠️ Enhanced profit taking error: {e}")
                    self.execute_original_profit_taking()
                
                # Gap Detection and Filling
                try:
                    self.detect_and_fill_gaps()
                except Exception as e:
                    print(f"⚠️ Gap detection error: {e}")
                
                # Portfolio Rebalancing
                try:
                    self.rebalance_portfolio()
                except Exception as e:
                    print(f"⚠️ Portfolio rebalancing error: {e}")
                
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ Enhanced AI Main Loop error: {e}")
                time.sleep(5)
        
        print("🛑 Enhanced AI Main Loop: Stopped")

    def manage_original_grid(self):
        """Original grid management (fallback)"""
        try:
            # Original grid logic here
            current_positions = len(self.active_positions)
            pending_orders = len(self.pending_orders)
            total_exposure = current_positions + pending_orders
            
            if total_exposure < 6:
                print("📊 Grid Coverage Low - Adding orders (original method)...")
                # Add original logic here
                
        except Exception as e:
            print(f"❌ Original grid management error: {e}")

    def execute_original_profit_taking(self):
        """Original profit taking (fallback)"""
        try:
            # Original profit taking logic
            opportunities = self.find_original_profit_opportunities()
            
            for opportunity in opportunities[:2]:
                success = self.execute_profit_opportunity(opportunity)
                if success:
                    print(f"✅ Original profit opportunity executed")
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ Original profit taking error: {e}")

    def manage_enhanced_grid(self):
        """Enhanced grid management with dynamic spacing"""
        try:
            current_positions = len(self.active_positions)
            pending_orders = len(self.pending_orders)
            total_exposure = current_positions + pending_orders
            
            print(f"📊 Grid Status: Positions:{current_positions}, Orders:{pending_orders}, Total:{total_exposure}")
            
            # ⭐ แก้ไขตรงนี้ - เช็ค pending orders แยกจาก positions
            if pending_orders < 8:  # เปลี่ยนจาก total_exposure < 6
                print("📊 Pending Orders Low - Adding orders...")
                self.add_strategic_orders()
            
            # ⭐ แก้ไขตรงนี้ - เช็คว่าไม่มี orders ใกล้ตลาดเลย
            current_price = self.get_current_price()
            if current_price:
                nearby_orders = 0
                nearby_range = 10.0  # 10 จุด
                
                for order in self.pending_orders.values():
                    order_price = order.get('price', 0)
                    if abs(order_price - current_price) <= nearby_range:
                        nearby_orders += 1
                
                print(f"📍 Orders near market (±{nearby_range} points): {nearby_orders}")
                
                # ถ้าไม่มี orders ใกล้ตลาด → สร้างฉุกเฉิน
                if nearby_orders < 4:
                    print("🚨 No orders near market - Emergency add!")
                    self.add_strategic_orders()
            
            # ⭐ แก้ไขตรงนี้ - ย้าย cleanup มาหลัง (ไม่ลบ orders ที่เพิ่งสร้าง)
            self.cleanup_stale_orders()
            
        except Exception as e:
            print(f"❌ Enhanced grid management error: {e}")

    def add_strategic_orders(self):
        """Add strategic orders with source tracking"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                return
            
            spacing = self.calculate_dynamic_spacing()
            spacing_dollars = spacing * 0.01
            
            orders_needed = 3
            
            if orders_needed > 0:
                print(f"   🎯 Adding {orders_needed} strategic orders...")
                
                # Add BUY orders with strategic comments
                for i in range(1, orders_needed + 1):
                    buy_price = current_price - (spacing_dollars * i)
                    
                    if not self.level_exists_enhanced(buy_price, 'BUY', spacing_dollars * 0.4):
                        # 🏷️ Strategic order comment
                        comment = OrderCommentManager.generate_comment(
                            source_function="STRATEGIC",
                            extra_info=f"BUY_L{i}"
                        )
                        
                        success = self.place_order_with_comment(
                            buy_price, 'BUY', self.base_lot, comment
                        )
                        
                        if success:
                            print(f"     ✅ Strategic BUY L{i}: ${buy_price:.2f} - {comment}")
                        time.sleep(0.3)
                
                # Add SELL orders with strategic comments
                for i in range(1, orders_needed + 1):
                    sell_price = current_price + (spacing_dollars * i)
                    
                    if not self.level_exists_enhanced(sell_price, 'SELL', spacing_dollars * 0.4):
                        # 🏷️ Strategic order comment
                        comment = OrderCommentManager.generate_comment(
                            source_function="STRATEGIC", 
                            extra_info=f"SELL_L{i}"
                        )
                        
                        success = self.place_order_with_comment(
                            sell_price, 'SELL', self.base_lot, comment
                        )
                        
                        if success:
                            print(f"     ✅ Strategic SELL L{i}: ${sell_price:.2f} - {comment}")
                        time.sleep(0.3)
            
        except Exception as e:
            print(f"❌ Strategic order addition error: {e}")
    
    def place_order_with_comment(self, price: float, direction: str, lot_size: float, comment: str) -> bool:
        """Generic order placement with custom comment"""
        try:
            # Get symbol info
            tick = mt5.symbol_info_tick(self.gold_symbol)
            symbol_info = mt5.symbol_info(self.gold_symbol)
            
            if not tick or not symbol_info:
                return False
            
            # Validate lot size
            volume = max(symbol_info.volume_min, lot_size)
            volume = min(volume, symbol_info.volume_max)
            volume = round(volume / symbol_info.volume_step) * symbol_info.volume_step
            volume = round(volume, 3)
            
            # Determine order type
            order_type_int = 2 if direction == "BUY" else 3
            
            # Create order request
            request = {
                "action": 5,
                "symbol": self.gold_symbol,
                "volume": volume,
                "type": order_type_int,
                "price": round(price, 2),
                "magic": self.magic_number,
                "comment": comment  # 🏷️ Custom comment
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result and result.retcode == 10009:
                # Store with comment tracking
                self.pending_orders[result.order] = {
                    'order_id': result.order,
                    'price': round(price, 2),
                    'direction': direction,
                    'lot_size': volume,
                    'source_function': comment.split('_')[0],  # Extract function name
                    'comment': comment,
                    'enhancement_used': False,
                    'timestamp': datetime.now()
                }
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Order placement with comment error: {e}")
            return False

    # 🔍 Volume Boost orders with comments:

    def generate_micro_scalp_opportunities(self) -> List[Dict]:
        """สร้างโอกาส micro-scalping with source tracking"""
        opportunities = []
        current_price = self.technical.get_current_price()
        
        for offset in [1, 2, 3]:
            buy_price = current_price - offset
            sell_price = current_price + offset
            
            # 🏷️ Micro scalp comments
            buy_comment = OrderCommentManager.generate_comment(
                source_function="MICRO_SCALP",
                extra_info=f"BUY_M{offset}"
            )
            
            sell_comment = OrderCommentManager.generate_comment(
                source_function="MICRO_SCALP",
                extra_info=f"SELL_M{offset}"
            )
            
            opportunities.extend([
                {
                    'type': 'MICRO_SCALP',
                    'direction': 'BUY',
                    'price': buy_price,
                    'lot_size': 0.003,
                    'comment': buy_comment,
                    'profit_target': offset + 1,
                    'rebate_value': self.rebate_optimizer.calculate_rebate_value(0.003),
                    'reasoning': f'Micro scalp BUY @${buy_price:.2f}'
                },
                {
                    'type': 'MICRO_SCALP',
                    'direction': 'SELL',
                    'price': sell_price,
                    'lot_size': 0.003,
                    'comment': sell_comment,
                    'profit_target': offset + 1,
                    'rebate_value': self.rebate_optimizer.calculate_rebate_value(0.003),
                    'reasoning': f'Micro scalp SELL @${sell_price:.2f}'
                }
            ])
        
        return opportunities[:4]

    # 📊 Comment Analysis - เพิ่ม method สำหรับวิเคราะห์ comment

    def analyze_order_sources(self) -> Dict:
        """วิเคราะห์ที่มาของออเดอร์จาก comment"""
        try:
            source_stats = {}
            
            # Analyze pending orders
            for order in self.pending_orders.values():
                comment = order.get('comment', 'UNKNOWN')
                source = comment.split('_')[0]  # Get function name
                
                if source not in source_stats:
                    source_stats[source] = {'count': 0, 'total_lots': 0}
                
                source_stats[source]['count'] += 1
                source_stats[source]['total_lots'] += order.get('lot_size', 0)
            
            # Analyze active positions (if they have comments)
            for position in self.active_positions.values():
                comment = position.get('comment', 'UNKNOWN')
                if comment != 'UNKNOWN':
                    source = comment.split('_')[0]
                    
                    if source not in source_stats:
                        source_stats[source] = {'count': 0, 'total_lots': 0}
                    
                    source_stats[source]['count'] += 1
                    source_stats[source]['total_lots'] += position.get('lot_size', 0)
            
            return source_stats
            
        except Exception as e:
            print(f"❌ Order source analysis error: {e}")
            return {}

    def display_order_source_summary(self):
        """แสดงสรุปที่มาของออเดอร์"""
        try:
            source_stats = self.analyze_order_sources()
            
            if source_stats:
                print("📊 ORDER SOURCE SUMMARY:")
                print("-" * 40)
                for source, stats in source_stats.items():
                    print(f"   {source}: {stats['count']} orders, {stats['total_lots']:.3f} lots")
            
        except Exception as e:
            print(f"❌ Source summary error: {e}")

    def detect_and_fill_gaps(self):
        """Detect and fill price gaps with source tracking"""
        try:
            if len(self.pending_orders) < 4:
                return
            
            current_price = self.get_current_price()
            if not current_price:
                return
            
            # Find gaps (same logic as before)
            all_prices = [current_price]
            for order in self.pending_orders.values():
                all_prices.append(order.get('price', 0))
            
            all_prices = sorted([p for p in all_prices if p > 0])
            gap_threshold = self.grid_config['gap_threshold'] / 100
            
            gaps_found = 0
            for i in range(1, len(all_prices)):
                gap_size = all_prices[i] - all_prices[i-1]
                
                if gap_size > gap_threshold:
                    gap_center = (all_prices[i] + all_prices[i-1]) / 2
                    direction = 'BUY' if gap_center < current_price else 'SELL'
                    
                    if not self.level_exists_enhanced(gap_center, direction, gap_threshold * 0.3):
                        # 🏷️ Gap fill comment
                        comment = OrderCommentManager.generate_comment(
                            source_function="GAP_FILL",
                            extra_info=f"{direction}_G{gaps_found+1}"
                        )
                        
                        success = self.place_order_with_comment(
                            gap_center, direction, self.base_lot, comment
                        )
                        
                        if success:
                            gaps_found += 1
                            print(f"   🔧 Gap filled: {direction} @ ${gap_center:.2f} - {comment}")
                        time.sleep(0.2)
            
            if gaps_found > 0:
                print(f"✅ Filled {gaps_found} gaps")
                
        except Exception as e:
            print(f"❌ Gap detection error: {e}")

    def rebalance_portfolio(self):
        """Rebalance portfolio with source tracking"""
        try:
            # Count positions and orders by direction (same logic)
            buy_positions = len([p for p in self.active_positions.values() if p.get('direction') == 'BUY'])
            sell_positions = len([p for p in self.active_positions.values() if p.get('direction') == 'SELL'])
            buy_orders = len([o for o in self.pending_orders.values() if o.get('direction') == 'BUY'])
            sell_orders = len([o for o in self.pending_orders.values() if o.get('direction') == 'SELL'])
            
            total_buy = buy_positions + buy_orders
            total_sell = sell_positions + sell_orders
            imbalance = abs(total_buy - total_sell)
            
            if imbalance > self.grid_config['rebalance_threshold']:
                print(f"📊 Portfolio Rebalance needed: BUY:{total_buy} vs SELL:{total_sell}")
                
                # Determine which side needs more orders
                if total_buy < total_sell:
                    needed_direction = 'BUY'
                    orders_to_add = (total_sell - total_buy) // 2
                else:
                    needed_direction = 'SELL'
                    orders_to_add = (total_buy - total_sell) // 2
                
                # Add rebalancing orders with tracking
                current_price = self.get_current_price()
                if current_price and orders_to_add > 0:
                    spacing = self.calculate_dynamic_spacing()
                    spacing_dollars = spacing * 0.01
                    
                    for i in range(1, min(orders_to_add + 1, 4)):
                        if needed_direction == 'BUY':
                            order_price = current_price - (spacing_dollars * i)
                        else:
                            order_price = current_price + (spacing_dollars * i)
                        
                        if not self.level_exists_enhanced(order_price, needed_direction, spacing_dollars * 0.4):
                            # 🏷️ Rebalance comment
                            comment = OrderCommentManager.generate_comment(
                                source_function="REBALANCE",
                                extra_info=f"{needed_direction}_R{i}"
                            )
                            
                            success = self.place_order_with_comment(
                                order_price, needed_direction, self.base_lot, comment
                            )
                            
                            if success:
                                print(f"     ✅ Rebalance {needed_direction} L{i}: ${order_price:.2f} - {comment}")
                            time.sleep(0.3)
                    
                    print(f"✅ Rebalance orders added: {needed_direction}")
                    
        except Exception as e:
            print(f"❌ Portfolio rebalancing error: {e}")

    def execute_enhanced_profit_taking(self):
        """Enhanced profit taking with error handling"""
        try:
            if len(self.active_positions) < 2:
                return
            
            # Analyze all opportunities
            profit_opportunities = self.find_enhanced_profit_opportunities()
            
            if profit_opportunities:
                print(f"💰 Found {len(profit_opportunities)} profit opportunities")
                
                # Execute best opportunities (limit to 3 per cycle)
                executed_count = 0
                for opportunity in profit_opportunities[:3]:
                    try:
                        # Debug opportunity structure if needed
                        if hasattr(self, 'debug_mode') and self.debug_mode:
                            self.debug_opportunity_structure(opportunity)
                        
                        # Execute opportunity
                        success = self.execute_profit_opportunity(opportunity)
                        
                        if success:
                            executed_count += 1
                            print(f"   ✅ Opportunity {executed_count} executed successfully")
                        else:
                            print(f"   ❌ Opportunity execution failed")
                        
                        time.sleep(1)  # Wait between executions
                        
                    except Exception as e:
                        print(f"   ❌ Individual opportunity error: {e}")
                        continue
                
                if executed_count > 0:
                    print(f"🎉 Successfully executed {executed_count} profit opportunities")
                else:
                    print(f"⚠️ No opportunities were successfully executed")
            else:
                print(f"ℹ️ No profit opportunities found")
                
        except Exception as e:
            print(f"❌ Enhanced profit taking error: {e}")


    def find_enhanced_profit_opportunities(self) -> List[Dict]:
        """
        RESCUE ONLY SYSTEM - หักลบกัน ไม่คัทไม้ทิ้ง
        ⭐ เพิ่ม Portfolio Balance Protection
        """
        try:
            # ⭐ เพิ่มส่วนนี้ - Portfolio Balance Protection Control
            enable_balance_protection = getattr(self, 'portfolio_balance_protection', True)
            
            if enable_balance_protection:
                print("🛡️ RESCUE ONLY SYSTEM + PORTFOLIO BALANCE PROTECTION")
                # เช็ค portfolio balance ก่อน
                balance_info = self.check_portfolio_balance_ratio()
                print(f"📊 Portfolio Status: {balance_info['status']} - {balance_info['details']}")
                
                # ถ้า imbalance รุนแรง ใช้ balanced approach
                if balance_info['status'] in ['CRITICAL_IMBALANCE', 'SEVERE_IMBALANCE']:
                    print("🚨 Critical imbalance detected - using balanced approach")
                    return self.find_balanced_profit_opportunities()
            else:
                print("🛡️ RESCUE ONLY PROFIT SYSTEM - NO CUTTING LOSSES")
            
            print("=" * 60)
            
            positions = list(self.active_positions.values())
            if len(positions) < 1:
                return []
            
            # ⭐ ลบส่วนนี้ออก หรือ comment
            # filtered_positions = []
            # for pos in positions:
            #     ticket = pos.get('ticket')
            #     if self.is_position_trailing_protected(ticket):
            #         print(f"🔒 SKIP #{ticket} - has trailing protection")
            #         continue
            #     filtered_positions.append(pos)
            
            # ⭐ ใช้ positions ตรงๆ
            filtered_positions = positions  # ไม่ filter trailing

            # 📊 Step 1: Portfolio Analysis
            portfolio_analysis = self._analyze_portfolio_comprehensive(filtered_positions)
            
            # 🧠 Step 2: RESCUE STRATEGIES ONLY
            all_strategies = [
                self._strategy_high_profit_only(filtered_positions, portfolio_analysis),    # เก็บกําไรสูงเท่านั้น
                self._strategy_rescue_operations(filtered_positions, portfolio_analysis),   # หักลบช่วยเหลือ
                self._strategy_smart_rescue_combinations(filtered_positions, portfolio_analysis)  # รวมหักลบ
            ]
            
            # 🔄 Step 3: Merge Results
            merged_opportunities = []
            for strategy_results in all_strategies:
                merged_opportunities.extend(strategy_results)
            
            # ⭐ Step 3.5: Apply Balance Filter (ใหม่)
            if enable_balance_protection and merged_opportunities:
                print("🛡️ Applying balance filter to rescue opportunities...")
                filtered_opportunities = []
                blocked_count = 0
                
                for opportunity in merged_opportunities:
                    positions_to_check = opportunity.get('positions', [])
                    can_execute = True
                    
                    # เช็คแต่ละ position ใน opportunity
                    for pos_ticket in positions_to_check:
                        position = None
                        for pos in filtered_positions:
                            if pos.get('ticket') == pos_ticket:
                                position = pos
                                break
                        
                        if position:
                            safety_check = self.can_close_position_safely(position, opportunity.get('strategy', 'RESCUE'))
                            if not safety_check['can_close']:
                                can_execute = False
                                break
                    
                    if can_execute:
                        opportunity['balance_approved'] = True
                        filtered_opportunities.append(opportunity)
                    else:
                        blocked_count += 1
                
                print(f"📊 Balance Filter: {len(filtered_opportunities)} approved, {blocked_count} blocked")
                merged_opportunities = filtered_opportunities
            
            # 🎯 Step 4: Score & Sort
            final_opportunities = self._apply_rescue_scoring(merged_opportunities, portfolio_analysis)
            final_opportunities = self._final_rescue_optimization(final_opportunities, portfolio_analysis)
            
            print(f"\n🏆 RESCUE RESULTS:")
            print(f"   High Profit: {len([o for o in final_opportunities if o['strategy'] == 'HIGH_PROFIT'])}")
            print(f"   Rescue Pairs: {len([o for o in final_opportunities if o['strategy'] == 'RESCUE_OPERATIONS'])}")
            print(f"   Smart Combos: {len([o for o in final_opportunities if o['strategy'] == 'SMART_RESCUE'])}")
            
            # ⭐ เพิ่ม balance info ใน opportunities
            if enable_balance_protection:
                for opp in final_opportunities:
                    opp['balance_protected'] = True
                    opp['balance_status'] = getattr(self, '_current_balance_info', {}).get('status', 'UNKNOWN')
            
            return final_opportunities
            
        except Exception as e:
            print(f"❌ Rescue system error: {e}")
            return []
       
    def _final_rescue_optimization(self, opportunities, analysis) -> List[Dict]:
        """🚀 FINAL RESCUE OPTIMIZATION - ป้องกันซ้ำ"""
        try:
            if not opportunities:
                return []
            
            final_opportunities = []
            used_positions = set()
            
            for opp in opportunities:
                position_tickets = set(opp['positions'])
                
                # ป้องกันใช้ position ซ้ำ
                if not position_tickets.intersection(used_positions):
                    final_opportunities.append(opp)
                    used_positions.update(position_tickets)
                    
                    # จำกัดจำนวน
                    if len(final_opportunities) >= 10:
                        break
            
            return final_opportunities
            
        except Exception as e:
            return opportunities[:5]
    
    def _apply_rescue_scoring(self, opportunities, analysis) -> List[Dict]:
        """🎯 RESCUE SCORING - ให้คะแนนเฉพาะ rescue ที่ดี"""
        try:
            for opp in opportunities:
                # Base scores
                profit_score = opp['expected_profit'] * 20  # เน้นกำไรสุทธิ
                confidence_score = opp['confidence']
                
                # Strategy bonuses
                strategy_bonus = {
                    'HIGH_PROFIT': 30,      # เก็บกำไรสูง
                    'RESCUE_OPERATIONS': 50, # ช่วยเหลือหักลบ
                    'SMART_RESCUE': 40      # รวมอัจฉริยะ
                }.get(opp['strategy'], 0)
                
                # Rescue efficiency bonus
                rescue_bonus = 0
                if 'rescue_efficiency' in opp:
                    efficiency = opp['rescue_efficiency']
                    if efficiency <= 0.5:  # ช่วยได้ดี
                        rescue_bonus = 20
                    elif efficiency <= 0.8:
                        rescue_bonus = 10
                
                # Final score
                rescue_score = profit_score + confidence_score + strategy_bonus + rescue_bonus
                opp['rescue_score'] = round(rescue_score, 2)
            
            # Filter เฉพาะที่ได้คะแนนดี
            good_opportunities = [opp for opp in opportunities if opp['rescue_score'] >= 80]
            good_opportunities.sort(key=lambda x: x['rescue_score'], reverse=True)
            
            return good_opportunities
            
        except Exception as e:
            return opportunities
    
    def _strategy_smart_rescue_combinations(self, positions, analysis) -> List[Dict]:
        """🧠 SMART RESCUE COMBOS - หักลบอัจฉริยะ เฉพาะที่ได้กำไรสุทธิ"""
        opportunities = []
        
        try:
            if len(positions) < 3:
                return []
            
            profitable = analysis['profitable_positions']
            losing = analysis['losing_positions']
            
            if not profitable or not losing:
                return []
            
            # 🎯 3-5 Position Smart Rescue Combinations
            from itertools import combinations
            
            # ลองรวม profitable + losing positions
            for num_profitable in range(1, min(4, len(profitable) + 1)):
                for num_losing in range(1, min(4, len(losing) + 1)):
                    
                    if num_profitable + num_losing > 5:  # ไม่เกิน 5 positions
                        continue
                    
                    # ลองทุก combination
                    for profit_combo in combinations(profitable, num_profitable):
                        for loss_combo in combinations(losing, num_losing):
                            
                            total_profit = sum(pos.get('profit', 0) for pos in profit_combo)
                            total_loss = sum(pos.get('profit', 0) for pos in loss_combo)
                            net_profit = total_profit + total_loss
                            
                            # เฉพาะที่หักลบแล้วได้กำไรสุทธิ
                            if net_profit >= 2.0:  # ต้องได้กำไรสุทธิ
                                all_positions = list(profit_combo) + list(loss_combo)
                                tickets = [pos['ticket'] for pos in all_positions]
                                total_margin = sum(pos.get('lot_size', 0) for pos in all_positions) * 2000
                                
                                # คำนวณ rescue efficiency
                                rescue_efficiency = abs(total_loss) / total_profit if total_profit > 0 else 0
                                
                                opportunities.append({
                                    'strategy': 'SMART_RESCUE',
                                    'type': f'COMBO_{num_profitable}P_{num_losing}L',
                                    'positions': tickets,
                                    'expected_profit': net_profit,
                                    'confidence': 75,
                                    'reasoning': f"Smart combo: ${total_profit:.2f} rescues ${total_loss:.2f} = +${net_profit:.2f}",
                                    'rescue_efficiency': rescue_efficiency,
                                    'combo_size': len(all_positions),
                                    'urgency': 2,
                                    'impact_score': net_profit * 8,
                                    'margin_relief': total_margin
                                })
            
            # เรียงตาม net profit
            opportunities.sort(key=lambda x: x['expected_profit'], reverse=True)
            
            return opportunities[:15]  # เอาแค่ 15 อันดับแรก
            
        except Exception as e:
            print(f"❌ Smart rescue combinations error: {e}")
            return []
    
    def _strategy_high_profit_only(self, positions, analysis) -> List[Dict]:
        """🚀 เก็บแต่กำไรสูงๆ เท่านั้น - ไม่เก็บกำไรเล็กๆ"""
        opportunities = []
        
        try:
            profitable = analysis['profitable_positions']
            
            # 🔒 Filter out trailing-protected positions
            filtered_profitable = []
            for pos in profitable:
                ticket = pos.get('ticket')
                if self.is_position_trailing_protected(ticket):
                    print(f"🔒 SKIP #{ticket} - has trailing protection")
                    continue
                filtered_profitable.append(pos)
            
            for pos in filtered_profitable:
                profit = pos.get('profit', 0)
                age_minutes = self._calculate_position_age(pos)
                
                # เก็บแต่กำไรสูงหรืออายุเยอะ
                should_take = False
                reasoning = []
                
                if profit >= 8.0:  # กำไรสูง
                    should_take = True
                    reasoning.append(f"High profit ${profit:.2f}")
                elif profit >= 5.0 and age_minutes > 60:  # กำไรปานกลางแต่อายุเยอะ
                    should_take = True
                    reasoning.append(f"Aged profit ${profit:.2f} ({age_minutes}min)")
                elif profit >= 3.0 and age_minutes > 120:  # กำไรน้อยแต่อายุมาก
                    should_take = True
                    reasoning.append(f"Very aged profit ${profit:.2f} ({age_minutes}min)")
                
                if should_take:
                    opportunities.append({
                        'strategy': 'HIGH_PROFIT',
                        'type': 'SAFE_PROFIT_TAKING',
                        'positions': [pos['ticket']],
                        'expected_profit': profit,
                        'confidence': 90,
                        'reasoning': " | ".join(reasoning),
                        'urgency': 1,
                        'impact_score': profit * 10,
                        'margin_relief': pos.get('lot_size', 0) * 2000
                    })
            
            return opportunities
            
        except Exception as e:
            return []
    
    def _analyze_portfolio_comprehensive(self, positions) -> Dict:
        """
        🔍 Comprehensive Portfolio Analysis - วิเคราะห์ portfolio รอบด้าน
        """
        try:
            analysis = {
                'total_positions': len(positions),
                'profitable_positions': [],
                'losing_positions': [],
                'neutral_positions': [],
                'buy_positions': [],
                'sell_positions': [],
                'total_profit': 0,
                'total_loss': 0,
                'net_pnl': 0,
                'total_margin_used': 0,
                'portfolio_health': 0,
                'risk_level': 'UNKNOWN',
                'dominant_direction': 'NEUTRAL',
                'margin_pressure': False,
                'emergency_level': 0
            }
            
            # Basic categorization
            for pos in positions:
                profit = pos.get('profit', 0)
                direction = pos.get('direction', 'UNKNOWN')
                lot_size = pos.get('lot_size', 0)
                
                # Profit categorization
                if profit > 0.5:
                    analysis['profitable_positions'].append(pos)
                    analysis['total_profit'] += profit
                elif profit < -0.5:
                    analysis['losing_positions'].append(pos)
                    analysis['total_loss'] += profit
                else:
                    analysis['neutral_positions'].append(pos)
                
                # Direction categorization
                if direction == 'BUY':
                    analysis['buy_positions'].append(pos)
                elif direction == 'SELL':
                    analysis['sell_positions'].append(pos)
                
                # Margin calculation
                analysis['total_margin_used'] += lot_size * 2000
            
            analysis['net_pnl'] = analysis['total_profit'] + analysis['total_loss']
            
            # Advanced analysis
            analysis.update(self._calculate_portfolio_health(analysis))
            analysis.update(self._determine_risk_level(analysis))
            analysis.update(self._assess_margin_situation(analysis))
            
            return analysis
            
        except Exception as e:
            print(f"❌ Portfolio analysis error: {e}")
            return {'total_positions': len(positions), 'emergency_level': 5}

    def _calculate_portfolio_health(self, analysis) -> Dict:
        """คำนวณสุขภาพของ portfolio"""
        try:
            net_pnl = analysis['net_pnl']
            total_positions = analysis['total_positions']
            
            # Base health from P&L
            if net_pnl > 50:
                health = 90
            elif net_pnl > 20:
                health = 80
            elif net_pnl > 0:
                health = 70
            elif net_pnl > -20:
                health = 60
            elif net_pnl > -50:
                health = 40
            else:
                health = 20
            
            # Position count penalty
            if total_positions > 20:
                health -= 20
            elif total_positions > 15:
                health -= 10
            elif total_positions > 10:
                health -= 5
            
            return {
                'portfolio_health': max(0, min(100, health))
            }
        except Exception as e:
            return {'portfolio_health': 50}

    def _determine_risk_level(self, analysis) -> Dict:
        """กำหนดระดับความเสี่ยง - ไม่รุนแรง"""
        try:
            net_pnl = analysis['net_pnl']
            total_margin = analysis['total_margin_used']
            
            # ปรับให้ไม่รุนแรง
            if net_pnl < -200 or total_margin > 100000:  # เพิ่มเกณฑ์
                risk_level = 'HIGH'
                emergency_level = 3  # ลดจาก 5 เป็น 3
            elif net_pnl < -100 or total_margin > 50000:
                risk_level = 'MEDIUM'
                emergency_level = 2  # ลดจาก 4 เป็น 2
            elif net_pnl < -50 or total_margin > 30000:
                risk_level = 'LOW'
                emergency_level = 1  # ลดจาก 3 เป็น 1
            else:
                risk_level = 'VERY_LOW'
                emergency_level = 0  # ลดจาก 2 เป็น 0
            
            return {
                'risk_level': risk_level,
                'emergency_level': emergency_level
            }
        except Exception as e:
            return {'risk_level': 'LOW', 'emergency_level': 1}
    
    def _assess_margin_situation(self, analysis) -> Dict:
        """ประเมินสถานการณ์ margin"""
        try:
            total_margin = analysis['total_margin_used']
            
            # Get account info for free margin
            account_info = self.mt5_connector.get_account_info()
            free_margin = account_info.get('free_margin', 10000) if account_info else 10000
            
            margin_pressure = total_margin > (free_margin * 0.8)
            
            # Determine dominant direction
            buy_count = len(analysis['buy_positions'])
            sell_count = len(analysis['sell_positions'])
            
            if buy_count > sell_count * 1.5:
                dominant_direction = 'BUY'
            elif sell_count > buy_count * 1.5:
                dominant_direction = 'SELL'
            else:
                dominant_direction = 'NEUTRAL'
            
            return {
                'margin_pressure': margin_pressure,
                'dominant_direction': dominant_direction
            }
        except Exception as e:
            return {'margin_pressure': False, 'dominant_direction': 'NEUTRAL'}
    
    def _strategy_instant_profit(self, positions, analysis) -> List[Dict]:
        """
        🚀 Strategy 1: Instant Profit - เก็บกำไรด่วนอัจฉริยะ
        """
        opportunities = []
        
        try:
            profitable = analysis['profitable_positions']
            
            for pos in profitable:
                profit = pos.get('profit', 0)
                age_minutes = self._calculate_position_age(pos)
                
                # 🎯 Dynamic profit thresholds based on situation
                if analysis['emergency_level'] >= 4:
                    min_profit = 0.5  # ฉุกเฉิน - เก็บกำไรเล็กๆ
                elif analysis['portfolio_health'] > 80:
                    min_profit = 3.0  # สุขภาพดี - เก็บกำไรใหญ่
                elif analysis['margin_pressure']:
                    min_profit = 1.0  # มี margin pressure - เก็บกำไรปานกลาง
                else:
                    min_profit = 2.0  # ปกติ
                
                # 💡 Intelligent profit taking conditions
                should_take = False
                reasoning = []
                confidence = 50
                
                # High profit - always take
                if profit >= 5.0:
                    should_take = True
                    reasoning.append(f"High profit ${profit:.2f}")
                    confidence = 95
                    
                # Medium profit with conditions
                elif profit >= min_profit:
                    if age_minutes > 30:
                        should_take = True
                        reasoning.append(f"Aged profit ${profit:.2f} ({age_minutes}min)")
                        confidence = 80
                    elif analysis['emergency_level'] >= 3:
                        should_take = True
                        reasoning.append(f"Emergency profit taking ${profit:.2f}")
                        confidence = 85
                    elif analysis['margin_pressure'] and profit >= 1.5:
                        should_take = True
                        reasoning.append(f"Margin relief profit ${profit:.2f}")
                        confidence = 75
                
                # Small profit in emergency
                elif profit >= 0.5 and analysis['emergency_level'] >= 4:
                    should_take = True
                    reasoning.append(f"Emergency small profit ${profit:.2f}")
                    confidence = 60
                
                if should_take:
                    opportunities.append({
                        'strategy': 'INSTANT_PROFIT',
                        'type': 'SINGLE_PROFIT',
                        'positions': [pos['ticket']],
                        'expected_profit': profit,
                        'confidence': confidence,
                        'reasoning': " | ".join(reasoning),
                        'urgency': self._calculate_urgency(pos, analysis),
                        'impact_score': profit * 10,
                        'margin_relief': pos.get('lot_size', 0) * 2000
                    })
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Instant profit strategy error: {e}")
            return []

    def _strategy_rescue_operations(self, positions, analysis) -> List[Dict]:
        """🛡️ PURE RESCUE - หักลบช่วยเหลือเท่านั้น ไม่คัทไม้"""
        opportunities = []
        
        try:
            profitable = analysis['profitable_positions']
            losing = analysis['losing_positions']
            
            if not profitable or not losing:
                return []
            
            print(f"🔍 Rescue Analysis: {len(profitable)} profitable vs {len(losing)} losing")
            
            # 🔄 1:1 Perfect Rescue (กำไร + ขาดทุน = บวก)
            for profit_pos in profitable:
                profit_amt = profit_pos.get('profit', 0)
                
                for loss_pos in losing:
                    loss_amt = loss_pos.get('profit', 0)
                    net_profit = profit_amt + loss_amt
                    
                    # เฉพาะที่หักลบแล้วได้กำไร
                    if net_profit >= 1.0:  # ต้องได้กำไรสุทธิ
                        rescue_ratio = abs(loss_amt) / profit_amt if profit_amt > 0 else 0
                        
                        opportunities.append({
                            'strategy': 'RESCUE_OPERATIONS',
                            'type': 'PERFECT_RESCUE_1_1',
                            'positions': [profit_pos['ticket'], loss_pos['ticket']],
                            'expected_profit': net_profit,
                            'confidence': 85,
                            'reasoning': f"Rescue: ${profit_amt:.2f} saves ${loss_amt:.2f} = +${net_profit:.2f}",
                            'rescue_ratio': rescue_ratio,
                            'urgency': 3,
                            'impact_score': net_profit * 15,
                            'margin_relief': (profit_pos.get('lot_size', 0) + loss_pos.get('lot_size', 0)) * 2000
                        })
            
            # 🔄 1:2 Super Rescue (1 กำไรช่วย 2 ขาดทุน)
            for profit_pos in profitable:
                profit_amt = profit_pos.get('profit', 0)
                
                if profit_amt < 3.0:  # ต้องมีกำไรพอ
                    continue
                    
                for i, loss_pos1 in enumerate(losing):
                    for loss_pos2 in losing[i+1:]:
                        loss_amt1 = loss_pos1.get('profit', 0)
                        loss_amt2 = loss_pos2.get('profit', 0)
                        total_loss = loss_amt1 + loss_amt2
                        net_profit = profit_amt + total_loss
                        
                        # เฉพาะที่หักลบแล้วได้กำไร
                        if net_profit >= 2.0:  # ต้องได้กำไรสุทธิ
                            opportunities.append({
                                'strategy': 'RESCUE_OPERATIONS',
                                'type': 'SUPER_RESCUE_1_2',
                                'positions': [profit_pos['ticket'], loss_pos1['ticket'], loss_pos2['ticket']],
                                'expected_profit': net_profit,
                                'confidence': 80,
                                'reasoning': f"Super rescue: ${profit_amt:.2f} saves ${total_loss:.2f} = +${net_profit:.2f}",
                                'rescue_ratio': abs(total_loss) / profit_amt if profit_amt > 0 else 0,
                                'urgency': 4,
                                'impact_score': net_profit * 12,
                                'margin_relief': (profit_pos.get('lot_size', 0) + loss_pos1.get('lot_size', 0) + loss_pos2.get('lot_size', 0)) * 2000
                            })
            
            # 🔄 2:1 Power Rescue (2 กำไรช่วย 1 ขาดทุนใหญ่)
            for i, profit_pos1 in enumerate(profitable):
                for profit_pos2 in profitable[i+1:]:
                    profit_amt1 = profit_pos1.get('profit', 0)
                    profit_amt2 = profit_pos2.get('profit', 0)
                    total_profit = profit_amt1 + profit_amt2
                    
                    if total_profit < 4.0:  # ต้องมีกำไรรวมพอ
                        continue
                    
                    for loss_pos in losing:
                        loss_amt = loss_pos.get('profit', 0)
                        
                        if loss_amt > -15.0:  # เฉพาะขาดทุนใหญ่
                            continue
                            
                        net_profit = total_profit + loss_amt
                        
                        # เฉพาะที่หักลบแล้วได้กำไร
                        if net_profit >= 3.0:  # ต้องได้กำไรสุทธิ
                            opportunities.append({
                                'strategy': 'RESCUE_OPERATIONS',
                                'type': 'POWER_RESCUE_2_1',
                                'positions': [profit_pos1['ticket'], profit_pos2['ticket'], loss_pos['ticket']],
                                'expected_profit': net_profit,
                                'confidence': 85,
                                'reasoning': f"Power rescue: ${total_profit:.2f} saves ${loss_amt:.2f} = +${net_profit:.2f}",
                                'rescue_ratio': abs(loss_amt) / total_profit if total_profit > 0 else 0,
                                'urgency': 5,
                                'impact_score': net_profit * 20,
                                'margin_relief': (profit_pos1.get('lot_size', 0) + profit_pos2.get('lot_size', 0) + loss_pos.get('lot_size', 0)) * 2000
                            })
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Rescue operations error: {e}")
            return []
    
    def _strategy_smart_combinations(self, positions, analysis) -> List[Dict]:
        """
        🧠 Strategy 8: Smart Combinations - การรวมอัจฉริยะ
        """
        opportunities = []
        
        try:
            if len(positions) < 3:
                return []
            
            profitable = analysis['profitable_positions']
            losing = analysis['losing_positions']
            neutral = analysis['neutral_positions']
            
            # 🎯 Multi-position intelligent combinations
            all_pos = profitable + losing + neutral
            
            # ลองรวม 3-5 positions แบบต่างๆ
            for combo_size in [3, 4, 5]:
                if len(all_pos) < combo_size:
                    continue
                
                # Generate smart combinations
                from itertools import combinations
                for combo in list(combinations(all_pos, combo_size))[:20]:  # จำกัดไม่ให้เยอะเกิน
                    total_profit = sum(pos.get('profit', 0) for pos in combo)
                    total_margin = sum(pos.get('lot_size', 0) for pos in combo) * 2000
                    
                    # ประเมินความคุ้มค่า
                    is_valuable = False
                    reasoning = []
                    confidence = 40
                    
                    # High profit combination
                    if total_profit >= 5.0:
                        is_valuable = True
                        reasoning.append(f"High combo profit ${total_profit:.2f}")
                        confidence = 85
                    
                    # Emergency margin relief
                    elif analysis['margin_pressure'] and total_margin >= 2000:
                        if total_profit >= -3.0:  # ยอมขาดทุนเล็กน้อยเพื่อลด margin
                            is_valuable = True
                            reasoning.append(f"Emergency margin relief ${total_margin:.0f}")
                            confidence = 70
                    
                    # Portfolio rebalancing
                    elif self._improves_portfolio_balance(combo, analysis):
                        if total_profit >= 0.0:
                            is_valuable = True
                            reasoning.append(f"Portfolio rebalancing benefit")
                            confidence = 65
                    
                    # Emergency cleanup
                    elif analysis['emergency_level'] >= 4:
                        if total_profit >= -5.0:  # ยอมขาดทุนเพื่อลด positions
                            is_valuable = True
                            reasoning.append(f"Emergency position cleanup")
                            confidence = 55
                    
                    if is_valuable:
                        tickets = [pos['ticket'] for pos in combo]
                        
                        opportunities.append({
                            'strategy': 'SMART_COMBINATIONS',
                            'type': f'COMBO_{combo_size}_POSITIONS',
                            'positions': tickets,
                            'expected_profit': total_profit,
                            'confidence': confidence,
                            'reasoning': " | ".join(reasoning) + f" ({combo_size} positions)",
                            'combo_size': combo_size,
                            'complexity': combo_size * 10,
                            'urgency': analysis['emergency_level'],
                            'impact_score': total_profit * 5 + (total_margin / 100),
                            'margin_relief': total_margin
                        })
            
            # เรียงตาม impact score
            opportunities.sort(key=lambda x: x['impact_score'], reverse=True)
            
            return opportunities[:10]  # เอาแค่ 10 อันดับแรก
            
        except Exception as e:
            print(f"❌ Smart combinations error: {e}")
            return []

    def _apply_intelligence_scoring(self, opportunities, analysis) -> List[Dict]:
        """
        🧠 Apply Advanced Intelligence Scoring
        """
        try:
            for opp in opportunities:
                # Base scores
                profit_score = max(0, opp['expected_profit'] * 10)
                confidence_score = opp['confidence']
                urgency_score = opp.get('urgency', 0) * 10
                
                # Strategy bonuses
                strategy_bonus = {
                    'INSTANT_PROFIT': 20,
                    'RESCUE_OPERATIONS': 30,
                    'MARGIN_OPTIMIZATION': 25,
                    'PORTFOLIO_REBALANCING': 15,
                    'RISK_REDUCTION': 35,
                    'OPPORTUNITY_HARVESTING': 10,
                    'SMART_COMBINATIONS': 5
                }.get(opp['strategy'], 0)
                
                # Emergency multiplier
                emergency_multiplier = 1.0 + (analysis['emergency_level'] * 0.2)
                
                # Final intelligence score
                intelligence_score = (
                    profit_score * 0.3 +
                    confidence_score * 0.25 +
                    urgency_score * 0.2 +
                    strategy_bonus * 0.15 +
                    opp.get('impact_score', 0) * 0.1
                ) * emergency_multiplier
                
                opp['intelligence_score'] = round(intelligence_score, 2)
            
            # Filter and sort by intelligence score
            intelligent_opportunities = [opp for opp in opportunities if opp['intelligence_score'] >= 30]
            intelligent_opportunities.sort(key=lambda x: x['intelligence_score'], reverse=True)
            
            return intelligent_opportunities
            
        except Exception as e:
            print(f"❌ Intelligence scoring error: {e}")
            return opportunities

    def _final_optimization(self, opportunities, analysis) -> List[Dict]:
        """
        🚀 Final Optimization & Selection
        """
        try:
            if not opportunities:
                return []
            
            # ป้องกันการปิดไม้ซ้ำ
            final_opportunities = []
            used_positions = set()
            
            for opp in opportunities:
                position_tickets = set(opp['positions'])
                
                # เช็คว่าไม้ซ้ำกันหรือไม่
                if not position_tickets.intersection(used_positions):
                    final_opportunities.append(opp)
                    used_positions.update(position_tickets)
                    
                    # จำกัดจำนวนโอกาสตาม emergency level
                    max_opportunities = min(15, 5 + analysis['emergency_level'] * 2)
                    if len(final_opportunities) >= max_opportunities:
                        break
            
            return final_opportunities
            
        except Exception as e:
            print(f"❌ Final optimization error: {e}")
            return opportunities[:10]

    # Helper methods (เพิ่มตามต้องการ)
    def _calculate_position_age(self, position) -> int:
        """คำนวณอายุของ position ในหน่วยนาที"""
        try:
            from datetime import datetime
            created_time = position.get('timestamp', datetime.now())
            if isinstance(created_time, str):
                # Parse string timestamp if needed
                created_time = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
            age = (datetime.now() - created_time).total_seconds() / 60
            return int(age)
        except:
            return 0

    def _calculate_urgency(self, position, analysis) -> int:
        """คำนวณความเร่งด่วน 0-10"""
        urgency = 0
        
        # Emergency level
        urgency += analysis['emergency_level']
        
        # Position age
        age = self._calculate_position_age(position)
        if age > 60: urgency += 2
        elif age > 30: urgency += 1
        
        # Profit/loss magnitude
        profit = position.get('profit', 0)
        if profit > 5.0: urgency += 3
        elif profit < -10.0: urgency += 4
        
        return min(10, urgency)

    def _calculate_rescue_urgency(self, losing_position, analysis) -> int:
        """คำนวณความเร่งด่วนในการช่วย"""
        loss = abs(losing_position.get('profit', 0))
        urgency = analysis['emergency_level']
        
        if loss > 15.0: urgency += 4
        elif loss > 10.0: urgency += 3
        elif loss > 5.0: urgency += 2
        else: urgency += 1
        
        return min(10, urgency)

    def _improves_portfolio_balance(self, combo, analysis) -> bool:
        """เช็คว่า combo นี้ช่วยปรับปรุง portfolio balance หรือไม่"""
        buy_count = len([p for p in combo if p.get('direction') == 'BUY'])
        sell_count = len([p for p in combo if p.get('direction') == 'SELL'])
        
        current_buy = len(analysis['buy_positions'])
        current_sell = len(analysis['sell_positions'])
        current_imbalance = abs(current_buy - current_sell)
        
        new_buy = current_buy - buy_count
        new_sell = current_sell - sell_count
        new_imbalance = abs(new_buy - new_sell)
        
        return new_imbalance < current_imbalance

    def get_current_trading_status(self) -> Dict:
        """Get current trading status for volume boost analysis"""
        try:
            enhancement_status = self.smart_enhancer.get_enhancement_status()
            
            return {
                'current_volume': enhancement_status['daily_volume'],
                'daily_rebate': enhancement_status['daily_rebate'],
                'target_rebate': enhancement_status['rebate_target'],
                'market_condition': self.detect_market_condition(),
                'active_positions': len(self.active_positions),
                'pending_orders': len(self.pending_orders)
            }
        except Exception as e:
            print(f"⚠️ Status retrieval error: {e}")
            return {
                'current_volume': 0.05,
                'daily_rebate': 10.0,
                'target_rebate': 50.0,
                'market_condition': 'RANGING',
                'active_positions': 5,
                'pending_orders': 3
            }

    def detect_market_condition(self) -> str:
        """Simple market condition detection"""
        try:
            if hasattr(self.smart_enhancer.technical, 'analyze_trend'):
                trend_data = self.smart_enhancer.technical.analyze_trend()
                trend_direction = trend_data.get('direction', 'SIDEWAYS')
                
                if trend_direction == 'UPTREND':
                    return 'TRENDING_UP'
                elif trend_direction == 'DOWNTREND':
                    return 'TRENDING_DOWN'
                else:
                    return 'RANGING'
            else:
                return 'RANGING'
        except:
            return 'RANGING'

    def get_current_market_condition(self) -> str:
        """Get current market condition for enhancement"""
        return self.detect_market_condition()

    def track_enhancement_performance(self, enhancement):
        """Track enhancement performance for learning"""
        try:
            if not hasattr(self, 'enhancement_stats'):
                self.enhancement_stats = {
                    'total_enhanced_orders': 0,
                    'successful_enhancements': 0,
                    'total_confidence_score': 0,
                    'tier_performance': {}
                }
            
            self.enhancement_stats['total_enhanced_orders'] += 1
            self.enhancement_stats['total_confidence_score'] += enhancement.confidence
            
            tier = enhancement.tier.value
            if tier not in self.enhancement_stats['tier_performance']:
                self.enhancement_stats['tier_performance'][tier] = {'count': 0, 'success': 0}
            
            self.enhancement_stats['tier_performance'][tier]['count'] += 1
            
        except Exception as e:
            print(f"⚠️ Enhancement tracking error: {e}")

    def track_skipped_order(self, enhancement):
        """Track skipped orders for analysis"""
        try:
            if not hasattr(self, 'skipped_stats'):
                self.skipped_stats = {
                    'total_skipped': 0,
                    'low_confidence_skips': 0,
                    'technical_skips': 0
                }
            
            self.skipped_stats['total_skipped'] += 1
            
            if enhancement.confidence < 30:
                self.skipped_stats['low_confidence_skips'] += 1
            else:
                self.skipped_stats['technical_skips'] += 1
                
        except Exception as e:
            print(f"⚠️ Skipped tracking error: {e}")

    def fallback_original_order_placement(self, price: float, direction: str, order_type: str) -> bool:
        """Fallback to original order placement logic"""
        try:
            print(f"       🔄 Falling back to original order placement...")
            
            # Original logic (simplified version)
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                return False
            
            symbol_info = mt5.symbol_info(self.gold_symbol)
            if not symbol_info:
                return False
            
            volume = max(symbol_info.volume_min, self.base_lot)
            order_type_int = 2 if direction == "BUY" else 3
            
            request = {
                "action": 5,
                "symbol": self.gold_symbol,
                "volume": volume,
                "type": order_type_int,
                "price": round(price, 2),
                "magic": self.magic_number,
                "comment": f"FALLBACK_{direction}"
            }
            
            result = mt5.order_send(request)
            
            if result and result.retcode == 10009:
                self.pending_orders[result.order] = {
                    'order_id': result.order,
                    'price': round(price, 2),
                    'direction': direction,
                    'lot_size': volume,
                    'ai_type': 'FALLBACK',
                    'enhancement_used': False,
                    'timestamp': datetime.now()
                }
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Fallback order placement error: {e}")
            return False

    def get_enhancement_summary(self) -> Dict:
        """Get summary of enhancement performance"""
        try:
            enhancement_status = self.smart_enhancer.get_enhancement_status()
            
            # Calculate enhancement efficiency
            total_orders = getattr(self, 'enhancement_stats', {}).get('total_enhanced_orders', 0)
            skipped_orders = getattr(self, 'skipped_stats', {}).get('total_skipped', 0)
            
            if total_orders + skipped_orders > 0:
                efficiency = (total_orders / (total_orders + skipped_orders)) * 100
            else:
                efficiency = 0
            
            return {
                'enhancement_enabled': enhancement_status['enabled'],
                'daily_volume': enhancement_status['daily_volume'],
                'daily_rebate': enhancement_status['daily_rebate'],
                'rebate_progress': (enhancement_status['daily_rebate'] / enhancement_status['rebate_target']) * 100,
                'orders_enhanced': total_orders,
                'orders_skipped': skipped_orders,
                'enhancement_efficiency': round(efficiency, 1),
                'avg_confidence': round(getattr(self, 'enhancement_stats', {}).get('total_confidence_score', 0) / max(total_orders, 1), 1)
            }
            
        except Exception as e:
            print(f"⚠️ Enhancement summary error: {e}")
            return {
                'enhancement_enabled': True,
                'daily_volume': 0,
                'daily_rebate': 0,
                'rebate_progress': 0,
                'orders_enhanced': 0,
                'orders_skipped': 0,
                'enhancement_efficiency': 0,
                'avg_confidence': 0
            }
    
    def combine_all_opportunities(self, enhanced_opportunities: List, volume_boosts: List) -> List[Dict]:
        """Combine and prioritize all opportunities"""
        combined = []
        
        try:
            # Convert enhanced opportunities
            for enh_opp in enhanced_opportunities:
                total_value = enh_opp.expected_profit + enh_opp.rebate_bonus
                
                combined.append({
                    'type': 'PROFIT_TAKING',
                    'positions': enh_opp.positions,
                    'expected_profit': enh_opp.expected_profit,
                    'rebate_bonus': enh_opp.rebate_bonus,
                    'total_value': total_value,
                    'confidence': enh_opp.confidence,
                    'tier': enh_opp.tier,
                    'reasoning': enh_opp.reasoning,
                    'priority': 'HIGH' if enh_opp.confidence >= 80 else 'MEDIUM'
                })
            
            # Convert volume boosts
            for boost in volume_boosts:
                combined.append({
                    'type': 'VOLUME_BOOST',
                    'action': 'PLACE_ORDER',
                    'direction': boost['direction'],
                    'price': boost['price'],
                    'lot_size': boost['lot_size'],
                    'expected_profit': boost['profit_target'],
                    'rebate_bonus': boost['rebate_value'],
                    'total_value': boost['profit_target'] + boost['rebate_value'],
                    'confidence': 60,  # Medium confidence for volume trades
                    'tier': boost['type'],
                    'reasoning': boost['reasoning'],
                    'priority': 'LOW'
                })
            
            # Sort by total value and confidence
            combined.sort(key=lambda x: (x['total_value'] + x['confidence']/10), reverse=True)
            
            return combined
            
        except Exception as e:
            print(f"❌ Opportunity combination error: {e}")
            return []
    
    def find_original_profit_opportunities(self) -> List[Dict]:
        """Original profit finding logic (unchanged)"""
        opportunities = []
        
        try:
            positions = list(self.active_positions.values())
            if len(positions) < 2:
                return opportunities
            
            # 🔒 Filter out trailing-protected positions
            filtered_positions = []
            for p in positions:
                ticket = p.get('ticket')
                if self.is_position_trailing_protected(ticket):
                    print(f"🔒 SKIP #{ticket} - has trailing protection")
                    continue
                filtered_positions.append(p)
            
            profitable_positions = [p for p in filtered_positions if p.get('profit', 0) > 0]
            
            # Strategy 1: Single profitable positions (>$3)
            for pos in profitable_positions:
                profit = pos.get('profit', 0)
                if profit > 3.0:
                    opportunities.append({
                        'type': 'SINGLE_PROFIT',
                        'positions': [pos['ticket']],
                        'expected_profit': profit,
                        'confidence': 0.9,
                        'description': f"Single profit: ${profit:.2f}"
                    })
            
            # Strategy 2: Profitable pairs
            for i, pos1 in enumerate(profitable_positions):
                for pos2 in profitable_positions[i+1:]:
                    total_profit = pos1.get('profit', 0) + pos2.get('profit', 0)
                    if total_profit > 2.0:
                        opportunities.append({
                            'type': 'PROFIT_PAIR',
                            'positions': [pos1['ticket'], pos2['ticket']],
                            'expected_profit': total_profit,
                            'confidence': 0.8,
                            'description': f"Profit pair: ${total_profit:.2f}"
                        })
            
            # Strategy 3: Rescue pairs
            losing_positions = [p for p in filtered_positions if p.get('profit', 0) < 0]
            
            for profit_pos in profitable_positions:
                for loss_pos in losing_positions:
                    net_profit = profit_pos.get('profit', 0) + loss_pos.get('profit', 0)
                    if net_profit > 1.0:
                        opportunities.append({
                            'type': 'RESCUE_PAIR',
                            'positions': [profit_pos['ticket'], loss_pos['ticket']],
                            'expected_profit': net_profit,
                            'confidence': 0.7,
                            'description': f"Rescue pair: ${net_profit:.2f}"
                        })
            
            # Sort by profit
            opportunities.sort(key=lambda x: x['expected_profit'], reverse=True)
            return opportunities[:5]
            
        except Exception as e:
            print(f"❌ Original profit opportunities error: {e}")
            return []

    def execute_profit_opportunity(self, opportunity: Dict) -> bool:
        """
        ⚡ ปิดไม้ตาม opportunity - เพิ่ม Balance Protection Double-check
        แก้ไขจาก method เดิม เพิ่ม safety check
        """
        try:
            # ⭐ เพิ่ม Balance Protection Double-check
            enable_balance_protection = getattr(self, 'portfolio_balance_protection', True)
            
            if enable_balance_protection and not opportunity.get('balance_emergency', False):
                # Double-check ก่อนปิดจริง
                positions_to_close = opportunity.get('positions', [])
                
                for pos_ticket in positions_to_close:
                    # หา position data
                    position = None
                    for pos in self.active_positions.values():
                        if pos.get('ticket') == pos_ticket:
                            position = pos
                            break
                    
                    if position:
                        final_safety_check = self.can_close_position_safely(position, 'FINAL_CHECK')
                        
                        if not final_safety_check['can_close']:
                            print(f"🚫 Final safety check BLOCKED position #{pos_ticket}")
                            print(f"    Reason: {final_safety_check['reason']}")
                            print(f"    Alternative: {final_safety_check['alternative_action']}")
                            return False  # ไม่ปิด
            
            # 📊 Original execution logic (ไม่แก้)
            strategy = opportunity.get('strategy', 'UNKNOWN')
            positions_to_close = opportunity.get('positions', [])
            expected_profit = opportunity.get('expected_profit', 0)
            
            print(f"⚡ Executing {strategy}: {len(positions_to_close)} positions, ${expected_profit:.2f}")
            
            success_count = 0
            total_profit = 0
            
            for ticket in positions_to_close:
                if ticket in self.active_positions:
                    position = self.active_positions[ticket]
                    
                    # 🎯 เพิ่มส่วนนี้ - Balance-aware comment
                    balance_comment = ""
                    if enable_balance_protection and opportunity.get('balance_filtered'):
                        balance_comment = f"|BAL:{opportunity.get('balance_status', 'UNK')}"
                    
                    comment = f"{strategy}|${position.get('profit', 0):.1f}{balance_comment}"
                    
                    # ปิด position (logic เดิม)
                    if self.close_position(ticket, comment):
                        success_count += 1
                        total_profit += position.get('profit', 0)
                        print(f"     ✅ Closed #{ticket}: ${position.get('profit', 0):.2f}")
                    else:
                        print(f"     ❌ Failed to close #{ticket}")
                    
                    time.sleep(0.1)
            
            # รายงานผล (เดิม)
            if success_count > 0:
                print(f"🎉 {strategy} completed: {success_count}/{len(positions_to_close)} closed, "
                    f"${total_profit:.2f} profit")
                return True
            else:
                print(f"❌ {strategy} failed: No positions closed")
                return False
                
        except Exception as e:
            #print(f"❌ Execute profit opportunity error: {e}")
            return False

    def debug_opportunity_structure(self, opportunity):
        """Debug helper to understand opportunity structure"""
        try:
            print(f"🔍 DEBUG: Opportunity Structure Analysis")
            print(f"   Type: {type(opportunity)}")
            
            if hasattr(opportunity, '__dict__'):
                print(f"   Attributes: {list(opportunity.__dict__.keys())}")
                for key, value in opportunity.__dict__.items():
                    print(f"      {key}: {value}")
            elif isinstance(opportunity, dict):
                print(f"   Dictionary Keys: {list(opportunity.keys())}")
                for key, value in opportunity.items():
                    print(f"      {key}: {value}")
            else:
                print(f"   Raw Value: {opportunity}")
                
        except Exception as e:
            print(f"   Debug error: {e}")

    def close_position_by_ticket(self, ticket: int) -> bool:
        """Close position by ticket number"""
        try:
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return False
            
            pos = position[0]
            
            # Determine close parameters
            if pos.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(pos.symbol).bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(pos.symbol).ask
            
            # Create close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "magic": self.magic_number,
                "comment": "AI_PROFIT_CLOSE"
            }
            
            # Execute close
            result = mt5.order_send(request)
            
            if result and result.retcode == 10009:
                # Remove from tracking
                if ticket in self.active_positions:
                    del self.active_positions[ticket]
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Position close error: {e}")
            return False

    def cleanup_stale_orders(self):
        """Remove old or stale pending orders"""
        try:
            current_time = datetime.now()
            stale_orders = []
            
            for order_id, order_info in self.pending_orders.items():
                order_time = order_info.get('timestamp', current_time)
                age_minutes = (current_time - order_time).total_seconds() / 60
                
                # Remove orders older than 60 minutes
                if age_minutes > 60:
                    stale_orders.append(order_id)
            
            for order_id in stale_orders:
                self.cancel_order_by_ticket(order_id)
                
            if stale_orders:
                print(f"🧹 Cleaned {len(stale_orders)} stale orders")
                
        except Exception as e:
            print(f"❌ Stale order cleanup error: {e}")

    def cancel_order_by_ticket(self, ticket: int) -> bool:
        """Cancel pending order by ticket"""
        try:
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": ticket
            }
            
            result = mt5.order_send(request)
            
            if result and result.retcode == 10009:
                if ticket in self.pending_orders:
                    del self.pending_orders[ticket]
                return True
            return False
            
        except Exception as e:
            print(f"❌ Order cancellation error: {e}")
            return False

    def ai_enhanced_monitoring_loop(self):
        """Enhanced monitoring loop"""
        print("👁️ AI ENHANCED MONITORING: Starting comprehensive monitoring...")
        
        while self.ai_active:
            try:
                # Update positions from MT5
                old_position_count = len(self.active_positions)
                old_pending_count = len(self.pending_orders)
                
                self.ai_update_positions_from_mt5()
                
                new_position_count = len(self.active_positions)
                new_pending_count = len(self.pending_orders)
                
                # Detect filled orders
                if new_position_count > old_position_count:
                    filled_orders = new_position_count - old_position_count
                    print(f"✅ {filled_orders} order(s) filled! New positions opened")
                
                # Detect closed positions
                if new_position_count < old_position_count:
                    closed_positions = old_position_count - new_position_count
                    print(f"💰 {closed_positions} position(s) closed!")
                
                # Log status every 30 seconds
                if not hasattr(self, 'last_status_log'):
                    self.last_status_log = datetime.now()
                elif (datetime.now() - self.last_status_log).total_seconds() >= 30:
                    self.log_enhanced_status()
                    self.last_status_log = datetime.now()
                
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Enhanced monitoring error: {e}")
                time.sleep(5)
        
        print("🛑 Enhanced AI Monitoring: Stopped")

    def log_enhanced_status(self):
        """Log enhanced system status with Support info"""
        try:
            current_price = self.get_current_price()
            health_score = self.ai_health_score
            
            buy_positions = len([p for p in self.active_positions.values() if p.get('direction') == 'BUY'])
            sell_positions = len([p for p in self.active_positions.values() if p.get('direction') == 'SELL'])
            buy_orders = len([o for o in self.pending_orders.values() if o.get('direction') == 'BUY'])
            sell_orders = len([o for o in self.pending_orders.values() if o.get('direction') == 'SELL'])
            
            total_profit = sum(p.get('profit', 0) for p in self.active_positions.values())
            
            # 🛡️ NEW: Support System Info
            support_count = len(self.portfolio_support_positions)
            trailing_count = len(self.support_trailing_data)
            support_value = sum(self.active_positions.get(ticket, {}).get('profit', 0) 
                            for ticket in self.portfolio_support_positions.keys())
            
            print("=" * 80)
            print("📊 ENHANCED AI GRID STATUS")
            print(f"💰 Current Price: ${current_price:.2f}")
            print(f"🧠 AI Health: {health_score:.1f}/100")
            print(f"📈 Positions: BUY:{buy_positions} | SELL:{sell_positions}")
            print(f"📋 Orders: BUY:{buy_orders} | SELL:{sell_orders}")
            print(f"💵 Total P&L: ${total_profit:.2f}")
            print(f"🎯 Dynamic Spacing: {self.calculate_dynamic_spacing()} points")
            print(f"🛡️ Support System: {support_count} positions (${support_value:.2f})")
            print(f"🔄 Trailing Active: {trailing_count} positions")
            print("=" * 80)
            
        except Exception as e:
            print(f"❌ Status logging error: {e}")

    # Utility methods (keeping existing ones and adding new)
    def get_current_price(self) -> Optional[float]:
        """Get current gold price"""
        try:
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if tick:
                return (tick.ask + tick.bid) / 2
            return None
        except:
            return None

    def get_current_drawdown_points(self) -> float:
        """Calculate current drawdown in points"""
        try:
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return 0.0
            
            balance = account_info.get('balance', 0)
            equity = account_info.get('equity', 0)
            
            if balance <= 0:
                return 0.0
            
            drawdown_dollars = balance - equity
            if drawdown_dollars <= 0:
                return 0.0
            
            # Convert to points (assuming $1 per point for base lot)
            drawdown_points = drawdown_dollars / self.base_lot * 100
            return max(0, drawdown_points)
            
        except Exception as e:
            print(f"❌ Drawdown calculation error: {e}")
            return 0.0

    def ai_update_positions_from_mt5(self):
        """Update positions and orders from MT5"""
        try:
            # Update active positions
            positions = mt5.positions_get(symbol=self.gold_symbol)
            current_positions = {}
            
            if positions:
                for pos in positions:
                    if pos.magic == self.magic_number:
                        direction = 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL'
                        current_positions[pos.ticket] = {
                            'ticket': pos.ticket,
                            'direction': direction,
                            'lot_size': pos.volume,
                            'price_open': pos.price_open,
                            'price_current': pos.price_current,
                            'profit': pos.profit,
                            'timestamp': datetime.fromtimestamp(pos.time)
                        }
            
            self.active_positions = current_positions
            
            # Update pending orders
            orders = mt5.orders_get(symbol=self.gold_symbol)
            current_orders = {}
            
            if orders:
                for order in orders:
                    if order.magic == self.magic_number:
                        direction = 'BUY' if order.type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP] else 'SELL'
                        current_orders[order.ticket] = {
                            'order_id': order.ticket,
                            'direction': direction,
                            'lot_size': order.volume_initial,
                            'price': order.price_open,
                            'timestamp': datetime.fromtimestamp(order.time_setup)
                        }
            
            self.pending_orders = current_orders
            
        except Exception as e:
            print(f"❌ Position update error: {e}")

    def ai_calculate_portfolio_health(self) -> float:
        """Calculate portfolio health score"""
        try:
            if not self.active_positions:
                return 75.0  # Good health when no positions
            
            total_profit = sum(p.get('profit', 0) for p in self.active_positions.values())
            position_count = len(self.active_positions)
            
            # Base health from profit
            if total_profit > 20:
                profit_health = 90
            elif total_profit > 10:
                profit_health = 80
            elif total_profit > 0:
                profit_health = 70
            elif total_profit > -10:
                profit_health = 60
            elif total_profit > -30:
                profit_health = 40
            else:
                profit_health = 20
            
            # Adjust for position count
            if position_count > 15:
                count_penalty = -10
            elif position_count > 10:
                count_penalty = -5
            else:
                count_penalty = 0
            
            # Adjust for drawdown
            drawdown_points = self.get_current_drawdown_points()
            if self.survivability > 0:
                drawdown_ratio = drawdown_points / self.survivability
                if drawdown_ratio > 0.7:
                    drawdown_penalty = -20
                elif drawdown_ratio > 0.5:
                    drawdown_penalty = -10
                elif drawdown_ratio > 0.3:
                    drawdown_penalty = -5
                else:
                    drawdown_penalty = 0
            else:
                drawdown_penalty = 0
            
            health_score = max(10, min(100, profit_health + count_penalty + drawdown_penalty))
            return health_score
            
        except Exception as e:
            print(f"❌ Portfolio health calculation error: {e}")
            return 50.0

    def ai_analyze_market_condition(self) -> Optional[AIMarketAnalysis]:
        """Analyze current market conditions"""
        try:
            # Get recent price history
            price_history = self.get_recent_price_history(20)
            if len(price_history) < 5:
                return self.create_fallback_analysis()
            
            current_price = price_history[-1]
            
            # Calculate volatility
            price_changes = [abs(price_history[i] - price_history[i-1]) for i in range(1, len(price_history))]
            avg_change = sum(price_changes) / len(price_changes) if price_changes else 0
            
            volatility_score = min(100, (avg_change / 2.0) * 100)
            
            # Calculate trend
            if len(price_history) >= 10:
                recent_avg = sum(price_history[-5:]) / 5
                older_avg = sum(price_history[-10:-5]) / 5
                trend_strength = (recent_avg - older_avg) * 10
            else:
                trend_strength = 0
            
            # Determine market condition
            if volatility_score > 70:
                condition = MarketCondition.HIGH_VOLATILITY
            elif volatility_score < 30:
                condition = MarketCondition.LOW_VOLATILITY
            elif trend_strength > 5:
                condition = MarketCondition.TRENDING_UP
            elif trend_strength < -5:
                condition = MarketCondition.TRENDING_DOWN
            else:
                condition = MarketCondition.RANGING
            
            # Calculate optimal spacing
            optimal_spacing = self.calculate_dynamic_spacing()
            
            return AIMarketAnalysis(
                condition=condition,
                volatility_score=volatility_score,
                trend_strength=trend_strength,
                support_level=min(price_history[-10:]) if len(price_history) >= 10 else current_price - 10,
                resistance_level=max(price_history[-10:]) if len(price_history) >= 10 else current_price + 10,
                optimal_spacing=optimal_spacing,
                recommended_action="ENHANCED_GRID_MANAGEMENT",
                confidence=0.8
            )
            
        except Exception as e:
            print(f"❌ Market analysis error: {e}")
            return self.create_fallback_analysis()

    def create_fallback_analysis(self) -> AIMarketAnalysis:
        """Create fallback market analysis"""
        current_price = self.get_current_price() or 2000.0
        optimal_spacing = self.calculate_dynamic_spacing()
        
        return AIMarketAnalysis(
            condition=MarketCondition.RANGING,
            volatility_score=50.0,
            trend_strength=0.0,
            support_level=current_price - 20,
            resistance_level=current_price + 20,
            optimal_spacing=optimal_spacing,
            recommended_action="ENHANCED_GRID_MANAGEMENT",
            confidence=0.6
        )

    def get_recent_price_history(self, count: int) -> List[float]:
        """Get recent price history - Fixed MT5 method"""
        try:
            # 🔧 Fix: Use copy_rates_from_pos instead of copy_ticks_from_pos
            rates = mt5.copy_rates_from_pos(self.gold_symbol, mt5.TIMEFRAME_M1, 0, count)
            
            if rates is not None and len(rates) > 0:
                # Use close prices
                prices = [float(rate['close']) for rate in rates]
                print(f"   📊 Got {len(prices)} price history points")
                return prices
            
            print(f"   ⚠️ No rates data, trying alternative method...")
            
            # Alternative method: use symbol_info_tick multiple times
            current_price = self.get_current_price()
            if current_price:
                # Create fake history with small variations
                import random
                prices = []
                base_price = current_price
                
                for i in range(count):
                    # Add small random variation (±$2)
                    variation = random.uniform(-2.0, 2.0)
                    price = base_price + variation
                    prices.append(round(price, 2))
                
                print(f"   🔄 Generated {len(prices)} fallback prices around ${current_price:.2f}")
                return prices
            
            print(f"   ❌ Cannot get any price data")
            return []
            
        except Exception as e:
            print(f"❌ Price history error: {e}")
            
            # Final fallback
            try:
                tick = mt5.symbol_info_tick(self.gold_symbol)
                if tick:
                    price = (tick.ask + tick.bid) / 2
                    return [price] * min(count, 5)
            except:
                pass
            
            return []
    
    def validate_symbol_and_account(self) -> bool:
        """Validate symbol and account before trading"""
        try:
            print("🔍 Validating symbol and account...")
            
            # Check symbol info
            symbol_info = mt5.symbol_info(self.gold_symbol)
            if not symbol_info:
                print(f"❌ Symbol {self.gold_symbol} not found")
                return False
            
            # Make symbol visible if needed
            if not symbol_info.visible:
                print(f"⚠️ Making {self.gold_symbol} visible...")
                if not mt5.symbol_select(self.gold_symbol, True):
                    print(f"❌ Failed to select symbol {self.gold_symbol}")
                    return False
            
            # Check account info
            account_info = mt5.account_info()
            if not account_info:
                print("❌ Cannot get account info")
                return False
            
            if not account_info.trade_allowed:
                print("❌ Trading not allowed on this account")
                return False
            
            # Log symbol specifications
            print(f"✅ Symbol validation successful:")
            print(f"   📊 Symbol: {symbol_info.name}")
            print(f"   📊 Visible: {symbol_info.visible}")
            print(f"   📊 Trade mode: {symbol_info.trade_mode}")
            print(f"   📊 Volume min: {symbol_info.volume_min}")
            print(f"   📊 Volume max: {symbol_info.volume_max}")
            print(f"   📊 Volume step: {symbol_info.volume_step}")
            print(f"   📊 Digits: {symbol_info.digits}")
            print(f"   📊 Point: {symbol_info.point}")
            
            return True
            
        except Exception as e:
            print(f"❌ Symbol validation error: {e}")
            return False
    
    def stop_ai_trading(self):
        """Stop AI trading system with Support System cleanup"""
        try:
            print("🛑 Stopping Enhanced AI Grid System...")
            self.ai_active = False
            
            # 🛡️ NEW: Cleanup Support System
            try:
                print("🧹 Cleaning up Support System...")
                self.portfolio_support_positions.clear()
                self.support_trailing_data.clear()
                print("✅ Support System cleaned")
            except Exception as e:
                print(f"⚠️ Support cleanup error: {e}")
            
            # Wait for threads to finish
            if hasattr(self, 'ai_main_thread'):
                self.ai_main_thread.join(timeout=5)
            if hasattr(self, 'ai_monitor_thread'):
                self.ai_monitor_thread.join(timeout=5)
            
            print("✅ Enhanced AI Grid System stopped")
            
        except Exception as e:
            print(f"❌ Stop AI trading error: {e}")

    def get_ai_status(self) -> Dict:
        """Get comprehensive AI status with Support System"""
        try:
            current_price = self.get_current_price()
            
            # 🛡️ NEW: Support System Status
            support_positions_count = len(self.portfolio_support_positions)
            trailing_positions_count = len(self.support_trailing_data)
            
            # คำนวณ total support value
            total_support_value = 0
            for ticket, support_data in self.portfolio_support_positions.items():
                if ticket in self.active_positions:
                    current_profit = self.active_positions[ticket].get('profit', 0)
                    total_support_value += current_profit
            
            base_status = {
                'ai_active': self.ai_active,
                'ai_health_score': self.ai_health_score,
                'current_price': current_price,
                'active_positions': len(self.active_positions),
                'pending_orders': len(self.pending_orders),
                'total_profit': sum(p.get('profit', 0) for p in self.active_positions.values()),
                'dynamic_spacing': self.calculate_dynamic_spacing(),
                'market_condition': self.market_analysis.condition.value if self.market_analysis else 'UNKNOWN',
                'survivability_usage': self.get_current_drawdown_points() / self.survivability if self.survivability > 0 else 0,
                
                # 🛡️ NEW: Support System Status
                'support_positions': support_positions_count,
                'trailing_positions': trailing_positions_count,
                'total_support_value': round(total_support_value, 2),
                'support_system_active': support_positions_count > 0,
                
                'last_update': datetime.now().isoformat()
            }
            
            return base_status
            
        except Exception as e:
            print(f"❌ Status retrieval error: {e}")
            return {'error': str(e)}
            
    def _strategy_margin_optimization(self, positions, analysis) -> List[Dict]:
        """Strategy 3: Margin Optimization - เพิ่มประสิทธิภาพ margin"""
        opportunities = []
        
        try:
            if not analysis['margin_pressure']:
                return []
            
            # หาไม้ที่ใช้ margin เยอะที่สุด
            high_margin_positions = [pos for pos in positions if pos.get('lot_size', 0) >= 0.02]
            
            for pos in high_margin_positions:
                profit = pos.get('profit', 0)
                margin_used = pos.get('lot_size', 0) * 2000
                
                if profit >= -5.0:  # ยอมขาดทุนเล็กน้อยเพื่อลด margin
                    opportunities.append({
                        'strategy': 'MARGIN_OPTIMIZATION',
                        'type': 'MARGIN_RELIEF',
                        'positions': [pos['ticket']],
                        'expected_profit': profit,
                        'confidence': 75,
                        'reasoning': f"Margin relief: free ${margin_used:.0f} margin",
                        'urgency': 5,
                        'impact_score': margin_used / 100,
                        'margin_relief': margin_used
                    })
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Margin optimization error: {e}")
            return []

    def _strategy_portfolio_rebalancing(self, positions, analysis) -> List[Dict]:
        """Strategy 4: Portfolio Rebalancing - ปรับสมดุล portfolio"""
        opportunities = []
        
        try:
            buy_count = len(analysis['buy_positions'])
            sell_count = len(analysis['sell_positions'])
            
            if abs(buy_count - sell_count) < 3:
                return []  # สมดุลอยู่แล้ว
            
            # หาไม้ที่ควรปิดเพื่อปรับสมดุล
            if buy_count > sell_count:
                target_positions = analysis['buy_positions']
                direction_label = "BUY"
            else:
                target_positions = analysis['sell_positions']
                direction_label = "SELL"
            
            for pos in target_positions[:3]:  # เอาแค่ 3 ตัวแรก
                profit = pos.get('profit', 0)
                
                if profit >= -2.0:  # ยอมขาดทุนเล็กน้อยเพื่อสมดุล
                    opportunities.append({
                        'strategy': 'PORTFOLIO_REBALANCING',
                        'type': 'BALANCE_ADJUSTMENT',
                        'positions': [pos['ticket']],
                        'expected_profit': profit,
                        'confidence': 65,
                        'reasoning': f"Rebalance {direction_label} excess",
                        'urgency': 3,
                        'impact_score': abs(buy_count - sell_count),
                        'margin_relief': pos.get('lot_size', 0) * 2000
                    })
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Portfolio rebalancing error: {e}")
            return []

    def _strategy_risk_reduction(self, positions, analysis) -> List[Dict]:
        """Strategy 5: Risk Reduction - ลดความเสี่ยง"""
        opportunities = []
        
        try:
            if analysis['emergency_level'] < 3:
                return []
            
            # หาไม้ที่มีความเสี่ยงสูง
            risky_positions = [pos for pos in positions if pos.get('profit', 0) < -10.0]
            
            for pos in risky_positions:
                loss = pos.get('profit', 0)
                
                opportunities.append({
                    'strategy': 'RISK_REDUCTION',
                    'type': 'CUT_LOSS',
                    'positions': [pos['ticket']],
                    'expected_profit': loss,
                    'confidence': 70,
                    'reasoning': f"Cut loss ${loss:.2f} to reduce risk",
                    'urgency': 7,
                    'impact_score': abs(loss) * 2,
                    'margin_relief': pos.get('lot_size', 0) * 2000
                })
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Risk reduction error: {e}")
            return []

    def _strategy_opportunity_harvesting(self, positions, analysis) -> List[Dict]:
        """Strategy 6: Opportunity Harvesting - เก็บเกี่ยวโอกาส"""
        opportunities = []
        
        try:
            # หาไม้ที่มีกำไรปานกลาง (1-3 ดอลลาร์)
            medium_profit_positions = [pos for pos in positions 
                                    if 1.0 <= pos.get('profit', 0) <= 3.0]
            
            for pos in medium_profit_positions:
                profit = pos.get('profit', 0)
                age = self._calculate_position_age(pos)
                
                if age > 20:  # อายุเกิน 20 นาที
                    opportunities.append({
                        'strategy': 'OPPORTUNITY_HARVESTING',
                        'type': 'MEDIUM_HARVEST',
                        'positions': [pos['ticket']],
                        'expected_profit': profit,
                        'confidence': 60,
                        'reasoning': f"Harvest ${profit:.2f} ({age}min old)",
                        'urgency': 2,
                        'impact_score': profit * 5,
                        'margin_relief': pos.get('lot_size', 0) * 2000
                    })
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Opportunity harvesting error: {e}")
            return []

    def _detect_and_manage_support_positions(self):
        """🔍 ตรวจจับและจัดการไม้ Support"""
        
        try:
            current_positions = list(self.active_positions.values())
            if not current_positions:
                return
            
            # วิเคราะห์ portfolio
            portfolio_analysis = self._analyze_portfolio_comprehensive(current_positions)
            
            # หาไม้ที่ควร Support
            support_opportunities = self._strategy_portfolio_support(current_positions, portfolio_analysis)
            
            for support_opp in support_opportunities:
                position_ticket = support_opp['positions'][0]
                
                # เพิ่มเข้าระบบ Support
                if position_ticket not in self.portfolio_support_positions:
                    self._add_to_support_system(position_ticket, support_opp)
                    print(f"🛡️ Added Position {position_ticket} to Support System")
            
            # ลบไม้ที่ไม่อยู่แล้ว
            self._cleanup_closed_support_positions()
            
        except Exception as e:
            print(f"❌ Support detection error: {e}")

    def _strategy_portfolio_support(self, positions, analysis) -> List[Dict]:
        """🛡️ Portfolio Support - ถือไม้กำไรค้ำพอร์ต"""
        support_decisions = []
        
        try:
            profitable = analysis['profitable_positions']
            losing = analysis['losing_positions']
            
            if not profitable or not losing:
                return []
            
            # 📊 Portfolio Health Assessment
            portfolio_health = self._assess_portfolio_support_health(analysis)
            
            for pos in profitable:
                profit = pos.get('profit', 0)
                
                # 🛡️ Support Decision Logic
                support_decision = self._calculate_support_decision(pos, portfolio_health, analysis)
                
                if support_decision['should_hold']:
                    support_decisions.append({
                        'strategy': 'PORTFOLIO_SUPPORT',
                        'type': 'HOLD_FOR_SUPPORT',
                        'positions': [pos['ticket']],
                        'expected_profit': profit,
                        'confidence': support_decision['confidence'],
                        'reasoning': support_decision['reasoning'],
                        'support_value': support_decision['support_value'],
                        'hold_duration': support_decision['recommended_hold_minutes'],
                        'urgency': -1,  # Negative urgency = HOLD
                        'impact_score': support_decision['support_value'] * 5,
                        'margin_relief': 0
                    })
            
            return support_decisions
            
        except Exception as e:
            print(f"❌ Portfolio support error: {e}")
            return []

    def _assess_portfolio_support_health(self, analysis) -> Dict:
        """📊 ประเมินความต้องการ support ของ portfolio"""
        try:
            net_pnl = analysis['net_pnl']
            profitable_count = len(analysis['profitable_positions'])
            losing_count = len(analysis['losing_positions'])
            total_positions = analysis['total_positions']
            
            # คำนวณ support need level
            support_need = 0
            
            if net_pnl < -20: support_need += 4
            elif net_pnl < -10: support_need += 3
            elif net_pnl < -5: support_need += 2
            elif net_pnl < 0: support_need += 1
            
            if losing_count > profitable_count * 2: support_need += 3
            elif losing_count > profitable_count: support_need += 2
            
            if total_positions > 15: support_need += 2
            elif total_positions > 10: support_need += 1
            
            balance_ratio = profitable_count / max(total_positions, 1)
            
            return {
                'support_need_level': min(support_need, 10),
                'balance_ratio': balance_ratio,
                'net_pnl': net_pnl,
                'should_support': support_need >= 3,
                'support_strength': 'HIGH' if support_need >= 7 else 'MEDIUM' if support_need >= 4 else 'LOW'
            }
            
        except Exception as e:
            return {'support_need_level': 0, 'should_support': False}

    def _calculate_support_decision(self, position, portfolio_health, analysis) -> Dict:
        """🎯 คำนวณการตัดสินใจ support สำหรับแต่ละไม้"""
        try:
            profit = position.get('profit', 0)
            age_minutes = self._calculate_position_age(position)
            lot_size = position.get('lot_size', 0)
            
            support_need = portfolio_health['support_need_level']
            
            should_hold = False
            reasoning = []
            confidence = 50
            support_value = 0
            recommended_hold = 30
            
            # Support Decision Logic
            if 2.0 <= profit <= 8.0 and support_need >= 4:
                should_hold = True
                reasoning.append(f"Strong support: ${profit:.2f} profit stabilizes portfolio")
                confidence = 85
                support_value = profit * 2
                recommended_hold = 60
            
            elif 1.0 <= profit <= 3.0 and support_need >= 6:
                should_hold = True
                reasoning.append(f"Strategic support: Hold ${profit:.2f} for portfolio stability")
                confidence = 75
                support_value = profit * 3
                recommended_hold = 45
            
            elif profit >= 1.5 and lot_size >= 0.02 and support_need >= 3:
                should_hold = True
                reasoning.append(f"Large position support: {lot_size} lots with ${profit:.2f}")
                confidence = 80
                support_value = profit * lot_size * 50
                recommended_hold = 90
            
            return {
                'should_hold': should_hold,
                'reasoning': " | ".join(reasoning) if reasoning else "No support needed",
                'confidence': confidence,
                'support_value': support_value,
                'recommended_hold_minutes': recommended_hold
            }
            
        except Exception as e:
            return {'should_hold': False, 'reasoning': 'Error in calculation', 'confidence': 0, 'support_value': 0, 'recommended_hold_minutes': 30}

    def _add_to_support_system(self, position_ticket, support_opportunity):
        """🛡️ เพิ่มไม้เข้าระบบ Support แบบ Hybrid (Pure + Trailing)"""
        
        try:
            position = self.active_positions.get(position_ticket)
            if not position:
                return
            
            current_profit = position.get('profit', 0)
            support_value = support_opportunity['support_value']
            lot_size = position.get('lot_size', 0)
            
            # 🎯 ตัดสินใจประเภท Support
            support_mode = self._determine_support_mode(current_profit, support_value, lot_size)
            
            # สร้าง Support Data
            support_data = {
                'added_time': datetime.now(),
                'original_profit': current_profit,
                'support_reasoning': support_opportunity['reasoning'],
                'support_value': support_value,
                'support_mode': support_mode,  # 🆕 เพิ่ม mode
                'status': 'ACTIVE'
            }
            
            # 🔀 สร้าง Trailing Data ตาม Mode
            if support_mode == "PURE_SUPPORT":
                # ไม้สำคัญ = ไม่ trailing เลย
                support_data['trailing_enabled'] = False
                print(f"🛡️ PURE SUPPORT: Position {position_ticket} - NO trailing")
                print(f"   💰 Critical Profit: ${current_profit:.2f}")
                print(f"   🔒 Protected permanently for portfolio support")
                
            elif support_mode == "SUPPORT_WITH_TRAILING":
                # ไม้ปกติ = Support + Trailing
                support_data['trailing_enabled'] = True
                
                # Dynamic trail distance
                trail_distance = self._calculate_dynamic_trail_distance(current_profit)
                
                trailing_data = {
                    'initial_profit': current_profit,
                    'current_trailing_stop': max(0, current_profit - trail_distance),
                    'highest_profit_seen': current_profit,
                    'trail_distance': trail_distance,
                    'trail_step': 1.0,
                    'last_update': datetime.now()
                }
                
                self.support_trailing_data[position_ticket] = trailing_data
                print(f"🔄 SUPPORT + TRAILING: Position {position_ticket}")
                print(f"   💰 Current Profit: ${current_profit:.2f}")
                print(f"   🎯 Trailing Stop: ${trailing_data['current_trailing_stop']:.2f}")
                print(f"   📏 Trail Distance: ${trail_distance}")
            
            # เก็บข้อมูล
            self.portfolio_support_positions[position_ticket] = support_data
            
        except Exception as e:
            print(f"❌ Add to support error: {e}")

    def _determine_support_mode(self, profit, support_value, lot_size) -> str:
        """🎯 ตัดสินใจว่าไม้นี้ควรเป็น Pure Support หรือ Support+Trailing"""
        
        try:
            # 🔥 เกณฑ์ไม้สำคัญ (PURE_SUPPORT)
            is_critical = False
            reasons = []
            
            # 1. กำไรสูงมาก
            if profit >= 8.0:
                is_critical = True
                reasons.append(f"High profit ${profit:.2f}")
            
            # 2. Support value สูง
            if support_value >= 15:
                is_critical = True
                reasons.append(f"High support value {support_value}")
            
            # 3. ไม้ใหญ่ + กำไรดี
            if lot_size >= 0.03 and profit >= 3.0:
                is_critical = True
                reasons.append(f"Large position {lot_size} lots")
            
            # 4. Portfolio แย่มาก + มีกำไร
            portfolio_analysis = self._get_current_portfolio_analysis()
            if portfolio_analysis and portfolio_analysis.get('net_pnl', 0) < -30 and profit >= 2.0:
                is_critical = True
                reasons.append("Critical portfolio support needed")
            
            if is_critical:
                print(f"   🔒 PURE SUPPORT criteria: {' | '.join(reasons)}")
                return "PURE_SUPPORT"
            else:
                print(f"   🔄 SUPPORT+TRAILING: Normal support position")
                return "SUPPORT_WITH_TRAILING"
                
        except Exception as e:
            print(f"❌ Support mode determination error: {e}")
            return "SUPPORT_WITH_TRAILING"  # Default

    def _calculate_dynamic_trail_distance(self, profit):
        """🎯 คำนวณ trail distance แบบ dynamic"""
        
        if profit >= 10.0:
            return 3.0      # กำไรสูง = trail ห่าง $3
        elif profit >= 5.0:
            return 2.5      # กำไรปานกลาง = trail ห่าง $2.5
        elif profit >= 3.0:
            return 2.0      # กำไรปกติ = trail ห่าง $2
        elif profit >= 1.0:
            return 1.5      # กำไรน้อย = trail ห่าง $1.5
        else:
            return 1.0      # กำไรเล็ก = trail ห่าง $1

    def _get_current_portfolio_analysis(self) -> Dict:
        """📊 ได้ portfolio analysis ปัจจุบัน"""
        try:
            positions = list(self.active_positions.values())
            if positions:
                return self._analyze_portfolio_comprehensive(positions)
            return {}
        except:
            return {}
    
    def _cleanup_closed_support_positions(self):
        """🧹 ลบไม้ที่ปิดแล้วออกจากระบบ Support"""
        try:
            closed_tickets = []
            
            for ticket in self.portfolio_support_positions.keys():
                if ticket not in self.active_positions:
                    closed_tickets.append(ticket)
            
            for ticket in closed_tickets:
                self._remove_from_support_system(ticket)
                print(f"🧹 Removed closed position {ticket} from Support System")
                
        except Exception as e:
            print(f"❌ Support cleanup error: {e}")

    def _remove_from_support_system(self, position_ticket):
        """🗑️ ลบไม้ออกจากระบบ Support"""
        try:
            if position_ticket in self.portfolio_support_positions:
                del self.portfolio_support_positions[position_ticket]
            if position_ticket in self.support_trailing_data:
                del self.support_trailing_data[position_ticket]
        except Exception as e:
            print(f"❌ Remove from support error: {e}")

    def _update_all_trailing_stops(self):
        """🔄 อัพเดต Trailing Stop เฉพาะไม้ที่ enable trailing"""
        
        try:
            if not self.support_trailing_data:
                return
            
            for position_ticket in list(self.support_trailing_data.keys()):
                # เช็คว่าไม้นี้ enable trailing หรือไม่
                support_data = self.portfolio_support_positions.get(position_ticket)
                if support_data and support_data.get('trailing_enabled', True):
                    self._update_single_trailing_stop(position_ticket)
                else:
                    print(f"🔒 PURE SUPPORT: Skipping trailing for {position_ticket}")
                
        except Exception as e:
            print(f"❌ Trailing update error: {e}")

    def _update_single_trailing_stop(self, position_ticket):
        """🔄 อัพเดต Trailing Stop ไม้เดียว"""
        
        try:
            # Get current position
            position = self.active_positions.get(position_ticket)
            if not position:
                self._remove_from_support_system(position_ticket)
                return
            
            trailing_data = self.support_trailing_data.get(position_ticket)
            if not trailing_data:
                return
            
            current_profit = position.get('profit', 0)
            current_trailing = trailing_data['current_trailing_stop']
            trail_distance = trailing_data['trail_distance']
            highest_seen = trailing_data['highest_profit_seen']
            
            # 📈 อัพเดต highest profit
            if current_profit > highest_seen:
                trailing_data['highest_profit_seen'] = current_profit
                
                # คำนวณ trailing stop ใหม่
                new_trailing = current_profit - trail_distance
                new_trailing = max(0, new_trailing)
                
                # ขยับขึ้นเท่านั้น
                if new_trailing > current_trailing:
                    trailing_data['current_trailing_stop'] = new_trailing
                    trailing_data['last_update'] = datetime.now()
                    
                    print(f"🔄 Trailing Updated: Position {position_ticket}")
                    print(f"   📈 Current Profit: ${current_profit:.2f}")
                    print(f"   🎯 New Trailing: ${new_trailing:.2f}")
            
        except Exception as e:
            print(f"❌ Single trailing update error: {e}")

    def _check_trailing_stop_hits(self):
        """🚨 เช็คว่าไม้ไหนโดน Trailing Stop"""
        
        try:
            if not self.support_trailing_data:
                return
                
            trailing_hits = []
            
            for position_ticket, trailing_data in self.support_trailing_data.items():
                position = self.active_positions.get(position_ticket)
                if not position:
                    continue
                    
                current_profit = position.get('profit', 0)
                trailing_stop = trailing_data['current_trailing_stop']
                
                # เช็คว่าโดน trailing stop หรือไม่
                if current_profit <= trailing_stop and trailing_stop > 0:
                   # print(f"🚨 TRAILING HIT: Position {position_ticket}")
                   # print(f"   💰 Current Profit: ${current_profit:.2f}")
                    # print(f"   🎯 Trailing Stop: ${trailing_stop:.2f}")
                    
                    # เพิ่มเข้า list ปิด
                    trailing_hits.append({
                        'strategy': 'TRAILING_SUPPORT_CLOSE',
                        'type': 'TRAILING_STOP_HIT',
                        'positions': [position_ticket],
                        'expected_profit': current_profit,
                        'confidence': 95,
                        'reasoning': f"Trailing stop hit: ${current_profit:.2f} <= ${trailing_stop:.2f}",
                        'urgency': 10,
                        'impact_score': current_profit * 20,
                        'margin_relief': position.get('lot_size', 0) * 2000
                    })
            
            # ปิดไม้ที่โดน trailing
            for hit in trailing_hits:
                try:
                    success = self.execute_profit_opportunity(hit)
                    if success:
                        position_ticket = hit['positions'][0]
                        self._remove_from_support_system(position_ticket)
                        print(f"✅ Trailing stop executed for position {position_ticket}")
                except Exception as e:
                    print(f"❌ Trailing execution error: {e}")
                    
        except Exception as e:
            print(f"❌ Trailing check error: {e}")

    def get_current_spread_points(self):
        """ดึง spread ปัจจุบันเป็น points"""
        try:
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if tick and tick.ask and tick.bid:
                symbol_info = mt5.symbol_info(self.gold_symbol)
                if symbol_info:
                    spread_points = int((tick.ask - tick.bid) / symbol_info.point)
                    return max(10, spread_points)  # อย่างน้อย 1 pip
            return 25  # fallback 2.5 pips
        except:
            return 25

    def calculate_safe_distance(self, base_distance, action_type="general"):
        """คำนวณระยะปลอดภัยรวม spread"""
        current_spread = self.get_current_spread_points()
        
        if action_type == "trailing":
            spread_buffer = current_spread + 20  # เผื่อ 2 pips
        elif action_type == "profit_target":
            spread_buffer = current_spread + 30  # เผื่อ 3 pips
        else:
            spread_buffer = current_spread + 10  # default
        
        return base_distance + spread_buffer

    def setup_position_trailing(self, ticket, entry_price, order_type, lot_size):
        """ตั้งค่า trailing สำหรับ position - รวมกับระบบเก่า"""
        
        # คำนวณ trail distance ตามขนาดไม้
        if lot_size >= 0.1:
            trail_distance = 3.0   # $3 trail
        elif lot_size >= 0.05:
            trail_distance = 2.5   # $2.5 trail
        else:
            trail_distance = 2.0   # $2 trail
        
        # เผื่อ spread
        spread_buffer = self.get_current_spread_points() * 0.01  # convert to dollars
        safe_trail_distance = trail_distance + spread_buffer
        
        # ใช้โครงสร้างเดิม + เพิ่มข้อมูลใหม่
        self.support_trailing_data[ticket] = {
            # ระบบเก่า (ต้องมี)
            'initial_profit': 0,
            'current_trailing_stop': 0,
            'highest_profit_seen': 0,
            'trail_distance': safe_trail_distance,
            'trail_step': 1.0,
            'last_update': datetime.now(),
            
            # ระบบใหม่ (เพิ่ม)
            'entry_price': entry_price,
            'order_type': order_type,
            'lot_size': lot_size,
            'profit_threshold': 2.0,  # เริ่ม trail เมื่อกำไร $2
            'best_price': entry_price,
            'trailing_active': False
        }
        if ticket not in self.portfolio_support_positions:
            self.portfolio_support_positions[ticket] = {}
    
        self.portfolio_support_positions[ticket]['trailing_protected'] = True
        print(f"🔒 Position #{ticket} PROTECTED from main profit system")
        print(f"🎯 Unified trailing setup #{ticket}: trail ${safe_trail_distance:.2f}")

    def update_position_trailing(self):
        return
        """อัพเดท trailing stops"""
        for ticket, trail_data in list(self.support_trailing_data.items()):
            try:
                positions = mt5.positions_get(ticket=ticket)
                if not positions:
                    del self.support_trailing_data[ticket]
                    continue
                    
                position = positions[0]
                current_price = position.price_current
                
                # 🔧 แก้ไข: ใช้ข้อมูลจาก position ถ้าไม่มีใน trail_data
                entry_price = trail_data.get('entry_price', position.price_open)
                order_type = trail_data.get('order_type', position.type)
                
                # ถ้าไม่มี safe_trailing_distance ให้คำนวณใหม่
                if 'safe_trailing_distance' not in trail_data:
                    lot_size = position.volume
                    if lot_size >= 0.1:
                        base_trailing = 100
                    elif lot_size >= 0.05:
                        base_trailing = 80
                    else:
                        base_trailing = 60
                    safe_distance = self.calculate_safe_distance(base_trailing, "trailing")
                    trail_data['safe_trailing_distance'] = safe_distance
                else:
                    safe_distance = trail_data['safe_trailing_distance']
                
                symbol_info = mt5.symbol_info(self.gold_symbol)
                if not symbol_info:
                    continue
                    
                # คำนวณกำไร
                if order_type == mt5.ORDER_TYPE_BUY or position.type == mt5.POSITION_TYPE_BUY:
                    profit_points = (current_price - entry_price) / symbol_info.point
                    if current_price > trail_data.get('best_price', entry_price):
                        trail_data['best_price'] = current_price
                else:  # SELL
                    profit_points = (entry_price - current_price) / symbol_info.point
                    if current_price < trail_data.get('best_price', entry_price):
                        trail_data['best_price'] = current_price
                
                # อัพเดทข้อมูลที่อาจหายไป
                trail_data['max_profit_seen'] = max(trail_data.get('max_profit_seen', 0), profit_points)
                trail_data['profit_threshold'] = trail_data.get('profit_threshold', 40)
                
                # เริ่ม trailing
                if profit_points >= trail_data['profit_threshold']:
                    trail_data['trailing_active'] = True
                    
                    if order_type == mt5.ORDER_TYPE_BUY or position.type == mt5.POSITION_TYPE_BUY:
                        new_sl = trail_data['best_price'] - (safe_distance * symbol_info.point)
                        if new_sl > position.sl or position.sl == 0:
                            self.modify_position_stop_loss(ticket, new_sl)
                    else:  # SELL
                        new_sl = trail_data['best_price'] + (safe_distance * symbol_info.point)
                        if new_sl < position.sl or position.sl == 0:
                            self.modify_position_stop_loss(ticket, new_sl)
                
            except Exception as e:
                print(f"❌ Trailing error #{ticket}: {e}")
                # ลบ trail_data ที่มีปัญหา
                if ticket in self.support_trailing_data:
                    del self.support_trailing_data[ticket]

    def detect_existing_positions(self):
        """ตรวจจับ position เก่าที่ยังไม่มี trailing data"""
        try:
            positions = mt5.positions_get(symbol=self.gold_symbol)
            if not positions:
                return
                
            for position in positions:
                if position.magic == self.magic_number:
                    ticket = position.ticket
                    
                    # ถ้ายังไม่มี trailing data ให้สร้างใหม่
                    if ticket not in self.support_trailing_data:
                        print(f"🔍 Detected existing position #{ticket} - setting up trailing")
                        self.setup_position_trailing(
                            ticket, 
                            position.price_open,
                            position.type,
                            position.volume
                        )
                        
        except Exception as e:
            print(f"❌ Detect existing positions error: {e}")

    def modify_position_stop_loss(self, ticket, new_sl):
        """แก้ไข Stop Loss ของ position"""
        try:
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return False
                
            position = positions[0]
            
            # ตรวจสอบว่า SL ใหม่ต่างจากเดิมมากพอหรือไม่
            if position.sl != 0:
                symbol_info = mt5.symbol_info(position.symbol)
                price_diff = abs(new_sl - position.sl) / symbol_info.point
                if price_diff < 10:  # ต่างน้อยกว่า 1 pip ไม่ต้องแก้
                    return True
            
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": ticket,
                "sl": round(new_sl, 5),
                "tp": position.tp,
                "magic": self.magic_number,
                "comment": "AI_Trail_SL"
            }
            
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ SL updated #{ticket}: {new_sl:.5f}")
                return True
            else:
                print(f"❌ SL update failed #{ticket}: {result.comment}")
                return False
                
        except Exception as e:
            print(f"❌ SL modify error #{ticket}: {e}")
            return False
        
    def is_position_trailing_protected(self, ticket):
        """เช็คว่าไม้นี้ถูกป้องกันด้วย trailing หรือไม่"""
        
        # ⭐ เพิ่มการเช็ค override flag ก่อน
        if getattr(self, 'ignore_trailing_protection', False):
            return False  # ข้าม trailing protection
        
        trail_data = self.support_trailing_data.get(ticket)
        if not trail_data:
            return False
        
        # ถ้า trailing active แล้ว = ป้องกัน
        trailing_active = trail_data.get('trailing_active', False)
        
        # หรือถ้ากำไรใกล้ threshold = เตรียมป้องกัน
        if not trailing_active:
            positions = mt5.positions_get(ticket=ticket)
            if positions:
                position = positions[0]
                entry_price = trail_data.get('entry_price', position.price_open)
                current_price = position.price_current
                
                if position.type == mt5.POSITION_TYPE_BUY:
                    profit_points = (current_price - entry_price) / mt5.symbol_info(self.gold_symbol).point
                else:
                    profit_points = (entry_price - current_price) / mt5.symbol_info(self.gold_symbol).point
                
                profit_threshold = trail_data.get('profit_threshold', 40)
                # ป้องกันถ้าใกล้ threshold แล้ว (80% ของ threshold)
                if profit_points >= profit_threshold * 0.8:
                    return True
        
        return trailing_active
    
    def check_portfolio_balance_ratio(self) -> Dict:
        """
        🧠 Smart Balance Logic - ฉลาดกว่าเดิม
        ไม่เข้มงวดเกินไป แต่ยังป้องกันได้
        """
        try:
            # นับ positions แยกตามทิศทาง
            buy_positions = len([p for p in self.active_positions.values() if p.get('direction') == 'BUY'])
            sell_positions = len([p for p in self.active_positions.values() if p.get('direction') == 'SELL'])
            
            total_positions = buy_positions + sell_positions
            
            # ⭐ Smart Logic 1: ถ้าไม้น้อย ไม่ต้องเข้มงวด
            if total_positions <= 20:
                return {
                    'status': 'BALANCED',
                    'total_buy': buy_positions,
                    'total_sell': sell_positions,
                    'ratio': 1.0,
                    'details': f'Small portfolio ({total_positions} positions) - Allow any close',
                    'action_required': False,
                    'severity': 'BALANCED'
                }
            
            # ⭐ Smart Logic 2: ถ้าขาดทุนรวมเยอะ ไม่ต้องเข้มงวด
            total_pnl = sum(p.get('profit', 0) for p in self.active_positions.values())
            if total_pnl < -150:  # ขาดทุนเกิน $150
                return {
                    'status': 'BALANCED',
                    'total_buy': buy_positions,
                    'total_sell': sell_positions,
                    'ratio': 1.0,
                    'details': f'High loss (${total_pnl:.2f}) - Emergency profit taking allowed',
                    'action_required': False,
                    'severity': 'EMERGENCY_LOSS'
                }
            
            # ⭐ Smart Logic 3: คำนวณ ratio แบบยืดหยุ่น
            if buy_positions == 0 and sell_positions == 0:
                ratio = 1.0
                imbalance_type = 'NO_POSITIONS'
            elif sell_positions == 0:
                ratio = float('inf')
                imbalance_type = 'BUY_ONLY'
            elif buy_positions == 0:
                ratio = float('inf')
                imbalance_type = 'SELL_ONLY'
            else:
                ratio = max(buy_positions, sell_positions) / min(buy_positions, sell_positions)
                imbalance_type = 'BUY_HEAVY' if buy_positions > sell_positions else 'SELL_HEAVY'
            
            # ⭐ Smart Logic 4: เกณฑ์ที่ยืดหยุ่นตามจำนวนไม้
            if total_positions > 50:
                # ไม้เยอะมาก → เข้มงวดน้อย
                severe_threshold = 4.0    # 80:20
                critical_threshold = 6.0  # 85:15
            elif total_positions > 30:
                # ไม้ปานกลาง → เข้มงวดปกติ
                severe_threshold = 3.0    # 75:25
                critical_threshold = 4.0  # 80:20
            else:
                # ไม้น้อย → เข้มงวดมาก
                severe_threshold = 2.5    # 71:29
                critical_threshold = 3.0  # 75:25
            
            # กำหนดระดับความรุนแรง
            if ratio == float('inf'):
                severity = 'CRITICAL'
                status = 'CRITICAL_IMBALANCE'
            elif ratio > critical_threshold:
                severity = 'CRITICAL'
                status = 'CRITICAL_IMBALANCE'
            elif ratio > severe_threshold:
                severity = 'SEVERE'
                status = 'SEVERE_IMBALANCE'
            elif ratio > 2.0:  # 67:33
                severity = 'MODERATE'
                status = 'MODERATE_IMBALANCE'
            elif ratio > 1.5:  # 60:40
                severity = 'MINOR'
                status = 'MINOR_IMBALANCE'
            else:
                severity = 'BALANCED'
                status = 'BALANCED'
            
            balance_info = {
                'status': status,
                'imbalance_type': imbalance_type,
                'severity': severity,
                'ratio': ratio if ratio != float('inf') else 999,
                'total_buy': buy_positions,
                'total_sell': sell_positions,
                'total_positions': total_positions,
                'total_pnl': total_pnl,
                'action_required': severity in ['CRITICAL'],  # ⭐ เฉพาะ CRITICAL เท่านั้น
                'recommended_action': self._get_smart_balance_recommendation(status, imbalance_type, buy_positions, sell_positions, total_pnl),
                'details': f"{imbalance_type}: BUY:{buy_positions} vs SELL:{sell_positions} (Ratio: {ratio:.1f}, P&L: ${total_pnl:.2f})"
            }
            
            # 📊 Log แบบฉลาด
            if severity == 'CRITICAL':
                print(f"🚨 CRITICAL Portfolio Imbalance: {balance_info['details']}")
            elif severity == 'SEVERE':
                print(f"⚠️ Severe imbalance (allowed): {balance_info['details']}")
            elif total_pnl < -100:
                print(f"💸 High loss portfolio: {balance_info['details']}")
            else:
                print(f"📊 Portfolio status: {balance_info['details']}")
            
            return balance_info
            
        except Exception as e:
            print(f"❌ Smart balance check error: {e}")
            return {
                'status': 'BALANCED',  # Default ให้ปิดได้
                'ratio': 1.0,
                'action_required': False,
                'details': f'Error - allow close: {e}'
            }

    def can_close_position_safely(self, position: Dict, close_reason: str = "PROFIT") -> Dict:
        """
        🧠 Smart Position Close Check - ฉลาดกว่าเดิม
        """
        try:
            ticket = position.get('ticket', 0)
            direction = position.get('direction', 'UNKNOWN')
            profit = position.get('profit', 0)
            
            # ⭐ Smart Check 1: ขาดทุนรวมเยอะ → ปิดได้ทุกไม้
            total_pnl = sum(p.get('profit', 0) for p in self.active_positions.values())
            if total_pnl < -150:
                return {
                    'can_close': True,
                    'reason': f'Emergency loss recovery: Total P&L ${total_pnl:.2f}',
                    'urgency': 'EMERGENCY_LOSS',
                    'alternative_action': None
                }
            
            # ⭐ Smart Check 2: กำไรสูง → ปิดได้
            if profit > 8.0:
                return {
                    'can_close': True,
                    'reason': f'High profit override: ${profit:.2f}',
                    'urgency': 'HIGH_PROFIT',
                    'alternative_action': None
                }
            
            # ⭐ Smart Check 3: ไม้เยอะมาก → ปิดได้
            total_positions = len(self.active_positions)
            if total_positions > 45:
                return {
                    'can_close': True,
                    'reason': f'Too many positions: {total_positions} > 45',
                    'urgency': 'POSITION_OVERLOAD',
                    'alternative_action': None
                }
            
            # เช็ค portfolio balance
            balance_info = self.check_portfolio_balance_ratio()
            
            # ⭐ Smart Check 4: เฉพาะ CRITICAL ถึงจะ block
            if balance_info['status'] != 'CRITICAL_IMBALANCE':
                return {
                    'can_close': True,
                    'reason': f'Portfolio not critical: {balance_info["status"]}',
                    'urgency': 'NORMAL',
                    'alternative_action': None
                }
            
            # ถึงจุดนี้ = CRITICAL_IMBALANCE
            majority_direction = 'BUY' if balance_info['total_buy'] > balance_info['total_sell'] else 'SELL'
            
            if direction == majority_direction:
                # ปิดฝั่งที่เยอะ = ดี
                return {
                    'can_close': True,
                    'reason': f'Reduces {majority_direction} dominance',
                    'urgency': 'BALANCE_IMPROVEMENT',
                    'alternative_action': None
                }
            else:
                # ปิดฝั่งที่น้อย = ต้องระวัง
                if profit > 15.0:  # กำไรสูงมาก
                    return {
                        'can_close': True,
                        'reason': f'Very high profit ${profit:.2f} overrides balance',
                        'urgency': 'VERY_HIGH_PROFIT',
                        'alternative_action': None
                    }
                else:
                    return {
                        'can_close': False,
                        'reason': f'Would worsen critical {majority_direction} dominance',
                        'urgency': 'BLOCKED',
                        'alternative_action': f'Wait for {majority_direction} profit pair or higher profit'
                    }
            
        except Exception as e:
            print(f"❌ Smart safety check error: {e}")
            return {
                'can_close': True,  # Error = ให้ปิดได้
                'reason': f'Error fallback: {e}',
                'urgency': 'ERROR_FALLBACK',
                'alternative_action': None
            }

    def _get_smart_balance_recommendation(self, status: str, imbalance_type: str, buy_count: int, sell_count: int, total_pnl: float) -> List[str]:
        """💡 Smart recommendations"""
        recommendations = []
        
        if status == 'CRITICAL_IMBALANCE':
            if imbalance_type == 'BUY_ONLY':
                recommendations.extend([
                    "🚨 CRITICAL: Only BUY positions - high risk if gold rises",
                    "💡 Solution: Take some BUY profits and create SELL positions"
                ])
            elif imbalance_type == 'SELL_ONLY':
                recommendations.extend([
                    "🚨 CRITICAL: Only SELL positions - high risk if gold falls", 
                    "💡 Solution: Take some SELL profits and create BUY positions"
                ])
            else:
                majority = 'BUY' if buy_count > sell_count else 'SELL'
                recommendations.append(f"🚨 CRITICAL: Too much {majority} bias - reduce {majority} positions")
        
        elif total_pnl < -100:
            recommendations.extend([
                f"💸 High loss (${total_pnl:.2f}) - Focus on profit taking",
                "💡 Consider emergency profit taking to reduce exposure"
            ])
        
        else:
            recommendations.append("✅ Portfolio manageable - normal profit taking allowed")
        
        return recommendations

    def find_balanced_profit_opportunities(self) -> List[Dict]:
        """
        🎯 ปรับปรุง: ลดความเข้มงวดของ Balance Protection
        """
        try:
            positions = list(self.active_positions.values())
            if len(positions) < 1:
                return []
            
            # เช็ค portfolio balance
            balance_info = self.check_portfolio_balance_ratio()
            print(f"🎯 PAIR WAITING SYSTEM: {balance_info['details']}")
            
            opportunities = []
            
            # แยก positions ตามทิศทางและกำไร
            buy_positions = [p for p in positions if p.get('direction') == 'BUY']
            sell_positions = [p for p in positions if p.get('direction') == 'SELL']
            
            profitable_buys = [p for p in buy_positions if p.get('profit', 0) > 2.0]
            profitable_sells = [p for p in sell_positions if p.get('profit', 0) > 2.0]
            
            total_positions = len(positions)
            
            print(f"📊 Profitable Analysis:")
            print(f"   💰 BUY profitable: {len(profitable_buys)}")
            print(f"   💰 SELL profitable: {len(profitable_sells)}")
            print(f"   ⚖️ Portfolio: BUY:{len(buy_positions)} vs SELL:{len(sell_positions)}")
            print(f"   📈 Total positions: {total_positions}")
            
            # 🚨 เพิ่ม Emergency Relief - ถ้าไม้เยอะเกิน 40 ตัว
            if total_positions > 40:
                print("🚨 EMERGENCY RELIEF: Too many positions (>40)")
                # ปิดไม้กำไรได้ ไม่ว่าจะเป็นฝั่งไหน
                all_profitable = profitable_buys + profitable_sells
                all_profitable.sort(key=lambda x: x.get('profit', 0), reverse=True)  # เรียงตามกำไร
                
                for pos in all_profitable[:5]:  # ปิด 5 ตัวแรกที่กำไรสูงสุด
                    profit = pos.get('profit', 0)
                    if profit > 1.5:  # เกณฑ์ต่ำ
                        opportunities.append({
                            'strategy': 'EMERGENCY_RELIEF',
                            'type': 'TOO_MANY_POSITIONS',
                            'positions': [pos['ticket']],
                            'expected_profit': profit,
                            'confidence': 85,
                            'reasoning': f'Emergency relief: {total_positions} positions, ${profit:.2f} profit',
                            'urgency': 1,
                            'pair_waiting_approved': True
                        })
                        
                        print(f"   🚨 Emergency Relief: #{pos['ticket']} ${profit:.2f}")
                
                if opportunities:
                    return opportunities  # ปิดฉุกเฉินก่อน
            
            # 🎯 Priority 1: Perfect Pairs (เหมือนเดิม)
            if len(profitable_buys) > 0 and len(profitable_sells) > 0:
                print("✅ PERFECT PAIRS AVAILABLE - Closing pairs")
                
                for buy_pos in profitable_buys[:2]:
                    for sell_pos in profitable_sells[:2]:
                        total_profit = buy_pos.get('profit', 0) + sell_pos.get('profit', 0)
                        
                        if total_profit > 3.0:
                            opportunities.append({
                                'strategy': 'PERFECT_PAIR',
                                'type': 'BALANCED_PAIR_CLOSE',
                                'positions': [buy_pos['ticket'], sell_pos['ticket']],
                                'expected_profit': total_profit,
                                'confidence': 95,
                                'reasoning': f'Perfect pair: BUY ${buy_pos.get("profit", 0):.2f} + SELL ${sell_pos.get("profit", 0):.2f}',
                                'urgency': 1,
                                'pair_waiting_approved': True
                            })
                
                if opportunities:
                    return opportunities
            
            # 🎯 Priority 2: ปรับเกณฑ์ Imbalance ให้หลวมขึ้น
            if balance_info['status'] in ['SEVERE_IMBALANCE', 'CRITICAL_IMBALANCE']:  # เอา MODERATE ออก
                majority_direction = 'BUY' if balance_info['total_buy'] > balance_info['total_sell'] else 'SELL'
                
                print(f"⚖️ SEVERE IMBALANCE DETECTED: {majority_direction} heavy")
                
                # ปิดได้แค่ฝั่งที่เยอะเกิน
                if majority_direction == 'BUY' and len(profitable_buys) > 0:
                    for buy_pos in profitable_buys[:3]:  # เพิ่มจาก 2 เป็น 3
                        profit = buy_pos.get('profit', 0)
                        if profit > 1.5:  # ลดเกณฑ์จาก 2.0 เป็น 1.5
                            opportunities.append({
                                'strategy': 'MAJORITY_RELIEF',
                                'type': 'IMBALANCE_REDUCTION',
                                'positions': [buy_pos['ticket']],
                                'expected_profit': profit,
                                'confidence': 80,
                                'reasoning': f'Reduce BUY imbalance: ${profit:.2f} profit',
                                'urgency': 3,
                                'pair_waiting_approved': True
                            })
                
                elif majority_direction == 'SELL' and len(profitable_sells) > 0:
                    for sell_pos in profitable_sells[:3]:  # เพิ่มจาก 2 เป็น 3
                        profit = sell_pos.get('profit', 0)
                        if profit > 1.5:  # ลดเกณฑ์จาก 2.0 เป็น 1.5
                            opportunities.append({
                                'strategy': 'MAJORITY_RELIEF',
                                'type': 'IMBALANCE_REDUCTION',
                                'positions': [sell_pos['ticket']],
                                'expected_profit': profit,
                                'confidence': 80,
                                'reasoning': f'Reduce SELL imbalance: ${profit:.2f} profit',
                                'urgency': 3,
                                'pair_waiting_approved': True
                            })
            
            # 🎯 Priority 3: ลดเกณฑ์ High Profit Override
            elif len(profitable_buys) > 0 or len(profitable_sells) > 0:
                print("🎯 CHECKING HIGH PROFIT OVERRIDE (>$5)")  # ลดจาก $10 เป็น $5
                
                all_profitable = profitable_buys + profitable_sells
                for pos in all_profitable:
                    profit = pos.get('profit', 0)
                    direction = pos.get('direction')
                    
                    if profit > 5.0:  # ลดจาก 10.0 เป็น 5.0
                        opportunities.append({
                            'strategy': 'HIGH_PROFIT_OVERRIDE',
                            'type': 'EMERGENCY_HIGH_PROFIT',
                            'positions': [pos['ticket']],
                            'expected_profit': profit,
                            'confidence': 90,
                            'reasoning': f'High profit override: ${profit:.2f} > $5 threshold',
                            'urgency': 2,
                            'pair_waiting_approved': True
                        })
                        
                        print(f"   💰 High Profit Override: {direction} #{pos['ticket']} ${profit:.2f}")
                    else:
                        print(f"   ⏳ {direction} #{pos['ticket']} ${profit:.2f} - waiting for pair")
            
            # 🎯 Priority 4: เพิ่ม Moderate Profit Release (ใหม่)
            else:
                print("🎯 MODERATE PROFIT RELEASE - ปิดกำไรปานกลาง")
                all_profitable = profitable_buys + profitable_sells
                all_profitable.sort(key=lambda x: x.get('profit', 0), reverse=True)
                
                for pos in all_profitable[:2]:  # ปิด 2 ตัวที่กำไรสูงสุด
                    profit = pos.get('profit', 0)
                    if profit > 2.5:  # เกณฑ์ปานกลาง
                        opportunities.append({
                            'strategy': 'MODERATE_PROFIT',
                            'type': 'MODERATE_PROFIT_TAKING',
                            'positions': [pos['ticket']],
                            'expected_profit': profit,
                            'confidence': 70,
                            'reasoning': f'Moderate profit release: ${profit:.2f}',
                            'urgency': 5,
                            'pair_waiting_approved': True
                        })
            
            print(f"\n🏆 BALANCED RESULTS: {len(opportunities)} opportunities")
            for opp in opportunities:
                print(f"   {opp['strategy']}: ${opp['expected_profit']:.2f} ({opp['reasoning']})")
            
            return opportunities
            
        except Exception as e:
            print(f"❌ Balanced profit opportunities error: {e}")
            return []
           
    def _find_emergency_balance_opportunities(self, balance_info: Dict) -> List[Dict]:
        """
        🚨 หา emergency opportunities เพื่อปรับสมดุล portfolio
        """
        try:
            emergency_ops = []
            
            # หาฝั่งที่เยอะเกิน
            if balance_info['total_buy'] > balance_info['total_sell']:
                majority_direction = 'BUY'
                target_positions = [p for p in self.active_positions.values() if p.get('direction') == 'BUY']
            else:
                majority_direction = 'SELL' 
                target_positions = [p for p in self.active_positions.values() if p.get('direction') == 'SELL']
            
            # หา positions ที่ขาดทุนน้อยที่สุด (เพื่อปิดเพื่อสมดุล)
            target_positions.sort(key=lambda x: x.get('profit', 0), reverse=True)  # เรียงจากกำไรมากสุด
            
            for pos in target_positions[:3]:  # เอาแค่ 3 ตัวแรก
                profit = pos.get('profit', 0)
                
                # ยอมขาดทุนเล็กน้อยเพื่อสมดุล
                if profit >= -5.0:  # ขาดทุนไม่เกิน $5
                    emergency_ops.append({
                        'strategy': 'EMERGENCY_BALANCE',
                        'type': 'BALANCE_CORRECTION',
                        'positions': [pos['ticket']],
                        'expected_profit': profit,
                        'confidence': 80,  # ความมั่นใจสูง เพราะเพื่อสมดุล
                        'reasoning': f"Emergency {majority_direction} reduction for portfolio balance",
                        'urgency': 8,  # ด่วนมาก
                        'impact_score': 50,  # ผลกระทบสูง
                        'balance_emergency': True
                    })
                    
                    print(f"🚨 Emergency balance opportunity: Close {majority_direction} #{pos['ticket']} "
                        f"(${profit:.2f}) for portfolio balance")
            
            return emergency_ops
            
        except Exception as e:
            print(f"❌ Emergency balance opportunities error: {e}")
            return []
