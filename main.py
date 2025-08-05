"""
AI Gold Grid Trading System with 20,000+ Points Survivability
Main GUI Controller - main.py
Created for MetaTrader5 Gold Trading with Auto Money Management
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
import os
import sys

# Import custom modules
try:
    from mt5_auto_connector import MT5AutoConnector
    from ai_gold_grid import AIGoldGrid
    from survivability_engine import SurvivabilityEngine, TradingMode
    from ai_money_manager import AIMoneyManager
except ImportError as e:
    print(f"Module import error: {e}")
    print("Please ensure all required modules are in the same directory")

class AIGoldTradingGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_main_window()
        self.load_config()
        self.init_components()
        self.create_gui()
        self.setup_status_monitoring()
        self.current_trading_mode = TradingMode.BALANCED

    def setup_main_window(self):
        """Setup main window properties"""
        self.root.title("🏆 AI Gold Grid Trading System - 20,000+ Points Survivability")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1a1a2e')
        
        # Center window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def load_config(self):
        """Load configuration from config.json with trading mode support"""
        default_config = {
            "target_survivability": 20000,
            "default_trading_mode": "BALANCED",  # ⭐ เพิ่ม
            "safety_ratio": 0.6,
            "emergency_stop_percentage": 50,
            "daily_loss_limit_percentage": 10,
            "hedge_triggers": [0.15, 0.30, 0.45, 0.60],
            "hedge_multipliers": [0.5, 1.0, 1.5, 2.0],
            "log_level": "INFO",
            "auto_connect_mt5": True,
            "gold_symbols": ["XAUUSD", "GOLD", "XAU/USD", "XAUUSD.cmd", "GOLD#"],
            # ⭐ เพิ่มส่วนนี้
            "trading_modes": {
                "SAFE": {
                    "description": "Maximum protection with 20,000 points survivability",
                    "recommended_for": "Conservative traders, large accounts"
                },
                "BALANCED": {
                    "description": "Good balance with 10,000 points survivability", 
                    "recommended_for": "Most traders, medium accounts"
                },
                "AGGRESSIVE": {
                    "description": "Higher risk/reward with 8,000 points survivability",
                    "recommended_for": "Experienced traders, fast growth"
                },
                "TURBO": {
                    "description": "Maximum speed with 5,000 points survivability",
                    "recommended_for": "Expert traders only, high risk tolerance"
                }
            }
        }
        
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = default_config
                self.save_config()
                
            # ⭐ เพิ่มส่วนนี้ - Set default trading mode from config
            default_mode_name = self.config.get('default_trading_mode', 'BALANCED')
            try:
                self.current_trading_mode = TradingMode(default_mode_name)
            except ValueError:
                self.current_trading_mode = TradingMode.BALANCED  # Fallback
                
        except Exception as e:
            print(f"Config load error: {e}")
            self.config = default_config
            self.current_trading_mode = TradingMode.BALANCED  # Fallback

    def save_config(self):
        """Save configuration to config.json"""
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Config save error: {e}")
            
    def init_components(self):
        """Initialize all system components"""
        try:
            self.mt5_connector = MT5AutoConnector()
            self.survivability_engine = SurvivabilityEngine(self.config)
            self.money_manager = AIMoneyManager(self.config)
            self.grid_trader = None  # Will be initialized after MT5 connection
            
            # System status
            self.is_connected = False
            self.is_trading = False
            self.account_info = {}
            self.current_calculations = {}
            
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to initialize components: {e}")
            
    def create_gui(self):
        """Create main GUI interface"""
        # Create main frame
        main_frame = tk.Frame(self.root, bg='#1a1a2e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create sections
        self.create_header_section(main_frame)
        self.create_connection_section(main_frame)
        self.create_survivability_section(main_frame)
        self.create_hedge_section(main_frame)
        self.create_control_section(main_frame)
        self.create_log_section(main_frame)
        
    def create_header_section(self, parent):
        """Create header with system title and status"""
        header_frame = tk.Frame(parent, bg='#16213e', relief='raised', bd=1)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        title_label = tk.Label(
            header_frame,
            text="🏆 AI Gold Grid Trading System",
            font=('Arial', 14, 'bold'),
            fg='#ffd700',
            bg='#16213e'
        )
        title_label.pack(pady=5)
        
        subtitle_label = tk.Label(
            header_frame,
            text="Survivability Calculator & Auto Money Management",
            font=('Arial', 10),
            fg='#ffffff',
            bg='#16213e'
        )
        subtitle_label.pack(pady=(0, 5))
        
    def create_connection_section(self, parent):
        """Create MT5 connection section"""
        conn_frame = tk.LabelFrame(
            parent,
            text="🔗 MT5 Auto Connection",
            font=('Arial', 10, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        conn_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Connection status
        status_frame = tk.Frame(conn_frame, bg='#16213e')
        status_frame.pack(fill=tk.X, padx=5, pady=3)
        
        tk.Label(status_frame, text="📡 Status:", font=('Arial', 10, 'bold'), 
                fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)
        
        self.connection_status = tk.Label(
            status_frame, 
            text="❌ Disconnected", 
            font=('Arial', 10), 
            fg='#ff6b6b', 
            bg='#16213e'
        )
        self.connection_status.pack(side=tk.LEFT, padx=(10, 0))
        
        # Account info
        account_frame = tk.Frame(conn_frame, bg='#16213e')
        account_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.account_label = tk.Label(
            account_frame,
            text="💰 Account: Not Connected",
            font=('Arial', 10),
            fg='#ffffff',
            bg='#16213e'
        )
        self.account_label.pack(side=tk.LEFT)
        
        # Connection button
        self.connect_btn = tk.Button(
            conn_frame,
            text="🔌 Connect to MT5",
            font=('Arial', 10, 'bold'),
            bg='#4ecdc4',
            fg='#1a1a2e',
            relief='raised',
            bd=3,
            command=self.connect_mt5
        )
        self.connect_btn.pack(pady=10)
        
    def create_survivability_section(self, parent):
        """Create survivability calculation display with Smart Grid focus"""
        surv_frame = tk.LabelFrame(
            parent,
            text="🚀 AI Smart Grid Calculator",  # เปลี่ยนชื่อ
            font=('Arial', 12, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        surv_frame.pack(fill=tk.X, pady=(0, 10))
        
        # ⭐ Trading Mode Selection
        mode_frame = tk.Frame(surv_frame, bg='#16213e')
        mode_frame.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        tk.Label(mode_frame, text="🎯 Trading Mode:", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#16213e').pack(side=tk.LEFT)
        
        # Mode selection variable
        self.mode_var = tk.StringVar(value="BALANCED")
        
        # Mode selection combobox
        mode_options = ["SAFE", "BALANCED", "AGGRESSIVE", "TURBO"]
        self.mode_combo = ttk.Combobox(
            mode_frame, 
            textvariable=self.mode_var, 
            values=mode_options, 
            state="readonly", 
            width=12,
            font=('Arial', 10)
        )
        self.mode_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Mode description label
        self.mode_desc_label = tk.Label(
            mode_frame,
            text="⚖️ Good balance between speed and safety",
            font=('Arial', 10),
            fg='#adb5bd',
            bg='#16213e'
        )
        self.mode_desc_label.pack(side=tk.LEFT, padx=(15, 0))
        
        # Bind mode change event
        self.mode_combo.bind('<<ComboboxSelected>>', self.on_mode_change)
        
        # Target survivability display
        target_frame = tk.Frame(surv_frame, bg='#16213e')
        target_frame.pack(fill=tk.X, padx=15, pady=5)
        
        self.target_surv_label = tk.Label(
            target_frame,
            text="🎯 Target: 10,000 points",
            font=('Arial', 11, 'bold'),
            fg='#ffd43b',
            bg='#16213e'
        )
        self.target_surv_label.pack(side=tk.LEFT)
        
        self.risk_level_label = tk.Label(
            target_frame,
            text="⚠️ Risk: Medium",
            font=('Arial', 11),
            fg='#ffd43b',
            bg='#16213e'
        )
        self.risk_level_label.pack(side=tk.RIGHT)
        
        # Main content area - 3 columns layout
        content_frame = tk.Frame(surv_frame, bg='#16213e')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Left column - Account & Basic Parameters (40%)
        left_col = tk.Frame(content_frame, bg='#16213e')
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(left_col, text="💰 Account Information:", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#16213e').pack(anchor='w')
        
        self.balance_label = tk.Label(left_col, text="💰 Balance: $0", 
                                    font=('Arial', 10), fg='#ffffff', bg='#16213e')
        self.balance_label.pack(anchor='w', pady=(5, 2))
        
        self.base_lot_label = tk.Label(left_col, text="🎯 Base Lot: 0.00", 
                                    font=('Arial', 10), fg='#ffffff', bg='#16213e')
        self.base_lot_label.pack(anchor='w', pady=2)
        
        self.safety_margin_label = tk.Label(left_col, text="💪 Safety Margin: $0", 
                                        font=('Arial', 10), fg='#ffffff', bg='#16213e')
        self.safety_margin_label.pack(anchor='w', pady=2)
        
        # Middle column - Smart Grid Parameters (35%)
        middle_col = tk.Frame(content_frame, bg='#16213e')
        middle_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        tk.Label(middle_col, text="🚀 Smart Grid Setup:", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#16213e').pack(anchor='w')
        
        self.grid_spacing_label = tk.Label(middle_col, text="📏 Grid Spacing: 0 points", 
                                        font=('Arial', 10), fg='#ffffff', bg='#16213e')
        self.grid_spacing_label.pack(anchor='w', pady=(5, 2))
        
        self.max_levels_label = tk.Label(middle_col, text="📈 Max Levels: 0", 
                                        font=('Arial', 10), fg='#ffffff', bg='#16213e')
        self.max_levels_label.pack(anchor='w', pady=2)
        
        self.survivability_label = tk.Label(middle_col, text="🛡️ Survivability: 0 points", 
                                        font=('Arial', 11, 'bold'), fg='#51cf66', bg='#16213e')
        self.survivability_label.pack(anchor='w', pady=2)
        
        # Right column - Smart Grid Benefits (25%)
        right_col = tk.Frame(content_frame, bg='#16213e')
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        tk.Label(right_col, text="✨ Smart Grid Benefits:", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#16213e').pack(anchor='w')
        
        # Benefits list
        benefits = [
            "💸 No hedge costs",
            "⚖️ Auto-balancing", 
            "⚡ 3x faster profits",
            "🎯 Tighter grid spacing",
            "🔄 Smart reposition"
        ]
        
        for i, benefit in enumerate(benefits):
            benefit_label = tk.Label(right_col, text=benefit, 
                                font=('Arial', 9), fg='#51cf66', bg='#16213e')
            benefit_label.pack(anchor='w', pady=(5 if i == 0 else 1, 1))
        
        # Separator line
        separator = tk.Frame(surv_frame, height=2, bg='#4ecdc4')
        separator.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        # Status summary row
        status_frame = tk.Frame(surv_frame, bg='#16213e')
        status_frame.pack(fill=tk.X, padx=15, pady=5)
        
        # Smart Grid status indicator
        self.smart_grid_status = tk.Label(
            status_frame,
            text="🚀 Smart Grid: Ready to calculate",
            font=('Arial', 10, 'bold'),
            fg='#4ecdc4',
            bg='#16213e'
        )
        self.smart_grid_status.pack(side=tk.LEFT)
        
        # Capital efficiency indicator  
        self.efficiency_indicator = tk.Label(
            status_frame,
            text="📊 Efficiency: Calculating...",
            font=('Arial', 10),
            fg='#adb5bd',
            bg='#16213e'
        )
        self.efficiency_indicator.pack(side=tk.RIGHT)
        
        # Calculate button - ปรับให้สวยขึ้น
        button_frame = tk.Frame(surv_frame, bg='#16213e')
        button_frame.pack(fill=tk.X, pady=(10, 15))
        
        calc_btn = tk.Button(
            button_frame,
            text="🔄 Calculate Smart Grid",  # เปลี่ยนข้อความ
            font=('Arial', 12, 'bold'),
            bg='#4ecdc4',  # เปลี่ยนสี
            fg='#1a1a2e',
            relief='raised',
            bd=3,
            width=25,
            command=self.calculate_survivability
        )
        calc_btn.pack()

    def on_mode_change(self, event=None):
        """Handle trading mode change"""
        try:
            mode_name = self.mode_var.get()
            self.current_trading_mode = TradingMode(mode_name)
            
            # Update mode description and target
            self.update_mode_display()
            
            # Auto-recalculate if connected
            if self.is_connected and self.account_info:
                self.calculate_survivability()
                
            self.log_message(f"🎯 Trading mode changed to: {mode_name}", "INFO")
            
        except Exception as e:
            self.log_message(f"❌ Mode change error: {e}", "ERROR")

    def update_mode_display(self):
        """Update mode description and target display"""
        try:
            if not hasattr(self, 'survivability_engine'):
                return
                
            mode_config = self.survivability_engine.mode_configs[self.current_trading_mode]
            
            # Mode descriptions with emojis
            descriptions = {
                'SAFE': '🛡️ Maximum protection, slower gains',
                'BALANCED': '⚖️ Good balance between speed and safety', 
                'AGGRESSIVE': '🚀 Faster gains, higher risk',
                'TURBO': '⚡ Maximum speed, maximum risk'
            }
            
            # Risk level colors
            risk_colors = {
                'Low': '#51cf66',
                'Medium': '#ffd43b',
                'High': '#ff6b6b',
                'Very High': '#e74c3c'
            }
            
            # Update labels
            mode_desc = descriptions.get(self.current_trading_mode.value, mode_config['description'])
            self.mode_desc_label.config(text=mode_desc)
            
            target_points = mode_config['target_survivability']
            self.target_surv_label.config(text=f"🎯 Target: {target_points:,} points")
            
            risk_level = mode_config['risk_level']
            risk_color = risk_colors.get(risk_level, '#ffffff')
            self.risk_level_label.config(
                text=f"⚠️ Risk: {risk_level}",
                fg=risk_color
            )
            
        except Exception as e:
            print(f"Error updating mode display: {e}")

    def create_hedge_section(self, parent):
        """Create hedge monitoring section"""
        hedge_frame = tk.LabelFrame(
            parent,
            text="⚡ Real-time Hedge Monitor",
            font=('Arial', 12, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        hedge_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Current status
        status_frame = tk.Frame(hedge_frame, bg='#16213e')
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.current_drawdown_label = tk.Label(
            status_frame,
            text="📊 Current Drawdown: 0 points",
            font=('Arial', 10, 'bold'),
            fg='#51cf66',
            bg='#16213e'
        )
        self.current_drawdown_label.pack(side=tk.LEFT)
        
        self.next_hedge_label = tk.Label(
            status_frame,
            text="⏳ Next Hedge: N/A",
            font=('Arial', 10),
            fg='#ffffff',
            bg='#16213e'
        )
        self.next_hedge_label.pack(side=tk.RIGHT)
        
    def create_control_section(self, parent):
        """Create trading control section with Smart Profit Controls"""
        control_frame = tk.LabelFrame(
            parent,
            text="🎮 Trading Controls",
            font=('Arial', 12, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Main Control buttons
        btn_frame = tk.Frame(control_frame, bg='#16213e')
        btn_frame.pack(pady=10)
        
        self.start_btn = tk.Button(
            btn_frame,
            text="🚀 Start AI Grid Trading",
            font=('Arial', 12, 'bold'),
            bg='#51cf66',
            fg='#1a1a2e',
            relief='raised',
            bd=3,
            width=20,
            command=self.start_trading
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹️ Stop Trading",
            font=('Arial', 12, 'bold'),
            bg='#ff6b6b',
            fg='#ffffff',
            relief='raised',
            bd=3,
            width=20,
            command=self.stop_trading,
            state='disabled'
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.emergency_btn = tk.Button(
            btn_frame,
            text="🚨 EMERGENCY STOP",
            font=('Arial', 12, 'bold'),
            bg='#e74c3c',
            fg='#ffffff',
            relief='raised',
            bd=3,
            width=20,
            command=self.emergency_stop
        )
        self.emergency_btn.pack(side=tk.LEFT, padx=5)
        
        # 🧠 Smart Profit Control Section
        smart_frame = tk.LabelFrame(
            control_frame,
            text="🧠 Smart Profit Management",
            font=('Arial', 10, 'bold'),
            fg='#4ecdc4',
            bg='#16213e',
            relief='groove',
            bd=1
        )
        smart_frame.pack(fill=tk.X, pady=(10, 5), padx=10)
        
        # Strategy Selection Row
        strategy_row = tk.Frame(smart_frame, bg='#16213e')
        strategy_row.pack(fill=tk.X, pady=5, padx=5)
        
        tk.Label(strategy_row, text="📊 Strategy:", font=('Arial', 10, 'bold'), 
                    fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)
        
        self.strategy_var = tk.StringVar(value="BALANCED")
        strategy_options = ["QUICK_SAFE", "BALANCED", "AGGRESSIVE"]
        
        self.strategy_combo = ttk.Combobox(strategy_row, textvariable=self.strategy_var, 
                                            values=strategy_options, state="readonly", width=12)
        self.strategy_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Strategy descriptions
        strategy_desc = tk.Label(strategy_row, text="⚡ Quick & Safe: $2.5/0.01lot", 
                                font=('Arial', 9), fg='#adb5bd', bg='#16213e')
        strategy_desc.pack(side=tk.LEFT, padx=(15, 0))
        
        self.strategy_desc = strategy_desc  # Store reference for updates
        
        # Control buttons row
        control_row = tk.Frame(smart_frame, bg='#16213e')
        control_row.pack(fill=tk.X, pady=5, padx=5)
        
        # Apply Strategy Button
        self.apply_strategy_btn = tk.Button(
            control_row,
            text="✅ Apply Strategy",
            font=('Arial', 9, 'bold'),
            bg='#4ecdc4',
            fg='#1a1a2e',
            relief='raised',
            bd=2,
            width=15,
            command=self.apply_strategy_change
        )
        self.apply_strategy_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Manual Profit Taking Button
        self.manual_profit_btn = tk.Button(
            control_row,
            text="💰 Take Profit Now",
            font=('Arial', 9, 'bold'),
            bg='#ffd43b',
            fg='#1a1a2e',
            relief='raised',
            bd=2,
            width=15,
            command=self.manual_take_profit,
            state='disabled'
        )
        self.manual_profit_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Close All Profitable Button
        self.close_profitable_btn = tk.Button(
            control_row,
            text="🎯 Close All Profitable",
            font=('Arial', 9, 'bold'),
            bg='#51cf66',
            fg='#1a1a2e',
            relief='raised',
            bd=2,
            width=18,
            command=self.close_all_profitable
        )
        self.close_profitable_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Toggle Smart Profit Button
        self.toggle_smart_btn = tk.Button(
            control_row,
            text="🤖 Smart: ON",
            font=('Arial', 9, 'bold'),
            bg='#6f42c1',
            fg='#ffffff',
            relief='raised',
            bd=2,
            width=12,
            command=self.toggle_smart_profit
        )
        self.toggle_smart_btn.pack(side=tk.RIGHT)
        
        # Status row
        status_row = tk.Frame(smart_frame, bg='#16213e')
        status_row.pack(fill=tk.X, pady=(5, 10), padx=5)
        
        self.smart_status_display = tk.Label(
            status_row,
            text="🤖 Smart Profit: Ready to initialize...",
            font=('Arial', 9),
            fg='#adb5bd',
            bg='#16213e'
        )
        self.smart_status_display.pack(side=tk.LEFT)
        
        # Bind strategy change event
        self.strategy_combo.bind('<<ComboboxSelected>>', self.on_strategy_change)
        
        # Initialize strategy descriptions
        self.update_strategy_description()

    def on_strategy_change(self, event=None):
        """Handle strategy selection change"""
        self.update_strategy_description()
        
    def update_strategy_description(self):
        """Update strategy description based on selection"""
        strategy = self.strategy_var.get()
        descriptions = {
            "QUICK_SAFE": "⚡ Quick & Safe: $2.5/0.01lot, Fast profits",
            "BALANCED": "⚖️ Balanced: $5.0/0.01lot, Good balance", 
            "AGGRESSIVE": "🚀 Aggressive: $10.0/0.01lot, Higher targets"
        }
        
        desc = descriptions.get(strategy, "🤖 Unknown strategy")
        self.strategy_desc.config(text=desc)
        
    def apply_strategy_change(self):
        """Apply strategy change to smart profit manager"""
        try:
            if (hasattr(self, 'grid_trader') and self.grid_trader and 
                hasattr(self.grid_trader, 'smart_profit_enabled') and 
                self.grid_trader.smart_profit_enabled):
                
                new_strategy = self.strategy_var.get()
                
                # Update the strategy in smart profit manager
                from smart_profit_manager import ProfitStrategy
                strategy_mapping = {
                    "QUICK_SAFE": ProfitStrategy.QUICK_SAFE,
                    "BALANCED": ProfitStrategy.BALANCED,
                    "AGGRESSIVE": ProfitStrategy.AGGRESSIVE
                }
                
                if new_strategy in strategy_mapping:
                    self.grid_trader.smart_profit_manager.default_strategy = strategy_mapping[new_strategy]
                    
                    self.log_message(f"✅ Strategy changed to: {new_strategy}", "SUCCESS")
                    self.smart_status_display.config(
                        text=f"🎯 Strategy updated: {new_strategy}",
                        fg='#51cf66'
                    )
                    
                    # Auto-hide success message after 3 seconds
                    self.root.after(3000, lambda: self.smart_status_display.config(
                        text="🤖 Smart Profit: Active",
                        fg='#4ecdc4'
                    ))
                else:
                    self.log_message(f"❌ Invalid strategy: {new_strategy}", "ERROR")
            else:
                self.log_message("⚠️ Smart Profit Manager not available", "WARNING")
                
        except Exception as e:
            self.log_message(f"❌ Strategy change error: {e}", "ERROR")
            
    def manual_take_profit(self):
        """Manually trigger profit taking on all profitable positions"""
        try:
            if (hasattr(self, 'grid_trader') and self.grid_trader and 
                hasattr(self, 'grid_trader.smart_profit_enabled') and 
                self.grid_trader.smart_profit_enabled):
                
                # Force profit taking run
                self.grid_trader.smart_profit_manager.run_smart_profit_management()
                self.log_message("💰 Manual profit taking triggered", "SUCCESS")
            else:
                self.log_message("⚠️ Smart Profit Manager not available", "WARNING")
                
        except Exception as e:
            self.log_message(f"❌ Manual profit taking error: {e}", "ERROR")
            
    def close_all_profitable(self):
        """Close all positions with profit > $1"""
        try:
            if not hasattr(self, 'grid_trader') or not self.grid_trader:
                self.log_message("⚠️ Grid trader not available", "WARNING")
                return
                
            confirm = messagebox.askyesno(
                "Close Profitable Positions", 
                "Close all positions with profit > $1?\n\nThis action cannot be undone."
            )
            
            if confirm:
                closed_count = 0
                
                if hasattr(self.grid_trader, 'active_positions'):
                    for position_id, grid_level in list(self.grid_trader.active_positions.items()):
                        if grid_level.pnl > 1.0:  # Profit > $1
                            if self.grid_trader.close_grid_position(grid_level):
                                closed_count += 1
                                
                self.log_message(f"✅ Closed {closed_count} profitable positions", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"❌ Close profitable positions error: {e}", "ERROR")
            
    def toggle_smart_profit(self):
        """Toggle Smart Profit Management on/off"""
        try:
            if (hasattr(self, 'grid_trader') and self.grid_trader and 
                hasattr(self.grid_trader, 'smart_profit_enabled')):
                
                # Toggle the state
                current_state = self.grid_trader.smart_profit_enabled
                self.grid_trader.smart_profit_enabled = not current_state
                
                if self.grid_trader.smart_profit_enabled:
                    self.toggle_smart_btn.config(text="🤖 Smart: ON", bg='#6f42c1')
                    self.log_message("🧠 Smart Profit Management: ENABLED", "SUCCESS")
                else:
                    self.toggle_smart_btn.config(text="🤖 Smart: OFF", bg='#6c757d')
                    self.log_message("🧠 Smart Profit Management: DISABLED", "WARNING")
                    
            else:
                self.log_message("⚠️ Smart Profit Manager not available", "WARNING")
                
        except Exception as e:
            self.log_message(f"❌ Toggle smart profit error: {e}", "ERROR")

    def create_log_section(self, parent):
        """Create logging and monitoring section"""
        log_frame = tk.LabelFrame(
            parent,
            text="📜 System Logs & Monitoring",
            font=('Arial', 12, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Log display
        self.log_display = scrolledtext.ScrolledText(
            log_frame,
            height=8,
            font=('Consolas', 9),
            bg='#0f0f0f',
            fg='#00ff00',
            insertbackground='#00ff00'
        )
        self.log_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Clear log button
        clear_btn = tk.Button(
            log_frame,
            text="🗑️ Clear Logs",
            font=('Arial', 9),
            bg='#6c757d',
            fg='#ffffff',
            command=self.clear_logs
        )
        clear_btn.pack(pady=(0, 10))
        
    def setup_status_monitoring(self):
        """Setup real-time status monitoring"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_system, daemon=True)
        self.monitor_thread.start()
        
    def log_message(self, message, level="INFO"):
        """Add message to log display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding by level
        colors = {
            "INFO": "#00ff00",
            "WARNING": "#ffd43b", 
            "ERROR": "#ff6b6b",
            "SUCCESS": "#51cf66"
        }
        
        color = colors.get(level, "#ffffff")
        formatted_msg = f"[{timestamp}] {level}: {message}\n"
        
        # Insert to log display
        self.log_display.insert(tk.END, formatted_msg)
        self.log_display.see(tk.END)
        
        # Limit log lines
        lines = self.log_display.get("1.0", tk.END).split('\n')
        if len(lines) > 500:
            self.log_display.delete("1.0", "50.0")
            
    def connect_mt5(self):
        """Connect to MetaTrader5"""
        def connect_thread():
            try:
                self.log_message("🔍 Detecting MT5 installation...")
                
                if self.mt5_connector.auto_connect():
                    self.is_connected = True
                    account_info = self.mt5_connector.get_account_info()
                    gold_symbol = self.mt5_connector.get_gold_symbol()
                    
                    if account_info and gold_symbol:
                        self.account_info = account_info
                        self.update_connection_display(account_info, gold_symbol)
                        self.log_message(f"✅ Connected to MT5 Account: {account_info['login']}", "SUCCESS")
                        self.log_message(f"🥇 Gold Symbol Detected: {gold_symbol}", "SUCCESS")
                        
                        # Calculate survivability automatically
                        self.calculate_survivability()
                        
                    else:
                        raise Exception("Failed to get account info or detect gold symbol")
                        
                else:
                    raise Exception("MT5 connection failed")
                    
            except Exception as e:
                self.is_connected = False
                self.log_message(f"❌ Connection Error: {str(e)}", "ERROR")
                messagebox.showerror("Connection Error", f"Failed to connect to MT5:\n{str(e)}")
                
        threading.Thread(target=connect_thread, daemon=True).start()
        
    def update_connection_display(self, account_info, gold_symbol):
        """Update connection status display"""
        self.connection_status.config(text="✅ Connected", fg='#51cf66')
        
        # Check market status
        market_status = self.check_market_status()
        market_text = "🟢 Open" if market_status else "🔴 Closed"
        market_color = '#51cf66' if market_status else '#ff6b6b'
        
        account_text = f"💰 Account: {account_info['login']} | Balance: ${account_info['balance']:,.2f} | {gold_symbol} | Market: {market_text}"
        self.account_label.config(text=account_text, fg=market_color if not market_status else '#ffffff')
        
        # Enable calculate button
        self.connect_btn.config(text="✅ Connected", state='disabled')
        
    def check_market_status(self) -> bool:
        """Check if market is currently open"""
        try:
            if not hasattr(self, 'mt5_connector') or not self.mt5_connector:
                return False
                
            # Get current time
            current_time = datetime.now()
            
            # Check if it's weekend
            if current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return False
                
            # Check MT5 tick data
            import MetaTrader5 as mt5
            gold_symbol = self.mt5_connector.get_gold_symbol()
            if gold_symbol:
                tick = mt5.symbol_info_tick(gold_symbol)
                return tick is not None and tick.time > 0
                
            return False
            
        except Exception as e:
            print(f"Error checking market status: {e}")
            return False
        
    def calculate_survivability(self):
        """Calculate and display survivability parameters with selected trading mode"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to MT5 first")
            return
            
        try:
            balance = self.account_info.get('balance', 0)
            if balance <= 0:
                raise ValueError("Invalid account balance")
                
            # Get broker minimum lot size
            symbol_info = self.mt5_connector.get_symbol_info()
            min_lot = symbol_info.get('volume_min', 0.01) if symbol_info else 0.01
            calculations = self.survivability_engine.calculate_for_balance(
            balance, min_lot, self.current_trading_mode, symbol_info
            )    
            self.log_message(f"🧮 Calculating survivability for ${balance:,.2f}...")
            self.log_message(f"🎯 Mode: {self.current_trading_mode.value}")
            self.log_message(f"📏 Broker minimum lot: {min_lot}")
            
            # ⭐ แก้ไขส่วนนี้ - ใช้ method เดิมที่มีอยู่แล้ว
            # เพิ่ม parameter target_survivability จาก mode config
            mode_config = self.survivability_engine.mode_configs[self.current_trading_mode]
            target_survivability = mode_config['target_survivability']
            
            # Calculate using survivability engine with mode by passing target_survivability
            calculations = self.survivability_engine.calculate_for_balance(
                balance, 
                min_lot, 
                self.current_trading_mode  # ส่ง trading_mode
            )
            self.current_calculations = calculations
            
            # Update display
            self.update_survivability_display(calculations)
        
            
            # Log warnings if any
            if calculations.get('warnings'):
                for warning in calculations['warnings']:
                    self.log_message(f"⚠️ {warning}", "WARNING")
            
            # Show success message based on mode target
            target_surv = calculations.get('target_survivability', 20000)
            realistic_surv = calculations.get('realistic_survivability', calculations.get('survivability', 0))
            
            if calculations.get('target_met', False) or realistic_surv >= target_surv:
                self.log_message(f"✅ {self.current_trading_mode.value} mode target achieved!", "SUCCESS")
            elif realistic_surv >= target_surv * 0.8:
                self.log_message(f"✅ {self.current_trading_mode.value} mode ready with good protection", "SUCCESS")
            else:
                self.log_message(f"✅ {self.current_trading_mode.value} mode ready with basic protection", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"❌ Calculation Error: {str(e)}", "ERROR")
            messagebox.showerror("Calculation Error", str(e))

    def update_survivability_display(self, calc):
        """Update survivability display with calculations and mode information"""
        self.balance_label.config(text=f"💰 Balance: ${calc['account_balance']:,.2f}")
        
        # ⭐ เพิ่มการแสดง Mode ที่ใช้
        mode_text = f"🎯 Mode: {calc['trading_mode']} | Target: {calc['target_survivability']:,} pts"
        if not hasattr(self, 'mode_display_label'):
            # สร้าง label ใหม่ถ้ายังไม่มี
            self.mode_display_label = tk.Label(
                self.balance_label.master,
                text=mode_text,
                font=('Arial', 10, 'bold'),
                fg='#4ecdc4',
                bg='#16213e'
            )
            self.mode_display_label.pack(anchor='w', pady=2)
        else:
            self.mode_display_label.config(text=mode_text)
        
        # Show both ideal and actual lot sizes
        if calc.get('lot_size_adjusted', False):
            lot_text = f"🎯 Lot: {calc['base_lot']:.3f} (Ideal: {calc['ideal_base_lot']:.3f}) ⚠️"
            lot_color = '#ffd43b'  # Yellow for warning
        else:
            lot_text = f"🎯 Base Lot: {calc['base_lot']:.3f}"
            lot_color = '#ffffff'
            
        self.base_lot_label.config(text=lot_text, fg=lot_color)
        
        self.grid_spacing_label.config(text=f"📏 Grid Spacing: {calc['grid_spacing']} points (${calc['grid_spacing']*0.01:.2f})")
        self.max_levels_label.config(text=f"📈 Max Levels: {calc['max_levels']}")
        
        # 🚀 เพิ่ม Smart Grid Status Display
        if not hasattr(self, 'smart_grid_label'):
            self.smart_grid_label = tk.Label(
                self.balance_label.master,
                text="",
                font=('Arial', 10, 'bold'),
                fg='#4ecdc4',
                bg='#16213e'
            )
            self.smart_grid_label.pack(anchor='w', pady=2)
        
        # แสดงข้อมูล Smart Grid
        smart_text = f"🚀 Smart Grid: {calc['grid_spacing']}pt spacing, Auto-Balance Portfolio, No Hedge Cost"
        self.smart_grid_label.config(text=smart_text)
        
        # Show both theoretical and realistic survivability with target comparison
        theoretical_surv = calc['survivability']
        realistic_surv = calc.get('realistic_survivability', theoretical_surv)
        target_surv = calc['target_survivability']
        
        # ⭐ ปรับเงื่อนไขสีตาม target ของ mode
        if realistic_surv >= target_surv:
            surv_color = '#51cf66'  # Green - ถึงเป้าหมายแล้ว
            status_emoji = "✅"
        elif realistic_surv >= target_surv * 0.8:
            surv_color = '#ffd43b'  # Yellow - ใกล้เป้าหมาย
            status_emoji = "⚠️"
        else:
            surv_color = '#ff6b6b'  # Red - ต่ำกว่าเป้าหมาย
            status_emoji = "❌"
        
        if realistic_surv != theoretical_surv:
            surv_text = f"🛡️ Survivability: {realistic_surv:,.0f} points {status_emoji} (Theory: {theoretical_surv:,.0f}) | Target: {target_surv:,.0f}"
        else:
            surv_text = f"🛡️ Survivability: {realistic_surv:,.0f} points {status_emoji} | Target: {target_surv:,.0f}"
            
        self.survivability_label.config(text=surv_text, fg=surv_color)
        
        # ⭐ แสดง Mode Description และ Risk Level
        mode_desc = calc.get('mode_description', '')
        risk_level = calc.get('mode_risk_level', '')
        
        if not hasattr(self, 'mode_info_label'):
            self.mode_info_label = tk.Label(
                self.balance_label.master,
                text=f"📝 {mode_desc} | Risk: {risk_level}",
                font=('Arial', 9),
                fg='#adb5bd',
                bg='#16213e'
            )
            self.mode_info_label.pack(anchor='w', pady=1)
        else:
            self.mode_info_label.config(text=f"📝 {mode_desc} | Risk: {risk_level}")
        
        # Safety margin (existing code...)
        safety_margin = calc['account_balance'] * (1 - self.config.get('safety_ratio', 0.6))
        if 'safety_margin_percentage' in calc:
            safety_pct = calc['safety_margin_percentage']
        else:
            safety_pct = (calc['safety_margin'] / calc['account_balance']) * 100
            
        self.safety_margin_label.config(text=f"💪 Safety Margin: ${calc['safety_margin']:,.2f} ({safety_pct:.1f}%)")
        
        # Show capital utilization if available
        if 'capital_utilization' in calc:
            util_text = f"📊 Capital Used: {calc['capital_utilization']:.1f}%"
            if calc['capital_utilization'] > 90:
                util_color = '#ff6b6b'  # Red for high utilization
            elif calc['capital_utilization'] > 70:
                util_color = '#ffd43b'  # Yellow for moderate
            else:
                util_color = '#51cf66'  # Green for safe
            
            # Add utilization label if not exists
            if not hasattr(self, 'utilization_label'):
                self.utilization_label = tk.Label(
                    self.max_levels_label.master, 
                    text=util_text, 
                    font=('Arial', 10), 
                    fg=util_color, 
                    bg='#16213e'
                )
                self.utilization_label.pack(anchor='w', pady=2)
            else:
                self.utilization_label.config(text=util_text, fg=util_color)

        # 🚀 เพิ่ม Smart Grid Benefits Display
        if not hasattr(self, 'benefits_label'):
            self.benefits_label = tk.Label(
                self.balance_label.master,
                text="",
                font=('Arial', 9),
                fg='#51cf66',
                bg='#16213e'
            )
            self.benefits_label.pack(anchor='w', pady=1)
        
        # แสดงประโยชน์ของ Smart Grid
        benefits_text = "💡 Benefits: 3x faster profits, Self-balancing, No hedge costs, Tighter grid"
        self.benefits_label.config(text=benefits_text)

        # 🚀 เพิ่ม Smart Grid Efficiency Display
        if 'smart_grid_efficiency' in calc:
            if not hasattr(self, 'efficiency_label'):
                self.efficiency_label = tk.Label(
                    self.balance_label.master,
                    text="",
                    font=('Arial', 9),
                    fg='#4ecdc4',
                    bg='#16213e'
                )
                self.efficiency_label.pack(anchor='w', pady=1)
            
            efficiency = calc['smart_grid_efficiency']
            saved_amount = calc.get('capital_saved', 0)
            efficiency_text = f"⚡ Smart Grid Efficiency: {efficiency:.1f}x | Capital Saved: ${saved_amount:.0f}"
            self.efficiency_label.config(text=efficiency_text)

    def start_trading(self):
        """Start AI grid trading system - REAL TRADING"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to MT5 first")
            return
            
        if not self.current_calculations:
            messagebox.showwarning("Warning", "Please calculate survivability first")
            return
            
        # Final confirmation for real trading
        confirm_msg = f"""⚠️ REAL TRADING CONFIRMATION ⚠️

