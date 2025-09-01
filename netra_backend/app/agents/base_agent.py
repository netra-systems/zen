from shared.isolated_environment import get_env
"""Base Agent Core Module

Main base agent class that composes functionality from focused modular components.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List

# Remove mixin imports since we're using single inheritance now
# from netra_backend.app.agents.agent_communication import AgentCommunicationMixin
# from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
# from netra_backend.app.agents.agent_observability import AgentObservabilityMixin
# from netra_backend.app.agents.agent_state import AgentStateMixin
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
from netra_backend.app.agents.interfaces import BaseAgentProtocol
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.config import get_config
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.observability import generate_llm_correlation_id
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent import SubAgentLifecycle

# Import timing components
from netra_backend.app.agents.base.timing_collector import ExecutionTimingCollector


class BaseSubAgent(ABC):
    """Base agent class with simplified single inheritance pattern.
    
    Uses WebSocketBridgeAdapter for centralized WebSocket event emission through
    the SSOT AgentWebSocketBridge. All sub-agents can emit WebSocket events:
    - emit_thinking() - For real-time reasoning visibility
    - emit_tool_executing() / emit_tool_completed() - For tool usage transparency
    - emit_progress() - For partial results and progress updates
    - emit_error() - For structured error reporting
    - emit_subagent_started() / emit_subagent_completed() - For sub-agent lifecycle
    
    CRITICAL: WebSocket bridge must be set via set_websocket_bridge() before
    any WebSocket events can be emitted. This is handled by the supervisor/execution engine.
    
    Now includes functionality from mixins directly for simplified inheritance:
    - Agent lifecycle management
    - Communication capabilities
    - State management
    - Observability features
    """
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, name: str = "BaseSubAgent", description: str = "This is the base sub-agent.", agent_id: Optional[str] = None, user_id: Optional[str] = None):
        # Initialize with simple single inheritance pattern
        super().__init__()
        
        self.llm_manager = llm_manager
        self.state = SubAgentLifecycle.PENDING
        self.name = name
        self.description = description
        self.start_time = None
        self.end_time = None
        self.context = {}  # Protected context for this agent
        self.user_id = user_id  # Deprecated - kept for backward compatibility
        self.logger = central_logger.get_logger(name)
        self.correlation_id = generate_llm_correlation_id()  # Unique ID for tracing
        self._subagent_logging_enabled = self._get_subagent_logging_enabled()
        
        # Initialize attributes required by AgentCommunicationMixin
        self.agent_id = agent_id or f"{name}_{self.correlation_id}"  # Unique agent identifier
        self._user_id = user_id  # Note underscore prefix as expected by AgentCommunicationMixin
        
        # Initialize WebSocket bridge adapter (SSOT for WebSocket events)
        self._websocket_adapter = WebSocketBridgeAdapter()
        
        # Initialize timing collector
        self.timing_collector = ExecutionTimingCollector(agent_name=name)

    # === State Management Methods (from AgentStateMixin) ===
    
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
            SubAgentLifecycle.PENDING: [
                SubAgentLifecycle.RUNNING,
                SubAgentLifecycle.FAILED,
                SubAgentLifecycle.SHUTDOWN
            ],
            SubAgentLifecycle.RUNNING: [
                SubAgentLifecycle.RUNNING,    # Allow staying in running state
                SubAgentLifecycle.COMPLETED,
                SubAgentLifecycle.FAILED,
                SubAgentLifecycle.SHUTDOWN
            ],
            SubAgentLifecycle.FAILED: [
                SubAgentLifecycle.PENDING,  # Allow retry via pending
                SubAgentLifecycle.RUNNING,  # Allow direct retry
                SubAgentLifecycle.SHUTDOWN
            ],
            SubAgentLifecycle.COMPLETED: [
                SubAgentLifecycle.RUNNING,   # Allow retry from completed state
                SubAgentLifecycle.PENDING,   # Allow reset to pending
                SubAgentLifecycle.SHUTDOWN   # Allow final shutdown
            ],
            SubAgentLifecycle.SHUTDOWN: []  # Terminal state
        }

    def get_state(self) -> SubAgentLifecycle:
        """Get current agent state."""
        return self.state
    
    # === Communication and Observability Methods ===
    
    def _log_agent_start(self, run_id: str) -> None:
        """Log agent start event."""
        if self._subagent_logging_enabled:
            self.logger.info(f"{self.name} started for run_id: {run_id}")
    
    def _log_agent_completion(self, run_id: str, status: str) -> None:
        """Log agent completion event."""
        if self._subagent_logging_enabled:
            self.logger.info(f"{self.name} {status} for run_id: {run_id}")
    
    # === Abstract Methods ===
    
    @abstractmethod
    async def execute(self, state: Optional[DeepAgentState], run_id: str = "", stream_updates: bool = False) -> Any:
        """Execute the agent. Subclasses must implement this method."""
        pass

    def _get_subagent_logging_enabled(self) -> bool:
        """Get subagent logging configuration setting."""
        import os
        # Skip heavy config loading during test collection
        if get_env().get('TEST_COLLECTION_MODE') == '1':
            return False
        try:
            config = get_config()
            return getattr(config, 'subagent_logging_enabled', True)
        except Exception:
            return True  # Default to enabled if config unavailable

    async def shutdown(self) -> None:
        """Graceful shutdown of the agent."""
        # Make shutdown idempotent - avoid multiple shutdowns
        if self.state == SubAgentLifecycle.SHUTDOWN:
            return
            
        self.logger.info(f"Shutting down {self.name}")
        self.set_state(SubAgentLifecycle.SHUTDOWN)
        
        # Clear any remaining context safely
        try:
            self.context.clear()
        except Exception as e:
            self.logger.warning(f"Error clearing context during shutdown: {e}")
        
        # Cleanup timing collector if it has pending operations
        try:
            if hasattr(self, 'timing_collector') and self.timing_collector:
                # Complete any pending timing tree to avoid resource leaks
                if hasattr(self.timing_collector, 'current_tree') and self.timing_collector.current_tree:
                    self.timing_collector.complete_execution()
        except Exception as e:
            self.logger.warning(f"Error cleaning up timing collector during shutdown: {e}")
        
        # Subclasses can override to add specific shutdown logic
    
    # WebSocket Bridge Integration Methods (SSOT Pattern)
    
    def set_websocket_bridge(self, bridge, run_id: str) -> None:
        """Set the WebSocket bridge for event emission (SSOT pattern).
        
        Args:
            bridge: The AgentWebSocketBridge instance
            run_id: The execution run ID
        """
        self._websocket_adapter.set_websocket_bridge(bridge, run_id, self.name)
    
    # Delegate WebSocket methods to the adapter
    
    async def emit_agent_started(self, message: Optional[str] = None) -> None:
        """Emit agent started event via WebSocket bridge."""
        await self._websocket_adapter.emit_agent_started(message)
    
    async def emit_thinking(self, thought: str, step_number: Optional[int] = None) -> None:
        """Emit agent thinking event via WebSocket bridge."""
        await self._websocket_adapter.emit_thinking(thought, step_number)
    
    async def emit_tool_executing(self, tool_name: str, parameters: Optional[Dict] = None) -> None:
        """Emit tool executing event via WebSocket bridge."""
        await self._websocket_adapter.emit_tool_executing(tool_name, parameters)
    
    async def emit_tool_completed(self, tool_name: str, result: Optional[Dict] = None) -> None:
        """Emit tool completed event via WebSocket bridge."""
        await self._websocket_adapter.emit_tool_completed(tool_name, result)
    
    async def emit_agent_completed(self, result: Optional[Dict] = None) -> None:
        """Emit agent completed event via WebSocket bridge."""
        await self._websocket_adapter.emit_agent_completed(result)
    
    async def emit_progress(self, content: str, is_complete: bool = False) -> None:
        """Emit progress update via WebSocket bridge."""
        await self._websocket_adapter.emit_progress(content, is_complete)
    
    async def emit_error(self, error_message: str, error_type: Optional[str] = None,
                        error_details: Optional[Dict] = None) -> None:
        """Emit error event via WebSocket bridge."""
        await self._websocket_adapter.emit_error(error_message, error_type, error_details)
    
    # Backward compatibility methods for legacy code
    
    async def emit_tool_started(self, tool_name: str, parameters: Optional[Dict] = None) -> None:
        """Backward compatibility: emit_tool_started maps to emit_tool_executing."""
        await self._websocket_adapter.emit_tool_started(tool_name, parameters)
    
    async def emit_subagent_started(self, subagent_name: str, subagent_id: Optional[str] = None) -> None:
        """Emit subagent started event via WebSocket bridge."""
        await self._websocket_adapter.emit_subagent_started(subagent_name, subagent_id)
    
    async def emit_subagent_completed(self, subagent_name: str, subagent_id: Optional[str] = None,
                                     result: Optional[Dict] = None, duration_ms: float = 0) -> None:
        """Emit subagent completed event via WebSocket bridge."""
        await self._websocket_adapter.emit_subagent_completed(subagent_name, subagent_id, result, duration_ms)
    
    def has_websocket_context(self) -> bool:
        """Check if WebSocket bridge is available."""
        return self._websocket_adapter.has_websocket_bridge()