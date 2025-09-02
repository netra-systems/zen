"""Comprehensive Session Isolation Tests

This module tests the database session management patterns to ensure proper per-request
isolation and prevent session leakage between users.

Tests cover:
1. Session isolation between concurrent users
2. Session validation and tagging
3. DatabaseSessionManager functionality
4. Agent session storage validation
5. Transaction isolation
6. Error handling and cleanup
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Dict, Any
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from netra_backend.app.database.session_manager import (
    DatabaseSessionManager,
    SessionScopeValidator,
    SessionIsolationError,
    SessionManagerError,
    SessionLifecycleError,
    managed_session,
    validate_agent_session_isolation
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    InvalidContextError
)
from netra_backend.app.agents.base_agent import BaseAgent


class TestDatabaseSessionManager:
    """Test DatabaseSessionManager functionality."""
    
    @pytest.fixture
    async def mock_session(self) -> AsyncMock:
        """Create mock AsyncSession for testing."""
        session = AsyncMock(spec=AsyncSession)
        session.info = {}
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        session.begin = AsyncMock()
        session.refresh = AsyncMock()
        return session
    
    @pytest.fixture
    def user_context(self, mock_session: AsyncMock) -> UserExecutionContext:
        """Create user execution context with mock session."""
        return UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456", 
            run_id="run_789",
            db_session=mock_session,
            request_id="req_abc"
        )
    
    async def test_session_manager_initialization(self, user_context: UserExecutionContext):
        """Test session manager initialization and validation."""
        session_manager = DatabaseSessionManager(user_context)
        
        assert session_manager.context == user_context
        assert session_manager.session == user_context.db_session
        assert session_manager._is_active is True
        assert session_manager._transaction_count == 0
        assert session_manager._operation_count == 0
        
        # Verify session tagging
        session_info = session_manager.session.info
        assert session_info['user_id'] == user_context.user_id
        assert session_info['run_id'] == user_context.run_id
        assert session_info['request_id'] == user_context.request_id
        assert session_info['is_request_scoped'] is True
    
    async def test_invalid_context_initialization(self):
        """Test session manager fails with invalid context."""
        with pytest.raises(SessionManagerError, match="Invalid context type"):
            DatabaseSessionManager("invalid_context")
    
    async def test_missing_session_initialization(self):
        """Test session manager fails when context lacks session."""
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="thread_123",
            run_id="run_456",
            db_session=None  # Missing session
        )
        
        with pytest.raises(SessionManagerError, match="must contain a database session"):
            DatabaseSessionManager(context)
    
    async def test_session_ownership_validation(self, user_context: UserExecutionContext):
        """Test session ownership validation."""
        session_manager = DatabaseSessionManager(user_context)
        
        # Should pass with correct ownership
        session_manager._validate_session_ownership()
        
        # Modify session info to simulate wrong user
        session_manager.session.info['user_id'] = 'different_user'
        
        with pytest.raises(SessionIsolationError, match="Session belongs to user"):
            session_manager._validate_session_ownership()
    
    async def test_execute_with_validation(self, user_context: UserExecutionContext):
        """Test query execution with session validation."""
        session_manager = DatabaseSessionManager(user_context)
        mock_query = Mock()
        mock_result = Mock()
        session_manager.session.execute.return_value = mock_result
        
        result = await session_manager.execute(mock_query)
        
        assert result == mock_result
        assert session_manager._operation_count == 1
        session_manager.session.execute.assert_called_once_with(mock_query)
    
    async def test_transaction_context_manager(self, user_context: UserExecutionContext):
        """Test transaction context manager."""
        session_manager = DatabaseSessionManager(user_context)
        
        # Mock the context manager behavior properly
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=session_manager.session)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        session_manager.session.begin.return_value = mock_context_manager
        
        async with session_manager.transaction() as session:
            assert session == session_manager.session
            assert session_manager._transaction_count == 1
    
    async def test_commit_and_rollback(self, user_context: UserExecutionContext):
        """Test commit and rollback operations."""
        session_manager = DatabaseSessionManager(user_context)
        
        # Test successful commit
        await session_manager.commit()
        session_manager.session.commit.assert_called_once()
        
        # Test rollback
        await session_manager.rollback()
        session_manager.session.rollback.assert_called_once()
    
    async def test_commit_with_error_rollback(self, user_context: UserExecutionContext):
        """Test automatic rollback on commit error."""
        session_manager = DatabaseSessionManager(user_context)
        
        # Make commit fail
        session_manager.session.commit.side_effect = SQLAlchemyError("Commit failed")
        
        with pytest.raises(SQLAlchemyError):
            await session_manager.commit()
        
        # Should have called rollback
        session_manager.session.rollback.assert_called_once()
    
    async def test_session_close(self, user_context: UserExecutionContext):
        """Test session close functionality."""
        session_manager = DatabaseSessionManager(user_context)
        
        await session_manager.close()
        
        assert session_manager._is_active is False
        session_manager.session.close.assert_called_once()
        
        # Subsequent operations should fail
        with pytest.raises(SessionLifecycleError):
            session_manager._validate_session_ownership()
    
    async def test_idempotent_close(self, user_context: UserExecutionContext):
        """Test that close can be called multiple times safely."""
        session_manager = DatabaseSessionManager(user_context)
        
        await session_manager.close()
        await session_manager.close()  # Should not raise
        
        # Close should only be called once on the session
        session_manager.session.close.assert_called_once()
    
    async def test_get_session_info(self, user_context: UserExecutionContext):
        """Test session info retrieval."""
        session_manager = DatabaseSessionManager(user_context)
        
        info = session_manager.get_session_info()
        
        assert info['user_id'] == user_context.user_id
        assert info['run_id'] == user_context.run_id
        assert info['request_id'] == user_context.request_id
        assert info['is_active'] is True
        assert info['transaction_count'] == 0
        assert info['operation_count'] == 0
        assert 'session_python_id' in info
        assert 'session_info' in info


class TestSessionScopeValidator:
    """Test SessionScopeValidator functionality."""
    
    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock session for validation tests."""
        session = AsyncMock(spec=AsyncSession)
        session.info = {}
        return session
    
    def test_validate_no_stored_sessions_clean_object(self):
        """Test validation passes for objects without stored sessions."""
        
        class CleanObject:
            def __init__(self):
                self.some_property = "value"
                self.another_property = 42
        
        obj = CleanObject()
        result = SessionScopeValidator.validate_no_stored_sessions(obj, "CleanObject")
        assert result is True
    
    def test_validate_no_stored_sessions_with_session(self, mock_session: AsyncMock):
        """Test validation fails for objects storing sessions."""
        
        class BadObject:
            def __init__(self, session):
                self.db_session = session  # This should trigger validation error
                self.other_property = "value"
        
        obj = BadObject(mock_session)
        
        with pytest.raises(SessionIsolationError, match="stores AsyncSession"):
            SessionScopeValidator.validate_no_stored_sessions(obj, "BadObject")
    
    def test_tag_session(self, mock_session: AsyncMock):
        """Test session tagging functionality."""
        user_id = "user_123"
        run_id = "run_456" 
        request_id = "req_789"
        
        SessionScopeValidator.tag_session(mock_session, user_id, run_id, request_id)
        
        assert mock_session.info['user_id'] == user_id
        assert mock_session.info['run_id'] == run_id
        assert mock_session.info['request_id'] == request_id
        assert mock_session.info['is_request_scoped'] is True
        assert 'tagged_at' in mock_session.info
    
    def test_validate_session_context_success(self, mock_session: AsyncMock):
        """Test successful session context validation."""
        context = UserExecutionContext(
            user_id="user_123",
            thread_id="thread_456",
            run_id="run_789",
            request_id="req_abc"
        )
        
        # Tag session to match context
        mock_session.info = {
            'user_id': context.user_id,
            'run_id': context.run_id,
            'is_request_scoped': True
        }
        
        result = SessionScopeValidator.validate_session_context(mock_session, context)
        assert result is True
    
    def test_validate_session_context_user_mismatch(self, mock_session: AsyncMock):
        """Test session context validation fails with user mismatch."""
        context = UserExecutionContext(
            user_id="user_123",
            thread_id="thread_456", 
            run_id="run_789"
        )
        
        # Session tagged with different user
        mock_session.info = {
            'user_id': 'different_user',
            'run_id': context.run_id,
            'is_request_scoped': True
        }
        
        with pytest.raises(SessionIsolationError, match="Session user_id"):
            SessionScopeValidator.validate_session_context(mock_session, context)
    
    def test_validate_request_scoped_success(self, mock_session: AsyncMock):
        """Test request-scoped validation success."""
        mock_session.info = {'is_request_scoped': True}
        
        result = SessionScopeValidator.validate_request_scoped(mock_session)
        assert result is True
    
    def test_validate_request_scoped_failure(self, mock_session: AsyncMock):
        """Test request-scoped validation failure."""
        mock_session.info = {'is_request_scoped': False}
        
        with pytest.raises(SessionIsolationError, match="not marked as request-scoped"):
            SessionScopeValidator.validate_request_scoped(mock_session)


