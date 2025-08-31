"""Enhanced tool execution with WebSocket notifications.

Business Value: Real-time tool execution status for improved UX.

DEPRECATED: This module is kept for backward compatibility.
Use unified_tool_execution.py directly for new code.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from netra_backend.app.websocket_core import WebSocketManager

from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class EnhancedToolExecutionEngine(UnifiedToolExecutionEngine):
    """Tool execution engine with WebSocket notifications - delegates to unified engine.
    
    DEPRECATED: This class is kept for backward compatibility.
    Use UnifiedToolExecutionEngine directly instead.
    """
    
    def __init__(self, websocket_manager: Optional['WebSocketManager'] = None):
        """Initialize with WebSocket manager - delegates to unified engine."""
        super().__init__(websocket_manager=websocket_manager)
        # Keep these for backward compatibility
        self.websocket_manager = websocket_manager
        self.websocket_notifier = self.websocket_notifier


def enhance_tool_dispatcher_with_notifications(tool_dispatcher, websocket_manager):
    """Enhance existing tool dispatcher with WebSocket notifications.
    
    This function wraps the tool dispatcher's executor with enhanced notifications.
    """
    if hasattr(tool_dispatcher, 'executor'):
        # Check if already enhanced
        if isinstance(tool_dispatcher.executor, (EnhancedToolExecutionEngine, UnifiedToolExecutionEngine)):
            logger.debug("Tool dispatcher already enhanced with WebSocket notifications")
            return tool_dispatcher
        
        # Replace executor with unified version
        unified_executor = UnifiedToolExecutionEngine(websocket_manager)
        
        # Store original executor for testing/validation
        tool_dispatcher._original_executor = tool_dispatcher.executor
        tool_dispatcher.executor = unified_executor
        
        # Mark as enhanced for validation
        tool_dispatcher._websocket_enhanced = True
        
        logger.info("Enhanced tool dispatcher with WebSocket notifications")
    else:
        logger.warning("Tool dispatcher does not have executor attribute")
    
    return tool_dispatcher


class ContextualToolExecutor(UnifiedToolExecutionEngine):
    """Tool executor with enhanced contextual WebSocket events.
    
    DEPRECATED: This class is kept for backward compatibility.
    Use UnifiedToolExecutionEngine directly which includes all features.
    """
    pass


def create_contextual_tool_executor(websocket_manager) -> ContextualToolExecutor:
    """Create enhanced tool executor with contextual events.
    
    DEPRECATED: Use UnifiedToolExecutionEngine directly.
    """
    return ContextualToolExecutor(websocket_manager)