"""Agent Lifecycle Management Module

Handles agent execution lifecycle including pre-run, post-run, and main execution flow.
"""

import time
from abc import ABC, abstractmethod
from typing import Optional

from starlette.websockets import WebSocketDisconnect

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.Agent import SubAgentLifecycle


class AgentLifecycleMixin(ABC):
    """Mixin providing agent lifecycle management functionality"""
    
    async def _pre_run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> bool:
        """Entry conditions and setup. Returns True if agent should proceed."""
        self._initialize_agent_run(run_id)
        await self._send_starting_update(run_id, stream_updates)
        return await self.check_entry_conditions(state, run_id)
    
    async def _post_run(self, state: DeepAgentState, run_id: str, stream_updates: bool, success: bool) -> None:
        """Exit conditions and cleanup."""
        execution_time = self._finalize_execution_timing()
        status = self._update_lifecycle_status(success)
        await self._complete_agent_run(run_id, stream_updates, status, execution_time, state)
    
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
        completion_data = self._build_completion_data(status, execution_time)
        await self._send_update(run_id, completion_data)
    
    async def run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Main run method with lifecycle management."""
        try:
            success = await self._execute_with_conditions(state, run_id, stream_updates)
            if success:
                await self._post_run(state, run_id, stream_updates, success=True)
        except WebSocketDisconnect as e:
            await self._handle_websocket_disconnect(e, state, run_id, stream_updates)
        except Exception as e:
            await self._handle_and_reraise_error(e, state, run_id, stream_updates)
    
    async def _handle_and_reraise_error(self, e: Exception, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Handle execution error and reraise."""
        await self._handle_execution_error(e, state, run_id, stream_updates)
        raise
    
    async def _handle_entry_conditions(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> bool:
        """Handle entry condition checks and failures."""
        if await self._pre_run(state, run_id, stream_updates):
            return True
        await self._handle_entry_failure(run_id, stream_updates, state)
        return False
    
    async def _send_entry_condition_warning(self, run_id: str, stream_updates: bool) -> None:
        """Send warning about failed entry conditions."""
        if not (stream_updates and self.websocket_manager):
            return
        try:
            await self._send_websocket_warning(run_id)
        except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
            self.logger.debug(f"WebSocket disconnected when sending warning: {e}")
    
    async def _send_websocket_warning(self, run_id: str) -> None:
        """Send WebSocket warning about entry conditions."""
        ws_user_id = self._get_websocket_user_id(run_id)
        message = f"Entry conditions not met for {self.name}"
        await self.websocket_manager.send_agent_log(ws_user_id, "warning", message, self.name)
    
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
            await self._send_websocket_error(error, run_id)
        except (WebSocketDisconnect, RuntimeError, ConnectionError):
            self.logger.debug(f"WebSocket disconnected when sending error")
    
    async def _send_websocket_error(self, error: Exception, run_id: str) -> None:
        """Send WebSocket error notification."""
        ws_user_id = self._get_websocket_user_id(run_id)
        error_message = f"{self.name} encountered an error: {str(error)}"
        await self.websocket_manager.send_error(ws_user_id, error_message, self.name)
    
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
    
    def _initialize_agent_run(self, run_id: str) -> None:
        """Initialize agent run with logging and state."""
        self.logger.info(f"{self.name} checking entry conditions for run_id: {run_id}")
        self.start_time = time.time()
        self.set_state(SubAgentLifecycle.RUNNING)
        self._log_agent_start(run_id)
    
    async def _send_starting_update(self, run_id: str, stream_updates: bool) -> None:
        """Send starting update if streaming enabled."""
        if stream_updates and self.websocket_manager:
            starting_data = {"status": "starting", "message": f"{self.name} is starting"}
            await self._send_update(run_id, starting_data)
    
    async def _complete_agent_run(
        self, run_id: str, stream_updates: bool, status: str, execution_time: float, state: DeepAgentState
    ) -> None:
        """Complete agent run with logging and updates."""
        self._log_execution_completion(run_id, status, execution_time)
        await self._send_completion_update(run_id, stream_updates, status, execution_time)
        await self.cleanup(state, run_id)
    
    def _build_completion_data(self, status: str, execution_time: float) -> dict:
        """Build completion update data dictionary."""
        return {
            "status": status,
            "message": f"{self.name} {status}",
            "execution_time": execution_time
        }
    
    async def _execute_with_conditions(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> bool:
        """Execute agent if entry conditions pass."""
        if not await self._handle_entry_conditions(state, run_id, stream_updates):
            return False
        await self.execute(state, run_id, stream_updates)
        state.step_count += 1
        return True
    
    async def _handle_entry_failure(self, run_id: str, stream_updates: bool, state: DeepAgentState) -> None:
        """Handle failed entry conditions."""
        self.logger.warning(f"{self.name} entry conditions not met for run_id: {run_id}")
        await self._send_entry_condition_warning(run_id, stream_updates)
        await self._post_run(state, run_id, stream_updates, success=False)
    
    def _get_websocket_user_id(self, run_id: str) -> str:
        """Get WebSocket user ID for messaging."""
        return self.user_id if self.user_id else run_id