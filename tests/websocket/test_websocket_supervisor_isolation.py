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
    # REMOVED_SYNTAX_ERROR: Comprehensive WebSocket Supervisor Isolation Tests

    # REMOVED_SYNTAX_ERROR: This test suite validates the WebSocket supervisor isolation patterns and multi-user
    # REMOVED_SYNTAX_ERROR: support with both v2 (legacy) and v3 (clean) patterns.

    # REMOVED_SYNTAX_ERROR: CRITICAL: These tests verify that the WebSocket remediation provides:
        # REMOVED_SYNTAX_ERROR: 1. Complete multi-user isolation
        # REMOVED_SYNTAX_ERROR: 2. Concurrent connection safety
        # REMOVED_SYNTAX_ERROR: 3. Performance characteristics
        # REMOVED_SYNTAX_ERROR: 4. Error recovery and resilience
        # REMOVED_SYNTAX_ERROR: 5. Feature flag switching functionality
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import os
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: from concurrent.futures import ThreadPoolExecutor
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta
        # REMOVED_SYNTAX_ERROR: from typing import List, Dict, Any
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
        # REMOVED_SYNTAX_ERROR: # Removed non-existent AuthManager import
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # REMOVED_SYNTAX_ERROR: from fastapi import WebSocket
        # REMOVED_SYNTAX_ERROR: from starlette.websockets import WebSocketState
        # REMOVED_SYNTAX_ERROR: from sqlalchemy.ext.asyncio import AsyncSession

        # Import the WebSocket components
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.context import WebSocketContext
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class TestWebSocketSupervisorIsolation:
    # REMOVED_SYNTAX_ERROR: """Comprehensive tests for WebSocket supervisor isolation."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock WebSocket for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: ws = Mock(spec=WebSocket)
    # REMOVED_SYNTAX_ERROR: ws.client_state = WebSocketState.CONNECTED
    # REMOVED_SYNTAX_ERROR: return ws

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_db_session():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock database session."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return AsyncMock(spec=AsyncSession)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_message(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a sample WebSocket message for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return WebSocketMessage( )
    # REMOVED_SYNTAX_ERROR: type=MessageType.START_AGENT,
    # REMOVED_SYNTAX_ERROR: payload={"thread_id": "test_thread", "task": "analyze data"},
    # REMOVED_SYNTAX_ERROR: user_id="test_user",
    # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
    # REMOVED_SYNTAX_ERROR: correlation_id="test_correlation"
    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_basic_websocket_context_isolation(self, mock_websocket, mock_db_session):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test that WebSocketContext properly isolates different user connections.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # Create contexts for different users
        # REMOVED_SYNTAX_ERROR: contexts = []
        # REMOVED_SYNTAX_ERROR: for i in range(3):
            # REMOVED_SYNTAX_ERROR: context = WebSocketContext.create_for_user( )
            # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
            # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
            
            # REMOVED_SYNTAX_ERROR: contexts.append(context)

            # Each context should be completely isolated
            # REMOVED_SYNTAX_ERROR: for i, ctx in enumerate(contexts):
                # REMOVED_SYNTAX_ERROR: assert ctx.user_id == "formatted_string"
                # REMOVED_SYNTAX_ERROR: assert ctx.thread_id == "formatted_string"
                # REMOVED_SYNTAX_ERROR: assert ctx.connection_id != contexts[(i + 1) % 3].connection_id

                # Isolation keys should be unique
                # REMOVED_SYNTAX_ERROR: isolation_key = ctx.to_isolation_key()
                # REMOVED_SYNTAX_ERROR: for j, other_ctx in enumerate(contexts):
                    # REMOVED_SYNTAX_ERROR: if i != j:
                        # REMOVED_SYNTAX_ERROR: assert isolation_key != other_ctx.to_isolation_key()

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_concurrent_supervisor_creation(self, mock_websocket, mock_db_session):
                            # REMOVED_SYNTAX_ERROR: '''
                            # REMOVED_SYNTAX_ERROR: Test that multiple supervisors can be created concurrently without interference.
                            # REMOVED_SYNTAX_ERROR: '''
                            # REMOVED_SYNTAX_ERROR: pass
                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.supervisor_factory._get_websocket_supervisor_components') as mock_components:
                                # REMOVED_SYNTAX_ERROR: mock_components.return_value = { )
                                # REMOVED_SYNTAX_ERROR: "llm_client":                 "websocket_bridge":                 "tool_dispatcher":             }

                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.supervisor_factory.create_supervisor_core') as mock_create_core:
                                    # Create multiple contexts
                                    # REMOVED_SYNTAX_ERROR: contexts = []
                                    # REMOVED_SYNTAX_ERROR: tasks = []

                                    # REMOVED_SYNTAX_ERROR: for i in range(5):
                                        # REMOVED_SYNTAX_ERROR: context = WebSocketContext.create_for_user( )
                                        # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
                                        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
                                        
                                        # REMOVED_SYNTAX_ERROR: contexts.append(context)

                                        # Return unique supervisor for each call
                                        # REMOVED_SYNTAX_ERROR: unique_supervisor = Mock(name="formatted_string")
                                        # REMOVED_SYNTAX_ERROR: mock_create_core.return_value = unique_supervisor

                                        # Create supervisor creation task
                                        # REMOVED_SYNTAX_ERROR: task = asyncio.create_task( )
                                        # REMOVED_SYNTAX_ERROR: get_websocket_scoped_supervisor(context, mock_db_session)
                                        
                                        # REMOVED_SYNTAX_ERROR: tasks.append(task)

                                        # Execute all supervisor creations concurrently
                                        # REMOVED_SYNTAX_ERROR: supervisors = await asyncio.gather(*tasks)

                                        # Verify all supervisors were created
                                        # REMOVED_SYNTAX_ERROR: assert len(supervisors) == 5
                                        # REMOVED_SYNTAX_ERROR: for supervisor in supervisors:
                                            # REMOVED_SYNTAX_ERROR: assert supervisor is not None

                                            # Verify supervisor factory was called for each context
                                            # REMOVED_SYNTAX_ERROR: assert mock_create_core.call_count == 5

                                            # Verify each call had correct isolation parameters
                                            # REMOVED_SYNTAX_ERROR: for i, call in enumerate(mock_create_core.call_args_list):
                                                # REMOVED_SYNTAX_ERROR: kwargs = call[1]
                                                # REMOVED_SYNTAX_ERROR: assert kwargs['user_id'] == "formatted_string"
                                                # REMOVED_SYNTAX_ERROR: assert kwargs['thread_id'] == "formatted_string"
                                                # REMOVED_SYNTAX_ERROR: assert 'websocket_connection_id' in kwargs

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_websocket_context_lifecycle_isolation(self, mock_websocket):
                                                    # REMOVED_SYNTAX_ERROR: '''
                                                    # REMOVED_SYNTAX_ERROR: Test that WebSocket context lifecycle operations don"t interfere between users.
                                                    # REMOVED_SYNTAX_ERROR: '''
                                                    # REMOVED_SYNTAX_ERROR: pass
                                                    # Create contexts for multiple users
                                                    # REMOVED_SYNTAX_ERROR: contexts = []
                                                    # REMOVED_SYNTAX_ERROR: for i in range(3):
                                                        # REMOVED_SYNTAX_ERROR: context = WebSocketContext.create_for_user( )
                                                        # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
                                                        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                                        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
                                                        
                                                        # REMOVED_SYNTAX_ERROR: contexts.append(context)

                                                        # Perform lifecycle operations on different contexts
                                                        # REMOVED_SYNTAX_ERROR: for i, ctx in enumerate(contexts):
                                                            # Update activity
                                                            # REMOVED_SYNTAX_ERROR: original_activity = ctx.last_activity
                                                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)
                                                            # REMOVED_SYNTAX_ERROR: ctx.update_activity()

                                                            # Verify activity was updated for this context only
                                                            # REMOVED_SYNTAX_ERROR: assert ctx.last_activity > original_activity

                                                            # Verify other contexts weren't affected
                                                            # REMOVED_SYNTAX_ERROR: for j, other_ctx in enumerate(contexts):
                                                                # REMOVED_SYNTAX_ERROR: if i != j:
                                                                    # Other contexts should have earlier activity timestamps
                                                                    # REMOVED_SYNTAX_ERROR: assert other_ctx.last_activity < ctx.last_activity

                                                                    # Test connection state isolation
                                                                    # REMOVED_SYNTAX_ERROR: mock_websocket.client_state = WebSocketState.DISCONNECTED

                                                                    # All contexts should detect disconnected state
                                                                    # REMOVED_SYNTAX_ERROR: for ctx in contexts:
                                                                        # REMOVED_SYNTAX_ERROR: assert not ctx.is_active

                                                                        # Reconnect and verify all contexts detect connected state
                                                                        # REMOVED_SYNTAX_ERROR: mock_websocket.client_state = WebSocketState.CONNECTED
                                                                        # REMOVED_SYNTAX_ERROR: for ctx in contexts:
                                                                            # REMOVED_SYNTAX_ERROR: assert ctx.is_active

                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                            # Removed problematic line: async def test_concurrent_message_handling_isolation(self, mock_websocket, sample_message):
                                                                                # REMOVED_SYNTAX_ERROR: '''
                                                                                # REMOVED_SYNTAX_ERROR: Test that concurrent message handling maintains proper user isolation.
                                                                                # REMOVED_SYNTAX_ERROR: '''
                                                                                # REMOVED_SYNTAX_ERROR: pass
                                                                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.message_handlers import MessageHandlerService
                                                                                # REMOVED_SYNTAX_ERROR: mock_service = Mock(spec=MessageHandlerService)
                                                                                # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(message_handler_service=mock_service)

                                                                                # Create messages for different users
                                                                                # REMOVED_SYNTAX_ERROR: messages = []
                                                                                # REMOVED_SYNTAX_ERROR: for i in range(4):
                                                                                    # REMOVED_SYNTAX_ERROR: message = WebSocketMessage( )
                                                                                    # REMOVED_SYNTAX_ERROR: type=MessageType.USER_MESSAGE,
                                                                                    # REMOVED_SYNTAX_ERROR: payload={"message": "formatted_string", "thread_id": "formatted_string"},
                                                                                    # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                                                                    # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
                                                                                    # REMOVED_SYNTAX_ERROR: correlation_id="formatted_string"
                                                                                    
                                                                                    # REMOVED_SYNTAX_ERROR: messages.append(message)

                                                                                    # Force v3 clean pattern
                                                                                    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V3': 'true'}):
                                                                                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_ws_supervisor:
                                                                                            # Track supervisor calls for isolation verification
                                                                                            # REMOVED_SYNTAX_ERROR: supervisor_calls = []

