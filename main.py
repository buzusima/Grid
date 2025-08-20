"""
AI Smart Profit Gold Trading System with 20,000+ Points Survivability
Main GUI Controller - main.py (Updated for AI Smart Profit Manager)
Created for MetaTrader5 Gold Trading with True AI Intelligence
UPDATED VERSION - Using AI Smart Profit Manager as primary trading engine
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
    from ai_smart_profit_manager import AISmartProfitManager  # Updated import
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
        
        self.api_base_url = "http://123.253.62.50:8080/api"

    
    def setup_main_window(self):
        """Setup main window properties"""
        self.root.title("🧠 AI Smart Profit Gold Trading System")
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
            "ai_smart_profit": {  # New AI configuration section
                "analysis_interval": 3,
                "market_memory_size": 100,
                "decision_confidence_threshold": 0.6,
                "max_positions_per_direction": 5,
                "dynamic_spacing_enabled": True,
                "cross_direction_trading": True,
                "adaptive_risk_management": True
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
            self.ai_smart_trader = None  # Will be initialized after MT5 connection
            
            # System status
            self.is_connected = False
            self.is_trading = False
            self.monitoring = True
            self.account_info = {}
            self.current_calculations = {}
            
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to initialize components: {e}")

    def create_gui(self):
        """Create main GUI interface"""
        main_frame = tk.Frame(self.root, bg='#1a1a2e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header section
        self.create_header_section(main_frame)
        
        # Connection and calculation section
        self.create_connection_section(main_frame)
        
        # AI Smart Profit controls section
        self.create_ai_smart_profit_section(main_frame)
        
        # Trading controls section
        self.create_trading_controls_section(main_frame)
        
        # AI Status and monitoring section
        self.create_ai_status_monitoring_section(main_frame)
        
        # Log section
        self.create_log_section(main_frame)

    def create_header_section(self, parent):
        """Create header section"""
        header_frame = tk.LabelFrame(
            parent,
            text="🧠 AI Smart Profit Gold Trading System",
            font=('Arial', 14, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=3
        )
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        header_label = tk.Label(
            header_frame,
            text="🏆 True AI Intelligence • Dynamic Market Analysis • Intelligent Decision Making",
            font=('Arial', 12),
            fg='#ffffff',
            bg='#16213e'
        )
        header_label.pack(pady=10)

    def create_connection_section(self, parent):
        """Create connection and calculation section"""
        conn_frame = tk.LabelFrame(
            parent,
            text="🔌 MT5 Connection & AI Calculation",
            font=('Arial', 12, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Connection row
        conn_row = tk.Frame(conn_frame, bg='#16213e')
        conn_row.pack(fill=tk.X, padx=10, pady=5)
        
        self.connection_status = tk.Label(
            conn_row,
            text="❌ Disconnected",
            font=('Arial', 10, 'bold'),
            fg='#ff6b6b',
            bg='#16213e'
        )
        self.connection_status.pack(side=tk.LEFT)
        
        self.connect_btn = tk.Button(
            conn_row,
            text="🔌 Connect MT5",
            font=('Arial', 10, 'bold'),
            bg='#51cf66',
            fg='#1a1a2e',
            relief='raised',
            bd=2,
            command=self.connect_mt5
        )
        self.connect_btn.pack(side=tk.LEFT, padx=(20, 0))
        
        # Trading mode selection
        mode_row = tk.Frame(conn_frame, bg='#16213e')
        mode_row.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(mode_row, text="🎯 Trading Mode:", font=('Arial', 10), fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)
        
        self.mode_var = tk.StringVar(value=self.current_trading_mode.value)
        self.mode_combo = ttk.Combobox(
            mode_row,
            textvariable=self.mode_var,
            values=["SAFE", "BALANCED", "AGGRESSIVE", "TURBO"],
            width=15,
            state="readonly"
        )
        self.mode_combo.pack(side=tk.LEFT, padx=(10, 0))
        self.mode_combo.bind('<<ComboboxSelected>>', self.on_mode_change)
        
        # Account info
        self.account_label = tk.Label(
            conn_frame,
            text="💰 Account: Not connected",
            font=('Arial', 10),
            fg='#ffffff',
            bg='#16213e'
        )
        self.account_label.pack(padx=10, pady=5)
        
        # Calculate button
        self.calculate_btn = tk.Button(
            conn_frame,
            text="🧠 Calculate AI Parameters",
            font=('Arial', 11, 'bold'),
            bg='#339af0',
            fg='#ffffff',
            relief='raised',
            bd=2,
            state='disabled',
            command=self.calculate_survivability
        )
        self.calculate_btn.pack(pady=10)

    def create_ai_smart_profit_section(self, parent):
        """Create AI Smart Profit management section"""
        ai_frame = tk.LabelFrame(
            parent,
            text="🧠 AI Smart Intelligence Controls",
            font=('Arial', 12, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        ai_frame.pack(fill=tk.X, pady=(0, 10))
        
        # AI Configuration row
        ai_config_row = tk.Frame(ai_frame, bg='#16213e')
        ai_config_row.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(ai_config_row, text="🔬 AI Analysis:", font=('Arial', 10), fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)
        
        self.ai_interval_var = tk.StringVar(value=str(self.config.get('ai_smart_profit', {}).get('analysis_interval', 3)))
        self.ai_interval_combo = ttk.Combobox(
            ai_config_row,
            textvariable=self.ai_interval_var,
            values=["1", "3", "5", "10"],
            width=8,
            state="readonly"
        )
        self.ai_interval_combo.pack(side=tk.LEFT, padx=(10, 0))
        self.ai_interval_combo.bind('<<ComboboxSelected>>', self.on_ai_config_change)
        
        tk.Label(ai_config_row, text="seconds", font=('Arial', 9), fg='#adb5bd', bg='#16213e').pack(side=tk.LEFT, padx=(5, 0))
        
        # AI Features row
        ai_features_row = tk.Frame(ai_frame, bg='#16213e')
        ai_features_row.pack(fill=tk.X, padx=10, pady=5)
        
        self.dynamic_spacing_var = tk.BooleanVar(value=self.config.get('ai_smart_profit', {}).get('dynamic_spacing_enabled', True))
        self.dynamic_spacing_check = tk.Checkbutton(
            ai_features_row,
            text="🎯 Dynamic Spacing",
            variable=self.dynamic_spacing_var,
            font=('Arial', 9),
            fg='#ffffff',
            bg='#16213e',
            selectcolor='#16213e',
            command=self.on_ai_config_change
        )
        self.dynamic_spacing_check.pack(side=tk.LEFT)
        
        self.cross_direction_var = tk.BooleanVar(value=self.config.get('ai_smart_profit', {}).get('cross_direction_trading', True))
        self.cross_direction_check = tk.Checkbutton(
            ai_features_row,
            text="🔄 Cross-Direction",
            variable=self.cross_direction_var,
            font=('Arial', 9),
            fg='#ffffff',
            bg='#16213e',
            selectcolor='#16213e',
            command=self.on_ai_config_change
        )
        self.cross_direction_check.pack(side=tk.LEFT, padx=(20, 0))
        
        self.adaptive_risk_var = tk.BooleanVar(value=self.config.get('ai_smart_profit', {}).get('adaptive_risk_management', True))
        self.adaptive_risk_check = tk.Checkbutton(
            ai_features_row,
            text="🛡️ Adaptive Risk",
            variable=self.adaptive_risk_var,
            font=('Arial', 9),
            fg='#ffffff',
            bg='#16213e',
            selectcolor='#16213e',
            command=self.on_ai_config_change
        )
        self.adaptive_risk_check.pack(side=tk.LEFT, padx=(20, 0))
        
        # AI Performance row
        ai_perf_row = tk.Frame(ai_frame, bg='#16213e')
        ai_perf_row.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(ai_perf_row, text="🎯 AI Accuracy:", font=('Arial', 10), fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)
        
        self.ai_accuracy_display = tk.Label(
            ai_perf_row,
            text="---%",
            font=('Arial', 10, 'bold'),
            fg='#51cf66',
            bg='#16213e'
        )
        self.ai_accuracy_display.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Label(ai_perf_row, text="🧠 Decisions:", font=('Arial', 10), fg='#ffffff', bg='#16213e').pack(side=tk.LEFT, padx=(30, 0))
        
        self.ai_decisions_display = tk.Label(
            ai_perf_row,
            text="0",
            font=('Arial', 10),
            fg='#74c0fc',
            bg='#16213e'
        )
        self.ai_decisions_display.pack(side=tk.LEFT, padx=(10, 0))

    def create_trading_controls_section(self, parent):
        """Create trading controls section"""
        control_frame = tk.LabelFrame(
            parent,
            text="🎮 AI Trading Controls",
            font=('Arial', 12, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Main control buttons
        btn_frame = tk.Frame(control_frame, bg='#16213e')
        btn_frame.pack(pady=10)
        
        self.start_btn = tk.Button(
            btn_frame,
            text="🧠 Start AI Smart Trading",
            font=('Arial', 12, 'bold'),
            bg='#51cf66',
            fg='#1a1a2e',
            relief='raised',
            bd=3,
            width=22,
            command=self.start_ai_trading
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹️ Stop AI Trading",
            font=('Arial', 12, 'bold'),
            bg='#ff6b6b',
            fg='#ffffff',
            relief='raised',
            bd=3,
            width=20,
            command=self.stop_ai_trading,
            state='disabled'
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.emergency_btn = tk.Button(
            btn_frame,
            text="🚨 Emergency Stop",
            font=('Arial', 12, 'bold'),
            bg='#e03131',
            fg='#ffffff',
            relief='raised',
            bd=3,
            width=18,
            command=self.emergency_stop,
            state='disabled'
        )
        self.emergency_btn.pack(side=tk.LEFT, padx=5)

    def create_ai_status_monitoring_section(self, parent):
        """Create AI status and monitoring section"""
        status_frame = tk.LabelFrame(
            parent,
            text="📊 AI Real-time Intelligence Status",
            font=('Arial', 12, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # AI Status display in grid
        status_grid = tk.Frame(status_frame, bg='#16213e')
        status_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Row 1: AI Intelligence stats
        row1 = tk.Frame(status_grid, bg='#16213e')
        row1.pack(fill=tk.X, pady=2)
        
        self.ai_health_label = tk.Label(row1, text="🏥 AI Health: --/100", font=('Arial', 10, 'bold'), fg='#51cf66', bg='#16213e')
        self.ai_health_label.pack(side=tk.LEFT)
        
        self.portfolio_status_label = tk.Label(row1, text="💰 Portfolio: ANALYZING", font=('Arial', 10), fg='#74c0fc', bg='#16213e')
        self.portfolio_status_label.pack(side=tk.LEFT, padx=(50, 0))
        
        self.market_condition_label = tk.Label(row1, text="🔬 Market: SCANNING", font=('Arial', 10), fg='#ffd43b', bg='#16213e')
        self.market_condition_label.pack(side=tk.LEFT, padx=(50, 0))
        
        # Row 2: Trading stats
        row2 = tk.Frame(status_grid, bg='#16213e')
        row2.pack(fill=tk.X, pady=2)
        
        self.positions_label = tk.Label(row2, text="📈 Positions: 0", font=('Arial', 10), fg='#74c0fc', bg='#16213e')
        self.positions_label.pack(side=tk.LEFT)
        
        self.pnl_label = tk.Label(row2, text="💰 PnL: $0.00", font=('Arial', 10, 'bold'), fg='#51cf66', bg='#16213e')
        self.pnl_label.pack(side=tk.LEFT, padx=(50, 0))
        
        self.risk_usage_label = tk.Label(row2, text="🛡️ Risk: 0%", font=('Arial', 10), fg='#51cf66', bg='#16213e')
        self.risk_usage_label.pack(side=tk.LEFT, padx=(50, 0))
        
        # Row 3: AI Performance stats
        row3 = tk.Frame(status_grid, bg='#16213e')
        row3.pack(fill=tk.X, pady=2)
        
        self.volatility_label = tk.Label(row3, text="📊 Volatility: --/100", font=('Arial', 10), fg='#ffd43b', bg='#16213e')
        self.volatility_label.pack(side=tk.LEFT)
        
        self.trend_strength_label = tk.Label(row3, text="📈 Trend: --", font=('Arial', 10), fg='#74c0fc', bg='#16213e')
        self.trend_strength_label.pack(side=tk.LEFT, padx=(50, 0))
        
        self.ai_confidence_label = tk.Label(row3, text="🎯 Confidence: --%", font=('Arial', 10), fg='#51cf66', bg='#16213e')
        self.ai_confidence_label.pack(side=tk.LEFT, padx=(50, 0))

    def create_log_section(self, parent):
        """Create logging section"""
        log_frame = tk.LabelFrame(
            parent,
            text="📜 AI Intelligence Logs",
            font=('Arial', 11, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Log display
        self.log_display = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            font=('Consolas', 9),
            bg='#2c2c54',
            fg='#ffffff',
            insertbackground='#ffffff',
            selectbackground='#40407a'
        )
        self.log_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure log colors
        self.log_display.tag_configure("SUCCESS", foreground="#51cf66")
        self.log_display.tag_configure("ERROR", foreground="#ff6b6b")
        self.log_display.tag_configure("WARNING", foreground="#ffd43b")
        self.log_display.tag_configure("INFO", foreground="#74c0fc")
        self.log_display.tag_configure("AI", foreground="#9775fa")

    def on_mode_change(self, event=None):
        """Handle trading mode change"""
        try:
            mode_str = self.mode_var.get()
            self.current_trading_mode = TradingMode[mode_str]
            self.log_message(f"🎯 Trading Mode changed to: {mode_str}", "INFO")
            
            # Update AI config if trading is active
            if self.is_trading and hasattr(self, 'ai_smart_trader') and self.ai_smart_trader:
                self.log_message("🧠 AI adapting to new trading mode...", "AI")
            
            # Recalculate if we have connection
            if self.is_connected and self.account_info:
                self.calculate_survivability()
                
        except Exception as e:
            self.log_message(f"❌ Mode change error: {e}", "ERROR")

    def on_ai_config_change(self, event=None):
        """Handle AI configuration change"""
        try:
            # Update AI config
            self.config['ai_smart_profit']['analysis_interval'] = int(self.ai_interval_var.get())
            self.config['ai_smart_profit']['dynamic_spacing_enabled'] = self.dynamic_spacing_var.get()
            self.config['ai_smart_profit']['cross_direction_trading'] = self.cross_direction_var.get()
            self.config['ai_smart_profit']['adaptive_risk_management'] = self.adaptive_risk_var.get()
            
            self.log_message("🧠 AI Configuration updated", "AI")
            
            # Apply to active AI trader if running
            if self.is_trading and hasattr(self, 'ai_smart_trader') and self.ai_smart_trader:
                self.apply_ai_config_changes()
                
        except Exception as e:
            self.log_message(f"❌ AI config error: {e}", "ERROR")

    def apply_ai_config_changes(self):
        """Apply AI configuration changes to active trader"""
        try:
            if hasattr(self, 'ai_smart_trader') and self.ai_smart_trader:
                # Update AI config
                self.ai_smart_trader.ai_config.update({
                    'analysis_interval': int(self.ai_interval_var.get()),
                    'dynamic_spacing_enabled': self.dynamic_spacing_var.get(),
                    'cross_direction_trading': self.cross_direction_var.get(),
                    'adaptive_risk_management': self.adaptive_risk_var.get()
                })
                
                self.log_message("🧠 AI real-time configuration applied", "AI")
                
        except Exception as e:
            self.log_message(f"❌ AI config apply error: {e}", "ERROR")

    def connect_mt5(self):
        """Connect to MetaTrader5"""
        try:
            self.log_message("🔌 Connecting to MetaTrader5...", "INFO")
            
            if self.mt5_connector.auto_connect():
                self.is_connected = True
                self.connection_status.config(text="✅ Connected", fg='#51cf66')
                
                # Get account information
                account_info = self.mt5_connector.get_account_info()
                if account_info:
                    self.account_info = account_info
                    
                    # Check market status
                    market_status = self.check_market_status()
                    gold_symbol = self.mt5_connector.get_gold_symbol()
                    
                    market_text = "🟢 Open" if market_status else "🔴 Closed"
                    market_color = '#51cf66' if market_status else '#ff6b6b'
                    
                    account_text = f"💰 Account: {account_info['login']} | Balance: ${account_info['balance']:,.2f} | {gold_symbol} | Market: {market_text}"
                    self.account_label.config(text=account_text, fg=market_color if not market_status else '#ffffff')
                    
                    # Enable calculate button
                    self.calculate_btn.config(state='normal')
                    self.connect_btn.config(text="✅ Connected", state='disabled')
                    
                    self.log_message("✅ MT5 Connected Successfully", "SUCCESS")
                    self.log_message(f"📊 Account: {account_info['login']} | Balance: ${account_info['balance']:,.2f}", "INFO")
                    
                else:
                    self.log_message("❌ Failed to get account information", "ERROR")
                    
            else:
                self.log_message("❌ Failed to connect to MT5", "ERROR")
                messagebox.showerror("Connection Error", "Failed to connect to MetaTrader5. Please ensure MT5 is running and logged in.")
                
        except Exception as e:
            self.log_message(f"❌ Connection error: {e}", "ERROR")
            messagebox.showerror("Error", f"Connection error: {e}")

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

    def calculate_survivability(self):
        """Calculate and display survivability parameters"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to MT5 first")
            return
            
        try:
            balance = self.account_info.get('balance', 0)
            if balance <= 0:
                raise ValueError("Invalid account balance")
                
            self.log_message("🧠 AI Calculating optimal parameters...", "AI")
            
            # Use survivability engine to calculate parameters
            results = self.survivability_engine.calculate_for_balance(
                balance, 
                trading_mode=self.current_trading_mode
            )
            
            if results and results.get('target_met', False):
                self.current_calculations = results
                
                # Display results
                self.log_message("✅ AI Calculation completed successfully!", "SUCCESS")
                self.log_message(f"🎯 Mode: {self.current_trading_mode.value}", "AI")
                self.log_message(f"💰 Base Lot: {results['base_lot']:.3f}", "INFO")
                self.log_message(f"📏 Grid Spacing: {results['grid_spacing']} points", "INFO")
                self.log_message(f"📊 Max Levels: {results['max_levels']}", "INFO")
                self.log_message(f"🛡️ Survivability: {results['realistic_survivability']:,} points", "INFO")
                self.log_message(f"💪 Safety Margin: {results['safety_margin_percentage']:.1f}%", "INFO")
                
                # Enable trading buttons
                self.start_btn.config(state='normal')
                
            else:
                self.log_message("❌ Failed to calculate survivability parameters", "ERROR")
                messagebox.showerror("Calculation Error", "Failed to calculate optimal parameters for your account")
                
        except Exception as e:
            self.log_message(f"❌ Calculation error: {e}", "ERROR")
            messagebox.showerror("Error", f"Calculation error: {e}")

    def start_ai_trading(self):
        """Start AI Smart Profit trading"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to MT5 first")
            return
            
        if not self.current_calculations:
            messagebox.showwarning("Warning", "Please calculate AI parameters first")
            return
        
        try:
            self.log_message("🧠 Initializing AI Smart Profit Trading System...", "AI")
            
            # Initialize AI Smart Profit Manager
            self.ai_smart_trader = AISmartProfitManager(
                self.mt5_connector,
                self.current_calculations,
                self.config
            )
            
            # Start AI trading
            success = self.ai_smart_trader.start_ai_trading()
            
            if success:
                self.is_trading = True
                
                # Update GUI
                self.start_btn.config(state='disabled', bg='#6c757d')
                self.stop_btn.config(state='normal', bg='#ff6b6b')
                self.emergency_btn.config(state='normal', bg='#e03131')
                
                self.log_message("🚀 AI SMART PROFIT TRADING STARTED!", "SUCCESS")
                survivability = self.current_calculations.get('realistic_survivability', 0)
                self.log_message(f"🛡️ Protection Level: {survivability:,} points", "AI")
                self.log_message(f"🧠 AI Intelligence: FULLY OPERATIONAL", "AI")
                self.log_message(f"🔬 Market Analysis: CONTINUOUS", "AI")
                self.log_message(f"🎯 Decision Making: AUTONOMOUS", "AI")
                
                # Start real-time AI monitoring
                self.start_ai_real_time_monitoring()
                
            else:
                self.log_message("❌ Failed to start AI trading system", "ERROR")
                messagebox.showerror("Error", "Failed to start AI Smart Profit trading system")
                
        except Exception as e:
            self.log_message(f"❌ AI Trading start error: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Failed to start AI trading: {str(e)}")

    def stop_ai_trading(self):
        """Stop AI Smart Profit trading"""
        if not self.is_trading:
            return
            
        try:
            self.log_message("🛑 Stopping AI Smart Profit Trading...", "WARNING")
            
            self.is_trading = False
            
            if self.ai_smart_trader:
                self.ai_smart_trader.stop_ai_trading()
                
            # Update GUI
            self.start_btn.config(state='normal', bg='#51cf66')
            self.stop_btn.config(state='disabled', bg='#6c757d')
            self.emergency_btn.config(state='disabled', bg='#6c757d')
            
            self.log_message("✅ AI Smart Profit Trading STOPPED", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"❌ Stop AI trading error: {str(e)}", "ERROR")

    def emergency_stop(self):
        """Emergency stop AI trading"""
        if not self.is_trading:
            return
            
        # Confirm emergency stop
        result = messagebox.askyesno(
            "Emergency Stop", 
            "🚨 EMERGENCY STOP AI TRADING\n\nThis will:\n• Stop all AI decision making\n• Cancel pending orders\n• Keep positions open\n\nPositions will NOT be closed automatically.\n\nContinue?"
        )
        
        if not result:
            return
            
        try:
            self.log_message("🚨 Emergency stop requested by user", "WARNING")
            
            self.is_trading = False
            
            if self.ai_smart_trader:
                # Stop AI system
                self.ai_smart_trader.stop_ai_trading()
                
            # Update GUI
            self.start_btn.config(state='normal', bg='#51cf66')
            self.stop_btn.config(state='disabled', bg='#6c757d')
            self.emergency_btn.config(state='disabled', bg='#6c757d')
            
            self.log_message("✅ AI trading system stopped safely", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"❌ Emergency stop error: {str(e)}", "ERROR")

    def start_ai_real_time_monitoring(self):
        """Start real-time AI monitoring"""
        if not hasattr(self, 'ai_monitoring_thread') or not self.ai_monitoring_thread.is_alive():
            self.ai_monitoring_thread = threading.Thread(target=self.ai_real_time_monitor, daemon=True)
            self.ai_monitoring_thread.start()

    def ai_real_time_monitor(self):
        """Real-time AI monitoring thread"""
        update_count = 0
        
        while self.is_trading and self.monitoring:
            try:
                if self.ai_smart_trader:
                    # Get current AI status
                    ai_status = self.ai_smart_trader.get_ai_system_status()
                    
                    # Update GUI every 3 seconds
                    if update_count % 3 == 0:
                        self.root.after(0, self.update_ai_status_display, ai_status)
                        
                    # Check for AI emergency conditions
                    if not ai_status.get('ai_active', False):
                        self.root.after(0, self.handle_ai_emergency_triggered)
                        break
                        
                    update_count += 1
                    
                time.sleep(1)  # Update every second
                
            except Exception as e:
                print(f"AI Monitor error: {e}")
                time.sleep(5)

    def update_ai_status_display(self, ai_status):
        """Update real-time AI status display"""
        try:
            if not ai_status or 'error' in ai_status:
                return
                
            # Update AI Intelligence stats
            ai_health = ai_status.get('ai_health_score', 0)
            portfolio_status = ai_status.get('portfolio_status', 'UNKNOWN')
            
            health_color = '#51cf66' if ai_health >= 70 else '#ffd43b' if ai_health >= 40 else '#ff6b6b'
            self.ai_health_label.config(text=f"🏥 AI Health: {ai_health:.0f}/100", fg=health_color)
            
            status_colors = {
                'PROFITABLE': '#51cf66',
                'BALANCED': '#ffd43b', 
                'LOSING': '#ff6b6b'
            }
            status_color = status_colors.get(portfolio_status, '#74c0fc')
            self.portfolio_status_label.config(text=f"💰 Portfolio: {portfolio_status}", fg=status_color)
            
            # Update Market Analysis
            market_analysis = ai_status.get('market_analysis')
            if market_analysis:
                condition = market_analysis.get('condition', 'UNKNOWN')
                volatility = market_analysis.get('volatility_score', 0)
                trend = market_analysis.get('trend_strength', 0)
                
                condition_colors = {
                    'TRENDING_UP': '#51cf66',
                    'TRENDING_DOWN': '#ff6b6b',
                    'RANGING': '#ffd43b',
                    'HIGH_VOLATILITY': '#ff9500',
                    'LOW_VOLATILITY': '#74c0fc'
                }
                condition_color = condition_colors.get(condition, '#ffd43b')
                self.market_condition_label.config(text=f"🔬 Market: {condition}", fg=condition_color)
                
                volatility_color = '#ff6b6b' if volatility > 70 else '#ffd43b' if volatility > 40 else '#51cf66'
                self.volatility_label.config(text=f"📊 Volatility: {volatility:.0f}/100", fg=volatility_color)
                
                trend_direction = "📈" if trend > 0 else "📉" if trend < 0 else "📊"
                trend_color = '#51cf66' if abs(trend) > 50 else '#ffd43b'
                self.trend_strength_label.config(text=f"{trend_direction} Trend: {abs(trend):.0f}", fg=trend_color)
            
            # Update Trading stats
            positions = ai_status.get('active_positions', 0)
            self.positions_label.config(text=f"📈 Positions: {positions}")
            
            # Calculate PnL from account info
            account_balance = ai_status.get('account_balance', 0)
            account_equity = ai_status.get('account_equity', 0)
            pnl = account_equity - account_balance
            
            pnl_color = '#51cf66' if pnl >= 0 else '#ff6b6b'
            self.pnl_label.config(text=f"💰 PnL: ${pnl:.2f}", fg=pnl_color)
            
            # Update Risk usage
            risk_ratio = ai_status.get('risk_ratio', 0)
            risk_pct = risk_ratio * 100
            
            risk_color = '#51cf66' if risk_pct < 30 else '#ffd43b' if risk_pct < 60 else '#ff6b6b'
            self.risk_usage_label.config(text=f"🛡️ Risk: {risk_pct:.1f}%", fg=risk_color)
            
            # Update AI Performance
            ai_accuracy = ai_status.get('ai_accuracy', 0)
            total_decisions = ai_status.get('total_decisions', 0)
            market_confidence = ai_status.get('market_confidence', 0)
            
            accuracy_color = '#51cf66' if ai_accuracy >= 0.7 else '#ffd43b' if ai_accuracy >= 0.5 else '#ff6b6b'
            self.ai_accuracy_display.config(text=f"{ai_accuracy:.1%}", fg=accuracy_color)
            
            self.ai_decisions_display.config(text=f"{total_decisions}")
            
            confidence_color = '#51cf66' if market_confidence >= 0.7 else '#ffd43b' if market_confidence >= 0.5 else '#ff6b6b'
            self.ai_confidence_label.config(text=f"🎯 Confidence: {market_confidence:.1%}", fg=confidence_color)
                    
        except Exception as e:
            print(f"AI Status update error: {e}")

    def handle_ai_emergency_triggered(self):
        """Handle AI emergency stop"""
        try:
            self.is_trading = False
            
            self.start_btn.config(state='normal', bg='#51cf66')
            self.stop_btn.config(state='disabled', bg='#6c757d')
            self.emergency_btn.config(state='disabled', bg='#6c757d')
            
            self.log_message("🚨 AI EMERGENCY PROTECTION TRIGGERED!", "ERROR")
            
            messagebox.showerror(
                "🚨 AI Emergency Stop", 
                "AI Emergency Protection was triggered!\n\nCheck the logs for details.\nAI detected critical risk conditions."
            )
            
        except Exception as e:
            print(f"AI Emergency handler error: {e}")

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
                        
                time.sleep(5)  # Monitor every 5 seconds
                
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(10)

    def log_message(self, message: str, level: str = "INFO"):
        """Log message to display"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}\n"
            
            self.log_display.insert(tk.END, formatted_message, level)
            self.log_display.see(tk.END)
            
            # Print to console as well
            print(formatted_message.strip())
            
        except Exception as e:
            print(f"Logging error: {e}")

    def on_closing(self):
        """Handle application closing"""
        try:
            if self.is_trading:
                result = messagebox.askyesnocancel(
                    "AI Trading Active", 
                    "AI Trading is active. Stop AI trading before exit?\n\n• YES = Stop AI trading (keep positions)\n• NO = Force close\n• CANCEL = Don't exit"
                )
                
                if result is True:  # YES - Stop trading
                    self.stop_ai_trading()
                    time.sleep(2)
                    
                elif result is False:  # NO - Force close
                    self.emergency_stop()
                    time.sleep(3)
                    
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
        self.log_message("🏆 True AI Intelligence for Gold Trading", "AI")
        self.log_message("🔬 Dynamic Market Analysis & Decision Making", "AI")
        self.log_message("🎯 Intelligent Positioning & Risk Management", "AI")
        self.log_message("🔗 Ready to connect to MetaTrader5", "INFO")
        
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        if not getattr(sys, 'frozen', False):
            # Check if required files exist
            required_files = [
                'mt5_auto_connector.py',
                'ai_smart_profit_manager.py',  # Updated requirement
                'survivability_engine.py',
                'ai_money_manager.py',
                'gold_hedge_calculator.py',
                'api_connector.py'
            ]
            
            missing_files = [f for f in required_files if not os.path.exists(f)]
            
            if missing_files:
                print("⚠️ Missing required files:")
                for file in missing_files:
                    print(f"   - {file}")
                print("\nPlease ensure all AI modules are in the same directory.")
                print("Note: Now using AI Smart Profit Manager for true AI intelligence!")
                input("Press Enter to continue anyway...")
            
        # Start GUI
        app = AISmartProfitGUI()
        app.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()