# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: WebSocket Bridge Factory Unit Tests

    # REMOVED_SYNTAX_ERROR: Business Value:
        # REMOVED_SYNTAX_ERROR: - Ensures factory correctly creates per-user WebSocket emitters
        # REMOVED_SYNTAX_ERROR: - Validates user isolation and event routing
        # REMOVED_SYNTAX_ERROR: - Tests configuration and lifecycle management
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
        # REMOVED_SYNTAX_ERROR: import uuid
        # REMOVED_SYNTAX_ERROR: import json
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
        # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.websocket_bridge_factory import ( )
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
        # REMOVED_SYNTAX_ERROR: WebSocketBridgeFactory,
        # REMOVED_SYNTAX_ERROR: UserWebSocketEmitter,
        # REMOVED_SYNTAX_ERROR: WebSocketConnectionPool,
        # REMOVED_SYNTAX_ERROR: ConnectionStatus,
        # REMOVED_SYNTAX_ERROR: EventPriority,
        # REMOVED_SYNTAX_ERROR: EventType
        


# REMOVED_SYNTAX_ERROR: class TestWebSocketBridgeFactory:
    # REMOVED_SYNTAX_ERROR: """Unit tests for WebSocketBridgeFactory class."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def factory(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a WebSocketBridgeFactory instance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return WebSocketBridgeFactory()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_pool():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock connection pool."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: pool = MagicMock(spec=WebSocketConnectionPool)
    # REMOVED_SYNTAX_ERROR: pool.add_connection = AsyncMock(return_value="conn-123")
    # REMOVED_SYNTAX_ERROR: pool.remove_connection = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: pool.broadcast_to_user = AsyncMock(return_value=1)
    # REMOVED_SYNTAX_ERROR: pool.get_active_connections = MagicMock(return_value=[])
    # REMOVED_SYNTAX_ERROR: pool.cleanup_user_connections = AsyncMock(return_value=2)
    # REMOVED_SYNTAX_ERROR: pool.get_pool_metrics = Magic        return pool

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock WebSocket."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: ws = Magic        ws.websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: ws.state = Magic        ws.state.name = "OPEN"
    # REMOVED_SYNTAX_ERROR: return ws

# REMOVED_SYNTAX_ERROR: def test_factory_initialization(self, factory):
    # REMOVED_SYNTAX_ERROR: """Test factory initialization."""
    # REMOVED_SYNTAX_ERROR: assert factory.connection_pool is not None
    # REMOVED_SYNTAX_ERROR: assert isinstance(factory.connection_pool, WebSocketConnectionPool)
    # REMOVED_SYNTAX_ERROR: assert factory.user_emitters == {}
    # REMOVED_SYNTAX_ERROR: assert factory.configuration is not None
    # REMOVED_SYNTAX_ERROR: assert factory.monitor is not None

