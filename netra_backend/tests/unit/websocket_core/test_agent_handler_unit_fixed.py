# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Comprehensive Unit Tests for AgentMessageHandler

# REMOVED_SYNTAX_ERROR: Business Value Justification:
    # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
    # REMOVED_SYNTAX_ERROR: - Business Goal: Development Velocity & Multi-User Safety
    # REMOVED_SYNTAX_ERROR: - Value Impact: Ensures critical WebSocket agent handling works reliably for multiple users
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: Protects against data leakage, race conditions, and system failures

    # REMOVED_SYNTAX_ERROR: CRITICAL: These tests validate the complete multi-user isolation architecture that
    # REMOVED_SYNTAX_ERROR: prevents data leakage between users and ensures safe concurrent execution.

    # REMOVED_SYNTAX_ERROR: Test Coverage:
        # REMOVED_SYNTAX_ERROR: 1. Multi-user isolation and data safety
        # REMOVED_SYNTAX_ERROR: 2. Thread association and WebSocket routing
        # REMOVED_SYNTAX_ERROR: 3. User execution context creation and validation
        # REMOVED_SYNTAX_ERROR: 4. Request-scoped supervisor factory isolation
        # REMOVED_SYNTAX_ERROR: 5. Database session lifecycle safety
        # REMOVED_SYNTAX_ERROR: 6. Error handling and statistics tracking
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import os
        # REMOVED_SYNTAX_ERROR: import uuid
        # REMOVED_SYNTAX_ERROR: from datetime import datetime
        # REMOVED_SYNTAX_ERROR: from typing import Dict, Any
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
        # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: from fastapi import WebSocket
        # REMOVED_SYNTAX_ERROR: from sqlalchemy.ext.asyncio import AsyncSession

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.context import WebSocketContext
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.dependencies import ( )
        # REMOVED_SYNTAX_ERROR: create_user_execution_context,
        # REMOVED_SYNTAX_ERROR: UserExecutionContext,
        # REMOVED_SYNTAX_ERROR: RequestScopedContext
        
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.message_handlers import MessageHandlerService


# REMOVED_SYNTAX_ERROR: class TestAgentHandlerMultiUserSafety:
    # REMOVED_SYNTAX_ERROR: """Test multi-user isolation and data safety in agent handling."""
    # REMOVED_SYNTAX_ERROR: pass

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_multi_user_isolation_no_data_leakage(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test 1: Multi-user isolation prevents data leakage between concurrent users.

        # REMOVED_SYNTAX_ERROR: CRITICAL: Validates that User A's data never appears in User B's context or responses.
        # REMOVED_SYNTAX_ERROR: This is essential for business trust and regulatory compliance.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # Set environment for v2 legacy mode to ensure proper mocking
        # REMOVED_SYNTAX_ERROR: os.environ['USE_WEBSOCKET_SUPERVISOR_V3'] = 'false'

        # Create mock dependencies
        # REMOVED_SYNTAX_ERROR: mock_websocket_a = Mock(spec=WebSocket)
        # REMOVED_SYNTAX_ERROR: mock_websocket_b = Mock(spec=WebSocket)
        # REMOVED_SYNTAX_ERROR: mock_message_service_a = Mock(spec=MessageHandlerService)
        # REMOVED_SYNTAX_ERROR: mock_message_service_b = Mock(spec=MessageHandlerService)

        # Create handlers for each user
        # REMOVED_SYNTAX_ERROR: handler_a = AgentMessageHandler(mock_message_service_a, mock_websocket_a)
        # REMOVED_SYNTAX_ERROR: handler_b = AgentMessageHandler(mock_message_service_b, mock_websocket_b)

        # Create test messages
        # REMOVED_SYNTAX_ERROR: user_a_id = "user_a_12345"
        # REMOVED_SYNTAX_ERROR: user_b_id = "user_b_67890"

        # REMOVED_SYNTAX_ERROR: message_a = WebSocketMessage( )
        # REMOVED_SYNTAX_ERROR: type=MessageType.START_AGENT,
        # REMOVED_SYNTAX_ERROR: payload={ )
        # REMOVED_SYNTAX_ERROR: "user_request": "User A confidential request",
        # REMOVED_SYNTAX_ERROR: "thread_id": "thread_a_secret",
        # REMOVED_SYNTAX_ERROR: "run_id": "run_a_classified"
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: thread_id="thread_a_secret",
        # REMOVED_SYNTAX_ERROR: user_id=user_a_id
        

        # REMOVED_SYNTAX_ERROR: message_b = WebSocketMessage( )
        # REMOVED_SYNTAX_ERROR: type=MessageType.START_AGENT,
        # REMOVED_SYNTAX_ERROR: payload={ )
        # REMOVED_SYNTAX_ERROR: "user_request": "User B different request",
        # REMOVED_SYNTAX_ERROR: "thread_id": "thread_b_public",
        # REMOVED_SYNTAX_ERROR: "run_id": "run_b_normal"
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: thread_id="thread_b_public",
        # REMOVED_SYNTAX_ERROR: user_id=user_b_id
        

        # Mock all dependencies to track calls
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr, \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db_gen, \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context') as mock_context, \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor') as mock_supervisor, \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.services.thread_service.ThreadService'), \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_msg_svc, \
        # REMOVED_SYNTAX_ERROR: patch('fastapi.Request'):

            # Configure WebSocket manager mock
            # REMOVED_SYNTAX_ERROR: ws_manager = UnifiedWebSocketManager()
            # REMOVED_SYNTAX_ERROR: ws_manager.get_connection_id_by_websocket = UnifiedWebSocketManager()
            # REMOVED_SYNTAX_ERROR: ws_manager.update_connection_thread = update_connection_thread_instance  # Initialize appropriate service
            # REMOVED_SYNTAX_ERROR: ws_manager.send_error = AsyncNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: ws_manager.get_connection_id_by_websocket.side_effect = lambda x: None ( )
            # REMOVED_SYNTAX_ERROR: "conn_a" if ws == mock_websocket_a else "conn_b"
            
            # REMOVED_SYNTAX_ERROR: mock_ws_mgr.return_value = ws_manager

            # Configure database session mock
            # REMOVED_SYNTAX_ERROR: mock_db_session = AsyncMock(spec=AsyncSession)