You are about to start LIVE trading with:
• Account Balance: ${self.current_calculations['account_balance']:,.2f}
• Base Lot Size: {self.current_calculations['base_lot']:.3f}
• Max Survivability: {self.current_calculations.get('realistic_survivability', self.current_calculations['survivability']):,.0f} points
• Daily Loss Limit: ${self.config.get('daily_loss_limit', 500):,.2f}

This will place REAL orders on your MT5 account!

Are you absolutely sure you want to proceed?"""

        if not messagebox.askyesno("⚠️ LIVE TRADING CONFIRMATION", confirm_msg):
            return
            
        try:
            # Initialize grid trader with real trading
            gold_symbol = self.mt5_connector.get_gold_symbol()
            self.grid_trader = AIGoldGrid(
                self.mt5_connector,
                self.current_calculations,
                self.config
            )
            
            # Initialize the grid system
            self.log_message("🚀 Initializing AI Grid Trading System...", "INFO")
            if not self.grid_trader.initialize_grid():
                raise Exception("Failed to initialize grid system")
            
            # Start trading
            if self.grid_trader.start_trading():
                self.is_trading = True
                self.start_btn.config(state='disabled', bg='#6c757d')
                self.stop_btn.config(state='normal', bg='#dc3545')
                
                self.log_message("🚀 AI Grid Trading System Started - LIVE TRADING!", "SUCCESS")
                self.log_message(f"📊 Trading {gold_symbol} with {self.current_calculations.get('realistic_survivability', 0):,.0f} points survivability", "INFO")
                self.log_message(f"🎯 Magic Number: {self.grid_trader.magic_number}", "INFO")
                
                # Start trading monitoring thread
                self.trading_thread = threading.Thread(target=self.run_trading_loop, daemon=True)
                self.trading_thread.start()
                
                # Start real-time monitoring
                self.start_real_time_monitoring()
            else:
                raise Exception("Failed to start trading system")
            
        except Exception as e:
            self.log_message(f"❌ Start Trading Error: {str(e)}", "ERROR")
            messagebox.showerror("Trading Error", f"Failed to start trading:\n{str(e)}")
            
    def stop_trading(self):
        """Stop trading system gracefully"""
        if not self.is_trading:
            return
            
        try:
            confirm_msg = "Stop AI Grid Trading?\n\nThis will:\n• Stop placing new orders\n• Keep existing positions open\n• Cancel pending orders\n\nContinue?"
            
            if messagebox.askyesno("Stop Trading", confirm_msg):
                self.is_trading = False
                
                if self.grid_trader:
                    self.grid_trader.stop_trading()
                    
                    # Cancel pending orders
                    cancelled = self.grid_trader.cancel_all_orders()
                    self.log_message(f"🔴 Cancelled {cancelled} pending orders", "WARNING")
                    
                self.start_btn.config(state='normal', bg='#51cf66')
                self.stop_btn.config(state='disabled', bg='#6c757d')
                
                self.log_message("⏹️ AI Grid Trading System Stopped", "WARNING")
                
                # Show final status
                if self.grid_trader:
                    status = self.grid_trader.get_grid_status()
                    self.log_message(f"📊 Final Status: {status['active_positions']} positions, Total PnL: ${status['total_pnl']:.2f}", "INFO")
                
        except Exception as e:
            self.log_message(f"❌ Stop Trading Error: {str(e)}", "ERROR")
            
    def emergency_stop(self):
        """Emergency stop - close all positions immediately"""
        if not self.is_trading:
            messagebox.showwarning("Warning", "Trading is not active")
            return
            
        emergency_msg = """🚨 EMERGENCY STOP WARNING 🚨

