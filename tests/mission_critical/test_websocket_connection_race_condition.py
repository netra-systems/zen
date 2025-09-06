# REMOVED_SYNTAX_ERROR: '''Test WebSocket connection race conditions in staging environment.

# REMOVED_SYNTAX_ERROR: This test reproduces the critical issue where messages are sent before
# REMOVED_SYNTAX_ERROR: WebSocket connections are established, causing complete chat failure.
# REMOVED_SYNTAX_ERROR: '''

import asyncio
import pytest
from datetime import datetime
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

# REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import ( )
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
UnifiedWebSocketManager,
WebSocketConnection



# REMOVED_SYNTAX_ERROR: class TestWebSocketConnectionRaceCondition:
    # REMOVED_SYNTAX_ERROR: """Test suite for WebSocket connection race conditions."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def manager(self):
    # REMOVED_SYNTAX_ERROR: """Create a UnifiedWebSocketManager instance."""
    # REMOVED_SYNTAX_ERROR: return UnifiedWebSocketManager()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def mock_websocket(self):
    # REMOVED_SYNTAX_ERROR: """Create a mock WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: return ws

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_message_sent_before_connection_established(self, manager):
        # REMOVED_SYNTAX_ERROR: '''Test that sending message before connection fails loudly.

        # REMOVED_SYNTAX_ERROR: This reproduces the exact error seen in staging:
            # REMOVED_SYNTAX_ERROR: 'No WebSocket connections found for user startup_test_032e17dc-25d9-430e-8a74-7b87b2a70064'
            # REMOVED_SYNTAX_ERROR: '''
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user_id = "startup_test_032e17dc-25d9-430e-8a74-7b87b2a70064"
            # REMOVED_SYNTAX_ERROR: message = { )
            # REMOVED_SYNTAX_ERROR: "type": "startup_test",
            # REMOVED_SYNTAX_ERROR: "data": {"test": "data"},
            # REMOVED_SYNTAX_ERROR: "timestamp": datetime.utcnow().isoformat()
            

            # Attempt to send message with no connection
            # REMOVED_SYNTAX_ERROR: with patch.object(manager, '_store_failed_message', new_callable=AsyncMock) as mock_store:
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.unified_manager.logger') as mock_logger:
                    # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_id, message)

                    # Verify critical error was logged
                    # REMOVED_SYNTAX_ERROR: mock_logger.critical.assert_called_once()
                    # REMOVED_SYNTAX_ERROR: error_msg = mock_logger.critical.call_args[0][0]
                    # REMOVED_SYNTAX_ERROR: assert "No WebSocket connections found for user" in error_msg
                    # REMOVED_SYNTAX_ERROR: assert user_id in error_msg
                    # REMOVED_SYNTAX_ERROR: assert "startup_test" in error_msg

                    # Verify message was stored for recovery
                    # REMOVED_SYNTAX_ERROR: mock_store.assert_called_once_with(user_id, message, "no_connections")

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_connection_established_after_message_attempt(self, manager, mock_websocket):
                        # REMOVED_SYNTAX_ERROR: '''Test the staging scenario where connection is established after message send.

                        # REMOVED_SYNTAX_ERROR: Timeline:
                            # REMOVED_SYNTAX_ERROR: 1. Backend starts (Phase 3)
                            # REMOVED_SYNTAX_ERROR: 2. Startup message queued
                            # REMOVED_SYNTAX_ERROR: 3. Message send attempted -> FAILS (no connection)
                            # REMOVED_SYNTAX_ERROR: 4. WebSocket upgrade completes
                            # REMOVED_SYNTAX_ERROR: 5. Connection registered -> TOO LATE
                            # REMOVED_SYNTAX_ERROR: '''
                            # REMOVED_SYNTAX_ERROR: pass
                            # REMOVED_SYNTAX_ERROR: user_id = "test_user_staging"
                            # REMOVED_SYNTAX_ERROR: connection_id = "conn_123"
                            # REMOVED_SYNTAX_ERROR: message = {"type": "agent_started", "data": {}}

                            # Step 1-3: Try to send message (fails)
                            # REMOVED_SYNTAX_ERROR: with patch.object(manager, '_store_failed_message', new_callable=AsyncMock):
                                # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_id, message)
                                # REMOVED_SYNTAX_ERROR: assert len(manager.get_user_connections(user_id)) == 0

                                # Step 4-5: Connection established after the fact
                                # REMOVED_SYNTAX_ERROR: connection = WebSocketConnection( )
                                # REMOVED_SYNTAX_ERROR: connection_id=connection_id,
                                # REMOVED_SYNTAX_ERROR: user_id=user_id,
                                # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
                                # REMOVED_SYNTAX_ERROR: connected_at=datetime.utcnow()
                                
                                # REMOVED_SYNTAX_ERROR: await manager.add_connection(connection)

                                # Verify connection now exists but message was already lost
                                # REMOVED_SYNTAX_ERROR: assert len(manager.get_user_connections(user_id)) == 1
                                # Message never delivered to user
                                # REMOVED_SYNTAX_ERROR: mock_websocket.send_json.assert_not_called()

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_cloud_run_cold_start_timing(self, manager, mock_websocket):
                                    # REMOVED_SYNTAX_ERROR: '''Test WebSocket behavior during Cloud Run cold starts.

                                    # REMOVED_SYNTAX_ERROR: Simulates the timing issues specific to GCP Cloud Run where:
                                        # REMOVED_SYNTAX_ERROR: - Service takes time to warm up
                                        # REMOVED_SYNTAX_ERROR: - WebSocket upgrade has additional latency
                                        # REMOVED_SYNTAX_ERROR: - Messages may be queued during cold start
                                        # REMOVED_SYNTAX_ERROR: '''
                                        # REMOVED_SYNTAX_ERROR: pass
                                        # REMOVED_SYNTAX_ERROR: user_id = "cold_start_user"
                                        # REMOVED_SYNTAX_ERROR: startup_messages = [ )
                                        # REMOVED_SYNTAX_ERROR: {"type": "service_initializing", "data": {}},
                                        # REMOVED_SYNTAX_ERROR: {"type": "dependencies_loading", "data": {}},
                                        # REMOVED_SYNTAX_ERROR: {"type": "startup_complete", "data": {}}
                                        

                                        # Simulate messages queued during cold start
                                        # REMOVED_SYNTAX_ERROR: stored_messages = []
                                        # REMOVED_SYNTAX_ERROR: with patch.object(manager, '_store_failed_message', new_callable=AsyncMock) as mock_store:
                                            # REMOVED_SYNTAX_ERROR: mock_store.side_effect = lambda x: None stored_messages.append((u, m, r))

                                            # All messages fail during cold start
                                            # REMOVED_SYNTAX_ERROR: for msg in startup_messages:
                                                # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_id, msg)

                                                # Verify all messages were stored for recovery
                                                # REMOVED_SYNTAX_ERROR: assert len(stored_messages) == 3
                                                # REMOVED_SYNTAX_ERROR: for i, (stored_user, stored_msg, reason) in enumerate(stored_messages):
                                                    # REMOVED_SYNTAX_ERROR: assert stored_user == user_id
                                                    # REMOVED_SYNTAX_ERROR: assert stored_msg == startup_messages[i]
                                                    # REMOVED_SYNTAX_ERROR: assert reason == "no_connections"

                                                    # Removed problematic line: @pytest.mark.asyncio
                                                    # Removed problematic line: async def test_concurrent_connection_and_message(self, manager, mock_websocket):
                                                        # REMOVED_SYNTAX_ERROR: '''Test race condition when connection and message happen simultaneously.

                                                        # REMOVED_SYNTAX_ERROR: This can occur when:
                                                            # REMOVED_SYNTAX_ERROR: 1. Frontend establishes WebSocket
                                                            # REMOVED_SYNTAX_ERROR: 2. Backend immediately sends message
                                                            # REMOVED_SYNTAX_ERROR: 3. Race between connection registration and message send
                                                            # REMOVED_SYNTAX_ERROR: '''
                                                            # REMOVED_SYNTAX_ERROR: pass
                                                            # REMOVED_SYNTAX_ERROR: user_id = "concurrent_user"
                                                            # REMOVED_SYNTAX_ERROR: connection_id = "concurrent_conn"
                                                            # REMOVED_SYNTAX_ERROR: message = {"type": "immediate_message", "data": {}}

                                                            # Create tasks that will race
