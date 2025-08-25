"""
Comprehensive thread service tests for improved test coverage.
Tests various thread lifecycle operations and edge cases.
"""

import asyncio
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.core.exceptions_database import DatabaseError, RecordNotFoundError
from netra_backend.app.db.models_postgres import Thread, Message, Run, Assistant
from netra_backend.app.services.thread_service import ThreadService


class TestThreadServiceComprehensive:
    """Comprehensive test suite for ThreadService to improve coverage"""

    @pytest.fixture
    def thread_service(self):
        """Create ThreadService instance for testing"""
        return ThreadService()

    @pytest.fixture
    def mock_uow(self):
        """Mock unit of work"""
        mock_uow = AsyncMock()
        mock_uow.threads = AsyncMock()
        mock_uow.messages = AsyncMock()
        mock_uow.runs = AsyncMock()
        mock_uow.assistants = AsyncMock()
        return mock_uow

    @pytest.fixture
    def sample_thread(self):
        """Sample thread for testing"""
        return Thread(
            id=str(uuid.uuid4()),
            user_id="test_user_123",
            title="Test Thread",
            metadata={"created_by": "test_user"}
        )

    @pytest.fixture
    def sample_message(self):
        """Sample message for testing"""
        return Message(
            id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            content="Test message content",
            role="user",
            metadata={"source": "test"}
        )

    @pytest.mark.asyncio
    async def test_create_thread_success(self, thread_service, mock_uow, sample_thread):
        """Test successful thread creation"""
        user_id = "test_user_123"
        mock_uow.threads.create.return_value = sample_thread
        
        with patch.object(thread_service, '_execute_with_uow', return_value=sample_thread) as mock_execute:
            result = await thread_service.create_thread(user_id)
            
            assert result == sample_thread
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_thread_database_error(self, thread_service):
        """Test thread creation with database error"""
        user_id = "test_user_123"
        
        with patch.object(thread_service, '_execute_with_uow', side_effect=Exception("DB Error")):
            with pytest.raises(DatabaseError):
                await thread_service.create_thread(user_id)

    @pytest.mark.asyncio
    async def test_get_thread_by_id_success(self, thread_service, mock_uow, sample_thread):
        """Test successful thread retrieval by ID"""
        thread_id = sample_thread.id
        mock_uow.threads.get_by_id.return_value = sample_thread
        
        with patch.object(thread_service, '_execute_with_uow', return_value=sample_thread):
            result = await thread_service.get_thread_by_id(thread_id)
            
            assert result == sample_thread

    @pytest.mark.asyncio
    async def test_get_thread_by_id_not_found(self, thread_service, mock_uow):
        """Test thread retrieval when thread doesn't exist"""
        thread_id = "nonexistent_thread"
        
        with patch.object(thread_service, '_execute_with_uow', return_value=None):
            with pytest.raises(RecordNotFoundError):
                await thread_service.get_thread_by_id(thread_id)

    @pytest.mark.asyncio
    async def test_get_user_threads_success(self, thread_service, sample_thread):
        """Test successful retrieval of user threads"""
        user_id = "test_user_123"
        threads = [sample_thread]
        
        with patch.object(thread_service, '_execute_with_uow', return_value=threads):
            result = await thread_service.get_user_threads(user_id)
            
            assert result == threads
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_user_threads_empty_result(self, thread_service):
        """Test retrieval of user threads when no threads exist"""
        user_id = "test_user_123"
        
        with patch.object(thread_service, '_execute_with_uow', return_value=[]):
            result = await thread_service.get_user_threads(user_id)
            
            assert result == []

    @pytest.mark.asyncio
    async def test_add_message_to_thread_success(self, thread_service, sample_message):
        """Test successful message addition to thread"""
        thread_id = "test_thread_123"
        content = "Test message"
        role = "user"
        
        with patch.object(thread_service, '_execute_with_uow', return_value=sample_message):
            result = await thread_service.add_message_to_thread(thread_id, content, role)
            
            assert result == sample_message

    @pytest.mark.asyncio
    async def test_add_message_with_metadata(self, thread_service, sample_message):
        """Test adding message with metadata"""
        thread_id = "test_thread_123"
        content = "Test message with metadata"
        role = "user"
        metadata = {"source": "api", "priority": "high"}
        
        with patch.object(thread_service, '_execute_with_uow', return_value=sample_message):
            result = await thread_service.add_message_to_thread(
                thread_id, content, role, metadata=metadata
            )
            
            assert result == sample_message

    @pytest.mark.asyncio
    async def test_get_thread_messages_success(self, thread_service, sample_message):
        """Test successful retrieval of thread messages"""
        thread_id = "test_thread_123"
        messages = [sample_message]
        
        with patch.object(thread_service, '_execute_with_uow', return_value=messages):
            result = await thread_service.get_thread_messages(thread_id)
            
            assert result == messages
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_thread_messages_with_limit(self, thread_service):
        """Test retrieval of thread messages with limit"""
        thread_id = "test_thread_123"
        limit = 10
        messages = []
        
        with patch.object(thread_service, '_execute_with_uow', return_value=messages):
            result = await thread_service.get_thread_messages(thread_id, limit=limit)
            
            assert result == messages

    @pytest.mark.asyncio
    async def test_update_thread_title_success(self, thread_service, sample_thread):
        """Test successful thread title update"""
        thread_id = sample_thread.id
        new_title = "Updated Thread Title"
        updated_thread = Thread(
            id=thread_id,
            user_id=sample_thread.user_id,
            title=new_title,
            metadata=sample_thread.metadata
        )
        
        with patch.object(thread_service, '_execute_with_uow', return_value=updated_thread):
            result = await thread_service.update_thread_title(thread_id, new_title)
            
            assert result == updated_thread

    @pytest.mark.asyncio
    async def test_delete_thread_success(self, thread_service):
        """Test successful thread deletion"""
        thread_id = "test_thread_123"
        
        with patch.object(thread_service, '_execute_with_uow', return_value=True):
            result = await thread_service.delete_thread(thread_id)
            
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_thread(self, thread_service):
        """Test deletion of nonexistent thread"""
        thread_id = "nonexistent_thread"
        
        with patch.object(thread_service, '_execute_with_uow', side_effect=RecordNotFoundError("Thread not found")):
            with pytest.raises(RecordNotFoundError):
                await thread_service.delete_thread(thread_id)

    @pytest.mark.asyncio
    async def test_websocket_event_sending(self, thread_service):
        """Test WebSocket event sending during thread creation"""
        user_id = "test_user_123"
        
        with patch('app.services.thread_service.manager') as mock_manager:
            mock_manager.send_message = AsyncMock()
            
            await thread_service._send_thread_created_event(user_id)
            
            mock_manager.send_message.assert_called_once()
            call_args = mock_manager.send_message.call_args
            assert call_args[0][0] == user_id
            assert call_args[0][1]["type"] == "thread_created"
            assert "thread_id" in call_args[0][1]["payload"]

    @pytest.mark.asyncio
    async def test_execute_with_uow_no_db_session(self, thread_service):
        """Test _execute_with_uow without existing database session"""
        async def mock_operation(uow):
            return "success"
        
        with patch('app.services.thread_service.get_unit_of_work') as mock_get_uow:
            mock_uow = AsyncMock()
            mock_get_uow.return_value.__aenter__.return_value = mock_uow
            mock_get_uow.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await thread_service._execute_with_uow(mock_operation)
            
            assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_uow_with_db_session(self, thread_service):
        """Test _execute_with_uow with existing database session"""
        async def mock_operation(uow):
            return "success_with_db"
        
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.services.thread_service.get_unit_of_work') as mock_get_uow:
            mock_uow = AsyncMock()
            mock_get_uow.return_value.__aenter__.return_value = mock_uow
            mock_get_uow.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await thread_service._execute_with_uow(mock_operation, db=mock_db)
            
            assert result == "success_with_db"
            mock_get_uow.assert_called_with(mock_db)

    @pytest.mark.asyncio
    async def test_concurrent_thread_operations(self, thread_service):
        """Test concurrent thread operations for thread safety"""
        user_id = "test_user_123"
        
        async def create_thread_mock():
            await asyncio.sleep(0.01)  # Simulate async work
            return Thread(id=str(uuid.uuid4()), user_id=user_id, title=f"Thread {uuid.uuid4()}")
        
        with patch.object(thread_service, '_execute_with_uow', side_effect=create_thread_mock):
            # Create multiple threads concurrently
            tasks = [thread_service.create_thread(user_id) for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            assert all(isinstance(result, Thread) for result in results)

    @pytest.mark.asyncio
    async def test_error_handling_in_database_operations(self, thread_service):
        """Test error handling wrapper function"""
        from netra_backend.app.services.thread_service import _handle_database_error
        
        operation = "test_operation"
        context = {"user_id": "test_user"}
        error = Exception("Database connection failed")
        
        result = _handle_database_error(operation, context, error)
        
        assert isinstance(result, DatabaseError)
        assert "Failed to test_operation" in str(result)