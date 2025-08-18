"""
Comprehensive Database Mock Utilities Framework

Consolidates 80+ database mock patterns into modular, reusable components.
Supports PostgreSQL/ClickHouse testing with async operations, transactions,
repository patterns, and error simulation.

BVJ: Engineering efficiency - Reduce database test complexity by 80%
Module: ≤300 lines, Functions: ≤8 lines (MANDATORY)
"""

import pytest
import uuid
import asyncio
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Union, Callable, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, DisconnectionError


# === Core Session Mock Factories ===

def create_mock_session() -> AsyncMock:
    """Create standard AsyncSession mock with basic methods."""
    session = AsyncMock(spec=AsyncSession)
    _setup_session_methods(session)
    return session


def _setup_session_methods(session: AsyncMock) -> None:
    """Setup core AsyncSession methods with defaults."""
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock(side_effect=_add_mock_id)
    session.execute = AsyncMock()
    session.scalar = AsyncMock()


async def _add_mock_id(entity: Any) -> None:
    """Add mock ID to entity if missing."""
    if hasattr(entity, 'id') and not entity.id:
        entity.id = f"mock_{uuid.uuid4().hex[:8]}"


def with_transaction_support(session: AsyncMock) -> AsyncMock:
    """Add transaction capabilities to session mock."""
    session.begin = AsyncMock()
    session.flush = AsyncMock()
    session.merge = AsyncMock()
    session.expunge = MagicMock()
    return session


def with_query_results(session: AsyncMock, results: Dict[str, Any]) -> AsyncMock:
    """Configure query responses for session mock."""
    mock_result = Mock()
    _configure_result_mock(mock_result, results)
    session.execute.return_value = mock_result
    return session


def _configure_result_mock(mock_result: Mock, results: Dict[str, Any]) -> None:
    """Configure result mock with provided data."""
    mock_result.scalar_one_or_none.return_value = results.get('single')
    mock_result.scalars.return_value.all.return_value = results.get('multiple', [])
    mock_result.scalars.return_value.first.return_value = results.get('first')


# === SessionBuilder Pattern ===

class SessionBuilder:
    """Fluent interface for building database session mocks."""
    
    def __init__(self):
        self._session = create_mock_session()
        self._features = []
    
    def with_transactions(self) -> 'SessionBuilder':
        """Add transaction support."""
        with_transaction_support(self._session)
        self._features.append('transactions')
        return self
    
    def with_results(self, results: Dict[str, Any]) -> 'SessionBuilder':
        """Add query result configuration."""
        with_query_results(self._session, results)
        self._features.append('results')
        return self
    
    def with_repository_mocks(self) -> 'SessionBuilder':
        """Add repository mock patterns."""
        _setup_repository_patterns(self._session)
        self._features.append('repositories')
        return self
    
    def build(self) -> AsyncMock:
        """Build configured session mock."""
        return self._session


def _setup_repository_patterns(session: AsyncMock) -> None:
    """Setup common repository mock patterns."""
    session.get = AsyncMock()
    session.delete = AsyncMock()
    session.query = MagicMock()


# === Repository Mock Factories ===

def create_repository_mock(model_factory: Optional[Callable] = None) -> AsyncMock:
    """Create repository mock with standard CRUD operations."""
    repo = AsyncMock()
    _setup_crud_methods(repo, model_factory)
    return repo


def _setup_crud_methods(repo: AsyncMock, factory: Optional[Callable]) -> None:
    """Setup CRUD methods for repository mock."""
    repo.create = AsyncMock(side_effect=_mock_create(factory))
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])


def _mock_create(factory: Optional[Callable]) -> Callable:
    """Create entity using factory if provided."""
    async def create_entity(*args, **kwargs):
        if factory:
            return factory(**kwargs)
        return Mock(id=f"entity_{uuid.uuid4().hex[:8]}", **kwargs)
    return create_entity


# === Bulk Operations Support ===

def create_bulk_operations_mock(session: AsyncMock, batch_size: int = 100) -> None:
    """Configure session for bulk insert/update operations."""
    session.bulk_insert_mappings = AsyncMock()
    session.bulk_update_mappings = AsyncMock()
    session.bulk_save_objects = AsyncMock()
    session.bulk_batches = []
    session.bulk_batch_size = batch_size
    

# === Error Simulation Utilities ===

