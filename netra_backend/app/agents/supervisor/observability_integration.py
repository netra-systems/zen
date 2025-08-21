"""Observability integration module for supervisor components.

Provides hook registration and integration helpers for existing components.
Each function must be ≤8 lines as per architecture requirements.
"""

from typing import Dict, List, Callable, Any, Optional
from netra_backend.app.logging_config import central_logger
from netra_backend.app.llm.observability import generate_llm_correlation_id
from netra_backend.app.observability_flow import get_supervisor_flow_logger

logger = central_logger.get_logger(__name__)


class ObservabilityHookRegistry:
    """Manages observability hooks for supervisor components."""

    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}
        self.flow_logger = get_supervisor_flow_logger()
        self._registered_events = self._init_event_types()

    def _init_event_types(self) -> List[str]:
        """Initialize supported event types."""
        return [
            "flow_started", "flow_completed", "step_started", "step_completed",
            "decision_made", "parallel_execution", "sequential_execution",
            "retry_attempt", "fallback_triggered", "todo_added", "todo_completed"
        ]

    def register_hook(self, event_type: str, hook_func: Callable) -> None:
        """Register a hook for a specific event type."""
        if event_type not in self._registered_events:
            logger.warning(f"Unknown event type: {event_type}")
            return
        if event_type not in self._hooks:
            self._hooks[event_type] = []
        self._hooks[event_type].append(hook_func)

    def trigger_hooks(self, event_type: str, **kwargs) -> None:
        """Trigger all hooks for an event type."""
        if event_type not in self._hooks:
            return
        for hook in self._hooks[event_type]:
            self._execute_hook_safely(hook, event_type, **kwargs)

    def _execute_hook_safely(self, hook: Callable, event_type: str, **kwargs) -> None:
        """Execute hook with error handling."""
        try:
            hook(**kwargs)
        except Exception as e:
            logger.error(f"Hook failed for {event_type}: {e}")

    def get_registered_hooks(self) -> Dict[str, int]:
        """Get count of registered hooks by event type."""
        return {event: len(hooks) for event, hooks in self._hooks.items()}

    def clear_hooks(self, event_type: Optional[str] = None) -> None:
        """Clear hooks for specific event type or all."""
        if event_type:
            self._hooks.pop(event_type, None)
        else:
            self._hooks.clear()


class StateManagerIntegration:
    """Integration helpers for state manager observability."""

    def __init__(self):
        self.flow_logger = get_supervisor_flow_logger()
        self.hook_registry = ObservabilityHookRegistry()

    def log_state_transition(self, from_state: str, to_state: str, correlation_id: str) -> None:
        """Log state transition event."""
        flow_id = self.flow_logger.generate_flow_id()
        self.flow_logger.log_decision(flow_id, f"state_transition_{from_state}", to_state)
        self.hook_registry.trigger_hooks("decision_made", 
                                        decision_point=f"state_{from_state}",
                                        chosen_path=to_state, correlation_id=correlation_id)

    def log_checkpoint_operation(self, operation: str, success: bool, correlation_id: str) -> None:
        """Log checkpoint operation."""
        task_id = f"checkpoint_{operation}"
        if success:
            self.flow_logger.complete_todo_task(task_id, correlation_id)
        else:
            self.flow_logger.fail_todo_task(task_id, correlation_id, f"Checkpoint {operation} failed")

    def log_recovery_event(self, recovery_type: str, success: bool, correlation_id: str) -> None:
        """Log recovery event."""
        flow_id = self.flow_logger.generate_flow_id()
        if success:
            self.flow_logger.log_decision(flow_id, "recovery_attempt", f"success_{recovery_type}")
        else:
            self.flow_logger.log_fallback_triggered(flow_id, f"recovery_{recovery_type}", "manual_intervention")

    def register_state_hooks(self, state_change_hook: Callable, checkpoint_hook: Callable) -> None:
        """Register state management hooks."""
        self.hook_registry.register_hook("decision_made", state_change_hook)
        self.hook_registry.register_hook("todo_completed", checkpoint_hook)


