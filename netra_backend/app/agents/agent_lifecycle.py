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
    async def _pre_run(self, context: UserExecutionContext, run_id: str, stream_updates: bool) -> bool:
        """Entry conditions and setup. Returns True if agent should proceed."""
        self._initialize_agent_run(run_id)
        await self._send_starting_update(run_id, stream_updates)
        return await self.check_entry_conditions(context, run_id)

    @time_operation("post_run", TimingCategory.ORCHESTRATION)
    async def _post_run(self, context: UserExecutionContext, run_id: str, stream_updates: bool, success: bool) -> None:
        """Exit conditions and cleanup."""
        execution_time = self._finalize_execution_timing()
        status = self._update_lifecycle_status(success)
        await self._complete_agent_run(run_id, stream_updates, status, execution_time, context)

    def _finalize_execution_timing(self) -> float:
        """Finalize execution timing and return duration."""
        self.end_time = time.time()
        if self.start_time is None:
            return 0.0  # Return 0 if start_time was never set
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

    async def run(self, context: UserExecutionContext, run_id: str, stream_updates: bool) -> None:
        """Main run method with lifecycle management."""
        # Start timing execution tree
        if hasattr(self, 'timing_collector'):
            timing_tree = self.timing_collector.start_execution(correlation_id=run_id)

        try:
            success = await self._execute_with_conditions(context, run_id, stream_updates)
            if success:
                await self._post_run(context, run_id, stream_updates, success=True)
        except WebSocketDisconnect as e:
            await self._handle_websocket_disconnect(e, context, run_id, stream_updates)
        except Exception as e:
            await self._handle_and_reraise_error(e, context, run_id, stream_updates)
        finally:
            # Complete timing execution tree
            if hasattr(self, 'timing_collector'):
                completed_tree = self.timing_collector.complete_execution()
                if completed_tree:
                    self.logger.debug(f"Execution timing completed: {completed_tree.get_total_duration_ms():.2f}ms")

    async def _handle_and_reraise_error(self, e: Exception, context: UserExecutionContext, run_id: str, stream_updates: bool) -> None:
        """Handle execution error and reraise."""
        await self._handle_execution_error(e, context, run_id, stream_updates)
        raise

    async def _handle_entry_conditions(self, context: UserExecutionContext, run_id: str, stream_updates: bool) -> bool:
        """Handle entry condition checks and failures."""
        if await self._pre_run(context, run_id, stream_updates):
            return True
        await self._handle_entry_failure(run_id, stream_updates, context)
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


    async def _handle_websocket_disconnect(self, e: WebSocketDisconnect, context: UserExecutionContext, run_id: str, stream_updates: bool) -> None:
        """Handle WebSocket disconnection during execution."""
        self.logger.info(f"WebSocket disconnected during {self.name} execution: {e}")
        await self._post_run(context, run_id, stream_updates, success=False)

    async def _handle_execution_error(self, e: Exception, context: UserExecutionContext, run_id: str, stream_updates: bool) -> None:
        """Handle execution errors and send notifications."""
        self.logger.error(f"{self.name} failed for run_id: {run_id}: {e}")
        await self._send_error_notification(e, run_id, stream_updates)
        await self._post_run(context, run_id, stream_updates, success=False)

    async def _send_error_notification(self, error: Exception, run_id: str, stream_updates: bool) -> None:
        """Send error notification via WebSocket."""
        if not stream_updates:
            return
        try:
            await self.emit_error(f"{self.name} encountered an error: {str(error)}", "execution_error")
        except (WebSocketDisconnect, RuntimeError, ConnectionError):
            self.logger.debug(f"WebSocket disconnected when sending error")


    @abstractmethod
    async def execute(self, context: UserExecutionContext, run_id: str, stream_updates: bool) -> None:
        """The main execution logic of the agent. Subclasses must implement this."""
        pass

    @time_operation("check_entry_conditions", TimingCategory.VALIDATION)
    async def check_entry_conditions(self, context: UserExecutionContext, run_id: str) -> bool:
        """Check if agent should proceed. Override in subclasses for specific conditions."""
        return True

    @time_operation("cleanup", TimingCategory.ORCHESTRATION)
    async def cleanup(self, context: UserExecutionContext, run_id: str) -> None:
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
        self, run_id: str, stream_updates: bool, status: str, execution_time: float, context: UserExecutionContext
    ) -> None:
        """Complete agent run with logging and updates."""
        self._log_execution_completion(run_id, status, execution_time)
        await self._send_completion_update(run_id, stream_updates, status, execution_time)
        await self.cleanup(context, run_id)

    def _build_completion_data(self, status: str, execution_time: float) -> Dict[str, Any]:
        """Build completion update data dictionary."""
        return {
            "status": status,
            "message": f"{self.name} {status}",
            "execution_time": execution_time
        }

    @time_operation("execute_with_conditions", TimingCategory.ORCHESTRATION)
    async def _execute_with_conditions(self, context: UserExecutionContext, run_id: str, stream_updates: bool) -> bool:
        """Execute agent if entry conditions pass."""
        if not await self._handle_entry_conditions(context, run_id, stream_updates):
            return False
        await self.execute(context, run_id, stream_updates)
        # UserExecutionContext is immutable - step counting handled by agent internally
        self._increment_execution_step()
        return True

    async def _handle_entry_failure(self, run_id: str, stream_updates: bool, context: UserExecutionContext) -> None:
        """Handle failed entry conditions."""
        self.logger.warning(f"{self.name} entry conditions not met for run_id: {run_id}")
        await self._send_entry_condition_warning(run_id, stream_updates)
        await self._post_run(context, run_id, stream_updates, success=False)

    def _get_websocket_user_id(self, run_id: str) -> str:
        """Get WebSocket user ID for messaging."""
        return self.user_id if self.user_id else run_id

    def _increment_execution_step(self) -> None:
        """Increment execution step counter in agent's internal state."""
        # Store step count in the agent instance, not in UserExecutionContext
        if not hasattr(self, '_execution_steps'):
            self._execution_steps = 0
        self._execution_steps += 1


