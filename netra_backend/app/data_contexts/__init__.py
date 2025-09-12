"""
Netra Data Contexts - User-Scoped Data Operations

This module provides user-scoped data contexts that wrap ClickHouse and Redis
operations with proper user isolation. Each context ensures that all operations
are automatically namespaced by user_id to prevent data leakage.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Data-level user isolation for security and compliance
- Value Impact: Complete elimination of cross-user data contamination
- Revenue Impact: Enables enterprise deployment with strict data governance

Key Contexts:
- UserDataContext: Base class for user-scoped data operations
- UserClickHouseContext: ClickHouse operations with user isolation
- UserRedisContext: Redis operations with user namespacing
"""

from netra_backend.app.data_contexts.user_data_context import (
    UserDataContext,
    UserClickHouseContext,
    UserRedisContext
)

__all__ = [
    "UserDataContext",
    "UserClickHouseContext", 
    "UserRedisContext"
]