class DatabaseErrorSimulator:
    """Simulates database error conditions for testing."""
    
    def __init__(self, session: AsyncMock):
        self.session = session
    
    def integrity_error(self, operation: str = 'commit') -> None:
        """Configure IntegrityError for specified operation."""
        error = IntegrityError("Constraint failed", None, None)
        getattr(self.session, operation).side_effect = error
    
    def connection_error(self, operation: str = 'execute') -> None:
        """Configure DisconnectionError for specified operation."""
        error = DisconnectionError("Connection lost", None, None)
        getattr(self.session, operation).side_effect = error
    
    def timeout_error(self, operation: str = 'commit') -> None:
        """Configure timeout error for specified operation."""
        getattr(self.session, operation).side_effect = asyncio.TimeoutError()


# === ClickHouse Mock Support ===

class ClickHouseQueryMocker:
    """Mock ClickHouse query execution and results."""
    
    def __init__(self):
        self.query_log = []
        self.result_map = {}
    
    def mock_query(self, pattern: str, result: Any) -> None:
        """Configure result for query pattern."""
        self.result_map[pattern] = result
    
    async def execute(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute mock query with result lookup."""
        self.query_log.append((query, params))
        return self._find_result(query)
    
    def _find_result(self, query: str) -> Any:
        """Find matching result for query."""
        for pattern, result in self.result_map.items():
            if pattern in query:
                return result
        return []


# === Transaction Context Managers ===

class MockTransactionContext:
    """Mock transaction context for async operations."""
    
    def __init__(self, session: AsyncMock, auto_commit: bool = True):
        self.session = session
        self.auto_commit = auto_commit
        self._active = False
    
    async def __aenter__(self):
        """Enter transaction context."""
        self._active = True
        await self.session.begin()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction with commit/rollback handling."""
        if exc_type or not self.auto_commit:
            await self.session.rollback()
        else:
            await self.session.commit()
        self._active = False


# === Model Factories ===

def create_mock_user(**kwargs) -> Mock:
    """Create mock User model instance."""
    return Mock(id=kwargs.get('id', f"user_{uuid.uuid4().hex[:8]}"),
                email=kwargs.get('email', 'test@example.com'),
                full_name=kwargs.get('full_name', 'Test User'),
                is_active=kwargs.get('is_active', True),
                created_at=kwargs.get('created_at', datetime.now(UTC)))


def create_mock_thread(**kwargs) -> Mock:
    """Create mock Thread model instance."""
    return Mock(id=kwargs.get('id', f"thread_{uuid.uuid4().hex[:8]}"),
                user_id=kwargs.get('user_id', 'test_user'),
                title=kwargs.get('title', 'Test Thread'),
                created_at=kwargs.get('created_at', datetime.now(UTC)))


def create_mock_message(**kwargs) -> Mock:
    """Create mock Message model instance."""
    return Mock(id=kwargs.get('id', f"msg_{uuid.uuid4().hex[:8]}"),
                thread_id=kwargs.get('thread_id', 'test_thread'),
                content=kwargs.get('content', 'Test message'),
                role=kwargs.get('role', 'user'),
                created_at=kwargs.get('created_at', datetime.now(UTC)))


# === Pytest Fixtures ===

@pytest.fixture
def db_session():
    """Standard database session fixture."""
    return SessionBuilder().build()

@pytest.fixture
def transaction_session():
    """Database session with transaction support."""
    return SessionBuilder().with_transactions().build()

@pytest.fixture
def error_simulator(db_session):
    """Database error simulator fixture."""
    return DatabaseErrorSimulator(db_session)

@pytest.fixture
def clickhouse_mocker():
    """ClickHouse query mocker fixture."""
    return ClickHouseQueryMocker()

@pytest.fixture
def session_builder():
    """Session builder factory fixture."""
    return SessionBuilder

# === Helper Functions ===

def create_bulk_result_set(count: int, factory: Callable) -> List[Any]:
    """Generate bulk test data using model factory."""
    return [factory(id=f"bulk_{i}") for i in range(count)]

async def with_async_transaction(session: AsyncMock, operation: Callable) -> Any:
    """Execute operation within async transaction context."""
    async with MockTransactionContext(session):
        return await operation(session)

def assert_session_operations(session: AsyncMock, expected_calls: Dict[str, int]) -> None:
    """Assert expected database operations were called."""
    for operation, count in expected_calls.items():
        method = getattr(session, operation)
        assert method.call_count == count

def create_connection_pool_mock(pool_size: int = 5) -> Mock:
    """Create mock database connection pool."""
    pool = Mock()
    pool.acquire = AsyncMock(return_value=create_mock_session())
    pool.release = AsyncMock()
    return pool