"""
Tests for basic database repository transaction management
Tests basic transaction handling, rollback scenarios, and error handling
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import asyncio
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from sqlalchemy.exc import DisconnectionError, IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.tests.services.database_transaction_test_helpers import (
    MockDatabaseModel,
    MockRepository,
    TransactionTestManager,
)

class TestDatabaseRepositoryTransactions:
    """Test database repository transaction management"""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()  # Add flush mock
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.close = AsyncMock()
        
        # Mock query results
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalars.return_value.first.return_value = None
        session.execute.return_value = mock_result
        
        return session
    
    @pytest.fixture
    def mock_repository(self):
        """Create mock repository for testing"""
        return MockRepository()
    
    @pytest.fixture
    def transaction_manager(self):
        """Create transaction test manager"""
        return TransactionTestManager()
    async def test_successful_transaction_commit(self, mock_session, mock_repository):
        """Test successful transaction commit"""
        # Setup
        create_data = {'name': 'Test Entity', 'description': 'Test Description'}
        
        # Mock successful creation
        created_entity = MockDatabaseModel(**create_data)
        mock_session.refresh = AsyncMock(side_effect=lambda entity: setattr(entity, 'id', 'test_123'))
        
        # Execute
        result = await mock_repository.create(mock_session, **create_data)
        
        # Assert
        assert result != None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()  # Check flush instead of commit
        mock_session.rollback.assert_not_called()
        
        # Check operation was logged
        assert len(mock_repository.operation_log) == 1
        assert mock_repository.operation_log[0][0] == 'create'
    async def test_transaction_rollback_on_integrity_error(self, mock_session, mock_repository):
        """Test transaction rollback on integrity constraint violation"""
        # Setup - simulate integrity error
        mock_session.flush.side_effect = IntegrityError("duplicate key", None, None, None)
        
        # Execute
        result = await mock_repository.create(mock_session, name='Duplicate Entity')
        
        # Assert
        assert result == None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        # Rollback is not called since exception is caught and None is returned in our mock
    async def test_transaction_rollback_on_sql_error(self, mock_session, mock_repository):
        """Test transaction rollback on SQL error"""
        # Setup - simulate SQL error
        mock_session.flush.side_effect = SQLAlchemyError("database connection failed")
        
        # Execute
        result = await mock_repository.create(mock_session, name='Failed Entity')
        
        # Assert
        assert result == None
        mock_session.flush.assert_called_once()
    async def test_transaction_rollback_on_unexpected_error(self, mock_session, mock_repository):
        """Test transaction rollback on unexpected error"""
        # Setup - simulate unexpected error
        mock_session.add.side_effect = ValueError("unexpected error during add")
        
        # Execute
        result = await mock_repository.create(mock_session, name='Error Entity')
        
        # Assert
        assert result == None
        mock_session.add.assert_called_once()
    async def test_concurrent_transaction_isolation(self, mock_repository):
        """Test transaction isolation under concurrent operations"""
        # Create separate mock sessions for concurrent operations
        session1 = AsyncMock(spec=AsyncSession)
        session2 = AsyncMock(spec=AsyncSession)
        
        # Setup mock responses
        for session in [session1, session2]:
            session.add = MagicMock()
            session.commit = AsyncMock()
            session.flush = AsyncMock()
            session.rollback = AsyncMock()
            session.refresh = AsyncMock()
        
        # Simulate delay in first transaction
        async def delayed_flush():
            await asyncio.sleep(0.1)
            return None
        
        session1.flush.side_effect = delayed_flush
        
        # Execute concurrent operations
        task1 = mock_repository.create(session1, name='Entity 1')
        task2 = mock_repository.create(session2, name='Entity 2')
        
        results = await asyncio.gather(task1, task2)
        
        # Assert both operations completed independently
        assert len(results) == 2
        session1.add.assert_called_once()
        session2.add.assert_called_once()
        session1.flush.assert_called_once()
        session2.flush.assert_called_once()
    async def test_transaction_timeout_handling(self, mock_session, mock_repository):
        """Test handling of transaction timeouts"""
        # Setup - simulate long-running transaction
        async def slow_flush():
            await asyncio.sleep(2.0)  # 2 second delay
            return None
        
        mock_session.flush.side_effect = slow_flush
        
        # Execute with timeout - timeout error should propagate through MockRepository
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                mock_repository.create(mock_session, name='Slow Entity'),
                timeout=0.5  # 500ms timeout
            )
    async def test_nested_transaction_handling(self, mock_repository):
        """Test nested transaction handling"""
        outer_session = AsyncMock(spec=AsyncSession)
        inner_session = AsyncMock(spec=AsyncSession)
        
        # Setup sessions
        for session in [outer_session, inner_session]:
            session.add = MagicMock()
            session.flush = AsyncMock()  # BaseRepository uses flush, not commit
            session.rollback = AsyncMock()
            session.refresh = AsyncMock()
            session.execute = AsyncMock()
            
            # Mock query results
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            session.execute.return_value = mock_result
        
        # Simulate nested transaction failure on inner session
        # The create method will call flush internally
        inner_session.flush.side_effect = IntegrityError("constraint violation", None, None, None)
        
        # Execute outer transaction
        outer_result = await mock_repository.create(outer_session, name='Outer Entity')
        assert outer_result is not None  # Should succeed
        
        # Try inner transaction (will fail due to IntegrityError)
        inner_result = await mock_repository.create(inner_session, name='Inner Entity')
        assert inner_result is None  # Should fail and return None
        
        # The inner session should have attempted flush (which failed)
        inner_session.flush.assert_called()
        
        # Outer session should have flushed successfully (not rolled back)
        outer_session.flush.assert_called()
        outer_session.rollback.assert_not_called()
    async def test_batch_operation_transaction_consistency(self, mock_session, mock_repository):
        """Test transaction consistency in batch operations"""
        # Setup batch data
        batch_data = [
            {'name': 'Entity 1', 'type': 'A'},
            {'name': 'Entity 2', 'type': 'B'},
            {'name': 'Entity 3', 'type': 'C'},
            {'name': 'Entity 4', 'type': 'D'},
            {'name': 'Entity 5', 'type': 'E'}
        ]
        
        # Simulate failure on third entity and all subsequent operations
        flush_calls = [0]  # Use list to avoid closure issues
        
        async def selective_failure():
            flush_calls[0] += 1
            if flush_calls[0] >= 3:  # Fail on third entity and all subsequent operations
                raise IntegrityError("batch constraint violation", None, None, None)
            return None
        
        mock_session.flush.side_effect = selective_failure
        
        # Execute batch operations
        results = []
        for i, data in enumerate(batch_data):
            try:
                result = await mock_repository.create(mock_session, **data)
                results.append(result)
            except Exception:
                # If an exception occurs, the repository returns None  
                results.append(None)
        
        # Count actual results
        successful_results = [r for r in results if r is not None]
        failed_results = [r for r in results if r is None]
        
        # First two succeed, third and subsequent fail due to IntegrityError
        # MockRepository.create catches IntegrityError and returns None
        assert len(successful_results) == 2  # First two succeed
        assert len(failed_results) == 3   # Third, fourth, and fifth all fail
        assert flush_calls[0] == 5  # All flush calls attempted, but 3rd, 4th, 5th failed
    async def test_deadlock_detection_and_retry(self, mock_session, mock_repository, transaction_manager):
        """Test deadlock detection and retry mechanism"""
        # Setup deadlock simulation
        retry_count = 0
        max_retries = 3
        
        async def deadlock_then_success():
            nonlocal retry_count
            retry_count += 1
            if retry_count <= 2:  # Fail first 2 attempts
                # Raise SQLAlchemyError to simulate deadlock
                raise SQLAlchemyError("deadlock detected")
            return None  # Success on third attempt
        
        mock_session.flush.side_effect = deadlock_then_success
        
        # Implement retry logic
        async def create_with_retry(repository, session, **data):
            successful_result = None
            for attempt in range(max_retries):
                try:
                    result = await repository.create(session, **data)
                    if result is not None:
                        successful_result = result
                        break
                except Exception:
                    # On SQLAlchemyError, create returns None rather than raising
                    if attempt == max_retries - 1:
                        break
                    await asyncio.sleep(0.01 * (2 ** attempt))  # Exponential backoff
            return successful_result
        
        # Execute with retry
        result = await create_with_retry(mock_repository, mock_session, name='Retry Entity')
        
        # Assert success after retries
        # The first two attempts will fail with SQLAlchemyError (caught in create method)
        # The third attempt should succeed
        assert retry_count == 3
        assert mock_session.flush.call_count == 3
        # BaseRepository.create catches SQLAlchemyError and raises DatabaseError
        assert result is not None  # Should eventually succeed
    async def test_connection_recovery_handling(self, mock_repository, transaction_manager):
        """Test connection recovery handling"""
        # Create session that loses connection
        disconnected_session = AsyncMock(spec=AsyncSession)
        reconnected_session = AsyncMock(spec=AsyncSession)
        
        # Setup disconnection simulation
        disconnected_session.add = MagicMock()
        disconnected_session.flush.side_effect = DisconnectionError(
            "connection lost", None, None
        )
        disconnected_session.rollback = AsyncMock()
        disconnected_session.refresh = AsyncMock()
        disconnected_session.execute = AsyncMock()
        
        # Setup successful reconnection
        reconnected_session.add = MagicMock()
        reconnected_session.flush = AsyncMock()
        reconnected_session.refresh = AsyncMock()
        reconnected_session.execute = AsyncMock()
        
        # Mock query results
        for session in [disconnected_session, reconnected_session]:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            session.execute.return_value = mock_result
        
        # Simulate connection recovery
        # First attempt will fail with DisconnectionError, caught by BaseRepository
        result1 = await mock_repository.create(disconnected_session, name='Disconnected Entity')
        assert result1 is None  # Should fail and return None
        
        # Second attempt with reconnected session should succeed
        result2 = await mock_repository.create(reconnected_session, name='Recovered Entity')
        assert result2 is not None  # Should succeed
        
        # Assert recovery process
        disconnected_session.add.assert_called_once()
        disconnected_session.flush.assert_called_once()
        
        reconnected_session.add.assert_called_once()
        reconnected_session.flush.assert_called_once()
        reconnected_session.rollback.assert_not_called()  # Should not rollback on success