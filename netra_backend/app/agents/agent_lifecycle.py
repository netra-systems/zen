"""Agent Lifecycle Management Module

Handles agent execution lifecycle including pre-run, post-run, and main execution flow.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from starlette.websockets import WebSocketDisconnect

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.agents.base.timing_decorators import time_operation, TimingCategory
from netra_backend.app.agents.base.timing_collector import ExecutionTimingTree


class AgentLifecycleMixin(ABC):
    """Mixin providing agent lifecycle management functionality"""
    
    @time_operation("pre_run", TimingCategory.ORCHESTRATION)
    async def _pre_run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> bool:
        """Entry conditions and setup. Returns True if agent should proceed."""
        self._initialize_agent_run(run_id)
        await self._send_starting_update(run_id, stream_updates)
        return await self.check_entry_conditions(state, run_id)
    
    @time_operation("post_run", TimingCategory.ORCHESTRATION)
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
        if not stream_updates:
            return
        # Use unified emit methods from BaseAgent's WebSocketBridgeAdapter
        if status == "completed":
            await self.emit_agent_completed({"execution_time": execution_time})
        else:
            await self.emit_error(f"{self.name} {status}", "execution_failure")
    
    async def run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Main run method with lifecycle management."""
        # Start timing execution tree
        if hasattr(self, 'timing_collector'):
            timing_tree = self.timing_collector.start_execution(correlation_id=run_id)
        
        try:
            success = await self._execute_with_conditions(state, run_id, stream_updates)
            if success:
                await self._post_run(state, run_id, stream_updates, success=True)
        except WebSocketDisconnect as e:
            await self._handle_websocket_disconnect(e, state, run_id, stream_updates)
        except Exception as e:
            await self._handle_and_reraise_error(e, state, run_id, stream_updates)
        finally:
            # Complete timing execution tree
            if hasattr(self, 'timing_collector'):
                completed_tree = self.timing_collector.complete_execution()
                if completed_tree:
                    self.logger.debug(f"Execution timing completed: {completed_tree.get_total_duration_ms():.2f}ms")
    
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
        if not stream_updates:
            return
        try:
            message = f"Entry conditions not met for {self.name}"
            await self.emit_error(message, "entry_condition_failure")
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
        if not stream_updates:
            return
        try:
            await self.emit_error(f"{self.name} encountered an error: {str(error)}", "execution_error")
        except (WebSocketDisconnect, RuntimeError, ConnectionError):
            self.logger.debug(f"WebSocket disconnected when sending error")
    
    
    @abstractmethod
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """The main execution logic of the agent. Subclasses must implement this."""
        pass
    
    @time_operation("check_entry_conditions", TimingCategory.VALIDATION)
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if agent should proceed. Override in subclasses for specific conditions."""
        return True
    
    @time_operation("cleanup", TimingCategory.ORCHESTRATION)
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
        if stream_updates:
            await self.emit_agent_started(f"{self.name} is starting")
    
    async def _complete_agent_run(
        self, run_id: str, stream_updates: bool, status: str, execution_time: float, state: DeepAgentState
    ) -> None:
        """Complete agent run with logging and updates."""
        self._log_execution_completion(run_id, status, execution_time)
        await self._send_completion_update(run_id, stream_updates, status, execution_time)
        await self.cleanup(state, run_id)
    
    def _build_completion_data(self, status: str, execution_time: float) -> Dict[str, Any]:
        """Build completion update data dictionary."""
        return {
            "status": status,
            "message": f"{self.name} {status}",
            "execution_time": execution_time
        }
    
    @time_operation("execute_with_conditions", TimingCategory.ORCHESTRATION)
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