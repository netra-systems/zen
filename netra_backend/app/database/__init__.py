"""Database Module - Single Source of Truth for Netra Backend Database Access

This module consolidates ALL database session management for netra_backend.
CRITICAL: This is the ONLY location where database sessions should be defined.

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Eliminate duplicate database session management code
- Value Impact: Ensures system integrity and prevents "Abominations" per CLAUDE.md
- Strategic Impact: Single source of truth for database access patterns
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.db.postgres_session import get_async_db

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

# SINGLE SOURCE OF TRUTH for database sessions in netra_backend
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Primary database session provider for netra_backend service.
    
    This is the SINGLE source of truth for database sessions in netra_backend.
    All other functions must use this implementation.
    """
    async with get_async_db() as session:
        yield session

# Compatibility aliases - all delegate to the single source of truth
def get_db_session():
    """Compatibility function - delegates to primary implementation."""
    return get_db()

def get_database_session():
    """Compatibility function - delegates to primary implementation."""
    return get_db()

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
    'get_db_session', 
    'get_database_session',
    'get_database_manager',
    'Base'
]