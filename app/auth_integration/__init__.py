"""
Dependency injection module for FastAPI endpoints.

This module provides dependency functions for authentication,
authorization, and other cross-cutting concerns.
"""

# Import from parent dependencies.py file for backward compatibility
from app.dependencies import DbDep, get_db_dependency, get_llm_manager

from .auth import (
    ActiveUserDep,
    DeveloperDep,
    AdminDep,
    ActiveUserWsDep,
    require_permission,
    get_current_user,
    get_current_active_user,
    get_current_user_optional,
    require_admin,
    require_developer,
    get_password_hash,
    verify_password,
    create_access_token,
    validate_token_jwt
)

__all__ = [
    'DbDep',
    'get_db_dependency',
    'get_llm_manager',
    'ActiveUserDep',
    'DeveloperDep',
    'AdminDep',
    'ActiveUserWsDep',
    'require_permission',
    'get_current_user',
    'get_current_active_user',
    'get_current_user_optional',
    'require_admin',
    'require_developer',
    'get_password_hash',
    'verify_password',
    'create_access_token',
    'validate_token_jwt'
]