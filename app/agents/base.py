"""Base agent class and interfaces."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import asyncio
import time

from app.llm.llm_manager import LLMManager
from app.schemas import SubAgentLifecycle, SubAgentUpdate, SubAgentState
from app.schemas.websocket_unified import WebSocketMessage, WebSocketMessageType
from app.agents.state import DeepAgentState
from app.logging_config import central_logger
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
            try:
                await self._send_update(run_id, {"status": "starting", "message": f"{self.name} is starting"})
            except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                self.logger.debug(f"WebSocket disconnected when sending start update: {e}")
        
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
            try:
                await self._send_update(run_id, {
                    "status": status,
                    "message": f"{self.name} {status}",
                    "execution_time": execution_time
                })
            except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                self.logger.debug(f"WebSocket disconnected when sending finish update: {e}")
        
        # Cleanup
        await self.cleanup(state, run_id)
    
    async def run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Main run method with lifecycle management."""
        try:
            # Check entry conditions
            if not await self._pre_run(state, run_id, stream_updates):
                self.logger.warning(f"{self.name} entry conditions not met for run_id: {run_id}")
                if stream_updates and self.websocket_manager:
                    try:
                        ws_user_id = self.user_id if self.user_id else run_id
                        await self.websocket_manager.send_agent_log(
                            ws_user_id, "warning", 
                            f"Entry conditions not met for {self.name}",
                            self.name
                        )
                    except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                        self.logger.debug(f"WebSocket disconnected when sending warning: {e}")
                await self._post_run(state, run_id, stream_updates, success=False)
                return
            
            # Execute the agent's main logic
            await self.execute(state, run_id, stream_updates)
            
            # Exit successfully
            await self._post_run(state, run_id, stream_updates, success=True)
            
        except WebSocketDisconnect as e:
            self.logger.info(f"WebSocket disconnected during {self.name} execution: {e}")
            await self._post_run(state, run_id, stream_updates, success=False)
            # Don't re-raise WebSocket disconnects
        except Exception as e:
            self.logger.error(f"{self.name} failed for run_id: {run_id}: {e}")
            if stream_updates and self.websocket_manager:
                try:
                    ws_user_id = self.user_id if self.user_id else run_id
                    await self.websocket_manager.send_error(
                        ws_user_id, 
                        f"{self.name} encountered an error: {str(e)}",
                        self.name
                    )
                except (WebSocketDisconnect, RuntimeError, ConnectionError):
                    self.logger.debug(f"WebSocket disconnected when sending error")
            await self._post_run(state, run_id, stream_updates, success=False)
            raise
    
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
    
    async def _send_update(self, run_id: str, data: Dict[str, Any]) -> None:
        """Send WebSocket update for this agent using unified types."""
        if self.websocket_manager:
            try:
                # Create a proper BaseMessage object
                message_content = data.get("message", "")
                message = SystemMessage(content=message_content)
                
                sub_agent_state = SubAgentState(
                    messages=[message],
                    next_node="",
                    lifecycle=self.get_state()
                )
                # Get user_id from supervisor if available, otherwise use run_id
                ws_user_id = getattr(self.websocket_manager, '_current_user_id', run_id) if hasattr(self.websocket_manager, '_current_user_id') else run_id
                
                # Create properly typed SubAgentUpdate payload
                update_payload = SubAgentUpdate(
                    sub_agent_name=self.name,
                    state=sub_agent_state
                )
                
                # Use unified WebSocketMessage type
                websocket_message = WebSocketMessage(
                    type=WebSocketMessageType.SUB_AGENT_UPDATE,
                    payload=update_payload.model_dump()
                )
                
                await self.websocket_manager.send_message(
                    ws_user_id,
                    websocket_message.model_dump()
                )
            except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                self.logger.debug(f"WebSocket disconnected when sending update: {e}")
                # Don't re-raise, just log and continue

    async def run_in_background(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        loop = asyncio.get_event_loop()
        loop.create_task(self.run(state, run_id, stream_updates))
    
    async def shutdown(self) -> None:
        """Graceful shutdown of the agent."""
        self.logger.info(f"Shutting down {self.name}")
        self.set_state(SubAgentLifecycle.SHUTDOWN)
        # Clear any remaining context
        self.context.clear()
        # Subclasses can override to add specific shutdown logic
