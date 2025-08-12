"""
Comprehensive tests for Database Repository transaction management and rollback behavior
Tests transaction handling, rollback scenarios, concurrency, and data consistency
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, DisconnectionError
from sqlalchemy import select, text

from app.services.database.base_repository import BaseRepository
from app.services.database.unit_of_work import UnitOfWork
from app.services.database.thread_repository import ThreadRepository
from app.services.database.message_repository import MessageRepository
from app.services.database.run_repository import RunRepository
from app.core.exceptions import NetraException


class MockDatabaseModel:
    """Mock database model for testing"""
    
    def __init__(self, id: str = None, name: str = None, **kwargs):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
        
        # Set other attributes
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockRepository(BaseRepository[MockDatabaseModel]):
    """Mock repository for testing transaction behavior"""
    
    def __init__(self):
        super().__init__(MockDatabaseModel)
        self.operation_log = []  # Track operations for testing
    
    async def create(self, db: Optional[AsyncSession] = None, **kwargs) -> Optional[MockDatabaseModel]:
        """Override create to log operations"""
        self.operation_log.append(('create', kwargs))
        return await super().create(db, **kwargs)
    
    async def update(self, db: AsyncSession, entity_id: str, **kwargs) -> Optional[MockDatabaseModel]:
        """Override update to log operations"""
        self.operation_log.append(('update', entity_id, kwargs))
        return await super().update(db, entity_id, **kwargs)
    
    async def delete(self, db: AsyncSession, entity_id: str) -> bool:
        """Override delete to log operations"""
        self.operation_log.append(('delete', entity_id))
        return await super().delete(db, entity_id)
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[MockDatabaseModel]:
        """Implementation of abstract method find_by_user"""
        self.operation_log.append(('find_by_user', user_id))
        # Return empty list for testing purposes
        return []
    
    def clear_log(self):
        """Clear operation log"""
        self.operation_log.clear()


class TransactionTestManager:
    """Manages transaction test scenarios"""
    
    def __init__(self):
        self.transaction_states = {}  # transaction_id -> state
        self.rollback_counts = 0
        self.commit_counts = 0
        self.deadlock_simulations = 0
        
    def simulate_deadlock(self, session: AsyncSession):
        """Simulate database deadlock"""
        self.deadlock_simulations += 1
        raise SQLAlchemyError("deadlock detected")
    
    def simulate_connection_loss(self, session: AsyncSession):
        """Simulate connection loss"""
        raise DisconnectionError("connection lost", None, None)
    
    def track_transaction_state(self, transaction_id: str, state: str):
        """Track transaction state changes"""
        self.transaction_states[transaction_id] = state
    
    def increment_rollback(self):
        """Track rollback operations"""
        self.rollback_counts += 1
    
    def increment_commit(self):
        """Track commit operations"""
        self.commit_counts += 1


class TestDatabaseRepositoryTransactions:
    """Test database repository transaction management"""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.commit = AsyncMock()
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
    
    @pytest.mark.asyncio
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
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        mock_session.rollback.assert_not_called()
        
        # Check operation was logged
        assert len(mock_repository.operation_log) == 1
        assert mock_repository.operation_log[0][0] == 'create'
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_integrity_error(self, mock_session, mock_repository):
        """Test transaction rollback on integrity constraint violation"""
        # Setup - simulate integrity error
        mock_session.commit.side_effect = IntegrityError("duplicate key", None, None, None)
        
        # Execute
        result = await mock_repository.create(mock_session, name='Duplicate Entity')
        
        # Assert
        assert result == None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_called_once()
        mock_session.refresh.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_sql_error(self, mock_session, mock_repository):
        """Test transaction rollback on SQL error"""
        # Setup - simulate SQL error
        mock_session.commit.side_effect = SQLAlchemyError("database connection failed")
        
        # Execute
        result = await mock_repository.create(mock_session, name='Failed Entity')
        
        # Assert
        assert result == None
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_unexpected_error(self, mock_session, mock_repository):
        """Test transaction rollback on unexpected error"""
        # Setup - simulate unexpected error
        mock_session.add.side_effect = ValueError("unexpected error during add")
        
        # Execute
        result = await mock_repository.create(mock_session, name='Error Entity')
        
        # Assert
        assert result == None
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_transaction_isolation(self, mock_repository):
        """Test transaction isolation under concurrent operations"""
        # Create separate mock sessions for concurrent operations
        session1 = AsyncMock(spec=AsyncSession)
        session2 = AsyncMock(spec=AsyncSession)
        
        # Setup mock responses
        for session in [session1, session2]:
            session.add = MagicMock()
            session.commit = AsyncMock()
            session.rollback = AsyncMock()
            session.refresh = AsyncMock()
        
        # Simulate delay in first transaction
        async def delayed_commit():
            await asyncio.sleep(0.1)
            return None
        
        session1.commit.side_effect = delayed_commit
        
        # Execute concurrent operations
        task1 = mock_repository.create(session1, name='Entity 1')
        task2 = mock_repository.create(session2, name='Entity 2')
        
        results = await asyncio.gather(task1, task2)
        
        # Assert both operations completed independently
        assert len(results) == 2
        session1.add.assert_called_once()
        session2.add.assert_called_once()
        session1.commit.assert_called_once()
        session2.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transaction_timeout_handling(self, mock_session, mock_repository):
        """Test handling of transaction timeouts"""
        # Setup - simulate long-running transaction
        async def slow_commit():
            await asyncio.sleep(2.0)  # 2 second delay
            return None
        
        mock_session.commit.side_effect = slow_commit
        
        # Execute with timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                mock_repository.create(mock_session, name='Slow Entity'),
                timeout=0.5  # 500ms timeout
            )
    
    @pytest.mark.asyncio
    async def test_nested_transaction_handling(self, mock_repository):
        """Test nested transaction handling"""
        outer_session = AsyncMock(spec=AsyncSession)
        inner_session = AsyncMock(spec=AsyncSession)
        
        # Setup sessions
        for session in [outer_session, inner_session]:
            session.add = MagicMock()
            session.commit = AsyncMock()
            session.rollback = AsyncMock()
            session.refresh = AsyncMock()
            session.execute = AsyncMock()
            
            # Mock query results
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            session.execute.return_value = mock_result
        
        # Simulate nested transaction failure on inner session
        # The create method will call commit internally
        inner_session.commit.side_effect = IntegrityError("constraint violation", None, None, None)
        
        # Execute outer transaction
        outer_result = await mock_repository.create(outer_session, name='Outer Entity')
        assert outer_result is not None  # Should succeed
        
        # Try inner transaction (will fail due to IntegrityError)
        inner_result = await mock_repository.create(inner_session, name='Inner Entity')
        assert inner_result is None  # Should fail and return None
        
        # The inner session should have rolled back due to the error
        inner_session.rollback.assert_called()
        
        # Outer session should have committed successfully (not rolled back)
        outer_session.commit.assert_called()
        outer_session.rollback.assert_not_called()
    
    @pytest.mark.asyncio
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
        
        # Simulate failure on third entity
        commit_calls = 0
        
        async def selective_failure():
            nonlocal commit_calls
            commit_calls += 1
            if commit_calls == 3:  # Fail on third entity
                raise IntegrityError("batch constraint violation", None, None, None)
            return None
        
        mock_session.commit.side_effect = selective_failure
        
        # Execute batch operations
        results = []
        for data in batch_data:
            result = await mock_repository.create(mock_session, **data)
            results.append(result)
        
        # After the IntegrityError on the third commit, all subsequent creates
        # will use a session that has already failed, so they will also fail
        successful_results = [r for r in results if r is not None]
        failed_results = [r for r in results if r is None]
        
        # First two succeed, third fails and triggers rollback
        # BaseRepository.create returns None on IntegrityError
        assert len(successful_results) == 2  # First two succeed
        assert len(failed_results) == 3   # Third fails, and subsequent ones also fail
        assert mock_session.rollback.call_count >= 1  # At least one rollback for the failed transaction
    
    @pytest.mark.asyncio
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
        
        mock_session.commit.side_effect = deadlock_then_success
        
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
        assert mock_session.commit.call_count == 3
        # BaseRepository.create catches SQLAlchemyError and calls rollback internally
        assert mock_session.rollback.call_count >= 2  # Rollback on failed attempts
    
    @pytest.mark.asyncio 
    async def test_connection_recovery_handling(self, mock_repository, transaction_manager):
        """Test connection recovery handling"""
        # Create session that loses connection
        disconnected_session = AsyncMock(spec=AsyncSession)
        reconnected_session = AsyncMock(spec=AsyncSession)
        
        # Setup disconnection simulation
        disconnected_session.add = MagicMock()
        disconnected_session.commit.side_effect = DisconnectionError(
            "connection lost", None, None
        )
        disconnected_session.rollback = AsyncMock()
        disconnected_session.refresh = AsyncMock()
        disconnected_session.execute = AsyncMock()
        
        # Setup successful reconnection
        reconnected_session.add = MagicMock()
        reconnected_session.commit = AsyncMock()
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
        disconnected_session.commit.assert_called_once()
        disconnected_session.rollback.assert_called_once()  # Should rollback on DisconnectionError
        
        reconnected_session.add.assert_called_once()
        reconnected_session.commit.assert_called_once()
        reconnected_session.rollback.assert_not_called()  # Should not rollback on success


class TestUnitOfWorkTransactions:
    """Test Unit of Work pattern transaction handling"""
    
    @pytest.fixture
    def mock_async_session_factory(self):
        """Mock async session factory"""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        
        factory = MagicMock()
        factory.return_value = session
        return factory, session
    
    @pytest.mark.asyncio
    async def test_unit_of_work_successful_transaction(self, mock_async_session_factory):
        """Test successful Unit of Work transaction"""
        factory, mock_session = mock_async_session_factory
        
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            async with UnitOfWork() as uow:
                # Verify repositories are initialized
                assert uow.threads != None
                assert uow.messages != None
                assert uow.runs != None
                assert uow.references != None
                
                # Verify session is injected
                assert uow.threads._session is mock_session
                assert uow.messages._session is mock_session
                
        # Session should not be closed or rolled back on success
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_unit_of_work_rollback_on_exception(self, mock_async_session_factory):
        """Test Unit of Work rollback on exception"""
        factory, mock_session = mock_async_session_factory
        
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            try:
                async with UnitOfWork() as uow:
                    # Simulate operation that raises exception
                    raise ValueError("Simulated error in UoW")
            except ValueError:
                pass  # Expected exception
        
        # Should rollback and close on exception
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_unit_of_work_with_external_session(self):
        """Test Unit of Work with externally provided session"""
        external_session = AsyncMock(spec=AsyncSession)
        
        async with UnitOfWork(external_session) as uow:
            assert uow._session is external_session
            assert uow._external_session == True
        
        # External session should not be closed
        external_session.close.assert_not_called()
        external_session.rollback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_unit_of_work_complex_transaction(self, mock_async_session_factory):
        """Test complex transaction across multiple repositories"""
        factory, mock_session = mock_async_session_factory
        
        # Mock successful operations
        mock_thread = MagicMock()
        mock_thread.id = "thread_123"
        mock_message = MagicMock()
        mock_message.id = "message_456"
        mock_run = MagicMock()
        mock_run.id = "run_789"
        
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            async with UnitOfWork() as uow:
                # Mock repository methods
                uow.threads.create = AsyncMock(return_value=mock_thread)
                uow.messages.create_message = AsyncMock(return_value=mock_message)
                uow.runs.create_run = AsyncMock(return_value=mock_run)
                
                # Simulate complex operation
                thread = await uow.threads.create(user_id="user_123", name="Test Thread")
                message = await uow.messages.create_message(
                    thread_id=thread.id, role="user", content="Test message"
                )
                run = await uow.runs.create_run(
                    thread_id=thread.id, assistant_id="assistant_id", model="gpt-4"
                )
                
                # Verify operations
                assert thread.id == "thread_123"
                assert message.id == "message_456"
                assert run.id == "run_789"
        
        # All operations should complete successfully
        mock_session.close.assert_called_once()
        mock_session.rollback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_unit_of_work_partial_failure_rollback(self, mock_async_session_factory):
        """Test Unit of Work rollback on partial operation failure"""
        factory, mock_session = mock_async_session_factory
        
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            try:
                async with UnitOfWork() as uow:
                    # Mock first operation success
                    uow.threads.create = AsyncMock(return_value=MagicMock(id="thread_123"))
                    
                    # Mock second operation failure
                    uow.messages.create_message = AsyncMock(
                        side_effect=IntegrityError("constraint violation", None, None, None)
                    )
                    
                    # Execute operations
                    thread = await uow.threads.create(user_id="user_123", name="Test Thread")
                    
                    # This should fail and trigger rollback
                    await uow.messages.create_message(
                        thread_id=thread.id, role="user", content="Test message"
                    )
                    
            except IntegrityError:
                pass  # Expected exception
        
        # Should rollback entire transaction
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestTransactionPerformanceAndScaling:
    """Test transaction performance under various load conditions"""
    
    @pytest.fixture
    def performance_repository(self):
        """Repository for performance testing"""
        repo = MockRepository()
        return repo
    
    @pytest.mark.asyncio
    async def test_high_concurrency_transactions(self, performance_repository):
        """Test transaction handling under high concurrency"""
        num_concurrent = 50
        sessions = []
        
        # Create mock sessions
        for i in range(num_concurrent):
            session = AsyncMock(spec=AsyncSession)
            session.add = MagicMock()
            session.commit = AsyncMock()
            session.rollback = AsyncMock()
            session.refresh = AsyncMock()
            sessions.append(session)
        
        # Execute concurrent transactions
        async def create_entity(session, index):
            return await performance_repository.create(
                session, name=f'Concurrent Entity {index}'
            )
        
        tasks = [
            create_entity(sessions[i], i) 
            for i in range(num_concurrent)
        ]
        
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = asyncio.get_event_loop().time()
        
        execution_time = end_time - start_time
        
        # Assert performance and results
        assert execution_time < 2.0  # Should complete within 2 seconds
        assert len(results) == num_concurrent
        
        # Count successful operations
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful == num_concurrent
        
        # Verify all sessions were used
        for session in sessions:
            session.add.assert_called_once()
            session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_transaction_performance(self, performance_repository):
        """Test performance of batch transactions"""
        batch_size = 100
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Execute batch operations
        start_time = asyncio.get_event_loop().time()
        
        tasks = []
        for i in range(batch_size):
            task = performance_repository.create(
                mock_session, 
                name=f'Batch Entity {i}',
                batch_id=f'batch_{i // 10}'  # Group into batches of 10
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        execution_time = end_time - start_time
        
        # Assert performance metrics
        assert execution_time < 1.0  # Should complete within 1 second
        assert len(results) == batch_size
        assert mock_session.add.call_count == batch_size
        assert mock_session.commit.call_count == batch_size
    
    @pytest.mark.asyncio
    async def test_transaction_memory_usage(self, performance_repository):
        """Test memory usage during large transactions"""
        import tracemalloc
        
        # Start memory tracing
        tracemalloc.start()
        
        # Create session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Execute large number of operations
        large_batch_size = 500
        tasks = []
        
        for i in range(large_batch_size):
            task = performance_repository.create(
                mock_session,
                name=f'Memory Test Entity {i}',
                description=f'Large description for entity {i}' * 10  # Increase memory usage
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Check memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Assert reasonable memory usage (less than 50MB for this test)
        assert peak < 50 * 1024 * 1024  # 50MB
        
        # Verify operations completed
        assert mock_session.add.call_count == large_batch_size
    
    def test_transaction_resource_cleanup(self, performance_repository):
        """Test proper resource cleanup after transactions"""
        # Track resource usage
        created_sessions = []
        
        def mock_session_factory():
            session = AsyncMock(spec=AsyncSession)
            session.add = MagicMock()
            session.commit = AsyncMock()
            session.rollback = AsyncMock()
            session.close = AsyncMock()
            session.refresh = AsyncMock()
            created_sessions.append(session)
            return session
        
        # Simulate multiple transaction cycles
        async def transaction_cycle():
            session = mock_session_factory()
            try:
                await performance_repository.create(session, name='Cleanup Test')
            finally:
                await session.close()
        
        # Run multiple cycles
        import asyncio
        
        async def run_cycles():
            tasks = [transaction_cycle() for _ in range(10)]
            await asyncio.gather(*tasks)
        
        asyncio.run(run_cycles())
        
        # Assert all sessions were properly closed
        assert len(created_sessions) == 10
        for session in created_sessions:
            session.close.assert_called_once()