"""Comprehensive tests for threads_route.py to achieve 100% coverage"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException
from app.routes.threads_route import (
    router,
    ThreadCreate,
    ThreadUpdate,
    ThreadResponse,
    list_threads,
    create_thread,
    get_thread,
    update_thread,
    delete_thread,
    get_thread_messages,
    auto_rename_thread
)
import time
import uuid


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


@pytest.fixture
def mock_thread():
    """Mock thread object"""
    thread = Mock()
    thread.id = "thread_abc123"
    thread.object = "thread"
    thread.created_at = 1234567890
    thread.metadata_ = {
        "user_id": "test_user_123",
        "title": "Test Thread",
        "updated_at": 1234567900
    }
    return thread


@pytest.fixture
def mock_message():
    """Mock message object"""
    message = Mock()
    message.id = "msg_123"
    message.role = "user"
    message.content = "Test message content"
    message.created_at = 1234567890
    message.metadata_ = {}
    return message


class TestListThreads:
    """Test cases for GET / endpoint"""
    
    @pytest.mark.asyncio
    async def test_list_threads_success(self, mock_db, mock_user, mock_thread):
        """Test successful thread listing with pagination"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.MessageRepository') as MockMessageRepo:
            
            # Setup mocks
            thread_repo = MockThreadRepo.return_value
            thread_repo.find_by_user = AsyncMock(return_value=[mock_thread])
            
            message_repo = MockMessageRepo.return_value
            message_repo.count_by_thread = AsyncMock(return_value=5)
            
            # Call endpoint
            result = await list_threads(
                db=mock_db,
                current_user=mock_user,
                limit=20,
                offset=0
            )
            
            # Assertions
            assert len(result) == 1
            assert result[0].id == "thread_abc123"
            assert result[0].message_count == 5
            thread_repo.find_by_user.assert_called_once_with(mock_db, "test_user_123")
            message_repo.count_by_thread.assert_called_once_with(mock_db, "thread_abc123")
    
    @pytest.mark.asyncio
    async def test_list_threads_with_pagination(self, mock_db, mock_user):
        """Test thread listing with offset and limit"""
        threads = [Mock(id=f"thread_{i}", object="thread", created_at=123456789+i, metadata_={"title": f"Thread {i}"}) 
                  for i in range(30)]
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.MessageRepository') as MockMessageRepo:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.find_by_user = AsyncMock(return_value=threads)
            
            message_repo = MockMessageRepo.return_value
            message_repo.count_by_thread = AsyncMock(return_value=0)
            
            # Test with offset=10, limit=5
            result = await list_threads(
                db=mock_db,
                current_user=mock_user,
                limit=5,
                offset=10
            )
            
            assert len(result) == 5
            assert result[0].id == "thread_10"
            assert result[4].id == "thread_14"
    
    @pytest.mark.asyncio
    async def test_list_threads_empty_metadata(self, mock_db, mock_user):
        """Test thread listing when metadata is None"""
        thread = Mock(id="thread_1", object="thread", created_at=123456789, metadata_=None)
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.MessageRepository') as MockMessageRepo:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.find_by_user = AsyncMock(return_value=[thread])
            
            message_repo = MockMessageRepo.return_value
            message_repo.count_by_thread = AsyncMock(return_value=0)
            
            result = await list_threads(db=mock_db, current_user=mock_user, limit=20, offset=0)
            
            assert len(result) == 1
            assert result[0].title is None
            assert result[0].updated_at is None
    
    @pytest.mark.asyncio
    async def test_list_threads_exception(self, mock_db, mock_user):
        """Test error handling in list_threads"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.logger') as mock_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.find_by_user = AsyncMock(side_effect=Exception("Database error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await list_threads(db=mock_db, current_user=mock_user)
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to list threads"
            mock_logger.error.assert_called_once()


class TestCreateThread:
    """Test cases for POST / endpoint"""
    
    @pytest.mark.asyncio
    @patch('app.routes.threads_route.uuid.uuid4')
    @patch('app.routes.threads_route.time.time')
    async def test_create_thread_success(self, mock_time, mock_uuid, mock_db, mock_user, mock_thread):
        """Test successful thread creation"""
        mock_time.return_value = 1234567890
        mock_uuid_obj = Mock()
        mock_uuid_obj.hex = "abcdef1234567890"
        mock_uuid.return_value = mock_uuid_obj
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.create = AsyncMock(return_value=mock_thread)
            
            thread_data = ThreadCreate(title="New Thread", metadata={"custom": "data"})
            
            result = await create_thread(
                thread_data=thread_data,
                db=mock_db,
                current_user=mock_user
            )
            
            assert result.id == "thread_abc123"
            assert result.title == "Test Thread"
            assert result.message_count == 0
            
            # Verify thread creation call
            thread_repo.create.assert_called_once()
            call_args = thread_repo.create.call_args
            assert call_args[0][0] == mock_db
            assert "thread_" in call_args[1]["id"]
            assert call_args[1]["object"] == "thread"
            assert call_args[1]["metadata_"]["user_id"] == "test_user_123"
            assert call_args[1]["metadata_"]["title"] == "New Thread"
            assert call_args[1]["metadata_"]["custom"] == "data"
            assert call_args[1]["metadata_"]["status"] == "active"
            
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_thread_no_title(self, mock_db, mock_user, mock_thread):
        """Test thread creation without title"""
        mock_thread.metadata_ = {"user_id": "test_user_123", "status": "active"}
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.create = AsyncMock(return_value=mock_thread)
            
            thread_data = ThreadCreate()
            
            result = await create_thread(
                thread_data=thread_data,
                db=mock_db,
                current_user=mock_user
            )
            
            assert result.title is None
            
            # Verify title not in metadata
            call_args = thread_repo.create.call_args
            assert "title" not in call_args[1]["metadata_"] or call_args[1]["metadata_"].get("title") is None
    
    @pytest.mark.asyncio
    async def test_create_thread_exception(self, mock_db, mock_user):
        """Test error handling in create_thread"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.logger') as mock_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.create = AsyncMock(side_effect=Exception("Database error"))
            
            thread_data = ThreadCreate(title="Test")
            
            with pytest.raises(HTTPException) as exc_info:
                await create_thread(thread_data=thread_data, db=mock_db, current_user=mock_user)
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to create thread"
            mock_logger.error.assert_called_once()


