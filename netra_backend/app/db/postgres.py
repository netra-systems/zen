"""PostgreSQL database integration module.

Main module that imports and exposes functionality from focused sub-modules.
Maintains backward compatibility while adhering to modular architecture.
Now enhanced with resilience patterns for pragmatic rigor and degraded operation.
"""

from contextlib import asynccontextmanager

# Import SSOT configuration (Issue #1075 remediation)
from netra_backend.app.config import get_config

# Import core functionality
from netra_backend.app.db.postgres_core import (
    Database,
    async_engine,
    async_session_factory,
    get_converted_async_db_url,
    initialize_postgres,
)

# Import pool monitoring
from netra_backend.app.db.postgres_pool import close_async_db, get_pool_status

# Import session management
from netra_backend.app.db.postgres_session import (
    get_async_db,
    get_postgres_session,
    get_session_validation_error,
    validate_session,
)

# Alias for backward compatibility - AsyncSessionLocal
AsyncSessionLocal = async_session_factory

# Import resilience features
try:
    from netra_backend.app.db.postgres_resilience import (
        PostgresResilienceError,
        ReadOnlyModeError,
        postgres_resilience,
        resilient_postgres_session,
        with_postgres_resilience,
    )
    _RESILIENCE_AVAILABLE = True
except ImportError:
    _RESILIENCE_AVAILABLE = False
    postgres_resilience = None
    with_postgres_resilience = None
    resilient_postgres_session = None
    PostgresResilienceError = None
    ReadOnlyModeError = None

# Backward compatibility alias with resilience awareness
async def get_postgres_db():
    """Alias for get_async_db for backward compatibility.
    
    Uses resilient session if available, otherwise falls back to standard session.
    """
    # FIX: get_resilient_postgres_session() is an async context manager that yields once
    # Use async with, not async for
    async with get_resilient_postgres_session() as session:
        yield session

@asynccontextmanager
async def get_resilient_postgres_session():
    """Get PostgreSQL session with resilience patterns if available."""
    if _RESILIENCE_AVAILABLE and resilient_postgres_session:
        async with resilient_postgres_session() as session:
            yield session
    else:
        # Fallback to standard session
        async with get_async_db() as session:
            yield session

def get_postgres_resilience_status():
    """Get PostgreSQL resilience status and configuration."""
    if _RESILIENCE_AVAILABLE and postgres_resilience:
        return postgres_resilience.get_status()
    return {
        "resilience_available": False,
        "message": "PostgreSQL resilience module not available"
    }

# Re-export all functionality for backward compatibility
__all__ = [
    # Core functionality
    'Database',
    # DatabaseConfig removed - use netra_backend.app.config.get_config() instead (SSOT) 
    'async_engine',
    'async_session_factory',
    'AsyncSessionLocal',
    'get_converted_async_db_url',
    'initialize_postgres',
    
    # Session management
    'validate_session',
    'get_session_validation_error',
    'get_async_db',
    'get_postgres_db',
    'get_postgres_session',
    
    # Pool monitoring
    'get_pool_status',
    'close_async_db',
    
    # Resilience features (if available)
    'get_resilient_postgres_session',
    'get_postgres_resilience_status',
    'postgres_resilience',
    'with_postgres_resilience',
    'resilient_postgres_session',
    'PostgresResilienceError',
    'ReadOnlyModeError'
]