This will IMMEDIATELY:
• Close ALL open positions at market price
• Cancel ALL pending orders  
• Stop the trading system completely

This action cannot be undone!
Use only in emergency situations.

Proceed with emergency stop?"""

        if messagebox.askyesno("🚨 EMERGENCY STOP", emergency_msg):
            try:
                self.log_message("🚨 EMERGENCY STOP INITIATED!", "ERROR")
                
                if self.grid_trader:
                    # Emergency close all
                    self.grid_trader.emergency_close_all()
                    
                    # Get final status
                    status = self.grid_trader.get_grid_status()
                    self.log_message(f"🚨 Emergency Stop Completed - Final PnL: ${status['total_pnl']:.2f}", "ERROR")
                    
                self.is_trading = False
                self.start_btn.config(state='normal', bg='#51cf66')
                self.stop_btn.config(state='disabled', bg='#6c757d')
                
                messagebox.showinfo("Emergency Stop", "Emergency stop completed!\nAll positions have been closed.")
                
            except Exception as e:
                self.log_message(f"❌ Emergency Stop Error: {str(e)}", "ERROR")
                messagebox.showerror("Emergency Stop Error", f"Error during emergency stop:\n{str(e)}")
                
    def run_trading_loop(self):
        """Main trading monitoring loop"""
        if not self.grid_trader:
            return
            
        # Start the grid trader's internal loop
        self.grid_trader.run_trading_loop()
        
    def start_real_time_monitoring(self):
        """Start real-time monitoring of trading status"""
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self.real_time_monitor, daemon=True)
        self.monitoring_thread.start()
        
    def real_time_monitor(self):
        """Real-time monitoring thread"""
        update_count = 0
        
        while self.is_trading and self.monitoring_active:
            try:
                if self.grid_trader:
                    # Get current status
                    status = self.grid_trader.get_grid_status()
                    
                    # Update GUI every 5 seconds
                    if update_count % 5 == 0:
                        self.root.after(0, self.update_trading_display, status)
                        
                    # Check for emergency conditions
                    if status.get('emergency_stop', False):
                        self.root.after(0, self.handle_emergency_triggered)
                        break
                        
                    update_count += 1
                    
                time.sleep(1)  # Update every second
                
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(5)
                
    def update_trading_display(self, status: Dict):
        """Update GUI with real-time trading data + Smart Profit Status"""
        try:
            # Update current drawdown display
            current_drawdown = status.get('current_drawdown', 0)
            total_pnl = status.get('total_pnl', 0)
            market_open = status.get('market_open', True)
            
            if total_pnl >= 0:
                color = '#51cf66'  # Green for profit
                text = f"📊 Current Profit: +${total_pnl:.2f} ({current_drawdown:.0f} pts)"
            else:
                color = '#ff6b6b'  # Red for loss
                text = f"📊 Current Loss: ${total_pnl:.2f} ({current_drawdown:.0f} pts)"
                
            # Add market status to display
            market_emoji = "🟢" if market_open else "🔴"
            text += f" | Market: {market_emoji}"
                
            self.current_drawdown_label.config(text=text, fg=color)
            
            # Update next hedge trigger
            if hasattr(self, 'hedge_calculator') and current_drawdown > 0:
                next_hedge = self.hedge_calculator.get_next_hedge_trigger(current_drawdown)
                if next_hedge:
                    self.next_hedge_label.config(text=f"⏳ Next Hedge: {next_hedge:,.0f} points")
                else:
                    self.next_hedge_label.config(text="⏳ Next Hedge: Max Level")
            
            # Update position counts and hedge status
            if not hasattr(self, 'position_count_label'):
                self.position_count_label = tk.Label(
                    self.current_drawdown_label.master,
                    text="",
                    font=('Arial', 10),
                    fg='#ffffff',
                    bg='#16213e'
                )
                self.position_count_label.pack(anchor='w', pady=2)
                
            # Check hedge status from grid trader
            hedge_status = ""
            try:
                if (hasattr(self, 'grid_trader') and self.grid_trader and 
                    hasattr(self.grid_trader, 'has_active_hedge') and 
                    self.grid_trader.has_active_hedge()):
                    hedge_status = " | 🛡️ HEDGE ACTIVE"
            except Exception as hedge_error:
                # If hedge check fails, just continue without hedge status
                pass
                
            position_text = f"📈 Positions: {status.get('active_positions', 0)} active, {status.get('pending_orders', 0)} pending{hedge_status}"
            if not market_open:
                position_text += " | 🕒 Market Closed - Orders paused"
                
            self.position_count_label.config(text=position_text)
            
            # 🧠 ADD SMART PROFIT STATUS DISPLAY
            if not hasattr(self, 'smart_status_label'):
                self.smart_status_label = tk.Label(
                    self.current_drawdown_label.master,
                    text="",
                    font=('Arial', 10),
                    fg='#4ecdc4',
                    bg='#16213e'
                )
                self.smart_status_label.pack(anchor='w', pady=2)
            
            # Update Smart Profit Status - ENHANCED WITH SAFE FALLBACK
            smart_text = "💡 Smart Profit: Not Available"
            smart_color = '#6c757d'  # Gray default
            
            try:
                if (hasattr(self, 'grid_trader') and self.grid_trader and 
                    hasattr(self.grid_trader, 'smart_profit_enabled') and 
                    self.grid_trader.smart_profit_enabled):
                    
                    # Try to get detailed status
                    try:
                        smart_status = self.grid_trader.smart_profit_manager.get_profit_management_status()
                        
                        # Check if smart_status has error
                        if 'error' in smart_status:
                            smart_text = "🧠 Smart: ✅ ACTIVE (Status Error)"
                            smart_color = '#ffd43b'
                        else:
                            strategy = smart_status.get('strategy', 'BALANCED')
                            risk_pct = smart_status.get('risk_percentage', 0)
                            trailing_active = smart_status.get('trailing_stops_active', 0)
                            total_positions = smart_status.get('total_positions', 0)
                            hedge_positions = smart_status.get('hedge_positions', 0)
                            
                            # Color based on risk level
                            if risk_pct < 10:
                                smart_color = '#51cf66'  # Green - Low risk
                                risk_emoji = "🟢"
                            elif risk_pct < 20:
                                smart_color = '#ffd43b'  # Yellow - Medium risk
                                risk_emoji = "🟡"
                            else:
                                smart_color = '#ff6b6b'  # Red - High risk
                                risk_emoji = "🔴"
                            
                            # Strategy emoji
                            strategy_emoji = {
                                'QUICK_SAFE': '⚡',
                                'BALANCED': '⚖️',
                                'AGGRESSIVE': '🚀'
                            }.get(strategy, '🤖')
                            
                            smart_text = f"🧠 Smart: {strategy_emoji} {strategy} | Risk: {risk_pct:.1f}% {risk_emoji}"
                            
                            if trailing_active > 0:
                                smart_text += f" | 📈 Trailing: {trailing_active}"
                                
                            if hedge_positions > 0:
                                smart_text += f" | 🛡️ Hedge: {hedge_positions}"
                        
                    except Exception as status_error:
                        # Smart is enabled but status call failed - still working
                        smart_text = "🧠 Smart: ✅ ACTIVE (Display Issue)"
                        smart_color = '#ffd43b'
                        
                elif hasattr(self, 'grid_trader') and self.grid_trader:
                    # Check if smart profit manager exists but not enabled
                    if hasattr(self.grid_trader, 'smart_profit_manager'):
                        smart_text = "🧠 Smart: 🔄 READY (Click to Enable)"
                        smart_color = '#ffd43b'
                    else:
                        smart_text = "🧠 Smart: ❌ NOT INITIALIZED"
                        smart_color = '#6c757d'
                else:
                    smart_text = "🧠 Smart: ❌ GRID NOT ACTIVE"
                    smart_color = '#6c757d'
                    
            except Exception as smart_error:
                # Final fallback - assume working if grid trader exists
                if hasattr(self, 'grid_trader') and self.grid_trader:
                    smart_text = "🧠 Smart: ✅ WORKING (Unknown Status)"
                    smart_color = '#51cf66'
                else:
                    smart_text = "🧠 Smart: ❌ ERROR"
                    smart_color = '#ff6b6b'
            
            self.smart_status_label.config(text=smart_text, fg=smart_color)
            
            # 📊 ADD PROFIT TARGET INFO - SIMPLIFIED VERSION
            if not hasattr(self, 'target_info_label'):
                self.target_info_label = tk.Label(
                    self.current_drawdown_label.master,
                    text="",
                    font=('Arial', 9),
                    fg='#adb5bd',
                    bg='#16213e'
                )
                self.target_info_label.pack(anchor='w', pady=1)
            
            # Show simplified target info
            target_text = ""
            try:
                if (hasattr(self, 'grid_trader') and self.grid_trader and 
                    status.get('active_positions', 0) > 0):
                    
                    active_positions = status.get('active_positions', 0)
                    
                    # Get strategy safely
                    strategy = "BALANCED"  # Default
                    target_per_lot = 5.0   # Default for BALANCED
                    
                    try:
                        if hasattr(self.grid_trader, 'smart_profit_manager'):
                            # Try to get strategy from smart manager
                            if hasattr(self.grid_trader.smart_profit_manager, 'default_strategy'):
                                strategy_obj = self.grid_trader.smart_profit_manager.default_strategy
                                strategy = strategy_obj.value if hasattr(strategy_obj, 'value') else str(strategy_obj)
                                
                                # Map strategy to target
                                if 'QUICK' in strategy:
                                    target_per_lot = 2.5
                                elif 'AGGRESSIVE' in strategy:
                                    target_per_lot = 10.0
                                else:
                                    target_per_lot = 5.0
                    except:
                        pass  # Use defaults
                    
                    # Calculate estimated targets
                    estimated_target = active_positions * target_per_lot
                    target_text = f"🎯 Est. Targets: ~${estimated_target:.1f} | Strategy: ${target_per_lot:.1f}/0.01lot"
                    
            except Exception as target_error:
                pass  # Don't show target info if error
            
            self.target_info_label.config(text=target_text)
            
        except Exception as e:
            print(f"Display update error: {e}")

    def handle_emergency_triggered(self):
        """Handle emergency stop triggered by system"""
        
        # Get the reason from the grid trader if available
        if hasattr(self, 'grid_trader') and self.grid_trader:
            status = self.grid_trader.get_grid_status()
            
            # Don't show emergency dialog if it's just market closure
            # Emergency stops should only be for real emergencies (loss limits, margin, etc.)
            if status.get('market_open', True) == False:
                # Market is closed - this is not a real emergency
                self.log_message("🕒 Market closed - System in monitoring mode", "INFO")
                return
                
        # Real emergency stop
        self.is_trading = False
        self.monitoring_active = False
        
        self.start_btn.config(state='normal', bg='#51cf66')
        self.stop_btn.config(state='disabled', bg='#6c757d')
        
        self.log_message("🚨 AUTOMATIC EMERGENCY STOP TRIGGERED!", "ERROR")
        
        messagebox.showerror(
            "🚨 Emergency Stop", 
            "Automatic emergency stop was triggered!\n\nCheck the logs for details.\nAll positions have been closed."
        )
                
    def monitor_system(self):
        """Monitor system status"""
        while self.monitoring:
            try:
                if self.is_connected and self.mt5_connector:
                    # Update account info
                    account_info = self.mt5_connector.get_account_info()
                    if account_info:
                        self.account_info = account_info
                        
                    # Update current drawdown if trading
                    if self.is_trading and self.grid_trader:
                        current_drawdown = self.grid_trader.get_current_drawdown()
                        self.root.after(0, self.update_drawdown_display, current_drawdown)
                        
                time.sleep(2)  # Monitor every 2 seconds
                
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(5)
                
    def update_drawdown_display(self, drawdown):
        """Update current drawdown display"""
        if drawdown >= 0:
            color = '#51cf66'  # Green for profit
            text = f"📊 Current Profit: +{drawdown:,.0f} points"
        else:
            color = '#ff6b6b'  # Red for loss
            text = f"📊 Current Drawdown: {abs(drawdown):,.0f} points"
            
        self.current_drawdown_label.config(text=text, fg=color)
        
        # 🚀 Smart Grid status instead of hedge trigger
        if self.current_calculations and abs(drawdown) > 0:
            # แสดง Smart Grid rebalancing status แทน
            abs_drawdown = abs(drawdown)
            if abs_drawdown > 1000:
                balance_text = "⚖️ Smart Grid: Active rebalancing"
            elif abs_drawdown > 500:
                balance_text = "⚖️ Smart Grid: Monitoring balance"
            else:
                balance_text = "⚖️ Smart Grid: Portfolio balanced"
                
            self.next_hedge_label.config(text=balance_text)
        else:
            self.next_hedge_label.config(text="⚖️ Smart Grid: Ready")

    def clear_logs(self):
        """Clear log display"""
        self.log_display.delete("1.0", tk.END)
        self.log_message("🗑️ Logs cleared", "INFO")
        
    def on_closing(self):
        """Handle application closing - SAFE EXIT"""
        
        if self.is_trading:
            exit_msg = """Trading is currently active!

