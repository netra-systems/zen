"""
WebSocket Tool Dispatcher Enhancement Module

This module provides functions to enhance tool dispatchers with WebSocket notification capabilities.
Created to fix missing imports in e2e tests.
"""

from shared.logging.unified_logging_ssot import get_logger
from typing import Any, Optional

logger = get_logger(__name__)


def enhance_tool_dispatcher_with_notifications(tool_dispatcher: Any, websocket_manager: Any) -> None:
    """
    Enhance a tool dispatcher with WebSocket notification capabilities.
    
    This function replaces the tool dispatcher's executor with a 
    UnifiedToolExecutionEngine that has WebSocket notification capabilities.
    
    Args:
        tool_dispatcher: The tool dispatcher to enhance
        websocket_manager: The WebSocket manager for sending notifications
    """
    if not tool_dispatcher or not websocket_manager:
        logger.warning("Cannot enhance tool dispatcher: missing dispatcher or websocket manager")
        return
    
    # Check if already enhanced with WebSocket bridge
    if hasattr(tool_dispatcher, 'executor') and hasattr(tool_dispatcher.executor, 'websocket_bridge'):
        if tool_dispatcher.executor.websocket_bridge is not None:
            logger.debug("Tool dispatcher already enhanced with WebSocket notifications")
            return
    
    # Import required components
    from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    
    # Create WebSocket bridge
    websocket_bridge = AgentWebSocketBridge()
    # CRITICAL FIX: Use the correct private member name
    websocket_bridge._websocket_manager = websocket_manager
    
    # Replace executor with enhanced version
    enhanced_executor = UnifiedToolExecutionEngine(
        websocket_bridge=websocket_bridge,
        permission_service=getattr(tool_dispatcher.executor, 'permission_service', None) if hasattr(tool_dispatcher, 'executor') else None
    )
    
    # Store reference to websocket manager for compatibility
    enhanced_executor.websocket_manager = websocket_manager
    
    # Replace the executor
    tool_dispatcher.executor = enhanced_executor
    
    # Mark as enhanced to prevent double enhancement
    tool_dispatcher._websocket_enhanced = True
    tool_dispatcher._websocket_manager = websocket_manager
    
    logger.info(" PASS:  Tool dispatcher enhanced with UnifiedToolExecutionEngine and WebSocket notifications")


class WebSocketToolEnhancer:
    """
    SSOT-compliant WebSocket Tool Enhancement class

    Provides class-based interface for WebSocket tool dispatcher enhancement
    while maintaining backward compatibility with existing function-based approach.
    """

    def __init__(self, websocket_manager=None):
        """Initialize WebSocket tool enhancer with optional WebSocket manager."""
        self.websocket_manager = websocket_manager
        self.logger = logging.getLogger(__name__)

    def enhance_dispatcher(self, tool_dispatcher, websocket_manager=None):
        """
        Enhance a tool dispatcher with WebSocket notification capabilities.

        Args:
            tool_dispatcher: The tool dispatcher to enhance
            websocket_manager: Optional WebSocket manager (uses instance manager if not provided)
        """
        manager = websocket_manager or self.websocket_manager
        if not manager:
            self.logger.warning("No WebSocket manager available for enhancement")
            return

        # Use the existing function implementation
        enhance_tool_dispatcher_with_notifications(tool_dispatcher, manager)
        self.logger.info("Tool dispatcher enhanced successfully via WebSocketToolEnhancer")

    @classmethod
    def create_with_manager(cls, websocket_manager):
        """Factory method to create enhancer with WebSocket manager."""
        return cls(websocket_manager=websocket_manager)

    def is_enhanced(self, tool_dispatcher):
        """Check if tool dispatcher is already enhanced."""
        return hasattr(tool_dispatcher, '_websocket_enhanced') and tool_dispatcher._websocket_enhanced


# For backward compatibility, also export from unified_tool_execution
__all__ = ['enhance_tool_dispatcher_with_notifications', 'WebSocketToolEnhancer']