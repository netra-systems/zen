"""User type definitions - imports from single source of truth in registry.py"""

# Import all User types from single source of truth
# Additional types for compatibility
from typing import Optional
from pydantic import BaseModel

from netra_backend.app.schemas.registry import (
    User,
    UserBase,
    UserCreate,
    UserCreateOAuth,
)

# Import PlanTier as UserTier for compatibility with rate limiting tests
from netra_backend.app.schemas.user_plan import PlanTier as UserTier


class UserUpdate(BaseModel):
    """User update model."""
    email: Optional[str] = None
    full_name: Optional[str] = None
    picture: Optional[str] = None
    is_active: Optional[bool] = None


# Alias for backward compatibility
UserInDB = User