Choose your exit option:

• STOP TRADING: Stop system but keep positions open
• EMERGENCY CLOSE: Close all positions immediately  
• CANCEL: Continue trading

What would you like to do?"""

            # Custom dialog for exit options
            from tkinter import messagebox
            
            result = messagebox.askyesnocancel(
                "Trading Active", 
                "Trading is active. Stop trading before exit?\n\n• YES = Stop trading (keep positions)\n• NO = Emergency close all\n• CANCEL = Don't exit"
            )
            
            if result is True:  # YES - Stop trading
                self.stop_trading()
                time.sleep(2)  # Give time for cleanup
                
            elif result is False:  # NO - Emergency close
                self.emergency_stop()
                time.sleep(3)  # Give time for emergency close
                
            else:  # CANCEL - Don't exit
                return
                
        # Stop monitoring
        self.monitoring = False
        if hasattr(self, 'monitoring_active'):
            self.monitoring_active = False
        
        # Disconnect MT5
        if hasattr(self, 'mt5_connector'):
            self.mt5_connector.disconnect()
            
        # Save config
        self.save_config()
        
        # Final log
        self.log_message("👋 AI Gold Grid Trading System Closed Safely", "INFO")
        
        self.root.destroy()
        
    def run(self):
        """Run the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Welcome message
        self.log_message("🏆 AI Gold Grid Trading System Initialized", "SUCCESS")
        self.log_message("📊 Target: 20,000+ Points Survivability", "INFO")
        self.log_message("🔗 Ready to connect to MetaTrader5", "INFO")
        
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        # Check if required files exist
        required_files = [
            'mt5_auto_connector.py',
            'ai_gold_grid.py', 
            'survivability_engine.py',
            'ai_money_manager.py',
            'gold_hedge_calculator.py'
        ]
        
        missing_files = [f for f in required_files if not os.path.exists(f)]
        
        if missing_files:
            print("⚠️ Missing required files:")
            for file in missing_files:
                print(f"   - {file}")
            print("\nPlease ensure all modules are in the same directory.")
            input("Press Enter to continue anyway...")
            
        # Start GUI
        app = AIGoldTradingGUI()
        app.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()