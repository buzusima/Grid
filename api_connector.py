"""
Backend API Connector
backend_api_connector.py
Pure API communication layer for backend status checking
"""

import requests
import json
from datetime import datetime
from typing import Dict, Optional, Tuple
import time

class BackendAPIConnector:
    def __init__(self, api_base_url: str, timeout: int = 10, bot_name: str = "Grid", bot_version: str = "0.0.1"):
        """
        Initialize Backend API Connector
        
        Args:
            api_base_url: Base URL for backend API
            timeout: Request timeout in seconds
            bot_name: Name of the bot for identification
            bot_version: Version of the bot
        """
        self.api_base_url = api_base_url.rstrip('/')  # Remove trailing slash
        self.timeout = timeout
        self.bot_name = bot_name
        self.bot_version = bot_version
        
        # Request session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': f'{bot_name}/{bot_version}'
        })
        
        # print(f"🔗 Backend API Connector initialized")
        # print(f"   Base URL: {self.api_base_url}")
        # print(f"   Bot: {self.bot_name} v{self.bot_version}")
        # print(f"   Timeout: {self.timeout}s")

    def check_trading_status(self, account_data: Dict) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Check trading status with backend API
        
        Args:
            account_data: Account information from MT5 connector
            
        Returns:
            Tuple[success: bool, response_data: Dict, error_message: str]
        """
        try:
            print(f"🔍 Checking trading status with backend...")
            
            # Prepare payload
            payload = self._prepare_account_payload(account_data)
            
            print(f"📤 Sending request to: {self.api_base_url}/customer-clients/status")
            # print(f"📊 Account: {payload.get('tradingAccountId')} | Balance: ${payload.get('currentBalance', 0):,.2f}")
            
            # Make API request
            # start_time = time.time()
            response = self.session.post(
                f"{self.api_base_url}/customer-clients/status",
                json=payload,
                timeout=self.timeout
                # f"{self.api_base_url}/customer-clients/status",
                # json={
                #     "tradingAccountId": "000005",
                #     "name": "Dupoin",
                #     "brokerName": "000003",
                #     "currentBalance": "1000000",
                #     "currentProfit": "1000",
                #     "currency": "currency",
                #     "botName": "AI Dashboard",
                #     "botVersion": "0.0.1"
                # },
            )
            # request_duration = time.time() - start_time
            
            # print(f"📡 API Response: {response.status_code} ({request_duration:.2f}s)")
            
            # Handle response
            if response.status_code == 200:
                response_data = response.json()
                print(f"✅ Status check successful")
                return True, response_data, None
            else:
                error_msg = f"API returned status {response.status_code}"
                try:
                    error_detail = response.json().get('message', 'No error message')
                    error_msg += f": {error_detail}"
                except:
                    error_msg += f": {response.text[:100]}"
                    
                print(f"❌ Status check failed: {error_msg}")
                return False, None, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {self.timeout}s"
            print(f"⏰ {error_msg}")
            return False, None, error_msg
            
        except requests.exceptions.ConnectionError:
            error_msg = "Connection error - backend unreachable"
            print(f"🔌 {error_msg}")
            return False, None, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            print(f"❌ {error_msg}")
            return False, None, error_msg
            
        except json.JSONDecodeError:
            error_msg = "Invalid JSON response from backend"
            print(f"📄 {error_msg}")
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"💥 {error_msg}")
            return False, None, error_msg

    def _prepare_account_payload(self, account_data: Dict) -> Dict:
        """
        Prepare request payload from MT5 account data
        
        Args:
            account_data: Raw account data from MT5 connector
            
        Returns:
            Dict: Formatted payload for API request
        """
        try:
            # Extract required fields with safe defaults
            payload = {
                "tradingAccountId": str(self._safe_get(account_data, 'login', 'account_id', default='unknown')),
                "name": self._safe_get(account_data, 'name', 'account_name', default='AI Trading Account'),
                "brokerName": self._safe_get(account_data, 'company', 'broker_name', default='Unknown Broker'),
                "currentBalance": '0',
                "currentProfit": '0',
                "currency": self._safe_get(account_data, 'currency', default='USD'),
                "botName": self.bot_name,
                "botVersion": self.bot_version
            }
            
            # # Calculate equity if not provided (but keep as string)
            # if 'equity' in account_data:
            #     equity_val = float(account_data['equity']) if isinstance(account_data['equity'], str) else account_data['equity']
            #     balance_val = float(payload["currentBalance"])
            #     calculated_profit = equity_val - balance_val
            #     payload["currentProfit"] = str(round(calculated_profit, 2))
            
            # # Ensure numeric formatting for display but keep as strings
            # try:
            #     balance_val = self._safe_get(account_data, 'balance', 'current_balance', default='0')
            #     profit_val = self._safe_get(account_data, 'profit', 'current_profit', default='0')
                
            #     # Convert to float, format, then back to string
            #     balance_float = float(balance_val)
            #     profit_float = float(profit_val)
                
            #     payload["currentBalance"] = f"{balance_float:.2f}"
            #     payload["currentProfit"] = f"{profit_float:.2f}"
            # except (ValueError, TypeError):
            #     # Keep original values if conversion fails
            #     payload["currentBalance"] = str(payload["currentBalance"])
            #     payload["currentProfit"] = str(payload["currentProfit"])
            
            print(f"📦 Payload prepared:")
            print(f"   Account: {payload['tradingAccountId']}")
            print(f"   Broker: {payload['brokerName']}")
            print(f"   Balance: {payload['currentBalance']}")
            print(f"   Profit: {payload['currentProfit']}")
            print(f"   Currency: {payload['currency']}")
            
            return payload
            
        except Exception as e:
            print(f"❌ Error preparing payload: {e}")
            # Return minimal payload to prevent complete failure
            return {
                "tradingAccountId": "error",
                "name": "Error Account",
                "brokerName": "Unknown",
                "currentBalance": 0.0,
                "currentProfit": 0.0,
                "currency": "USD",
                "botName": self.bot_name,
                "botVersion": self.bot_version
            }

    def _safe_get(self, data: Dict, *keys, default=None):
        """
        Safely get value from dict using multiple possible keys
        
        Args:
            data: Dictionary to search
            *keys: Possible keys to try
            default: Default value if none found
            
        Returns:
            Value found or default
        """
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
        return default

    def format_datetime_response(self, datetime_str: str) -> Optional[datetime]:
        """
        Format datetime string from backend response
        Handles microseconds truncation and timezone parsing
        
        Args:
            datetime_str: Datetime string from backend
            
        Returns:
            datetime object or None if parsing fails
        """
        try:
            if not datetime_str:
                return None
                
            # Handle microseconds truncation
            if '.' in datetime_str and '+' in datetime_str:
                parts = datetime_str.split('.')
                microseconds = parts[1].split('+')[0]
                timezone_part = '+' + parts[1].split('+')[1]
                
                # Truncate microseconds to 6 digits
                if len(microseconds) > 6:
                    microseconds = microseconds[:6]
                
                datetime_str = f"{parts[0]}.{microseconds}{timezone_part}"
            
            # Parse to datetime object
            parsed_datetime = datetime.fromisoformat(datetime_str)
            print(f"📅 Parsed datetime: {parsed_datetime}")
            
            return parsed_datetime
            
        except Exception as e:
            print(f"❌ Error parsing datetime '{datetime_str}': {e}")
            return None

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to backend API
        
        Returns:
            Tuple[success: bool, message: str]
        """
        try:
            print(f"🧪 Testing backend connection...")
            
            # Simple test payload
            test_payload = {
                "tradingAccountId": "test_connection",
                "name": "Connection Test",
                "brokerName": "Test Broker",
                "currentBalance": 1000.0,
                "currentProfit": 0.0,
                "currency": "USD",
                "botName": self.bot_name,
                "botVersion": self.bot_version
            }
            
            start_time = time.time()
            response = self.session.post(
                f"{self.api_base_url}/customer-clients/status",
                json=test_payload,
                timeout=5  # Shorter timeout for test
            )
            duration = time.time() - start_time
            
            if response.status_code in [200, 400, 401, 403]:  # Any proper HTTP response
                print(f"✅ Backend reachable ({duration:.2f}s)")
                return True, f"Connection successful - {response.status_code}"
            else:
                print(f"⚠️ Backend returned {response.status_code}")
                return False, f"Unexpected status code: {response.status_code}"
                
        except requests.exceptions.Timeout:
            print(f"⏰ Connection test timeout")
            return False, "Connection timeout"
            
        except requests.exceptions.ConnectionError:
            print(f"🔌 Connection test failed")
            return False, "Cannot reach backend"
            
        except Exception as e:
            print(f"❌ Connection test error: {e}")
            return False, f"Test error: {str(e)}"

    def get_connection_info(self) -> Dict:
        """
        Get connector configuration info
        
        Returns:
            Dict with connector information
        """
        return {
            'api_base_url': self.api_base_url,
            'timeout': self.timeout,
            'bot_name': self.bot_name,
            'bot_version': self.bot_version,
            'endpoint': f"{self.api_base_url}/customer-clients/status"
        }

    def close(self):
        """Close session and cleanup"""
        try:
            self.session.close()
            print(f"🔒 Backend API Connector closed")
        except Exception as e:
            print(f"❌ Error closing connector: {e}")

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            if hasattr(self, 'session'):
                self.session.close()
        except:
            pass