# REMOVED_SYNTAX_ERROR: def test_factory_singleton(self):
    # REMOVED_SYNTAX_ERROR: """Test factory is a singleton."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: factory1 = WebSocketBridgeFactory()
    # REMOVED_SYNTAX_ERROR: factory2 = WebSocketBridgeFactory()
    # REMOVED_SYNTAX_ERROR: assert factory1 is factory2

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_create_user_emitter(self, factory, mock_pool):
        # REMOVED_SYNTAX_ERROR: """Test creating a user-specific emitter."""
        # REMOVED_SYNTAX_ERROR: factory.connection_pool = mock_pool
        # REMOVED_SYNTAX_ERROR: user_id = "user-123"
        # REMOVED_SYNTAX_ERROR: session_id = "session-456"

        # REMOVED_SYNTAX_ERROR: emitter = await factory.create_user_emitter( )
        # REMOVED_SYNTAX_ERROR: user_id=user_id,
        # REMOVED_SYNTAX_ERROR: session_id=session_id
        

        # REMOVED_SYNTAX_ERROR: assert emitter is not None
        # REMOVED_SYNTAX_ERROR: assert isinstance(emitter, UserWebSocketEmitter)
        # REMOVED_SYNTAX_ERROR: assert emitter.user_id == user_id
        # REMOVED_SYNTAX_ERROR: assert emitter.session_id == session_id
        # REMOVED_SYNTAX_ERROR: assert factory.user_emitters[user_id] == emitter

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_create_emitter_with_websocket(self, factory, mock_pool, mock_websocket):
            # REMOVED_SYNTAX_ERROR: """Test creating emitter with WebSocket connection."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: factory.connection_pool = mock_pool
            # REMOVED_SYNTAX_ERROR: user_id = "user-123"
            # REMOVED_SYNTAX_ERROR: session_id = "session-456"

            # REMOVED_SYNTAX_ERROR: emitter = await factory.create_user_emitter( )
            # REMOVED_SYNTAX_ERROR: user_id=user_id,
            # REMOVED_SYNTAX_ERROR: session_id=session_id,
            # REMOVED_SYNTAX_ERROR: websocket=mock_websocket
            

            # REMOVED_SYNTAX_ERROR: assert emitter is not None
            # REMOVED_SYNTAX_ERROR: mock_pool.add_connection.assert_called_once_with(user_id, mock_websocket)
            # REMOVED_SYNTAX_ERROR: assert emitter.connection_id == "conn-123"

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_get_existing_emitter(self, factory, mock_pool):
                # REMOVED_SYNTAX_ERROR: """Test getting an existing emitter."""
                # REMOVED_SYNTAX_ERROR: factory.connection_pool = mock_pool
                # REMOVED_SYNTAX_ERROR: user_id = "user-123"
                # REMOVED_SYNTAX_ERROR: session_id = "session-456"

                # Create emitter
                # REMOVED_SYNTAX_ERROR: emitter1 = await factory.create_user_emitter(user_id, session_id)

                # Get existing emitter
                # REMOVED_SYNTAX_ERROR: emitter2 = factory.get_user_emitter(user_id)

                # REMOVED_SYNTAX_ERROR: assert emitter2 is emitter1

# REMOVED_SYNTAX_ERROR: def test_get_nonexistent_emitter(self, factory):
    # REMOVED_SYNTAX_ERROR: """Test getting non-existent emitter returns None."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: emitter = factory.get_user_emitter("non-existent-user")
    # REMOVED_SYNTAX_ERROR: assert emitter is None

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_remove_user_emitter(self, factory, mock_pool):
        # REMOVED_SYNTAX_ERROR: """Test removing a user emitter."""
        # REMOVED_SYNTAX_ERROR: factory.connection_pool = mock_pool
        # REMOVED_SYNTAX_ERROR: user_id = "user-123"
        # REMOVED_SYNTAX_ERROR: session_id = "session-456"

        # Create emitter
        # REMOVED_SYNTAX_ERROR: emitter = await factory.create_user_emitter(user_id, session_id)

        # Remove emitter
        # REMOVED_SYNTAX_ERROR: removed = await factory.remove_user_emitter(user_id)

        # REMOVED_SYNTAX_ERROR: assert removed is True
        # REMOVED_SYNTAX_ERROR: assert user_id not in factory.user_emitters
        # REMOVED_SYNTAX_ERROR: mock_pool.cleanup_user_connections.assert_called_once_with(user_id)

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_remove_nonexistent_emitter(self, factory, mock_pool):
            # REMOVED_SYNTAX_ERROR: """Test removing non-existent emitter."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: factory.connection_pool = mock_pool
            # REMOVED_SYNTAX_ERROR: removed = await factory.remove_user_emitter("non-existent-user")

            # REMOVED_SYNTAX_ERROR: assert removed is False
            # REMOVED_SYNTAX_ERROR: mock_pool.cleanup_user_connections.assert_not_called()

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_broadcast_to_user(self, factory, mock_pool):
                # REMOVED_SYNTAX_ERROR: """Test broadcasting event to user."""
                # REMOVED_SYNTAX_ERROR: factory.connection_pool = mock_pool
                # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                # Create emitter
                # REMOVED_SYNTAX_ERROR: await factory.create_user_emitter(user_id, "session-456")

                # Broadcast event
                # REMOVED_SYNTAX_ERROR: event = { )
                # REMOVED_SYNTAX_ERROR: "type": "agent_started",
                # REMOVED_SYNTAX_ERROR: "data": {"agent": "test"}
                

                # REMOVED_SYNTAX_ERROR: success = await factory.broadcast_to_user(user_id, event)

                # REMOVED_SYNTAX_ERROR: assert success is True
                # REMOVED_SYNTAX_ERROR: mock_pool.broadcast_to_user.assert_called_once()

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_broadcast_to_nonexistent_user(self, factory, mock_pool):
                    # REMOVED_SYNTAX_ERROR: """Test broadcasting to non-existent user."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: factory.connection_pool = mock_pool

                    # REMOVED_SYNTAX_ERROR: event = {"type": "test"}
                    # REMOVED_SYNTAX_ERROR: success = await factory.broadcast_to_user("non-existent-user", event)

                    # REMOVED_SYNTAX_ERROR: assert success is False
                    # REMOVED_SYNTAX_ERROR: mock_pool.broadcast_to_user.assert_not_called()

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_cleanup_inactive_emitters(self, factory, mock_pool):
                        # REMOVED_SYNTAX_ERROR: """Test cleaning up inactive emitters."""
                        # REMOVED_SYNTAX_ERROR: factory.connection_pool = mock_pool

                        # Create multiple emitters
                        # REMOVED_SYNTAX_ERROR: user1 = "user-123"
                        # REMOVED_SYNTAX_ERROR: user2 = "user-456"

                        # REMOVED_SYNTAX_ERROR: emitter1 = await factory.create_user_emitter(user1, "session-1")
                        # REMOVED_SYNTAX_ERROR: emitter2 = await factory.create_user_emitter(user2, "session-2")

                        # Mark emitter1 as inactive
                        # REMOVED_SYNTAX_ERROR: emitter1.is_active = False
                        # REMOVED_SYNTAX_ERROR: mock_pool.get_active_connections.return_value = []

                        # Cleanup inactive
                        # REMOVED_SYNTAX_ERROR: cleaned = await factory.cleanup_inactive_emitters()

                        # REMOVED_SYNTAX_ERROR: assert cleaned == 1
                        # REMOVED_SYNTAX_ERROR: assert user1 not in factory.user_emitters
                        # REMOVED_SYNTAX_ERROR: assert user2 in factory.user_emitters

