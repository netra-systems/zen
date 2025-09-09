"""
SSOT Re-export of UserExecutionContextFactory for core module compatibility.

This module provides a compatibility layer for integration tests that expect
UserExecutionContextFactory to be importable from netra_backend.app.core.user_context.

Following CLAUDE.md SSOT principles by creating proper aliases rather than
duplicating the UserExecutionContextFactory implementation.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & Test Reliability
- Value Impact: Ensures integration tests can run without import failures
- Strategic Impact: Critical for maintaining test coverage and development workflow
"""

# SSOT import from the actual implementation
from netra_backend.app.services.user_execution_context import UserExecutionContextFactory

# Re-export for backward compatibility
__all__ = [
    "UserExecutionContextFactory",
]