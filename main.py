"""
AI Smart Profit Gold Trading System with 20,000+ Points Survivability
Main GUI Controller - main.py
Created for MetaTrader5 Gold Trading with Smart Profit Manager Integration
UPDATED VERSION - Enhanced GUI for AI Smart System with One-Click Operation
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import os
import sys

import requests

from api_connector import BackendAPIConnector

# Import custom modules
try:
   from mt5_auto_connector import MT5AutoConnector
   from smart_profit_manager import SmartProfitManager
   from survivability_engine import SurvivabilityEngine, TradingMode
   from ai_money_manager import AIMoneyManager
   from gold_hedge_calculator import GoldHedgeCalculator
except ImportError as e:
   print(f"Module import error: {e}")
   print("Please ensure all required modules are in the same directory")

class AISmartProfitGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_main_window()
        self.load_config()
        self.init_components()
        self.create_gui()
        self.setup_status_monitoring()
        self.current_trading_mode = TradingMode.BALANCED
        
        self.api_base_url ="http://123.253.62.50:8080/api"

    
    def setup_main_window(self):
        """Setup main window properties"""
        self.root.title("🧠 AI Smart Profit Gold Trading System")
        self.root.geometry("1400x900")
        self.root.configure(bg='#0d1117')
        
        # Center window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def load_config(self):
        """Load configuration from config.json"""
        default_config = {
            "target_survivability": 20000,
            "default_trading_mode": "BALANCED",
            "safety_ratio": 0.6,
            "emergency_stop_percentage": 50,
            "daily_loss_limit_percentage": 10,
            "hedge_triggers": [0.15, 0.30, 0.45, 0.60],
            "hedge_multipliers": [0.5, 1.0, 1.5, 2.0],
            "log_level": "INFO",
            "auto_connect_mt5": True,
            "gold_symbols": ["XAUUSD", "GOLD", "XAU/USD", "XAUUSD"],
            "portfolio_recovery": {
                "enabled": True,
                "trigger_loss": -50,
                "auto_mode": False
            },
            "smart_profit": {
                "default_strategy": "BALANCED",
                "quick_profit_enabled": True,
                "auto_reposition": True,
                "trailing_stop_distance": 50
            },
            "ai_settings": {
                "grid_intelligence": "FULLY_AI",
                "cleanup_auto": True,
                "max_order_age": 45,
                "auto_execute_pairs": True,
                "aggressiveness": 3
            }
        }
        
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
                    
            # Set trading mode from config
            mode_str = default_config.get('default_trading_mode', 'BALANCED')
            try:
                self.current_trading_mode = TradingMode[mode_str]
            except KeyError:
                self.current_trading_mode = TradingMode.BALANCED
                
        except Exception as e:
            print(f"Config load error: {e}")
            
        self.config = default_config

    def save_config(self):
        """Save current configuration"""
        try:
            self.config['default_trading_mode'] = self.current_trading_mode.value
            
            with open('config.json', 'w') as f:
                json.dump(self.config, f, indent=2)
                
        except Exception as e:
            print(f"Config save error: {e}")

    def init_components(self):
        """Initialize trading components"""
        try:
            # Initialize core components
            self.mt5_connector = MT5AutoConnector()
            self.survivability_engine = SurvivabilityEngine(self.config)
            self.money_manager = AIMoneyManager(self.config)
            self.hedge_calculator = GoldHedgeCalculator(self.config)
            self.smart_profit_trader = None  # Will be initialized after MT5 connection
            
            # System status
            self.is_connected = False
            self.is_trading = False
            self.monitoring = True
            self.account_info = {}
            self.current_calculations = {}
            
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to initialize components: {e}")

    def create_gui(self):
        """Create enhanced AI Smart GUI interface"""
        # Main container with 3 columns
        main_container = tk.Frame(self.root, bg='#0d1117')
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create header first
        self.create_header_section(main_container)
        
        # Create main content area with 3 columns
        content_frame = tk.Frame(main_container, bg='#0d1117')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Left Column - AI Status & Controls
        left_frame = tk.Frame(content_frame, bg='#0d1117', width=450)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)
        
        # Center Column - Main Controls & Logs
        center_frame = tk.Frame(content_frame, bg='#0d1117')
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Right Column - Performance & Status
        right_frame = tk.Frame(content_frame, bg='#0d1117', width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        right_frame.pack_propagate(False)
        
        # Populate columns
        self.create_left_column(left_frame)
        self.create_center_column(center_frame)
        self.create_right_column(right_frame)

    def create_header_section(self, parent):
        """Create enhanced header section"""
        header_frame = tk.LabelFrame(
            parent,
            text="🧠 AI Smart Profit Gold Trading System - One-Click Operation",
            font=('Arial', 14, 'bold'),
            fg='#58a6ff',
            bg='#161b22',
            relief='groove',
            bd=2
        )
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Header content with quick status
        header_content = tk.Frame(header_frame, bg='#161b22')
        header_content.pack(fill=tk.X, padx=10, pady=8)
        
        # One-Click Start Button (Large)
        self.quick_start_btn = tk.Button(
            header_content,
            text="🚀 ONE-CLICK START\\nConnect → Calculate → Trade",
            font=('Arial', 14, 'bold'),
            bg='#238636',
            fg='#ffffff',
            relief='raised',
            bd=3,
            height=2,
            command=self.one_click_start
        )
        self.quick_start_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        # Quick Status Display
        status_frame = tk.Frame(header_content, bg='#161b22')
        status_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.quick_status = tk.Label(
            status_frame,
            text="🔌 Ready to Connect → 🧠 Ready to Calculate → 🚀 Ready to Trade",
            font=('Arial', 11),
            fg='#f0f6fc',
            bg='#161b22'
        )
        self.quick_status.pack(anchor='w')
        
        # Emergency Stop (Always visible)
        self.emergency_stop_btn = tk.Button(
            header_content,
            text="🚨 EMERGENCY\\nSTOP",
            font=('Arial', 11, 'bold'),
            bg='#da3633',
            fg='#ffffff',
            relief='raised',
            bd=2,
            width=12,
            height=2,
            command=self.emergency_stop,
            state='disabled'
        )
        self.emergency_stop_btn.pack(side=tk.RIGHT)

    def create_left_column(self, parent):
        """Create left column - AI Status & Smart Controls"""
        
        # AI Intelligence Status
        ai_status_frame = tk.LabelFrame(
            parent,
            text="🧠 AI Intelligence Status",
            font=('Arial', 11, 'bold'),
            fg='#58a6ff',
            bg='#161b22',
            relief='groove',
            bd=2
        )
        ai_status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # AI Status Content
        ai_content = tk.Frame(ai_status_frame, bg='#161b22')
        ai_content.pack(fill=tk.X, padx=8, pady=8)
        
        self.ai_mode_label = tk.Label(
            ai_content,
            text="🎯 Mode: STANDBY",
            font=('Arial', 10, 'bold'),
            fg='#ffd700',
            bg='#161b22'
        )
        self.ai_mode_label.pack(anchor='w')
        
        self.market_condition_label = tk.Label(
            ai_content,
            text="📊 Market: ANALYZING...",
            font=('Arial', 9),
            fg='#7c3aed',
            bg='#161b22'
        )
        self.market_condition_label.pack(anchor='w')
        
        self.ai_health_label = tk.Label(
            ai_content,
            text="🧠 AI Health: --/100",
            font=('Arial', 9),
            fg='#10b981',
            bg='#161b22'
        )
        self.ai_health_label.pack(anchor='w')
        
        self.portfolio_balance_label = tk.Label(
            ai_content,
            text="⚖️ Balance: -- BUY / -- SELL",
            font=('Arial', 9),
            fg='#f59e0b',
            bg='#161b22'
        )
        self.portfolio_balance_label.pack(anchor='w')
        
        # Smart Grid Control
        grid_frame = tk.LabelFrame(
            parent,
            text="🎯 AI Smart Grid Controls",
            font=('Arial', 11, 'bold'),
            fg='#58a6ff',
            bg='#161b22',
            relief='groove',
            bd=2
        )
        grid_frame.pack(fill=tk.X, pady=(0, 10))
        
        grid_content = tk.Frame(grid_frame, bg='#161b22')
        grid_content.pack(fill=tk.X, padx=8, pady=8)
        
        # Grid Mode Selection
        mode_row = tk.Frame(grid_content, bg='#161b22')
        mode_row.pack(fill=tk.X, pady=2)
        
        tk.Label(mode_row, text="Grid Mode:", font=('Arial', 9), fg='#f0f6fc', bg='#161b22').pack(side=tk.LEFT)
        
        self.grid_mode_var = tk.StringVar(value="AI Adaptive")
        self.grid_mode_combo = ttk.Combobox(
            mode_row,
            textvariable=self.grid_mode_var,
            values=["AI Adaptive", "AI Assisted", "Manual Override"],
            width=15,
            state="readonly"
        )
        self.grid_mode_combo.pack(side=tk.RIGHT)
        
        # Spacing Display
        self.spacing_label = tk.Label(
            grid_content,
            text="📏 Spacing: Auto-calculated",
            font=('Arial', 9),
            fg='#a5a5a5',
            bg='#161b22'
        )
        self.spacing_label.pack(anchor='w', pady=2)
        
        # Coverage Display
        self.coverage_label = tk.Label(
            grid_content,
            text="📊 Coverage: Calculating...",
            font=('Arial', 9),
            fg='#a5a5a5',
            bg='#161b22'
        )
        self.coverage_label.pack(anchor='w', pady=2)
        
        # Smart Action Buttons
        btn_frame = tk.Frame(grid_content, bg='#161b22')
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.smart_rebalance_btn = tk.Button(
            btn_frame,
            text="🎯 Smart Rebalance",
            font=('Arial', 9, 'bold'),
            bg='#6366f1',
            fg='#ffffff',
            relief='raised',
            bd=2,
            command=self.smart_rebalance
        )
        self.smart_rebalance_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clean_orders_btn = tk.Button(
            btn_frame,
            text="🧹 Clean Orders",
            font=('Arial', 9, 'bold'),
            bg='#f59e0b',
            fg='#ffffff',
            relief='raised',
            bd=2,
            command=self.clean_orders
        )
        self.clean_orders_btn.pack(side=tk.RIGHT)
        
        # Order Quality Monitor
        quality_frame = tk.LabelFrame(
            parent,
            text="🧹 Order Quality Monitor",
            font=('Arial', 11, 'bold'),
            fg='#58a6ff',
            bg='#161b22',
            relief='groove',
            bd=2
        )
        quality_frame.pack(fill=tk.X, pady=(0, 10))
        
        quality_content = tk.Frame(quality_frame, bg='#161b22')
        quality_content.pack(fill=tk.X, padx=8, pady=8)
        
        self.total_orders_label = tk.Label(
            quality_content,
            text="📊 Total Orders: --",
            font=('Arial', 9),
            fg='#74c0fc',
            bg='#161b22'
        )
        self.total_orders_label.pack(anchor='w')
        
        self.quality_score_label = tk.Label(
            quality_content,
            text="🧹 Quality Score: --/100",
            font=('Arial', 9, 'bold'),
            fg='#51cf66',
            bg='#161b22'
        )
        self.quality_score_label.pack(anchor='w')
        
        self.quality_issues_label = tk.Label(
            quality_content,
            text="Issues: 🕒 -- | 📏 -- | 🔄 --",
            font=('Arial', 8),
            fg='#a5a5a5',
            bg='#161b22'
        )
        self.quality_issues_label.pack(anchor='w')
        
        # Auto Cleanup Toggle
        cleanup_row = tk.Frame(quality_content, bg='#161b22')
        cleanup_row.pack(fill=tk.X, pady=(8, 0))
        
        self.auto_cleanup_var = tk.BooleanVar(value=True)
        self.auto_cleanup_check = tk.Checkbutton(
            cleanup_row,
            text="Auto Cleanup",
            variable=self.auto_cleanup_var,
            font=('Arial', 9),
            fg='#f0f6fc',
            bg='#161b22',
            selectcolor='#161b22'
        )
        self.auto_cleanup_check.pack(side=tk.LEFT)
        
        # Trading Mode Selection
        mode_frame = tk.LabelFrame(
            parent,
            text="🎯 Trading Configuration",
            font=('Arial', 11, 'bold'),
            fg='#58a6ff',
            bg='#161b22',
            relief='groove',
            bd=2
        )
        mode_frame.pack(fill=tk.X)
        
        mode_content = tk.Frame(mode_frame, bg='#161b22')
        mode_content.pack(fill=tk.X, padx=8, pady=8)
        
        # Trading Mode
        tk.Label(mode_content, text="Trading Mode:", font=('Arial', 9), fg='#f0f6fc', bg='#161b22').pack(anchor='w')
        
        self.mode_var = tk.StringVar(value=self.current_trading_mode.value)
        self.mode_combo = ttk.Combobox(
            mode_content,
            textvariable=self.mode_var,
            values=["SAFE", "BALANCED", "AGGRESSIVE", "TURBO"],
            width=20,
            state="readonly"
        )
        self.mode_combo.pack(fill=tk.X, pady=(2, 8))
        self.mode_combo.bind('<<ComboboxSelected>>', self.on_mode_change)
        
        # Mode Description
        self.mode_desc_label = tk.Label(
            mode_content,
            text="⚖️ Balanced: 10,000 points survivability",
            font=('Arial', 8),
            fg='#a5a5a5',
            bg='#161b22',
            wraplength=200
        )
        self.mode_desc_label.pack(anchor='w')

    def create_center_column(self, parent):
        """Create center column - Main Controls & Logs"""
        
        # Connection & Account Status
        conn_frame = tk.LabelFrame(
            parent,
            text="🔌 Connection & Account Status",
            font=('Arial', 11, 'bold'),
            fg='#58a6ff',
            bg='#161b22',
            relief='groove',
            bd=2
        )
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        conn_content = tk.Frame(conn_frame, bg='#161b22')
        conn_content.pack(fill=tk.X, padx=10, pady=8)
        
        # Connection Status Row
        conn_row = tk.Frame(conn_content, bg='#161b22')
        conn_row.pack(fill=tk.X, pady=2)
        
        self.connection_status = tk.Label(
            conn_row,
            text="❌ Disconnected",
            font=('Arial', 10, 'bold'),
            fg='#f85149',
            bg='#161b22'
        )
        self.connection_status.pack(side=tk.LEFT)
        
        # Account Info
        self.account_label = tk.Label(
            conn_content,
            text="💰 Account: Not connected",
            font=('Arial', 9),
            fg='#f0f6fc',
            bg='#161b22'
        )
        self.account_label.pack(anchor='w', pady=2)
        
        # AI Profit Opportunities
        profit_frame = tk.LabelFrame(
            parent,
            text="💰 AI Profit Analysis",
            font=('Arial', 11, 'bold'),
            fg='#58a6ff',
            bg='#161b22',
            relief='groove',
            bd=2
        )
        profit_frame.pack(fill=tk.X, pady=(0, 10))
        
        profit_content = tk.Frame(profit_frame, bg='#161b22')
        profit_content.pack(fill=tk.X, padx=10, pady=8)
        
        self.high_profit_label = tk.Label(
            profit_content,
            text="💎 High Profit Positions: --",
            font=('Arial', 9),
            fg='#ffd700',
            bg='#161b22'
        )
        self.high_profit_label.pack(anchor='w')
        
        self.trailing_stop_label = tk.Label(
            profit_content,
            text="📈 Trailing Stop Eligible: --",
            font=('Arial', 9),
            fg='#10b981',
            bg='#161b22'
        )
        self.trailing_stop_label.pack(anchor='w')
        
        self.pair_opportunities_label = tk.Label(
            profit_content,
            text="🎯 Pair Close Opportunities: --",
            font=('Arial', 9),
            fg='#f59e0b',
            bg='#161b22'
        )
        self.pair_opportunities_label.pack(anchor='w')
        
        self.ai_recommendation_label = tk.Label(
            profit_content,
            text="💡 Recommendation: Analyzing...",
            font=('Arial', 9, 'bold'),
            fg='#58a6ff',
            bg='#161b22'
        )
        self.ai_recommendation_label.pack(anchor='w', pady=(5, 0))
        
        # Execute AI Suggestions Button
        self.execute_ai_btn = tk.Button(
            profit_content,
            text="💰 Execute AI Suggestions",
            font=('Arial', 10, 'bold'),
            bg='#238636',
            fg='#ffffff',
            relief='raised',
            bd=2,
            state='disabled',
            command=self.execute_ai_suggestions
        )
        self.execute_ai_btn.pack(pady=(8, 0))
        
        # Enhanced Log Section
        log_frame = tk.LabelFrame(
            parent,
            text="📜 AI System Logs",
            font=('Arial', 11, 'bold'),
            fg='#58a6ff',
            bg='#161b22',
            relief='groove',
            bd=2
        )
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Log Controls
        log_controls = tk.Frame(log_frame, bg='#161b22')
        log_controls.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(log_controls, text="Filters:", font=('Arial', 9), fg='#f0f6fc', bg='#161b22').pack(side=tk.LEFT)
        
        # Log Filter Buttons
        filter_frame = tk.Frame(log_controls, bg='#161b22')
        filter_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        self.log_filters = ["All", "🧠 AI", "🎯 Grid", "💰 Profit", "🧹 Cleanup", "💊 Recovery"]
        self.current_filter = "All"
        
        for filter_name in self.log_filters:
            btn = tk.Button(
                filter_frame,
                text=filter_name,
                font=('Arial', 8),
                bg='#21262d' if filter_name != "All" else '#238636',
                fg='#f0f6fc',
                relief='raised',
                bd=1,
                padx=8,
                command=lambda f=filter_name: self.set_log_filter(f)
            )
            btn.pack(side=tk.LEFT, padx=1)
        
        # Clear Log Button
        clear_btn = tk.Button(
            log_controls,
            text="🗑️ Clear",
            font=('Arial', 8),
            bg='#da3633',
            fg='#ffffff',
            relief='raised',
            bd=1,
            command=self.clear_logs
        )
        clear_btn.pack(side=tk.RIGHT)
        
        # Log Display
        self.log_display = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            font=('Consolas', 9),
            bg='#0d1117',
            fg='#f0f6fc',
            insertbackground='#f0f6fc',
            selectbackground='#264f78'
        )
        self.log_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # Configure log colors
        self.log_display.tag_configure("SUCCESS", foreground="#3fb950")
        self.log_display.tag_configure("ERROR", foreground="#f85149")
        self.log_display.tag_configure("WARNING", foreground="#d29922")
        self.log_display.tag_configure("INFO", foreground="#58a6ff")
        self.log_display.tag_configure("AI", foreground="#a5a5a5")

    def create_right_column(self, parent):
        """Create right column - Performance & Status"""
        
        # Real-time AI Status
        status_frame = tk.LabelFrame(
            parent,
            text="📊 Real-time AI Status",
            font=('Arial', 11, 'bold'),
            fg='#58a6ff',
            bg='#161b22',
            relief='groove',
            bd=2
        )
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        status_content = tk.Frame(status_frame, bg='#161b22')
        status_content.pack(fill=tk.X, padx=8, pady=8)
        
        # AI Status Grid
        self.ai_mode_display = tk.Label(
            status_content,
            text="🧠 AI Mode: STANDBY",
            font=('Arial', 10, 'bold'),
            fg='#ffd700',
            bg='#161b22'
        )
        self.ai_mode_display.pack(anchor='w')
        
        self.positions_label = tk.Label(
            status_content,
            text="📈 Positions: 0 BUY (0.000L) / 0 SELL",
            font=('Arial', 9),
            fg='#74c0fc',
            bg='#161b22'
        )
        self.positions_label.pack(anchor='w')
        
        self.pnl_label = tk.Label(
            status_content,
            text="💰 PnL: $0.00 | 🛡️ Safety: 100%",
            font=('Arial', 9, 'bold'),
            fg='#51cf66',
            bg='#161b22'
        )
        self.pnl_label.pack(anchor='w')
        
        self.balance_ratio_label = tk.Label(
            status_content,
            text="⚖️ Balance Ratio: --",
            font=('Arial', 9),
            fg='#f59e0b',
            bg='#161b22'
        )
        self.balance_ratio_label.pack(anchor='w')
        
        self.performance_label = tk.Label(
            status_content,
            text="🎯 Win Rate: 0% | 📊 Trades: 0/0",
            font=('Arial', 9),
            fg='#a5a5a5',
            bg='#161b22'
        )
        self.performance_label.pack(anchor='w')
        
        # Portfolio Recovery Panel
        recovery_frame = tk.LabelFrame(
            parent,
            text="💊 AI Portfolio Recovery",
            font=('Arial', 11, 'bold'),
            fg='#58a6ff',
            bg='#161b22',
            relief='groove',
            bd=2
        )
        recovery_frame.pack(fill=tk.X, pady=(0, 10))
        
        recovery_content = tk.Frame(recovery_frame, bg='#161b22')
        recovery_content.pack(fill=tk.X, padx=8, pady=8)
        
        self.recovery_status_label = tk.Label(
            recovery_content,
            text="Status: 🟢 STANDBY (Healthy)",
            font=('Arial', 9),
            fg='#3fb950',
            bg='#161b22'
        )
        self.recovery_status_label.pack(anchor='w')
        
        self.recovery_trigger_label = tk.Label(
            recovery_content,
            text="Trigger: -$50 | Current: $0.00",
            font=('Arial', 9),
            fg='#a5a5a5',
            bg='#161b22'
        )
        self.recovery_trigger_label.pack(anchor='w')
        
        # Recovery Controls
        recovery_controls = tk.Frame(recovery_content, bg='#161b22')
        recovery_controls.pack(fill=tk.X, pady=(8, 0))
        
        self.auto_recovery_var = tk.BooleanVar(value=False)
        self.auto_recovery_check = tk.Checkbutton(
            recovery_controls,
            text="Auto Mode",
            variable=self.auto_recovery_var,
            font=('Arial', 9),
            fg='#f0f6fc',
            bg='#161b22',
            selectcolor='#161b22',
            command=self.toggle_auto_recovery
        )
        self.auto_recovery_check.pack(side=tk.LEFT)
        
        self.manual_recovery_btn = tk.Button(
            recovery_controls,
            text="🚀 Manual Trigger",
            font=('Arial', 9, 'bold'),
            bg='#fd7e14',
            fg='#ffffff',
            relief='raised',
            bd=2,
            command=self.manual_trigger_recovery
        )
        self.manual_recovery_btn.pack(side=tk.RIGHT)
        
        # Performance Metrics
        metrics_frame = tk.LabelFrame(
            parent,
            text="📈 Performance Metrics",
            font=('Arial', 11, 'bold'),
            fg='#58a6ff',
            bg='#161b22',
            relief='groove',
            bd=2
        )
        metrics_frame.pack(fill=tk.X, pady=(0, 10))
        
        metrics_content = tk.Frame(metrics_frame, bg='#161b22')
        metrics_content.pack(fill=tk.X, padx=8, pady=8)
        
        self.drawdown_label = tk.Label(
            metrics_content,
            text="📉 Drawdown: 0 pts",
            font=('Arial', 9),
            fg='#ffd43b',
            bg='#161b22'
        )
        self.drawdown_label.pack(anchor='w')
        
        self.survivability_label = tk.Label(
            metrics_content,
            text="🛡️ Safety: 100%",
                        bg='#161b22'
        )
        self.survivability_label.pack(anchor='w')
        
        self.win_rate_label = tk.Label(
            metrics_content,
            text="🎯 Win Rate: 0%",
            font=('Arial', 9),
            fg='#51cf66',
            bg='#161b22'
        )
        self.win_rate_label.pack(anchor='w')
        
        self.trades_label = tk.Label(
            metrics_content,
            text="📊 Trades: 0/0",
            font=('Arial', 9),
            fg='#74c0fc',
            bg='#161b22'
        )
        self.trades_label.pack(anchor='w')
        
        # AI Settings Panel
        settings_frame = tk.LabelFrame(
            parent,
            text="⚙️ AI Settings",
            font=('Arial', 11, 'bold'),
            fg='#58a6ff',
            bg='#161b22',
            relief='groove',
            bd=2
        )
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        settings_content = tk.Frame(settings_frame, bg='#161b22')
        settings_content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Grid Intelligence Setting
        tk.Label(settings_content, text="Grid Intelligence:", font=('Arial', 9), fg='#f0f6fc', bg='#161b22').pack(anchor='w')
        
        self.intelligence_var = tk.StringVar(value="Fully AI Controlled")
        intelligence_combo = ttk.Combobox(
            settings_content,
            textvariable=self.intelligence_var,
            values=["Fully AI Controlled", "AI Assisted", "Manual Override"],
            width=25,
            state="readonly"
        )
        intelligence_combo.pack(fill=tk.X, pady=(2, 8))
        
        # Aggressiveness Scale
        tk.Label(settings_content, text="AI Aggressiveness:", font=('Arial', 9), fg='#f0f6fc', bg='#161b22').pack(anchor='w')
        
        self.aggressiveness_var = tk.IntVar(value=3)
        aggressiveness_scale = tk.Scale(
            settings_content,
            variable=self.aggressiveness_var,
            from_=1,
            to=5,
            orient=tk.HORIZONTAL,
            bg='#161b22',
            fg='#f0f6fc',
            highlightbackground='#161b22'
        )
        aggressiveness_scale.pack(fill=tk.X, pady=(2, 8))
        
        # Auto Execute Pairs
        self.auto_execute_var = tk.BooleanVar(value=True)
        auto_execute_check = tk.Checkbutton(
            settings_content,
            text="Auto Execute AI Pairs",
            variable=self.auto_execute_var,
            font=('Arial', 9),
            fg='#f0f6fc',
            bg='#161b22',
            selectcolor='#161b22'
        )
        auto_execute_check.pack(anchor='w', pady=2)
        
        # Max Order Age Setting
        age_frame = tk.Frame(settings_content, bg='#161b22')
        age_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(age_frame, text="Max Order Age (min):", font=('Arial', 9), fg='#f0f6fc', bg='#161b22').pack(side=tk.LEFT)
        
        self.max_age_var = tk.StringVar(value="45")
        age_entry = tk.Entry(age_frame, textvariable=self.max_age_var, width=8, bg='#21262d', fg='#f0f6fc')
        age_entry.pack(side=tk.RIGHT)

    def one_click_start(self):
        """One-click start - Connect → Calculate → Trade"""
        try:
            self.log_message("🚀 ONE-CLICK START: Initiating complete AI setup...", "SUCCESS")
            
            # Update button to show progress
            self.quick_start_btn.config(
                text="⏳ PROCESSING...\\nPlease wait...",
                state='disabled',
                bg='#f59e0b'
            )
            
            # Step 1: Connect to MT5
            self.quick_status.config(text="🔌 Connecting to MT5...")
            self.root.update()
            
            if not self.is_connected:
                self.log_message("🔌 Step 1: Connecting to MetaTrader5...", "INFO")
                success = self.connect_mt5_silent()
                if not success:
                    self.reset_quick_start_button()
                    return
                    
            # Step 2: Calculate AI Parameters
            self.quick_status.config(text="🧠 Calculating AI parameters...")
            self.root.update()
            
            if not self.current_calculations:
                self.log_message("🧠 Step 2: Calculating AI survivability parameters...", "INFO")
                success = self.calculate_survivability_silent()
                if not success:
                    self.reset_quick_start_button()
                    return
                    
            # Step 3: Start AI Trading
            self.quick_status.config(text="🚀 Starting AI Smart Trading...")
            self.root.update()
            
            if not self.is_trading:
                self.log_message("🚀 Step 3: Starting AI Smart Profit Trading...", "INFO")
                success = self.start_trading_silent()
                if not success:
                    self.reset_quick_start_button()
                    return
                    
            # Success - Update UI
            self.quick_start_btn.config(
                text="✅ TRADING ACTIVE\\nAI in Control",
                bg='#238636',
                fg='#ffffff'
            )
            
            self.quick_status.config(text="✅ Connected → ✅ Calculated → ✅ Trading (AI Active)")
            self.emergency_stop_btn.config(state='normal')
            
            self.log_message("🎉 ONE-CLICK START COMPLETED! AI Smart Trading is now active!", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"❌ One-click start error: {e}", "ERROR")
            self.reset_quick_start_button()

    def connect_mt5_silent(self):
        """Silent MT5 connection for one-click start"""
        try:
            if self.mt5_connector.auto_connect():
                self.is_connected = True
                self.connection_status.config(text="✅ Connected", fg='#3fb950')
                
                # Get account information
                account_info = self.mt5_connector.get_account_info()
                if account_info:
                    self.account_info = account_info
                    
                    # Check market status
                    market_status = self.check_market_status()
                    gold_symbol = self.mt5_connector.get_gold_symbol()
                    
                    market_text = "🟢 Open" if market_status else "🔴 Closed"
                    
                    account_text = f"💰 Account: {account_info['login']} | Balance: ${account_info['balance']:,.2f} | {gold_symbol} | {market_text}"
                    self.account_label.config(text=account_text)
                    
                    self.log_message("✅ MT5 Connected Successfully", "SUCCESS")
                    return True
                else:
                    self.log_message("❌ Failed to get account information", "ERROR")
                    return False
            else:
                self.log_message("❌ Failed to connect to MT5", "ERROR")
                messagebox.showerror("Connection Error", "Failed to connect to MetaTrader5. Please ensure MT5 is running and logged in.")
                return False
                
        except Exception as e:
            self.log_message(f"❌ Connection error: {e}", "ERROR")
            return False

    def calculate_survivability_silent(self):
        """Silent survivability calculation for one-click start"""
        try:
            balance = self.account_info.get('balance', 0)
            if balance <= 0:
                self.log_message("❌ Invalid account balance", "ERROR")
                return False
                
            # Use survivability engine to calculate parameters
            results = self.survivability_engine.calculate_for_balance(
                balance,
                min_lot=0.01,
                trading_mode=self.current_trading_mode
            )
            
            if results and results.get('target_met', False):
                self.current_calculations = results
                
                self.log_message("✅ AI Calculation completed successfully!", "SUCCESS")
                self.log_message(f"🎯 Mode: {self.current_trading_mode.value}", "INFO")
                self.log_message(f"💰 Base Lot: {results['base_lot']:.3f}", "INFO")
                self.log_message(f"📏 Grid Spacing: {results['grid_spacing']} points", "INFO")
                self.log_message(f"🛡️ Survivability: {results.get('realistic_survivability', results['survivability']):,} points", "INFO")
                
                return True
            else:
                self.log_message("❌ Failed to calculate survivability parameters", "ERROR")
                return False
                
        except Exception as e:
            self.log_message(f"❌ Calculation error: {e}", "ERROR")
            return False

    def start_trading_silent(self):
        """Silent trading start for one-click start"""
        try:
            # Initialize Smart Profit Manager
            self.smart_profit_trader = SmartProfitManager(
                self.mt5_connector,
                self.current_calculations,
                self.config
            )
            
            # Start trading
            success = self.smart_profit_trader.start_trading()
            
            if success:
                self.is_trading = True
                
                self.log_message("🚀 AI Smart Profit Trading STARTED!", "SUCCESS")
                survivability = self.current_calculations.get('realistic_survivability', 
                                self.current_calculations.get('survivability', 0))
                self.log_message(f"🛡️ Protection Level: {survivability:,} points", "INFO")
                self.log_message(f"🧠 AI Control: FULL AUTOMATION", "INFO")
                
                # Start real-time monitoring
                self.start_real_time_monitoring()
                
                return True
            else:
                self.log_message("❌ Failed to start AI trading system", "ERROR")
                return False
                
        except Exception as e:
            self.log_message(f"❌ Trading start error: {str(e)}", "ERROR")
            return False

    def reset_quick_start_button(self):
        """Reset quick start button to initial state"""
        self.quick_start_btn.config(
            text="🚀 ONE-CLICK START\\nConnect → Calculate → Trade",
            state='normal',
            bg='#238636'
        )
        self.quick_status.config(text="❌ Setup incomplete - ready to retry")

    def smart_rebalance(self):
        """Execute smart rebalance"""
        try:
            if not self.is_trading or not self.smart_profit_trader:
                messagebox.showwarning("Warning", "Trading must be active to rebalance")
                return
                
            self.log_message("🎯 Executing Smart Rebalance...", "INFO")
            # Call smart rebalance function
            if hasattr(self.smart_profit_trader, 'intelligent_portfolio_rebalance'):
                self.smart_profit_trader.intelligent_portfolio_rebalance()
                self.log_message("✅ Smart Rebalance completed", "SUCCESS")
            else:
                self.log_message("⚠️ Smart Rebalance not available", "WARNING")
                
        except Exception as e:
            self.log_message(f"❌ Smart Rebalance error: {e}", "ERROR")

    def clean_orders(self):
        """Execute order cleanup"""
        try:
            if not self.is_trading or not self.smart_profit_trader:
                messagebox.showwarning("Warning", "Trading must be active to clean orders")
                return
                
            self.log_message("🧹 Executing Order Cleanup...", "INFO")
            # Force order cleanup
            if hasattr(self.smart_profit_trader, 'ai_order_cleanup_analysis'):
                cleanup_results = self.smart_profit_trader.ai_order_cleanup_analysis()
                if cleanup_results.get('cleanup_performed', False):
                    self.log_message(f"✅ Cleanup completed: {cleanup_results['summary']}", "SUCCESS")
                else:
                    self.log_message("ℹ️ No cleanup needed - orders are optimal", "INFO")
            else:
                self.log_message("⚠️ Order cleanup not available", "WARNING")
                
        except Exception as e:
            self.log_message(f"❌ Order cleanup error: {e}", "ERROR")

    def execute_ai_suggestions(self):
        """Execute AI profit suggestions"""
        try:
            if not self.is_trading or not self.smart_profit_trader:
                messagebox.showwarning("Warning", "Trading must be active to execute AI suggestions")
                return
                
            self.log_message("💰 Executing AI Profit Suggestions...", "INFO")
            
            # Get portfolio analysis
            portfolio = self.smart_profit_trader.analyze_portfolio_positions()
            if 'error' not in portfolio:
                positions = portfolio.get('grid_positions', [])
                
                # Find profitable pairs
                profitable_pairs = self.smart_profit_trader.find_profitable_pairs(positions)
                
                if profitable_pairs:
                    # Execute top pairs
                    self.smart_profit_trader.execute_pair_closes(profitable_pairs[:2])
                    self.log_message(f"✅ Executed {len(profitable_pairs[:2])} AI suggestions", "SUCCESS")
                else:
                    self.log_message("ℹ️ No profitable opportunities found", "INFO")
            else:
                self.log_message("❌ Cannot analyze portfolio for suggestions", "ERROR")
                
        except Exception as e:
            self.log_message(f"❌ Execute AI suggestions error: {e}", "ERROR")

    def set_log_filter(self, filter_name):
        """Set log filter"""
        self.current_filter = filter_name
        # Update button colors (simplified)
        self.log_message(f"📋 Log filter set to: {filter_name}", "INFO")

    def clear_logs(self):
        """Clear log display"""
        self.log_display.delete(1.0, tk.END)
        self.log_message("🗑️ Logs cleared", "INFO")

    def check_market_status(self) -> bool:
        """Check if market is currently open"""
        try:
            if not hasattr(self, 'mt5_connector') or not self.mt5_connector:
                return False
                
            current_time = datetime.now()
            
            if current_time.weekday() >= 5:  # Weekend
                return False
                
            import MetaTrader5 as mt5
            gold_symbol = self.mt5_connector.get_gold_symbol()
            if gold_symbol:
                tick = mt5.symbol_info_tick(gold_symbol)
                return tick is not None and tick.time > 0
                
            return False
            
        except Exception as e:
            print(f"Error checking market status: {e}")
            return False

    def on_mode_change(self, event=None):
        """Handle trading mode change"""
        try:
            mode_str = self.mode_var.get()
            self.current_trading_mode = TradingMode[mode_str]
            
            # Update mode description
            mode_descriptions = {
                "SAFE": "🛡️ Safe: 20,000 points survivability",
                "BALANCED": "⚖️ Balanced: 10,000 points survivability", 
                "AGGRESSIVE": "🚀 Aggressive: 8,000 points survivability",
                "TURBO": "⚡ Turbo: 5,000 points survivability"
            }
            
            desc = mode_descriptions.get(mode_str, "🤖 Unknown mode")
            self.mode_desc_label.config(text=desc)
            
            self.log_message(f"🎯 Trading Mode changed to: {mode_str}", "INFO")
            
            # Recalculate if we have connection
            if self.is_connected and self.account_info:
                self.calculate_survivability_silent()
                
        except Exception as e:
            self.log_message(f"❌ Mode change error: {e}", "ERROR")

    def toggle_auto_recovery(self):
        """Toggle auto recovery mode"""
        try:
            new_state = self.auto_recovery_var.get()
            
            self.config['portfolio_recovery']['auto_mode'] = new_state
            
            if new_state:
                self.log_message("💊 Auto Recovery: ENABLED", "SUCCESS")
            else:
                self.log_message("💊 Auto Recovery: DISABLED", "WARNING")
                
            # Update Smart Profit Manager if active
            if hasattr(self, 'smart_profit_trader') and self.smart_profit_trader:
                self.smart_profit_trader.recovery_auto_mode = new_state
                
        except Exception as e:
            self.log_message(f"❌ Toggle auto recovery error: {e}", "ERROR")

    def manual_trigger_recovery(self):
        """Manual trigger recovery system"""
        try:
            if not hasattr(self, 'smart_profit_trader') or not self.smart_profit_trader:
                self.log_message("⚠️ Start trading first", "WARNING")
                messagebox.showwarning("Recovery", "Please start trading first")
                return
                
            self.log_message("💊 Manual Recovery triggered by user", "INFO")
            
            success = self.smart_profit_trader.manual_trigger_recovery()
            
            if success:
                self.log_message("✅ Recovery system activated", "SUCCESS")
            else:
                self.log_message("⚠️ Recovery system already active or no positions", "WARNING")
                
        except Exception as e:
            self.log_message(f"❌ Manual recovery error: {e}", "ERROR")

    def emergency_stop(self):
        """Emergency stop trading"""
        if not self.is_trading:
            return
            
        # Confirm emergency stop
        result = messagebox.askyesno(
            "Emergency Stop", 
            "🛑 EMERGENCY STOP TRADING\\n\\nThis will:\\n• Stop all AI trading\\n• Cancel pending orders\\n• Keep positions open\\n\\nContinue?"
        )
        
        if not result:
            return
            
        try:
            self.log_message("🛑 Emergency stop requested by user", "WARNING")
            
            self.is_trading = False
            
            if self.smart_profit_trader:
                self.smart_profit_trader.stop_trading()
                
            # Reset UI
            self.quick_start_btn.config(
                text="🚀 ONE-CLICK START\\nConnect → Calculate → Trade",
                state='normal',
                bg='#238636'
            )
            
            self.emergency_stop_btn.config(state='disabled')
            self.quick_status.config(text="🛑 Emergency stopped - ready to restart")
            
            self.log_message("✅ Trading system stopped safely", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"❌ Emergency stop error: {str(e)}", "ERROR")

    def start_real_time_monitoring(self):
        """Start real-time monitoring of trading status"""
        if not hasattr(self, 'monitoring_thread') or not self.monitoring_thread.is_alive():
            self.monitoring_thread = threading.Thread(target=self.real_time_monitor, daemon=True)
            self.monitoring_thread.start()

    def real_time_monitor(self):
        """Real-time monitoring thread"""
        update_count = 0
        
        while self.is_trading and self.monitoring:
            try:
                if self.smart_profit_trader:
                    # Get current status from Smart Profit Manager
                    status = self.smart_profit_trader.get_grid_status()
                    
                    # Update GUI every 3 seconds
                    if update_count % 3 == 0:
                        self.root.after(0, self.update_ai_status_display, status)
                        
                    # Check for emergency conditions
                    if status.get('emergency_stop', False):
                        self.root.after(0, self.handle_emergency_triggered)
                        break
                        
                    update_count += 1
                    
                time.sleep(1)  # Update every second
                
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(5)

    def update_ai_status_display(self, status):
        """Update AI status display with enhanced information"""
        try:
            if not status or 'error' in status:
                return
                
            # Update AI Mode and Status
            ai_health = status.get('ai_health_score', 50)
            if hasattr(self, 'smart_profit_trader') and self.smart_profit_trader:
                portfolio = self.smart_profit_trader.analyze_portfolio_positions()
                
                if 'error' not in portfolio:
                    total_pnl = portfolio.get('total_pnl', 0)
                    
                    if total_pnl > 0:
                        ai_mode = "PROFIT OPTIMIZATION"
                        mode_color = '#ffd700'
                    elif abs(total_pnl) < 5:
                        ai_mode = "BALANCED MONITORING"
                        mode_color = '#58a6ff'
                    else:
                        ai_mode = "RECOVERY FOCUS"
                        mode_color = '#f85149'
                else:
                    ai_mode = "ANALYZING"
                    mode_color = '#a5a5a5'
            else:
                ai_mode = "STANDBY"
                mode_color = '#a5a5a5'
                
            self.ai_mode_label.config(text=f"🎯 Mode: {ai_mode}", fg=mode_color)
            self.ai_mode_display.config(text=f"🧠 AI Mode: {ai_mode}", fg=mode_color)
            
            # Update market condition (simplified)
            current_hour = datetime.now().hour
            if current_hour in [8, 9, 13, 14, 15, 16]:
                market_condition = "ACTIVE (1.5x vol)"
                condition_color = '#f59e0b'
            elif current_hour in [22, 23, 0, 1, 2, 3]:
                market_condition = "QUIET (0.7x vol)"
                condition_color = '#6366f1'
            else:
                market_condition = "NORMAL (1.0x vol)"
                condition_color = '#10b981'
                
            self.market_condition_label.config(text=f"📊 Market: {market_condition}", fg=condition_color)
            
            # Update AI Health
            health_color = '#51cf66' if ai_health >= 70 else '#ffd43b' if ai_health >= 40 else '#ff6b6b'
            self.ai_health_label.config(text=f"🧠 AI Health: {ai_health}/100", fg=health_color)
            
            # Update positions and portfolio balance
            positions = status.get('active_positions', 0)
            pnl = status.get('total_pnl', 0)
            
            # Get detailed position info if available
            if hasattr(self, 'smart_profit_trader') and self.smart_profit_trader:
                try:
                    portfolio = self.smart_profit_trader.analyze_portfolio_positions()
                    if 'error' not in portfolio:
                        grid_positions = portfolio.get('grid_positions', [])
                        buy_positions = [p for p in grid_positions if p.direction == "BUY"]
                        sell_positions = [p for p in grid_positions if p.direction == "SELL"]
                        
                        buy_exposure = sum(p.lot_size for p in buy_positions)
                        sell_exposure = sum(p.lot_size for p in sell_positions)
                        
                        self.portfolio_balance_label.config(
                            text=f"⚖️ Balance: {len(buy_positions)} BUY / {len(sell_positions)} SELL"
                        )
                        
                        self.positions_label.config(
                            text=f"📈 Positions: {len(buy_positions)} BUY ({buy_exposure:.3f}L) / {len(sell_positions)} SELL"
                        )
                        
                        # Update balance ratio
                        if len(sell_positions) > 0:
                            ratio = len(buy_positions) / len(sell_positions)
                            if 0.5 <= ratio <= 2.0:
                                ratio_status = "BALANCED"
                                ratio_color = '#51cf66'
                            else:
                                ratio_status = "IMBALANCED"
                                ratio_color = '#ffd43b'
                        else:
                            ratio_status = "NEEDS SELL ORDERS"
                            ratio_color = '#f85149'
                            
                        self.balance_ratio_label.config(
                            text=f"⚖️ Balance: {ratio_status}",
                            fg=ratio_color
                        )
                        
                except:
                    pass
            
            # Update PnL and safety
            pnl_color = '#51cf66' if pnl >= 0 else '#ff6b6b'
            survivability_used = status.get('survivability_used', 0)
            safety_percent = 100 - survivability_used
            
            self.pnl_label.config(
                text=f"💰 PnL: ${pnl:.2f} | 🛡️ Safety: {safety_percent:.1f}%",
                fg=pnl_color
            )
            
            # Update performance metrics
            win_rate = status.get('win_rate', 0)
            trades_opened = status.get('trades_opened', 0)
            trades_closed = status.get('trades_closed', 0)
            drawdown = status.get('current_drawdown', 0)
            
            win_rate_color = '#51cf66' if win_rate >= 60 else '#ffd43b' if win_rate >= 40 else '#ff6b6b'
            self.performance_label.config(
                text=f"🎯 Win Rate: {win_rate:.1f}% | 📊 Trades: {trades_opened}/{trades_closed}",
                fg=win_rate_color
            )
            
            drawdown_color = '#51cf66' if drawdown < 1000 else '#ffd43b' if drawdown < 5000 else '#ff6b6b'
            self.drawdown_label.config(text=f"📉 Drawdown: {drawdown:.0f} pts", fg=drawdown_color)
            
            safety_color = '#51cf66' if safety_percent > 70 else '#ffd43b' if safety_percent > 40 else '#ff6b6b'
            self.survivability_label.config(text=f"🛡️ Safety: {safety_percent:.1f}%", fg=safety_color)
            
            # Update order quality if available
            if hasattr(self, 'smart_profit_trader') and self.smart_profit_trader:
                try:
                    cleanup_status = self.smart_profit_trader.get_order_cleanup_status()
                    
                    total_orders = cleanup_status.get('total_orders', 0)
                    health_score = cleanup_status.get('health_score', 100)
                    issues = cleanup_status.get('issues', {})
                    
                    self.total_orders_label.config(text=f"📊 Total Orders: {total_orders}")
                    
                    score_color = '#51cf66' if health_score >= 80 else '#ffd43b' if health_score >= 60 else '#ff6b6b'
                    self.quality_score_label.config(
                        text=f"🧹 Quality Score: {health_score}/100",
                        fg=score_color
                    )
                    
                    self.quality_issues_label.config(
                        text=f"Issues: 🕒 {issues.get('stale', 0)} | 📏 {issues.get('distant', 0)} | 🔄 {issues.get('redundant', 0)}"
                    )
                    
                except:
                    pass
            
            # Update profit opportunities
            try:
                if hasattr(self, 'smart_profit_trader') and self.smart_profit_trader:
                    portfolio = self.smart_profit_trader.analyze_portfolio_positions()
                    if 'error' not in portfolio:
                        positions = portfolio.get('grid_positions', [])
                        
                        high_profit = len([p for p in positions if p.pnl > 5.0])
                        trailing_eligible = len([p for p in positions if p.pnl > 3.0])
                        
                        profitable_pairs = self.smart_profit_trader.find_profitable_pairs(positions)
                        pair_opportunities = len(profitable_pairs)
                        
                        self.high_profit_label.config(text=f"💎 High Profit Positions: {high_profit}")
                        self.trailing_stop_label.config(text=f"📈 Trailing Stop Eligible: {trailing_eligible}")
                        self.pair_opportunities_label.config(text=f"🎯 Pair Close Opportunities: {pair_opportunities}")
                        
                        # AI Recommendation
                        if pair_opportunities > 0:
                            recommendation = f"Execute {pair_opportunities} pair closes"
                            rec_color = '#ffd700'
                            self.execute_ai_btn.config(state='normal')
                        elif high_profit > 0:
                            recommendation = "Monitor high profit positions"
                            rec_color = '#10b981'
                            self.execute_ai_btn.config(state='disabled')
                        else:
                            recommendation = "Hold & Monitor - Portfolio stable"
                            rec_color = '#58a6ff'
                            self.execute_ai_btn.config(state='disabled')
                            
                        self.ai_recommendation_label.config(
                            text=f"💡 Recommendation: {recommendation}",
                            fg=rec_color
                        )
                        
            except:
                pass
                
            # Update recovery status
            recovery_status = status.get('recovery_system', {})
            if recovery_status.get('active', False):
                elapsed = recovery_status.get('elapsed_minutes', 0)
                self.recovery_status_label.config(
                    text=f"Status: 🟡 ACTIVE ({elapsed:.1f}min)",
                    fg='#ffd700'
                )
            else:
                if pnl >= 0:
                    self.recovery_status_label.config(
                        text="Status: 🟢 STANDBY (Healthy)",
                        fg='#3fb950'
                    )
                else:
                    self.recovery_status_label.config(
                        text="Status: 🟡 MONITORING (Loss detected)",
                        fg='#ffd43b'
                    )
                    
            trigger_loss = self.config.get('portfolio_recovery', {}).get('trigger_loss', -50)
            self.recovery_trigger_label.config(
                text=f"Trigger: ${trigger_loss} | Current: ${pnl:.2f}"
            )
                
        except Exception as e:
            print(f"Status update error: {e}")

    def handle_emergency_triggered(self):
        """Handle automatic emergency stop"""
        try:
            self.is_trading = False
            
            self.quick_start_btn.config(
                text="🚀 ONE-CLICK START\\nConnect → Calculate → Trade",
                state='normal',
                bg='#238636'
            )
            
            self.emergency_stop_btn.config(state='disabled')
            self.quick_status.config(text="🚨 Emergency stopped - check logs for details")
            
            self.log_message("🚨 AUTOMATIC EMERGENCY STOP TRIGGERED!", "ERROR")
            
            messagebox.showerror(
                "🚨 Emergency Stop", 
                "Automatic emergency stop was triggered!\\n\\nCheck the logs for details.\\nPositions remain open for manual management."
            )
            
        except Exception as e:
            print(f"Emergency handler error: {e}")

    def setup_status_monitoring(self):
        """Setup status monitoring thread"""
        self.monitoring = True
        self.monitoring_thread = threading.Thread(target=self.monitor_system, daemon=True)
        self.monitoring_thread.start()

    def monitor_system(self):
        """Monitor system status"""
        while self.monitoring:
            try:
                if self.is_connected and self.mt5_connector:
                    # Update account info
                    account_info = self.mt5_connector.get_account_info()
                    if account_info:
                        self.account_info = account_info
                        
                time.sleep(10)  # Monitor every 10 seconds
                
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(30)

    def log_message(self, message: str, level: str = "INFO"):
        """Enhanced log message with filtering"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Check filter
            if self.current_filter != "All":
                filter_keywords = {
                    "🧠 AI": ["AI", "Mode", "Health", "Intelligence"],
                    "🎯 Grid": ["Grid", "Order", "Position", "Spacing"],
                    "💰 Profit": ["Profit", "PnL", "Pair", "Close"],
                    "🧹 Cleanup": ["Cleanup", "Clean", "Quality", "Remove"],
                    "💊 Recovery": ["Recovery", "Trigger", "Emergency"]
                }
                
                keywords = filter_keywords.get(self.current_filter, [])
                if not any(keyword.lower() in message.lower() for keyword in keywords):
                    return
            
            formatted_message = f"[{timestamp}] {message}\\n"
            
            self.log_display.insert(tk.END, formatted_message, level)
            self.log_display.see(tk.END)
            
            # Keep only last 1000 lines
            lines = self.log_display.get("1.0", tk.END).count('\\n')
            if lines > 1000:
                self.log_display.delete("1.0", "100.0")
            
            # Print to console as well
            print(formatted_message.strip())
            
        except Exception as e:
            print(f"Logging error: {e}")

    def on_closing(self):
        """Handle application closing"""
        try:
            if self.is_trading:
                result = messagebox.askyesnocancel(
                    "Trading Active", 
                    "AI Trading is active. How would you like to proceed?\\n\\n• YES = Stop trading safely (recommended)\\n• NO = Force close (emergency)\\n• CANCEL = Don't exit"
                )
                
                if result is True:  # YES - Safe stop
                    self.log_message("🛑 Safely stopping AI trading before exit...", "WARNING")
                    if self.smart_profit_trader:
                        self.smart_profit_trader.stop_trading()
                    time.sleep(2)
                    
                elif result is False:  # NO - Force close
                    self.log_message("🚨 Force closing application...", "ERROR")
                    
                else:  # CANCEL - Don't exit
                    return
                    
            # Stop monitoring
            self.monitoring = False
            
            # Disconnect MT5
            if hasattr(self, 'mt5_connector'):
                try:
                    import MetaTrader5 as mt5
                    mt5.shutdown()
                except:
                    pass
                
            # Save config
            self.save_config()
            
            # Final log
            self.log_message("👋 AI Smart Profit Trading System Closed Safely", "INFO")
            
            self.root.destroy()
            
        except Exception as e:
            print(f"Closing error: {e}")
            self.root.destroy()
    
    def run(self):
        """Run the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Welcome message
        self.log_message("🧠 AI Smart Profit Trading System Initialized", "SUCCESS")
        self.log_message("🏆 Target: 20,000+ Points Survivability", "INFO")
        self.log_message("💰 One-Click Operation: Connect → Calculate → Trade", "INFO")
        self.log_message("🔗 Ready for ONE-CLICK START", "INFO")
        
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        if not getattr(sys, 'frozen', False):
            # Check if required files exist
            required_files = [
                'mt5_auto_connector.py',
                'smart_profit_manager.py', 
                'survivability_engine.py',
                'ai_money_manager.py',
                'gold_hedge_calculator.py'
            ]
            
            missing_files = [f for f in required_files if not os.path.exists(f)]
            
            if missing_files:
                print("⚠️ Missing required files:")
                for file in missing_files:
                    print(f"   - {file}")
                print("\\nPlease ensure all modules are in the same directory.")
                print("Note: Enhanced GUI with AI Smart System!")
                input("Press Enter to continue anyway...")
            
        # Start Enhanced GUI
        app = AISmartProfitGUI()
        app.run()
        
    except KeyboardInterrupt:
        print("\\n🛑 Application stopped by user")
    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
   main()
