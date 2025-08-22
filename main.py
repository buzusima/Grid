"""
Simple AI Trading GUI - Working Version
main.py
เรียบง่าย ใช้งานได้จริง ไม่มี error
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import threading
import time
from datetime import datetime
import os

# Import modules
try:
    from mt5_auto_connector import MT5AutoConnector
    from ai_smart_profit_manager import AISmartProfitManager
except ImportError as e:
    print(f"Import error: {e}")

class SimpleAITradingGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.init_variables()
        self.create_gui()
        
    def setup_window(self):
        """Setup main window"""
        self.root.title("🚀 AI Smart Profit Trading - Simple Edition")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1a1a2e')
        
        # Center window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def init_variables(self):
        """Initialize variables"""
        self.is_connected = False
        self.is_trading = False
        self.account_info = {}
        self.mt5_connector = MT5AutoConnector()
        self.ai_smart_trader = None
        
        # Colors
        self.bg_color = '#1a1a2e'
        self.card_color = '#16213E'
        self.accent_color = '#00D4FF'
        self.success_color = '#00FF88'
        self.error_color = '#FF3366'
        self.text_color = '#FFFFFF'
        
    def create_gui(self):
        """Create simple GUI"""
        # Main container
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Header
        self.create_header(main_frame)
        
        # Content
        content_frame = tk.Frame(main_frame, bg=self.bg_color)
        content_frame.pack(fill='both', expand=True, pady=20)
        
        # Left panel
        left_frame = tk.Frame(content_frame, bg=self.card_color, relief='solid', borderwidth=1)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Right panel
        right_frame = tk.Frame(content_frame, bg=self.card_color, relief='solid', borderwidth=1)
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        # Create content
        self.create_controls(left_frame)
        self.create_monitor(right_frame)
        
    def create_header(self, parent):
        """Create header"""
        header = tk.Frame(parent, bg='#16213E', height=80, relief='solid', borderwidth=1)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        # Title
        title = tk.Label(header, text="🚀 AI Smart Profit Trading",
                        bg='#16213E', fg=self.accent_color,
                        font=('Arial', 18, 'bold'))
        title.pack(side='left', padx=20, pady=20)
        
        # Status
        self.status_label = tk.Label(header, text="● Disconnected",
                                   bg='#16213E', fg=self.error_color,
                                   font=('Arial', 12, 'bold'))
        self.status_label.pack(side='right', padx=20, pady=20)
        
    def create_controls(self, parent):
        """Create control panel"""
        # Title
        title = tk.Label(parent, text="🎛️ Trading Controls",
                        bg=self.card_color, fg=self.text_color,
                        font=('Arial', 14, 'bold'))
        title.pack(pady=20)
        
        # Connection
        conn_frame = tk.Frame(parent, bg=self.card_color)
        conn_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(conn_frame, text="📡 Connection:",
                bg=self.card_color, fg=self.text_color,
                font=('Arial', 11, 'bold')).pack(anchor='w')
        
        self.connect_btn = tk.Button(conn_frame, text="🔌 Connect MT5",
                                   command=self.connect_mt5,
                                   bg=self.accent_color, fg='black',
                                   font=('Arial', 10, 'bold'),
                                   relief='flat', padx=20, pady=10)
        self.connect_btn.pack(fill='x', pady=(5, 0))
        
        # Account info
        self.account_label = tk.Label(conn_frame, text="No account connected",
                                    bg=self.card_color, fg='#888888',
                                    font=('Arial', 9))
        self.account_label.pack(anchor='w', pady=(5, 0))
        
        # Trading mode
        mode_frame = tk.Frame(parent, bg=self.card_color)
        mode_frame.pack(fill='x', padx=20, pady=20)
        
        tk.Label(mode_frame, text="🎯 Trading Mode:",
                bg=self.card_color, fg=self.text_color,
                font=('Arial', 11, 'bold')).pack(anchor='w')
        
        self.mode_var = tk.StringVar(value="BALANCED")
        
        modes = [("🛡️ SAFE", "SAFE"), ("⚖️ BALANCED", "BALANCED"), 
                ("🚀 AGGRESSIVE", "AGGRESSIVE")]
        
        for text, value in modes:
            rb = tk.Radiobutton(mode_frame, text=text, variable=self.mode_var, value=value,
                              bg=self.card_color, fg=self.text_color,
                              selectcolor=self.bg_color,
                              font=('Arial', 10))
            rb.pack(anchor='w', pady=2)
        
        # Buttons
        btn_frame = tk.Frame(parent, bg=self.card_color)
        btn_frame.pack(fill='x', padx=20, pady=20)
        
        self.calc_btn = tk.Button(btn_frame, text="🧮 Calculate Parameters",
                                command=self.calculate_params,
                                bg='#FFB800', fg='black',
                                font=('Arial', 10, 'bold'),
                                relief='flat', padx=20, pady=10,
                                state='disabled')
        self.calc_btn.pack(fill='x', pady=2)
        
        self.start_btn = tk.Button(btn_frame, text="🚀 Start AI Trading",
                                 command=self.start_trading,
                                 bg=self.success_color, fg='black',
                                 font=('Arial', 11, 'bold'),
                                 relief='flat', padx=20, pady=15,
                                 state='disabled')
        self.start_btn.pack(fill='x', pady=5)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹️ Stop Trading",
                                command=self.stop_trading,
                                bg=self.error_color, fg='white',
                                font=('Arial', 10, 'bold'),
                                relief='flat', padx=20, pady=10,
                                state='disabled')
        self.stop_btn.pack(fill='x', pady=2)
        
    def create_monitor(self, parent):
        """Create monitor panel"""
        # Title
        title = tk.Label(parent, text="📊 System Monitor",
                        bg=self.card_color, fg=self.text_color,
                        font=('Arial', 14, 'bold'))
        title.pack(pady=20)
        
        # Stats
        stats_frame = tk.Frame(parent, bg=self.card_color)
        stats_frame.pack(fill='x', padx=20, pady=10)
        
        self.health_label = tk.Label(stats_frame, text="🧠 AI Health: --",
                                   bg=self.card_color, fg=self.accent_color,
                                   font=('Arial', 11, 'bold'))
        self.health_label.pack(anchor='w', pady=2)
        
        self.profit_label = tk.Label(stats_frame, text="💰 Total P&L: $0.00",
                                   bg=self.card_color, fg=self.success_color,
                                   font=('Arial', 11, 'bold'))
        self.profit_label.pack(anchor='w', pady=2)
        
        self.positions_label = tk.Label(stats_frame, text="📈 Positions: 0",
                                      bg=self.card_color, fg='#FFB800',
                                      font=('Arial', 11, 'bold'))
        self.positions_label.pack(anchor='w', pady=2)
        
        self.risk_label = tk.Label(stats_frame, text="🛡️ Risk: 0%",
                                 bg=self.card_color, fg=self.text_color,
                                 font=('Arial', 11, 'bold'))
        self.risk_label.pack(anchor='w', pady=2)
        
        # Log
        log_frame = tk.Frame(parent, bg=self.card_color)
        log_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(log_frame, text="📋 System Log:",
                bg=self.card_color, fg=self.text_color,
                font=('Arial', 11, 'bold')).pack(anchor='w')
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20,
                                                bg='#0F0F23', fg=self.text_color,
                                                font=('Consolas', 9),
                                                relief='flat', borderwidth=1)
        self.log_text.pack(fill='both', expand=True, pady=(5, 0))
        
        # Initial log
        self.log("🚀 AI Smart Profit Trading System Ready")
        self.log("📡 Please connect to MetaTrader5 to begin")
        
    def log(self, message):
        """Add log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, formatted)
        self.log_text.see(tk.END)
        
    def show_message(self, title, message, type="info"):
        """Show message box"""
        if type == "error":
            messagebox.showerror(title, message)
        elif type == "warning":
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)
        
    def connect_mt5(self):
        """Connect to MT5"""
        try:
            self.log("🔌 Connecting to MetaTrader5...")
            
            if self.mt5_connector.auto_connect():
                self.is_connected = True
                self.status_label.config(text="● Connected", fg=self.success_color)
                
                # Get account info
                account_info = self.mt5_connector.get_account_info()
                if account_info:
                    self.account_info = account_info
                    login = account_info['login']
                    balance = account_info['balance']
                    
                    self.account_label.config(
                        text=f"Account: {login} | Balance: ${balance:,.2f}",
                        fg=self.text_color
                    )
                    
                    # Enable buttons
                    self.calc_btn.config(state='normal')
                    self.connect_btn.config(text="✅ Connected", state='disabled')
                    
                    self.log(f"✅ Connected to account {login}")
                    self.log(f"💰 Balance: ${balance:,.2f}")
                    
                else:
                    self.log("❌ Failed to get account information")
                    self.show_message("Error", "Failed to get account information", "error")
            else:
                self.log("❌ MT5 connection failed")
                self.show_message("Error", "Failed to connect to MT5", "error")
                
        except Exception as e:
            self.log(f"❌ Connection error: {e}")
            self.show_message("Error", f"Connection error: {e}", "error")
            
    def calculate_params(self):
        """Calculate parameters"""
        if not self.is_connected:
            self.show_message("Warning", "Please connect to MT5 first", "warning")
            return
            
        try:
            self.log("🧮 Calculating trading parameters...")
            
            # Simple calculation
            balance = self.account_info.get('balance', 1000)
            
            # Basic parameters
            self.calc_results = {
                'base_lot': max(0.01, balance / 100000),
                'min_spacing': 80,
                'normal_spacing': 100,
                'max_spacing': 300,
                'survivability': min(20000, balance * 15),
                'safety_margin': 60.0
            }
            
            # Log results
            self.log("✅ Parameters calculated successfully")
            self.log(f"📊 Base Lot: {self.calc_results['base_lot']:.3f}")
            self.log(f"📏 Spacing: {self.calc_results['min_spacing']}-{self.calc_results['max_spacing']} points")
            self.log(f"🛡️ Survivability: {self.calc_results['survivability']:,} points")
            
            # Enable start button
            self.start_btn.config(state='normal')
            
        except Exception as e:
            self.log(f"❌ Calculation error: {e}")
            self.show_message("Error", f"Calculation error: {e}", "error")
            
    def start_trading(self):
        """Start trading"""
        if not self.is_connected or not hasattr(self, 'calc_results'):
            self.show_message("Warning", "Please connect and calculate parameters first", "warning")
            return
            
        try:
            self.log("🚀 Starting AI trading system...")
            
            # Initialize AI trader
            config = {
                'enhanced_grid': {
                    'min_spacing': 80,
                    'normal_spacing': 100,
                    'max_spacing': 300,
                    'profit_only_mode': True
                },
                'ai_smart_profit': {
                    'analysis_interval': 3,
                    'profit_only_mode': True
                },
                # ⭐ เพิ่มส่วนนี้ - Portfolio Balance Protection Config
                'portfolio_balance_protection': {
                    'enabled': True,
                    'mode': 'STANDARD',
                    'max_imbalance_ratio': 2.3,    # 70:30
                    'critical_imbalance_ratio': 3.0  # 75:25
                }
            }
            
            self.ai_smart_trader = AISmartProfitManager(
                self.mt5_connector,
                self.calc_results,
                config
            )
            
            # ⭐ เพิ่มส่วนนี้ - Setup Portfolio Balance Protection
            self.ai_smart_trader.portfolio_balance_protection = config['portfolio_balance_protection']['enabled']
            self.ai_smart_trader.balance_protection_mode = config['portfolio_balance_protection']['mode']
            self.ai_smart_trader.max_imbalance_ratio = config['portfolio_balance_protection']['max_imbalance_ratio']
            self.ai_smart_trader.critical_imbalance_ratio = config['portfolio_balance_protection']['critical_imbalance_ratio']
            
            # Log Portfolio Balance Protection settings
            self.log("🛡️ Portfolio Balance Protection: ENABLED")
            self.log(f"📊 Max Imbalance Ratio: {self.ai_smart_trader.max_imbalance_ratio:.1f}:1 (70:30)")
            self.log(f"🚨 Critical Threshold: {self.ai_smart_trader.critical_imbalance_ratio:.1f}:1 (75:25)")
            
            # Start trading
            success = self.ai_smart_trader.start_ai_trading()
            
            if success:
                self.is_trading = True
                
                # Update buttons
                self.start_btn.config(state='disabled')
                self.stop_btn.config(state='normal')
                
                self.log("🎉 AI Trading started successfully!")
                self.log("🧠 AI Engine: ACTIVE")
                self.log("🎯 Grid Manager: OPERATIONAL")
                self.log("💰 Profit System: MONITORING")
                self.log("🛡️ Balance Protection: ACTIVE")  # ⭐ เพิ่มบรรทัดนี้
                
                # Start monitoring
                self.start_monitoring()
                
            else:
                self.log("❌ Failed to start AI trading")
                self.show_message("Error", "Failed to start AI trading", "error")
                
        except Exception as e:
            self.log(f"❌ Trading start error: {e}")
            self.show_message("Error", f"Trading start error: {e}", "error")

    def stop_trading(self):
        """Stop trading"""
        if not self.is_trading:
            return
            
        try:
            self.log("🛑 Stopping AI trading...")
            
            self.is_trading = False
            
            if self.ai_smart_trader:
                self.ai_smart_trader.stop_ai_trading()
                
            # Update buttons
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            
            self.log("✅ AI Trading stopped successfully")
            
        except Exception as e:
            self.log(f"❌ Stop error: {e}")
            
    def start_monitoring(self):
        """Start monitoring thread"""
        def monitor():
            while self.is_trading:
                try:
                    if self.ai_smart_trader:
                        status = self.ai_smart_trader.get_ai_status()
                        
                        if status and 'error' not in status:
                            # Update GUI
                            self.root.after(0, self.update_display, status)
                    
                    time.sleep(3)
                    
                except Exception as e:
                    self.log(f"❌ Monitor error: {e}")
                    time.sleep(5)
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        
    def update_display(self, status):
        """Update display with status"""
        try:
            # Update health
            health = status.get('ai_health_score', 0)
            health_color = self.success_color if health > 70 else '#FFB800' if health > 40 else self.error_color
            self.health_label.config(text=f"🧠 AI Health: {health:.1f}/100", fg=health_color)
            
            # Update profit
            profit = status.get('total_profit', 0)
            profit_color = self.success_color if profit > 0 else self.error_color if profit < 0 else self.text_color
            self.profit_label.config(text=f"💰 Total P&L: ${profit:.2f}", fg=profit_color)
            
            # Update positions
            positions = status.get('active_positions', 0)
            self.positions_label.config(text=f"📈 Positions: {positions}")
            
            # Update risk
            risk = status.get('survivability_usage', 0)
            risk_color = self.success_color if risk < 0.3 else '#FFB800' if risk < 0.7 else self.error_color
            self.risk_label.config(text=f"🛡️ Risk: {risk:.1%}", fg=risk_color)
            
        except Exception as e:
            print(f"Display update error: {e}")
            
    def run(self):
        """Run the GUI"""
        try:
            self.log("🎯 Simple AI Trading GUI Started")
            self.log("🔧 No complex layouts - just works!")
            self.root.mainloop()
        except Exception as e:
            print(f"GUI error: {e}")

def main():
    """Main function"""
    try:
        print("🚀 Simple AI Trading GUI")
        print("=" * 40)
        print("✅ Simple layout - no errors")
        print("✅ Easy to use")
        print("✅ Just works!")
        print("=" * 40)
        
        app = SimpleAITradingGUI()
        app.run()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()