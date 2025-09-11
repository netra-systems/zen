"""
Database test fixtures module - Highly modular database testing utilities.

This module consolidates 70+ duplicate AsyncSession mock patterns into reusable,
modular components. Supports PostgreSQL and ClickHouse testing with transaction
management, query simulation, and error handling.

Business Value Justification (BVJ):
- Segment: Engineering efficiency
- Business Goal: Reduce database test complexity by 75%
- Value Impact: Consistent database testing patterns across 200+ test files
- Revenue Impact: Faster bug detection and fix cycles, improved code quality

All functions are ≤8 lines, file is ≤300 lines total.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from sqlalchemy.exc import DisconnectionError, IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

# === Core Session Mock Factories ===

@pytest.fixture
def async_session_mock():
    """Create standard AsyncSession mock with basic methods."""
    # Mock: Database session isolation for transaction testing without real database dependency
    session = AsyncMock(spec=AsyncSession)
    _setup_basic_session_methods(session)
    return session

def _setup_basic_session_methods(session: AsyncMock) -> None:
    """Setup core AsyncSession methods with defaults."""
    # Mock: Session isolation for controlled testing without external state
    session.add = MagicMock()
    # Mock: Session isolation for controlled testing without external state
    session.commit = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.rollback = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.close = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.refresh = AsyncMock(side_effect=_default_refresh)
    # Mock: Session isolation for controlled testing without external state
    session.execute = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.scalar = AsyncMock()

async def _default_refresh(entity: Any) -> None:
    """Default refresh behavior - adds ID if missing."""
    if hasattr(entity, 'id') and not entity.id:
        entity.id = f"mock_id_{uuid.uuid4().hex[:8]}"

@pytest.fixture
def transaction_session_mock():
    """Create AsyncSession mock with transaction capabilities."""
    # Mock: Database session isolation for transaction testing without real database dependency
    session = AsyncMock(spec=AsyncSession)
    _setup_transaction_methods(session)
    return session

def _setup_transaction_methods(session: AsyncMock) -> None:
    """Setup transaction-specific session methods."""
    _setup_basic_session_methods(session)
    # Mock: Session isolation for controlled testing without external state
    session.begin = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.flush = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.merge = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.expunge = MagicMock()

# === Query Result Simulators ===

class QueryResultBuilder:
    """Builds mock query results for different scenarios."""
    
    def __init__(self):
        self._results = []
    
    def with_single_result(self, entity: Any) -> 'QueryResultBuilder':
        """Add single result to query response."""
        # Mock: Generic component isolation for controlled unit testing
        result = Mock()
        result.scalars.return_value.first.return_value = entity
        result.scalar_one_or_none.return_value = entity
        self._results.append(result)
        return self
    
    def with_multiple_results(self, entities: List[Any]) -> 'QueryResultBuilder':
        """Add multiple results to query response."""
        # Mock: Generic component isolation for controlled unit testing
        result = Mock()
        result.scalars.return_value.all.return_value = entities
        result.scalars.return_value.first.return_value = entities[0] if entities else None
        self._results.append(result)
        return self
    
    def with_empty_result(self) -> 'QueryResultBuilder':
        """Add empty result to query response."""
        # Mock: Generic component isolation for controlled unit testing
        result = Mock()
        result.scalars.return_value.first.return_value = None
        result.scalars.return_value.all.return_value = []
        result.scalar_one_or_none.return_value = None
        self._results.append(result)
        return self
    
    def build(self) -> Mock:
        """Build final query result mock."""
        return self._results[0] if self._results else self.with_empty_result()._results[0]

@pytest.fixture
def query_builder():
    """Create query result builder instance."""
    return QueryResultBuilder()

# === Database Model Factories ===

def create_mock_user(**kwargs) -> Mock:
    """Create mock User model instance."""
    # Mock: Component isolation for controlled unit testing
    return Mock(
        id=kwargs.get('id', f"user_{uuid.uuid4().hex[:8]}"),
        email=kwargs.get('email', 'test@example.com'),
        full_name=kwargs.get('full_name', 'Test User'),
        hashed_password=kwargs.get('hashed_password', 'hashed_pwd'),
        is_active=kwargs.get('is_active', True)
    )

def create_mock_thread(**kwargs) -> Mock:
    """Create mock Thread model instance."""
    # Mock: Component isolation for controlled unit testing
    return Mock(
        id=kwargs.get('id', f"thread_{uuid.uuid4().hex[:8]}"),
        user_id=kwargs.get('user_id', 'test_user'),
        title=kwargs.get('title', 'Test Thread'),
        created_at=kwargs.get('created_at', datetime.now()),
        updated_at=kwargs.get('updated_at', datetime.now())
    )

def create_mock_message(**kwargs) -> Mock:
    """Create mock Message model instance."""
    # Mock: Component isolation for controlled unit testing
    return Mock(
        id=kwargs.get('id', f"msg_{uuid.uuid4().hex[:8]}"),
        thread_id=kwargs.get('thread_id', 'test_thread'),
        content=kwargs.get('content', 'Test message'),
        role=kwargs.get('role', 'user'),
        created_at=kwargs.get('created_at', datetime.now())
    )

# === Error Simulation Utilities ===

class DatabaseErrorSimulator:
    """Simulates various database error conditions."""
    
    def __init__(self, session: AsyncMock):
        self.session = session
    
    def simulate_integrity_error(self, operation: str = 'commit') -> None:
        """Configure session to raise IntegrityError."""
        error = IntegrityError("UNIQUE constraint failed", None, None)
        getattr(self.session, operation).side_effect = error
    
    def simulate_connection_error(self, operation: str = 'execute') -> None:
        """Configure session to raise DisconnectionError."""
        error = DisconnectionError("Connection lost", None, None)
        getattr(self.session, operation).side_effect = error
    
    def simulate_timeout_error(self, operation: str = 'commit') -> None:
        """Configure session to raise timeout error."""
        import asyncio
        getattr(self.session, operation).side_effect = asyncio.TimeoutError()

@pytest.fixture
def error_simulator(async_session_mock):
    """Create database error simulator."""
    return DatabaseErrorSimulator(async_session_mock)

# === Transaction Context Managers ===

class MockTransactionContext:
    """Mock transaction context manager for testing."""
    
    def __init__(self, session: AsyncMock, commit_behavior: str = 'success'):
        self.session = session
        self.commit_behavior = commit_behavior
        self._entered = False
    
    async def __aenter__(self):
        """Enter transaction context."""
        self._entered = True
        await self.session.begin()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction context with error handling."""
        if exc_type or self.commit_behavior == 'rollback':
            await self.session.rollback()
        else:
            await self.session.commit()
        self._entered = False

