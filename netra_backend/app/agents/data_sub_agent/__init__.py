"""
Data Sub-Agent Module

Legacy module stub for backward compatibility with existing tests.
Functionality has been consolidated into the unified data agent.
"""

from typing import Any, Dict, Optional
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager

# Import models for backward compatibility
from netra_backend.app.agents.data_sub_agent.models import (
    AnomalyDetectionResponse,
    CorrelationAnalysis,
    DataAnalysisResponse,
    DataQualityMetrics,
    PerformanceInsights,
    PerformanceMetrics,
    UsageAnalysisResponse,
    UsagePattern,
)


class DataSubAgent(BaseAgent):
    """
    Data Sub-Agent for backward compatibility.
    
    This class provides minimal functionality for tests that still import DataSubAgent.
    The actual data analysis functionality has been consolidated into the unified agent system.
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: UnifiedToolDispatcher, 
                 websocket_manager: Optional[Any] = None):
        super().__init__(
            name="DataSubAgent", 
            description="Legacy data analysis agent for backward compatibility"
        )
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.websocket_manager = websocket_manager
    
    def _is_fallback_mode(self) -> bool:
        """Check if agent is running in fallback mode."""
        return self.llm_manager.enabled is False
    
    def _create_execution_context(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> Any:
        """Create execution context for backward compatibility."""
        from netra_backend.app.agents.base.interface import ExecutionContext
        return ExecutionContext(
            request_id=run_id,
            user_id=getattr(state, 'user_id', None),
            metadata={
                "agent_name": self.name,
                "state": state,
                "stream_updates": stream_updates
            }
        )
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if agent should handle this request."""
        return False  # Legacy agent, should not be used
    
    async def execute_core_logic(self, context: Any) -> Dict[str, Any]:
        """Execute core data analysis logic."""
        return {"data_analysis_result": "legacy_stub"}
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> Any:
        """Execute agent workflow."""
        return {"status": "completed", "result": "legacy_stub"}


__all__ = [
    "DataSubAgent",
    "AnomalyDetectionResponse",
    "CorrelationAnalysis", 
    "DataAnalysisResponse",
    "DataQualityMetrics",
    "PerformanceInsights",
    "PerformanceMetrics",
    "UsageAnalysisResponse", 
    "UsagePattern"
]