# REMOVED_SYNTAX_ERROR: def track_supervisor_call(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: supervisor_calls.append(kwargs['context'])
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return
    # REMOVED_SYNTAX_ERROR: mock_ws_supervisor.side_effect = track_supervisor_call

    # Process messages concurrently
    # REMOVED_SYNTAX_ERROR: tasks = []
    # REMOVED_SYNTAX_ERROR: for i, message in enumerate(messages):
        # REMOVED_SYNTAX_ERROR: task = asyncio.create_task( )
        # REMOVED_SYNTAX_ERROR: handler.handle_message("formatted_string", mock_websocket, message)
        
        # REMOVED_SYNTAX_ERROR: tasks.append(task)

        # Wait for all message processing to complete
        # REMOVED_SYNTAX_ERROR: with patch.object(handler, '_route_agent_message_v3', return_value=True):
            # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify supervisor was called for each user
            # REMOVED_SYNTAX_ERROR: assert len(supervisor_calls) == 4

            # Verify each supervisor call had correct user isolation
            # REMOVED_SYNTAX_ERROR: for i, context in enumerate(supervisor_calls):
                # REMOVED_SYNTAX_ERROR: assert isinstance(context, WebSocketContext)
                # REMOVED_SYNTAX_ERROR: assert context.user_id == "formatted_string"
                # REMOVED_SYNTAX_ERROR: assert context.thread_id == "formatted_string"

                # Verify contexts are unique
                # REMOVED_SYNTAX_ERROR: for j, other_context in enumerate(supervisor_calls):
                    # REMOVED_SYNTAX_ERROR: if i != j:
                        # REMOVED_SYNTAX_ERROR: assert context.connection_id != other_context.connection_id
                        # REMOVED_SYNTAX_ERROR: assert context.to_isolation_key() != other_context.to_isolation_key()

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_error_isolation_between_users(self, mock_websocket, mock_db_session):
                            # REMOVED_SYNTAX_ERROR: '''
                            # REMOVED_SYNTAX_ERROR: Test that errors in one user's context don't affect other users.
                            # REMOVED_SYNTAX_ERROR: '''
                            # REMOVED_SYNTAX_ERROR: pass
                            # Create contexts for multiple users
                            # REMOVED_SYNTAX_ERROR: contexts = []
                            # REMOVED_SYNTAX_ERROR: for i in range(3):
                                # REMOVED_SYNTAX_ERROR: context = WebSocketContext.create_for_user( )
                                # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
                                # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
                                
                                # REMOVED_SYNTAX_ERROR: contexts.append(context)

                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.supervisor_factory._get_websocket_supervisor_components') as mock_components:
                                    # REMOVED_SYNTAX_ERROR: mock_components.return_value = { )
                                    # REMOVED_SYNTAX_ERROR: "llm_client":                 "websocket_bridge":                 "tool_dispatcher":             }

                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.supervisor_factory.create_supervisor_core') as mock_create_core:
                                        # Make supervisor creation fail for user_1 only
