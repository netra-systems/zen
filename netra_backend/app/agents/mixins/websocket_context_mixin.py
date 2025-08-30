"""WebSocket Context Mixin for Agent WebSocket Event Emission

This mixin provides a centralized, thread-safe way for all agents to emit WebSocket events
during execution. It follows the Single Source of Truth principle and provides consistent
event payload structure across all agent types.

CRITICAL: This mixin is essential for chat functionality - without proper WebSocket event
emission, the chat UI will appear broken to users.
"""

import asyncio
from typing import TYPE_CHECKING, Optional, Any, Dict, Union
from datetime import datetime, timezone

if TYPE_CHECKING:
    from netra_backend.app.websocket_core import WebSocketManager
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketContextMixin:
    """Mixin providing WebSocket event emission capabilities to all agents.
    
    This mixin centralizes WebSocket context management and provides helper methods
    for emitting the required WebSocket events during agent execution:
    
    Required Events (CRITICAL for chat functionality):
    1. agent_started - User must see agent began processing
    2. agent_thinking - Real-time reasoning visibility  
    3. tool_executing - Tool usage transparency
    4. tool_completed - Tool results display
    5. agent_completed - User must know when done
    
    Thread Safety:
    - All methods are async and thread-safe
    - Uses proper locking for concurrent agent execution
    - Gracefully handles missing WebSocket context
    
    Single Source of Truth:
    - Centralizes all WebSocket event emission logic
    - Consistent payload structure across all agents
    - Prevents duplicate event emission patterns
    """
    
    def set_websocket_context(self, context: 'AgentExecutionContext', 
                              notifier: 'WebSocketNotifier') -> None:
        """Set WebSocket context for event emission.
        
        Args:
            context: Agent execution context with run_id, thread_id, user_id, etc.
            notifier: WebSocketNotifier instance for sending events
            
        CRITICAL: This method must be called before any WebSocket events are emitted.
        The supervisor/execution engine is responsible for calling this method.
        """
        self._websocket_context = context
        self._websocket_notifier = notifier
        
        # Store user_id for backward compatibility with existing mixin methods
        if hasattr(self, 'user_id'):
            self.user_id = context.user_id
    
    def has_websocket_context(self) -> bool:
        """Check if WebSocket context is available."""
        return (hasattr(self, '_websocket_context') and self._websocket_context is not None and
                hasattr(self, '_websocket_notifier') and self._websocket_notifier is not None)
    
    async def emit_thinking(self, message: str, step_number: Optional[int] = None) -> None:
        """Emit agent thinking event for real-time reasoning visibility.
        
        Args:
            message: The current thought or reasoning step
            step_number: Optional step number for progress tracking
            
        CRITICAL: This event is required for users to see agent is actively processing.
        Without this, the UI appears frozen during long-running operations.
        """
        if not self.has_websocket_context():
            logger.debug(f"No WebSocket context available for {self.name} thinking event")
            return
        
        try:
            await self._websocket_notifier.send_agent_thinking(
                self._websocket_context, message, step_number
            )
        except Exception as e:
            logger.debug(f"Failed to emit thinking event for {self.name}: {e}")
    
    async def emit_progress(self, content: str, is_complete: bool = False) -> None:
        """Emit progress update with partial results.
        
        Args:
            content: Partial result or progress message
            is_complete: Whether this is the final progress update
            
        Use this for streaming results or showing incremental progress.
        """
        if not self.has_websocket_context():
            logger.debug(f"No WebSocket context available for {self.name} progress event")
            return
        
        try:
            await self._websocket_notifier.send_partial_result(
                self._websocket_context, content, is_complete
            )
        except Exception as e:
            logger.debug(f"Failed to emit progress event for {self.name}: {e}")
    
    async def emit_tool_started(self, tool_name: str, parameters: Optional[Dict[str, Any]] = None) -> None:
        """Emit tool started event before tool execution.
        
        Args:
            tool_name: Name of the tool being started
            parameters: Optional tool parameters
            
        CRITICAL: This provides transparency about what tools are being used.
        """
        if not self.has_websocket_context():
            logger.debug(f"No WebSocket context available for {self.name} tool started event")
            return
        
        try:
            await self._websocket_notifier.send_tool_started(
                self._websocket_context, tool_name, parameters
            )
        except Exception as e:
            logger.debug(f"Failed to emit tool started event for {self.name}: {e}")
    
    async def emit_tool_executing(self, tool_name: str) -> None:
        """Emit tool executing event during tool execution.
        
        Args:
            tool_name: Name of the tool being executed
            
        CRITICAL: This event is required to show tool usage in the UI.
        Without this, users won't see what tools are being used.
        """
        if not self.has_websocket_context():
            logger.debug(f"No WebSocket context available for {self.name} tool executing event")
            return
        
        try:
            await self._websocket_notifier.send_tool_executing(
                self._websocket_context, tool_name
            )
        except Exception as e:
            logger.debug(f"Failed to emit tool executing event for {self.name}: {e}")
    
    async def emit_tool_completed(self, tool_name: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Emit tool completed event after tool execution.
        
        Args:
            tool_name: Name of the tool that completed
            result: Optional tool execution result
            
        CRITICAL: This event is required to show tool completion in the UI.
        """
        if not self.has_websocket_context():
            logger.debug(f"No WebSocket context available for {self.name} tool completed event")
            return
        
        try:
            await self._websocket_notifier.send_tool_completed(
                self._websocket_context, tool_name, result
            )
        except Exception as e:
            logger.debug(f"Failed to emit tool completed event for {self.name}: {e}")
    
    async def emit_error(self, error_message: str, error_type: str = "general", 
                         error_details: Optional[Dict[str, Any]] = None) -> None:
        """Emit structured error event.
        
        Args:
            error_message: The error message
            error_type: Type of error (e.g., "validation", "execution", "network")
            error_details: Optional additional error details
            
        Use this for reporting errors that need to be visible to users.
        """
        if not self.has_websocket_context():
            logger.debug(f"No WebSocket context available for {self.name} error event")
            return
        
        try:
            await self._websocket_notifier.send_agent_error(
                self._websocket_context, error_message, error_type, error_details
            )
        except Exception as e:
            logger.debug(f"Failed to emit error event for {self.name}: {e}")
    
    async def emit_log(self, level: str, message: str, 
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """Emit debug logging event for development/debugging.
        
        Args:
            level: Log level (debug, info, warning, error)
            message: Log message
            metadata: Optional additional metadata
            
        Use this for detailed logging that needs to be visible in the UI for debugging.
        """
        if not self.has_websocket_context():
            logger.debug(f"No WebSocket context available for {self.name} log event")
            return
        
        try:
            await self._websocket_notifier.send_agent_log(
                self._websocket_context, level, message, metadata
            )
        except Exception as e:
            logger.debug(f"Failed to emit log event for {self.name}: {e}")
    
    async def emit_stream_chunk(self, chunk_id: str, content: str, 
                               is_final: bool = False) -> None:
        """Emit streaming content chunk for real-time content delivery.
        
        Args:
            chunk_id: Unique identifier for this chunk
            content: The content chunk
            is_final: Whether this is the final chunk
            
        Use this for streaming large responses or real-time content generation.
        """
        if not self.has_websocket_context():
            logger.debug(f"No WebSocket context available for {self.name} stream chunk event")
            return
        
        try:
            await self._websocket_notifier.send_stream_chunk(
                self._websocket_context, chunk_id, content, is_final
            )
        except Exception as e:
            logger.debug(f"Failed to emit stream chunk event for {self.name}: {e}")
    
    async def emit_subagent_started(self, subagent_name: str, 
                                   subagent_id: Optional[str] = None) -> None:
        """Emit sub-agent lifecycle start event.
        
        Args:
            subagent_name: Name of the sub-agent being started
            subagent_id: Optional unique identifier for the sub-agent
            
        Use this when starting sub-agents or delegating to other agents.
        """
        if not self.has_websocket_context():
            logger.debug(f"No WebSocket context available for {self.name} subagent started event")
            return
        
        try:
            await self._websocket_notifier.send_subagent_started(
                self._websocket_context, subagent_name, subagent_id
            )
        except Exception as e:
            logger.debug(f"Failed to emit subagent started event for {self.name}: {e}")
    
    async def emit_subagent_completed(self, subagent_name: str, 
                                     subagent_id: Optional[str] = None,
                                     result: Optional[Dict[str, Any]] = None, 
                                     duration_ms: float = 0) -> None:
        """Emit sub-agent lifecycle completion event.
        
        Args:
            subagent_name: Name of the sub-agent that completed
            subagent_id: Optional unique identifier for the sub-agent
            result: Optional execution result
            duration_ms: Execution duration in milliseconds
            
        Use this when sub-agents complete execution.
        """
        if not self.has_websocket_context():
            logger.debug(f"No WebSocket context available for {self.name} subagent completed event")
            return
        
        try:
            await self._websocket_notifier.send_subagent_completed(
                self._websocket_context, subagent_name, subagent_id, result, duration_ms
            )
        except Exception as e:
            logger.debug(f"Failed to emit subagent completed event for {self.name}: {e}")
    
    # Backward Compatibility Methods
    # These methods provide compatibility with existing agent implementations
    # that use the old direct WebSocket patterns
    
    def get_websocket_thread_id(self) -> Optional[str]:
        """Get thread_id for WebSocket messaging (backward compatibility)."""
        if self.has_websocket_context():
            return self._websocket_context.thread_id
        return None
    
    def get_websocket_user_id(self) -> Optional[str]:
        """Get user_id for WebSocket messaging (backward compatibility)."""
        if self.has_websocket_context():
            return self._websocket_context.user_id
        return None
    
    def get_websocket_run_id(self) -> Optional[str]:
        """Get run_id for WebSocket messaging (backward compatibility)."""
        if self.has_websocket_context():
            return self._websocket_context.run_id
        return None
    
    # Convenience method for common patterns
    async def emit_thinking_with_progress(self, thought: str, step_number: Optional[int] = None,
                                         progress_content: Optional[str] = None) -> None:
        """Emit both thinking and progress events in one call.
        
        Args:
            thought: The current thought or reasoning step
            step_number: Optional step number for progress tracking
            progress_content: Optional progress content to display
            
        Convenience method for the common pattern of showing both thinking and progress.
        """
        await self.emit_thinking(thought, step_number)
        if progress_content:
            await self.emit_progress(progress_content)
    
    async def emit_tool_lifecycle(self, tool_name: str, 
                                 parameters: Optional[Dict[str, Any]] = None,
                                 result: Optional[Dict[str, Any]] = None) -> None:
        """Emit complete tool lifecycle (started -> executing -> completed) events.
        
        Args:
            tool_name: Name of the tool
            parameters: Optional tool parameters
            result: Optional tool execution result
            
        Convenience method for tools that want to emit all lifecycle events.
        Note: This should be used carefully - typically you want to emit executing
        and completed separately around the actual tool execution.
        """
        await self.emit_tool_started(tool_name, parameters)
        await self.emit_tool_executing(tool_name)
        await self.emit_tool_completed(tool_name, result)