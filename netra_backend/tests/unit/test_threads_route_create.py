"""Tests for create_thread endpoint - split from test_threads_route.py"""

import sys
from pathlib import Path

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from netra_backend.app.routes.threads_route import create_thread, ThreadCreate
from netra_backend.tests.helpers.thread_test_helpers import (
    assert_http_exception,
    assert_thread_creation_call,
    create_mock_thread,
    create_thread_update_scenario,
    create_uuid_scenario,
    setup_thread_repo_mock,
)

@pytest.fixture
def mock_db():
    """Mock database session"""
    # Mock: Generic component isolation for controlled unit testing
    db = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    db.commit = AsyncMock()
    return db

@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    # Mock: Generic component isolation for controlled unit testing
    user = Mock()
    user.id = "test_user_123"
    user.email = "test@example.com"
    return user

class TestCreateThread:
    """Test cases for POST / endpoint"""
    @pytest.mark.asyncio
    async def test_create_thread_success(self, mock_db, mock_user):
        """Test successful thread creation"""
        mock_thread = create_mock_thread(title="New Thread")
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.thread_helpers.handle_create_thread_request') as mock_handler:
            mock_handler.return_value = mock_thread
            thread_data = ThreadCreate(
                title="New Thread", 
                metadata={"custom": "data"}
            )
            
            result = await create_thread(thread_data=thread_data, db=mock_db, current_user=mock_user)
            
            assert result.id == "thread_abc123"
            assert result.metadata_["title"] == "New Thread"
            mock_handler.assert_called_once_with(mock_db, thread_data, "test_user_123")
    @pytest.mark.asyncio
    async def test_create_thread_no_title(self, mock_db, mock_user):
        """Test thread creation without title"""
        mock_thread = create_mock_thread()
        mock_thread.metadata_ = {"user_id": "test_user_123", "status": "active"}
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.thread_helpers.handle_create_thread_request') as mock_handler:
            mock_handler.return_value = mock_thread
            thread_data = ThreadCreate()
            
            result = await create_thread(thread_data=thread_data, db=mock_db, current_user=mock_user)
            
            assert result.metadata_["user_id"] == "test_user_123"
            mock_handler.assert_called_once_with(mock_db, thread_data, "test_user_123")
    @pytest.mark.asyncio
    async def test_create_thread_exception(self, mock_db, mock_user):
        """Test error handling in create_thread"""
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.thread_helpers.handle_create_thread_request') as mock_handler, \
             patch('netra_backend.app.logging_config.central_logger.get_logger') as mock_get_logger:
            
            mock_handler.side_effect = Exception("Database error")
            thread_data = ThreadCreate(title="Test")
            
            with pytest.raises(HTTPException) as exc_info:
                await create_thread(thread_data=thread_data, db=mock_db, current_user=mock_user)
            
            assert_http_exception(exc_info, 500, "Failed to create thread")
            mock_logger = mock_get_logger.return_value
            mock_logger.error.assert_called_once()