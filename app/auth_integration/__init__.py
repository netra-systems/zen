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
    require_permission,
    get_current_user,
    get_current_active_user,
    require_admin,
    require_developer
)

__all__ = [
    'DbDep',
    'get_db_dependency',
    'get_llm_manager',
    'ActiveUserDep',
    'DeveloperDep',
    'AdminDep',
    'require_permission',
    'get_current_user',
    'get_current_active_user',
    'require_admin',
    'require_developer'
]