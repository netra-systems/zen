"""Base agent class and interfaces."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Union, Any, TYPE_CHECKING
import asyncio
import time

from app.llm.llm_manager import LLMManager
from app.schemas import SubAgentLifecycle, SubAgentUpdate, SubAgentState
from app.schemas.registry import WebSocketMessage, WebSocketMessageType
from app.agents.state import DeepAgentState
from app.agents.interfaces import BaseAgentProtocol
from app.schemas.strict_types import TypedAgentResult, AgentExecutionMetrics
from app.core.type_validators import agent_type_safe, StrictTypeChecker
from app.logging_config import central_logger
from app.agents.error_handler import (
    global_error_handler, ErrorContext, WebSocketError, handle_agent_error
)
from langchain_core.messages import SystemMessage
from starlette.websockets import WebSocketDisconnect

class BaseSubAgent(ABC):
    def __init__(self, llm_manager: Optional[LLMManager] = None, name: str = "BaseSubAgent", description: str = "This is the base sub-agent."):
        self.llm_manager = llm_manager
        self.state = SubAgentLifecycle.PENDING
        self.name = name
        self.description = description
        self.start_time = None
        self.end_time = None
        self.context = {}  # Protected context for this agent
        self.websocket_manager = None  # Will be set by Supervisor
        self.user_id = None  # Will be set by Supervisor for WebSocket messages
        self.logger = central_logger.get_logger(name)

    async def _pre_run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> bool:
        """Entry conditions and setup. Returns True if agent should proceed."""
        self.logger.info(f"{self.name} checking entry conditions for run_id: {run_id}")
        self.start_time = time.time()
        self.set_state(SubAgentLifecycle.RUNNING)
        
        # Stream update that agent is starting
        if stream_updates and self.websocket_manager:
            await self._send_update(run_id, {"status": "starting", "message": f"{self.name} is starting"})
        
        # Subclasses can override to add specific entry conditions
        return await self.check_entry_conditions(state, run_id)
    
    async def _post_run(self, state: DeepAgentState, run_id: str, stream_updates: bool, success: bool) -> None:
        """Exit conditions and cleanup."""
        self.end_time = time.time()
        execution_time = self.end_time - self.start_time
        
        if success:
            self.set_state(SubAgentLifecycle.COMPLETED)
            status = "completed"
        else:
            self.set_state(SubAgentLifecycle.FAILED)
            status = "failed"
        
        self.logger.info(f"{self.name} {status} for run_id: {run_id} in {execution_time:.2f}s")
        
        # Stream update that agent finished
        if stream_updates and self.websocket_manager:
            await self._send_update(run_id, {
                "status": status,
                "message": f"{self.name} {status}",
                "execution_time": execution_time
            })
        
        # Cleanup
        await self.cleanup(state, run_id)
    
    def get_execution_metrics(self) -> AgentExecutionMetrics:
        """Get execution metrics for the agent."""
        return getattr(self, '_execution_metrics', AgentExecutionMetrics(execution_time_ms=0.0))
    
    def _create_failure_result(self, error_message: str, start_time: float) -> TypedAgentResult:
        """Create a failure result with metrics."""
        execution_time = (time.time() - start_time) * 1000
        return TypedAgentResult(
            success=False,
            agent_name=self.name,
            execution_time_ms=execution_time,
            error_message=error_message,
            metrics=self.get_execution_metrics()
        )
    
    def _create_success_result(self, start_time: float, result_data=None) -> TypedAgentResult:
        """Create a success result with metrics."""
        execution_time = (time.time() - start_time) * 1000
        return TypedAgentResult(
            success=True,
            agent_name=self.name,
            execution_time_ms=execution_time,
            result_data=result_data,
            metrics=self.get_execution_metrics()
        )
    
    async def run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Main run method with lifecycle management."""
        try:
            if not await self._handle_entry_conditions(state, run_id, stream_updates):
                return
            
            await self.execute(state, run_id, stream_updates)
            await self._post_run(state, run_id, stream_updates, success=True)
            
        except WebSocketDisconnect as e:
            await self._handle_websocket_disconnect(e, state, run_id, stream_updates)
        except Exception as e:
            await self._handle_execution_error(e, state, run_id, stream_updates)
            raise
    
    async def _handle_entry_conditions(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> bool:
        """Handle entry condition checks and failures."""
        if await self._pre_run(state, run_id, stream_updates):
            return True
        
        self.logger.warning(f"{self.name} entry conditions not met for run_id: {run_id}")
        await self._send_entry_condition_warning(run_id, stream_updates)
        await self._post_run(state, run_id, stream_updates, success=False)
        return False
    
    async def _send_entry_condition_warning(self, run_id: str, stream_updates: bool) -> None:
        """Send warning about failed entry conditions."""
        if not (stream_updates and self.websocket_manager):
            return
        
        try:
            ws_user_id = self.user_id if self.user_id else run_id
            await self.websocket_manager.send_agent_log(
                ws_user_id, "warning", 
                f"Entry conditions not met for {self.name}",
                self.name
            )
        except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
            self.logger.debug(f"WebSocket disconnected when sending warning: {e}")
    
    async def _handle_websocket_disconnect(self, e: WebSocketDisconnect, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Handle WebSocket disconnection during execution."""
        self.logger.info(f"WebSocket disconnected during {self.name} execution: {e}")
        await self._post_run(state, run_id, stream_updates, success=False)
    
    async def _handle_execution_error(self, e: Exception, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Handle execution errors and send notifications."""
        self.logger.error(f"{self.name} failed for run_id: {run_id}: {e}")
        await self._send_error_notification(e, run_id, stream_updates)
        await self._post_run(state, run_id, stream_updates, success=False)
    
    async def _send_error_notification(self, error: Exception, run_id: str, stream_updates: bool) -> None:
        """Send error notification via WebSocket."""
        if not (stream_updates and self.websocket_manager):
            return
        
        try:
            ws_user_id = self.user_id if self.user_id else run_id
            await self.websocket_manager.send_error(
                ws_user_id, 
                f"{self.name} encountered an error: {str(error)}",
                self.name
            )
        except (WebSocketDisconnect, RuntimeError, ConnectionError):
            self.logger.debug(f"WebSocket disconnected when sending error")
    
    @abstractmethod
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """The main execution logic of the agent. Subclasses must implement this."""
        pass
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if agent should proceed. Override in subclasses for specific conditions."""
        return True
    
    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution. Override in subclasses if needed."""
        self.context.clear()  # Clear protected context

    def set_state(self, new_state: SubAgentLifecycle) -> None:
        """Set agent state with transition validation."""
        current_state = self.state
        
        # Validate state transition
        if not self._is_valid_transition(current_state, new_state):
            self._raise_transition_error(current_state, new_state)
        
        self.logger.debug(f"{self.name} transitioning from {current_state} to {new_state}")
        self.state = new_state
    
    def _raise_transition_error(self, from_state: SubAgentLifecycle, to_state: SubAgentLifecycle) -> None:
        """Raise transition error with proper message"""
        raise ValueError(
            f"Invalid state transition from {from_state} to {to_state} "
            f"for agent {self.name}"
        )
    
    def _is_valid_transition(self, from_state: SubAgentLifecycle, to_state: SubAgentLifecycle) -> bool:
        """Validate if state transition is allowed."""
        valid_transitions = self._get_valid_transitions()
        return to_state in valid_transitions.get(from_state, [])
    
    def _get_valid_transitions(self) -> Dict[SubAgentLifecycle, List[SubAgentLifecycle]]:
        """Get mapping of valid state transitions."""
        return {
            SubAgentLifecycle.PENDING: self._get_pending_transitions(),
            SubAgentLifecycle.RUNNING: self._get_running_transitions(), 
            SubAgentLifecycle.COMPLETED: [SubAgentLifecycle.SHUTDOWN],
            SubAgentLifecycle.FAILED: self._get_failed_transitions(),
            SubAgentLifecycle.SHUTDOWN: []  # Terminal state
        }
    
    def _get_pending_transitions(self) -> List[SubAgentLifecycle]:
        """Get valid transitions from PENDING state."""
        return [
            SubAgentLifecycle.RUNNING,
            SubAgentLifecycle.FAILED,
            SubAgentLifecycle.SHUTDOWN
        ]
    
    def _get_running_transitions(self) -> List[SubAgentLifecycle]:
        """Get valid transitions from RUNNING state.""" 
        return [
            SubAgentLifecycle.COMPLETED,
            SubAgentLifecycle.FAILED,
            SubAgentLifecycle.SHUTDOWN
        ]
    
    def _get_failed_transitions(self) -> List[SubAgentLifecycle]:
        """Get valid transitions from FAILED state."""
        return [
            SubAgentLifecycle.PENDING,  # Allow retry
            SubAgentLifecycle.SHUTDOWN
        ]

    def get_state(self) -> SubAgentLifecycle:
        return self.state
    
    async def _send_update(self, run_id: str, data: "Dict[str, Any]") -> None:
        """Send WebSocket update with proper error recovery."""
        if not self.websocket_manager:
            return
            
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                await self._attempt_websocket_update(run_id, data)
                return  # Success, exit retry loop
            except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                retry_count += 1
                if retry_count >= max_retries:
                    self.logger.warning(f"WebSocket update failed after {max_retries} attempts: {e}")
                    await self._handle_websocket_failure(run_id, data, e)
                    return
                
                # Exponential backoff for retries
                await asyncio.sleep(0.1 * (2 ** retry_count))
            except Exception as e:
                self.logger.error(f"Unexpected error in WebSocket update: {e}")
                return
                
    async def _attempt_websocket_update(self, run_id: str, data: "Dict[str, Any]") -> None:
        """Attempt to send WebSocket update."""
        message_content = data.get("message", "")
        message = SystemMessage(content=message_content)
        
        sub_agent_state = SubAgentState(
            messages=[message],
            next_node="",
            lifecycle=self.get_state()
        )
        
        ws_user_id = self._get_websocket_user_id(run_id)
        
        update_payload = SubAgentUpdate(
            sub_agent_name=self.name,
            state=sub_agent_state
        )
        
        websocket_message = WebSocketMessage(
            type=WebSocketMessageType.SUB_AGENT_UPDATE,
            payload=update_payload.model_dump()
        )
        
        await self.websocket_manager.send_message(
            ws_user_id,
            websocket_message.model_dump()
        )
        
    def _get_websocket_user_id(self, run_id: str) -> str:
        """Get WebSocket user ID with fallback."""
        if hasattr(self.websocket_manager, '_current_user_id'):
            return getattr(self.websocket_manager, '_current_user_id', run_id)
        return run_id
        
    async def _handle_websocket_failure(self, run_id: str, data: "Dict[str, Any]", error: Exception) -> None:
        """Handle WebSocket failure with graceful degradation and centralized error tracking."""
        # Create error context for centralized handling
        context = ErrorContext(
            agent_name=self.name,
            operation_name="websocket_update", 
            run_id=run_id,
            timestamp=time.time(),
            additional_data=data
        )
        
        # Use centralized error handler for consistent tracking
        websocket_error = WebSocketError(f"WebSocket update failed: {str(error)}", context)
        global_error_handler._store_error(websocket_error)
        global_error_handler._log_error(websocket_error)
        
        # Store failed update for potential retry later
        if not hasattr(self, '_failed_updates'):
            self._failed_updates = []
        
        self._failed_updates.append({
            "run_id": run_id,
            "data": data,
            "timestamp": time.time(),
            "error": str(error)
        })
        
        # Keep only recent failed updates (max 10)
        if len(self._failed_updates) > 10:
            self._failed_updates = self._failed_updates[-10:]

    async def run_in_background(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        loop = asyncio.get_event_loop()
        loop.create_task(self.run(state, run_id, stream_updates))
    
    async def shutdown(self) -> None:
        """Graceful shutdown of the agent."""
        self.logger.info(f"Shutting down {self.name}")
        self.set_state(SubAgentLifecycle.SHUTDOWN)
        # Clear any remaining context
        self.context.clear()
        # Subclasses can override to add specific shutdown logic
