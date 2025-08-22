"""Tests for delete_thread endpoint - split from test_threads_route.py"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

# Add project root to path
from netra_backend.app.routes.threads_route import delete_thread
from .thread_test_helpers import (
    assert_http_exception,
    create_access_denied_thread,
    # Add project root to path
    create_mock_thread,
)


@pytest.fixture
def mock_db():
    """Mock database session"""
    return AsyncMock(commit=AsyncMock())


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = Mock()
    user.id = "test_user_123"
    user.email = "test@example.com"
    return user


class TestDeleteThread:
    """Test cases for DELETE /{thread_id} endpoint"""
    async def test_delete_thread_success(self, mock_db, mock_user):
        """Test successful thread deletion (archival)"""
        mock_thread = create_mock_thread()
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            thread_repo.archive_thread = AsyncMock(return_value=True)
            
            result = await delete_thread("thread_abc123", mock_db, mock_user)
            
        assert result == {"message": "Thread archived successfully"}
        thread_repo.archive_thread.assert_called_once_with(mock_db, "thread_abc123")
    async def test_delete_thread_archive_failure(self, mock_db, mock_user):
        """Test failure to archive thread"""
        mock_thread = create_mock_thread()
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            thread_repo.archive_thread = AsyncMock(return_value=False)
            
            with pytest.raises(HTTPException) as exc_info:
                await delete_thread("thread_abc123", mock_db, mock_user)
            
            assert_http_exception(exc_info, 500, "Failed to archive thread")
    async def test_delete_thread_not_found(self, mock_db, mock_user):
        """Test deleting non-existent thread"""
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await delete_thread("nonexistent", mock_db, mock_user)
            
            assert_http_exception(exc_info, 404, "Thread not found")
    async def test_delete_thread_access_denied(self, mock_db, mock_user):
        """Test deleting thread owned by another user"""
        mock_thread = create_access_denied_thread()
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            with pytest.raises(HTTPException) as exc_info:
                await delete_thread("thread_abc123", mock_db, mock_user)
            
            assert_http_exception(exc_info, 403, "Access denied")
    async def test_delete_thread_exception(self, mock_db, mock_user):
        """Test general exception in delete_thread"""
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo, \
             patch('app.logging_config.central_logger.get_logger') as mock_get_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await delete_thread("thread_abc123", mock_db, mock_user)
            
            assert_http_exception(exc_info, 500, "Failed to delete thread")
            mock_logger = mock_get_logger.return_value
            mock_logger.error.assert_called_once()