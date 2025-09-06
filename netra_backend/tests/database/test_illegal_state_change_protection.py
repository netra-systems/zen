from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''Comprehensive test suite to protect against IllegalStateChangeError in database sessions.

# REMOVED_SYNTAX_ERROR: This test suite ensures that the critical fix for handling IllegalStateChangeError,
# REMOVED_SYNTAX_ERROR: GeneratorExit, and concurrent session access remains stable and effective.

# REMOVED_SYNTAX_ERROR: CRITICAL: These tests protect against the staging error where SQLAlchemy raises
# REMOVED_SYNTAX_ERROR: IllegalStateChangeError during concurrent session operations or cleanup.
""

import asyncio
import pytest
import threading
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IllegalStateChangeError
from contextlib import asynccontextmanager
from test_framework.database.test_database_manager import TestDatabaseManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.db.database_manager import DatabaseManager


# REMOVED_SYNTAX_ERROR: class TestIllegalStateChangeProtection:
    # REMOVED_SYNTAX_ERROR: """Test suite for IllegalStateChangeError protection in database sessions."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_generator_exit_handling(self):
        # REMOVED_SYNTAX_ERROR: """Test that GeneratorExit is handled gracefully without attempting operations."""
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            # Create a mock session that raises IllegalStateChangeError on any operation
            # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock(spec=AsyncSession)
            # REMOVED_SYNTAX_ERROR: mock_session.in_transaction = MagicMock(side_effect=IllegalStateChangeError("Session is closed"))
            # REMOVED_SYNTAX_ERROR: mock_session.commit = AsyncMock(side_effect=IllegalStateChangeError("Session is closed"))
            # REMOVED_SYNTAX_ERROR: mock_session.rollback = AsyncMock(side_effect=IllegalStateChangeError("Session is closed"))
            # REMOVED_SYNTAX_ERROR: mock_session.close = AsyncMock(side_effect=IllegalStateChangeError("Session is closed"))

            # Create async context manager that yields the mock session
            # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def mock_session_context():
    # REMOVED_SYNTAX_ERROR: yield mock_session

    # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(return_value=mock_session_context())

    # Simulate GeneratorExit scenario
# REMOVED_SYNTAX_ERROR: async def use_session():
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as session:
            # Simulate work
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)
            # Force a GeneratorExit by breaking out early
            # REMOVED_SYNTAX_ERROR: raise GeneratorExit()
            # REMOVED_SYNTAX_ERROR: except GeneratorExit:
                # The fix should handle this gracefully
                # REMOVED_SYNTAX_ERROR: pass

                # Should complete without raising IllegalStateChangeError
                # REMOVED_SYNTAX_ERROR: await use_session()

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_illegal_state_change_error_caught(self):
                    # REMOVED_SYNTAX_ERROR: """Test that IllegalStateChangeError is caught and handled during cleanup."""
                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
                        # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock(spec=AsyncSession)
                        # REMOVED_SYNTAX_ERROR: mock_session.in_transaction = MagicMock(return_value=True)
                        # REMOVED_SYNTAX_ERROR: mock_session.commit = AsyncMock(side_effect=IllegalStateChangeError("Cannot commit"))

                        # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def mock_session_context():
    # REMOVED_SYNTAX_ERROR: yield mock_session

    # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(return_value=mock_session_context())

    # Should complete without raising
    # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as session:
        # REMOVED_SYNTAX_ERROR: pass  # Session cleanup should handle the error

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_concurrent_session_access(self):
            # REMOVED_SYNTAX_ERROR: """Test that concurrent access to sessions doesn't cause IllegalStateChangeError."""
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
                # Create sessions that track their state
                # REMOVED_SYNTAX_ERROR: sessions_created = []

# REMOVED_SYNTAX_ERROR: def create_mock_session():
    # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def session_context():
    # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock(spec=AsyncSession)
    # REMOVED_SYNTAX_ERROR: mock_session.id = len(sessions_created)
    # REMOVED_SYNTAX_ERROR: mock_session.in_transaction = MagicMock(return_value=False)
    # REMOVED_SYNTAX_ERROR: mock_session.commit = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock_session.rollback = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: sessions_created.append(mock_session)
    # REMOVED_SYNTAX_ERROR: yield mock_session
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return session_context()

    # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(side_effect=create_mock_session)

    # Run multiple concurrent session operations
