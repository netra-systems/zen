'''Test WebSocket connection race conditions in staging environment.

This test reproduces the critical issue where messages are sent before
WebSocket connections are established, causing complete chat failure.
'''

import asyncio
import pytest
from datetime import datetime
from typing import Dict, Any
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core.websocket_manager import ( )
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
UnifiedWebSocketManager,
WebSocketConnection



class TestWebSocketConnectionRaceCondition:
    """Test suite for WebSocket connection race conditions."""

    @pytest.fixture
    def manager(self):
        """Create a UnifiedWebSocketManager instance."""
        return UnifiedWebSocketManager()

        @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        pass
        websocket = TestWebSocketConnection()
        return ws

@pytest.mark.asyncio
    async def test_message_sent_before_connection_established(self, manager):
'''Test that sending message before connection fails loudly.

This reproduces the exact error seen in staging:
'No WebSocket connections found for user startup_test_032e17dc-25d9-430e-8a74-7b87b2a70064'
'''
pass
user_id = "startup_test_032e17dc-25d9-430e-8a74-7b87b2a70064"
message = { )
"type": "startup_test",
"data": {"test": "data"},
"timestamp": datetime.utcnow().isoformat()
            

            # Attempt to send message with no connection
with patch.object(manager, '_store_failed_message', new_callable=AsyncMock) as mock_store:
with patch('netra_backend.app.websocket_core.unified_manager.logger') as mock_logger:
await manager.send_to_user(user_id, message)

                    # Verify critical error was logged
mock_logger.critical.assert_called_once()
error_msg = mock_logger.critical.call_args[0][0]
assert "No WebSocket connections found for user" in error_msg
assert user_id in error_msg
assert "startup_test" in error_msg

                    # Verify message was stored for recovery
mock_store.assert_called_once_with(user_id, message, "no_connections")

@pytest.mark.asyncio
    async def test_connection_established_after_message_attempt(self, manager, mock_websocket):
'''Test the staging scenario where connection is established after message send.

Timeline:
1. Backend starts (Phase 3)
2. Startup message queued
3. Message send attempted -> FAILS (no connection)
4. WebSocket upgrade completes
5. Connection registered -> TOO LATE
'''
pass
user_id = "test_user_staging"
connection_id = "conn_123"
message = {"type": "agent_started", "data": {}}

                            # Step 1-3: Try to send message (fails)
with patch.object(manager, '_store_failed_message', new_callable=AsyncMock):
await manager.send_to_user(user_id, message)
assert len(manager.get_user_connections(user_id)) == 0

                                # Step 4-5: Connection established after the fact
connection = WebSocketConnection( )
connection_id=connection_id,
user_id=user_id,
websocket=mock_websocket,
connected_at=datetime.utcnow()
                                
await manager.add_connection(connection)

                                # Verify connection now exists but message was already lost
assert len(manager.get_user_connections(user_id)) == 1
                                # Message never delivered to user
mock_websocket.send_json.assert_not_called()

@pytest.mark.asyncio
    async def test_cloud_run_cold_start_timing(self, manager, mock_websocket):
'''Test WebSocket behavior during Cloud Run cold starts.

Simulates the timing issues specific to GCP Cloud Run where:
- Service takes time to warm up
- WebSocket upgrade has additional latency
- Messages may be queued during cold start
'''
pass
user_id = "cold_start_user"
startup_messages = [ )
{"type": "service_initializing", "data": {}},
{"type": "dependencies_loading", "data": {}},
{"type": "startup_complete", "data": {}}
                                        

                                        # Simulate messages queued during cold start
stored_messages = []
with patch.object(manager, '_store_failed_message', new_callable=AsyncMock) as mock_store:
mock_store.side_effect = lambda x: None stored_messages.append((u, m, r))

                                            # All messages fail during cold start
for msg in startup_messages:
await manager.send_to_user(user_id, msg)

                                                # Verify all messages were stored for recovery
assert len(stored_messages) == 3
for i, (stored_user, stored_msg, reason) in enumerate(stored_messages):
assert stored_user == user_id
assert stored_msg == startup_messages[i]
assert reason == "no_connections"

@pytest.mark.asyncio
    async def test_concurrent_connection_and_message(self, manager, mock_websocket):
'''Test race condition when connection and message happen simultaneously.

This can occur when:
1. Frontend establishes WebSocket
2. Backend immediately sends message
3. Race between connection registration and message send
'''
pass
user_id = "concurrent_user"
connection_id = "concurrent_conn"
message = {"type": "immediate_message", "data": {}}

                                                            # Create tasks that will race
