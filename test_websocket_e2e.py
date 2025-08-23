#!/usr/bin/env python3
"""
End-to-End WebSocket Test Script
Tests authentication and WebSocket connectivity for Netra Apex platform
"""

import asyncio
import json
import sys
import time
from typing import Dict, Any, Optional

import httpx
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
import jwt


class E2EWebSocketTester:
    """Comprehensive end-to-end WebSocket testing for Netra platform"""
    
    def __init__(self):
        self.auth_url = "http://localhost:8081"
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000/ws"
        self.access_token: Optional[str] = None
        self.user_data: Optional[Dict[str, Any]] = None
        
    async def test_auth_service_health(self) -> Dict[str, Any]:
        """Test auth service health endpoint"""
        print("🔍 Testing Auth Service Health...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.auth_url}/health", timeout=10.0)
                result = {
                    "status": "success" if response.status_code == 200 else "failed",
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else response.text
                }
                print(f"✅ Auth service health: {result['status']}")
                return result
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            print(f"❌ Auth service health failed: {e}")
            return result

    async def test_dev_login(self) -> Dict[str, Any]:
        """Test development login flow"""
        print("🔐 Testing Dev Login...")
        try:
            async with httpx.AsyncClient() as client:
                login_data = {"email": "dev@test.com"}
                response = await client.post(
                    f"{self.auth_url}/auth/dev/login",
                    json=login_data,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    self.user_data = data.get("user")
                    
                    # Decode JWT token to inspect contents
                    token_payload = None
                    if self.access_token:
                        try:
                            # Decode without verification for inspection (dev mode)
                            token_payload = jwt.decode(self.access_token, options={"verify_signature": False})
                        except Exception as decode_err:
                            print(f"⚠️ JWT decode warning: {decode_err}")
                    
                    result = {
                        "status": "success",
                        "access_token": self.access_token[:20] + "..." if self.access_token else None,
                        "user": self.user_data,
                        "token_payload": token_payload,
                        "expires_in": data.get("expires_in")
                    }
                    print(f"✅ Dev login successful for user: {self.user_data.get('email')}")
                    return result
                else:
                    result = {
                        "status": "failed",
                        "status_code": response.status_code,
                        "error": response.text
                    }
                    print(f"❌ Dev login failed: {response.status_code}")
                    return result
                    
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            print(f"❌ Dev login error: {e}")
            return result

    async def test_backend_health(self) -> Dict[str, Any]:
        """Test backend service health"""
        print("🔍 Testing Backend Health...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.backend_url}/health/", timeout=10.0)
                result = {
                    "status": "success" if response.status_code == 200 else "failed",
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else response.text
                }
                print(f"✅ Backend health: {result['status']}")
                return result
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            print(f"❌ Backend health failed: {e}")
            return result

    async def test_websocket_connection(self) -> Dict[str, Any]:
        """Test WebSocket connection with authentication"""
        print("🌐 Testing WebSocket Connection...")
        
        if not self.access_token:
            return {"status": "failed", "error": "No access token available"}
            
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            async with websockets.connect(
                self.websocket_url,
                extra_headers=headers,
                timeout=10
            ) as websocket:
                print("✅ WebSocket connection established")
                
                # Test ping/pong
                await websocket.ping()
                print("✅ WebSocket ping successful")
                
                # Wait a moment to see if we get any initial messages
                try:
                    welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f"📨 Welcome message: {welcome_msg}")
                except asyncio.TimeoutError:
                    print("ℹ️ No welcome message received (normal)")
                
                return {
                    "status": "success",
                    "connection_established": True,
                    "ping_successful": True
                }
                
        except ConnectionClosedError as e:
            result = {"status": "failed", "error": f"Connection closed: {e}"}
            print(f"❌ WebSocket connection closed: {e}")
            return result
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            print(f"❌ WebSocket connection error: {e}")
            return result

    async def test_chat_functionality(self) -> Dict[str, Any]:
        """Test chat functionality through WebSocket"""
        print("💬 Testing Chat Functionality...")
        
        if not self.access_token:
            return {"status": "failed", "error": "No access token available"}
            
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            async with websockets.connect(
                self.websocket_url,
                extra_headers=headers,
                timeout=10
            ) as websocket:
                
                # Send a test message
                test_message = {
                    "type": "message",
                    "content": "Hello, this is an E2E test message",
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(test_message))
                print("✅ Test message sent")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    print(f"📨 Response received: {response_data.get('type', 'unknown')}")
                    
                    return {
                        "status": "success",
                        "message_sent": True,
                        "response_received": True,
                        "response_type": response_data.get("type"),
                        "response_data": response_data
                    }
                except asyncio.TimeoutError:
                    return {
                        "status": "partial",
                        "message_sent": True,
                        "response_received": False,
                        "error": "No response received within timeout"
                    }
                    
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            print(f"❌ Chat functionality error: {e}")
            return result

    async def test_frontend_accessibility(self) -> Dict[str, Any]:
        """Test frontend accessibility"""
        print("🖥️ Testing Frontend Accessibility...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:3000", timeout=10.0)
                result = {
                    "status": "success" if response.status_code == 200 else "failed",
                    "status_code": response.status_code,
                    "accessible": response.status_code == 200,
                    "content_length": len(response.content) if response.status_code == 200 else 0
                }
                print(f"✅ Frontend accessible: {result['accessible']}")
                return result
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            print(f"❌ Frontend accessibility error: {e}")
            return result

    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run comprehensive end-to-end test suite"""
        print("Starting Comprehensive E2E Test Suite")
        print("=" * 50)
        
        results = {
            "test_timestamp": time.time(),
            "overall_status": "unknown",
            "tests": {}
        }
        
        # Test sequence
        test_sequence = [
            ("auth_health", self.test_auth_service_health),
            ("dev_login", self.test_dev_login),
            ("backend_health", self.test_backend_health),
            ("websocket_connection", self.test_websocket_connection),
            ("chat_functionality", self.test_chat_functionality),
            ("frontend_accessibility", self.test_frontend_accessibility)
        ]
        
        successful_tests = 0
        failed_tests = 0
        
        for test_name, test_method in test_sequence:
            print(f"\n{'='*20} {test_name.upper()} {'='*20}")
            try:
                test_result = await test_method()
                results["tests"][test_name] = test_result
                
                if test_result["status"] == "success":
                    successful_tests += 1
                else:
                    failed_tests += 1
                    
            except Exception as e:
                print(f"❌ Test {test_name} crashed: {e}")
                results["tests"][test_name] = {"status": "crashed", "error": str(e)}
                failed_tests += 1
        
        # Overall assessment
        total_tests = successful_tests + failed_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        results.update({
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "overall_status": "success" if failed_tests == 0 else "partial" if successful_tests > 0 else "failed"
        })
        
        return results


async def main():
    """Main test runner"""
    tester = E2EWebSocketTester()
    results = await tester.run_full_test_suite()
    
    # Print final report
    print("\n" + "="*60)
    print("🏁 FINAL E2E TEST REPORT")
    print("="*60)
    
    print(f"Overall Status: {results['overall_status'].upper()}")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    print(f"Tests Passed: {results['successful_tests']}/{results['total_tests']}")
    
    print("\nDetailed Results:")
    for test_name, test_result in results["tests"].items():
        status_emoji = "✅" if test_result["status"] == "success" else "❌" if test_result["status"] == "failed" else "⚠️"
        print(f"  {status_emoji} {test_name}: {test_result['status']}")
        if test_result.get("error"):
            print(f"    Error: {test_result['error']}")
    
    # Return appropriate exit code
    return 0 if results["overall_status"] == "success" else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)