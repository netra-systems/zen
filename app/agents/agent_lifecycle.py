"""Agent Lifecycle Management Module

Handles agent execution lifecycle including pre-run, post-run, and main execution flow.
"""

import time
from typing import Optional
from abc import ABC, abstractmethod
from starlette.websockets import WebSocketDisconnect

from app.schemas import SubAgentLifecycle
from app.agents.state import DeepAgentState
from app.logging_config import central_logger


class AgentLifecycleMixin(ABC):
    """Mixin providing agent lifecycle management functionality"""
    
    async def _pre_run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> bool:
        """Entry conditions and setup. Returns True if agent should proceed."""
        self.logger.info(f"{self.name} checking entry conditions for run_id: {run_id}")
        self.start_time = time.time()
        self.set_state(SubAgentLifecycle.RUNNING)
        
        # Log agent starting communication
        self._log_agent_start(run_id)
        
        # Stream update that agent is starting
        if stream_updates and self.websocket_manager:
            await self._send_update(run_id, {"status": "starting", "message": f"{self.name} is starting"})
        
        # Subclasses can override to add specific entry conditions
        return await self.check_entry_conditions(state, run_id)
    
    async def _post_run(self, state: DeepAgentState, run_id: str, stream_updates: bool, success: bool) -> None:
        """Exit conditions and cleanup."""
        execution_time = self._finalize_execution_timing()
        status = self._update_lifecycle_status(success)
        self._log_execution_completion(run_id, status, execution_time)
        await self._send_completion_update(run_id, stream_updates, status, execution_time)
        await self.cleanup(state, run_id)
    
    def _finalize_execution_timing(self) -> float:
        """Finalize execution timing and return duration."""
        self.end_time = time.time()
        return self.end_time - self.start_time
    
    def _update_lifecycle_status(self, success: bool) -> str:
        """Update lifecycle state and return status string."""
        if success:
            self.set_state(SubAgentLifecycle.COMPLETED)
            return "completed"
        else:
            self.set_state(SubAgentLifecycle.FAILED)
            return "failed"
    
    def _log_execution_completion(self, run_id: str, status: str, execution_time: float) -> None:
        """Log execution completion details."""
        self.logger.info(f"{self.name} {status} for run_id: {run_id} in {execution_time:.2f}s")
        self._log_agent_completion(run_id, status)
    
    async def _send_completion_update(self, run_id: str, stream_updates: bool, status: str, execution_time: float) -> None:
        """Send completion update via WebSocket."""
        if not (stream_updates and self.websocket_manager):
            return
        
        await self._send_update(run_id, {
            "status": status,
            "message": f"{self.name} {status}",
            "execution_time": execution_time
        })
    
    async def run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Main run method with lifecycle management."""
        try:
            if not await self._handle_entry_conditions(state, run_id, stream_updates):
                return
            
            await self.execute(state, run_id, stream_updates)
            
            # Increment step count on successful completion
            state.step_count += 1
            
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