async def establish_connection():
pass
await asyncio.sleep(0.01)  # Small delay to simulate network
connection = WebSocketConnection( )
connection_id=connection_id,
user_id=user_id,
websocket=mock_websocket,
connected_at=datetime.utcnow()
    
await manager.add_connection(connection)

async def send_message():
pass
    # Try to send immediately
await manager.send_to_user(user_id, message)

    # Run concurrently
with patch.object(manager, '_store_failed_message', new_callable=AsyncMock) as mock_store:
results = await asyncio.gather( )
establish_connection(),
send_message(),
return_exceptions=True
        

        # Message likely failed due to race
if mock_store.called:
            # Connection wasn't ready in time
mock_store.assert_called_with(user_id, message, "no_connections")

@pytest.mark.asyncio
    async def test_message_recovery_after_connection(self, manager, mock_websocket):
'''Test that stored messages can be recovered after connection established.

This is the recovery mechanism that should deliver messages that
failed during the race condition.
'''
pass
user_id = "recovery_user"
connection_id = "recovery_conn"
failed_messages = [ )
{"type": "message_1", "data": {"seq": 1}},
{"type": "message_2", "data": {"seq": 2}}
                

                # Store messages that failed
if not hasattr(manager, '_message_recovery_queue'):
manager._message_recovery_queue = {}
manager._message_recovery_queue[user_id] = failed_messages.copy()

                    # Establish connection
connection = WebSocketConnection( )
connection_id=connection_id,
user_id=user_id,
websocket=mock_websocket,
connected_at=datetime.utcnow()
                    
await manager.add_connection(connection)

                    # Simulate recovery mechanism
if user_id in manager._message_recovery_queue:
for msg in manager._message_recovery_queue[user_id]:
await manager.send_to_user(user_id, msg)
manager._message_recovery_queue[user_id] = []

                            # Verify all messages were delivered
assert mock_websocket.send_json.call_count == 2
delivered = [call[0][0] for call in mock_websocket.send_json.call_args_list]
assert delivered == failed_messages

@pytest.mark.asyncio
    async def test_staging_specific_timeout_handling(self, manager):
'''Test staging-specific timeout scenarios.

GCP staging has specific timeout characteristics:
- Load balancer WebSocket timeout
- Cloud Run request timeout
- Inter-service communication delays
'''
pass
user_id = "timeout_user"

                                    # Simulate waiting for connection with timeout
async def wait_for_connection(timeout=5.0):
pass
start = asyncio.get_event_loop().time()
while asyncio.get_event_loop().time() - start < timeout:
if manager.get_user_connections(user_id):
await asyncio.sleep(0)
return True
await asyncio.sleep(0.1)
return False

            # Connection never arrives within timeout
connected = await wait_for_connection(timeout=0.5)
assert not connected

            # Verify no connections exist
assert len(manager.get_user_connections(user_id)) == 0


class TestWebSocketConnectionRetryLogic:
        """Test the proposed retry logic for connection establishment."""

@pytest.mark.asyncio
    async def test_retry_logic_success_on_second_attempt(self):
"""Test that retry logic succeeds when connection established on retry."""
manager = UnifiedWebSocketManager()
user_id = "retry_user"
message = {"type": "test_message"}
websocket = TestWebSocketConnection()

        # Setup: No connection initially, then connection on second check
attempt_count = 0
original_get_connections = manager.get_user_connections

def mock_get_connections(uid):
nonlocal attempt_count
attempt_count += 1
if attempt_count == 1:
await asyncio.sleep(0)
return set()  # First attempt: no connection
else:
return {"conn_123"}  # Second attempt: connection exists

with patch.object(manager, 'get_user_connections', side_effect=mock_get_connections):
with patch.object(manager, 'get_connection') as mock_get_conn:
                    # Setup connection for second attempt
mock_get_conn.return_value = WebSocketConnection( )
connection_id="conn_123",
user_id=user_id,
websocket=mock_ws,
connected_at=datetime.utcnow()
                    

                    # This should retry and succeed
await manager.send_to_user(user_id, message)

                    # Verify message was sent after retry
mock_ws.send_json.assert_called_once_with(message)

@pytest.mark.asyncio
    async def test_retry_logic_all_attempts_fail(self):
"""Test that retry logic handles complete failure gracefully."""
pass
manager = UnifiedWebSocketManager()
user_id = "always_fail_user"
message = {"type": "doomed_message"}

                        # No connection ever appears
with patch.object(manager, 'get_user_connections', return_value=set()):
with patch.object(manager, '_store_failed_message', new_callable=AsyncMock) as mock_store:
await manager.send_to_user(user_id, message)

                                # Verify message was stored after all retries failed
mock_store.assert_called_once_with(user_id, message, "no_connections")


if __name__ == "__main__":
