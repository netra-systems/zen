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
    
    This function wraps the tool dispatcher's execute method to send WebSocket
    notifications during tool execution.
    
    Args:
        tool_dispatcher: The tool dispatcher to enhance
        websocket_manager: The WebSocket manager for sending notifications
    """
    if not tool_dispatcher or not websocket_manager:
        logger.warning("Cannot enhance tool dispatcher: missing dispatcher or websocket manager")
        return
    
    # Mark the dispatcher as enhanced to avoid double enhancement
    if getattr(tool_dispatcher, '_websocket_enhanced', False):
        logger.debug("Tool dispatcher already enhanced with WebSocket notifications")
        return
    
    # Store the original execute method
    original_execute = getattr(tool_dispatcher, 'execute', None)
    if not original_execute:
        logger.warning("Tool dispatcher has no execute method to enhance")
        return
    
    async def enhanced_execute(tool_name: str, *args, **kwargs):
        """Enhanced execute method with WebSocket notifications"""
        thread_id = kwargs.get('thread_id')
        
        # Send tool executing notification
        if websocket_manager and thread_id:
            try:
                await websocket_manager.send_message({
                    'type': 'tool_executing',
                    'tool': tool_name,
                    'thread_id': thread_id
                })
            except Exception as e:
                logger.error(f"Failed to send tool_executing notification: {e}")
        
        # Execute the original tool
        try:
            result = await original_execute(tool_name, *args, **kwargs)
            
            # Send tool completed notification
            if websocket_manager and thread_id:
                try:
                    await websocket_manager.send_message({
                        'type': 'tool_completed',
                        'tool': tool_name,
                        'thread_id': thread_id,
                        'success': True
                    })
                except Exception as e:
                    logger.error(f"Failed to send tool_completed notification: {e}")
            
            return result
            
        except Exception as e:
            # Send tool failed notification
            if websocket_manager and thread_id:
                try:
                    await websocket_manager.send_message({
                        'type': 'tool_completed',
                        'tool': tool_name,
                        'thread_id': thread_id,
                        'success': False,
                        'error': str(e)
                    })
                except Exception as e2:
                    logger.error(f"Failed to send tool_failed notification: {e2}")
            raise
    
    # Replace the execute method with the enhanced version
    tool_dispatcher.execute = enhanced_execute
    tool_dispatcher._websocket_enhanced = True
    tool_dispatcher._websocket_manager = websocket_manager
    
    logger.info("Successfully enhanced tool dispatcher with WebSocket notifications")


# For backward compatibility, also export from unified_tool_execution
__all__ = ['enhance_tool_dispatcher_with_notifications']