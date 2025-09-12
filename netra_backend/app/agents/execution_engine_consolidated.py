"""DEPRECATED: Use UserExecutionEngine from netra_backend.app.agents.supervisor.user_execution_engine

This file redirects to the SSOT UserExecutionEngine to maintain backwards compatibility.
"""

# SSOT redirect for backwards compatibility
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine

__all__ = ['ExecutionEngine']