class AgentLifecycleManager:
    """
    SSOT-compliant Agent Lifecycle Management class

    Provides centralized lifecycle management for agents with proper factory pattern support
    and multi-user isolation capabilities.
    """

    def __init__(self, registry=None):
        """Initialize lifecycle manager with optional registry reference."""
        self._registry = registry
        self.logger = central_logger.get_logger(__name__)
        self._active_agents = {}  # user_id -> agent_dict mapping
        self._execution_stats = {}  # user_id -> stats mapping

    def register_agent_lifecycle(self, user_id: str, agent_name: str, agent_instance):
        """Register an agent for lifecycle tracking."""
        if user_id not in self._active_agents:
            self._active_agents[user_id] = {}

        self._active_agents[user_id][agent_name] = {
            'agent': agent_instance,
            'created_at': time.time(),
            'executions': 0,
            'total_execution_time': 0.0
        }

        self.logger.debug(f"Registered agent {agent_name} for user {user_id}")

    def unregister_agent_lifecycle(self, user_id: str, agent_name: str):
        """Unregister an agent from lifecycle tracking."""
        if user_id in self._active_agents and agent_name in self._active_agents[user_id]:
            del self._active_agents[user_id][agent_name]
            if not self._active_agents[user_id]:  # Remove user entry if no agents
                del self._active_agents[user_id]

            self.logger.debug(f"Unregistered agent {agent_name} for user {user_id}")

    def get_active_agents(self, user_id: str = None):
        """Get active agents for a specific user or all users."""
        if user_id:
            return self._active_agents.get(user_id, {})
        return self._active_agents

    def update_execution_stats(self, user_id: str, agent_name: str, execution_time: float):
        """Update execution statistics for an agent."""
        if user_id in self._active_agents and agent_name in self._active_agents[user_id]:
            agent_info = self._active_agents[user_id][agent_name]
            agent_info['executions'] += 1
            agent_info['total_execution_time'] += execution_time

            self.logger.debug(f"Updated stats for agent {agent_name} (user {user_id}): "
                            f"{agent_info['executions']} executions, "
                            f"{agent_info['total_execution_time']:.2f}s total")

    def cleanup_user_agents(self, user_id: str):
        """Clean up all agents for a specific user."""
        if user_id in self._active_agents:
            agent_count = len(self._active_agents[user_id])
            del self._active_agents[user_id]
            self.logger.info(f"Cleaned up {agent_count} agents for user {user_id}")

    def get_lifecycle_summary(self, user_id: str = None):
        """Get lifecycle summary statistics."""
        if user_id:
            return {
                'user_id': user_id,
                'active_agents': len(self._active_agents.get(user_id, {})),
                'agents': self._active_agents.get(user_id, {})
            }

        return {
            'total_users': len(self._active_agents),
            'total_agents': sum(len(agents) for agents in self._active_agents.values()),
            'users': list(self._active_agents.keys())
        }

    @classmethod
    def create_for_registry(cls, registry):
        """Factory method to create lifecycle manager for a specific registry."""
        return cls(registry=registry)