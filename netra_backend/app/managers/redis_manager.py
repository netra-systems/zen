"""Redis Manager Compatibility Layer

This module provides backward compatibility for redis manager imports.
Redirects to the SSOT redis manager in the app module.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Maintain test compatibility while following SSOT principles
- Value Impact: Ensures existing tests continue to work without breaking changes
- Strategic Impact: Maintains system stability during module consolidation
"""

from netra_backend.app.redis_manager import (
    RedisManager,
    redis_manager,
    BackendEnvironment
)

# Re-export all functionality for backward compatibility
__all__ = [
    'RedisManager',
    'redis_manager',
    'BackendEnvironment'
]