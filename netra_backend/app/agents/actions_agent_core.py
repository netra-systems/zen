# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-24T09:40:00.000000+00:00
# Agent: Claude Sonnet 4
# Context: Split large agent into focused modules following SRP
# Git: critical-remediation-20250823 | Boundary compliance refactoring
# Change: Refactor | Scope: Module | Risk: Medium
# Session: boundary-remediation | Seq: 1
# Review: Pending | Score: TBD
# ================================
from typing import Any, Dict

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.interface import (
    ExecutionContext,
)
from netra_backend.app.agents.input_validation import validate_agent_input
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger as logger

from netra_backend.app.agents.actions_agent_execution import ActionsAgentExecutionManager
from netra_backend.app.agents.actions_agent_llm import ActionsAgentLLMHandler
from netra_backend.app.agents.actions_agent_monitoring import ActionsAgentMonitoringService


class ActionsToMeetGoalsSubAgent(BaseSubAgent):
    """Refactored core agent following SRP - orchestrates focused sub-modules."""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        """Initialize with focused sub-modules."""
        self._initialize_base_classes(llm_manager)
        self.tool_dispatcher = tool_dispatcher
        self._setup_focused_modules()

    def _initialize_base_classes(self, llm_manager: LLMManager) -> None:
        """Initialize base classes for the agent."""
        BaseSubAgent.__init__(
            self, llm_manager, 
            name="ActionsToMeetGoalsSubAgent", 
            description="This agent creates a plan of action."
        )
        # Set properties for standardized execution patterns
        self.agent_name = "ActionsToMeetGoalsSubAgent"
        self.websocket_manager = None  # Will be set by registry if needed

    def _setup_focused_modules(self) -> None:
        """Setup focused module components following SRP."""
        self.execution_manager = ActionsAgentExecutionManager()
        self.monitoring_service = ActionsAgentMonitoringService()
        self.llm_handler = ActionsAgentLLMHandler(self.llm_manager)

    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions."""
        return self.execution_manager.validate_preconditions(context)

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core action plan generation logic."""
        return await self.execution_manager.execute_core_logic(
            context, self.monitoring_service, self.llm_handler
        )

    async def send_status_update(
        self, context: ExecutionContext, 
        status: str, message: str
    ) -> None:
        """Send status update via WebSocket."""
        await self.monitoring_service.send_status_update(context, status, message)

    @validate_agent_input('ActionsToMeetGoalsSubAgent')
    async def execute(
        self, state: DeepAgentState, 
        run_id: str, stream_updates: bool
    ) -> None:
        """Modernized execute using focused execution manager."""
        context = self._create_execution_context(state, run_id, stream_updates)
        await self.execution_manager.execute_with_fallback(context)

    def _create_execution_context(
        self, state: DeepAgentState, 
        run_id: str, stream_updates: bool
    ) -> ExecutionContext:
        """Create execution context for the request."""
        return ExecutionContext(
            run_id=run_id,
            agent_name=self.name,
            state=state,
            stream_updates=stream_updates,
            metadata={"description": self.description}
        )

    def get_health_status(self) -> dict:
        """Get comprehensive health status."""
        return {
            "agent": self.name,
            "execution": self.execution_manager.get_health_status(),
            "monitoring": self.monitoring_service.get_health_status(),
            "llm": self.llm_handler.get_health_status()
        }

    def get_performance_metrics(self) -> dict:
        """Get performance metrics."""
        return self.execution_manager.get_performance_metrics()

    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status."""
        return self.execution_manager.get_circuit_breaker_status()

    async def check_entry_conditions(
        self, state: DeepAgentState, run_id: str
    ) -> bool:
        """Check entry conditions for execution."""
        return self.execution_manager.check_entry_conditions(state, run_id)