"""Tests for get_thread_messages endpoint - split from test_threads_route.py"""

import sys
from pathlib import Path

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from netra_backend.app.routes.utils.thread_handlers import handle_get_messages_request
from netra_backend.tests.helpers.thread_test_helpers import (
    assert_http_exception,
    assert_thread_messages_response,
    create_access_denied_thread,
    create_mock_message,
    create_mock_thread,
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

class TestGetThreadMessages:
    """Test cases for GET /{thread_id}/messages endpoint"""
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @patch('netra_backend.app.routes.utils.thread_builders.MessageRepository')
    @pytest.mark.asyncio
    async def test_get_thread_messages_success(self, MockMessageRepo, MockThreadRepo, mock_db, mock_user):
        """Test successful message retrieval"""
        mock_thread = create_mock_thread()
        mock_message = create_mock_message()
        
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
        message_repo = MockMessageRepo.return_value
        message_repo.find_by_thread = AsyncMock(return_value=[mock_message])
        message_repo.count_by_thread = AsyncMock(return_value=1)
        
        result = await handle_get_messages_request(mock_db, "thread_abc123", mock_user.id, 50, 0)
        
        assert_thread_messages_response(result, "thread_abc123", 1, 50, 0)
        assert result["messages"][0]["id"] == "msg_123"
        message_repo.find_by_thread.assert_called_once_with(mock_db, "thread_abc123", limit=50, offset=0)
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @pytest.mark.asyncio
    async def test_get_thread_messages_not_found(self, MockThreadRepo, mock_db, mock_user):
        """Test getting messages for non-existent thread"""
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await handle_get_messages_request(mock_db, "nonexistent", mock_user.id, 50, 0)
        
        assert_http_exception(exc_info, 404, "Thread not found")
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @pytest.mark.asyncio
    async def test_get_thread_messages_access_denied(self, MockThreadRepo, mock_db, mock_user):
        """Test getting messages for thread owned by another user"""
        mock_thread = create_access_denied_thread()
        
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
        
        with pytest.raises(HTTPException) as exc_info:
            await handle_get_messages_request(mock_db, "thread_abc123", mock_user.id, 50, 0)
        
        assert_http_exception(exc_info, 403, "Access denied")
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @patch('netra_backend.app.logging_config.central_logger.get_logger')
    @pytest.mark.asyncio
    async def test_get_thread_messages_exception(self, mock_get_logger, MockThreadRepo, mock_db, mock_user):
        """Test general exception in get_thread_messages"""
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(Exception) as exc_info:
            await handle_get_messages_request(mock_db, "thread_abc123", mock_user.id, 50, 0)
        
        assert str(exc_info.value) == "Database error"