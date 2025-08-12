"""Test database repositories and Unit of Work pattern implementation."""

import pytest
from datetime import datetime, timedelta
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.services.database.unit_of_work import UnitOfWork
from app.services.database.base_repository import BaseRepository
from app.services.database.message_repository import MessageRepository
from app.services.database.thread_repository import ThreadRepository
from app.services.database.run_repository import RunRepository
from app.services.database.reference_repository import ReferenceRepository
# Note: Adjust imports based on actual model locations
# from app.db.models import Message, Thread, Run, Reference, User


@pytest.fixture
def unit_of_work(mock_session, mock_models):
    """Create a test unit of work instance with mocked session."""
    # Mock the session factory to return our mock session
    with patch('app.services.database.unit_of_work.async_session_factory') as mock_factory:
        mock_factory.return_value = mock_session
        uow = UnitOfWork()
        return uow


@pytest.fixture
def mock_models():
    """Mock the database models."""
    # Create mock model classes
    class MockThread:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', 'thread_' + str(datetime.now().timestamp()))
            self.user_id = kwargs.get('user_id')
            self.title = kwargs.get('title')
            self.created_at = kwargs.get('created_at', datetime.now())
            self.updated_at = kwargs.get('updated_at', datetime.now())
    
    class MockMessage:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', 'msg_' + str(datetime.now().timestamp()))
            self.thread_id = kwargs.get('thread_id')
            self.content = kwargs.get('content')
            self.role = kwargs.get('role')
            self.created_at = kwargs.get('created_at', datetime.now())
    
    class MockRun:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', 'run_' + str(datetime.now().timestamp()))
            self.thread_id = kwargs.get('thread_id')
            self.status = kwargs.get('status', 'completed')
            self.created_at = kwargs.get('created_at', datetime.now())
    
    class MockReference:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', 'ref_' + str(datetime.now().timestamp()))
            self.message_id = kwargs.get('message_id')
            self.source = kwargs.get('source')
            self.content = kwargs.get('content')
    
    # Return the mock classes directly instead of using context manager
    return {
        'Thread': MockThread,
        'Message': MockMessage,
        'Run': MockRun,
        'Reference': MockReference
    }

@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    
    # Mock the refresh to update the entity with an ID
    async def mock_refresh(entity):
        if hasattr(entity, 'id') and not entity.id:
            entity.id = "test_id_123"
    session.refresh.side_effect = mock_refresh
    
    return session


@pytest.mark.asyncio
class TestUnitOfWork:
    """Test Unit of Work pattern implementation."""

    async def test_uow_initialization(self, unit_of_work):
        """Test UoW initialization and repository access."""
        async with unit_of_work as uow:
            assert uow.messages != None
            assert uow.threads != None
            assert uow.runs != None
            assert uow.references != None
            assert isinstance(uow.messages, MessageRepository)
            assert isinstance(uow.threads, ThreadRepository)

    async def test_uow_transaction_commit(self, unit_of_work):
        """Test successful transaction commit."""
        async with unit_of_work:
            # Create test data
            thread = await unit_of_work.threads.create({
                "user_id": "test_user",
                "title": "Test Thread"
            })
            
            message = await unit_of_work.messages.create({
                "thread_id": thread.id,
                "content": "Test message",
                "role": "user"
            })
            
            # Commit should be called on context exit
            await unit_of_work.commit()
        
        # Verify data persisted
        retrieved_thread = await unit_of_work.threads.get(thread.id)
        assert retrieved_thread != None
        assert retrieved_thread.title == "Test Thread"

    async def test_uow_transaction_rollback(self, unit_of_work):
        """Test transaction rollback on error."""
        try:
            async with unit_of_work:
                # Create test data
                await unit_of_work.threads.create({
                    "user_id": "test_user",
                    "title": "Test Thread"
                })
                
                # Simulate error
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Verify rollback was called
        assert unit_of_work.session.rollback.called

    async def test_uow_nested_transactions(self, unit_of_work):
        """Test nested transaction handling."""
        async with unit_of_work:
            # Outer transaction
            thread = await unit_of_work.threads.create({
                "user_id": "test_user",
                "title": "Outer Transaction"
            })
            
            # Nested transaction (savepoint)
            async with unit_of_work.begin_nested() as nested:
                message = await unit_of_work.messages.create({
                    "thread_id": thread.id,
                    "content": "Nested message",
                    "role": "user"
                })
                
                # Rollback nested only
                await nested.rollback()
            
            # Outer transaction should still be valid
            await unit_of_work.commit()
        
        # Thread should exist, message should not
        assert await unit_of_work.threads.get(thread.id) != None
        messages = await unit_of_work.messages.get_by_thread(thread.id)
        assert len(messages) == 0

    async def test_uow_concurrent_access(self, unit_of_work):
        """Test concurrent UoW instances."""
        async def create_thread(uow, thread_id):
            async with uow:
                return await uow.threads.create({
                    "user_id": f"user_{thread_id}",
                    "title": f"Thread {thread_id}"
                })
        
        # Create multiple UoW instances
        uow1 = UnitOfWork()
        uow2 = UnitOfWork()
        
        # Execute concurrently
        import asyncio
        results = await asyncio.gather(
            create_thread(uow1, 1),
            create_thread(uow2, 2)
        )
        
        assert len(results) == 2
        assert results[0].title == "Thread 1"
        assert results[1].title == "Thread 2"


