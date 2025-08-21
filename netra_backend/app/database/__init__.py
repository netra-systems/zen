"""Database Module - Compatibility Layer

This module provides compatibility for imports that expect app.database
while the actual database implementation is in app.db and app.services.database.

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Ensure test compatibility and smooth imports
- Value Impact: Prevents import errors that would break CI/CD pipelines
- Strategic Impact: Maintains backward compatibility during system evolution
"""

# Re-export common database components for compatibility
from netra_backend.app.dependencies import get_db_dependency as get_db
from netra_backend.app.db.session import get_db_session
try:
    from netra_backend.app.db.base import Base
except ImportError:
    Base = None
try:
    from netra_backend.app.db.models_postgres import *
except ImportError:
    pass

# Re-export database management components
try:
    from netra_backend.app.services.database_env_service import DatabaseEnvService as DatabaseManager
    
    def get_database_session():
        """Compatibility function for getting database session."""
        return get_db()
        
    def get_database_manager():
        """Compatibility function for getting database manager."""
        return DatabaseManager()
        
except ImportError:
    # Fallback implementations
    def get_database_session():
        """Fallback database session."""
        return get_db()
        
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