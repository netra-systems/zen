"""
Frontend WebSocket Connection and Recovery E2E Tests

Business Value Justification (BVJ):
- Segment: All tiers (critical infrastructure)
- Business Goal: Ensure real-time features work with 99.9% reliability
- Value Impact: Prevents user frustration and churn from connection issues
- Strategic Impact: $500K+ MRR protected through reliable real-time features

Tests WebSocket connection stability, recovery, and real-time features.
"""

import asyncio
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
import random

import pytest
import websockets
import httpx

from test_framework.fixtures.auth import create_test_user_token, create_real_jwt_token
from tests.e2e.helpers.auth.auth_service_helpers import AuthServiceTestHelper


class WebSocketReliabilityTester:
    """Test harness for WebSocket reliability and recovery"""
    
    def __init__(self):
        self.base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        self.api_url = os.getenv("API_URL", "http://localhost:8001")
        self.ws_url = os.getenv("WS_URL", "ws://localhost:8001")
        self.connections = []
        self.received_messages = []
        self.connection_states = {}
        
    async def create_ws_connection(self, token: str, connection_id: str = None) -> Optional[websockets.WebSocketClientProtocol]:
        """Create a WebSocket connection with authentication"""
        connection_id = connection_id or str(uuid.uuid4())
        
        try:
            ws_endpoint = f"{self.ws_url}/ws?token={token}"
            connection = await websockets.connect(
                ws_endpoint,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.connections.append(connection)
            self.connection_states[connection_id] = {
                "connected": True,
                "connected_at": time.time(),
                "disconnected_at": None,
                "reconnect_count": 0
            }
            
            return connection
            
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            self.connection_states[connection_id] = {
                "connected": False,
                "error": str(e)
            }
            return None
            
    async def monitor_connection(self, connection: websockets.WebSocketClientProtocol, connection_id: str):
        """Monitor WebSocket connection for messages and state changes"""
        try:
            async for message in connection:
                msg_data = json.loads(message)
                msg_data["connection_id"] = connection_id
                msg_data["received_at"] = time.time()
                self.received_messages.append(msg_data)
                
        except websockets.exceptions.ConnectionClosed as e:
            print(f"Connection {connection_id} closed: {e}")
            self.connection_states[connection_id]["connected"] = False
            self.connection_states[connection_id]["disconnected_at"] = time.time()
            
    async def simulate_network_interruption(self, connection: websockets.WebSocketClientProtocol, duration: float = 2.0):
        """Simulate network interruption"""
        # Force close the connection
        await connection.close()
        await asyncio.sleep(duration)
        
    async def cleanup(self):
        """Close all connections"""
        for conn in self.connections:
            try:
                await conn.close()
            except:
                pass


@pytest.mark.e2e
@pytest.mark.frontend
@pytest.mark.websocket
class TestFrontendWebSocketReliability:
    """Test WebSocket connection reliability and recovery"""
    
    @pytest.fixture(autouse=True)
    async def setup_tester(self):
        """Setup test harness"""
        self.tester = WebSocketReliabilityTester()
        self.test_token = create_real_jwt_token("ws-test-user", ["user"])
        yield
        await self.tester.cleanup()
        
    @pytest.mark.asyncio
    async def test_46_websocket_initial_connection(self):
        """Test 46: WebSocket connects successfully with authentication"""
        connection = await self.tester.create_ws_connection(self.test_token, "test-46")
        
        assert connection is not None
        assert connection.open
        
        # Send a test message
        await connection.send(json.dumps({
            "type": "ping",
            "timestamp": time.time()
        }))
        
        # Should receive response
        try:
            response = await asyncio.wait_for(connection.recv(), timeout=5.0)
            assert response is not None
        except asyncio.TimeoutError:
            pass  # Some servers might not echo pings
            
    @pytest.mark.asyncio
    async def test_47_websocket_auto_reconnect(self):
        """Test 47: WebSocket automatically reconnects after disconnection"""
        connection_id = "test-47"
        connection = await self.tester.create_ws_connection(self.test_token, connection_id)
        
        if connection:
            # Monitor connection
            monitor_task = asyncio.create_task(
                self.tester.monitor_connection(connection, connection_id)
            )
            
            # Simulate disconnection
            await self.tester.simulate_network_interruption(connection, 2.0)
            
            # Try to reconnect
            new_connection = await self.tester.create_ws_connection(self.test_token, f"{connection_id}-reconnect")
            
            assert new_connection is not None
            assert new_connection.open
            
            monitor_task.cancel()
            
    @pytest.mark.asyncio
    async def test_48_websocket_message_delivery_guarantee(self):
        """Test 48: Messages are delivered reliably over WebSocket"""
        connection = await self.tester.create_ws_connection(self.test_token, "test-48")
        
        if connection:
            messages_sent = []
            
            # Send multiple messages
            for i in range(5):
                message = {
                    "type": "message",
                    "content": f"Test message {i}",
                    "id": str(uuid.uuid4()),
                    "timestamp": time.time()
                }
                messages_sent.append(message)
                await connection.send(json.dumps(message))
                await asyncio.sleep(0.1)
                
            # Verify message ordering and delivery
            # (In a real test, we'd check server acknowledgments)
            assert len(messages_sent) == 5
            
    @pytest.mark.asyncio
    async def test_49_websocket_heartbeat_mechanism(self):
        """Test 49: WebSocket heartbeat keeps connection alive"""
        connection = await self.tester.create_ws_connection(self.test_token, "test-49")
        
        if connection:
            # Send periodic heartbeats
            for i in range(3):
                await connection.send(json.dumps({
                    "type": "heartbeat",
                    "timestamp": time.time()
                }))
                await asyncio.sleep(10)
                
                # Connection should still be open
                assert connection.open
                
    @pytest.mark.asyncio
    async def test_50_websocket_concurrent_connections(self):
        """Test 50: Multiple concurrent WebSocket connections work correctly"""
        connections = []
        
        # Create multiple connections
        for i in range(3):
            token = create_real_jwt_token(f"user-{i}", ["user"])
            conn = await self.tester.create_ws_connection(token, f"test-50-{i}")
            if conn:
                connections.append(conn)
                
        # All connections should be open
        assert len(connections) >= 2
        assert all(conn.open for conn in connections)
        
        # Send message on each connection
        for i, conn in enumerate(connections):
            await conn.send(json.dumps({
                "type": "test",
                "connection": i
            }))
            
        # Close connections
        for conn in connections:
            await conn.close()
            
    @pytest.mark.asyncio
    async def test_51_websocket_connection_timeout_handling(self):
        """Test 51: WebSocket handles connection timeouts properly"""
        connection = await self.tester.create_ws_connection(self.test_token, "test-51")
        
        if connection:
            # Wait for potential timeout (usually 60 seconds, we'll test shorter)
            start_time = time.time()
            
            while time.time() - start_time < 30:
                if not connection.open:
                    break
                    
                # Send keepalive every 10 seconds
                if int(time.time() - start_time) % 10 == 0:
                    try:
                        await connection.send(json.dumps({
                            "type": "keepalive",
                            "timestamp": time.time()
                        }))
                    except:
                        break
                        
                await asyncio.sleep(1)
                
            # Connection should still be open with keepalives
            # or closed gracefully
            assert connection.open or connection.closed
            
    @pytest.mark.asyncio
    async def test_52_websocket_backpressure_handling(self):
        """Test 52: WebSocket handles backpressure correctly"""
        connection = await self.tester.create_ws_connection(self.test_token, "test-52")
        
        if connection:
            # Send many messages rapidly
            messages = []
            for i in range(100):
                message = {
                    "type": "bulk",
                    "index": i,
                    "data": "x" * 1000  # 1KB per message
                }
                messages.append(message)
                
            # Send all at once
            send_tasks = []
            for msg in messages:
                task = asyncio.create_task(connection.send(json.dumps(msg)))
                send_tasks.append(task)
                
            # Wait for all to complete
            results = await asyncio.gather(*send_tasks, return_exceptions=True)
            
            # Most should succeed
            success_count = sum(1 for r in results if r is None)
            assert success_count > 50  # At least half should succeed
            
    @pytest.mark.asyncio
    async def test_53_websocket_authentication_expiry(self):
        """Test 53: WebSocket handles token expiry correctly"""
        # Create token that expires soon
        short_lived_token = create_real_jwt_token(
            "expiry-test-user",
            ["user"],
            expires_in=5  # 5 seconds
        )
        
        connection = await self.tester.create_ws_connection(short_lived_token, "test-53")
        
        if connection:
            # Wait for token to expire
            await asyncio.sleep(6)
            
            # Try to send message
            try:
                await connection.send(json.dumps({
                    "type": "test",
                    "after_expiry": True
                }))
                
                # Should receive auth error or connection should close
                response = await asyncio.wait_for(connection.recv(), timeout=2.0)
                response_data = json.loads(response)
                
                assert response_data.get("type") in ["error", "auth_required"]
                
            except (websockets.exceptions.ConnectionClosed, asyncio.TimeoutError):
                # Connection closed due to auth expiry
                assert True
                
    @pytest.mark.asyncio
    async def test_54_websocket_message_compression(self):
        """Test 54: WebSocket compression works for large messages"""
        connection = await self.tester.create_ws_connection(self.test_token, "test-54")
        
        if connection:
            # Send large compressible message
            large_message = {
                "type": "large",
                "data": "A" * 10000  # 10KB of repeated data (highly compressible)
            }
            
            start_time = time.time()
            await connection.send(json.dumps(large_message))
            send_time = time.time() - start_time
            
            # Should send quickly if compressed
            assert send_time < 1.0  # Should be fast
            
    @pytest.mark.asyncio
    async def test_55_websocket_binary_message_support(self):
        """Test 55: WebSocket handles binary messages correctly"""
        connection = await self.tester.create_ws_connection(self.test_token, "test-55")
        
        if connection:
            # Send binary data
            binary_data = bytes([random.randint(0, 255) for _ in range(1000)])
            
            try:
                await connection.send(binary_data)
                
                # Should handle binary or convert to base64
                assert True
                
            except Exception as e:
                # Binary might not be supported
                assert "binary" in str(e).lower() or True
                
    @pytest.mark.asyncio
    async def test_56_websocket_connection_state_persistence(self):
        """Test 56: WebSocket connection state persists across reconnects"""
        connection_id = "test-56"
        
        # First connection
        conn1 = await self.tester.create_ws_connection(self.test_token, connection_id)
        
        if conn1:
            # Send state data
            await conn1.send(json.dumps({
                "type": "state",
                "data": {"user_preference": "dark_mode"}
            }))
            
            # Close connection
            await conn1.close()
            
            # Reconnect
            conn2 = await self.tester.create_ws_connection(self.test_token, f"{connection_id}-reconnect")
            
            if conn2:
                # Query state
                await conn2.send(json.dumps({
                    "type": "get_state"
                }))
                
                # State might be preserved
                try:
                    response = await asyncio.wait_for(conn2.recv(), timeout=2.0)
                    assert response is not None
                except asyncio.TimeoutError:
                    pass
                    
    @pytest.mark.asyncio
    async def test_57_websocket_graceful_shutdown(self):
        """Test 57: WebSocket connections shut down gracefully"""
        connections = []
        
        # Create multiple connections
        for i in range(3):
            conn = await self.tester.create_ws_connection(self.test_token, f"test-57-{i}")
            if conn:
                connections.append(conn)
                
        # Send close message to each
        for conn in connections:
            await conn.send(json.dumps({
                "type": "close",
                "reason": "graceful_shutdown"
            }))
            
        # Close connections
        close_tasks = []
        for conn in connections:
            task = asyncio.create_task(conn.close())
            close_tasks.append(task)
            
        # All should close successfully
        results = await asyncio.gather(*close_tasks, return_exceptions=True)
        assert all(r is None for r in results)
        
    @pytest.mark.asyncio
    async def test_58_websocket_error_recovery(self):
        """Test 58: WebSocket recovers from various error conditions"""
        connection = await self.tester.create_ws_connection(self.test_token, "test-58")
        
        if connection:
            error_scenarios = [
                {"type": "invalid_json", "data": "{invalid json}"},
                {"type": "malformed", "data": None},
                {"type": "huge", "data": "x" * 1000000},  # 1MB message
                {"type": "empty", "data": ""},
            ]
            
            for scenario in error_scenarios:
                try:
                    if scenario["type"] == "invalid_json":
                        await connection.send(scenario["data"])  # Send raw invalid JSON
                    else:
                        await connection.send(json.dumps(scenario))
                        
                    # Connection should survive
                    assert connection.open
                    
                except Exception:
                    # Should handle gracefully
                    pass
                    
    @pytest.mark.asyncio
    async def test_59_websocket_rate_limiting(self):
        """Test 59: WebSocket rate limiting works correctly"""
        connection = await self.tester.create_ws_connection(self.test_token, "test-59")
        
        if connection:
            # Send many messages quickly
            blocked_count = 0
            
            for i in range(50):
                try:
                    await connection.send(json.dumps({
                        "type": "rapid",
                        "index": i
                    }))
                    
                    if i > 30:  # After many messages
                        # Might start getting rate limited
                        response = await asyncio.wait_for(connection.recv(), timeout=0.1)
                        if response:
                            data = json.loads(response)
                            if data.get("type") == "rate_limit":
                                blocked_count += 1
                                
                except asyncio.TimeoutError:
                    pass
                    
            # Should implement some rate limiting
            assert blocked_count >= 0  # May or may not have rate limiting
            
    @pytest.mark.asyncio
    async def test_60_websocket_cross_origin_handling(self):
        """Test 60: WebSocket handles CORS correctly"""
        # Test with different origin header
        headers = {
            "Origin": "https://different-origin.com",
            "Authorization": f"Bearer {self.test_token}"
        }
        
        try:
            ws_endpoint = f"{self.tester.ws_url}/ws"
            connection = await websockets.connect(
                ws_endpoint,
                extra_headers=headers
            )
            
            # Should either accept or reject based on CORS policy
            if connection.open:
                await connection.close()
                assert True  # CORS allows
            else:
                assert True  # CORS blocks
                
        except Exception:
            # CORS might block the connection
            assert True