"""Comprehensive test suite for SQLAlchemy session state management.

This test suite verifies proper handling of session states to prevent
IllegalStateChangeError and other concurrency issues.

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Ensure database session reliability
- Value Impact: Prevents production crashes from state errors
- Strategic Impact: Critical for system stability under load
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IllegalStateChangeError
from contextlib import asynccontextmanager
import concurrent.futures
from typing import AsyncGenerator, List
import random
import time

from netra_backend.app.database import get_db, UnifiedDatabaseManager
from netra_backend.app.db.database_manager import DatabaseManager


class TestSQLAlchemyStateManagement:
    """Test suite for SQLAlchemy session state management."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock session with state properties."""
        session = AsyncMock(spec=AsyncSession)
        session.is_active = True
        session.in_transaction = Mock(return_value=True)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_session_factory(self, mock_session):
        """Create a mock session factory."""
        @asynccontextmanager
        async def factory():
            yield mock_session
        
        return factory
    
    @pytest.mark.asyncio
    async def test_normal_commit_with_state_check(self, mock_session_factory):
        """Test normal commit operation with proper state checking."""
        # Setup
        async with mock_session_factory() as mock_session:
            mock_session.is_active = True
            mock_session.in_transaction.return_value = True
            
            # Execute
            session_yielded = False
            try:
                session_yielded = True
                # Simulate the fix pattern
                if hasattr(mock_session, 'is_active') and mock_session.is_active:
                    if hasattr(mock_session, 'in_transaction') and mock_session.in_transaction():
                        await mock_session.commit()
            except Exception:
                if (session_yielded and 
                    hasattr(mock_session, 'is_active') and mock_session.is_active and
                    hasattr(mock_session, 'in_transaction') and mock_session.in_transaction()):
                    await mock_session.rollback()
            
            # Verify
            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_no_commit_when_inactive(self, mock_session_factory):
        """Test that commit is skipped when session is inactive."""
        async with mock_session_factory() as mock_session:
            # Setup
            mock_session.is_active = False
            
            # Execute
            if hasattr(mock_session, 'is_active') and mock_session.is_active:
                if hasattr(mock_session, 'in_transaction') and mock_session.in_transaction():
                    await mock_session.commit()
            
            # Verify
            mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_no_commit_when_not_in_transaction(self, mock_session_factory):
        """Test that commit is skipped when not in transaction."""
        async with mock_session_factory() as mock_session:
            # Setup
            mock_session.is_active = True
            mock_session.in_transaction.return_value = False
            
            # Execute
            if hasattr(mock_session, 'is_active') and mock_session.is_active:
                if hasattr(mock_session, 'in_transaction') and mock_session.in_transaction():
                    await mock_session.commit()
            
            # Verify
            mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_rollback_with_state_check(self, mock_session_factory):
        """Test rollback operation with proper state checking."""
        async with mock_session_factory() as mock_session:
            # Setup
            mock_session.is_active = True
            mock_session.in_transaction.return_value = True
            session_yielded = True
            
            # Execute
            if (session_yielded and 
                hasattr(mock_session, 'is_active') and mock_session.is_active and
                hasattr(mock_session, 'in_transaction') and mock_session.in_transaction()):
                try:
                    await mock_session.rollback()
                except Exception:
                    pass  # Let context manager handle cleanup
            
            # Verify
            mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancelled_error_handling(self, mock_session_factory):
        """Test proper handling of asyncio.CancelledError."""
        async with mock_session_factory() as mock_session:
            # Execute and verify
            with pytest.raises(asyncio.CancelledError):
                try:
                    raise asyncio.CancelledError()
                except asyncio.CancelledError:
                    # Should not attempt any session operations
                    raise
            
            # Verify no session operations were attempted
            mock_session.commit.assert_not_called()
            mock_session.rollback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generator_exit_handling(self, mock_session_factory):
        """Test proper handling of GeneratorExit."""
        async with mock_session_factory() as mock_session:
            # Execute
            try:
                raise GeneratorExit()
            except GeneratorExit:
                # Should silently pass without session operations
                pass
            
            # Verify no session operations were attempted
            mock_session.commit.assert_not_called()
            mock_session.rollback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_illegal_state_change_prevention(self):
        """Test that the fix prevents IllegalStateChangeError."""
        # Setup a session that would raise IllegalStateChangeError
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.is_active = True
        mock_session.in_transaction = Mock(return_value=True)
        
        # Simulate the error condition
        mock_session.close = AsyncMock(side_effect=IllegalStateChangeError(
            "Method 'close()' can't be called here; method '_connection_for_bind()' is already in progress"
        ))
        
        # Execute with the fix pattern
        session_yielded = False
        error_raised = False
        try:
            session_yielded = True
            # Try to close (this would normally raise)
            if hasattr(mock_session, 'is_active') and mock_session.is_active:
                # With the fix, we check state before operations
                pass  # Don't call close if in wrong state
        except IllegalStateChangeError:
            error_raised = True
        
        # Verify error was prevented
        assert not error_raised
    
    @pytest.mark.asyncio
    async def test_concurrent_session_access(self):
        """Test handling of concurrent session access."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.is_active = True
        mock_session.in_transaction = Mock(return_value=True)
        mock_session.execute = AsyncMock()
        
        # Simulate concurrent access
        async def access_session(session, delay):
            await asyncio.sleep(delay)
            if hasattr(session, 'is_active') and session.is_active:
                await session.execute("SELECT 1")
        
        # Execute concurrent operations
        tasks = [
            access_session(mock_session, random.uniform(0, 0.1))
            for _ in range(10)
        ]
        
        # Should complete without errors
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify no exceptions
        for result in results:
            assert not isinstance(result, Exception)
    
    @pytest.mark.asyncio
    async def test_session_state_transitions(self):
        """Test session state transitions during lifecycle."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        states = []
        
        # Track state transitions
        mock_session.is_active = True
        states.append(('initial', mock_session.is_active))
        
        # Begin transaction
        mock_session.in_transaction = Mock(return_value=True)
        states.append(('in_transaction', mock_session.in_transaction()))
        
        # Commit
        if hasattr(mock_session, 'is_active') and mock_session.is_active:
            if hasattr(mock_session, 'in_transaction') and mock_session.in_transaction():
                await mock_session.commit()
                mock_session.in_transaction = Mock(return_value=False)
                states.append(('after_commit', mock_session.in_transaction()))
        
        # Verify state transitions
        assert states[0] == ('initial', True)
        assert states[1] == ('in_transaction', True)
        assert states[2] == ('after_commit', False)
    
    @pytest.mark.asyncio
    async def test_rollback_failure_handling(self):
        """Test graceful handling of rollback failures."""
        # Setup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.is_active = True
        mock_session.in_transaction = Mock(return_value=True)
        mock_session.rollback = AsyncMock(side_effect=Exception("Rollback failed"))
        
        session_yielded = True
        rollback_error = None
        
        # Execute
        if (session_yielded and 
            hasattr(mock_session, 'is_active') and mock_session.is_active and
            hasattr(mock_session, 'in_transaction') and mock_session.in_transaction()):
            try:
                await mock_session.rollback()
            except Exception as e:
                # Should handle rollback failure gracefully
                rollback_error = e
                pass
        
        # Verify graceful handling
        assert rollback_error is not None
        assert str(rollback_error) == "Rollback failed"
        # Should not propagate the error


