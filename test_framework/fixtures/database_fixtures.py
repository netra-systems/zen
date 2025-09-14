from shared.isolated_environment import get_env
"""
Database-related test fixtures - Single Source of Truth for Test Database Sessions.

CRITICAL: This is the ONLY location where shared test database sessions should be defined.
Service-specific implementations should be removed and delegated to this module.

Business Value Justification (BVJ):
- Segment: Platform/Internal (test infrastructure)
- Business Goal: Eliminate duplicate test database session management
- Value Impact: Consistent test database handling across all services
- Strategic Impact: Single source of truth for test database patterns
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


# Skip heavy imports during collection to avoid side effects
import os
if not os.environ.get("TEST_COLLECTION_MODE"):
    try:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
        from sqlalchemy.pool import StaticPool
        SQLALCHEMY_AVAILABLE = True
    except ImportError:
        SQLALCHEMY_AVAILABLE = False
else:
    SQLALCHEMY_AVAILABLE = False


@pytest.fixture
async def test_db_session():
    """SINGLE SOURCE OF TRUTH for test database sessions across all services.
    
    Creates async database session for tests with fresh tables.
    All services should use this fixture instead of creating their own.
    """
    if not SQLALCHEMY_AVAILABLE:
        # Return mock session if SQLAlchemy not available
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.get = AsyncMock()
        try:
            yield mock_session
        finally:
            # Ensure mock session cleanup
            await mock_session.close()
        return
    
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        echo=False,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        pool_recycle=300
    )
    
    # Create tables if model is available
    try:
        from netra_backend.app.db.models_postgres import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except ImportError:
        pass  # Models not available, skip table creation
    
    # Create session with proper lifecycle management
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    session = None
    try:
        session = async_session_maker()
        yield session
    except Exception:
        if session:
            try:
                await session.rollback()
            except Exception:
                pass
        raise
    finally:
        # Comprehensive cleanup with error handling
        if session:
            try:
                await session.rollback()
            except Exception:
                pass
            try:
                await session.close()
            except Exception:
                pass
        
        # Proper engine cleanup
        try:
            await engine.dispose()
        except Exception:
            pass
        
        # Force garbage collection for SQLite connections
        import gc
        gc.collect()


@pytest.fixture
async def netra_backend_db_session():
    """Test database session specifically for netra_backend service.
    
    Delegates to the service's single source of truth implementation.
    """
    try:
        from netra_backend.app.database import get_db
        async with get_db() as session:
            try:
                yield session
            finally:
                # Enhanced cleanup with rollback and close
                if hasattr(session, 'rollback'):
                    try:
                        await session.rollback()
                    except Exception:
                        pass
                if hasattr(session, 'close'):
                    try:
                        await session.close()
                    except Exception:
                        pass
    except ImportError:
        # Fall back to mock session if netra_backend is not available
        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        try:
            yield mock_session
        finally:
            await mock_session.rollback()
            await mock_session.close()


@pytest.fixture  
async def auth_service_db_session():
    """Test database session specifically for auth_service.
    
    Delegates to the service's single source of truth implementation.
    """
    try:
        from auth_service.auth_core.database.connection import auth_db
        # Initialize if not already initialized
        if not auth_db._initialized:
            await auth_db.initialize()
        
        async with auth_db.get_session() as session:
            try:
                yield session
            finally:
                # Enhanced cleanup with proper error handling
                if hasattr(session, 'rollback'):
                    try:
                        await session.rollback()
                    except Exception:
                        pass
                if hasattr(session, 'close'):
                    try:
                        await session.close()
                    except Exception:
                        pass
    except ImportError:
        # Fall back to mock session if auth_service is not available
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()
        try:
            yield mock_session
        finally:
            await mock_session.rollback()
            await mock_session.close()

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
        model=LLMModel.GEMINI_2_5_FLASH.value,
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
async def database_cleanup():
    """Database cleanup fixture with async support"""
    cleanup_actions = []
    
    def add_cleanup(action):
        cleanup_actions.append(action)
    
    yield add_cleanup
    
    # Run cleanup actions
    for action in cleanup_actions:
        try:
            if asyncio.iscoroutinefunction(action):
                await action()
            else:
                action()
        except Exception:
            pass  # Ignore cleanup errors


def database_session_factory():
    """
    Factory function for creating database session managers.
    
    Returns:
        Callable that creates database sessions with transaction management
    """
    def _session_factory():
        """Create a mock database session factory for testing."""
        from test_framework.unified.auth_database_session import AuthDatabaseSessionTestManager
        return AuthDatabaseSessionTestManager()
    
    return _session_factory
