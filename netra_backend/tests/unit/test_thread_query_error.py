"""Unit test for thread query error with asyncpg parameter type issue.

This test demonstrates the DB_QUERY_FAILED error when fetching a non-existent thread.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import ProgrammingError

from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.services.database.repository_errors import RepositoryErrorHandler
from netra_backend.app.core.exceptions_database import DatabaseError


class TestThreadQueryError:
    """Test thread query failures with asyncpg parameter type issues."""
    
    @pytest.mark.asyncio
    async def test_thread_fetch_with_varchar_cast_error(self):
        """Test that fetching a thread with asyncpg parameter error raises DB_QUERY_FAILED."""
        # Arrange
        repository = ThreadRepository()
        mock_session = AsyncMock()
        
        # Simulate the exact asyncpg error we're seeing in production
        error_msg = "could not determine data type of parameter $1"
        mock_error = ProgrammingError(
            statement="SELECT threads.id, threads.object... WHERE threads.id = $1::VARCHAR",
            params=('thread_dev-temp-e946eb46',),
            orig=Exception(error_msg)
        )
        
        # Configure mock to raise the error
        mock_session.execute.side_effect = mock_error
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_id(mock_session, "thread_dev-temp-e946eb46")
        
        # Verify the error details
        assert exc_info.value.code.value == "DB_QUERY_FAILED"
        assert "thread_dev-temp-e946eb46" in str(exc_info.value.context)
    
    @pytest.mark.asyncio
    async def test_thread_repository_handles_missing_thread_gracefully(self):
        """Test that thread repository returns None for non-existent threads without errors."""
        # Arrange
        repository = ThreadRepository()
        mock_session = AsyncMock()
        
        # Configure mock to return None (thread doesn't exist)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.get_by_id(mock_session, "thread_dev-temp-nonexistent")
        
        # Assert
        assert result is None
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_development_mode_thread_id_format(self):
        """Test that development mode thread IDs are handled correctly."""
        # Arrange
        repository = ThreadRepository()
        mock_session = AsyncMock()
        
        # Test various development mode thread ID formats
        dev_thread_ids = [
            "thread_development-user",
            "thread_dev-temp-e946eb46",
            "thread_dev_12345",
            "thread_localhost_test"
        ]
        
        for thread_id in dev_thread_ids:
                # Configure mock to simulate parameter type error
            mock_session.execute.side_effect = ProgrammingError(
                statement=f"SELECT ... WHERE threads.id = $1::VARCHAR",
                params=(thread_id,),
                orig=Exception("could not determine data type of parameter $1")
            )
            
            # Act & Assert
            with pytest.raises(DatabaseError) as exc_info:
                await repository.get_by_id(mock_session, thread_id)
            
            # Verify error is consistently raised for all dev thread formats
            assert exc_info.value.code.value == "DB_QUERY_FAILED"