"""Workflow Execution Helper for Supervisor Agent

Handles all workflow execution steps to reduce main supervisor file size.
Keeps methods under 8 lines each.

Business Value: Modular workflow execution with standardized patterns.
"""

from typing import Any, Dict, List

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import PipelineStep
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SupervisorWorkflowExecutor:
    """Helper class for supervisor workflow execution."""
    
    def __init__(self, supervisor_agent):
        self.supervisor = supervisor_agent
    
    async def execute_workflow_steps(self, flow_id: str, user_prompt: str, 
                                   thread_id: str, user_id: str, run_id: str) -> DeepAgentState:
        """Execute all workflow steps."""
        context = await self._create_context_step(flow_id, thread_id, user_id, run_id)
        state = await self._initialize_state_step(flow_id, user_prompt, thread_id, user_id, run_id)
        pipeline = await self._build_pipeline_step(flow_id, user_prompt, state)
        await self._execute_pipeline_step(flow_id, pipeline, state, context)
        return state
    
    async def _create_context_step(self, flow_id: str, thread_id: str, user_id: str, run_id: str) -> dict:
        """Execute create context step."""
        self.supervisor.flow_logger.step_started(flow_id, "create_context", "initialization")
        context = self._create_run_context(thread_id, user_id, run_id)
        self.supervisor.flow_logger.step_completed(flow_id, "create_context", "initialization")
        return context
    
    async def _initialize_state_step(self, flow_id: str, user_prompt: str, 
                                   thread_id: str, user_id: str, run_id: str) -> DeepAgentState:
        """Execute initialize state step."""
        self.supervisor.flow_logger.step_started(flow_id, "initialize_state", "state_management")
        state = await self.supervisor.state_manager.initialize_state(user_prompt, thread_id, user_id, run_id)
        self.supervisor.flow_logger.step_completed(flow_id, "initialize_state", "state_management")
        return state
    
    async def _build_pipeline_step(self, flow_id: str, user_prompt: str, state: DeepAgentState) -> List[PipelineStep]:
        """Execute build pipeline step."""
        self.supervisor.flow_logger.step_started(flow_id, "build_pipeline", "planning")
        pipeline = self.supervisor.pipeline_builder.get_execution_pipeline(user_prompt, state)
        self.supervisor.flow_logger.step_completed(flow_id, "build_pipeline", "planning")
        return pipeline
    
    async def _execute_pipeline_step(self, flow_id: str, pipeline: List[PipelineStep], 
                                   state: DeepAgentState, context: dict) -> None:
        """Execute pipeline step."""
        self.supervisor.flow_logger.step_started(flow_id, "execute_pipeline", "execution")
        await self._execute_with_context(pipeline, state, context)
        self.supervisor.flow_logger.step_completed(flow_id, "execute_pipeline", "execution")
    
    def _create_run_context(self, thread_id: str, user_id: str, run_id: str) -> Dict[str, str]:
        """Create execution context."""
        return {
            "thread_id": thread_id,
            "user_id": user_id,
            "run_id": run_id
        }
    
    async def _execute_with_context(self, pipeline: List[PipelineStep],
                                   state: DeepAgentState, context: Dict[str, str]) -> None:
        """Execute pipeline with context."""
        await self.supervisor.pipeline_executor.execute_pipeline(
            pipeline, state, context["run_id"], context
        )
        await self.supervisor.pipeline_executor.finalize_state(state, context)