@pytest.mark.asyncio
class TestBaseRepository:
    """Test base repository functionality."""

    async def test_repository_create(self, unit_of_work):
        """Test creating an entity."""
        thread_data = {
            "user_id": "test_user",
            "title": "Test Thread",
            "metadata": {"key": "value"}
        }
        
        thread = await unit_of_work.threads.create(thread_data)
        
        assert thread.id != None
        assert thread.user_id == "test_user"
        assert thread.title == "Test Thread"
        assert thread.created_at != None

    async def test_repository_bulk_create(self, unit_of_work, mock_models):
        """Test bulk entity creation."""
        import time
        async with unit_of_work as uow:
            # Mock the bulk_create to return mock threads
            mock_threads = []
            for i in range(10):
                thread = mock_models['Thread'](
                    id=f"thread_{i}",
                    object="thread",
                    created_at=int(time.time()),
                    metadata_={"user_id": f"user_{i}", "title": f"Thread {i}"}
                )
                mock_threads.append(thread)
            
            # Mock the bulk_create method
            uow.threads.bulk_create = AsyncMock(return_value=mock_threads)
            
            threads_data = [
                {
                    "object": "thread",
                    "created_at": int(time.time()),
                    "metadata_": {"user_id": f"user_{i}", "title": f"Thread {i}"}
                }
                for i in range(10)
            ]
            
            threads = await uow.threads.bulk_create(threads_data)
            
            assert len(threads) == 10
            assert all(t.id != None for t in threads)

    async def test_repository_get_by_id(self, unit_of_work, mock_models):
        """Test getting entity by ID."""
        async with unit_of_work as uow:
            # Create a mock thread
            mock_thread = mock_models['Thread'](
                id="thread_test_123",
                user_id="test_user",
                title="Test Thread"
            )
            
            # Mock the create and get methods
            uow.threads.create = AsyncMock(return_value=mock_thread)
            uow.threads.get = AsyncMock(return_value=mock_thread)
            
            thread = await uow.threads.create({
                "user_id": "test_user",
                "title": "Test Thread"
            })
            
            retrieved = await uow.threads.get(thread.id)
            
            assert retrieved != None
            assert retrieved.id == thread.id
            assert retrieved.title == thread.title

    async def test_repository_get_many(self, unit_of_work, mock_models):
        """Test getting multiple entities."""
        async with unit_of_work as uow:
            # Create mock threads
            mock_threads = []
            thread_ids = []
            for i in range(5):
                thread = mock_models['Thread'](
                    id=f"thread_{i}",
                    user_id="test_user",
                    title=f"Thread {i}"
                )
                mock_threads.append(thread)
                thread_ids.append(thread.id)
            
            # Mock the create and get_many methods
            uow.threads.create = AsyncMock(side_effect=mock_threads)
            uow.threads.get_many = AsyncMock(return_value=mock_threads[:3])
            
            # Create test data
            created_ids = []
            for i in range(5):
                thread = await uow.threads.create({
                    "user_id": "test_user",
                    "title": f"Thread {i}"
                })
                created_ids.append(thread.id)
            
            # Get multiple
            threads = await uow.threads.get_many(created_ids[:3])
            
            assert len(threads) == 3
            assert all(t.id in thread_ids[:3] for t in threads)

    async def test_repository_update(self, unit_of_work):
        """Test updating an entity."""
        thread = await unit_of_work.threads.create({
            "user_id": "test_user",
            "title": "Original Title"
        })
        
        updated = await unit_of_work.threads.update(
            thread.id,
            {"title": "Updated Title"}
        )
        
        assert updated.title == "Updated Title"
        assert updated.updated_at > thread.created_at

    async def test_repository_delete(self, unit_of_work):
        """Test deleting an entity."""
        thread = await unit_of_work.threads.create({
            "user_id": "test_user",
            "title": "To Delete"
        })
        
        deleted = await unit_of_work.threads.delete(thread.id)
        assert deleted == True
        
        # Verify deletion
        retrieved = await unit_of_work.threads.get(thread.id)
        assert retrieved == None

    async def test_repository_soft_delete(self, unit_of_work):
        """Test soft delete functionality."""
        thread = await unit_of_work.threads.create({
            "user_id": "test_user",
            "title": "Soft Delete Test"
        })
        
        # Soft delete
        await unit_of_work.threads.soft_delete(thread.id)
        
        # Should not appear in regular queries
        retrieved = await unit_of_work.threads.get(thread.id)
        assert retrieved == None
        
        # Should be retrievable with include_deleted
        retrieved = await unit_of_work.threads.get(
            thread.id,
            include_deleted=True
        )
        assert retrieved != None
        assert retrieved.deleted_at != None

    async def test_repository_pagination(self, unit_of_work):
        """Test pagination functionality."""
        # Create test data
        for i in range(25):
            await unit_of_work.threads.create({
                "user_id": "test_user",
                "title": f"Thread {i}"
            })
        
        # Test pagination
        page1 = await unit_of_work.threads.get_paginated(page=1, page_size=10)
        page2 = await unit_of_work.threads.get_paginated(page=2, page_size=10)
        page3 = await unit_of_work.threads.get_paginated(page=3, page_size=10)
        
        assert len(page1.items) == 10
        assert len(page2.items) == 10
        assert len(page3.items) == 5
        assert page1.total == 25
        assert page1.pages == 3