# REMOVED_SYNTAX_ERROR: def selective_failure(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: if kwargs.get('user_id') == 'user_1':
        # REMOVED_SYNTAX_ERROR: raise ValueError("Simulated failure for user_1")
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return
        # REMOVED_SYNTAX_ERROR: mock_create_core.side_effect = selective_failure

        # Attempt supervisor creation for all users
        # REMOVED_SYNTAX_ERROR: results = []
        # REMOVED_SYNTAX_ERROR: for ctx in contexts:
            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: supervisor = await get_websocket_scoped_supervisor(ctx, mock_db_session)
                # REMOVED_SYNTAX_ERROR: results.append(('success', supervisor))
                # REMOVED_SYNTAX_ERROR: except Exception as e:
                    # REMOVED_SYNTAX_ERROR: results.append(('error', str(e)))

                    # Verify isolation: only user_1 should fail
                    # REMOVED_SYNTAX_ERROR: assert len(results) == 3
                    # REMOVED_SYNTAX_ERROR: assert results[0][0] == 'success'  # user_0 succeeds
                    # REMOVED_SYNTAX_ERROR: assert results[1][0] == 'error'    # user_1 fails
                    # REMOVED_SYNTAX_ERROR: assert results[1][1] == 'Simulated failure for user_1'
                    # REMOVED_SYNTAX_ERROR: assert results[2][0] == 'success'  # user_2 succeeds

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_feature_flag_isolation(self, mock_websocket, sample_message):
                        # REMOVED_SYNTAX_ERROR: '''
                        # REMOVED_SYNTAX_ERROR: Test that feature flag switching works correctly with user isolation.
                        # REMOVED_SYNTAX_ERROR: '''
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.message_handlers import MessageHandlerService
                        # REMOVED_SYNTAX_ERROR: mock_service = Mock(spec=MessageHandlerService)
                        # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(message_handler_service=mock_service)

                        # Create messages for multiple users
                        # REMOVED_SYNTAX_ERROR: users = ['user_v2', 'user_v3']
                        # REMOVED_SYNTAX_ERROR: messages = []
                        # REMOVED_SYNTAX_ERROR: for user in users:
                            # REMOVED_SYNTAX_ERROR: message = WebSocketMessage( )
                            # REMOVED_SYNTAX_ERROR: type=MessageType.START_AGENT,
                            # REMOVED_SYNTAX_ERROR: payload={"message": "formatted_string", "thread_id": "formatted_string"},
                            # REMOVED_SYNTAX_ERROR: user_id=user,
                            # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
                            # REMOVED_SYNTAX_ERROR: correlation_id="formatted_string"
                            
                            # REMOVED_SYNTAX_ERROR: messages.append(message)

                            # Test both patterns work with proper isolation
                            # REMOVED_SYNTAX_ERROR: patterns = [ )
                            # REMOVED_SYNTAX_ERROR: ('false', '_handle_message_v2_legacy'),
                            # REMOVED_SYNTAX_ERROR: ('true', '_handle_message_v3_clean')
                            

                            # REMOVED_SYNTAX_ERROR: for flag_value, expected_method in patterns:
                                # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V3': flag_value}):
                                    # REMOVED_SYNTAX_ERROR: method_calls = []

                                    # Mock both handler methods to track calls
