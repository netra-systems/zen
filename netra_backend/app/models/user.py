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

# Re-export for backward compatibility
__all__ = ["User", "UserBase", "UserCreate", "UserCreateOAuth"]