"""Canonical User type definitions.

This provides base user types that can be extended by specific services.
Each service can have its own specialized User model that inherits from these base types.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field


class UserBase(BaseModel):
    """Base user model with core fields common across all user representations.
    
    This serves as the foundation for all user models in the system.
    Services can extend this for their specific needs.
    """
    email: EmailStr
    full_name: Optional[str] = None
    picture: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class UserInfo(BaseModel):
    """Minimal user information for API responses and inter-service communication.
    
    Use this for lightweight user data exchange where full user details aren't needed.
    """
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    picture: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    """User creation model with required fields for new user registration."""
    pass


class UserUpdate(UserBase):
    """User update model - all fields optional for partial updates."""
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class ExtendedUser(UserInfo):
    """Extended user model with additional fields for specialized use cases."""
    role: str
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime
    last_login: Optional[datetime] = None