# REMOVED_SYNTAX_ERROR: async def session_operation(operation_id):
    # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as session:
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)  # Simulate work
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return "formatted_string"

        # Run 10 concurrent operations
        # REMOVED_SYNTAX_ERROR: tasks = [session_operation(i) for i in range(10)]
        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should complete successfully
        # REMOVED_SYNTAX_ERROR: assert len(results) == 10
        # REMOVED_SYNTAX_ERROR: assert all(isinstance(r, str) and "completed" in r for r in results)
        # REMOVED_SYNTAX_ERROR: assert len(sessions_created) == 10  # Each operation gets its own session

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_cancellation_with_shield(self):
            # REMOVED_SYNTAX_ERROR: """Test that cancellation is handled with asyncio.shield for critical operations."""
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
                # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock(spec=AsyncSession)
                # REMOVED_SYNTAX_ERROR: mock_session.in_transaction = MagicMock(return_value=True)
                # REMOVED_SYNTAX_ERROR: rollback_called = False

# REMOVED_SYNTAX_ERROR: async def mock_rollback():
    # REMOVED_SYNTAX_ERROR: nonlocal rollback_called
    # REMOVED_SYNTAX_ERROR: rollback_called = True
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)

    # REMOVED_SYNTAX_ERROR: mock_session.rollback = mock_rollback

    # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def mock_session_context():
    # REMOVED_SYNTAX_ERROR: yield mock_session

    # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(return_value=mock_session_context())

    # Create a task that will be cancelled
