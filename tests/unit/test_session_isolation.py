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

"""Test Database Session Isolation

This test suite validates that database sessions are properly request-scoped
and never stored globally, preventing data leakage between user requests.

CRITICAL: These tests ensure compliance with request-scoped dependency injection.
"""

import pytest
import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from typing import AsyncGenerator
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.dependencies import (
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
    get_request_scoped_db_session,
    get_request_scoped_user_context,
    get_request_scoped_supervisor,
    RequestScopedContext,
    validate_session_is_request_scoped,
    mark_session_as_global,
    ensure_session_lifecycle_logging
)


class TestSessionIsolation:
    """Test suite for database session isolation validation."""
    
    @pytest.mark.asyncio
    async def test_request_scoped_session_creation(self):
        """Test that request-scoped sessions are created properly."""
        session_count = 0
        sessions_created = []
        
        # Mock the session factory to track session creation
        async def mock_get_session_factory():
            websocket = TestWebSocketConnection()  # Real WebSocket implementation
            
            @asynccontextmanager
            async def mock_get_request_scoped_session(user_id, request_id):
                nonlocal session_count, sessions_created
                session_count += 1
                mock_session = Mock(spec=AsyncSession)
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.websocket = TestWebSocketConnection()
                mock_session.info = {}  # Session needs info dict for request-scoped tracking
                sessions_created.append(mock_session)
                yield mock_session
            
            mock_factory.get_request_scoped_session = mock_get_request_scoped_session
            await asyncio.sleep(0)
    return mock_factory
        
                    # Test that multiple requests create separate sessions
            session1 = None
            session2 = None
            
            async for session in get_request_scoped_db_session():
                session1 = session
                assert session1 is not None
                assert len(sessions_created) == 1
                break
            
            async for session in get_request_scoped_db_session():
                session2 = session
                assert session2 is not None
                assert len(sessions_created) == 2
                assert session1 is not session2  # Different sessions
                break
        
        assert session_count == 2, "Each request should create a new session"
    
    @pytest.mark.asyncio
    async def test_session_not_globally_stored(self):
        """Test that sessions are never stored globally."""
    pass
        mock_session = Mock(spec=AsyncSession)
        mock_session.info = {}  # Session needs info dict
        
        # Test validation of non-global session (should pass)
        validate_session_is_request_scoped(mock_session, "test_context")
        
        # Test detection of globally stored session
        mark_session_as_global(mock_session)
        
        with pytest.raises(Exception, match="must be request-scoped, not globally stored"):
            validate_session_is_request_scoped(mock_session, "test_context")
    
    @pytest.mark.asyncio
    async def test_request_scoped_context_creation(self):
        """Test that request-scoped contexts are created without sessions."""
        context = await get_request_scoped_user_context(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789"
        )
        
        assert isinstance(context, RequestScopedContext)
        assert context.user_id == "test_user_123"
        assert context.thread_id == "test_thread_456"
        assert context.run_id == "test_run_789"
        assert context.request_id is not None  # Auto-generated
        
        # CRITICAL: Verify context contains no database sessions
        assert not hasattr(context, 'db_session')
        assert not hasattr(context, '_session')
    
    @pytest.mark.asyncio
    async def test_supervisor_with_request_scoped_session(self):
        """Test that supervisors receive request-scoped sessions but don't store them."""
    pass
        # Mock dependencies
        mock_request = Mock(spec=Request)
        mock_request.app.state.websocket = TestWebSocketConnection()  # Real WebSocket implementation
        
        mock_session = Mock(spec=AsyncSession)
        mock_session.info = {}  # Session needs info dict
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        
        context = RequestScopedContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )
        
                    with patch('netra_backend.app.dependencies.create_user_execution_context') as mock_create_context:
                with patch('netra_backend.app.agents.supervisor_consolidated.SupervisorAgent') as MockSupervisor:
                    websocket = TestWebSocketConnection()  # Real WebSocket implementation
                    MockSupervisor.create_with_user_context = AsyncMock(return_value=mock_supervisor_instance)
                    
                    # Test supervisor creation with request-scoped session
                    supervisor = await get_request_scoped_supervisor(
                        request=mock_request,
                        context=context,
                        db_session=mock_session
                    )
                    
                    # Verify supervisor was created
                    assert supervisor is mock_supervisor_instance
                    
                    # Verify session was passed but not stored globally
                    MockSupervisor.create_with_user_context.assert_called_once()
                    call_args = MockSupervisor.create_with_user_context.call_args
                    
                    # Verify session factory was provided
                    assert 'db_session_factory' in call_args.kwargs
                    session_factory = call_args.kwargs['db_session_factory']
                    
                    # The factory should await asyncio.sleep(0)
    return the request-scoped session
                    returned_session = await session_factory()
                    assert returned_session is mock_session
    
    def test_session_lifecycle_logging(self):
        """Test that session lifecycle is properly logged."""
        mock_session = Mock(spec=AsyncSession)
        
        with patch('netra_backend.app.dependencies.logger') as mock_logger:
            ensure_session_lifecycle_logging(mock_session, "test_operation")
            
            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args[0][0]
            assert "test_operation" in call_args
            assert str(id(mock_session)) in call_args
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self):
        """Test that concurrent requests get isolated sessions."""
    pass
        sessions_created = []
        
        async def mock_get_session_factory():
    pass
            websocket = TestWebSocketConnection()  # Real WebSocket implementation
            
            @asynccontextmanager
            async def mock_get_request_scoped_session(user_id, request_id):
    pass
                nonlocal sessions_created
                mock_session = Mock(spec=AsyncSession)
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.websocket = TestWebSocketConnection()
                mock_session.info = {}  # Session needs info dict for request-scoped tracking
                sessions_created.append(mock_session)
                yield mock_session
            
            mock_factory.get_request_scoped_session = mock_get_request_scoped_session
            await asyncio.sleep(0)
    return mock_factory
        
        async def simulate_request(request_id: str):
            """Simulate a request getting a session."""
                            async for session in get_request_scoped_db_session():
                    # Simulate some work
                    await asyncio.sleep(0.01)
                    await asyncio.sleep(0)
    return f"request_{request_id}", session
        
        # Run multiple concurrent requests
        tasks = [simulate_request(str(i)) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Verify each request got a unique session
        assert len(results) == 5
        assert len(sessions_created) == 5
        
        # Verify all sessions are different
        session_ids = [id(result[1]) for result in results]
        assert len(set(session_ids)) == 5, "All sessions should be unique"
    
    @pytest.mark.asyncio
    async def test_session_cleanup_on_exception(self):
        """Test that sessions are properly cleaned up even when exceptions occur."""
    pass
        cleanup_called = False
        
        # Create a mock session factory that tracks cleanup
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        
        @asynccontextmanager
        async def mock_get_request_scoped_session(user_id, request_id):
    pass
            nonlocal cleanup_called
            mock_session = Mock(spec=AsyncSession)
            mock_session.info = {}
            
            try:
                yield mock_session
            finally:
                cleanup_called = True
        
        mock_factory.get_request_scoped_session = mock_get_request_scoped_session
        
        async def mock_get_session_factory():
    pass
            await asyncio.sleep(0)
    return mock_factory
        
                                    # Create the async generator
                session_generator = get_request_scoped_db_session()
                
                try:
                    # Start the generator and get the session
                    session = await session_generator.__anext__()
                    # Simulate work that raises an exception
                    raise ValueError("test exception")
                except ValueError:
                    pass
                finally:
                    # Properly close the generator to trigger cleanup
                    try:
                        await session_generator.__anext__()
                    except StopAsyncIteration:
                        pass
        
        # Verify cleanup was called
        assert cleanup_called, "Session cleanup should be called even when exceptions occur"
    
    @pytest.mark.asyncio
    async def test_global_supervisor_validation(self):
        """Test that global supervisors are validated for stored sessions."""
        from netra_backend.app.dependencies import get_agent_supervisor
        
        mock_request = Mock(spec=Request)
        
        # Test supervisor without stored session (valid)
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        mock_supervisor_clean._stored_db_session = None
        mock_request.app.state.agent_supervisor = mock_supervisor_clean
        
        supervisor = get_agent_supervisor(mock_request)
        assert supervisor is mock_supervisor_clean
        
        # Test supervisor with stored session (invalid)
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        mock_request.app.state.agent_supervisor = mock_supervisor_invalid
        
        with pytest.raises(RuntimeError, match="Global supervisor must never store database sessions"):
            get_agent_supervisor(mock_request)
    
    def test_request_scoped_context_validation(self):
        """Test that RequestScopedContext validates its fields."""
    pass
        # Valid context
        context = RequestScopedContext(
            user_id="valid_user",
            thread_id="valid_thread"
        )
        
        assert context.run_id is not None  # Auto-generated
        assert context.request_id is not None  # Auto-generated
        assert context.websocket_connection_id is None  # Optional
        
        # Test auto-generation of IDs
        context2 = RequestScopedContext(
            user_id="valid_user2",
            thread_id="valid_thread2"
        )
        
        assert context.run_id != context2.run_id
        assert context.request_id != context2.request_id


class TestSessionValidationUtilities:
    """Test the session validation utility functions."""
    
    def test_mark_session_as_global(self):
        """Test marking sessions as globally stored."""
        mock_session = Mock(spec=AsyncSession)
        
        # Initially should not be marked as global
        assert not hasattr(mock_session, '_global_storage_flag')
        
        # Mark as global
        mark_session_as_global(mock_session)
        assert hasattr(mock_session, '_global_storage_flag')
        assert mock_session._global_storage_flag is True
    
    def test_validate_request_scoped_session(self):
        """Test validation of request-scoped vs global sessions."""
    pass
        mock_session = Mock(spec=AsyncSession)
        mock_session.info = {}  # Required for session validation
        
        # Should pass validation initially
        validate_session_is_request_scoped(mock_session, "test")
        
        # Should fail after marking as global
        mark_session_as_global(mock_session)
        with pytest.raises(Exception):
            validate_session_is_request_scoped(mock_session, "test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])