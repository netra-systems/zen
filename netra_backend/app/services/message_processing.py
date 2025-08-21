"""Message processing utilities"""

from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect
from app.logging_config import central_logger
from app.db.models_postgres import Thread, Run
from app.ws_manager import manager

logger = central_logger.get_logger(__name__)

async def send_agent_started_notification(
    user_id: str, thread: Optional[Thread], run: Optional[Run]
) -> None:
    """Send agent_started notification to frontend"""
    thread_id = thread.id if thread else None
    run_id = run.id if run else None
    await manager.send_message(user_id, {
        "type": "agent_started",
        "payload": {"thread_id": thread_id, "run_id": run_id}
    })

async def process_user_message_with_notifications(
    supervisor, user_id: str, text: str, thread: Optional[Thread],
    run: Optional[Run], db_session: Optional[AsyncSession], thread_service
) -> None:
    """Process user message and send response"""
    try:
        # Send agent_started notification
        await send_agent_started_notification(user_id, thread, run)
        response = await execute_and_persist(
            supervisor, user_id, text, thread, run, db_session, thread_service
        )
        await send_response_safely(user_id, response)
    except WebSocketDisconnect:
        handle_disconnect(user_id)
    except Exception as e:
        await handle_processing_error(user_id, e)

async def execute_and_persist(
    supervisor, user_id: str, text: str, thread: Optional[Thread],
    run: Optional[Run], db_session: Optional[AsyncSession], thread_service
) -> Any:
    """Execute supervisor and persist response"""
    run_id = run.id if run else user_id
    thread_id = thread.id if thread else user_id
    response = await supervisor.run(text, thread_id, user_id, run_id)
    if db_session and response and thread:
        await persist_response(thread, run, response, db_session, thread_service)
    return response

async def persist_response(
    thread: Thread, run: Optional[Run], response: Any, 
    db_session: AsyncSession, thread_service
) -> None:
    """Persist assistant response to database"""
    try:
        await save_assistant_message(thread, run, response, db_session, thread_service)
        if run:
            await mark_run_completed(run, db_session, thread_service)
    except Exception as e:
        logger.error(f"Error persisting assistant message: {e}")

async def save_assistant_message(
    thread: Thread, run: Optional[Run], response: Any, 
    db_session: AsyncSession, thread_service
) -> None:
    """Save assistant message to thread"""
    await thread_service.create_message(
        thread.id, role="assistant", content=str(response),
        metadata={"type": "agent_response"}, assistant_id="netra-assistant",
        run_id=run.id if run else None, db=db_session
    )

async def mark_run_completed(run: Run, db_session: AsyncSession, thread_service) -> None:
    """Mark run as completed"""
    await thread_service.update_run_status(
        run.id, status="completed", db=db_session
    )

async def send_response_safely(user_id: str, response: Any) -> None:
    """Send response to user with error handling"""
    from app.services.message_handler_base import MessageHandlerBase
    response_data = MessageHandlerBase.convert_response_to_dict(response)
    try:
        await manager.send_message(
            user_id, {"type": "agent_completed", "payload": response_data}
        )
    except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
        logger.info(f"WebSocket disconnected when sending response to user {user_id}: {e}")

def handle_disconnect(user_id: str) -> None:
    """Handle WebSocket disconnection"""
    logger.info(f"WebSocket disconnected for user {user_id} during processing")

async def handle_processing_error(user_id: str, error: Exception) -> None:
    """Handle errors during message processing"""
    if isinstance(error, RuntimeError) and is_connection_error(error):
        logger.info(f"WebSocket already closed for user {user_id}: {error}")
    else:
        logger.error(f"Error processing user message: {error}")
        await send_error_safely(user_id, error)

def is_connection_error(error: RuntimeError) -> bool:
    """Check if runtime error is connection related"""
    error_str = str(error)
    return "Cannot call" in error_str or "close" in error_str.lower()

async def send_error_safely(user_id: str, error: Exception) -> None:
    """Send error message to user safely"""
    try:
        await manager.send_error(user_id, f"Internal server error: {str(error)}")
    except Exception:
        logger.debug(f"Could not send error to user {user_id}")