# REMOVED_SYNTAX_ERROR: async def cancellable_operation():
    # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as session:
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(1)  # Will be cancelled before this completes

        # REMOVED_SYNTAX_ERROR: task = asyncio.create_task(cancellable_operation())
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)  # Let the task start
        # REMOVED_SYNTAX_ERROR: task.cancel()

        # REMOVED_SYNTAX_ERROR: with pytest.raises(asyncio.CancelledError):
            # REMOVED_SYNTAX_ERROR: await task

            # Rollback should have been attempted (shielded from cancellation)
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.02)  # Give time for shielded rollback
            # REMOVED_SYNTAX_ERROR: assert rollback_called

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_session_state_checks_are_defensive(self):
                # REMOVED_SYNTAX_ERROR: """Test that session state checks use defensive programming patterns."""
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
                    # Test various broken session states
                    # REMOVED_SYNTAX_ERROR: test_cases = [ )
                    # Session without in_transaction method
                    # REMOVED_SYNTAX_ERROR: AsyncMock(spec=['commit', 'rollback']),
                    # Session with non-callable in_transaction
                    # REMOVED_SYNTAX_ERROR: type('MockSession', (), {'in_transaction': True, 'commit': AsyncMock()  # TODO: Use real service instance})(),
                    # Session that raises AttributeError on state check
                    # REMOVED_SYNTAX_ERROR: type('MockSession', (), { ))
                    # REMOVED_SYNTAX_ERROR: 'in_transaction': MagicMock(side_effect=AttributeError("No attribute")),
                    # REMOVED_SYNTAX_ERROR: 'commit': AsyncMock()  # TODO: Use real service instance
                    # REMOVED_SYNTAX_ERROR: })(),
                    

                    # REMOVED_SYNTAX_ERROR: for mock_session in test_cases:
                        # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def mock_session_context():
    # REMOVED_SYNTAX_ERROR: yield mock_session

    # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(return_value=mock_session_context())

    # Should handle broken session states gracefully
    # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as session:
        # REMOVED_SYNTAX_ERROR: pass  # Should complete without errors

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_exception_during_transaction(self):
            # REMOVED_SYNTAX_ERROR: """Test that exceptions during transaction are handled with proper rollback."""
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
                # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock(spec=AsyncSession)
                # REMOVED_SYNTAX_ERROR: mock_session.in_transaction = MagicMock(return_value=True)
                # REMOVED_SYNTAX_ERROR: mock_session.rollback = AsyncMock()  # TODO: Use real service instance

                # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def mock_session_context():
    # REMOVED_SYNTAX_ERROR: yield mock_session

    # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(return_value=mock_session_context())

    # Raise an exception during the transaction
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError):
        # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as session:
            # REMOVED_SYNTAX_ERROR: raise ValueError("Test exception")

            # Rollback should have been called
            # REMOVED_SYNTAX_ERROR: mock_session.rollback.assert_called_once()

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_rollback_failure_is_handled(self):
                # REMOVED_SYNTAX_ERROR: """Test that rollback failures don't cause additional errors."""
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
                    # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock(spec=AsyncSession)
                    # REMOVED_SYNTAX_ERROR: mock_session.in_transaction = MagicMock(return_value=True)
                    # REMOVED_SYNTAX_ERROR: mock_session.rollback = AsyncMock(side_effect=IllegalStateChangeError("Cannot rollback"))

                    # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def mock_session_context():
    # REMOVED_SYNTAX_ERROR: yield mock_session

    # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(return_value=mock_session_context())

    # Original exception should be raised, not the rollback error
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError) as exc_info:
        # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as session:
            # REMOVED_SYNTAX_ERROR: raise ValueError("Original error")

            # REMOVED_SYNTAX_ERROR: assert str(exc_info.value) == "Original error"

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_normal_operation_flow(self):
                # REMOVED_SYNTAX_ERROR: """Test that normal operations work correctly with the fix in place."""
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
                    # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock(spec=AsyncSession)
                    # REMOVED_SYNTAX_ERROR: mock_session.in_transaction = MagicMock(return_value=True)
                    # REMOVED_SYNTAX_ERROR: mock_session.commit = AsyncMock()  # TODO: Use real service instance
                    # REMOVED_SYNTAX_ERROR: mock_session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=42)))

                    # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def mock_session_context():
    # REMOVED_SYNTAX_ERROR: yield mock_session

    # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(return_value=mock_session_context())

    # Normal operation should work
    # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as session:
        # REMOVED_SYNTAX_ERROR: result = await session.execute("SELECT 42")
        # REMOVED_SYNTAX_ERROR: value = result.scalar()

        # REMOVED_SYNTAX_ERROR: assert value == 42
        # REMOVED_SYNTAX_ERROR: mock_session.commit.assert_called_once()

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_nested_context_managers(self):
            # REMOVED_SYNTAX_ERROR: """Test that nested session context managers don't interfere with each other."""
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
                # REMOVED_SYNTAX_ERROR: sessions = []

                # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def create_mock_session():
    # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock(spec=AsyncSession)
    # REMOVED_SYNTAX_ERROR: mock_session.id = len(sessions)
    # REMOVED_SYNTAX_ERROR: mock_session.in_transaction = MagicMock(return_value=False)
    # REMOVED_SYNTAX_ERROR: sessions.append(mock_session)
    # REMOVED_SYNTAX_ERROR: yield mock_session

    # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(side_effect=lambda x: None create_mock_session())

    # Use nested sessions
    # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as outer_session:
        # REMOVED_SYNTAX_ERROR: outer_id = outer_session.id
        # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as inner_session:
            # REMOVED_SYNTAX_ERROR: inner_id = inner_session.id
            # REMOVED_SYNTAX_ERROR: assert outer_id != inner_id  # Should be different sessions

            # REMOVED_SYNTAX_ERROR: assert len(sessions) == 2


