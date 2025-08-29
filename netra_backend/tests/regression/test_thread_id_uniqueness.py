"""Regression Test Suite for Thread ID Uniqueness

This test suite ensures that thread IDs are unique and prevent
the redirect loop issue that occurred in development mode.
"""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import Thread
from netra_backend.app.services.database.thread_repository import ThreadRepository


class TestThreadIdUniqueness:
    """Test suite to prevent regression on thread ID generation issues"""
    
    @pytest.fixture
    def thread_repo(self):
        """Create a ThreadRepository instance"""
        return ThreadRepository()
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_multiple_threads_get_unique_ids(self, thread_repo, mock_db):
        """Test that multiple calls to get_or_create_for_user create unique thread IDs
        
        This test should FAIL with the old implementation where thread_id = f"thread_{user_id}"
        and PASS with the new implementation using UUIDs
        """
        user_id = "dev-temp-bace0170"
        
        # Mock get_active_thread to always return None (no existing thread)
        thread_repo.get_active_thread = AsyncMock(return_value=None)
        
        # Track created thread IDs
        created_thread_ids = []
        
        async def mock_create(db, **kwargs):
            thread_id = kwargs.get('id')
            created_thread_ids.append(thread_id)
            thread = Thread(
                id=thread_id,
                object=kwargs.get('object'),
                created_at=kwargs.get('created_at'),
                metadata_=kwargs.get('metadata_')
            )
            return thread
        
        thread_repo.create = AsyncMock(side_effect=mock_create)
        
        # Create multiple threads for the same user
        thread1 = await thread_repo.get_or_create_for_user(mock_db, user_id)
        thread2 = await thread_repo.get_or_create_for_user(mock_db, user_id)
        thread3 = await thread_repo.get_or_create_for_user(mock_db, user_id)
        
        # Assert that all thread IDs are unique
        assert len(created_thread_ids) == 3, "Should have created 3 threads"
        assert len(set(created_thread_ids)) == 3, f"Thread IDs should be unique, but got: {created_thread_ids}"
        
        # Assert that thread IDs are not predictable (not based on user_id)
        for thread_id in created_thread_ids:
            assert thread_id != f"thread_{user_id}", f"Thread ID should not be predictable: {thread_id}"
    
    @pytest.mark.asyncio
    async def test_thread_id_not_tied_to_user_id(self, thread_repo, mock_db):
        """Test that thread IDs are not directly tied to user IDs
        
        This test should FAIL with the old implementation and PASS with the new one
        """
        user_id = "test-user-123"
        
        # Mock get_active_thread to return None
        thread_repo.get_active_thread = AsyncMock(return_value=None)
        
        created_thread_id = None
        
        async def mock_create(db, **kwargs):
            nonlocal created_thread_id
            created_thread_id = kwargs.get('id')
            return Thread(
                id=created_thread_id,
                object=kwargs.get('object'),
                created_at=kwargs.get('created_at'),
                metadata_=kwargs.get('metadata_')
            )
        
        thread_repo.create = AsyncMock(side_effect=mock_create)
        
        # Create a thread
        thread = await thread_repo.get_or_create_for_user(mock_db, user_id)
        
        # Assert that the thread ID is NOT the predictable pattern
        assert created_thread_id is not None
        assert created_thread_id != f"thread_{user_id}", \
            f"Thread ID should not be predictable pattern 'thread_{{user_id}}', got: {created_thread_id}"
        
        # Assert that thread ID contains some randomness (e.g., UUID pattern)
        # UUID hex contains only lowercase letters and numbers
        assert any(c in '0123456789abcdef' for c in created_thread_id.replace('thread_', '')), \
            f"Thread ID should contain UUID-like characters, got: {created_thread_id}"
    
    @pytest.mark.asyncio
    async def test_existing_thread_is_reused(self, thread_repo, mock_db):
        """Test that existing threads are properly reused when they exist
        
        This ensures we don't create unnecessary threads
        """
        user_id = "test-user-456"
        existing_thread_id = f"thread_{uuid.uuid4().hex[:16]}"
        
        existing_thread = Thread(
            id=existing_thread_id,
            object="thread",
            created_at=int(time.time()),
            metadata_={"user_id": user_id}
        )
        
        # Mock get_active_thread to return existing thread
        thread_repo.get_active_thread = AsyncMock(return_value=existing_thread)
        thread_repo.create = AsyncMock()
        
        # Get existing thread
        thread = await thread_repo.get_or_create_for_user(mock_db, user_id)
        
        # Assert existing thread is returned and create was not called
        assert thread.id == existing_thread_id
        thread_repo.create.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_concurrent_thread_creation_produces_unique_ids(self, thread_repo, mock_db):
        """Test that concurrent thread creation produces unique IDs
        
        This simulates multiple concurrent requests creating threads
        """
        user_id = "concurrent-user"
        
        # Always return None to force creation
        thread_repo.get_active_thread = AsyncMock(return_value=None)
        
        created_threads = []
        
        async def mock_create(db, **kwargs):
            thread = Thread(
                id=kwargs.get('id'),
                object=kwargs.get('object'),
                created_at=kwargs.get('created_at'),
                metadata_=kwargs.get('metadata_')
            )
            created_threads.append(thread)
            return thread
        
        thread_repo.create = AsyncMock(side_effect=mock_create)
        
        # Simulate concurrent thread creation
        import asyncio
        tasks = [
            thread_repo.get_or_create_for_user(mock_db, user_id)
            for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Extract thread IDs
        thread_ids = [t.id for t in created_threads]
        
        # Assert all IDs are unique
        assert len(thread_ids) == 5, "Should have created 5 threads"
        assert len(set(thread_ids)) == 5, f"All thread IDs should be unique, got: {thread_ids}"
        
        # Assert none use the predictable pattern
        for thread_id in thread_ids:
            assert thread_id != f"thread_{user_id}", \
                f"Thread ID should not use predictable pattern: {thread_id}"
    
    @pytest.mark.asyncio
    async def test_thread_id_format_is_valid(self, thread_repo, mock_db):
        """Test that generated thread IDs follow a valid format"""
        user_id = "format-test-user"
        
        thread_repo.get_active_thread = AsyncMock(return_value=None)
        
        created_thread_id = None
        
        async def mock_create(db, **kwargs):
            nonlocal created_thread_id
            created_thread_id = kwargs.get('id')
            return Thread(
                id=created_thread_id,
                object=kwargs.get('object'),
                created_at=kwargs.get('created_at'),
                metadata_=kwargs.get('metadata_')
            )
        
        thread_repo.create = AsyncMock(side_effect=mock_create)
        
        # Create a thread
        await thread_repo.get_or_create_for_user(mock_db, user_id)
        
        # Assert thread ID format
        assert created_thread_id is not None
        assert created_thread_id.startswith("thread_"), \
            f"Thread ID should start with 'thread_' prefix, got: {created_thread_id}"
        assert len(created_thread_id) > len("thread_"), \
            f"Thread ID should have content after prefix, got: {created_thread_id}"
        
        # Extract the ID part after 'thread_'
        id_part = created_thread_id[7:]  # Remove 'thread_' prefix
        assert len(id_part) >= 8, \
            f"Thread ID suffix should be at least 8 characters for uniqueness, got: {id_part}"