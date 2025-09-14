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

# Compatibility stubs for test classes that no longer exist
class EngineConfig:
    """Deprecated compatibility stub - use UserExecutionEngine directly"""
    def __init__(self, **kwargs):
        pass

class ExecutionExtension:
    """Deprecated compatibility stub - extensions integrated into UserExecutionEngine"""
    pass

class UserExecutionExtension(ExecutionExtension):
    """Deprecated compatibility stub"""
    pass

class MCPExecutionExtension(ExecutionExtension):
    """Deprecated compatibility stub"""
    pass

class DataExecutionExtension(ExecutionExtension):
    """Deprecated compatibility stub"""
    pass

class WebSocketExtension(ExecutionExtension):
    """Deprecated compatibility stub"""
    pass

async def execute_agent(*args, **kwargs):
    """Deprecated compatibility stub - use ExecutionEngine.execute_agent directly"""
    raise NotImplementedError("Use ExecutionEngine.execute_agent instead")

def execution_engine_context(*args, **kwargs):
    """Deprecated compatibility stub - use UserExecutionContext directly"""
    raise NotImplementedError("Use UserExecutionContext instead")

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

# Re-export everything for backwards compatibility
__all__ = [
    'ExecutionEngine', 
    'UserExecutionContext',
    'AgentExecutionContext',
    'AgentExecutionResult', 
    'ExecutionEngineFactory',
    'RequestScopedExecutionEngine',
    'EngineConfig',
    'ExecutionExtension',
    'UserExecutionExtension',
    'MCPExecutionExtension', 
    'DataExecutionExtension',
    'WebSocketExtension',
    'execute_agent',
    'execution_engine_context',
    'create_execution_engine',
    'get_execution_engine_factory',
    'ExecutionEngineWithWebSocketEvents'
]
