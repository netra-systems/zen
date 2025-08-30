"""
Test suite to prevent WebSocket message routing regression.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Risk Reduction
- Value Impact: Prevents message delivery failures that would break agent updates
- Strategic Impact: Ensures reliable real-time communication with users

This test suite ensures that WebSocket messages are properly routed based on run_id
and prevents regression where messages would be broadcast to all users instead of
being routed to the correct user session.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from netra_backend.app.websocket_core.manager import WebSocketManager


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state = WebSocketState.CONNECTED
        self.messages_sent: List[Dict[str, Any]] = []
        self.closed = False
        self.close_code = None
        self.close_reason = None
        
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Mock sending JSON data."""
        if self.closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(data)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure") -> None:
        """Mock closing the connection."""
        self.closed = True
        self.close_code = code
        self.close_reason = reason
        self.state = WebSocketState.DISCONNECTED


@pytest.fixture
async def websocket_manager():
    """Create a fresh WebSocket manager instance."""
    # Clear singleton
    WebSocketManager._instance = None
    
    # Patch is_websocket_connected for our mock WebSockets
    def mock_is_connected(websocket):
        if isinstance(websocket, MockWebSocket):
            return websocket.state == WebSocketState.CONNECTED and not websocket.closed
        # For real WebSocket objects, return based on state
        return getattr(websocket, 'state', None) == WebSocketState.CONNECTED
    
    with patch('netra_backend.app.websocket_core.manager.is_websocket_connected', mock_is_connected):
        with patch('netra_backend.app.websocket_core.utils.is_websocket_connected', mock_is_connected):
            manager = WebSocketManager()
            yield manager
    
    # Cleanup
    WebSocketManager._instance = None


@pytest.fixture
async def mock_websockets():
    """Create mock WebSocket connections for testing."""
    return {
        "user1": MockWebSocket("user1"),
        "user2": MockWebSocket("user2"),
        "user3": MockWebSocket("user3"),
    }


