"""
Unified test fixtures package.
Organizes test fixtures by domain for easy reuse across services.
"""

from test_framework.fixtures.auth_fixtures import *
from test_framework.fixtures.database_fixtures import *  
from test_framework.fixtures.service_fixtures import *
from test_framework.fixtures.health import *
from test_framework.fixtures.real_services import *

# Import unified WebSocket mock fixtures
from test_framework.fixtures.websocket_manager_mock import *
from test_framework.fixtures.websocket_test_helpers import *

# Create ConfigManagerHelper stub for compatibility
class ConfigManagerHelper:
    """Stub for ConfigManagerHelper to maintain test compatibility."""
    def __init__(self, *args, **kwargs):
        pass
    
    def get_config(self, key: str, default=None):
        """Get configuration value with fallback to default."""
        return default
    
    def set_config(self, key: str, value):
        """Set configuration value (stub implementation)."""
        pass

# Create create_test_app stub for compatibility
def create_test_app():
    """
    Create test app stub for compatibility with existing tests.
    
    This provides a basic FastAPI app instance for tests that import
    create_test_app from test_framework.fixtures.
    """
    try:
        from fastapi import FastAPI
        app = FastAPI(title="Test App", version="1.0.0")
        
        @app.get("/")
        async def root():
            return {"message": "Test app"}
            
        @app.get("/health")
        async def health():
            return {"status": "ok"}
            
        return app
    except ImportError:
        # Fallback if FastAPI not available
        from unittest.mock import MagicMock
        return MagicMock()

# Import create_test_client from backend route helpers
try:
    from netra_backend.tests.helpers.route_test_helpers import create_test_client
except ImportError:
    # Fallback if route helpers are not available
    def create_test_client():
        """Fallback test client creator."""
        from unittest.mock import MagicMock
        return MagicMock()

# Add stub for missing fixtures
def create_test_deep_state():
    """Stub for create_test_deep_state fixture."""
    return {}

def create_test_thread_message():
    """Stub for create_test_thread_message fixture."""
    return {"id": "test_thread", "content": "test message"}

def create_test_user(tier: str = "free"):
    """
    Create test user fixture compatible with checkpoint recovery tests.
    
    Args:
        tier: User tier (free, enterprise, etc.)
        
    Returns:
        Object with id attribute for compatibility with existing tests
    """
    import uuid
    import time
    
    class TestUser:
        def __init__(self, user_id: str, tier: str):
            self.id = user_id
            self.tier = tier
            self.email = f"test_{tier}_{int(time.time())}@example.com"
            
    user_id = str(uuid.uuid4())
    return TestUser(user_id, tier)

def get_test_db_session():
    """
    Get test database session context manager.
    
    Provides compatibility layer for tests expecting get_test_db_session function.
    Delegates to the proper database fixture implementation.
    """
    try:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
        from sqlalchemy.pool import StaticPool
    except ImportError:
        # Return mock session if SQLAlchemy not available
        from unittest.mock import AsyncMock
        
        class MockSessionContext:
            async def __aenter__(self):
                mock_session = AsyncMock()
                mock_session.commit = AsyncMock()
                mock_session.rollback = AsyncMock()
                mock_session.close = AsyncMock()
                mock_session.add = AsyncMock()
                mock_session.execute = AsyncMock()
                mock_session.get = AsyncMock()
                return mock_session
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
                
        return MockSessionContext()
    
    class DatabaseSessionContext:
        def __init__(self):
            self.session = None
            self.engine = None
            
        async def __aenter__(self):
            # Use in-memory SQLite for tests
            self.engine = create_async_engine(
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
                async with self.engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            except ImportError:
                pass  # Models not available, skip table creation
            
            # Create session
            async_session_maker = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
            
            self.session = async_session_maker()
            return self.session
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            # Cleanup
            if self.session:
                try:
                    if exc_type:
                        await self.session.rollback()
                    else:
                        await self.session.commit()
                except Exception:
                    pass
                try:
                    await self.session.close()
                except Exception:
                    pass
                    
            if self.engine:
                try:
                    await self.engine.dispose()
                except Exception:
                    pass
                    
            # Force garbage collection for SQLite connections
            import gc
            gc.collect()
            
    return DatabaseSessionContext()

__all__ = [
    # Re-export all fixtures from submodules
    "ConfigManagerHelper",
    "create_test_app",
    "create_test_client",
    "create_test_deep_state", 
    "create_test_thread_message",
    "create_test_user",
    "get_test_db_session",
]