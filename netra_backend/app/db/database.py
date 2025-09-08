"""Database module - SSOT alias for base database functionality."""

from netra_backend.app.db.base import Base

# Re-export for backward compatibility
__all__ = ["Base"]