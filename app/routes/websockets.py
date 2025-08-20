from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from app.ws_manager import manager
from app.logging_config import central_logger
from app.routes.utils.websocket_helpers import (
    accept_websocket_connection, extract_app_services,
    authenticate_websocket_user, receive_message_with_timeout, handle_pong_message,
    parse_json_message, validate_and_handle_message, process_agent_message,
    check_connection_alive, cleanup_websocket_connection
)
from app.websocket.error_recovery_handler import get_error_recovery_handler
import asyncio
import time

logger = central_logger.get_logger(__name__)
router = APIRouter()

async def _handle_none_message() -> bool:
    """Handle None message case."""
    return True

async def _process_valid_message(user_id_str: str, data: str, agent_service) -> bool:
    """Process validated message through agent service."""
    await process_agent_message(user_id_str, data, agent_service)
    return True

async def _handle_validated_message(
    user_id_str: str, websocket: WebSocket, message, data: str, agent_service
) -> bool:
    """Handle message after validation."""
    # CRITICAL FIX: Always process through agent service regardless of manager result
    # The manager handles WebSocket-level concerns (ping/pong, routing, etc)
    # But messages still need to go to the agent service for actual processing
    
    message_type = message.get("type", "unknown")
    logger.info(f"[WS MESSAGE ROUTING] Processing message type: {message_type} for user {user_id_str}")
    
    # Let manager handle WebSocket-specific messages (ping/pong, etc)
    manager_handled = await validate_and_handle_message(user_id_str, websocket, message, manager)
    
    # If it's a ping or other system message, manager handles it completely
    if message_type in ["ping", "pong", "auth"]:
        logger.debug(f"[WS SYSTEM] System message {message_type} handled by manager")
        return True
    
    # For user messages, ALWAYS forward to agent service
    logger.info(f"[WS AGENT] Forwarding {message_type} to agent service for user {user_id_str}")
    success = await _process_valid_message(user_id_str, data, agent_service)
    logger.info(f"[WS AGENT] Agent processing completed for {message_type}, success: {success}")
    return success

async def _handle_parsed_message(
    user_id_str: str, websocket: WebSocket, message, data: str, agent_service
) -> bool:
    """Handle parsed message validation and processing."""
    if message is None:
        return await _handle_none_message()
    return await _handle_validated_message(user_id_str, websocket, message, data, agent_service)

async def _process_single_message(user_id_str: str, websocket: WebSocket, agent_service):
    """Process a single WebSocket message with enhanced error handling."""
    try:
        logger.info(f"[WS MESSAGE] Waiting for message from user {user_id_str}")
        data = await receive_message_with_timeout(websocket)
        logger.info(f"[WS MESSAGE] Received raw data from {user_id_str}: {data[:100] if data else 'None'}")
        
        # Enhanced parsing with error recovery
        message = await parse_json_message(data, user_id_str, manager)
        logger.info(f"[WS MESSAGE] Parsed message from {user_id_str}: {message}")
        
        # Handle pong messages
        if await handle_pong_message(data, user_id_str, websocket, manager):
            logger.info(f"[WS MESSAGE] Handled pong from {user_id_str}")
            return True
        
        # Process message with error recovery
        logger.info(f"[WS MESSAGE] Processing message type: {message.get('type') if message else 'None'}")
        return await _handle_parsed_message(user_id_str, websocket, message, data, agent_service)
        
    except Exception as e:
        logger.error(f"[WS MESSAGE ERROR] Error processing message for user {user_id_str}: {e}", exc_info=True)
        # Send error response but keep connection alive
        try:
            await manager.send_error(user_id_str, "Message processing failed")
        except Exception as send_error:
            logger.error(f"[WS MESSAGE ERROR] Failed to send error response: {send_error}")
        return True  # Keep connection alive after errors

async def _handle_message_timeout(conn_info, user_id_str: str) -> bool:
    """Handle message processing timeout."""
    return check_connection_alive(conn_info, user_id_str, manager)

async def _try_process_single_message(
    user_id_str: str, websocket: WebSocket, agent_service
) -> bool:
    """Try to process single message."""
    await _process_single_message(user_id_str, websocket, agent_service)
    return True

