# Shim module for backward compatibility - REDIRECTS TO SINGLE SOURCE OF TRUTH
from netra_backend.app.db.database_manager import *

# DEPRECATED: Use netra_backend.app.database for SSOT compliance
import warnings
warnings.warn(
    "netra_backend.app.core.database is deprecated. Use 'from netra_backend.app.database import get_db' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import Database and AsyncDatabase for backward compatibility but with warning
from netra_backend.app.db.postgres_core import Database, AsyncDatabase
