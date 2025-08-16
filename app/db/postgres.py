"""PostgreSQL database integration module.

Main module that imports and exposes functionality from focused sub-modules.
Maintains backward compatibility while adhering to modular architecture.
"""

# Import configuration
from .postgres_config import DatabaseConfig

# Import core functionality
from .postgres_core import (
    Database,
    async_engine,
    async_session_factory
)

# Import session management
from .postgres_session import (
    validate_session,
    get_session_validation_error,
    get_async_db,
    get_postgres_session
)

# Import pool monitoring
from .postgres_pool import (
    get_pool_status,
    close_async_db
)

# Re-export all functionality for backward compatibility
__all__ = [
    'Database',
    'DatabaseConfig',
    'async_engine',
    'async_session_factory',
    'validate_session',
    'get_session_validation_error',
    'get_async_db',
    'get_postgres_session',
    'get_pool_status',
    'close_async_db'
]