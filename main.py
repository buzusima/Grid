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
import os
import sys

# Import custom modules (will be created)
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
        
        self.grid_spacing_label = tk.Label(left_col, text="📏 Grid Spacing: 0 จุด", 
                                          font=('Arial', 10), fg='#ffffff', bg='#16213e')
        self.grid_spacing_label.pack(anchor='w', pady=2)
        
        self.max_levels_label = tk.Label(left_col, text="📈 Max Levels: 0", 
                                        font=('Arial', 10), fg='#ffffff', bg='#16213e')
        self.max_levels_label.pack(anchor='w', pady=2)
        
        self.survivability_label = tk.Label(left_col, text="🛡️ Survivability: 0 จุด", 
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
            text="📊 Current Drawdown: 0 จุด",
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
                    gold_symbol = self.mt5_connector.detect_gold_symbol()
                    
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
        
        account_text = f"💰 Account: {account_info['login']} | Balance: ${account_info['balance']:,.2f} | {gold_symbol}"
        self.account_label.config(text=account_text)
        
        # Enable calculate button
        self.connect_btn.config(text="✅ Connected", state='disabled')
        
    def calculate_survivability(self):
        """Calculate and display survivability parameters"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to MT5 first")
            return
            
        try:
            balance = self.account_info.get('balance', 0)
            if balance <= 0:
                raise ValueError("Invalid account balance")
                
            self.log_message(f"🧮 Calculating survivability for ${balance:,.2f}...")
            
            # Calculate using survivability engine
            calculations = self.survivability_engine.calculate_for_balance(balance)
            self.current_calculations = calculations
            
            # Update display
            self.update_survivability_display(calculations)
            
            # Calculate hedge plan
            hedge_plan = self.hedge_calculator.calculate_hedge_plan(calculations)
            self.update_hedge_display(hedge_plan)
            
            self.log_message("✅ Survivability calculation completed", "SUCCESS")
            
        except Exception as e:
            self.log_message(f"❌ Calculation Error: {str(e)}", "ERROR")
            messagebox.showerror("Calculation Error", str(e))
            
    def update_survivability_display(self, calc):
        """Update survivability display with calculations"""
        self.balance_label.config(text=f"💰 Balance: ${calc['account_balance']:,.2f}")
        self.base_lot_label.config(text=f"🎯 Base Lot: {calc['base_lot']:.2f}")
        self.grid_spacing_label.config(text=f"📏 Grid Spacing: {calc['grid_spacing']} จุด (${calc['grid_spacing']*0.01:.2f})")
        self.max_levels_label.config(text=f"📈 Max Levels: {calc['max_levels']}")
        
        # Survivability with color coding
        survivability = calc['survivability']
        if survivability >= 20000:
            surv_color = '#51cf66'  # Green
            surv_text = f"🛡️ Survivability: {survivability:,.0f} จุด ✅"
        else:
            surv_color = '#ff6b6b'  # Red
            surv_text = f"🛡️ Survivability: {survivability:,.0f} จุด ⚠️"
            
        self.survivability_label.config(text=surv_text, fg=surv_color)
        
        safety_margin = calc['account_balance'] * (1 - self.config['safety_ratio'])
        self.safety_margin_label.config(text=f"💪 Safety Margin: ${safety_margin:,.2f} ({100-self.config['safety_ratio']*100:.0f}%)")
        
    def update_hedge_display(self, hedge_plan):
        """Update hedge plan display"""
        # Clear previous hedge display
        for widget in self.hedge_display.winfo_children():
            widget.destroy()
            
        for i, (trigger_points, hedge_size) in enumerate(hedge_plan):
            hedge_frame = tk.Frame(self.hedge_display, bg='#16213e')
            hedge_frame.pack(fill=tk.X, pady=2)
            
            trigger_label = tk.Label(
                hedge_frame,
                text=f"▶️ @{trigger_points:,.0f} จุด:",
                font=('Arial', 9),
                fg='#ffd43b',
                bg='#16213e',
                width=20,
                anchor='w'
            )
            trigger_label.pack(side=tk.LEFT)
            
            hedge_label = tk.Label(
                hedge_frame,
                text=f"+{hedge_size:.3f} lot hedge",
                font=('Arial', 9),
                fg='#ffffff',
                bg='#16213e'
            )
            hedge_label.pack(side=tk.LEFT, padx=(10, 0))
            
    def start_trading(self):
        """Start AI grid trading system"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to MT5 first")
            return
            
        if not self.current_calculations:
            messagebox.showwarning("Warning", "Please calculate survivability first")
            return
            
        try:
            # Initialize grid trader
            gold_symbol = self.mt5_connector.get_gold_symbol()
            self.grid_trader = AIGoldGrid(
                self.mt5_connector,
                self.current_calculations,
                self.config
            )
            
            # Start trading
            self.is_trading = True
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            
            self.log_message("🚀 AI Grid Trading System Started!", "SUCCESS")
            self.log_message(f"📊 Trading {gold_symbol} with {self.current_calculations['survivability']:,.0f} points survivability", "INFO")
            
            # Start trading thread
            self.trading_thread = threading.Thread(target=self.run_trading_loop, daemon=True)
            self.trading_thread.start()
            
        except Exception as e:
            self.log_message(f"❌ Start Trading Error: {str(e)}", "ERROR")
            messagebox.showerror("Trading Error", str(e))
            
    def stop_trading(self):
        """Stop trading system"""
        self.is_trading = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        
        if self.grid_trader:
            self.grid_trader.stop_trading()
            
        self.log_message("⏹️ AI Grid Trading System Stopped", "WARNING")
        
    def emergency_stop(self):
        """Emergency stop - close all positions"""
        if messagebox.askyesno("Emergency Stop", "⚠️ This will close ALL positions immediately!\nAre you sure?"):
            try:
                if self.grid_trader:
                    self.grid_trader.emergency_close_all()
                    
                self.stop_trading()
                self.log_message("🚨 EMERGENCY STOP EXECUTED - All positions closed", "ERROR")
                
            except Exception as e:
                self.log_message(f"❌ Emergency Stop Error: {str(e)}", "ERROR")
                
    def run_trading_loop(self):
        """Main trading loop"""
        while self.is_trading:
            try:
                if self.grid_trader:
                    self.grid_trader.update_grid()
                    self.grid_trader.check_hedge_triggers()
                    
                time.sleep(1)  # Update every second
                
            except Exception as e:
                self.log_message(f"❌ Trading Loop Error: {str(e)}", "ERROR")
                time.sleep(5)
                
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
            text = f"📊 Current Profit: +{drawdown:,.0f} จุด"
        else:
            color = '#ff6b6b'  # Red for loss
            text = f"📊 Current Drawdown: {abs(drawdown):,.0f} จุด"
            
        self.current_drawdown_label.config(text=text, fg=color)
        
        # Update next hedge trigger
        if self.current_calculations and abs(drawdown) > 0:
            next_hedge = self.hedge_calculator.get_next_hedge_trigger(abs(drawdown))
            if next_hedge:
                self.next_hedge_label.config(text=f"⏳ Next Hedge: {next_hedge:,.0f} จุด")
            else:
                self.next_hedge_label.config(text="⏳ Next Hedge: Max Level")
                
    def clear_logs(self):
        """Clear log display"""
        self.log_display.delete("1.0", tk.END)
        self.log_message("🗑️ Logs cleared", "INFO")
        
    def on_closing(self):
        """Handle application closing"""
        if self.is_trading:
            if messagebox.askyesno("Confirm Exit", "Trading is active. Stop trading before exit?"):
                self.stop_trading()
                time.sleep(1)
            else:
                return
                
        self.monitoring = False
        
        if hasattr(self, 'mt5_connector'):
            self.mt5_connector.disconnect()
            
        self.save_config()
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