async def _process_message_with_timeout_handling(
    user_id_str: str, websocket: WebSocket, conn_info, agent_service
) -> bool:
    """Process single message with timeout handling."""
    try:
        return await _try_process_single_message(user_id_str, websocket, agent_service)
    except asyncio.TimeoutError:
        return await _handle_message_timeout(conn_info, user_id_str)

async def _handle_message_loop(user_id_str: str, websocket: WebSocket, conn_info, agent_service):
    """Handle the main message processing loop with error recovery."""
    logger.info(f"[MESSAGE LOOP] Starting message loop for user {user_id_str}")
    message_count = 0
    error_count = 0
    max_consecutive_errors = 5
    
    while True:
        message_count += 1
        logger.info(f"[MESSAGE LOOP] Waiting for message #{message_count} from {user_id_str}")
        
        try:
            continue_loop = await _process_message_with_timeout_handling(
                user_id_str, websocket, conn_info, agent_service
            )
            
            # Reset error count on successful processing
            if continue_loop:
                error_count = 0
            
            if not continue_loop:
                logger.info(f"[MESSAGE LOOP] Exiting loop for {user_id_str} after {message_count} messages")
                break
                
        except Exception as e:
            error_count += 1
            logger.error(f"[MESSAGE LOOP ERROR] Error #{error_count} for user {user_id_str}: {e}", exc_info=True)
            
            # If too many consecutive errors, exit loop but don't crash
            if error_count >= max_consecutive_errors:
                logger.error(f"[MESSAGE LOOP] Too many consecutive errors ({error_count}) for user {user_id_str}, exiting loop")
                try:
                    await manager.send_error(user_id_str, "Too many errors occurred, please reconnect")
                except Exception:
                    pass
                break
            
            # Brief pause after error to prevent tight error loops
            await asyncio.sleep(0.1)

async def _handle_websocket_disconnect(e: WebSocketDisconnect, user_id_str: str, websocket: WebSocket):
    """Handle WebSocket disconnect with proper cleanup for network drops."""
    logger.info(f"WebSocket disconnected for user {user_id_str}: {e.code} - {e.reason}")
    
    # Determine if this is a network drop or abnormal disconnect
    is_abnormal_disconnect = e.code in [1006, 1011, 1012, 1013, 1014] or "network" in (e.reason or "").lower()
    
    reason = e.reason or ("Network disconnect" if is_abnormal_disconnect else "Client disconnect")
    
    if is_abnormal_disconnect:
        logger.warning(f"Abnormal disconnect detected for user {user_id_str}: code {e.code}, reason: {reason}")
    
    await manager.disconnect_user(user_id_str, websocket, code=e.code, reason=reason)

def _is_websocket_connected(websocket: WebSocket) -> bool:
    """Check if WebSocket is connected."""
    try:
        return (hasattr(websocket, 'application_state') and 
                websocket.application_state == WebSocketState.CONNECTED)
    except Exception:
        return False


def _is_recoverable_error(error: Exception) -> bool:
    """Determine if WebSocket error is recoverable."""
    error_str = str(error).lower()
    recoverable_indicators = [
        'timeout', 'connection lost', 'connection reset', 'network', 
        'temporary', 'rate limit', 'server overloaded'
    ]
    # JSON parsing and validation errors are recoverable
    if any(indicator in error_str for indicator in recoverable_indicators):
        return True
    # Check error types
    if isinstance(error, (TimeoutError, ConnectionError)):
        return True
    return False

async def _handle_websocket_error(e: Exception, user_id_str: str, websocket: WebSocket):
    """Handle WebSocket error with enhanced recovery attempt."""
    logger.error(f"WebSocket error for user {user_id_str}: {e}", exc_info=True)
    
    # Find connection info for error recovery
    conn_info = await manager.connection_manager.find_connection(user_id_str, websocket)
    reconnection_token = None
    
    # Determine if error is recoverable
    is_recoverable = _is_recoverable_error(e)
    
    if conn_info and is_recoverable:
        try:
            # Attempt error recovery
            error_handler = get_error_recovery_handler()
            reconnection_token = await error_handler.handle_error(e, conn_info)
        except Exception as recovery_error:
            logger.error(f"Error recovery failed for user {user_id_str}: {recovery_error}")
    
    # Send error notification if connection is still alive
    if _is_websocket_connected(websocket):
        try:
            await manager.send_error(user_id_str, 
                "Connection error occurred" + (" - reconnection available" if reconnection_token else ""))
        except Exception as notify_error:
            logger.debug(f"Could not send error notification: {notify_error}")
        
        # Disconnect with appropriate code and potential reconnection token
        disconnect_code = 1011 if not is_recoverable else 1012  # Server error vs Service restart
        await manager.disconnect_user(
            user_id_str, websocket, code=disconnect_code, reason="Server error",
            agent_state={"reconnection_token": reconnection_token} if reconnection_token else None
        )

