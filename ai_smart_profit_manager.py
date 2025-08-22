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

        self.crisis_mode = False
        self.last_crisis_check = time.time()
        self.crisis_check_interval = 30 

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
        """Calculate dynamic spacing based on market conditions - แก้ให้แคบลง"""
        try:
            # Get account balance
            account_info = self.mt5_connector.get_account_info()
            balance = account_info.get('balance', 1000) if account_info else 1000
            
            # ⭐ แก้ spacing ให้แคบลงทั้งหมด
            if balance >= 50000:
                base_spacing = 60   # เดิม: 80 → ใหม่: 60
            elif balance >= 10000:
                base_spacing = 70   # เดิม: 90 → ใหม่: 70
            elif balance >= 5000:
                base_spacing = 80   # เดิม: 100 → ใหม่: 80
            elif balance >= 1000:
                base_spacing = 90   # เดิม: 110 → ใหม่: 90
            else:
                base_spacing = 100  # เดิม: 120 → ใหม่: 100
            
            # Get current drawdown
            drawdown_points = self.get_current_drawdown_points() if hasattr(self, 'get_current_drawdown_points') else 0
            drawdown_ratio = drawdown_points / self.survivability if self.survivability > 0 else 0
            
            # Adjust for market conditions
            if hasattr(self, 'market_analysis') and self.market_analysis:
                volatility_factor = 1.0 + (self.market_analysis.volatility_score - 50) / 200
                base_spacing = int(base_spacing * volatility_factor)
            
            # ⭐ ลด drawdown factor (ให้ spacing แคบขึ้น)
            if drawdown_ratio > 0.5:
                drawdown_factor = 1.2  # เดิม: 1.5 → ใหม่: 1.2
            elif drawdown_ratio > 0.3:
                drawdown_factor = 1.1  # เดิม: 1.3 → ใหม่: 1.1
            elif drawdown_ratio > 0.1:
                drawdown_factor = 1.05 # เดิม: 1.1 → ใหม่: 1.05
            else:
                drawdown_factor = 1.0
            
            final_spacing = int(base_spacing * drawdown_factor)
            
            # Apply limits (ลดลง)
            final_spacing = max(50,     # เดิม: min_spacing → ใหม่: 50
                            min(final_spacing, 150))  # เดิม: max_spacing → ใหม่: 150
            
            print(f"   ✅ Dynamic spacing: {final_spacing} points (balance: ${balance:,.0f})")
            
            return final_spacing
            
        except Exception as e:
            print(f"❌ Dynamic spacing calculation error: {e}")
            return 100  # เดิม: normal_spacing → ใหม่: 100
    
    def level_exists_enhanced(self, target_price: float, direction: str, tolerance: float = 3.0) -> bool:
        """🔍 แก้ไข Level check - ไม่ loop ไม่ spam"""
        try:
            # เก็บ cache เพื่อไม่ให้เช็คซ้ำ
            cache_key = f"{target_price:.1f}_{direction}"
            current_time = time.time()
            
            if hasattr(self, '_level_check_cache'):
                if cache_key in self._level_check_cache:
                    cache_time, cache_result = self._level_check_cache[cache_key]
                    if current_time - cache_time < 5:  # cache 5 วินาที
                        return cache_result
            else:
                self._level_check_cache = {}
            
            # เช็คแค่ pending orders (ไม่เช็ค positions)
            exists = False
            if hasattr(self, 'pending_orders'):
                for order_info in self.pending_orders.values():
                    order_price = order_info.get('price', 0)
                    order_direction = order_info.get('direction', '')
                    
                    if (direction == order_direction and 
                        abs(target_price - order_price) <= tolerance):
                        exists = True
                        break
            
            # เก็บ cache
            self._level_check_cache[cache_key] = (current_time, exists)
            
            # ทำความสะอาด cache เก่า
            if len(self._level_check_cache) > 20:
                old_keys = [k for k, (t, _) in self._level_check_cache.items() 
                        if current_time - t > 30]
                for k in old_keys:
                    del self._level_check_cache[k]
            
            return exists
            
        except Exception as e:
            # ไม่ print error เพื่อไม่ spam
            return False
        
    def place_enhanced_order(self, price: float, direction: str, source: str, custom_lot: float = None) -> bool:
        """🎯 แก้ไข Enhanced order - ลด log spam"""
        try:
            # Crisis mode check (แค่บรรทัดเดียว)
            #if getattr(self, 'crisis_mode', False) and source not in ['EMERGENCY_HEDGE', 'SCALPING_RECOVERY']:
            #    return False
            
            # ทำความสะอาด lot size
            if custom_lot is not None:
                base_lot = float(custom_lot)
            else:
                base_lot = float(getattr(self, 'base_lot', 0.01))
            
            # Validate
            if base_lot <= 0 or base_lot > 1.0:
                base_lot = 0.01
            
            enhanced_lot = round(base_lot, 3)
            
            # เช็ค level (แค่สำหรับ INITIAL_GRID)
            if source == 'INITIAL_GRID':
                if self.level_exists_enhanced(price, direction, 5.0):
                    return False
            
            # ปรับราคาถ้าใกล้เกินไป
            current_price = self.get_current_price()
            if current_price and source not in ['EMERGENCY_HEDGE']:
                price_diff = abs(price - current_price)
                if price_diff < 3.0:
                    if direction == 'BUY':
                        price = current_price - 3.0
                    else:
                        price = current_price + 3.0
            
            # สร้าง order request
            if source == 'EMERGENCY_HEDGE':
                order_type = mt5.ORDER_TYPE_BUY if direction == 'BUY' else mt5.ORDER_TYPE_SELL
                action = mt5.TRADE_ACTION_DEAL
            else:
                order_type = mt5.ORDER_TYPE_BUY_LIMIT if direction == 'BUY' else mt5.ORDER_TYPE_SELL_LIMIT
                action = mt5.TRADE_ACTION_PENDING
            
            order_request = {
                "action": action,
                "symbol": self.gold_symbol,
                "volume": enhanced_lot,
                "type": order_type,
                "price": round(price, 2),
                "magic": getattr(self, 'magic_number', 123456),
                "comment": source[:15]
            }
            
            if source == 'EMERGENCY_HEDGE':
                order_request["deviation"] = 50
            
            # ส่ง order
            result = mt5.order_send(order_request)
            
            if result is None:
                return False
            
            if result.retcode == 10009:  # Success
                # อัพเดต tracking (ไม่ print)
                if source != 'EMERGENCY_HEDGE' and hasattr(self, 'pending_orders'):
                    self.pending_orders[result.order] = {
                        'price': price,
                        'direction': direction,
                        'volume': enhanced_lot,
                        'source': source,
                        'timestamp': datetime.now()
                    }
                return True
            else:
                # ไม่ print error detail
                return False
                
        except Exception as e:
            # ไม่ print error
            return False
    
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
        """🧠 Enhanced main AI loop - แก้ไข method calls"""
        print("🧠 AI ENHANCED MAIN LOOP: Starting with AI Pro crisis management...")
        
        while self.ai_active:
            try:
                # 🚨 Step 1: Crisis Detection & Management (แก้ไขให้ไม่บล็อค)
                if hasattr(self, 'check_and_handle_crisis'):
                    try:
                        self.check_and_handle_crisis()
                    except Exception as e:
                        print(f"⚠️ Crisis check error: {e}")
                
                # 📊 Step 2: Update Positions from MT5
                try:
                    self.ai_update_positions_from_mt5()
                    self.update_position_trailing()
                    self.detect_existing_positions()
                except Exception as e:
                    print(f"⚠️ Position update error: {e}")
                
                # 🧠 Step 3: Calculate AI Health Score
                try:
                    health_score = self.ai_calculate_portfolio_health()
                    self.ai_health_score = health_score
                    
                    if health_score < 30:
                        print(f"⚠️ Low AI Health Score: {health_score:.1f}/100")
                    else:
                        print(f"💪 AI Health Score: {health_score:.1f}/100")
                        
                except Exception as e:
                    print(f"⚠️ Health calculation error: {e}")
                    self.ai_health_score = 50  # Default fallback
                
                # ⭐ Step 4: Enhanced Profit Taking Analysis - แก้ไข method calls
                try:
                    print("💰 Enhanced Profit Taking Analysis...")
                    
                    # ใช้ method ที่มีอยู่แล้วแทน find_enhanced_profit_opportunities
                    ai_pro_opportunities = []
                    
                    # Method 1: ใช้ find_balanced_profit_opportunities
                    if hasattr(self, 'find_balanced_profit_opportunities'):
                        try:
                            balanced_opportunities = self.find_balanced_profit_opportunities()
                            if balanced_opportunities:
                                ai_pro_opportunities.extend(balanced_opportunities)
                                print(f"🎯 Found {len(balanced_opportunities)} balanced opportunities")
                        except Exception as e:
                            print(f"⚠️ Balanced opportunities error: {e}")
                    
                    # Method 2: ใช้ smart_enhancer.enhance_profit_taking
                    if hasattr(self, 'smart_enhancer') and self.smart_enhancer.enabled:
                        try:
                            # ใช้ find_enhanced_profit_opportunities ที่มีอยู่ใน class
                            if hasattr(self, 'find_enhanced_profit_opportunities'):
                                enhanced_opportunities = self.find_enhanced_profit_opportunities()
                                if enhanced_opportunities:
                                    ai_pro_opportunities.extend(enhanced_opportunities)
                                    print(f"🚀 Found {len(enhanced_opportunities)} enhanced opportunities")
                            
                            # หรือใช้ enhance_profit_taking
                            elif hasattr(self.smart_enhancer, 'enhance_profit_taking'):
                                # สร้าง profit opportunities พื้นฐานก่อน
                                basic_opportunities = self.find_original_profit_opportunities() if hasattr(self, 'find_original_profit_opportunities') else []
                                if basic_opportunities:
                                    enhanced = self.smart_enhancer.enhance_profit_taking(basic_opportunities)
                                    # แปลง enhanced opportunities เป็น format ที่ใช้ได้
                                    for enh in enhanced:
                                        ai_pro_opportunities.append({
                                            'type': 'ENHANCED_PROFIT',
                                            'positions': enh.positions,
                                            'expected_profit': enh.expected_profit,
                                            'confidence': enh.confidence,
                                            'tier': enh.tier,
                                            'reasoning': enh.reasoning,
                                            'strategy': 'AI_ENHANCED'
                                        })
                                    print(f"🧠 Enhanced {len(enhanced)} basic opportunities")
                        except Exception as e:
                            print(f"⚠️ Smart enhancer error: {e}")
                    
                    # Method 3: Fallback - ใช้ original opportunities
                    if not ai_pro_opportunities and hasattr(self, 'find_original_profit_opportunities'):
                        try:
                            original_opportunities = self.find_original_profit_opportunities()
                            if original_opportunities:
                                ai_pro_opportunities.extend(original_opportunities)
                                print(f"📋 Using {len(original_opportunities)} original opportunities")
                        except Exception as e:
                            print(f"⚠️ Original opportunities error: {e}")
                    
                    # Execute opportunities
                    if ai_pro_opportunities:
                        print(f"🎯 Processing {len(ai_pro_opportunities)} total opportunities")
                        executed_count = 0
                        
                        for opportunity in ai_pro_opportunities[:3]:  # Process top 3
                            try:
                                # Debug info
                                strategy = opportunity.get('strategy', opportunity.get('type', 'UNKNOWN'))
                                expected_profit = opportunity.get('expected_profit', 0)
                                print(f"   💡 Executing: {strategy} (${expected_profit:.1f})")
                                
                                success = self.execute_profit_opportunity(opportunity)
                                if success:
                                    executed_count += 1
                                    print(f"   ✅ Opportunity executed successfully")
                                else:
                                    print(f"   ❌ Opportunity execution failed")
                                    
                            except Exception as e:
                                print(f"   ❌ Individual opportunity error: {e}")
                                continue
                        
                        if executed_count > 0:
                            print(f"🎉 Successfully executed {executed_count} opportunities")
                        else:
                            print(f"⚠️ No opportunities executed successfully")
                    else:
                        print(f"📊 No profit opportunities found at this time")
                            
                except Exception as e:
                    print(f"❌ Enhanced profit taking error: {e}")
                    # Fallback to original method
                    try:
                        if hasattr(self, 'execute_original_profit_taking'):
                            self.execute_original_profit_taking()
                    except Exception as e2:
                        print(f"❌ Original profit taking fallback error: {e2}")
                
                # ⭐ Step 5: Enhanced Grid Management - ลบ crisis_mode check
                try:
                    print("🕸️ Enhanced Grid Management...")
                    if hasattr(self, 'smart_enhancer') and self.smart_enhancer.enabled:
                        self.manage_enhanced_grid()
                    else:
                        self.manage_original_grid()
                except Exception as e:
                    print(f"⚠️ Enhanced grid management error: {e}")
                    # Fallback to original
                    try:
                        if hasattr(self, 'manage_original_grid'):
                            self.manage_original_grid()
                    except Exception as e2:
                        print(f"❌ Original grid fallback error: {e2}")
                
                # ⭐ Step 6: Recovery Plan Execution (ปรับให้ไม่บล็อค grid)
                if hasattr(self, 'smart_enhancer'):
                    try:
                        current_price = self.get_current_price()
                        if current_price:
                            positions = list(self.active_positions.values())
                            account_info = self.mt5_connector.get_account_info() if self.mt5_connector else {}
                            
                            if positions and account_info:
                                crisis_analysis = self.smart_enhancer.check_crisis_situations(positions, account_info)
                                
                                # เฉพาะ EMERGENCY เท่านั้นถึงจะทำ recovery
                                if crisis_analysis.level.value == 'EMERGENCY':
                                    # เช็ค margin ก่อน
                                    margin_level = account_info.get('margin_level', 1000)
                                    if margin_level < 200:  # เฉพาะ margin ต่ำมากๆ
                                        recovery_plan = self.smart_enhancer.generate_recovery_plan(crisis_analysis, current_price)
                                        if recovery_plan:
                                            print(f"🔄 Executing recovery plan for TRUE EMERGENCY (margin: {margin_level:.0f}%)")
                                            self.execute_recovery_plan(recovery_plan)
                                    else:
                                        print(f"⚠️ Emergency detected but margin sufficient ({margin_level:.0f}%) - continuing normal operations")
                                else:
                                    print(f"📊 Crisis level: {crisis_analysis.level.value} - no recovery needed")
                                    
                    except Exception as e:
                        print(f"⚠️ Recovery plan error: {e}")
                
                # 📊 Step 7: Status Reporting
                try:
                    total_positions = len(getattr(self, 'active_positions', {}))
                    total_pending = len(getattr(self, 'pending_orders', {}))
                    
                    if total_positions > 0 or total_pending > 0:
                        print(f"📊 Portfolio: {total_positions} positions, {total_pending} pending orders")
                        
                        # แสดงสถานะการทำงาน
                        account_info = self.mt5_connector.get_account_info() if self.mt5_connector else {}
                        margin_level = account_info.get('margin_level', 1000) if account_info else 1000
                        
                        if margin_level > 2000:
                            print(f"✅ Status: OPTIMAL OPERATIONS (Margin: {margin_level:.0f}%)")
                        elif margin_level > 1000:
                            print(f"✅ Status: NORMAL OPERATIONS (Margin: {margin_level:.0f}%)")
                        elif margin_level > 500:
                            print(f"⚠️ Status: MONITORED OPERATIONS (Margin: {margin_level:.0f}%)")
                        else:
                            print(f"🚨 Status: CAUTIOUS OPERATIONS (Margin: {margin_level:.0f}%)")
                            
                except Exception as e:
                    print(f"⚠️ Status reporting error: {e}")
                
                # 😴 Sleep interval
                sleep_time = 2
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"❌ Enhanced AI Main Loop critical error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)
        
        print("🛑 Enhanced AI Main Loop: Stopped")

    def execute_recovery_plan(self, recovery_plan: Dict) -> bool:
        """🔄 Execute recovery plan - ลบ crisis mode blocks ให้เทรดได้ตลอด"""
        try:
            if not recovery_plan:
                print("❌ No recovery plan provided")
                return False
            
            crisis_level = recovery_plan.get('crisis_level', 'NORMAL')
            immediate_actions = recovery_plan.get('immediate_actions', [])
            
            print(f"\n🔄 EXECUTING RECOVERY PLAN: {crisis_level}")
            print("=" * 50)
            
            recovery_success = False
            
            # ⭐ เช็คสถานะปัจจุบันก่อนทำอะไร
            print(f"\n📊 Current Portfolio Status Check...")
            total_positions = len(getattr(self, 'active_positions', {}))
            total_orders = len(getattr(self, 'pending_orders', {}))
            total_exposure = total_positions + total_orders
            
            print(f"   📈 Active Positions: {total_positions}")
            print(f"   📋 Pending Orders: {total_orders}")
            print(f"   📊 Total Exposure: {total_exposure}")
            
            # ⭐ เช็ค margin level เพื่อตัดสินใจ
            account_info = getattr(self, 'mt5_connector', None)
            margin_level = 1000  # default
            
            if account_info and hasattr(account_info, 'get_account_info'):
                acc_data = account_info.get_account_info()
                if acc_data:
                    margin_level = acc_data.get('margin_level', 1000)
                    print(f"   💹 Current Margin Level: {margin_level:.1f}%")
            
            # Step 1: Execute Immediate Actions - แก้ไขการตั้ง crisis_mode
            if immediate_actions:
                print(f"\n⚡ Executing {len(immediate_actions)} immediate actions...")
                
                for action in immediate_actions:
                    try:
                        print(f"   ⚡ Action: {action}")
                        
                        if action == "STOP_ALL_NEW_ORDERS":
                            # ⭐ เช็ค margin ก่อนตั้ง crisis_mode
                            if margin_level < 300:  # เฉพาะ margin < 300% เท่านั้น
                                self.crisis_mode = True
                                print(f"   ✅ Crisis mode activated - low margin: {margin_level:.0f}%")
                            else:
                                print(f"   🎯 Crisis mode SKIPPED - margin sufficient: {margin_level:.0f}%")
                                
                        elif action == "ACTIVATE_EMERGENCY_HEDGE":
                            hedge_recs = recovery_plan.get('hedge_recommendations', [])
                            for hedge_rec in hedge_recs:
                                if hedge_rec.get('action') == 'EMERGENCY_HEDGE':
                                    hedge_size = hedge_rec.get('size', 0.1)
                                    if hasattr(self, 'execute_emergency_hedge'):
                                        success = self.execute_emergency_hedge(hedge_size)
                                        if success:
                                            print(f"   ✅ Emergency hedge executed: {hedge_size} lot")
                                            recovery_success = True
                                        else:
                                            print(f"   ❌ Emergency hedge failed")
                                            
                        elif action == "CLOSE_PRIORITY_POSITIONS":
                            priority_positions = recovery_plan.get('priority_positions', [])
                            if priority_positions and hasattr(self, 'close_priority_positions'):
                                closed_count = self.close_priority_positions(priority_positions[:3])
                                if closed_count > 0:
                                    print(f"   ✅ Closed {closed_count} priority positions")
                                    recovery_success = True
                                else:
                                    print(f"   ⚠️ No positions were closed")
                                    
                        elif action == "LIMIT_NEW_ORDERS":
                            # ⭐ ไม่ตั้ง crisis_mode แค่ log
                            if margin_level < 200:  # เฉพาะ margin ต่ำมาก
                                self.crisis_mode = True
                                print(f"   ✅ Order limitations activated - very low margin: {margin_level:.0f}%")
                            else:
                                print(f"   📝 Order limitations noted but NOT enforced - margin OK: {margin_level:.0f}%")
                                
                        elif action == "MONITOR_MARGIN_CLOSELY":
                            print(f"   ✅ Enhanced margin monitoring activated")
                            self.enhanced_margin_monitoring = True
                            
                        elif action == "ACTIVATE_PROTECTION_HEDGE":
                            print(f"   ✅ Protection hedge mode activated")
                            
                        elif action == "NORMAL_OPERATIONS_WITH_MONITORING":
                            print(f"   ✅ Normal operations with monitoring")
                            # ⭐ Force disable crisis mode
                            if hasattr(self, 'crisis_mode'):
                                self.crisis_mode = False
                            
                        elif action == "CONTINUE_NORMAL_OPERATIONS":
                            print(f"   ✅ Continue normal operations")
                            # ⭐ Force disable crisis mode
                            if hasattr(self, 'crisis_mode'):
                                self.crisis_mode = False
                            
                    except Exception as e:
                        print(f"   ❌ Action execution error: {e}")
                        continue
            
            # ⭐ Step 2: Smart Scalping Recovery (แก้ให้ liberal มาก)
            print(f"\n⚡ Evaluating Scalping Recovery Eligibility...")
            
            scalping_plan = recovery_plan.get('scalping_plan', [])
            if scalping_plan and len(scalping_plan) > 0:
                
                # 🛑 แก้ไข restrictions ให้ liberal มาก
                skip_scalping = False
                skip_reasons = []
                
                # ⭐ Dynamic limits ตาม margin level (liberal มาก)
                if margin_level > 10000:    # เกิน 10,000%
                    max_exposure = 50       # มากมาย
                    max_positions = 30
                    max_scalping = 10
                elif margin_level > 5000:   # เกิน 5,000%
                    max_exposure = 40
                    max_positions = 25
                    max_scalping = 8
                elif margin_level > 2000:   # เกิน 2,000%
                    max_exposure = 30
                    max_positions = 20
                    max_scalping = 6
                elif margin_level > 1000:   # เกิน 1,000%
                    max_exposure = 20
                    max_positions = 15
                    max_scalping = 4
                elif margin_level > 500:    # เกิน 500%
                    max_exposure = 15
                    max_positions = 10
                    max_scalping = 3
                else:                       # ต่ำกว่า 500%
                    max_exposure = 10
                    max_positions = 8
                    max_scalping = 2
                
                print(f"   🎯 Dynamic Limits: Max exposure: {max_exposure}, Max positions: {max_positions}, Max scalping: {max_scalping}")
                
                # Restriction 1: Total exposure (liberal มาก)
                if total_exposure >= max_exposure:
                    skip_scalping = True
                    skip_reasons.append(f"Too many total exposure: {total_exposure}/{max_exposure}")
                    
                # Restriction 2: Too many positions (liberal มาก)
                if total_positions >= max_positions:
                    skip_scalping = True
                    skip_reasons.append(f"Too many positions: {total_positions}/{max_positions}")
                    
                # Restriction 3: Crisis level (อนุญาตเกือบทุกระดับ)
                blocked_crisis_levels = []
                if margin_level > 5000:  # margin สูงมาก = อนุญาตทุก level
                    blocked_crisis_levels = []  # ไม่บล็อคเลย
                elif margin_level > 2000:  # margin สูง = อนุญาตเกือบทุก level
                    blocked_crisis_levels = []  # ไม่บล็อคเลย
                elif margin_level > 1000:  # margin ปานกลาง = บล็อคแค่ emergency
                    blocked_crisis_levels = ['EMERGENCY']
                else:  # margin ต่ำ = บล็อค emergency และ critical
                    blocked_crisis_levels = ['EMERGENCY', 'CRITICAL']
                
                if crisis_level in blocked_crisis_levels:
                    skip_scalping = True
                    skip_reasons.append(f"Crisis level blocked: {crisis_level} (margin: {margin_level:.0f}%)")
                
                # Restriction 4: Margin level check (liberal มาก)
                if margin_level < 100:  # เฉพาะ margin ต่ำมากๆ เท่านั้น
                    skip_scalping = True
                    skip_reasons.append(f"Margin level too low: {margin_level}%")
                
                # Restriction 5: Time-based cooldown (ลดมาก)
                if not hasattr(self, '_last_recovery_time'):
                    self._last_recovery_time = 0
                
                current_time = time.time()
                if margin_level > 5000:
                    cooldown_time = 60      # 1 นาที
                elif margin_level > 2000:
                    cooldown_time = 120     # 2 นาที
                else:
                    cooldown_time = 180     # 3 นาที
                
                if current_time - self._last_recovery_time < cooldown_time:
                    time_remaining = cooldown_time - (current_time - self._last_recovery_time)
                    skip_scalping = True
                    skip_reasons.append(f"Recovery cooldown: {time_remaining:.0f}s remaining")
                
                # Execute or skip scalping
                if skip_scalping:
                    print(f"\n🚫 SCALPING RECOVERY DISABLED")
                    print(f"   📋 Planned orders: {len(scalping_plan)} scalping orders")
                    print(f"   🛑 Blocking reasons:")
                    for reason in skip_reasons:
                        print(f"      • {reason}")
                    print(f"   ✅ Scalping recovery safely skipped")
                    
                else:
                    print(f"\n⚡ Executing LIBERAL scalping recovery...")
                    print(f"   ⚠️ Original plan: {len(scalping_plan)} orders")
                    
                    scalping_success = 0
                    scalping_limit = min(len(scalping_plan), max_scalping)
                    
                    print(f"   🎯 Executing: {scalping_limit} orders (liberal limit)")
                    
                    for i, scalp_order in enumerate(scalping_plan[:scalping_limit]):
                        try:
                            print(f"   ⚡ Scalping {i+1}/{scalping_limit}: {scalp_order.get('type', 'UNKNOWN')}")
                            
                            if hasattr(self, 'execute_scalping_order'):
                                success = self.execute_scalping_order(scalp_order)
                                if success:
                                    scalping_success += 1
                                    print(f"   ✅ Scalping order {i+1} placed successfully")
                                else:
                                    print(f"   ❌ Scalping order {i+1} blocked/failed")
                            
                            sleep_time = 0.5 if margin_level > 5000 else 1.0
                            time.sleep(sleep_time)
                            
                        except Exception as e:
                            print(f"   ❌ Scalping order {i+1} error: {e}")
                            continue
                    
                    # Update cooldown timer
                    self._last_recovery_time = current_time
                    
                    if scalping_success > 0:
                        print(f"   🎯 Scalping result: {scalping_success}/{scalping_limit} orders placed")
                        recovery_success = True
                    else:
                        print(f"   ⚠️ All scalping orders were blocked/failed")
            else:
                print(f"   ✅ No scalping plan provided - skipping scalping recovery")
            
            # Step 3: Execute Hedge Recommendations
            hedge_recommendations = recovery_plan.get('hedge_recommendations', [])
            if hedge_recommendations:
                print(f"\n🛡️ Processing {len(hedge_recommendations)} hedge recommendations...")
                
                for hedge_rec in hedge_recommendations:
                    try:
                        action = hedge_rec.get('action', 'UNKNOWN')
                        size = hedge_rec.get('size', 0)
                        reasoning = hedge_rec.get('reasoning', 'No reason provided')
                        
                        print(f"   🛡️ Hedge: {action} - Size: {size} - {reasoning}")
                        
                        if action == 'EMERGENCY_HEDGE' and size > 0:
                            if hasattr(self, 'execute_emergency_hedge'):
                                success = self.execute_emergency_hedge(size)
                                if success:
                                    print(f"   ✅ Emergency hedge executed: {size} lot")
                                    recovery_success = True
                                else:
                                    print(f"   ❌ Emergency hedge failed")
                                    
                    except Exception as e:
                        print(f"   ❌ Hedge execution error: {e}")
                        continue
            
            # Step 4: Execute Rebalancing Actions
            rebalance_suggestions = recovery_plan.get('rebalance_suggestions', [])
            if rebalance_suggestions:
                print(f"\n⚖️ Processing {len(rebalance_suggestions)} rebalancing actions...")
                
                for rebalance in rebalance_suggestions:
                    try:
                        # เช็คว่าเป็น dict หรือ string
                        if isinstance(rebalance, dict):
                            action_type = rebalance.get('action', 'UNKNOWN')
                        elif isinstance(rebalance, str):
                            action_type = rebalance
                        else:
                            action_type = str(rebalance)
                        
                        print(f"   ⚖️ Rebalance: {action_type}")
                        
                        if action_type == 'CLOSE_WORST_POSITIONS':
                            if hasattr(self, 'close_worst_positions'):
                                close_count = 3 if margin_level > 5000 else 2
                                closed = self.close_worst_positions(close_count)
                                if closed:
                                    recovery_success = True
                                    print(f"   ✅ Closed worst positions: {closed}")
                        
                        elif action_type == 'HEDGE_PROTECTION_NEEDED':
                            if hasattr(self, 'activate_hedge_protection'):
                                self.activate_hedge_protection()
                                print(f"   ✅ Hedge protection activated")
                        
                        elif action_type == 'REDUCE_EXPOSURE':
                            print(f"   ✅ Exposure reduction noted")
                        
                        else:
                            print(f"   📝 Rebalance action noted: {action_type}")
                            
                    except Exception as e:
                        print(f"   ❌ Rebalancing error: {e}")
                        continue
            
            # ⭐ Step 5: Force Disable Crisis Mode (ถ้า margin ดี)
            if margin_level > 2000:
                if hasattr(self, 'crisis_mode') and self.crisis_mode:
                    self.crisis_mode = False
                    print(f"\n🎯 Crisis mode FORCE DISABLED - excellent margin: {margin_level:.0f}%")
            
            # Step 6: Recovery Summary
            print(f"\n📊 RECOVERY PLAN SUMMARY:")
            print(f"   🚨 Crisis Level: {crisis_level}")
            print(f"   💹 Margin Level: {margin_level:.1f}%")
            print(f"   ⚡ Immediate Actions: {len(immediate_actions)} executed")
            print(f"   🎯 Scalping Orders: {len(scalping_plan)} planned, max {max_scalping if 'max_scalping' in locals() else 2} allowed")
            print(f"   🛡️ Hedge Recommendations: {len(hedge_recommendations)}")
            print(f"   ⚖️ Rebalance Actions: {len(rebalance_suggestions)}")
            print(f"   📈 Portfolio Status: {total_positions} pos, {total_orders} orders")
            print(f"   🎯 Crisis Mode: {'DISABLED' if not getattr(self, 'crisis_mode', False) else 'ACTIVE'}")
            print(f"   ✅ Overall Success: {'YES' if recovery_success else 'PARTIAL'}")
            
            if recovery_success:
                print(f"🎉 Recovery plan execution completed successfully")
            else:
                if margin_level > 3000:
                    print(f"⚠️ Recovery plan partial success - but margin excellent, continuing operations")
                else:
                    print(f"⚠️ Recovery plan had limited success")
            
            print("=" * 50)
            return recovery_success
            
        except Exception as e:
            print(f"❌ Recovery plan execution error: {e}")
            import traceback
            traceback.print_exc()
            return False
                    
    def execute_scalping_order(self, scalp_order: Dict):
        """⚡ Smart Scalping - ไม่ออกถี่เบลอ แก้ไขจากเดิม"""
        try:
            order_type = scalp_order['type']  # SCALP_BUY or SCALP_SELL
            price = scalp_order['price']
            lot_size = scalp_order['lot_size']
            
            direction = 'BUY' if 'BUY' in order_type else 'SELL'
            
            print(f"🧠 Smart Scalping Check: {direction} {lot_size} lot at ${price:.2f}")
            
            # 🛡️ SMART CHECK 1: Cooldown Period (ไม่ให้ยิงบ่อย)
            if not hasattr(self, '_last_scalp_time'):
                self._last_scalp_time = {}
            
            cooldown_key = f"{direction}_{int(price/10)*10}"  # Group by 10-point zones (กว้างขึ้น)
            current_time = time.time()
            
            if cooldown_key in self._last_scalp_time:
                time_since_last = current_time - self._last_scalp_time[cooldown_key]
                if time_since_last < 300:  # 5 นาที cooldown (เพิ่มจาก 3 นาที)
                    print(f"   ⏱️ Cooldown active: {300-time_since_last:.0f}s remaining")
                    return False
            
            # 🛡️ SMART CHECK 2: ระยะห่างจากไม้อื่น (ไม่ให้แออัด)
            current_price = self.get_current_price()
            if current_price:
                # ⭐ เพิ่มระยะห่างขั้นต่ำให้มากขึ้น
                min_spacing_orders = 150  # จาก pending orders ห่าง 150 points
                min_spacing_positions = 200  # จาก positions ห่าง 200 points
                
                # เช็คระยะห่างจาก pending orders
                if hasattr(self, 'pending_orders'):
                    nearby_orders = 0
                    for order_info in self.pending_orders.values():
                        existing_price = order_info.get('price', 0)
                        distance = abs(price - existing_price)
                        
                        if distance < min_spacing_orders:
                            nearby_orders += 1
                            print(f"   🚫 Too close to order: {distance:.1f} points < {min_spacing_orders}")
                    
                    # ถ้ามีไม้ใกล้เกิน 2 ตัว = เกินไป
                    if nearby_orders >= 2:
                        print(f"   ❌ Too many nearby orders: {nearby_orders} orders within {min_spacing_orders} points")
                        return False
                
                # เช็คระยะห่างจาก current positions (เข้มงวดกว่า)
                if hasattr(self, 'active_positions'):
                    for pos_info in self.active_positions.values():
                        pos_price = pos_info.get('price_open', 0)
                        distance = abs(price - pos_price)
                        
                        if distance < min_spacing_positions:
                            print(f"   ❌ BLOCKED: Too close to position: {distance:.1f} points < {min_spacing_positions}")
                            return False
                            
                # ⭐ เพิ่มเช็คระยะห่างจาก market price
                market_distance = abs(price - current_price)
                if market_distance < 50:  # ไม่ให้วางไม้ใกล้ market เกินไป
                    print(f"   ⚠️ Too close to market: {market_distance:.1f} points < 50")
                    return False
            
            # 🛡️ SMART CHECK 3: Portfolio Load (ไม่ให้เทรดเกิน capacity)
            total_positions = len(getattr(self, 'active_positions', {}))
            total_orders = len(getattr(self, 'pending_orders', {}))
            total_exposure = total_positions + total_orders
            
            # ⭐ ลดจำนวนไม้สูงสุดให้น้อยลง
            max_exposure = 8  # จาก 15 → 8 ตัว (ลดลง 47%)
            max_positions = 5  # positions ไม่เกิน 5 ตัว
            
            if total_exposure >= max_exposure:
                print(f"   ❌ Portfolio full: {total_exposure}/{max_exposure} total exposure")
                return False
                
            if total_positions >= max_positions:
                print(f"   ❌ Too many positions: {total_positions}/{max_positions} positions")
                return False
            
            # 🛡️ SMART CHECK 4: Market Distance (ปรับเฉพาะถ้าใกล้มาก)
            if current_price:
                price_diff = abs(price - current_price)
                
                # ปรับเกณฑ์ให้เหมาะสม - ใกล้แค่ 20 points ถึงจะใช้ market
                if price_diff < 20.0:  # เดิม: 3.0 → ใหม่: 20.0
                    print(f"   💡 Price close to market ({price_diff:.1f} points) - using market order")
                    
                    # ใช้ market order แทน
                    order_type_mt5 = mt5.ORDER_TYPE_BUY if direction == 'BUY' else mt5.ORDER_TYPE_SELL
                    
                    order_request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": self.gold_symbol,
                        "volume": lot_size,
                        "type": order_type_mt5,
                        "deviation": 20,
                        "magic": self.magic_number,
                        "comment": "SMART_SCALP_MARKET"
                    }
                else:
                    # ใช้ pending order
                    order_type_mt5 = mt5.ORDER_TYPE_BUY_LIMIT if direction == 'BUY' else mt5.ORDER_TYPE_SELL_LIMIT
                    
                    order_request = {
                        "action": mt5.TRADE_ACTION_PENDING,
                        "symbol": self.gold_symbol,
                        "volume": lot_size,
                        "type": order_type_mt5,
                        "price": round(price, 2),
                        "magic": self.magic_number,
                        "comment": f"SMART_SCALP_{int(price_diff)}pts"
                    }
            else:
                print(f"⚠️ Cannot get current price - using conservative pending order")
                # Fallback to pending order
                order_type_mt5 = mt5.ORDER_TYPE_BUY_LIMIT if direction == 'BUY' else mt5.ORDER_TYPE_SELL_LIMIT
                
                order_request = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": self.gold_symbol,
                    "volume": lot_size,
                    "type": order_type_mt5,
                    "price": round(price, 2),
                    "magic": self.magic_number,
                    "comment": "SMART_SCALP_SAFE"
                }
            
            print(f"   📤 Smart scalping request: {order_request}")
            
            # Execute scalping order
            result = mt5.order_send(order_request)
            
            if result is None:
                print(f"   ❌ Smart scalping: order_send returned None")
                return False
            
            print(f"   📥 Smart scalping result: {result.retcode}")
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                # 🎯 อัพเดท cooldown timer
                self._last_scalp_time[cooldown_key] = current_time
                
                print(f"   ✅ Smart scalping success: {direction} {lot_size} lot")
                print(f"   ⏱️ Cooldown set for zone: {cooldown_key}")
                return True
            else:
                error_msg = self.get_error_description(result.retcode) if hasattr(self, 'get_error_description') else f"Error {result.retcode}"
                print(f"   ❌ Smart scalping failed: {error_msg}")
                return False
                
        except Exception as e:
            print(f"❌ Smart scalping error: {e}")
            return False
            
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
        """Enhanced grid management - แก้ให้เทรดได้เต็มที่ ไม่มีข้อจำกัด"""
        try:
            current_positions = len(self.active_positions)
            pending_orders = len(self.pending_orders)
            total_exposure = current_positions + pending_orders
            
            print(f"📊 Grid Status: Positions:{current_positions}, Orders:{pending_orders}, Total:{total_exposure}")
            
            # ⭐ แก้ไข 1: Force disable crisis mode ทุกครั้ง
            account_info = getattr(self, 'mt5_connector', None)
            margin_level = 1000  # default
            
            if account_info and hasattr(account_info, 'get_account_info'):
                acc_data = account_info.get_account_info()
                if acc_data:
                    margin_level = acc_data.get('margin_level', 1000)
                    print(f"💹 Current Margin Level: {margin_level:.1f}%")
            
            # ⭐ ALWAYS disable crisis mode เมื่อ margin > 1000%
            if margin_level > 1000:  # ลดจาก 2000 → 1000
                if hasattr(self, 'crisis_mode'):
                    self.crisis_mode = False
                    print(f"✅ Crisis mode FORCE DISABLED - margin: {margin_level:.0f}%")
            
            # ⭐ แก้ไข 2: เพิ่มขีดจำกัดให้สูงมากๆ
            max_orders = 25  # เดิม: 15 → ใหม่: 25
            if pending_orders < max_orders:
                shortage = max_orders - pending_orders
                print(f"📊 Pending Orders Low: {pending_orders}/{max_orders} - Adding {shortage} orders...")
                
                # เรียก add_strategic_orders หลายครั้ง
                for batch in range(min(3, shortage // 5 + 1)):  # แบ่งเป็น batch
                    self.add_strategic_orders()
                    time.sleep(0.2)  # หน่วงเล็กน้อย
            
            # ⭐ แก้ไข 3: เช็ค nearby orders แบบ aggressive
            current_price = self.get_current_price()
            if current_price:
                nearby_range = 50.0  # เดิม: 30.0 → ใหม่: 50.0 (กว้างมากขึ้น)
                nearby_orders = 0
                
                for order in self.pending_orders.values():
                    order_price = order.get('price', 0)
                    if abs(order_price - current_price) <= nearby_range:
                        nearby_orders += 1
                
                print(f"📍 Orders near market (±{nearby_range} points): {nearby_orders}")
                
                # ⭐ แก้ไข 4: เพิ่มไม้ aggressive มาก
                min_nearby = 3  # เดิม: 1 → ใหม่: 3
                if nearby_orders < min_nearby:
                    print(f"🚨 Need more nearby orders ({nearby_orders}/{min_nearby}) - Adding AGGRESSIVE coverage!")
                    
                    # เพิ่มไม้หลายระดับ
                    distances = [10, 20, 30, 40, 50]  # 5 ระดับ
                    for distance in distances:
                        buy_price = current_price - (distance * 0.01)
                        sell_price = current_price + (distance * 0.01)
                        
                        if not self.level_exists_enhanced(buy_price, 'BUY', 5):  # tolerance ลดลง
                            self.place_enhanced_order(buy_price, 'BUY', 'AGGRESSIVE_BUY')
                            print(f"   🚨 Added BUY at ${buy_price:.2f}")
                        
                        if not self.level_exists_enhanced(sell_price, 'SELL', 5):
                            self.place_enhanced_order(sell_price, 'SELL', 'AGGRESSIVE_SELL')
                            print(f"   🚨 Added SELL at ${sell_price:.2f}")
                        
                        time.sleep(0.1)  # หน่วงสั้นๆ
            
            # ⭐ แก้ไข 5: ลบ crisis mode restrictions ทั้งหมด
            # (ลบส่วน crisis override ออก เพราะเราปิด crisis mode แล้ว)
            
            # ⭐ เพิ่ม: Coverage Check - ตรวจสอบ gap ใหญ่
            if current_price and len(self.pending_orders) > 0:
                # หา gap ที่ใหญ่ที่สุด
                prices = [order.get('price', 0) for order in self.pending_orders.values()]
                prices.sort()
                
                max_gap = 0
                gap_start = 0
                
                for i in range(len(prices) - 1):
                    gap = prices[i + 1] - prices[i]
                    if gap > max_gap:
                        max_gap = gap
                        gap_start = prices[i]
                
                # ถ้า gap ใหญ่กว่า 100 points
                if max_gap > 1.0:  # 100 points
                    print(f"🕳️ Large gap detected: {max_gap:.2f} points - Filling gap...")
                    
                    # เติมไม้ใน gap
                    gap_middle = gap_start + (max_gap / 2)
                    
                    if not self.level_exists_enhanced(gap_middle, 'BUY', 20):
                        self.place_enhanced_order(gap_middle, 'BUY', 'GAP_FILL_BUY')
                        print(f"   🕳️ Gap fill BUY at ${gap_middle:.2f}")
                    
                    if not self.level_exists_enhanced(gap_middle, 'SELL', 20):
                        self.place_enhanced_order(gap_middle, 'SELL', 'GAP_FILL_SELL')
                        print(f"   🕳️ Gap fill SELL at ${gap_middle:.2f}")
            
            # ⭐ เพิ่ม: Ultra Aggressive Mode สำหรับ margin สูงมาก
            if margin_level > 10000:  # margin เกิน 10,000%
                print(f"🚀 ULTRA AGGRESSIVE MODE - Margin: {margin_level:.0f}%")
                
                # เพิ่มไม้ ultra aggressive
                if pending_orders < 40:  # สูงสุด 40 orders!
                    ultra_shortage = min(5, 40 - pending_orders)
                    print(f"🚀 Ultra mode: Adding {ultra_shortage} more orders...")
                    
                    for _ in range(ultra_shortage):
                        self.add_strategic_orders()
                        time.sleep(0.1)
            
            print(f"✅ Grid management completed - Status: {pending_orders} orders, {current_positions} positions")
            
        except Exception as e:
            print(f"❌ Enhanced grid management error: {e}")

    def add_emergency_nearby_orders(self):
        """เพิ่ม orders ใกล้ตลาดเพื่อ coverage - ใหม่"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                return
            
            # เพิ่มไม้ใกล้ๆ ตลาด
            close_spacing = 20  # 20 points
            
            buy_price = current_price - (close_spacing * 0.01)
            sell_price = current_price + (close_spacing * 0.01)
            
            orders_added = 0
            
            if not self.level_exists_enhanced(buy_price, 'BUY', 10):
                success = self.place_enhanced_order(buy_price, 'BUY', 'EMERGENCY_NEAR')
                if success:
                    orders_added += 1
                    print(f"   🚨 Emergency BUY at ${buy_price:.2f}")
            
            if not self.level_exists_enhanced(sell_price, 'SELL', 10):
                success = self.place_enhanced_order(sell_price, 'SELL', 'EMERGENCY_NEAR')
                if success:
                    orders_added += 1
                    print(f"   🚨 Emergency SELL at ${sell_price:.2f}")
            
            if orders_added > 0:
                print(f"🚨 Emergency nearby orders: {orders_added} added")
            
        except Exception as e:
            print(f"❌ Emergency nearby orders error: {e}")


    def add_strategic_orders(self):
        """เพิ่ม orders อย่างมีกลยุทธ์ - แก้ให้ aggressive"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                print("❌ Cannot get current price for strategic orders")
                return
            
            spacing = self.calculate_dynamic_spacing()
            orders_added = 0
            max_orders = 8  # เดิม: 6 → ใหม่: 8
            
            print(f"🎯 Adding strategic orders with {spacing} points spacing...")
            
            # เพิ่ม BUY orders
            for i in range(1, max_orders + 1):
                buy_price = current_price - (spacing * i * 0.01)
                
                if not self.level_exists_enhanced(buy_price, 'BUY', spacing * 0.01 * 0.2):  # tolerance ลดลง
                    success = self.place_enhanced_order(buy_price, 'BUY', 'STRATEGIC_GRID')
                    if success:
                        orders_added += 1
                        print(f"   ✅ Strategic BUY at ${buy_price:.2f}")
                    time.sleep(0.1)  # เดิม: 0.3 → ใหม่: 0.1 (เร็วขึ้น)
            
            # เพิ่ม SELL orders
            for i in range(1, max_orders + 1):
                sell_price = current_price + (spacing * i * 0.01)
                
                if not self.level_exists_enhanced(sell_price, 'SELL', spacing * 0.01 * 0.2):
                    success = self.place_enhanced_order(sell_price, 'SELL', 'STRATEGIC_GRID')
                    if success:
                        orders_added += 1
                        print(f"   ✅ Strategic SELL at ${sell_price:.2f}")
                    time.sleep(0.1)
            
            print(f"📊 Strategic orders result: {orders_added} orders added")
            
        except Exception as e:
            print(f"❌ Strategic orders error: {e}")

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
        แก้ไขจาก method เดิม เพิ่ม safety check + แก้ปัญหาการปิดไม้
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
            
            # 📊 Original execution logic (แก้ไขการปิดไม้)
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
                    
                    print(f"   🎯 Attempting to close position #{ticket} - {comment}")
                    
                    # ✅ แก้ไข: ใช้ close_position_by_ticket แทน close_position
                    if self.close_position_by_ticket(ticket):
                        success_count += 1
                        profit = position.get('profit', 0)
                        total_profit += profit
                        print(f"     ✅ Closed #{ticket}: ${profit:.2f} - {comment}")
                    else:
                        print(f"     ❌ Failed to close #{ticket} - {comment}")
                    
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
            print(f"❌ Execute profit opportunity error: {e}")
            import traceback
            traceback.print_exc()
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
        """Close position by ticket number - แก้ปัญหาการปิดไม้"""
        try:
            # 1. ดึงข้อมูล position ปัจจุบัน
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                print(f"❌ Position {ticket} not found")
                return False
            
            position = positions[0]
            print(f"🔍 Closing position {ticket}: {position.symbol} {position.type} {position.volume}")
            
            # 2. ดึงราคาปัจจุบันแบบ fresh
            tick = mt5.symbol_info_tick(position.symbol)
            if not tick:
                print(f"❌ Cannot get tick data for {position.symbol}")
                return False
            
            # 3. กำหนดทิศทางการปิดและราคา
            if position.type == mt5.POSITION_TYPE_BUY:
                # ปิด BUY ด้วย SELL ที่ราคา BID
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
                print(f"   📉 Closing BUY position at BID: ${price:.2f}")
            else:
                # ปิด SELL ด้วย BUY ที่ราคา ASK  
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
                print(f"   📈 Closing SELL position at ASK: ${price:.2f}")
            
            # 4. สร้าง request ที่ถูกต้อง
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": ticket,  # ใช้ ticket ของ position
                "price": price,
                "magic": position.magic,  # ใช้ magic เดียวกับ position
                "comment": "AI_SMART_CLOSE",
                "deviation": 20  # เพิ่ม deviation เผื่อราคาเปลี่ยน
            }
            
            print(f"   📤 Close request: {close_request}")
            
            # 5. ส่ง order ปิด
            result = mt5.order_send(close_request)
            
            if result is None:
                print(f"   ❌ order_send returned None for ticket {ticket}")
                return False
            
            print(f"   📥 Result code: {result.retcode}")
            
            # 6. ตรวจสอบผลลัพธ์
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                # สำเร็จ
                profit = getattr(result, 'profit', 0.0)
                print(f"   ✅ Position {ticket} CLOSED successfully! Profit: ${profit:.2f}")
                
                # ลบออกจาก tracking
                if hasattr(self, 'active_positions') and ticket in self.active_positions:
                    del self.active_positions[ticket]
                
                return True
                
            elif result.retcode == mt5.TRADE_RETCODE_REQUOTE:
                # ราคาเปลี่ยน ลองใหม่ 1 ครั้ง
                print(f"   ⚠️ Requote detected, retrying...")
                time.sleep(0.5)
                
                # ดึงราคาใหม่
                new_tick = mt5.symbol_info_tick(position.symbol)
                if new_tick:
                    new_price = new_tick.bid if position.type == mt5.POSITION_TYPE_BUY else new_tick.ask
                    close_request["price"] = new_price
                    
                    retry_result = mt5.order_send(close_request)
                    if retry_result and retry_result.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"   ✅ Position {ticket} CLOSED on retry!")
                        return True
                    else:
                        print(f"   ❌ Retry failed: {retry_result.retcode if retry_result else 'None'}")
                
                return False
                
            else:
                # ล้มเหลว
                error_msg = self.get_error_description(result.retcode)
                print(f"   ❌ Close failed: {error_msg}")
                return False
            
        except Exception as e:
            print(f"❌ Close position error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_error_description(self, error_code):
        """Get human readable error description"""
        error_codes = {
            10004: "Requote - ราคาเปลี่ยน",
            10006: "Request rejected - คำขอถูกปฏิเสธ", 
            10007: "Request canceled - คำขอถูกยกเลิก",
            10008: "Order placed - Order ถูกวาง",
            10009: "Request completed - สำเร็จ",
            10010: "Partial fill only - Fill บางส่วน",
            10011: "Request processing error - ข้อผิดพลาดการประมวลผล",
            10012: "Request timeout - หมดเวลา",
            10013: "Invalid request - คำขอไม่ถูกต้อง",
            10014: "Invalid volume - Volume ไม่ถูกต้อง",
            10015: "Invalid price - ราคาไม่ถูกต้อง",
            10016: "Invalid stops - Stop ไม่ถูกต้อง",
            10017: "Trade disabled - การเทรดถูกปิด",
            10018: "Market closed - ตลาดปิด",
            10019: "Not enough money - เงินไม่พอ",
            10020: "Price changed - ราคาเปลี่ยน",
            10021: "Off quotes - ไม่มีราคา",
            10022: "Invalid expiration - วันหมดอายุไม่ถูกต้อง",
            10023: "Order state changed - สถานะ Order เปลี่ยน",
            10024: "Too many requests - คำขอมากเกินไป",
            10025: "No changes - ไม่มีการเปลี่ยนแปลง",
            10026: "Autotrading disabled - Auto trading ปิด",
            10027: "Market closed - ตลาดปิด",
            10028: "Invalid price in request - ราคาในคำขอไม่ถูกต้อง",
            10029: "Invalid stops in request - Stop ในคำขอไม่ถูกต้อง",
            10030: "Invalid volume in request - Volume ในคำขอไม่ถูกต้อง"
        }
        return error_codes.get(error_code, f"Unknown error: {error_code}")
        
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
        """📊 Get comprehensive AI status with Pro features + Crisis info"""
        try:
            # Basic account information
            account_info = self.mt5_connector.get_account_info() if self.mt5_connector else {}
            balance = account_info.get('balance', 0)
            equity = account_info.get('equity', balance)
            margin_level = account_info.get('margin_level', 1000)
            
            # Position and order counts
            total_positions = len(getattr(self, 'active_positions', {}))
            total_pending = len(getattr(self, 'pending_orders', {}))
            
            # Calculate floating P&L
            floating_pnl = equity - balance if balance > 0 else 0
            
            # Calculate total profit from active positions
            total_profit = 0
            profitable_positions = 0
            losing_positions = 0
            
            if hasattr(self, 'active_positions'):
                for position in self.active_positions.values():
                    profit = position.get('profit', 0)
                    total_profit += profit
                    if profit > 0:
                        profitable_positions += 1
                    elif profit < 0:
                        losing_positions += 1
            
            # Calculate AI health score
            ai_health = getattr(self, 'ai_health_score', 50)
            if hasattr(self, 'ai_calculate_portfolio_health'):
                try:
                    ai_health = self.ai_calculate_portfolio_health()
                except:
                    pass
            
            # Calculate survivability usage
            survivability_used = 0
            if hasattr(self, 'survivability') and self.survivability > 0:
                if floating_pnl < 0:
                    survivability_used = abs(floating_pnl) / (self.survivability * 0.1)  # Approximate
            
            # Basic status
            status = {
                # Account information
                'account_balance': balance,
                'account_equity': equity,
                'floating_pnl': floating_pnl,
                'margin_level': margin_level,
                
                # Trading information
                'total_positions': total_positions,
                'total_pending_orders': total_pending,
                'total_profit': total_profit,
                'profitable_positions': profitable_positions,
                'losing_positions': losing_positions,
                
                # AI information
                'ai_active': getattr(self, 'ai_active', False),
                'ai_health_score': ai_health,
                'survivability_usage': survivability_used,
                
                # System status
                'gold_symbol': getattr(self, 'gold_symbol', 'XAUUSD'),
                'base_lot': getattr(self, 'base_lot', 0.01),
                'last_update': datetime.now().isoformat(),
            }
            
            # 🆕 AI Pro features
            status.update({
                'crisis_mode': getattr(self, 'crisis_mode', False),
                'smart_enhancement_enabled': hasattr(self, 'smart_enhancer') and getattr(self.smart_enhancer, 'enabled', False),
                'last_crisis_check': getattr(self, 'last_crisis_check', 0),
                'enhanced_margin_monitoring': getattr(self, 'enhanced_margin_monitoring', False),
            })
            
            # SmartEnhancements V2 status
            if hasattr(self, 'smart_enhancer') and self.smart_enhancer.enabled:
                try:
                    enhancement_status = self.smart_enhancer.get_enhancement_status()
                    status.update({
                        # Market analysis
                        'current_session': enhancement_status.get('current_session', 'UNKNOWN'),
                        'volatility_forecast': enhancement_status.get('volatility_forecast', 0),
                        'is_peak_time': enhancement_status.get('is_peak_time', False),
                        'optimal_strategy': enhancement_status.get('optimal_strategy', 'CONSERVATIVE'),
                        
                        # Enhancement performance
                        'daily_rebate': enhancement_status.get('daily_rebate', 0),
                        'daily_volume': enhancement_status.get('daily_volume', 0),
                        'volume_efficiency': enhancement_status.get('volume_efficiency', 0),
                        'rebate_target': enhancement_status.get('rebate_target', 50),
                        
                        # System status
                        'enhancement_last_update': enhancement_status.get('last_update', ''),
                    })
                    
                except Exception as e:
                    print(f"⚠️ Enhancement status error: {e}")
                    status['enhancement_error'] = str(e)
            
            # Crisis analysis (if available)
            if hasattr(self, 'smart_enhancer') and total_positions > 0:
                try:
                    positions = list(self.active_positions.values())
                    crisis_analysis = self.smart_enhancer.check_crisis_situations(positions, account_info)
                    
                    status.update({
                        'crisis_level': crisis_analysis.level.value,
                        'imbalance_ratio': crisis_analysis.imbalance_ratio,
                        'emergency_hedge_size': crisis_analysis.emergency_hedge_size,
                        'priority_positions_count': len(crisis_analysis.priority_positions),
                        'recommended_actions_count': len(crisis_analysis.recommended_actions),
                    })
                    
                except Exception as e:
                    print(f"⚠️ Crisis analysis error: {e}")
                    status['crisis_analysis_error'] = str(e)
            
            # Portfolio balance analysis
            if total_positions > 0:
                buy_positions = [p for p in self.active_positions.values() if p.get('direction') == 'BUY']
                sell_positions = [p for p in self.active_positions.values() if p.get('direction') == 'SELL']
                
                status.update({
                    'buy_positions_count': len(buy_positions),
                    'sell_positions_count': len(sell_positions),
                    'portfolio_balance_ratio': len(buy_positions) / max(len(sell_positions), 1),
                    'buy_total_profit': sum([p.get('profit', 0) for p in buy_positions]),
                    'sell_total_profit': sum([p.get('profit', 0) for p in sell_positions]),
                })
            
            # Performance metrics
            if hasattr(self, 'performance_history'):
                try:
                    recent_performance = getattr(self, 'performance_history', [])[-10:]  # Last 10 records
                    if recent_performance:
                        avg_profit = sum([p.get('profit', 0) for p in recent_performance]) / len(recent_performance)
                        status['recent_avg_profit'] = avg_profit
                except:
                    pass
            
            return status
            
        except Exception as e:
            print(f"❌ AI Status error: {e}")
            import traceback
            traceback.print_exc()
            
            # Return minimal status on error
            return {
                'error': str(e),
                'ai_active': getattr(self, 'ai_active', False),
                'crisis_mode': getattr(self, 'crisis_mode', False),
                'total_positions': len(getattr(self, 'active_positions', {})),
                'last_update': datetime.now().isoformat(),
            }
                
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
        🧠 Ultra Smart Safety Check - ปิดได้ทุกสถานการณ์ แต่ฉลาด + คุ้มค่า
        """
        try:
            ticket = position.get('ticket', 0)
            direction = position.get('direction', 'UNKNOWN')
            profit = position.get('profit', 0)
            lot_size = position.get('lot_size', 0)
            
            # 📊 ข้อมูลภาพรวม Portfolio
            total_positions = len(self.active_positions)
            total_pnl = sum(p.get('profit', 0) for p in self.active_positions.values())
            profitable_positions = len([p for p in self.active_positions.values() if p.get('profit', 0) > 1.0])
            losing_positions = len([p for p in self.active_positions.values() if p.get('profit', 0) < -1.0])
            
            # 🔥 Priority 1: เก็บกำไรเสมอ (ไม่ว่าจะเป็นสถานการณ์ไหน)
            if profit > 0.5:  # กำไรทุกจำนวน
                
                # เช็ค Balance แบบฉลาด
                balance_info = self.check_portfolio_balance_ratio()
                
                # กำไรสูง → ปิดได้ทันที ไม่สน balance
                if profit > 8.0:
                    return {
                        'can_close': True,
                        'reason': f'High profit override: ${profit:.2f}',
                        'urgency': 'HIGH_PROFIT',
                        'alternative_action': None
                    }
                
                # กำไรปานกลาง → เช็ค balance แบบหลวม
                if balance_info['status'] in ['BALANCED', 'MINOR_IMBALANCE', 'MODERATE_IMBALANCE']:
                    return {
                        'can_close': True,
                        'reason': f'Good profit + balanced portfolio: ${profit:.2f}',
                        'urgency': 'PROFIT_BALANCED',
                        'alternative_action': None
                    }
                
                # SEVERE/CRITICAL Imbalance → พิจารณาอย่างฉลาด
                if balance_info['status'] in ['SEVERE_IMBALANCE', 'CRITICAL_IMBALANCE']:
                    majority_direction = 'BUY' if balance_info['total_buy'] > balance_info['total_sell'] else 'SELL'
                    
                    # ปิดฝั่งที่เยอะ → ดีเสมอ
                    if direction == majority_direction:
                        return {
                            'can_close': True,
                            'reason': f'Profit + reduces {majority_direction} excess: ${profit:.2f}',
                            'urgency': 'PROFIT_BALANCE_HELP',
                            'alternative_action': None
                        }
                    
                    # ปิดฝั่งที่น้อย → ต้องมีคู่หรือกำไรดี
                    else:
                        # หาคู่กำไรฝั่งตรงข้าม
                        opposite_profitable = [p for p in self.active_positions.values() 
                                            if p.get('direction') == majority_direction and p.get('profit', 0) > 1.0]
                        
                        if len(opposite_profitable) > 0 and profit > 2.0:
                            # มีคู่และกำไรดี → ปิดแบบคู่
                            return {
                                'can_close': True,
                                'reason': f'Profit with available pairs: ${profit:.2f}',
                                'urgency': 'PROFIT_WITH_PAIR',
                                'alternative_action': f'Consider closing {majority_direction} pair too'
                            }
                        elif profit > 5.0:
                            # กำไรดีมาก → ปิดได้
                            return {
                                'can_close': True,
                                'reason': f'Good profit overrides imbalance: ${profit:.2f}',
                                'urgency': 'GOOD_PROFIT_OVERRIDE',
                                'alternative_action': None
                            }
                        else:
                            # รอคู่กำไรก่อน
                            return {
                                'can_close': False,
                                'reason': f'Wait for {majority_direction} profit pair (Current: ${profit:.2f})',
                                'urgency': 'WAIT_PROFIT_PAIR',
                                'alternative_action': f'Find profitable {majority_direction} to close together'
                            }
                
                # Default สำหรับกำไร → ปิดได้
                return {
                    'can_close': True,
                    'reason': f'Profit is always good: ${profit:.2f}',
                    'urgency': 'DEFAULT_PROFIT',
                    'alternative_action': None
                }
            
            # 🎯 Priority 2: Position Overload Management
            if total_positions > 45:
                # ไม้เยอะเกินไป → ปิดแม้ขาดทุนเล็กน้อย
                if profit > -3.0:  # ขาดทุนไม่เกิน $3
                    return {
                        'can_close': True,
                        'reason': f'Position overload cleanup: {total_positions} positions, ${profit:.2f} loss acceptable',
                        'urgency': 'OVERLOAD_CLEANUP',
                        'alternative_action': None
                    }
            
            # 💪 Priority 3: Margin Optimization
            margin_used = lot_size * 2000  # ประมาณการ margin
            if margin_used > 1000 and profit > -2.0:  # ไม้ใหญ่ + ขาดทุนไม่เกิน $2
                return {
                    'can_close': True,
                    'reason': f'Free up margin: ${margin_used:.0f} margin, ${profit:.2f} minor loss',
                    'urgency': 'MARGIN_OPTIMIZATION',
                    'alternative_action': None
                }
            
            # 🔄 Priority 4: Smart Loss Management
            if profit < 0:  # ขาดทุน
                
                # ไม่ปิดขาดทุนใหญ่ (เว้นแต่จำเป็น)
                if profit < -5.0:
                    # เฉพาะกรณีฉุกเฉินถึงจะปิดขาดทุนใหญ่
                    if total_positions > 60:  # ไม้เยอะมากจริงๆ
                        return {
                            'can_close': True,
                            'reason': f'Emergency: {total_positions} positions, cut large loss ${profit:.2f}',
                            'urgency': 'EMERGENCY_CUT_LOSS',
                            'alternative_action': None
                        }
                    else:
                        return {
                            'can_close': False,
                            'reason': f'Keep large loss for recovery: ${profit:.2f}',
                            'urgency': 'HOLD_FOR_RECOVERY',
                            'alternative_action': 'Wait for market reversal or hedge'
                        }
                
                # ขาดทุนเล็ก → พิจารณาตาม portfolio
                else:  # ขาดทุน $0-5
                    balance_info = self.check_portfolio_balance_ratio()
                    
                    # ถ้าปิดแล้วช่วย balance → อนุญาต
                    if balance_info['status'] in ['SEVERE_IMBALANCE', 'CRITICAL_IMBALANCE']:
                        majority_direction = 'BUY' if balance_info['total_buy'] > balance_info['total_sell'] else 'SELL'
                        
                        if direction == majority_direction:
                            return {
                                'can_close': True,
                                'reason': f'Minor loss but helps balance: ${profit:.2f}',
                                'urgency': 'LOSS_FOR_BALANCE',
                                'alternative_action': None
                            }
                    
                    # Portfolio มีกำไรรวมดี → ยอมขาดทุนเล็ก
                    if total_pnl > 50 and profit > -2.0:
                        return {
                            'can_close': True,
                            'reason': f'Portfolio profitable (${total_pnl:.2f}), minor loss OK: ${profit:.2f}',
                            'urgency': 'PORTFOLIO_BUFFER',
                            'alternative_action': None
                        }
                    
                    # มีไม้กำไรเยอะ → ยอมขาดทุนเล็ก
                    if profitable_positions > losing_positions and profit > -1.5:
                        return {
                            'can_close': True,
                            'reason': f'More profitable positions ({profitable_positions}), tiny loss OK: ${profit:.2f}',
                            'urgency': 'PROFIT_MAJORITY',
                            'alternative_action': None
                        }
                    
                    # Default สำหรับขาดทุนเล็ก → รอก่อน
                    return {
                        'can_close': False,
                        'reason': f'Hold small loss for recovery: ${profit:.2f}',
                        'urgency': 'HOLD_SMALL_LOSS',
                        'alternative_action': 'Wait for reversal or pair with profit'
                    }
            
            # 🕒 Priority 5: Time-based Flexibility
            position_age = self._calculate_position_age_minutes(position)
            if position_age > 180:  # อยู่เกิน 3 ชั่วโมง
                if profit > -1.0:  # ขาดทุนไม่เกิน $3
                    return {
                        'can_close': True,
                        'reason': f'Aged position ({position_age:.0f} min), acceptable loss: ${profit:.2f}',
                        'urgency': 'TIME_BASED_CLEANUP',
                        'alternative_action': None
                    }
            
            # 🎯 Final Decision: Default Hold
            return {
                'can_close': False,
                'reason': f'Hold for better opportunity: ${profit:.2f}',
                'urgency': 'STRATEGIC_HOLD',
                'alternative_action': 'Wait for profit or better market conditions'
            }
            
        except Exception as e:
            # Error case → อนุญาตปิดเพื่อความปลอดภัย
            return {
                'can_close': True,
                'reason': f'Error safety fallback: {e}',
                'urgency': 'ERROR_SAFETY',
                'alternative_action': None
            }

    def _calculate_position_age_minutes(self, position: Dict) -> float:
        """คำนวณอายุของ position เป็นนาที"""
        try:
            # ลองดึง entry time จาก position
            entry_time = position.get('entry_time')
            if not entry_time:
                # ถ้าไม่มี ใช้ current time (assume ใหม่)
                return 0
            
            if isinstance(entry_time, str):
                from datetime import datetime
                entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            
            from datetime import datetime
            age_seconds = (datetime.now() - entry_time).total_seconds()
            return age_seconds / 60
            
        except Exception as e:
            # ถ้า error ถือว่าไม้ใหม่
            return 0
    
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
        🧠 AI PRO TRADER SYSTEM - ระบบแก้ไม้ระดับเทพ
        แก้จาก method เดิม เพิ่มความฉลาดแบบนักเทรดมืออาชีพ
        คำนึงถึง: Margin, Floating P&L, Critical Situations, Smart Recovery
        """
        try:
            print("🧠 AI PRO TRADER SYSTEM - Professional Recovery & Management")
            print("=" * 70)
            
            # ===================== ACCOUNT ANALYSIS =====================
            account_info = mt5.account_info()
            if account_info:
                balance = account_info.balance
                equity = account_info.equity
                margin = account_info.margin
                free_margin = account_info.margin_free
                floating_pnl = equity - balance
                margin_level = account_info.margin_level if account_info.margin_level else 0
                
                # 🚨 Critical Status Detection
                is_margin_critical = margin_level < 300
                is_floating_critical = floating_pnl < -200
                is_emergency = is_margin_critical or floating_pnl < -500
                
                print(f"📊 ACCOUNT STATUS:")
                print(f"   💵 Balance: ${balance:.2f} | 💎 Equity: ${equity:.2f}")
                print(f"   📈 Floating P&L: ${floating_pnl:.2f}")
                print(f"   🔒 Margin: ${margin:.2f} | 🆓 Free: ${free_margin:.2f}")
                print(f"   📊 Margin Level: {margin_level:.1f}%")
                print(f"   🚨 Status: {'EMERGENCY' if is_emergency else 'CRITICAL' if (is_margin_critical or is_floating_critical) else 'NORMAL'}")
            else:
                print("⚠️ Cannot get account info - using simulation mode")
                balance = equity = margin = free_margin = floating_pnl = margin_level = 0
                is_emergency = is_margin_critical = is_floating_critical = False
            
            positions = list(self.active_positions.values())
            if len(positions) == 0:
                return []
            
            # ===================== POSITION ANALYSIS =====================
            current_price = self.get_current_price()
            if not current_price:
                current_price = 2650.0  # fallback
            
            buy_positions = [p for p in positions if p.get('direction') == 'BUY']
            sell_positions = [p for p in positions if p.get('direction') == 'SELL']
            
            profitable_buys = [p for p in buy_positions if p.get('profit', 0) > 1]
            profitable_sells = [p for p in sell_positions if p.get('profit', 0) > 1]
            losing_buys = [p for p in buy_positions if p.get('profit', 0) < -1]
            losing_sells = [p for p in sell_positions if p.get('profit', 0) < -1]
            
            # 🔍 Critical Situation Detection
            total_buy_volume = sum([p.get('volume', 0.01) for p in buy_positions])
            total_sell_volume = sum([p.get('volume', 0.01) for p in sell_positions])
            total_buy_loss = sum([p.get('profit', 0) for p in losing_buys if p.get('profit', 0) < 0])
            total_sell_loss = sum([p.get('profit', 0) for p in losing_sells if p.get('profit', 0) < 0])
            
            # 🚨 CRITICAL IMBALANCE DETECTION (แบบในภาพคุณ)
            is_buy_heavy = len(buy_positions) >= 15 and len(sell_positions) <= 3
            is_sell_heavy = len(sell_positions) >= 15 and len(buy_positions) <= 3
            is_massive_loss = total_buy_loss < -300 or total_sell_loss < -300
            
            print(f"📊 POSITION ANALYSIS:")
            print(f"   📈 BUY: {len(buy_positions)} positions ({len(profitable_buys)} profit, {len(losing_buys)} loss)")
            print(f"   📉 SELL: {len(sell_positions)} positions ({len(profitable_sells)} profit, {len(losing_sells)} loss)")
            print(f"   💰 BUY P&L: ${sum([p.get('profit', 0) for p in buy_positions]):.1f}")
            print(f"   💰 SELL P&L: ${sum([p.get('profit', 0) for p in sell_positions]):.1f}")
            print(f"   🚨 Critical: Buy Heavy={is_buy_heavy}, Sell Heavy={is_sell_heavy}, Massive Loss={is_massive_loss}")
            
            opportunities = []
            
            # ===================== EMERGENCY PROTOCOLS =====================
            
            if is_emergency or (is_buy_heavy and is_massive_loss):
                print(f"\n🚨 EMERGENCY PROTOCOL ACTIVATED")
                
                # 🛡️ Emergency Hedge Strategy
                if is_buy_heavy and total_buy_loss < -200:
                    hedge_size = min(total_buy_volume * 0.6, 1.0)  # Max 1.0 lot hedge
                    expected_protection = abs(total_buy_loss) * 0.7  # คาดว่าป้องกันได้ 70%
                    
                    opportunities.append({
                        'strategy': 'EMERGENCY_HEDGE',
                        'type': 'CRITICAL_PROTECTION',
                        'action': 'PLACE_SELL_HEDGE',
                        'hedge_size': hedge_size,
                        'current_price': current_price,
                        'expected_profit': expected_protection,
                        'margin_impact': -(hedge_size * 1000),  # เพิ่ม margin requirement
                        'confidence': 95,
                        'reasoning': f'Emergency SELL hedge {hedge_size:.2f} lot to protect ${abs(total_buy_loss):.0f} BUY losses',
                        'urgency': 10,
                        'emergency': True
                    })
                    print(f"   🛡️ EMERGENCY HEDGE: SELL {hedge_size:.2f} lot at ${current_price:.2f}")
                
                elif is_sell_heavy and total_sell_loss < -200:
                    hedge_size = min(total_sell_volume * 0.6, 1.0)
                    expected_protection = abs(total_sell_loss) * 0.7
                    
                    opportunities.append({
                        'strategy': 'EMERGENCY_HEDGE',
                        'type': 'CRITICAL_PROTECTION',
                        'action': 'PLACE_BUY_HEDGE',
                        'hedge_size': hedge_size,
                        'current_price': current_price,
                        'expected_profit': expected_protection,
                        'margin_impact': -(hedge_size * 1000),
                        'confidence': 95,
                        'reasoning': f'Emergency BUY hedge {hedge_size:.2f} lot to protect ${abs(total_sell_loss):.0f} SELL losses',
                        'urgency': 10,
                        'emergency': True
                    })
                    print(f"   🛡️ EMERGENCY HEDGE: BUY {hedge_size:.2f} lot at ${current_price:.2f}")
            
            # ===================== PRO TRADER STRATEGIES =====================
            
            # 🎯 Strategy 1: Margin Relief (สำคัญที่สุดเมื่อ margin ต่ำ)
            if is_margin_critical:
                print(f"\n🆘 MARGIN RELIEF PROTOCOL (Level: {margin_level:.1f}%)")
                
                # หาไม้ที่คืน margin เยอะ + ขาดทุนน้อย
                all_positions_with_margin = []
                for p in positions:
                    volume = p.get('volume', 0.01)
                    profit = p.get('profit', 0)
                    margin_return = volume * 1000  # ประมาณการ margin ที่จะคืน
                    priority_score = margin_return - abs(profit) if profit < 0 else margin_return + profit
                    
                    all_positions_with_margin.append({
                        'ticket': p.get('ticket'),
                        'direction': p.get('direction'),
                        'profit': profit,
                        'margin_return': margin_return,
                        'priority_score': priority_score,
                        'original': p
                    })
                
                # เรียงตาม priority score (คืน margin เยอะ + ขาดทุนน้อย)
                all_positions_with_margin.sort(key=lambda x: x['priority_score'], reverse=True)
                
                for pos in all_positions_with_margin[:5]:  # เอา 5 ไม้แรก
                    if pos['profit'] > -30:  # ขาดทุนไม่เกิน $30
                        opportunities.append({
                            'strategy': 'MARGIN_RELIEF',
                            'type': 'EMERGENCY_MARGIN_RECOVERY',
                            'positions': [pos['ticket']],
                            'expected_profit': pos['profit'],
                            'margin_return': pos['margin_return'],
                            'confidence': 90,
                            'reasoning': f"Margin relief: Free ${pos['margin_return']:.0f} margin (${pos['profit']:.1f} P&L)",
                            'urgency': 9,
                            'emergency': True
                        })
                        print(f"   🆘 Close #{pos['ticket']}: Free M${pos['margin_return']:.0f} (P&L: ${pos['profit']:.1f})")
            
            # 🎯 Strategy 2: Smart Scalping Recovery
            if floating_pnl < -100:
                print(f"\n⚡ SCALPING RECOVERY PROTOCOL (Floating: ${floating_pnl:.2f})")
                
                # สร้าง scalping orders เล็กๆ
                scalp_size = 0.01
                scalp_distance = 10  # 10 points
                
                # ทั้ง 2 ทิศทาง
                for direction in ['BUY', 'SELL']:
                    price_offset = scalp_distance if direction == 'SELL' else -scalp_distance
                    scalp_price = current_price + price_offset
                    
                    opportunities.append({
                        'strategy': 'SCALPING_RECOVERY',
                        'type': 'MICRO_PROFIT_HUNT',
                        'action': f'PLACE_{direction}',
                        'lot_size': scalp_size,
                        'price': scalp_price,
                        'expected_profit': 5,  # เป้า $5 ต่อรอบ
                        'margin_impact': -(scalp_size * 1000),
                        'confidence': 75,
                        'reasoning': f'Scalp {direction} {scalp_size} lot for quick ${5} profit',
                        'urgency': 5
                    })
                    print(f"   ⚡ Scalp {direction}: {scalp_size} lot @ ${scalp_price:.2f} → Target $5")
            
            # 🎯 Strategy 3: Professional Hedge Pairs (แบบนักเทรดมืออาชีพ)
            if len(profitable_buys) > 0 and len(losing_sells) > 0:
                print(f"\n🤝 PRO HEDGE PAIRS - BUY Profit + SELL Loss")
                
                for buy_pos in profitable_buys[:3]:
                    for sell_pos in losing_sells[:3]:
                        buy_profit = buy_pos.get('profit', 0)
                        sell_loss = sell_pos.get('profit', 0)
                        net_profit = buy_profit + sell_loss
                        
                        # คำนวณ margin impact
                        buy_volume = buy_pos.get('volume', 0.01)
                        sell_volume = sell_pos.get('volume', 0.01)
                        margin_freed = (buy_volume + sell_volume) * 1000
                        
                        if net_profit > 2:  # กำไรสุทธิ $2+
                            opportunities.append({
                                'strategy': 'PRO_HEDGE_PAIR',
                                'type': 'BALANCED_CLOSING',
                                'positions': [buy_pos['ticket'], sell_pos['ticket']],
                                'expected_profit': net_profit,
                                'margin_return': margin_freed,
                                'confidence': 85,
                                'reasoning': f'Pro pair: BUY +${buy_profit:.1f} + SELL ${sell_loss:.1f} = ${net_profit:.1f} +M${margin_freed:.0f}',
                                'urgency': 3,
                                'pair_waiting_approved': True
                            })
                            print(f"   🤝 Pair: BUY #{buy_pos['ticket']} +${buy_profit:.1f} + SELL #{sell_pos['ticket']} ${sell_loss:.1f}")
            
            # 🎯 Strategy 4: Time-Based Recovery (ตามเวลาเทรด)
            current_hour = datetime.now().hour
            is_peak_time = current_hour in [8, 9, 13, 14, 21, 22]  # London, NY open
            
            if is_peak_time and floating_pnl < -50:
                print(f"\n⏰ PEAK TIME RECOVERY (Hour: {current_hour})")
                
                # ใช้ volatility สูงช่วง peak time
                for pos in positions:
                    profit = pos.get('profit', 0)
                    if -20 < profit < -5:  # ขาดทุนปานกลาง
                        opportunities.append({
                            'strategy': 'PEAK_TIME_RECOVERY',
                            'type': 'VOLATILITY_RECOVERY',
                            'positions': [pos['ticket']],
                            'expected_profit': profit,
                            'confidence': 70,
                            'reasoning': f'Peak time recovery: ${profit:.1f} during high volatility',
                            'urgency': 4
                        })
                        print(f"   ⏰ Peak recovery: #{pos['ticket']} ${profit:.1f}")
            
            # 🎯 Strategy 5: Portfolio Rebalancing (ปรับสมดุลแบบเทพ)
            portfolio_imbalance = abs(len(buy_positions) - len(sell_positions))
            if portfolio_imbalance >= 10:  # ไม่สมดุลมาก
                print(f"\n⚖️ PORTFOLIO REBALANCING (Imbalance: {portfolio_imbalance})")
                
                majority_side = 'BUY' if len(buy_positions) > len(sell_positions) else 'SELL'
                majority_positions = buy_positions if majority_side == 'BUY' else sell_positions
                
                # หาไม้ที่ขาดทุนน้อยที่สุดในฝั่งที่เยอะ
                majority_positions.sort(key=lambda x: x.get('profit', 0), reverse=True)
                
                for pos in majority_positions[:3]:
                    profit = pos.get('profit', 0)
                    if profit > -25:  # ขาดทุนไม่เกิน $25
                        opportunities.append({
                            'strategy': 'PORTFOLIO_REBALANCE',
                            'type': 'IMBALANCE_CORRECTION',
                            'positions': [pos['ticket']],
                            'expected_profit': profit,
                            'confidence': 80,
                            'reasoning': f'Rebalance: Reduce {majority_side} excess (${profit:.1f})',
                            'urgency': 6
                        })
                        print(f"   ⚖️ Rebalance: Close {majority_side} #{pos['ticket']} ${profit:.1f}")
            
            # 🎯 Strategy 6: Smart Profit Taking (กำไรแบบฉลาด)
            if len(profitable_buys) > 0 and len(profitable_sells) > 0:
                print(f"\n💎 SMART PROFIT TAKING")
                
                # Perfect pairs (กำไรทั้งคู่)
                for buy_pos in profitable_buys[:2]:
                    for sell_pos in profitable_sells[:2]:
                        total_profit = buy_pos.get('profit', 0) + sell_pos.get('profit', 0)
                        
                        if total_profit > 8:  # กำไรรวม $8+
                            buy_volume = buy_pos.get('volume', 0.01)
                            sell_volume = sell_pos.get('volume', 0.01)
                            margin_freed = (buy_volume + sell_volume) * 1000
                            
                            opportunities.append({
                                'strategy': 'PERFECT_PROFIT_PAIR',
                                'type': 'SMART_PROFIT_TAKING',
                                'positions': [buy_pos['ticket'], sell_pos['ticket']],
                                'expected_profit': total_profit,
                                'margin_return': margin_freed,
                                'confidence': 95,
                                'reasoning': f'Perfect pair: ${total_profit:.1f} profit +M${margin_freed:.0f}',
                                'urgency': 1,
                                'pair_waiting_approved': True
                            })
                            print(f"   💎 Perfect: BUY #{buy_pos['ticket']} + SELL #{sell_pos['ticket']} = ${total_profit:.1f}")
            
            # ===================== PRIORITIZE & FILTER =====================
            
            # เรียงตามความสำคัญ (Emergency > Margin > Profit)
            opportunities.sort(key=lambda x: (
                x.get('emergency', False),           # Emergency ก่อน
                -x.get('urgency', 5),               # Urgency สูงก่อน
                -x.get('expected_profit', 0),       # กำไรสูงก่อน
                x.get('margin_return', 0)           # คืน margin เยอะก่อน
            ), reverse=True)
            
            # Filter ตามสถานการณ์
            if is_emergency:
                opportunities = [o for o in opportunities if o.get('emergency', False) or o.get('urgency', 0) >= 8]
            elif is_margin_critical:
                opportunities = [o for o in opportunities if o.get('urgency', 0) >= 6]
            
            print(f"\n🧠 AI PRO RESULTS: {len(opportunities)} opportunities")
            for i, opp in enumerate(opportunities[:8]):
                margin_text = f" +M${opp.get('margin_return', 0):.0f}" if opp.get('margin_return', 0) > 0 else ""
                emergency_text = " 🚨" if opp.get('emergency', False) else ""
                print(f"   {i+1}. {opp['strategy']}: ${opp.get('expected_profit', 0):.1f}{margin_text} (U:{opp.get('urgency', 0)}){emergency_text}")
                print(f"      └─ {opp['reasoning']}")
            
            return opportunities[:10]  # คืน 10 โอกาสดีที่สุด
            
        except Exception as e:
            print(f"❌ AI Pro Trader error: {e}")
            import traceback
            traceback.print_exc()
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

    def check_and_handle_crisis(self):
        """🚨 แก้ไข Crisis check - ไม่เช็คบ่อยเกินไป"""
        try:
            current_time = time.time()
            
            # เช็คทุก 60 วินาที (ไม่บ่อย)
            if hasattr(self, 'last_crisis_check'):
                if current_time - self.last_crisis_check < 60:
                    return
            
            self.last_crisis_check = current_time
            
            # เช็คแค่พื้นฐาน
            positions = list(self.active_positions.values()) if hasattr(self, 'active_positions') else []
            
            if len(positions) == 0:
                self.crisis_mode = False
                return
            
            # นับ BUY/SELL
            buy_count = len([p for p in positions if p.get('direction') == 'BUY'])
            sell_count = len([p for p in positions if p.get('direction') == 'SELL'])
            
            # เช็คแค่ imbalance รุนแรง
            imbalance_ratio = max(buy_count, sell_count) / max(min(buy_count, sell_count), 1)
            
            if imbalance_ratio > 5:  # มากเกิน 5 เท่า
                print(f"🚨 Portfolio imbalance: {buy_count} BUY, {sell_count} SELL")
                self.crisis_mode = True
                
                # ทำ emergency hedge แค่ครั้งเดียว
                if not hasattr(self, '_emergency_hedge_done'):
                    hedge_size = 0.1  # ขนาดคงที่
                    success = self.execute_emergency_hedge(hedge_size)
                    if success:
                        self._emergency_hedge_done = True
            else:
                self.crisis_mode = False
                # รีเซ็ต flag
                if hasattr(self, '_emergency_hedge_done'):
                    delattr(self, '_emergency_hedge_done')
            
        except Exception as e:
            # ไม่ print error
            pass

    def execute_emergency_hedge(self, hedge_size: float):
        """🛡️ แก้ไข Emergency hedge - หยุด recursion และ log spam"""
        try:
            # ป้องกัน recursion
            if hasattr(self, '_emergency_hedge_running'):
                print("🚫 Emergency hedge already running")
                return False
            
            self._emergency_hedge_running = True
            
            try:
                current_price = self.get_current_price()
                if not current_price:
                    print("❌ Cannot get current price")
                    return False
                
                # Validate hedge size (ไม่ spam log)
                if hedge_size < 0.01 or hedge_size > 1.0:
                    print(f"❌ Invalid hedge size: {hedge_size}")
                    return False
                
                # ตรวจสอบ portfolio direction
                buy_count = len([p for p in self.active_positions.values() if p.get('direction') == 'BUY'])
                sell_count = len([p for p in self.active_positions.values() if p.get('direction') == 'SELL'])
                
                if buy_count > sell_count:
                    hedge_direction = 'SELL'
                else:
                    hedge_direction = 'BUY'
                
                print(f"🛡️ Emergency hedge: {hedge_direction} {hedge_size}")
                
                # ใช้ place_enhanced_order (ไม่เรียกตัวเอง)
                success = self.place_enhanced_order(current_price, hedge_direction, 'EMERGENCY_HEDGE', hedge_size)
                
                if success:
                    print(f"✅ Emergency hedge completed")
                else:
                    print(f"❌ Emergency hedge failed")
                
                return success
                
            finally:
                # ปล่อย lock
                if hasattr(self, '_emergency_hedge_running'):
                    delattr(self, '_emergency_hedge_running')
                
        except Exception as e:
            print(f"❌ Emergency hedge error: {e}")
            if hasattr(self, '_emergency_hedge_running'):
                delattr(self, '_emergency_hedge_running')
            return False

    def close_priority_positions(self, priority_tickets: List[int]):
        """🎯 ปิดไม้ priority ในสถานการณ์วิกฤต"""
        try:
            print(f"🎯 Closing {len(priority_tickets)} priority positions for crisis management")
            
            for ticket in priority_tickets:
                if ticket in self.active_positions:
                    print(f"   🎯 Closing priority position #{ticket}")
                    success = self.close_position_by_ticket(ticket)
                    if success:
                        print(f"   ✅ Priority position #{ticket} closed")
                    else:
                        print(f"   ❌ Failed to close priority position #{ticket}")
                    time.sleep(0.2)
                    
        except Exception as e:
            print(f"❌ Priority close error: {e}")
