"""Modern Execution Helpers for Supervisor Agent

Focused helper methods for modern execution patterns.
Keeps supervisor main file under 300 lines.

Business Value: Standardized execution patterns with 25-line function limit.
"""

from typing import Any, Dict

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SupervisorExecutionHelpers:
    """Helper methods for modern supervisor execution."""
    
    def __init__(self, supervisor_agent):
        self.supervisor = supervisor_agent
    
    async def run_supervisor_workflow(self, context: UserExecutionContext, run_id: str) -> UserExecutionContext:
        """Run supervisor workflow using secure user execution context."""
        # Extract user request from context metadata or agent_context
        user_request = context.agent_context.get('user_request', 'default_request')

        # Use secure context data for execution
        result = await self.supervisor.run(
            user_request,
            context.thread_id,
            context.user_id,
            run_id
        )

        # Return updated context (maintaining immutability)
        return context.create_child_context(
            operation_name="supervisor_workflow",
            additional_agent_context={"workflow_result": result.to_dict() if hasattr(result, 'to_dict') else str(result)}
        )
    
    async def handle_execution_failure(self, result: ExecutionResult, context: UserExecutionContext) -> None:
        """Handle execution failure with proper error handling."""
        logger.error(
            f"Supervisor execution failed for user {context.user_id}, thread {context.thread_id}: {result.error}",
            extra={"user_id": context.user_id, "thread_id": context.thread_id, "request_id": context.request_id}
        )
        # Could add fallback strategy here if needed
    
    async def execute_legacy_workflow(self, context: UserExecutionContext,
                                    run_id: str, stream_updates: bool) -> UserExecutionContext:
        """Legacy execution workflow adapted for secure user execution context."""
        flow_id = self._start_execution_flow(run_id)
        execution_data = self._extract_context_from_execution_context(context, run_id)
        updated_result = await self._execute_run_with_logging(flow_id, execution_data)
        return self._finalize_execution(flow_id, context, updated_result)
    
    def _start_execution_flow(self, run_id: str) -> str:
        """Start execution flow logging."""
        flow_id = self.supervisor.flow_logger.generate_flow_id()
        self.supervisor.flow_logger.start_flow(flow_id, run_id, 3)
        return flow_id
    
    def _extract_context_from_execution_context(self, context: UserExecutionContext, run_id: str) -> dict:
        """Extract execution context from secure user execution context."""
        return {
            "thread_id": context.thread_id,
            "user_id": context.user_id,
            "user_prompt": context.agent_context.get('user_request', ''),
            "run_id": run_id
        }
    
    async def _execute_run_with_logging(self, flow_id: str, context: dict) -> dict:
        """Execute run with flow logging."""
        self.supervisor.flow_logger.step_started(flow_id, "execute_run", "supervisor")
        updated_result = await self.supervisor.run(
            context["user_prompt"], context["thread_id"], context["user_id"], context["run_id"]
        )
        self.supervisor.flow_logger.step_completed(flow_id, "execute_run", "supervisor")
        return {"result": updated_result.to_dict() if hasattr(updated_result, 'to_dict') else str(updated_result)}
    
    def _finalize_execution(self, flow_id: str, context: UserExecutionContext, updated_result: dict) -> UserExecutionContext:
        """Finalize execution and create updated context."""
        # Create child context with execution results
        updated_context = context.create_child_context(
            operation_name="finalized_execution",
            additional_agent_context=updated_result
        )
        self.supervisor.flow_logger.complete_flow(flow_id)
        return updated_context