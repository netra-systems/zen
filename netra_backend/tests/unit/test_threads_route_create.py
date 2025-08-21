"""Tests for create_thread endpoint - split from test_threads_route.py"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException
from netra_backend.app.routes.threads_route import ThreadCreate, create_thread
from netra_backend.tests.helpers.thread_test_helpers import (
    create_mock_thread,
    setup_thread_repo_mock,
    create_uuid_scenario,
    create_thread_update_scenario,
    assert_thread_creation_call,
    assert_http_exception
)


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = Mock()
    user.id = "test_user_123"
    user.email = "test@example.com"
    return user


class TestCreateThread:
    """Test cases for POST / endpoint"""
    @patch('app.routes.utils.thread_helpers.uuid.uuid4')
    @patch('app.routes.utils.thread_helpers.time.time')
    async def test_create_thread_success(self, mock_time, mock_uuid, mock_db, mock_user):
        """Test successful thread creation"""
        create_thread_update_scenario(mock_time, 1234567890)
        create_uuid_scenario(mock_uuid)
        mock_thread = create_mock_thread(title="New Thread")
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.create = AsyncMock(return_value=mock_thread)
            thread_data = ThreadCreate(title="New Thread", metadata={"custom": "data"})
            
            result = await create_thread(thread_data=thread_data, db=mock_db, current_user=mock_user)
            
            assert result.id == "thread_abc123"
            assert result.title == "New Thread"
            assert result.message_count == 0
            assert_thread_creation_call(thread_repo, mock_db, "test_user_123", "New Thread")
    async def test_create_thread_no_title(self, mock_db, mock_user):
        """Test thread creation without title"""
        mock_thread = create_mock_thread()
        mock_thread.metadata_ = {"user_id": "test_user_123", "status": "active"}
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.create = AsyncMock(return_value=mock_thread)
            thread_data = ThreadCreate()
            
            result = await create_thread(thread_data=thread_data, db=mock_db, current_user=mock_user)
            
            assert result.title == None
            call_args = thread_repo.create.call_args
            assert "title" not in call_args[1]["metadata_"] or call_args[1]["metadata_"].get("title") == None
    async def test_create_thread_exception(self, mock_db, mock_user):
        """Test error handling in create_thread"""
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo, \
             patch('app.logging_config.central_logger.get_logger') as mock_get_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.create = AsyncMock(side_effect=Exception("Database error"))
            thread_data = ThreadCreate(title="Test")
            
            with pytest.raises(HTTPException) as exc_info:
                await create_thread(thread_data=thread_data, db=mock_db, current_user=mock_user)
            
            assert_http_exception(exc_info, 500, "Failed to create thread")
            mock_logger = mock_get_logger.return_value
            mock_logger.error.assert_called_once()