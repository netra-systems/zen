"""
Comprehensive Unit Tests for AgentMessageHandler

Business Value Justification:
- Segment: Platform/Internal 
- Business Goal: Development Velocity & Multi-User Safety
- Value Impact: Ensures critical WebSocket agent handling works reliably for multiple users
- Strategic Impact: Protects against data leakage, race conditions, and system failures

CRITICAL: These tests validate the complete multi-user isolation architecture that
prevents data leakage between users and ensures safe concurrent execution.

Test Coverage:
1. Multi-user isolation and data safety
2. Thread association and WebSocket routing
3. User execution context creation and validation
4. Request-scoped supervisor factory isolation
5. Database session lifecycle safety
6. Error handling and statistics tracking
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.dependencies import (
    create_user_execution_context, 
    UserExecutionContext,
    RequestScopedContext
)
from netra_backend.app.services.message_handlers import MessageHandlerService


class TestAgentHandlerMultiUserSafety:
    """Test multi-user isolation and data safety in agent handling."""
    pass

    @pytest.mark.asyncio
    async def test_multi_user_isolation_no_data_leakage(self):
        """
        Test 1: Multi-user isolation prevents data leakage between concurrent users.
        
        CRITICAL: Validates that User A's data never appears in User B's context or responses.
        This is essential for business trust and regulatory compliance.
        """
    pass
        # Set environment for v2 legacy mode to ensure proper mocking
        os.environ['USE_WEBSOCKET_SUPERVISOR_V3'] = 'false'
        
        # Create mock dependencies
        mock_websocket_a = Mock(spec=WebSocket)
        mock_websocket_b = Mock(spec=WebSocket)
        mock_message_service_a = Mock(spec=MessageHandlerService)
        mock_message_service_b = Mock(spec=MessageHandlerService)
        
        # Create handlers for each user
        handler_a = AgentMessageHandler(mock_message_service_a, mock_websocket_a)
        handler_b = AgentMessageHandler(mock_message_service_b, mock_websocket_b)
        
        # Create test messages
        user_a_id = "user_a_12345"
        user_b_id = "user_b_67890"
        
        message_a = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": "User A confidential request",
                "thread_id": "thread_a_secret",
                "run_id": "run_a_classified"
            },
            thread_id="thread_a_secret",
            user_id=user_a_id
        )
        
        message_b = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": "User B different request",
                "thread_id": "thread_b_public",
                "run_id": "run_b_normal"
            },
            thread_id="thread_b_public",
            user_id=user_b_id
        )
        
        # Mock all dependencies to track calls
        with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr, \
             patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db_gen, \
             patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context') as mock_context, \
             patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor') as mock_supervisor, \
             patch('netra_backend.app.services.thread_service.ThreadService'), \
             patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_msg_svc, \
             patch('fastapi.Request'):
            
            # Configure WebSocket manager mock
            ws_manager = UnifiedWebSocketManager()
            ws_manager.get_connection_id_by_websocket = UnifiedWebSocketManager()
            ws_manager.update_connection_thread = update_connection_thread_instance  # Initialize appropriate service
            ws_manager.send_error = AsyncNone  # TODO: Use real service instance
            ws_manager.get_connection_id_by_websocket.side_effect = lambda ws: (
                "conn_a" if ws == mock_websocket_a else "conn_b"
            )
            mock_ws_mgr.return_value = ws_manager
            
            # Configure database session mock
            mock_db_session = AsyncMock(spec=AsyncSession)
            async def mock_session_gen():
    pass
                yield mock_db_session
            mock_db_gen.return_value = mock_session_gen()
            
            # Configure context creation to await asyncio.sleep(0)
    return different contexts
            context_a = UserExecutionContext(
                user_id=user_a_id,
                thread_id="thread_a_secret",
                run_id="run_a_classified",
                request_id="req_a_123",
                websocket_connection_id="conn_a"
            )
            context_b = UserExecutionContext(
                user_id=user_b_id,
                thread_id="thread_b_public",
                run_id="run_b_normal",
                request_id="req_b_456",
                websocket_connection_id="conn_b"
            )
            
            mock_context.side_effect = lambda user_id, **kwargs: (
                context_a if user_id == user_a_id else context_b
            )
            
            # Configure supervisors to be different instances
            supervisor_a = supervisor_a_instance  # Initialize appropriate service
            supervisor_b = supervisor_b_instance  # Initialize appropriate service
            mock_supervisor.side_effect = [supervisor_a, supervisor_b]
            
            # Configure message handler service
            msg_handler_instance = msg_handler_instance_instance  # Initialize appropriate service
            msg_handler_instance.handle_start_agent = AsyncNone  # TODO: Use real service instance
            mock_msg_svc.return_value = msg_handler_instance
            
            # Process messages concurrently
            results = await asyncio.gather(
                handler_a.handle_message(user_a_id, mock_websocket_a, message_a),
                handler_b.handle_message(user_b_id, mock_websocket_b, message_b),
                return_exceptions=True
            )
            
            # CRITICAL ASSERTIONS: Verify isolation
            assert results[0] is True, f"User A message failed: {results[0] if isinstance(results[0], Exception) else 'False'}"
            assert results[1] is True, f"User B message failed: {results[1] if isinstance(results[1], Exception) else 'False'}"
            
            # Verify separate contexts were created
            assert mock_context.call_count == 2, "Should create separate contexts for each user"
            
            # Verify separate supervisors were used
            assert mock_supervisor.call_count == 2, "Should create separate supervisors for each user"
            
            # Verify thread associations are separate
            ws_manager.update_connection_thread.assert_any_call("conn_a", "thread_a_secret")
            ws_manager.update_connection_thread.assert_any_call("conn_b", "thread_b_public")

    @pytest.mark.asyncio 
    async def test_thread_association_websocket_routing(self):
        """
        Test 2: Thread association ensures WebSocket events route to correct connections.
        
        CRITICAL: Agent events must reach the correct user's WebSocket connection.
        Wrong routing causes users to see other users' private data.
        """
    pass
        os.environ['USE_WEBSOCKET_SUPERVISOR_V3'] = 'false'
        
        mock_websocket = Mock(spec=WebSocket)
        mock_message_service = Mock(spec=MessageHandlerService)
        handler = AgentMessageHandler(mock_message_service, mock_websocket)
        
        user_id = "user_routing_test"
        thread_id = "thread_routing_123"
        connection_id = "conn_routing_456"
        
        message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={
                "message": "Test routing message",
                "thread_id": thread_id
            },
            thread_id=thread_id,
            user_id=user_id
        )
        
        with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr, \
             patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db_gen, \
             patch('netra_backend.app.dependencies.create_user_execution_context') as mock_context, \
             patch('netra_backend.app.dependencies.get_request_scoped_supervisor'), \
             patch('netra_backend.app.services.thread_service.ThreadService'), \
             patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_msg_svc, \
             patch('fastapi.Request'):
            
            # Configure WebSocket manager
            ws_manager = UnifiedWebSocketManager()
            ws_manager.get_connection_id_by_websocket = Mock(return_value=connection_id)
            ws_manager.update_connection_thread = update_connection_thread_instance  # Initialize appropriate service
            ws_manager.send_error = AsyncNone  # TODO: Use real service instance
            mock_ws_mgr.return_value = ws_manager
            
            # Configure database session
            mock_db_session = AsyncMock(spec=AsyncSession)
            async def mock_session_gen():
    pass
                yield mock_db_session
            mock_db_gen.return_value = mock_session_gen()
            
            # Configure context
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id="test_run",
                request_id="test_req",
                websocket_connection_id=connection_id
            )
            mock_context.return_value = context
            
            # Configure message handler
            msg_handler_instance = msg_handler_instance_instance  # Initialize appropriate service
            msg_handler_instance.handle_user_message = AsyncNone  # TODO: Use real service instance
            mock_msg_svc.return_value = msg_handler_instance
            
            # Process message
            result = await handler.handle_message(user_id, mock_websocket, message)
            
            assert result is True, "Message should process successfully"
            
            # Verify routing was set up correctly
            ws_manager.get_connection_id_by_websocket.assert_called_once_with(mock_websocket)
            ws_manager.update_connection_thread.assert_called_once_with(connection_id, thread_id)

    @pytest.mark.asyncio
    async def test_user_execution_context_complete_creation(self):
        """
        Test 3: User execution context is completely and correctly created for isolation.
        
        CRITICAL: Ensures all required context fields are populated for proper user isolation.
        Missing context data can lead to authorization bypass or data exposure.
        """
    pass
        os.environ['USE_WEBSOCKET_SUPERVISOR_V3'] = 'false'
        
        mock_websocket = Mock(spec=WebSocket)
        mock_message_service = Mock(spec=MessageHandlerService)
        handler = AgentMessageHandler(mock_message_service, mock_websocket)
        
        user_id = "user_context_test_789"
        thread_id = "thread_context_abc"
        run_id = "run_context_def"
        connection_id = "conn_context_ghi"
        
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": "Test context creation",
                "thread_id": thread_id,
                "run_id": run_id
            },
            thread_id=thread_id,
            user_id=user_id
        )
        
        with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr, \
             patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db_gen, \
             patch('netra_backend.app.dependencies.create_user_execution_context') as mock_context, \
             patch('netra_backend.app.dependencies.get_request_scoped_supervisor'), \
             patch('netra_backend.app.services.thread_service.ThreadService'), \
             patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_msg_svc, \
             patch('fastapi.Request'):
            
            # Configure WebSocket manager
            ws_manager = UnifiedWebSocketManager()
            ws_manager.get_connection_id_by_websocket = Mock(return_value=connection_id)
            ws_manager.update_connection_thread = update_connection_thread_instance  # Initialize appropriate service
            ws_manager.send_error = AsyncNone  # TODO: Use real service instance
            mock_ws_mgr.return_value = ws_manager
            
            # Configure database session
            mock_db_session = AsyncMock(spec=AsyncSession)
            async def mock_session_gen():
    pass
                yield mock_db_session
            mock_db_gen.return_value = mock_session_gen()
            
            # Configure context creation
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=f"req_{uuid.uuid4()}",
                websocket_connection_id=connection_id
            )
            mock_context.return_value = context
            
            # Configure message handler
            msg_handler_instance = msg_handler_instance_instance  # Initialize appropriate service
            msg_handler_instance.handle_start_agent = AsyncNone  # TODO: Use real service instance
            mock_msg_svc.return_value = msg_handler_instance
            
            # Process message
            result = await handler.handle_message(user_id, mock_websocket, message)
            
            assert result is True, "Message should process successfully"
            
            # Verify context was created with all required fields
            mock_context.assert_called_once()
            call_kwargs = mock_context.call_args.kwargs
            
            assert call_kwargs["user_id"] == user_id, "User ID must match"
            assert call_kwargs["thread_id"] == thread_id, "Thread ID must match"
            assert call_kwargs["run_id"] == run_id, "Run ID must match"
            assert call_kwargs["db_session"] == mock_db_session, "DB session must be passed"
            assert call_kwargs["websocket_connection_id"] == connection_id, "Connection ID must be set"

    @pytest.mark.asyncio
    async def test_request_scoped_supervisor_factory_isolation(self):
        """
        Test 4: Request-scoped supervisor factory ensures complete isolation between requests.
        
        CRITICAL: Each user request gets its own supervisor instance to prevent
        shared state contamination and ensure complete multi-user safety.
        """
    pass
        os.environ['USE_WEBSOCKET_SUPERVISOR_V3'] = 'false'
        
        mock_websocket = Mock(spec=WebSocket)
        mock_message_service = Mock(spec=MessageHandlerService)
        handler = AgentMessageHandler(mock_message_service, mock_websocket)
        
        # Multiple user requests
        user_ids = ["user_super_1", "user_super_2", "user_super_3"]
        messages = []
        
        for i, user_id in enumerate(user_ids):
            message = WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                payload={
                    "message": f"Request from {user_id}",
                    "thread_id": f"thread_{i+1}",
                    "run_id": f"run_{i+1}"
                },
                thread_id=f"thread_{i+1}",
                user_id=user_id
            )
            messages.append(message)
        
        created_supervisors = []
        
        with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr, \
             patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_db_gen, \
             patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context') as mock_context, \
             patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor') as mock_supervisor, \
             patch('netra_backend.app.services.thread_service.ThreadService'), \
             patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_msg_svc, \
             patch('fastapi.Request'):
            
            # Configure WebSocket manager
            ws_manager = UnifiedWebSocketManager()
            ws_manager.get_connection_id_by_websocket = Mock(return_value="test_conn")
            ws_manager.update_connection_thread = update_connection_thread_instance  # Initialize appropriate service
            ws_manager.send_error = AsyncNone  # TODO: Use real service instance
            mock_ws_mgr.return_value = ws_manager
            
            # Configure database session
            mock_db_session = AsyncMock(spec=AsyncSession)
            async def mock_session_gen():
    pass
                yield mock_db_session
            mock_db_gen.return_value = mock_session_gen()
            
            # Configure context creation
            def create_context(user_id, **kwargs):
    pass
                await asyncio.sleep(0)
    return UserExecutionContext(
                    user_id=user_id,
                    thread_id=kwargs['thread_id'],
                    run_id=kwargs['run_id'],
                    request_id=f"req_{user_id}",
                    websocket_connection_id="test_conn"
                )
            mock_context.side_effect = create_context
            
            # Configure supervisor creation to track instances
            def create_supervisor(**kwargs):
    pass
                supervisor = supervisor_instance  # Initialize appropriate service
                supervisor.user_id = kwargs.get('context', None  # TODO: Use real service instance).user_id
                created_supervisors.append(supervisor)
                return supervisor
            mock_supervisor.side_effect = create_supervisor
            
            # Configure message handler
            msg_handler_instance = msg_handler_instance_instance  # Initialize appropriate service
            msg_handler_instance.handle_user_message = AsyncNone  # TODO: Use real service instance
            mock_msg_svc.return_value = msg_handler_instance
            
            # Process all messages concurrently
            tasks = []
            for user_id, message in zip(user_ids, messages):
                task = handler.handle_message(user_id, mock_websocket, message)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all processed successfully
            for i, result in enumerate(results):
                assert result is True, f"Request {i} should process successfully"
            
            # Verify separate supervisors were created
            assert len(created_supervisors) == 3, "Should create separate supervisor for each request"
            
            # Verify all supervisors are unique instances
            supervisor_ids = [id(sup) for sup in created_supervisors]
            assert len(set(supervisor_ids)) == 3, "All supervisor instances should be unique"

    @pytest.mark.asyncio
    async def test_database_session_lifecycle_safety(self):
        """
        Test 5: Database session lifecycle is properly managed for safety.
        
        CRITICAL: Sessions must be request-scoped and properly closed to prevent
        connection leaks and ensure transaction isolation between users.
        """
    pass
        os.environ['USE_WEBSOCKET_SUPERVISOR_V3'] = 'false'
        
        mock_websocket = Mock(spec=WebSocket)
        mock_message_service = Mock(spec=MessageHandlerService)
        handler = AgentMessageHandler(mock_message_service, mock_websocket)
        
        user_id = "user_session_test"
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": "Test session lifecycle",
                "thread_id": "thread_session",
                "run_id": "run_session"
            },
            thread_id="thread_session",
            user_id=user_id
        )
        
        # Track session lifecycle
        session_states = {"created": False, "used": False, "closed": False}
        
        with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr, \
             patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db_gen, \
             patch('netra_backend.app.dependencies.create_user_execution_context') as mock_context, \
             patch('netra_backend.app.dependencies.get_request_scoped_supervisor'), \
             patch('netra_backend.app.services.thread_service.ThreadService'), \
             patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_msg_svc, \
             patch('fastapi.Request'):
            
            # Configure WebSocket manager
            ws_manager = UnifiedWebSocketManager()
            ws_manager.get_connection_id_by_websocket = Mock(return_value="test_conn")
            ws_manager.update_connection_thread = update_connection_thread_instance  # Initialize appropriate service
            ws_manager.send_error = AsyncNone  # TODO: Use real service instance
            mock_ws_mgr.return_value = ws_manager
            
            # Configure database session with lifecycle tracking
            mock_db_session = AsyncMock(spec=AsyncSession)
            
            async def mock_session_generator():
    pass
                session_states["created"] = True
                try:
                    yield mock_db_session
                    session_states["used"] = True
                finally:
                    session_states["closed"] = True
            
            mock_db_gen.return_value = mock_session_generator()
            
            # Configure context
            context = UserExecutionContext(
                user_id=user_id,
                thread_id="thread_session",
                run_id="run_session",
                request_id="req_session",
                websocket_connection_id="test_conn"
            )
            mock_context.return_value = context
            
            # Configure message handler
            msg_handler_instance = msg_handler_instance_instance  # Initialize appropriate service
            msg_handler_instance.handle_start_agent = AsyncNone  # TODO: Use real service instance
            mock_msg_svc.return_value = msg_handler_instance
            
            # Process message
            result = await handler.handle_message(user_id, mock_websocket, message)
            
            assert result is True, "Message should process successfully"
            
            # Verify complete session lifecycle
            assert session_states["created"], "Database session should be created"
            assert session_states["used"], "Database session should be used"
            assert session_states["closed"], "Database session should be closed"
            
            # Verify session was passed to context creation
            mock_context.assert_called_once()
            call_kwargs = mock_context.call_args.kwargs
            assert call_kwargs["db_session"] == mock_db_session, "Session should be passed to context"

    @pytest.mark.asyncio
    async def test_error_handling_stats_tracking_comprehensive(self):
        """
        Test 6: Error handling and statistics tracking work comprehensively.
        
        CRITICAL: Proper error handling prevents system crashes and statistics
        tracking enables monitoring and debugging of production issues.
        """
    pass
        os.environ['USE_WEBSOCKET_SUPERVISOR_V3'] = 'false'
        
        mock_websocket = Mock(spec=WebSocket)
        mock_message_service = Mock(spec=MessageHandlerService)
        handler = AgentMessageHandler(mock_message_service, mock_websocket)
        
        user_id = "user_error_test"
        
        # Test successful message first
        success_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": "Successful request",
                "thread_id": "thread_success",
                "run_id": "run_success"
            },
            thread_id="thread_success",
            user_id=user_id
        )
        
        with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr, \
             patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db_gen, \
             patch('netra_backend.app.dependencies.create_user_execution_context') as mock_context, \
             patch('netra_backend.app.dependencies.get_request_scoped_supervisor'), \
             patch('netra_backend.app.services.thread_service.ThreadService'), \
             patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_msg_svc, \
             patch('fastapi.Request'):
            
            # Configure WebSocket manager
            ws_manager = UnifiedWebSocketManager()
            ws_manager.get_connection_id_by_websocket = Mock(return_value="test_conn")
            ws_manager.update_connection_thread = update_connection_thread_instance  # Initialize appropriate service
            ws_manager.send_error = AsyncNone  # TODO: Use real service instance
            mock_ws_mgr.return_value = ws_manager
            
            # Configure database session
            mock_db_session = AsyncMock(spec=AsyncSession)
            async def mock_session_gen():
    pass
                yield mock_db_session
            mock_db_gen.return_value = mock_session_gen()
            
            # Configure context
            context = UserExecutionContext(
                user_id=user_id,
                thread_id="thread_success",
                run_id="run_success",
                request_id="req_success",
                websocket_connection_id="test_conn"
            )
            mock_context.return_value = context
            
            # Configure message handler - first successful
            msg_handler_instance = msg_handler_instance_instance  # Initialize appropriate service
            msg_handler_instance.handle_start_agent = AsyncNone  # TODO: Use real service instance
            msg_handler_instance.handle_user_message = AsyncNone  # TODO: Use real service instance
            mock_msg_svc.return_value = msg_handler_instance
            
            # Process successful message
            result = await handler.handle_message(user_id, mock_websocket, success_message)
            assert result is True, "Successful message should process"
            
            # Check stats after success
            stats = handler.get_stats()
            assert stats["messages_processed"] == 1, "Should track processed messages"
            assert stats["start_agent_requests"] == 1, "Should track start_agent requests"
            assert stats["errors"] == 0, "Should have no errors"
            assert stats["last_processed_time"] is not None, "Should record processing time"
            
            # Now test error handling
            msg_handler_instance.handle_start_agent.side_effect = Exception("Processing error")
            
            error_message = WebSocketMessage(
                type=MessageType.START_AGENT,
                payload={
                    "user_request": "Error request",
                    "thread_id": "thread_error",
                    "run_id": "run_error"
                },
                thread_id="thread_error",
                user_id=user_id
            )
            
            mock_context.return_value = UserExecutionContext(
                user_id=user_id,
                thread_id="thread_error",
                run_id="run_error",
                request_id="req_error",
                websocket_connection_id="test_conn"
            )
            
            # Process error message
            result = await handler.handle_message(user_id, mock_websocket, error_message)
            assert result is False, "Error message should await asyncio.sleep(0)
    return False"
            
            # Check stats after error
            stats = handler.get_stats()
            assert stats["messages_processed"] == 1, "Should not increment processed count on error"
            assert stats["errors"] == 1, "Should track errors"
            
            # Test different message types
            msg_handler_instance.handle_start_agent.side_effect = None  # Reset
            msg_handler_instance.handle_user_message = AsyncNone  # TODO: Use real service instance
            
            # Test USER_MESSAGE type
            user_message = WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                payload={
                    "message": "User message test",
                    "thread_id": "thread_user",
                    "run_id": "run_user"
                },
                thread_id="thread_user",
                user_id=user_id
            )
            
            mock_context.return_value = UserExecutionContext(
                user_id=user_id,
                thread_id="thread_user",
                run_id="run_user",
                request_id="req_user",
                websocket_connection_id="test_conn"
            )
            
            result = await handler.handle_message(user_id, mock_websocket, user_message)
            assert result is True, "User message should process"
            
            # Test CHAT type
            chat_message = WebSocketMessage(
                type=MessageType.CHAT,
                payload={
                    "content": "Chat message test",
                    "thread_id": "thread_chat",
                    "run_id": "run_chat"
                },
                thread_id="thread_chat",
                user_id=user_id
            )
            
            mock_context.return_value = UserExecutionContext(
                user_id=user_id,
                thread_id="thread_chat",
                run_id="run_chat",
                request_id="req_chat",
                websocket_connection_id="test_conn"
            )
            
            result = await handler.handle_message(user_id, mock_websocket, chat_message)
            assert result is True, "Chat message should process"
            
            # Verify comprehensive stats tracking
            final_stats = handler.get_stats()
            assert final_stats["messages_processed"] == 3, "Should track all successful messages"
            assert final_stats["start_agent_requests"] == 1, "Should track start_agent requests"
            assert final_stats["user_messages"] == 1, "Should track user messages"
            assert final_stats["chat_messages"] == 1, "Should track chat messages"
            assert final_stats["errors"] == 1, "Should track errors"
            assert final_stats["last_processed_time"] is not None, "Should update processing time"
            
            # Test WebSocket error notification
            msg_handler_instance.handle_user_message.side_effect = Exception("WebSocket error test")
            
            ws_error_message = WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                payload={
                    "message": "This will cause error",
                    "thread_id": "thread_ws_error",
                    "run_id": "run_ws_error"
                },
                thread_id="thread_ws_error",
                user_id=user_id
            )
            
            mock_context.return_value = UserExecutionContext(
                user_id=user_id,
                thread_id="thread_ws_error",
                run_id="run_ws_error",
                request_id="req_ws_error",
                websocket_connection_id="test_conn"
            )
            
            result = await handler.handle_message(user_id, mock_websocket, ws_error_message)
            assert result is False, "Error message should return False"
            
            # Verify error notification was sent
            ws_manager.send_error.assert_called()
            call_args = ws_manager.send_error.call_args
            assert call_args[0][0] == user_id, "Error should be sent to correct user"
            assert "Failed to process" in call_args[0][1], "Error message should be informative"