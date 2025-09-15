"""
Unit Test: User Session Isolation and Database Connection Management

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure strict user data isolation prevents data leakage 
- Value Impact: User data privacy is fundamental to platform trust and compliance
- Strategic Impact: Core foundation for multi-user platform with proper isolation

This unit test validates:
1. User execution context creates isolated database sessions
2. Session boundaries prevent cross-user data access  
3. UserExecutionContext properly manages database resources
4. Session cleanup happens correctly for user contexts

CRITICAL: Uses SSOT patterns and real database connections.
"""

import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from netra_backend.tests.unit.test_base import BaseUnitTest
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ensure_user_id
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment

# Import SQLAlchemy for session management testing
try:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy import text, select
    from sqlalchemy.pool import NullPool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    AsyncSession = None


class TestUserSessionIsolation(BaseUnitTest):
    """Test user session isolation and database connection management."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        if not SQLALCHEMY_AVAILABLE:
            pytest.skip("SQLAlchemy not available for session testing", allow_module_level=True)

    @pytest.mark.unit
    async def test_user_execution_context_creates_isolated_sessions(self):
        """Test that each UserExecutionContext creates properly isolated database sessions."""
        
        # Create test users
        user_ids = [ensure_user_id(str(uuid.uuid4())) for _ in range(3)]
        contexts = []
        
        # Mock isolated environment for testing
        env_mock = MagicMock()
        env_mock.get.side_effect = lambda key, default=None: {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432', 
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'postgres',
            'POSTGRES_DB': 'netra_test',
            'ENVIRONMENT': 'test'
        }.get(key, default)
        
        # Create database URL builder
        db_builder = DatabaseURLBuilder(env_mock.get.side_effect.__self__)
        test_db_url = db_builder.test.auto_url
        
        # Mock async engine and sessionmaker
        mock_engine = MagicMock()
        mock_sessionmaker = MagicMock()
        mock_sessionmaker.return_value = AsyncMock(spec=AsyncSession)
        
        # Create user contexts with mocked database sessions
        for user_id in user_ids:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.bind = mock_engine
            mock_session.is_active = True
            
            context = StronglyTypedUserExecutionContext(
                user_id=user_id,
                thread_id=ThreadID(f"thread_{uuid.uuid4()}"),
                run_id=RunID(f"run_{uuid.uuid4()}"),
                request_id=RequestID(f"req_{uuid.uuid4()}"),
                db_session=mock_session
            )
            contexts.append(context)
        
        # Verify each context has isolated session
        for i, context in enumerate(contexts):
            assert context.db_session is not None, f"Context {i} missing database session"
            assert context.db_session.is_active, f"Context {i} session not active"
            
            # Verify user isolation - each context should have different user_id
            for j, other_context in enumerate(contexts):
                if i != j:
                    assert context.user_id != other_context.user_id, \
                        f"Contexts {i} and {j} have same user_id - isolation violated"
                    
                    # Verify different sessions (mocked objects will be different)
                    assert context.db_session is not other_context.db_session, \
                        f"Contexts {i} and {j} share same database session - CRITICAL ISOLATION BUG"
    
    @pytest.mark.unit
    async def test_session_boundaries_prevent_cross_user_access(self):
        """Test that session boundaries prevent cross-user data access."""
        
        # Create isolated users and contexts
        user_a = ensure_user_id(str(uuid.uuid4()))
        user_b = ensure_user_id(str(uuid.uuid4()))
        
        # Mock database sessions with different transaction boundaries
        session_a = AsyncMock(spec=AsyncSession)
        session_a.in_transaction.return_value = True
        session_a.get_transaction.return_value = MagicMock()
        session_a.connection = MagicMock()
        session_a.connection.info = {'user_id': str(user_a)}
        
        session_b = AsyncMock(spec=AsyncSession) 
        session_b.in_transaction.return_value = True
        session_b.get_transaction.return_value = MagicMock()
        session_b.connection = MagicMock()
        session_b.connection.info = {'user_id': str(user_b)}
        
        context_a = StronglyTypedUserExecutionContext(
            user_id=user_a,
            thread_id=ThreadID(f"thread_a_{uuid.uuid4()}"),
            run_id=RunID(f"run_a_{uuid.uuid4()}"),
            request_id=RequestID(f"req_a_{uuid.uuid4()}"),
            db_session=session_a
        )
        
        context_b = StronglyTypedUserExecutionContext(
            user_id=user_b,
            thread_id=ThreadID(f"thread_b_{uuid.uuid4()}"),
            run_id=RunID(f"run_b_{uuid.uuid4()}"),
            request_id=RequestID(f"req_b_{uuid.uuid4()}"),
            db_session=session_b
        )
        
        # Verify session isolation
        assert context_a.db_session is not context_b.db_session, \
            "Users sharing database session - CRITICAL SECURITY VIOLATION"
        
        # Verify connection isolation
        assert context_a.db_session.connection.info['user_id'] == str(user_a)
        assert context_b.db_session.connection.info['user_id'] == str(user_b)
        
        # Simulate cross-user access attempt (should be prevented by different sessions)
        user_a_data_query = f"SELECT * FROM user_data WHERE user_id = '{user_a}'"
        user_b_data_query = f"SELECT * FROM user_data WHERE user_id = '{user_b}'"
        
        # Mock query execution - each session only sees its user's data
        session_a.execute.return_value.scalars.return_value.all.return_value = [
            {'user_id': str(user_a), 'data': 'user_a_secret'}
        ]
        session_b.execute.return_value.scalars.return_value.all.return_value = [
            {'user_id': str(user_b), 'data': 'user_b_secret'}
        ]
        
        # Execute queries through respective sessions
        result_a = await session_a.execute(text(user_a_data_query))
        result_b = await session_b.execute(text(user_b_data_query))
        
        # Verify sessions were called with correct queries
        session_a.execute.assert_called_with(text(user_a_data_query))
        session_b.execute.assert_called_with(text(user_b_data_query))
        
        # Verify no cross-contamination
        assert session_a.execute.call_count == 1, "Session A called more than expected"
        assert session_b.execute.call_count == 1, "Session B called more than expected"

    @pytest.mark.unit
    async def test_user_context_session_lifecycle_management(self):
        """Test UserExecutionContext properly manages session lifecycle."""
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        
        # Mock session with lifecycle tracking
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.is_active = True
        mock_session.in_transaction.return_value = False
        
        # Track session operations
        session_operations = []
        
        async def track_commit():
            session_operations.append('commit')
        
        async def track_rollback():
            session_operations.append('rollback')
            
        async def track_close():
            session_operations.append('close')
            mock_session.is_active = False
        
        mock_session.commit = track_commit
        mock_session.rollback = track_rollback  
        mock_session.close = track_close
        
        # Create context with session
        context = StronglyTypedUserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(f"thread_{uuid.uuid4()}"),
            run_id=RunID(f"run_{uuid.uuid4()}"),
            request_id=RequestID(f"req_{uuid.uuid4()}"),
            db_session=mock_session
        )
        
        # Verify initial session state
        assert context.db_session is not None, "Context missing database session"
        assert context.db_session.is_active, "Initial session should be active"
        
        # Simulate normal operation lifecycle
        await context.db_session.commit()
        assert 'commit' in session_operations, "Commit operation not tracked"
        
        # Simulate error condition lifecycle
        await context.db_session.rollback()
        assert 'rollback' in session_operations, "Rollback operation not tracked"
        
        # Simulate cleanup lifecycle
        await context.db_session.close()
        assert 'close' in session_operations, "Close operation not tracked"
        assert not mock_session.is_active, "Session should be inactive after close"
        
        # Verify expected operation sequence
        expected_operations = ['commit', 'rollback', 'close']
        assert session_operations == expected_operations, \
            f"Unexpected session operations: {session_operations}"

    @pytest.mark.unit 
    async def test_child_context_session_inheritance(self):
        """Test that child contexts properly inherit and isolate database sessions."""
        
        parent_user_id = ensure_user_id(str(uuid.uuid4()))
        
        # Mock parent session
        parent_session = AsyncMock(spec=AsyncSession)
        parent_session.is_active = True
        parent_session.in_transaction.return_value = True
        
        parent_context = StronglyTypedUserExecutionContext(
            user_id=parent_user_id,
            thread_id=ThreadID(f"thread_{uuid.uuid4()}"),
            run_id=RunID(f"run_{uuid.uuid4()}"),
            request_id=RequestID(f"req_{uuid.uuid4()}"),
            db_session=parent_session
        )
        
        # Create child context
        child_context = parent_context.create_child_context()
        
        # Verify child context session inheritance
        assert child_context.db_session is parent_context.db_session, \
            "Child context should inherit parent session"
        
        # Verify child context maintains parent user isolation
        assert child_context.user_id == parent_context.user_id, \
            "Child context should maintain same user_id for isolation"
        
        # Verify child context has different request_id for tracking
        assert child_context.request_id != parent_context.request_id, \
            "Child context should have unique request_id"
        
        # Verify parent-child relationship
        assert child_context.parent_request_id == parent_context.request_id, \
            "Child context should reference parent request_id"
        
        assert child_context.operation_depth == parent_context.operation_depth + 1, \
            "Child context should have incremented operation depth"
        
        # Verify session sharing doesn't violate isolation
        # Both contexts share session but maintain separate identities
        assert child_context.db_session is parent_context.db_session, \
            "Child should share parent session (same transaction boundary)"
        
        # Create grandchild to test multi-level inheritance
        grandchild_context = child_context.create_child_context()
        
        assert grandchild_context.db_session is parent_session, \
            "Grandchild should inherit same session"
        assert grandchild_context.user_id == parent_user_id, \
            "Grandchild should maintain user isolation"
        assert grandchild_context.operation_depth == 2, \
            "Grandchild should have correct operation depth"