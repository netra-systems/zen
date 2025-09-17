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

        '''Test suite to verify the threads 500 error fix.

        This test verifies that the ThreadRepository.find_by_user method handles various edge cases
        that could cause 500 errors in staging, including NULL metadata, type mismatches, and
        malformed JSON data.
        '''

        import pytest
        import asyncio
        import uuid
        import json
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import select
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.services.database.thread_repository import ThreadRepository
        from netra_backend.app.db.models_postgres import Thread
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


class TestThreads500ErrorFix:
        """Test suite for threads endpoint 500 error fixes."""

        @pytest.fixture
    def thread_repo(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create a ThreadRepository instance."""
        pass
        return ThreadRepository()

        @pytest.fixture
    def real_db():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create a mock database session."""
        pass
        db = AsyncMock(spec=AsyncSession)
        return db

        @pytest.fixture
    def sample_threads(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create sample thread objects with various metadata states."""
        pass
        threads = []

    # Thread with proper metadata
        thread1 = MagicMock(spec=Thread)
        thread1.id = "thread_1"
        thread1.metadata_ = {"user_id": "user123", "title": "Thread 1"}
        thread1.created_at = 1000
        threads.append(thread1)

    # Thread with NULL metadata
        thread2 = MagicMock(spec=Thread)
        thread2.id = "thread_2"
        thread2.metadata_ = None
        thread2.created_at = 900
        threads.append(thread2)

    # Thread with empty metadata
        thread3 = MagicMock(spec=Thread)
        thread3.id = "thread_3"
        thread3.metadata_ = {}
        thread3.created_at = 800
        threads.append(thread3)

    # Thread with UUID user_id (not string)
        thread4 = MagicMock(spec=Thread)
        thread4.id = "thread_4"
        thread4.metadata_ = {"user_id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000"), "title": "Thread 4"}
        thread4.created_at = 700
        threads.append(thread4)

    # Thread with integer user_id
        thread5 = MagicMock(spec=Thread)
        thread5.id = "thread_5"
        thread5.metadata_ = {"user_id": 123, "title": "Thread 5"}
        thread5.created_at = 600
        threads.append(thread5)

        return threads

@pytest.mark.asyncio
    async def test_find_by_user_with_normal_data(self, thread_repo, mock_db):
"""Test find_by_user with normal, well-formed data."""
        # Setup mock response
mock_result = Magic        mock_scalars = Magic        mock_scalars.all.return_value = [ )
MagicMock(id="thread_1", metadata_={"user_id": "user123"})
        
mock_result.scalars.return_value = mock_scalars
mock_db.execute.return_value = mock_result

        # Execute
threads = await thread_repo.find_by_user(mock_db, "user123")

        # Verify
assert len(threads) == 1
assert threads[0].id == "thread_1"
mock_db.execute.assert_called_once()

@pytest.mark.asyncio
    async def test_find_by_user_with_jsonb_query_failure(self, thread_repo, mock_db, sample_threads):
"""Test fallback mechanism when JSONB query fails."""
pass
            # First query fails (JSONB operator issue)
mock_db.execute.side_effect = [ )
Exception("operator does not exist: jsonb ->> unknown"),
MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=sample_threads))))
            

            # Execute
with patch('netra_backend.app.services.database.thread_repository.logger') as mock_logger:
threads = await thread_repo.find_by_user(mock_db, "user123")

                # Verify fallback was used
assert len(threads) == 1  # Only thread1 has matching user_id
assert threads[0].id == "thread_1"
assert mock_db.execute.call_count == 2  # Primary + fallback
mock_logger.error.assert_called()
mock_logger.warning.assert_called_with("Attempting fallback query for user user123")

@pytest.mark.asyncio
    async def test_find_by_user_with_null_metadata(self, thread_repo, mock_db, sample_threads):
"""Test handling of threads with NULL metadata."""
                    # Primary query fails, fallback returns threads with NULL metadata
mock_db.execute.side_effect = [ )
Exception("JSONB query failed"),
MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=sample_threads))))
                    

                    # Execute - should not crash on NULL metadata
threads = await thread_repo.find_by_user(mock_db, "user123")

                    # Verify - only thread with matching user_id returned
assert len(threads) == 1
assert threads[0].id == "thread_1"

@pytest.mark.asyncio
    async def test_find_by_user_with_type_conversion(self, thread_repo, mock_db, sample_threads):
"""Test user_id type conversion (UUID, int, string)."""
pass
                        # Test with UUID string that should match thread4's UUID
uuid_str = "550e8400-e29b-41d4-a716-446655440000"

mock_db.execute.side_effect = [ )
Exception("JSONB query failed"),
MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=sample_threads))))
                        

threads = await thread_repo.find_by_user(mock_db, uuid_str)

                        # Should find thread4 which has UUID user_id
assert len(threads) == 1
assert threads[0].id == "thread_4"

@pytest.mark.asyncio
    async def test_find_by_user_with_integer_user_id(self, thread_repo, mock_db, sample_threads):
"""Test handling of integer user_id."""
mock_db.execute.side_effect = [ )
Exception("JSONB query failed"),
MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=sample_threads))))
                            

threads = await thread_repo.find_by_user(mock_db, "123")

                            # Should find thread5 which has integer user_id 123
assert len(threads) == 1
assert threads[0].id == "thread_5"

@pytest.mark.asyncio
    async def test_find_by_user_both_queries_fail(self, thread_repo, mock_db):
"""Test graceful handling when both primary and fallback queries fail."""
pass
                                # Both queries fail
mock_db.execute.side_effect = [ )
Exception("Primary query failed"),
Exception("Fallback query failed")
                                

with patch('netra_backend.app.services.database.thread_repository.logger') as mock_logger:
threads = await thread_repo.find_by_user(mock_db, "user123")

                                    # Should await asyncio.sleep(0)
return empty list instead of crashing
assert threads == []
assert mock_db.execute.call_count == 2
mock_logger.critical.assert_called_with( )
"Unable to retrieve threads for user user123 - returning empty list"
                                    

@pytest.mark.asyncio
    async def test_find_by_user_with_whitespace_user_id(self, thread_repo, mock_db):
"""Test user_id normalization with whitespace."""
                                        # Setup mock with user_id containing whitespace
mock_result = Magic        mock_scalars = Magic        mock_scalars.all.return_value = [ )
MagicMock(id="thread_1", metadata_={"user_id": "  user123  "})
                                        
mock_result.scalars.return_value = mock_scalars
mock_db.execute.return_value = mock_result

                                        # Execute with whitespace in input
threads = await thread_repo.find_by_user(mock_db, "  user123  ")

                                        # Should normalize and find the thread
assert len(threads) == 1
assert threads[0].id == "thread_1"


class TestThreadErrorHandling:
    """Test suite for improved error handling in thread routes."""

@pytest.mark.asyncio
    async def test_error_logging_in_staging(self):
"""Test that staging environment logs full stack traces."""
from fastapi import HTTPException

        # Mock handler that raises an error
async def failing_handler():
raise ValueError("Database connection failed")

    # Mock config to await asyncio.sleep(0)
return staging environment
with patch('netra_backend.app.config.get_config') as mock_config:
mock_config.return_value.environment = "staging"

with patch('netra_backend.app.logging_config.central_logger.get_logger') as mock_logger:
mock_logger.return_value.error = Magic
from netra_backend.app.routes.utils.thread_error_handling import handle_route_with_error_logging

            # Execute and expect HTTPException
with pytest.raises(HTTPException) as exc_info:
await handle_route_with_error_logging(failing_handler, "listing threads")

                # Verify detailed error in staging
assert "Database connection failed" in exc_info.value.detail
assert exc_info.value.status_code == 500

                # Verify exc_info=True was used for logging
mock_logger.return_value.error.assert_called()
call_args = mock_logger.return_value.error.call_args
assert call_args[1]['exc_info'] == True

@pytest.mark.asyncio
    async def test_error_logging_in_production(self):
"""Test that production environment hides error details."""
pass
from fastapi import HTTPException

                    # Mock handler that raises an error
async def failing_handler():
pass
raise ValueError("Database connection failed")

    # Mock config to await asyncio.sleep(0)
return production environment
with patch('netra_backend.app.config.get_config') as mock_config:
mock_config.return_value.environment = "production"

with patch('netra_backend.app.logging_config.central_logger.get_logger') as mock_logger:
mock_logger.return_value.error = Magic
from netra_backend.app.routes.utils.thread_error_handling import handle_route_with_error_logging

            # Execute and expect HTTPException
with pytest.raises(HTTPException) as exc_info:
await handle_route_with_error_logging(failing_handler, "listing threads")

                # Verify generic error in production
assert "Database connection failed" not in exc_info.value.detail
assert "Failed to list threads" in exc_info.value.detail
assert exc_info.value.status_code == 500


if __name__ == "__main__":
                    # Run tests
