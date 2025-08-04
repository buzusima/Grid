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
    from survivability_engine import SurvivabilityEngine
    from ai_money_manager import AIMoneyManager
    from gold_hedge_calculator import GoldHedgeCalculator
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
        """Load configuration from config.json"""
        default_config = {
            "target_survivability": 20000,
            "safety_ratio": 0.6,
            "emergency_stop_percentage": 50,
            "daily_loss_limit_percentage": 10,
            "hedge_triggers": [0.15, 0.30, 0.45, 0.60],
            "hedge_multipliers": [0.5, 1.0, 1.5, 2.0],
            "log_level": "INFO",
            "auto_connect_mt5": True,
            "gold_symbols": ["XAUUSD", "GOLD", "XAU/USD", "XAUUSD.cmd", "GOLD#"]
        }
        
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = default_config
                self.save_config()
        except Exception as e:
            print(f"Config load error: {e}")
            self.config = default_config
            
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
            self.hedge_calculator = GoldHedgeCalculator(self.config)
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
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create sections
        self.create_header_section(main_frame)
        self.create_connection_section(main_frame)
        self.create_survivability_section(main_frame)
        self.create_hedge_section(main_frame)
        self.create_control_section(main_frame)
        self.create_log_section(main_frame)
        
    def create_header_section(self, parent):
        """Create header with system title and status"""
        header_frame = tk.Frame(parent, bg='#16213e', relief='raised', bd=2)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = tk.Label(
            header_frame,
            text="🏆 AI Gold Grid Trading System",
            font=('Arial', 18, 'bold'),
            fg='#ffd700',
            bg='#16213e'
        )
        title_label.pack(pady=10)
        
        subtitle_label = tk.Label(
            header_frame,
            text="📊 20,000+ Points Survivability Calculator & Auto Money Management",
            font=('Arial', 12),
            fg='#ffffff',
            bg='#16213e'
        )
        subtitle_label.pack(pady=(0, 10))
        
    def create_connection_section(self, parent):
        """Create MT5 connection section"""
        conn_frame = tk.LabelFrame(
            parent,
            text="🔗 MT5 Auto Connection",
            font=('Arial', 12, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Connection status
        status_frame = tk.Frame(conn_frame, bg='#16213e')
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
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
        """Create survivability calculation display"""
        surv_frame = tk.LabelFrame(
            parent,
            text="🛡️ AI Survivability Calculator",
            font=('Arial', 12, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        surv_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create two columns
        left_col = tk.Frame(surv_frame, bg='#16213e')
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        right_col = tk.Frame(surv_frame, bg='#16213e')
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left column - Account & Parameters
        tk.Label(left_col, text="📊 AI Calculated Parameters:", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#16213e').pack(anchor='w')
        
        self.balance_label = tk.Label(left_col, text="💰 Balance: $0", 
                                     font=('Arial', 10), fg='#ffffff', bg='#16213e')
        self.balance_label.pack(anchor='w', pady=2)
        
        self.base_lot_label = tk.Label(left_col, text="🎯 Base Lot: 0.00", 
                                      font=('Arial', 10), fg='#ffffff', bg='#16213e')
        self.base_lot_label.pack(anchor='w', pady=2)
        
        self.grid_spacing_label = tk.Label(left_col, text="📏 Grid Spacing: 0 points", 
                                          font=('Arial', 10), fg='#ffffff', bg='#16213e')
        self.grid_spacing_label.pack(anchor='w', pady=2)
        
        self.max_levels_label = tk.Label(left_col, text="📈 Max Levels: 0", 
                                        font=('Arial', 10), fg='#ffffff', bg='#16213e')
        self.max_levels_label.pack(anchor='w', pady=2)
        
        self.survivability_label = tk.Label(left_col, text="🛡️ Survivability: 0 points", 
                                           font=('Arial', 10, 'bold'), fg='#51cf66', bg='#16213e')
        self.survivability_label.pack(anchor='w', pady=2)
        
        self.safety_margin_label = tk.Label(left_col, text="💪 Safety Margin: $0", 
                                           font=('Arial', 10), fg='#ffffff', bg='#16213e')
        self.safety_margin_label.pack(anchor='w', pady=2)
        
        # Right column - Hedge Plan
        tk.Label(right_col, text="🛡️ Hedge Protection Plan:", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#16213e').pack(anchor='w')
        
        self.hedge_display = tk.Frame(right_col, bg='#16213e')
        self.hedge_display.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Calculate button
        calc_btn = tk.Button(
            surv_frame,
            text="🔄 Recalculate Survivability",
            font=('Arial', 10, 'bold'),
            bg='#ffd43b',
            fg='#1a1a2e',
            relief='raised',
            bd=3,
            command=self.calculate_survivability
        )
        calc_btn.pack(pady=10)
        
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
        """Create trading control section"""
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
        
        # Control buttons
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
        """Calculate and display survivability parameters"""
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
                
            self.log_message(f"🧮 Calculating survivability for ${balance:,.2f}...")
            self.log_message(f"📏 Broker minimum lot: {min_lot}")
            
            # Calculate using survivability engine with broker constraints
            calculations = self.survivability_engine.calculate_for_balance(balance, min_lot)
            self.current_calculations = calculations
            
            # Update display
            self.update_survivability_display(calculations)
            
            # Calculate hedge plan with broker constraints
            symbol_info = self.mt5_connector.get_symbol_info()
            min_lot = symbol_info.get('volume_min', 0.01) if symbol_info else 0.01
            hedge_plan = self.hedge_calculator.calculate_hedge_plan(calculations, min_lot)
            self.update_hedge_display(hedge_plan)
            
            # Log warnings if any
            if calculations.get('warnings'):
                for warning in calculations['warnings']:
                    self.log_message(f"⚠️ {warning}", "WARNING")
            
            # Show appropriate success message based on target achievement
            realistic_surv = calculations.get('realistic_survivability', calculations.get('survivability', 0))
            if calculations.get('target_met', False) or realistic_surv >= 20000:
                self.log_message("✅ Survivability calculation completed - Target achieved!", "SUCCESS")
            elif realistic_surv >= 10000:
                self.log_message("✅ Survivability calculation completed - System ready with good protection", "SUCCESS")
            else:
                self.log_message("✅ Survivability calculation completed - System ready with basic protection", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"❌ Calculation Error: {str(e)}", "ERROR")
            messagebox.showerror("Calculation Error", str(e))

    def update_survivability_display(self, calc):
        """Update survivability display with calculations"""
        self.balance_label.config(text=f"💰 Balance: ${calc['account_balance']:,.2f}")
        
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
        
        # Show both theoretical and realistic survivability
        theoretical_surv = calc['survivability']
        realistic_surv = calc.get('realistic_survivability', theoretical_surv)
        
        # ปรับเงื่อนไขสีให้ยืดหยุ่นมากขึ้น
        if realistic_surv >= 20000:
            surv_color = '#51cf66'  # Green - ถึงเป้าหมายแล้ว
            if realistic_surv != theoretical_surv:
                surv_text = f"🛡️ Survivability: {realistic_surv:,.0f} points ✅ (Theory: {theoretical_surv:,.0f})"
            else:
                surv_text = f"🛡️ Survivability: {realistic_surv:,.0f} points ✅"
        elif realistic_surv >= 10000:
            surv_color = '#ffd43b'  # Yellow - ใช้ได้แต่ต่ำกว่าเป้าหมาย
            if realistic_surv != theoretical_surv:
                surv_text = f"🛡️ Survivability: {realistic_surv:,.0f} points ⚠️ (Theory: {theoretical_surv:,.0f})"
            else:
                surv_text = f"🛡️ Survivability: {realistic_surv:,.0f} points ⚠️"
        else:
            surv_color = '#ff6b6b'  # Red - ต่ำมาก
            if realistic_surv != theoretical_surv:
                surv_text = f"🛡️ Survivability: {realistic_surv:,.0f} points ⚠️ (Theory: {theoretical_surv:,.0f})"
            else:
                surv_text = f"🛡️ Survivability: {realistic_surv:,.0f} points ⚠️"
            
        self.survivability_label.config(text=surv_text, fg=surv_color)
        
        safety_margin = calc['account_balance'] * (1 - self.config['safety_ratio'])
        self.safety_margin_label.config(text=f"💪 Safety Margin: ${safety_margin:,.2f} ({100-self.config['safety_ratio']*100:.0f}%)")
    
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

    def update_hedge_display(self, hedge_plan):
        """Update hedge plan display with minimum lot warnings"""
        # Clear previous hedge display
        for widget in self.hedge_display.winfo_children():
            widget.destroy()
            
        # Get minimum lot for comparison with error handling
        min_lot = 0.01  # Default minimum lot
        try:
            if hasattr(self, 'mt5_connector') and self.mt5_connector:
                symbol_info = self.mt5_connector.get_symbol_info()
                if symbol_info and isinstance(symbol_info, dict):
                    min_lot = symbol_info.get('volume_min', 0.01)
        except Exception as e:
            print(f"Warning: Could not get symbol info for hedge display: {e}")
            
        for i, (trigger_points, hedge_size) in enumerate(hedge_plan):
            hedge_frame = tk.Frame(self.hedge_display, bg='#16213e')
            hedge_frame.pack(fill=tk.X, pady=2)
            
            trigger_label = tk.Label(
                hedge_frame,
                text=f"▶️ @{trigger_points:,.0f} points:",
                font=('Arial', 9),
                fg='#ffd43b',
                bg='#16213e',
                width=20,
                anchor='w'
            )
            trigger_label.pack(side=tk.LEFT)
            
            # Check if hedge size was adjusted to minimum
            is_minimum = abs(hedge_size - min_lot) < 0.0001  # Account for floating point precision
            
            if is_minimum and hedge_size == min_lot:
                hedge_text = f"+{hedge_size:.3f} lot hedge ⚠️"
                hedge_color = '#ffd43b'  # Yellow for minimum lot warning
            else:
                hedge_text = f"+{hedge_size:.3f} lot hedge"
                hedge_color = '#ffffff'
            
            hedge_label = tk.Label(
                hedge_frame,
                text=hedge_text,
                font=('Arial', 9),
                fg=hedge_color,
                bg='#16213e'
            )
            hedge_label.pack(side=tk.LEFT, padx=(10, 0))
            
        # Add summary if any hedges were adjusted
        adjusted_count = sum(1 for _, size in hedge_plan if abs(size - min_lot) < 0.0001 and size == min_lot)
        if adjusted_count > 0:
            summary_frame = tk.Frame(self.hedge_display, bg='#16213e')
            summary_frame.pack(fill=tk.X, pady=(10, 0))
            
            summary_label = tk.Label(
                summary_frame,
                text=f"⚠️ {adjusted_count} hedge levels using minimum lot ({min_lot})",
                font=('Arial', 9, 'italic'),
                fg='#ffd43b',
                bg='#16213e'
            )
            summary_label.pack(anchor='w')
            
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
        """Update GUI with real-time trading data"""
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
        
        # Update next hedge trigger
        if self.current_calculations and abs(drawdown) > 0:
            next_hedge = self.hedge_calculator.get_next_hedge_trigger(abs(drawdown))
            if next_hedge:
                self.next_hedge_label.config(text=f"⏳ Next Hedge: {next_hedge:,.0f} points")
            else:
                self.next_hedge_label.config(text="⏳ Next Hedge: Max Level")
                
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