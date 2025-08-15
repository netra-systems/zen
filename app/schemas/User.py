"""User type definitions - imports from single source of truth in registry.py"""

# Import all User types from single source of truth
from app.schemas.registry import UserBase, UserCreate, UserCreateOAuth, User

# Additional types for compatibility
from pydantic import BaseModel

class UserUpdate(UserBase):
    """User update model."""
    pass

# Alias for backward compatibility
UserInDB = User