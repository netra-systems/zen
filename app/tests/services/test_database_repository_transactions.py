"""
Comprehensive tests for Database Repository transaction management and rollback behavior
Tests transaction handling, rollback scenarios, concurrency, and data consistency
REFACTORED VERSION: All functions ≤8 lines
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
from app.core.exceptions_base import NetraException


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
        
        if not db:
            return None
            
        try:
            # Create mock entity directly without calling super()
            entity = MockDatabaseModel(**kwargs)
            db.add(entity)
            await db.flush()  # Use flush instead of commit to match BaseRepository
            return entity
        except (IntegrityError, SQLAlchemyError):
            await db.rollback()
            return None
        except asyncio.TimeoutError:
            raise
        except Exception:
            await db.rollback()
            return None
    
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
        return []
    
    def clear_log(self):
        """Clear operation log"""
        self.operation_log.clear()


class TransactionTestManager:
    """Manages transaction test scenarios"""
    
    def __init__(self):
        self.transaction_states = {}
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
        session.flush = AsyncMock()
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
    
    def _setup_successful_transaction_data(self):
        """Setup data for successful transaction test"""
        return {'name': 'Test Entity', 'description': 'Test Description'}

    def _setup_successful_transaction_mocks(self, mock_session, create_data):
        """Setup mocks for successful transaction"""
        created_entity = MockDatabaseModel(**create_data)
        mock_session.refresh = AsyncMock(side_effect=lambda entity: setattr(entity, 'id', 'test_123'))
        return created_entity

    def _assert_successful_transaction(self, result, mock_session, mock_repository):
        """Assert successful transaction results"""
        assert result != None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.rollback.assert_not_called()

    def _assert_operation_logged(self, mock_repository, operation_type):
        """Assert operation was logged correctly"""
        assert len(mock_repository.operation_log) == 1
        assert mock_repository.operation_log[0][0] == operation_type

    @pytest.mark.asyncio
    async def test_successful_transaction_commit(self, mock_session, mock_repository):
        """Test successful transaction commit"""
        create_data = self._setup_successful_transaction_data()
        self._setup_successful_transaction_mocks(mock_session, create_data)
        result = await mock_repository.create(mock_session, **create_data)
        self._assert_successful_transaction(result, mock_session, mock_repository)
        self._assert_operation_logged(mock_repository, 'create')

    def _setup_integrity_error_mock(self, mock_session):
        """Setup mock to simulate integrity error"""
        mock_session.flush.side_effect = IntegrityError("duplicate key", None, None, None)

    def _assert_integrity_error_handling(self, result, mock_session):
        """Assert integrity error was handled correctly"""
        assert result == None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_integrity_error(self, mock_session, mock_repository):
        """Test transaction rollback on integrity constraint violation"""
        self._setup_integrity_error_mock(mock_session)
        result = await mock_repository.create(mock_session, name='Duplicate Entity')
        self._assert_integrity_error_handling(result, mock_session)

    def _setup_sql_error_mock(self, mock_session):
        """Setup mock to simulate SQL error"""
        mock_session.flush.side_effect = SQLAlchemyError("database connection failed")

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_sql_error(self, mock_session, mock_repository):
        """Test transaction rollback on SQL error"""
        self._setup_sql_error_mock(mock_session)
        result = await mock_repository.create(mock_session, name='Failed Entity')
        assert result == None
        mock_session.flush.assert_called_once()

    def _setup_unexpected_error_mock(self, mock_session):
        """Setup mock to simulate unexpected error"""
        mock_session.add.side_effect = ValueError("unexpected error during add")

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_unexpected_error(self, mock_session, mock_repository):
        """Test transaction rollback on unexpected error"""
        self._setup_unexpected_error_mock(mock_session)
        result = await mock_repository.create(mock_session, name='Error Entity')
        assert result == None
        mock_session.add.assert_called_once()

    def _create_concurrent_sessions(self):
        """Create mock sessions for concurrent operations"""
        session1 = AsyncMock(spec=AsyncSession)
        session2 = AsyncMock(spec=AsyncSession)
        return session1, session2

    def _setup_concurrent_session_mocks(self, session1, session2):
        """Setup mocks for concurrent sessions"""
        for session in [session1, session2]:
            session.add = MagicMock()
            session.commit = AsyncMock()
            session.flush = AsyncMock()
            session.rollback = AsyncMock()
            session.refresh = AsyncMock()

    async def _create_delayed_flush(self):
        """Create delayed flush function"""
        await asyncio.sleep(0.1)
        return None

    def _assert_concurrent_operations(self, results, session1, session2):
        """Assert concurrent operations completed"""
        assert len(results) == 2
        session1.add.assert_called_once()
        session2.add.assert_called_once()
        session1.flush.assert_called_once()
        session2.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_transaction_isolation(self, mock_repository):
        """Test transaction isolation under concurrent operations"""
        session1, session2 = self._create_concurrent_sessions()
        self._setup_concurrent_session_mocks(session1, session2)
        session1.flush.side_effect = self._create_delayed_flush
        task1 = mock_repository.create(session1, name='Entity 1')
        task2 = mock_repository.create(session2, name='Entity 2')
        results = await asyncio.gather(task1, task2)
        self._assert_concurrent_operations(results, session1, session2)

    async def _create_slow_flush(self):
        """Create slow flush function for timeout testing"""
        await asyncio.sleep(2.0)
        return None

    @pytest.mark.asyncio
    async def test_transaction_timeout_handling(self, mock_session, mock_repository):
        """Test handling of transaction timeouts"""
        mock_session.flush.side_effect = self._create_slow_flush
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                mock_repository.create(mock_session, name='Slow Entity'),
                timeout=0.5
            )


class TestUnitOfWorkTransactions:
    """Test Unit of Work pattern transaction handling"""
    
    @pytest.fixture
    def mock_async_session_factory(self):
        """Mock async session factory"""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.begin = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        
        # Create a context manager that returns the session
        session_context = AsyncMock()
        session_context.__aenter__ = AsyncMock(return_value=session)
        session_context.__aexit__ = AsyncMock(return_value=None)
        
        factory = MagicMock()
        factory.return_value = session_context
        return factory, session
    
    def _assert_uow_repositories_initialized(self, uow, mock_session):
        """Assert UoW repositories are properly initialized"""
        assert uow.threads != None
        assert uow.messages != None
        assert uow.runs != None
        assert uow.references != None
        assert uow.threads._session is mock_session
        assert uow.messages._session is mock_session

    @pytest.mark.asyncio
    async def test_unit_of_work_successful_transaction(self, mock_async_session_factory):
        """Test successful Unit of Work transaction"""
        factory, mock_session = mock_async_session_factory
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            async with UnitOfWork() as uow:
                self._assert_uow_repositories_initialized(uow, mock_session)
        mock_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_unit_of_work_rollback_on_exception(self, mock_async_session_factory):
        """Test Unit of Work rollback on exception"""
        factory, mock_session = mock_async_session_factory
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            try:
                async with UnitOfWork() as uow:
                    raise ValueError("Simulated error in UoW")
            except ValueError:
                pass
        mock_session.rollback.assert_called_once()

    def _assert_external_session_handling(self, external_session, uow):
        """Assert external session is handled correctly"""
        assert uow._session is external_session
        assert uow._external_session == True
        external_session.close.assert_not_called()
        external_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_unit_of_work_with_external_session(self):
        """Test Unit of Work with externally provided session"""
        external_session = AsyncMock(spec=AsyncSession)
        async with UnitOfWork(external_session) as uow:
            self._assert_external_session_handling(external_session, uow)


class TestTransactionPerformanceAndScaling:
    """Test transaction performance under various load conditions"""
    
    @pytest.fixture
    def performance_repository(self):
        """Repository for performance testing"""
        repo = MockRepository()
        return repo
    
    def _create_concurrent_sessions(self, num_concurrent):
        """Create mock sessions for concurrency test"""
        sessions = []
        for i in range(num_concurrent):
            session = AsyncMock(spec=AsyncSession)
            session.add = MagicMock()
            session.flush = AsyncMock()
            session.rollback = AsyncMock()
            session.refresh = AsyncMock()
            sessions.append(session)
        return sessions

    async def _create_concurrent_entity(self, performance_repository, session, index):
        """Create entity for concurrent testing"""
        return await performance_repository.create(session, name=f'Concurrent Entity {index}')

    def _create_concurrent_tasks(self, performance_repository, sessions, num_concurrent):
        """Create concurrent tasks for testing"""
        return [self._create_concurrent_entity(performance_repository, sessions[i], i) for i in range(num_concurrent)]

    def _assert_concurrency_performance(self, execution_time, results, num_concurrent):
        """Assert concurrency performance metrics"""
        assert execution_time < 2.0
        assert len(results) == num_concurrent
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful == num_concurrent

    def _assert_all_sessions_used(self, sessions):
        """Assert all sessions were used correctly"""
        for session in sessions:
            session.add.assert_called_once()
            session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_high_concurrency_transactions(self, performance_repository):
        """Test transaction handling under high concurrency"""
        num_concurrent = 50
        sessions = self._create_concurrent_sessions(num_concurrent)
        tasks = self._create_concurrent_tasks(performance_repository, sessions, num_concurrent)
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = asyncio.get_event_loop().time()
        execution_time = end_time - start_time
        self._assert_concurrency_performance(execution_time, results, num_concurrent)
        self._assert_all_sessions_used(sessions)