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


class TestUserData(UserInfo):
    """
    SSOT Test User Data Model - Supports both object and dict access patterns.
    
    Resolves the interface mismatch where tests expect user_data.id attribute access
    but receive dict format. This model provides:
    
    1. Object attribute access: user_data.id, user_data.email
    2. Dict-style access: user_data['id'], user_data['email'] 
    3. Backward compatibility with existing dict-based code
    4. Forward compatibility with dataclass-expecting code
    
    Business Value:
    - Enables Golden Path agent conversation sessions 
    - Prevents AttributeError: 'dict' object has no attribute 'id'
    - Standardizes user data format across test infrastructure
    
    Usage:
        # Object access (new pattern)
        user_data = TestUserData(id="123", email="test@example.com") 
        user_id = user_data.id  # Works
        
        # Dict access (backward compatibility)
        user_id = user_data['id']  # Also works
        
        # From dict conversion (existing integration tests)
        user_data = TestUserData.from_dict(dict_data)
    """
    # Additional test-specific fields
    hashed_password: Optional[str] = None
    plan_tier: str = "free"
    auth_provider: str = "test"
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        # Enable dict-style access for backward compatibility
        extra='allow'
    )
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TestUserData':
        """
        Create TestUserData from dict format (used by integration tests).
        
        Converts dict-based user data to TestUserData object supporting
        both attribute and dict access patterns.
        """
        # Handle datetime conversion if needed
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        return cls(
            id=str(data.get('id', '')),
            email=data.get('email', ''),
            full_name=data.get('name') or data.get('full_name'),
            picture=data.get('picture'),
            is_active=data.get('is_active', True),
            hashed_password=data.get('hashed_password'),
            plan_tier=data.get('plan_tier', 'free'),
            auth_provider=data.get('auth_provider', 'test'),
            created_at=created_at or datetime.now()
        )
    
    def __getitem__(self, key: str):
        """Enable dict-style access for backward compatibility."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"'{key}'")
    
    def __setitem__(self, key: str, value):
        """Enable dict-style assignment for backward compatibility."""
        setattr(self, key, value)
    
    def __contains__(self, key: str) -> bool:
        """Enable 'in' operator for dict-style checking."""
        return hasattr(self, key)
    
    def get(self, key: str, default=None):
        """Dict-style get method for backward compatibility."""
        return getattr(self, key, default)
    
    def keys(self):
        """Return all field names like dict.keys()."""
        return self.model_fields.keys()
    
    def values(self):
        """Return all field values like dict.values().""" 
        return [getattr(self, key) for key in self.keys()]
    
    def items(self):
        """Return all field items like dict.items()."""
        return [(key, getattr(self, key)) for key in self.keys()]