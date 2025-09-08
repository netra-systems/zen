"""
Triage Sub-Agent - Backward Compatibility Module

This module provides backward compatibility for tests and imports that expect
the triage_sub_agent.agent structure. Following SSOT principles, it imports
and re-exports the unified triage agent instead of duplicating functionality.

The actual triage implementation is in:
- netra_backend.app.agents.triage.unified_triage_agent (SSOT)
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

# Import SSOT implementations
from netra_backend.app.agents.triage.unified_triage_agent import (
    UnifiedTriageAgent as TriageAgent,
    UnifiedTriageAgentFactory as TriageAgentFactory,
    TriageConfig
)

# Import models from SSOT location
from netra_backend.app.agents.triage.models import (
    Priority,
    Complexity,
    ExtractedEntities,
    UserIntent,
    ToolRecommendation,
    TriageResult,
    TriageMetadata,
    KeyParameters,
    SuggestedWorkflow
)

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# Create aliases for backward compatibility with existing imports
class TriageSubAgent(TriageAgent):
    """
    Backward compatibility alias for UnifiedTriageAgent.
    
    This class provides the same interface but uses the SSOT implementation
    from netra_backend.app.agents.triage.unified_triage_agent.
    """
    
    def __init__(self, 
                 llm_manager: 'LLMManager',
                 tool_dispatcher: 'ToolDispatcher',
                 context: Optional['UserExecutionContext'] = None,
                 execution_priority: int = 0):
        """Initialize triage sub-agent using SSOT implementation."""
        super().__init__(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher,
            context=context,
            execution_priority=execution_priority
        )

# Factory function for creating triage agents (backward compatibility)
def create_triage_agent(
    context: 'UserExecutionContext',
    llm_manager: 'LLMManager', 
    tool_dispatcher: 'ToolDispatcher',
    websocket_bridge: Optional['AgentWebSocketBridge'] = None
) -> TriageSubAgent:
    """
    Factory function for creating isolated triage agents.
    
    This maintains backward compatibility while using the SSOT factory pattern.
    """
    # Use the SSOT factory but return our compatibility wrapper
    unified_agent = TriageAgentFactory.create_for_context(
        context=context,
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        websocket_bridge=websocket_bridge
    )
    
    # Wrap in compatibility class
    return TriageSubAgent(
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        context=context,
        execution_priority=0
    )

# Export public interface for backward compatibility
__all__ = [
    # Main classes
    "TriageSubAgent",
    "TriageAgent",  # Direct access to SSOT
    "TriageAgentFactory",
    "TriageConfig",
    "create_triage_agent",
    
    # Models
    "Priority",
    "Complexity", 
    "ExtractedEntities",
    "UserIntent",
    "ToolRecommendation",
    "TriageResult",
    "TriageMetadata",
    "KeyParameters",
    "SuggestedWorkflow"
]