"""Tests for list_threads endpoint - split from test_threads_route.py"""

import sys
from pathlib import Path

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from netra_backend.app.routes.utils.thread_handlers import handle_list_threads_request
from netra_backend.tests.helpers.thread_test_helpers import (
    assert_http_exception,
    assert_repo_calls,
    assert_thread_response,
    create_empty_metadata_thread,
    create_mock_thread,
    create_multiple_threads,
    setup_message_repo_mock,
    setup_repos_with_patches,
    setup_thread_repo_mock,
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

class TestListThreads:
    """Test cases for GET / endpoint"""
    @patch('netra_backend.app.routes.utils.thread_creators.ThreadRepository')
    @patch('netra_backend.app.routes.utils.thread_builders.MessageRepository')
    @pytest.mark.asyncio
    async def test_list_threads_success(self, MockMessageRepo, MockThreadRepo, mock_db, mock_user):
        """Test successful thread listing with pagination"""
        mock_thread = create_mock_thread()
        
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.find_by_user = AsyncMock(return_value=[mock_thread])
        message_repo = MockMessageRepo.return_value
        message_repo.count_by_thread = AsyncMock(return_value=5)
        
        result = await handle_list_threads_request(mock_db, mock_user.id, 0, 20)
        
        assert len(result) == 1
        assert_thread_response(result[0], "thread_abc123", 5)
        thread_repo.find_by_user.assert_called_once_with(mock_db, mock_user.id)
        message_repo.count_by_thread.assert_called_once_with(mock_db, "thread_abc123")
    @patch('netra_backend.app.routes.utils.thread_creators.ThreadRepository')
    @patch('netra_backend.app.routes.utils.thread_builders.MessageRepository')
    @pytest.mark.asyncio
    async def test_list_threads_with_pagination(self, MockMessageRepo, MockThreadRepo, mock_db, mock_user):
        """Test thread listing with offset and limit"""
        threads = create_multiple_threads(30)
        
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.find_by_user = AsyncMock(return_value=threads)
        message_repo = MockMessageRepo.return_value
        message_repo.count_by_thread = AsyncMock(return_value=0)
        
        result = await handle_list_threads_request(mock_db, mock_user.id, 10, 5)
        
        assert len(result) == 5
        assert result[0].id == "thread_10"
        assert result[4].id == "thread_14"
    @patch('netra_backend.app.routes.utils.thread_creators.ThreadRepository')
    @patch('netra_backend.app.routes.utils.thread_builders.MessageRepository')
    @pytest.mark.asyncio
    async def test_list_threads_empty_metadata(self, MockMessageRepo, MockThreadRepo, mock_db, mock_user):
        """Test thread listing when metadata == None"""
        thread = create_empty_metadata_thread()
        
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.find_by_user = AsyncMock(return_value=[thread])
        message_repo = MockMessageRepo.return_value
        message_repo.count_by_thread = AsyncMock(return_value=0)
        
        result = await handle_list_threads_request(mock_db, mock_user.id, 0, 20)
        
        assert len(result) == 1
        assert result[0].title == None
        assert result[0].updated_at == None
    @patch('netra_backend.app.routes.utils.thread_creators.ThreadRepository')
    @patch('netra_backend.app.logging_config.central_logger.get_logger')
    @pytest.mark.asyncio
    async def test_list_threads_exception(self, mock_get_logger, MockThreadRepo, mock_db, mock_user):
        """Test error handling in list_threads"""
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.find_by_user = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(Exception) as exc_info:
            await handle_list_threads_request(mock_db, mock_user.id, 0, 20)
        
        assert str(exc_info.value) == "Database error"