@pytest.fixture
def transaction_context(transaction_session_mock):
    """Create mock transaction context."""
    return MockTransactionContext(transaction_session_mock)

# === Connection Pool Simulators ===

class MockConnectionPool:
    """Mock database connection pool for testing."""
    
    def __init__(self, pool_size: int = 5):
        self.pool_size = pool_size
        self.active_connections = 0
        self._connections = []
    
    async def acquire(self) -> AsyncMock:
        """Acquire connection from pool."""
        if self.active_connections >= self.pool_size:
            raise Exception("Pool exhausted")
        
        # Mock: Database session isolation for transaction testing without real database dependency
        conn = AsyncMock(spec=AsyncSession)
        _setup_basic_session_methods(conn)
        self.active_connections += 1
        self._connections.append(conn)
        return conn
    
    async def release(self, connection: AsyncMock) -> None:
        """Release connection back to pool."""
        if connection in self._connections:
            self._connections.remove(connection)
            self.active_connections -= 1

@pytest.fixture
def connection_pool():
    """Create mock connection pool."""
    return MockConnectionPool()

# === ClickHouse Test Utilities ===

class ClickHouseQueryMocker:
    """Mock ClickHouse query execution and results."""
    
    def __init__(self):
        self.query_log = []
        self.results = {}
    
    def mock_query_result(self, query_pattern: str, result: Any) -> None:
        """Configure result for query pattern."""
        self.results[query_pattern] = result
    
    async def execute_query(self, query: str, params: Optional[Dict] = None):
        """Mock query execution with result lookup."""
        self.query_log.append((query, params))
        
        for pattern, result in self.results.items():
            if pattern in query:
                return result
        
        return []  # Default empty result

@pytest.fixture
def clickhouse_mocker():
    """Create ClickHouse query mocker."""
    return ClickHouseQueryMocker()

# === Batch Operation Helpers ===

def create_batch_insert_mock(session: AsyncMock, batch_size: int = 100) -> None:
    """Configure session for batch insert operations."""
    batches_committed = []
    
    async def mock_flush():
        """Track batch flushes."""
        batches_committed.append(len(session.add.call_args_list))
    
    session.flush.side_effect = mock_flush
    session.batch_committed = batches_committed

def create_bulk_result_set(count: int, factory: Callable) -> List[Any]:
    """Create bulk result set using model factory."""
    return [factory(id=f"bulk_{i}") for i in range(count)]

# === Migration Test Helpers ===

class MigrationTestHelper:
    """Helper for testing database migrations."""
    
    def __init__(self, session: AsyncMock):
        self.session = session
        self.schema_changes = []
    
    def simulate_schema_change(self, table: str, operation: str) -> None:
        """Simulate schema modification."""
        self.schema_changes.append((table, operation))
    
    def verify_migration_state(self, expected_changes: List[tuple]) -> bool:
        """Verify migration applied correctly."""
        return self.schema_changes == expected_changes

@pytest.fixture
def migration_helper(async_session_mock):
    """Create migration test helper."""
    return MigrationTestHelper(async_session_mock)

# === Alias for ClickHouse Connection Pool ===

@pytest.fixture
def clickhouse_connection_pool(connection_pool):
    """Alias for connection_pool fixture for ClickHouse compatibility."""
    return connection_pool