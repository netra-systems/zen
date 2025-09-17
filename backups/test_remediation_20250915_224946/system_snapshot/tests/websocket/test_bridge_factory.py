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
        WebSocket Bridge Factory Unit Tests

        Business Value:
        - Ensures factory correctly creates per-user WebSocket emitters
        - Validates user isolation and event routing
        - Tests configuration and lifecycle management
        '''

        import asyncio
        import pytest
        from datetime import datetime, timezone
        import uuid
        import json
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.services.websocket_bridge_factory import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        WebSocketBridgeFactory,
        UserWebSocketEmitter,
        WebSocketConnectionPool,
        ConnectionStatus,
        EventPriority,
        EventType
        


class TestWebSocketBridgeFactory:
        """Unit tests for WebSocketBridgeFactory class."""

        @pytest.fixture
    def factory(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create a WebSocketBridgeFactory instance."""
        pass
        return WebSocketBridgeFactory()

        @pytest.fixture
    def real_pool():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create a mock connection pool."""
        pass
        pool = MagicMock(spec=WebSocketConnectionPool)
        pool.add_connection = AsyncMock(return_value="conn-123")
        pool.remove_connection = AsyncMock(return_value=True)
        pool.broadcast_to_user = AsyncMock(return_value=1)
        pool.get_active_connections = MagicMock(return_value=[])
        pool.cleanup_user_connections = AsyncMock(return_value=2)
        pool.get_pool_metrics = Magic        return pool

        @pytest.fixture
    def real_websocket():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create a mock WebSocket."""
        pass
        ws = Magic        ws.websocket = TestWebSocketConnection()
        ws.state = Magic        ws.state.name = "OPEN"
        return ws

    def test_factory_initialization(self, factory):
        """Test factory initialization."""
        assert factory.connection_pool is not None
        assert isinstance(factory.connection_pool, WebSocketConnectionPool)
        assert factory.user_emitters == {}
        assert factory.configuration is not None
        assert factory.monitor is not None

    def test_factory_singleton(self):
        """Test factory is a singleton."""
        pass
        factory1 = WebSocketBridgeFactory()
        factory2 = WebSocketBridgeFactory()
        assert factory1 is factory2

@pytest.mark.asyncio
    async def test_create_user_emitter(self, factory, mock_pool):
"""Test creating a user-specific emitter."""
factory.connection_pool = mock_pool
user_id = "user-123"
session_id = "session-456"

emitter = await factory.create_user_emitter( )
user_id=user_id,
session_id=session_id
        

assert emitter is not None
assert isinstance(emitter, UserWebSocketEmitter)
assert emitter.user_id == user_id
assert emitter.session_id == session_id
assert factory.user_emitters[user_id] == emitter

@pytest.mark.asyncio
    async def test_create_emitter_with_websocket(self, factory, mock_pool, mock_websocket):
"""Test creating emitter with WebSocket connection."""
pass
factory.connection_pool = mock_pool
user_id = "user-123"
session_id = "session-456"

emitter = await factory.create_user_emitter( )
user_id=user_id,
session_id=session_id,
websocket=mock_websocket
            

assert emitter is not None
mock_pool.add_connection.assert_called_once_with(user_id, mock_websocket)
assert emitter.connection_id == "conn-123"

@pytest.mark.asyncio
    async def test_get_existing_emitter(self, factory, mock_pool):
"""Test getting an existing emitter."""
factory.connection_pool = mock_pool
user_id = "user-123"
session_id = "session-456"

                # Create emitter
emitter1 = await factory.create_user_emitter(user_id, session_id)

                # Get existing emitter
emitter2 = factory.get_user_emitter(user_id)

assert emitter2 is emitter1

def test_get_nonexistent_emitter(self, factory):
"""Test getting non-existent emitter returns None."""
pass
emitter = factory.get_user_emitter("non-existent-user")
assert emitter is None

@pytest.mark.asyncio
    async def test_remove_user_emitter(self, factory, mock_pool):
"""Test removing a user emitter."""
factory.connection_pool = mock_pool
user_id = "user-123"
session_id = "session-456"

        # Create emitter
emitter = await factory.create_user_emitter(user_id, session_id)

        # Remove emitter
removed = await factory.remove_user_emitter(user_id)

assert removed is True
assert user_id not in factory.user_emitters
mock_pool.cleanup_user_connections.assert_called_once_with(user_id)

@pytest.mark.asyncio
    async def test_remove_nonexistent_emitter(self, factory, mock_pool):
"""Test removing non-existent emitter."""
pass
factory.connection_pool = mock_pool
removed = await factory.remove_user_emitter("non-existent-user")

assert removed is False
mock_pool.cleanup_user_connections.assert_not_called()

@pytest.mark.asyncio
    async def test_broadcast_to_user(self, factory, mock_pool):
"""Test broadcasting event to user."""
factory.connection_pool = mock_pool
user_id = "user-123"

                # Create emitter
await factory.create_user_emitter(user_id, "session-456")

                # Broadcast event
event = { )
"type": "agent_started",
"data": {"agent": "test"}
                

success = await factory.broadcast_to_user(user_id, event)

assert success is True
mock_pool.broadcast_to_user.assert_called_once()

@pytest.mark.asyncio
    async def test_broadcast_to_nonexistent_user(self, factory, mock_pool):
"""Test broadcasting to non-existent user."""
pass
factory.connection_pool = mock_pool

event = {"type": "test"}
success = await factory.broadcast_to_user("non-existent-user", event)

assert success is False
mock_pool.broadcast_to_user.assert_not_called()

@pytest.mark.asyncio
    async def test_cleanup_inactive_emitters(self, factory, mock_pool):
"""Test cleaning up inactive emitters."""
factory.connection_pool = mock_pool

                        # Create multiple emitters
user1 = "user-123"
user2 = "user-456"

emitter1 = await factory.create_user_emitter(user1, "session-1")
emitter2 = await factory.create_user_emitter(user2, "session-2")

                        # Mark emitter1 as inactive
emitter1.is_active = False
mock_pool.get_active_connections.return_value = []

                        # Cleanup inactive
cleaned = await factory.cleanup_inactive_emitters()

assert cleaned == 1
assert user1 not in factory.user_emitters
assert user2 in factory.user_emitters

def test_get_factory_metrics(self, factory):
"""Test getting factory metrics."""
pass
metrics = factory.get_factory_metrics()

assert "total_emitters" in metrics
assert "active_emitters" in metrics
assert "connection_pool" in metrics
assert metrics["total_emitters"] == 0

@pytest.mark.asyncio
    async def test_factory_with_multiple_users(self, factory, mock_pool):
"""Test factory handles multiple users correctly."""
factory.connection_pool = mock_pool

users = ["user-1", "user-2", "user-3"]
emitters = []

        # Create emitters for multiple users
for user_id in users:
emitter = await factory.create_user_emitter( )
user_id=user_id,
session_id="formatted_string"
            
emitters.append(emitter)

            # Verify all emitters are tracked
assert len(factory.user_emitters) == 3

            # Verify each user has unique emitter
for i, user_id in enumerate(users):
assert factory.get_user_emitter(user_id) == emitters[i]

@pytest.mark.asyncio
    async def test_factory_error_handling(self, factory):
"""Test factory error handling."""
pass
                    # Mock pool to raise error
mock_pool = MagicMock(spec=WebSocketConnectionPool)
mock_pool.add_connection = AsyncMock(side_effect=Exception("Connection failed"))
factory.connection_pool = mock_pool

user_id = "user-123"

                    # Should handle error gracefully
emitter = await factory.create_user_emitter(user_id, "session-456")

                    # Emitter should still be created but without connection
assert emitter is not None
assert emitter.user_id == user_id
assert emitter.connection_id is None

@pytest.mark.asyncio
    async def test_configure_factory(self, factory):
"""Test factory configuration."""
config = { )
"max_queue_size": 1000,
"batch_size": 50,
"flush_interval": 0.5,
"retry_attempts": 5,
"health_check_interval": 10
                        

factory.configure(config)

assert factory.configuration["max_queue_size"] == 1000
assert factory.configuration["batch_size"] == 50
assert factory.configuration["retry_attempts"] == 5

@pytest.mark.asyncio
    async def test_factory_health_check(self, factory, mock_pool):
"""Test factory health check."""
pass
factory.connection_pool = mock_pool

                            # Add some emitters
await factory.create_user_emitter("user-1", "session-1")
await factory.create_user_emitter("user-2", "session-2")

                            # Mock pool metrics
pool_metrics = Magic        pool_metrics.healthy_connections = 2
pool_metrics.unhealthy_connections = 0
mock_pool.get_pool_metrics.return_value = pool_metrics

                            # Check health
health = await factory.check_health()

assert health["status"] == "healthy"
assert health["emitter_count"] == 2
assert health["pool_health"]["healthy_connections"] == 2


class TestUserWebSocketEmitter:
    """Unit tests for UserWebSocketEmitter class."""

    @pytest.fixture
    def real_pool():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create a mock connection pool."""
        pass
        pool = MagicMock(spec=WebSocketConnectionPool)
        pool.broadcast_to_user = AsyncMock(return_value=1)
        pool.get_active_connections = MagicMock(return_value=[])
        await asyncio.sleep(0)
        return pool

        @pytest.fixture
    def emitter(self, mock_pool):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create a UserWebSocketEmitter instance."""
        pass
        return UserWebSocketEmitter( )
        user_id="user-123",
        session_id="session-456",
        connection_pool=mock_pool
    

    def test_emitter_initialization(self, emitter):
        """Test emitter initialization."""
        assert emitter.user_id == "user-123"
        assert emitter.session_id == "session-456"
        assert emitter.is_active is True
        assert emitter.connection_id is None
        assert len(emitter.event_queue) == 0
        assert emitter.metrics["events_sent"] == 0
        assert emitter.metrics["events_failed"] == 0

@pytest.mark.asyncio
    async def test_emit_event(self, emitter, mock_pool):
"""Test emitting an event."""
pass
event = { )
"type": "agent_started",
"data": {"agent": "test"}
        

success = await emitter.emit(event)

assert success is True
mock_pool.broadcast_to_user.assert_called_once()
assert emitter.metrics["events_sent"] == 1

@pytest.mark.asyncio
    async def test_emit_with_priority(self, emitter, mock_pool):
"""Test emitting event with priority."""
event = { )
"type": "error",
"data": {"message": "Critical error"}
            

success = await emitter.emit(event, priority=EventPriority.HIGH)

assert success is True
            # High priority events should be sent immediately
mock_pool.broadcast_to_user.assert_called_once()

@pytest.mark.asyncio
    async def test_queue_event(self, emitter):
"""Test queueing events."""
pass
event1 = {"type": "test1"}
event2 = {"type": "test2"}

emitter.queue_event(event1)
emitter.queue_event(event2)

assert len(emitter.event_queue) == 2
assert emitter.metrics["events_queued"] == 2

@pytest.mark.asyncio
    async def test_flush_queue(self, emitter, mock_pool):
"""Test flushing event queue."""
                    # Queue some events
events = [ )
{"type": "formatted_string"} for i in range(5)
                    
for event in events:
emitter.queue_event(event)

                        # Flush queue
flushed = await emitter.flush_queue()

assert flushed == 5
assert len(emitter.event_queue) == 0
assert mock_pool.broadcast_to_user.call_count == 5

@pytest.mark.asyncio
    async def test_batch_processing(self, emitter, mock_pool):
"""Test batch event processing."""
pass
                            # Configure for batching
emitter.batch_size = 3

                            # Queue many events
for i in range(10):
emitter.queue_event({"type": "formatted_string"})

                                # Process batch
processed = await emitter.process_batch()

assert processed == 3  # Should process batch_size events
assert len(emitter.event_queue) == 7  # Remaining events
assert mock_pool.broadcast_to_user.call_count == 3

@pytest.mark.asyncio
    async def test_emit_handles_errors(self, emitter, mock_pool):
"""Test emit handles broadcast errors."""
mock_pool.broadcast_to_user.side_effect = Exception("Send failed")

event = {"type": "test"}
success = await emitter.emit(event)

assert success is False
assert emitter.metrics["events_failed"] == 1

@pytest.mark.asyncio
    async def test_sanitize_event(self, emitter):
"""Test event sanitization."""
pass
event = { )
"type": "agent_thinking",
"data": { )
"thought": "Using API key: sk-12345",
"plan": "Process data"
                                        
                                        

sanitized = emitter.sanitize_event(event)

                                        # Should remove sensitive data
assert "sk-12345" not in str(sanitized)

def test_inactive_emitter(self, emitter):
"""Test inactive emitter behavior."""
emitter.is_active = False

    # Should not queue events when inactive
emitter.queue_event({"type": "test"})
assert len(emitter.event_queue) == 0

@pytest.mark.asyncio
    async def test_connection_management(self, emitter):
"""Test connection ID management."""
pass
        # Set connection ID
emitter.set_connection_id("conn-123")
assert emitter.connection_id == "conn-123"

        # Clear connection ID
emitter.clear_connection_id()
assert emitter.connection_id is None

def test_get_metrics(self, emitter):
"""Test getting emitter metrics."""
emitter.metrics["events_sent"] = 10
emitter.metrics["events_failed"] = 2
emitter.metrics["events_queued"] = 5

metrics = emitter.get_metrics()

assert metrics["events_sent"] == 10
assert metrics["events_failed"] == 2
assert metrics["events_queued"] == 5
assert metrics["user_id"] == "user-123"
assert metrics["session_id"] == "session-456"

@pytest.mark.asyncio
    async def test_lifecycle_events(self, emitter, mock_pool):
"""Test lifecycle event emissions."""
pass
        # Start event
await emitter.emit_lifecycle_event("started")

        # Complete event
await emitter.emit_lifecycle_event("completed", {"result": "success"})

assert mock_pool.broadcast_to_user.call_count == 2

        # Verify event structure
calls = mock_pool.broadcast_to_user.call_args_list
start_event = calls[0][0][1]
complete_event = calls[1][0][1]

assert start_event["type"] == "lifecycle_started"
assert complete_event["type"] == "lifecycle_completed"
assert complete_event["data"]["result"] == "success"
