"""Shared type definitions - Single Source of Truth for common types.

This module provides canonical type definitions to prevent SSOT violations
across the codebase. All services should import from here rather than
defining duplicate types.
"""

from .performance_metrics import PerformanceMetrics
from .user_types import UserBase, UserInfo, UserCreate, UserUpdate, ExtendedUser

__all__ = [
    "PerformanceMetrics", 
    "UserBase",
    "UserInfo",
    "UserCreate", 
    "UserUpdate",
    "ExtendedUser"
]