class PipelineIntegration:
    """Integration helpers for pipeline execution observability."""

    def __init__(self):
        self.flow_logger = get_supervisor_flow_logger()
        self.hook_registry = ObservabilityHookRegistry()

    def create_pipeline_context(self, pipeline_id: str, steps: int) -> Dict[str, Any]:
        """Create pipeline execution context."""
        correlation_id = generate_llm_correlation_id()
        flow_id = self.flow_logger.generate_flow_id()
        self.flow_logger.start_flow(flow_id, correlation_id, steps)
        return {"flow_id": flow_id, "correlation_id": correlation_id, "pipeline_id": pipeline_id}

    def log_step_execution(self, context: Dict[str, Any], step_name: str, 
                          step_type: str, status: str) -> None:
        """Log pipeline step execution."""
        flow_id = context.get("flow_id")
        if not flow_id:
            return
        self._handle_step_status(flow_id, step_name, step_type, status)

    def _handle_step_status(self, flow_id: str, step_name: str, step_type: str, status: str) -> None:
        """Handle step status logging."""
        if status == "started":
            self.flow_logger.step_started(flow_id, step_name, step_type)
        elif status == "completed":
            self.flow_logger.step_completed(flow_id, step_name, step_type)

    def log_execution_strategy(self, context: Dict[str, Any], 
                              strategy: str, agents: List[str]) -> None:
        """Log pipeline execution strategy."""
        flow_id = context.get("flow_id")
        if not flow_id:
            return
        self._handle_strategy_logging(flow_id, strategy, agents)

    def _handle_strategy_logging(self, flow_id: str, strategy: str, agents: List[str]) -> None:
        """Handle strategy-specific logging."""
        if strategy == "parallel":
            self.flow_logger.log_parallel_execution(flow_id, agents)
        elif strategy == "sequential":
            self.flow_logger.log_sequential_execution(flow_id, agents)

    def complete_pipeline_context(self, context: Dict[str, Any]) -> None:
        """Complete pipeline execution context."""
        flow_id = context.get("flow_id")
        if flow_id:
            self.flow_logger.complete_flow(flow_id)

    def register_pipeline_hooks(self, step_hook: Callable, completion_hook: Callable) -> None:
        """Register pipeline execution hooks."""
        self.hook_registry.register_hook("step_completed", step_hook)
        self.hook_registry.register_hook("flow_completed", completion_hook)


class AgentExecutionIntegration:
    """Integration helpers for agent execution observability."""

    def __init__(self):
        self.flow_logger = get_supervisor_flow_logger()
        self.hook_registry = ObservabilityHookRegistry()

    def enhance_execution_context(self, context: Any, flow_id: str, correlation_id: str) -> None:
        """Enhance execution context with observability data."""
        setattr(context, 'flow_id', flow_id)
        setattr(context, 'correlation_id', correlation_id)
        setattr(context, 'observability_enabled', True)

    def log_agent_start(self, agent_name: str, context: Dict[str, Any]) -> None:
        """Log agent execution start."""
        flow_id = context.get("flow_id")
        correlation_id = context.get("correlation_id", generate_llm_correlation_id())
        if flow_id:
            self.flow_logger.step_started(flow_id, agent_name, "agent")
        self.hook_registry.trigger_hooks("step_started", agent_name=agent_name, 
                                        flow_id=flow_id, correlation_id=correlation_id)

    def log_agent_completion(self, agent_name: str, context: Dict[str, Any], success: bool) -> None:
        """Log agent execution completion."""
        flow_id = context.get("flow_id")
        correlation_id = context.get("correlation_id", "")
        self._log_agent_step_completion(flow_id, agent_name)
        self._trigger_completion_hooks(agent_name, flow_id, correlation_id, success)

    def _log_agent_step_completion(self, flow_id: str, agent_name: str) -> None:
        """Log agent step completion."""
        if flow_id:
            self.flow_logger.step_completed(flow_id, agent_name, "agent")

    def _trigger_completion_hooks(self, agent_name: str, flow_id: str, correlation_id: str, success: bool) -> None:
        """Trigger completion event hooks."""
        event_type = "step_completed" if success else "step_failed"
        self.hook_registry.trigger_hooks(event_type, agent_name=agent_name,
                                        flow_id=flow_id, correlation_id=correlation_id, success=success)

    def log_retry_event(self, agent_name: str, attempt_num: int, context: Dict[str, Any]) -> None:
        """Log agent retry event."""
        flow_id = context.get("flow_id")
        if flow_id:
            self.flow_logger.log_retry_attempt(flow_id, agent_name, attempt_num)
        self.hook_registry.trigger_hooks("retry_attempt", agent_name=agent_name,
                                        attempt_num=attempt_num, flow_id=flow_id)

    def log_fallback_event(self, failed_agent: str, fallback_agent: str, context: Dict[str, Any]) -> None:
        """Log agent fallback event."""
        flow_id = context.get("flow_id")
        if flow_id:
            self.flow_logger.log_fallback_triggered(flow_id, failed_agent, fallback_agent)
        self.hook_registry.trigger_hooks("fallback_triggered", failed_agent=failed_agent,
                                        fallback_agent=fallback_agent, flow_id=flow_id)

    def register_agent_hooks(self, start_hook: Callable, completion_hook: Callable, 
                           retry_hook: Callable) -> None:
        """Register agent execution hooks."""
        self.hook_registry.register_hook("step_started", start_hook)
        self.hook_registry.register_hook("step_completed", completion_hook)
        self.hook_registry.register_hook("retry_attempt", retry_hook)


