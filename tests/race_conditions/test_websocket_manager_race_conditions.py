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

    # REMOVED_SYNTAX_ERROR: '''Test UnifiedWebSocketManager race condition fixes.

    # REMOVED_SYNTAX_ERROR: This focused test validates the connection-level thread safety enhancements
    # REMOVED_SYNTAX_ERROR: to the UnifiedWebSocketManager.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from datetime import datetime
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class TestUnifiedWebSocketManagerRaceConditions:
    # REMOVED_SYNTAX_ERROR: """Test UnifiedWebSocketManager race condition fixes."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def websocket_manager(self):
    # REMOVED_SYNTAX_ERROR: """Create UnifiedWebSocketManager instance for testing."""
    # REMOVED_SYNTAX_ERROR: return UnifiedWebSocketManager()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def mock_websocket(self):
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: return websocket

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_concurrent_connection_management(self, websocket_manager, mock_websocket):
        # REMOVED_SYNTAX_ERROR: """Test concurrent connection add/remove operations are thread-safe."""
        # REMOVED_SYNTAX_ERROR: users = ["formatted_string" for i in range(5)]
        # REMOVED_SYNTAX_ERROR: connections_per_user = 3

# REMOVED_SYNTAX_ERROR: async def add_user_connections(user_id: str, count: int):
    # REMOVED_SYNTAX_ERROR: """Add multiple connections for a user concurrently."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: connections = []
    # REMOVED_SYNTAX_ERROR: for i in range(count):
        # REMOVED_SYNTAX_ERROR: connection_id = "formatted_string"
        # REMOVED_SYNTAX_ERROR: connection = WebSocketConnection( )
        # REMOVED_SYNTAX_ERROR: connection_id=connection_id,
        # REMOVED_SYNTAX_ERROR: user_id=user_id,
        # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
        # REMOVED_SYNTAX_ERROR: connected_at=datetime.now()
        
        # REMOVED_SYNTAX_ERROR: await websocket_manager.add_connection(connection)
        # REMOVED_SYNTAX_ERROR: connections.append(connection)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return connections

        # Add connections concurrently for all users
        # REMOVED_SYNTAX_ERROR: add_tasks = []
        # REMOVED_SYNTAX_ERROR: for user in users:
            # REMOVED_SYNTAX_ERROR: task = add_user_connections(user, connections_per_user)
            # REMOVED_SYNTAX_ERROR: add_tasks.append(task)

            # REMOVED_SYNTAX_ERROR: all_connections = await asyncio.gather(*add_tasks)

            # Verify all connections were added correctly
            # REMOVED_SYNTAX_ERROR: total_expected_connections = len(users) * connections_per_user
            # REMOVED_SYNTAX_ERROR: stats = websocket_manager.get_stats()
            # REMOVED_SYNTAX_ERROR: assert stats['total_connections'] == total_expected_connections
            # REMOVED_SYNTAX_ERROR: assert stats['unique_users'] == len(users)

            # Verify each user has the correct number of connections
            # REMOVED_SYNTAX_ERROR: for user in users:
                # REMOVED_SYNTAX_ERROR: user_connections = websocket_manager.get_user_connections(user)
                # REMOVED_SYNTAX_ERROR: assert len(user_connections) == connections_per_user

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_concurrent_message_sending_safety(self, websocket_manager, mock_websocket):
                    # REMOVED_SYNTAX_ERROR: """Test concurrent message sending to users is thread-safe."""
                    # REMOVED_SYNTAX_ERROR: users = ["formatted_string" for i in range(3)]
                    # REMOVED_SYNTAX_ERROR: connections_per_user = 2
                    # REMOVED_SYNTAX_ERROR: messages_per_user = 5

                    # Add connections for all users
                    # REMOVED_SYNTAX_ERROR: for user in users:
                        # REMOVED_SYNTAX_ERROR: for i in range(connections_per_user):
                            # REMOVED_SYNTAX_ERROR: connection_id = "formatted_string"
                            # REMOVED_SYNTAX_ERROR: connection = WebSocketConnection( )
                            # REMOVED_SYNTAX_ERROR: connection_id=connection_id,
                            # REMOVED_SYNTAX_ERROR: user_id=user,
                            # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
                            # REMOVED_SYNTAX_ERROR: connected_at=datetime.now()
                            
                            # REMOVED_SYNTAX_ERROR: await websocket_manager.add_connection(connection)