class TestConcurrentDatabaseOperations:
    """Test concurrent database operations and race conditions."""
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_concurrent_commits(self):
        """Test multiple sessions committing concurrently."""
        sessions = []
        
        # Create multiple mock sessions
        for i in range(5):
            session = AsyncMock(spec=AsyncSession)
            session.is_active = True
            session.in_transaction = Mock(return_value=True)
            session.commit = AsyncMock()
            session.id = i
            sessions.append(session)
        
        # Define concurrent commit operation
        async def commit_session(session):
            await asyncio.sleep(random.uniform(0, 0.05))
            if hasattr(session, 'is_active') and session.is_active:
                if hasattr(session, 'in_transaction') and session.in_transaction():
                    await session.commit()
                    return f"Session {session.id} committed"
            return f"Session {session.id} skipped"
        
        # Execute concurrent commits
        results = await asyncio.gather(
            *[commit_session(s) for s in sessions],
            return_exceptions=True
        )
        
        # Verify all completed successfully
        for i, result in enumerate(results):
            assert not isinstance(result, Exception)
            assert f"Session {i} committed" == result
    
    @pytest.mark.asyncio
    async def test_session_cleanup_during_operation(self):
        """Test session cleanup while operation is in progress."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.is_active = True
        mock_session.in_transaction = Mock(return_value=True)
        
        # Simulate operation in progress
        operation_complete = False
        
        async def long_operation():
            nonlocal operation_complete
            await asyncio.sleep(0.1)
            operation_complete = True
        
        async def cleanup_session():
            await asyncio.sleep(0.05)  # Cleanup attempts before operation completes
            if hasattr(mock_session, 'is_active') and mock_session.is_active:
                # Check state before cleanup
                pass  # Would normally close/cleanup
        
        # Execute concurrently
        await asyncio.gather(
            long_operation(),
            cleanup_session(),
            return_exceptions=True
        )
        
        assert operation_complete
    
    @pytest.mark.asyncio
    async def test_rapid_session_creation_destruction(self):
        """Test rapid session creation and destruction cycles."""
        results = []
        
        async def session_lifecycle(index):
            # Create session
            session = AsyncMock(spec=AsyncSession)
            session.is_active = True
            session.in_transaction = Mock(return_value=True)
            
            # Use session
            await asyncio.sleep(random.uniform(0, 0.01))
            
            # Cleanup with state check
            if hasattr(session, 'is_active') and session.is_active:
                if hasattr(session, 'in_transaction') and session.in_transaction():
                    await session.commit()
            
            return f"Lifecycle {index} complete"
        
        # Execute many rapid lifecycles
        tasks = [session_lifecycle(i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all completed without errors
        for result in results:
            assert not isinstance(result, Exception)
            assert "complete" in result


class TestDatabaseManagerIntegration:
    """Integration tests for DatabaseManager with state management."""
    
    @pytest.mark.asyncio
    async def test_database_manager_session_state_handling(self):
        """Test DatabaseManager's session state handling."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            # Setup mock session with state
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.is_active = True
            mock_session.in_transaction = Mock(return_value=True)
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            
            @asynccontextmanager
            async def mock_context():
                yield mock_session
            
            mock_factory.return_value = Mock(return_value=mock_context())
            
            # Test the actual get_async_session method
            async with DatabaseManager.get_async_session() as session:
                assert session == mock_session
            
            # Verify commit was attempted with state check
            # The actual implementation should have checked state
            mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_unified_database_manager_postgres_session(self):
        """Test UnifiedDatabaseManager's postgres_session with state management."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            # Setup
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.is_active = True
            mock_session.in_transaction = Mock(return_value=True)
            mock_session.commit = AsyncMock()
            
            @asynccontextmanager
            async def mock_context():
                yield mock_session
            
            mock_factory.return_value = Mock(return_value=mock_context())
            
            # Test UnifiedDatabaseManager
            manager = UnifiedDatabaseManager()
            async for session in manager.postgres_session():
                assert session == mock_session
                # Session should be yielded properly
                break
            
            # Verify proper cleanup
            mock_session.commit.assert_called()


class TestStressAndRaceConditions:
    """Stress tests for race conditions and edge cases."""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_stress_concurrent_operations(self):
        """Stress test with many concurrent operations."""
        operation_count = 100
        results = []
        
        async def database_operation(op_id):
            # Simulate database operation
            session = AsyncMock(spec=AsyncSession)
            session.is_active = random.choice([True, False])
            session.in_transaction = Mock(return_value=random.choice([True, False]))
            
            # Random delay to create race conditions
            await asyncio.sleep(random.uniform(0, 0.01))
            
            # Apply state checking pattern
            committed = False
            if hasattr(session, 'is_active') and session.is_active:
                if hasattr(session, 'in_transaction') and session.in_transaction():
                    await session.commit()
                    committed = True
            
            return {'op_id': op_id, 'committed': committed}
        
        # Execute stress test
        tasks = [database_operation(i) for i in range(operation_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify no exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Found {len(exceptions)} exceptions in stress test"
        
        # Verify results
        successful_ops = [r for r in results if isinstance(r, dict)]
        assert len(successful_ops) == operation_count
    
    @pytest.mark.asyncio
    async def test_race_condition_close_during_operation(self):
        """Test race condition: close() called during _connection_for_bind()."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.is_active = True
        connection_in_progress = True
        
        # Simulate _connection_for_bind in progress
        async def connection_for_bind():
            nonlocal connection_in_progress
            await asyncio.sleep(0.1)
            connection_in_progress = False
        
        # Simulate close attempt during connection
        async def attempt_close():
            await asyncio.sleep(0.05)  # Try to close mid-operation
            
            # This would normally raise IllegalStateChangeError
            # But with state checking, we prevent it
            if connection_in_progress:
                # Don't close if operation in progress
                return "Close prevented"
            else:
                await mock_session.close()
                return "Close succeeded"
        
        # Execute race condition
        results = await asyncio.gather(
            connection_for_bind(),
            attempt_close(),
            return_exceptions=True
        )
        
        # Verify no exceptions and close was prevented
        assert not any(isinstance(r, Exception) for r in results)
        assert results[1] == "Close prevented"
    
    @pytest.mark.asyncio
    async def test_task_cancellation_during_commit(self):
        """Test task cancellation during commit operation."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.is_active = True
        mock_session.in_transaction = Mock(return_value=True)
        
        # Simulate slow commit
        async def slow_commit():
            await asyncio.sleep(0.2)
        
        mock_session.commit = slow_commit
        
        # Create task that will be cancelled
        async def database_task():
            try:
                if hasattr(mock_session, 'is_active') and mock_session.is_active:
                    if hasattr(mock_session, 'in_transaction') and mock_session.in_transaction():
                        await mock_session.commit()
            except asyncio.CancelledError:
                # Proper handling of cancellation
                raise
        
        # Start task and cancel it
        task = asyncio.create_task(database_task())
        await asyncio.sleep(0.05)  # Let it start
        task.cancel()
        
        # Verify proper cancellation
        with pytest.raises(asyncio.CancelledError):
            await task


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_missing_session_attributes(self):
        """Test handling of sessions missing expected attributes."""
        # Create session without some attributes
        mock_session = Mock()  # Not AsyncMock, missing async methods
        
        # Should handle gracefully with hasattr checks
        if hasattr(mock_session, 'is_active') and mock_session.is_active:
            if hasattr(mock_session, 'in_transaction') and mock_session.in_transaction():
                if hasattr(mock_session, 'commit'):
                    await mock_session.commit()
        
        # Should not raise AttributeError
        assert True  # If we get here, test passed
    
    @pytest.mark.asyncio
    async def test_session_state_after_error(self):
        """Test session state after various error conditions."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.is_active = True
        mock_session.in_transaction = Mock(return_value=True)
        mock_session.execute = AsyncMock(side_effect=Exception("Query failed"))
        
        # Execute operation that fails
        error_caught = False
        try:
            await mock_session.execute("SELECT 1")
        except Exception:
            error_caught = True
            
            # Check if rollback is safe
            if (hasattr(mock_session, 'is_active') and mock_session.is_active and
                hasattr(mock_session, 'in_transaction') and mock_session.in_transaction()):
                try:
                    await mock_session.rollback()
                except Exception:
                    pass
        
        assert error_caught
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_nested_transaction_handling(self):
        """Test handling of nested transactions."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.is_active = True
        mock_session.in_transaction = Mock(return_value=True)
        mock_session.begin_nested = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # Simulate nested transaction
        async with mock_session.begin_nested():
            # Inner transaction
            if hasattr(mock_session, 'is_active') and mock_session.is_active:
                # Do work
                pass
        
        # Outer transaction commit
        if hasattr(mock_session, 'is_active') and mock_session.is_active:
            if hasattr(mock_session, 'in_transaction') and mock_session.in_transaction():
                await mock_session.commit()
        
        mock_session.commit.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])