# REMOVED_SYNTAX_ERROR: async def establish_connection():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)  # Small delay to simulate network
    # REMOVED_SYNTAX_ERROR: connection = WebSocketConnection( )
    # REMOVED_SYNTAX_ERROR: connection_id=connection_id,
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
    # REMOVED_SYNTAX_ERROR: connected_at=datetime.utcnow()
    
    # REMOVED_SYNTAX_ERROR: await manager.add_connection(connection)

# REMOVED_SYNTAX_ERROR: async def send_message():
    # REMOVED_SYNTAX_ERROR: pass
    # Try to send immediately
    # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_id, message)

    # Run concurrently
    # REMOVED_SYNTAX_ERROR: with patch.object(manager, '_store_failed_message', new_callable=AsyncMock) as mock_store:
        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather( )
        # REMOVED_SYNTAX_ERROR: establish_connection(),
        # REMOVED_SYNTAX_ERROR: send_message(),
        # REMOVED_SYNTAX_ERROR: return_exceptions=True
        

        # Message likely failed due to race
        # REMOVED_SYNTAX_ERROR: if mock_store.called:
            # Connection wasn't ready in time
            # REMOVED_SYNTAX_ERROR: mock_store.assert_called_with(user_id, message, "no_connections")

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_message_recovery_after_connection(self, manager, mock_websocket):
                # REMOVED_SYNTAX_ERROR: '''Test that stored messages can be recovered after connection established.

                # REMOVED_SYNTAX_ERROR: This is the recovery mechanism that should deliver messages that
                # REMOVED_SYNTAX_ERROR: failed during the race condition.
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: user_id = "recovery_user"
                # REMOVED_SYNTAX_ERROR: connection_id = "recovery_conn"
                # REMOVED_SYNTAX_ERROR: failed_messages = [ )
                # REMOVED_SYNTAX_ERROR: {"type": "message_1", "data": {"seq": 1}},
                # REMOVED_SYNTAX_ERROR: {"type": "message_2", "data": {"seq": 2}}
                

                # Store messages that failed
                # REMOVED_SYNTAX_ERROR: if not hasattr(manager, '_message_recovery_queue'):
                    # REMOVED_SYNTAX_ERROR: manager._message_recovery_queue = {}
                    # REMOVED_SYNTAX_ERROR: manager._message_recovery_queue[user_id] = failed_messages.copy()

                    # Establish connection
                    # REMOVED_SYNTAX_ERROR: connection = WebSocketConnection( )
                    # REMOVED_SYNTAX_ERROR: connection_id=connection_id,
                    # REMOVED_SYNTAX_ERROR: user_id=user_id,
                    # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
                    # REMOVED_SYNTAX_ERROR: connected_at=datetime.utcnow()
                    
                    # REMOVED_SYNTAX_ERROR: await manager.add_connection(connection)

                    # Simulate recovery mechanism
                    # REMOVED_SYNTAX_ERROR: if user_id in manager._message_recovery_queue:
                        # REMOVED_SYNTAX_ERROR: for msg in manager._message_recovery_queue[user_id]:
                            # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_id, msg)
                            # REMOVED_SYNTAX_ERROR: manager._message_recovery_queue[user_id] = []

                            # Verify all messages were delivered
                            # REMOVED_SYNTAX_ERROR: assert mock_websocket.send_json.call_count == 2
                            # REMOVED_SYNTAX_ERROR: delivered = [call[0][0] for call in mock_websocket.send_json.call_args_list]
                            # REMOVED_SYNTAX_ERROR: assert delivered == failed_messages

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_staging_specific_timeout_handling(self, manager):
                                # REMOVED_SYNTAX_ERROR: '''Test staging-specific timeout scenarios.

                                # REMOVED_SYNTAX_ERROR: GCP staging has specific timeout characteristics:
                                    # REMOVED_SYNTAX_ERROR: - Load balancer WebSocket timeout
                                    # REMOVED_SYNTAX_ERROR: - Cloud Run request timeout
                                    # REMOVED_SYNTAX_ERROR: - Inter-service communication delays
                                    # REMOVED_SYNTAX_ERROR: '''
                                    # REMOVED_SYNTAX_ERROR: pass
                                    # REMOVED_SYNTAX_ERROR: user_id = "timeout_user"

                                    # Simulate waiting for connection with timeout
