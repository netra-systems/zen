"""Agent Error Handler Module.

DEPRECATED: This module has been replaced by the consolidated error handlers
in app.core.error_handlers. This file now provides backward compatibility.
"""

# Import from consolidated error handlers for backward compatibility
from app.core.error_handlers import AgentErrorHandler as ConsolidatedAgentErrorHandler
from app.core.error_handlers import global_agent_error_handler

# Maintain the original interface
AgentErrorHandler = ConsolidatedAgentErrorHandler

# Export the same interface for backward compatibility
__all__ = [
    'AgentErrorHandler',
    'global_agent_error_handler'
]