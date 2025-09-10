"""Connection Pool Module - Compatibility Layer

This module provides backward compatibility for connection pool handling.
Aliases existing connection pool functionality from db and core modules.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Maintain test compatibility while following SSOT principles
- Value Impact: Ensures existing tests continue to work without breaking changes
- Strategic Impact: Maintains system stability during module consolidation
"""

from netra_backend.app.database.postgresql_pool_manager import PostgreSQLPoolManager
from netra_backend.app.core.async_connection_pool import AsyncConnectionPool

# Create alias for backward compatibility - using the actual pool manager
ConnectionPool = PostgreSQLPoolManager

# Re-export all functionality
__all__ = [
    'ConnectionPool', 
    'PostgreSQLPoolManager', 
    'AsyncConnectionPool'
]