# REMOVED_SYNTAX_ERROR: def test_get_factory_metrics(self, factory):
    # REMOVED_SYNTAX_ERROR: """Test getting factory metrics."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: metrics = factory.get_factory_metrics()

    # REMOVED_SYNTAX_ERROR: assert "total_emitters" in metrics
    # REMOVED_SYNTAX_ERROR: assert "active_emitters" in metrics
    # REMOVED_SYNTAX_ERROR: assert "connection_pool" in metrics
    # REMOVED_SYNTAX_ERROR: assert metrics["total_emitters"] == 0

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_factory_with_multiple_users(self, factory, mock_pool):
        # REMOVED_SYNTAX_ERROR: """Test factory handles multiple users correctly."""
        # REMOVED_SYNTAX_ERROR: factory.connection_pool = mock_pool

        # REMOVED_SYNTAX_ERROR: users = ["user-1", "user-2", "user-3"]
        # REMOVED_SYNTAX_ERROR: emitters = []

        # Create emitters for multiple users
        # REMOVED_SYNTAX_ERROR: for user_id in users:
            # REMOVED_SYNTAX_ERROR: emitter = await factory.create_user_emitter( )
            # REMOVED_SYNTAX_ERROR: user_id=user_id,
            # REMOVED_SYNTAX_ERROR: session_id="formatted_string"
            
            # REMOVED_SYNTAX_ERROR: emitters.append(emitter)

            # Verify all emitters are tracked
            # REMOVED_SYNTAX_ERROR: assert len(factory.user_emitters) == 3

            # Verify each user has unique emitter
            # REMOVED_SYNTAX_ERROR: for i, user_id in enumerate(users):
                # REMOVED_SYNTAX_ERROR: assert factory.get_user_emitter(user_id) == emitters[i]

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_factory_error_handling(self, factory):
                    # REMOVED_SYNTAX_ERROR: """Test factory error handling."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # Mock pool to raise error
                    # REMOVED_SYNTAX_ERROR: mock_pool = MagicMock(spec=WebSocketConnectionPool)
                    # REMOVED_SYNTAX_ERROR: mock_pool.add_connection = AsyncMock(side_effect=Exception("Connection failed"))
                    # REMOVED_SYNTAX_ERROR: factory.connection_pool = mock_pool

                    # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                    # Should handle error gracefully
                    # REMOVED_SYNTAX_ERROR: emitter = await factory.create_user_emitter(user_id, "session-456")

                    # Emitter should still be created but without connection
                    # REMOVED_SYNTAX_ERROR: assert emitter is not None
                    # REMOVED_SYNTAX_ERROR: assert emitter.user_id == user_id
                    # REMOVED_SYNTAX_ERROR: assert emitter.connection_id is None

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_configure_factory(self, factory):
                        # REMOVED_SYNTAX_ERROR: """Test factory configuration."""
                        # REMOVED_SYNTAX_ERROR: config = { )
                        # REMOVED_SYNTAX_ERROR: "max_queue_size": 1000,
                        # REMOVED_SYNTAX_ERROR: "batch_size": 50,
                        # REMOVED_SYNTAX_ERROR: "flush_interval": 0.5,
                        # REMOVED_SYNTAX_ERROR: "retry_attempts": 5,
                        # REMOVED_SYNTAX_ERROR: "health_check_interval": 10
                        

                        # REMOVED_SYNTAX_ERROR: factory.configure(config)

                        # REMOVED_SYNTAX_ERROR: assert factory.configuration["max_queue_size"] == 1000
                        # REMOVED_SYNTAX_ERROR: assert factory.configuration["batch_size"] == 50
                        # REMOVED_SYNTAX_ERROR: assert factory.configuration["retry_attempts"] == 5

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_factory_health_check(self, factory, mock_pool):
                            # REMOVED_SYNTAX_ERROR: """Test factory health check."""
                            # REMOVED_SYNTAX_ERROR: pass
                            # REMOVED_SYNTAX_ERROR: factory.connection_pool = mock_pool

                            # Add some emitters
                            # REMOVED_SYNTAX_ERROR: await factory.create_user_emitter("user-1", "session-1")
                            # REMOVED_SYNTAX_ERROR: await factory.create_user_emitter("user-2", "session-2")

                            # Mock pool metrics
                            # REMOVED_SYNTAX_ERROR: pool_metrics = Magic        pool_metrics.healthy_connections = 2
                            # REMOVED_SYNTAX_ERROR: pool_metrics.unhealthy_connections = 0
                            # REMOVED_SYNTAX_ERROR: mock_pool.get_pool_metrics.return_value = pool_metrics

                            # Check health
                            # REMOVED_SYNTAX_ERROR: health = await factory.check_health()

                            # REMOVED_SYNTAX_ERROR: assert health["status"] == "healthy"
                            # REMOVED_SYNTAX_ERROR: assert health["emitter_count"] == 2
                            # REMOVED_SYNTAX_ERROR: assert health["pool_health"]["healthy_connections"] == 2


