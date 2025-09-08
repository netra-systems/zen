"""
User Model: Compatibility Wrapper for Core User Model

This module provides backward compatibility for test imports that expect
netra_backend.app.models.user, redirecting to the canonical User model
defined in schemas.core_models.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Maintain test infrastructure stability
- Value Impact: Enable seamless imports without breaking existing test code
- Revenue Impact: Prevent test failures that could delay releases
"""

# Import User model from canonical source
from netra_backend.app.schemas.core_models import User, UserBase, UserCreate, UserCreateOAuth
from shared.session_management.user_session_manager import UserSession
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Stub classes for test compatibility
@dataclass
class UserPreferences:
    """Stub class for user preferences in tests"""
    theme: str = "light"
    language: str = "en"
    notifications: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.notifications is None:
            self.notifications = {"email": True, "push": True}

@dataclass  
class UserState:
    """Stub class for user state in tests"""
    last_active: Optional[datetime] = None
    session_count: int = 0
    preferences: Optional[UserPreferences] = None
    
    def __post_init__(self):
        if self.preferences is None:
            self.preferences = UserPreferences()

# Re-export for backward compatibility
__all__ = ["User", "UserBase", "UserCreate", "UserCreateOAuth", "UserSession", "UserPreferences", "UserState"]