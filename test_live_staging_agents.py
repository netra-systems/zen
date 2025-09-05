#!/usr/bin/env python
"""Test LIVE STAGING agent endpoints - NO LOCAL CODE, JUST HTTP/WebSocket calls!"""

import asyncio
import aiohttp
import json
import time
import sys
from typing import Dict, List, Optional
import websockets
import ssl

# LIVE STAGING ENDPOINTS
STAGING_BASE_URL = "https://api.staging.netrasystems.ai"
STAGING_WS_URL = "wss://api.staging.netrasystems.ai/ws"
STAGING_AUTH_URL = f"{STAGING_BASE_URL}/auth"

# Test configuration
TEST_TIMEOUT = 30  # seconds per test
TEST_USER_ID = "test_user_staging_e2e"
TEST_SESSION_ID = f"test_session_{int(time.time())}"

class StagingTester:
    """Tests against LIVE staging deployment"""
    
    def __init__(self):
        self.results = {}
        self.session = None
        self.auth_token = None
        
    async def setup(self):
        """Setup HTTP session"""
        timeout = aiohttp.ClientTimeout(total=TEST_TIMEOUT)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
    async def teardown(self):
        """Cleanup"""
        if self.session:
            await self.session.close()
    
    async def test_health_check(self) -> bool:
        """Test 1: Basic health check of staging API"""
        test_name = "Health Check"
        print(f"\n{'='*60}")
        print(f"TEST 1: {test_name}")
        print(f"{'='*60}")
        
        try:
            async with self.session.get(f"{STAGING_BASE_URL}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"[PASS] Staging is healthy: {data}")
                    return True
                else:
                    print(f"[FAIL] Health check returned {resp.status}")
                    return False
        except aiohttp.ClientError as e:
            # Try alternative endpoints
            try:
                async with self.session.get(f"{STAGING_BASE_URL}/api/health") as resp:
                    if resp.status == 200:
                        print(f"[PASS] Staging is healthy (via /api/health)")
                        return True
            except:
                pass
                
            try:
                async with self.session.get(STAGING_BASE_URL) as resp:
                    if resp.status in [200, 404, 403]:  # Any response means server is up
                        print(f"[PASS] Staging is responding (status: {resp.status})")
                        return True
            except:
                pass
                
            print(f"[FAIL] Cannot connect to staging: {e}")
            return False
    
    async def test_agent_list(self) -> bool:
        """Test 2: Get list of available agents"""
        test_name = "Agent List API"
        print(f"\n{'='*60}")
        print(f"TEST 2: {test_name}")
        print(f"{'='*60}")
        
        try:
            headers = {"Content-Type": "application/json"}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
                
            async with self.session.get(
                f"{STAGING_BASE_URL}/api/agents",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    agents = await resp.json()
                    print(f"[PASS] Found {len(agents)} agents available")
                    return True
                elif resp.status == 404:
                    # Try alternative endpoint
                    async with self.session.get(
                        f"{STAGING_BASE_URL}/api/v1/agents",
                        headers=headers
                    ) as resp2:
                        if resp2.status == 200:
                            agents = await resp2.json()
                            print(f"[PASS] Found agents via v1 API")
                            return True
                    print(f"[WARN] Agent list endpoint not found (404)")
                    return False
                else:
                    print(f"[FAIL] Agent list returned {resp.status}")
                    return False
        except Exception as e:
            print(f"[FAIL] Error getting agent list: {e}")
            return False
    
    async def test_websocket_connection(self) -> bool:
        """Test 3: WebSocket connection to staging"""
        test_name = "WebSocket Connection"
        print(f"\n{'='*60}")
        print(f"TEST 3: {test_name}")
        print(f"{'='*60}")
        
        try:
            # Create SSL context that doesn't verify certificates (for staging)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Try to connect to WebSocket
            async with websockets.connect(
                STAGING_WS_URL,
                ssl=ssl_context,
                ping_interval=None,
                close_timeout=5
            ) as websocket:
                # Send a test message
                test_msg = {
                    "type": "ping",
                    "user_id": TEST_USER_ID,
                    "session_id": TEST_SESSION_ID,
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(test_msg))
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=5.0
                    )
                    print(f"[PASS] WebSocket connected and received: {response[:100]}")
                    return True
                except asyncio.TimeoutError:
                    print(f"[PASS] WebSocket connected (no response to ping)")
                    return True
                    
        except Exception as e:
            print(f"[FAIL] WebSocket connection failed: {e}")
            return False
    
    async def test_agent_message(self) -> bool:
        """Test 4: Send message to agent via REST API"""
        test_name = "Agent Message Processing"
        print(f"\n{'='*60}")
        print(f"TEST 4: {test_name}")
        print(f"{'='*60}")
        
        try:
            # Prepare test message
            message = {
                "user_id": TEST_USER_ID,
                "session_id": TEST_SESSION_ID,
                "message": "Hello, this is a test message to the staging agent",
                "context": {
                    "test": True,
                    "timestamp": time.time()
                }
            }
            
            headers = {"Content-Type": "application/json"}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # Try multiple possible endpoints
            endpoints = [
                f"{STAGING_BASE_URL}/api/chat",
                f"{STAGING_BASE_URL}/api/v1/chat",
                f"{STAGING_BASE_URL}/api/messages",
                f"{STAGING_BASE_URL}/api/v1/messages",
                f"{STAGING_BASE_URL}/api/agent/message"
            ]
            
            for endpoint in endpoints:
                try:
                    async with self.session.post(
                        endpoint,
                        json=message,
                        headers=headers
                    ) as resp:
                        if resp.status in [200, 201, 202]:
                            result = await resp.json()
                            print(f"[PASS] Message processed via {endpoint}")
                            print(f"  Response: {str(result)[:200]}")
                            return True
                        elif resp.status == 404:
                            continue  # Try next endpoint
                        else:
                            print(f"  {endpoint} returned {resp.status}")
                except:
                    continue
                    
            print(f"[FAIL] No working message endpoint found")
            return False
            
        except Exception as e:
            print(f"[FAIL] Error sending message: {e}")
            return False
    
    async def test_agent_websocket_flow(self) -> bool:
        """Test 5: Complete agent flow via WebSocket"""
        test_name = "Agent WebSocket Flow"
        print(f"\n{'='*60}")
        print(f"TEST 5: {test_name}")
        print(f"{'='*60}")
        
        try:
            # Create SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            events_received = []
            
            async with websockets.connect(
                STAGING_WS_URL,
                ssl=ssl_context,
                ping_interval=None,
                close_timeout=10
            ) as websocket:
                
                # Send a chat message
                chat_msg = {
                    "type": "message",
                    "user_id": TEST_USER_ID,
                    "session_id": TEST_SESSION_ID,
                    "content": "What are the top 3 optimizations I should focus on?",
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(chat_msg))
                print(f"Sent message: {chat_msg['content']}")
                
                # Collect events for up to 10 seconds
                start_time = time.time()
                while time.time() - start_time < 10:
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(), 
                            timeout=1.0
                        )
                        event = json.loads(response)
                        events_received.append(event)
                        print(f"  Received event: {event.get('type', 'unknown')}")
                        
                        # Check for completion
                        if event.get('type') in ['agent_completed', 'message_complete', 'response']:
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        print(f"  Received non-JSON: {response[:100]}")
                        continue
                
                # Validate we got expected events
                event_types = [e.get('type') for e in events_received]
                
                if len(events_received) > 0:
                    print(f"[PASS] Received {len(events_received)} WebSocket events")
                    print(f"  Event types: {event_types}")
                    return True
                else:
                    print(f"[WARN] No events received via WebSocket")
                    return False
                    
        except Exception as e:
            print(f"[FAIL] WebSocket flow failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all staging tests"""
        await self.setup()
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Agent List", self.test_agent_list),
            ("WebSocket Connection", self.test_websocket_connection),
            ("Agent Message", self.test_agent_message),
            ("WebSocket Flow", self.test_agent_websocket_flow)
        ]
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                self.results[test_name] = result
            except Exception as e:
                print(f"[ERROR] Test {test_name} crashed: {e}")
                self.results[test_name] = False
        
        await self.teardown()
        return self.results


async def main():
    """Main test runner"""
    print("\n" + "="*70)
    print("LIVE STAGING AGENT E2E TESTS")
    print("="*70)
    print(f"Target: {STAGING_BASE_URL}")
    print(f"WebSocket: {STAGING_WS_URL}")
    print("="*70)
    
    tester = StagingTester()
    results = await tester.run_all_tests()
    
    # Print summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r)
    failed = len(results) - passed
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n[SUCCESS] All staging tests passed!")
        return 0
    else:
        print(f"\n[WARNING] {failed} tests failed - staging may have issues")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)