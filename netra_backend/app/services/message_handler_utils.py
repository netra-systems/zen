"""Utility functions for message handling"""

from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.ws_manager import manager

logger = central_logger.get_logger(__name__)

async def handle_thread_history(thread_service, user_id: str, db_session: Optional[Any]) -> None:
    """Handle get_thread_history message type"""
    if not db_session:
        await manager.send_error(user_id, "Database session not available")
        return
    
    thread = await thread_service.get_or_create_thread(user_id, db_session)
    if not thread:
        await manager.send_error(user_id, "Failed to retrieve thread history")
        return
    
    messages = await thread_service.get_thread_messages(thread.id, db=db_session)
    history = _format_message_history(messages)
    await _send_thread_history(user_id, thread.id, history)

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

async def _send_thread_history(user_id: str, thread_id: str, history: list) -> None:
    """Send thread history to user"""
    await manager.send_message(
        user_id,
        {
            "type": "thread_history",
            "payload": {
                "thread_id": thread_id,
                "messages": history
            }
        }
    )

async def handle_stop_agent(user_id: str) -> None:
    """Handle stop_agent message type"""
    logger.info(f"Received stop agent request from {user_id}")
    await manager.send_message(
        user_id,
        {
            "type": "agent_stopped",
            "payload": {"status": "stopped"}
        }
    )