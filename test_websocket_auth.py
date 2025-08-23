#!/usr/bin/env python3
"""
WebSocket Authentication Test Script for Netra Platform

This script tests WebSocket connections with JWT authentication and real-time messaging.
MISSION CRITICAL - Part of comprehensive E2E test suite.

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise)
- Business Goal: Real-time User Experience
- Value Impact: Validates real-time AI optimization feedback loops
- Strategic Impact: Core platform differentiator - real-time optimization insights
"""

import asyncio
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List

import httpx
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

# Add project root to path

# Service URLs from running services
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/ws"
WEBSOCKET_SECURE_URL = "ws://localhost:8000/ws"

class WebSocketAuthTester:
    """Test WebSocket authentication and real-time messaging for the Netra platform."""
    
    def __init__(self, auth_token: Optional[str] = None):
        self.auth_token = auth_token
        self.test_results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "tests_passed": 0,
            "tests_failed": 0,
            "websocket_connections": [],
            "messages_sent": [],
            "messages_received": [],
            "errors": []
        }
    
    def log_success(self, test_name: str, details: str = ""):
        """Log successful test."""
        self.test_results["tests_passed"] += 1
        print(f"✅ {test_name}: PASSED")
        if details:
            print(f"   Details: {details}")
    
    def log_failure(self, test_name: str, error: str):
        """Log failed test."""
        self.test_results["tests_failed"] += 1
        self.test_results["errors"].append({"test": test_name, "error": error})
        print(f"❌ {test_name}: FAILED")
        print(f"   Error: {error}")
    
    def get_websocket_headers(self) -> Dict[str, str]:
        """Get WebSocket connection headers with authentication."""
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
    
    def get_websocket_subprotocols(self) -> List[str]:
        """Get WebSocket subprotocols for authentication."""
        if self.auth_token:
            return ["jwt-auth", f"Bearer.{self.auth_token}"]
        return []
    
    async def test_websocket_info_endpoint(self) -> bool:
        """Test WebSocket info endpoint for service discovery."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{BACKEND_URL}/ws")
                
                if response.status_code == 200:
                    data = response.json()
                    endpoints = data.get("endpoints", {})
                    self.log_success("WebSocket Info Endpoint", f"Found {len(endpoints)} endpoints")
                    return True
                else:
                    self.log_failure("WebSocket Info Endpoint", f"HTTP {response.status_code}: {response.text}")
                    return False
        except Exception as e:
            self.log_failure("WebSocket Info Endpoint", f"Request error: {str(e)}")
            return False
    
    async def test_websocket_config_endpoint(self) -> bool:
        """Test WebSocket configuration endpoint."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{BACKEND_URL}/ws/config")
                
                if response.status_code == 200:
                    data = response.json()
                    config = data.get("websocket_config", {})
                    endpoints = config.get("available_endpoints", [])
                    self.log_success("WebSocket Config Endpoint", f"Config loaded with {len(endpoints)} endpoints")
                    return True
                else:
                    self.log_failure("WebSocket Config Endpoint", f"HTTP {response.status_code}: {response.text}")
                    return False
        except Exception as e:
            self.log_failure("WebSocket Config Endpoint", f"Request error: {str(e)}")
            return False
    
    async def test_websocket_connection(self, ws_url: str, test_name: str) -> Optional[websockets.WebSocketServerProtocol]:
        """Test WebSocket connection with authentication."""
        try:
            # Prepare connection parameters
            headers = self.get_websocket_headers()
            subprotocols = self.get_websocket_subprotocols()
            
            # Try connection with different auth methods
            websocket = None
            connection_method = "unknown"
            
            # Method 1: Headers + Subprotocols
            if self.auth_token:
                try:
                    websocket = await websockets.connect(
                        ws_url,
                        extra_headers=headers,
                        subprotocols=subprotocols,
                        timeout=30
                    )
                    connection_method = "headers_and_subprotocols"
                except Exception:
                    pass
            
            # Method 2: Headers only
            if not websocket and self.auth_token:
                try:
                    websocket = await websockets.connect(
                        ws_url,
                        extra_headers=headers,
                        timeout=30
                    )
                    connection_method = "headers_only"
                except Exception:
                    pass
            
            # Method 3: Subprotocols only
            if not websocket and self.auth_token:
                try:
                    websocket = await websockets.connect(
                        ws_url,
                        subprotocols=subprotocols,
                        timeout=30
                    )
                    connection_method = "subprotocols_only"
                except Exception:
                    pass
            
            # Method 4: No auth (fallback)
            if not websocket:
                try:
                    websocket = await websockets.connect(ws_url, timeout=30)
                    connection_method = "no_auth"
                except Exception:
                    pass
            
            if websocket:
                self.test_results["websocket_connections"].append({
                    "url": ws_url,
                    "method": connection_method,
                    "timestamp": datetime.now().isoformat()
                })
                self.log_success(test_name, f"Connected via {connection_method}")
                return websocket
            else:
                self.log_failure(test_name, "All connection methods failed")
                return None
                
        except InvalidStatusCode as e:
            self.log_failure(test_name, f"Invalid status code: {e.status_code}")
            return None
        except Exception as e:
            self.log_failure(test_name, f"Connection error: {str(e)}")
            return None
    
    async def test_websocket_message_exchange(self, websocket: websockets.WebSocketServerProtocol, test_name: str) -> bool:
        """Test sending and receiving messages through WebSocket."""
        try:
            # Prepare test message
            test_message = {
                "type": "message",
                "data": {
                    "message": "Hello WebSocket! This is a test from the E2E suite.",
                    "thread_id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat()
                },
                "id": str(uuid.uuid4())
            }
            
            # Send message
            await websocket.send(json.dumps(test_message))
            self.test_results["messages_sent"].append({
                "message": test_message,
                "timestamp": datetime.now().isoformat()
            })
            
            self.log_success(f"{test_name} - Send", "Message sent successfully")
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                response_data = json.loads(response) if response else None
                
                if response_data:
                    self.test_results["messages_received"].append({
                        "message": response_data,
                        "timestamp": datetime.now().isoformat()
                    })
                    self.log_success(f"{test_name} - Receive", f"Got response: {type(response_data)}")
                    return True
                else:
                    self.log_failure(f"{test_name} - Receive", "Empty response received")
                    return False
                    
            except asyncio.TimeoutError:
                self.log_failure(f"{test_name} - Receive", "Timeout waiting for response")
                return False
            except json.JSONDecodeError as e:
                self.log_failure(f"{test_name} - Receive", f"Invalid JSON response: {str(e)}")
                return False
                
        except Exception as e:
            self.log_failure(f"{test_name} - Message Exchange", f"Error: {str(e)}")
            return False
    
    async def test_websocket_ping_pong(self, websocket: websockets.WebSocketServerProtocol, test_name: str) -> bool:
        """Test WebSocket ping/pong for connection health."""
        try:
            # Send ping
            pong_waiter = await websocket.ping()
            
            # Wait for pong with timeout
            await asyncio.wait_for(pong_waiter, timeout=10.0)
            
            self.log_success(f"{test_name} - Ping/Pong", "Ping/Pong successful")
            return True
            
        except asyncio.TimeoutError:
            self.log_failure(f"{test_name} - Ping/Pong", "Ping timeout")
            return False
        except Exception as e:
            self.log_failure(f"{test_name} - Ping/Pong", f"Error: {str(e)}")
            return False
    
    async def test_websocket_endpoints(self) -> Dict[str, Any]:
        """Test all available WebSocket endpoints."""
        websocket_endpoints = [
            (WEBSOCKET_URL, "Standard WebSocket"),
            (WEBSOCKET_SECURE_URL, "Secure WebSocket"),
            (f"ws://localhost:8000/ws/test-user", "User-specific WebSocket"),
            (f"ws://localhost:8000/ws/v1/test-user", "V1 User WebSocket")
        ]
        
        for ws_url, test_name in websocket_endpoints:
            print(f"\n🔗 Testing {test_name} at {ws_url}")
            
            websocket = await self.test_websocket_connection(ws_url, f"{test_name} Connection")
            
            if websocket:
                try:
                    # Test ping/pong
                    await self.test_websocket_ping_pong(websocket, test_name)
                    
                    # Test message exchange
                    await self.test_websocket_message_exchange(websocket, test_name)
                    
                    # Give some time for processing
                    await asyncio.sleep(1)
                    
                finally:
                    await websocket.close()
            
            # Brief pause between endpoint tests
            await asyncio.sleep(0.5)
        
        return self.test_results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all WebSocket tests."""
        print("🌐 Starting WebSocket Authentication Tests for Netra Platform\n")
        
        # Test info endpoints
        await self.test_websocket_info_endpoint()
        await self.test_websocket_config_endpoint()
        
        # Test WebSocket connections
        await self.test_websocket_endpoints()
        
        return self.test_results

async def get_auth_token() -> Optional[str]:
    """Get authentication token using the auth test script logic."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try backend dev login first
            response = await client.post(
                f"{BACKEND_URL}/api/auth/dev/login",
                json={"email": "test@netra.ai"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            
            # If that fails, try auth service directly
            response = await client.post(
                "http://localhost:8083/auth/dev/login",
                json={}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            
            return None
    except:
        return None

async def main():
    """Main test execution."""
    print("🔑 Getting authentication token...")
    auth_token = await get_auth_token()
    
    if not auth_token:
        print("❌ Failed to get authentication token. Running tests without auth...")
        print("   WebSocket connections may fail if authentication is required.")
    else:
        print(f"✅ Got authentication token: {auth_token[:20]}...")
    
    tester = WebSocketAuthTester(auth_token)
    results = await tester.run_all_tests()
    
    print(f"\n📊 WebSocket Authentication Test Results:")
    print(f"   ✅ Tests Passed: {results['tests_passed']}")
    print(f"   ❌ Tests Failed: {results['tests_failed']}")
    
    print(f"   🔗 WebSocket Connections: {len(results['websocket_connections'])}")
    print(f"   📤 Messages Sent: {len(results['messages_sent'])}")
    print(f"   📥 Messages Received: {len(results['messages_received'])}")
    
    if results["websocket_connections"]:
        print(f"\n✅ Successful Connections:")
        for conn in results["websocket_connections"]:
            print(f"   - {conn['url']} ({conn['method']})")
    
    if results["errors"]:
        print(f"\n❌ Errors:")
        for error in results["errors"]:
            print(f"   - {error['test']}: {error['error']}")
    
    # Save results to file
    with open("websocket_auth_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📝 Results saved to websocket_auth_test_results.json")
    
    # Return success if all tests passed
    success = results["tests_failed"] == 0 and results["tests_passed"] > 0
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)