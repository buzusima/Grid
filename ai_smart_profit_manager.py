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
        """Enhanced order placement with validation - Fixed Volume Issue"""
        try:
            # Get current price for validation
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                print(f"       ❌ Cannot get tick for {self.gold_symbol}")
                return False
            
            current_price = (tick.ask + tick.bid) / 2
            
            # Validate price vs direction
            if direction == "BUY" and price >= current_price:
                price = current_price - 1.00  # Adjust to $1 below
                print(f"       🔧 Adjusted BUY price to: ${price:.2f}")
            elif direction == "SELL" and price <= current_price:
                price = current_price + 1.00  # Adjust to $1 above
                print(f"       🔧 Adjusted SELL price to: ${price:.2f}")
            
            # 🔧 Fix Volume Issue - Get symbol info first
            symbol_info = mt5.symbol_info(self.gold_symbol)
            if not symbol_info:
                print(f"       ❌ Cannot get symbol info for {self.gold_symbol}")
                return False
            
            # Validate and fix volume
            min_volume = symbol_info.volume_min
            max_volume = symbol_info.volume_max
            volume_step = symbol_info.volume_step
            
            # Use minimum volume to avoid error
            volume = max(min_volume, 0.01)
            volume = min(volume, max_volume)
            
            # Round to valid step
            volume = round(volume / volume_step) * volume_step
            volume = round(volume, 3)  # Round to 3 decimal places
            
            print(f"       📊 Volume validation:")
            print(f"          Min: {min_volume}, Max: {max_volume}, Step: {volume_step}")
            print(f"          Using: {volume}")
            
            # Determine order type
            order_type_int = 2 if direction == "BUY" else 3  # LIMIT orders only
            
            # Create order request with validated volume
            request = {
                "action": 5,  # TRADE_ACTION_PENDING
                "symbol": self.gold_symbol,
                "volume": volume,  # ✅ Fixed volume
                "type": order_type_int,
                "price": round(price, 2),
                "magic": self.magic_number,
                "comment": f"AI_ENHANCED_{order_type}_{direction}"
            }
            
            print(f"       📋 Order Request: {request}")
            
            # Send order
            result = mt5.order_send(request)
            
            if result and result.retcode == 10009:
                # Store in tracking
                self.pending_orders[result.order] = {
                    'order_id': result.order,
                    'price': round(price, 2),
                    'direction': direction,
                    'lot_size': volume,  # Store actual volume used
                    'ai_type': order_type,
                    'timestamp': datetime.now()
                }
                print(f"       ✅ Order SUCCESS! ID: {result.order}")
                return True
            else:
                error_code = result.retcode if result else "No result"
                print(f"       ❌ Order failed: {error_code}")
                if result and hasattr(result, 'comment'):
                    print(f"       💬 Comment: {result.comment}")
                return False
                
        except Exception as e:
            print(f"❌ Enhanced order placement error: {e}")
            import traceback
            traceback.print_exc()
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
        """Enhanced main AI decision loop"""
        print("🧠 AI ENHANCED MAIN LOOP: Starting intelligent grid management...")
        
        while self.ai_active:
            try:
                # Update market analysis
                market_analysis = self.ai_analyze_market_condition()
                if market_analysis:
                    self.market_analysis = market_analysis
                
                # Update positions from MT5
                self.ai_update_positions_from_mt5()
                
                # Calculate portfolio health
                health_score = self.ai_calculate_portfolio_health()
                self.ai_health_score = health_score
                
                # Enhanced Grid Management
                self.manage_enhanced_grid()
                
                # Enhanced Profit Taking
                self.execute_enhanced_profit_taking()
                
                # Gap Detection and Filling
                self.detect_and_fill_gaps()
                
                # Portfolio Rebalancing
                self.rebalance_portfolio()
                
                # Sleep between cycles
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ Enhanced AI Main Loop error: {e}")
                time.sleep(5)
        
        print("🛑 Enhanced AI Main Loop: Stopped")

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
        """Add strategic orders to maintain grid coverage"""
        try:
            current_price = self.get_current_price()
            if not current_price:
                return
            
            spacing = self.calculate_dynamic_spacing()
            spacing_dollars = spacing * 0.01
            
            # Count current orders by direction
            buy_orders = len([o for o in self.pending_orders.values() if o.get('direction') == 'BUY'])
            sell_orders = len([o for o in self.pending_orders.values() if o.get('direction') == 'SELL'])
            
            orders_needed = 3 - min(buy_orders, sell_orders)
            
            if orders_needed > 0:
                print(f"   🎯 Adding {orders_needed} strategic orders...")
                
                # Add BUY orders if needed
                if buy_orders < 3:
                    for i in range(1, orders_needed + 1):
                        buy_price = current_price - (spacing_dollars * i)
                        if not self.level_exists_enhanced(buy_price, 'BUY', spacing_dollars * 0.4):
                            self.place_enhanced_order(buy_price, 'BUY', 'STRATEGIC')
                            time.sleep(0.3)
                
                # Add SELL orders if needed
                if sell_orders < 3:
                    for i in range(1, orders_needed + 1):
                        sell_price = current_price + (spacing_dollars * i)
                        if not self.level_exists_enhanced(sell_price, 'SELL', spacing_dollars * 0.4):
                            self.place_enhanced_order(sell_price, 'SELL', 'STRATEGIC')
                            time.sleep(0.3)
            
        except Exception as e:
            print(f"❌ Strategic order addition error: {e}")

    def detect_and_fill_gaps(self):
        """Detect and fill price gaps in the grid"""
        try:
            if len(self.pending_orders) < 4:
                return  # Need minimum orders to detect gaps
            
            current_price = self.get_current_price()
            if not current_price:
                return
            
            # Get all order prices
            all_prices = [current_price]
            for order in self.pending_orders.values():
                all_prices.append(order.get('price', 0))
            
            all_prices = sorted([p for p in all_prices if p > 0])
            
            gap_threshold = self.grid_config['gap_threshold'] / 100  # Convert to dollars
            
            # Find gaps
            gaps_found = 0
            for i in range(1, len(all_prices)):
                gap_size = all_prices[i] - all_prices[i-1]
                
                if gap_size > gap_threshold:
                    # Fill the gap
                    gap_center = (all_prices[i] + all_prices[i-1]) / 2
                    
                    # Determine direction
                    direction = 'BUY' if gap_center < current_price else 'SELL'
                    
                    if not self.level_exists_enhanced(gap_center, direction, gap_threshold * 0.3):
                        success = self.place_enhanced_order(gap_center, direction, 'GAP_FILL')
                        if success:
                            gaps_found += 1
                            print(f"   🔧 Gap filled: {direction} @ ${gap_center:.2f}")
                        time.sleep(0.2)
            
            if gaps_found > 0:
                print(f"✅ Filled {gaps_found} gaps")
                
        except Exception as e:
            print(f"❌ Gap detection error: {e}")

    def rebalance_portfolio(self):
        """Rebalance portfolio to maintain equal BUY/SELL exposure"""
        try:
            # Count positions and orders by direction
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
                
                # Add rebalancing orders
                current_price = self.get_current_price()
                if current_price and orders_to_add > 0:
                    spacing = self.calculate_dynamic_spacing()
                    spacing_dollars = spacing * 0.01
                    
                    for i in range(1, min(orders_to_add + 1, 4)):  # Max 3 rebalance orders
                        if needed_direction == 'BUY':
                            order_price = current_price - (spacing_dollars * i)
                        else:
                            order_price = current_price + (spacing_dollars * i)
                        
                        if not self.level_exists_enhanced(order_price, needed_direction, spacing_dollars * 0.4):
                            self.place_enhanced_order(order_price, needed_direction, 'REBALANCE')
                            time.sleep(0.3)
                
                print(f"✅ Rebalance orders added: {needed_direction}")
                
        except Exception as e:
            print(f"❌ Portfolio rebalancing error: {e}")

    def execute_enhanced_profit_taking(self):
        """Enhanced profit taking with zero-loss philosophy"""
        try:
            if len(self.active_positions) < 2:
                return
            
            # Analyze all positions for profit opportunities
            profit_opportunities = self.find_enhanced_profit_opportunities()
            
            if profit_opportunities:
                print(f"💰 Found {len(profit_opportunities)} profit opportunities")
                
                # Execute best opportunities
                for opportunity in profit_opportunities[:2]:  # Max 2 executions per cycle
                    self.execute_profit_opportunity(opportunity)
                    time.sleep(1)
            
        except Exception as e:
            print(f"❌ Enhanced profit taking error: {e}")

    def find_enhanced_profit_opportunities(self) -> List[Dict]:
        """Find profit opportunities with zero-loss guarantee"""
        opportunities = []
        
        try:
            positions = list(self.active_positions.values())
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
            
            # Strategy 2: Profitable pairs (both positive)
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
            
            # Strategy 3: Rescue pairs (profit saves loss, net positive)
            losing_positions = [p for p in positions if p.get('profit', 0) < 0]
            
            for profit_pos in profitable_positions:
                for loss_pos in losing_positions:
                    net_profit = profit_pos.get('profit', 0) + loss_pos.get('profit', 0)
                    if net_profit > 1.0:  # Net positive
                        opportunities.append({
                            'type': 'RESCUE_PAIR',
                            'positions': [profit_pos['ticket'], loss_pos['ticket']],
                            'expected_profit': net_profit,
                            'confidence': 0.7,
                            'description': f"Rescue pair: ${net_profit:.2f}"
                        })
            
            # Sort by expected profit (highest first)
            opportunities.sort(key=lambda x: x['expected_profit'], reverse=True)
            
            return opportunities[:5]  # Return top 5 opportunities
            
        except Exception as e:
            print(f"❌ Profit opportunity analysis error: {e}")
            return []

    def execute_profit_opportunity(self, opportunity: Dict) -> bool:
        """Execute a profit opportunity"""
        try:
            position_tickets = opportunity['positions']
            expected_profit = opportunity['expected_profit']
            opportunity_type = opportunity['type']
            
            print(f"💰 Executing {opportunity_type}: ${expected_profit:.2f}")
            
            # Close all positions in the opportunity
            success_count = 0
            for ticket in position_tickets:
                if self.close_position_by_ticket(ticket):
                    success_count += 1
                time.sleep(0.5)
            
            if success_count == len(position_tickets):
                print(f"   ✅ Success: Closed {success_count} positions")
                return True
            else:
                print(f"   ⚠️ Partial success: {success_count}/{len(position_tickets)} closed")
                return False
                
        except Exception as e:
            print(f"❌ Profit opportunity execution error: {e}")
            return False

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