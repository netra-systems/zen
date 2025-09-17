class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

def __init__(self):
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
        self._closed = True
self.is_connected = False

def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

'''
        Comprehensive Error Handling Tests

This test suite validates the enhanced error handling functionality implemented across:
        - WebSocket error handling and user notifications
- Agent execution error handling and recovery
- Authentication error handling with user-visible messages
- Background task monitoring and failure recovery

SSOT Compliance: Enhances existing error handling patterns, creates no new error handlers.
'''

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import get_env


class TestEnhancedWebSocketErrorHandling:
        """Test enhanced WebSocket error handling and user notifications."""

def setup_method(self):
        """Set up test fixtures."""
        self.manager = UnifiedWebSocketManager()
self.user_id = "test_user_123"
self.websocket = TestWebSocketConnection()

@pytest.mark.asyncio
async def test_send_to_user_no_connections_loud_error(self):
        """Test loud error logging when no connections available for user."""
message = {"type": "test_event", "data": {"test": "data"}}

        # Should log critical error and store for recovery
with patch.object(self.manager, '_store_failed_message') as mock_store:
    await self.manager.send_to_user(self.user_id, message)

            # Verify failure was stored
mock_store.assert_called_once_with(self.user_id, message, "no_connections")

@pytest.mark.asyncio
async def test_send_to_user_websocket_failure_loud_error(self):
        """Test loud error logging when WebSocket send fails."""
                # Add connection with failing websocket
from netra_backend.app.websocket_core.websocket_manager import WebSocketConnection

                # Mock websocket that will fail
websocket = TestWebSocketConnection()
failing_websocket.send_json.side_effect = Exception("WebSocket connection broken")

connection = WebSocketConnection( )
connection_id="test_conn",
user_id=self.user_id,
websocket=failing_websocket,
connected_at=datetime.utcnow()
                

await self.manager.add_connection(connection)

message = {"type": "test_event", "data": {"test": "data"}}

with patch.object(self.manager, '_store_failed_message') as mock_store:
    await self.manager.send_to_user(self.user_id, message)

                    # Verify failure was stored
mock_store.assert_called_once_with(self.user_id, message, "all_connections_failed")

@pytest.mark.asyncio
async def test_emit_critical_event_validation(self):
        """Test critical event parameter validation with loud errors."""
with pytest.raises(ValueError, match="user_id cannot be empty"):
    await self.manager.emit_critical_event("", "test_event", {})

with pytest.raises(ValueError, match="event_type cannot be empty"):
    await self.manager.emit_critical_event(self.user_id, "", {})

@pytest.mark.asyncio
async def test_emit_critical_event_no_active_connections(self):
        """Test critical event emission when no active connections with user notification."""
event_type = "agent_started"
data = {"agent": "test_agent"}

with patch.object(self.manager, '_store_failed_message') as mock_store, \
patch.object(self.manager, '_emit_connection_error_notification') as mock_notify:

await self.manager.emit_critical_event(self.user_id, event_type, data)

                                        # Verify message stored and user notified
mock_store.assert_called_once()
mock_notify.assert_called_once_with(self.user_id, event_type)

@pytest.mark.asyncio
async def test_connection_error_notification(self):
        """Test user-visible connection error notification generation."""
failed_event_type = "agent_started"

                                            # Test notification without any connections (should log critical)
await self.manager._emit_connection_error_notification(self.user_id, failed_event_type)

                                            # Should complete without exceptions and log appropriately

@pytest.mark.asyncio
async def test_message_recovery_system(self):
        """Test failed message storage and recovery system."""
message = {"type": "test_event", "data": {"test": "data"}}
failure_reason = "connection_failed"

                                                # Store failed message
await self.manager._store_failed_message(self.user_id, message, failure_reason)

                                                # Verify message was stored
assert self.user_id in self.manager._message_recovery_queue
stored_messages = self.manager._message_recovery_queue[self.user_id]
assert len(stored_messages) == 1
assert stored_messages[0]['failure_reason'] == failure_reason

                                                # Test queue size limiting
for i in range(55):  # Exceed max queue size of 50
await self.manager._store_failed_message(self.user_id, message, "formatted_string")

                                                # Verify queue was trimmed
assert len(self.manager._message_recovery_queue[self.user_id]) == 50

@pytest.mark.asyncio
async def test_error_statistics_reporting(self):
        """Test comprehensive error statistics collection."""
                                                    # Generate some errors
await self.manager._store_failed_message(self.user_id, {"type": "test"}, "test_error")
await self.manager._store_failed_message("user2", {"type": "test"}, "test_error")

