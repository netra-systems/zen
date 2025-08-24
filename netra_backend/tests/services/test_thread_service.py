import sys
from pathlib import Path

import time
from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import pytest

from netra_backend.app.db.models_postgres import Message, Run, Thread

from netra_backend.app.services.thread_service import ThreadService

@pytest.fixture
def thread_service():
    return ThreadService()

@pytest.fixture
def sample_thread():
    return Thread(
        id="thread_user123",
        object="thread",
        created_at=int(time.time()),
        metadata_={"user_id": "user123"}
    )

@pytest.fixture
def sample_message():
    return Message(
        id="msg_test123",
        object="thread.message",
        created_at=int(time.time()),
        thread_id="thread_user123",
        role="user",
        content=[{"type": "text", "text": {"value": "Test message"}}],
        assistant_id=None,
        run_id=None,
        file_ids=[],
        metadata_={}
    )

@pytest.fixture
def sample_run():
    return Run(
        id="run_test123",
        object="thread.run",
        created_at=int(time.time()),
        thread_id="thread_user123",
        assistant_id="asst_test123",
        status="in_progress",
        model="gpt-4",
        instructions="Test instructions",
        tools=[],
        file_ids=[],
        metadata_={}
    )

class TestThreadService:
    """Test suite for ThreadService with UnitOfWork pattern"""

    @patch('app.services.thread_service.get_unit_of_work')
    @patch('app.services.thread_service.manager')
    @pytest.mark.asyncio
    async def test_get_or_create_thread_existing(self, mock_manager, mock_get_uow, thread_service, sample_thread):
        """Test getting an existing thread"""
        # Setup mock UnitOfWork
        mock_uow = AsyncMock()
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.threads.get_or_create_for_user = AsyncMock(return_value=sample_thread)
        mock_uow.session = MagicMock()
        
        mock_get_uow.return_value = mock_uow
        mock_manager.send_message = AsyncMock()
        
        # Execute
        result = await thread_service.get_or_create_thread("user123")
        
        # Assert
        assert result == sample_thread
        mock_uow.threads.get_or_create_for_user.assert_called_once_with(mock_uow.session, "user123")
        mock_manager.send_message.assert_called_once()

    @patch('app.services.thread_service.get_unit_of_work')
    @patch('app.services.thread_service.manager')
    @pytest.mark.asyncio
    async def test_create_message_success(self, mock_manager, mock_get_uow, thread_service, sample_message):
        """Test creating a message successfully"""
        # Setup mock UnitOfWork
        mock_uow = AsyncMock()
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.messages.create = AsyncMock(return_value=sample_message)
        
        mock_get_uow.return_value = mock_uow
        
        with patch('uuid.uuid4', return_value="test-uuid"), \
             patch('time.time', return_value=1234567890):
            result = await thread_service.create_message(
                "thread_123", "user", "Hello world"
            )
        
        assert result == sample_message
        mock_uow.messages.create.assert_called_once()

    @patch('app.services.thread_service.get_unit_of_work')
    @pytest.mark.asyncio
    async def test_get_thread_messages_success(self, mock_get_uow, thread_service):
        """Test retrieving thread messages"""
        # Create test messages
        messages = [
            Message(id=f"msg{i}", thread_id="thread_123", created_at=i*1000, 
                   role="user", content=[], object="thread.message", file_ids=[], metadata_={})
            for i in range(3)
        ]
        
        # Setup mock UnitOfWork
        mock_uow = AsyncMock()
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.messages.get_by_thread = AsyncMock(return_value=messages)
        mock_uow.session = MagicMock()
        
        mock_get_uow.return_value = mock_uow
        
        result = await thread_service.get_thread_messages("thread_123")
        
        assert len(result) == 3
        mock_uow.messages.get_by_thread.assert_called_once_with(mock_uow.session, "thread_123", 50)

    @patch('app.services.thread_service.get_unit_of_work')
    @patch('app.services.thread_service.manager')
    @pytest.mark.asyncio
    async def test_create_run_success(self, mock_manager, mock_get_uow, thread_service, sample_run, sample_thread):
        """Test creating a run successfully"""
        # Setup mock UnitOfWork
        mock_uow = AsyncMock()
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.runs.create = AsyncMock(return_value=sample_run)
        mock_uow.threads.get_by_id = AsyncMock(return_value=sample_thread)
        mock_uow.session = MagicMock()
        
        mock_get_uow.return_value = mock_uow
        mock_manager.send_message = AsyncMock()
        
        with patch('uuid.uuid4', return_value="test-uuid"), \
             patch('time.time', return_value=1234567890):
            result = await thread_service.create_run(
                "thread_123", "asst_456"
            )
        
        assert result == sample_run
        mock_uow.runs.create.assert_called_once()
        mock_manager.send_message.assert_called_once()

    @patch('app.services.thread_service.get_unit_of_work')
    @pytest.mark.asyncio
    async def test_update_run_status_completed(self, mock_get_uow, thread_service, sample_run):
        """Test updating run status to completed"""
        # Setup mock UnitOfWork
        mock_uow = AsyncMock()
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        
        # Update the sample run to completed
        completed_run = sample_run
        completed_run.status = "completed"
        completed_run.completed_at = 1234567890
        
        mock_uow.runs.update = AsyncMock(return_value=completed_run)
        mock_uow.session = MagicMock()
        
        mock_get_uow.return_value = mock_uow
        
        with patch('time.time', return_value=1234567890):
            result = await thread_service.update_run_status(
                "run_test123", "completed"
            )
        
        assert result.status == "completed"
        mock_uow.runs.update.assert_called_once()
        
    @patch('app.services.thread_service.get_unit_of_work')
    @pytest.mark.asyncio
    async def test_get_thread_success(self, mock_get_uow, thread_service, sample_thread):
        """Test getting a thread by ID"""
        # Setup mock UnitOfWork
        mock_uow = AsyncMock()
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.threads.get_by_id = AsyncMock(return_value=sample_thread)
        mock_uow.session = MagicMock()
        
        mock_get_uow.return_value = mock_uow
        
        result = await thread_service.get_thread("thread_user123")
        
        assert result == sample_thread
        mock_uow.threads.get_by_id.assert_called_once_with(mock_uow.session, "thread_user123")

    @patch('app.services.thread_service.get_unit_of_work')
    @patch('app.services.thread_service.manager')
    @pytest.mark.asyncio
    async def test_delete_thread_success(self, mock_manager, mock_get_uow, thread_service):
        """Test deleting a thread"""
        # Setup mock UnitOfWork
        mock_uow = AsyncMock()
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.__aexit__.return_value = None
        mock_uow.threads.delete = AsyncMock(return_value=True)
        mock_uow.session = MagicMock()
        
        mock_get_uow.return_value = mock_uow
        mock_manager.send_message = AsyncMock()
        
        result = await thread_service.delete_thread("thread_123", "user123")
        
        assert result == True
        mock_uow.threads.delete.assert_called_once_with(mock_uow.session, "thread_123")
        mock_manager.send_message.assert_called_once()