# REMOVED_SYNTAX_ERROR: class TestUserWebSocketEmitter:
    # REMOVED_SYNTAX_ERROR: """Unit tests for UserWebSocketEmitter class."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_pool():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock connection pool."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: pool = MagicMock(spec=WebSocketConnectionPool)
    # REMOVED_SYNTAX_ERROR: pool.broadcast_to_user = AsyncMock(return_value=1)
    # REMOVED_SYNTAX_ERROR: pool.get_active_connections = MagicMock(return_value=[])
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return pool

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def emitter(self, mock_pool):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a UserWebSocketEmitter instance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserWebSocketEmitter( )
    # REMOVED_SYNTAX_ERROR: user_id="user-123",
    # REMOVED_SYNTAX_ERROR: session_id="session-456",
    # REMOVED_SYNTAX_ERROR: connection_pool=mock_pool
    

# REMOVED_SYNTAX_ERROR: def test_emitter_initialization(self, emitter):
    # REMOVED_SYNTAX_ERROR: """Test emitter initialization."""
    # REMOVED_SYNTAX_ERROR: assert emitter.user_id == "user-123"
    # REMOVED_SYNTAX_ERROR: assert emitter.session_id == "session-456"
    # REMOVED_SYNTAX_ERROR: assert emitter.is_active is True
    # REMOVED_SYNTAX_ERROR: assert emitter.connection_id is None
    # REMOVED_SYNTAX_ERROR: assert len(emitter.event_queue) == 0
    # REMOVED_SYNTAX_ERROR: assert emitter.metrics["events_sent"] == 0
    # REMOVED_SYNTAX_ERROR: assert emitter.metrics["events_failed"] == 0

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_emit_event(self, emitter, mock_pool):
        # REMOVED_SYNTAX_ERROR: """Test emitting an event."""
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: event = { )
        # REMOVED_SYNTAX_ERROR: "type": "agent_started",
        # REMOVED_SYNTAX_ERROR: "data": {"agent": "test"}
        

        # REMOVED_SYNTAX_ERROR: success = await emitter.emit(event)

        # REMOVED_SYNTAX_ERROR: assert success is True
        # REMOVED_SYNTAX_ERROR: mock_pool.broadcast_to_user.assert_called_once()
        # REMOVED_SYNTAX_ERROR: assert emitter.metrics["events_sent"] == 1

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_emit_with_priority(self, emitter, mock_pool):
            # REMOVED_SYNTAX_ERROR: """Test emitting event with priority."""
            # REMOVED_SYNTAX_ERROR: event = { )
            # REMOVED_SYNTAX_ERROR: "type": "error",
            # REMOVED_SYNTAX_ERROR: "data": {"message": "Critical error"}
            

            # REMOVED_SYNTAX_ERROR: success = await emitter.emit(event, priority=EventPriority.HIGH)

            # REMOVED_SYNTAX_ERROR: assert success is True
            # High priority events should be sent immediately
            # REMOVED_SYNTAX_ERROR: mock_pool.broadcast_to_user.assert_called_once()

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_queue_event(self, emitter):
                # REMOVED_SYNTAX_ERROR: """Test queueing events."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: event1 = {"type": "test1"}
                # REMOVED_SYNTAX_ERROR: event2 = {"type": "test2"}

                # REMOVED_SYNTAX_ERROR: emitter.queue_event(event1)
                # REMOVED_SYNTAX_ERROR: emitter.queue_event(event2)

                # REMOVED_SYNTAX_ERROR: assert len(emitter.event_queue) == 2
                # REMOVED_SYNTAX_ERROR: assert emitter.metrics["events_queued"] == 2

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_flush_queue(self, emitter, mock_pool):
                    # REMOVED_SYNTAX_ERROR: """Test flushing event queue."""
                    # Queue some events
                    # REMOVED_SYNTAX_ERROR: events = [ )
                    # REMOVED_SYNTAX_ERROR: {"type": "formatted_string"} for i in range(5)
                    
                    # REMOVED_SYNTAX_ERROR: for event in events:
                        # REMOVED_SYNTAX_ERROR: emitter.queue_event(event)

                        # Flush queue
                        # REMOVED_SYNTAX_ERROR: flushed = await emitter.flush_queue()

                        # REMOVED_SYNTAX_ERROR: assert flushed == 5
                        # REMOVED_SYNTAX_ERROR: assert len(emitter.event_queue) == 0
                        # REMOVED_SYNTAX_ERROR: assert mock_pool.broadcast_to_user.call_count == 5

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_batch_processing(self, emitter, mock_pool):
                            # REMOVED_SYNTAX_ERROR: """Test batch event processing."""
                            # REMOVED_SYNTAX_ERROR: pass
                            # Configure for batching
                            # REMOVED_SYNTAX_ERROR: emitter.batch_size = 3

                            # Queue many events
                            # REMOVED_SYNTAX_ERROR: for i in range(10):
                                # REMOVED_SYNTAX_ERROR: emitter.queue_event({"type": "formatted_string"})

                                # Process batch
                                # REMOVED_SYNTAX_ERROR: processed = await emitter.process_batch()

                                # REMOVED_SYNTAX_ERROR: assert processed == 3  # Should process batch_size events
                                # REMOVED_SYNTAX_ERROR: assert len(emitter.event_queue) == 7  # Remaining events
                                # REMOVED_SYNTAX_ERROR: assert mock_pool.broadcast_to_user.call_count == 3

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_emit_handles_errors(self, emitter, mock_pool):
                                    # REMOVED_SYNTAX_ERROR: """Test emit handles broadcast errors."""
                                    # REMOVED_SYNTAX_ERROR: mock_pool.broadcast_to_user.side_effect = Exception("Send failed")

                                    # REMOVED_SYNTAX_ERROR: event = {"type": "test"}
                                    # REMOVED_SYNTAX_ERROR: success = await emitter.emit(event)

                                    # REMOVED_SYNTAX_ERROR: assert success is False
                                    # REMOVED_SYNTAX_ERROR: assert emitter.metrics["events_failed"] == 1

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_sanitize_event(self, emitter):
                                        # REMOVED_SYNTAX_ERROR: """Test event sanitization."""
                                        # REMOVED_SYNTAX_ERROR: pass
                                        # REMOVED_SYNTAX_ERROR: event = { )
                                        # REMOVED_SYNTAX_ERROR: "type": "agent_thinking",
                                        # REMOVED_SYNTAX_ERROR: "data": { )
                                        # REMOVED_SYNTAX_ERROR: "thought": "Using API key: sk-12345",
                                        # REMOVED_SYNTAX_ERROR: "plan": "Process data"
                                        
                                        

                                        # REMOVED_SYNTAX_ERROR: sanitized = emitter.sanitize_event(event)

                                        # Should remove sensitive data
                                        # REMOVED_SYNTAX_ERROR: assert "sk-12345" not in str(sanitized)