# REMOVED_SYNTAX_ERROR: async def wait_for_connection(timeout=5.0):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: start = asyncio.get_event_loop().time()
    # REMOVED_SYNTAX_ERROR: while asyncio.get_event_loop().time() - start < timeout:
        # REMOVED_SYNTAX_ERROR: if manager.get_user_connections(user_id):
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
            # REMOVED_SYNTAX_ERROR: return True
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)
            # REMOVED_SYNTAX_ERROR: return False

            # Connection never arrives within timeout
            # REMOVED_SYNTAX_ERROR: connected = await wait_for_connection(timeout=0.5)
            # REMOVED_SYNTAX_ERROR: assert not connected

            # Verify no connections exist
            # REMOVED_SYNTAX_ERROR: assert len(manager.get_user_connections(user_id)) == 0


# REMOVED_SYNTAX_ERROR: class TestWebSocketConnectionRetryLogic:
    # REMOVED_SYNTAX_ERROR: """Test the proposed retry logic for connection establishment."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_retry_logic_success_on_second_attempt(self):
        # REMOVED_SYNTAX_ERROR: """Test that retry logic succeeds when connection established on retry."""
        # REMOVED_SYNTAX_ERROR: manager = UnifiedWebSocketManager()
        # REMOVED_SYNTAX_ERROR: user_id = "retry_user"
        # REMOVED_SYNTAX_ERROR: message = {"type": "test_message"}
        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()

        # Setup: No connection initially, then connection on second check
        # REMOVED_SYNTAX_ERROR: attempt_count = 0
        # REMOVED_SYNTAX_ERROR: original_get_connections = manager.get_user_connections

