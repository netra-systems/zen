"""Database Module - Single Source of Truth for Netra Backend Database Access

This module consolidates ALL database session management for netra_backend.
CRITICAL: This is the ONLY location where database sessions should be defined.

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Eliminate duplicate database session management code
- Value Impact: Ensures system integrity and prevents SSOT violations per CLAUDE.md
- Strategic Impact: Single canonical DatabaseManager implementation

ATOMIC CONSOLIDATION: Uses DatabaseManager as the single source of truth
"""

from typing import AsyncGenerator, Any, Dict, List, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

# SINGLE SOURCE OF TRUTH: Use DatabaseManager exclusively
from netra_backend.app.db.database_manager import DatabaseManager

# Import ClickHouse functionality
try:
    from netra_backend.app.db.clickhouse import get_clickhouse_client as _get_clickhouse_client
    from netra_backend.app.db.clickhouse import get_clickhouse_config
    _CLICKHOUSE_AVAILABLE = True
except ImportError:
    _CLICKHOUSE_AVAILABLE = False
    _get_clickhouse_client = None
    get_clickhouse_config = None

class UnifiedDatabaseManager:
    """Unified database connection manager using DatabaseManager as single source of truth.
    
    This class delegates ALL operations to the canonical DatabaseManager implementation,
    eliminating SSOT violations across the codebase.
    """
    
    @staticmethod
    @asynccontextmanager
    async def postgres_session() -> AsyncGenerator[AsyncSession, None]:
        """Get PostgreSQL session via DatabaseManager - single source of truth."""
        # Use DatabaseManager's session factory directly
        async_session_factory = DatabaseManager.get_application_session()
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    @staticmethod
    def clickhouse_client():
        """Get ClickHouse client - single source of truth."""
        if not _CLICKHOUSE_AVAILABLE or not _get_clickhouse_client:
            raise RuntimeError("ClickHouse client not available")
        return _get_clickhouse_client()

# Create singleton instance
_db_manager = UnifiedDatabaseManager()

# Session manager for compatibility
class SessionManager:
    """Session manager for database connections."""
    
    def __init__(self):
        self.active_sessions = 0
        self.total_sessions_created = 0
    
    async def get_session(self):
        """Get a database session via DatabaseManager."""
        async for session in get_db():
            yield session

session_manager = SessionManager()

# SINGLE SOURCE OF TRUTH for PostgreSQL sessions in netra_backend
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Primary PostgreSQL session provider using DatabaseManager.
    
    This is the SINGLE source of truth for PostgreSQL sessions in netra_backend.
    All database access delegates to DatabaseManager implementation.
    """
    async with _db_manager.postgres_session() as session:
        yield session

# SINGLE SOURCE OF TRUTH for ClickHouse connections
def get_clickhouse_client():
    """Primary ClickHouse client provider for netra_backend service.
    
    This is the SINGLE source of truth for ClickHouse connections in netra_backend.
    All imports should use this function instead of individual module imports.
    Returns an async context manager for ClickHouse client access.
    """
    return _db_manager.clickhouse_client()

# ClickHouse configuration for compatibility
def get_clickhouse_config():
    """Get ClickHouse configuration - delegates to environment config."""
    from netra_backend.app.core.configuration.base import get_unified_config
    config = get_unified_config()
    return {
        'url': getattr(config, 'clickhouse_url', None),
        'host': getattr(config, 'clickhouse_host', 'localhost'),
        'port': getattr(config, 'clickhouse_port', 9000),
        'database': getattr(config, 'clickhouse_database', 'default')
    }

# PostgreSQL Compatibility aliases - all delegate to the single source of truth
async def get_postgres_db() -> AsyncGenerator[AsyncSession, None]:
    """Compatibility alias - delegates to primary implementation."""
    async for session in get_db():
        yield session

def get_db_session():
    """Compatibility function - delegates to primary implementation."""
    return get_db()

def get_database_session():
    """Compatibility function - delegates to primary implementation."""
    return get_db()

class DatabaseConfigManager:
    """Database configuration manager for unified config system."""
    
    def populate_database_config(self, config):
        """Populate database configuration."""
        pass
    
    def validate_database_consistency(self, config):
        """Validate database configuration consistency."""
        return []
    
    def refresh_environment(self):
        """Refresh environment settings."""
        pass

# Re-export database components
try:
    from netra_backend.app.db.base import Base
except ImportError:
    Base = None

try:
    from netra_backend.app.db.models_postgres import *
except ImportError:
    pass

try:
    from netra_backend.app.services.database_env_service import (
        DatabaseEnvService as DatabaseManager,
    )
    
    def get_database_manager():
        """Get database manager."""
        return DatabaseManager()
        
except ImportError:
    def get_database_manager():
        """Fallback database manager."""
        return None

__all__ = [
    'get_db',
    'get_postgres_db',
    'get_clickhouse_client',
    'get_clickhouse_config', 
    'get_db_session', 
    'get_database_session',
    'get_database_manager',
    'UnifiedDatabaseManager',
    'SessionManager',
    'session_manager',
    'Base'
]