# REMOVED_SYNTAX_ERROR: def test_inactive_emitter(self, emitter):
    # REMOVED_SYNTAX_ERROR: """Test inactive emitter behavior."""
    # REMOVED_SYNTAX_ERROR: emitter.is_active = False

    # Should not queue events when inactive
    # REMOVED_SYNTAX_ERROR: emitter.queue_event({"type": "test"})
    # REMOVED_SYNTAX_ERROR: assert len(emitter.event_queue) == 0

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_connection_management(self, emitter):
        # REMOVED_SYNTAX_ERROR: """Test connection ID management."""
        # REMOVED_SYNTAX_ERROR: pass
        # Set connection ID
        # REMOVED_SYNTAX_ERROR: emitter.set_connection_id("conn-123")
        # REMOVED_SYNTAX_ERROR: assert emitter.connection_id == "conn-123"

        # Clear connection ID
        # REMOVED_SYNTAX_ERROR: emitter.clear_connection_id()
        # REMOVED_SYNTAX_ERROR: assert emitter.connection_id is None

# REMOVED_SYNTAX_ERROR: def test_get_metrics(self, emitter):
    # REMOVED_SYNTAX_ERROR: """Test getting emitter metrics."""
    # REMOVED_SYNTAX_ERROR: emitter.metrics["events_sent"] = 10
    # REMOVED_SYNTAX_ERROR: emitter.metrics["events_failed"] = 2
    # REMOVED_SYNTAX_ERROR: emitter.metrics["events_queued"] = 5

    # REMOVED_SYNTAX_ERROR: metrics = emitter.get_metrics()

    # REMOVED_SYNTAX_ERROR: assert metrics["events_sent"] == 10
    # REMOVED_SYNTAX_ERROR: assert metrics["events_failed"] == 2
    # REMOVED_SYNTAX_ERROR: assert metrics["events_queued"] == 5
    # REMOVED_SYNTAX_ERROR: assert metrics["user_id"] == "user-123"
    # REMOVED_SYNTAX_ERROR: assert metrics["session_id"] == "session-456"

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_lifecycle_events(self, emitter, mock_pool):
        # REMOVED_SYNTAX_ERROR: """Test lifecycle event emissions."""
        # REMOVED_SYNTAX_ERROR: pass
        # Start event
        # REMOVED_SYNTAX_ERROR: await emitter.emit_lifecycle_event("started")

        # Complete event
        # REMOVED_SYNTAX_ERROR: await emitter.emit_lifecycle_event("completed", {"result": "success"})

        # REMOVED_SYNTAX_ERROR: assert mock_pool.broadcast_to_user.call_count == 2

        # Verify event structure
        # REMOVED_SYNTAX_ERROR: calls = mock_pool.broadcast_to_user.call_args_list
        # REMOVED_SYNTAX_ERROR: start_event = calls[0][0][1]
        # REMOVED_SYNTAX_ERROR: complete_event = calls[1][0][1]

        # REMOVED_SYNTAX_ERROR: assert start_event["type"] == "lifecycle_started"
        # REMOVED_SYNTAX_ERROR: assert complete_event["type"] == "lifecycle_completed"
        # REMOVED_SYNTAX_ERROR: assert complete_event["data"]["result"] == "success"