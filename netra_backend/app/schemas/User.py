"""User type definitions - imports from single source of truth in registry.py"""

# Import all User types from single source of truth
# Additional types for compatibility
from pydantic import BaseModel

from netra_backend.app.schemas.registry import (
    User,
    UserBase,
    UserCreate,
    UserCreateOAuth,
)

# Import PlanTier as UserTier for compatibility with rate limiting tests
from netra_backend.app.schemas.UserPlan import PlanTier as UserTier


class UserUpdate(UserBase):
    """User update model."""
    pass


# Alias for backward compatibility
UserInDB = User