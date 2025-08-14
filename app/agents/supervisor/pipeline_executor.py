"""Pipeline execution logic for supervisor agent."""

from typing import Dict, List
from app.agents.state import DeepAgentState
from app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)
from app.agents.supervisor.execution_engine import ExecutionEngine
from app.services.state_persistence_service import state_persistence_service
from app.logging_config import central_logger
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
    
    async def execute_pipeline(self, pipeline: List[PipelineStep],
                              state: DeepAgentState, run_id: str,
                              context: Dict[str, str]) -> None:
        """Execute the agent pipeline."""
        exec_context = self._build_execution_context(run_id, context)
        await self._run_pipeline_with_hooks(pipeline, state, exec_context)
    
    def _build_execution_context(self, run_id: str, 
                                context: Dict[str, str]) -> AgentExecutionContext:
        """Build execution context."""
        return AgentExecutionContext(
            run_id=run_id,
            thread_id=context["thread_id"],
            user_id=context["user_id"],
            agent_name="supervisor"
        )
    
    async def _run_pipeline_with_hooks(self, pipeline: List[PipelineStep],
                                      state: DeepAgentState,
                                      context: AgentExecutionContext) -> None:
        """Run pipeline with error handling."""
        try:
            await self._execute_and_process(pipeline, state, context)
        except Exception as e:
            await self._handle_pipeline_error(state, e)
    
    async def _execute_and_process(self, pipeline: List[PipelineStep],
                                  state: DeepAgentState,
                                  context: AgentExecutionContext) -> None:
        """Execute pipeline and process results."""
        results = await self.engine.execute_pipeline(pipeline, context, state)
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
    
    async def finalize_state(self, state: DeepAgentState, 
                            context: Dict[str, str]) -> None:
        """Finalize and persist state."""
        await self._persist_final_state(state, context)
        await self._notify_completion(state, context)
    
    async def _persist_final_state(self, state: DeepAgentState,
                                  context: Dict[str, str]) -> None:
        """Save final state to persistence."""
        await self.state_persistence.save_agent_state(
            run_id=context["run_id"],
            thread_id=context["thread_id"],
            user_id=context["user_id"],
            state=state,
            db_session=self.db_session
        )
    
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
        from app.schemas import WebSocketMessage, AgentCompleted, AgentResult
        from starlette.websockets import WebSocketDisconnect
        
        try:
            content = AgentCompleted(
                run_id=run_id,
                result=AgentResult(
                    success=True,
                    output=state.to_dict()
                ),
                execution_time_ms=0.0
            )
            message = WebSocketMessage(
                type="agent_completed", 
                payload=content.model_dump()
            )
            await self.websocket_manager.send_to_thread(
                thread_id, message.model_dump()
            )
        except WebSocketDisconnect:
            logger.warning(f"WebSocket disconnected for thread {thread_id}")
        except Exception as e:
            logger.error(f"Failed to send completion: {e}")