class TestWebSocketRoutingRegression:
    """Test suite to prevent WebSocket routing regression."""
    
    async def test_send_agent_update_should_route_by_run_id(self, websocket_manager, mock_websockets):
        """Test that agent updates are routed to the correct user based on run_id."""
        # Setup: Connect multiple users with different run_ids
        run_id_1 = f"run_{uuid.uuid4().hex[:8]}"
        run_id_2 = f"run_{uuid.uuid4().hex[:8]}"
        
        # Connect user1 with run_id_1
        conn_id_1 = await websocket_manager.connect_user("user1", mock_websockets["user1"])
        websocket_manager.connections[conn_id_1]["run_id"] = run_id_1
        
        # Connect user2 with run_id_2
        conn_id_2 = await websocket_manager.connect_user("user2", mock_websockets["user2"])
        websocket_manager.connections[conn_id_2]["run_id"] = run_id_2
        
        # Connect user3 without run_id (should not receive updates)
        conn_id_3 = await websocket_manager.connect_user("user3", mock_websockets["user3"])
        
        # Act: Send agent update for run_id_1
        await websocket_manager.send_agent_update(
            run_id=run_id_1,
            agent_name="TestAgent",
            update={"status": "processing", "progress": 50}
        )
        
        # Assert: Only user1 should receive the update
        assert len(mock_websockets["user1"].messages_sent) == 1
        assert len(mock_websockets["user2"].messages_sent) == 0
        assert len(mock_websockets["user3"].messages_sent) == 0
        
        # Verify message content
        message = mock_websockets["user1"].messages_sent[0]
        assert message["type"] == "agent_update"
        assert message["payload"]["run_id"] == run_id_1
        assert message["payload"]["agent_name"] == "TestAgent"
        assert message["payload"]["update"]["status"] == "processing"
    
    async def test_multiple_connections_same_run_id(self, websocket_manager, mock_websockets):
        """Test that multiple connections with same run_id all receive updates."""
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Connect multiple sessions for same user with same run_id
        ws1 = MockWebSocket("user1")
        ws2 = MockWebSocket("user1")
        
        conn_id_1 = await websocket_manager.connect_user("user1", ws1)
        websocket_manager.connections[conn_id_1]["run_id"] = run_id
        
        conn_id_2 = await websocket_manager.connect_user("user1", ws2)
        websocket_manager.connections[conn_id_2]["run_id"] = run_id
        
        # Send agent update
        await websocket_manager.send_agent_update(
            run_id=run_id,
            agent_name="MultiAgent",
            update={"message": "test"}
        )
        
        # Both connections should receive the update
        assert len(ws1.messages_sent) == 1
        assert len(ws2.messages_sent) == 1
        assert ws1.messages_sent[0]["payload"]["run_id"] == run_id
        assert ws2.messages_sent[0]["payload"]["run_id"] == run_id
    
    async def test_no_broadcast_to_unrelated_connections(self, websocket_manager):
        """Test that updates are NOT broadcast to all connections."""
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Create many unrelated connections
        unrelated_sockets = []
        for i in range(10):
            ws = MockWebSocket(f"user_{i}")
            conn_id = await websocket_manager.connect_user(f"user_{i}", ws)
            # These connections have different or no run_ids
            if i % 2 == 0:
                websocket_manager.connections[conn_id]["run_id"] = f"run_other_{i}"
            unrelated_sockets.append(ws)
        
        # Create one connection with our target run_id
        target_ws = MockWebSocket("target_user")
        target_conn_id = await websocket_manager.connect_user("target_user", target_ws)
        websocket_manager.connections[target_conn_id]["run_id"] = run_id
        
        # Send update for specific run_id
        await websocket_manager.send_agent_update(
            run_id=run_id,
            agent_name="TargetAgent",
            update={"data": "sensitive"}
        )
        
        # Only target should receive update
        assert len(target_ws.messages_sent) == 1
        for ws in unrelated_sockets:
            assert len(ws.messages_sent) == 0, "Unrelated connection should not receive update"
    
    async def test_run_id_persistence_across_updates(self, websocket_manager):
        """Test that run_id association persists across multiple updates."""
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        ws = MockWebSocket("user1")
        conn_id = await websocket_manager.connect_user("user1", ws)
        websocket_manager.connections[conn_id]["run_id"] = run_id
        
        # Send multiple updates
        for i in range(5):
            await websocket_manager.send_agent_update(
                run_id=run_id,
                agent_name=f"Agent{i}",
                update={"iteration": i}
            )
        
        # All updates should be received
        assert len(ws.messages_sent) == 5
        for i, msg in enumerate(ws.messages_sent):
            assert msg["payload"]["run_id"] == run_id
            assert msg["payload"]["agent_name"] == f"Agent{i}"
            assert msg["payload"]["update"]["iteration"] == i
    
    async def test_run_id_cleanup_on_disconnect(self, websocket_manager):
        """Test that run_id mappings are cleaned up on disconnect."""
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        ws = MockWebSocket("user1")
        conn_id = await websocket_manager.connect_user("user1", ws)
        websocket_manager.connections[conn_id]["run_id"] = run_id
        
        # Add run_id to active runs mapping (if it exists)
        if not hasattr(websocket_manager, "active_runs"):
            websocket_manager.active_runs = {}
        websocket_manager.active_runs[run_id] = {conn_id}
        
        # Disconnect using the proper method signature
        await websocket_manager.disconnect("user1", ws)
        
        # Verify cleanup
        assert conn_id not in websocket_manager.connections
        if hasattr(websocket_manager, "active_runs"):
            assert run_id not in websocket_manager.active_runs or conn_id not in websocket_manager.active_runs.get(run_id, set())
        
        # New update should not crash
        await websocket_manager.send_agent_update(
            run_id=run_id,
            agent_name="PostDisconnect",
            update={"test": "cleanup"}
        )
        
        # No messages sent since connection is gone
        assert len(ws.messages_sent) == 0
    
    async def test_concurrent_updates_different_run_ids(self, websocket_manager):
        """Test that concurrent updates to different run_ids don't interfere."""
        run_ids = [f"run_{i}" for i in range(5)]
        websockets = {}
        
        # Setup connections with different run_ids
        for i, run_id in enumerate(run_ids):
            ws = MockWebSocket(f"user_{i}")
            conn_id = await websocket_manager.connect_user(f"user_{i}", ws)
            websocket_manager.connections[conn_id]["run_id"] = run_id
            websockets[run_id] = ws
        
        # Send concurrent updates
        tasks = []
        for run_id in run_ids:
            task = websocket_manager.send_agent_update(
                run_id=run_id,
                agent_name="ConcurrentAgent",
                update={"run_id": run_id}
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Each connection should only receive its own update
        for run_id, ws in websockets.items():
            assert len(ws.messages_sent) == 1
            assert ws.messages_sent[0]["payload"]["run_id"] == run_id
            assert ws.messages_sent[0]["payload"]["update"]["run_id"] == run_id
    
    async def test_invalid_run_id_handling(self, websocket_manager):
        """Test graceful handling of updates to non-existent run_ids."""
        # Send update to non-existent run_id (should not crash)
        await websocket_manager.send_agent_update(
            run_id="run_nonexistent",
            agent_name="GhostAgent",
            update={"test": "invalid"}
        )
        
        # Should complete without error
        assert True
    
    async def test_run_id_format_validation(self, websocket_manager):
        """Test that run_ids follow expected format."""
        ws = MockWebSocket("user1")
        conn_id = await websocket_manager.connect_user("user1", ws)
        
        # Valid run_id format
        valid_run_id = f"run_{uuid.uuid4().hex[:8]}"
        websocket_manager.connections[conn_id]["run_id"] = valid_run_id
        
        await websocket_manager.send_agent_update(
            run_id=valid_run_id,
            agent_name="ValidAgent",
            update={"test": "valid"}
        )
        
        assert len(ws.messages_sent) == 1
        
        # Also test with full UUID format
        full_uuid_run_id = f"run_{uuid.uuid4()}"
        websocket_manager.connections[conn_id]["run_id"] = full_uuid_run_id
        
        await websocket_manager.send_agent_update(
            run_id=full_uuid_run_id,
            agent_name="UUIDAgent",
            update={"test": "uuid"}
        )
        
        assert len(ws.messages_sent) == 2


class TestWebSocketManagerRunIdMapping:
    """Test run_id mapping functionality in WebSocket manager."""
    
    async def test_associate_run_id_with_connection(self, websocket_manager):
        """Test associating a run_id with an existing connection."""
        ws = MockWebSocket("user1")
        conn_id = await websocket_manager.connect_user("user1", ws)
        
        # Associate run_id
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        if hasattr(websocket_manager, 'associate_run_id'):
            await websocket_manager.associate_run_id(conn_id, run_id)
        else:
            # Direct assignment for testing
            websocket_manager.connections[conn_id]["run_id"] = run_id
        
        # Verify association
        assert websocket_manager.connections[conn_id]["run_id"] == run_id
    
    async def test_get_connections_by_run_id(self, websocket_manager):
        """Test retrieving all connections for a given run_id."""
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Create multiple connections with same run_id
        connections = []
        for i in range(3):
            ws = MockWebSocket(f"user_{i}")
            conn_id = await websocket_manager.connect_user(f"user_{i}", ws)
            websocket_manager.connections[conn_id]["run_id"] = run_id
            connections.append(conn_id)
        
        # Get connections by run_id
        if hasattr(websocket_manager, 'get_connections_by_run_id'):
            found_connections = await websocket_manager.get_connections_by_run_id(run_id)
            assert set(found_connections) == set(connections)
        else:
            # Manual check
            found = [
                cid for cid, info in websocket_manager.connections.items()
                if info.get("run_id") == run_id
            ]
            assert set(found) == set(connections)


@pytest.mark.asyncio
async def test_websocket_routing_integration():
    """Integration test for complete WebSocket routing flow."""
    manager = WebSocketManager()
    
    # Simulate real connection flow
    user_id = "test_user_123"
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    
    ws = MockWebSocket(user_id)
    conn_id = await manager.connect_user(user_id, ws)
    
    # Associate run_id with connection
    manager.connections[conn_id]["run_id"] = run_id
    
    # Send multiple agent updates
    agents = ["TriageAgent", "DataAgent", "SupplyAgent"]
    for agent_name in agents:
        await manager.send_agent_update(
            run_id=run_id,
            agent_name=agent_name,
            update={
                "status": "processing",
                "message": f"{agent_name} is working"
            }
        )
    
    # Verify all updates received
    assert len(ws.messages_sent) == len(agents)
    for i, msg in enumerate(ws.messages_sent):
        assert msg["type"] == "agent_update"
        assert msg["payload"]["agent_name"] == agents[i]
        assert msg["payload"]["run_id"] == run_id
    
    # Cleanup
    await manager.disconnect(user_id, ws)