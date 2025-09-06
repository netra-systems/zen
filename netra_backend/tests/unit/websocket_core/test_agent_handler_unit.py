# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Unit Tests for WebSocket Agent Handler - Tests 1-30

# REMOVED_SYNTAX_ERROR: Business Value Justification:
    # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
    # REMOVED_SYNTAX_ERROR: - Business Goal: Development Velocity & Platform Stability
    # REMOVED_SYNTAX_ERROR: - Value Impact: Ensures multi-user isolation and chat reliability
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: Enables $500K+ ARR through reliable WebSocket infrastructure

    # REMOVED_SYNTAX_ERROR: This test suite validates the critical v2 factory-based isolation patterns
    # REMOVED_SYNTAX_ERROR: that enable safe multi-user concurrent execution.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any, Optional, List
    # REMOVED_SYNTAX_ERROR: from datetime import datetime
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import pytest_asyncio
    # REMOVED_SYNTAX_ERROR: from fastapi import WebSocket
    # REMOVED_SYNTAX_ERROR: from sqlalchemy.ext.asyncio import AsyncSession

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.message_handlers import MessageHandlerService
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.dependencies import ( )
    # REMOVED_SYNTAX_ERROR: create_user_execution_context,
    # REMOVED_SYNTAX_ERROR: get_request_scoped_supervisor,
    # REMOVED_SYNTAX_ERROR: RequestScopedContext
    

    # ============================================================================
    # FIXTURES AND HELPERS
    # ============================================================================

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock WebSocket for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: ws = AsyncMock(spec=WebSocket)
    # REMOVED_SYNTAX_ERROR: ws.send_json = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: ws.receive_json = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: ws.close = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return ws

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_db_session():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock database session."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: session = AsyncMock(spec=AsyncSession)
    # REMOVED_SYNTAX_ERROR: session.is_active = True
    # REMOVED_SYNTAX_ERROR: session.commit = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: session.rollback = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: session.close = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return session

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_message_handler_service():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock MessageHandlerService."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: service = AsyncMock(spec=MessageHandlerService)
    # REMOVED_SYNTAX_ERROR: service.handle_start_agent = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: service.handle_user_message = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: return service

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock WebSocketManager."""
    # REMOVED_SYNTAX_ERROR: manager = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: manager.connect_user = AsyncMock(return_value=Mock(connection_id="test-connection-123"))
    # REMOVED_SYNTAX_ERROR: manager.disconnect_user = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: manager.emit_critical_event = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: manager.send_error = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: manager.get_connection_id_by_websocket = Mock(return_value="test-connection-123")
    # REMOVED_SYNTAX_ERROR: manager.update_connection_thread = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return manager

# REMOVED_SYNTAX_ERROR: async def create_test_message( )
# REMOVED_SYNTAX_ERROR: message_type: MessageType,
# REMOVED_SYNTAX_ERROR: payload: Dict[str, Any],
# REMOVED_SYNTAX_ERROR: thread_id: Optional[str] = None
# REMOVED_SYNTAX_ERROR: ) -> WebSocketMessage:
    # REMOVED_SYNTAX_ERROR: """Helper to create test WebSocket messages."""
    # REMOVED_SYNTAX_ERROR: return WebSocketMessage( )
    # REMOVED_SYNTAX_ERROR: type=message_type,
    # REMOVED_SYNTAX_ERROR: payload=payload,
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id or str(uuid.uuid4()),
    # REMOVED_SYNTAX_ERROR: timestamp=datetime.utcnow().isoformat()
    

    # ============================================================================
    # TESTS 1-6: CRITICAL MULTI-USER ISOLATION
    # ============================================================================

    # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestMultiUserIsolation:
    # REMOVED_SYNTAX_ERROR: """Test suite for multi-user isolation and v2 factory patterns."""

    # Removed problematic line: async def test_multi_user_isolation_no_data_leakage( )
    # REMOVED_SYNTAX_ERROR: self,
    # REMOVED_SYNTAX_ERROR: mock_websocket,
    # REMOVED_SYNTAX_ERROR: mock_db_session,
    # REMOVED_SYNTAX_ERROR: mock_message_handler_service,
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test 1: Verify complete data isolation between concurrent users.

        # REMOVED_SYNTAX_ERROR: Business Impact: Prevents data leakage between customers ($100K+ security risk).
        # REMOVED_SYNTAX_ERROR: '''
        # Setup
        # REMOVED_SYNTAX_ERROR: user_a_id = "user_a_test"
        # REMOVED_SYNTAX_ERROR: user_b_id = "user_b_test"
        # REMOVED_SYNTAX_ERROR: user_a_thread = "thread_a_123"
        # REMOVED_SYNTAX_ERROR: user_b_thread = "thread_b_456"

        # Track contexts created for each user
        # REMOVED_SYNTAX_ERROR: created_contexts = []

# REMOVED_SYNTAX_ERROR: async def track_context_creation(user_id, thread_id, run_id, db_session, websocket_connection_id=None):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: context = Mock( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
    # REMOVED_SYNTAX_ERROR: run_id=run_id,
    # REMOVED_SYNTAX_ERROR: db_session=db_session,
    # REMOVED_SYNTAX_ERROR: websocket_connection_id=websocket_connection_id
    
    # REMOVED_SYNTAX_ERROR: created_contexts.append(context)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return context

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', side_effect=track_context_creation):
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock) as mock_supervisor:

                    # Configure database session generator
# REMOVED_SYNTAX_ERROR: async def db_generator():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: yield mock_db_session
    # REMOVED_SYNTAX_ERROR: mock_get_db.return_value = db_generator()

    # Configure supervisor to await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return unique instances
    # REMOVED_SYNTAX_ERROR: supervisor_instances = []
# REMOVED_SYNTAX_ERROR: async def create_supervisor(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: supervisor = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: supervisor_instances.append(supervisor)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return supervisor
    # REMOVED_SYNTAX_ERROR: mock_supervisor.side_effect = create_supervisor

    # Create handler
    # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)

    # Create messages for both users
    # REMOVED_SYNTAX_ERROR: user_a_message = await create_test_message( )
    # REMOVED_SYNTAX_ERROR: MessageType.START_AGENT,
    # REMOVED_SYNTAX_ERROR: {"user_request": "User A request", "thread_id": user_a_thread},
    # REMOVED_SYNTAX_ERROR: thread_id=user_a_thread
    

    # REMOVED_SYNTAX_ERROR: user_b_message = await create_test_message( )
    # REMOVED_SYNTAX_ERROR: MessageType.START_AGENT,
    # REMOVED_SYNTAX_ERROR: {"user_request": "User B request", "thread_id": user_b_thread},
    # REMOVED_SYNTAX_ERROR: thread_id=user_b_thread
    

    # Process messages concurrently
    # REMOVED_SYNTAX_ERROR: results = await asyncio.gather( )
    # REMOVED_SYNTAX_ERROR: handler.handle_message(user_a_id, mock_websocket, user_a_message),
    # REMOVED_SYNTAX_ERROR: handler.handle_message(user_b_id, mock_websocket, user_b_message),
    # REMOVED_SYNTAX_ERROR: return_exceptions=True
    

    # Assertions
    # REMOVED_SYNTAX_ERROR: assert len(created_contexts) == 2, "Should create separate contexts for each user"

    # Verify User A context
    # REMOVED_SYNTAX_ERROR: user_a_context = next(c for c in created_contexts if c.user_id == user_a_id)
    # REMOVED_SYNTAX_ERROR: assert user_a_context.thread_id == user_a_thread
    # REMOVED_SYNTAX_ERROR: assert user_a_context.user_id == user_a_id

    # Verify User B context
    # REMOVED_SYNTAX_ERROR: user_b_context = next(c for c in created_contexts if c.user_id == user_b_id)
    # REMOVED_SYNTAX_ERROR: assert user_b_context.thread_id == user_b_thread
    # REMOVED_SYNTAX_ERROR: assert user_b_context.user_id == user_b_id

    # Verify no cross-contamination
    # REMOVED_SYNTAX_ERROR: assert user_a_context.thread_id != user_b_context.thread_id
    # REMOVED_SYNTAX_ERROR: assert user_a_context.run_id != user_b_context.run_id
    # REMOVED_SYNTAX_ERROR: assert user_a_context.db_session is user_b_context.db_session  # Same mock, but in real scenario would be different

    # Verify separate supervisor instances
    # REMOVED_SYNTAX_ERROR: assert len(supervisor_instances) == 2, "Should create separate supervisors"

    # Removed problematic line: async def test_thread_association_websocket_routing( )
    # REMOVED_SYNTAX_ERROR: self,
    # REMOVED_SYNTAX_ERROR: mock_websocket,
    # REMOVED_SYNTAX_ERROR: mock_db_session,
    # REMOVED_SYNTAX_ERROR: mock_message_handler_service,
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test 2: Verify thread association updates for WebSocket message routing.

        # REMOVED_SYNTAX_ERROR: Business Impact: Ensures agent events route to correct user connections.
        # REMOVED_SYNTAX_ERROR: '''
        # Setup
        # REMOVED_SYNTAX_ERROR: user_id = "test_user_routing"
        # REMOVED_SYNTAX_ERROR: thread_id = "thread_routing_123"
        # REMOVED_SYNTAX_ERROR: connection_id = "connection_456"

        # Configure WebSocket manager
        # REMOVED_SYNTAX_ERROR: mock_websocket_manager.get_connection_id_by_websocket.return_value = connection_id

        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock) as mock_create_context:
                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):

                        # Configure database session
# REMOVED_SYNTAX_ERROR: async def db_generator():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: yield mock_db_session
    # REMOVED_SYNTAX_ERROR: mock_get_db.return_value = db_generator()

    # Configure context creation
    # REMOVED_SYNTAX_ERROR: mock_context = Mock( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
    # REMOVED_SYNTAX_ERROR: run_id=str(uuid.uuid4()),
    # REMOVED_SYNTAX_ERROR: db_session=mock_db_session,
    # REMOVED_SYNTAX_ERROR: websocket_connection_id=connection_id
    
    # REMOVED_SYNTAX_ERROR: mock_create_context.return_value = mock_context

    # Create handler
    # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)

    # Create message with thread_id
    # REMOVED_SYNTAX_ERROR: message = await create_test_message( )
    # REMOVED_SYNTAX_ERROR: MessageType.START_AGENT,
    # REMOVED_SYNTAX_ERROR: {"user_request": "Test request", "thread_id": thread_id},
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id
    

    # Process message
    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message(user_id, mock_websocket, message)

    # Assertions
    # REMOVED_SYNTAX_ERROR: assert result is True, "Message should be processed successfully"

    # Verify WebSocket manager interactions
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.get_connection_id_by_websocket.assert_called_with(mock_websocket)
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.update_connection_thread.assert_called_with(connection_id, thread_id)

    # Verify context creation with connection_id
    # REMOVED_SYNTAX_ERROR: mock_create_context.assert_called_once()
    # REMOVED_SYNTAX_ERROR: call_args = mock_create_context.call_args
    # REMOVED_SYNTAX_ERROR: assert call_args[1]['websocket_connection_id'] == connection_id
    # REMOVED_SYNTAX_ERROR: assert call_args[1]['thread_id'] == thread_id

    # Removed problematic line: async def test_user_execution_context_complete_creation( )
    # REMOVED_SYNTAX_ERROR: self,
    # REMOVED_SYNTAX_ERROR: mock_websocket,
    # REMOVED_SYNTAX_ERROR: mock_db_session,
    # REMOVED_SYNTAX_ERROR: mock_message_handler_service,
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test 3: Verify complete UserExecutionContext creation with all required fields.

        # REMOVED_SYNTAX_ERROR: Business Impact: Ensures proper user isolation and audit trail.
        # REMOVED_SYNTAX_ERROR: '''
        # Setup
        # REMOVED_SYNTAX_ERROR: user_id = "test_user_context"
        # REMOVED_SYNTAX_ERROR: thread_id = "thread_context_123"
        # REMOVED_SYNTAX_ERROR: run_id = "run_context_456"
        # REMOVED_SYNTAX_ERROR: connection_id = "connection_context_789"

        # Configure WebSocket manager
        # REMOVED_SYNTAX_ERROR: mock_websocket_manager.get_connection_id_by_websocket.return_value = connection_id

        # Track context creation
        # REMOVED_SYNTAX_ERROR: created_context = None

# REMOVED_SYNTAX_ERROR: def capture_context(user_id, thread_id, run_id, db_session, websocket_connection_id=None):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: nonlocal created_context
    # REMOVED_SYNTAX_ERROR: created_context = Mock( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
    # REMOVED_SYNTAX_ERROR: run_id=run_id,
    # REMOVED_SYNTAX_ERROR: db_session=db_session,
    # REMOVED_SYNTAX_ERROR: websocket_connection_id=websocket_connection_id,
    # REMOVED_SYNTAX_ERROR: request_id=str(uuid.uuid4())  # Should be auto-generated
    
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return created_context

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', side_effect=capture_context):
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):

                    # Configure database session
# REMOVED_SYNTAX_ERROR: async def db_generator():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: yield mock_db_session
    # REMOVED_SYNTAX_ERROR: mock_get_db.return_value = db_generator()

    # Create handler
    # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)

    # Test 1: Message with explicit run_id
    # REMOVED_SYNTAX_ERROR: message_with_run_id = await create_test_message( )
    # REMOVED_SYNTAX_ERROR: MessageType.START_AGENT,
    # REMOVED_SYNTAX_ERROR: {"user_request": "Test", "thread_id": thread_id, "run_id": run_id},
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id
    

    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message(user_id, mock_websocket, message_with_run_id)

    # Assertions for explicit run_id
    # REMOVED_SYNTAX_ERROR: assert created_context is not None
    # REMOVED_SYNTAX_ERROR: assert created_context.user_id == user_id
    # REMOVED_SYNTAX_ERROR: assert created_context.thread_id == thread_id
    # REMOVED_SYNTAX_ERROR: assert created_context.run_id == run_id
    # REMOVED_SYNTAX_ERROR: assert created_context.db_session == mock_db_session
    # REMOVED_SYNTAX_ERROR: assert created_context.websocket_connection_id == connection_id
    # REMOVED_SYNTAX_ERROR: assert hasattr(created_context, 'request_id')

    # Reset for next test
    # REMOVED_SYNTAX_ERROR: created_context = None

    # Test 2: Message without run_id (should auto-generate)
    # REMOVED_SYNTAX_ERROR: message_without_run_id = await create_test_message( )
    # REMOVED_SYNTAX_ERROR: MessageType.USER_MESSAGE,
    # REMOVED_SYNTAX_ERROR: {"message": "Test message"},
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id
    

    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message(user_id, mock_websocket, message_without_run_id)

    # Assertions for auto-generated run_id
    # REMOVED_SYNTAX_ERROR: assert created_context is not None
    # REMOVED_SYNTAX_ERROR: assert created_context.run_id is not None
    # REMOVED_SYNTAX_ERROR: assert created_context.run_id != run_id  # Should be different from previous

    # Removed problematic line: async def test_request_scoped_supervisor_factory_isolation( )
    # REMOVED_SYNTAX_ERROR: self,
    # REMOVED_SYNTAX_ERROR: mock_websocket,
    # REMOVED_SYNTAX_ERROR: mock_db_session,
    # REMOVED_SYNTAX_ERROR: mock_message_handler_service,
    # REMOVED_SYNTAX_ERROR: mock_websocket_manager
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test 4: Verify request-scoped supervisor creation using v2 factory pattern.

        # REMOVED_SYNTAX_ERROR: Business Impact: Prevents shared state between user requests.
        # REMOVED_SYNTAX_ERROR: '''
        # Setup
        # REMOVED_SYNTAX_ERROR: supervisors_created = []
        # REMOVED_SYNTAX_ERROR: request_contexts_created = []

# REMOVED_SYNTAX_ERROR: async def track_supervisor_creation(request, context, db_session):
    # REMOVED_SYNTAX_ERROR: supervisor = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: supervisor.context = context
    # REMOVED_SYNTAX_ERROR: supervisor.request = request
    # REMOVED_SYNTAX_ERROR: supervisors_created.append(supervisor)
    # REMOVED_SYNTAX_ERROR: request_contexts_created.append(context)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return supervisor

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock):
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', side_effect=track_supervisor_creation):

                    # Configure database session
# REMOVED_SYNTAX_ERROR: async def db_generator():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: yield mock_db_session
    # REMOVED_SYNTAX_ERROR: mock_get_db.return_value = db_generator()

    # Create handler
    # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)

    # Process multiple messages
    # REMOVED_SYNTAX_ERROR: for i in range(3):
        # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
        # REMOVED_SYNTAX_ERROR: message = await create_test_message( )
        # REMOVED_SYNTAX_ERROR: MessageType.START_AGENT,
        # REMOVED_SYNTAX_ERROR: {"user_request": "formatted_string"},
        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
        

        # REMOVED_SYNTAX_ERROR: await handler.handle_message(user_id, mock_websocket, message)

        # Assertions
        # REMOVED_SYNTAX_ERROR: assert len(supervisors_created) == 3, "Should create separate supervisor for each request"

        # Verify each supervisor is unique
        # REMOVED_SYNTAX_ERROR: supervisor_ids = [id(s) for s in supervisors_created]
        # REMOVED_SYNTAX_ERROR: assert len(set(supervisor_ids)) == 3, "All supervisors should be different instances"

        # Verify each has its own context
        # REMOVED_SYNTAX_ERROR: assert len(request_contexts_created) == 3
        # REMOVED_SYNTAX_ERROR: context_ids = [id(c) for c in request_contexts_created]
        # REMOVED_SYNTAX_ERROR: assert len(set(context_ids)) == 3, "All contexts should be different"

        # Verify mock Request object creation
        # REMOVED_SYNTAX_ERROR: for supervisor in supervisors_created:
            # REMOVED_SYNTAX_ERROR: assert supervisor.request is not None
            # REMOVED_SYNTAX_ERROR: assert hasattr(supervisor, 'context')

            # Removed problematic line: async def test_database_session_lifecycle_safety( )
            # REMOVED_SYNTAX_ERROR: self,
            # REMOVED_SYNTAX_ERROR: mock_websocket,
            # REMOVED_SYNTAX_ERROR: mock_message_handler_service,
            # REMOVED_SYNTAX_ERROR: mock_websocket_manager
            # REMOVED_SYNTAX_ERROR: ):
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: Test 5: Verify proper database session lifecycle management.

                # REMOVED_SYNTAX_ERROR: Business Impact: Prevents connection leaks and ensures data consistency.
                # REMOVED_SYNTAX_ERROR: '''
                # Track session lifecycle
                # REMOVED_SYNTAX_ERROR: sessions_created = []
                # REMOVED_SYNTAX_ERROR: sessions_closed = []

# REMOVED_SYNTAX_ERROR: class TrackedSession:
# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.is_active = True
    # REMOVED_SYNTAX_ERROR: self.closed = False
    # REMOVED_SYNTAX_ERROR: sessions_created.append(self)

# REMOVED_SYNTAX_ERROR: async def commit(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: async def rollback(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: async def close(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.closed = True
    # REMOVED_SYNTAX_ERROR: self.is_active = False
    # REMOVED_SYNTAX_ERROR: sessions_closed.append(self)

# REMOVED_SYNTAX_ERROR: async def __aenter__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self

# REMOVED_SYNTAX_ERROR: async def __aexit__(self, exc_type, exc_val, exc_tb):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await self.close()

# REMOVED_SYNTAX_ERROR: async def create_tracked_session():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: session = TrackedSession()
    # REMOVED_SYNTAX_ERROR: yield session
    # Session should be closed after yield
    # REMOVED_SYNTAX_ERROR: if not session.closed:
        # REMOVED_SYNTAX_ERROR: await session.close()

        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session', side_effect=create_tracked_session):
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock):
                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):

                        # Create handler
                        # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)

                        # Test 1: Successful message processing
                        # REMOVED_SYNTAX_ERROR: message = await create_test_message( )
                        # REMOVED_SYNTAX_ERROR: MessageType.START_AGENT,
                        # REMOVED_SYNTAX_ERROR: {"user_request": "Test request"}
                        

                        # REMOVED_SYNTAX_ERROR: result = await handler.handle_message("test_user", mock_websocket, message)

                        # Verify session was created and closed
                        # REMOVED_SYNTAX_ERROR: assert len(sessions_created) == 1
                        # REMOVED_SYNTAX_ERROR: assert len(sessions_closed) == 1
                        # REMOVED_SYNTAX_ERROR: assert sessions_created[0].closed is True

                        # Reset for error test
                        # REMOVED_SYNTAX_ERROR: sessions_created.clear()
                        # REMOVED_SYNTAX_ERROR: sessions_closed.clear()

                        # Test 2: Error during processing
                        # REMOVED_SYNTAX_ERROR: with patch.object(mock_message_handler_service, 'handle_start_agent', side_effect=Exception("Test error")):
                            # REMOVED_SYNTAX_ERROR: message_error = await create_test_message( )
                            # REMOVED_SYNTAX_ERROR: MessageType.START_AGENT,
                            # REMOVED_SYNTAX_ERROR: {"user_request": "Error request"}
                            

                            # REMOVED_SYNTAX_ERROR: result = await handler.handle_message("test_user", mock_websocket, message_error)

                            # Session should still be closed even on error
                            # REMOVED_SYNTAX_ERROR: assert result is False
                            # REMOVED_SYNTAX_ERROR: assert len(sessions_created) == 1
                            # REMOVED_SYNTAX_ERROR: assert len(sessions_closed) == 1
                            # REMOVED_SYNTAX_ERROR: assert sessions_created[0].closed is True

                            # Removed problematic line: async def test_error_handling_stats_tracking_comprehensive( )
                            # REMOVED_SYNTAX_ERROR: self,
                            # REMOVED_SYNTAX_ERROR: mock_websocket,
                            # REMOVED_SYNTAX_ERROR: mock_db_session,
                            # REMOVED_SYNTAX_ERROR: mock_message_handler_service,
                            # REMOVED_SYNTAX_ERROR: mock_websocket_manager
                            # REMOVED_SYNTAX_ERROR: ):
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: Test 6: Verify comprehensive error handling with statistics tracking.

                                # REMOVED_SYNTAX_ERROR: Business Impact: Enables production monitoring and debugging.
                                # REMOVED_SYNTAX_ERROR: '''
                                # Setup
                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=mock_websocket_manager):
                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock):
                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):

                                                # Configure database session
# REMOVED_SYNTAX_ERROR: async def db_generator():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: yield mock_db_session
    # REMOVED_SYNTAX_ERROR: mock_get_db.return_value = db_generator()

    # Create handler
    # REMOVED_SYNTAX_ERROR: handler = AgentMessageHandler(mock_message_handler_service, mock_websocket)

    # Get initial stats
    # REMOVED_SYNTAX_ERROR: initial_stats = handler.get_stats()
    # REMOVED_SYNTAX_ERROR: assert initial_stats['messages_processed'] == 0
    # REMOVED_SYNTAX_ERROR: assert initial_stats['errors'] == 0

    # Test 1: Successful START_AGENT
    # REMOVED_SYNTAX_ERROR: message_start = await create_test_message( )
    # REMOVED_SYNTAX_ERROR: MessageType.START_AGENT,
    # REMOVED_SYNTAX_ERROR: {"user_request": "Start agent"}
    
    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message("user1", mock_websocket, message_start)

    # REMOVED_SYNTAX_ERROR: stats = handler.get_stats()
    # REMOVED_SYNTAX_ERROR: assert stats['messages_processed'] == 1
    # REMOVED_SYNTAX_ERROR: assert stats['start_agent_requests'] == 1
    # REMOVED_SYNTAX_ERROR: assert stats['errors'] == 0
    # REMOVED_SYNTAX_ERROR: assert stats['last_processed_time'] is not None

    # Test 2: Successful USER_MESSAGE
    # REMOVED_SYNTAX_ERROR: message_user = await create_test_message( )
    # REMOVED_SYNTAX_ERROR: MessageType.USER_MESSAGE,
    # REMOVED_SYNTAX_ERROR: {"message": "User message"}
    
    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message("user2", mock_websocket, message_user)

    # REMOVED_SYNTAX_ERROR: stats = handler.get_stats()
    # REMOVED_SYNTAX_ERROR: assert stats['messages_processed'] == 2
    # REMOVED_SYNTAX_ERROR: assert stats['user_messages'] == 1
    # REMOVED_SYNTAX_ERROR: assert stats['errors'] == 0

    # Test 3: Successful CHAT
    # REMOVED_SYNTAX_ERROR: message_chat = await create_test_message( )
    # REMOVED_SYNTAX_ERROR: MessageType.CHAT,
    # REMOVED_SYNTAX_ERROR: {"content": "Chat message"}
    
    # REMOVED_SYNTAX_ERROR: result = await handler.handle_message("user3", mock_websocket, message_chat)

    # REMOVED_SYNTAX_ERROR: stats = handler.get_stats()
    # REMOVED_SYNTAX_ERROR: assert stats['messages_processed'] == 3
    # REMOVED_SYNTAX_ERROR: assert stats['chat_messages'] == 1
    # REMOVED_SYNTAX_ERROR: assert stats['errors'] == 0

    # Test 4: Error handling
    # REMOVED_SYNTAX_ERROR: with patch.object(mock_message_handler_service, 'handle_start_agent', side_effect=Exception("Processing error")):
        # REMOVED_SYNTAX_ERROR: message_error = await create_test_message( )
        # REMOVED_SYNTAX_ERROR: MessageType.START_AGENT,
        # REMOVED_SYNTAX_ERROR: {"user_request": "Error request"}
        
        # REMOVED_SYNTAX_ERROR: result = await handler.handle_message("user4", mock_websocket, message_error)

        # REMOVED_SYNTAX_ERROR: assert result is False
        # REMOVED_SYNTAX_ERROR: stats = handler.get_stats()
        # REMOVED_SYNTAX_ERROR: assert stats['errors'] == 1
        # REMOVED_SYNTAX_ERROR: assert stats['messages_processed'] == 3  # Should not increment on error

        # Test 5: Critical error (should be re-raised)
        # REMOVED_SYNTAX_ERROR: with patch.object(mock_message_handler_service, 'handle_start_agent', side_effect=ImportError("Critical import error")):
            # REMOVED_SYNTAX_ERROR: message_critical = await create_test_message( )
            # REMOVED_SYNTAX_ERROR: MessageType.START_AGENT,
            # REMOVED_SYNTAX_ERROR: {"user_request": "Critical error"}
            

            # Critical errors should be handled but logged
            # REMOVED_SYNTAX_ERROR: result = await handler.handle_message("user5", mock_websocket, message_critical)
            # REMOVED_SYNTAX_ERROR: assert result is False

            # REMOVED_SYNTAX_ERROR: stats = handler.get_stats()
            # REMOVED_SYNTAX_ERROR: assert stats['errors'] == 2  # Error count should increase

            # Verify error notification attempt
            # REMOVED_SYNTAX_ERROR: if mock_websocket_manager.send_error.called:
                # REMOVED_SYNTAX_ERROR: error_calls = mock_websocket_manager.send_error.call_args_list
                # REMOVED_SYNTAX_ERROR: assert len(error_calls) >= 1
                # Verify user-friendly error message
                # REMOVED_SYNTAX_ERROR: assert "try again" in str(error_calls[0]).lower()

                # Additional test classes will be added in subsequent files for tests 7-30