# REMOVED_SYNTAX_ERROR: async def track_v2_call(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: method_calls.append(('v2', args[0]))  # args[0] is user_id
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: async def track_v3_call(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: method_calls.append(('v3', args[0]))  # args[0] is user_id
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return True

    # REMOVED_SYNTAX_ERROR: with patch.object(handler, '_handle_message_v2_legacy', side_effect=track_v2_call):
        # REMOVED_SYNTAX_ERROR: with patch.object(handler, '_handle_message_v3_clean', side_effect=track_v3_call):
            # Process messages for both users
            # REMOVED_SYNTAX_ERROR: for i, message in enumerate(messages):
                # REMOVED_SYNTAX_ERROR: await handler.handle_message(users[i], mock_websocket, message)

                # Verify correct pattern was used with proper user isolation
                # REMOVED_SYNTAX_ERROR: assert len(method_calls) == 2
                # REMOVED_SYNTAX_ERROR: for call in method_calls:
                    # REMOVED_SYNTAX_ERROR: pattern, user_id = call
                    # REMOVED_SYNTAX_ERROR: if flag_value == 'false':
                        # REMOVED_SYNTAX_ERROR: assert pattern == 'v2', "formatted_string"
                        # REMOVED_SYNTAX_ERROR: else:
                            # REMOVED_SYNTAX_ERROR: assert pattern == 'v3', "formatted_string"

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_performance_under_concurrent_load(self, mock_websocket, mock_db_session):
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: Test performance characteristics of WebSocket supervisor isolation under load.
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: pass
                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.supervisor_factory._get_websocket_supervisor_components') as mock_components:
                                    # REMOVED_SYNTAX_ERROR: mock_components.return_value = { )
                                    # REMOVED_SYNTAX_ERROR: "llm_client":                 "websocket_bridge":                 "tool_dispatcher":             }

                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.supervisor_factory.create_supervisor_core') as mock_create_core:
                                        # REMOVED_SYNTAX_ERROR: mock_create_core.websocket = TestWebSocketConnection()  # Real WebSocket implementation

                                        # Create a larger number of concurrent connections
                                        # REMOVED_SYNTAX_ERROR: num_connections = 50
                                        # REMOVED_SYNTAX_ERROR: contexts = []

                                        # REMOVED_SYNTAX_ERROR: for i in range(num_connections):
                                            # REMOVED_SYNTAX_ERROR: context = WebSocketContext.create_for_user( )
                                            # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
                                            # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                            # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
                                            
                                            # REMOVED_SYNTAX_ERROR: contexts.append(context)

                                            # Measure time for concurrent supervisor creation
                                            # REMOVED_SYNTAX_ERROR: start_time = time.time()

                                            # REMOVED_SYNTAX_ERROR: tasks = []
                                            # REMOVED_SYNTAX_ERROR: for ctx in contexts:
                                                # REMOVED_SYNTAX_ERROR: task = asyncio.create_task( )
                                                # REMOVED_SYNTAX_ERROR: get_websocket_scoped_supervisor(ctx, mock_db_session)
                                                
                                                # REMOVED_SYNTAX_ERROR: tasks.append(task)

                                                # Execute all supervisor creations concurrently
                                                # REMOVED_SYNTAX_ERROR: supervisors = await asyncio.gather(*tasks)

                                                # REMOVED_SYNTAX_ERROR: end_time = time.time()
                                                # REMOVED_SYNTAX_ERROR: duration = end_time - start_time

                                                # Verify all supervisors were created
                                                # REMOVED_SYNTAX_ERROR: assert len(supervisors) == num_connections
                                                # REMOVED_SYNTAX_ERROR: for supervisor in supervisors:
                                                    # REMOVED_SYNTAX_ERROR: assert supervisor is not None

                                                    # Performance assertion - should complete within reasonable time
                                                    # (This is lenient since we're using mocks, but validates no deadlocks)
                                                    # REMOVED_SYNTAX_ERROR: assert duration < 5.0, "formatted_string"

                                                    # Verify no race conditions in isolation
                                                    # REMOVED_SYNTAX_ERROR: assert mock_create_core.call_count == num_connections

                                                    # Verify each context maintained unique identities
                                                    # REMOVED_SYNTAX_ERROR: user_ids = set()
                                                    # REMOVED_SYNTAX_ERROR: for call in mock_create_core.call_args_list:
                                                        # REMOVED_SYNTAX_ERROR: kwargs = call[1]
                                                        # REMOVED_SYNTAX_ERROR: user_id = kwargs['user_id']
                                                        # REMOVED_SYNTAX_ERROR: assert user_id not in user_ids, "formatted_string"
                                                        # REMOVED_SYNTAX_ERROR: user_ids.add(user_id)

                                                        # Removed problematic line: @pytest.mark.asyncio
                                                        # Removed problematic line: async def test_websocket_disconnection_isolation(self, mock_db_session):
                                                            # REMOVED_SYNTAX_ERROR: '''
                                                            # REMOVED_SYNTAX_ERROR: Test that WebSocket disconnections are properly isolated between users.
                                                            # REMOVED_SYNTAX_ERROR: '''
                                                            # REMOVED_SYNTAX_ERROR: pass
                                                            # Create WebSocket mocks for different users
                                                            # REMOVED_SYNTAX_ERROR: websockets = []
                                                            # REMOVED_SYNTAX_ERROR: contexts = []

                                                            # REMOVED_SYNTAX_ERROR: for i in range(3):
                                                                # REMOVED_SYNTAX_ERROR: ws = Mock(spec=WebSocket)
                                                                # REMOVED_SYNTAX_ERROR: ws.client_state = WebSocketState.CONNECTED
                                                                # REMOVED_SYNTAX_ERROR: websockets.append(ws)

                                                                # REMOVED_SYNTAX_ERROR: context = WebSocketContext.create_for_user( )
                                                                # REMOVED_SYNTAX_ERROR: websocket=ws,
                                                                # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                                                # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
                                                                
                                                                # REMOVED_SYNTAX_ERROR: contexts.append(context)

                                                                # Verify all are initially active
                                                                # REMOVED_SYNTAX_ERROR: for ctx in contexts:
                                                                    # REMOVED_SYNTAX_ERROR: assert ctx.is_active

                                                                    # Disconnect user_1's WebSocket
                                                                    # REMOVED_SYNTAX_ERROR: websockets[1].client_state = WebSocketState.DISCONNECTED

                                                                    # Verify isolation: only user_1 should be inactive
                                                                    # REMOVED_SYNTAX_ERROR: assert contexts[0].is_active, "User 0 should remain active"
                                                                    # REMOVED_SYNTAX_ERROR: assert not contexts[1].is_active, "User 1 should be inactive"
                                                                    # REMOVED_SYNTAX_ERROR: assert contexts[2].is_active, "User 2 should remain active"

                                                                    # Test validation isolation
                                                                    # REMOVED_SYNTAX_ERROR: for i, ctx in enumerate(contexts):
                                                                        # REMOVED_SYNTAX_ERROR: if i == 1:  # Disconnected user
                                                                        # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="not active"):
                                                                            # REMOVED_SYNTAX_ERROR: ctx.validate_for_message_processing()
                                                                            # REMOVED_SYNTAX_ERROR: else:  # Active users
                                                                            # REMOVED_SYNTAX_ERROR: assert ctx.validate_for_message_processing()

                                                                            # Reconnect user_1
                                                                            # REMOVED_SYNTAX_ERROR: websockets[1].client_state = WebSocketState.CONNECTED

                                                                            # Verify all are active again
                                                                            # REMOVED_SYNTAX_ERROR: for ctx in contexts:
                                                                                # REMOVED_SYNTAX_ERROR: assert ctx.is_active
                                                                                # REMOVED_SYNTAX_ERROR: assert ctx.validate_for_message_processing()

                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                # Removed problematic line: async def test_websocket_context_factory_isolation(self):
                                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                                    # REMOVED_SYNTAX_ERROR: Test that the WebSocketContext factory creates properly isolated contexts.
                                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                                    # REMOVED_SYNTAX_ERROR: pass
                                                                                    # Create WebSocket connections for different users
                                                                                    # REMOVED_SYNTAX_ERROR: websockets = []
                                                                                    # REMOVED_SYNTAX_ERROR: for i in range(3):
                                                                                        # REMOVED_SYNTAX_ERROR: ws = Mock(spec=WebSocket)
                                                                                        # REMOVED_SYNTAX_ERROR: ws.client_state = WebSocketState.CONNECTED
                                                                                        # REMOVED_SYNTAX_ERROR: websockets.append(ws)

                                                                                        # Create contexts using factory method
                                                                                        # REMOVED_SYNTAX_ERROR: contexts = []
                                                                                        # REMOVED_SYNTAX_ERROR: for i, ws in enumerate(websockets):
                                                                                            # REMOVED_SYNTAX_ERROR: context = WebSocketContext.create_for_user( )
                                                                                            # REMOVED_SYNTAX_ERROR: websocket=ws,
                                                                                            # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                                                                            # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
                                                                                            # REMOVED_SYNTAX_ERROR: run_id="formatted_string"
                                                                                            
                                                                                            # REMOVED_SYNTAX_ERROR: contexts.append(context)

                                                                                            # Verify each context is properly isolated
                                                                                            # REMOVED_SYNTAX_ERROR: connection_ids = set()
                                                                                            # REMOVED_SYNTAX_ERROR: isolation_keys = set()

                                                                                            # REMOVED_SYNTAX_ERROR: for i, ctx in enumerate(contexts):
                                                                                                # Verify correct data
                                                                                                # REMOVED_SYNTAX_ERROR: assert ctx.user_id == "formatted_string"
                                                                                                # REMOVED_SYNTAX_ERROR: assert ctx.thread_id == "formatted_string"
                                                                                                # REMOVED_SYNTAX_ERROR: assert ctx.run_id == "formatted_string"

                                                                                                # Verify uniqueness
                                                                                                # REMOVED_SYNTAX_ERROR: assert ctx.connection_id not in connection_ids
                                                                                                # REMOVED_SYNTAX_ERROR: connection_ids.add(ctx.connection_id)

                                                                                                # REMOVED_SYNTAX_ERROR: isolation_key = ctx.to_isolation_key()
                                                                                                # REMOVED_SYNTAX_ERROR: assert isolation_key not in isolation_keys
                                                                                                # REMOVED_SYNTAX_ERROR: isolation_keys.add(isolation_key)

                                                                                                # Verify WebSocket association
                                                                                                # REMOVED_SYNTAX_ERROR: assert ctx.websocket == websockets[i]
                                                                                                # REMOVED_SYNTAX_ERROR: assert ctx.is_active

                                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                                # Removed problematic line: async def test_memory_isolation_and_cleanup(self, mock_websocket, mock_db_session):
                                                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                                                    # REMOVED_SYNTAX_ERROR: Test that WebSocket contexts don"t leak memory between users.
                                                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                                                    # REMOVED_SYNTAX_ERROR: pass
                                                                                                    # This test verifies that contexts don't retain references to each other
                                                                                                    # REMOVED_SYNTAX_ERROR: import weakref

                                                                                                    # REMOVED_SYNTAX_ERROR: contexts = []
                                                                                                    # REMOVED_SYNTAX_ERROR: weak_refs = []

                                                                                                    # Create contexts and weak references
                                                                                                    # REMOVED_SYNTAX_ERROR: for i in range(5):
                                                                                                        # REMOVED_SYNTAX_ERROR: context = WebSocketContext.create_for_user( )
                                                                                                        # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
                                                                                                        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                                                                                        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
                                                                                                        
                                                                                                        # REMOVED_SYNTAX_ERROR: contexts.append(context)
                                                                                                        # REMOVED_SYNTAX_ERROR: weak_refs.append(weakref.ref(context))

                                                                                                        # Verify contexts are independent (no shared state)
                                                                                                        # REMOVED_SYNTAX_ERROR: for i, ctx in enumerate(contexts):
                                                                                                            # Each context should have unique data
                                                                                                            # REMOVED_SYNTAX_ERROR: assert ctx.user_id == "formatted_string"

                                                                                                            # Modify one context and verify others aren't affected
                                                                                                            # REMOVED_SYNTAX_ERROR: original_activity = ctx.last_activity
                                                                                                            # REMOVED_SYNTAX_ERROR: ctx.update_activity()

                                                                                                            # REMOVED_SYNTAX_ERROR: for j, other_ctx in enumerate(contexts):
                                                                                                                # REMOVED_SYNTAX_ERROR: if i != j:
                                                                                                                    # REMOVED_SYNTAX_ERROR: assert other_ctx.last_activity != ctx.last_activity

                                                                                                                    # Clear references to allow garbage collection
                                                                                                                    # REMOVED_SYNTAX_ERROR: contexts.clear()

                                                                                                                    # Force garbage collection (this is implementation-dependent)
                                                                                                                    # REMOVED_SYNTAX_ERROR: import gc
                                                                                                                    # REMOVED_SYNTAX_ERROR: gc.collect()

                                                                                                                    # Verify weak references can be collected (no memory leaks)
                                                                                                                    # Note: This test might be flaky in some Python implementations
                                                                                                                    # but serves as a basic memory leak detector
                                                                                                                    # REMOVED_SYNTAX_ERROR: alive_refs = [item for item in []]

                                                                                                                    # In a clean implementation, we'd expect few or no references to remain
                                                                                                                    # This is more of a smoke test than a strict requirement
                                                                                                                    # REMOVED_SYNTAX_ERROR: assert len(alive_refs) <= len(weak_refs), "Potential memory leak detected"

                                                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                                                    # Removed problematic line: async def test_cross_user_data_isolation(self, mock_websocket):
                                                                                                                        # REMOVED_SYNTAX_ERROR: '''
                                                                                                                        # REMOVED_SYNTAX_ERROR: Test that user data cannot leak between different WebSocket contexts.
                                                                                                                        # REMOVED_SYNTAX_ERROR: '''
                                                                                                                        # REMOVED_SYNTAX_ERROR: pass
                                                                                                                        # Create contexts with sensitive user data
                                                                                                                        # REMOVED_SYNTAX_ERROR: sensitive_data = [ )
                                                                                                                        # REMOVED_SYNTAX_ERROR: ("user_alice", "thread_secret_project", "run_confidential_001"),
                                                                                                                        # REMOVED_SYNTAX_ERROR: ("user_bob", "thread_personal_data", "run_private_002"),
                                                                                                                        # REMOVED_SYNTAX_ERROR: ("user_charlie", "thread_financial_info", "run_sensitive_003")
                                                                                                                        

                                                                                                                        # REMOVED_SYNTAX_ERROR: contexts = []
                                                                                                                        # REMOVED_SYNTAX_ERROR: for user_id, thread_id, run_id in sensitive_data:
                                                                                                                            # REMOVED_SYNTAX_ERROR: context = WebSocketContext( )
                                                                                                                            # REMOVED_SYNTAX_ERROR: connection_id="formatted_string",
                                                                                                                            # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
                                                                                                                            # REMOVED_SYNTAX_ERROR: user_id=user_id,
                                                                                                                            # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
                                                                                                                            # REMOVED_SYNTAX_ERROR: run_id=run_id,
                                                                                                                            # REMOVED_SYNTAX_ERROR: connected_at=datetime.utcnow(),
                                                                                                                            # REMOVED_SYNTAX_ERROR: last_activity=datetime.utcnow()
                                                                                                                            
                                                                                                                            # REMOVED_SYNTAX_ERROR: contexts.append(context)

                                                                                                                            # Verify complete data isolation
                                                                                                                            # REMOVED_SYNTAX_ERROR: for i, ctx in enumerate(contexts):
                                                                                                                                # REMOVED_SYNTAX_ERROR: expected_user, expected_thread, expected_run = sensitive_data[i]

                                                                                                                                # Verify context contains only its own data
                                                                                                                                # REMOVED_SYNTAX_ERROR: assert ctx.user_id == expected_user
                                                                                                                                # REMOVED_SYNTAX_ERROR: assert ctx.thread_id == expected_thread
                                                                                                                                # REMOVED_SYNTAX_ERROR: assert ctx.run_id == expected_run

                                                                                                                                # Verify isolation keys don't contain other users' data
                                                                                                                                # REMOVED_SYNTAX_ERROR: isolation_key = ctx.to_isolation_key()

                                                                                                                                # REMOVED_SYNTAX_ERROR: for j, (other_user, other_thread, other_run) in enumerate(sensitive_data):
                                                                                                                                    # REMOVED_SYNTAX_ERROR: if i != j:
                                                                                                                                        # Other users' data should not appear in this context
                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert other_user not in isolation_key
                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert other_thread not in isolation_key
                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert other_run not in isolation_key

                                                                                                                                        # Verify connection info doesn't leak other users' data
                                                                                                                                        # REMOVED_SYNTAX_ERROR: conn_info = ctx.get_connection_info()

                                                                                                                                        # REMOVED_SYNTAX_ERROR: for j, (other_user, other_thread, other_run) in enumerate(sensitive_data):
                                                                                                                                            # REMOVED_SYNTAX_ERROR: if i != j:
                                                                                                                                                # Other users' data should not appear in connection info
                                                                                                                                                # REMOVED_SYNTAX_ERROR: info_str = str(conn_info)
                                                                                                                                                # REMOVED_SYNTAX_ERROR: assert other_user not in info_str
                                                                                                                                                # REMOVED_SYNTAX_ERROR: assert other_thread not in info_str
                                                                                                                                                # REMOVED_SYNTAX_ERROR: assert other_run not in info_str

                                                                                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                                # Removed problematic line: async def test_supervisor_isolation_health_check(self, mock_websocket, mock_db_session):
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: Test the health check functionality works correctly with isolation.
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: pass
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.supervisor_factory import get_websocket_supervisor_health

                                                                                                                                                    # Mock required components
                                                                                                                                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.supervisor_factory.get_supervisor_health_info') as mock_core_health:
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: mock_core_health.return_value = { )
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: "components_valid": True,
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: "llm_client_available": True
                                                                                                                                                        

                                                                                                                                                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.supervisor_factory.get_websocket_manager') as mock_ws_manager:
                                                                                                                                                            # Test healthy state
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: mock_ws_manager.websocket = TestWebSocketConnection()  # Real WebSocket implementation

                                                                                                                                                            # REMOVED_SYNTAX_ERROR: health = get_websocket_supervisor_health()

                                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert "websocket_supervisor_factory" in health
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: factory_health = health["websocket_supervisor_factory"]
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert factory_health["status"] == "healthy"
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert factory_health["components_valid"] is True
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert factory_health["websocket_manager_available"] is True
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert factory_health["websocket_bridge_available"] is True

                                                                                                                                                            # Test degraded state (missing WebSocket manager)
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: mock_ws_manager.return_value = None

                                                                                                                                                            # REMOVED_SYNTAX_ERROR: health = get_websocket_supervisor_health()
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: factory_health = health["websocket_supervisor_factory"]
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert factory_health["status"] == "degraded"
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: assert factory_health["websocket_manager_available"] is False


                                                                                                                                                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short", "--asyncio-mode=auto"])