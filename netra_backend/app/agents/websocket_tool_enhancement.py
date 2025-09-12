"""
WebSocket Tool Dispatcher Enhancement Module

This module provides functions to enhance tool dispatchers with WebSocket notification capabilities.
Created to fix missing imports in e2e tests.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


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


# For backward compatibility, also export from unified_tool_execution
__all__ = ['enhance_tool_dispatcher_with_notifications']