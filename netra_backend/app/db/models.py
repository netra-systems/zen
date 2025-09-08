# Shim module for backward compatibility
from netra_backend.app.models import *

# Export SQLAlchemy Base class for database models
from netra_backend.app.db.base import Base