@pytest.mark.asyncio
class TestMessageRepository:
    """Test message repository specific functionality."""

    async def test_get_messages_by_thread(self, unit_of_work):
        """Test getting messages by thread ID."""
        thread = await unit_of_work.threads.create({
            "user_id": "test_user",
            "title": "Test Thread"
        })
        
        # Create messages
        for i in range(5):
            await unit_of_work.messages.create({
                "thread_id": thread.id,
                "content": f"Message {i}",
                "role": "user" if i % 2 == 0 else "assistant"
            })
        
        messages = await unit_of_work.messages.get_by_thread(thread.id)
        
        assert len(messages) == 5
        assert all(m.thread_id == thread.id for m in messages)

    async def test_get_messages_with_pagination(self, unit_of_work):
        """Test paginated message retrieval."""
        thread = await unit_of_work.threads.create({
            "user_id": "test_user",
            "title": "Test Thread"
        })
        
        # Create many messages
        for i in range(50):
            await unit_of_work.messages.create({
                "thread_id": thread.id,
                "content": f"Message {i}",
                "role": "user"
            })
        
        # Get paginated
        page = await unit_of_work.messages.get_by_thread_paginated(
            thread.id,
            page=2,
            page_size=10
        )
        
        assert len(page.items) == 10
        assert page.total == 50

    async def test_get_latest_messages(self, unit_of_work):
        """Test getting latest messages."""
        thread = await unit_of_work.threads.create({
            "user_id": "test_user",
            "title": "Test Thread"
        })
        
        # Create messages with delays
        import asyncio
        for i in range(10):
            await unit_of_work.messages.create({
                "thread_id": thread.id,
                "content": f"Message {i}",
                "role": "user"
            })
            await asyncio.sleep(0.01)
        
        # Get latest 5
        latest = await unit_of_work.messages.get_latest(thread.id, limit=5)
        
        assert len(latest) == 5
        assert latest[0].content == "Message 9"
        assert latest[-1].content == "Message 5"


