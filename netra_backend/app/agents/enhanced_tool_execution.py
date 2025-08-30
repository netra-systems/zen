"""Enhanced tool execution with WebSocket notifications.

Business Value: Real-time tool execution status for improved UX.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from netra_backend.app.websocket_core import WebSocketManager

from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.agents.utils import extract_thread_id
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
            # Extract thread_id using unified utility
            thread_id = extract_thread_id(state, run_id)
            
            context = AgentExecutionContext(
                agent_name="ToolExecutor",
                run_id=run_id,
                thread_id=thread_id,
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
        # Check if already enhanced
        if isinstance(tool_dispatcher.executor, EnhancedToolExecutionEngine):
            logger.debug("Tool dispatcher already enhanced with WebSocket notifications")
            return tool_dispatcher
            
        # Replace executor with enhanced version
        enhanced_executor = EnhancedToolExecutionEngine(websocket_manager)
        # Preserve any existing state
        if hasattr(tool_dispatcher.executor, '_core_engine'):
            enhanced_executor._core_engine = tool_dispatcher.executor._core_engine
        
        # Store original executor for testing/validation
        tool_dispatcher._original_executor = tool_dispatcher.executor
        tool_dispatcher.executor = enhanced_executor
        
        # Mark as enhanced for validation
        tool_dispatcher._websocket_enhanced = True
        
        logger.info("Enhanced tool dispatcher with WebSocket notifications")
    else:
        logger.warning("Tool dispatcher does not have executor attribute")
    
    return tool_dispatcher


class ContextualToolExecutor(EnhancedToolExecutionEngine):
    """Tool executor with enhanced contextual WebSocket events."""
    
    def _get_tool_purpose(self, tool_name: str, tool_input) -> str:
        """Generate contextual purpose description for tools."""
        # Extract meaningful purpose from tool name and parameters
        purpose_mappings = {
            "search": "Finding relevant information",
            "query": "Retrieving data from database",
            "analyze": "Performing data analysis",
            "generate": "Creating content or reports",
            "validate": "Checking data integrity",
            "optimize": "Improving performance",
            "export": "Exporting results",
            "import": "Loading external data",
            "llm": "Processing with AI model",
            "calculation": "Computing metrics",
            "transformation": "Converting data format"
        }
        
        # Check for patterns in tool name
        for pattern, purpose in purpose_mappings.items():
            if pattern.lower() in tool_name.lower():
                return purpose
                
        return f"Executing {tool_name} operation"
    
    def _estimate_tool_duration(self, tool_name: str, tool_input) -> int:
        """Estimate tool execution duration in milliseconds."""
        # Duration estimates based on tool patterns
        duration_estimates = {
            "search": 3000,     # 3 seconds
            "query": 2000,      # 2 seconds  
            "analyze": 15000,   # 15 seconds
            "generate": 8000,   # 8 seconds
            "validate": 2000,   # 2 seconds
            "optimize": 30000,  # 30 seconds
            "export": 5000,     # 5 seconds
            "import": 10000,    # 10 seconds
            "llm": 12000,       # 12 seconds
            "calculation": 5000, # 5 seconds
            "transformation": 3000  # 3 seconds
        }
        
        # Check for patterns in tool name
        for pattern, duration in duration_estimates.items():
            if pattern.lower() in tool_name.lower():
                return duration
                
        return 5000  # Default 5 seconds
    
    def _create_parameters_summary(self, tool_input) -> str:
        """Create user-friendly summary of tool parameters."""
        if not tool_input:
            return "No parameters"
            
        try:
            # Handle different tool input formats
            if hasattr(tool_input, "model_dump"):
                params = tool_input.model_dump()
            elif hasattr(tool_input, "__dict__"):
                params = tool_input.__dict__
            elif isinstance(tool_input, dict):
                params = tool_input
            else:
                return str(tool_input)[:100]
            
            # Extract key information
            summary_parts = []
            
            # Common parameter patterns
            if "query" in params:
                summary_parts.append(f"Query: {str(params['query'])[:50]}")
            if "table_name" in params:
                summary_parts.append(f"Table: {params['table_name']}")
            if "limit" in params:
                summary_parts.append(f"Limit: {params['limit']}")
            if "filters" in params and params["filters"]:
                summary_parts.append(f"Filters: {len(params['filters'])} applied")
            
            if summary_parts:
                return "; ".join(summary_parts)
            else:
                # Fallback: show first few key-value pairs
                key_items = list(params.items())[:3]
                return "; ".join([f"{k}: {str(v)[:30]}" for k, v in key_items])
                
        except Exception:
            return "Complex parameters"


def create_contextual_tool_executor(websocket_manager) -> ContextualToolExecutor:
    """Create enhanced tool executor with contextual events."""
    return ContextualToolExecutor(websocket_manager)

