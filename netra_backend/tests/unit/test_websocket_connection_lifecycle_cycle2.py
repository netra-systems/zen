"""
Unit Tests for WebSocket Connection Lifecycle - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable WebSocket connection management for chat interactions
- Value Impact: Stable connections enable uninterrupted AI conversations and real-time updates
- Strategic Impact: Connection reliability directly affects user experience and retention

CRITICAL: WebSocket connection lifecycle management enables the chat business value by
ensuring users maintain stable connections for real-time AI interactions. Poor connection
management would break the primary value delivery mechanism.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Optional
import time
import uuid

from netra_backend.websocket.websocket_manager import WebSocketManager
from netra_backend.websocket.connection_state import ConnectionState, ConnectionStatus
from shared.types import UserID, ConnectionID
from test_framework.ssot.websocket_test_client import WebSocketTestClient


class TestWebSocketConnectionLifecycle:
    """Test WebSocket connection lifecycle management patterns."""
    
    @pytest.mark.unit
    def test_connection_establishment_lifecycle(self):
        """
        Test complete WebSocket connection establishment lifecycle.
        
        Business Value: Users can successfully establish chat connections to interact with AI.
        Connection establishment is the first step in delivering chat business value.
        """
        # Arrange: WebSocket manager and connection parameters
        manager = WebSocketManager()
        user_id = UserID("lifecycle_user")
        connection_id = ConnectionID(str(uuid.uuid4()))
        
        mock_websocket = Mock()
        mock_websocket.client_state = Mock()
        mock_websocket.client_state.value = 1  # OPEN state
        
        # Act: Establish connection through complete lifecycle
        connection_state = manager.create_connection_state(
            user_id=user_id,
            connection_id=connection_id,
            websocket=mock_websocket
        )
        
        # Verify initial state
        assert connection_state.status == ConnectionStatus.CONNECTING, "Should start in connecting state"
        assert connection_state.user_id == user_id, "Should track correct user"
        assert connection_state.connection_id == connection_id, "Should track correct connection"
        
        # Complete connection establishment
        manager.mark_connection_established(connection_id)
        updated_state = manager.get_connection_state(connection_id)
        
        # Assert: Connection properly established
        assert updated_state.status == ConnectionStatus.CONNECTED, "Should transition to connected state"
        assert updated_state.established_at is not None, "Should record establishment time"
        assert updated_state.is_active(), "Connection should be active"
        
        # Business requirement: Connected state enables message delivery
        assert manager.can_send_message(connection_id), "Established connection should accept messages"

    @pytest.mark.unit
    def test_connection_heartbeat_lifecycle_management(self):
        """
        Test WebSocket connection heartbeat lifecycle for connection health monitoring.
        
        Business Value: Heartbeat monitoring prevents chat session timeouts and maintains
        continuous AI interaction capability for users.
        """
        # Arrange: Connection with heartbeat monitoring
        manager = WebSocketManager()
        user_id = UserID("heartbeat_user")
        connection_id = ConnectionID(str(uuid.uuid4()))
        
        mock_websocket = Mock()
        mock_websocket.client_state = Mock()
        mock_websocket.client_state.value = 1  # OPEN state
        
        connection_state = manager.create_connection_state(
            user_id=user_id,
            connection_id=connection_id,
            websocket=mock_websocket,
            heartbeat_enabled=True
        )
        
        manager.mark_connection_established(connection_id)
        
        # Act: Simulate heartbeat lifecycle
        initial_heartbeat = time.time()
        manager.record_heartbeat(connection_id, initial_heartbeat)
        
        # Verify heartbeat recorded
        state_after_heartbeat = manager.get_connection_state(connection_id)
        assert state_after_heartbeat.last_heartbeat == initial_heartbeat, "Should record heartbeat time"
        assert state_after_heartbeat.is_healthy(), "Connection should be healthy after heartbeat"
        
        # Simulate missed heartbeats (connection health degradation)
        time.sleep(0.1)  # Small delay to simulate time passage
        expired_threshold = initial_heartbeat + 30  # 30 second threshold
        
        with patch('time.time', return_value=expired_threshold + 1):
            health_status = manager.check_connection_health(connection_id)
            
            # Assert: Connection marked as unhealthy after missed heartbeats
            assert not health_status["is_healthy"], "Connection should be unhealthy after missed heartbeats"
            assert health_status["seconds_since_heartbeat"] > 30, "Should track time since last heartbeat"
            
            # Business requirement: Unhealthy connections trigger cleanup
            assert health_status["requires_cleanup"], "Unhealthy connections should trigger cleanup"

    @pytest.mark.unit
    def test_connection_cleanup_lifecycle(self):
        """
        Test WebSocket connection cleanup lifecycle for resource management.
        
        Business Value: Proper connection cleanup prevents resource leaks and maintains
        system stability for continuous chat service availability.
        """
        # Arrange: Multiple connections for cleanup testing
        manager = WebSocketManager()
        connections = []
        
        for i in range(5):
            user_id = UserID(f"cleanup_user_{i}")
            connection_id = ConnectionID(str(uuid.uuid4()))
            mock_websocket = Mock()
            mock_websocket.client_state = Mock()
            mock_websocket.client_state.value = 1  # OPEN state
            
            connection_state = manager.create_connection_state(
                user_id=user_id,
                connection_id=connection_id,
                websocket=mock_websocket
            )
            
            manager.mark_connection_established(connection_id)
            connections.append((user_id, connection_id, connection_state))
        
        # Verify all connections established
        assert manager.get_connection_count() == 5, "Should have 5 active connections"
        
        # Act: Cleanup individual connection
        user_id_1, connection_id_1, _ = connections[0]
        cleanup_result = manager.cleanup_connection(connection_id_1)
        
        # Assert: Individual connection cleaned up
        assert cleanup_result["success"], "Individual cleanup should succeed"
        assert cleanup_result["connection_removed"], "Connection should be removed"
        assert manager.get_connection_count() == 4, "Should have 4 connections after individual cleanup"
        
        # Verify connection no longer accessible
        cleaned_state = manager.get_connection_state(connection_id_1)
        assert cleaned_state is None, "Cleaned connection should not be accessible"
        
        # Act: Cleanup all connections for a user (simulate user logout)
        user_id_2, connection_id_2, _ = connections[1]
        user_cleanup_result = manager.cleanup_user_connections(user_id_2)
        
        # Assert: User connections cleaned up
        assert user_cleanup_result["success"], "User cleanup should succeed"
        assert user_cleanup_result["connections_removed"] >= 1, "Should remove user connections"
        
        # Act: System-wide cleanup (simulate shutdown)
        system_cleanup_result = manager.cleanup_all_connections()
        
        # Assert: System-wide cleanup
        assert system_cleanup_result["success"], "System cleanup should succeed"
        assert system_cleanup_result["total_connections_removed"] >= 3, "Should clean remaining connections"
        assert manager.get_connection_count() == 0, "Should have no connections after system cleanup"
        
        # Business requirement: Clean system state after cleanup
        assert manager.get_active_users() == [], "Should have no active users after cleanup"

    @pytest.mark.unit
    def test_connection_state_transitions(self):
        """
        Test WebSocket connection state transition lifecycle.
        
        Business Value: Proper state management ensures users receive appropriate
        feedback about their connection status during chat interactions.
        """
        # Arrange: Connection for state transition testing
        manager = WebSocketManager()
        user_id = UserID("state_user")
        connection_id = ConnectionID(str(uuid.uuid4()))
        
        mock_websocket = Mock()
        mock_websocket.client_state = Mock()
        mock_websocket.client_state.value = 1  # OPEN state
        
        # Act & Assert: Test complete state transition lifecycle
        
        # 1. Initial state: CONNECTING
        connection_state = manager.create_connection_state(
            user_id=user_id,
            connection_id=connection_id,
            websocket=mock_websocket
        )
        assert connection_state.status == ConnectionStatus.CONNECTING
        
        # 2. Transition to: CONNECTED
        manager.mark_connection_established(connection_id)
        state = manager.get_connection_state(connection_id)
        assert state.status == ConnectionStatus.CONNECTED
        assert state.can_receive_messages(), "Connected state should allow message receipt"
        
        # 3. Transition to: RECONNECTING (simulated network issue)
        manager.mark_connection_reconnecting(connection_id, reason="network_interruption")
        state = manager.get_connection_state(connection_id)
        assert state.status == ConnectionStatus.RECONNECTING
        assert not state.can_send_messages(), "Reconnecting state should block message sending"
        
        # 4. Transition back to: CONNECTED (successful reconnection)
        manager.mark_connection_established(connection_id)
        state = manager.get_connection_state(connection_id)
        assert state.status == ConnectionStatus.CONNECTED
        assert state.can_send_messages(), "Reconnected state should restore message sending"
        
        # 5. Transition to: DISCONNECTING (graceful shutdown)
        manager.mark_connection_disconnecting(connection_id, reason="user_logout")
        state = manager.get_connection_state(connection_id)
        assert state.status == ConnectionStatus.DISCONNECTING
        
        # 6. Final state: DISCONNECTED
        manager.mark_connection_disconnected(connection_id)
        state = manager.get_connection_state(connection_id)
        assert state.status == ConnectionStatus.DISCONNECTED
        assert not state.is_active(), "Disconnected state should not be active"
        
        # Business requirement: State transitions enable proper user feedback
        state_history = manager.get_connection_state_history(connection_id)
        expected_states = [
            ConnectionStatus.CONNECTING,
            ConnectionStatus.CONNECTED,
            ConnectionStatus.RECONNECTING,
            ConnectionStatus.CONNECTED,
            ConnectionStatus.DISCONNECTING,
            ConnectionStatus.DISCONNECTED
        ]
        
        assert len(state_history) == len(expected_states), "Should track all state transitions"
        for i, expected_status in enumerate(expected_states):
            assert state_history[i]["status"] == expected_status, f"State {i} should be {expected_status}"

    @pytest.mark.unit
    def test_connection_error_handling_lifecycle(self):
        """
        Test WebSocket connection error handling throughout lifecycle.
        
        Business Value: Robust error handling ensures users maintain chat capabilities
        even when network issues or system errors occur.
        """
        # Arrange: Connection with error simulation capabilities
        manager = WebSocketManager()
        user_id = UserID("error_user")
        connection_id = ConnectionID(str(uuid.uuid4()))
        
        mock_websocket = Mock()
        mock_websocket.client_state = Mock()
        mock_websocket.client_state.value = 1  # OPEN state
        
        connection_state = manager.create_connection_state(
            user_id=user_id,
            connection_id=connection_id,
            websocket=mock_websocket
        )
        
        manager.mark_connection_established(connection_id)
        
        # Act: Test various error scenarios
        
        # 1. Network error during message send
        network_error = ConnectionError("Network unreachable")
        error_result = manager.handle_connection_error(
            connection_id,
            error=network_error,
            error_type="network"
        )
        
        # Assert: Network error handled gracefully
        assert error_result["error_handled"], "Network error should be handled"
        assert error_result["connection_preserved"], "Connection should be preserved for retry"
        
        state = manager.get_connection_state(connection_id)
        assert state.status == ConnectionStatus.RECONNECTING, "Should transition to reconnecting"
        assert state.error_count > 0, "Should track error count"
        
        # 2. Protocol error (malformed message)
        protocol_error = ValueError("Invalid message format")
        error_result = manager.handle_connection_error(
            connection_id,
            error=protocol_error,
            error_type="protocol"
        )
        
        # Assert: Protocol error handled with validation
        assert error_result["error_handled"], "Protocol error should be handled"
        assert error_result["validation_enabled"], "Should enable stricter validation"
        
        # 3. Critical system error (requires disconnection)
        critical_error = RuntimeError("System resource exhausted")
        error_result = manager.handle_connection_error(
            connection_id,
            error=critical_error,
            error_type="critical"
        )
        
        # Assert: Critical error triggers disconnection
        assert error_result["error_handled"], "Critical error should be handled"
        assert error_result["connection_terminated"], "Critical error should terminate connection"
        
        state = manager.get_connection_state(connection_id)
        assert state.status == ConnectionStatus.DISCONNECTED, "Critical error should disconnect"
        
        # Business requirement: Error recovery maintains service availability
        error_history = manager.get_connection_error_history(connection_id)
        assert len(error_history) == 3, "Should track all error events"
        assert error_history[-1]["error_type"] == "critical", "Should record critical error"

    @pytest.mark.unit
    def test_connection_resource_lifecycle_management(self):
        """
        Test WebSocket connection resource lifecycle for memory and performance.
        
        Business Value: Efficient resource management ensures chat service can scale
        to handle enterprise-level concurrent user loads without performance degradation.
        """
        # Arrange: Resource monitoring setup
        manager = WebSocketManager()
        resource_limits = {
            "max_connections_per_user": 3,
            "max_total_connections": 100,
            "memory_limit_mb": 50,
            "message_queue_limit": 1000
        }
        
        manager.configure_resource_limits(resource_limits)
        
        # Act: Test resource lifecycle patterns
        
        # 1. Test connection limit enforcement
        user_id = UserID("resource_user")
        user_connections = []
        
        # Create connections up to limit
        for i in range(3):
            connection_id = ConnectionID(str(uuid.uuid4()))
            mock_websocket = Mock()
            mock_websocket.client_state = Mock()
            mock_websocket.client_state.value = 1
            
            connection_state = manager.create_connection_state(
                user_id=user_id,
                connection_id=connection_id,
                websocket=mock_websocket
            )
            
            user_connections.append(connection_id)
            manager.mark_connection_established(connection_id)
        
        # Attempt to exceed limit
        excess_connection_id = ConnectionID(str(uuid.uuid4()))
        mock_websocket_excess = Mock()
        mock_websocket_excess.client_state = Mock()
        mock_websocket_excess.client_state.value = 1
        
        try:
            excess_connection = manager.create_connection_state(
                user_id=user_id,
                connection_id=excess_connection_id,
                websocket=mock_websocket_excess
            )
            # Should not reach here due to limit enforcement
            assert False, "Should reject connection exceeding user limit"
        except ValueError as e:
            assert "connection limit exceeded" in str(e).lower()
        
        # 2. Test resource cleanup and recovery
        # Cleanup one connection to free resources
        cleanup_connection_id = user_connections[0]
        cleanup_result = manager.cleanup_connection(cleanup_connection_id)
        
        assert cleanup_result["success"], "Cleanup should succeed"
        assert cleanup_result["resources_freed"], "Should free connection resources"
        
        # Now excess connection should be allowed
        try:
            excess_connection = manager.create_connection_state(
                user_id=user_id,
                connection_id=excess_connection_id,
                websocket=mock_websocket_excess
            )
            assert excess_connection is not None, "Should allow connection after cleanup"
        except ValueError:
            assert False, "Should allow connection after resource cleanup"
        
        # 3. Test memory pressure handling
        with patch.object(manager, '_get_memory_usage', return_value=45):  # 45MB usage
            memory_status = manager.check_memory_pressure()
            assert not memory_status["memory_pressure"], "Should not have memory pressure at 45MB"
        
        with patch.object(manager, '_get_memory_usage', return_value=55):  # 55MB usage (over limit)
            memory_status = manager.check_memory_pressure()
            assert memory_status["memory_pressure"], "Should have memory pressure at 55MB"
            assert memory_status["cleanup_triggered"], "Should trigger cleanup under memory pressure"
        
        # Business requirement: Resource management enables scalability
        resource_metrics = manager.get_resource_metrics()
        assert resource_metrics["max_connections_supported"] >= 100, "Should support enterprise scale"
        assert resource_metrics["memory_efficiency"] > 0.8, "Should maintain memory efficiency"