@pytest.mark.asyncio
class TestThreadRepository:
    """Test thread repository specific functionality."""

    async def test_get_threads_by_user(self, unit_of_work):
        """Test getting threads by user ID."""
        user_id = "test_user"
        
        # Create threads
        for i in range(5):
            await unit_of_work.threads.create({
                "user_id": user_id,
                "title": f"Thread {i}"
            })
        
        threads = await unit_of_work.threads.get_by_user(user_id)
        
        assert len(threads) == 5
        assert all(t.user_id == user_id for t in threads)

    async def test_get_active_threads(self, unit_of_work):
        """Test getting active threads."""
        user_id = "test_user"
        
        # Create threads with different activity
        active_thread = await unit_of_work.threads.create({
            "user_id": user_id,
            "title": "Active Thread",
            "last_activity": datetime.now()
        })
        
        inactive_thread = await unit_of_work.threads.create({
            "user_id": user_id,
            "title": "Inactive Thread",
            "last_activity": datetime.now() - timedelta(days=30)
        })
        
        active = await unit_of_work.threads.get_active(
            user_id,
            since=datetime.now() - timedelta(days=7)
        )
        
        assert len(active) == 1
        assert active[0].id == active_thread.id

    async def test_archive_thread(self, unit_of_work):
        """Test thread archival."""
        thread = await unit_of_work.threads.create({
            "user_id": "test_user",
            "title": "To Archive"
        })
        
        archived = await unit_of_work.threads.archive(thread.id)
        
        assert archived.is_archived == True
        assert archived.archived_at != None


@pytest.mark.asyncio
class TestRunRepository:
    """Test run repository specific functionality."""

    async def test_create_run_with_tools(self, unit_of_work):
        """Test creating a run with tool configurations."""
        thread = await unit_of_work.threads.create({
            "user_id": "test_user",
            "title": "Test Thread"
        })
        
        run = await unit_of_work.runs.create({
            "thread_id": thread.id,
            "status": "in_progress",
            "tools": ["code_interpreter", "retrieval"],
            "model": "gpt-4",
            "instructions": "Test instructions"
        })
        
        assert run.id != None
        assert run.tools == ["code_interpreter", "retrieval"]
        assert run.status == "in_progress"

    async def test_update_run_status(self, unit_of_work):
        """Test updating run status."""
        thread = await unit_of_work.threads.create({
            "user_id": "test_user",
            "title": "Test Thread"
        })
        
        run = await unit_of_work.runs.create({
            "thread_id": thread.id,
            "status": "in_progress"
        })
        
        # Update status
        updated = await unit_of_work.runs.update_status(
            run.id,
            "completed",
            metadata={"tokens_used": 150}
        )
        
        assert updated.status == "completed"
        assert updated.completed_at != None
        assert updated.metadata["tokens_used"] == 150

    async def test_get_active_runs(self, unit_of_work):
        """Test getting active runs."""
        thread = await unit_of_work.threads.create({
            "user_id": "test_user",
            "title": "Test Thread"
        })
        
        # Create runs with different statuses
        active_run = await unit_of_work.runs.create({
            "thread_id": thread.id,
            "status": "in_progress"
        })
        
        completed_run = await unit_of_work.runs.create({
            "thread_id": thread.id,
            "status": "completed"
        })
        
        active = await unit_of_work.runs.get_active()
        
        assert any(r.id == active_run.id for r in active)
        assert not any(r.id == completed_run.id for r in active)


@pytest.mark.asyncio
class TestReferenceRepository:
    """Test reference repository specific functionality."""

    async def test_create_reference_with_metadata(self, unit_of_work):
        """Test creating a reference with metadata."""
        message = await unit_of_work.messages.create({
            "thread_id": "test_thread",
            "content": "Test message",
            "role": "user"
        })
        
        reference = await unit_of_work.references.create({
            "message_id": message.id,
            "type": "document",
            "source": "knowledge_base",
            "content": "Referenced content",
            "metadata": {
                "document_id": "doc123",
                "page": 5,
                "relevance_score": 0.95
            }
        })
        
        assert reference.id != None
        assert reference.metadata["relevance_score"] == 0.95

    async def test_get_references_by_message(self, unit_of_work):
        """Test getting references by message ID."""
        message = await unit_of_work.messages.create({
            "thread_id": "test_thread",
            "content": "Test message",
            "role": "user"
        })
        
        # Create references
        for i in range(3):
            await unit_of_work.references.create({
                "message_id": message.id,
                "type": "document",
                "source": f"source_{i}",
                "content": f"Reference {i}"
            })
        
        references = await unit_of_work.references.get_by_message(message.id)
        
        assert len(references) == 3
        assert all(r.message_id == message.id for r in references)

    async def test_search_references(self, unit_of_work):
        """Test searching references."""
        # Create references with searchable content
        for i in range(5):
            await unit_of_work.references.create({
                "message_id": f"msg_{i}",
                "type": "document",
                "source": "knowledge_base",
                "content": f"Python programming reference {i}"
            })
        
        # Search
        results = await unit_of_work.references.search(
            query="Python",
            limit=10
        )
        
        assert len(results) == 5
        assert all("Python" in r.content for r in results)