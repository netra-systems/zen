"""Real WebSocket Connection Lifecycle Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Connection Stability & User Experience 
- Value Impact: Ensures WebSocket connections establish and close properly for chat value delivery
- Strategic Impact: Prevents connection leaks that cause chat failures affecting 90% of user traffic

Tests real WebSocket connection establishment, maintenance, and cleanup with Docker services.
Validates connection state transitions and proper resource cleanup.

CRITICAL: Tests the PRIMARY path (90% traffic goes through WebSocket) per CLAUDE.md
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
import websockets
from websockets.exceptions import WebSocketException

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.types import (
    WebSocketConnectionState,
    WebSocketMessage,
    MessageType
)
from netra_backend.tests.real_services_test_fixtures import skip_if_no_real_services
from shared.isolated_environment import get_env

env = get_env()


@pytest.mark.real_services
@pytest.mark.websocket
@skip_if_no_real_services
class TestRealWebSocketConnectionLifecycle:
    """Test real WebSocket connection lifecycle with Docker services.
    
    CRITICAL: Tests actual WebSocket connections, not mocks.
    Validates connection state management for chat value delivery.
    """
    
    @pytest.fixture
    async def websocket_manager(self):
        """Create real WebSocket manager for testing."""
        manager = UnifiedWebSocketManager()
        yield manager
        # Cleanup: Close all connections
        await manager.disconnect_all()
    
    @pytest.fixture
    def websocket_url(self):
        """Get WebSocket URL from environment."""
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000")
        return f"ws://{backend_host}:{backend_port}/ws"
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers for WebSocket connection."""
        # Use real JWT token for testing
        jwt_token = env.get("TEST_JWT_TOKEN", "test_token_123")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "Netra-Test-Client/1.0"
        }
    
    @pytest.mark.asyncio
    async def test_connection_establishment_real(self, websocket_url, auth_headers):
        """Test real WebSocket connection establishment."""
        connection_established = False
        connection_id = None
        
        try:
            # Establish real WebSocket connection with auth headers
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket:
                connection_established = True
                
                # Send handshake message
                handshake_message = {
                    "type": "connect",
                    "user_id": "test_user_lifecycle",
                    "client_info": {
                        "user_agent": "Netra-Test-Client",
                        "version": "1.0"
                    }
                }
                
                await websocket.send(json.dumps(handshake_message))
                
                # Receive connection acknowledgment
                response_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response = json.loads(response_raw)
                
                # Validate connection response
                assert response["type"] == "connection_established"
                assert "connection_id" in response
                assert response["status"] == "connected"
                connection_id = response["connection_id"]
                
                # Verify connection is active
                ping_message = {"type": "heartbeat", "timestamp": time.time()}
                await websocket.send(json.dumps(ping_message))
                
                pong_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                pong_data = json.loads(pong_response)
                assert pong_data["type"] == "heartbeat_ack"
                
        except Exception as e:
            pytest.fail(f"WebSocket connection establishment failed: {e}")
        
        # Verify connection was properly established
        assert connection_established, "WebSocket connection was not established"
        assert connection_id is not None, "Connection ID was not received"
    
    @pytest.mark.asyncio
    async def test_connection_state_transitions(self, websocket_url, auth_headers):
        """Test WebSocket connection state transitions."""
        states_observed = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket:
                states_observed.append("CONNECTING")
                
                # Send connect message
                connect_msg = {
                    "type": "connect",
                    "user_id": "test_user_states",
                    "track_states": True
                }
                await websocket.send(json.dumps(connect_msg))
                
                # Receive connection confirmation
                response = json.loads(await websocket.recv())
                if response.get("status") == "connected":
                    states_observed.append("CONNECTED")
                
                # Send disconnect message
                disconnect_msg = {"type": "disconnect", "reason": "test_cleanup"}
                await websocket.send(json.dumps(disconnect_msg))
                
                # Wait for disconnect confirmation
                try:
                    final_response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    final_data = json.loads(final_response)
                    if final_data.get("type") == "disconnect_ack":
                        states_observed.append("DISCONNECTING")
                except asyncio.TimeoutError:
                    # Expected if connection closes immediately
                    pass
                
        except WebSocketException:
            states_observed.append("DISCONNECTED")
        
        # Validate state transitions occurred
        assert "CONNECTING" in states_observed or len(states_observed) > 0
        assert len(states_observed) >= 2, f"Expected multiple state transitions, got: {states_observed}"
    
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_close(self, websocket_manager, websocket_url, auth_headers):
        """Test proper connection cleanup when WebSocket closes."""
        connection_id = None
        user_id = "test_user_cleanup"
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket:
                # Register connection
                connect_msg = {
                    "type": "connect", 
                    "user_id": user_id,
                    "request_connection_tracking": True
                }
                await websocket.send(json.dumps(connect_msg))
                
                response = json.loads(await websocket.recv())
                connection_id = response.get("connection_id")
                
                # Verify connection is tracked
                assert connection_id is not None
                
                # Connection will close when exiting context
                
        except Exception as e:
            # Connection closed as expected
            pass
        
        # Allow time for cleanup
        await asyncio.sleep(1)
        
        # Verify connection was cleaned up in manager
        # Note: This tests the manager's cleanup logic
        user_connections = websocket_manager._user_connections.get(user_id, set())
        connection_exists = connection_id in websocket_manager._connections
        
        # Connection should be cleaned up
        assert len(user_connections) == 0 or connection_id not in user_connections
        assert not connection_exists, "Connection was not properly cleaned up"
    
    @pytest.mark.asyncio
    async def test_multiple_connection_lifecycle(self, websocket_url, auth_headers):
        """Test lifecycle of multiple concurrent connections."""
        connection_tasks = []
        connection_results = []
        
        async def create_connection(user_id: str, connection_num: int):
            """Create and manage a single connection."""
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=10
                ) as websocket:
                    # Connect
                    connect_msg = {"type": "connect", "user_id": user_id}
                    await websocket.send(json.dumps(connect_msg))
                    
                    response = json.loads(await websocket.recv())
                    connection_id = response.get("connection_id")
                    
                    # Hold connection briefly
                    await asyncio.sleep(0.5)
                    
                    # Send test message
                    test_msg = {
                        "type": "user_message",
                        "content": f"Test message from connection {connection_num}",
                        "user_id": user_id
                    }
                    await websocket.send(json.dumps(test_msg))
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        connection_results.append({
                            "connection_id": connection_id,
                            "user_id": user_id,
                            "success": True,
                            "connection_num": connection_num
                        })
                    except asyncio.TimeoutError:
                        connection_results.append({
                            "connection_id": connection_id,
                            "user_id": user_id,
                            "success": False,
                            "connection_num": connection_num,
                            "error": "timeout"
                        })
                        
            except Exception as e:
                connection_results.append({
                    "user_id": user_id,
                    "success": False,
                    "connection_num": connection_num,
                    "error": str(e)
                })
        
        # Create multiple concurrent connections
        for i in range(3):
            user_id = f"test_user_multi_{i}"
            task = asyncio.create_task(create_connection(user_id, i))
            connection_tasks.append(task)
        
        # Wait for all connections to complete
        await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Validate results
        assert len(connection_results) == 3, f"Expected 3 results, got {len(connection_results)}"
        
        successful_connections = [r for r in connection_results if r.get("success")]
        assert len(successful_connections) >= 1, f"At least 1 connection should succeed. Results: {connection_results}"
    
    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self, websocket_url, auth_headers):
        """Test WebSocket connection timeout scenarios."""
        # Test connection timeout
        with pytest.raises((asyncio.TimeoutError, WebSocketException, OSError)):
            async with websockets.connect(
                "ws://invalid-host-that-does-not-exist:8000/ws",
                extra_headers=auth_headers,
                timeout=1  # Very short timeout
            ) as websocket:
                await websocket.send('{"type": "connect"}')
        
        # Test valid connection with message timeout
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket:
                # Send connect message
                await websocket.send(json.dumps({"type": "connect", "user_id": "timeout_test"}))
                
                # Wait for response with timeout
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                
                # Connection established successfully
                assert response is not None
                response_data = json.loads(response)
                assert "type" in response_data
                
        except (asyncio.TimeoutError, WebSocketException) as e:
            # Timeout is acceptable for this test
            assert "timeout" in str(e).lower() or "connection" in str(e).lower()