class TestAgentSessionIsolation:
    """Test agent session isolation requirements."""
    
    def test_validate_clean_agent(self):
        """Test validation passes for agents without stored sessions."""
        
        class CleanAgent(BaseAgent):
            async def execute_with_context(self, context, stream_updates=False):
                return "success"
        
        agent = CleanAgent()
        
        # Should pass validation
        result = validate_agent_session_isolation(agent)
        assert result is True
    
    def test_validate_agent_with_stored_session(self):
        """Test validation fails for agents storing sessions."""
        
        class BadAgent(BaseAgent):
            def __init__(self):
                super().__init__()
                # This violates session isolation
                self.db_session = AsyncMock(spec=AsyncSession)
            
            async def execute_with_context(self, context, stream_updates=False):
                return "success"
        
        agent = BadAgent()
        
        with pytest.raises(SessionIsolationError):
            validate_agent_session_isolation(agent)


class TestConcurrentSessionIsolation:
    """Test session isolation between concurrent users."""
    
    async def test_concurrent_user_sessions(self):
        """Test multiple users with concurrent database operations."""
        
        # Create contexts for different users
        user_contexts = []
        session_managers = []
        
        for i in range(3):
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.info = {}
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.close = AsyncMock()
            
            context = UserExecutionContext(
                user_id=f"user_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}",
                db_session=mock_session
            )
            
            user_contexts.append(context)
            session_managers.append(DatabaseSessionManager(context))
        
        # Simulate concurrent operations
        async def user_operation(session_manager: DatabaseSessionManager, user_id: str):
            """Simulate user-specific database operation."""
            mock_query = Mock()
            mock_query.user_id = user_id  # Tag query with user
            
            # Each user should only access their own session
            await session_manager.execute(mock_query)
            await session_manager.commit()
            return f"result_for_{user_id}"
        
        # Run operations concurrently
        tasks = [
            user_operation(sm, ctx.user_id)
            for sm, ctx in zip(session_managers, user_contexts)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify each user got their own result
        for i, result in enumerate(results):
            assert result == f"result_for_user_{i}"
        
        # Verify session isolation - each session should only be used by its owner
        for i, sm in enumerate(session_managers):
            session_info = sm.get_session_info()
            assert session_info['user_id'] == f"user_{i}"
            assert session_info['operation_count'] == 1
            assert session_info['transaction_count'] == 0  # No explicit transactions used
    
    async def test_session_leakage_prevention(self):
        """Test that sessions cannot leak between users."""
        
        # Create session for user A
        session_a = AsyncMock(spec=AsyncSession)
        session_a.info = {}
        context_a = UserExecutionContext(
            user_id="user_a",
            thread_id="thread_a",
            run_id="run_a", 
            db_session=session_a
        )
        
        # Create context for user B but try to use user A's session
        context_b = UserExecutionContext(
            user_id="user_b",
            thread_id="thread_b",
            run_id="run_b",
            db_session=session_a  # Same session - this should be detected
        )
        
        # Create session managers
        manager_a = DatabaseSessionManager(context_a)
        manager_b = DatabaseSessionManager(context_b)  # This will tag session with user_b
        
        # User A's operations should now fail because session was re-tagged for user B
        with pytest.raises(SessionIsolationError):
            await manager_a.execute(Mock())


class TestManagedSessionContextManager:
    """Test managed_session context manager."""
    
    @pytest.fixture
    def user_context_with_session(self) -> UserExecutionContext:
        """Create user context with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.info = {}
        mock_session.close = AsyncMock()
        
        return UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            db_session=mock_session
        )
    
    async def test_managed_session_success(self, user_context_with_session: UserExecutionContext):
        """Test successful managed session usage."""
        
        async with managed_session(user_context_with_session) as session_manager:
            assert isinstance(session_manager, DatabaseSessionManager)
            assert session_manager._is_active is True
            
            # Use session manager for operations
            await session_manager.execute(Mock())
            assert session_manager._operation_count == 1
        
        # Session should be closed after context exit
        assert session_manager._is_active is False
        user_context_with_session.db_session.close.assert_called_once()
    
    async def test_managed_session_with_exception(self, user_context_with_session: UserExecutionContext):
        """Test managed session cleanup on exception."""
        
        with pytest.raises(ValueError, match="Test exception"):
            async with managed_session(user_context_with_session) as session_manager:
                assert session_manager._is_active is True
                # Simulate error during operations
                raise ValueError("Test exception")
        
        # Session should still be closed despite exception
        user_context_with_session.db_session.close.assert_called_once()


class TestTransactionIsolation:
    """Test transaction isolation between users."""
    
    async def test_isolated_transactions(self):
        """Test that transactions are isolated between users."""
        
        # Create two users with separate sessions
        sessions = []
        contexts = []
        managers = []
        
        for i in range(2):
            session = AsyncMock(spec=AsyncSession)
            session.info = {}
            session.begin.return_value = AsyncMock()
            session.commit = AsyncMock()
            session.rollback = AsyncMock()
            
            context = UserExecutionContext(
                user_id=f"user_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}",
                db_session=session
            )
            
            sessions.append(session)
            contexts.append(context)
            managers.append(DatabaseSessionManager(context))
        
        # User 1 starts transaction
        async with managers[0].transaction():
            # User 2 should be able to start independent transaction
            async with managers[1].transaction():
                # Both transactions should be independent
                assert managers[0]._transaction_count == 1
                assert managers[1]._transaction_count == 1
        
        # Both transactions should complete independently
        sessions[0].begin.assert_called_once()
        sessions[1].begin.assert_called_once()


class TestErrorHandlingAndCleanup:
    """Test error handling and cleanup scenarios."""
    
    async def test_session_cleanup_on_manager_error(self):
        """Test session cleanup when session manager encounters errors."""
        
        session = AsyncMock(spec=AsyncSession)
        session.info = {}
        session.execute.side_effect = SQLAlchemyError("Database error")
        session.close = AsyncMock()
        
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread", 
            run_id="test_run",
            db_session=session
        )
        
        session_manager = DatabaseSessionManager(context)
        
        # Operation should fail but session should still be cleanable
        with pytest.raises(SQLAlchemyError):
            await session_manager.execute(Mock())
        
        # Session should still be closable
        await session_manager.close()
        session.close.assert_called_once()
    
    async def test_partial_initialization_cleanup(self):
        """Test cleanup when session manager initialization partially fails."""
        
        # Create invalid context that will cause initialization to fail
        with pytest.raises(SessionManagerError):
            DatabaseSessionManager("invalid_context")
        
        # No sessions should be leaked - test passes if no exceptions during cleanup


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])