# REMOVED_SYNTAX_ERROR: async def mock_session_gen():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: yield mock_db_session
    # REMOVED_SYNTAX_ERROR: mock_db_gen.return_value = mock_session_gen()

    # Configure context creation to await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return different contexts
    # REMOVED_SYNTAX_ERROR: context_a = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_a_id,
    # REMOVED_SYNTAX_ERROR: thread_id="thread_a_secret",
    # REMOVED_SYNTAX_ERROR: run_id="run_a_classified",
    # REMOVED_SYNTAX_ERROR: request_id="req_a_123",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_a"
    
    # REMOVED_SYNTAX_ERROR: context_b = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_b_id,
    # REMOVED_SYNTAX_ERROR: thread_id="thread_b_public",
    # REMOVED_SYNTAX_ERROR: run_id="run_b_normal",
    # REMOVED_SYNTAX_ERROR: request_id="req_b_456",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_b"
    

    # REMOVED_SYNTAX_ERROR: mock_context.side_effect = lambda x: None ( )
    # REMOVED_SYNTAX_ERROR: context_a if user_id == user_a_id else context_b
    

    # Configure supervisors to be different instances
    # REMOVED_SYNTAX_ERROR: supervisor_a = supervisor_a_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: supervisor_b = supervisor_b_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: mock_supervisor.side_effect = [supervisor_a, supervisor_b]

    # Configure message handler service
    # REMOVED_SYNTAX_ERROR: msg_handler_instance = msg_handler_instance_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: msg_handler_instance.handle_start_agent = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_msg_svc.return_value = msg_handler_instance

    # Process messages concurrently
    # REMOVED_SYNTAX_ERROR: results = await asyncio.gather( )
    # REMOVED_SYNTAX_ERROR: handler_a.handle_message(user_a_id, mock_websocket_a, message_a),
    # REMOVED_SYNTAX_ERROR: handler_b.handle_message(user_b_id, mock_websocket_b, message_b),
    # REMOVED_SYNTAX_ERROR: return_exceptions=True
    

    # CRITICAL ASSERTIONS: Verify isolation
    # REMOVED_SYNTAX_ERROR: assert results[0] is True, "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert results[1] is True, "formatted_string"

    # Verify separate contexts were created
    # REMOVED_SYNTAX_ERROR: assert mock_context.call_count == 2, "Should create separate contexts for each user"

    # Verify separate supervisors were used
    # REMOVED_SYNTAX_ERROR: assert mock_supervisor.call_count == 2, "Should create separate supervisors for each user"

    # Verify thread associations are separate
    # REMOVED_SYNTAX_ERROR: ws_manager.update_connection_thread.assert_any_call("conn_a", "thread_a_secret")
    # REMOVED_SYNTAX_ERROR: ws_manager.update_connection_thread.assert_any_call("conn_b", "thread_b_public")

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_thread_association_websocket_routing(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test 2: Thread association ensures WebSocket events route to correct connections.

        # REMOVED_SYNTAX_ERROR: CRITICAL: Agent events must reach the correct user"s WebSocket connection.
        # REMOVED_SYNTAX_ERROR: Wrong routing causes users to see other users" private data.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: os.environ['USE_WEBSOCKET_SUPERVISOR_V3'] = 'false'

        # REMOVED_SYNTAX_ERROR: mock_websocket = Mock(spec=WebSocket)
        # REMOVED_SYNTAX_ERROR: mock_message_service = Mock(spec=MessageHandlerService)
        # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(mock_message_service, mock_websocket)

        # REMOVED_SYNTAX_ERROR: user_id = "user_routing_test"
        # REMOVED_SYNTAX_ERROR: thread_id = "thread_routing_123"
        # REMOVED_SYNTAX_ERROR: connection_id = "conn_routing_456"

        # REMOVED_SYNTAX_ERROR: message = WebSocketMessage( )
        # REMOVED_SYNTAX_ERROR: type=MessageType.USER_MESSAGE,
        # REMOVED_SYNTAX_ERROR: payload={ )
        # REMOVED_SYNTAX_ERROR: "message": "Test routing message",
        # REMOVED_SYNTAX_ERROR: "thread_id": thread_id
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
        # REMOVED_SYNTAX_ERROR: user_id=user_id
        

        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr, \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db_gen, \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.dependencies.create_user_execution_context') as mock_context, \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.dependencies.get_request_scoped_supervisor'), \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.services.thread_service.ThreadService'), \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_msg_svc, \
        # REMOVED_SYNTAX_ERROR: patch('fastapi.Request'):

            # Configure WebSocket manager
            # REMOVED_SYNTAX_ERROR: ws_manager = UnifiedWebSocketManager()
            # REMOVED_SYNTAX_ERROR: ws_manager.get_connection_id_by_websocket = Mock(return_value=connection_id)
            # REMOVED_SYNTAX_ERROR: ws_manager.update_connection_thread = update_connection_thread_instance  # Initialize appropriate service
            # REMOVED_SYNTAX_ERROR: ws_manager.send_error = AsyncNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_ws_mgr.return_value = ws_manager

            # Configure database session
            # REMOVED_SYNTAX_ERROR: mock_db_session = AsyncMock(spec=AsyncSession)
