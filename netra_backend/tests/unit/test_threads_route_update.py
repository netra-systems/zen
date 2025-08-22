"""Tests for update_thread endpoint - split from test_threads_route.py"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

# Add project root to path
from app.routes.threads_route import ThreadUpdate, update_thread
from .thread_test_helpers import (
    assert_http_exception,
    create_access_denied_thread,
    # Add project root to path
    create_mock_thread,
    create_thread_update_scenario,
    setup_message_repo_mock,
    setup_repos_with_patches,
    setup_thread_repo_mock,
    setup_thread_with_special_metadata,
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


class TestUpdateThread:
    """Test cases for PUT /{thread_id} endpoint"""
    @patch('app.routes.utils.thread_helpers.time.time')
    async def test_update_thread_success(self, mock_time, mock_db, mock_user):
        """Test successful thread update"""
        create_thread_update_scenario(mock_time)
        mock_thread = create_mock_thread()
        thread_repo = setup_thread_repo_mock(mock_thread)
        message_repo = setup_message_repo_mock(15)
        patches = setup_repos_with_patches(thread_repo, message_repo)
        
        with patches[0], patches[1]:
            thread_update = ThreadUpdate(title="Updated Title", metadata={"new_field": "value"})
            result = await update_thread("thread_abc123", thread_update, mock_db, mock_user)
            
        assert result.title == "Updated Title"
        assert mock_thread.metadata_["title"] == "Updated Title"
        assert mock_thread.metadata_["new_field"] == "value"
        assert mock_thread.metadata_["updated_at"] == 1234567900
        mock_db.commit.assert_called_once()
    @patch('app.routes.utils.thread_helpers.time.time')
    async def test_update_thread_empty_metadata(self, mock_time, mock_db, mock_user):
        """Test updating thread with empty initial metadata"""
        create_thread_update_scenario(mock_time)
        mock_thread = setup_thread_with_special_metadata()
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.utils.thread_helpers.MessageRepository') as MockMessageRepo:
            
            thread_repo = MockThreadRepo.return_value
            def get_thread(db, thread_id):
                if hasattr(mock_thread.metadata_, 'call_count') and mock_thread.metadata_.call_count > 0:
                    mock_thread.metadata_ = None
                return mock_thread
            thread_repo.get_by_id = AsyncMock(side_effect=get_thread)
            message_repo = MockMessageRepo.return_value
            message_repo.count_by_thread = AsyncMock(return_value=0)
            thread_update = ThreadUpdate(title="New Title")
            
            result = await update_thread("thread_abc123", thread_update, mock_db, mock_user)
            
        assert mock_thread.metadata_ != None
        assert mock_thread.metadata_["title"] == "New Title"
        assert mock_thread.metadata_["updated_at"] == 1234567900
    async def test_update_thread_not_found(self, mock_db, mock_user):
        """Test updating non-existent thread"""
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=None)
            thread_update = ThreadUpdate(title="Update")
            
            with pytest.raises(HTTPException) as exc_info:
                await update_thread("nonexistent", thread_update, mock_db, mock_user)
            
            assert_http_exception(exc_info, 404, "Thread not found")
    async def test_update_thread_access_denied(self, mock_db, mock_user):
        """Test updating thread owned by another user"""
        mock_thread = create_access_denied_thread()
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            thread_update = ThreadUpdate(title="Update")
            
            with pytest.raises(HTTPException) as exc_info:
                await update_thread("thread_abc123", thread_update, mock_db, mock_user)
            
            assert_http_exception(exc_info, 403, "Access denied")
    async def test_update_thread_exception(self, mock_db, mock_user):
        """Test general exception in update_thread"""
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo, \
             patch('app.logging_config.central_logger.get_logger') as mock_get_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
            thread_update = ThreadUpdate(title="Update")
            
            with pytest.raises(HTTPException) as exc_info:
                await update_thread("thread_abc123", thread_update, mock_db, mock_user)
            
            assert_http_exception(exc_info, 500, "Failed to update thread")
            mock_logger = mock_get_logger.return_value
            mock_logger.error.assert_called_once()