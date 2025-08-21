"""
MT5 Order Testing & Debugging Tool
ตรวจสอบสาเหตุที่ mt5.order_send() return None
"""

import MetaTrader5 as mt5
from datetime import datetime
import time

class MT5OrderTester:
    def __init__(self, symbol="XAUUSD.v"):
        self.symbol = symbol
        self.magic_number = 77703292
        self.initialize_mt5()
    
    def initialize_mt5(self):
        """🆕 Initialize MT5 connection"""
        
        try:
            print("🔧 Initializing MT5...")
            
            # Initialize MT5
            if not mt5.initialize():
                print(f"❌ MT5 initialize failed: {mt5.last_error()}")
                return False
            
            # Check connection
            terminal = mt5.terminal_info()
            if terminal:
                print(f"✅ Terminal connected: {terminal.connected}")
                print(f"✅ Company: {terminal.company}")
            else:
                print("❌ Cannot get terminal info")
                return False
            
            # Check account
            account = mt5.account_info()
            if account:
                print(f"✅ Account: {account.login}")
                print(f"✅ Balance: ${account.balance:.2f}")
            else:
                print("❌ No account info")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ MT5 initialization error: {e}")
            return False
    def test_all_scenarios(self):
        """🧪 ทดสอบทุกสถานการณ์"""
        
        print("="*60)
        print("🧪 MT5 ORDER COMPREHENSIVE TEST")
        print("="*60)
        
        # Test 1: Basic MT5 Status
        self.test_mt5_basic_status()
        
        # Test 2: Symbol Information
        self.test_symbol_information()
        
        # Test 3: Account Limitations
        self.test_account_limitations()
        
        # Test 4: Simple Order Tests
        self.test_simple_orders()
        
        # Test 5: Different Order Types
        self.test_different_order_types()
        
        # Test 6: Parameter Testing
        self.test_parameter_variations()
        
        # Test 7: Magic Number Testing
        self.test_magic_number_issues()
        
        print("="*60)
        print("🧪 TEST COMPLETED")
        print("="*60)
    
    def test_mt5_basic_status(self):
        """Test 1: Basic MT5 Status"""
        
        print("\n🔍 TEST 1: MT5 Basic Status")
        print("-" * 40)
        
        try:
            # Terminal Info
            terminal = mt5.terminal_info()
            if terminal:
                print(f"✅ Terminal connected: {terminal.connected}")
                print(f"✅ Trade allowed: {terminal.trade_allowed}")
                print(f"✅ Build: {terminal.build}")
                print(f"✅ Company: {terminal.company}")
            else:
                print("❌ Cannot get terminal info")
                return False
            
            # Account Info
            account = mt5.account_info()
            if account:
                print(f"✅ Account: {account.login}")
                print(f"✅ Balance: ${account.balance:.2f}")
                print(f"✅ Trade allowed: {account.trade_allowed}")
                print(f"✅ Trade expert: {account.trade_expert}")
                print(f"✅ Trade mode: {account.trade_mode}")
                print(f"✅ Margin mode: {account.margin_mode}")
            else:
                print("❌ Cannot get account info")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Basic status error: {e}")
            return False
    
    def test_symbol_information(self):
        """Test 2: Symbol Information"""
        
        print(f"\n🔍 TEST 2: Symbol Information ({self.symbol})")
        print("-" * 40)
        
        try:
            # Symbol Info
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info:
                print(f"✅ Symbol name: {symbol_info.name}")
                print(f"✅ Visible: {symbol_info.visible}")
                print(f"✅ Trade mode: {symbol_info.trade_mode}")
                print(f"✅ Volume min: {symbol_info.volume_min}")
                print(f"✅ Volume max: {symbol_info.volume_max}")
                print(f"✅ Volume step: {symbol_info.volume_step}")
                print(f"✅ Tick size: {symbol_info.trade_tick_size}")
                print(f"✅ Tick value: {symbol_info.trade_tick_value}")
                print(f"✅ Point: {symbol_info.point}")
                print(f"✅ Digits: {symbol_info.digits}")
                print(f"✅ Stops level: {symbol_info.trade_stops_level}")
                print(f"✅ Freeze level: {symbol_info.trade_freeze_level}")
                
                # ลองเปิด symbol ถ้าไม่ visible
                if not symbol_info.visible:
                    print("⚠️ Symbol not visible - attempting to select...")
                    result = mt5.symbol_select(self.symbol, True)
                    print(f"   Select result: {result}")
                
            else:
                print(f"❌ Cannot get symbol info for {self.symbol}")
                return False
            
            # Tick Info
            tick = mt5.symbol_info_tick(self.symbol)
            if tick:
                print(f"✅ Current bid: ${tick.bid:.2f}")
                print(f"✅ Current ask: ${tick.ask:.2f}")
                print(f"✅ Spread: ${(tick.ask - tick.bid):.2f}")
                print(f"✅ Last: ${tick.last:.2f}")
                print(f"✅ Time: {datetime.fromtimestamp(tick.time)}")
            else:
                print("❌ Cannot get tick info")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Symbol info error: {e}")
            return False
    
    def test_account_limitations(self):
        """Test 3: Account Limitations"""
        
        print("\n🔍 TEST 3: Account Limitations")
        print("-" * 40)
        
        try:
            account = mt5.account_info()
            if not account:
                print("❌ No account info")
                return False
            
            # Account Type Analysis
            print(f"📊 Account Analysis:")
            print(f"   Login: {account.login}")
            print(f"   Server: {account.server}")
            print(f"   Currency: {account.currency}")
            print(f"   Leverage: 1:{account.leverage}")
            print(f"   Margin mode: {account.margin_mode}")
            print(f"   Trade mode: {account.trade_mode}")
            print(f"   Stopout mode: {account.margin_so_mode}")
            print(f"   Stopout level: {account.margin_so_so}%")
            
            # Check existing positions and orders
            positions = mt5.positions_get(symbol=self.symbol)
            orders = mt5.orders_get(symbol=self.symbol)
            
            print(f"\n📊 Current Trading Status:")
            print(f"   Active positions: {len(positions) if positions else 0}")
            print(f"   Pending orders: {len(orders) if orders else 0}")
            
            if orders:
                print(f"   Existing orders:")
                for order in orders[:3]:  # Show first 3
                    print(f"     Order {order.ticket}: {order.type} {order.volume} @ {order.price_open}")
            
            # Magic number check
            all_orders = mt5.orders_get()
            magic_conflicts = []
            if all_orders:
                for order in all_orders:
                    if order.magic == self.magic_number:
                        magic_conflicts.append(order.ticket)
            
            if magic_conflicts:
                print(f"⚠️ Magic number conflicts: {magic_conflicts}")
            else:
                print(f"✅ Magic number {self.magic_number} is clean")
            
            return True
            
        except Exception as e:
            print(f"❌ Account limitations error: {e}")
            return False
    
    def test_simple_orders(self):
        """Test 4: Simple Order Tests"""
        
        print("\n🔍 TEST 4: Simple Order Tests")
        print("-" * 40)
        
        try:
            # Get current price
            tick = mt5.symbol_info_tick(self.symbol)
            if not tick:
                print("❌ Cannot get current price")
                return False
            
            current_price = tick.bid
            print(f"💰 Current price: ${current_price:.2f}")
            
            # Test 1: Minimal Market Order
            print(f"\n🧪 Test 4.1: Minimal Market BUY Order")
            market_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": 0.01,
                "type": mt5.ORDER_TYPE_BUY,
                "magic": self.magic_number,
                "comment": "TEST_MARKET"
            }
            
            print(f"   Request: {market_request}")
            result = mt5.order_send(market_request)
            
            if result is not None:
                print(f"   ✅ Got result: {result.retcode}")
                print(f"   Comment: {getattr(result, 'comment', 'No comment')}")
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   🎉 MARKET ORDER SUCCESS!")
                    # Close it immediately
                    self.close_position_by_ticket(result.order)
                else:
                    print(f"   ❌ Market order failed: {result.retcode}")
            else:
                print(f"   ❌ Market order returned None")
            
            time.sleep(2)
            
            # Test 2: Minimal Pending Order
            print(f"\n🧪 Test 4.2: Minimal Pending BUY LIMIT Order")
            
            buy_price = round(current_price - 2.0, 2)  # $2 below market
            
            pending_request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": self.symbol,
                "volume": 0.01,
                "type": mt5.ORDER_TYPE_BUY_LIMIT,
                "price": buy_price,
                "magic": self.magic_number,
                "comment": "TEST_PENDING"
            }
            
            print(f"   Request: {pending_request}")
            print(f"   Price: ${buy_price:.2f} (${current_price - buy_price:.2f} below market)")
            
            result = mt5.order_send(pending_request)
            
            if result is not None:
                print(f"   ✅ Got result: {result.retcode}")
                print(f"   Comment: {getattr(result, 'comment', 'No comment')}")
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   🎉 PENDING ORDER SUCCESS!")
                    # Cancel it immediately
                    self.cancel_order_by_ticket(result.order)
                else:
                    print(f"   ❌ Pending order failed: {result.retcode}")
                    print(f"   Error description: {self.get_error_description(result.retcode)}")
            else:
                print(f"   ❌ Pending order returned None")
            
            return True
            
        except Exception as e:
            print(f"❌ Simple order test error: {e}")
            return False
    
    def test_different_order_types(self):
        """Test 5: Different Order Types"""
        
        print("\n🔍 TEST 5: Different Order Types")
        print("-" * 40)
        
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            current_price = tick.bid
            
            order_tests = [
                {
                    "name": "BUY LIMIT",
                    "type": mt5.ORDER_TYPE_BUY_LIMIT,
                    "price": round(current_price - 1.5, 2)
                },
                {
                    "name": "SELL LIMIT", 
                    "type": mt5.ORDER_TYPE_SELL_LIMIT,
                    "price": round(current_price + 1.5, 2)
                },
                {
                    "name": "BUY STOP",
                    "type": mt5.ORDER_TYPE_BUY_STOP,
                    "price": round(current_price + 1.5, 2)
                },
                {
                    "name": "SELL STOP",
                    "type": mt5.ORDER_TYPE_SELL_STOP,
                    "price": round(current_price - 1.5, 2)
                }
            ]
            
            for i, test in enumerate(order_tests):
                print(f"\n🧪 Test 5.{i+1}: {test['name']}")
                
                request = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": self.symbol,
                    "volume": 0.01,
                    "type": test["type"],
                    "price": test["price"],
                    "magic": self.magic_number + i + 100,  # Different magic
                    "comment": f"TEST_{test['name'].replace(' ', '_')}"
                }
                
                print(f"   Price: ${test['price']:.2f} (current: ${current_price:.2f})")
                
                result = mt5.order_send(request)
                
                if result is not None:
                    print(f"   ✅ Result: {result.retcode}")
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"   🎉 {test['name']} SUCCESS!")
                        self.cancel_order_by_ticket(result.order)
                    else:
                        print(f"   ❌ {test['name']} failed: {self.get_error_description(result.retcode)}")
                else:
                    print(f"   ❌ {test['name']} returned None")
                
                time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"❌ Order types test error: {e}")
            return False
    
    def test_parameter_variations(self):
        """Test 6: Parameter Variations"""
        
        print("\n🔍 TEST 6: Parameter Variations")
        print("-" * 40)
        
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            current_price = tick.bid
            test_price = round(current_price - 2.0, 2)
            
            parameter_tests = [
                {
                    "name": "Basic Request",
                    "request": {
                        "action": mt5.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": 0.01,
                        "type": mt5.ORDER_TYPE_BUY_LIMIT,
                        "price": test_price,
                        "magic": self.magic_number
                    }
                },
                {
                    "name": "With Comment",
                    "request": {
                        "action": mt5.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": 0.01,
                        "type": mt5.ORDER_TYPE_BUY_LIMIT,
                        "price": test_price,
                        "magic": self.magic_number,
                        "comment": "TEST_COMMENT"
                    }
                },
                {
                    "name": "With Deviation",
                    "request": {
                        "action": mt5.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": 0.01,
                        "type": mt5.ORDER_TYPE_BUY_LIMIT,
                        "price": test_price,
                        "magic": self.magic_number,
                        "deviation": 20
                    }
                },
                {
                    "name": "With Type Filling",
                    "request": {
                        "action": mt5.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": 0.01,
                        "type": mt5.ORDER_TYPE_BUY_LIMIT,
                        "price": test_price,
                        "magic": self.magic_number,
                        "type_filling": mt5.ORDER_FILLING_RETURN
                    }
                },
                {
                    "name": "With Type Time",
                    "request": {
                        "action": mt5.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": 0.01,
                        "type": mt5.ORDER_TYPE_BUY_LIMIT,
                        "price": test_price,
                        "magic": self.magic_number,
                        "type_time": mt5.ORDER_TIME_GTC
                    }
                }
            ]
            
            for i, test in enumerate(parameter_tests):
                print(f"\n🧪 Test 6.{i+1}: {test['name']}")
                print(f"   Request: {test['request']}")
                
                result = mt5.order_send(test["request"])
                
                if result is not None:
                    print(f"   ✅ Result: {result.retcode}")
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"   🎉 {test['name']} SUCCESS!")
                        self.cancel_order_by_ticket(result.order)
                    else:
                        print(f"   ❌ Failed: {self.get_error_description(result.retcode)}")
                else:
                    print(f"   ❌ Returned None")
                
                time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"❌ Parameter test error: {e}")
            return False
    
    def test_magic_number_issues(self):
        """Test 7: Magic Number Testing"""
        
        print("\n🔍 TEST 7: Magic Number Testing")
        print("-" * 40)
        
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            current_price = tick.bid
            test_price = round(current_price - 2.0, 2)
            
            magic_tests = [
                {"name": "Magic 0", "magic": 0},
                {"name": "Magic 123", "magic": 123},
                {"name": "Magic 12345", "magic": 12345},
                {"name": "Current Magic", "magic": self.magic_number},
                {"name": "Large Magic", "magic": 999999999}
            ]
            
            for i, test in enumerate(magic_tests):
                print(f"\n🧪 Test 7.{i+1}: {test['name']} ({test['magic']})")
                
                request = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": self.symbol,
                    "volume": 0.01,
                    "type": mt5.ORDER_TYPE_BUY_LIMIT,
                    "price": test_price,
                    "magic": test["magic"],
                    "comment": f"MAGIC_TEST_{test['magic']}"
                }
                
                result = mt5.order_send(request)
                
                if result is not None:
                    print(f"   ✅ Result: {result.retcode}")
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"   🎉 Magic {test['magic']} SUCCESS!")
                        self.cancel_order_by_ticket(result.order)
                    else:
                        print(f"   ❌ Failed: {self.get_error_description(result.retcode)}")
                else:
                    print(f"   ❌ Returned None")
                
                time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"❌ Magic number test error: {e}")
            return False
    
    def close_position_by_ticket(self, ticket):
        """Close position by ticket"""
        try:
            positions = mt5.positions_get(ticket=ticket)
            if positions:
                position = positions[0]
                tick = mt5.symbol_info_tick(self.symbol)
                
                if position.type == mt5.POSITION_TYPE_BUY:
                    price = tick.bid
                    order_type = mt5.ORDER_TYPE_SELL
                else:
                    price = tick.ask
                    order_type = mt5.ORDER_TYPE_BUY
                
                close_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": position.volume,
                    "type": order_type,
                    "position": ticket,
                    "price": price,
                    "magic": position.magic,
                    "comment": "TEST_CLOSE"
                }
                
                result = mt5.order_send(close_request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   ✅ Position {ticket} closed")
                else:
                    print(f"   ⚠️ Failed to close position {ticket}")
        except Exception as e:
            print(f"   ❌ Close position error: {e}")
    
    def cancel_order_by_ticket(self, ticket):
        """Cancel order by ticket"""
        try:
            cancel_request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": ticket
            }
            
            result = mt5.order_send(cancel_request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"   ✅ Order {ticket} canceled")
            else:
                print(f"   ⚠️ Failed to cancel order {ticket}")
        except Exception as e:
            print(f"   ❌ Cancel order error: {e}")
    
    def get_error_description(self, error_code):
        """Get error description"""
        error_codes = {
            10004: "Requote",
            10006: "Request rejected", 
            10007: "Request canceled",
            10008: "Order placed",
            10009: "Request completed",
            10010: "Partial fill only",
            10011: "Request processing error",
            10012: "Request timeout",
            10013: "Invalid request",
            10014: "Invalid volume",
            10015: "Invalid price",
            10016: "Invalid stops",
            10017: "Trade disabled",
            10018: "Market closed",
            10019: "Not enough money",
            10020: "Price changed",
            10021: "Off quotes",
            10022: "Invalid expiration",
            10023: "Order state changed",
            10024: "Too many requests",
            10025: "No changes",
            10026: "Autotrading disabled",
            10027: "Market closed",
            10028: "Invalid price in request",
            10029: "Invalid stops in request",
            10030: "Invalid volume in request"
        }
        return error_codes.get(error_code, f"Unknown error: {error_code}")

# วิธีใช้งาน
if __name__ == "__main__":
    # สร้าง tester
    tester = MT5OrderTester("XAUUSD.v")
    
    # รันการทดสอบทั้งหมด
    tester.test_all_scenarios()