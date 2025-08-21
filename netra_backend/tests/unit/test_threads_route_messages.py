"""Tests for get_thread_messages endpoint - split from test_threads_route.py"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException
from netra_backend.app.routes.threads_route import get_thread_messages
from netra_backend.tests.helpers.thread_test_helpers import (
    create_mock_thread,
    create_mock_message,
    setup_thread_repo_mock,
    setup_message_repo_mock,
    setup_repos_with_patches,
    assert_thread_messages_response,
    assert_http_exception,
    create_access_denied_thread
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


class TestGetThreadMessages:
    """Test cases for GET /{thread_id}/messages endpoint"""
    async def test_get_thread_messages_success(self, mock_db, mock_user):
        """Test successful message retrieval"""
        mock_thread = create_mock_thread()
        mock_message = create_mock_message()
        thread_repo = setup_thread_repo_mock(mock_thread)
        message_repo = setup_message_repo_mock(1, [mock_message])
        patches = setup_repos_with_patches(thread_repo, message_repo)
        
        with patches[0], patches[1]:
            result = await get_thread_messages("thread_abc123", mock_db, mock_user, 50, 0)
            
        assert_thread_messages_response(result, "thread_abc123", 1, 50, 0)
        assert result["messages"][0]["id"] == "msg_123"
        message_repo.find_by_thread.assert_called_once_with(mock_db, "thread_abc123", limit=50, offset=0)
    async def test_get_thread_messages_not_found(self, mock_db, mock_user):
        """Test getting messages for non-existent thread"""
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_thread_messages("nonexistent", mock_db, mock_user)
            
            assert_http_exception(exc_info, 404, "Thread not found")
    async def test_get_thread_messages_access_denied(self, mock_db, mock_user):
        """Test getting messages for thread owned by another user"""
        mock_thread = create_access_denied_thread()
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_thread_messages("thread_abc123", mock_db, mock_user)
            
            assert_http_exception(exc_info, 403, "Access denied")
    async def test_get_thread_messages_exception(self, mock_db, mock_user):
        """Test general exception in get_thread_messages"""
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo, \
             patch('app.logging_config.central_logger.get_logger') as mock_get_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await get_thread_messages("thread_abc123", mock_db, mock_user)
            
            assert_http_exception(exc_info, 500, "Failed to get thread messages")
            mock_logger = mock_get_logger.return_value
            mock_logger.error.assert_called_once()