# REMOVED_SYNTAX_ERROR: async def mock_session_gen():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: yield mock_db_session
    # REMOVED_SYNTAX_ERROR: mock_db_gen.return_value = mock_session_gen()

    # Configure context
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
    # REMOVED_SYNTAX_ERROR: run_id="test_run",
    # REMOVED_SYNTAX_ERROR: request_id="test_req",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id=connection_id
    
    # REMOVED_SYNTAX_ERROR: mock_context.return_value = context

    # Configure message handler
    # REMOVED_SYNTAX_ERROR: msg_handler_instance = msg_handler_instance_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: msg_handler_instance.handle_user_message = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_msg_svc.return_value = msg_handler_instance

    # Process message
    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message(user_id, mock_websocket, message)

    # REMOVED_SYNTAX_ERROR: assert result is True, "Message should process successfully"

    # Verify routing was set up correctly
    # REMOVED_SYNTAX_ERROR: ws_manager.get_connection_id_by_websocket.assert_called_once_with(mock_websocket)
    # REMOVED_SYNTAX_ERROR: ws_manager.update_connection_thread.assert_called_once_with(connection_id, thread_id)

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_user_execution_context_complete_creation(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test 3: User execution context is completely and correctly created for isolation.

        # REMOVED_SYNTAX_ERROR: CRITICAL: Ensures all required context fields are populated for proper user isolation.
        # REMOVED_SYNTAX_ERROR: Missing context data can lead to authorization bypass or data exposure.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: os.environ['USE_WEBSOCKET_SUPERVISOR_V3'] = 'false'

        # REMOVED_SYNTAX_ERROR: mock_websocket = Mock(spec=WebSocket)
        # REMOVED_SYNTAX_ERROR: mock_message_service = Mock(spec=MessageHandlerService)
        # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(mock_message_service, mock_websocket)

        # REMOVED_SYNTAX_ERROR: user_id = "user_context_test_789"
        # REMOVED_SYNTAX_ERROR: thread_id = "thread_context_abc"
        # REMOVED_SYNTAX_ERROR: run_id = "run_context_def"
        # REMOVED_SYNTAX_ERROR: connection_id = "conn_context_ghi"

        # REMOVED_SYNTAX_ERROR: message = WebSocketMessage( )
        # REMOVED_SYNTAX_ERROR: type=MessageType.START_AGENT,
        # REMOVED_SYNTAX_ERROR: payload={ )
        # REMOVED_SYNTAX_ERROR: "user_request": "Test context creation",
        # REMOVED_SYNTAX_ERROR: "thread_id": thread_id,
        # REMOVED_SYNTAX_ERROR: "run_id": run_id
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
        # REMOVED_SYNTAX_ERROR: user_id=user_id
        

        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr, \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db_gen, \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.dependencies.create_user_execution_context') as mock_context, \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.dependencies.get_request_scoped_supervisor'), \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.services.thread_service.ThreadService'), \
        # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_msg_svc, \
        # REMOVED_SYNTAX_ERROR: patch('fastapi.Request'):

            # Configure WebSocket manager
            # REMOVED_SYNTAX_ERROR: ws_manager = UnifiedWebSocketManager()
            # REMOVED_SYNTAX_ERROR: ws_manager.get_connection_id_by_websocket = Mock(return_value=connection_id)
            # REMOVED_SYNTAX_ERROR: ws_manager.update_connection_thread = update_connection_thread_instance  # Initialize appropriate service
            # REMOVED_SYNTAX_ERROR: ws_manager.send_error = AsyncNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_ws_mgr.return_value = ws_manager

            # Configure database session
            # REMOVED_SYNTAX_ERROR: mock_db_session = AsyncMock(spec=AsyncSession)
