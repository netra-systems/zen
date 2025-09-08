"""Message processing utilities"""

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect

from netra_backend.app.db.models_postgres import Run, Thread
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)

async def send_agent_started_notification(
    user_id: str, thread: Optional[Thread], run: Optional[Run], user_context: Optional[UserExecutionContext] = None
) -> None:
    """Send agent_started notification to frontend"""
    thread_id = thread.id if thread else None
    run_id = run.id if run else None
    
    # Create user context if not provided
    if not user_context:
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id
        )
    
    # Create isolated manager for this user
    manager = create_websocket_manager(user_context)
    
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
        # Don't process if thread creation failed
        if thread is None:
            logger.error(f"Cannot process message without thread for user {user_id}")
            # Create minimal context for error handling
            error_context = UserExecutionContext(user_id=user_id)
            await send_error_safely(user_id, "Failed to create or access thread", error_context)
            return
        
        # Create user context for this message processing
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread.id if thread else None,
            run_id=run.id if run else None,
            db_session=db_session
        )
            
        # Send agent_started notification with user context
        await send_agent_started_notification(user_id, thread, run, user_context)
        response = await execute_and_persist(
            supervisor, text, user_id, thread, run, db_session, thread_service
        )
        await send_response_safely(user_id, response, user_context)
    except WebSocketDisconnect:
        handle_disconnect(user_id)
    except Exception as e:
        # Create context for error handling if not already created
        if 'user_context' not in locals():
            user_context = UserExecutionContext(user_id=user_id)
        await handle_processing_error(user_id, e, user_context)

async def execute_and_persist(
    supervisor, user_id: str, text: str, thread: Optional[Thread],
    run: Optional[Run], db_session: Optional[AsyncSession], thread_service
) -> Any:
    """Execute supervisor and persist response using UserExecutionContext pattern"""
    run_id = run.id if run else user_id
    thread_id = thread.id if thread else user_id
    
    logger.info(f"🔧 execute_and_persist called for user={user_id}, thread={thread_id}, run={run_id}")
    logger.info(f"🔍 db_session type: {type(db_session)}, is None: {db_session is None}")
    
    # CRITICAL: Register run-thread mapping for WebSocket routing
    # This ensures all agent events reach the correct user
    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        bridge = AgentWebSocketBridge()
        
        # CRITICAL FIX: Create proper UserExecutionContext first
        temp_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            db_session=db_session
        )
        
        # Create WebSocket manager for this user context
        websocket_manager = create_websocket_manager(temp_context)
        
        # CRITICAL FIX: Set the WebSocket manager on the bridge
        # This fixes the issue where all bridge events fail due to missing _websocket_manager
        bridge._websocket_manager = websocket_manager
        
        logger.info(f"✅ Bridge created with WebSocket manager for user isolation - run_id={run_id} → thread_id={thread_id}")
        
        # Store bridge for later use with UserExecutionContext
        bridge_for_emitter = bridge
            
    except Exception as e:
        logger.error(f"🚨 Error creating WebSocket bridge with manager: {e}")
        # Continue execution even if registration fails
        bridge_for_emitter = None
    
    # UserExecutionContext already imported at top of file
    
    try:
        # Create context with proper metadata using db_session
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            db_session=db_session,
            metadata={
                "user_request": text,
                "timestamp": run.created_at if run else None
            }
        )
        logger.info(f"✅ Created UserExecutionContext for user={user_id}, thread={thread_id}, run={run_id}")
        
        # CRITICAL: Create per-user WebSocket emitter (SECURITY: prevents cross-user leakage)
        if bridge_for_emitter is not None:
            try:
                # CRITICAL FIX: Set the bridge on the supervisor directly 
                # This ensures the supervisor can emit all 5 required WebSocket events
                if hasattr(supervisor, 'websocket_bridge'):
                    supervisor.websocket_bridge = bridge_for_emitter
                    logger.info(f"✅ Set WebSocket bridge on supervisor for real-time events - run_id={run_id}")
                    
                    # Also try to create user emitter for advanced usage
                    try:
                        user_emitter = await bridge_for_emitter.create_user_emitter(context)
                        if hasattr(supervisor, 'set_websocket_emitter'):
                            supervisor.set_websocket_emitter(user_emitter)
                            logger.info(f"✅ Also set user-specific WebSocket emitter on supervisor for run_id={run_id}")
                    except Exception as emitter_error:
                        logger.warning(f"⚠️ Could not create user emitter (will use bridge directly): {emitter_error}")
                        
                elif hasattr(supervisor, 'set_websocket_bridge'):
                    # Backward compatibility: use bridge if emitter method not available
                    supervisor.set_websocket_bridge(bridge_for_emitter, run_id)
                    logger.info(f"✅ Set WebSocket bridge on supervisor using legacy method - run_id={run_id}")
                else:
                    logger.warning(f"⚠️ Supervisor doesn't have WebSocket bridge property or methods")
                    
            except Exception as emitter_error:
                logger.error(f"🚨 Failed to create user emitter: {emitter_error}")
                # Continue execution without WebSocket events rather than failing completely
        
        # Check if supervisor has execute method
        if not hasattr(supervisor, 'execute'):
            logger.error(f"🚨 CRITICAL: SupervisorAgent does not have 'execute' method!")
            logger.error(f"🚨 Available methods: {[m for m in dir(supervisor) if not m.startswith('_')]}")
            # Fall back to old run method if available
            if hasattr(supervisor, 'run'):
                logger.warning(f"⚠️ Falling back to supervisor.run() method")
                response = await supervisor.run(text, thread_id, user_id, run_id)
            else:
                raise AttributeError("SupervisorAgent missing both execute and run methods")
        else:
            # Execute the supervisor with the new UserExecutionContext pattern
            logger.info(f"🚀 Calling supervisor.execute() with context for run_id={run_id}")
            response = await supervisor.execute(context, stream_updates=True)
            logger.info(f"✅ SupervisorAgent executed successfully for run_id={run_id}")
        
    except Exception as e:
        logger.error(f"❌ Error executing supervisor: {e}", exc_info=True)
        raise
    
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

