"""Tests for list_threads endpoint - split from test_threads_route.py"""

import sys
from pathlib import Path

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from netra_backend.app.routes.threads_route import list_threads
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
    return AsyncMock(commit=AsyncMock())

@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = Mock()
    user.id = "test_user_123"
    user.email = "test@example.com"
    return user

class TestListThreads:
    """Test cases for GET / endpoint"""
    @pytest.mark.asyncio
    async def test_list_threads_success(self, mock_db, mock_user):
        """Test successful thread listing with pagination"""
        mock_thread = create_mock_thread()
        thread_repo = setup_thread_repo_mock(mock_thread)
        message_repo = setup_message_repo_mock(5)
        patches = setup_repos_with_patches(thread_repo, message_repo)
        
        with patches[0], patches[1]:
            result = await list_threads(db=mock_db, current_user=mock_user, limit=20, offset=0)
            
        assert len(result) == 1
        assert_thread_response(result[0], "thread_abc123", 5)
        assert_repo_calls(thread_repo, message_repo, mock_db, "test_user_123", "thread_abc123")
    @pytest.mark.asyncio
    async def test_list_threads_with_pagination(self, mock_db, mock_user):
        """Test thread listing with offset and limit"""
        threads = create_multiple_threads(30)
        thread_repo = setup_thread_repo_mock(find_result=threads)
        message_repo = setup_message_repo_mock(0)
        patches = setup_repos_with_patches(thread_repo, message_repo)
        
        with patches[0], patches[1]:
            result = await list_threads(db=mock_db, current_user=mock_user, limit=5, offset=10)
            
        assert len(result) == 5
        assert result[0].id == "thread_10"
        assert result[4].id == "thread_14"
    @pytest.mark.asyncio
    async def test_list_threads_empty_metadata(self, mock_db, mock_user):
        """Test thread listing when metadata == None"""
        thread = create_empty_metadata_thread()
        thread_repo = setup_thread_repo_mock(find_result=[thread])
        message_repo = setup_message_repo_mock(0)
        patches = setup_repos_with_patches(thread_repo, message_repo)
        
        with patches[0], patches[1]:
            result = await list_threads(db=mock_db, current_user=mock_user, limit=20, offset=0)
            
        assert len(result) == 1
        assert result[0].title == None
        assert result[0].updated_at == None
    @pytest.mark.asyncio
    async def test_list_threads_exception(self, mock_db, mock_user):
        """Test error handling in list_threads"""
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo, \
             patch('app.logging_config.central_logger.get_logger') as mock_get_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.find_by_user = AsyncMock(side_effect=Exception("Database error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await list_threads(db=mock_db, current_user=mock_user)
            
            assert_http_exception(exc_info, 500, "Failed to list threads")
            mock_logger = mock_get_logger.return_value
            mock_logger.error.assert_called_once()