"""
SSOT Re-export of ExecutionEngine for core module compatibility.

This module provides a compatibility layer for integration tests that expect
ExecutionEngine to be importable from netra_backend.app.core.execution_engine.

Following CLAUDE.md SSOT principles by creating proper aliases rather than
duplicating the ExecutionEngine implementation.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & Test Reliability  
- Value Impact: Ensures integration tests can run without import failures
- Strategic Impact: Critical for maintaining test coverage and development workflow
"""

# SSOT import from the actual implementation
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine

# Re-export for backward compatibility
__all__ = [
    "ExecutionEngine",
]