class TestGetThread:
    """Test cases for GET /{thread_id} endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_thread_success(self, mock_db, mock_user, mock_thread):
        """Test successful thread retrieval"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.MessageRepository') as MockMessageRepo:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            message_repo = MockMessageRepo.return_value
            message_repo.count_by_thread = AsyncMock(return_value=10)
            
            result = await get_thread(
                thread_id="thread_abc123",
                db=mock_db,
                current_user=mock_user
            )
            
            assert result.id == "thread_abc123"
            assert result.message_count == 10
            thread_repo.get_by_id.assert_called_once_with(mock_db, "thread_abc123")
    
    @pytest.mark.asyncio
    async def test_get_thread_not_found(self, mock_db, mock_user):
        """Test thread not found"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_thread(thread_id="nonexistent", db=mock_db, current_user=mock_user)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Thread not found"
    
    @pytest.mark.asyncio
    async def test_get_thread_access_denied(self, mock_db, mock_user, mock_thread):
        """Test access denied for thread owned by another user"""
        mock_thread.metadata_["user_id"] = "another_user"
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_thread(thread_id="thread_abc123", db=mock_db, current_user=mock_user)
            
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail == "Access denied"
    
    @pytest.mark.asyncio
    async def test_get_thread_general_exception(self, mock_db, mock_user):
        """Test general exception handling"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.logger') as mock_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await get_thread(thread_id="thread_abc123", db=mock_db, current_user=mock_user)
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to get thread"
            mock_logger.error.assert_called_once()


