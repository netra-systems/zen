"""DEPRECATED - This file has been DEPRECATED as part of ExecutionEngine SSOT consolidation.

MIGRATION REQUIRED:
- Use UserExecutionEngine from netra_backend.app.agents.supervisor.user_execution_engine
- This file will be REMOVED in the next release

SECURITY FIX: Multiple ExecutionEngine implementations caused WebSocket user 
isolation vulnerabilities. UserExecutionEngine is now the SINGLE SOURCE OF TRUTH.
"""

# Import UserExecutionEngine as ExecutionEngine for backward compatibility
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine

# Legacy factory methods for backward compatibility
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    create_request_scoped_engine,
)
from netra_backend.app.agents.supervisor.user_execution_engine import (
    create_execution_context_manager,
    detect_global_state_usage
)

__all__ = [
    'ExecutionEngine',
    'create_request_scoped_engine', 
    'create_execution_context_manager',
    'detect_global_state_usage'
]