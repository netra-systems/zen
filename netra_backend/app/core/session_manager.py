"""
Session Manager Module - Compatibility Layer for Integration Tests

This module provides a compatibility layer for integration tests that expect
a session manager in the core directory. It re-exports the actual implementation.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for integration tests
- Re-exports SSOT implementation from database.session_manager
- DO NOT add new functionality here - extend the SSOT module instead

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Stability
- Value Impact: Enables integration test collection and execution
- Strategic Impact: Maintains test coverage during system evolution
"""

# Re-export from the SSOT implementation
from netra_backend.app.core.database.session_manager import (
    DatabaseSessionManager,
    SessionManager,
    session_manager,
    managed_session,
    validate_agent_session_isolation,
    SessionIsolationError,
    SessionScopeValidator,
)

# Re-export for backward compatibility
__all__ = [
    "DatabaseSessionManager",
    "SessionManager",
    "session_manager",
    "managed_session",
    "validate_agent_session_isolation",
    "SessionIsolationError",
    "SessionScopeValidator",
]