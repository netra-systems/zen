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

        '''Test UnifiedWebSocketManager race condition fixes.

        This focused test validates the connection-level thread safety enhancements
        to the UnifiedWebSocketManager.
        '''

        import asyncio
        import pytest
        import uuid
        from datetime import datetime
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, WebSocketConnection
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


class TestUnifiedWebSocketManagerRaceConditions:
        """Test UnifiedWebSocketManager race condition fixes."""

        @pytest.fixture
    def websocket_manager(self):
        """Create UnifiedWebSocketManager instance for testing."""
        return UnifiedWebSocketManager()

        @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        pass
        websocket = TestWebSocketConnection()
        return websocket

@pytest.mark.asyncio
    async def test_concurrent_connection_management(self, websocket_manager, mock_websocket):
        """Test concurrent connection add/remove operations are thread-safe."""
users = ["formatted_string" for i in range(5)]
connections_per_user = 3

async def add_user_connections(user_id: str, count: int):
    """Add multiple connections for a user concurrently."""
pass
connections = []
for i in range(count):
    connection_id = "formatted_string"
connection = WebSocketConnection( )
connection_id=connection_id,
user_id=user_id,
websocket=mock_websocket,
connected_at=datetime.now()
        
await websocket_manager.add_connection(connection)
connections.append(connection)
await asyncio.sleep(0)
return connections

        # Add connections concurrently for all users
add_tasks = []
for user in users:
    task = add_user_connections(user, connections_per_user)
add_tasks.append(task)

all_connections = await asyncio.gather(*add_tasks)

            # Verify all connections were added correctly
total_expected_connections = len(users) * connections_per_user
stats = websocket_manager.get_stats()
assert stats['total_connections'] == total_expected_connections
assert stats['unique_users'] == len(users)

            # Verify each user has the correct number of connections
for user in users:
    user_connections = websocket_manager.get_user_connections(user)
assert len(user_connections) == connections_per_user

@pytest.mark.asyncio
    async def test_concurrent_message_sending_safety(self, websocket_manager, mock_websocket):
        """Test concurrent message sending to users is thread-safe."""
users = ["formatted_string" for i in range(3)]
connections_per_user = 2
messages_per_user = 5

                    # Add connections for all users
for user in users:
    for i in range(connections_per_user):
        connection_id = "formatted_string"
connection = WebSocketConnection( )
connection_id=connection_id,
user_id=user,
websocket=mock_websocket,
connected_at=datetime.now()
                            
await websocket_manager.add_connection(connection)

async def send_messages_to_user(user_id: str, message_count: int):
    """Send multiple messages to a user concurrently."""
pass
sent_messages = []
for i in range(message_count):
    message = { )
"type": "test_message",
"data": "formatted_string",
"timestamp": datetime.utcnow().isoformat()
        
await websocket_manager.send_to_user(user_id, message)
sent_messages.append(message)
await asyncio.sleep(0)
return sent_messages

        # Send messages to all users concurrently
send_tasks = []
for user in users:
    task = send_messages_to_user(user, messages_per_user)
send_tasks.append(task)

all_sent_messages = await asyncio.gather(*send_tasks)

            # Verify all messages were sent without race conditions
expected_total_calls = len(users) * connections_per_user * messages_per_user
assert mock_websocket.send_json.call_count == expected_total_calls

@pytest.mark.asyncio
    async def test_user_connection_lock_isolation(self, websocket_manager):
        """Test that user-specific connection locks provide proper isolation."""
users = ["formatted_string" for i in range(5)]

                # Test that each user gets their own lock
locks = {}
for user in users:
    lock1 = await websocket_manager._get_user_connection_lock(user)
lock2 = await websocket_manager._get_user_connection_lock(user)
                    # Same user should get same lock instance
assert lock1 is lock2, "formatted_string"
locks[user] = lock1

                    # Different users should get different locks
user_lock_ids = {user: id(lock) for user, lock in locks.items()}
assert len(set(user_lock_ids.values())) == len(users), "Users sharing locks - isolation broken"

@pytest.mark.asyncio
    async def test_concurrent_add_remove_operations(self, websocket_manager, mock_websocket):
        """Test concurrent add/remove operations don't cause race conditions."""
pass
user_id = "test_user"
operation_count = 20

async def add_remove_cycle(cycle_id: int):
    """Add and remove a connection in sequence."""
connection_id = "formatted_string"

    # Add connection
connection = WebSocketConnection( )
connection_id=connection_id,
user_id=user_id,
websocket=mock_websocket,
connected_at=datetime.now()
    
await websocket_manager.add_connection(connection)

    # Immediately remove it
await websocket_manager.remove_connection(connection_id)

await asyncio.sleep(0)
return connection_id

    # Run many add/remove cycles concurrently
tasks = [add_remove_cycle(i) for i in range(operation_count)]
completed_cycles = await asyncio.gather(*tasks)

    # Verify all operations completed
assert len(completed_cycles) == operation_count

    # Verify final state is clean (no leftover connections)
stats = websocket_manager.get_stats()
user_connections = websocket_manager.get_user_connections(user_id)
assert len(user_connections) == 0, "formatted_string"

@pytest.mark.asyncio
    async def test_legacy_interface_compatibility(self, websocket_manager, mock_websocket):
        """Test that legacy interface still works alongside new thread-safe methods."""
pass
        # Test legacy connect_user method
conn_info = await websocket_manager.connect_user("legacy_user", mock_websocket)
assert conn_info.user_id == "legacy_user"

        # Test stats work
stats = websocket_manager.get_stats()
assert stats['total_connections'] >= 1

        # Test legacy disconnect_user method
await websocket_manager.disconnect_user("legacy_user", mock_websocket)

        # Verify cleanup
final_stats = websocket_manager.get_stats()
legacy_connections = websocket_manager.get_user_connections("legacy_user")
assert len(legacy_connections) == 0, "Legacy user connections not properly cleaned up"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