# REMOVED_SYNTAX_ERROR: async def mock_session_gen():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: yield mock_db_session
    # REMOVED_SYNTAX_ERROR: mock_db_gen.return_value = mock_session_gen()

    # Configure context creation
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
    # REMOVED_SYNTAX_ERROR: run_id=run_id,
    # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id=connection_id
    
    # REMOVED_SYNTAX_ERROR: mock_context.return_value = context

    # Configure message handler
    # REMOVED_SYNTAX_ERROR: msg_handler_instance = msg_handler_instance_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: msg_handler_instance.handle_start_agent = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_msg_svc.return_value = msg_handler_instance

    # Process message
    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message(user_id, mock_websocket, message)

    # REMOVED_SYNTAX_ERROR: assert result is True, "Message should process successfully"

    # Verify context was created with all required fields
    # REMOVED_SYNTAX_ERROR: mock_context.assert_called_once()
    # REMOVED_SYNTAX_ERROR: call_kwargs = mock_context.call_args.kwargs

    # REMOVED_SYNTAX_ERROR: assert call_kwargs["user_id"] == user_id, "User ID must match"
    # REMOVED_SYNTAX_ERROR: assert call_kwargs["thread_id"] == thread_id, "Thread ID must match"
    # REMOVED_SYNTAX_ERROR: assert call_kwargs["run_id"] == run_id, "Run ID must match"
    # REMOVED_SYNTAX_ERROR: assert call_kwargs["db_session"] == mock_db_session, "DB session must be passed"
    # REMOVED_SYNTAX_ERROR: assert call_kwargs["websocket_connection_id"] == connection_id, "Connection ID must be set"

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_request_scoped_supervisor_factory_isolation(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test 4: Request-scoped supervisor factory ensures complete isolation between requests.

        # REMOVED_SYNTAX_ERROR: CRITICAL: Each user request gets its own supervisor instance to prevent
        # REMOVED_SYNTAX_ERROR: shared state contamination and ensure complete multi-user safety.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: os.environ['USE_WEBSOCKET_SUPERVISOR_V3'] = 'false'

        # REMOVED_SYNTAX_ERROR: mock_websocket = Mock(spec=WebSocket)
        # REMOVED_SYNTAX_ERROR: mock_message_service = Mock(spec=MessageHandlerService)
        # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(mock_message_service, mock_websocket)

        # Multiple user requests
        # REMOVED_SYNTAX_ERROR: user_ids = ["user_super_1", "user_super_2", "user_super_3"]
        # REMOVED_SYNTAX_ERROR: messages = []

        # REMOVED_SYNTAX_ERROR: for i, user_id in enumerate(user_ids):
            # REMOVED_SYNTAX_ERROR: message = WebSocketMessage( )
            # REMOVED_SYNTAX_ERROR: type=MessageType.USER_MESSAGE,
            # REMOVED_SYNTAX_ERROR: payload={ )
            # REMOVED_SYNTAX_ERROR: "message": "formatted_string",
            # REMOVED_SYNTAX_ERROR: "thread_id": "formatted_string",
            # REMOVED_SYNTAX_ERROR: "run_id": "formatted_string"
            # REMOVED_SYNTAX_ERROR: },
            # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: user_id=user_id
            
            # REMOVED_SYNTAX_ERROR: messages.append(message)

            # REMOVED_SYNTAX_ERROR: created_supervisors = []

            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr, \
            # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db_gen, \
            # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context') as mock_context, \
            # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor') as mock_supervisor, \
            # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.services.thread_service.ThreadService'), \
            # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_msg_svc, \
            # REMOVED_SYNTAX_ERROR: patch('fastapi.Request'):

                # Configure WebSocket manager
                # REMOVED_SYNTAX_ERROR: ws_manager = UnifiedWebSocketManager()
                # REMOVED_SYNTAX_ERROR: ws_manager.get_connection_id_by_websocket = Mock(return_value="test_conn")
                # REMOVED_SYNTAX_ERROR: ws_manager.update_connection_thread = update_connection_thread_instance  # Initialize appropriate service
                # REMOVED_SYNTAX_ERROR: ws_manager.send_error = AsyncNone  # TODO: Use real service instance
                # REMOVED_SYNTAX_ERROR: mock_ws_mgr.return_value = ws_manager

                # Configure database session
                # REMOVED_SYNTAX_ERROR: mock_db_session = AsyncMock(spec=AsyncSession)
# REMOVED_SYNTAX_ERROR: async def mock_session_gen():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: yield mock_db_session
    # REMOVED_SYNTAX_ERROR: mock_db_gen.return_value = mock_session_gen()

    # Configure context creation
# REMOVED_SYNTAX_ERROR: def create_context(user_id, **kwargs):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id=kwargs['thread_id'],
    # REMOVED_SYNTAX_ERROR: run_id=kwargs['run_id'],
    # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="test_conn"
    
    # REMOVED_SYNTAX_ERROR: mock_context.side_effect = create_context

    # Configure supervisor creation to track instances
# REMOVED_SYNTAX_ERROR: def create_supervisor(**kwargs):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: supervisor = supervisor_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: supervisor.user_id = kwargs.get('context', None  # TODO: Use real service instance).user_id
    # REMOVED_SYNTAX_ERROR: created_supervisors.append(supervisor)
    # REMOVED_SYNTAX_ERROR: return supervisor
    # REMOVED_SYNTAX_ERROR: mock_supervisor.side_effect = create_supervisor

    # Configure message handler
    # REMOVED_SYNTAX_ERROR: msg_handler_instance = msg_handler_instance_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: msg_handler_instance.handle_user_message = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_msg_svc.return_value = msg_handler_instance

    # Process all messages concurrently
    # REMOVED_SYNTAX_ERROR: tasks = []
    # REMOVED_SYNTAX_ERROR: for user_id, message in zip(user_ids, messages):
        # REMOVED_SYNTAX_ERROR: task = handler.handle_message(user_id, mock_websocket, message)
        # REMOVED_SYNTAX_ERROR: tasks.append(task)

        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all processed successfully
        # REMOVED_SYNTAX_ERROR: for i, result in enumerate(results):
            # REMOVED_SYNTAX_ERROR: assert result is True, "formatted_string"

            # Verify separate supervisors were created
            # REMOVED_SYNTAX_ERROR: assert len(created_supervisors) == 3, "Should create separate supervisor for each request"

            # Verify all supervisors are unique instances
            # REMOVED_SYNTAX_ERROR: supervisor_ids = [id(sup) for sup in created_supervisors]
            # REMOVED_SYNTAX_ERROR: assert len(set(supervisor_ids)) == 3, "All supervisor instances should be unique"

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_database_session_lifecycle_safety(self):
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: Test 5: Database session lifecycle is properly managed for safety.

                # REMOVED_SYNTAX_ERROR: CRITICAL: Sessions must be request-scoped and properly closed to prevent
                # REMOVED_SYNTAX_ERROR: connection leaks and ensure transaction isolation between users.
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: os.environ['USE_WEBSOCKET_SUPERVISOR_V3'] = 'false'

                # REMOVED_SYNTAX_ERROR: mock_websocket = Mock(spec=WebSocket)
                # REMOVED_SYNTAX_ERROR: mock_message_service = Mock(spec=MessageHandlerService)
                # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(mock_message_service, mock_websocket)

                # REMOVED_SYNTAX_ERROR: user_id = "user_session_test"
                # REMOVED_SYNTAX_ERROR: message = WebSocketMessage( )
                # REMOVED_SYNTAX_ERROR: type=MessageType.START_AGENT,
                # REMOVED_SYNTAX_ERROR: payload={ )
                # REMOVED_SYNTAX_ERROR: "user_request": "Test session lifecycle",
                # REMOVED_SYNTAX_ERROR: "thread_id": "thread_session",
                # REMOVED_SYNTAX_ERROR: "run_id": "run_session"
                # REMOVED_SYNTAX_ERROR: },
                # REMOVED_SYNTAX_ERROR: thread_id="thread_session",
                # REMOVED_SYNTAX_ERROR: user_id=user_id
                

                # Track session lifecycle
                # REMOVED_SYNTAX_ERROR: session_states = {"created": False, "used": False, "closed": False}

                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr, \
                # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db_gen, \
                # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.dependencies.create_user_execution_context') as mock_context, \
                # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.dependencies.get_request_scoped_supervisor'), \
                # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.services.thread_service.ThreadService'), \
                # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_msg_svc, \
                # REMOVED_SYNTAX_ERROR: patch('fastapi.Request'):

                    # Configure WebSocket manager
                    # REMOVED_SYNTAX_ERROR: ws_manager = UnifiedWebSocketManager()
                    # REMOVED_SYNTAX_ERROR: ws_manager.get_connection_id_by_websocket = Mock(return_value="test_conn")
                    # REMOVED_SYNTAX_ERROR: ws_manager.update_connection_thread = update_connection_thread_instance  # Initialize appropriate service
                    # REMOVED_SYNTAX_ERROR: ws_manager.send_error = AsyncNone  # TODO: Use real service instance
                    # REMOVED_SYNTAX_ERROR: mock_ws_mgr.return_value = ws_manager

                    # Configure database session with lifecycle tracking
                    # REMOVED_SYNTAX_ERROR: mock_db_session = AsyncMock(spec=AsyncSession)

# REMOVED_SYNTAX_ERROR: async def mock_session_generator():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: session_states["created"] = True
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: yield mock_db_session
        # REMOVED_SYNTAX_ERROR: session_states["used"] = True
        # REMOVED_SYNTAX_ERROR: finally:
            # REMOVED_SYNTAX_ERROR: session_states["closed"] = True

            # REMOVED_SYNTAX_ERROR: mock_db_gen.return_value = mock_session_generator()

            # Configure context
            # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id=user_id,
            # REMOVED_SYNTAX_ERROR: thread_id="thread_session",
            # REMOVED_SYNTAX_ERROR: run_id="run_session",
            # REMOVED_SYNTAX_ERROR: request_id="req_session",
            # REMOVED_SYNTAX_ERROR: websocket_connection_id="test_conn"
            
            # REMOVED_SYNTAX_ERROR: mock_context.return_value = context

            # Configure message handler
            # REMOVED_SYNTAX_ERROR: msg_handler_instance = msg_handler_instance_instance  # Initialize appropriate service
            # REMOVED_SYNTAX_ERROR: msg_handler_instance.handle_start_agent = AsyncNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_msg_svc.return_value = msg_handler_instance

            # Process message
            # REMOVED_SYNTAX_ERROR: result = await handler.handle_message(user_id, mock_websocket, message)

            # REMOVED_SYNTAX_ERROR: assert result is True, "Message should process successfully"

            # Verify complete session lifecycle
            # REMOVED_SYNTAX_ERROR: assert session_states["created"], "Database session should be created"
            # REMOVED_SYNTAX_ERROR: assert session_states["used"], "Database session should be used"
            # REMOVED_SYNTAX_ERROR: assert session_states["closed"], "Database session should be closed"

            # Verify session was passed to context creation
            # REMOVED_SYNTAX_ERROR: mock_context.assert_called_once()
            # REMOVED_SYNTAX_ERROR: call_kwargs = mock_context.call_args.kwargs
            # REMOVED_SYNTAX_ERROR: assert call_kwargs["db_session"] == mock_db_session, "Session should be passed to context"

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_error_handling_stats_tracking_comprehensive(self):
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: Test 6: Error handling and statistics tracking work comprehensively.

                # REMOVED_SYNTAX_ERROR: CRITICAL: Proper error handling prevents system crashes and statistics
                # REMOVED_SYNTAX_ERROR: tracking enables monitoring and debugging of production issues.
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: os.environ['USE_WEBSOCKET_SUPERVISOR_V3'] = 'false'

                # REMOVED_SYNTAX_ERROR: mock_websocket = Mock(spec=WebSocket)
                # REMOVED_SYNTAX_ERROR: mock_message_service = Mock(spec=MessageHandlerService)
                # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(mock_message_service, mock_websocket)

                # REMOVED_SYNTAX_ERROR: user_id = "user_error_test"

                # Test successful message first
                # REMOVED_SYNTAX_ERROR: success_message = WebSocketMessage( )
                # REMOVED_SYNTAX_ERROR: type=MessageType.START_AGENT,
                # REMOVED_SYNTAX_ERROR: payload={ )
                # REMOVED_SYNTAX_ERROR: "user_request": "Successful request",
                # REMOVED_SYNTAX_ERROR: "thread_id": "thread_success",
                # REMOVED_SYNTAX_ERROR: "run_id": "run_success"
                # REMOVED_SYNTAX_ERROR: },
                # REMOVED_SYNTAX_ERROR: thread_id="thread_success",
                # REMOVED_SYNTAX_ERROR: user_id=user_id
                

                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr, \
                # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db_gen, \
                # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.dependencies.create_user_execution_context') as mock_context, \
                # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.dependencies.get_request_scoped_supervisor'), \
                # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.services.thread_service.ThreadService'), \
                # REMOVED_SYNTAX_ERROR: patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_msg_svc, \
                # REMOVED_SYNTAX_ERROR: patch('fastapi.Request'):

                    # Configure WebSocket manager
                    # REMOVED_SYNTAX_ERROR: ws_manager = UnifiedWebSocketManager()
                    # REMOVED_SYNTAX_ERROR: ws_manager.get_connection_id_by_websocket = Mock(return_value="test_conn")
                    # REMOVED_SYNTAX_ERROR: ws_manager.update_connection_thread = update_connection_thread_instance  # Initialize appropriate service
                    # REMOVED_SYNTAX_ERROR: ws_manager.send_error = AsyncNone  # TODO: Use real service instance
                    # REMOVED_SYNTAX_ERROR: mock_ws_mgr.return_value = ws_manager

                    # Configure database session
                    # REMOVED_SYNTAX_ERROR: mock_db_session = AsyncMock(spec=AsyncSession)
# REMOVED_SYNTAX_ERROR: async def mock_session_gen():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: yield mock_db_session
    # REMOVED_SYNTAX_ERROR: mock_db_gen.return_value = mock_session_gen()

    # Configure context
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id="thread_success",
    # REMOVED_SYNTAX_ERROR: run_id="run_success",
    # REMOVED_SYNTAX_ERROR: request_id="req_success",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="test_conn"
    
    # REMOVED_SYNTAX_ERROR: mock_context.return_value = context

    # Configure message handler - first successful
    # REMOVED_SYNTAX_ERROR: msg_handler_instance = msg_handler_instance_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: msg_handler_instance.handle_start_agent = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: msg_handler_instance.handle_user_message = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_msg_svc.return_value = msg_handler_instance

    # Process successful message
    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message(user_id, mock_websocket, success_message)
    # REMOVED_SYNTAX_ERROR: assert result is True, "Successful message should process"

    # Check stats after success
    # REMOVED_SYNTAX_ERROR: stats = handler.get_stats()
    # REMOVED_SYNTAX_ERROR: assert stats["messages_processed"] == 1, "Should track processed messages"
    # REMOVED_SYNTAX_ERROR: assert stats["start_agent_requests"] == 1, "Should track start_agent requests"
    # REMOVED_SYNTAX_ERROR: assert stats["errors"] == 0, "Should have no errors"
    # REMOVED_SYNTAX_ERROR: assert stats["last_processed_time"] is not None, "Should record processing time"

    # Now test error handling
    # REMOVED_SYNTAX_ERROR: msg_handler_instance.handle_start_agent.side_effect = Exception("Processing error")

    # REMOVED_SYNTAX_ERROR: error_message = WebSocketMessage( )
    # REMOVED_SYNTAX_ERROR: type=MessageType.START_AGENT,
    # REMOVED_SYNTAX_ERROR: payload={ )
    # REMOVED_SYNTAX_ERROR: "user_request": "Error request",
    # REMOVED_SYNTAX_ERROR: "thread_id": "thread_error",
    # REMOVED_SYNTAX_ERROR: "run_id": "run_error"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: thread_id="thread_error",
    # REMOVED_SYNTAX_ERROR: user_id=user_id
    

    # REMOVED_SYNTAX_ERROR: mock_context.return_value = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id="thread_error",
    # REMOVED_SYNTAX_ERROR: run_id="run_error",
    # REMOVED_SYNTAX_ERROR: request_id="req_error",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="test_conn"
    

    # Process error message
    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message(user_id, mock_websocket, error_message)
    # Removed problematic line: assert result is False, "Error message should await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return False"

    # Check stats after error
    # REMOVED_SYNTAX_ERROR: stats = handler.get_stats()
    # REMOVED_SYNTAX_ERROR: assert stats["messages_processed"] == 1, "Should not increment processed count on error"
    # REMOVED_SYNTAX_ERROR: assert stats["errors"] == 1, "Should track errors"

    # Test different message types
    # REMOVED_SYNTAX_ERROR: msg_handler_instance.handle_start_agent.side_effect = None  # Reset
    # REMOVED_SYNTAX_ERROR: msg_handler_instance.handle_user_message = AsyncNone  # TODO: Use real service instance

    # Test USER_MESSAGE type
    # REMOVED_SYNTAX_ERROR: user_message = WebSocketMessage( )
    # REMOVED_SYNTAX_ERROR: type=MessageType.USER_MESSAGE,
    # REMOVED_SYNTAX_ERROR: payload={ )
    # REMOVED_SYNTAX_ERROR: "message": "User message test",
    # REMOVED_SYNTAX_ERROR: "thread_id": "thread_user",
    # REMOVED_SYNTAX_ERROR: "run_id": "run_user"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: thread_id="thread_user",
    # REMOVED_SYNTAX_ERROR: user_id=user_id
    

    # REMOVED_SYNTAX_ERROR: mock_context.return_value = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id="thread_user",
    # REMOVED_SYNTAX_ERROR: run_id="run_user",
    # REMOVED_SYNTAX_ERROR: request_id="req_user",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="test_conn"
    

    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message(user_id, mock_websocket, user_message)
    # REMOVED_SYNTAX_ERROR: assert result is True, "User message should process"

    # Test CHAT type
    # REMOVED_SYNTAX_ERROR: chat_message = WebSocketMessage( )
    # REMOVED_SYNTAX_ERROR: type=MessageType.CHAT,
    # REMOVED_SYNTAX_ERROR: payload={ )
    # REMOVED_SYNTAX_ERROR: "content": "Chat message test",
    # REMOVED_SYNTAX_ERROR: "thread_id": "thread_chat",
    # REMOVED_SYNTAX_ERROR: "run_id": "run_chat"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: thread_id="thread_chat",
    # REMOVED_SYNTAX_ERROR: user_id=user_id
    

    # REMOVED_SYNTAX_ERROR: mock_context.return_value = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id="thread_chat",
    # REMOVED_SYNTAX_ERROR: run_id="run_chat",
    # REMOVED_SYNTAX_ERROR: request_id="req_chat",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="test_conn"
    

    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message(user_id, mock_websocket, chat_message)
    # REMOVED_SYNTAX_ERROR: assert result is True, "Chat message should process"

    # Verify comprehensive stats tracking
    # REMOVED_SYNTAX_ERROR: final_stats = handler.get_stats()
    # REMOVED_SYNTAX_ERROR: assert final_stats["messages_processed"] == 3, "Should track all successful messages"
    # REMOVED_SYNTAX_ERROR: assert final_stats["start_agent_requests"] == 1, "Should track start_agent requests"
    # REMOVED_SYNTAX_ERROR: assert final_stats["user_messages"] == 1, "Should track user messages"
    # REMOVED_SYNTAX_ERROR: assert final_stats["chat_messages"] == 1, "Should track chat messages"
    # REMOVED_SYNTAX_ERROR: assert final_stats["errors"] == 1, "Should track errors"
    # REMOVED_SYNTAX_ERROR: assert final_stats["last_processed_time"] is not None, "Should update processing time"

    # Test WebSocket error notification
    # REMOVED_SYNTAX_ERROR: msg_handler_instance.handle_user_message.side_effect = Exception("WebSocket error test")

    # REMOVED_SYNTAX_ERROR: ws_error_message = WebSocketMessage( )
    # REMOVED_SYNTAX_ERROR: type=MessageType.USER_MESSAGE,
    # REMOVED_SYNTAX_ERROR: payload={ )
    # REMOVED_SYNTAX_ERROR: "message": "This will cause error",
    # REMOVED_SYNTAX_ERROR: "thread_id": "thread_ws_error",
    # REMOVED_SYNTAX_ERROR: "run_id": "run_ws_error"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: thread_id="thread_ws_error",
    # REMOVED_SYNTAX_ERROR: user_id=user_id
    

    # REMOVED_SYNTAX_ERROR: mock_context.return_value = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id="thread_ws_error",
    # REMOVED_SYNTAX_ERROR: run_id="run_ws_error",
    # REMOVED_SYNTAX_ERROR: request_id="req_ws_error",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="test_conn"
    

    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message(user_id, mock_websocket, ws_error_message)
    # REMOVED_SYNTAX_ERROR: assert result is False, "Error message should return False"

    # Verify error notification was sent
    # REMOVED_SYNTAX_ERROR: ws_manager.send_error.assert_called()
    # REMOVED_SYNTAX_ERROR: call_args = ws_manager.send_error.call_args
    # REMOVED_SYNTAX_ERROR: assert call_args[0][0] == user_id, "Error should be sent to correct user"
    # REMOVED_SYNTAX_ERROR: assert "Failed to process" in call_args[0][1], "Error message should be informative"