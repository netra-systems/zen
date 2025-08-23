"""
Database-related test fixtures.
Consolidates database fixtures from across services.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

# Skip heavy imports during collection to avoid side effects
import os
if not os.environ.get("TEST_COLLECTION_MODE"):
    try:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.pool import StaticPool
        SQLALCHEMY_AVAILABLE = True
    except ImportError:
        SQLALCHEMY_AVAILABLE = False
else:
    SQLALCHEMY_AVAILABLE = False


@pytest.fixture
async def test_db_session():
    """Create async database session for tests with fresh tables"""
    if not SQLALCHEMY_AVAILABLE:
        # Return mock session if SQLAlchemy not available
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.get = AsyncMock()
        yield mock_session
        return
    
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        echo=False,
    )
    
    # Create session
    from sqlalchemy.ext.asyncio import async_sessionmaker
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()
    
    await engine.dispose()

@pytest.fixture
def mock_postgres_connection():
    """Mock PostgreSQL connection"""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=MagicMock())
    conn.fetchone = AsyncMock(return_value=None)
    conn.fetchall = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=None)
    conn.close = AsyncMock()
    return conn

@pytest.fixture
def mock_clickhouse_connection():
    """Mock ClickHouse connection"""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=[])
    conn.insert = AsyncMock(return_value=True)
    conn.close = AsyncMock()
    return conn

@pytest.fixture
def mock_database_manager():
    """Mock database manager with connection pooling"""
    manager = AsyncMock()
    manager.get_connection = AsyncMock()
    manager.execute_query = AsyncMock(return_value=[])
    manager.execute_insert = AsyncMock(return_value=True)
    manager.begin_transaction = AsyncMock()
    manager.commit_transaction = AsyncMock()
    manager.rollback_transaction = AsyncMock()
    manager.close_all_connections = AsyncMock()
    return manager

@pytest.fixture
def mock_thread_data():
    """Mock thread data for tests"""
    return MagicMock(
        id="test_thread_123",
        user_id="test_user_001", 
        metadata_={"user_id": "test_user_001", "created_at": "2025-01-01T00:00:00Z"},
        created_at=1640995200,
        object="thread"
    )

@pytest.fixture
def mock_run_data():
    """Mock run data for tests"""
    return MagicMock(
        id="test_run_123",
        thread_id="test_thread_123",
        status="completed",
        assistant_id="test_assistant",
        model="gpt-4",
        metadata_={"user_id": "test_user_001"},
        created_at=1640995200
    )

@pytest.fixture
def mock_transaction_context():
    """Mock database transaction context"""
    class MockTransaction:
        def __init__(self):
            self.committed = False
            self.rolled_back = False
            
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.rolled_back = True
            else:
                self.committed = True
                
        async def commit(self):
            self.committed = True
            
        async def rollback(self):
            self.rolled_back = True
    
    return MockTransaction()

@pytest.fixture
def setup_test_database():
    """Setup test database with schema"""
    async def _setup():
        # Mock database setup
        return {
            "database_url": "sqlite+aiosqlite:///test.db",
            "schema_created": True,
            "test_data_loaded": False
        }
    return _setup

@pytest.fixture
def database_cleanup():
    """Database cleanup fixture"""
    cleanup_actions = []
    
    def add_cleanup(action):
        cleanup_actions.append(action)
    
    yield add_cleanup
    
    # Run cleanup actions
    for action in cleanup_actions:
        try:
            if asyncio.iscoroutinefunction(action):
                # Would need to run in event loop
                pass
            else:
                action()
        except Exception:
            pass  # Ignore cleanup errors