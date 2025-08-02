"""
MT5 Auto Connector - Auto-detect and connect to MetaTrader5
Automatically detects MT5 installation, connects to active account,
and identifies gold trading symbols across different brokers.
File: mt5_auto_connector.py
"""

import MetaTrader5 as mt5
import os
import sys
import time
import winreg
from pathlib import Path
import psutil
from datetime import datetime

class MT5AutoConnector:
    def __init__(self):
        self.mt5_path = None
        self.is_connected = False
        self.account_info = None
        self.gold_symbol = None
        self.gold_specifications = None
        
        # Common gold symbols across brokers
        self.possible_gold_symbols = [
            "XAUUSD", "GOLD", "XAU/USD", "XAUUSD.cmd", "GOLD#", 
            "XAUUSD.", "XAUUSD.raw", "GOLD.cmd", "XAU-USD",
            "XAUUSD_", "GOLDUSD", "XAU_USD", "Gold", "XAUUSD#",
            "XAUUSD.c", "XAUUSD.ecn", "XAUUSD.pro", "XAUUSD.m",
            "XAUUSDm", "XAUUSDc", "XAUUSD.low", "XAUUSD_m"
        ]
        
    def detect_mt5_installation(self):
        """Auto-detect MetaTrader5 installation path"""
        print("🔍 Detecting MetaTrader5 installation...")
        
        # Method 1: Check registry
        mt5_path = self._check_registry()
        if mt5_path and os.path.exists(mt5_path):
            self.mt5_path = mt5_path
            print(f"✅ Found MT5 via registry: {mt5_path}")
            return True
            
        # Method 2: Check running processes
        mt5_path = self._check_running_processes()
        if mt5_path:
            self.mt5_path = mt5_path
            print(f"✅ Found MT5 via running process: {mt5_path}")
            return True
            
        # Method 3: Check common installation paths
        mt5_path = self._check_common_paths()
        if mt5_path:
            self.mt5_path = mt5_path
            print(f"✅ Found MT5 via common path: {mt5_path}")
            return True
            
        print("❌ MetaTrader5 installation not found")
        return False
        
    def _check_registry(self):
        """Check Windows registry for MT5 installation"""
        try:
            # Check HKEY_CURRENT_USER
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              r"SOFTWARE\MetaQuotes\Terminal") as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    subkey_name = winreg.EnumKey(key, i)
                    try:
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            path, _ = winreg.QueryValueEx(subkey, "Path")
                            terminal_exe = os.path.join(path, "terminal64.exe")
                            if os.path.exists(terminal_exe):
                                return terminal_exe
                    except:
                        continue
                        
            # Check HKEY_LOCAL_MACHINE
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r"SOFTWARE\MetaQuotes\Terminal") as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    subkey_name = winreg.EnumKey(key, i)
                    try:
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            path, _ = winreg.QueryValueEx(subkey, "Path")
                            terminal_exe = os.path.join(path, "terminal64.exe")
                            if os.path.exists(terminal_exe):
                                return terminal_exe
                    except:
                        continue
                        
        except Exception as e:
            print(f"Registry check error: {e}")
            
        return None
        
    def _check_running_processes(self):
        """Check if MT5 is currently running"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_name = proc.info['name'].lower()
                    if proc_name in ['terminal64.exe', 'terminal.exe', 'metatrader.exe']:
                        exe_path = proc.info['exe']
                        if exe_path and 'terminal' in exe_path.lower():
                            return exe_path
                except:
                    continue
                    
        except Exception as e:
            print(f"Process check error: {e}")
            
        return None
        
    def _check_common_paths(self):
        """Check common MetaTrader5 installation paths"""
        common_paths = [
            # Standard installation paths
            r"C:\Program Files\MetaTrader 5\terminal64.exe",
            r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
            r"C:\Users\{}\AppData\Roaming\MetaQuotes\Terminal\*.exe",
            
            # Broker-specific paths
            r"C:\Program Files\Admiral Markets MetaTrader 5\terminal64.exe",
            r"C:\Program Files\FXTM MetaTrader 5\terminal64.exe",
            r"C:\Program Files\IC Markets MetaTrader 5\terminal64.exe",
            r"C:\Program Files\Exness MetaTrader 5\terminal64.exe",
            r"C:\Program Files\XM MetaTrader 5\terminal64.exe",
            r"C:\Program Files\OANDA MetaTrader 5\terminal64.exe",
            r"C:\Program Files\ActivTrades MetaTrader 5\terminal64.exe",
            
            # Alternative locations
            r"D:\MetaTrader 5\terminal64.exe",
            r"E:\MetaTrader 5\terminal64.exe",
        ]
        
        username = os.getenv('USERNAME', '')
        
        for path_template in common_paths:
            if '{username}' in path_template:
                path = path_template.format(username=username)
            else:
                path = path_template
                
            if '*' in path:
                # Handle wildcard paths
                from glob import glob
                matches = glob(path)
                for match in matches:
                    if os.path.exists(match) and 'terminal' in match.lower():
                        return match
            else:
                if os.path.exists(path):
                    return path
                    
        return None
        
    def auto_connect(self):
        """Auto-connect to MetaTrader5"""
        try:
            # Step 1: Detect MT5 installation
            if not self.detect_mt5_installation():
                raise Exception("MetaTrader5 not found. Please install MT5 first.")
                
            # Step 2: Initialize MT5 connection
            print("🔗 Initializing MT5 connection...")
            
            # Try to initialize with detected path
            if self.mt5_path:
                if not mt5.initialize(path=self.mt5_path):
                    # Try without path (use default)
                    if not mt5.initialize():
                        error = mt5.last_error()
                        raise Exception(f"MT5 initialization failed: {error}")
            else:
                if not mt5.initialize():
                    error = mt5.last_error()
                    raise Exception(f"MT5 initialization failed: {error}")
                    
            print("✅ MT5 initialized successfully")
            
            # Step 3: Get account information
            account_info = mt5.account_info()
            if account_info is None:
                raise Exception("No active account found. Please login to MT5 first.")
                
            self.account_info = account_info._asdict()
            self.is_connected = True
            
            print(f"✅ Connected to account: {self.account_info['login']}")
            print(f"💰 Balance: ${self.account_info['balance']:,.2f}")
            print(f"🏦 Broker: {self.account_info['company']}")
            
            # Step 4: Detect gold symbol
            gold_symbol = self.detect_gold_symbol()
            if not gold_symbol:
                print("⚠️ Warning: Gold symbol not detected")
            else:
                self.gold_symbol = gold_symbol
                print(f"🥇 Gold symbol detected: {gold_symbol}")
                
            return True
            
        except Exception as e:
            print(f"❌ Auto-connect failed: {e}")
            self.disconnect()
            return False
            
    def detect_gold_symbol(self):
        """Detect available gold trading symbol"""
        if not self.is_connected:
            return None
            
        print("🔍 Detecting gold trading symbol...")
        
        try:
            # Get all available symbols
            all_symbols = mt5.symbols_get()
            if not all_symbols:
                print("❌ No symbols available")
                return None
                
            available_symbols = [symbol.name for symbol in all_symbols]
            print(f"📊 Found {len(available_symbols)} total symbols")
            
            # Check each possible gold symbol
            for gold_symbol in self.possible_gold_symbols:
                if gold_symbol in available_symbols:
                    # Verify it's actually a gold symbol by checking specifications
                    if self._verify_gold_symbol(gold_symbol):
                        self.gold_symbol = gold_symbol
                        self.gold_specifications = self._get_symbol_specifications(gold_symbol)
                        print(f"✅ Gold symbol confirmed: {gold_symbol}")
                        self._print_gold_specifications()
                        return gold_symbol
                        
            # If exact match not found, search for symbols containing gold keywords
            gold_keywords = ['XAU', 'GOLD', 'Au']
            for symbol in available_symbols:
                symbol_upper = symbol.upper()
                for keyword in gold_keywords:
                    if keyword in symbol_upper and 'USD' in symbol_upper:
                        if self._verify_gold_symbol(symbol):
                            self.gold_symbol = symbol
                            self.gold_specifications = self._get_symbol_specifications(symbol)
                            print(f"✅ Gold symbol found by keyword: {symbol}")
                            self._print_gold_specifications()
                            return symbol
                            
            print("❌ No gold symbol found")
            return None
            
        except Exception as e:
            print(f"❌ Gold symbol detection error: {e}")
            return None
            
    def _verify_gold_symbol(self, symbol):
        """Verify if symbol is actually gold by checking its properties"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return False
                
            # Check if symbol is tradeable
            if not symbol_info.visible:
                # Try to enable symbol
                if not mt5.symbol_select(symbol, True):
                    return False
                    
            # Get fresh symbol info
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return False
                
            # Basic validation
            description = symbol_info.description.upper()
            path = symbol_info.path.upper()
            
            # Check for gold-related keywords
            gold_keywords = ['GOLD', 'XAU', 'AU/USD', 'PRECIOUS']
            has_gold_keyword = any(keyword in description or keyword in path 
                                 for keyword in gold_keywords)
            
            # Check typical gold characteristics
            # Gold typically has point value around 0.01 and digits of 2 or 3
            reasonable_digits = symbol_info.digits in [2, 3, 4, 5]
            
            # Check if it's a currency pair (should have USD)
            has_usd = 'USD' in symbol.upper()
            
            return has_gold_keyword and reasonable_digits and has_usd
            
        except Exception as e:
            print(f"Symbol verification error for {symbol}: {e}")
            return False
            
    def _get_symbol_specifications(self, symbol):
        """Get detailed symbol specifications"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return None
                
            return {
                'symbol': symbol,
                'description': symbol_info.description,
                'digits': symbol_info.digits,
                'spread': symbol_info.spread,
                'point': symbol_info.point,
                'tick_value': symbol_info.trade_tick_value,
                'tick_size': symbol_info.trade_tick_size,
                'contract_size': symbol_info.trade_contract_size,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step,
                'margin_initial': symbol_info.margin_initial,
                'margin_maintenance': symbol_info.margin_maintenance,
                'swap_long': symbol_info.swap_long,
                'swap_short': symbol_info.swap_short,
                'path': symbol_info.path
            }
            
        except Exception as e:
            print(f"Error getting specifications for {symbol}: {e}")
            return None
            
    def _print_gold_specifications(self):
        """Print gold symbol specifications"""
        if not self.gold_specifications:
            return
            
        specs = self.gold_specifications
        print("\n📋 Gold Symbol Specifications:")
        print(f"   📛 Symbol: {specs['symbol']}")
        print(f"   📝 Description: {specs['description']}")
        print(f"   🔢 Digits: {specs['digits']}")
        print(f"   📏 Point: {specs['point']}")
        print(f"   💰 Tick Value: {specs['tick_value']}")
        print(f"   📊 Contract Size: {specs['contract_size']}")
        print(f"   📈 Volume Min: {specs['volume_min']}")
        print(f"   📉 Volume Step: {specs['volume_step']}")
        print(f"   💸 Spread: {specs['spread']} points")
        
        # Calculate point value for lot calculation
        if specs['digits'] == 2:
            point_value = 1.0  # 1 point = $1 for 0.01 lot
        elif specs['digits'] == 3:
            point_value = 0.1  # 1 point = $0.1 for 0.01 lot  
        else:
            point_value = specs['tick_value'] / specs['tick_size'] * specs['point']
            
        print(f"   🧮 Point Value: ${point_value:.2f} per 0.01 lot")
        print("")
        
    def get_account_info(self):
        """Get current account information"""
        if not self.is_connected:
            return None
            
        try:
            account_info = mt5.account_info()
            if account_info:
                return account_info._asdict()
            return None
        except Exception as e:
            print(f"Error getting account info: {e}")
            return None
            
    def get_gold_symbol(self):
        """Get detected gold symbol"""
        return self.gold_symbol
        
    def get_gold_specifications(self):
        """Get gold symbol specifications"""
        return self.gold_specifications
        
    def get_current_price(self, symbol=None):
        """Get current price for symbol"""
        if not symbol:
            symbol = self.gold_symbol
            
        if not symbol or not self.is_connected:
            return None
            
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                return {
                    'symbol': symbol,
                    'bid': tick.bid,
                    'ask': tick.ask,
                    'spread': tick.ask - tick.bid,
                    'time': datetime.fromtimestamp(tick.time)
                }
            return None
        except Exception as e:
            print(f"Error getting price for {symbol}: {e}")
            return None
            
    def test_connection(self):
        """Test MT5 connection and functionality"""
        if not self.is_connected:
            return False
            
        try:
            # Test account info
            account = self.get_account_info()
            if not account:
                return False
                
            # Test symbol info
            if self.gold_symbol:
                price = self.get_current_price()
                if not price:
                    print("⚠️ Warning: Cannot get gold price")
                    
            # Test positions
            positions = mt5.positions_get()
            
            # Test orders
            orders = mt5.orders_get()
            
            print("✅ Connection test passed")
            return True
            
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
            
    def get_trading_info(self):
        """Get comprehensive trading information"""
        if not self.is_connected:
            return None
            
        try:
            account = self.get_account_info()
            positions = mt5.positions_get()
            orders = mt5.orders_get()
            price = self.get_current_price()
            
            return {
                'account': account,
                'gold_symbol': self.gold_symbol,
                'gold_specs': self.gold_specifications,
                'current_price': price,
                'positions_count': len(positions) if positions else 0,
                'orders_count': len(orders) if orders else 0,
                'connection_time': datetime.now(),
                'mt5_version': mt5.version()
            }
            
        except Exception as e:
            print(f"Error getting trading info: {e}")
            return None
            
    def disconnect(self):
        """Disconnect from MetaTrader5"""
        try:
            if self.is_connected:
                mt5.shutdown()
                self.is_connected = False
                self.account_info = None
                self.gold_symbol = None
                self.gold_specifications = None
                print("✅ Disconnected from MT5")
        except Exception as e:
            print(f"Error during disconnect: {e}")

def test_connector():
    """Test the MT5 Auto Connector"""
    print("🧪 Testing MT5 Auto Connector...")
    print("=" * 50)
    
    connector = MT5AutoConnector()
    
    # Test connection
    if connector.auto_connect():
        print("\n✅ Auto-connection successful!")
        
        # Test functionality
        if connector.test_connection():
            print("\n📊 Getting trading information...")
            trading_info = connector.get_trading_info()
            
            if trading_info:
                print(f"\n📋 Trading Summary:")
                print(f"   🏦 Broker: {trading_info['account']['company']}")
                print(f"   👤 Account: {trading_info['account']['login']}")
                print(f"   💰 Balance: ${trading_info['account']['balance']:,.2f}")
                print(f"   🥇 Gold Symbol: {trading_info['gold_symbol']}")
                
                if trading_info['current_price']:
                    price = trading_info['current_price']
                    print(f"   💹 Current Price: {price['bid']:.{trading_info['gold_specs']['digits']}f}")
                    print(f"   📊 Spread: {price['spread']:.{trading_info['gold_specs']['digits']}f}")
                    
                print(f"   📈 Open Positions: {trading_info['positions_count']}")
                print(f"   📋 Pending Orders: {trading_info['orders_count']}")
        
        # Disconnect
        connector.disconnect()
        
    else:
        print("❌ Auto-connection failed")
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure MetaTrader5 is installed")
        print("   2. Login to your MT5 account")
        print("   3. Make sure MT5 is running")
        print("   4. Check if Python has admin rights")

if __name__ == "__main__":
    test_connector()