# REMOVED_SYNTAX_ERROR: class TestStressScenarios:
    # REMOVED_SYNTAX_ERROR: """Stress tests for database session management under extreme conditions."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_rapid_session_creation_and_cleanup(self):
        # REMOVED_SYNTAX_ERROR: """Test rapid session creation and cleanup doesn't cause state errors."""
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
            # REMOVED_SYNTAX_ERROR: session_count = 0

            # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def create_mock_session():
    # REMOVED_SYNTAX_ERROR: nonlocal session_count
    # REMOVED_SYNTAX_ERROR: session_count += 1
    # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock(spec=AsyncSession)
    # REMOVED_SYNTAX_ERROR: mock_session.in_transaction = MagicMock(return_value=False)
    # REMOVED_SYNTAX_ERROR: yield mock_session

    # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(side_effect=lambda x: None create_mock_session())

    # Rapidly create and destroy sessions
# REMOVED_SYNTAX_ERROR: async def rapid_session_use():
    # REMOVED_SYNTAX_ERROR: for _ in range(10):
        # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as session:
            # REMOVED_SYNTAX_ERROR: pass  # Immediate cleanup

            # Run multiple rapid users concurrently
            # REMOVED_SYNTAX_ERROR: await asyncio.gather(*[rapid_session_use() for _ in range(5)])

            # REMOVED_SYNTAX_ERROR: assert session_count == 50  # 5 tasks * 10 sessions each

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_session_cleanup_during_shutdown(self):
                # REMOVED_SYNTAX_ERROR: """Test that sessions are cleaned up properly during shutdown scenarios."""
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
                    # REMOVED_SYNTAX_ERROR: cleanup_attempted = []

                    # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def create_mock_session():
    # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock(spec=AsyncSession)
    # REMOVED_SYNTAX_ERROR: mock_session.in_transaction = MagicMock(return_value=True)

# REMOVED_SYNTAX_ERROR: async def cleanup_with_error():
    # REMOVED_SYNTAX_ERROR: cleanup_attempted.append(True)
    # REMOVED_SYNTAX_ERROR: raise IllegalStateChangeError("Shutdown in progress")

    # REMOVED_SYNTAX_ERROR: mock_session.commit = cleanup_with_error
    # REMOVED_SYNTAX_ERROR: mock_session.rollback = cleanup_with_error
    # REMOVED_SYNTAX_ERROR: yield mock_session

    # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(return_value=create_mock_session())

    # Session should handle cleanup errors during shutdown
    # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as session:
        # REMOVED_SYNTAX_ERROR: pass  # Cleanup will attempt and fail

        # REMOVED_SYNTAX_ERROR: assert len(cleanup_attempted) > 0  # Cleanup was attempted

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_mixed_error_conditions(self):
            # REMOVED_SYNTAX_ERROR: """Test handling of mixed error conditions simultaneously."""
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:

                # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def create_problematic_session():
    # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock(spec=AsyncSession)
    # Session that randomly fails different operations
    # REMOVED_SYNTAX_ERROR: import random

# REMOVED_SYNTAX_ERROR: def random_failure():
    # REMOVED_SYNTAX_ERROR: errors = [ )
    # REMOVED_SYNTAX_ERROR: IllegalStateChangeError("Random state error"),
    # REMOVED_SYNTAX_ERROR: AttributeError("Missing attribute"),
    # REMOVED_SYNTAX_ERROR: RuntimeError("Runtime problem"),
    
    # REMOVED_SYNTAX_ERROR: if random.random() > 0.5:
        # REMOVED_SYNTAX_ERROR: raise random.choice(errors)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return True

        # REMOVED_SYNTAX_ERROR: mock_session.in_transaction = MagicMock(side_effect=random_failure)
        # REMOVED_SYNTAX_ERROR: mock_session.commit = AsyncMock(side_effect=random_failure)
        # REMOVED_SYNTAX_ERROR: mock_session.rollback = AsyncMock(side_effect=random_failure)
        # REMOVED_SYNTAX_ERROR: yield mock_session

        # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(side_effect=lambda x: None create_problematic_session())

        # Run multiple operations with random failures
        # REMOVED_SYNTAX_ERROR: results = []
        # REMOVED_SYNTAX_ERROR: for _ in range(10):
            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as session:
                    # REMOVED_SYNTAX_ERROR: results.append("success")
                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: results.append("formatted_string")

                        # All operations should either succeed or handle errors gracefully
                        # REMOVED_SYNTAX_ERROR: assert len(results) == 10