class WebSocketIntegration:
    """Integration helpers for WebSocket observability events."""

    def __init__(self):
        self.flow_logger = get_supervisor_flow_logger()

    def log_websocket_event(self, event_type: str, thread_id: str, 
                           correlation_id: str, data_size: int) -> None:
        """Log WebSocket communication event."""
        task_id = f"websocket_{event_type}_{thread_id}"
        if event_type == "send":
            self.flow_logger.add_todo_task(task_id, f"Send WebSocket message to {thread_id}", 
                                         "medium", correlation_id)
            self.flow_logger.complete_todo_task(task_id, correlation_id)

    def log_connection_event(self, event_type: str, thread_id: str, correlation_id: str) -> None:
        """Log WebSocket connection event."""
        flow_id = self.flow_logger.generate_flow_id()
        self.flow_logger.log_decision(flow_id, f"websocket_{event_type}", thread_id)

    def create_websocket_context(self, thread_id: str) -> Dict[str, str]:
        """Create WebSocket context for observability."""
        correlation_id = generate_llm_correlation_id()
        return {"thread_id": thread_id, "correlation_id": correlation_id}


# Global integration instances
_hook_registry: Optional[ObservabilityHookRegistry] = None
_state_integration: Optional[StateManagerIntegration] = None
_pipeline_integration: Optional[PipelineIntegration] = None
_agent_integration: Optional[AgentExecutionIntegration] = None
_websocket_integration: Optional[WebSocketIntegration] = None


def get_hook_registry() -> ObservabilityHookRegistry:
    """Get global hook registry instance."""
    global _hook_registry
    if _hook_registry is None:
        _hook_registry = ObservabilityHookRegistry()
    return _hook_registry


def get_state_integration() -> StateManagerIntegration:
    """Get global state manager integration instance."""
    global _state_integration
    if _state_integration is None:
        _state_integration = StateManagerIntegration()
    return _state_integration


def get_pipeline_integration() -> PipelineIntegration:
    """Get global pipeline integration instance."""
    global _pipeline_integration
    if _pipeline_integration is None:
        _pipeline_integration = PipelineIntegration()
    return _pipeline_integration


def get_agent_integration() -> AgentExecutionIntegration:
    """Get global agent execution integration instance."""
    global _agent_integration
    if _agent_integration is None:
        _agent_integration = AgentExecutionIntegration()
    return _agent_integration


def get_websocket_integration() -> WebSocketIntegration:
    """Get global WebSocket integration instance."""
    global _websocket_integration
    if _websocket_integration is None:
        _websocket_integration = WebSocketIntegration()
    return _websocket_integration