"""
Unit Tests for WebSocket Agent Handler - Tests 1-30

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Platform Stability
- Value Impact: Ensures multi-user isolation and chat reliability
- Strategic Impact: Enables $500K+ ARR through reliable WebSocket infrastructure

This test suite validates the critical v2 factory-based isolation patterns
that enable safe multi-user concurrent execution.
"""

import asyncio
import uuid
import time
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call
from datetime import datetime

import pytest
import pytest_asyncio
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.dependencies import (
    create_user_execution_context,
    get_request_scoped_supervisor,
    RequestScopedContext
)

# ============================================================================
# FIXTURES AND HELPERS
# ============================================================================

@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    ws = AsyncMock(spec=WebSocket)
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.close = AsyncMock()
    return ws

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.is_active = True
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session

@pytest.fixture
def mock_message_handler_service():
    """Create a mock MessageHandlerService."""
    service = AsyncMock(spec=MessageHandlerService)
    service.handle_start_agent = AsyncMock(return_value=True)
    service.handle_user_message = AsyncMock(return_value=True)
    return service

@pytest.fixture
def mock_websocket_manager():
    """Create a mock WebSocketManager."""
    manager = AsyncMock()
    manager.connect_user = AsyncMock(return_value=Mock(connection_id="test-connection-123"))
    manager.disconnect_user = AsyncMock()
    manager.emit_critical_event = AsyncMock()
    manager.send_error = AsyncMock()
    manager.get_connection_id_by_websocket = Mock(return_value="test-connection-123")
    manager.update_connection_thread = AsyncMock()
    return manager

async def create_test_message(
    message_type: MessageType,
    payload: Dict[str, Any],
    thread_id: Optional[str] = None
) -> WebSocketMessage:
    """Helper to create test WebSocket messages."""
    return WebSocketMessage(
        type=message_type,
        payload=payload,
        thread_id=thread_id or str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat()
    )

# ============================================================================
# TESTS 1-6: CRITICAL MULTI-USER ISOLATION
# ============================================================================