# REMOVED_SYNTAX_ERROR: class TestRegressionPrevention:
    # REMOVED_SYNTAX_ERROR: """Tests to prevent regression of the IllegalStateChangeError fix."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_fix_handles_all_exception_types(self):
        # REMOVED_SYNTAX_ERROR: """Ensure the fix handles IllegalStateChangeError explicitly."""
        # REMOVED_SYNTAX_ERROR: source_file = "C:\\Users\\antho\\OneDrive\\Desktop\\Netra\"
        # REMOVED_SYNTAX_ERROR: etra-core-generation-1\
        # REMOVED_SYNTAX_ERROR: etra_backend\\app\\db\\database_manager.py""

        # Read the actual implementation to verify the fix is in place
        # REMOVED_SYNTAX_ERROR: with open(source_file, 'r') as f:
            # REMOVED_SYNTAX_ERROR: content = f.read()

            # Check that IllegalStateChangeError is explicitly handled
            # REMOVED_SYNTAX_ERROR: assert "IllegalStateChangeError" in content, "Fix must explicitly handle IllegalStateChangeError"

            # Check that GeneratorExit is handled
            # REMOVED_SYNTAX_ERROR: assert "GeneratorExit" in content, "Fix must handle GeneratorExit"

            # Check that asyncio.shield is used for cancellation
            # REMOVED_SYNTAX_ERROR: assert "asyncio.shield" in content, "Fix must use asyncio.shield for cancellation protection"

            # Check for defensive callable() checks
            # REMOVED_SYNTAX_ERROR: assert "callable(" in content, "Fix must use callable() for defensive checks" )

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_fix_prevents_staging_error(self):
                # REMOVED_SYNTAX_ERROR: """Test the exact scenario that caused the staging error."""
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.db.database_manager.DatabaseManager.get_application_session') as mock_factory:
                    # REMOVED_SYNTAX_ERROR: mock_session = AsyncMock(spec=AsyncSession)

                    # Simulate the exact staging error condition
                    # REMOVED_SYNTAX_ERROR: connection_call_count = 0

# REMOVED_SYNTAX_ERROR: def connection_for_bind():
    # REMOVED_SYNTAX_ERROR: nonlocal connection_call_count
    # REMOVED_SYNTAX_ERROR: connection_call_count += 1
    # REMOVED_SYNTAX_ERROR: if connection_call_count > 1:
        # Second call during cleanup causes the error
        # REMOVED_SYNTAX_ERROR: raise IllegalStateChangeError( )
        # REMOVED_SYNTAX_ERROR: "Session already has a Connection associated for the given "
        # REMOVED_SYNTAX_ERROR: "Connection"s Engine; a Session may only be associated with "
        # REMOVED_SYNTAX_ERROR: "one Connection per Engine at a time."
        
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return MagicMock()  # TODO: Use real service instance

        # REMOVED_SYNTAX_ERROR: mock_session._connection_for_bind = connection_for_bind
        # REMOVED_SYNTAX_ERROR: mock_session.in_transaction = MagicMock(return_value=True)
        # REMOVED_SYNTAX_ERROR: mock_session.close = AsyncMock(side_effect=lambda x: None connection_for_bind())

        # REMOVED_SYNTAX_ERROR: @asynccontextmanager
# REMOVED_SYNTAX_ERROR: async def mock_session_context():
    # REMOVED_SYNTAX_ERROR: yield mock_session
    # Context manager cleanup would trigger the error
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: await mock_session.close()
        # REMOVED_SYNTAX_ERROR: except IllegalStateChangeError:
            # REMOVED_SYNTAX_ERROR: pass  # This is what we"re protecting against

            # REMOVED_SYNTAX_ERROR: mock_factory.return_value = MagicMock(return_value=mock_session_context())

            # This should not raise an error with the fix in place
            # REMOVED_SYNTAX_ERROR: async with DatabaseManager.get_async_session() as session:
                # REMOVED_SYNTAX_ERROR: pass  # The fix should handle the cleanup error


                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                    # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])