async def send_response_safely(user_id: str, response: Any, user_context: UserExecutionContext) -> None:
    """Send response to user with error handling"""
    from netra_backend.app.services.message_handler_base import MessageHandlerBase
    response_data = MessageHandlerBase.convert_response_to_dict(response)
    
    # Create isolated manager for this user
    manager = create_websocket_manager(user_context)
    
    try:
        await manager.send_message(
            user_id, {"type": "agent_completed", "payload": response_data}
        )
    except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
        logger.info(f"WebSocket disconnected when sending response to user {user_id}: {e}")

def handle_disconnect(user_id: str) -> None:
    """Handle WebSocket disconnection"""
    logger.info(f"WebSocket disconnected for user {user_id} during processing")

async def handle_processing_error(user_id: str, error: Exception, user_context: UserExecutionContext) -> None:
    """Handle errors during message processing"""
    if isinstance(error, RuntimeError) and is_connection_error(error):
        logger.info(f"WebSocket already closed for user {user_id}: {error}")
    else:
        logger.error(f"Error processing user message: {error}")
        await send_error_safely(user_id, error, user_context)

def is_connection_error(error: RuntimeError) -> bool:
    """Check if runtime error is connection related"""
    error_str = str(error)
    return "Cannot call" in error_str or "close" in error_str.lower()

async def send_error_safely(user_id: str, error: Exception, user_context: UserExecutionContext) -> None:
    """Send error message to user safely"""
    # Create isolated manager for this user
    manager = create_websocket_manager(user_context)
    
    try:
        await manager.send_error(user_id, f"Internal server error: {str(error)}")
    except Exception:
        logger.debug(f"Could not send error to user {user_id}")