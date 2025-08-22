"""Tests for get_thread endpoint - split from test_threads_route.py"""

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
from netra_backend.app.routes.threads_route import get_thread
from .thread_test_helpers import (
    assert_http_exception,
    create_access_denied_thread,
    # Add project root to path
    create_mock_thread,
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


class TestGetThread:
    """Test cases for GET /{thread_id} endpoint"""
    async def test_get_thread_success(self, mock_db, mock_user):
        """Test successful thread retrieval"""
        mock_thread = create_mock_thread()
        thread_repo = setup_thread_repo_mock(mock_thread)
        message_repo = setup_message_repo_mock(10)
        patches = setup_repos_with_patches(thread_repo, message_repo)
        
        with patches[0], patches[1]:
            result = await get_thread(thread_id="thread_abc123", db=mock_db, current_user=mock_user)
            
        assert result.id == "thread_abc123"
        assert result.message_count == 10
        thread_repo.get_by_id.assert_called_once_with(mock_db, "thread_abc123")
    async def test_get_thread_not_found(self, mock_db, mock_user):
        """Test thread not found"""
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_thread(thread_id="nonexistent", db=mock_db, current_user=mock_user)
            
            assert_http_exception(exc_info, 404, "Thread not found")
    async def test_get_thread_access_denied(self, mock_db, mock_user):
        """Test access denied for thread owned by another user"""
        mock_thread = create_access_denied_thread()
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_thread(thread_id="thread_abc123", db=mock_db, current_user=mock_user)
            
            assert_http_exception(exc_info, 403, "Access denied")
    async def test_get_thread_general_exception(self, mock_db, mock_user):
        """Test general exception handling"""
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo, \
             patch('app.logging_config.central_logger.get_logger') as mock_get_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await get_thread(thread_id="thread_abc123", db=mock_db, current_user=mock_user)
            
            assert_http_exception(exc_info, 500, "Failed to get thread")
            mock_logger = mock_get_logger.return_value
            mock_logger.error.assert_called_once()