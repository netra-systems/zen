"""Pipeline execution logic for supervisor agent."""

from typing import Dict, List, Any
from app.agents.state import DeepAgentState
from app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)
from app.agents.supervisor.execution_engine import ExecutionEngine
from app.services.state_persistence import state_persistence_service
from app.logging_config import central_logger
from app.llm.observability import generate_llm_correlation_id
from app.agents.supervisor.observability_flow import get_supervisor_flow_logger
from sqlalchemy.ext.asyncio import AsyncSession
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ws_manager import WebSocketManager

logger = central_logger.get_logger(__name__)


class PipelineExecutor:
    """Handles pipeline execution logic for supervisor agent."""
    
    def __init__(self, engine: ExecutionEngine, 
                 websocket_manager: 'WebSocketManager',
                 db_session: AsyncSession):
        self.engine = engine
        self.websocket_manager = websocket_manager
        self.db_session = db_session
        self.state_persistence = state_persistence_service
        self.flow_logger = get_supervisor_flow_logger()
    
    async def execute_pipeline(self, pipeline: List[PipelineStep],
                              state: DeepAgentState, run_id: str,
                              context: Dict[str, str]) -> None:
        """Execute the agent pipeline."""
        correlation_id = generate_llm_correlation_id()
        flow_id = self.flow_logger.generate_flow_id()
        self.flow_logger.start_flow(flow_id, correlation_id, len(pipeline))
        
        exec_context = self._build_execution_context(run_id, context)
        await self._run_pipeline_with_hooks(pipeline, state, exec_context, flow_id)
        self.flow_logger.complete_flow(flow_id)
    
    def _build_execution_context(self, run_id: str, 
                                context: Dict[str, str]) -> AgentExecutionContext:
        """Build execution context."""
        params = self._extract_context_params(run_id, context)
        return AgentExecutionContext(**params)
    
    def _extract_context_params(self, run_id: str, 
                               context: Dict[str, str]) -> Dict[str, str]:
        """Extract parameters for execution context."""
        base_params = self._get_base_execution_params(run_id, context)
        return {**base_params, "agent_name": "supervisor"}
    
    def _get_base_execution_params(self, run_id: str, context: Dict[str, str]) -> Dict[str, str]:
        """Get base execution parameters."""
        return {
            "run_id": run_id,
            "thread_id": context["thread_id"],
            "user_id": context["user_id"]
        }
    
    async def _run_pipeline_with_hooks(self, pipeline: List[PipelineStep],
                                      state: DeepAgentState,
                                      context: AgentExecutionContext,
                                      flow_id: str) -> None:
        """Run pipeline with error handling."""
        try:
            await self._execute_and_process(pipeline, state, context, flow_id)
        except Exception as e:
            await self._handle_pipeline_error(state, e)
    
    async def _execute_and_process(self, pipeline: List[PipelineStep],
                                  state: DeepAgentState,
                                  context: AgentExecutionContext,
                                  flow_id: str) -> None:
        """Execute pipeline and process results."""
        self._log_pipeline_execution_type(flow_id, pipeline)
        results = await self._execute_with_step_logging(pipeline, context, state, flow_id)
        self._process_results(results, state)
    
    async def _handle_pipeline_error(self, state: DeepAgentState, 
                                    error: Exception) -> None:
        """Handle pipeline execution error."""
        logger.error(f"Pipeline execution failed: {error}")
        raise
    
    def _process_results(self, results: List[AgentExecutionResult],
                        state: DeepAgentState) -> None:
        """Process execution results."""
        for result in results:
            if result.success and result.state:
                state.merge_from(result.state)

    def _log_pipeline_execution_type(self, flow_id: str, pipeline: List[PipelineStep]) -> None:
        """Log pipeline execution type (parallel vs sequential)."""
        agent_names = self._extract_agent_names(pipeline)
        if len(agent_names) > 1:
            self.flow_logger.log_parallel_execution(flow_id, agent_names)
        else:
            self.flow_logger.log_sequential_execution(flow_id, agent_names)

    def _extract_agent_names(self, pipeline: List[PipelineStep]) -> List[str]:
        """Extract agent names from pipeline steps."""
        return [step.agent_name for step in pipeline if hasattr(step, 'agent_name')]

    async def _execute_with_step_logging(self, pipeline: List[PipelineStep],
                                        context: AgentExecutionContext,
                                        state: DeepAgentState, 
                                        flow_id: str) -> List[AgentExecutionResult]:
        """Execute pipeline with step transition logging."""
        for i, step in enumerate(pipeline):
            step_name = getattr(step, 'agent_name', f'step_{i}')
            self.flow_logger.step_started(flow_id, step_name, "agent")
        
        results = await self.engine.execute_pipeline(pipeline, context, state)
        
        for i, step in enumerate(pipeline):
            step_name = getattr(step, 'agent_name', f'step_{i}')
            self.flow_logger.step_completed(flow_id, step_name, "agent")
        
        return results
    
    async def finalize_state(self, state: DeepAgentState, 
                            context: Dict[str, str]) -> None:
        """Finalize and persist state."""
        await self._persist_final_state(state, context)
        await self._notify_completion(state, context)
    
    async def _persist_final_state(self, state: DeepAgentState,
                                  context: Dict[str, str]) -> None:
        """Save final state to persistence."""
        params = self._build_persistence_params(state, context)
        await self.state_persistence.save_agent_state(**params)
    
    def _build_persistence_params(self, state: DeepAgentState, 
                                 context: Dict[str, str]) -> Dict[str, Any]:
        """Build parameters for state persistence."""
        return self._create_persistence_dict(state, context)
    
    def _create_persistence_dict(self, state: DeepAgentState,
                                context: Dict[str, str]) -> Dict[str, Any]:
        """Create persistence parameter dictionary."""
        context_params = self._extract_persistence_context(context)
        state_params = self._get_state_persistence_params(state)
        return {**context_params, **state_params}
    
    def _extract_persistence_context(self, context: Dict[str, str]) -> Dict[str, str]:
        """Extract context for persistence."""
        return {
            "run_id": context["run_id"],
            "thread_id": context["thread_id"],
            "user_id": context["user_id"]
        }
    
    def _get_state_persistence_params(self, state: DeepAgentState) -> Dict[str, Any]:
        """Get state persistence parameters."""
        return {
            "state": state,
            "db_session": self.db_session
        }
    
    async def _notify_completion(self, state: DeepAgentState,
                                context: Dict[str, str]) -> None:
        """Send completion notification."""
        if not self.websocket_manager:
            return
        await self._send_completion_message(
            state, context["thread_id"], context["run_id"]
        )
    
    async def _send_completion_message(self, state: DeepAgentState, 
                                      thread_id: str, run_id: str) -> None:
        """Send completion message via WebSocket."""
        try:
            await self._send_message_safely(state, run_id, thread_id)
        except Exception as e:
            await self._handle_message_error(e, thread_id)
    
    async def _send_message_safely(self, state: DeepAgentState, 
                                  run_id: str, thread_id: str) -> None:
        """Send message with error handling."""
        message = self._build_completion_message(state, run_id)
        await self.websocket_manager.send_to_thread(
            thread_id, message.model_dump()
        )
    
    async def _handle_message_error(self, error: Exception, thread_id: str) -> None:
        """Handle WebSocket message errors."""
        from starlette.websockets import WebSocketDisconnect
        if isinstance(error, WebSocketDisconnect):
            logger.warning(f"WebSocket disconnected for thread {thread_id}")
        else:
            logger.error(f"Failed to send completion: {error}")
    
    def _build_completion_message(self, state: DeepAgentState, 
                                 run_id: str) -> 'WebSocketMessage':
        """Build completion message."""
        content = self._create_completion_content(state, run_id)
        return self._create_websocket_message(content)
    
    def _create_completion_content(self, state: DeepAgentState, run_id: str):
        """Create agent completion content."""
        from app.schemas import AgentCompleted, AgentResult
        return AgentCompleted(
            run_id=run_id,
            result=AgentResult(success=True, output=state.to_dict()),
            execution_time_ms=0.0
        )
    
    def _create_websocket_message(self, content) -> 'WebSocketMessage':
        """Create WebSocket message wrapper."""
        from app.schemas import WebSocketMessage
        return WebSocketMessage(
            type="agent_completed", payload=content.model_dump()
        )