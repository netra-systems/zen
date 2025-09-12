"""
User Context Factory - SSOT Import Alias for Existing Implementation

This module provides SSOT import compatibility by aliasing the existing
UserContextFactory implementation from the user execution context module.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Ensure proper user request isolation and context management
- Value Impact: Prevents data leakage between concurrent user requests
- Strategic Impact: Critical for multi-user system reliability and data security
"""

# SSOT Import: Use existing UserContextFactory from user execution context module
from netra_backend.app.services.user_execution_context import (
    UserContextFactory,
    UserExecutionContext,
    managed_user_context,
    create_isolated_execution_context,
    InvalidContextError,
    ContextIsolationError
)

# Export for test compatibility
__all__ = [
    'UserContextFactory',
    'UserExecutionContext',
    'managed_user_context',
    'create_isolated_execution_context',
    'InvalidContextError',
    'ContextIsolationError'
]