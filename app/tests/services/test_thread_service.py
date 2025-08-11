import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.services.thread_service import ThreadService
from app.db.models_postgres import Thread, Message, Run
import uuid
import time
from typing import List, Dict, Any


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


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


@pytest.mark.asyncio
class TestThreadService:
    """Test suite for ThreadService covering all methods with comprehensive scenarios"""

    class TestGetOrCreateThread:
        """Tests for get_or_create_thread method"""

        async def test_get_existing_thread_success(self, thread_service, mock_db, sample_thread):
            """Test getting an existing thread"""
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = sample_thread
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            result = await thread_service.get_or_create_thread(mock_db, "user123")
            
            assert result == sample_thread
            mock_db.execute.assert_called_once()
            mock_db.add.assert_not_called()
            mock_db.commit.assert_not_called()

        async def test_create_new_thread_success(self, thread_service, mock_db):
            """Test creating a new thread when none exists"""
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            with patch('time.time', return_value=1234567890):
                result = await thread_service.get_or_create_thread(mock_db, "user123")
            
            assert result is not None
            assert result.id == "thread_user123"
            assert result.metadata_["user_id"] == "user123"
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

        async def test_handle_integrity_error_race_condition(self, thread_service, mock_db, sample_thread):
            """Test handling race condition during thread creation"""
            mock_result_first = MagicMock()
            mock_result_first.scalar_one_or_none.return_value = None
            mock_result_second = MagicMock()
            mock_result_second.scalar_one_or_none.return_value = sample_thread
            
            mock_db.execute = AsyncMock(side_effect=[mock_result_first, mock_result_second])
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock(side_effect=IntegrityError("statement", "params", "orig"))
            mock_db.rollback = AsyncMock()
            
            result = await thread_service.get_or_create_thread(mock_db, "user123")
            
            assert result == sample_thread
            mock_db.rollback.assert_called_once()
            assert mock_db.execute.call_count == 2

        async def test_handle_sqlalchemy_error(self, thread_service, mock_db):
            """Test handling SQLAlchemy errors"""
            mock_db.execute = AsyncMock(side_effect=SQLAlchemyError("Database error"))
            mock_db.rollback = AsyncMock()
            
            result = await thread_service.get_or_create_thread(mock_db, "user123")
            
            assert result is None
            mock_db.rollback.assert_called_once()

        async def test_handle_unexpected_error(self, thread_service, mock_db):
            """Test handling unexpected errors"""
            mock_db.execute = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_db.rollback = AsyncMock()
            
            result = await thread_service.get_or_create_thread(mock_db, "user123")
            
            assert result is None
            mock_db.rollback.assert_called_once()

    class TestCreateMessage:
        """Tests for create_message method"""

        async def test_create_message_success_minimal(self, thread_service, mock_db):
            """Test creating a message with minimal parameters"""
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            with patch('uuid.uuid4', return_value="test-uuid"), \
                 patch('time.time', return_value=1234567890):
                result = await thread_service.create_message(
                    mock_db, "thread_123", "user", "Hello world"
                )
            
            assert result is not None
            assert result.id == "msg_test-uuid"
            assert result.thread_id == "thread_123"
            assert result.role == "user"
            assert result.content[0]["text"]["value"] == "Hello world"
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

        async def test_create_message_success_full_params(self, thread_service, mock_db):
            """Test creating a message with all parameters"""
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            metadata = {"priority": "high", "source": "api"}
            
            with patch('uuid.uuid4', return_value="test-uuid"), \
                 patch('time.time', return_value=1234567890):
                result = await thread_service.create_message(
                    db=mock_db,
                    thread_id="thread_123",
                    role="assistant",
                    content="Response message",
                    assistant_id="asst_456",
                    run_id="run_789",
                    metadata=metadata
                )
            
            assert result is not None
            assert result.assistant_id == "asst_456"
            assert result.run_id == "run_789"
            assert result.metadata_ == metadata

        async def test_create_message_sqlalchemy_error(self, thread_service, mock_db):
            """Test handling SQLAlchemy error during message creation"""
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock(side_effect=SQLAlchemyError("Database error"))
            mock_db.rollback = AsyncMock()
            
            result = await thread_service.create_message(
                mock_db, "thread_123", "user", "Test message"
            )
            
            assert result is None
            mock_db.rollback.assert_called_once()

        async def test_create_message_unexpected_error(self, thread_service, mock_db):
            """Test handling unexpected error during message creation"""
            mock_db.add = MagicMock(side_effect=Exception("Unexpected error"))
            mock_db.rollback = AsyncMock()
            
            result = await thread_service.create_message(
                mock_db, "thread_123", "user", "Test message"
            )
            
            assert result is None
            mock_db.rollback.assert_called_once()

    class TestGetThreadMessages:
        """Tests for get_thread_messages method"""

        async def test_get_thread_messages_success(self, thread_service, mock_db, sample_message):
            """Test retrieving thread messages successfully"""
            msg1 = Message(id="msg1", thread_id="thread_123", created_at=1000, role="user", content=[])
            msg2 = Message(id="msg2", thread_id="thread_123", created_at=2000, role="assistant", content=[])
            msg3 = Message(id="msg3", thread_id="thread_123", created_at=3000, role="user", content=[])
            
            mock_result = MagicMock()
            # Messages should be returned in desc order by query, then reversed
            mock_result.scalars.return_value.all.return_value = [msg3, msg2, msg1]
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            result = await thread_service.get_thread_messages(mock_db, "thread_123")
            
            assert len(result) == 3
            assert result[0].id == "msg1"  # Chronological order after reversal
            assert result[1].id == "msg2"
            assert result[2].id == "msg3"
            mock_db.execute.assert_called_once()

        async def test_get_thread_messages_with_limit(self, thread_service, mock_db):
            """Test retrieving thread messages with custom limit"""
            messages = [Message(id=f"msg{i}", thread_id="thread_123", created_at=i*1000, role="user", content=[]) 
                       for i in range(3)]
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = list(reversed(messages))
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            result = await thread_service.get_thread_messages(mock_db, "thread_123", limit=10)
            
            assert len(result) == 3
            mock_db.execute.assert_called_once()

        async def test_get_thread_messages_empty_thread(self, thread_service, mock_db):
            """Test retrieving messages from empty thread"""
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            result = await thread_service.get_thread_messages(mock_db, "empty_thread")
            
            assert result == []
            mock_db.execute.assert_called_once()

    class TestCreateRun:
        """Tests for create_run method"""

        async def test_create_run_success_minimal(self, thread_service, mock_db):
            """Test creating a run with minimal parameters"""
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            with patch('uuid.uuid4', return_value="test-uuid"), \
                 patch('time.time', return_value=1234567890):
                result = await thread_service.create_run(
                    mock_db, "thread_123", "asst_456"
                )
            
            assert result is not None
            assert result.id == "run_test-uuid"
            assert result.thread_id == "thread_123"
            assert result.assistant_id == "asst_456"
            assert result.status == "in_progress"
            assert result.model == "gpt-4"
            assert result.instructions is None
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

        async def test_create_run_success_full_params(self, thread_service, mock_db):
            """Test creating a run with all parameters"""
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            with patch('uuid.uuid4', return_value="test-uuid"), \
                 patch('time.time', return_value=1234567890):
                result = await thread_service.create_run(
                    db=mock_db,
                    thread_id="thread_123",
                    assistant_id="asst_456",
                    model="gpt-3.5-turbo",
                    instructions="Custom instructions"
                )
            
            assert result is not None
            assert result.model == "gpt-3.5-turbo"
            assert result.instructions == "Custom instructions"

    class TestUpdateRunStatus:
        """Tests for update_run_status method"""

        async def test_update_run_status_to_completed(self, thread_service, mock_db, sample_run):
            """Test updating run status to completed"""
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = sample_run
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            with patch('time.time', return_value=1234567890):
                result = await thread_service.update_run_status(
                    mock_db, "run_test123", "completed"
                )
            
            assert result.status == "completed"
            assert result.completed_at == 1234567890
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

        async def test_update_run_status_to_failed_with_error(self, thread_service, mock_db, sample_run):
            """Test updating run status to failed with error details"""
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = sample_run
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            error_details = {"code": "rate_limit_exceeded", "message": "Too many requests"}
            
            with patch('time.time', return_value=1234567890):
                result = await thread_service.update_run_status(
                    mock_db, "run_test123", "failed", error=error_details
                )
            
            assert result.status == "failed"
            assert result.failed_at == 1234567890
            assert result.last_error == error_details

        async def test_update_run_status_to_in_progress(self, thread_service, mock_db, sample_run):
            """Test updating run status to in_progress (no timestamps)"""
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = sample_run
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            result = await thread_service.update_run_status(
                mock_db, "run_test123", "in_progress"
            )
            
            assert result.status == "in_progress"
            # Should not set completed_at or failed_at
            assert not hasattr(result, 'completed_at') or result.completed_at is None
            assert not hasattr(result, 'failed_at') or result.failed_at is None

        async def test_update_run_status_run_not_found(self, thread_service, mock_db):
            """Test updating status when run doesn't exist"""
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            result = await thread_service.update_run_status(
                mock_db, "nonexistent_run", "completed"
            )
            
            assert result is None
            mock_db.commit.assert_not_called()
            mock_db.refresh.assert_not_called()

    class TestThreadServiceIntegration:
        """Integration tests simulating real workflows"""

        async def test_complete_conversation_flow(self, thread_service, mock_db):
            """Test complete flow: create thread, add messages, create run, update status"""
            # Mock thread creation
            mock_result_thread = MagicMock()
            mock_result_thread.scalar_one_or_none.return_value = None
            mock_db.execute = AsyncMock(return_value=mock_result_thread)
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            # Step 1: Create/get thread
            with patch('time.time', return_value=1000):
                thread = await thread_service.get_or_create_thread(mock_db, "user123")
            
            assert thread.id == "thread_user123"
            
            # Step 2: Create user message
            with patch('uuid.uuid4', return_value="msg-uuid"), \
                 patch('time.time', return_value=2000):
                user_message = await thread_service.create_message(
                    mock_db, thread.id, "user", "Hello assistant"
                )
            
            assert user_message.role == "user"
            assert user_message.content[0]["text"]["value"] == "Hello assistant"
            
            # Step 3: Create run
            with patch('uuid.uuid4', return_value="run-uuid"), \
                 patch('time.time', return_value=3000):
                run = await thread_service.create_run(
                    mock_db, thread.id, "asst_123", instructions="Be helpful"
                )
            
            assert run.status == "in_progress"
            assert run.instructions == "Be helpful"
            
            # Step 4: Create assistant response
            with patch('uuid.uuid4', return_value="response-uuid"), \
                 patch('time.time', return_value=4000):
                assistant_message = await thread_service.create_message(
                    mock_db, thread.id, "assistant", "Hello user!", 
                    assistant_id="asst_123", run_id=run.id
                )
            
            assert assistant_message.role == "assistant"
            assert assistant_message.assistant_id == "asst_123"
            assert assistant_message.run_id == run.id
            
            # Step 5: Complete the run
            mock_result_run = MagicMock()
            mock_result_run.scalar_one_or_none.return_value = run
            mock_db.execute = AsyncMock(return_value=mock_result_run)
            
            with patch('time.time', return_value=5000):
                completed_run = await thread_service.update_run_status(
                    mock_db, run.id, "completed"
                )
            
            assert completed_run.status == "completed"
            assert completed_run.completed_at == 5000

        async def test_error_handling_workflow(self, thread_service, mock_db):
            """Test workflow with various error conditions"""
            # Test thread creation failure
            mock_db.execute = AsyncMock(side_effect=SQLAlchemyError("DB Error"))
            mock_db.rollback = AsyncMock()
            
            thread = await thread_service.get_or_create_thread(mock_db, "user123")
            assert thread is None
            
            # Test message creation failure
            mock_db.execute = AsyncMock()  # Reset mock
            mock_db.add = MagicMock(side_effect=Exception("Unexpected error"))
            mock_db.rollback = AsyncMock()
            
            message = await thread_service.create_message(
                mock_db, "thread_123", "user", "Test"
            )
            assert message is None
            mock_db.rollback.assert_called()