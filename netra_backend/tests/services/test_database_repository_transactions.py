"""
Tests for database repository transaction management.
All functions ≤8 lines per requirements.
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import DisconnectionError, IntegrityError, SQLAlchemyError

from app.core.exceptions import DatabaseError

# Add project root to path
from app.db.transaction_core import with_deadlock_retry
from .database_transaction_test_helpers import (
    MockDatabaseModel,
    assert_all_sessions_closed,
    configure_mock_query_results,
    # Add project root to path
    create_mock_session,
    create_tracked_session_factory,
    run_multiple_transaction_cycles,
)
from .database_transaction_test_mocks import (
    MockRepository,
    TransactionTestManager,
)


@pytest.fixture
def mock_session():
    """Create mock database session"""
    session = create_mock_session()
    configure_mock_query_results(session)
    return session


@pytest.fixture
def mock_repository():
    """Create mock repository for testing"""
    return MockRepository()


@pytest.fixture
def transaction_manager():
    """Create transaction test manager"""
    return TransactionTestManager()


class TestDatabaseRepositoryTransactions:
    """Test database repository transaction management"""
    
    async def test_successful_transaction_commit(self, mock_session, mock_repository):
        """Test successful transaction commit"""
        create_data = {'name': 'Test Entity', 'description': 'Test Description'}
        _setup_successful_creation(mock_session, create_data)
        
        result = await mock_repository.create(mock_session, **create_data)
        
        _assert_successful_transaction(result, mock_session, mock_repository)
    
    async def test_transaction_rollback_on_integrity_error(self, mock_session, mock_repository):
        """Test transaction rollback on integrity constraint violation"""
        _setup_integrity_error(mock_session)
        
        result = await mock_repository.create(mock_session, name='Duplicate Entity')
        
        _assert_rollback_on_error(result, mock_session)
    
    async def test_transaction_rollback_on_sql_error(self, mock_session, mock_repository):
        """Test transaction rollback on SQL error"""
        _setup_sql_error(mock_session)
        
        result = await mock_repository.create(mock_session, name='Error Entity')
        
        assert result is None
        mock_session.rollback.assert_called()
    
    async def test_concurrent_transaction_handling(self, mock_repository):
        """Test handling of concurrent transactions"""
        created_sessions = []
        session_factory = create_tracked_session_factory(created_sessions)
        
        await run_multiple_transaction_cycles(mock_repository, session_factory, count=5)
        
        assert_all_sessions_closed(created_sessions)
        assert len(created_sessions) == 5
    
    async def test_connection_loss_during_transaction(self, mock_session, mock_repository):
        """Test handling of connection loss during transaction"""
        _setup_connection_loss(mock_session)
        
        with pytest.raises(DisconnectionError):
            await mock_repository.create(mock_session, name='Connection Test')
    
    async def test_deadlock_detection_and_retry(self, mock_session, mock_repository, transaction_manager):
        """Test deadlock detection and retry logic"""
        transaction_manager.simulate_deadlock(mock_session)
        
        # Execute repository operation that should trigger deadlock
        result = await mock_repository.create(mock_session, name='Deadlock Test')
        
        # Should return None when deadlock occurs (error was handled)
        assert result is None
        
        # Verify session.rollback was called due to deadlock
        mock_session.rollback.assert_called()
        
        # Verify deadlock was detected and tracked
        stats = transaction_manager.get_transaction_stats()
        assert stats['deadlocks'] >= 1
    
    async def test_transaction_state_tracking(self, mock_repository, transaction_manager):
        """Test transaction state tracking"""
        transaction_id = "test_tx_123"
        transaction_manager.track_transaction_state(transaction_id, "STARTED")
        transaction_manager.track_transaction_state(transaction_id, "COMMITTED")
        
        assert transaction_manager.transaction_states[transaction_id] == "COMMITTED"
    
    async def test_repository_operation_logging(self, mock_session, mock_repository):
        """Test that repository operations are properly logged"""
        test_data = {'name': 'Logged Entity'}
        
        await mock_repository.create(mock_session, **test_data)
        await mock_repository.update(mock_session, "test_id", name="Updated")
        await mock_repository.delete(mock_session, "test_id")
        
        _assert_operation_logging(mock_repository)


def _setup_successful_creation(mock_session: AsyncMock, create_data: Dict[str, Any]) -> None:
    """Setup mock session for successful creation"""
    created_entity = MockDatabaseModel(**create_data)
    mock_session.refresh = AsyncMock(
        side_effect=lambda entity: setattr(entity, 'id', 'test_123')
    )


def _assert_successful_transaction(result, mock_session: AsyncMock, mock_repository) -> None:
    """Assert successful transaction completion"""
    assert result is not None
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    mock_session.rollback.assert_not_called()
    
    # Check operation was logged
    assert len(mock_repository.operation_log) == 1
    assert mock_repository.operation_log[0][0] == 'create'


def _setup_integrity_error(mock_session: AsyncMock) -> None:
    """Setup mock session to simulate integrity error"""
    mock_session.flush.side_effect = IntegrityError("duplicate key", None, None, None)


def _assert_rollback_on_error(result, mock_session: AsyncMock) -> None:
    """Assert rollback behavior on error"""
    assert result is None
    mock_session.add.assert_called_once()
    mock_session.rollback.assert_called()


def _setup_sql_error(mock_session: AsyncMock) -> None:
    """Setup mock session to simulate SQL error"""
    mock_session.flush.side_effect = SQLAlchemyError("database error")


def _setup_connection_loss(mock_session: AsyncMock) -> None:
    """Setup mock session to simulate connection loss"""
    mock_session.flush.side_effect = DisconnectionError("connection lost", None, None)


def _assert_operation_logging(mock_repository) -> None:
    """Assert operation logging functionality"""
    assert len(mock_repository.operation_log) == 3
    assert mock_repository.operation_log[0][0] == 'create'
    assert mock_repository.operation_log[1][0] == 'update'
    assert mock_repository.operation_log[2][0] == 'delete'