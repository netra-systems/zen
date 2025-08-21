"""Tests for auto_rename_thread endpoint - split from test_threads_route.py"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.routes.threads_route import auto_rename_thread
from netra_backend.tests.helpers.thread_test_helpers import (

# Add project root to path
    create_mock_thread,
    create_mock_message,
    setup_thread_repo_mock,
    setup_message_repo_mock,
    setup_llm_manager_mock,
    setup_repos_with_patches,
    setup_thread_with_special_metadata,
    setup_ws_manager_mock,
    create_thread_update_scenario,
    assert_ws_notification,
    assert_http_exception,
    clean_llm_title,
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


class TestAutoRenameThread:
    """Test cases for POST /{thread_id}/auto-rename endpoint"""
    @patch('app.routes.utils.thread_helpers.time.time')
    async def test_auto_rename_success(self, mock_time, mock_db, mock_user):
        """Test successful auto-rename with LLM"""
        create_thread_update_scenario(mock_time)
        mock_thread = create_mock_thread()
        mock_message = create_mock_message()
        thread_repo = setup_thread_repo_mock(mock_thread)
        message_repo = setup_message_repo_mock(1, [mock_message])
        llm_manager = setup_llm_manager_mock()
        mock_ws = setup_ws_manager_mock()
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository', return_value=thread_repo), \
             patch('app.routes.utils.thread_helpers.MessageRepository', return_value=message_repo), \
             patch('app.routes.utils.thread_helpers.LLMManager', return_value=llm_manager), \
             patch('app.routes.utils.thread_helpers.ws_manager', mock_ws):
            
            result = await auto_rename_thread("thread_abc123", mock_db, mock_user)
            
        assert result.title == "Generated Title"
        assert mock_thread.metadata_["title"] == "Generated Title"
        assert mock_thread.metadata_["auto_renamed"] == True
        assert mock_thread.metadata_["updated_at"] == 1234567900
        mock_db.commit.assert_called_once()
        assert_ws_notification(mock_ws, "test_user_123", "thread_abc123", "Generated Title")
    @patch('app.routes.utils.thread_helpers.time.time')
    async def test_auto_rename_llm_failure_fallback(self, mock_time, mock_db, mock_user):
        """Test auto-rename with LLM failure, using fallback"""
        create_thread_update_scenario(mock_time)
        mock_thread = create_mock_thread()
        mock_message = create_mock_message()
        thread_repo = setup_thread_repo_mock(mock_thread)
        message_repo = setup_message_repo_mock(1, [mock_message])
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository', return_value=thread_repo), \
             patch('app.routes.utils.thread_helpers.MessageRepository', return_value=message_repo), \
             patch('app.routes.utils.thread_helpers.LLMManager') as MockLLMManager, \
             patch('app.routes.utils.thread_helpers.ws_manager') as mock_ws, \
             patch('app.routes.utils.thread_helpers.logger') as mock_logger:
            
            llm_manager = MockLLMManager.return_value
            llm_manager.ask_llm = AsyncMock(side_effect=Exception("LLM error"))
            mock_ws.send_to_user = AsyncMock()
            
            result = await auto_rename_thread("thread_abc123", mock_db, mock_user)
            
        assert result.title == "Chat 1234567900"
        assert mock_thread.metadata_["title"] == "Chat 1234567900"
        mock_logger.warning.assert_called_once()
    async def test_auto_rename_no_user_message(self, mock_db, mock_user):
        """Test auto-rename when no user message exists"""
        mock_thread = create_mock_thread()
        system_message = Mock(role="system", content="System message")
        thread_repo = setup_thread_repo_mock(mock_thread)
        message_repo = setup_message_repo_mock(1, [system_message])
        patches = setup_repos_with_patches(thread_repo, message_repo)
        
        with patches[0], patches[1]:
            with pytest.raises(HTTPException) as exc_info:
                await auto_rename_thread("thread_abc123", mock_db, mock_user)
            
        assert_http_exception(exc_info, 400, "No user message found to generate title from")
    async def test_auto_rename_thread_not_found(self, mock_db, mock_user):
        """Test auto-rename for non-existent thread"""
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await auto_rename_thread("nonexistent", mock_db, mock_user)
            
            assert_http_exception(exc_info, 404, "Thread not found")
    async def test_auto_rename_access_denied(self, mock_db, mock_user):
        """Test auto-rename for thread owned by another user"""
        mock_thread = create_access_denied_thread()
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            with pytest.raises(HTTPException) as exc_info:
                await auto_rename_thread("thread_abc123", mock_db, mock_user)
            
            assert_http_exception(exc_info, 403, "Access denied")
    @patch('app.routes.utils.thread_helpers.time.time')
    async def test_auto_rename_empty_metadata(self, mock_time, mock_db, mock_user):
        """Test auto-rename when thread has no metadata"""
        create_thread_update_scenario(mock_time)
        mock_thread = setup_thread_with_special_metadata()
        mock_message = create_mock_message()
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.utils.thread_helpers.MessageRepository') as MockMessageRepo, \
             patch('app.routes.utils.thread_helpers.LLMManager') as MockLLMManager, \
             patch('app.routes.utils.thread_helpers.ws_manager') as mock_ws:
            
            thread_repo = MockThreadRepo.return_value
            def get_thread(db, thread_id):
                if hasattr(mock_thread.metadata_, 'call_count') and mock_thread.metadata_.call_count > 0:
                    mock_thread.metadata_ = None
                return mock_thread
            thread_repo.get_by_id = AsyncMock(side_effect=get_thread)
            message_repo = MockMessageRepo.return_value
            message_repo.find_by_thread = AsyncMock(return_value=[mock_message])
            message_repo.count_by_thread = AsyncMock(return_value=1)
            llm_manager = MockLLMManager.return_value
            llm_manager.ask_llm = AsyncMock(return_value="New Title")
            mock_ws.send_to_user = AsyncMock()
            
            result = await auto_rename_thread("thread_abc123", mock_db, mock_user)
            
        assert mock_thread.metadata_ != None
        assert mock_thread.metadata_["title"] == "New Title"
        assert mock_thread.metadata_["auto_renamed"] == True
        assert mock_thread.metadata_["updated_at"] == 1234567900
    async def test_auto_rename_title_cleanup(self, mock_db, mock_user):
        """Test that generated title is cleaned up properly"""
        mock_thread = create_mock_thread()
        mock_message = create_mock_message()
        raw_title = '  "Generated Title with lots of extra characters that should be truncated"  '
        
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.utils.thread_helpers.MessageRepository') as MockMessageRepo, \
             patch('app.routes.utils.thread_helpers.LLMManager') as MockLLMManager, \
             patch('app.routes.utils.thread_helpers.ws_manager') as mock_ws:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            message_repo = MockMessageRepo.return_value
            message_repo.find_by_thread = AsyncMock(return_value=[mock_message])
            message_repo.count_by_thread = AsyncMock(return_value=1)
            llm_manager = MockLLMManager.return_value
            llm_manager.ask_llm = AsyncMock(return_value=raw_title)
            mock_ws.send_to_user = AsyncMock()
            
            result = await auto_rename_thread("thread_abc123", mock_db, mock_user)
            
        expected_title = clean_llm_title(raw_title)
        assert result.title == expected_title
        assert len(result.title) == 50
    async def test_auto_rename_exception(self, mock_db, mock_user):
        """Test general exception in auto_rename_thread"""
        with patch('app.routes.utils.thread_helpers.ThreadRepository') as MockThreadRepo, \
             patch('app.logging_config.central_logger.get_logger') as mock_get_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await auto_rename_thread("thread_abc123", mock_db, mock_user)
            
            assert_http_exception(exc_info, 500, "Failed to auto-rename thread")
            mock_logger = mock_get_logger.return_value
            mock_logger.error.assert_called_once()