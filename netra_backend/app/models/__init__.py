"""
Models Package: Compatibility Layer for Test Imports

This package provides backward compatibility for test code that expects
models to be imported from netra_backend.app.models, while maintaining
the canonical sources of truth in the schemas package.

All models are imported from their canonical sources to prevent duplication.
"""

from netra_backend.app.models.session import Session, SessionModel
from netra_backend.app.models.user import User, UserBase, UserCreate, UserCreateOAuth

__all__ = [
    "Session", 
    "SessionModel",
    "User",
    "UserBase", 
    "UserCreate", 
    "UserCreateOAuth"
]