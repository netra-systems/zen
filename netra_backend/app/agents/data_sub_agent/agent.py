"""
Data Sub-Agent - Backward Compatibility Module

This module provides backward compatibility for tests and imports that expect
the data_sub_agent.agent structure. Following SSOT principles, it imports
and re-exports the unified data agent instead of duplicating functionality.

The actual data implementation is in:
- netra_backend.app.agents.data.unified_data_agent (SSOT)
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

# Import SSOT implementations
from netra_backend.app.agents.data.unified_data_agent import (
    UnifiedDataAgent as DataAgent,
    UnifiedDataAgentFactory
)

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# Create aliases for backward compatibility with existing imports
class DataSubAgent(DataAgent):
    """
    Backward compatibility alias for UnifiedDataAgent.
    
    This class provides the same interface but uses the SSOT implementation
    from netra_backend.app.agents.data.unified_data_agent.
    """
    
    def __init__(self, 
                 llm_manager: 'LLMManager',
                 tool_dispatcher: 'UnifiedToolDispatcher',
                 context: Optional['UserExecutionContext'] = None,
                 execution_priority: int = 0):
        """Initialize data sub-agent using SSOT implementation."""
        super().__init__(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher,
            context=context,
            execution_priority=execution_priority
        )

# Factory function for creating data agents (backward compatibility)
def create_data_agent(
    context: 'UserExecutionContext',
    llm_manager: 'LLMManager', 
    tool_dispatcher: 'UnifiedToolDispatcher',
    websocket_bridge: Optional['AgentWebSocketBridge'] = None
) -> DataSubAgent:
    """
    Factory function for creating isolated data agents.
    
    This maintains backward compatibility while using the SSOT factory pattern.
    """
    # Create the agent using SSOT implementation
    return DataSubAgent(
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        context=context,
        execution_priority=0
    )

# Export public interface for backward compatibility
__all__ = [
    # Main classes
    "DataSubAgent",
    "DataAgent",  # Direct access to SSOT
    "UnifiedDataAgentFactory",
    "create_data_agent",
]