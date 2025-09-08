# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: WebSocket Connection Pool Unit Tests

# REMOVED_SYNTAX_ERROR: Business Value:
    # REMOVED_SYNTAX_ERROR: - Ensures connection pool properly manages WebSocket connections
    # REMOVED_SYNTAX_ERROR: - Validates resource management and cleanup
    # REMOVED_SYNTAX_ERROR: - Tests concurrent user handling
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.websocket_bridge_factory import ( )
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
    # REMOVED_SYNTAX_ERROR: WebSocketConnectionPool,
    # REMOVED_SYNTAX_ERROR: UserWebSocketConnection as WebSocketConnection
    

    # Mock missing classes if needed
# REMOVED_SYNTAX_ERROR: class ConnectionStatus:
    # REMOVED_SYNTAX_ERROR: INITIALIZING = "initializing"
    # REMOVED_SYNTAX_ERROR: HEALTHY = "healthy"
    # REMOVED_SYNTAX_ERROR: UNHEALTHY = "unhealthy"
    # REMOVED_SYNTAX_ERROR: FAILED = "failed"
    # REMOVED_SYNTAX_ERROR: CLOSED = "closed"

# REMOVED_SYNTAX_ERROR: class ConnectionMetrics:
# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.total_connections = 0
    # REMOVED_SYNTAX_ERROR: self.total_users = 0
    # REMOVED_SYNTAX_ERROR: self.healthy_connections = 0
    # REMOVED_SYNTAX_ERROR: self.unhealthy_connections = 0
    # REMOVED_SYNTAX_ERROR: self.total_messages = 0
    # REMOVED_SYNTAX_ERROR: self.total_errors = 0


# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Unit tests for WebSocketConnection class."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock WebSocket instance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: ws = Magic        ws.websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: ws.state = Magic        ws.state.name = "OPEN"
    # REMOVED_SYNTAX_ERROR: return ws

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def connection(self, mock_websocket):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a WebSocketConnection instance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return WebSocketConnection( )
    # REMOVED_SYNTAX_ERROR: connection_id="test-connection-1",
    # REMOVED_SYNTAX_ERROR: user_id="user-123",
    # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
    # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc)
    

# REMOVED_SYNTAX_ERROR: def test_connection_initialization(self, connection):
    # REMOVED_SYNTAX_ERROR: """Test WebSocketConnection initialization."""
    # REMOVED_SYNTAX_ERROR: assert connection.connection_id == "test-connection-1"
    # REMOVED_SYNTAX_ERROR: assert connection.user_id == "user-123"
    # REMOVED_SYNTAX_ERROR: assert connection.status == ConnectionStatus.INITIALIZING
    # REMOVED_SYNTAX_ERROR: assert connection.is_active is True
    # REMOVED_SYNTAX_ERROR: assert connection.error_count == 0
    # REMOVED_SYNTAX_ERROR: assert connection.message_count == 0
    # REMOVED_SYNTAX_ERROR: assert connection.last_ping is None
    # REMOVED_SYNTAX_ERROR: assert connection.last_error is None

# REMOVED_SYNTAX_ERROR: def test_connection_metrics(self, connection):
    # REMOVED_SYNTAX_ERROR: """Test connection metrics tracking."""
    # REMOVED_SYNTAX_ERROR: pass
    # Update message count
    # REMOVED_SYNTAX_ERROR: connection.message_count = 10
    # REMOVED_SYNTAX_ERROR: connection.error_count = 2

    # REMOVED_SYNTAX_ERROR: assert connection.message_count == 10
    # REMOVED_SYNTAX_ERROR: assert connection.error_count == 2

    # Mark as healthy
    # REMOVED_SYNTAX_ERROR: connection.status = ConnectionStatus.HEALTHY
    # REMOVED_SYNTAX_ERROR: assert connection.status == ConnectionStatus.HEALTHY

    # Mark as failed
    # REMOVED_SYNTAX_ERROR: connection.status = ConnectionStatus.FAILED
    # REMOVED_SYNTAX_ERROR: connection.is_active = False
    # REMOVED_SYNTAX_ERROR: assert connection.is_active is False

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_websocket_send(self, connection, mock_websocket):
        # REMOVED_SYNTAX_ERROR: """Test sending messages through connection."""
        # REMOVED_SYNTAX_ERROR: await connection.websocket.send("test message")
        # REMOVED_SYNTAX_ERROR: mock_websocket.send.assert_called_once_with("test message")

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_websocket_close(self, connection, mock_websocket):
            # REMOVED_SYNTAX_ERROR: """Test closing WebSocket connection."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: await connection.websocket.close()
            # REMOVED_SYNTAX_ERROR: mock_websocket.close.assert_called_once()


