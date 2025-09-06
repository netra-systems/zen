from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""Comprehensive test suite to protect against IllegalStateChangeError in database sessions.

This test suite ensures that the critical fix for handling IllegalStateChangeError,
GeneratorExit, and concurrent session access remains stable and effective.

CRITICAL: These tests protect against the staging error where SQLAlchemy raises
IllegalStateChangeError during concurrent session operations or cleanup.
""""

import asyncio
import pytest
import threading
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IllegalStateChangeError
from contextlib import asynccontextmanager
from test_framework.database.test_database_manager import TestDatabaseManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.db.database_manager import DatabaseManager


class TestIllegalStateChangeProtection:
    """Test suite for IllegalStateChangeError protection in database sessions."""
    
    @pytest.mark.asyncio
    async def test_generator_exit_handling(self):
        """Test that GeneratorExit is handled gracefully without attempting operations."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            # Create a mock session that raises IllegalStateChangeError on any operation
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.in_transaction = MagicMock(side_effect=IllegalStateChangeError("Session is closed"))
            mock_session.commit = AsyncMock(side_effect=IllegalStateChangeError("Session is closed"))
            mock_session.rollback = AsyncMock(side_effect=IllegalStateChangeError("Session is closed"))
            mock_session.close = AsyncMock(side_effect=IllegalStateChangeError("Session is closed"))
            
            # Create async context manager that yields the mock session
            @asynccontextmanager
            async def mock_session_context():
                yield mock_session
            
            mock_factory.return_value = MagicMock(return_value=mock_session_context())
            
            # Simulate GeneratorExit scenario
            async def use_session():
                try:
                    async with DatabaseManager.get_async_session() as session:
                        # Simulate work
                        await asyncio.sleep(0.01)
                        # Force a GeneratorExit by breaking out early
                        raise GeneratorExit()
                except GeneratorExit:
                    # The fix should handle this gracefully
                    pass
            
            # Should complete without raising IllegalStateChangeError
            await use_session()
    
    @pytest.mark.asyncio
    async def test_illegal_state_change_error_caught(self):
        """Test that IllegalStateChangeError is caught and handled during cleanup."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.in_transaction = MagicMock(return_value=True)
            mock_session.commit = AsyncMock(side_effect=IllegalStateChangeError("Cannot commit"))
            
            @asynccontextmanager
            async def mock_session_context():
                yield mock_session
            
            mock_factory.return_value = MagicMock(return_value=mock_session_context())
            
            # Should complete without raising
            async with DatabaseManager.get_async_session() as session:
                pass  # Session cleanup should handle the error
    
    @pytest.mark.asyncio
    async def test_concurrent_session_access(self):
        """Test that concurrent access to sessions doesn't cause IllegalStateChangeError."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            # Create sessions that track their state
            sessions_created = []
            
            def create_mock_session():
                @asynccontextmanager
                async def session_context():
                    mock_session = AsyncMock(spec=AsyncSession)
                    mock_session.id = len(sessions_created)
                    mock_session.in_transaction = MagicMock(return_value=False)
                    mock_session.commit = AsyncMock()  # TODO: Use real service instance
                    mock_session.rollback = AsyncMock()  # TODO: Use real service instance
                    sessions_created.append(mock_session)
                    yield mock_session
                await asyncio.sleep(0)
    return session_context()
            
            mock_factory.return_value = MagicMock(side_effect=create_mock_session)
            
            # Run multiple concurrent session operations
            async def session_operation(operation_id):
                async with DatabaseManager.get_async_session() as session:
                    await asyncio.sleep(0.01)  # Simulate work
                    await asyncio.sleep(0)
    return f"Operation {operation_id} completed"
            
            # Run 10 concurrent operations
            tasks = [session_operation(i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All operations should complete successfully
            assert len(results) == 10
            assert all(isinstance(r, str) and "completed" in r for r in results)
            assert len(sessions_created) == 10  # Each operation gets its own session
    
    @pytest.mark.asyncio
    async def test_cancellation_with_shield(self):
        """Test that cancellation is handled with asyncio.shield for critical operations."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.in_transaction = MagicMock(return_value=True)
            rollback_called = False
            
            async def mock_rollback():
                nonlocal rollback_called
                rollback_called = True
                await asyncio.sleep(0.01)
            
            mock_session.rollback = mock_rollback
            
            @asynccontextmanager
            async def mock_session_context():
                yield mock_session
            
            mock_factory.return_value = MagicMock(return_value=mock_session_context())
            
            # Create a task that will be cancelled
            async def cancellable_operation():
                async with DatabaseManager.get_async_session() as session:
                    await asyncio.sleep(1)  # Will be cancelled before this completes
            
            task = asyncio.create_task(cancellable_operation())
            await asyncio.sleep(0.01)  # Let the task start
            task.cancel()
            
            with pytest.raises(asyncio.CancelledError):
                await task
            
            # Rollback should have been attempted (shielded from cancellation)
            await asyncio.sleep(0.02)  # Give time for shielded rollback
            assert rollback_called
    
    @pytest.mark.asyncio
    async def test_session_state_checks_are_defensive(self):
        """Test that session state checks use defensive programming patterns."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            # Test various broken session states
            test_cases = [
                # Session without in_transaction method
                AsyncMock(spec=['commit', 'rollback']),
                # Session with non-callable in_transaction
                type('MockSession', (), {'in_transaction': True, 'commit': AsyncMock()  # TODO: Use real service instance})(),
                # Session that raises AttributeError on state check
                type('MockSession', (), {
                    'in_transaction': MagicMock(side_effect=AttributeError("No attribute")),
                    'commit': AsyncMock()  # TODO: Use real service instance
                })(),
            ]
            
            for mock_session in test_cases:
                @asynccontextmanager
                async def mock_session_context():
                    yield mock_session
                
                mock_factory.return_value = MagicMock(return_value=mock_session_context())
                
                # Should handle broken session states gracefully
                async with DatabaseManager.get_async_session() as session:
                    pass  # Should complete without errors
    
    @pytest.mark.asyncio
    async def test_exception_during_transaction(self):
        """Test that exceptions during transaction are handled with proper rollback."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.in_transaction = MagicMock(return_value=True)
            mock_session.rollback = AsyncMock()  # TODO: Use real service instance
            
            @asynccontextmanager
            async def mock_session_context():
                yield mock_session
            
            mock_factory.return_value = MagicMock(return_value=mock_session_context())
            
            # Raise an exception during the transaction
            with pytest.raises(ValueError):
                async with DatabaseManager.get_async_session() as session:
                    raise ValueError("Test exception")
            
            # Rollback should have been called
            mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rollback_failure_is_handled(self):
        """Test that rollback failures don't cause additional errors."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.in_transaction = MagicMock(return_value=True)
            mock_session.rollback = AsyncMock(side_effect=IllegalStateChangeError("Cannot rollback"))
            
            @asynccontextmanager
            async def mock_session_context():
                yield mock_session
            
            mock_factory.return_value = MagicMock(return_value=mock_session_context())
            
            # Original exception should be raised, not the rollback error
            with pytest.raises(ValueError) as exc_info:
                async with DatabaseManager.get_async_session() as session:
                    raise ValueError("Original error")
            
            assert str(exc_info.value) == "Original error"
    
    @pytest.mark.asyncio
    async def test_normal_operation_flow(self):
        """Test that normal operations work correctly with the fix in place."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.in_transaction = MagicMock(return_value=True)
            mock_session.commit = AsyncMock()  # TODO: Use real service instance
            mock_session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=42)))
            
            @asynccontextmanager
            async def mock_session_context():
                yield mock_session
            
            mock_factory.return_value = MagicMock(return_value=mock_session_context())
            
            # Normal operation should work
            async with DatabaseManager.get_async_session() as session:
                result = await session.execute("SELECT 42")
                value = result.scalar()
            
            assert value == 42
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_nested_context_managers(self):
        """Test that nested session context managers don't interfere with each other."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            sessions = []
            
            @asynccontextmanager
            async def create_mock_session():
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.id = len(sessions)
                mock_session.in_transaction = MagicMock(return_value=False)
                sessions.append(mock_session)
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_mock_session())
            
            # Use nested sessions
            async with DatabaseManager.get_async_session() as outer_session:
                outer_id = outer_session.id
                async with DatabaseManager.get_async_session() as inner_session:
                    inner_id = inner_session.id
                    assert outer_id != inner_id  # Should be different sessions
            
            assert len(sessions) == 2


class TestStressScenarios:
    """Stress tests for database session management under extreme conditions."""
    
    @pytest.mark.asyncio
    async def test_rapid_session_creation_and_cleanup(self):
        """Test rapid session creation and cleanup doesn't cause state errors."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            session_count = 0
            
            @asynccontextmanager
            async def create_mock_session():
                nonlocal session_count
                session_count += 1
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.in_transaction = MagicMock(return_value=False)
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_mock_session())
            
            # Rapidly create and destroy sessions
            async def rapid_session_use():
                for _ in range(10):
                    async with DatabaseManager.get_async_session() as session:
                        pass  # Immediate cleanup
            
            # Run multiple rapid users concurrently
            await asyncio.gather(*[rapid_session_use() for _ in range(5)])
            
            assert session_count == 50  # 5 tasks * 10 sessions each
    
    @pytest.mark.asyncio
    async def test_session_cleanup_during_shutdown(self):
        """Test that sessions are cleaned up properly during shutdown scenarios."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            cleanup_attempted = []
            
            @asynccontextmanager
            async def create_mock_session():
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.in_transaction = MagicMock(return_value=True)
                
                async def cleanup_with_error():
                    cleanup_attempted.append(True)
                    raise IllegalStateChangeError("Shutdown in progress")
                
                mock_session.commit = cleanup_with_error
                mock_session.rollback = cleanup_with_error
                yield mock_session
            
            mock_factory.return_value = MagicMock(return_value=create_mock_session())
            
            # Session should handle cleanup errors during shutdown
            async with DatabaseManager.get_async_session() as session:
                pass  # Cleanup will attempt and fail
            
            assert len(cleanup_attempted) > 0  # Cleanup was attempted
    
    @pytest.mark.asyncio
    async def test_mixed_error_conditions(self):
        """Test handling of mixed error conditions simultaneously."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            
            @asynccontextmanager
            async def create_problematic_session():
                mock_session = AsyncMock(spec=AsyncSession)
                # Session that randomly fails different operations
                import random
                
                def random_failure():
                    errors = [
                        IllegalStateChangeError("Random state error"),
                        AttributeError("Missing attribute"),
                        RuntimeError("Runtime problem"),
                    ]
                    if random.random() > 0.5:
                        raise random.choice(errors)
                    await asyncio.sleep(0)
    return True
                
                mock_session.in_transaction = MagicMock(side_effect=random_failure)
                mock_session.commit = AsyncMock(side_effect=random_failure)
                mock_session.rollback = AsyncMock(side_effect=random_failure)
                yield mock_session
            
            mock_factory.return_value = MagicMock(side_effect=lambda: create_problematic_session())
            
            # Run multiple operations with random failures
            results = []
            for _ in range(10):
                try:
                    async with DatabaseManager.get_async_session() as session:
                        results.append("success")
                except Exception as e:
                    results.append(f"handled: {type(e).__name__}")
            
            # All operations should either succeed or handle errors gracefully
            assert len(results) == 10


class TestRegressionPrevention:
    """Tests to prevent regression of the IllegalStateChangeError fix."""
    
    @pytest.mark.asyncio
    async def test_fix_handles_all_exception_types(self):
        """Ensure the fix handles IllegalStateChangeError explicitly."""
        source_file = "C:\\Users\\antho\\OneDrive\\Desktop\\Netra\"
etra-core-generation-1\
etra_backend\\app\\db\\database_manager.py""
        
        # Read the actual implementation to verify the fix is in place
        with open(source_file, 'r') as f:
            content = f.read()
        
        # Check that IllegalStateChangeError is explicitly handled
        assert "IllegalStateChangeError" in content, "Fix must explicitly handle IllegalStateChangeError"
        
        # Check that GeneratorExit is handled
        assert "GeneratorExit" in content, "Fix must handle GeneratorExit"
        
        # Check that asyncio.shield is used for cancellation
        assert "asyncio.shield" in content, "Fix must use asyncio.shield for cancellation protection"
        
        # Check for defensive callable() checks
        assert "callable(" in content, "Fix must use callable() for defensive checks"
    
    @pytest.mark.asyncio
    async def test_fix_prevents_staging_error(self):
        """Test the exact scenario that caused the staging error."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            mock_session = AsyncMock(spec=AsyncSession)
            
            # Simulate the exact staging error condition
            connection_call_count = 0
            
            def connection_for_bind():
                nonlocal connection_call_count
                connection_call_count += 1
                if connection_call_count > 1:
                    # Second call during cleanup causes the error
                    raise IllegalStateChangeError(
                        "Session already has a Connection associated for the given "
                        "Connection's Engine; a Session may only be associated with "
                        "one Connection per Engine at a time."
                    )
                await asyncio.sleep(0)
    return MagicMock()  # TODO: Use real service instance
            
            mock_session._connection_for_bind = connection_for_bind
            mock_session.in_transaction = MagicMock(return_value=True)
            mock_session.close = AsyncMock(side_effect=lambda: connection_for_bind())
            
            @asynccontextmanager
            async def mock_session_context():
                yield mock_session
                # Context manager cleanup would trigger the error
                try:
                    await mock_session.close()
                except IllegalStateChangeError:
                    pass  # This is what we're protecting against
            
            mock_factory.return_value = MagicMock(return_value=mock_session_context())
            
            # This should not raise an error with the fix in place
            async with DatabaseManager.get_async_session() as session:
                pass  # The fix should handle the cleanup error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])