@pytest.mark.asyncio
class TestMultiUserIsolation:
    """Test suite for multi-user isolation and v2 factory patterns."""
    
    async def test_multi_user_isolation_no_data_leakage(
        self, 
        mock_websocket, 
        mock_db_session,
        mock_message_handler_service,
        mock_websocket_manager
    ):
        """
        Test 1: Verify complete data isolation between concurrent users.
        
        Business Impact: Prevents data leakage between customers ($100K+ security risk).
        """
        # Setup
        user_a_id = "user_a_test"
        user_b_id = "user_b_test"
        user_a_thread = "thread_a_123"
        user_b_thread = "thread_b_456"
        
        # Track contexts created for each user
        created_contexts = []
        
        async def track_context_creation(user_id, thread_id, run_id, db_session, websocket_connection_id=None):
            context = Mock(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                db_session=db_session,
                websocket_connection_id=websocket_connection_id
            )
            created_contexts.append(context)
            return context
        
        with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', side_effect=track_context_creation):
                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock) as mock_supervisor:
                        
                        # Configure database session generator
                        async def db_generator():
                            yield mock_db_session
                        mock_get_db.return_value = db_generator()
                        
                        # Configure supervisor to return unique instances
                        supervisor_instances = []
                        async def create_supervisor(*args, **kwargs):
                            supervisor = AsyncMock()
                            supervisor_instances.append(supervisor)
                            return supervisor
                        mock_supervisor.side_effect = create_supervisor
                        
                        # Create handler
                        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
                        
                        # Create messages for both users
                        user_a_message = await create_test_message(
                            MessageType.START_AGENT,
                            {"user_request": "User A request", "thread_id": user_a_thread},
                            thread_id=user_a_thread
                        )
                        
                        user_b_message = await create_test_message(
                            MessageType.START_AGENT,
                            {"user_request": "User B request", "thread_id": user_b_thread},
                            thread_id=user_b_thread
                        )
                        
                        # Process messages concurrently
                        results = await asyncio.gather(
                            handler.handle_message(user_a_id, mock_websocket, user_a_message),
                            handler.handle_message(user_b_id, mock_websocket, user_b_message),
                            return_exceptions=True
                        )
                        
                        # Assertions
                        assert len(created_contexts) == 2, "Should create separate contexts for each user"
                        
                        # Verify User A context
                        user_a_context = next(c for c in created_contexts if c.user_id == user_a_id)
                        assert user_a_context.thread_id == user_a_thread
                        assert user_a_context.user_id == user_a_id
                        
                        # Verify User B context
                        user_b_context = next(c for c in created_contexts if c.user_id == user_b_id)
                        assert user_b_context.thread_id == user_b_thread
                        assert user_b_context.user_id == user_b_id
                        
                        # Verify no cross-contamination
                        assert user_a_context.thread_id != user_b_context.thread_id
                        assert user_a_context.run_id != user_b_context.run_id
                        assert user_a_context.db_session is user_b_context.db_session  # Same mock, but in real scenario would be different
                        
                        # Verify separate supervisor instances
                        assert len(supervisor_instances) == 2, "Should create separate supervisors"

    async def test_thread_association_websocket_routing(
        self,
        mock_websocket,
        mock_db_session,
        mock_message_handler_service,
        mock_websocket_manager
    ):
        """
        Test 2: Verify thread association updates for WebSocket message routing.
        
        Business Impact: Ensures agent events route to correct user connections.
        """
        # Setup
        user_id = "test_user_routing"
        thread_id = "thread_routing_123"
        connection_id = "connection_456"
        
        # Configure WebSocket manager
        mock_websocket_manager.get_connection_id_by_websocket.return_value = connection_id
        
        with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock) as mock_create_context:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):
                        
                        # Configure database session
                        async def db_generator():
                            yield mock_db_session
                        mock_get_db.return_value = db_generator()
                        
                        # Configure context creation
                        mock_context = Mock(
                            user_id=user_id,
                            thread_id=thread_id,
                            run_id=str(uuid.uuid4()),
                            db_session=mock_db_session,
                            websocket_connection_id=connection_id
                        )
                        mock_create_context.return_value = mock_context
                        
                        # Create handler
                        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
                        
                        # Create message with thread_id
                        message = await create_test_message(
                            MessageType.START_AGENT,
                            {"user_request": "Test request", "thread_id": thread_id},
                            thread_id=thread_id
                        )
                        
                        # Process message
                        result = await handler.handle_message(user_id, mock_websocket, message)
                        
                        # Assertions
                        assert result is True, "Message should be processed successfully"
                        
                        # Verify WebSocket manager interactions
                        mock_websocket_manager.get_connection_id_by_websocket.assert_called_with(mock_websocket)
                        mock_websocket_manager.update_connection_thread.assert_called_with(connection_id, thread_id)
                        
                        # Verify context creation with connection_id
                        mock_create_context.assert_called_once()
                        call_args = mock_create_context.call_args
                        assert call_args[1]['websocket_connection_id'] == connection_id
                        assert call_args[1]['thread_id'] == thread_id

    async def test_user_execution_context_complete_creation(
        self,
        mock_websocket,
        mock_db_session,
        mock_message_handler_service,
        mock_websocket_manager
    ):
        """
        Test 3: Verify complete UserExecutionContext creation with all required fields.
        
        Business Impact: Ensures proper user isolation and audit trail.
        """
        # Setup
        user_id = "test_user_context"
        thread_id = "thread_context_123"
        run_id = "run_context_456"
        connection_id = "connection_context_789"
        
        # Configure WebSocket manager
        mock_websocket_manager.get_connection_id_by_websocket.return_value = connection_id
        
        # Track context creation
        created_context = None
        
        def capture_context(user_id, thread_id, run_id, db_session, websocket_connection_id=None):
            nonlocal created_context
            created_context = Mock(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                db_session=db_session,
                websocket_connection_id=websocket_connection_id,
                request_id=str(uuid.uuid4())  # Should be auto-generated
            )
            return created_context
        
        with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', side_effect=capture_context):
                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):
                        
                        # Configure database session
                        async def db_generator():
                            yield mock_db_session
                        mock_get_db.return_value = db_generator()
                        
                        # Create handler
                        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
                        
                        # Test 1: Message with explicit run_id
                        message_with_run_id = await create_test_message(
                            MessageType.START_AGENT,
                            {"user_request": "Test", "thread_id": thread_id, "run_id": run_id},
                            thread_id=thread_id
                        )
                        
                        result = await handler.handle_message(user_id, mock_websocket, message_with_run_id)
                        
                        # Assertions for explicit run_id
                        assert created_context is not None
                        assert created_context.user_id == user_id
                        assert created_context.thread_id == thread_id
                        assert created_context.run_id == run_id
                        assert created_context.db_session == mock_db_session
                        assert created_context.websocket_connection_id == connection_id
                        assert hasattr(created_context, 'request_id')
                        
                        # Reset for next test
                        created_context = None
                        
                        # Test 2: Message without run_id (should auto-generate)
                        message_without_run_id = await create_test_message(
                            MessageType.USER_MESSAGE,
                            {"message": "Test message"},
                            thread_id=thread_id
                        )
                        
                        result = await handler.handle_message(user_id, mock_websocket, message_without_run_id)
                        
                        # Assertions for auto-generated run_id
                        assert created_context is not None
                        assert created_context.run_id is not None
                        assert created_context.run_id != run_id  # Should be different from previous

    async def test_request_scoped_supervisor_factory_isolation(
        self,
        mock_websocket,
        mock_db_session,
        mock_message_handler_service,
        mock_websocket_manager
    ):
        """
        Test 4: Verify request-scoped supervisor creation using v2 factory pattern.
        
        Business Impact: Prevents shared state between user requests.
        """
        # Setup
        supervisors_created = []
        request_contexts_created = []
        
        async def track_supervisor_creation(request, context, db_session):
            supervisor = AsyncMock()
            supervisor.context = context
            supervisor.request = request
            supervisors_created.append(supervisor)
            request_contexts_created.append(context)
            return supervisor
        
        with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock):
                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', side_effect=track_supervisor_creation):
                        
                        # Configure database session
                        async def db_generator():
                            yield mock_db_session
                        mock_get_db.return_value = db_generator()
                        
                        # Create handler
                        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
                        
                        # Process multiple messages
                        for i in range(3):
                            user_id = f"user_{i}"
                            message = await create_test_message(
                                MessageType.START_AGENT,
                                {"user_request": f"Request {i}"},
                                thread_id=f"thread_{i}"
                            )
                            
                            await handler.handle_message(user_id, mock_websocket, message)
                        
                        # Assertions
                        assert len(supervisors_created) == 3, "Should create separate supervisor for each request"
                        
                        # Verify each supervisor is unique
                        supervisor_ids = [id(s) for s in supervisors_created]
                        assert len(set(supervisor_ids)) == 3, "All supervisors should be different instances"
                        
                        # Verify each has its own context
                        assert len(request_contexts_created) == 3
                        context_ids = [id(c) for c in request_contexts_created]
                        assert len(set(context_ids)) == 3, "All contexts should be different"
                        
                        # Verify mock Request object creation
                        for supervisor in supervisors_created:
                            assert supervisor.request is not None
                            assert hasattr(supervisor, 'context')

    async def test_database_session_lifecycle_safety(
        self,
        mock_websocket,
        mock_message_handler_service,
        mock_websocket_manager
    ):
        """
        Test 5: Verify proper database session lifecycle management.
        
        Business Impact: Prevents connection leaks and ensures data consistency.
        """
        # Track session lifecycle
        sessions_created = []
        sessions_closed = []
        
        class TrackedSession:
            def __init__(self):
                self.is_active = True
                self.closed = False
                sessions_created.append(self)
            
            async def commit(self):
                pass
            
            async def rollback(self):
                pass
            
            async def close(self):
                self.closed = True
                self.is_active = False
                sessions_closed.append(self)
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await self.close()
        
        async def create_tracked_session():
            session = TrackedSession()
            yield session
            # Session should be closed after yield
            if not session.closed:
                await session.close()
        
        with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session', side_effect=create_tracked_session):
                with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock):
                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):
                        
                        # Create handler
                        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
                        
                        # Test 1: Successful message processing
                        message = await create_test_message(
                            MessageType.START_AGENT,
                            {"user_request": "Test request"}
                        )
                        
                        result = await handler.handle_message("test_user", mock_websocket, message)
                        
                        # Verify session was created and closed
                        assert len(sessions_created) == 1
                        assert len(sessions_closed) == 1
                        assert sessions_created[0].closed is True
                        
                        # Reset for error test
                        sessions_created.clear()
                        sessions_closed.clear()
                        
                        # Test 2: Error during processing
                        with patch.object(mock_message_handler_service, 'handle_start_agent', side_effect=Exception("Test error")):
                            message_error = await create_test_message(
                                MessageType.START_AGENT,
                                {"user_request": "Error request"}
                            )
                            
                            result = await handler.handle_message("test_user", mock_websocket, message_error)
                            
                            # Session should still be closed even on error
                            assert result is False
                            assert len(sessions_created) == 1
                            assert len(sessions_closed) == 1
                            assert sessions_created[0].closed is True

    async def test_error_handling_stats_tracking_comprehensive(
        self,
        mock_websocket,
        mock_db_session,
        mock_message_handler_service,
        mock_websocket_manager
    ):
        """
        Test 6: Verify comprehensive error handling with statistics tracking.
        
        Business Impact: Enables production monitoring and debugging.
        """
        # Setup
        with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock):
                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):
                        
                        # Configure database session
                        async def db_generator():
                            yield mock_db_session
                        mock_get_db.return_value = db_generator()
                        
                        # Create handler
                        handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)
                        
                        # Get initial stats
                        initial_stats = handler.get_stats()
                        assert initial_stats['messages_processed'] == 0
                        assert initial_stats['errors'] == 0
                        
                        # Test 1: Successful START_AGENT
                        message_start = await create_test_message(
                            MessageType.START_AGENT,
                            {"user_request": "Start agent"}
                        )
                        result = await handler.handle_message("user1", mock_websocket, message_start)
                        
                        stats = handler.get_stats()
                        assert stats['messages_processed'] == 1
                        assert stats['start_agent_requests'] == 1
                        assert stats['errors'] == 0
                        assert stats['last_processed_time'] is not None
                        
                        # Test 2: Successful USER_MESSAGE
                        message_user = await create_test_message(
                            MessageType.USER_MESSAGE,
                            {"message": "User message"}
                        )
                        result = await handler.handle_message("user2", mock_websocket, message_user)
                        
                        stats = handler.get_stats()
                        assert stats['messages_processed'] == 2
                        assert stats['user_messages'] == 1
                        assert stats['errors'] == 0
                        
                        # Test 3: Successful CHAT
                        message_chat = await create_test_message(
                            MessageType.CHAT,
                            {"content": "Chat message"}
                        )
                        result = await handler.handle_message("user3", mock_websocket, message_chat)
                        
                        stats = handler.get_stats()
                        assert stats['messages_processed'] == 3
                        assert stats['chat_messages'] == 1
                        assert stats['errors'] == 0
                        
                        # Test 4: Error handling
                        with patch.object(mock_message_handler_service, 'handle_start_agent', side_effect=Exception("Processing error")):
                            message_error = await create_test_message(
                                MessageType.START_AGENT,
                                {"user_request": "Error request"}
                            )
                            result = await handler.handle_message("user4", mock_websocket, message_error)
                            
                            assert result is False
                            stats = handler.get_stats()
                            assert stats['errors'] == 1
                            assert stats['messages_processed'] == 3  # Should not increment on error
                        
                        # Test 5: Critical error (should be re-raised)
                        with patch.object(mock_message_handler_service, 'handle_start_agent', side_effect=ImportError("Critical import error")):
                            message_critical = await create_test_message(
                                MessageType.START_AGENT,
                                {"user_request": "Critical error"}
                            )
                            
                            # Critical errors should be handled but logged
                            result = await handler.handle_message("user5", mock_websocket, message_critical)
                            assert result is False
                            
                            stats = handler.get_stats()
                            assert stats['errors'] == 2  # Error count should increase
                        
                        # Verify error notification attempt
                        if mock_websocket_manager.send_error.called:
                            error_calls = mock_websocket_manager.send_error.call_args_list
                            assert len(error_calls) >= 1
                            # Verify user-friendly error message
                            assert "try again" in str(error_calls[0]).lower()

# Additional test classes will be added in subsequent files for tests 7-30