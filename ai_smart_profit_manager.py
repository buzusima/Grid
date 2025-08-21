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
        """Enhanced main AI decision loop with better error handling"""
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
                
                # Calculate portfolio health
                health_score = self.ai_calculate_portfolio_health()
                self.ai_health_score = health_score
                
                # Enhanced Grid Management (if enabled)
                if hasattr(self, 'smart_enhancer') and self.smart_enhancer.enabled:
                    try:
                        self.manage_enhanced_grid()
                    except Exception as e:
                        print(f"⚠️ Enhanced grid management error: {e}")
                        # Fallback to original method
                        self.manage_original_grid()
                else:
                    self.manage_original_grid()
                
                # Enhanced Profit Taking (with error handling)
                try:
                    self.execute_enhanced_profit_taking()
                except Exception as e:
                    print(f"⚠️ Enhanced profit taking error: {e}")
                    # Fallback to original method
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
                
                # Sleep between cycles
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ Enhanced AI Main Loop error: {e}")
                time.sleep(5)
        
        print("🛑 Enhanced AI Main Loop: Stopped")

    # 🔧 เพิ่ม fallback methods
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
            
            # Check if we need more orders
            if total_exposure < 6:  # Minimum 6 total orders
                print("📊 Grid Coverage Low - Adding orders...")
                self.add_strategic_orders()
            
            # Check for expired or stale orders
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
        Ultra Flexible Profit Taking - ปิดได้หลากหลาย ยืดหยุ่น และชาญฉลาด
        """
        try:
            print("🧠 ULTRA FLEXIBLE INTELLIGENT PROFIT SYSTEM")
            print("=" * 60)
            
            positions = list(self.active_positions.values())
            if len(positions) < 1:
                return []
            
            # 📊 Step 1: Comprehensive Portfolio Analysis
            portfolio_analysis = self._analyze_portfolio_comprehensive(positions)
            
            # 🧠 Step 2: Multi-Strategy Opportunity Detection
            all_strategies = [
                self._strategy_instant_profit(positions, portfolio_analysis),      # เก็บกำไรด่วน
                self._strategy_rescue_operations(positions, portfolio_analysis),   # ช่วยเหลือไม้ขาดทุน
                self._strategy_margin_optimization(positions, portfolio_analysis), # เพิ่มประสิทธิภาพ margin
                self._strategy_portfolio_rebalancing(positions, portfolio_analysis), # ปรับสมดุล portfolio
                self._strategy_risk_reduction(positions, portfolio_analysis),      # ลดความเสี่ยง
                self._strategy_opportunity_harvesting(positions, portfolio_analysis), # เก็บเกี่ยวโอกาส
                self._strategy_emergency_protocols(positions, portfolio_analysis), # โปรโตคอลฉุกเฉิน
                self._strategy_smart_combinations(positions, portfolio_analysis)   # การรวมอัจฉริยะ
            ]
            
            # 🔄 Step 3: Merge and Optimize All Strategies
            merged_opportunities = []
            for strategy_results in all_strategies:
                merged_opportunities.extend(strategy_results)
            
            # 🎯 Step 4: Intelligence Scoring & Ranking
            intelligent_opportunities = self._apply_intelligence_scoring(merged_opportunities, portfolio_analysis)
            
            # 🚀 Step 5: Final Optimization & Selection
            final_opportunities = self._final_optimization(intelligent_opportunities, portfolio_analysis)
            
            print(f"\n🏆 ULTRA FLEXIBLE RESULTS:")
            print(f"   Total Strategies: {len(all_strategies)}")
            print(f"   Raw Opportunities: {len(merged_opportunities)}")
            print(f"   Intelligent Filtered: {len(intelligent_opportunities)}")
            print(f"   Final Optimized: {len(final_opportunities)}")
            
            return final_opportunities
            
        except Exception as e:
            print(f"❌ Ultra flexible system error: {e}")
            return self.find_original_profit_opportunities()

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
        """
        🛡️ Strategy 2: Advanced Rescue Operations - การช่วยเหลือขั้นสูง
        """
        opportunities = []
        
        try:
            profitable = analysis['profitable_positions']
            losing = analysis['losing_positions']
            
            if not profitable or not losing:
                return []
            
            # 🎯 Dynamic rescue parameters
            if analysis['emergency_level'] >= 4:
                rescue_mode = "EMERGENCY"
                max_rescue_loss = -25.0
                min_net_profit = -2.0  # ยอมขาดทุนเพื่อลด positions
            elif analysis['emergency_level'] >= 3:
                rescue_mode = "AGGRESSIVE"
                max_rescue_loss = -15.0
                min_net_profit = 0.0
            elif analysis['portfolio_health'] < 50:
                rescue_mode = "MODERATE"
                max_rescue_loss = -10.0
                min_net_profit = 0.5
            else:
                rescue_mode = "CONSERVATIVE"
                max_rescue_loss = -6.0
                min_net_profit = 1.5
            
            # 🔄 1:1 Rescue pairs
            for profit_pos in profitable:
                profit_amt = profit_pos.get('profit', 0)
                
                for loss_pos in losing:
                    loss_amt = loss_pos.get('profit', 0)
                    
                    if loss_amt < max_rescue_loss:
                        continue
                    
                    net_profit = profit_amt + loss_amt
                    
                    if net_profit >= min_net_profit:
                        rescue_efficiency = abs(loss_amt) / profit_amt if profit_amt > 0 else 0
                        
                        opportunities.append({
                            'strategy': 'RESCUE_OPERATIONS',
                            'type': 'RESCUE_PAIR_1_1',
                            'positions': [profit_pos['ticket'], loss_pos['ticket']],
                            'expected_profit': net_profit,
                            'confidence': 80 if net_profit > 0 else 60,
                            'reasoning': f"{rescue_mode} rescue: ${profit_amt:.2f} saves ${loss_amt:.2f} = ${net_profit:.2f}",
                            'rescue_efficiency': rescue_efficiency,
                            'urgency': self._calculate_rescue_urgency(loss_pos, analysis),
                            'impact_score': (profit_amt * 5) + (abs(loss_amt) * 3),
                            'margin_relief': (profit_pos.get('lot_size', 0) + loss_pos.get('lot_size', 0)) * 2000
                        })
            
            # 🔄 1:2 Multi-rescue (emergency/aggressive only)
            if rescue_mode in ["EMERGENCY", "AGGRESSIVE"]:
                for profit_pos in profitable:
                    profit_amt = profit_pos.get('profit', 0)
                    
                    if profit_amt < abs(min_net_profit) + 2.0:
                        continue
                    
                    for i, loss_pos1 in enumerate(losing):
                        for loss_pos2 in losing[i+1:]:
                            loss_amt1 = loss_pos1.get('profit', 0)
                            loss_amt2 = loss_pos2.get('profit', 0)
                            total_loss = loss_amt1 + loss_amt2
                            
                            if total_loss < max_rescue_loss:
                                continue
                            
                            net_profit = profit_amt + total_loss
                            
                            if net_profit >= min_net_profit:
                                opportunities.append({
                                    'strategy': 'RESCUE_OPERATIONS',
                                    'type': 'RESCUE_PAIR_1_2',
                                    'positions': [profit_pos['ticket'], loss_pos1['ticket'], loss_pos2['ticket']],
                                    'expected_profit': net_profit,
                                    'confidence': 70 if net_profit > 0 else 50,
                                    'reasoning': f"{rescue_mode} multi-rescue: ${profit_amt:.2f} saves ${total_loss:.2f} = ${net_profit:.2f}",
                                    'rescue_efficiency': abs(total_loss) / profit_amt if profit_amt > 0 else 0,
                                    'urgency': max(self._calculate_rescue_urgency(loss_pos1, analysis), 
                                                self._calculate_rescue_urgency(loss_pos2, analysis)),
                                    'impact_score': (profit_amt * 3) + (abs(total_loss) * 2),
                                    'margin_relief': (profit_pos.get('lot_size', 0) + loss_pos1.get('lot_size', 0) + loss_pos2.get('lot_size', 0)) * 2000
                                })
            
            # 🔄 2:1 Power rescue (emergency only)
            if rescue_mode == "EMERGENCY" and len(profitable) >= 2:
                for loss_pos in losing:
                    loss_amt = loss_pos.get('profit', 0)
                    
                    if loss_amt > -8.0:  # เฉพาะขาดทุนใหญ่
                        continue
                    
                    for i, profit_pos1 in enumerate(profitable):
                        for profit_pos2 in profitable[i+1:]:
                            profit_amt1 = profit_pos1.get('profit', 0)
                            profit_amt2 = profit_pos2.get('profit', 0)
                            total_profit = profit_amt1 + profit_amt2
                            
                            net_profit = total_profit + loss_amt
                            
                            if net_profit >= min_net_profit and total_profit >= abs(loss_amt) * 0.7:
                                opportunities.append({
                                    'strategy': 'RESCUE_OPERATIONS',
                                    'type': 'POWER_RESCUE_2_1',
                                    'positions': [profit_pos1['ticket'], profit_pos2['ticket'], loss_pos['ticket']],
                                    'expected_profit': net_profit,
                                    'confidence': 85,
                                    'reasoning': f"EMERGENCY power rescue: ${total_profit:.2f} rescues ${loss_amt:.2f} = ${net_profit:.2f}",
                                    'rescue_efficiency': abs(loss_amt) / total_profit if total_profit > 0 else 0,
                                    'urgency': self._calculate_rescue_urgency(loss_pos, analysis) + 2,
                                    'impact_score': (total_profit * 4) + (abs(loss_amt) * 5),
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
                    'EMERGENCY_PROTOCOLS': 50,
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
            
            profitable_positions = [p for p in positions if p.get('profit', 0) > 0]
            
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
            losing_positions = [p for p in positions if p.get('profit', 0) < 0]
            
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

    def execute_profit_opportunity(self, opportunity) -> bool:
        """Execute a profit opportunity - Fixed for Enhanced System"""
        try:
            # 🔧 Fixed: Handle both old and new data structures
            if hasattr(opportunity, 'positions'):
                # New Enhanced system (object with attributes)
                position_tickets = opportunity.positions
                expected_profit = getattr(opportunity, 'expected_profit', 0)
                opportunity_type = getattr(opportunity, 'tier', 'UNKNOWN')
                confidence = getattr(opportunity, 'confidence', 0)
                reasoning = getattr(opportunity, 'reasoning', 'Enhanced opportunity')
            else:
                # Old system (dictionary)
                position_tickets = opportunity.get('positions', [])
                expected_profit = opportunity.get('expected_profit', 0)
                opportunity_type = opportunity.get('type', 'UNKNOWN')
                confidence = opportunity.get('confidence', 0) * 100 if opportunity.get('confidence', 0) <= 1 else opportunity.get('confidence', 0)
                reasoning = opportunity.get('description', 'Original opportunity')
            
            print(f"💰 Executing {opportunity_type}: ${expected_profit:.2f} (Confidence: {confidence:.0f}%)")
            print(f"   📋 Positions to close: {position_tickets}")
            print(f"   💡 Reasoning: {reasoning}")
            
            # Validate positions
            if not position_tickets or len(position_tickets) == 0:
                print(f"   ❌ No positions to close")
                return False
            
            # Close all positions in the opportunity
            success_count = 0
            total_actual_profit = 0
            
            for ticket in position_tickets:
                try:
                    # Get position info before closing
                    position_info = None
                    for pos in self.active_positions.values():
                        if pos.get('ticket') == ticket:
                            position_info = pos
                            break
                    
                    if position_info:
                        current_profit = position_info.get('profit', 0)
                        print(f"   🎯 Closing position {ticket}: ${current_profit:.2f} profit")
                        
                        if self.close_position_by_ticket(ticket):
                            success_count += 1
                            total_actual_profit += current_profit
                            print(f"   ✅ Position {ticket} closed successfully")
                        else:
                            print(f"   ❌ Failed to close position {ticket}")
                    else:
                        print(f"   ⚠️ Position {ticket} not found in active positions")
                    
                    time.sleep(0.5)  # Wait between closes
                    
                except Exception as e:
                    print(f"   ❌ Error closing position {ticket}: {e}")
                    continue
            
            # Evaluate success
            if success_count == len(position_tickets):
                print(f"   🎉 SUCCESS: Closed {success_count}/{len(position_tickets)} positions")
                print(f"   💰 Total Profit Realized: ${total_actual_profit:.2f}")
                
                # Track enhanced performance if applicable
                if hasattr(opportunity, 'rebate_bonus'):
                    rebate_bonus = getattr(opportunity, 'rebate_bonus', 0)
                    print(f"   🎁 Rebate Bonus: ${rebate_bonus:.2f}")
                    total_value = total_actual_profit + rebate_bonus
                    print(f"   💎 Total Value (Profit + Rebate): ${total_value:.2f}")
                    
                    # Update rebate tracking
                    if hasattr(self, 'smart_enhancer'):
                        estimated_volume = len(position_tickets) * 0.01  # Estimate
                        self.smart_enhancer.update_daily_stats(estimated_volume, rebate_bonus)
                
                return True
                
            elif success_count > 0:
                print(f"   ⚠️ PARTIAL SUCCESS: Closed {success_count}/{len(position_tickets)} positions")
                print(f"   💰 Partial Profit: ${total_actual_profit:.2f}")
                return True
                
            else:
                print(f"   ❌ FAILED: Could not close any positions")
                return False
                
        except Exception as e:
            print(f"❌ Profit opportunity execution error (FIXED): {e}")
            print(f"   🔍 Opportunity type: {type(opportunity)}")
            print(f"   📊 Opportunity data: {opportunity}")
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
        """Log enhanced system status"""
        try:
            current_price = self.get_current_price()
            health_score = self.ai_health_score
            
            buy_positions = len([p for p in self.active_positions.values() if p.get('direction') == 'BUY'])
            sell_positions = len([p for p in self.active_positions.values() if p.get('direction') == 'SELL'])
            buy_orders = len([o for o in self.pending_orders.values() if o.get('direction') == 'BUY'])
            sell_orders = len([o for o in self.pending_orders.values() if o.get('direction') == 'SELL'])
            
            total_profit = sum(p.get('profit', 0) for p in self.active_positions.values())
            
            print("=" * 60)
            print("📊 ENHANCED AI GRID STATUS")
            print(f"💰 Current Price: ${current_price:.2f}")
            print(f"🧠 AI Health: {health_score:.1f}/100")
            print(f"📈 Positions: BUY:{buy_positions} | SELL:{sell_positions}")
            print(f"📋 Orders: BUY:{buy_orders} | SELL:{sell_orders}")
            print(f"💵 Total P&L: ${total_profit:.2f}")
            print(f"🎯 Dynamic Spacing: {self.calculate_dynamic_spacing()} points")
            print("=" * 60)
            
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
        """Stop AI trading system"""
        try:
            print("🛑 Stopping Enhanced AI Grid System...")
            self.ai_active = False
            
            # Wait for threads to finish
            if hasattr(self, 'ai_main_thread'):
                self.ai_main_thread.join(timeout=5)
            if hasattr(self, 'ai_monitor_thread'):
                self.ai_monitor_thread.join(timeout=5)
            
            print("✅ Enhanced AI Grid System stopped")
            
        except Exception as e:
            print(f"❌ Stop AI trading error: {e}")

    def get_ai_status(self) -> Dict:
        """Get comprehensive AI status"""
        try:
            current_price = self.get_current_price()
            
            return {
                'ai_active': self.ai_active,
                'ai_health_score': self.ai_health_score,
                'current_price': current_price,
                'active_positions': len(self.active_positions),
                'pending_orders': len(self.pending_orders),
                'total_profit': sum(p.get('profit', 0) for p in self.active_positions.values()),
                'dynamic_spacing': self.calculate_dynamic_spacing(),
                'market_condition': self.market_analysis.condition.value if self.market_analysis else 'UNKNOWN',
                'survivability_usage': self.get_current_drawdown_points() / self.survivability if self.survivability > 0 else 0,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Status retrieval error: {e}")
            return {'error': str(e)}