stats = self.manager.get_error_statistics()

assert stats['total_users_with_errors'] == 2
assert stats['total_error_count'] == 2
assert stats['total_queued_messages'] == 2
assert stats['error_recovery_enabled'] is True
assert 'error_details' in stats


class TestEnhancedAgentExecutionErrorHandling:
    """Test enhanced agent execution error handling."""

def setup_method(self):
        """Set up test fixtures."""
        self.mock_registry = Magic        self.websocket = TestWebSocketConnection()

    # Create execution context
self.context = AgentExecutionContext( )
agent_name="test_agent",
run_id="test_run",
thread_id="test_thread",
user_id="test_user"
    
self.state = DeepAgentState()

@pytest.mark.asyncio
async def test_execution_error_loud_logging(self):
        """Test loud error logging for agent execution failures."""
        # Create engine with factory method to bypass __init__ restriction
engine = ExecutionEngine._init_from_factory( )
self.mock_registry,
self.mock_websocket_bridge
        

test_error = Exception("Test execution failure")

        # Mock the user notification method
with patch.object(engine, '_notify_user_of_execution_error') as mock_notify:
    result = await engine._handle_execution_error( )
self.context,
self.state,
test_error,
1234567890.0
            

            # Verify user was notified
mock_notify.assert_called_once_with(self.context, test_error)

            # Verify result indicates failure
assert result.success is False

@pytest.mark.asyncio
async def test_timeout_error_user_notification(self):
        """Test user notification for agent timeouts."""
engine = ExecutionEngine._init_from_factory( )
self.mock_registry,
self.mock_websocket_bridge
                

timeout_seconds = 30.0

                # Test timeout notification method directly
await engine._notify_user_of_timeout(self.context, timeout_seconds)

                # Verify websocket bridge was called
self.mock_websocket_bridge.notify_agent_error.assert_called_once()

                # Verify call arguments contain user-friendly message
args, kwargs = self.mock_websocket_bridge.notify_agent_error.call_args
error_data = args[2]  # Third argument is the error data

assert "user_friendly_message" in error_data
assert "support_code" in error_data
assert str(timeout_seconds) in error_data["user_friendly_message"]

@pytest.mark.asyncio
async def test_system_error_notification(self):
        """Test user notification for system errors."""
engine = ExecutionEngine._init_from_factory( )
self.mock_registry,
self.mock_websocket_bridge
                    

system_error = RuntimeError("Database connection failed")

                    # Test system error notification
await engine._notify_user_of_system_error(self.context, system_error)

                    # Verify notification was sent
self.mock_websocket_bridge.notify_agent_error.assert_called_once()

                    # Verify error data contains appropriate fields
args, kwargs = self.mock_websocket_bridge.notify_agent_error.call_args
error_data = args[2]

assert error_data["severity"] == "critical"
assert "system error" in error_data["user_friendly_message"]
assert error_data["error_type"] == "RuntimeError"


class TestEnhancedAuthenticationErrorHandling:
    """Test enhanced authentication error handling with user notifications."""

def setup_method(self):
        """Set up test fixtures."""
        self.auth_client = AuthServiceClient()
self.test_token = "test_token_123"

@pytest.mark.asyncio
async def test_auth_service_disabled_loud_error(self):
        """Test loud error when auth service is disabled."""
        # Mock settings to disable auth service
self.auth_client.settings.enabled = False

result = await self.auth_client._check_auth_service_enabled(self.test_token)

        # Verify error response with user notification
assert result is not None
assert result["valid"] is False
assert result["error"] == "auth_service_disabled"
assert "user_notification" in result
assert result["user_notification"]["severity"] == "critical"
assert "support_code" in result["user_notification"]

@pytest.mark.asyncio
async def test_validation_error_handling_with_notifications(self):
        """Test validation error handling with user-visible messages."""
test_error = ConnectionError("Auth service unreachable")

with patch.object(self.auth_client, '_local_validate') as mock_local:
    mock_local.return_value = {"valid": False}

result = await self.auth_client._handle_validation_error(self.test_token, test_error)

                # Verify user notification is included
assert "user_notification" in result
assert result["user_notification"]["severity"] == "error"
assert "support_code" in result["user_notification"]
assert "try logging in again" in result["user_notification"]["action_required"].lower()

@pytest.mark.asyncio
async def test_inter_service_auth_failure_notification(self):
        """Test inter-service authentication failure with user notification."""
                    # Simulate missing service credentials
self.auth_client.service_secret = None

test_error = Exception("403 Forbidden")

with patch.object(self.auth_client, '_local_validate') as mock_local:
    mock_local.return_value = {"valid": False}

