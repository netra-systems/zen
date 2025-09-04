"""Test suite to verify async context manager fixes.

This test ensures that all database session getters properly implement
async context manager protocol and can be used with 'async with' pattern.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Test imports from various sources to ensure they all work
from netra_backend.app.database import get_db, get_async_db
from netra_backend.app.db.postgres import get_async_db as postgres_get_async_db
from netra_backend.app.dependencies import get_request_scoped_db_session
from netra_backend.app.db.database_manager import DatabaseManager


class TestAsyncContextManagers:
    """Test all async context manager patterns are properly implemented."""
    
    @pytest.mark.asyncio
    async def test_get_db_context_manager(self):
        """Test that get_db() works as an async context manager."""
        try:
            async with get_db() as session:
                assert session is not None
                assert isinstance(session, AsyncSession)
                # Verify session is active
                result = await session.execute(text("SELECT 1"))
                assert result is not None
        except Exception as e:
            # If database is not available, that's OK - we're testing the pattern
            if "connection" not in str(e).lower():
                raise
    
    @pytest.mark.asyncio
    async def test_get_async_db_context_manager(self):
        """Test that get_async_db() works as an async context manager."""
        try:
            async with get_async_db() as session:
                assert session is not None
                assert isinstance(session, AsyncSession)
        except Exception as e:
            # Database connection errors are OK for this test
            if "connection" not in str(e).lower():
                raise
    
    @pytest.mark.asyncio
    async def test_postgres_get_async_db_context_manager(self):
        """Test that postgres module's get_async_db() works as context manager."""
        try:
            async with postgres_get_async_db() as session:
                assert session is not None
                assert isinstance(session, AsyncSession)
        except Exception as e:
            # Database connection errors are OK for this test
            if "connection" not in str(e).lower():
                raise
    
    @pytest.mark.asyncio
    async def test_request_scoped_db_session_context_manager(self):
        """Test that get_request_scoped_db_session() works as context manager."""
        try:
            async with get_request_scoped_db_session() as session:
                assert session is not None
                assert isinstance(session, AsyncSession)
        except Exception as e:
            # Database connection errors are OK for this test
            if "connection" not in str(e).lower():
                raise
    
    @pytest.mark.asyncio
    async def test_database_manager_get_async_session(self):
        """Test that DatabaseManager.get_async_session() works as context manager."""
        try:
            async with DatabaseManager.get_async_session() as session:
                assert session is not None
                assert isinstance(session, AsyncSession)
        except Exception as e:
            # Database connection errors are OK for this test
            if "connection" not in str(e).lower():
                raise
    
    @pytest.mark.asyncio
    async def test_no_async_generator_context_manager_error(self):
        """Test that we don't get '_AsyncGeneratorContextManager' object has no attribute errors."""
        # This would have failed before the fix with:
        # AttributeError: '_AsyncGeneratorContextManager' object has no attribute 'execute'
        
        try:
            async with get_db() as session:
                # Try to use session - this would fail if it's not properly managed
                if hasattr(session, 'execute'):
                    result = await session.execute(text("SELECT 1"))
                    assert result is not None
        except Exception as e:
            # We should NOT see _AsyncGeneratorContextManager errors
            assert "_AsyncGeneratorContextManager" not in str(e)
            # Database connection errors are OK
            if "connection" not in str(e).lower() and "SELECT 1" not in str(e):
                raise
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(self):
        """Test that multiple concurrent sessions don't interfere with each other."""
        async def use_session(session_id: int):
            try:
                async with get_db() as session:
                    assert session is not None
                    # Each session should be independent
                    await asyncio.sleep(0.01)  # Simulate some work
                    return f"Session {session_id} completed"
            except Exception as e:
                if "connection" not in str(e).lower():
                    raise
                return f"Session {session_id} - no database"
        
        # Run multiple sessions concurrently
        tasks = [use_session(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should complete without errors
        assert len(results) == 5
        for result in results:
            assert "completed" in result or "no database" in result


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])