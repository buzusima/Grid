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
        """Setup main window properties - MERGED COMPACT"""
        self.root.title("🏆 AI Gold Grid + Recovery")
        self.root.geometry("800x450")  # ลดเป็น 800x450
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
        """Create MERGED GUI - รวมทุกอย่างเข้าด้วยกัน"""
        main_frame = tk.Frame(self.root, bg='#1a1a2e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # รวม Header + Connection + Calculator ในกรอบเดียว
        self.create_merged_top_section(main_frame)
        
        # รวม Controls + Recovery + Hedge ในกรอบเดียว  
        self.create_merged_control_section(main_frame)
        
        # Log section เล็กลง
        self.create_compact_log_section(main_frame)
        
    def create_merged_top_section(self, parent):
        """รวม Header + Connection + Calculator + Hedge ในกรอบเดียว - แก้ไข Missing Labels"""
        top_frame = tk.LabelFrame(
            parent,
            text="🏆 AI Gold Grid System + Real-time Monitor",
            font=('Arial', 10, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        top_frame.pack(fill=tk.X, pady=(0, 3))
        
        # Row 1: Connection + Mode + Target
        row1 = tk.Frame(top_frame, bg='#16213e')
        row1.pack(fill=tk.X, padx=5, pady=3)
        
        # Connection Section (Left)
        conn_section = tk.Frame(row1, bg='#16213e')
        conn_section.pack(side=tk.LEFT)
        
        self.connection_status = tk.Label(
            conn_section, text="❌ Disconnected", font=('Arial', 9, 'bold'), 
            fg='#ff6b6b', bg='#16213e'
        )
        self.connection_status.pack(side=tk.LEFT)
        
        # Connection Button
        self.connect_btn = tk.Button(
            conn_section,
            text="🔌 Connect",
            font=('Arial', 8, 'bold'),
            bg='#4ecdc4',
            fg='#1a1a2e',
            relief='raised',
            bd=2,
            command=self.connect_mt5
        )
        self.connect_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Mode Selection (Center)
        mode_frame = tk.Frame(row1, bg='#16213e')
        mode_frame.pack(side=tk.LEFT, padx=(30, 0))
        
        tk.Label(mode_frame, text="🎯 Mode:", font=('Arial', 9, 'bold'), 
                fg='#4ecdc4', bg='#16213e').pack(side=tk.LEFT)
        
        self.mode_var = tk.StringVar(value="BALANCED")
        self.mode_combo = ttk.Combobox(
            mode_frame, textvariable=self.mode_var, 
            values=["SAFE", "BALANCED", "AGGRESSIVE", "TURBO"], 
            state="readonly", width=10, font=('Arial', 9)
        )
        self.mode_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.mode_combo.bind('<<ComboboxSelected>>', self.on_mode_change)
        
        # Target Display (Right)
        self.target_label = tk.Label(
            row1, text="🎯 Target: 10,000 points", 
            font=('Arial', 9, 'bold'), fg='#ffd43b', bg='#16213e'
        )
        self.target_label.pack(side=tk.RIGHT)
        
        # Row 2: Account Info + Calculator Results
        row2 = tk.Frame(top_frame, bg='#16213e')
        row2.pack(fill=tk.X, padx=5, pady=3)
        
        # Account Info (Left)
        account_frame = tk.Frame(row2, bg='#16213e')
        account_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.account_label = tk.Label(
            account_frame, text="💰 Account: Not Connected", 
            font=('Arial', 9), fg='#ffffff', bg='#16213e'
        )
        self.account_label.pack(anchor='w')
        
        self.balance_label = tk.Label(
            account_frame, text="💰 Balance: $0", 
            font=('Arial', 9), fg='#ffffff', bg='#16213e'
        )
        self.balance_label.pack(anchor='w')
        
        # ✅ เพิ่ม Safety Margin Label ที่หายไป
        self.safety_margin_label = tk.Label(
            account_frame, text="💪 Safety Margin: $0", 
            font=('Arial', 9), fg='#ffffff', bg='#16213e'
        )
        self.safety_margin_label.pack(anchor='w')
        
        # Calculator Results (Right)
        calc_frame = tk.Frame(row2, bg='#16213e')
        calc_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.base_lot_label = tk.Label(
            calc_frame, text="🎯 Base Lot: 0.000", 
            font=('Arial', 9), fg='#ffffff', bg='#16213e'
        )
        self.base_lot_label.pack(anchor='e')
        
        self.grid_spacing_label = tk.Label(
            calc_frame, text="📏 Spacing: 0 points", 
            font=('Arial', 9), fg='#ffffff', bg='#16213e'
        )
        self.grid_spacing_label.pack(anchor='e')
        
        # ✅ เพิ่ม Max Levels Label ที่หายไป
        self.max_levels_label = tk.Label(
            calc_frame, text="📈 Max Levels: 0", 
            font=('Arial', 9), fg='#ffffff', bg='#16213e'
        )
        self.max_levels_label.pack(anchor='e')
        
        # Row 3: Survivability + Hedge Monitor
        row3 = tk.Frame(top_frame, bg='#16213e')
        row3.pack(fill=tk.X, padx=5, pady=3)
        
        # Survivability (Left)
        self.survivability_label = tk.Label(
            row3, text="🛡️ Survivability: 0 points", 
            font=('Arial', 10, 'bold'), fg='#adb5bd', bg='#16213e'
        )
        self.survivability_label.pack(side=tk.LEFT)
        
        # Hedge Monitor (Right) 
        hedge_frame = tk.Frame(row3, bg='#16213e')
        hedge_frame.pack(side=tk.RIGHT)
        
        self.current_drawdown_label = tk.Label(
            hedge_frame, text="📊 Portfolio: Not active", 
            font=('Arial', 9), fg='#adb5bd', bg='#16213e'
        )
        self.current_drawdown_label.pack(side=tk.RIGHT)
        
        # ✅ เพิ่ม Next Hedge Label ที่หายไป (สำหรับ hedge section)
        self.next_hedge_label = tk.Label(
            hedge_frame, text="⏳ Next Hedge: N/A", 
            font=('Arial', 9), fg='#adb5bd', bg='#16213e'
        )
        self.next_hedge_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Row 4: Calculate Button + Portfolio Status
        row4 = tk.Frame(top_frame, bg='#16213e')
        row4.pack(fill=tk.X, padx=5, pady=5)
        
        # Calculate Button (Left)
        calc_btn = tk.Button(
            row4, text="🔄 Calculate Smart Grid",
            font=('Arial', 10, 'bold'), bg='#4ecdc4', fg='#1a1a2e',
            relief='raised', bd=2, command=self.calculate_survivability
        )
        calc_btn.pack(side=tk.LEFT)
        
        # Portfolio Status (Right)
        self.portfolio_status_label = tk.Label(
            row4, text="📊 Portfolio: Not active",
            font=('Arial', 9), fg='#adb5bd', bg='#16213e'
        )
        self.portfolio_status_label.pack(side=tk.RIGHT)
    
    def force_ai_rebalance(self):
        """บังคับให้ AI rebalance portfolio ทันที"""
        try:
            if not hasattr(self, 'grid_trader') or not self.grid_trader:
                self.log_message("⚠️ Start AI Portfolio first", "WARNING")
                return
                
            if hasattr(self.grid_trader, 'smart_profit_manager'):
                self.grid_trader.smart_profit_manager.run_smart_profit_management()
                self.log_message("⚖️ AI rebalance forced", "SUCCESS")
                self.ai_status_display.config(text="🤖 AI: Rebalancing...", fg='#ffd43b')
                
                # Reset status after 3 seconds
                self.root.after(3000, lambda: self.ai_status_display.config(
                    text="🤖 AI Portfolio: Active", fg='#4ecdc4'
                ))
            else:
                self.log_message("⚠️ AI Portfolio Manager not available", "WARNING")
                
        except Exception as e:
            self.log_message(f"❌ AI rebalance error: {e}", "ERROR")

    def run_ai_optimization(self):
        """รัน AI optimization"""
        try:
            if not hasattr(self, 'grid_trader') or not self.grid_trader:
                self.log_message("⚠️ Start AI Portfolio first", "WARNING")
                return
                
            # Run multiple AI cycles for optimization
            if hasattr(self.grid_trader, 'smart_profit_manager'):
                for i in range(3):  # รัน 3 รอบ
                    self.grid_trader.smart_profit_manager.run_smart_profit_management()
                    time.sleep(1)
                    
                self.log_message("🚀 AI optimization completed", "SUCCESS")
                self.ai_status_display.config(text="🚀 AI: Optimized!", fg='#51cf66')
                
                # Reset status after 5 seconds
                self.root.after(5000, lambda: self.ai_status_display.config(
                    text="🤖 AI Portfolio: Active", fg='#4ecdc4'
                ))
            else:
                self.log_message("⚠️ AI Portfolio Manager not available", "WARNING")
                
        except Exception as e:
            self.log_message(f"❌ AI optimization error: {e}", "ERROR")

    def create_merged_control_section(self, parent):
        """รวม Trading Controls + AI Portfolio Management"""
        control_frame = tk.LabelFrame(
            parent,
            text="🧠 AI Portfolio Trading Controls + Smart Management",
            font=('Arial', 10, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        control_frame.pack(fill=tk.X, pady=(0, 3))
        
        # Row 1: Main Trading Buttons
        btn_row = tk.Frame(control_frame, bg='#16213e')
        btn_row.pack(fill=tk.X, pady=5, padx=5)
        
        self.start_btn = tk.Button(
            btn_row, text="🧠 Start AI Portfolio",
            font=('Arial', 10, 'bold'), bg='#51cf66', fg='#1a1a2e',
            relief='raised', bd=2, width=18, command=self.start_trading
        )
        self.start_btn.pack(side=tk.LEFT, padx=2)
        
        self.stop_btn = tk.Button(
            btn_row, text="⏹️ Stop AI Trading",
            font=('Arial', 10, 'bold'), bg='#ff6b6b', fg='#ffffff',
            relief='raised', bd=2, width=18, command=self.stop_trading, state='disabled'
        )
        self.stop_btn.pack(side=tk.LEFT, padx=2)
        
        self.emergency_btn = tk.Button(
            btn_row, text="🚨 EMERGENCY",
            font=('Arial', 10, 'bold'), bg='#e74c3c', fg='#ffffff',
            relief='raised', bd=2, width=15, command=self.emergency_stop
        )
        self.emergency_btn.pack(side=tk.LEFT, padx=2)
        
        # AI Status Display (Right side)
        self.ai_status_display = tk.Label(
            btn_row, text="🤖 AI Portfolio: Ready to start",
            font=('Arial', 9), fg='#4ecdc4', bg='#16213e'
        )
        self.ai_status_display.pack(side=tk.RIGHT, padx=10)
        
        # Row 2: AI Portfolio Controls
        ai_controls_row = tk.Frame(control_frame, bg='#16213e')
        ai_controls_row.pack(fill=tk.X, pady=5, padx=5)
        
        # AI Portfolio Section (Left)
        ai_frame = tk.Frame(ai_controls_row, bg='#16213e', relief='groove', bd=1)
        ai_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(ai_frame, text="🧠 AI Portfolio Management", 
                font=('Arial', 9, 'bold'), fg='#4ecdc4', bg='#16213e').pack()
        
        ai_btn_row = tk.Frame(ai_frame, bg='#16213e')
        ai_btn_row.pack(pady=2)
        
        # AI Strategy Selection
        tk.Label(ai_btn_row, text="Strategy:", font=('Arial', 8), 
                fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)
        
        self.ai_strategy_var = tk.StringVar(value="BALANCED")
        self.ai_strategy_combo = ttk.Combobox(
            ai_btn_row, textvariable=self.ai_strategy_var, 
            values=["AGGRESSIVE", "BALANCED", "CONSERVATIVE"], 
            state="readonly", width=12, font=('Arial', 8)
        )
        self.ai_strategy_combo.pack(side=tk.LEFT, padx=2)
        
        # AI Portfolio Buttons
        self.ai_rebalance_btn = tk.Button(
            ai_btn_row, text="⚖️ Force Rebalance",
            font=('Arial', 8, 'bold'), bg='#ffd43b', fg='#1a1a2e',
            relief='raised', bd=2, width=14, command=self.force_ai_rebalance
        )
        self.ai_rebalance_btn.pack(side=tk.LEFT, padx=2)
        
        self.ai_optimize_btn = tk.Button(
            ai_btn_row, text="🚀 AI Optimize",
            font=('Arial', 8, 'bold'), bg='#6f42c1', fg='#ffffff',
            relief='raised', bd=2, width=12, command=self.run_ai_optimization
        )
        self.ai_optimize_btn.pack(side=tk.LEFT, padx=2)
        
        # Recovery System Section (Right)
        recovery_frame = tk.Frame(ai_controls_row, bg='#16213e', relief='groove', bd=1)
        recovery_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        tk.Label(recovery_frame, text="💊 Portfolio Recovery", 
                font=('Arial', 9, 'bold'), fg='#ff6b6b', bg='#16213e').pack()
        
        recovery_btn_row = tk.Frame(recovery_frame, bg='#16213e')
        recovery_btn_row.pack(pady=2)
        
        # Recovery Buttons
        self.manual_recovery_btn = tk.Button(
            recovery_btn_row, text="💊 Manual Recovery",
            font=('Arial', 8, 'bold'), bg='#ff6b6b', fg='#ffffff',
            relief='raised', bd=2, width=15, command=self.manual_trigger_recovery
        )
        self.manual_recovery_btn.pack(side=tk.LEFT, padx=2)
        
        self.auto_recovery_btn = tk.Button(
            recovery_btn_row, text="🤖 Auto: OFF",
            font=('Arial', 8, 'bold'), bg='#6c757d', fg='#ffffff',
            relief='raised', bd=2, width=10, command=self.toggle_auto_recovery
        )
        self.auto_recovery_btn.pack(side=tk.LEFT, padx=2)
        
        # Row 3: Status Information
        status_row = tk.Frame(control_frame, bg='#16213e')
        status_row.pack(fill=tk.X, pady=2, padx=5)
        
        # AI Strategy Description (Left)
        self.ai_strategy_desc = tk.Label(
            status_row, text="⚖️ BALANCED: Smart pair closing + auto hedging",
            font=('Arial', 8), fg='#adb5bd', bg='#16213e'
        )
        self.ai_strategy_desc.pack(side=tk.LEFT)
        
        # Recovery Status (Right)
        self.recovery_status_display = tk.Label(
            status_row, text="💊 Ready: Auto-trigger at -$50",
            font=('Arial', 8), fg='#adb5bd', bg='#16213e'
        )
        self.recovery_status_display.pack(side=tk.RIGHT)

    def create_compact_log_section(self, parent):
        """Create very compact log section"""
        log_frame = tk.LabelFrame(
            parent,
            text="📜 System Logs",
            font=('Arial', 9, 'bold'),
            fg='#ffd700',
            bg='#16213e',
            relief='groove',
            bd=2
        )
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Log display - very small
        self.log_display = scrolledtext.ScrolledText(
            log_frame,
            height=4,  # เล็กมาก แค่ 4 บรรทัด
            font=('Consolas', 8),
            bg='#0f0f0f',
            fg='#00ff00',
            insertbackground='#00ff00'
        )
        self.log_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Clear button - small
        clear_btn = tk.Button(
            log_frame, text="🗑️ Clear",
            font=('Arial', 8), bg='#6c757d', fg='#ffffff',
            command=self.clear_logs
        )
        clear_btn.pack(pady=2)

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
        """Update mode description and target display - แก้ไขให้ทำงานกับ merged GUI"""
        try:
            if not hasattr(self, 'survivability_engine'):
                return
                
            mode_config = self.survivability_engine.mode_configs[self.current_trading_mode]
            
            # Update target label ที่มีอยู่
            target_points = mode_config['target_survivability']
            self.target_label.config(text=f"🎯 Target: {target_points:,} points")
            
            # Risk level colors
            risk_colors = {
                'Low': '#51cf66',
                'Medium': '#ffd43b',
                'High': '#ff6b6b',
                'Very High': '#e74c3c'
            }
            
            risk_level = mode_config['risk_level']
            risk_color = risk_colors.get(risk_level, '#ffffff')
            
            # Update target label with risk info
            self.target_label.config(
                text=f"🎯 Target: {target_points:,} pts | Risk: {risk_level}",
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
        """Create trading control section with Smart Profit Controls + Recovery"""
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
        
        # 💊 Recovery System Section - เพิ่มใหม่
        recovery_frame = tk.LabelFrame(
            control_frame,
            text="💊 Recovery System",
            font=('Arial', 10, 'bold'),
            fg='#ff6b6b',
            bg='#16213e',
            relief='groove',
            bd=1
        )
        recovery_frame.pack(fill=tk.X, pady=(5, 5), padx=10)
        
        # Recovery buttons row
        recovery_row = tk.Frame(recovery_frame, bg='#16213e')
        recovery_row.pack(fill=tk.X, pady=5, padx=5)
        
        # Manual Recovery Button
        self.manual_recovery_btn = tk.Button(
            recovery_row,
            text="💊 Manual Recovery",
            font=('Arial', 9, 'bold'),
            bg='#ff6b6b',
            fg='#ffffff',
            relief='raised',
            bd=2,
            width=18,
            command=self.manual_trigger_recovery
        )
        self.manual_recovery_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Auto Recovery Toggle
        self.auto_recovery_btn = tk.Button(
            recovery_row,
            text="🤖 Auto Recovery: OFF",
            font=('Arial', 9, 'bold'),
            bg='#6c757d',
            fg='#ffffff',
            relief='raised',
            bd=2,
            width=20,
            command=self.toggle_auto_recovery
        )
        self.auto_recovery_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Recovery Status Display
        self.recovery_status_display = tk.Label(
            recovery_row,
            text="💊 Ready: Trigger at -$50",
            font=('Arial', 9),
            fg='#adb5bd',
            bg='#16213e'
        )
        self.recovery_status_display.pack(side=tk.RIGHT)
        
        # Status summary row
        status_frame = tk.Frame(smart_frame, bg='#16213e')
        status_frame.pack(fill=tk.X, pady=(5, 10), padx=5)
        
        self.smart_status_display = tk.Label(
            status_frame,
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
        """Create logging and monitoring section - ลดขนาด"""
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
        
        # Log display - ลดความสูง
        self.log_display = scrolledtext.ScrolledText(
            log_frame,
            height=6,  # ลดจาก 8 เป็น 6
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
        """Update survivability display - แก้ไขให้ทำงานกับ merged GUI"""
        
        # แสดงข้อมูลพื้นฐาน
        self.balance_label.config(text=f"💰 Balance: ${calc['account_balance']:,.2f}")
        
        # แสดง mode และ target
        mode_text = f"Mode: {calc['trading_mode']} | Target: {calc['target_survivability']:,} pts"
        # อัพเดตใน target_label แทน
        self.target_label.config(text=f"🎯 {mode_text}")
        
        # แสดง Base Lot
        if calc.get('lot_size_adjusted', False):
            lot_text = f"🎯 Lot: {calc['base_lot']:.3f} (Ideal: {calc['ideal_base_lot']:.3f}) ⚠️"
            lot_color = '#ffd43b'
        else:
            lot_text = f"🎯 Base Lot: {calc['base_lot']:.3f}"
            lot_color = '#ffffff'
        self.base_lot_label.config(text=lot_text, fg=lot_color)
        
        # แสดง Grid Spacing
        self.grid_spacing_label.config(text=f"📏 Grid Spacing: {calc['grid_spacing']} points")
        
        # แสดง Max Levels
        self.max_levels_label.config(text=f"📈 Max Levels: {calc['max_levels']}")
        
        # แสดง Survivability
        theoretical_surv = calc['survivability']
        realistic_surv = calc.get('realistic_survivability', theoretical_surv)
        target_surv = calc['target_survivability']
        
        if realistic_surv >= target_surv:
            surv_color = '#51cf66'
            status_emoji = "✅"
        elif realistic_surv >= target_surv * 0.8:
            surv_color = '#ffd43b'
            status_emoji = "⚠️"
        else:
            surv_color = '#ff6b6b'
            status_emoji = "❌"
        
        if realistic_surv != theoretical_surv:
            surv_text = f"🛡️ Survivability: {realistic_surv:,.0f} pts {status_emoji} (Theory: {theoretical_surv:,.0f})"
        else:
            surv_text = f"🛡️ Survivability: {realistic_surv:,.0f} pts {status_emoji}"
        
        self.survivability_label.config(text=surv_text, fg=surv_color)
        
        # แสดง Safety Margin
        safety_pct = calc.get('safety_margin_percentage', 40)
        self.safety_margin_label.config(text=f"💪 Safety Margin: ${calc['safety_margin']:,.2f} ({safety_pct:.1f}%)")

    def get_realtime_grid_stats(self) -> Dict:
        """ดึงสถิติ real-time จาก grid trader"""
        
        try:
            if not hasattr(self, 'grid_trader') or not self.grid_trader:
                return {}
                
            current_price = self.grid_trader.get_current_price()
            
            # นับไม้จริงที่วางอยู่
            pending_orders = list(self.grid_trader.pending_orders.values())
            active_positions = list(self.grid_trader.active_positions.values())
            
            if not pending_orders:
                return {'total_orders': 0, 'actual_survivability': 0}
            
            # คำนวณ average lot size
            total_lot = sum(order.lot_size for order in pending_orders)
            avg_lot = total_lot / len(pending_orders) if pending_orders else 0
            
            # คำนวณ actual grid spacing
            prices = sorted([order.price for order in pending_orders])
            if len(prices) >= 2:
                spacings = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
                avg_spacing_dollars = sum(spacings) / len(spacings)
                actual_spacing = int(avg_spacing_dollars / 0.01)  # convert to points
            else:
                actual_spacing = self.grid_trader.grid_spacing
            
            # คำนวณ actual survivability
            if len(prices) >= 2:
                price_range = prices[-1] - prices[0]  # max - min
                actual_survivability = int(price_range / 0.01)  # convert to points
            else:
                actual_survivability = 0
            
            # คำนวณ capital usage จริง
            estimated_margin = total_lot * (200 / 0.01)  # $200 per 0.01 lot
            account_info = self.grid_trader.mt5_connector.get_account_info()
            balance = account_info.get('balance', 1000) if account_info else 1000
            capital_usage = (estimated_margin / balance) * 100
            
            # สถิติเพิ่มเติม
            buy_orders = [o for o in pending_orders if o.direction == "BUY"]
            sell_orders = [o for o in pending_orders if o.direction == "SELL"]
            
            return {
                'total_orders': len(pending_orders),
                'active_positions': len(active_positions),
                'buy_orders': len(buy_orders),
                'sell_orders': len(sell_orders),
                'average_lot_size': round(avg_lot, 3),
                'actual_grid_spacing': actual_spacing,
                'actual_survivability': actual_survivability,
                'actual_capital_usage': round(capital_usage, 1),
                'price_range_dollars': round(prices[-1] - prices[0], 2) if len(prices) >= 2 else 0,
                'current_price': current_price
            }
            
        except Exception as e:
            print(f"❌ Real-time stats error: {e}")
            return {}
    
    def start_trading(self):
        """Start AI Portfolio Trading System"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to MT5 first")
            return
            
        if not self.current_calculations:
            messagebox.showwarning("Warning", "Please calculate survivability first")
            return
            
        # AI Portfolio confirmation
        confirm_msg = f"""🧠 AI PORTFOLIO TRADING CONFIRMATION

You are starting AI-powered portfolio management:

• Account Balance: ${self.current_calculations['account_balance']:,.2f}
• Starting Positions: 2 (1 BUY + 1 SELL)
• AI will manage portfolio dynamically
• No stop losses - AI rebalances automatically

🤖 AI Features:
• Smart pair closing for profits
• Automatic hedging for large losses  
• Dynamic position rebalancing
• Portfolio health monitoring

This is REAL trading with AI management!

Are you ready to start?"""

        if not messagebox.askyesno("🧠 AI PORTFOLIO CONFIRMATION", confirm_msg):
            return
            
        try:
            # Initialize AI Portfolio system
            gold_symbol = self.mt5_connector.get_gold_symbol()
            self.grid_trader = AIGoldGrid(
                self.mt5_connector,
                self.current_calculations,
                self.config
            )
            
            # Initialize the AI portfolio
            self.log_message("🧠 Initializing AI Portfolio Trading System...", "INFO")
            if not self.grid_trader.initialize_grid():
                raise Exception("Failed to initialize AI portfolio system")
            
            # Start AI trading
            if self.grid_trader.start_trading():
                self.is_trading = True
                self.start_btn.config(state='disabled', bg='#6c757d')
                self.stop_btn.config(state='normal', bg='#dc3545')
                
                self.log_message("🧠 AI Portfolio Trading Started!", "SUCCESS")
                self.log_message(f"🤖 AI managing {gold_symbol} with smart portfolio optimization", "INFO")
                self.log_message(f"🎯 Magic Number: {self.grid_trader.magic_number}", "INFO")
                
                # Start trading monitoring thread
                self.trading_thread = threading.Thread(target=self.run_trading_loop, daemon=True)
                self.trading_thread.start()
                
                # Start real-time monitoring
                self.start_real_time_monitoring()
            else:
                raise Exception("Failed to start AI portfolio system")
            
        except Exception as e:
            self.log_message(f"❌ Start AI Portfolio Error: {str(e)}", "ERROR")
            messagebox.showerror("AI Portfolio Error", f"Failed to start AI portfolio:\n{str(e)}")

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
        """Update GUI with AI Portfolio data - ทับของเดิมเลย"""
        try:
            # Basic trading info
            total_pnl = status.get('total_pnl', 0)
            active_positions = status.get('active_positions', 0)
            pending_orders = status.get('pending_orders', 0)
            market_open = status.get('market_open', True)
            
            # AI Portfolio specific
            if total_pnl >= 0:
                color = '#51cf66'  # Green for profit
                text = f"🧠 AI Portfolio Profit: +${total_pnl:.2f} ({active_positions} positions)"
            else:
                color = '#ff6b6b'  # Red for loss
                text = f"🧠 AI Portfolio Loss: ${total_pnl:.2f} ({active_positions} positions)"
                    
            # Add market status
            market_emoji = "🟢" if market_open else "🔴"
            text += f" | Market: {market_emoji}"
                    
            self.current_drawdown_label.config(text=text, fg=color)
            
            # AI Portfolio Status Display
            if not hasattr(self, 'ai_portfolio_status_label'):
                self.ai_portfolio_status_label = tk.Label(
                    self.current_drawdown_label.master,
                    text="",
                    font=('Arial', 10),
                    fg='#4ecdc4',
                    bg='#16213e'
                )
                self.ai_portfolio_status_label.pack(anchor='w', pady=2)
            
            # Get AI Portfolio summary
            ai_summary = {}
            try:
                if hasattr(self, 'grid_trader') and self.grid_trader:
                    ai_summary = self.grid_trader.get_ai_portfolio_summary()
            except Exception as ai_error:
                ai_summary = {'error': str(ai_error)}
                
            # Display AI status
            if 'error' not in ai_summary:
                health = ai_summary.get('portfolio_health', 50)
                pairs = ai_summary.get('profitable_pairs_available', 0)
                hedges = ai_summary.get('hedge_opportunities', 0)
                performance = ai_summary.get('performance_score', 50)
                
                # Health color
                if health >= 80:
                    health_color = '#51cf66'  # Green
                    health_emoji = "🟢"
                elif health >= 60:
                    health_color = '#ffd43b'  # Yellow
                    health_emoji = "🟡"
                else:
                    health_color = '#ff6b6b'  # Red  
                    health_emoji = "🔴"
                
                ai_text = f"🧠 AI Health: {health}% {health_emoji} | Performance: {performance}/100"
                
                if pairs > 0:
                    ai_text += f" | 💰 Profitable Pairs: {pairs}"
                if hedges > 0:
                    ai_text += f" | 🛡️ Hedge Ops: {hedges}"
                    
                self.ai_portfolio_status_label.config(text=ai_text, fg=health_color)
            else:
                self.ai_portfolio_status_label.config(
                    text="🧠 AI Portfolio: Error getting status", 
                    fg='#ff6b6b'
                )
            
            # Position breakdown
            if not hasattr(self, 'position_breakdown_label'):
                self.position_breakdown_label = tk.Label(
                    self.current_drawdown_label.master,
                    text="",
                    font=('Arial', 9),
                    fg='#adb5bd',
                    bg='#16213e'
                )
                self.position_breakdown_label.pack(anchor='w', pady=1)
            
            # Show position details
            breakdown_text = f"📊 Trading: {pending_orders} pending orders"
            
            if not market_open:
                breakdown_text += " | 🕒 Market Closed - AI monitoring only"
            else:
                breakdown_text += " | 🚀 AI actively managing portfolio"
                
            self.position_breakdown_label.config(text=breakdown_text)
            
        except Exception as e:
            print(f"❌ AI Portfolio display update error: {e}")

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
        """Monitor system status - เพิ่ม recovery status update"""
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
                        
                    # Update recovery status - เพิ่มใหม่
                    if hasattr(self, 'recovery_status_display'):
                        self.root.after(0, self.update_recovery_status_display)
                        
                time.sleep(2)  # Monitor every 2 seconds
                
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(5)

    def manual_trigger_recovery(self):
        """Manual trigger recovery system"""
        try:
            if not hasattr(self, 'grid_trader') or not self.grid_trader:
                self.log_message("⚠️ Start trading first", "WARNING")
                messagebox.showwarning("Recovery", "Please start trading first")
                return
                
            if not hasattr(self.grid_trader, 'smart_profit_manager'):
                self.log_message("⚠️ Smart Profit Manager not available", "WARNING")
                return
                
            result = self.grid_trader.smart_profit_manager.manual_trigger_recovery()
            
            if result:
                self.log_message("💊 Manual recovery started", "SUCCESS")
                self.recovery_status_display.config(text="💊 RECOVERY ACTIVE", fg='#ff6b6b')
            else:
                self.log_message("⚠️ Recovery failed to start", "WARNING")
                
        except Exception as e:
            self.log_message(f"❌ Recovery error: {e}", "ERROR")

    def toggle_auto_recovery(self):
        """Toggle auto recovery mode"""
        try:
            if hasattr(self, 'grid_trader') and self.grid_trader and hasattr(self.grid_trader, 'smart_profit_manager'):
                current_auto = getattr(self.grid_trader.smart_profit_manager, 'recovery_auto_mode', False)
                self.grid_trader.smart_profit_manager.recovery_auto_mode = not current_auto
                
                if self.grid_trader.smart_profit_manager.recovery_auto_mode:
                    self.auto_recovery_btn.config(text="🤖 Auto: ON", bg='#51cf66')
                    self.recovery_status_display.config(text="💊 Auto Mode: ON", fg='#51cf66')
                    self.log_message("🤖 Auto Recovery: ENABLED", "SUCCESS")
                else:
                    self.auto_recovery_btn.config(text="🤖 Auto: OFF", bg='#6c757d')
                    self.recovery_status_display.config(text="💊 Ready: Trigger -$50", fg='#adb5bd')
                    self.log_message("🤖 Auto Recovery: DISABLED", "WARNING")
            else:
                self.log_message("⚠️ Recovery system not available", "WARNING")
                
        except Exception as e:
            self.log_message(f"❌ Toggle recovery error: {e}", "ERROR")

    def update_recovery_status_display(self):
        """Update recovery status in GUI - เรียกใน monitoring loop"""
        try:
            if (hasattr(self, 'grid_trader') and self.grid_trader and 
                hasattr(self.grid_trader, 'smart_profit_manager')):
                
                recovery_status = self.grid_trader.smart_profit_manager.get_recovery_status()
                
                if recovery_status.get('active'):
                    elapsed = recovery_status.get('elapsed_minutes', 0)
                    self.recovery_status_display.config(
                        text=f"💊 ACTIVE: {elapsed:.1f}min elapsed",
                        fg='#ff6b6b'
                    )
                elif recovery_status.get('auto_mode'):
                    self.recovery_status_display.config(
                        text="💊 Auto Mode: ENABLED",
                        fg='#51cf66'
                    )
                else:
                    trigger_loss = recovery_status.get('trigger_loss', -50)
                    self.recovery_status_display.config(
                        text=f"💊 Ready: Trigger at ${trigger_loss}",
                        fg='#adb5bd'
                    )
            else:
                self.recovery_status_display.config(
                    text="💊 Not initialized",
                    fg='#6c757d'
                )
                
        except Exception as e:
            self.recovery_status_display.config(
                text="💊 Status error",
                fg='#ff6b6b'
            )


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