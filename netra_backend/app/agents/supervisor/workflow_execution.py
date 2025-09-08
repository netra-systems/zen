"""Workflow Execution Helper for Supervisor Agent

Handles all workflow execution steps to reduce main supervisor file size.
Keeps methods under 8 lines each.

Business Value: Modular workflow execution with standardized patterns.
"""

from typing import Any, Dict, List

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import PipelineStepConfig
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SupervisorWorkflowExecutor:
    """Helper class for supervisor workflow execution."""
    
    def __init__(self, supervisor_agent):
        self.supervisor = supervisor_agent
    
    async def execute_workflow_steps(self, flow_id: str, user_prompt: str, 
                                   thread_id: str, user_id: str, run_id: str) -> DeepAgentState:
        """Execute all workflow steps."""
        # Send orchestration-level start notification
        await self._send_orchestration_notification(thread_id, run_id, "orchestration_started", 
                                                   f"Starting to process your request: {user_prompt[:100]}...")
        
        context = await self._create_context_step(flow_id, thread_id, user_id, run_id)
        state = await self._initialize_state_step(flow_id, user_prompt, thread_id, user_id, run_id)
        
        # Send analysis notification
        await self._send_orchestration_notification(thread_id, run_id, "orchestration_thinking", 
                                                   "Analyzing your request and determining which agents to use...")
        
        pipeline = await self._build_pipeline_step(flow_id, user_prompt, state)
        
        # Send delegation notification
        agent_names = [getattr(step, 'agent_name', 'agent') for step in pipeline]
        await self._send_orchestration_notification(thread_id, run_id, "orchestration_delegating", 
                                                   f"Delegating to specialized agents: {', '.join(agent_names)}")
        
        await self._execute_pipeline_step(flow_id, pipeline, state, context)
        
        # Send completion notification
        await self._send_orchestration_notification(thread_id, run_id, "orchestration_completed", 
                                                   "Task completed - combining results and preparing response")
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
        
        # Get session for state initialization
        if self.supervisor.db_session_factory:
            async with self.supervisor.db_session_factory() as session:
                state = await self.supervisor.state_manager.initialize_state_with_session(
                    session, user_prompt, thread_id, user_id, run_id)
        else:
            # Fallback: create state without database persistence
            from netra_backend.app.agents.state import DeepAgentState
            state = DeepAgentState()
            state.user_request = user_prompt
            state.chat_thread_id = thread_id
            state.user_id = user_id
            state.step_count = 0
        
        self.supervisor.flow_logger.step_completed(flow_id, "initialize_state", "state_management")
        return state
    
    async def _build_pipeline_step(self, flow_id: str, user_prompt: str, state: DeepAgentState) -> List[PipelineStepConfig]:
        """Execute build pipeline step."""
        self.supervisor.flow_logger.step_started(flow_id, "build_pipeline", "planning")
        pipeline = self.supervisor.pipeline_builder.get_execution_pipeline(user_prompt, state)
        self.supervisor.flow_logger.step_completed(flow_id, "build_pipeline", "planning")
        return pipeline
    
    async def _execute_pipeline_step(self, flow_id: str, pipeline: List[PipelineStepConfig], 
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
    
    async def _execute_with_context(self, pipeline: List[PipelineStepConfig],
                                   state: DeepAgentState, context: Dict[str, str]) -> None:
        """Execute pipeline with context."""
        await self.supervisor.pipeline_executor.execute_pipeline(
            pipeline, state, context["run_id"], context
        )
        await self.supervisor.pipeline_executor.finalize_state(state, context)
    
    async def _send_orchestration_notification(self, thread_id: str, run_id: str, 
                                             event_type: str, message: str) -> None:
        """Send orchestration-level WebSocket notification."""
        try:
            # Check if supervisor has websocket manager
            websocket_manager = getattr(self.supervisor, 'websocket_manager', None)
            if not websocket_manager:
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
            await websocket_manager.send_to_thread(thread_id, notification.model_dump())
            
            logger.info(f"Sent orchestration notification: {event_type} - {message[:50]}...")
            
        except Exception as e:
            logger.warning(f"Failed to send orchestration notification {event_type}: {e}")
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).timestamp()