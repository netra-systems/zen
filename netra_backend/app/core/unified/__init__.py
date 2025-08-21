"""
Unified Core Components

Single Source of Truth implementations for common patterns across the Netra codebase.
This module eliminates code duplication by providing unified, well-tested implementations.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & System Stability
- Value Impact: Reduces maintenance overhead, improves reliability, accelerates development
- Strategic Impact: Eliminates technical debt, improves code quality metrics

Modules:
- jwt_validator: Unified JWT token validation and management
- db_connection_manager: Unified database connection and pool management
- retry_decorator: Unified retry logic with circuit breaker patterns
"""

from netra_backend.app.core.unified.jwt_validator import UnifiedJWTValidator, jwt_validator
from netra_backend.app.core.unified.db_connection_manager import UnifiedDatabaseManager, db_manager
from netra_backend.app.core.unified.retry_decorator import unified_retry, RetryConfig, RetryStrategy

__all__ = [
    'UnifiedJWTValidator',
    'jwt_validator', 
    'UnifiedDatabaseManager',
    'db_manager',
    'unified_retry',
    'RetryConfig', 
    'RetryStrategy'
]