# REMOVED_SYNTAX_ERROR: async def send_messages_to_user(user_id: str, message_count: int):
    # REMOVED_SYNTAX_ERROR: """Send multiple messages to a user concurrently."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: sent_messages = []
    # REMOVED_SYNTAX_ERROR: for i in range(message_count):
        # REMOVED_SYNTAX_ERROR: message = { )
        # REMOVED_SYNTAX_ERROR: "type": "test_message",
        # REMOVED_SYNTAX_ERROR: "data": "formatted_string",
        # REMOVED_SYNTAX_ERROR: "timestamp": datetime.utcnow().isoformat()
        
        # REMOVED_SYNTAX_ERROR: await websocket_manager.send_to_user(user_id, message)
        # REMOVED_SYNTAX_ERROR: sent_messages.append(message)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return sent_messages

        # Send messages to all users concurrently
        # REMOVED_SYNTAX_ERROR: send_tasks = []
        # REMOVED_SYNTAX_ERROR: for user in users:
            # REMOVED_SYNTAX_ERROR: task = send_messages_to_user(user, messages_per_user)
            # REMOVED_SYNTAX_ERROR: send_tasks.append(task)

            # REMOVED_SYNTAX_ERROR: all_sent_messages = await asyncio.gather(*send_tasks)

            # Verify all messages were sent without race conditions
            # REMOVED_SYNTAX_ERROR: expected_total_calls = len(users) * connections_per_user * messages_per_user
            # REMOVED_SYNTAX_ERROR: assert mock_websocket.send_json.call_count == expected_total_calls

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_user_connection_lock_isolation(self, websocket_manager):
                # REMOVED_SYNTAX_ERROR: """Test that user-specific connection locks provide proper isolation."""
                # REMOVED_SYNTAX_ERROR: users = ["formatted_string" for i in range(5)]

                # Test that each user gets their own lock
                # REMOVED_SYNTAX_ERROR: locks = {}
                # REMOVED_SYNTAX_ERROR: for user in users:
                    # REMOVED_SYNTAX_ERROR: lock1 = await websocket_manager._get_user_connection_lock(user)
                    # REMOVED_SYNTAX_ERROR: lock2 = await websocket_manager._get_user_connection_lock(user)
                    # Same user should get same lock instance
                    # REMOVED_SYNTAX_ERROR: assert lock1 is lock2, "formatted_string"
                    # REMOVED_SYNTAX_ERROR: locks[user] = lock1

                    # Different users should get different locks
                    # REMOVED_SYNTAX_ERROR: user_lock_ids = {user: id(lock) for user, lock in locks.items()}
                    # REMOVED_SYNTAX_ERROR: assert len(set(user_lock_ids.values())) == len(users), "Users sharing locks - isolation broken"

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_concurrent_add_remove_operations(self, websocket_manager, mock_websocket):
                        # REMOVED_SYNTAX_ERROR: """Test concurrent add/remove operations don't cause race conditions."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: user_id = "test_user"
                        # REMOVED_SYNTAX_ERROR: operation_count = 20

# REMOVED_SYNTAX_ERROR: async def add_remove_cycle(cycle_id: int):
    # REMOVED_SYNTAX_ERROR: """Add and remove a connection in sequence."""
    # REMOVED_SYNTAX_ERROR: connection_id = "formatted_string"

    # Add connection
    # REMOVED_SYNTAX_ERROR: connection = WebSocketConnection( )
    # REMOVED_SYNTAX_ERROR: connection_id=connection_id,
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
    # REMOVED_SYNTAX_ERROR: connected_at=datetime.now()
    
    # REMOVED_SYNTAX_ERROR: await websocket_manager.add_connection(connection)

    # Immediately remove it
    # REMOVED_SYNTAX_ERROR: await websocket_manager.remove_connection(connection_id)

    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return connection_id

    # Run many add/remove cycles concurrently
    # REMOVED_SYNTAX_ERROR: tasks = [add_remove_cycle(i) for i in range(operation_count)]
    # REMOVED_SYNTAX_ERROR: completed_cycles = await asyncio.gather(*tasks)

    # Verify all operations completed
    # REMOVED_SYNTAX_ERROR: assert len(completed_cycles) == operation_count

    # Verify final state is clean (no leftover connections)
    # REMOVED_SYNTAX_ERROR: stats = websocket_manager.get_stats()
    # REMOVED_SYNTAX_ERROR: user_connections = websocket_manager.get_user_connections(user_id)
    # REMOVED_SYNTAX_ERROR: assert len(user_connections) == 0, "formatted_string"

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_legacy_interface_compatibility(self, websocket_manager, mock_websocket):
        # REMOVED_SYNTAX_ERROR: """Test that legacy interface still works alongside new thread-safe methods."""
        # REMOVED_SYNTAX_ERROR: pass
        # Test legacy connect_user method
        # REMOVED_SYNTAX_ERROR: conn_info = await websocket_manager.connect_user("legacy_user", mock_websocket)
        # REMOVED_SYNTAX_ERROR: assert conn_info.user_id == "legacy_user"

        # Test stats work
        # REMOVED_SYNTAX_ERROR: stats = websocket_manager.get_stats()
        # REMOVED_SYNTAX_ERROR: assert stats['total_connections'] >= 1

        # Test legacy disconnect_user method
        # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user("legacy_user", mock_websocket)

        # Verify cleanup
        # REMOVED_SYNTAX_ERROR: final_stats = websocket_manager.get_stats()
        # REMOVED_SYNTAX_ERROR: legacy_connections = websocket_manager.get_user_connections("legacy_user")
        # REMOVED_SYNTAX_ERROR: assert len(legacy_connections) == 0, "Legacy user connections not properly cleaned up"


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])