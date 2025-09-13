"""DEPRECATED: Use UserExecutionEngine - this import redirects to SSOT implementation.

MIGRATION REQUIRED:
- Use UserExecutionEngine from netra_backend.app.agents.supervisor.user_execution_engine
- This file will be REMOVED in the next release

SECURITY FIX: Multiple ExecutionEngine implementations caused WebSocket user 
isolation vulnerabilities. UserExecutionEngine is now the SINGLE SOURCE OF TRUTH.
"""

from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.supervisor.execution_engine_factory import create_request_scoped_engine

__all__ = ["ExecutionEngine", "create_request_scoped_engine"]