class TestUpdateThread:
    """Test cases for PUT /{thread_id} endpoint"""
    
    @pytest.mark.asyncio
    @patch('app.routes.threads_route.time.time')
    async def test_update_thread_success(self, mock_time, mock_db, mock_user, mock_thread):
        """Test successful thread update"""
        mock_time.return_value = 1234567900
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.MessageRepository') as MockMessageRepo:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            message_repo = MockMessageRepo.return_value
            message_repo.count_by_thread = AsyncMock(return_value=15)
            
            thread_update = ThreadUpdate(title="Updated Title", metadata={"new_field": "value"})
            
            result = await update_thread(
                thread_id="thread_abc123",
                thread_update=thread_update,
                db=mock_db,
                current_user=mock_user
            )
            
            assert result.title == "Updated Title"
            assert mock_thread.metadata_["title"] == "Updated Title"
            assert mock_thread.metadata_["new_field"] == "value"
            assert mock_thread.metadata_["updated_at"] == 1234567900
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_thread_empty_metadata(self, mock_db, mock_user):
        """Test updating thread with empty initial metadata"""
        # Create a mock thread with None metadata and correct user_id
        mock_thread = Mock()
        mock_thread.id = "thread_abc123"
        mock_thread.object = "thread"
        mock_thread.created_at = 1234567890
        mock_thread.metadata_ = {"user_id": "test_user_123"}  # Has user_id but will be updated to None
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.MessageRepository') as MockMessageRepo:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            # After getting the thread, simulate it having None metadata to test line 186
            def side_effect(db, thread_id):
                mock_thread.metadata_ = {"user_id": "test_user_123"}  # For access check
                return mock_thread
            
            thread_repo.get_by_id = AsyncMock(side_effect=side_effect)
            
            message_repo = MockMessageRepo.return_value
            message_repo.count_by_thread = AsyncMock(return_value=0)
            
            thread_update = ThreadUpdate(title="New Title")
            
            # Mock the metadata_ being None after access check but before update
            original_get = mock_thread.metadata_.get
            call_count = [0]
            def mock_get(key, default=None):
                call_count[0] += 1
                if call_count[0] == 1 and key == "user_id":  # First call for access check
                    return "test_user_123"
                # After access check, set metadata to None to trigger line 186
                if call_count[0] == 2:
                    mock_thread.metadata_ = None
                return default
            
            mock_thread.metadata_.get = mock_get
            
            result = await update_thread(
                thread_id="thread_abc123",
                thread_update=thread_update,
                db=mock_db,
                current_user=mock_user
            )
            
            assert mock_thread.metadata_ is not None
            assert mock_thread.metadata_["title"] == "New Title"
    
    @pytest.mark.asyncio
    async def test_update_thread_not_found(self, mock_db, mock_user):
        """Test updating non-existent thread"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=None)
            
            thread_update = ThreadUpdate(title="Update")
            
            with pytest.raises(HTTPException) as exc_info:
                await update_thread(
                    thread_id="nonexistent",
                    thread_update=thread_update,
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Thread not found"
    
    @pytest.mark.asyncio
    async def test_update_thread_access_denied(self, mock_db, mock_user, mock_thread):
        """Test updating thread owned by another user"""
        mock_thread.metadata_["user_id"] = "another_user"
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            thread_update = ThreadUpdate(title="Update")
            
            with pytest.raises(HTTPException) as exc_info:
                await update_thread(
                    thread_id="thread_abc123",
                    thread_update=thread_update,
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail == "Access denied"
    
    @pytest.mark.asyncio
    async def test_update_thread_exception(self, mock_db, mock_user):
        """Test general exception in update_thread"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.logger') as mock_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
            
            thread_update = ThreadUpdate(title="Update")
            
            with pytest.raises(HTTPException) as exc_info:
                await update_thread(
                    thread_id="thread_abc123",
                    thread_update=thread_update,
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to update thread"
            mock_logger.error.assert_called_once()


class TestDeleteThread:
    """Test cases for DELETE /{thread_id} endpoint"""
    
    @pytest.mark.asyncio
    async def test_delete_thread_success(self, mock_db, mock_user, mock_thread):
        """Test successful thread deletion (archival)"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            thread_repo.archive_thread = AsyncMock(return_value=True)
            
            result = await delete_thread(
                thread_id="thread_abc123",
                db=mock_db,
                current_user=mock_user
            )
            
            assert result == {"message": "Thread archived successfully"}
            thread_repo.archive_thread.assert_called_once_with(mock_db, "thread_abc123")
    
    @pytest.mark.asyncio
    async def test_delete_thread_archive_failure(self, mock_db, mock_user, mock_thread):
        """Test failure to archive thread"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            thread_repo.archive_thread = AsyncMock(return_value=False)
            
            with pytest.raises(HTTPException) as exc_info:
                await delete_thread(
                    thread_id="thread_abc123",
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to archive thread"
    
    @pytest.mark.asyncio
    async def test_delete_thread_not_found(self, mock_db, mock_user):
        """Test deleting non-existent thread"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await delete_thread(
                    thread_id="nonexistent",
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Thread not found"
    
    @pytest.mark.asyncio
    async def test_delete_thread_access_denied(self, mock_db, mock_user, mock_thread):
        """Test deleting thread owned by another user"""
        mock_thread.metadata_["user_id"] = "another_user"
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            with pytest.raises(HTTPException) as exc_info:
                await delete_thread(
                    thread_id="thread_abc123",
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail == "Access denied"
    
    @pytest.mark.asyncio
    async def test_delete_thread_exception(self, mock_db, mock_user):
        """Test general exception in delete_thread"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.logger') as mock_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await delete_thread(
                    thread_id="thread_abc123",
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to delete thread"
            mock_logger.error.assert_called_once()


class TestGetThreadMessages:
    """Test cases for GET /{thread_id}/messages endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_thread_messages_success(self, mock_db, mock_user, mock_thread, mock_message):
        """Test successful message retrieval"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.MessageRepository') as MockMessageRepo:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            message_repo = MockMessageRepo.return_value
            message_repo.find_by_thread = AsyncMock(return_value=[mock_message])
            message_repo.count_by_thread = AsyncMock(return_value=1)
            
            result = await get_thread_messages(
                thread_id="thread_abc123",
                db=mock_db,
                current_user=mock_user,
                limit=50,
                offset=0
            )
            
            assert result["thread_id"] == "thread_abc123"
            assert len(result["messages"]) == 1
            assert result["messages"][0]["id"] == "msg_123"
            assert result["total"] == 1
            assert result["limit"] == 50
            assert result["offset"] == 0
            
            message_repo.find_by_thread.assert_called_once_with(
                mock_db, "thread_abc123", limit=50, offset=0
            )
    
    @pytest.mark.asyncio
    async def test_get_thread_messages_not_found(self, mock_db, mock_user):
        """Test getting messages for non-existent thread"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_thread_messages(
                    thread_id="nonexistent",
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Thread not found"
    
    @pytest.mark.asyncio
    async def test_get_thread_messages_access_denied(self, mock_db, mock_user, mock_thread):
        """Test getting messages for thread owned by another user"""
        mock_thread.metadata_["user_id"] = "another_user"
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_thread_messages(
                    thread_id="thread_abc123",
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail == "Access denied"
    
    @pytest.mark.asyncio
    async def test_get_thread_messages_exception(self, mock_db, mock_user):
        """Test general exception in get_thread_messages"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.logger') as mock_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await get_thread_messages(
                    thread_id="thread_abc123",
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to get thread messages"
            mock_logger.error.assert_called_once()


class TestAutoRenameThread:
    """Test cases for POST /{thread_id}/auto-rename endpoint"""
    
    @pytest.mark.asyncio
    @patch('app.routes.threads_route.time.time')
    async def test_auto_rename_success(self, mock_time, mock_db, mock_user, mock_thread, mock_message):
        """Test successful auto-rename with LLM"""
        mock_time.return_value = 1234567900
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.MessageRepository') as MockMessageRepo, \
             patch('app.routes.threads_route.LLMManager') as MockLLMManager, \
             patch('app.routes.threads_route.ws_manager') as mock_ws:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            message_repo = MockMessageRepo.return_value
            message_repo.find_by_thread = AsyncMock(return_value=[mock_message])
            message_repo.count_by_thread = AsyncMock(return_value=1)
            
            llm_manager = MockLLMManager.return_value
            llm_manager.ask_llm = AsyncMock(return_value="Generated Title")
            
            mock_ws.send_to_user = AsyncMock()
            
            result = await auto_rename_thread(
                thread_id="thread_abc123",
                db=mock_db,
                current_user=mock_user
            )
            
            assert result.title == "Generated Title"
            assert mock_thread.metadata_["title"] == "Generated Title"
            assert mock_thread.metadata_["auto_renamed"] is True
            assert mock_thread.metadata_["updated_at"] == 1234567900
            
            mock_db.commit.assert_called_once()
            
            # Verify WebSocket notification
            mock_ws.send_to_user.assert_called_once()
            ws_call_args = mock_ws.send_to_user.call_args
            assert ws_call_args[0][0] == "test_user_123"
            assert ws_call_args[0][1]["type"] == "thread_renamed"
            assert ws_call_args[0][1]["thread_id"] == "thread_abc123"
            assert ws_call_args[0][1]["new_title"] == "Generated Title"
    
    @pytest.mark.asyncio
    @patch('app.routes.threads_route.time.time')
    async def test_auto_rename_llm_failure_fallback(self, mock_time, mock_db, mock_user, mock_thread, mock_message):
        """Test auto-rename with LLM failure, using fallback"""
        mock_time.return_value = 1234567900
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.MessageRepository') as MockMessageRepo, \
             patch('app.routes.threads_route.LLMManager') as MockLLMManager, \
             patch('app.routes.threads_route.ws_manager') as mock_ws, \
             patch('app.routes.threads_route.logger') as mock_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            message_repo = MockMessageRepo.return_value
            message_repo.find_by_thread = AsyncMock(return_value=[mock_message])
            message_repo.count_by_thread = AsyncMock(return_value=1)
            
            llm_manager = MockLLMManager.return_value
            llm_manager.ask_llm = AsyncMock(side_effect=Exception("LLM error"))
            
            mock_ws.send_to_user = AsyncMock()
            
            result = await auto_rename_thread(
                thread_id="thread_abc123",
                db=mock_db,
                current_user=mock_user
            )
            
            # Should use fallback title
            assert result.title == "Chat 1234567900"
            assert mock_thread.metadata_["title"] == "Chat 1234567900"
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_auto_rename_no_user_message(self, mock_db, mock_user, mock_thread):
        """Test auto-rename when no user message exists"""
        system_message = Mock(role="system", content="System message")
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.MessageRepository') as MockMessageRepo:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            message_repo = MockMessageRepo.return_value
            message_repo.find_by_thread = AsyncMock(return_value=[system_message])
            
            with pytest.raises(HTTPException) as exc_info:
                await auto_rename_thread(
                    thread_id="thread_abc123",
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail == "No user message found to generate title from"
    
    @pytest.mark.asyncio
    async def test_auto_rename_thread_not_found(self, mock_db, mock_user):
        """Test auto-rename for non-existent thread"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await auto_rename_thread(
                    thread_id="nonexistent",
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Thread not found"
    
    @pytest.mark.asyncio
    async def test_auto_rename_access_denied(self, mock_db, mock_user, mock_thread):
        """Test auto-rename for thread owned by another user"""
        mock_thread.metadata_["user_id"] = "another_user"
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo:
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            with pytest.raises(HTTPException) as exc_info:
                await auto_rename_thread(
                    thread_id="thread_abc123",
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail == "Access denied"
    
    @pytest.mark.asyncio
    async def test_auto_rename_empty_metadata(self, mock_db, mock_user, mock_message):
        """Test auto-rename when thread has no metadata"""
        # Create a mock thread with proper user_id for access check
        mock_thread = Mock()
        mock_thread.id = "thread_abc123"
        mock_thread.object = "thread"
        mock_thread.created_at = 1234567890
        mock_thread.metadata_ = {"user_id": "test_user_123"}  # Has user_id for access check
        
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.MessageRepository') as MockMessageRepo, \
             patch('app.routes.threads_route.LLMManager') as MockLLMManager, \
             patch('app.routes.threads_route.ws_manager') as mock_ws:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            message_repo = MockMessageRepo.return_value
            message_repo.find_by_thread = AsyncMock(return_value=[mock_message])
            message_repo.count_by_thread = AsyncMock(return_value=1)
            
            llm_manager = MockLLMManager.return_value
            llm_manager.ask_llm = AsyncMock(return_value="New Title")
            
            mock_ws.send_to_user = AsyncMock()
            
            # Mock the metadata_ being None after access check but before update
            original_get = mock_thread.metadata_.get
            call_count = [0]
            def mock_get(key, default=None):
                call_count[0] += 1
                if call_count[0] == 1 and key == "user_id":  # First call for access check
                    return "test_user_123"
                # After access check, set metadata to None to trigger line 348
                if call_count[0] == 2:
                    mock_thread.metadata_ = None
                return default
            
            mock_thread.metadata_.get = mock_get
            
            result = await auto_rename_thread(
                thread_id="thread_abc123",
                db=mock_db,
                current_user=mock_user
            )
            
            assert mock_thread.metadata_ is not None
            assert mock_thread.metadata_["title"] == "New Title"
    
    @pytest.mark.asyncio
    async def test_auto_rename_title_cleanup(self, mock_db, mock_user, mock_thread, mock_message):
        """Test that generated title is cleaned up properly"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.MessageRepository') as MockMessageRepo, \
             patch('app.routes.threads_route.LLMManager') as MockLLMManager, \
             patch('app.routes.threads_route.ws_manager') as mock_ws:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(return_value=mock_thread)
            
            message_repo = MockMessageRepo.return_value
            message_repo.find_by_thread = AsyncMock(return_value=[mock_message])
            message_repo.count_by_thread = AsyncMock(return_value=1)
            
            llm_manager = MockLLMManager.return_value
            # LLM returns title with quotes and excess whitespace
            llm_manager.ask_llm = AsyncMock(return_value='  "Generated Title with lots of extra characters that should be truncated"  ')
            
            mock_ws.send_to_user = AsyncMock()
            
            result = await auto_rename_thread(
                thread_id="thread_abc123",
                db=mock_db,
                current_user=mock_user
            )
            
            # Title should be cleaned and truncated to 50 chars
            expected_title = "Generated Title with lots of extra characters that"[:50]
            assert result.title == expected_title
            assert len(result.title) == 50
    
    @pytest.mark.asyncio
    async def test_auto_rename_exception(self, mock_db, mock_user):
        """Test general exception in auto_rename_thread"""
        with patch('app.routes.threads_route.ThreadRepository') as MockThreadRepo, \
             patch('app.routes.threads_route.logger') as mock_logger:
            
            thread_repo = MockThreadRepo.return_value
            thread_repo.get_by_id = AsyncMock(side_effect=Exception("Database error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await auto_rename_thread(
                    thread_id="thread_abc123",
                    db=mock_db,
                    current_user=mock_user
                )
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to auto-rename thread"
            mock_logger.error.assert_called_once()


class TestRouterConfiguration:
    """Test router configuration"""
    
    def test_router_prefix(self):
        """Test router has correct prefix"""
        assert router.prefix == "/api/threads"
    
    def test_router_tags(self):
        """Test router has correct tags"""
        assert "threads" in router.tags
    
    def test_router_redirect_slashes(self):
        """Test router has redirect_slashes disabled"""
        assert router.redirect_slashes is False


class TestPydanticModels:
    """Test Pydantic model configurations"""
    
    def test_thread_create_model(self):
        """Test ThreadCreate model"""
        # Test with all fields
        thread = ThreadCreate(title="Test", metadata={"key": "value"})
        assert thread.title == "Test"
        assert thread.metadata == {"key": "value"}
        
        # Test with no fields
        thread = ThreadCreate()
        assert thread.title is None
        assert thread.metadata is None
    
    def test_thread_update_model(self):
        """Test ThreadUpdate model"""
        # Test with all fields
        update = ThreadUpdate(title="Updated", metadata={"new": "data"})
        assert update.title == "Updated"
        assert update.metadata == {"new": "data"}
        
        # Test with no fields
        update = ThreadUpdate()
        assert update.title is None
        assert update.metadata is None
    
    def test_thread_response_model(self):
        """Test ThreadResponse model"""
        response = ThreadResponse(
            id="thread_123",
            title="Test Thread",
            created_at=1234567890,
            updated_at=1234567900,
            metadata={"key": "value"},
            message_count=10
        )
        assert response.id == "thread_123"
        assert response.object == "thread"
        assert response.title == "Test Thread"
        assert response.created_at == 1234567890
        assert response.updated_at == 1234567900
        assert response.metadata == {"key": "value"}
        assert response.message_count == 10
        
        # Test defaults
        response = ThreadResponse(id="thread_456", created_at=1234567890)
        assert response.object == "thread"
        assert response.title is None
        assert response.updated_at is None
        assert response.metadata is None
        assert response.message_count == 0