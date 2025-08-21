"""
Token Models - DEPRECATED - USE app.schemas.auth_types INSTEAD

This module is now a compatibility wrapper that imports from the canonical source.
All new code should import directly from netra_backend.app.schemas.auth_types.
"""

# Import from canonical source
from netra_backend.app.schemas.auth_types import Token, TokenPayload

# Re-export for backward compatibility
__all__ = ["Token", "TokenPayload"]
