"""Utility functions for message handling"""

from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

async def handle_thread_history(thread_service, user_id: str, db_session: Optional[Any], websocket_manager=None) -> None:
    """Handle get_thread_history message type"""
    if not db_session:
        if websocket_manager:
            await websocket_manager.send_error(user_id, "Database session not available")
        else:
            logger.error(f"Database session not available for user {user_id}")
        return
    
    thread = await thread_service.get_or_create_thread(user_id, db_session)
    if not thread:
        if websocket_manager:
            await websocket_manager.send_error(user_id, "Failed to retrieve thread history")
        else:
            logger.error(f"Failed to retrieve thread history for user {user_id}")
        return
    
    messages = await thread_service.get_thread_messages(thread.id, db=db_session)
    history = _format_message_history(messages)
    await _send_thread_history(user_id, thread.id, history, websocket_manager)

def _format_message_history(messages: list) -> list:
    """Format messages for history response"""
    history = []
    for msg in messages:
        content = msg.content[0]["text"]["value"] if msg.content else ""
        history.append({
            "role": msg.role,
            "content": content,
            "created_at": msg.created_at,
            "id": msg.id
        })
    return history

async def _send_thread_history(user_id: str, thread_id: str, history: list, websocket_manager=None) -> None:
    """Send thread history to user"""
    if websocket_manager:
        await websocket_manager.send_message(
            user_id,
            {
                "type": "thread_history",
                "payload": {
                    "thread_id": thread_id,
                    "messages": history
                }
            }
        )
    else:
        logger.info(f"Thread history for user {user_id}, thread {thread_id}: {len(history)} messages")

async def handle_stop_agent(user_id: str, websocket_manager=None) -> None:
    """Handle stop_agent message type"""
    logger.info(f"Received stop agent request from {user_id}")
    if websocket_manager:
        await websocket_manager.send_message(
            user_id,
            {
                "type": "agent_stopped",
                "payload": {"status": "stopped"}
            }
        )
    else:
        logger.info(f"Agent stopped for user {user_id}")