"""DEPRECATED: Use UserExecutionEngine from netra_backend.app.agents.supervisor.user_execution_engine

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
    'execution_engine_context'
]