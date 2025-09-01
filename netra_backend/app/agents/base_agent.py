from shared.isolated_environment import get_env
"""Base Agent Core Module

Main base agent class that composes functionality from focused modular components.
"""

from abc import ABC
from typing import Dict, Optional

from netra_backend.app.agents.agent_communication import AgentCommunicationMixin

# Import modular components
from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
from netra_backend.app.agents.agent_observability import AgentObservabilityMixin
from netra_backend.app.agents.agent_state import AgentStateMixin
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


class BaseSubAgent(
    AgentLifecycleMixin, 
    AgentCommunicationMixin, 
    AgentStateMixin, 
    AgentObservabilityMixin,
    ABC
):
    """Base agent class combining all agent functionality through modular mixins.
    
    Uses WebSocketBridgeAdapter for centralized WebSocket event emission through
    the SSOT AgentWebSocketBridge. All sub-agents can emit WebSocket events:
    - emit_thinking() - For real-time reasoning visibility
    - emit_tool_executing() / emit_tool_completed() - For tool usage transparency
    - emit_progress() - For partial results and progress updates
    - emit_error() - For structured error reporting
    - emit_subagent_started() / emit_subagent_completed() - For sub-agent lifecycle
    
    CRITICAL: WebSocket bridge must be set via set_websocket_bridge() before
    any WebSocket events can be emitted. This is handled by the supervisor/execution engine.
    """
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, name: str = "BaseSubAgent", description: str = "This is the base sub-agent."):
        self.llm_manager = llm_manager
        self.state = SubAgentLifecycle.PENDING
        self.name = name
        self.description = description
        self.start_time = None
        self.end_time = None
        self.context = {}  # Protected context for this agent
        self.websocket_manager = None  # Deprecated - kept for backward compatibility
        self.user_id = None  # Deprecated - kept for backward compatibility
        self.logger = central_logger.get_logger(name)
        self.correlation_id = generate_llm_correlation_id()  # Unique ID for tracing
        self._subagent_logging_enabled = self._get_subagent_logging_enabled()
        
        # Initialize WebSocket bridge adapter (SSOT for WebSocket events)
        self._websocket_adapter = WebSocketBridgeAdapter()
        
        # Initialize timing collector
        self.timing_collector = ExecutionTimingCollector(agent_name=name)

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
    
    # Legacy WebSocketContextMixin compatibility methods (deprecated)
    
    def set_websocket_context(self, context, notifier) -> None:
        """DEPRECATED: Use set_websocket_bridge() instead.
        
        Kept for backward compatibility with legacy code.
        """
        self.logger.warning(f"DEPRECATED: {self.name} using legacy set_websocket_context(). "
                          "Should use set_websocket_bridge() with AgentWebSocketBridge instead.")
        # Store for potential legacy usage
        self._legacy_context = context
        self._legacy_notifier = notifier
    
    def has_websocket_context(self) -> bool:
        """Check if WebSocket bridge is available."""
        return self._websocket_adapter.has_websocket_bridge()
    
    def propagate_websocket_context_to_state(self, state) -> None:
        """DEPRECATED: No longer needed with bridge pattern."""
        pass  # No-op for backward compatibility