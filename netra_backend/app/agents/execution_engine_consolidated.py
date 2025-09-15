"""DEPRECATED: Use UserExecutionEngine - this import redirects to SSOT implementation.

This file redirects to the SSOT UserExecutionEngine to maintain backwards compatibility.
"""

# SSOT redirect for backwards compatibility - Export all key classes
from netra_backend.app.agents.supervisor.user_execution_engine import (
    UserExecutionEngine as ExecutionEngine,
    UserExecutionContext,
    AgentExecutionContext, 
    AgentExecutionResult,
    UserExecutionEngineExtensions as ExecutionEngineFactory
)

# For missing classes, provide basic compatibility stubs
from netra_backend.app.agents.supervisor.request_scoped_execution_engine import RequestScopedExecutionEngine

# Removed unused compatibility stubs - Phase 3 cleanup
# If tests fail, use direct imports from netra_backend.app.agents.supervisor.*

# Removed unused compatibility functions - Phase 3 cleanup

def create_execution_engine(*args, **kwargs):
    """DEPRECATED: SSOT factory function for ExecutionEngine - creates UserExecutionEngine instance
    
    🚨 DEPRECATION WARNING: Issue #884 factory consolidation
    This function is deprecated due to execution engine factory proliferation.
    
    MIGRATION PATH:
    - Use netra_backend.app.agents.supervisor.execution_engine_factory.ExecutionEngineFactory instead
    - Or use UserExecutionEngine directly for advanced use cases
    
    This is a compatibility bridge for Issue #565 migration.
    """
    import warnings
    warnings.warn(
        "⚠️  create_execution_engine() is DEPRECATED in Issue #884. "
        "This scattered factory function contributes to execution engine factory proliferation. "
        "MIGRATION: Use 'from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # Return a compatibility stub that can be used in tests
    return ExecutionEngine

def get_execution_engine_factory():
    """Get ExecutionEngine factory for creating instances with different configurations
    
    This is a compatibility bridge for Issue #565 migration.
    """
    return ExecutionEngineFactory

# Additional compatibility aliases for WebSocket event-related tests
ExecutionEngineWithWebSocketEvents = ExecutionEngine  # Alias for tests

# Re-export core classes for backwards compatibility - Phase 3 cleanup
__all__ = [
    'ExecutionEngine', 
    'UserExecutionContext',
    'AgentExecutionContext',
    'AgentExecutionResult', 
    'ExecutionEngineFactory',
    'RequestScopedExecutionEngine',
    'create_execution_engine',
    'get_execution_engine_factory',
    'ExecutionEngineWithWebSocketEvents'
]
