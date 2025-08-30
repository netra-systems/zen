"""WebSocket Context Mixin for Sub-Agents

Provides standardized WebSocket event emission capabilities for sub-agents
to enable real-time user interface updates during agent execution.

Business Value: Essential for user experience - prevents UI from appearing broken
BVJ: ALL segments | User Experience | Mission-critical chat functionality
"""

import time
from typing import Any, Dict, Optional, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketContextMixin:
    """Mixin to provide WebSocket event emission capabilities to sub-agents.
    
    This mixin enables sub-agents to emit the 5 critical WebSocket events:
    1. agent_started - Agent begins processing
    2. agent_thinking - Real-time reasoning visibility  
    3. tool_executing - Tool usage transparency
    4. tool_completed - Tool results display
    5. agent_completed - User notification when done
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._websocket_notifier: Optional['WebSocketNotifier'] = None
        self._execution_context: Optional['AgentExecutionContext'] = None
        self._websocket_enabled = False
    
    def set_websocket_context(self, notifier: 'WebSocketNotifier', 
                             context: 'AgentExecutionContext') -> None:
        """Set WebSocket context for event emissions."""
        self._websocket_notifier = notifier
        self._execution_context = context
        self._websocket_enabled = True
        logger.debug(f"WebSocket context enabled for {self.__class__.__name__}")
    
    def clear_websocket_context(self) -> None:
        """Clear WebSocket context."""
        self._websocket_notifier = None
        self._execution_context = None
        self._websocket_enabled = False
    
    @property
    def websocket_enabled(self) -> bool:
        """Check if WebSocket context is available."""
        return (self._websocket_enabled and 
                self._websocket_notifier is not None and
                self._execution_context is not None)
    
    async def emit_agent_started(self, message: str = None) -> None:
        """Emit agent started event."""
        if not self.websocket_enabled:
            return
        
        try:
            # Use subagent_started event for sub-agents
            await self._websocket_notifier.send_subagent_started(
                self._execution_context,
                subagent_name=self.__class__.__name__,
                subagent_id=f"{self._execution_context.run_id}_{self.__class__.__name__}"
            )
        except Exception as e:
            logger.debug(f"Failed to emit agent_started event: {e}")
    
    async def emit_thinking(self, thought: str, step_number: int = None) -> None:
        """Emit agent thinking event with reasoning details."""
        if not self.websocket_enabled:
            return
        
        try:
            await self._websocket_notifier.send_agent_thinking(
                self._execution_context, thought, step_number
            )
        except Exception as e:
            logger.debug(f"Failed to emit thinking event: {e}")
    
    async def emit_progress(self, message: str) -> None:
        """Emit progress update (using partial_result event)."""
        if not self.websocket_enabled:
            return
        
        try:
            await self._websocket_notifier.send_partial_result(
                self._execution_context, message, is_complete=False
            )
        except Exception as e:
            logger.debug(f"Failed to emit progress event: {e}")
    
    async def emit_tool_executing(self, tool_name: str) -> None:
        """Emit tool executing event."""
        if not self.websocket_enabled:
            return
        
        try:
            await self._websocket_notifier.send_tool_executing(
                self._execution_context, tool_name
            )
        except Exception as e:
            logger.debug(f"Failed to emit tool_executing event: {e}")
    
    async def emit_tool_completed(self, tool_name: str, result: Dict[str, Any] = None) -> None:
        """Emit tool completed event."""
        if not self.websocket_enabled:
            return
        
        try:
            await self._websocket_notifier.send_tool_completed(
                self._execution_context, tool_name, result or {}
            )
        except Exception as e:
            logger.debug(f"Failed to emit tool_completed event: {e}")
    
    async def emit_agent_completed(self, result: Dict[str, Any] = None, 
                                  duration_ms: float = 0) -> None:
        """Emit agent completed event."""
        if not self.websocket_enabled:
            return
        
        try:
            # Use subagent_completed for sub-agents
            await self._websocket_notifier.send_subagent_completed(
                self._execution_context,
                subagent_name=self.__class__.__name__,
                subagent_id=f"{self._execution_context.run_id}_{self.__class__.__name__}",
                result=result,
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.debug(f"Failed to emit agent_completed event: {e}")
    
    async def emit_error(self, error_message: str, error_type: str = None) -> None:
        """Emit agent error event."""
        if not self.websocket_enabled:
            return
        
        try:
            await self._websocket_notifier.send_agent_error(
                self._execution_context, error_message, error_type
            )
        except Exception as e:
            logger.debug(f"Failed to emit error event: {e}")
    
    def _create_execution_context_if_needed(self, run_id: str, agent_name: str = None) -> None:
        """Create minimal execution context if not available."""
        if not self._execution_context and run_id:
            # Import here to avoid circular imports
            from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
            
            self._execution_context = AgentExecutionContext(
                run_id=run_id,
                agent_name=agent_name or self.__class__.__name__,
                thread_id=run_id,  # Use run_id as thread_id if not available
                user_id=None,
                start_time=time.time()
            )


class WebSocketCapableAgent(ABC):
    """Abstract base class for agents that support WebSocket events.
    
    Defines the interface for agents that can emit WebSocket events
    during their execution lifecycle.
    """
    
    @abstractmethod
    async def setup_websocket_context(self, notifier: 'WebSocketNotifier', 
                                    context: 'AgentExecutionContext') -> None:
        """Setup WebSocket context for the agent."""
        pass
    
    @abstractmethod
    async def execute_with_events(self, *args, **kwargs) -> Any:
        """Execute agent logic with WebSocket event emissions."""
        pass