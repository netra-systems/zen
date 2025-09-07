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