# REMOVED_SYNTAX_ERROR: def mock_get_connections(uid):
    # REMOVED_SYNTAX_ERROR: nonlocal attempt_count
    # REMOVED_SYNTAX_ERROR: attempt_count += 1
    # REMOVED_SYNTAX_ERROR: if attempt_count == 1:
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return set()  # First attempt: no connection
        # REMOVED_SYNTAX_ERROR: else:
            # REMOVED_SYNTAX_ERROR: return {"conn_123"}  # Second attempt: connection exists

            # REMOVED_SYNTAX_ERROR: with patch.object(manager, 'get_user_connections', side_effect=mock_get_connections):
                # REMOVED_SYNTAX_ERROR: with patch.object(manager, 'get_connection') as mock_get_conn:
                    # Setup connection for second attempt
                    # REMOVED_SYNTAX_ERROR: mock_get_conn.return_value = WebSocketConnection( )
                    # REMOVED_SYNTAX_ERROR: connection_id="conn_123",
                    # REMOVED_SYNTAX_ERROR: user_id=user_id,
                    # REMOVED_SYNTAX_ERROR: websocket=mock_ws,
                    # REMOVED_SYNTAX_ERROR: connected_at=datetime.utcnow()
                    

                    # This should retry and succeed
                    # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_id, message)

                    # Verify message was sent after retry
                    # REMOVED_SYNTAX_ERROR: mock_ws.send_json.assert_called_once_with(message)

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_retry_logic_all_attempts_fail(self):
                        # REMOVED_SYNTAX_ERROR: """Test that retry logic handles complete failure gracefully."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: manager = UnifiedWebSocketManager()
                        # REMOVED_SYNTAX_ERROR: user_id = "always_fail_user"
                        # REMOVED_SYNTAX_ERROR: message = {"type": "doomed_message"}

                        # No connection ever appears
                        # REMOVED_SYNTAX_ERROR: with patch.object(manager, 'get_user_connections', return_value=set()):
                            # REMOVED_SYNTAX_ERROR: with patch.object(manager, '_store_failed_message', new_callable=AsyncMock) as mock_store:
                                # REMOVED_SYNTAX_ERROR: await manager.send_to_user(user_id, message)

                                # Verify message was stored after all retries failed
                                # REMOVED_SYNTAX_ERROR: mock_store.assert_called_once_with(user_id, message, "no_connections")


                                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                    # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])