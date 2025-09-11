"""Pipeline execution logic for supervisor agent."""

from typing import TYPE_CHECKING, Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

# CRITICAL SECURITY MIGRATION: Issue #271 - DeepAgentState removed for user isolation
# from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.db.session import get_session_from_factory
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
)
from netra_backend.app.agents.execution_engine_interface import IExecutionEngine as ExecutionEngine
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

if TYPE_CHECKING:
    # CANONICAL IMPORT: Use direct import path for better SSOT compliance
    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
    from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)


class PipelineExecutor:
    """Handles pipeline execution logic for supervisor agent.
    
    CRITICAL: This class no longer stores db_session as instance variable.
    Database sessions must be passed as parameters to methods that need them.
    """
    
    def __init__(self, engine: ExecutionEngine, 
                 websocket_manager: 'WebSocketManager', 
                 user_context=None):
        """Initialize without global session storage.
        
        Args:
            engine: Execution engine for running agents
            websocket_manager: WebSocket manager for notifications
            user_context: Optional user execution context for event isolation
        """
        self.engine = engine
        self.websocket_manager = websocket_manager
        # REMOVED: self.db_session = db_session (global session storage removed)
        self.state_persistence = self._get_persistence_service()
        self.flow_logger = get_supervisor_flow_logger()
        # Store user context for isolated WebSocket events (factory pattern)
        self.user_context = user_context
        self._websocket_emitter = None  # Will be created when user_context is available
    
    def _get_persistence_service(self):
        """Get the unified state persistence service.
        
        The service internally handles optimization based on environment configuration.
        """
        # The service now handles optimizations internally based on environment
        logger.debug("Using unified state persistence service")
        return state_persistence_service
    
    async def execute_pipeline(self, pipeline: List[PipelineStep],
                              user_context: UserExecutionContext, run_id: str,
                              context: Dict[str, str], db_session) -> None:
        """Execute the agent pipeline.
        
        SECURITY MIGRATION: Issue #271 - Uses UserExecutionContext for secure user isolation.
        
        Args:
            pipeline: Pipeline steps to execute
            user_context: User execution context (replaces DeepAgentState for security)
            run_id: Run identifier
            context: Execution context
            db_session: Database session for persistence operations
        """
        flow_context = self._prepare_flow_context(pipeline)
        exec_context = self._build_execution_context(run_id, context)
        await self._execute_pipeline_with_flow(pipeline, user_context, exec_context, flow_context, db_session)
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
                                         user_context: UserExecutionContext,
                                         exec_context: AgentExecutionContext,
                                         flow_context: Dict[str, Any], db_session) -> None:
        """Execute pipeline with flow context.
        
        SECURITY MIGRATION: Issue #271 - Uses UserExecutionContext for secure user isolation.
        """
        await self._run_pipeline_with_hooks(pipeline, user_context, exec_context, flow_context['flow_id'], db_session)
    
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
                                      user_context: UserExecutionContext,
                                      context: AgentExecutionContext,
                                      flow_id: str, db_session) -> None:
        """Run pipeline with error handling.
        
        SECURITY MIGRATION: Issue #271 - Uses UserExecutionContext for secure user isolation.
        """
        try:
            await self._execute_and_process(pipeline, user_context, context, flow_id, db_session)
        except Exception as e:
            await self._handle_pipeline_error(user_context, e)
    
    async def _execute_and_process(self, pipeline: List[PipelineStep],
                                  user_context: UserExecutionContext,
                                  context: AgentExecutionContext,
                                  flow_id: str, db_session) -> None:
        """Execute pipeline and process results with user context.
        
        SECURITY MIGRATION: Issue #271 - Uses UserExecutionContext for secure user isolation.
        """
        self._log_pipeline_execution_type(flow_id, pipeline)
        results = await self._execute_with_step_logging(pipeline, context, user_context, flow_id)
        await self._process_results_with_user_context(results, user_context, context, db_session)
    
    async def _handle_pipeline_error(self, user_context: UserExecutionContext, 
                                    error: Exception) -> None:
        """Handle pipeline execution error.
        
        SECURITY MIGRATION: Issue #271 - Uses UserExecutionContext for secure user isolation.
        """
        logger.error(f"Pipeline execution failed for user {user_context.user_id}: {error}")
        raise
    
    def _process_results(self, results: List[AgentExecutionResult],
                        user_context: UserExecutionContext) -> None:
        """Process execution results (deprecated - replaced by user context pattern).
        
        DEPRECATED: Issue #271 - This method was using DeepAgentState.merge_from() 
        which is insecure for multi-user environments. Use UserExecutionContext instead.
        """
        logger.warning(
            "DEPRECATED: _process_results() using DeepAgentState pattern. "
            "Migrate to UserExecutionContext for secure user isolation. "
            f"Processing {len(results)} results for user {user_context.user_id}"
        )
        # Legacy state merging is not supported with UserExecutionContext for security
        # Results should be processed through secure execution context patterns
    
    async def _process_results_with_user_context(self, results: List[AgentExecutionResult],
                                               user_context: UserExecutionContext,
                                               context: AgentExecutionContext, db_session) -> None:
        """Process execution results with secure user context isolation.
        
        SECURITY MIGRATION: Issue #271 - Uses UserExecutionContext instead of DeepAgentState 
        to prevent cross-user data contamination.
        """
        # Send orchestration notification about combining results
        await self._send_orchestration_notification(
            context.thread_id, context.run_id, 
            "orchestration_combining", 
            f"Combining results from {len(results)} agents for user {user_context.user_id}..."
        )
        
        # Collect all successful results for secure processing
        successful_results = []
        for result in results:
            if result.success:
                successful_results.append(result)
        
        if not successful_results:
            return
        
        # Process results through secure user context instead of state merging
        await self._process_results_securely(successful_results, user_context, context, db_session)
    
    async def _process_results_securely(self, successful_results: List[AgentExecutionResult],
                                       user_context: UserExecutionContext, 
                                       context: AgentExecutionContext, db_session) -> None:
        """Process successful results with secure user context isolation.
        
        SECURITY MIGRATION: Issue #271 - Secure alternative to state merging.
        """
        # Log processing for audit trail
        logger.info(
            f"Processing {len(successful_results)} successful results for user {user_context.user_id}, "
            f"thread {user_context.thread_id}"
        )
        
        # Store results in user's execution context instead of global state
        for result in successful_results:
            if result.data:
                # Store result data securely within the user context
                user_context.add_execution_result(result.agent_name, result.data)
        
        # Persist results securely through user context
        await self._persist_user_results(user_context, context, db_session)
    
    async def _batch_merge_states_deprecated(self, target_state, state_changes) -> None:
        """DEPRECATED: State merging replaced by secure user context processing.
        
        SECURITY MIGRATION: Issue #271 - This method performed unsafe state merging.
        """
        # Batch merge all states in one operation instead of individual merges
        # This reduces object creation and serialization overhead
        for state_change in state_changes:
            target_state.merge_from(state_change)
        
        logger.debug(f"Batched merge of {len(state_changes)} state changes")
    
    async def _persist_user_results(self, user_context: UserExecutionContext,
                                   context: AgentExecutionContext, db_session) -> None:
        """Persist user results securely through execution context.
        
        SECURITY MIGRATION: Issue #271 - Secure persistence replacing state batching.
        """
        try:
            # Create persistence request for secure user context data
            from netra_backend.app.schemas.agent_state import StatePersistenceRequest, CheckpointType
            
            # Get user execution results securely from context
            user_results = user_context.get_execution_results()
            
            persistence_request = StatePersistenceRequest(
                run_id=context.run_id,
                user_id=user_context.user_id,
                state_data=user_results,  # Secure user-isolated data
                checkpoint_type=CheckpointType.PIPELINE_COMPLETE,
                agent_phase="pipeline_user_context_persist"
            )
            
            # Use the optimized persistence service with secure user context
            success, snapshot_id = await self.state_persistence.save_agent_state(
                persistence_request, db_session
            )
            
            if success:
                logger.debug(
                    f"User context results persisted successfully for user {user_context.user_id}: {snapshot_id}"
                )
            else:
                logger.warning(f"User context persistence failed for user {user_context.user_id}")
                
        except Exception as e:
            logger.error(f"Error in user context persistence for user {user_context.user_id}: {e}")
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
                                        user_context: UserExecutionContext, 
                                        flow_id: str) -> List[AgentExecutionResult]:
        """Execute pipeline with step transition logging.
        
        SECURITY MIGRATION: Issue #271 - Uses UserExecutionContext for secure user isolation.
        """
        self._log_step_transitions_start(pipeline, flow_id)
        results = await self.engine.execute_pipeline(pipeline, context, user_context)
        self._log_step_transitions_complete(pipeline, flow_id)
        return results
    
    async def finalize_user_context(self, user_context: UserExecutionContext, 
                                   context: Dict[str, str], db_session) -> None:
        """Finalize and persist user context results.
        
        SECURITY MIGRATION: Issue #271 - Uses UserExecutionContext for secure user isolation.
        
        Args:
            user_context: User execution context to finalize
            context: Execution context
            db_session: Database session for persistence operations
        """
        await self._persist_final_user_context(user_context, context, db_session)
        await self._notify_user_completion(user_context, context)
    
    async def _persist_final_user_context(self, user_context: UserExecutionContext,
                                         context: Dict[str, str], db_session) -> None:
        """Save final user context to persistence.
        
        SECURITY MIGRATION: Issue #271 - Secure alternative to state persistence.
        """
        request = self._build_user_persistence_request(user_context, context)
        session = await get_session_from_factory(db_session)
        await self.state_persistence.save_agent_state(request, session)
    
    def _build_user_persistence_request(self, user_context: UserExecutionContext, 
                                       context: Dict[str, str]) -> StatePersistenceRequest:
        """Build StatePersistenceRequest for user context persistence."""
        from netra_backend.app.schemas.agent_state import StatePersistenceRequest, CheckpointType
        return StatePersistenceRequest(
            run_id=context["run_id"],
            thread_id=context.get("thread_id", user_context.thread_id),
            user_id=user_context.user_id,
            state_data=user_context.get_execution_results(),
            checkpoint_type=CheckpointType.AUTO
        )
    
    async def _notify_user_completion(self, user_context: UserExecutionContext,
                                     context: Dict[str, str]) -> None:
        """Send completion notification for user context.
        
        SECURITY MIGRATION: Issue #271 - User-isolated notifications.
        """
        if not self.websocket_manager:
            return
        await self._send_user_completion_message(user_context, context["thread_id"], context["run_id"])
        
    async def _send_user_completion_message(self, user_context: UserExecutionContext, 
                                          thread_id: str, run_id: str) -> None:
        """Send user completion message via WebSocket."""
        try:
            await self._send_user_message_safely(user_context, run_id, thread_id)
        except Exception as e:
            await self._handle_message_error(e, thread_id)
    
    async def _send_user_message_safely(self, user_context: UserExecutionContext, 
                                       run_id: str, thread_id: str) -> None:
        """Send message with error handling for user context."""
        try:
            # Get user-isolated emitter (factory pattern)
            emitter = await self._get_user_emitter_from_context(run_id, thread_id)
            if not emitter:
                logger.debug(f"No user context available for pipeline WebSocket updates for user {user_context.user_id} - skipping")
                return
            
            # Send pipeline completion notification with user context
            completion_content = self._create_user_completion_content(user_context, run_id)
            completion_message = self._build_user_completion_message(user_context, completion_content, run_id)
            await emitter(completion_message)
            
        except Exception as e:
            logger.error(f"Pipeline WebSocket notification failed for user {user_context.user_id}: {e}")
            # Don't re-raise to prevent breaking pipeline
    
    def _build_user_completion_message(self, user_context: UserExecutionContext, 
                                      content: Dict, run_id: str) -> Dict:
        """Build pipeline completion message for user context."""
        return {
            "type": "pipeline_completed",
            "run_id": run_id,
            "user_id": user_context.user_id,
            "thread_id": user_context.thread_id,
            "content": content,
            "timestamp": self._get_current_timestamp()
        }
        
    def _create_user_completion_content(self, user_context: UserExecutionContext, run_id: str):
        """Create completion content for user context."""
        return {
            "message": f"Pipeline execution completed for user {user_context.user_id}",
            "run_id": run_id,
            "results_count": len(user_context.get_execution_results()),
            "status": "completed"
        }
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for messaging."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    # DEPRECATED METHODS - Keep for backward compatibility but mark as deprecated
    async def _persist_final_state(self, state, context: Dict[str, str], db_session) -> None:
        """DEPRECATED: Save final state to persistence. Use _persist_final_user_context instead."""
        request = self._build_persistence_request(state, context)
        session = await get_session_from_factory(db_session)
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
        """Send message with error handling via factory pattern for user isolation."""
        try:
            # Get user-isolated emitter (factory pattern)
            emitter = await self._get_user_emitter_from_context(run_id, thread_id)
            if not emitter:
                logger.debug("No user context available for pipeline WebSocket updates - skipping")
                return
            
            # Send pipeline completion notification
            await emitter.emit_agent_completed("PipelineExecutor", {
                "pipeline_completed": True, 
                "state_summary": "Pipeline execution completed",
                "agent_name": "PipelineExecutor"
            })
        except Exception as e:
            logger.error(f"Failed to send completion via bridge: {e}")
    
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
        """Send orchestration-level WebSocket notification via factory pattern for user isolation."""
        try:
            # Get user-isolated emitter (factory pattern)
            emitter = await self._get_user_emitter_from_context(run_id, thread_id)
            if not emitter:
                logger.debug("No user context available for orchestration WebSocket updates - skipping")
                return
            
            # Map event types to appropriate emitter notifications
            if event_type == "pipeline_started":
                await emitter.emit_agent_started("PipelineExecutor", {"orchestration_level": True, "message": message})
            elif event_type == "pipeline_thinking" or "processing" in event_type:
                await emitter.emit_agent_thinking("PipelineExecutor", {"message": message, "orchestration_level": True})
            elif event_type == "pipeline_completed":
                await emitter.emit_agent_completed("PipelineExecutor", {"orchestration_level": True, "agent_name": "PipelineExecutor"})
            elif event_type == "pipeline_error":
                await emitter.emit_custom_event("agent_error", {"agent_name": "PipelineExecutor", "error_message": message, "orchestration_level": True})
            else:
                # Custom pipeline event
                payload = {
                    "run_id": run_id,
                    "event_type": event_type,
                    "message": message,
                    "timestamp": self._get_current_timestamp(),
                    "agent_name": "pipeline_executor",
                    "orchestration_level": True
                }
                await emitter.emit_custom_event(f"pipeline_{event_type}", payload)
            
            logger.info(f"Sent orchestration notification via factory pattern: {event_type} - {message[:50]}...")
            
        except Exception as e:
            logger.warning(f"Failed to send orchestration notification via factory pattern {event_type}: {e}")
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).timestamp()
    async def _get_user_emitter_from_context(self, run_id: str, thread_id: str, user_id: str = None):
        """Get user-isolated WebSocket emitter from context parameters using factory pattern."""
        try:
            # Try to get user context if already stored
            if self.user_context:
                return await self._get_user_emitter()
                
            # Create UserExecutionContext from parameters if available
            if run_id and thread_id:
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                
                user_context = UserExecutionContext(
                    user_id=user_id or "unknown_user",
                    thread_id=thread_id, 
                    run_id=run_id
                )
                
                # Use factory to create isolated bridge
                from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
                # Fix: create_agent_websocket_bridge is synchronous, not async
                bridge = create_agent_websocket_bridge(user_context)
                return await bridge.create_user_emitter(user_context)
            else:
                logger.debug("Missing required context parameters for user emitter")
                return None
                
        except Exception as e:
            logger.debug(f"Failed to create user emitter from context parameters: {e}")
            return None
            
    async def _get_user_emitter(self):
        """Get user-isolated WebSocket emitter using factory pattern."""
        if not self.user_context:
            return None
            
        # Create emitter if not already created (lazy initialization)
        if not self._websocket_emitter:
            try:
                from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
                # Use factory to create isolated bridge
                # Fix: create_agent_websocket_bridge is synchronous, not async
                bridge = create_agent_websocket_bridge(self.user_context)
                self._websocket_emitter = await bridge.create_user_emitter(self.user_context)
            except Exception as e:
                logger.debug(f"Failed to create user emitter: {e}")
                return None
                
        return self._websocket_emitter
    
    def set_user_context(self, user_context) -> None:
        """Set user context for isolated WebSocket events (factory pattern).
        
        Args:
            user_context: User execution context for event isolation
        """
        self.user_context = user_context
        # Reset emitter to force recreation with new context
        self._websocket_emitter = None
