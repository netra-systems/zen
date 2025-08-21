#!/usr/bin/env python3
"""
Comprehensive test to verify WebSocket reconnection and recovery:
1. Initial WebSocket connection establishment
2. Connection disruption simulation
3. Automatic reconnection with backoff
4. State recovery after reconnection
5. Message queue preservation during disconnect
6. Subscription restoration
7. Heartbeat mechanism validation

This test ensures WebSocket connections are resilient and recover gracefully.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import aiohttp
import websockets
import pytest
from datetime import datetime
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configuration
DEV_BACKEND_URL = "http://localhost:8000"
DEV_WEBSOCKET_URL = "ws://localhost:8000/websocket"
AUTH_SERVICE_URL = "http://localhost:8081"

# Test credentials
TEST_USER_EMAIL = "ws_test@example.com"
TEST_USER_PASSWORD = "wstest123"


class WebSocketReconnectionTester:
    """Test WebSocket reconnection and recovery flow."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.ws_connection = None
        self.connection_id: Optional[str] = None
        self.subscriptions: List[str] = []
        self.sent_messages: List[Dict] = []
        self.received_messages: List[Dict] = []
        self.disconnection_count = 0
        self.reconnection_count = 0
        self.last_heartbeat: Optional[datetime] = None
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        if self.ws_connection:
            await self.ws_connection.close()
        if self.session:
            await self.session.close()
            
    async def setup_authentication(self) -> bool:
        """Setup user authentication."""
        print("\n[AUTH] STEP 1: Setting up authentication...")
        
        try:
            # Register user
            register_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "name": "WebSocket Test User"
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/register",
                json=register_data
            ) as response:
                if response.status not in [200, 201, 409]:
                    print(f"[ERROR] Registration failed: {response.status}")
                    return False
                    
            # Login
            login_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/login",
                json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    print(f"[OK] Authentication successful")
                    return True
                else:
                    print(f"[ERROR] Login failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Authentication error: {e}")
            return False
            
    async def test_initial_connection(self) -> bool:
        """Test initial WebSocket connection."""
        print("\n[CONNECT] STEP 2: Establishing initial WebSocket connection...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            # Connect with auth token
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            self.ws_connection = await websockets.connect(
                DEV_WEBSOCKET_URL,
                extra_headers=headers,
                ping_interval=10,
                ping_timeout=5
            )
            
            # Send auth message
            auth_message = {
                "type": "auth",
                "token": self.auth_token
            }
            await self.ws_connection.send(json.dumps(auth_message))
            
            # Wait for auth response
            response = await asyncio.wait_for(
                self.ws_connection.recv(),
                timeout=5.0
            )
            
            data = json.loads(response)
            if data.get("type") == "auth_success":
                self.connection_id = data.get("connection_id")
                print(f"[OK] WebSocket connected: {self.connection_id}")
                return True
            else:
                print(f"[ERROR] WebSocket auth failed: {data}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Connection error: {e}")
            return False
            
    async def test_subscription_setup(self) -> bool:
        """Setup WebSocket subscriptions."""
        print("\n[SUBSCRIBE] STEP 3: Setting up subscriptions...")
        
        if not self.ws_connection:
            print("[ERROR] No WebSocket connection")
            return False
            
        try:
            # Subscribe to multiple channels
            channels = [
                "user_updates",
                "system_events",
                f"private_{self.connection_id}"
            ]
            
            for channel in channels:
                subscribe_message = {
                    "type": "subscribe",
                    "channel": channel,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.ws_connection.send(json.dumps(subscribe_message))
                self.subscriptions.append(channel)
                
                # Wait for subscription confirmation
                response = await asyncio.wait_for(
                    self.ws_connection.recv(),
                    timeout=5.0
                )
                
                data = json.loads(response)
                if data.get("type") == "subscribed":
                    print(f"[OK] Subscribed to {channel}")
                else:
                    print(f"[ERROR] Subscription failed for {channel}")
                    return False
                    
            print(f"[OK] All {len(self.subscriptions)} subscriptions active")
            return True
            
        except Exception as e:
            print(f"[ERROR] Subscription error: {e}")
            return False
            
    async def test_heartbeat_mechanism(self) -> bool:
        """Test WebSocket heartbeat mechanism."""
        print("\n[HEARTBEAT] STEP 4: Testing heartbeat mechanism...")
        
        if not self.ws_connection:
            print("[ERROR] No WebSocket connection")
            return False
            
        try:
            heartbeat_count = 0
            start_time = time.time()
            
            # Send and receive heartbeats for 10 seconds
            while time.time() - start_time < 10:
                # Send heartbeat
                heartbeat_message = {
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.ws_connection.send(json.dumps(heartbeat_message))
                
                # Wait for heartbeat response
                try:
                    response = await asyncio.wait_for(
                        self.ws_connection.recv(),
                        timeout=2.0
                    )
                    
                    data = json.loads(response)
                    if data.get("type") == "heartbeat_ack":
                        heartbeat_count += 1
                        self.last_heartbeat = datetime.utcnow()
                        
                except asyncio.TimeoutError:
                    pass  # Some heartbeats might not get immediate response
                    
                await asyncio.sleep(2)  # Send heartbeat every 2 seconds
                
            if heartbeat_count > 0:
                print(f"[OK] Heartbeat mechanism working: {heartbeat_count} heartbeats")
                return True
            else:
                print("[ERROR] No heartbeat responses received")
                return False
                
        except Exception as e:
            print(f"[ERROR] Heartbeat error: {e}")
            return False
            
    async def test_message_queue_before_disconnect(self) -> bool:
        """Send messages before simulating disconnect."""
        print("\n[QUEUE] STEP 5: Sending messages before disconnect...")
        
        if not self.ws_connection:
            print("[ERROR] No WebSocket connection")
            return False
            
        try:
            # Send multiple messages
            for i in range(5):
                message = {
                    "type": "user_message",
                    "content": f"Message {i} before disconnect",
                    "message_id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.ws_connection.send(json.dumps(message))
                self.sent_messages.append(message)
                print(f"[SEND] Message {i} sent")
                
            print(f"[OK] {len(self.sent_messages)} messages queued")
            return True
            
        except Exception as e:
            print(f"[ERROR] Message queue error: {e}")
            return False
            
    async def test_connection_disruption(self) -> bool:
        """Simulate connection disruption."""
        print("\n[DISRUPT] STEP 6: Simulating connection disruption...")
        
        if not self.ws_connection:
            print("[ERROR] No WebSocket connection to disrupt")
            return False
            
        try:
            # Store connection state
            old_connection_id = self.connection_id
            
            # Force close the connection
            await self.ws_connection.close()
            self.disconnection_count += 1
            print(f"[OK] Connection forcefully closed")
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Verify connection is closed
            if self.ws_connection.closed:
                print(f"[OK] Connection disrupted successfully")
                return True
            else:
                print("[ERROR] Connection still active")
                return False
                
        except Exception as e:
            print(f"[ERROR] Disruption error: {e}")
            return False
            
    async def test_automatic_reconnection(self) -> bool:
        """Test automatic reconnection with exponential backoff."""
        print("\n[RECONNECT] STEP 7: Testing automatic reconnection...")
        
        if not self.auth_token:
            print("[ERROR] No auth token for reconnection")
            return False
            
        max_retries = 5
        retry_count = 0
        backoff_time = 1
        
        while retry_count < max_retries:
            try:
                print(f"[RETRY] Attempt {retry_count + 1}/{max_retries} after {backoff_time}s...")
                await asyncio.sleep(backoff_time)
                
                # Try to reconnect
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                
                self.ws_connection = await websockets.connect(
                    DEV_WEBSOCKET_URL,
                    extra_headers=headers,
                    ping_interval=10,
                    ping_timeout=5
                )
                
                # Re-authenticate
                auth_message = {
                    "type": "auth",
                    "token": self.auth_token,
                    "reconnect": True,
                    "previous_connection_id": self.connection_id
                }
                await self.ws_connection.send(json.dumps(auth_message))
                
                # Wait for auth response
                response = await asyncio.wait_for(
                    self.ws_connection.recv(),
                    timeout=5.0
                )
                
                data = json.loads(response)
                if data.get("type") == "auth_success":
                    self.connection_id = data.get("connection_id")
                    self.reconnection_count += 1
                    print(f"[OK] Reconnected successfully: {self.connection_id}")
                    return True
                    
            except Exception as e:
                retry_count += 1
                backoff_time = min(backoff_time * 2, 30)  # Exponential backoff with max 30s
                print(f"[RETRY] Reconnection attempt {retry_count} failed: {e}")
                
        print("[ERROR] Failed to reconnect after max retries")
        return False
        
    async def test_state_recovery(self) -> bool:
        """Test state recovery after reconnection."""
        print("\n[RECOVER] STEP 8: Testing state recovery...")
        
        if not self.ws_connection:
            print("[ERROR] No WebSocket connection")
            return False
            
        try:
            # Request state recovery
            recovery_message = {
                "type": "recover_state",
                "subscriptions": self.subscriptions,
                "last_message_ids": [msg["message_id"] for msg in self.sent_messages[-3:]]
            }
            await self.ws_connection.send(json.dumps(recovery_message))
            
            # Wait for recovery response
            response = await asyncio.wait_for(
                self.ws_connection.recv(),
                timeout=10.0
            )
            
            data = json.loads(response)
            if data.get("type") == "state_recovered":
                recovered_subs = data.get("subscriptions", [])
                missed_messages = data.get("missed_messages", [])
                
                print(f"[OK] State recovered:")
                print(f"  - Subscriptions: {len(recovered_subs)}/{len(self.subscriptions)}")
                print(f"  - Missed messages: {len(missed_messages)}")
                
                # Re-subscribe if needed
                for sub in self.subscriptions:
                    if sub not in recovered_subs:
                        subscribe_message = {
                            "type": "subscribe",
                            "channel": sub
                        }
                        await self.ws_connection.send(json.dumps(subscribe_message))
                        
                return True
            else:
                print(f"[ERROR] State recovery failed: {data}")
                return False
                
        except Exception as e:
            print(f"[ERROR] State recovery error: {e}")
            return False
            
    async def test_message_delivery_after_reconnect(self) -> bool:
        """Test message delivery after reconnection."""
        print("\n[DELIVERY] STEP 9: Testing message delivery after reconnect...")
        
        if not self.ws_connection:
            print("[ERROR] No WebSocket connection")
            return False
            
        try:
            # Send new messages
            post_reconnect_messages = []
            for i in range(3):
                message = {
                    "type": "user_message",
                    "content": f"Message {i} after reconnect",
                    "message_id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.ws_connection.send(json.dumps(message))
                post_reconnect_messages.append(message)
                
            # Receive messages
            received_count = 0
            timeout_count = 0
            
            while timeout_count < 3:
                try:
                    response = await asyncio.wait_for(
                        self.ws_connection.recv(),
                        timeout=2.0
                    )
                    
                    data = json.loads(response)
                    self.received_messages.append(data)
                    received_count += 1
                    print(f"[RECV] Message received: {data.get('type')}")
                    
                except asyncio.TimeoutError:
                    timeout_count += 1
                    
            if received_count > 0:
                print(f"[OK] Received {received_count} messages after reconnect")
                return True
            else:
                print("[ERROR] No messages received after reconnect")
                return False
                
        except Exception as e:
            print(f"[ERROR] Message delivery error: {e}")
            return False
            
    async def test_connection_stability(self) -> bool:
        """Test connection stability over time."""
        print("\n[STABILITY] STEP 10: Testing connection stability...")
        
        if not self.ws_connection:
            print("[ERROR] No WebSocket connection")
            return False
            
        try:
            stability_duration = 15  # Test for 15 seconds
            start_time = time.time()
            ping_count = 0
            error_count = 0
            
            while time.time() - start_time < stability_duration:
                try:
                    # Send ping
                    ping_message = {
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await self.ws_connection.send(json.dumps(ping_message))
                    
                    # Wait for pong
                    response = await asyncio.wait_for(
                        self.ws_connection.recv(),
                        timeout=2.0
                    )
                    
                    data = json.loads(response)
                    if data.get("type") == "pong":
                        ping_count += 1
                        
                except asyncio.TimeoutError:
                    error_count += 1
                    
                await asyncio.sleep(1)
                
            success_rate = ping_count / (ping_count + error_count) if (ping_count + error_count) > 0 else 0
            
            if success_rate > 0.8:  # 80% success rate
                print(f"[OK] Connection stable: {success_rate:.1%} success rate")
                return True
            else:
                print(f"[ERROR] Connection unstable: {success_rate:.1%} success rate")
                return False
                
        except Exception as e:
            print(f"[ERROR] Stability test error: {e}")
            return False
            
    async def test_graceful_disconnect(self) -> bool:
        """Test graceful disconnect."""
        print("\n[DISCONNECT] STEP 11: Testing graceful disconnect...")
        
        if not self.ws_connection:
            print("[ERROR] No WebSocket connection")
            return False
            
        try:
            # Send disconnect message
            disconnect_message = {
                "type": "disconnect",
                "reason": "test_complete",
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.ws_connection.send(json.dumps(disconnect_message))
            
            # Wait for acknowledgment
            try:
                response = await asyncio.wait_for(
                    self.ws_connection.recv(),
                    timeout=5.0
                )
                
                data = json.loads(response)
                if data.get("type") == "disconnect_ack":
                    print(f"[OK] Disconnect acknowledged")
                    
            except asyncio.TimeoutError:
                pass  # Server might close immediately
                
            # Close connection
            await self.ws_connection.close()
            
            if self.ws_connection.closed:
                print(f"[OK] Connection closed gracefully")
                return True
            else:
                print("[ERROR] Connection not properly closed")
                return False
                
        except Exception as e:
            print(f"[ERROR] Disconnect error: {e}")
            return False
            
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests in sequence."""
        results = {}
        
        # Setup
        results["authentication"] = await self.setup_authentication()
        if not results["authentication"]:
            print("\n[CRITICAL] Authentication failed. Aborting tests.")
            return results
            
        # Connection tests
        results["initial_connection"] = await self.test_initial_connection()
        results["subscription_setup"] = await self.test_subscription_setup()
        results["heartbeat_mechanism"] = await self.test_heartbeat_mechanism()
        results["message_queue"] = await self.test_message_queue_before_disconnect()
        
        # Disruption and recovery
        results["connection_disruption"] = await self.test_connection_disruption()
        results["automatic_reconnection"] = await self.test_automatic_reconnection()
        results["state_recovery"] = await self.test_state_recovery()
        results["message_delivery"] = await self.test_message_delivery_after_reconnect()
        
        # Stability
        results["connection_stability"] = await self.test_connection_stability()
        results["graceful_disconnect"] = await self.test_graceful_disconnect()
        
        return results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_websocket_reconnection_flow():
    """Test WebSocket reconnection and recovery flow."""
    async with WebSocketReconnectionTester() as tester:
        results = await tester.run_all_tests()
        
        # Print summary
        print("\n" + "="*60)
        print("WEBSOCKET RECONNECTION TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {test_name:25} : {status}")
            
        print("="*60)
        
        # Print statistics
        print(f"\nConnection Statistics:")
        print(f"  Disconnections: {tester.disconnection_count}")
        print(f"  Reconnections: {tester.reconnection_count}")
        print(f"  Messages sent: {len(tester.sent_messages)}")
        print(f"  Messages received: {len(tester.received_messages)}")
        
        # Calculate overall result
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n[SUCCESS] All WebSocket reconnection tests passed!")
        else:
            print(f"\n[WARNING] {total_tests - passed_tests} tests failed.")
            
        # Assert all tests passed
        assert all(results.values()), f"Some tests failed: {results}"


async def main():
    """Run the test standalone."""
    print("="*60)
    print("WEBSOCKET RECONNECTION FLOW TEST")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with WebSocketReconnectionTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        if all(results.values()):
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)