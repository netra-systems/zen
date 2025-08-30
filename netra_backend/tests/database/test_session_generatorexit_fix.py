"""Test database session GeneratorExit handling fix.

This test verifies that the critical session lifecycle fix properly handles
GeneratorExit exceptions without causing IllegalStateChangeError.

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Prevent production outages from session state conflicts
- Value Impact: Ensures reliable database operations under high concurrency
- Strategic Impact: Critical for system reliability and data consistency
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

# Import the function we're testing
from netra_backend.app.database import get_db


@pytest.mark.asyncio
async def test_session_generatorexit_handling():
    """Test that GeneratorExit is handled gracefully without state conflicts."""
    
    # Mock session with proper async context manager behavior
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.in_transaction = Mock(return_value=True)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    
    # Mock session factory
    @asynccontextmanager
    async def mock_session_factory():
        """Mock session factory that yields our mock session."""
        yield mock_session
    
    # Patch DatabaseManager to return our mock factory
    with patch('netra_backend.app.database.DatabaseManager.get_application_session') as mock_get_app_session:
        mock_get_app_session.return_value = mock_session_factory
        
        # Create a generator and terminate it early to trigger GeneratorExit
        gen = get_db()
        session = await gen.__anext__()
        
        # Verify we got the mock session
        assert session == mock_session
        
        # Close the generator early (simulates early termination)
        await gen.aclose()
        
        # Verify no commit was attempted (GeneratorExit path)
        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_session_cancellation_handling():
    """Test that asyncio.CancelledError triggers proper rollback."""
    
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.in_transaction = Mock(return_value=True)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    
    @asynccontextmanager
    async def mock_session_factory():
        yield mock_session
    
    with patch('netra_backend.app.database.DatabaseManager.get_application_session') as mock_get_app_session:
        mock_get_app_session.return_value = mock_session_factory
        
        async def use_session():
            """Function that uses session and gets cancelled."""
            async for session in get_db():
                # Simulate work being cancelled
                raise asyncio.CancelledError()
        
        # Run and expect CancelledError
        with pytest.raises(asyncio.CancelledError):
            await use_session()
        
        # Verify rollback was attempted with shield
        mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_session_normal_exception_handling():
    """Test that normal exceptions trigger rollback."""
    
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.in_transaction = Mock(return_value=True)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    
    @asynccontextmanager
    async def mock_session_factory():
        yield mock_session
    
    with patch('netra_backend.app.database.DatabaseManager.get_application_session') as mock_get_app_session:
        mock_get_app_session.return_value = mock_session_factory
        
        async def use_session_with_error():
            """Function that raises an error during session use."""
            async for session in get_db():
                raise ValueError("Test error")
        
        # Run and expect ValueError
        with pytest.raises(ValueError, match="Test error"):
            await use_session_with_error()
        
        # Verify rollback was called
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_session_successful_commit():
    """Test that successful operations commit properly."""
    
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.in_transaction = Mock(return_value=True)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    
    @asynccontextmanager
    async def mock_session_factory():
        yield mock_session
    
    with patch('netra_backend.app.database.DatabaseManager.get_application_session') as mock_get_app_session:
        mock_get_app_session.return_value = mock_session_factory
        
        async def use_session_successfully():
            """Function that uses session successfully."""
            async for session in get_db():
                # Simulate successful work
                assert session == mock_session
                return "success"
        
        result = await use_session_successfully()
        assert result == "success"
        
        # Verify commit was called with shield
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_concurrent_session_generators():
    """Test that multiple concurrent generators don't interfere."""
    
    # Track sessions created
    sessions_created = []
    
    @asynccontextmanager
    async def mock_session_factory():
        """Create unique mock session for each call."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.id = len(sessions_created)  # Unique ID
        mock_session.in_transaction = Mock(return_value=True)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        sessions_created.append(mock_session)
        yield mock_session
    
    with patch('netra_backend.app.database.DatabaseManager.get_application_session') as mock_get_app_session:
        mock_get_app_session.return_value = mock_session_factory
        
        async def use_session(delay: float, should_fail: bool = False):
            """Use session with configurable delay and failure."""
            async for session in get_db():
                await asyncio.sleep(delay)
                if should_fail:
                    raise ValueError(f"Session {session.id} failed")
                return f"Session {session.id} succeeded"
        
        # Run multiple concurrent sessions
        results = await asyncio.gather(
            use_session(0.01),
            use_session(0.02),
            use_session(0.01, should_fail=True),
            return_exceptions=True
        )
        
        # Verify results
        assert results[0] == "Session 0 succeeded"
        assert results[1] == "Session 1 succeeded"
        assert isinstance(results[2], ValueError)
        
        # Verify proper cleanup for each session
        assert sessions_created[0].commit.called
        assert sessions_created[1].commit.called
        assert sessions_created[2].rollback.called


@pytest.mark.asyncio
async def test_session_no_transaction_skip_operations():
    """Test that commit/rollback are skipped when no transaction is active."""
    
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.in_transaction = Mock(return_value=False)  # No active transaction
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    
    @asynccontextmanager
    async def mock_session_factory():
        yield mock_session
    
    with patch('netra_backend.app.database.DatabaseManager.get_application_session') as mock_get_app_session:
        mock_get_app_session.return_value = mock_session_factory
        
        async def use_session():
            """Use session without active transaction."""
            async for session in get_db():
                return "done"
        
        result = await use_session()
        assert result == "done"
        
        # Verify no commit/rollback when no transaction
        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_not_called()


if __name__ == "__main__":
    # Run tests
    asyncio.run(pytest.main([__file__, "-v"]))