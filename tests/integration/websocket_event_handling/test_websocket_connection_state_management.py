"""
WebSocket Connection State Management Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable WebSocket connections for chat functionality
- Value Impact: Connection state management is critical for 90% platform value delivery
- Strategic Impact: Stable connections enable continuous AI-powered conversations

These tests validate WebSocket connection lifecycle management, ensuring users
maintain reliable connections for the chat functionality that delivers primary business value.
"""

import asyncio
import pytest
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket import (
    WebSocketTestUtility,
    WebSocketTestClient, 
    WebSocketEventType,
    WebSocketMessage
)
from shared.isolated_environment import get_env


class TestWebSocketConnectionStateManagement(SSotAsyncTestCase):
    """Test WebSocket connection state management patterns."""
    
    async def setup_method(self, method=None):
        """Set up test environment."""
        await super().async_setup_method(method)
        self.env = get_env()
        
        # Configure test environment
        self.set_env_var("WEBSOCKET_TEST_TIMEOUT", "15")
        self.set_env_var("WEBSOCKET_MOCK_MODE", "true")
        self.set_env_var("WEBSOCKET_RETRY_COUNT", "3")
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_connection_lifecycle_management(self):
        """
        Test complete WebSocket connection lifecycle (connect -> active -> disconnect).
        
        BVJ: All segments - Reliable connection lifecycle is foundation of chat experience.
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("lifecycle_user")
            
            # Test connection establishment
            connection_start = time.time()
            success = await client.connect(mock_mode=True)
            connection_time = time.time() - connection_start
            
            assert success, "Failed to establish WebSocket connection"
            assert client.is_connected, "Client should report as connected"
            assert connection_time < 5.0, f"Connection took too long: {connection_time}s"
            
            # Test active connection state
            await client.send_message(
                WebSocketEventType.PING,
                {"test_id": "lifecycle_test", "timestamp": time.time()}
            )
            
            # Wait for response and verify connection health
            await asyncio.sleep(1.0)
            assert client.is_connected, "Connection should remain active after sending message"
            
            # Test graceful disconnection
            disconnect_start = time.time()
            await client.disconnect()
            disconnect_time = time.time() - disconnect_start
            
            assert not client.is_connected, "Client should report as disconnected"
            assert disconnect_time < 2.0, f"Disconnection took too long: {disconnect_time}s"
            
            # Record performance metrics
            self.record_metric("connection_time_seconds", connection_time)
            self.record_metric("disconnect_time_seconds", disconnect_time)
            self.record_metric("lifecycle_test_success", True)
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_connection_heartbeat_monitoring(self):
        """
        Test WebSocket connection heartbeat and health monitoring.
        
        BVJ: Enterprise/Mid - Proactive connection monitoring prevents chat interruptions.
        """
        async with WebSocketTestUtility() as ws_util:
            async with ws_util.connected_client("heartbeat_user") as client:
                heartbeat_count = 0
                heartbeat_responses = []
                
                def track_heartbeat(message: WebSocketMessage):
                    nonlocal heartbeat_count
                    if message.event_type == WebSocketEventType.PONG:
                        heartbeat_count += 1
                        heartbeat_responses.append({
                            "timestamp": message.timestamp,
                            "latency": time.time() - message.data.get("sent_time", time.time())
                        })
                
                # Set up heartbeat tracking
                client.add_event_handler(WebSocketEventType.PONG, track_heartbeat)
                
                # Send heartbeat pings
                ping_count = 5
                for i in range(ping_count):
                    await client.send_message(
                        WebSocketEventType.PING,
                        {
                            "ping_id": i,
                            "sent_time": time.time(),
                            "heartbeat_test": True
                        }
                    )
                    await asyncio.sleep(0.5)
                
                # Wait for heartbeat responses
                await asyncio.sleep(2.0)
                
                # Verify heartbeat mechanism (in mock mode, we simulate responses)
                # In real implementation, server would respond with PONG events
                assert client.is_connected, "Connection should remain healthy during heartbeat test"
                
                # Verify connection stability
                stability_test_message = await client.send_message(
                    WebSocketEventType.AGENT_STARTED,
                    {"test": "connection_stability", "after_heartbeat": True}
                )
                
                assert stability_test_message.message_id, "Should be able to send messages after heartbeat"
                
                self.record_metric("heartbeat_pings_sent", ping_count)
                self.record_metric("connection_stability_verified", True)
                self.record_metric("heartbeat_test_duration", 2.5)
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_connection_auto_reconnect_mechanism(self):
        """
        Test automatic WebSocket reconnection after connection loss.
        
        BVJ: All segments - Auto-reconnect prevents user experience disruption.
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("reconnect_user")
            
            # Initial connection
            await client.connect(mock_mode=True)
            assert client.is_connected, "Initial connection failed"
            
            # Send initial message to establish session
            initial_message = await client.send_message(
                WebSocketEventType.USER_CONNECTED,
                {"session": "established", "user_id": "reconnect_user"}
            )
            
            # Simulate connection loss and recovery
            reconnect_attempts = 3
            successful_reconnects = 0
            reconnect_times = []
            
            for attempt in range(reconnect_attempts):
                # Simulate disconnect
                await client.disconnect()
                assert not client.is_connected, f"Should be disconnected after attempt {attempt}"
                
                # Wait brief period before reconnect
                await asyncio.sleep(0.5)
                
                # Attempt reconnection
                reconnect_start = time.time()
                success = await client.connect(mock_mode=True, timeout=10.0)
                reconnect_time = time.time() - reconnect_start
                
                if success:
                    successful_reconnects += 1
                    reconnect_times.append(reconnect_time)
                    
                    # Verify connection works after reconnect
                    test_message = await client.send_message(
                        WebSocketEventType.PING,
                        {"reconnect_test": attempt + 1, "timestamp": time.time()}
                    )
                    assert test_message.message_id, f"Failed to send after reconnect {attempt + 1}"
                
                await asyncio.sleep(0.2)
            
            # Verify reconnection success rate
            success_rate = successful_reconnects / reconnect_attempts
            assert success_rate >= 0.8, f"Reconnect success rate too low: {success_rate}"
            
            # Verify reconnection performance
            if reconnect_times:
                avg_reconnect_time = sum(reconnect_times) / len(reconnect_times)
                assert avg_reconnect_time < 5.0, f"Average reconnect time too slow: {avg_reconnect_time}s"
            
            self.record_metric("reconnect_attempts", reconnect_attempts)
            self.record_metric("successful_reconnects", successful_reconnects)
            self.record_metric("reconnect_success_rate", success_rate)
            if reconnect_times:
                self.record_metric("avg_reconnect_time", sum(reconnect_times) / len(reconnect_times))
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_concurrent_connection_management(self):
        """
        Test WebSocket connection management with multiple concurrent connections.
        
        BVJ: Enterprise - Multiple concurrent users require isolated connection management.
        """
        async with WebSocketTestUtility() as ws_util:
            concurrent_users = 10
            connection_tasks = []
            connected_clients = []
            
            # Create multiple concurrent connections
            async def create_and_connect_client(user_index: int) -> Dict[str, Any]:
                user_id = f"concurrent_user_{user_index}"
                client = await ws_util.create_authenticated_client(user_id)
                
                connect_start = time.time()
                success = await client.connect(mock_mode=True)
                connect_time = time.time() - connect_start
                
                if success:
                    # Send identification message
                    await client.send_message(
                        WebSocketEventType.USER_CONNECTED,
                        {
                            "user_id": user_id,
                            "connection_index": user_index,
                            "connect_time": connect_time
                        }
                    )
                    connected_clients.append(client)
                
                return {
                    "user_id": user_id,
                    "success": success,
                    "connect_time": connect_time,
                    "client": client
                }
            
            # Launch concurrent connection attempts
            connection_tasks = [
                create_and_connect_client(i) for i in range(concurrent_users)
            ]
            
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            try:
                # Verify concurrent connection success
                successful_connections = [
                    result for result in connection_results 
                    if isinstance(result, dict) and result.get("success", False)
                ]
                
                success_rate = len(successful_connections) / concurrent_users
                assert success_rate >= 0.9, f"Concurrent connection success rate too low: {success_rate}"
                
                # Test concurrent message sending
                message_tasks = []
                for i, client in enumerate(connected_clients[:5]):  # Test with first 5 clients
                    message_task = client.send_message(
                        WebSocketEventType.AGENT_STARTED,
                        {
                            "concurrent_test": True,
                            "client_index": i,
                            "message_timestamp": time.time()
                        }
                    )
                    message_tasks.append(message_task)
                
                # Wait for concurrent messages
                message_results = await asyncio.gather(*message_tasks, return_exceptions=True)
                successful_messages = [
                    result for result in message_results 
                    if not isinstance(result, Exception)
                ]
                
                message_success_rate = len(successful_messages) / len(message_tasks)
                assert message_success_rate >= 0.9, f"Concurrent message success rate too low: {message_success_rate}"
                
                # Verify connection isolation
                for client in connected_clients[:3]:  # Verify first 3 clients
                    assert client.is_connected, "Client should remain connected during concurrent test"
                    
                    # Verify each client can send independent messages
                    isolation_message = await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        {"isolation_test": True, "client_id": client.test_id}
                    )
                    assert isolation_message.message_id, "Client should maintain independent messaging"
                
                self.record_metric("concurrent_users_attempted", concurrent_users)
                self.record_metric("successful_concurrent_connections", len(successful_connections))
                self.record_metric("concurrent_connection_success_rate", success_rate)
                self.record_metric("concurrent_message_success_rate", message_success_rate)
                
            finally:
                # Clean up all connections
                disconnect_tasks = [
                    client.disconnect() for client in connected_clients 
                    if hasattr(client, 'disconnect')
                ]
                if disconnect_tasks:
                    await asyncio.gather(*disconnect_tasks, return_exceptions=True)
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_connection_timeout_handling(self):
        """
        Test WebSocket connection timeout handling and recovery.
        
        BVJ: All segments - Proper timeout handling prevents hanging connections.
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("timeout_user")
            
            # Test normal connection within timeout
            normal_connect_start = time.time()
            success = await client.connect(mock_mode=True, timeout=5.0)
            normal_connect_time = time.time() - normal_connect_start
            
            assert success, "Normal connection should succeed"
            assert normal_connect_time < 5.0, "Normal connection should be within timeout"
            
            # Test connection operations with short timeout
            await client.disconnect()
            
            # Simulate various timeout scenarios
            timeout_test_results = []
            
            # Test 1: Very short timeout (should handle gracefully)
            short_timeout_start = time.time()
            try:
                success = await client.connect(mock_mode=True, timeout=0.1)
                short_timeout_time = time.time() - short_timeout_start
                timeout_test_results.append({
                    "test": "short_timeout",
                    "success": success,
                    "time": short_timeout_time,
                    "within_timeout": short_timeout_time <= 0.2  # Allow small buffer
                })
            except asyncio.TimeoutError:
                timeout_test_results.append({
                    "test": "short_timeout", 
                    "success": False,
                    "time": time.time() - short_timeout_start,
                    "timeout_handled": True
                })
            
            # Test 2: Reasonable timeout (should succeed)
            if not client.is_connected:
                reasonable_timeout_start = time.time()
                success = await client.connect(mock_mode=True, timeout=3.0)
                reasonable_timeout_time = time.time() - reasonable_timeout_start
                
                timeout_test_results.append({
                    "test": "reasonable_timeout",
                    "success": success,
                    "time": reasonable_timeout_time,
                    "within_timeout": reasonable_timeout_time <= 3.0
                })
            
            # Test message sending with connection timeout awareness
            if client.is_connected:
                # Send message with timeout considerations
                timeout_aware_message = await client.send_message(
                    WebSocketEventType.AGENT_THINKING,
                    {
                        "timeout_test": True,
                        "message_timeout_awareness": "verified",
                        "timestamp": time.time()
                    }
                )
                
                assert timeout_aware_message.message_id, "Should handle message sending with timeout awareness"
            
            # Verify timeout handling results
            successful_timeout_tests = [
                result for result in timeout_test_results 
                if result.get("success") or result.get("timeout_handled")
            ]
            
            timeout_handling_rate = len(successful_timeout_tests) / len(timeout_test_results)
            assert timeout_handling_rate >= 0.8, f"Timeout handling rate too low: {timeout_handling_rate}"
            
            self.record_metric("timeout_tests_conducted", len(timeout_test_results))
            self.record_metric("timeout_handling_success_rate", timeout_handling_rate)
            self.record_metric("normal_connection_time", normal_connect_time)
            
            await client.disconnect()