# REMOVED_SYNTAX_ERROR: class TestWebSocketConnectionPool:
    # REMOVED_SYNTAX_ERROR: """Unit tests for WebSocketConnectionPool class."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def pool(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a WebSocketConnectionPool instance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return WebSocketConnectionPool( )
    # REMOVED_SYNTAX_ERROR: max_connections_per_user=3,
    # REMOVED_SYNTAX_ERROR: connection_timeout=30,
    # REMOVED_SYNTAX_ERROR: health_check_interval=5
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock WebSocket instance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: ws = Magic        ws.websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: ws.state = Magic        ws.state.name = "OPEN"
    # REMOVED_SYNTAX_ERROR: return ws

# REMOVED_SYNTAX_ERROR: def test_pool_initialization(self, pool):
    # REMOVED_SYNTAX_ERROR: """Test connection pool initialization."""
    # REMOVED_SYNTAX_ERROR: assert pool.max_connections_per_user == 3
    # REMOVED_SYNTAX_ERROR: assert pool.connection_timeout == 30
    # REMOVED_SYNTAX_ERROR: assert pool.health_check_interval == 5
    # REMOVED_SYNTAX_ERROR: assert len(pool.connections) == 0
    # REMOVED_SYNTAX_ERROR: assert len(pool.user_connections) == 0
    # REMOVED_SYNTAX_ERROR: assert pool.total_connections == 0

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_add_connection(self, pool, mock_websocket):
        # REMOVED_SYNTAX_ERROR: """Test adding a connection to the pool."""
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: user_id = "user-123"
        # REMOVED_SYNTAX_ERROR: connection_id = await pool.add_connection(user_id, mock_websocket)

        # REMOVED_SYNTAX_ERROR: assert connection_id is not None
        # REMOVED_SYNTAX_ERROR: assert pool.total_connections == 1
        # REMOVED_SYNTAX_ERROR: assert user_id in pool.user_connections
        # REMOVED_SYNTAX_ERROR: assert len(pool.user_connections[user_id]) == 1
        # REMOVED_SYNTAX_ERROR: assert connection_id in pool.connections

        # Verify connection properties
        # REMOVED_SYNTAX_ERROR: connection = pool.connections[connection_id]
        # REMOVED_SYNTAX_ERROR: assert connection.user_id == user_id
        # REMOVED_SYNTAX_ERROR: assert connection.websocket == mock_websocket
        # REMOVED_SYNTAX_ERROR: assert connection.status == ConnectionStatus.INITIALIZING

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_add_multiple_connections_same_user(self, pool, mock_websocket):
            # REMOVED_SYNTAX_ERROR: """Test adding multiple connections for the same user."""
            # REMOVED_SYNTAX_ERROR: user_id = "user-123"

            # Add three connections
            # REMOVED_SYNTAX_ERROR: conn_ids = []
            # REMOVED_SYNTAX_ERROR: for _ in range(3):
                # REMOVED_SYNTAX_ERROR: ws = Magic            ws.websocket = TestWebSocketConnection()
                # REMOVED_SYNTAX_ERROR: ws.state = Magic            ws.state.name = "OPEN"
                # REMOVED_SYNTAX_ERROR: conn_id = await pool.add_connection(user_id, ws)
                # REMOVED_SYNTAX_ERROR: conn_ids.append(conn_id)

                # REMOVED_SYNTAX_ERROR: assert pool.total_connections == 3
                # REMOVED_SYNTAX_ERROR: assert len(pool.user_connections[user_id]) == 3

                # Verify all connections are tracked
                # REMOVED_SYNTAX_ERROR: for conn_id in conn_ids:
                    # REMOVED_SYNTAX_ERROR: assert conn_id in pool.connections

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_max_connections_per_user(self, pool):
                        # REMOVED_SYNTAX_ERROR: """Test max connections per user limit."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                        # Add max connections
                        # REMOVED_SYNTAX_ERROR: for i in range(3):
                            # REMOVED_SYNTAX_ERROR: ws = Magic            ws.websocket = TestWebSocketConnection()
                            # REMOVED_SYNTAX_ERROR: ws.state = Magic            ws.state.name = "OPEN"
                            # REMOVED_SYNTAX_ERROR: await pool.add_connection(user_id, ws)

                            # Try to add one more (should close oldest)
                            # REMOVED_SYNTAX_ERROR: new_ws = Magic        new_ws.websocket = TestWebSocketConnection()
                            # REMOVED_SYNTAX_ERROR: new_ws.state = Magic        new_ws.state.name = "OPEN"

                            # REMOVED_SYNTAX_ERROR: oldest_conn = pool.user_connections[user_id][0]
                            # REMOVED_SYNTAX_ERROR: old_ws = pool.connections[oldest_conn].websocket

                            # REMOVED_SYNTAX_ERROR: await pool.add_connection(user_id, new_ws)

                            # Should have closed the oldest connection
                            # REMOVED_SYNTAX_ERROR: old_ws.close.assert_called()
                            # REMOVED_SYNTAX_ERROR: assert oldest_conn not in pool.connections
                            # REMOVED_SYNTAX_ERROR: assert pool.total_connections == 3

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_remove_connection(self, pool, mock_websocket):
                                # REMOVED_SYNTAX_ERROR: """Test removing a connection from the pool."""
                                # REMOVED_SYNTAX_ERROR: user_id = "user-123"
                                # REMOVED_SYNTAX_ERROR: connection_id = await pool.add_connection(user_id, mock_websocket)

                                # Remove the connection
                                # REMOVED_SYNTAX_ERROR: removed = await pool.remove_connection(connection_id)

                                # REMOVED_SYNTAX_ERROR: assert removed is True
                                # REMOVED_SYNTAX_ERROR: assert connection_id not in pool.connections
                                # REMOVED_SYNTAX_ERROR: assert pool.total_connections == 0
                                # REMOVED_SYNTAX_ERROR: assert len(pool.user_connections.get(user_id, [])) == 0
                                # REMOVED_SYNTAX_ERROR: mock_websocket.close.assert_called()

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_remove_nonexistent_connection(self, pool):
                                    # REMOVED_SYNTAX_ERROR: """Test removing a non-existent connection."""
                                    # REMOVED_SYNTAX_ERROR: pass
                                    # REMOVED_SYNTAX_ERROR: removed = await pool.remove_connection("non-existent-id")
                                    # REMOVED_SYNTAX_ERROR: assert removed is False

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_get_user_connections(self, pool):
                                        # REMOVED_SYNTAX_ERROR: """Test getting all connections for a user."""
                                        # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                                        # Add multiple connections
                                        # REMOVED_SYNTAX_ERROR: conn_ids = []
                                        # REMOVED_SYNTAX_ERROR: for _ in range(2):
                                            # REMOVED_SYNTAX_ERROR: ws = Magic            ws.websocket = TestWebSocketConnection()
                                            # REMOVED_SYNTAX_ERROR: ws.state = Magic            ws.state.name = "OPEN"
                                            # REMOVED_SYNTAX_ERROR: conn_id = await pool.add_connection(user_id, ws)
                                            # REMOVED_SYNTAX_ERROR: conn_ids.append(conn_id)

                                            # Get user connections
                                            # REMOVED_SYNTAX_ERROR: connections = pool.get_user_connections(user_id)

                                            # REMOVED_SYNTAX_ERROR: assert len(connections) == 2
                                            # REMOVED_SYNTAX_ERROR: for conn in connections:
                                                # REMOVED_SYNTAX_ERROR: assert conn.connection_id in conn_ids
                                                # REMOVED_SYNTAX_ERROR: assert conn.user_id == user_id

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_get_active_connections(self, pool):
                                                    # REMOVED_SYNTAX_ERROR: """Test getting only active connections for a user."""
                                                    # REMOVED_SYNTAX_ERROR: pass
                                                    # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                                                    # Add active connection
                                                    # REMOVED_SYNTAX_ERROR: ws1 = Magic        ws1.websocket = TestWebSocketConnection()
                                                    # REMOVED_SYNTAX_ERROR: ws1.state = Magic        ws1.state.name = "OPEN"
                                                    # REMOVED_SYNTAX_ERROR: conn_id1 = await pool.add_connection(user_id, ws1)
                                                    # REMOVED_SYNTAX_ERROR: pool.connections[conn_id1].status = ConnectionStatus.HEALTHY

                                                    # Add inactive connection
                                                    # REMOVED_SYNTAX_ERROR: ws2 = Magic        ws2.websocket = TestWebSocketConnection()
                                                    # REMOVED_SYNTAX_ERROR: ws2.state = Magic        ws2.state.name = "CLOSED"
                                                    # REMOVED_SYNTAX_ERROR: conn_id2 = await pool.add_connection(user_id, ws2)
                                                    # REMOVED_SYNTAX_ERROR: pool.connections[conn_id2].status = ConnectionStatus.FAILED
                                                    # REMOVED_SYNTAX_ERROR: pool.connections[conn_id2].is_active = False

                                                    # Get active connections
                                                    # REMOVED_SYNTAX_ERROR: active = pool.get_active_connections(user_id)

                                                    # REMOVED_SYNTAX_ERROR: assert len(active) == 1
                                                    # REMOVED_SYNTAX_ERROR: assert active[0].connection_id == conn_id1

                                                    # Removed problematic line: @pytest.mark.asyncio
                                                    # Removed problematic line: async def test_broadcast_to_user(self, pool):
                                                        # REMOVED_SYNTAX_ERROR: """Test broadcasting message to all user connections."""
                                                        # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                                                        # Add multiple connections
                                                        # REMOVED_SYNTAX_ERROR: websockets = []
                                                        # REMOVED_SYNTAX_ERROR: for _ in range(2):
                                                            # REMOVED_SYNTAX_ERROR: ws = Magic            ws.websocket = TestWebSocketConnection()
                                                            # REMOVED_SYNTAX_ERROR: ws.state = Magic            ws.state.name = "OPEN"
                                                            # REMOVED_SYNTAX_ERROR: websockets.append(ws)
                                                            # REMOVED_SYNTAX_ERROR: conn_id = await pool.add_connection(user_id, ws)
                                                            # REMOVED_SYNTAX_ERROR: pool.connections[conn_id].status = ConnectionStatus.HEALTHY

                                                            # Broadcast message
                                                            # REMOVED_SYNTAX_ERROR: message = {"type": "test", "data": "hello"}
                                                            # REMOVED_SYNTAX_ERROR: success_count = await pool.broadcast_to_user(user_id, message)

                                                            # REMOVED_SYNTAX_ERROR: assert success_count == 2
                                                            # REMOVED_SYNTAX_ERROR: for ws in websockets:
                                                                # REMOVED_SYNTAX_ERROR: ws.send.assert_called_once()

                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_broadcast_handles_send_errors(self, pool):
                                                                    # REMOVED_SYNTAX_ERROR: """Test broadcast handles errors during send."""
                                                                    # REMOVED_SYNTAX_ERROR: pass
                                                                    # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                                                                    # Add connection that will fail
                                                                    # REMOVED_SYNTAX_ERROR: ws = Magic        ws.send = AsyncMock(side_effect=Exception("Send failed"))
                                                                    # REMOVED_SYNTAX_ERROR: ws.state = Magic        ws.state.name = "OPEN"
                                                                    # REMOVED_SYNTAX_ERROR: conn_id = await pool.add_connection(user_id, ws)
                                                                    # REMOVED_SYNTAX_ERROR: pool.connections[conn_id].status = ConnectionStatus.HEALTHY

                                                                    # Broadcast should handle error gracefully
                                                                    # REMOVED_SYNTAX_ERROR: message = {"type": "test", "data": "hello"}
                                                                    # REMOVED_SYNTAX_ERROR: success_count = await pool.broadcast_to_user(user_id, message)

                                                                    # REMOVED_SYNTAX_ERROR: assert success_count == 0
                                                                    # REMOVED_SYNTAX_ERROR: assert pool.connections[conn_id].error_count > 0

                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                    # Removed problematic line: async def test_cleanup_inactive_connections(self, pool):
                                                                        # REMOVED_SYNTAX_ERROR: """Test cleaning up inactive connections."""
                                                                        # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                                                                        # Add healthy connection
                                                                        # REMOVED_SYNTAX_ERROR: ws1 = Magic        ws1.websocket = TestWebSocketConnection()
                                                                        # REMOVED_SYNTAX_ERROR: ws1.state = Magic        ws1.state.name = "OPEN"
                                                                        # REMOVED_SYNTAX_ERROR: conn_id1 = await pool.add_connection(user_id, ws1)
                                                                        # REMOVED_SYNTAX_ERROR: pool.connections[conn_id1].status = ConnectionStatus.HEALTHY

                                                                        # Add failed connection
                                                                        # REMOVED_SYNTAX_ERROR: ws2 = Magic        ws2.websocket = TestWebSocketConnection()
                                                                        # REMOVED_SYNTAX_ERROR: ws2.state = Magic        ws2.state.name = "CLOSED"
                                                                        # REMOVED_SYNTAX_ERROR: conn_id2 = await pool.add_connection(user_id, ws2)
                                                                        # REMOVED_SYNTAX_ERROR: pool.connections[conn_id2].status = ConnectionStatus.FAILED
                                                                        # REMOVED_SYNTAX_ERROR: pool.connections[conn_id2].is_active = False

                                                                        # Cleanup inactive
                                                                        # REMOVED_SYNTAX_ERROR: removed_count = await pool.cleanup_inactive_connections()

                                                                        # REMOVED_SYNTAX_ERROR: assert removed_count == 1
                                                                        # REMOVED_SYNTAX_ERROR: assert conn_id1 in pool.connections
                                                                        # REMOVED_SYNTAX_ERROR: assert conn_id2 not in pool.connections
                                                                        # REMOVED_SYNTAX_ERROR: ws2.close.assert_called()

                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # Removed problematic line: async def test_cleanup_user_connections(self, pool):
                                                                            # REMOVED_SYNTAX_ERROR: """Test cleaning up all connections for a user."""
                                                                            # REMOVED_SYNTAX_ERROR: pass
                                                                            # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                                                                            # Add multiple connections
                                                                            # REMOVED_SYNTAX_ERROR: websockets = []
                                                                            # REMOVED_SYNTAX_ERROR: conn_ids = []
                                                                            # REMOVED_SYNTAX_ERROR: for _ in range(2):
                                                                                # REMOVED_SYNTAX_ERROR: ws = Magic            ws.websocket = TestWebSocketConnection()
                                                                                # REMOVED_SYNTAX_ERROR: ws.state = Magic            ws.state.name = "OPEN"
                                                                                # REMOVED_SYNTAX_ERROR: websockets.append(ws)
                                                                                # REMOVED_SYNTAX_ERROR: conn_id = await pool.add_connection(user_id, ws)
                                                                                # REMOVED_SYNTAX_ERROR: conn_ids.append(conn_id)

                                                                                # Cleanup user connections
                                                                                # REMOVED_SYNTAX_ERROR: removed_count = await pool.cleanup_user_connections(user_id)

                                                                                # REMOVED_SYNTAX_ERROR: assert removed_count == 2
                                                                                # REMOVED_SYNTAX_ERROR: assert user_id not in pool.user_connections
                                                                                # REMOVED_SYNTAX_ERROR: for conn_id in conn_ids:
                                                                                    # REMOVED_SYNTAX_ERROR: assert conn_id not in pool.connections
                                                                                    # REMOVED_SYNTAX_ERROR: for ws in websockets:
                                                                                        # REMOVED_SYNTAX_ERROR: ws.close.assert_called()

                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                        # Removed problematic line: async def test_get_pool_metrics(self, pool):
                                                                                            # REMOVED_SYNTAX_ERROR: """Test getting pool metrics."""
                                                                                            # Add connections for multiple users
                                                                                            # REMOVED_SYNTAX_ERROR: user1 = "user-123"
                                                                                            # REMOVED_SYNTAX_ERROR: user2 = "user-456"

                                                                                            # REMOVED_SYNTAX_ERROR: ws1 = Magic        ws1.websocket = TestWebSocketConnection()
                                                                                            # REMOVED_SYNTAX_ERROR: ws1.state = Magic        ws1.state.name = "OPEN"
                                                                                            # REMOVED_SYNTAX_ERROR: conn_id1 = await pool.add_connection(user1, ws1)
                                                                                            # REMOVED_SYNTAX_ERROR: pool.connections[conn_id1].status = ConnectionStatus.HEALTHY
                                                                                            # REMOVED_SYNTAX_ERROR: pool.connections[conn_id1].message_count = 5

                                                                                            # REMOVED_SYNTAX_ERROR: ws2 = Magic        ws2.websocket = TestWebSocketConnection()
                                                                                            # REMOVED_SYNTAX_ERROR: ws2.state = Magic        ws2.state.name = "OPEN"
                                                                                            # REMOVED_SYNTAX_ERROR: conn_id2 = await pool.add_connection(user2, ws2)
                                                                                            # REMOVED_SYNTAX_ERROR: pool.connections[conn_id2].status = ConnectionStatus.UNHEALTHY
                                                                                            # REMOVED_SYNTAX_ERROR: pool.connections[conn_id2].error_count = 2

                                                                                            # Get metrics
                                                                                            # REMOVED_SYNTAX_ERROR: metrics = pool.get_pool_metrics()

                                                                                            # REMOVED_SYNTAX_ERROR: assert metrics.total_connections == 2
                                                                                            # REMOVED_SYNTAX_ERROR: assert metrics.total_users == 2
                                                                                            # REMOVED_SYNTAX_ERROR: assert metrics.healthy_connections == 1
                                                                                            # REMOVED_SYNTAX_ERROR: assert metrics.unhealthy_connections == 1
                                                                                            # REMOVED_SYNTAX_ERROR: assert metrics.total_messages == 5
                                                                                            # REMOVED_SYNTAX_ERROR: assert metrics.total_errors == 2

                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                            # Removed problematic line: async def test_health_check_healthy_connection(self, pool):
                                                                                                # REMOVED_SYNTAX_ERROR: """Test health check on healthy connection."""
                                                                                                # REMOVED_SYNTAX_ERROR: pass
                                                                                                # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                                                                                                # REMOVED_SYNTAX_ERROR: ws = Magic        ws.websocket = TestWebSocketConnection()
                                                                                                # REMOVED_SYNTAX_ERROR: ws.state = Magic        ws.state.name = "OPEN"

                                                                                                # REMOVED_SYNTAX_ERROR: conn_id = await pool.add_connection(user_id, ws)
                                                                                                # REMOVED_SYNTAX_ERROR: connection = pool.connections[conn_id]

                                                                                                # Perform health check
                                                                                                # REMOVED_SYNTAX_ERROR: is_healthy = await pool.check_connection_health(connection)

                                                                                                # REMOVED_SYNTAX_ERROR: assert is_healthy is True
                                                                                                # REMOVED_SYNTAX_ERROR: assert connection.status == ConnectionStatus.HEALTHY
                                                                                                # REMOVED_SYNTAX_ERROR: ws.ping.assert_called_once()

                                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                                # Removed problematic line: async def test_health_check_closed_connection(self, pool):
                                                                                                    # REMOVED_SYNTAX_ERROR: """Test health check on closed connection."""
                                                                                                    # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                                                                                                    # REMOVED_SYNTAX_ERROR: ws = Magic        ws.websocket = TestWebSocketConnection()
                                                                                                    # REMOVED_SYNTAX_ERROR: ws.state = Magic        ws.state.name = "CLOSED"

                                                                                                    # REMOVED_SYNTAX_ERROR: conn_id = await pool.add_connection(user_id, ws)
                                                                                                    # REMOVED_SYNTAX_ERROR: connection = pool.connections[conn_id]

                                                                                                    # Perform health check
                                                                                                    # REMOVED_SYNTAX_ERROR: is_healthy = await pool.check_connection_health(connection)

                                                                                                    # REMOVED_SYNTAX_ERROR: assert is_healthy is False
                                                                                                    # REMOVED_SYNTAX_ERROR: assert connection.status == ConnectionStatus.FAILED
                                                                                                    # REMOVED_SYNTAX_ERROR: assert connection.is_active is False
                                                                                                    # REMOVED_SYNTAX_ERROR: pass