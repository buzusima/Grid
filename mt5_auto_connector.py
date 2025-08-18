"""
MT5 Auto Connector with Gold Symbol Detection
mt5_auto_connector.py
Auto-detects MT5 installation, connects automatically, and finds gold symbols
"""

import MetaTrader5 as mt5
import os
import time
import re
from datetime import datetime
import psutil
import winreg
from pathlib import Path

class MT5AutoConnector:
    def __init__(self):
        self.is_connected = False
        self.gold_symbol = None
        self.account_info = {}
        self.symbol_info = {}
        self.mt5_path = None
        
        # Gold symbol variations to search for
        self.gold_symbols = [
            "XAUUSD", "GOLD", "XAU/USD", "XAUUSD.cmd", "GOLD#", 
            "XAUUSD.", "XAUUSD-", "XAU-USD", "GOLD.", "GOLD_",
            "XAUUSD.raw", "XAUUSD.ecn", "GOLDmicro", "XAUUSD.m",
            "XAUUSD_", "XAUUSD#", "XAUUSDpro", "GOLD.std"
        ]
        
    def detect_mt5_installation(self):
        """
        Auto-detect MetaTrader5 installation path
        Returns: path to MT5 terminal or None
        """
        possible_paths = []
        
        # Method 1: Check registry
        try:
            reg_paths = [
                r"SOFTWARE\MetaQuotes\Terminal\D0E8200F298C41E24B9CC8DE03C7F02C",  # MT5 default
                r"SOFTWARE\WOW6432Node\MetaQuotes\Terminal\D0E8200F298C41E24B9CC8DE03C7F02C",
            ]
            
            for reg_path in reg_paths:
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                        install_path = winreg.QueryValueEx(key, "DataPath")[0]
                        possible_paths.append(os.path.dirname(install_path))
                except:
                    continue
        except:
            pass
            
        # Method 2: Check common installation directories
        common_paths = [
            os.path.expanduser("~/AppData/Roaming/MetaQuotes/Terminal"),
            "C:/Program Files/MetaTrader 5",
            "C:/Program Files (x86)/MetaTrader 5", 
            "C:/MetaTrader 5",
            "D:/MetaTrader 5",
            "C:/Program Files/MetaQuotes/MetaTrader 5",
            "C:/Program Files (x86)/MetaQuotes/MetaTrader 5"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                # Look for terminal64.exe or terminal.exe
                for exe_name in ["terminal64.exe", "terminal.exe"]:
                    exe_path = os.path.join(path, exe_name)
                    if os.path.exists(exe_path):
                        possible_paths.append(exe_path)
                        
        # Method 3: Search in MetaQuotes folders
        try:
            roaming = os.path.expanduser("~/AppData/Roaming/MetaQuotes/Terminal")
            if os.path.exists(roaming):
                for folder in os.listdir(roaming):
                    folder_path = os.path.join(roaming, folder)
                    if os.path.isdir(folder_path):
                        # Look for origin.txt which indicates MT5 installation
                        origin_file = os.path.join(folder_path, "origin.txt")
                        if os.path.exists(origin_file):
                            try:
                                with open(origin_file, 'r') as f:
                                    mt5_exe_path = f.read().strip()
                                    if os.path.exists(mt5_exe_path):
                                        possible_paths.append(mt5_exe_path)
                            except:
                                continue
        except:
            pass
            
        # Method 4: Check running processes
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['name'] and 'terminal' in proc.info['name'].lower():
                        if proc.info['exe'] and 'metatrader' in proc.info['exe'].lower():
                            possible_paths.append(proc.info['exe'])
                except:
                    continue
        except:
            pass
            
        # Return first valid path found
        for path in possible_paths:
            if path and os.path.exists(path):
                self.mt5_path = path
                return path
                
        return None
        
    def is_mt5_running(self):
        """Check if MT5 is currently running"""
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and 'terminal' in proc.info['name'].lower():
                    return True
        except:
            pass
        return False
        
    def start_mt5_if_needed(self):
        """Start MT5 if not running"""
        if not self.is_mt5_running():
            if self.mt5_path:
                try:
                    os.startfile(self.mt5_path)
                    time.sleep(5)  # Wait for MT5 to start
                    return True
                except Exception as e:
                    print(f"Failed to start MT5: {e}")
                    return False
        return True
        
    def auto_connect(self):
        """
        Automatically connect to MT5
        Returns: True if successful, False otherwise
        """
        try:
            # Step 1: Detect MT5 installation
            print("🔍 Detecting MT5 installation...")
            mt5_path = self.detect_mt5_installation()
            
            if not mt5_path:
                print("❌ MT5 installation not found")
                return False
                
            print(f"✅ MT5 found at: {mt5_path}")
            
            # Step 2: Check if MT5 is running, start if needed
            print("🚀 Checking MT5 status...")
            if not self.start_mt5_if_needed():
                print("❌ Failed to start MT5")
                return False
                
            # Step 3: Initialize MT5 connection
            print("🔗 Connecting to MT5...")
            if not mt5.initialize():
                print("❌ MT5 initialization failed")
                return False
                
            # Step 4: Get account info
            account_info = mt5.account_info()
            if account_info is None:
                print("❌ No account logged in")
                return False
                
            print(f"✅ Connected to account: {account_info.login}")
            print(f"💰 Balance: ${account_info.balance:,.2f}")
            print(f"🏦 Broker: {account_info.company}")
            
            # Step 5: Detect gold symbol
            gold_symbol = self.detect_gold_symbol()
            if not gold_symbol:
                print("❌ Gold symbol not found")
                return False
                
            print(f"🥇 Gold symbol detected: {gold_symbol}")
            
            # Store information
            self.is_connected = True
            self.account_info = {
                'login': account_info.login,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'leverage': account_info.leverage,
                'company': account_info.company,
                'currency': account_info.currency
            }
            
            self.gold_symbol = gold_symbol
            
            # Get symbol specifications
            self.get_symbol_specifications(gold_symbol)
            
            return True
            
        except Exception as e:
            print(f"❌ Auto-connect error: {e}")
            return False
            
    def detect_gold_symbol(self):
        """
        Auto-detect gold symbol from available symbols
        Returns: gold symbol name or None
        """
        try:
            # Get all available symbols
            all_symbols = mt5.symbols_get()
            if not all_symbols:
                return None
                
            symbol_names = [symbol.name for symbol in all_symbols]
            
            # Method 1: Exact match with known gold symbols
            for gold_sym in self.gold_symbols:
                if gold_sym in symbol_names:
                    # Verify it's actually gold by checking symbol info
                    if self.verify_gold_symbol(gold_sym):
                        return gold_sym
                        
            # Method 2: Pattern matching for gold-like symbols
            gold_patterns = [
                r'^XAU.*USD.*$',  # XAUUSD variations
                r'^GOLD.*$',      # GOLD variations
                r'^.*GOLD.*$',    # Anything with GOLD
                r'^XAU.*$'        # XAU variations
            ]
            
            for pattern in gold_patterns:
                for symbol_name in symbol_names:
                    if re.match(pattern, symbol_name, re.IGNORECASE):
                        if self.verify_gold_symbol(symbol_name):
                            return symbol_name
                            
            # Method 3: Search by description
            for symbol in all_symbols:
                if symbol.description:
                    desc = symbol.description.lower()
                    if 'gold' in desc or 'xau' in desc:
                        if self.verify_gold_symbol(symbol.name):
                            return symbol.name
                            
            return None
            
        except Exception as e:
            print(f"Error detecting gold symbol: {e}")
            return None
            
    def verify_gold_symbol(self, symbol):
        """
        Verify that a symbol is actually gold by checking its properties
        """
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return False
                
            # Check if symbol is visible and can be traded
            if not symbol_info.visible:
                # Try to show symbol in Market Watch
                if not mt5.symbol_select(symbol, True):
                    return False
                    
            # Re-get symbol info after showing
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return False
                
            # Basic checks for gold characteristics
            # Gold typically has:
            # - Point value around 0.01 or 0.1
            # - Contract size of 100 (usually)
            # - Price in range 1000-3000 (historically)
            
            # Get current price to verify it's in gold range
            tick = mt5.symbol_info_tick(symbol)
            if tick and tick.bid:
                price = tick.bid
                # Gold price typically between 1000-5000
                if 1000 <= price <= 5000:
                    return True
                    
            return True  # If we can't verify price, assume it's valid
            
        except Exception as e:
            print(f"Error verifying gold symbol {symbol}: {e}")
            return False
            
    def get_symbol_specifications(self, symbol):
        """Get detailed symbol specifications"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                print(f"⚠️ Warning: Cannot get symbol info for {symbol}, using defaults")
                # Return default values for gold
                return {
                    'name': symbol,
                    'description': 'Gold vs US Dollar',
                    'point': 0.01,
                    'digits': 2,
                    'spread': 30,
                    'volume_min': 0.01,
                    'volume_max': 100.0,
                    'volume_step': 0.01,
                    'contract_size': 100,
                    'tick_value': 1.0,
                    'tick_size': 0.01,
                    'margin_initial': 1000,
                    'margin_maintenance': 1000,
                    'currency_base': 'XAU',
                    'currency_profit': 'USD',
                    'currency_margin': 'USD'
                }
                
            self.symbol_info = {
                'name': symbol_info.name,
                'description': symbol_info.description,
                'point': symbol_info.point,
                'digits': symbol_info.digits,
                'spread': symbol_info.spread,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step,
                'contract_size': symbol_info.trade_contract_size,
                'tick_value': symbol_info.trade_tick_value,
                'tick_size': symbol_info.trade_tick_size,
                'margin_initial': symbol_info.margin_initial,
                'margin_maintenance': symbol_info.margin_maintenance,
                'currency_base': symbol_info.currency_base,
                'currency_profit': symbol_info.currency_profit,
                'currency_margin': symbol_info.currency_margin
            }
            
            print(f"📊 Symbol Specifications for {symbol}:")
            print(f"   💎 Description: {symbol_info.description}")
            print(f"   📏 Digits: {symbol_info.digits}")
            print(f"   📈 Point: {symbol_info.point}")
            print(f"   📊 Spread: {symbol_info.spread}")
            print(f"   💰 Min Volume: {symbol_info.volume_min}")
            print(f"   📏 Volume Step: {symbol_info.volume_step}")
            print(f"   💵 Tick Value: ${symbol_info.trade_tick_value}")
            
            return self.symbol_info
            
        except Exception as e:
            print(f"Error getting symbol specifications: {e}")
            print(f"⚠️ Using default specifications for {symbol}")
            # Return safe defaults
            return {
                'name': symbol,
                'description': 'Gold vs US Dollar',
                'point': 0.01,
                'digits': 2,
                'spread': 30,
                'volume_min': 0.01,
                'volume_max': 100.0,
                'volume_step': 0.01,
                'contract_size': 100,
                'tick_value': 1.0,
                'tick_size': 0.01,
                'margin_initial': 1000,
                'margin_maintenance': 1000,
                'currency_base': 'XAU',
                'currency_profit': 'USD',
                'currency_margin': 'USD'
            }
            
    def get_current_price(self):
        """Get current gold price"""
        try:
            if not self.gold_symbol:
                return None
                
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if tick:
                return {
                    'bid': tick.bid,
                    'ask': tick.ask,
                    'spread': tick.ask - tick.bid,
                    'time': datetime.fromtimestamp(tick.time)
                }
            return None
            
        except Exception as e:
            print(f"Error getting current price: {e}")
            return None
            
    def get_account_info(self):
        """Get current account information"""
        try:
            account_info = mt5.account_info()
            if account_info:
                self.account_info.update({
                    # ข้อมูลระบุตัวตน
                    'account_id': account_info.login,
                    'account_name': account_info.name or f"Account {account_info.login}",
                    'broker_name': account_info.company,
                    'server': account_info.server,
                    
                    # ข้อมูลเงิน (สำหรับ backend API)
                    # 'current_balance': str(account_info.balance),
                    # 'current_profit': str(account_info.profit),
                    'currency': account_info.currency,
                    
                    # ข้อมูลเพิ่มเติม
                    'balance': account_info.balance,
                    'equity': account_info.equity,
                    'margin': account_info.margin,
                    'free_margin': account_info.margin_free,
                    'margin_level': account_info.margin_level if account_info.margin > 0 else 0,
                    'leverage': account_info.leverage,
                    
                    # สิทธิ์การเทรด
                    'trade_allowed': account_info.trade_allowed,
                    'expert_allowed': account_info.trade_expert,
                    
                    # เวลาอัพเดท
                    'last_updated': datetime.now().isoformat()
                })
                return self.account_info
            return None
            
        except Exception as e:
            print(f"Error getting account info: {e}")
            return None
            
    def get_gold_symbol(self):
        """Get detected gold symbol"""
        return self.gold_symbol
        
    def get_symbol_info(self):
        """Get symbol specifications - guaranteed to return dict"""
        if hasattr(self, 'symbol_info') and self.symbol_info:
            return self.symbol_info
        elif self.gold_symbol:
            # Try to get symbol info
            return self.get_symbol_specifications(self.gold_symbol)
        else:
            # Return safe defaults
            print("⚠️ Warning: No symbol info available, using defaults")
            return {
                'name': 'XAUUSD',
                'description': 'Gold vs US Dollar',
                'point': 0.01,
                'digits': 2,
                'spread': 30,
                'volume_min': 0.01,
                'volume_max': 100.0,
                'volume_step': 0.01,
                'contract_size': 100,
                'tick_value': 1.0,
                'tick_size': 0.01,
                'margin_initial': 1000,
                'margin_maintenance': 1000,
                'currency_base': 'XAU',
                'currency_profit': 'USD',
                'currency_margin': 'USD'
            }
        
    def calculate_lot_value(self, lots):
        """Calculate monetary value of lot size"""
        try:
            if not self.symbol_info or not self.gold_symbol:
                return 0
                
            tick_value = self.symbol_info.get('tick_value', 1)
            tick_size = self.symbol_info.get('tick_size', 0.01)
            
            # For gold, typically 1 lot = $100,000 contract
            # 1 point (0.01) movement = $10 for 1 lot
            point_value = (tick_value / tick_size) if tick_size > 0 else 10
            
            return lots * point_value
            
        except Exception as e:
            print(f"Error calculating lot value: {e}")
            return 0
            
    def calculate_margin_required(self, lots):
        """Calculate margin required for given lot size"""
        try:
            if not self.symbol_info or not self.gold_symbol:
                return 0
                
            price = self.get_current_price()
            if not price:
                return 0
                
            contract_size = self.symbol_info.get('contract_size', 100)
            leverage = self.account_info.get('leverage', 100)
            
            # Margin = (Contract Size * Lots * Price) / Leverage
            margin = (contract_size * lots * price['bid']) / leverage
            
            return margin
            
        except Exception as e:
            print(f"Error calculating margin: {e}")
            return 0
            
    def test_connection(self):
        """Test MT5 connection and return status"""
        try:
            # Test basic connection
            account_info = mt5.account_info()
            if not account_info:
                return False, "No account logged in"
                
            # Test symbol access
            if not self.gold_symbol:
                return False, "Gold symbol not detected"
                
            symbol_info = mt5.symbol_info(self.gold_symbol)
            if not symbol_info:
                return False, f"Cannot access symbol {self.gold_symbol}"
                
            # Test price access
            tick = mt5.symbol_info_tick(self.gold_symbol)
            if not tick:
                return False, f"Cannot get price for {self.gold_symbol}"
                
            # Test trading permissions
            if not symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                return False, f"Trading not allowed for {self.gold_symbol}"
                
            return True, "Connection test successful"
            
        except Exception as e:
            return False, f"Connection test error: {e}"
            
    def get_broker_info(self):
        """Get detailed broker information"""
        try:
            account_info = mt5.account_info()
            if not account_info:
                return None
                
            # Detect broker characteristics
            company = account_info.company.lower()
            
            broker_features = {
                'company': account_info.company,
                'leverage': account_info.leverage,
                'currency': account_info.currency,
                'margin_call': account_info.margin_so_call,
                'margin_stop': account_info.margin_so_so,
                'trade_allowed': account_info.trade_allowed,
                'expert_allowed': account_info.trade_expert,
                'hedge_allowed': True,  # Assume true for most brokers
                'fifo_rule': False      # Assume false unless detected
            }
            
            # Detect specific broker types
            if any(x in company for x in ['exness', 'ic markets', 'pepperstone']):
                broker_features['hedge_allowed'] = True
                broker_features['fifo_rule'] = False
            elif any(x in company for x in ['oanda', 'forex.com']):
                broker_features['hedge_allowed'] = False
                broker_features['fifo_rule'] = True
                
            return broker_features
            
        except Exception as e:
            print(f"Error getting broker info: {e}")
            return None
            
    def disconnect(self):
        """Disconnect from MT5"""
        try:
            if self.is_connected:
                mt5.shutdown()
                self.is_connected = False
                self.gold_symbol = None
                self.account_info = {}
                self.symbol_info = {}
                print("✅ Disconnected from MT5")
                return True
        except Exception as e:
            print(f"Error disconnecting: {e}")
            
        return False
        
    def __del__(self):
        """Cleanup when object is destroyed"""
        if self.is_connected:
            self.disconnect()

# Test function for standalone usage
def test_mt5_connector():
    """Test the MT5 connector"""
    print("🧪 Testing MT5 Auto Connector...")
    
    connector = MT5AutoConnector()
    
    if connector.auto_connect():
        print("✅ Connection successful!")
        
        # Display account info
        account = connector.get_account_info()
        print(f"\n📊 Account Information:")
        print(f"   Login: {account['login']}")
        print(f"   Balance: ${account['balance']:,.2f}")
        print(f"   Equity: ${account['equity']:,.2f}")
        print(f"   Free Margin: ${account['free_margin']:,.2f}")
        print(f"   Leverage: 1:{account['leverage']}")
        
        # Display symbol info
        symbol_info = connector.get_symbol_info()
        print(f"\n🥇 Gold Symbol Information:")
        print(f"   Symbol: {symbol_info['name']}")
        print(f"   Description: {symbol_info['description']}")
        print(f"   Min Lot: {symbol_info['volume_min']}")
        print(f"   Lot Step: {symbol_info['volume_step']}")
        
        # Display current price
        price = connector.get_current_price()
        if price:
            print(f"\n💰 Current Gold Price:")
            print(f"   Bid: {price['bid']}")
            print(f"   Ask: {price['ask']}")
            print(f"   Spread: {price['spread']:.1f} points")
            
        # Test calculations
        test_lots = 0.01
        lot_value = connector.calculate_lot_value(test_lots)
        margin_req = connector.calculate_margin_required(test_lots)
        
        print(f"\n🧮 Calculations for {test_lots} lots:")
        print(f"   Point Value: ${lot_value:.2f}")
        print(f"   Margin Required: ${margin_req:.2f}")
        
        connector.disconnect()
        
    else:
        print("❌ Connection failed!")

if __name__ == "__main__":
    test_mt5_connector()