# Example usage and testing
def test_backend_connector():
    """Test the backend connector with sample data"""
    
    print("🧪 Testing Backend API Connector...")
    print("="*50)
    
    # Initialize connector
    connector = BackendAPIConnector(
        api_base_url="http://123.253.62.50:8080/api",
        timeout=10,
        bot_name="Grid",
        bot_version="0.0.1"
    )
    
    # Test connection
    success, message = connector.test_connection()
    print(f"Connection test: {'✅' if success else '❌'} {message}")
    
    # Sample account data (as would come from MT5)
    sample_account_data = {
        'login': 12345678,
        'balance': 10000.50,
        'equity': 10150.75,
        'company': 'Test Broker LLC',
        'currency': 'USD',
        'name': 'AI Trading Account'
    }
    
    # Test status check
    print(f"\n📊 Testing status check with sample data...")
    success, response_data, error_msg = connector.check_trading_status(sample_account_data)
    
    if success:
        print(f"✅ Status check successful!")
        print(f"📄 Response: {json.dumps(response_data, indent=2)}")
        
        # Test datetime parsing if present
        if response_data and 'nextReportTime' in response_data:
            next_time = connector.format_datetime_response(response_data['nextReportTime'])
            print(f"📅 Next report time: {next_time}")
    else:
        print(f"❌ Status check failed: {error_msg}")
    
    # Show connector info
    info = connector.get_connection_info()
    print(f"\n🔧 Connector Info:")
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    # Cleanup
    connector.close()
    
    print(f"\n" + "="*50)
    print(f"✅ Backend Connector Test Completed")

if __name__ == "__main__":
    test_backend_connector()