"""Enhanced tool execution with WebSocket notifications.

Business Value: Real-time tool execution status for improved UX.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from netra_backend.app.websocket_core import WebSocketManager

from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.tool import ToolInput, ToolResult

logger = central_logger.get_logger(__name__)


class EnhancedToolExecutionEngine(ToolExecutionEngine):
    """Tool execution engine with WebSocket notifications."""
    
    def __init__(self, websocket_manager: Optional['WebSocketManager'] = None):
        """Initialize with optional WebSocket manager."""
        super().__init__()
        self.websocket_manager = websocket_manager
        self.websocket_notifier = WebSocketNotifier(websocket_manager) if websocket_manager else None
    
    async def execute_tool_with_input(self, tool_input: ToolInput, tool: Any, 
                                     kwargs: Dict[str, Any]) -> ToolResult:
        """Execute tool with WebSocket notifications."""
        # Get context from kwargs if available
        context = kwargs.get('context')
        tool_name = getattr(tool, 'name', str(tool))
        
        # Send tool executing notification
        if context and self.websocket_notifier:
            await self.websocket_notifier.send_tool_executing(context, tool_name)
        
        try:
            # Execute the actual tool
            result = await super().execute_tool_with_input(tool_input, tool, kwargs)
            
            # Send tool completed notification
            if context and self.websocket_notifier:
                result_dict = {
                    "status": "success",
                    "output": str(result)[:500] if result else None
                }
                await self.websocket_notifier.send_tool_completed(
                    context, tool_name, result_dict
                )
            
            return result
            
        except Exception as e:
            # Send error notification
            if context and self.websocket_notifier:
                error_dict = {
                    "status": "error",
                    "error": str(e)
                }
                await self.websocket_notifier.send_tool_completed(
                    context, tool_name, error_dict
                )
            raise
    
    async def execute_with_state(self, tool: Any, tool_name: str, 
                                parameters: Dict[str, Any], state: Any, 
                                run_id: str) -> Any:
        """Execute tool with state and WebSocket notifications."""
        # Create context for notifications
        context = None
        if self.websocket_notifier:
            context = AgentExecutionContext(
                agent_name="ToolExecutor",
                run_id=run_id,
                thread_id=getattr(state, 'thread_id', run_id),
                user_id=getattr(state, 'user_id', run_id)
            )
            
            # Send tool executing notification
            await self.websocket_notifier.send_tool_executing(context, tool_name)
        
        try:
            # Execute the tool
            result = await super().execute_with_state(
                tool, tool_name, parameters, state, run_id
            )
            
            # Send tool completed notification
            if context and self.websocket_notifier:
                result_dict = {
                    "status": "success",
                    "result": result.result if hasattr(result, 'result') else str(result)
                }
                await self.websocket_notifier.send_tool_completed(
                    context, tool_name, result_dict
                )
            
            return result
            
        except Exception as e:
            # Send error notification
            if context and self.websocket_notifier:
                error_dict = {
                    "status": "error",
                    "error": str(e)
                }
                await self.websocket_notifier.send_tool_completed(
                    context, tool_name, error_dict
                )
            raise


def enhance_tool_dispatcher_with_notifications(tool_dispatcher, websocket_manager):
    """Enhance existing tool dispatcher with WebSocket notifications.
    
    This function wraps the tool dispatcher's executor with enhanced notifications.
    """
    if hasattr(tool_dispatcher, 'executor'):
        # Replace executor with enhanced version
        enhanced_executor = EnhancedToolExecutionEngine(websocket_manager)
        # Preserve any existing state
        if hasattr(tool_dispatcher.executor, '_core_engine'):
            enhanced_executor._core_engine = tool_dispatcher.executor._core_engine
        tool_dispatcher.executor = enhanced_executor
        logger.info("Enhanced tool dispatcher with WebSocket notifications")
    else:
        logger.warning("Tool dispatcher does not have executor attribute")
    
    return tool_dispatcher