"""
AI Smart Profit Gold Trading System with 20,000+ Points Survivability
Main GUI Controller - main.py
Created for MetaTrader5 Gold Trading with Smart Profit Manager Integration
UPDATED VERSION - Using Smart Profit Manager as primary trading engine
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
            "smart_profit": {
                "default_strategy": "BALANCED",
                "quick_profit_enabled": True,
                "auto_reposition": True,
                "trailing_stop_distance": 50
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
        """Create main GUI interface"""
        main_frame = tk.Frame(self.root, bg='#1a1a2e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header section
        self.create_header_section(main_frame)
        
        # Connection and calculation section
        self.create_connection_section(main_frame)
        
        # Smart Profit controls section
        self.create_smart_profit_section(main_frame)
        
        # Trading controls section
        self.create_trading_controls_section(main_frame)
        
        # Status and monitoring section
        self.create_status_monitoring_section(main_frame)
        
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
            text="🏆 20,000+ Points Survivability • AI Portfolio Management • Smart Profit Recovery",
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

    def create_smart_profit_section(self, parent):
        """Create Smart Profit management section"""
        smart_frame = tk.LabelFrame(
            parent,
            text="🧠 AI Smart Profit Management",
            font=('Arial', 12, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        smart_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Strategy selection row
        strategy_row = tk.Frame(smart_frame, bg='#16213e')
        strategy_row.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(strategy_row, text="🎯 Profit Strategy:", font=('Arial', 10), fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)
        
        self.strategy_var = tk.StringVar(value="BALANCED")
        self.strategy_combo = ttk.Combobox(
            strategy_row,
            textvariable=self.strategy_var,
            values=["QUICK_SAFE", "BALANCED", "AGGRESSIVE"],
            width=15,
            state="readonly"
        )
        self.strategy_combo.pack(side=tk.LEFT, padx=(10, 0))
        self.strategy_combo.bind('<<ComboboxSelected>>', self.on_strategy_change)
        
        # Strategy description
        self.strategy_desc = tk.Label(
            strategy_row,
            text="⚖️ Balanced: Optimal profit/risk ratio",
            font=('Arial', 9),
            fg='#adb5bd',
            bg='#16213e'
        )
        self.strategy_desc.pack(side=tk.LEFT, padx=(20, 0))
        
        # Recovery system row
        recovery_row = tk.Frame(smart_frame, bg='#16213e')
        recovery_row.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(recovery_row, text="💊 Portfolio Recovery:", font=('Arial', 10), fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)
        
        self.auto_recovery_btn = tk.Button(
            recovery_row,
            text="🔄 Auto: OFF",
            font=('Arial', 9, 'bold'),
            bg='#6c757d',
            fg='#ffffff',
            relief='raised',
            bd=2,
            width=12,
            command=self.toggle_auto_recovery
        )
        self.auto_recovery_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        self.manual_recovery_btn = tk.Button(
            recovery_row,
            text="🚀 Manual Trigger",
            font=('Arial', 9, 'bold'),
            bg='#fd7e14',
            fg='#ffffff',
            relief='raised',
            bd=2,
            width=15,
            command=self.manual_trigger_recovery
        )
        self.manual_recovery_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Recovery status
        self.recovery_status_display = tk.Label(
            recovery_row,
            text="💊 Ready: Trigger at -$50",
            font=('Arial', 9),
            fg='#adb5bd',
            bg='#16213e'
        )
        self.recovery_status_display.pack(side=tk.RIGHT)
        
        # AI Health indicator
        health_row = tk.Frame(smart_frame, bg='#16213e')
        health_row.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(health_row, text="🏥 AI Health:", font=('Arial', 10), fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)
        
        self.ai_health_score = tk.Label(
            health_row,
            text="📊 --/100",
            font=('Arial', 10, 'bold'),
            fg='#51cf66',
            bg='#16213e'
        )
        self.ai_health_score.pack(side=tk.LEFT, padx=(10, 0))
        
        self.ai_health_status = tk.Label(
            health_row,
            text="ANALYZING",
            font=('Arial', 9),
            fg='#ffd43b',
            bg='#16213e'
        )
        self.ai_health_status.pack(side=tk.LEFT, padx=(10, 0))

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
            text="🚀 Start AI Smart Trading",
            font=('Arial', 12, 'bold'),
            bg='#51cf66',
            fg='#1a1a2e',
            relief='raised',
            bd=3,
            width=22,
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

    def create_status_monitoring_section(self, parent):
        """Create status and monitoring section"""
        status_frame = tk.LabelFrame(
            parent,
            text="📊 Real-time AI Status",
            font=('Arial', 12, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Status display in grid
        status_grid = tk.Frame(status_frame, bg='#16213e')
        status_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Row 1: Basic stats
        row1 = tk.Frame(status_grid, bg='#16213e')
        row1.pack(fill=tk.X, pady=2)
        
        self.positions_label = tk.Label(row1, text="📈 Positions: 0", font=('Arial', 10), fg='#74c0fc', bg='#16213e')
        self.positions_label.pack(side=tk.LEFT)
        
        self.pnl_label = tk.Label(row1, text="💰 PnL: $0.00", font=('Arial', 10, 'bold'), fg='#51cf66', bg='#16213e')
        self.pnl_label.pack(side=tk.LEFT, padx=(50, 0))
        
        self.drawdown_label = tk.Label(row1, text="📉 Drawdown: 0 pts", font=('Arial', 10), fg='#ffd43b', bg='#16213e')
        self.drawdown_label.pack(side=tk.LEFT, padx=(50, 0))
        
        # Row 2: AI stats
        row2 = tk.Frame(status_grid, bg='#16213e')
        row2.pack(fill=tk.X, pady=2)
        
        self.win_rate_label = tk.Label(row2, text="🎯 Win Rate: 0%", font=('Arial', 10), fg='#51cf66', bg='#16213e')
        self.win_rate_label.pack(side=tk.LEFT)
        
        self.trades_label = tk.Label(row2, text="📊 Trades: 0/0", font=('Arial', 10), fg='#74c0fc', bg='#16213e')
        self.trades_label.pack(side=tk.LEFT, padx=(50, 0))
        
        self.survivability_label = tk.Label(row2, text="🛡️ Safety: 0%", font=('Arial', 10), fg='#51cf66', bg='#16213e')
        self.survivability_label.pack(side=tk.LEFT, padx=(50, 0))

    def create_log_section(self, parent):
        """Create logging section"""
        log_frame = tk.LabelFrame(
            parent,
            text="📜 AI System Logs",
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

    def on_mode_change(self, event=None):
        """Handle trading mode change"""
        try:
            mode_str = self.mode_var.get()
            self.current_trading_mode = TradingMode[mode_str]
            self.log_message(f"🎯 Trading Mode changed to: {mode_str}", "INFO")
            
            # Recalculate if we have connection
            if self.is_connected and self.account_info:
                self.calculate_survivability()
                
        except Exception as e:
            self.log_message(f"❌ Mode change error: {e}", "ERROR")

    def on_strategy_change(self, event=None):
        """Handle strategy change"""
        try:
            strategy = self.strategy_var.get()
            descriptions = {
                "QUICK_SAFE": "⚡ Quick & Safe: Fast profits, lower targets",
                "BALANCED": "⚖️ Balanced: Optimal profit/risk ratio", 
                "AGGRESSIVE": "🚀 Aggressive: Higher targets, more patience"
            }
            
            desc = descriptions.get(strategy, "🤖 Unknown strategy")
            self.strategy_desc.config(text=desc)
            
            self.log_message(f"🎯 Profit Strategy changed to: {strategy}", "INFO")
            
        except Exception as e:
            self.log_message(f"❌ Strategy change error: {e}", "ERROR")

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
                
            self.log_message("🧠 AI Calculating optimal parameters...", "INFO")
            
            # Use survivability engine to calculate parameters
            results = self.survivability_engine.calculate_for_balance(balance)            
            
            if results and results.get('target_met', False):
                self.current_calculations = results
                
                # Display results
                self.log_message("✅ AI Calculation completed successfully!", "SUCCESS")
                self.log_message(f"🎯 Mode: {self.current_trading_mode.value}", "INFO")
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

    def start_trading(self):
        """Start AI Smart Profit trading"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to MT5 first")
            return
            
        if not self.current_calculations:
            messagebox.showwarning("Warning", "Please calculate AI parameters first")
            return
        
        try:
            self.log_message("🧠 Starting AI Smart Profit Trading System...", "INFO")
            
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
                
                # Update GUI
                self.start_btn.config(state='disabled', bg='#6c757d')
                self.stop_btn.config(state='normal', bg='#ff6b6b')
                self.emergency_btn.config(state='normal', bg='#e03131')
                
                self.log_message("🚀 AI Smart Profit Trading STARTED!", "SUCCESS")
                survivability = self.current_calculations.get('realistic_survivability', 0)
                self.log_message(f"🛡️ Protection Level: {survivability:,} points", "INFO")
                self.log_message(f"🧠 AI Control: FULL AUTOMATION", "INFO")
                
                # Start real-time monitoring
                self.start_real_time_monitoring()
                
            else:
                self.log_message("❌ Failed to start AI trading system", "ERROR")
                messagebox.showerror("Error", "Failed to start AI Smart Profit trading system")
                
        except Exception as e:
            self.log_message(f"❌ Trading start error: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Failed to start AI trading: {str(e)}")

    def stop_trading(self):
        """Stop AI Smart Profit trading"""
        if not self.is_trading:
            return
            
        try:
            self.log_message("🛑 Stopping AI Smart Profit Trading...", "WARNING")
            
            self.is_trading = False
            
            if self.smart_profit_trader:
                self.smart_profit_trader.stop_trading()
                
            # Update GUI
            self.start_btn.config(state='normal', bg='#51cf66')
            self.stop_btn.config(state='disabled', bg='#6c757d')
            self.emergency_btn.config(state='disabled', bg='#6c757d')
            
            self.log_message("✅ AI Smart Profit Trading STOPPED", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"❌ Stop trading error: {str(e)}", "ERROR")

    def emergency_stop(self):
        """Emergency stop - แก้ไขแล้ว ไม่มั่วซั่ว"""
        if not self.is_trading:
            return
            
        # ✅ ยืนยันก่อน stop
        result = messagebox.askyesno(
            "Stop Trading", 
            "🛑 STOP TRADING SYSTEM\n\nThis will:\n• Stop all AI trading\n• Cancel pending orders\n• Keep positions open\n\nPositions will NOT be closed automatically.\n\nContinue?"
        )
        
        if not result:
            return
            
        try:
            self.log_message("🛑 Emergency stop requested by user", "WARNING")
            
            self.is_trading = False
            
            if self.smart_profit_trader:
                # ✅ เรียกแค่ stop_trading ปกติ
                self.smart_profit_trader.stop_trading()
                
            # Update GUI
            self.start_btn.config(state='normal', bg='#51cf66')
            self.stop_btn.config(state='disabled', bg='#6c757d')
            self.emergency_btn.config(state='disabled', bg='#6c757d')
            
            self.log_message("✅ Trading system stopped safely", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"❌ Stop error: {str(e)}", "ERROR")

    def toggle_auto_recovery(self):
        """Toggle auto recovery mode"""
        try:
            current_state = self.config.get('portfolio_recovery', {}).get('auto_mode', False)
            new_state = not current_state
            
            self.config['portfolio_recovery']['auto_mode'] = new_state
           
            if new_state:
                self.auto_recovery_btn.config(text="🔄 Auto: ON", bg='#51cf66')
                self.log_message("💊 Auto Recovery: ENABLED", "SUCCESS")
            else:
                self.auto_recovery_btn.config(text="🔄 Auto: OFF", bg='#6c757d')
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
                        self.root.after(0, self.update_status_display, status)
                        
                    # Check for emergency conditions
                    if status.get('emergency_stop', False):
                        self.root.after(0, self.handle_emergency_triggered)
                        break
                        
                    update_count += 1
                    
                time.sleep(1)  # Update every second
                
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(5)

    def update_status_display(self, status):
        """Update real-time status display"""
        try:
            if not status or 'error' in status:
                return
                
            # Update basic stats
            positions = status.get('active_positions', 0)
            pnl = status.get('total_pnl', 0)
            drawdown = status.get('current_drawdown', 0)
            win_rate = status.get('win_rate', 0)
            trades_opened = status.get('trades_opened', 0)
            trades_closed = status.get('trades_closed', 0)
            survivability_used = status.get('survivability_used', 0)
            
            # Update labels
            self.positions_label.config(text=f"📈 Positions: {positions}")
            
            pnl_color = '#51cf66' if pnl >= 0 else '#ff6b6b'
            self.pnl_label.config(text=f"💰 PnL: ${pnl:.2f}", fg=pnl_color)
            
            drawdown_color = '#51cf66' if drawdown < 1000 else '#ffd43b' if drawdown < 5000 else '#ff6b6b'
            self.drawdown_label.config(text=f"📉 Drawdown: {drawdown:.0f} pts", fg=drawdown_color)
            
            win_rate_color = '#51cf66' if win_rate >= 60 else '#ffd43b' if win_rate >= 40 else '#ff6b6b'
            self.win_rate_label.config(text=f"🎯 Win Rate: {win_rate:.1f}%", fg=win_rate_color)
            
            self.trades_label.config(text=f"📊 Trades: {trades_opened}/{trades_closed}")
            
            safety_color = '#51cf66' if survivability_used < 30 else '#ffd43b' if survivability_used < 60 else '#ff6b6b'
            self.survivability_label.config(text=f"🛡️ Safety: {100-survivability_used:.1f}%", fg=safety_color)
            
            # Update AI Health
            if 'ai_health_score' in status:
                health_score = status['ai_health_score']
                health_color = '#51cf66' if health_score >= 70 else '#ffd43b' if health_score >= 40 else '#ff6b6b'
                self.ai_health_score.config(text=f"📊 {health_score}/100", fg=health_color)
                
                if health_score >= 80:
                    health_status = "EXCELLENT"
                elif health_score >= 60:
                    health_status = "GOOD"
                elif health_score >= 40:
                    health_status = "FAIR"
                else:
                    health_status = "POOR"
                    
                self.ai_health_status.config(text=health_status, fg=health_color)
            
            # Update Recovery Status
            if 'recovery_system' in status:
                recovery = status['recovery_system']
                if recovery.get('active', False):
                    elapsed = recovery.get('elapsed_minutes', 0)
                    self.recovery_status_display.config(
                        text=f"💊 Active: {elapsed:.1f}min running",
                        fg='#51cf66'
                    )
                else:
                    trigger_loss = recovery.get('trigger_loss', -50)
                    self.recovery_status_display.config(
                        text=f"💊 Ready: Trigger at ${trigger_loss}",
                        fg='#adb5bd'
                    )
                    
        except Exception as e:
            print(f"Status update error: {e}")

    def handle_emergency_triggered(self):
        """Handle automatic emergency stop"""
        try:
            self.is_trading = False
            
            self.start_btn.config(state='normal', bg='#51cf66')
            self.stop_btn.config(state='disabled', bg='#6c757d')
            self.emergency_btn.config(state='disabled', bg='#6c757d')
            
            self.log_message("🚨 AUTOMATIC EMERGENCY STOP TRIGGERED!", "ERROR")
            
            messagebox.showerror(
                "🚨 Emergency Stop", 
                "Automatic emergency stop was triggered!\n\nCheck the logs for details.\nAll positions have been closed."
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
                    "Trading Active", 
                    "AI Trading is active. Stop trading before exit?\n\n• YES = Stop trading (keep positions)\n• NO = Emergency close all\n• CANCEL = Don't exit"
                )
                
                if result is True:  # YES - Stop trading
                    self.stop_trading()
                    time.sleep(2)
                    
                elif result is False:  # NO - Emergency close
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
        self.log_message("🏆 Target: 20,000+ Points Survivability", "INFO")
        self.log_message("💰 AI Portfolio Management & Recovery", "INFO")
        self.log_message("🔗 Ready to connect to MetaTrader5", "INFO")
        
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
                print("\nPlease ensure all modules are in the same directory.")
                print("Note: ai_gold_grid.py is no longer required - using Smart Profit Manager!")
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
