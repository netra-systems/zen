# Shim module for backward compatibility - REDIRECTS TO SINGLE SOURCE OF TRUTH
# DEPRECATED: Use netra_backend.app.database for SSOT compliance
import warnings
warnings.warn(
    "netra_backend.app.core.database is deprecated. Use 'from netra_backend.app.database import get_db' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export SSOT database functions for backward compatibility
from netra_backend.app.database import (
    get_db,
    get_system_db,
    get_database_url,
    get_engine,
    get_sessionmaker,
    DatabaseManager,
    database_manager
)

# Re-export Database and AsyncDatabase classes from postgres_core for backward compatibility
from netra_backend.app.db.postgres_core import (
    Database,
    AsyncDatabase
)

# Additional SSOT database utilities that tests might need
try:
    from netra_backend.app.db.postgres_core import (
        initialize_postgres,
        create_async_database,
        get_converted_async_db_url
    )
except ImportError:
    # These functions might not be available in all contexts
    pass

# Additional helper functions for test compatibility
def get_database_manager():
    """Get database manager instance for backward compatibility."""
    return database_manager

def get_db_session():
    """Alias for get_db for backward compatibility."""
    return get_db()
