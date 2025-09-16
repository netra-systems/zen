"""
Focused Integration Test: UnifiedWebSocketManager Connection Patterns

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure UnifiedWebSocketManager provides reliable WebSocket coordination
- Value Impact: Validates WebSocket connection management, user isolation, and event delivery patterns
- Strategic Impact: Critical for real-time user experience and multi-user platform functionality

Tests UnifiedWebSocketManager SSOT coordination patterns:
- Connection creation and management validation
- User-scoped connection isolation patterns
- WebSocket event emission coordination (agent_started, agent_completed, etc.)
- Connection lifecycle management (connect, disconnect, cleanup)
- User isolation for WebSocket connections
- Event queuing and delivery coordination

This is a NON-DOCKER integration test that focuses on core UnifiedWebSocketManager SSOT patterns.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

# Core imports
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection
)

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment


class TestUnifiedWebSocketManagerConnections(BaseIntegrationTest):
    """Focused integration tests for UnifiedWebSocketManager SSOT coordination patterns."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set("TEST_MODE", "true", source="test")
        self.websocket_manager = UnifiedWebSocketManager()
        
    @pytest.fixture
    async def mock_websocket(self):
        """Create mock WebSocket connection."""
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        return mock_ws
        
    @pytest.fixture
    async def test_websocket_connection(self, mock_websocket):
        """Create test WebSocket connection."""
        connection = WebSocketConnection(
            connection_id=f"conn_{uuid.uuid4().hex[:8]}",
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            websocket=mock_websocket,
            connected_at=datetime.utcnow(),
            metadata={"test": "websocket_connection"}
        )
        return connection
    
    @pytest.mark.integration
    async def test_unified_websocket_manager_initialization_patterns(self):
        """Test UnifiedWebSocketManager initialization SSOT patterns."""
        
        # Validate basic initialization state
        assert isinstance(self.websocket_manager._connections, dict)
        assert isinstance(self.websocket_manager._user_connections, dict)
        assert self.websocket_manager._lock is not None
        
        # Validate enhanced thread safety features
        assert isinstance(self.websocket_manager._user_connection_locks, dict)
        assert self.websocket_manager._connection_lock_creation_lock is not None
        
        # Validate error handling and recovery system
        assert isinstance(self.websocket_manager._message_recovery_queue, dict)
        assert isinstance(self.websocket_manager._connection_error_count, dict)
        assert self.websocket_manager._error_recovery_enabled is True
        
        # Validate background monitoring system
        assert isinstance(self.websocket_manager._background_tasks, dict)
        assert isinstance(self.websocket_manager._task_failures, dict)
        assert self.websocket_manager._monitoring_enabled is True
        assert self.websocket_manager._shutdown_requested is False
        
        # Validate compatibility registry
        assert self.websocket_manager.registry is not None
        assert self.websocket_manager._connection_manager is self.websocket_manager
        assert self.websocket_manager.connection_manager is self.websocket_manager
        
        self.logger.info(" PASS:  UnifiedWebSocketManager initialization patterns validated")
    
    @pytest.mark.integration
    async def test_websocket_connection_addition_patterns(self, test_websocket_connection):
        """Test WebSocket connection addition SSOT patterns."""
        
        # Validate initial state (no connections)
        assert len(self.websocket_manager._connections) == 0
        assert len(self.websocket_manager._user_connections) == 0
        
        # Add connection using SSOT pattern
        await self.websocket_manager.add_connection(test_websocket_connection)
        
        # Validate connection was added
        connection_id = test_websocket_connection.connection_id
        user_id = test_websocket_connection.user_id
        
        assert connection_id in self.websocket_manager._connections
        assert self.websocket_manager._connections[connection_id] == test_websocket_connection
        
        # Validate user connection mapping
        assert user_id in self.websocket_manager._user_connections
        assert connection_id in self.websocket_manager._user_connections[user_id]
        
        # Validate thread safety - user lock created
        assert user_id in self.websocket_manager._user_connection_locks
        
        # Validate compatibility mapping
        assert user_id in self.websocket_manager.active_connections
        assert len(self.websocket_manager.active_connections[user_id]) == 1
        
        self.logger.info(" PASS:  WebSocket connection addition patterns validated")
    
    @pytest.mark.integration
    async def test_websocket_connection_removal_patterns(self, test_websocket_connection):
        """Test WebSocket connection removal SSOT patterns."""
        
        # Add connection first
        await self.websocket_manager.add_connection(test_websocket_connection)
        connection_id = test_websocket_connection.connection_id
        user_id = test_websocket_connection.user_id
        
        # Validate connection exists
        assert connection_id in self.websocket_manager._connections
        assert user_id in self.websocket_manager._user_connections
        
        # Remove connection using SSOT pattern
        await self.websocket_manager.remove_connection(connection_id)
        
        # Validate connection removed
        assert connection_id not in self.websocket_manager._connections
        
        # Validate user connection mapping cleaned up
        if user_id in self.websocket_manager._user_connections:
            assert connection_id not in self.websocket_manager._user_connections[user_id]
        
        # Validate compatibility mapping cleaned up
        if user_id in self.websocket_manager.active_connections:
            conn_ids = [c.connection_id for c in self.websocket_manager.active_connections[user_id]]
            assert connection_id not in conn_ids
        
        self.logger.info(" PASS:  WebSocket connection removal patterns validated")
    
    @pytest.mark.integration
    async def test_user_scoped_connection_isolation_patterns(self):
        """Test UnifiedWebSocketManager provides complete isolation between different users."""
        
        # Create connections for two different users
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        user1_connection = WebSocketConnection(
            connection_id=f"conn_1_{uuid.uuid4().hex[:8]}",
            user_id="isolation_user_1_alpha",
            websocket=mock_ws1,
            connected_at=datetime.utcnow(),
            metadata={"user_data": "sensitive_user_1_data"}
        )
        
        user2_connection = WebSocketConnection(
            connection_id=f"conn_2_{uuid.uuid4().hex[:8]}",
            user_id="isolation_user_2_beta", 
            websocket=mock_ws2,
            connected_at=datetime.utcnow(),
            metadata={"user_data": "sensitive_user_2_data"}
        )
        
        # Add both connections
        await self.websocket_manager.add_connection(user1_connection)
        await self.websocket_manager.add_connection(user2_connection)
        
        # Validate complete isolation between users
        user1_connections = self.websocket_manager.get_user_connections(user1_connection.user_id)
        user2_connections = self.websocket_manager.get_user_connections(user2_connection.user_id)
        
        # Users should have different connection sets
        assert user1_connections != user2_connections
        assert user1_connection.connection_id in user1_connections
        assert user1_connection.connection_id not in user2_connections
        assert user2_connection.connection_id in user2_connections
        assert user2_connection.connection_id not in user1_connections
        
        # Validate separate user locks created
        assert user1_connection.user_id in self.websocket_manager._user_connection_locks
        assert user2_connection.user_id in self.websocket_manager._user_connection_locks
        assert (self.websocket_manager._user_connection_locks[user1_connection.user_id] != 
                self.websocket_manager._user_connection_locks[user2_connection.user_id])
        
        # Validate connection health checks work per user
        assert self.websocket_manager.is_connection_active(user1_connection.user_id) is True
        assert self.websocket_manager.is_connection_active(user2_connection.user_id) is True
        
        user1_health = self.websocket_manager.get_connection_health(user1_connection.user_id)
        user2_health = self.websocket_manager.get_connection_health(user2_connection.user_id)
        
        assert user1_health['user_id'] == user1_connection.user_id
        assert user2_health['user_id'] == user2_connection.user_id
        assert user1_health != user2_health
        
        self.logger.info(" PASS:  User-scoped connection isolation patterns validated")
    
    @pytest.mark.integration
    async def test_websocket_event_emission_coordination_patterns(self, test_websocket_connection):
        """Test WebSocket event emission coordination patterns."""
        
        # Add connection for event testing
        await self.websocket_manager.add_connection(test_websocket_connection)
        user_id = test_websocket_connection.user_id
        mock_websocket = test_websocket_connection.websocket
        
        # Test basic event emission patterns
        test_events = [
            ("agent_started", {"agent_id": "test_agent_123", "task": "data_processing"}),
            ("agent_thinking", {"thought": "Analyzing data patterns...", "step": 1}),
            ("tool_executing", {"tool": "data_analyzer", "operation": "process_csv"}),
            ("tool_completed", {"tool": "data_analyzer", "result": "analysis_complete"}),
            ("agent_completed", {"agent_id": "test_agent_123", "result": "task_finished"})
        ]
        
        # Test each critical WebSocket event type
        for event_type, event_data in test_events:
            # Reset mock for clean testing
            mock_websocket.send_json.reset_mock()
            
            # Emit critical event using SSOT pattern
            await self.websocket_manager.emit_critical_event(user_id, event_type, event_data)
            
            # Validate event was sent with correct structure
            assert mock_websocket.send_json.called
            sent_message = mock_websocket.send_json.call_args[0][0]
            
            assert sent_message["type"] == event_type
            assert sent_message["data"] == event_data
            assert "timestamp" in sent_message
            assert sent_message["critical"] is True
            
        # Test broadcast coordination
        broadcast_message = {
            "type": "system_announcement",
            "data": {"message": "System maintenance scheduled"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        mock_websocket.send_json.reset_mock()
        await self.websocket_manager.broadcast(broadcast_message)
        
        # Validate broadcast was sent
        assert mock_websocket.send_json.called
        sent_broadcast = mock_websocket.send_json.call_args[0][0]
        assert sent_broadcast == broadcast_message
        
        self.logger.info(" PASS:  WebSocket event emission coordination patterns validated")
    
    @pytest.mark.integration
    async def test_connection_lifecycle_management_patterns(self):
        """Test connection lifecycle management patterns (connect, disconnect, cleanup)."""
        
        # Test legacy compatibility connection methods
        mock_websocket = AsyncMock()
        user_id = f"lifecycle_user_{uuid.uuid4().hex[:8]}"
        
        # Test connect_user legacy method
        connection_info = await self.websocket_manager.connect_user(user_id, mock_websocket)
        
        # Validate connection was established
        assert connection_info is not None
        assert connection_info.user_id == user_id
        assert connection_info.websocket == mock_websocket
        assert hasattr(connection_info, 'connection_id')
        
        # Validate connection exists in manager
        assert self.websocket_manager.is_connection_active(user_id) is True
        connection_health = self.websocket_manager.get_connection_health(user_id)
        assert connection_health['has_active_connections'] is True
        
        # Test find_connection method
        found_connection = await self.websocket_manager.find_connection(user_id, mock_websocket)
        assert found_connection is not None
        assert found_connection.user_id == user_id
        assert found_connection.websocket == mock_websocket
        
        # Test disconnect_user legacy method
        await self.websocket_manager.disconnect_user(user_id, mock_websocket)
        
        # Validate connection was cleaned up
        assert self.websocket_manager.is_connection_active(user_id) is False
        
        # Test connection cleanup was complete
        user_connections = self.websocket_manager.get_user_connections(user_id)
        assert len(user_connections) == 0
        
        self.logger.info(" PASS:  Connection lifecycle management patterns validated")
    
    @pytest.mark.integration 
    async def test_message_queuing_and_recovery_coordination_patterns(self):
        """Test message queuing and recovery coordination patterns."""
        
        user_id = f"recovery_user_{uuid.uuid4().hex[:8]}"
        
        # Test sending message when no connection exists (should queue)
        test_message = {
            "type": "agent_started",
            "data": {"agent_id": "test_recovery", "task": "queued_task"}
        }
        
        # This should queue the message since no connection exists
        await self.websocket_manager.send_to_user(user_id, test_message)
        
        # Validate message was queued for recovery
        assert user_id in self.websocket_manager._message_recovery_queue
        queued_messages = self.websocket_manager._message_recovery_queue[user_id]
        assert len(queued_messages) > 0
        
        # Find our test message in the queue
        test_msg_found = False
        for msg in queued_messages:
            if msg.get("type") == "agent_started" and msg.get("data", {}).get("agent_id") == "test_recovery":
                test_msg_found = True
                assert "failure_reason" in msg
                assert "failed_at" in msg
                break
        assert test_msg_found
        
        # Test message recovery when connection is established
        mock_websocket = AsyncMock()
        connection = WebSocketConnection(
            connection_id=f"recovery_conn_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.utcnow(),
            metadata={"test": "recovery_connection"}
        )
        
        # Add connection - this should trigger queued message processing
        await self.websocket_manager.add_connection(connection)
        
        # Give the async processing time to complete
        await asyncio.sleep(0.2)
        
        # Validate recovery attempts
        recovery_count = await self.websocket_manager.attempt_message_recovery(user_id)
        
        # Test error statistics tracking
        error_stats = self.websocket_manager.get_error_statistics()
        assert isinstance(error_stats, dict)
        assert "total_users_with_errors" in error_stats
        assert "error_recovery_enabled" in error_stats
        assert error_stats["error_recovery_enabled"] is True
        
        self.logger.info(" PASS:  Message queuing and recovery coordination patterns validated")
    
    @pytest.mark.integration
    async def test_websocket_manager_statistics_and_monitoring_patterns(self):
        """Test WebSocket manager statistics and monitoring patterns."""
        
        # Add multiple connections for different users
        connections = []
        for i in range(3):
            mock_ws = AsyncMock()
            connection = WebSocketConnection(
                connection_id=f"stats_conn_{i}_{uuid.uuid4().hex[:8]}",
                user_id=f"stats_user_{i}",
                websocket=mock_ws,
                connected_at=datetime.utcnow(),
                metadata={"index": i}
            )
            connections.append(connection)
            await self.websocket_manager.add_connection(connection)
        
        # Test get_stats method
        stats = self.websocket_manager.get_stats()
        assert isinstance(stats, dict)
        assert stats["total_connections"] == 3
        assert stats["unique_users"] == 3
        assert "connections_by_user" in stats
        
        # Validate each user has one connection
        for i in range(3):
            user_id = f"stats_user_{i}"
            assert user_id in stats["connections_by_user"]
            assert stats["connections_by_user"][user_id] == 1
        
        # Test background task monitoring status
        task_status = self.websocket_manager.get_background_task_status()
        assert isinstance(task_status, dict)
        assert "monitoring_enabled" in task_status
        assert "total_tasks" in task_status
        assert "running_tasks" in task_status
        assert "tasks" in task_status
        assert task_status["monitoring_enabled"] is True
        
        # Test monitoring health status
        health_status = await self.websocket_manager.get_monitoring_health_status()
        assert isinstance(health_status, dict)
        assert "monitoring_enabled" in health_status
        assert "task_health" in health_status
        assert "overall_health" in health_status
        assert "alerts" in health_status
        
        # Validate health score calculation
        overall_health = health_status["overall_health"]
        assert "score" in overall_health
        assert "status" in overall_health
        assert isinstance(overall_health["score"], (int, float))
        assert overall_health["status"] in ["healthy", "warning", "degraded", "critical"]
        
        self.logger.info(" PASS:  WebSocket manager statistics and monitoring patterns validated")


# Additional helper functions for WebSocket coordination validation

def validate_websocket_connection_isolation(manager: UnifiedWebSocketManager, 
                                          connection1: WebSocketConnection, 
                                          connection2: WebSocketConnection) -> None:
    """Validate that two WebSocket connections are completely isolated."""
    # Connection ID isolation
    assert connection1.connection_id != connection2.connection_id
    
    # User ID isolation (should be different for isolation testing)
    assert connection1.user_id != connection2.user_id
    
    # WebSocket instance isolation
    assert connection1.websocket != connection2.websocket
    
    # User connection mapping isolation
    user1_connections = manager.get_user_connections(connection1.user_id)
    user2_connections = manager.get_user_connections(connection2.user_id)
    assert user1_connections.isdisjoint(user2_connections)


def validate_websocket_manager_thread_safety(manager: UnifiedWebSocketManager, 
                                            user_id: str) -> None:
    """Validate that WebSocket manager provides proper thread safety for a user."""
    # User-specific lock should exist
    assert user_id in manager._user_connection_locks
    
    # Main lock should exist
    assert manager._lock is not None
    
    # Lock creation lock should exist
    assert manager._connection_lock_creation_lock is not None


def validate_websocket_event_structure(message: Dict[str, Any], 
                                     expected_type: str, 
                                     expected_data: Dict[str, Any]) -> None:
    """Validate that a WebSocket event message has the expected SSOT structure."""
    # Required fields present
    assert "type" in message
    assert "data" in message
    assert "timestamp" in message
    
    # Correct event type and data
    assert message["type"] == expected_type
    assert message["data"] == expected_data
    
    # Timestamp is valid ISO format
    timestamp_str = message["timestamp"]
    assert isinstance(timestamp_str, str)
    # Basic ISO format validation (should not raise exception)
    datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    
    # Critical event flag if present
    if "critical" in message:
        assert isinstance(message["critical"], bool)