async def _setup_websocket_auth(websocket: WebSocket):
    """Setup WebSocket authentication."""
    logger.info("[WEBSOCKET AUTH] Starting authentication")
    token = await accept_websocket_connection(websocket)
    logger.info(f"[WEBSOCKET AUTH] Token: {token[:20] if token else 'None'}...")
    security_service, agent_service = extract_app_services(websocket)
    logger.info(f"[WEBSOCKET AUTH] Services found: security={security_service is not None}, agent={agent_service is not None}")
    user_id_str = await authenticate_websocket_user(websocket, token, security_service)
    logger.info(f"[WEBSOCKET AUTH] Authenticated user: {user_id_str}")
    return user_id_str, agent_service

async def _finalize_websocket_connection(user_id_str: str, websocket: WebSocket):
    """Finalize WebSocket connection setup."""
    conn_info = await manager.connect_user(user_id_str, websocket)
    logger.info(f"WebSocket connection established for user {user_id_str}")
    return conn_info

async def _establish_websocket_connection(websocket: WebSocket):
    """Establish and authenticate WebSocket connection."""
    user_id_str, agent_service = await _setup_websocket_auth(websocket)
    conn_info = await _finalize_websocket_connection(user_id_str, websocket)
    return user_id_str, conn_info, agent_service

async def _handle_disconnect_exception(e: WebSocketDisconnect, user_id_str: str, websocket: WebSocket):
    """Handle WebSocket disconnect exception."""
    if user_id_str:
        await _handle_websocket_disconnect(e, user_id_str, websocket)

async def _handle_general_exception(e: Exception, user_id_str: str, websocket: WebSocket):
    """Handle general WebSocket exception."""
    logger.error(f"Error in WebSocket connection: {e}", exc_info=True)
    if user_id_str:
        await _handle_websocket_error(e, user_id_str, websocket)

async def _handle_websocket_exceptions(e: Exception, user_id_str: str, websocket: WebSocket):
    """Handle various WebSocket exceptions."""
    from fastapi import WebSocketException, HTTPException
    
    if isinstance(e, (WebSocketException, HTTPException)):
        # Re-raise these to let FastAPI handle the rejection properly
        raise e
    elif isinstance(e, WebSocketDisconnect):
        await _handle_disconnect_exception(e, user_id_str, websocket)
    elif isinstance(e, ValueError):
        return  # Authentication errors - connection already closed
    else:
        await _handle_general_exception(e, user_id_str, websocket)

async def _run_websocket_session(websocket: WebSocket):
    """Run WebSocket session with connection and message handling."""
    user_id_str, conn_info, agent_service = await _establish_websocket_connection(websocket)
    await _handle_message_loop(user_id_str, websocket, conn_info, agent_service)
    return user_id_str

async def _execute_websocket_session(websocket: WebSocket):
    """Execute WebSocket session with error handling."""
    from fastapi import WebSocketException, HTTPException
    user_id_str = None
    try:
        user_id_str = await _run_websocket_session(websocket)
    except (WebSocketException, HTTPException):
        # Re-raise these exceptions to let FastAPI handle the rejection
        raise
    except Exception as e:
        await _handle_websocket_exceptions(e, user_id_str, websocket)
    return user_id_str

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint handler."""
    logger.info("[WEBSOCKET CONNECTED] New WebSocket connection received at /ws endpoint")
    user_id_str = await _execute_websocket_session(websocket)
    if user_id_str:
        logger.info(f"[WEBSOCKET CLEANUP] Cleaning up connection for user {user_id_str}")
        await cleanup_websocket_connection(user_id_str, websocket, manager)