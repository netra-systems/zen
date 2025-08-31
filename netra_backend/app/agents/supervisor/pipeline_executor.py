"""Pipeline execution logic for supervisor agent."""

from typing import TYPE_CHECKING, Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.db.session import get_session_from_factory
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
)
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.observability_flow import (
    get_supervisor_flow_logger,
)
from netra_backend.app.llm.observability import generate_llm_correlation_id
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent_state import (
    CheckpointType,
    StatePersistenceRequest,
)
from netra_backend.app.services.state_persistence import state_persistence_service
from netra_backend.app.services.state_persistence_optimized import optimized_state_persistence

if TYPE_CHECKING:
    from netra_backend.app.websocket_core import UnifiedWebSocketManager as WebSocketManager

logger = central_logger.get_logger(__name__)


class PipelineExecutor:
    """Handles pipeline execution logic for supervisor agent."""
    
    def __init__(self, engine: ExecutionEngine, 
                 websocket_manager: 'WebSocketManager',
                 db_session: AsyncSession):
        self.engine = engine
        self.websocket_manager = websocket_manager
        self.db_session = db_session
        self.state_persistence = self._get_persistence_service()
        self.flow_logger = get_supervisor_flow_logger()
    
    def _get_persistence_service(self):
        """Get appropriate persistence service based on feature flag."""
        from netra_backend.app.core.isolated_environment import get_env
        
        # Check if optimized persistence is enabled
        optimized_enabled = get_env().get("ENABLE_OPTIMIZED_PERSISTENCE", "false").lower() == "true"
        
        if optimized_enabled:
            logger.info("Using optimized state persistence service")
            return optimized_state_persistence
        else:
            logger.debug("Using standard state persistence service")
            return state_persistence_service
    
    async def execute_pipeline(self, pipeline: List[PipelineStep],
                              state: DeepAgentState, run_id: str,
                              context: Dict[str, str]) -> None:
        """Execute the agent pipeline."""
        flow_context = self._prepare_flow_context(pipeline)
        exec_context = self._build_execution_context(run_id, context)
        await self._execute_pipeline_with_flow(pipeline, state, exec_context, flow_context)
        self.flow_logger.complete_flow(flow_context['flow_id'])
    
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
    
    def _prepare_flow_context(self, pipeline: List[PipelineStep]) -> Dict[str, Any]:
        """Prepare flow context for pipeline execution."""
        correlation_id = generate_llm_correlation_id()
        flow_id = self.flow_logger.generate_flow_id()
        self.flow_logger.start_flow(flow_id, correlation_id, len(pipeline))
        return {'flow_id': flow_id, 'correlation_id': correlation_id}
    
    async def _execute_pipeline_with_flow(self, pipeline: List[PipelineStep],
                                         state: DeepAgentState,
                                         exec_context: AgentExecutionContext,
                                         flow_context: Dict[str, Any]) -> None:
        """Execute pipeline with flow context."""
        await self._run_pipeline_with_hooks(pipeline, state, exec_context, flow_context['flow_id'])
    
    def _log_step_transitions_start(self, pipeline: List[PipelineStep], flow_id: str) -> None:
        """Log start of all step transitions."""
        for i, step in enumerate(pipeline):
            step_name = getattr(step, 'agent_name', f'step_{i}')
            self.flow_logger.step_started(flow_id, step_name, "agent")
    
    def _log_step_transitions_complete(self, pipeline: List[PipelineStep], flow_id: str) -> None:
        """Log completion of all step transitions."""
        for i, step in enumerate(pipeline):
            step_name = getattr(step, 'agent_name', f'step_{i}')
            self.flow_logger.step_completed(flow_id, step_name, "agent")
    
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
        """Execute pipeline and process results with batched state persistence."""
        self._log_pipeline_execution_type(flow_id, pipeline)
        results = await self._execute_with_step_logging(pipeline, context, state, flow_id)
        await self._process_results_with_batching(results, state, context)
    
    async def _handle_pipeline_error(self, state: DeepAgentState, 
                                    error: Exception) -> None:
        """Handle pipeline execution error."""
        logger.error(f"Pipeline execution failed: {error}")
        raise
    
    def _process_results(self, results: List[AgentExecutionResult],
                        state: DeepAgentState) -> None:
        """Process execution results (legacy method for backward compatibility)."""
        for result in results:
            if result.success and result.state:
                state.merge_from(result.state)
    
    async def _process_results_with_batching(self, results: List[AgentExecutionResult],
                                           state: DeepAgentState,
                                           context: AgentExecutionContext) -> None:
        """Process execution results with optimized batched state merging and persistence."""
        # Send orchestration notification about combining results
        await self._send_orchestration_notification(
            context.thread_id, context.run_id, 
            "orchestration_combining", 
            f"Combining results from {len(results)} agents..."
        )
        
        # Collect all successful state changes to merge in batch
        state_changes = []
        for result in results:
            if result.success and result.state:
                state_changes.append(result.state)
        
        if not state_changes:
            return
        
        # Perform batched state merge - more efficient than individual merges
        await self._batch_merge_states(state, state_changes)
        
        # Persist the final merged state once instead of multiple times
        await self._persist_batched_state(state, context)
    
    async def _batch_merge_states(self, target_state: DeepAgentState,
                                 state_changes: List[DeepAgentState]) -> None:
        """Efficiently merge multiple state changes into target state."""
        # Batch merge all states in one operation instead of individual merges
        # This reduces object creation and serialization overhead
        for state_change in state_changes:
            target_state.merge_from(state_change)
        
        logger.debug(f"Batched merge of {len(state_changes)} state changes")
    
    async def _persist_batched_state(self, state: DeepAgentState,
                                   context: AgentExecutionContext) -> None:
        """Persist state once after all batched changes instead of per-change."""
        try:
            # Create persistence request for the final merged state
            from netra_backend.app.schemas.agent_state import StatePersistenceRequest, CheckpointType
            
            persistence_request = StatePersistenceRequest(
                run_id=context.run_id,
                user_id=context.user_id,
                state_data=state.to_dict() if hasattr(state, 'to_dict') else state.__dict__,
                checkpoint_type=CheckpointType.PIPELINE_COMPLETE,
                agent_phase="pipeline_batch_persist"
            )
            
            # Use the optimized persistence service if available
            success, snapshot_id = await self.state_persistence.save_agent_state(
                persistence_request, self.db_session
            )
            
            if success:
                logger.debug(f"Batched state persisted successfully: {snapshot_id}")
            else:
                logger.warning("Batched state persistence failed")
                
        except Exception as e:
            logger.error(f"Error in batched state persistence: {e}")
            # Don't re-raise to avoid breaking pipeline execution

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
        self._log_step_transitions_start(pipeline, flow_id)
        results = await self.engine.execute_pipeline(pipeline, context, state)
        self._log_step_transitions_complete(pipeline, flow_id)
        return results
    
    async def finalize_state(self, state: DeepAgentState, 
                            context: Dict[str, str]) -> None:
        """Finalize and persist state."""
        await self._persist_final_state(state, context)
        await self._notify_completion(state, context)
    
    async def _persist_final_state(self, state: DeepAgentState,
                                  context: Dict[str, str]) -> None:
        """Save final state to persistence."""
        request = self._build_persistence_request(state, context)
        session = await get_session_from_factory(self.db_session)
        await self.state_persistence.save_agent_state(request, session)
    
    def _build_persistence_request(self, state: DeepAgentState, 
                                   context: Dict[str, str]) -> StatePersistenceRequest:
        """Build StatePersistenceRequest for state persistence."""
        return self._create_persistence_request(state, context)
    
    def _create_persistence_request(self, state: DeepAgentState,
                                   context: Dict[str, str]) -> StatePersistenceRequest:
        """Create StatePersistenceRequest object."""
        return StatePersistenceRequest(
            run_id=context["run_id"],
            thread_id=context["thread_id"],
            user_id=context["user_id"],
            state_data=state.to_dict(),
            checkpoint_type=CheckpointType.AUTO
        )
    
    
    async def _notify_completion(self, state: DeepAgentState,
                                context: Dict[str, str]) -> None:
        """Send completion notification."""
        if not self.websocket_manager:
            return
        await self._send_completion_message(state, context["thread_id"], context["run_id"])
    
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
            thread_id, message.model_dump(mode='json')
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
        from netra_backend.app.schemas.agent import AgentCompleted
        from netra_backend.app.schemas.agent_models import AgentResult
        result = AgentResult(success=True, output=state.to_dict())
        return AgentCompleted(run_id=run_id, result=result, execution_time_ms=0.0)
    
    def _create_websocket_message(self, content) -> 'WebSocketMessage':
        """Create WebSocket message wrapper."""
        from netra_backend.app.schemas.websocket_models import WebSocketMessage
        return WebSocketMessage(
            type="agent_completed", payload=content.model_dump(mode='json')
        )
    
    async def _send_orchestration_notification(self, thread_id: str, run_id: str, 
                                             event_type: str, message: str) -> None:
        """Send orchestration-level WebSocket notification."""
        try:
            if not self.websocket_manager:
                logger.debug(f"No WebSocket manager available for orchestration event: {event_type}")
                return
            
            # Create orchestration notification payload
            payload = {
                "run_id": run_id,
                "event_type": event_type,
                "message": message,
                "timestamp": self._get_current_timestamp(),
                "agent_name": "supervisor",
                "orchestration_level": True
            }
            
            # Send notification
            from netra_backend.app.schemas.websocket_models import WebSocketMessage
            notification = WebSocketMessage(type=event_type, payload=payload)
            await self.websocket_manager.send_to_thread(thread_id, notification.model_dump())
            
            logger.info(f"Sent orchestration notification: {event_type} - {message[:50]}...")
            
        except Exception as e:
            logger.warning(f"Failed to send orchestration notification {event_type}: {e}")
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).timestamp()