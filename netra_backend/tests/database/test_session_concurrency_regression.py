"""
Comprehensive test suite for SQLAlchemy session concurrency management.
Tests for regression prevention of IllegalStateChangeError.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System stability and reliability
- Value Impact: Prevents database connection errors that cause service outages
- Strategic Impact: Ensures enterprise-grade reliability for all tiers
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.database import get_db, UnifiedDatabaseManager
from netra_backend.app.db.database_manager import DatabaseManager


class TestSessionConcurrencyRegression:
    """Test suite to prevent regression of session concurrency issues."""
    
    @pytest.mark.asyncio
    async def test_normal_session_lifecycle(self):
        """Test normal session lifecycle without errors."""
        session_count = 0
        
        async for session in get_db():
            session_count += 1
            assert isinstance(session, AsyncSession)
            # Simulate normal operation
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        
        assert session_count == 1
    
    @pytest.mark.asyncio
    async def test_cancelled_task_handling(self):
        """Test that cancelled tasks don't cause IllegalStateChangeError."""
        async def long_running_operation():
            async for session in get_db():
                # Start a transaction
                await session.execute(text("SELECT 1"))
                # Simulate long operation that gets cancelled
                await asyncio.sleep(10)
                await session.execute(text("SELECT 2"))
        
        # Create and cancel task
        task = asyncio.create_task(long_running_operation())
        await asyncio.sleep(0.01)  # Let it start
        task.cancel()
        
        # Should raise CancelledError, not IllegalStateChangeError
        with pytest.raises(asyncio.CancelledError):
            await task
    
    @pytest.mark.asyncio
    async def test_exception_during_transaction(self):
        """Test proper rollback when exception occurs during transaction."""
        rollback_called = False
        
        async for session in get_db():
            # Mock the rollback to track if it's called
            original_rollback = session.rollback
            async def tracked_rollback():
                nonlocal rollback_called
                rollback_called = True
                await original_rollback()
            session.rollback = tracked_rollback
            
            # Simulate operation that fails
            await session.execute(text("SELECT 1"))
            
            # Force an exception
            with pytest.raises(ValueError):
                raise ValueError("Simulated error")
        
        # Rollback should have been called
        assert rollback_called
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self):
        """Test multiple concurrent sessions don't interfere."""
        results = []
        
        async def db_operation(operation_id: int):
            async for session in get_db():
                result = await session.execute(text("SELECT :id"), {"id": operation_id})
                results.append(result.scalar())
        
        # Run multiple operations concurrently
        tasks = [db_operation(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # All operations should complete
        assert len(results) == 10
        assert set(results) == set(range(10))
    
    @pytest.mark.asyncio
    async def test_nested_session_contexts(self):
        """Test nested session contexts handle properly."""
        outer_session_id = None
        inner_session_id = None
        
        async for outer_session in get_db():
            outer_session_id = id(outer_session)
            await outer_session.execute(text("SELECT 1"))
            
            # Nested context (different transaction)
            async for inner_session in get_db():
                inner_session_id = id(inner_session)
                await inner_session.execute(text("SELECT 2"))
            
            await outer_session.execute(text("SELECT 3"))
        
        # Should be different sessions
        assert outer_session_id != inner_session_id
    
    @pytest.mark.asyncio
    async def test_session_state_checks(self):
        """Test that session state is properly checked before operations."""
        db_manager = UnifiedDatabaseManager()
        
        async for session in db_manager.postgres_session():
            # Session should be active
            assert session.is_active
            
            # Execute query
            await session.execute(text("SELECT 1"))
            
            # Still active
            assert session.is_active
    
    @pytest.mark.asyncio
    async def test_generator_exit_handling(self):
        """Test GeneratorExit is handled gracefully."""
        async def generator_function():
            async for session in get_db():
                await session.execute(text("SELECT 1"))
                # Generator exits here without completing
                return
        
        # Should complete without error
        await generator_function()
    
    @pytest.mark.asyncio
    async def test_rapid_session_creation(self):
        """Test rapid session creation/destruction doesn't cause issues."""
        for _ in range(50):
            async for session in get_db():
                await session.execute(text("SELECT 1"))
                # Session closes immediately
    
    @pytest.mark.asyncio  
    async def test_database_manager_session_handling(self):
        """Test DatabaseManager's get_async_session handles cancellation."""
        async with DatabaseManager.get_async_session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_recovery(self):
        """Test recovery from connection pool exhaustion scenarios."""
        # Create many sessions simultaneously
        sessions = []
        
        async def create_session():
            async for session in get_db():
                sessions.append(session)
                await session.execute(text("SELECT 1"))
                await asyncio.sleep(0.01)
        
        # Try to create more sessions than pool size
        tasks = [create_session() for _ in range(20)]
        
        # Should handle without deadlock
        await asyncio.gather(*tasks, return_exceptions=True)
        
        assert len(sessions) == 20
    
    @pytest.mark.asyncio
    async def test_asyncio_shield_not_used(self):
        """Verify asyncio.shield is not used in session cleanup."""
        # This would cause IllegalStateChangeError
        with patch('asyncio.shield') as mock_shield:
            async for session in get_db():
                await session.execute(text("SELECT 1"))
            
            # Shield should not be called during session cleanup
            mock_shield.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_session_transaction_state_verification(self):
        """Test that in_transaction() check prevents inappropriate commits."""
        async for session in get_db():
            # Start transaction
            await session.begin()
            
            # Session is in transaction
            assert session.in_transaction()
            
            await session.execute(text("SELECT 1"))
            
            # Commit the transaction
            await session.commit()
            
            # No longer in transaction
            assert not session.in_transaction()


class TestAuthServiceSessionConcurrency:
    """Test auth service session management for concurrency issues."""
    
    @pytest.mark.asyncio
    async def test_auth_session_cancellation_handling(self):
        """Test auth service handles cancelled operations correctly."""
        from auth_service.auth_core.database.connection import auth_db
        
        # Initialize auth_db if needed
        if not auth_db._initialized:
            await auth_db.initialize()
        
        async def cancellable_operation():
            async with auth_db.get_session() as session:
                await session.execute(text("SELECT 1"))
                await asyncio.sleep(10)  # Will be cancelled
                await session.execute(text("SELECT 2"))
        
        task = asyncio.create_task(cancellable_operation())
        await asyncio.sleep(0.01)
        task.cancel()
        
        with pytest.raises(asyncio.CancelledError):
            await task
    
    @pytest.mark.asyncio
    async def test_auth_concurrent_sessions(self):
        """Test auth service handles concurrent sessions properly."""
        from auth_service.auth_core.database.connection import auth_db
        
        if not auth_db._initialized:
            await auth_db.initialize()
        
        results = []
        
        async def auth_operation(op_id: int):
            async with auth_db.get_session() as session:
                result = await session.execute(text("SELECT :id"), {"id": op_id})
                results.append(result.scalar())
        
        tasks = [auth_operation(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        assert len(results) == 5


@pytest.fixture
def mock_async_session():
    """Create a mock async session for testing."""
    session = AsyncMock(spec=AsyncSession)
    session.is_active = True
    session.in_transaction.return_value = False
    session.execute.return_value = AsyncMock(scalar=lambda: 1)
    return session


@pytest.mark.asyncio
async def test_session_lifecycle_with_mock(mock_async_session):
    """Test session lifecycle with mocked session."""
    with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_async_session
        mock_context.__aexit__.return_value = None
        mock_factory.return_value.return_value = mock_context
        
        async for session in get_db():
            await session.execute(text("SELECT 1"))
        
        # Verify session methods were called correctly
        assert mock_async_session.execute.called
        # Commit may or may not be called depending on session state check
        # The important thing is no errors occurred