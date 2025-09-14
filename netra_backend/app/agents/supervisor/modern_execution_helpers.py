"""Modern Execution Helpers for Supervisor Agent

Focused helper methods for modern execution patterns.
Keeps supervisor main file under 300 lines.

Business Value: Standardized execution patterns with 25-line function limit.
"""

from typing import Any, Dict

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SupervisorExecutionHelpers:
    """Helper methods for modern supervisor execution."""
    
    def __init__(self, supervisor_agent):
        self.supervisor = supervisor_agent
    
    async def run_supervisor_workflow(self, state: DeepAgentState, run_id: str) -> DeepAgentState:
        """Run supervisor workflow using legacy run method."""
        return await self.supervisor.run(
            state.user_request, 
            getattr(state, 'chat_thread_id', run_id),
            getattr(state, 'user_id', 'default_user'),
            run_id
        )
    
    async def handle_execution_failure(self, result: ExecutionResult, state: DeepAgentState) -> None:
        """Handle execution failure with proper error handling."""
        logger.error(f"Supervisor execution failed: {result.error}")
        # Could add fallback strategy here if needed
    
    async def execute_legacy_workflow(self, state: DeepAgentState, 
                                    run_id: str, stream_updates: bool) -> None:
        """Legacy execution workflow for backward compatibility."""
        flow_id = self._start_execution_flow(run_id)
        context = self._extract_context_from_state(state, run_id)
        updated_state = await self._execute_run_with_logging(flow_id, context)
        self._finalize_execution(flow_id, state, updated_state)
    
    def _start_execution_flow(self, run_id: str) -> str:
        """Start execution flow logging."""
        flow_id = self.supervisor.flow_logger.generate_flow_id()
        self.supervisor.flow_logger.start_flow(flow_id, run_id, 3)
        return flow_id
    
    def _extract_context_from_state(self, state: DeepAgentState, run_id: str) -> dict:
        """Extract execution context from state."""
        return {
            "thread_id": state.chat_thread_id or run_id,
            "user_id": state.user_id or "default_user",
            "user_prompt": state.user_request or "",
            "run_id": run_id
        }
    
    async def _execute_run_with_logging(self, flow_id: str, context: dict) -> DeepAgentState:
        """Execute run with flow logging."""
        self.supervisor.flow_logger.step_started(flow_id, "execute_run", "supervisor")
        updated_state = await self.supervisor.run(
            context["user_prompt"], context["thread_id"], context["user_id"], context["run_id"]
        )
        self.supervisor.flow_logger.step_completed(flow_id, "execute_run", "supervisor")
        return updated_state
    
    def _finalize_execution(self, flow_id: str, state: DeepAgentState, updated_state: DeepAgentState) -> None:
        """Finalize execution and merge states."""
        if updated_state:
            state = state.merge_from(updated_state)
        self.supervisor.flow_logger.complete_flow(flow_id)