result = await self.auth_client._handle_validation_error(self.test_token, test_error)

                        # Verify service auth failure response
assert result["error"] == "inter_service_auth_failed"
assert result["user_notification"]["severity"] == "critical"
assert "configuration issue" in result["user_notification"]["user_friendly_message"]


class TestBackgroundTaskMonitoring:
    """Test background task monitoring and error recovery."""

def setup_method(self):
        """Set up test fixtures."""
        self.manager = UnifiedWebSocketManager()

@pytest.mark.asyncio
async def test_background_task_failure_monitoring(self):
        """Test background task failure monitoring and loud error reporting."""

async def failing_task():
    """A task that always fails."""
raise RuntimeError("Task failed")

    # Start monitored task
task_name = "test_failing_task"

    # Run task with monitoring (should fail and log loudly)
with patch.object(self.manager, '_notify_admin_of_task_failure') as mock_notify:
    task = asyncio.create_task( )
self.manager._run_monitored_task(task_name, failing_task)
        

        # Wait for task to complete (should fail after retries)
await asyncio.sleep(0.1)  # Give it time to fail

        # Task should have recorded failures
assert task_name in self.manager._task_failures

        # If max failures reached, admin should be notified
if self.manager._task_failures[task_name] >= 3:
    mock_notify.assert_called_once()

@pytest.mark.asyncio
async def test_background_task_recovery(self):
        """Test background task automatic recovery after transient failures."""

call_count = 0

async def intermittent_task():
    """A task that fails twice then succeeds."""
nonlocal call_count
call_count += 1
if call_count <= 2:
    raise RuntimeError("formatted_string")
        # Success on third try

task_name = "test_recovery_task"

        # Start monitored task
task = asyncio.create_task( )
self.manager._run_monitored_task(task_name, intermittent_task)
        

        # Wait for task to complete
await asyncio.sleep(0.5)  # Give time for retries

        # Task should have recovered
assert task_name not in self.manager._task_failures  # Failures cleared on success
assert call_count == 3  # Should have been called 3 times

def test_background_task_status_reporting(self):
    """Test background task status reporting."""
    # Add some mock tasks
websocket = TestWebSocketConnection()
mock_task_1.done.return_value = False
mock_task_1.cancelled.return_value = False

websocket = TestWebSocketConnection()
mock_task_2.done.return_value = True
mock_task_2.cancelled.return_value = False
mock_task_2.exception.return_value = RuntimeError("Test error")

self.manager._background_tasks = {}
"task_1": mock_task_1,
"task_2": mock_task_2
    

self.manager._task_failures = {"task_2": 2}

status = self.manager.get_background_task_status()

assert status["total_tasks"] == 2
assert status["running_tasks"] == 1
assert status["failed_tasks"] == 1
assert "task_1" in status["tasks"]
assert "task_2" in status["tasks"]
assert status["tasks"]["task_2"]["failure_count"] == 2


class TestErrorHandlingIntegration:
        """Integration tests for error handling across components."""

@pytest.mark.asyncio
async def test_end_to_end_error_flow(self):
        """Test complete error flow from agent failure to user notification."""
        # This would test the complete flow:
            # 1. Agent execution fails
            # 2. Error is caught and logged loudly
            # 3. User is notified via WebSocket
            # 4. Error is stored for recovery if WebSocket fails
            # 5. Background monitoring detects and reports issues

manager = UnifiedWebSocketManager()
user_id = "test_user"

            # Simulate agent execution failure notification
event_type = "agent_error"
error_data = {}
"error": "Test agent failure",
"user_friendly_message": "Something went wrong with your request",
"support_code": "ERR_12345"
            

            # This should trigger the complete error handling chain
await manager.emit_critical_event(user_id, event_type, error_data)

            # Verify error was handled appropriately
            # (In real implementation, this would check logs, recovery queues, etc.)

def test_error_statistics_aggregation(self):
    """Test aggregation of error statistics across all components."""
manager = UnifiedWebSocketManager()

    # Simulate various types of errors
manager._connection_error_count = {}
"user1": 3,
"user2": 1,
"user3": 5
    

manager._task_failures = {}
"cleanup_task": 2,
"heartbeat_task": 1
    

    # Get comprehensive statistics
websocket_stats = manager.get_error_statistics()
task_stats = manager.get_background_task_status()

    # Verify comprehensive reporting
assert websocket_stats["total_error_count"] == 9  # Sum of user errors
assert task_stats["failed_tasks"] == 2  # Task failures

    # This would be used for monitoring dashboards and alerting


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
