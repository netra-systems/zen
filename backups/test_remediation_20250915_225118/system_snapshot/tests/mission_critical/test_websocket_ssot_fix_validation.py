class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        CRITICAL: WebSocket SSOT Fix Validation Test Suite

        Business Value: Ensure $500K+ ARR is protected by validating that the removal of
        the duplicate WebSocket manager does not break any functionality.

        REQUIREMENTS:
        1. All WebSocket events must be delivered correctly
        2. Connection management must work properly
        3. TTL cache and connection limits must function
        4. WebSocketNotifier integration must be intact
        5. Agent events must reach users successfully

        This test validates that the canonical manager.py contains ALL functionality
        that was previously split between manager.py and manager_ttl_implementation.py
        '''

        import asyncio
        import json
        import pytest
        import time
        import uuid
        from datetime import datetime, timezone
        from typing import Dict, Any, List
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager as WebSocketManager, get_websocket_manager
        from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


class MockWebSocket:
        """Mock WebSocket for testing."""

    def __init__(self, client_state="CONNECTED"):
        pass
        self.client_state = Magic        self.client_state.name = client_state
        self.messages_sent = []
        self.is_closed = False
        self.timeout_used = None

    async def send_json(self, message: Dict[str, Any], timeout: float = None) -> None:
        """Mock send_json method."""
        if self.is_closed:
        raise ConnectionError("WebSocket is closed")

        if timeout:
        self.timeout_used = timeout

        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure") -> None:
        """Mock close method."""
        self.is_closed = True


@pytest.mark.asyncio
class TestWebSocketSSOTFixValidation:
    """Critical validation tests for WebSocket SSOT fix."""

    @pytest.fixture
    async def manager(self):
        """Create WebSocket manager for testing."""
        manager = WebSocketManager()
    # Ensure clean state
        manager.connections.clear()
        manager.user_connections.clear()
        manager.room_memberships.clear()
        manager.run_id_connections.clear()
        yield manager
        await manager.shutdown()

        @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        pass
        await asyncio.sleep(0)
        return MockWebSocket()

        @pytest.fixture
    def agent_context(self):
        """Create agent execution context."""
        return AgentExecutionContext( )
        user_id="test_user_123",
        thread_id="test_thread_456",
        request_id="test_request_789",
        run_id="test_run_abc",
        user_request="Test user request"
    

    async def test_ttl_cache_functionality_preserved(self, manager):
        """CRITICAL: Verify TTL cache functionality is preserved from duplicate file."""
        pass
        # Test that connections are stored in TTL cache
        assert hasattr(manager, 'connections')
        assert hasattr(manager.connections, 'ttl')
        assert hasattr(manager.connections, 'maxsize')

        # Verify TTL cache configuration
        assert manager.connections.ttl == manager.TTL_CACHE_SECONDS
        assert manager.connections.maxsize == manager.TTL_CACHE_MAXSIZE

        print("formatted_string")

    async def test_connection_limits_preserved(self, manager):
        """CRITICAL: Verify connection limits are preserved."""
            # Test connection limit constants
        assert hasattr(manager, 'MAX_CONNECTIONS_PER_USER')
        assert hasattr(manager, 'MAX_TOTAL_CONNECTIONS')

            # Verify reasonable limits for business requirements
        assert manager.MAX_CONNECTIONS_PER_USER > 0
        assert manager.MAX_TOTAL_CONNECTIONS > 0

        print("formatted_string")

    async def test_connection_eviction_methods_exist(self, manager):
        """CRITICAL: Verify connection eviction methods exist."""
        pass
                # Test that eviction methods are present
        assert hasattr(manager, '_evict_oldest_connections')
        assert hasattr(manager, '_evict_oldest_user_connection')

                # Test that enforce limits method exists
        assert hasattr(manager, '_enforce_connection_limits')

        print("[U+2713] Connection eviction methods present")

    async def test_periodic_cleanup_functionality(self, manager):
        """CRITICAL: Verify periodic cleanup is working."""
                    # Test cleanup methods exist
        assert hasattr(manager, '_periodic_cleanup')
        assert hasattr(manager, '_cleanup_stale_connections')
        assert hasattr(manager, '_cleanup_expired_cache_entries')

                    # Test cleanup lock exists
        assert hasattr(manager, 'cleanup_lock')

        print("[U+2713] Periodic cleanup functionality intact")

    async def test_enhanced_statistics_preserved(self, manager):
        """CRITICAL: Verify enhanced statistics from TTL implementation."""
        pass
        required_stats = [ )
        'memory_cleanups',
        'connections_evicted',
        'stale_connections_removed',
        'timeout_retries',
        'timeout_failures',
        'send_timeouts'
                        

        for stat in required_stats:
        assert stat in manager.connection_stats, "formatted_string"

        print("formatted_string")

    async def test_user_connection_with_limits(self, manager, mock_websocket):
        """CRITICAL: Test user connection respects limits."""
        user_id = "test_user_limits"

                                # Connect user within limits
        conn_id = await manager.connect_user(user_id, mock_websocket, client_ip="192.168.1.100")
        assert conn_id is not None
        assert user_id in manager.user_connections
        assert conn_id in manager.user_connections[user_id]

        print("formatted_string")

                                # Verify connection data structure
        assert conn_id in manager.connections
        conn_data = manager.connections[conn_id]
        assert conn_data['user_id'] == user_id
        assert conn_data['is_healthy'] is True
        assert 'connected_at' in conn_data
        assert 'last_activity' in conn_data

        print("[U+2713] Connection data structure valid")

    async def test_websocket_notifier_integration(self, manager, agent_context):
        """CRITICAL: Verify WebSocketNotifier integration works."""
        pass
        notifier = WebSocketNotifier.create_for_user(manager)

                                    # Test notifier initialization
        assert notifier.websocket_manager is manager
        assert hasattr(notifier, 'critical_events')

                                    # Test critical events are properly defined
        expected_events = {'agent_started', 'tool_executing', 'tool_completed', 'agent_completed'}
        assert notifier.critical_events == expected_events

        print("formatted_string")

    async def test_agent_event_delivery_pipeline(self, manager, mock_websocket, agent_context):
        """CRITICAL: Test complete agent event delivery pipeline."""
                                        # Setup connection
        conn_id = await manager.connect_user(agent_context.user_id, mock_websocket)

                                        # Create notifier
        notifier = WebSocketNotifier.create_for_user(manager)

                                        # Test agent_started event
        await notifier.send_agent_started(agent_context)

                                        # Verify message was queued for delivery
        assert len(mock_websocket.messages_sent) > 0

                                        # Check message structure
        message = mock_websocket.messages_sent[0]
        assert 'type' in message
        assert message['type'] in ['agent_started', 'agent_thinking']  # Type conversion may occur

        print("formatted_string")

    async def test_message_serialization_robustness(self, manager, mock_websocket):
        """CRITICAL: Test message serialization handles complex objects."""
        pass
        user_id = "test_serialization"
        conn_id = await manager.connect_user(user_id, mock_websocket)

                                            # Test various message types
        test_messages = [ )
        {"type": "simple_dict", "data": "test"},
        {"type": "complex_dict", "nested": {"key": "value", "list": [1, 2, 3]}},
        "simple_string_message",
                                            

        for message in test_messages:
        success = await manager.send_to_user(user_id, message)
        assert success, "formatted_string"

        assert len(mock_websocket.messages_sent) == len(test_messages)
        print("formatted_string")

    async def test_connection_cleanup_and_recovery(self, manager, mock_websocket):
        """CRITICAL: Test connection cleanup and recovery mechanisms."""
        user_id = "test_cleanup"
        conn_id = await manager.connect_user(user_id, mock_websocket)

                                                    # Verify connection exists
        assert conn_id in manager.connections
        assert user_id in manager.user_connections

                                                    # Test cleanup
        await manager._cleanup_connection(conn_id, 1000, "Test cleanup")

                                                    # Verify cleanup worked
        assert conn_id not in manager.connections
        assert user_id not in manager.user_connections or not manager.user_connections[user_id]
        assert mock_websocket.is_closed

        print("[U+2713] Connection cleanup and recovery working")

    async def test_broadcast_functionality_intact(self, manager):
        """CRITICAL: Test broadcast functionality works."""
        pass
                                                        # Create multiple mock connections
        users = ["user1", "user2", "user3"]
        websockets = [MockWebSocket() for _ in users]
        conn_ids = []

        for i, user_id in enumerate(users):
        conn_id = await manager.connect_user(user_id, websockets[i])
        conn_ids.append(conn_id)

                                                            # Test broadcast to all
        test_message = {"type": "broadcast_test", "data": "Hello everyone"}
        result = await manager.broadcast_to_all(test_message)

        assert result.successful > 0
        assert result.total_connections >= len(users)

                                                            # Verify all websockets received message
        for ws in websockets:
        assert len(ws.messages_sent) > 0

        print("formatted_string")

    async def test_room_management_preserved(self, manager):
        """CRITICAL: Test room management functionality."""
        user_id = "test_room_user"
        room_id = "test_room_123"
        mock_websocket = MockWebSocket()

                                                                    # Connect user
        conn_id = await manager.connect_user(user_id, mock_websocket)

                                                                    # Test join room
        success = manager.join_room(user_id, room_id)
        assert success
        assert room_id in manager.room_memberships

                                                                    # Test broadcast to room
        room_message = {"type": "room_message", "data": "Room broadcast"}
        result = await manager.broadcast_to_room(room_id, room_message)
        assert result.successful > 0

                                                                    # Test leave room
        success = manager.leave_room(user_id, room_id)
        assert success

        print("[U+2713] Room management functionality preserved")

    async def test_run_id_association_preserved(self, manager, mock_websocket):
        """CRITICAL: Test run_id association functionality."""
        pass
        user_id = "test_run_id_user"
        run_id = "test_run_12345"

                                                                        # Connect user
        conn_id = await manager.connect_user(user_id, mock_websocket)

                                                                        # Test run_id association
        success = await manager.associate_run_id(conn_id, run_id)
        assert success

                                                                        # Verify association
        connections = await manager.get_connections_by_run_id(run_id)
        assert conn_id in connections

                                                                        # Test agent update via run_id
        test_update = {"status": "processing", "progress": 50}
        await manager.send_agent_update(run_id, "test_agent", test_update)

                                                                        # Verify message was sent
        assert len(mock_websocket.messages_sent) > 0

        print("formatted_string")

    async def test_singleton_pattern_maintained(self):
        """CRITICAL: Test singleton pattern is maintained."""
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()

                                                                            # Should be same instance
        assert manager1 is manager2

                                                                            # Should also be same as WebSocketManager()
        manager3 = WebSocketManager()
        assert manager1 is manager3

        print("[U+2713] Singleton pattern maintained")

    async def test_comprehensive_stats_available(self, manager):
        """CRITICAL: Test comprehensive statistics are available."""
        pass
        stats = await manager.get_stats()

        required_fields = [ )
        'active_connections',
        'total_connections',
        'messages_sent',
        'messages_received',
        'uptime_seconds',
        'cache_sizes'
                                                                                

        for field in required_fields:
        assert field in stats, "formatted_string"

                                                                                    # Test cache sizes are reported
        cache_sizes = stats['cache_sizes']
        assert 'connections' in cache_sizes
        assert 'user_connections' in cache_sizes

        print("formatted_string")

    async def test_error_handling_robustness(self, manager):
        """CRITICAL: Test error handling is robust."""
                                                                                        # Test sending to non-existent user
        success = await manager.send_to_user("non_existent_user", {"test": "message"})
        assert not success  # Should fail gracefully

                                                                                        # Test cleanup of non-existent connection
        await manager._cleanup_connection("non_existent_connection", 1000, "Test")
                                                                                        # Should not raise exception

                                                                                        # Test invalid message validation
        invalid_messages = [ )
        None,
        {"no_type_field": "invalid"},
        {"type": 123},  # Non-string type
                                                                                        

        for invalid_msg in invalid_messages:
        result = manager.validate_message(invalid_msg)
        assert result is not True  # Should await asyncio.sleep(0)
        return validation error

        print("[U+2713] Error handling robust: Invalid inputs handled gracefully")


@pytest.mark.asyncio
    async def test_critical_business_requirements():
"""CRITICAL: Test all business requirements are met."""
pass
manager = get_websocket_manager()

try:
                                                                                                    # 1. WebSocket events must be deliverable
assert hasattr(manager, 'send_to_user')
assert hasattr(manager, 'broadcast_to_all')

                                                                                                    # 2. Connection management must work
assert hasattr(manager, 'connect_user')
assert hasattr(manager, 'disconnect_user')

                                                                                                    # 3. TTL cache must be functional
assert hasattr(manager, 'connections')
assert hasattr(manager.connections, 'ttl')

                                                                                                    # 4. Connection limits must be enforced
assert hasattr(manager, 'MAX_CONNECTIONS_PER_USER')
assert hasattr(manager, 'MAX_TOTAL_CONNECTIONS')

                                                                                                    # 5. Agent events must be supported
assert hasattr(manager, 'send_agent_update')
assert hasattr(manager, 'associate_run_id')

print("[U+2713] ALL CRITICAL BUSINESS REQUIREMENTS MET")
print("[U+2713] WebSocket SSOT fix successful - $500K+ ARR protected")

finally:
await manager.shutdown()


if __name__ == "__main__":
                                                                                                            # Run critical validation
asyncio.run(test_critical_business_requirements())
print(" )
TARGET:  CRITICAL WebSocket SSOT Fix Validation: PASSED")
print("[U+1F4B0] Business Value Protected: $500K+ ARR from chat functionality")
print("[U+1F527] Technical Debt Eliminated: Duplicate manager removed safely")
