"""Tests for update_thread endpoint - split from test_threads_route.py"""

import sys
from pathlib import Path

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from netra_backend.app.routes.threads_route import ThreadUpdate
from netra_backend.app.routes.utils.thread_handlers import handle_update_thread_request
from netra_backend.tests.helpers.thread_test_helpers import (
    assert_http_exception,
    create_access_denied_thread,
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
    # Mock: Generic component isolation for controlled unit testing
    return AsyncMock(commit=AsyncMock())

@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    # Mock: Generic component isolation for controlled unit testing
    user = Mock()
    user.id = "test_user_123"
    user.email = "test@example.com"
    return user

class TestUpdateThread:
    """Test cases for PUT /{thread_id} endpoint"""
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @patch('netra_backend.app.routes.utils.thread_handlers.MessageRepository')
    @patch('netra_backend.app.routes.utils.thread_handlers.time.time')
    @pytest.mark.asyncio
    async def test_update_thread_success(self, mock_time, MockMessageRepo, MockThreadRepo, mock_db, mock_user):
        """Test successful thread update"""
        create_thread_update_scenario(mock_time)
        mock_thread = create_mock_thread()
        
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
        message_repo = MockMessageRepo.return_value
        message_repo.count_by_thread = AsyncMock(return_value=15)
        
        thread_update = ThreadUpdate(title="Updated Title", metadata={"new_field": "value"})
        result = await handle_update_thread_request(mock_db, "thread_abc123", thread_update, mock_user.id)
        
        assert result.title == "Updated Title"
        assert mock_thread.metadata_["title"] == "Updated Title"
        assert mock_thread.metadata_["new_field"] == "value"
        assert mock_thread.metadata_["updated_at"] == 1234567900
        mock_db.commit.assert_called_once()
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @patch('netra_backend.app.routes.utils.thread_handlers.MessageRepository')
    @patch('netra_backend.app.routes.utils.thread_handlers.time.time')
    @pytest.mark.asyncio
    async def test_update_thread_empty_metadata(self, mock_time, MockMessageRepo, MockThreadRepo, mock_db, mock_user):
        """Test updating thread with empty initial metadata"""
        create_thread_update_scenario(mock_time)
        mock_thread = setup_thread_with_special_metadata()
        
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        async def get_thread(db, thread_id):
            if hasattr(mock_thread.metadata_, 'call_count') and mock_thread.metadata_.call_count > 0:
                mock_thread.metadata_ = None
            return mock_thread
        thread_repo.get_by_id = AsyncMock(side_effect=get_thread)
        message_repo = MockMessageRepo.return_value
        message_repo.count_by_thread = AsyncMock(return_value=0)
        thread_update = ThreadUpdate(title="New Title")
        
        result = await handle_update_thread_request(mock_db, "thread_abc123", thread_update, mock_user.id)
        
        assert mock_thread.metadata_ != None
        assert mock_thread.metadata_["title"] == "New Title"
        assert mock_thread.metadata_["updated_at"] == 1234567900
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @pytest.mark.asyncio
    async def test_update_thread_not_found(self, MockThreadRepo, mock_db, mock_user):
        """Test updating non-existent thread"""
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(return_value=None)
        thread_update = ThreadUpdate(title="Update")
        
        with pytest.raises(HTTPException) as exc_info:
            await handle_update_thread_request(mock_db, "nonexistent", thread_update, mock_user.id)
        
        assert_http_exception(exc_info, 404, "Thread not found")
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @pytest.mark.asyncio
    async def test_update_thread_access_denied(self, MockThreadRepo, mock_db, mock_user):
        """Test updating thread owned by another user"""
        mock_thread = create_access_denied_thread()
        
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
        thread_update = ThreadUpdate(title="Update")
        
        with pytest.raises(HTTPException) as exc_info:
            await handle_update_thread_request(mock_db, "thread_abc123", thread_update, mock_user.id)
        
        assert_http_exception(exc_info, 403, "Access denied")
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @patch('netra_backend.app.logging_config.central_logger.get_logger')
    @pytest.mark.asyncio
    async def test_update_thread_exception(self, mock_get_logger, MockThreadRepo, mock_db, mock_user):
        """Test general exception in update_thread"""
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
        thread_update = ThreadUpdate(title="Update")
        
        with pytest.raises(Exception) as exc_info:
            await handle_update_thread_request(mock_db, "thread_abc123", thread_update, mock_user.id)
        
        assert str(exc_info.value) == "Database error"