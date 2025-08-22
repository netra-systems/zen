#!/usr/bin/env python3
"""
WebSocket Connection Test for Netra Backend

This script tests WebSocket endpoints to validate:
1. Connection establishment
2. Authentication handling  
3. Message sending/receiving
4. Error handling
"""

import asyncio
import json
import sys
import time
from datetime import datetime

print("Installing required dependencies...")
import subprocess
try:
    import websockets
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

print("Dependencies installed successfully")

class WebSocketConnectionTester:
    def __init__(self):
        self.results = {}
        self.backend_running = False
        
    async def check_backend_health(self, base_url="http://localhost:8000"):
        """Check if backend is running"""
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                self.backend_running = True
                print(f"✓ Backend is running at {base_url}")
                print(f"  Health response: {response.json()}")
                return True
        except Exception as e:
            print(f"✗ Backend not reachable at {base_url}: {e}")
        
        self.backend_running = False
        return False
    
    async def test_websocket_info_endpoint(self, base_url="http://localhost:8000"):
        """Test the WebSocket info endpoint"""
        try:
            response = requests.get(f"{base_url}/ws", timeout=5)
            print(f"WebSocket info endpoint status: {response.status_code}")
            if response.status_code == 200:
                info = response.json()
                print(f"Available endpoints: {info.get(\"endpoints\", {})}")
                return info
        except Exception as e:
            print(f"Failed to get WebSocket info: {e}")
        return None
    
    async def test_basic_websocket_connection(self, ws_url, timeout=10):
        """Test basic WebSocket connection without auth"""
        test_name = f"Basic Connection: {ws_url}"
        result = {
            "url": ws_url,
            "connected": False,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": [],
            "duration": 0,
            "close_code": None,
            "close_reason": None
        }
        
        start_time = time.time()
        try:
            print(f"\nTesting {test_name}")
            
            async with websockets.connect(ws_url, timeout=timeout) as websocket:
                result["connected"] = True
                print(f"✓ Connected to {ws_url}")
                
                # Send ping message
                ping_message = {
                    "type": "ping",
                    "timestamp": time.time(),
                    "test_id": "websocket_test"
                }
                
                await websocket.send(json.dumps(ping_message))
                result["messages_sent"] = 1
                print(f"Sent: {ping_message}")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    result["messages_received"] = 1
                    parsed_response = json.loads(response)
                    print(f"Received: {parsed_response}")
                except asyncio.TimeoutError:
                    print("No response received within timeout")
                    result["errors"].append("Response timeout")
                
        except websockets.exceptions.ConnectionClosedError as e:
            result["close_code"] = e.code
            result["close_reason"] = e.reason
            result["errors"].append(f"Connection closed: {e.code} - {e.reason}")
            print(f"✗ Connection closed: {e.code} - {e.reason}")
            
        except Exception as e:
            result["errors"].append(str(e))
            print(f"✗ Connection failed: {e}")
        
        result["duration"] = time.time() - start_time
        self.results[test_name] = result
        return result
    
    async def run_comprehensive_test(self):
        """Run comprehensive WebSocket testing"""
        print("=== NETRA WEBSOCKET CONNECTION AUDIT ===")
        print(f"Test started at: {datetime.now().isoformat()}")
        
        # 1. Check backend health
        backend_ok = await self.check_backend_health()
        if not backend_ok:
            print("\n❌ Backend not running - cannot test WebSocket connections")
            return
        
        # 2. Check WebSocket info endpoints
        await self.test_websocket_info_endpoint()
        
        # 3. Test WebSocket endpoints
        test_urls = [
            "ws://localhost:8000/ws",
            "ws://localhost:8000/ws/secure"
        ]
        
        for url in test_urls:
            await self.test_basic_websocket_connection(url)
        
        # 4. Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("WEBSOCKET CONNECTION AUDIT REPORT")
        print("="*60)
        
        total_tests = len(self.results)
        successful_connections = sum(1 for r in self.results.values() if r["connected"])
        
        print(f"Total Tests: {total_tests}")
        print(f"Successful Connections: {successful_connections}")
        print(f"Backend Running: {\"Yes\" if self.backend_running else \"No\"}")
        
        print(f"\nDETAILED RESULTS:")
        print("-" * 60)
        
        for test_name, result in self.results.items():
            status = "✓ PASS" if result["connected"] else "✗ FAIL"
            
            print(f"\n{test_name}: {status}")
            print(f"  Connected: {result[\"connected\"]}")
            print(f"  Messages Sent: {result[\"messages_sent\"]}")
            print(f"  Messages Received: {result[\"messages_received\"]}")
            print(f"  Duration: {result[\"duration\"]:.2f}s")
            
            if result["errors"]:
                print(f"  Errors: {result[\"errors\"]}")


async def main():
    """Main test execution"""
    tester = WebSocketConnectionTester()
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())
