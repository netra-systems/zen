"""Tests for delete_thread endpoint - split from test_threads_route.py"""

import sys
from pathlib import Path

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from netra_backend.app.routes.utils.thread_handlers import handle_delete_thread_request
from netra_backend.tests.helpers.thread_test_helpers import (
    assert_http_exception,
    create_access_denied_thread,
    create_mock_thread,
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

class TestDeleteThread:
    """Test cases for DELETE /{thread_id} endpoint"""
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @patch('netra_backend.app.routes.utils.thread_handlers.archive_thread_safely')
    @pytest.mark.asyncio
    async def test_delete_thread_success(self, mock_archive_safely, MockThreadRepo, mock_db, mock_user):
        """Test successful thread deletion (archival)"""
        mock_thread = create_mock_thread()
        
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
        mock_archive_safely.return_value = True
        
        result = await handle_delete_thread_request(mock_db, "thread_abc123", mock_user.id)
        
        assert result == {"message": "Thread archived successfully"}
        thread_repo.get_by_id.assert_called_once_with(mock_db, "thread_abc123")
        mock_archive_safely.assert_called_once_with(mock_db, "thread_abc123")
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @patch('netra_backend.app.routes.utils.thread_handlers.archive_thread_safely')
    @pytest.mark.asyncio
    async def test_delete_thread_archive_failure(self, mock_archive_safely, MockThreadRepo, mock_db, mock_user):
        """Test failure to archive thread"""
        mock_thread = create_mock_thread()
        
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
        mock_archive_safely.side_effect = HTTPException(status_code=500, detail="Failed to archive thread")
        
        with pytest.raises(HTTPException) as exc_info:
            await handle_delete_thread_request(mock_db, "thread_abc123", mock_user.id)
        
        assert_http_exception(exc_info, 500, "Failed to archive thread")
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @pytest.mark.asyncio
    async def test_delete_thread_not_found(self, MockThreadRepo, mock_db, mock_user):
        """Test deleting non-existent thread"""
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(HTTPException) as exc_info:
            await handle_delete_thread_request(mock_db, "nonexistent", mock_user.id)
        
        assert_http_exception(exc_info, 404, "Thread not found")
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @pytest.mark.asyncio
    async def test_delete_thread_access_denied(self, MockThreadRepo, mock_db, mock_user):
        """Test deleting thread owned by another user"""
        mock_thread = create_access_denied_thread()
        
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
        
        with pytest.raises(HTTPException) as exc_info:
            await handle_delete_thread_request(mock_db, "thread_abc123", mock_user.id)
        
        assert_http_exception(exc_info, 403, "Access denied")
    @patch('netra_backend.app.routes.utils.thread_validators.ThreadRepository')
    @patch('netra_backend.app.logging_config.central_logger.get_logger')
    @pytest.mark.asyncio
    async def test_delete_thread_exception(self, mock_get_logger, MockThreadRepo, mock_db, mock_user):
        """Test general exception in delete_thread"""
        # Setup mocks
        thread_repo = MockThreadRepo.return_value
        thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(Exception) as exc_info:
            await handle_delete_thread_request(mock_db, "thread_abc123", mock_user.id)
        
        assert str(exc_info.value) == "Database error"