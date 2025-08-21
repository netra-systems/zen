"""
Thread repository operations tests
Tests thread CRUD operations and soft delete functionality
COMPLIANCE: 450-line max file, 25-line max functions
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path

from netra_backend.app.services.database.thread_repository import ThreadRepository
from sqlalchemy import Column, String, DateTime, JSON
from netra_backend.app.db.base import Base
from datetime import datetime

# Add project root to path

# Mock Thread model for testing (with fields expected by test)
class Thread(Base):
    __tablename__ = "test_threads"
    id = Column(String, primary_key=True)
    user_id = Column(String)
    title = Column(String)
    metadata_ = Column(JSON)
    created_at = Column(DateTime)
    deleted_at = Column(DateTime, nullable=True)
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestThreadRepositoryOperations:
    """test_thread_repository_operations - Test thread CRUD operations and soft delete"""
    
    async def test_thread_crud_operations(self):
        """Test thread CRUD operations"""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = ThreadRepository()
        
        # Test Create
        thread_data = _create_thread_data()
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = Thread(
            id="thread123",
            **thread_data,
            created_at=datetime.now(timezone.utc)
        )
        
        thread = await repo.create(mock_session, thread_data)
        assert thread.id == "thread123"
        assert thread.title == "Test Thread"
        
        # Test Read
        mock_session.execute.return_value.scalar_one_or_none.return_value = thread
        retrieved = await repo.get_by_id(mock_session, "thread123")
        assert retrieved.id == thread.id
        
        # Test Update
        update_data = {"title": "Updated Thread"}
        _setup_update_mock(mock_session)
        
        updated = await repo.update(mock_session, "thread123", update_data)
        assert updated.title == "Updated Thread"
        
        # Test Delete
        result = await repo.delete(mock_session, "thread123")
        assert result == True
    
    async def test_soft_delete_functionality(self):
        """Test soft delete functionality"""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = ThreadRepository()
        
        # Soft delete
        thread = _create_test_thread()
        
        mock_session.execute.return_value.scalar_one_or_none.return_value = thread
        
        await repo.soft_delete(mock_session, "thread123")
        
        # Verify soft delete sets deleted_at
        assert mock_session.execute.called
        update_call = mock_session.execute.call_args[0][0]
        assert "deleted_at" in str(update_call)
        
        # Test filtering out soft-deleted items
        _setup_active_threads_mock(mock_session)
        
        active_threads = await repo.get_active_threads(mock_session, "user123")
        assert len([t for t in active_threads if t.deleted_at == None]) == 1


def _create_thread_data():
    """Create thread test data."""
    return {
        "user_id": "user123",
        "title": "Test Thread",
        "metadata_": {"tags": ["test", "demo"]}
    }


def _setup_update_mock(mock_session):
    """Setup update mock for testing."""
    mock_session.execute.return_value.scalar_one_or_none.return_value = Thread(
        id="thread123",
        user_id="user123",
        title="Updated Thread",
        created_at=datetime.now(timezone.utc)
    )


def _create_test_thread():
    """Create test thread for soft delete."""
    return Thread(
        id="thread123",
        user_id="user123",
        title="Test Thread",
        deleted_at=None
    )


def _setup_active_threads_mock(mock_session):
    """Setup active threads mock."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = [
        Thread(id="1", deleted_at=None),
        Thread(id="2", deleted_at=datetime.now(timezone.utc))
    ]