"""Test thread repository operations to prevent regressions"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path

from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.db.models_postgres import Thread

# Add project root to path


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    mock = AsyncMock(spec=AsyncSession)
    mock.execute = AsyncMock()
    mock.add = MagicMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.refresh = AsyncMock()
    mock.flush = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def thread_repo():
    """Create a thread repository instance"""
    return ThreadRepository()
async def test_create_thread_success(mock_db, thread_repo):
    """Test successful thread creation"""
    # Setup
    test_thread_data = {
        'id': 'thread_test123',
        'object': 'thread',
        'created_at': 1234567890,
        'metadata_': {'user_id': 'test_user', 'title': 'Test Thread'}
    }
    
    # Mock refresh to simulate database returning the created object
    async def refresh_side_effect(obj):
        for key, value in test_thread_data.items():
            setattr(obj, key, value)
    
    mock_db.refresh.side_effect = refresh_side_effect
    
    # Execute
    result = await thread_repo.create(mock_db, **test_thread_data)
    
    # Verify
    assert result != None
    assert result.id == 'thread_test123'
    assert result.metadata_['title'] == 'Test Thread'
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()  # Repository uses flush, not commit
async def test_get_by_id_with_correct_parameter_order(mock_db, thread_repo):
    """Test get_by_id with correct parameter order (db first, then entity_id)"""
    # Setup
    mock_thread = Thread(
        id='thread_test123',
        object='thread',
        created_at=1234567890,
        metadata_={'user_id': 'test_user'}
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_thread
    mock_db.execute.return_value = mock_result
    
    # Execute - This is the critical test for parameter order
    result = await thread_repo.get_by_id(mock_db, 'thread_test123')
    
    # Verify
    assert result != None
    assert result.id == 'thread_test123'
    mock_db.execute.assert_called_once()
async def test_find_by_user(mock_db, thread_repo):
    """Test finding threads by user"""
    # Setup
    mock_threads = [
        Thread(id='thread_1', object='thread', created_at=1234567890, 
               metadata_={'user_id': 'user123'}),
        Thread(id='thread_2', object='thread', created_at=1234567891,
               metadata_={'user_id': 'user123'})
    ]
    
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_threads
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result
    
    # Execute
    result = await thread_repo.find_by_user(mock_db, 'user123')
    
    # Verify
    assert len(result) == 2
    assert result[0].id == 'thread_1'
    assert result[1].id == 'thread_2'
    mock_db.execute.assert_called_once()
async def test_archive_thread(mock_db, thread_repo):
    """Test archiving a thread"""
    # Setup
    mock_thread = Thread(
        id='thread_test123',
        object='thread',
        created_at=1234567890,
        metadata_={'user_id': 'test_user'}
    )
    
    # Mock get_by_id to return the thread
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_thread
    mock_db.execute.return_value = mock_result
    
    # Execute
    result = await thread_repo.archive_thread(mock_db, 'thread_test123')
    
    # Verify
    assert result == True
    assert mock_thread.metadata_['status'] == 'archived'
    assert 'archived_at' in mock_thread.metadata_
    mock_db.commit.assert_called_once()
async def test_parameter_order_regression():
    """
    Regression test to ensure get_by_id parameter order is correct.
    This test ensures that the db parameter comes first, then entity_id.
    """
    repo = ThreadRepository()
    
    # Get the method signature
    import inspect
    sig = inspect.signature(repo.get_by_id)
    params = list(sig.parameters.keys())
    
    # Verify parameter order (self is not included when inspecting instance methods)
    assert len(params) == 2, f"get_by_id must have exactly 2 parameters (db, entity_id), got {params}"
    assert params[0] == 'db', f"First parameter must be 'db', but got '{params[0]}'"
    assert params[1] == 'entity_id', f"Second parameter must be 'entity_id', but got '{params[1]}'"
    
    print("SUCCESS: Parameter order verified: get_by_id(self, db, entity_id)")


if __name__ == "__main__":
    # Run the regression test directly
    asyncio.run(test_parameter_order_regression())
    print("All parameter order tests passed!")