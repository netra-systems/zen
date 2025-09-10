"""WebSocket route specific utilities."""

import asyncio
import json
import time
from typing import Any, Dict, Optional, Tuple

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import func, select

from netra_backend.app.clients.auth_client_core import auth_client
from netra_backend.app.core.configuration import unified_config_manager
from netra_backend.app.db.database_manager import get_db_session
from netra_backend.app.logging_config import central_logger
from netra_backend.app.routes.utils.validators import (
    validate_token_payload,
    validate_user_active,
    validate_user_id_in_payload,
)
from netra_backend.app.websocket_core.utils import is_websocket_connected

logger = central_logger.get_logger(__name__)


async def validate_websocket_token(websocket: WebSocket) -> str:
    """Validate WebSocket token from query params."""
    token = websocket.query_params.get("token")
    if not token:
        logger.error("No token provided in query parameters")
        await websocket.close(code=1008, reason="No token provided")
        raise ValueError("No token provided")
    return token


async def accept_websocket_connection(websocket: WebSocket) -> str:
    """Validate token signature BEFORE accepting WebSocket connection."""
    # Get token from query params first
    token = websocket.query_params.get("token")
    if not token:
        logger.error("No token provided in query parameters")
        # Reject at HTTP level before WebSocket upgrade
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="No token provided")
    
    # Pre-validate token signature before accepting connection using auth client
    try:
        # Validate token with auth service (same as REST endpoints)
        validation_result = await auth_client.validate_token_jwt(token)
        
        if not validation_result or not validation_result.get("valid"):
            logger.error("[WS AUTH] Token validation failed: invalid token from auth service")
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Invalid or expired token")
        
        logger.info("[WS AUTH] Token validated with auth service, accepting connection")
    except Exception as e:
        logger.error(f"[WS AUTH] Token validation failed: {e}")
        # Reject at HTTP level before WebSocket upgrade
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail=f"Invalid token: {str(e)[:100]}")
    
    # Only accept connection after token is validated
    await websocket.accept()
    return token


def extract_app_services(websocket: WebSocket) -> Tuple[Any, Any]:
    """Extract services from app state."""
    app = websocket.app
    return app.state.security_service, app.state.agent_service


async def decode_token_payload(security_service, token: str) -> Dict:
    """Decode and validate token payload using auth service."""
    # Use auth service for token validation (same as REST endpoints)
    validation_result = await auth_client.validate_token_jwt(token)
    
    if not validation_result or not validation_result.get("valid"):
        raise ValueError("Invalid or expired token")
    
    # Convert auth service response to expected payload format
    # Ensure user_id is treated as string (database expects varchar)
    user_id = validation_result.get("user_id")
    if user_id is not None:
        user_id = str(user_id)  # Convert to string for database compatibility
    
    payload = {
        "sub": user_id,
        "email": validation_result.get("email"),
        "permissions": validation_result.get("permissions", [])
    }
    
    return validate_token_payload(payload)


async def fetch_user_with_retry(security_service, db_session, user_id: str):
    """Fetch user with retry logic."""
    try:
        return await security_service.get_user_by_id(db_session, user_id)
    except Exception as db_error:
        logger.error(f"Database error while fetching user {user_id}: {db_error}")
        await db_session.rollback()
        return await security_service.get_user_by_id(db_session, user_id)


async def handle_legacy_email_lookup(security_service, db_session, user_id: str, user):
    """Handle legacy email-based token lookup."""
    if user is None and "@" in user_id:
        logger.warning(f"Token contains email {user_id}, attempting email lookup")
        user = await security_service.get_user(db_session, user_id)
    return user


async def log_empty_database_warning(db_session):
    """Log warning if database is empty."""
    from netra_backend.app.db.models_postgres import User
    user_count_result = await db_session.execute(select(func.count()).select_from(User))
    user_count = user_count_result.scalar()
    if user_count == 0:
        logger.warning("Database has no users. Run 'python create_test_user.py'")


async def check_user_exists_and_debug(db_session, user_id: str, payload: dict, user):
    """Check if user exists and provide debug info."""
    if user is None:
        logger.error(f"User with ID {user_id} not found in database")
        logger.debug(f"Token payload: {payload}")
        await log_empty_database_warning(db_session)
        # Try to create user if in development mode and auth service is providing valid user data
        config = unified_config_manager.get_config()
        env = config.environment.lower()
        if env in ["development", "test"] and payload.get("email"):
            logger.warning(f"Auto-creating user {user_id} in {env} environment")
            return user_id  # In dev mode, proceed without strict database validation
        raise ValueError("User not found")


async def get_and_validate_user(
    security_service, db_session, user_id: str, payload: dict
) -> str:
    """Get user and validate with legacy lookup support."""
    user = await fetch_user_with_retry(security_service, db_session, user_id)
    user = await handle_legacy_email_lookup(security_service, db_session, user_id, user)
    await check_user_exists_and_debug(db_session, user_id, payload, user)
    return validate_user_active(user)


async def authenticate_websocket_user(websocket: WebSocket, token: str, security_service) -> str:
    """Authenticate WebSocket user and return user ID string with enhanced error handling."""
    logger.info(f"[WS AUTH] Starting authentication with token: {token[:20] if token else 'None'}...")
    
    # Retry counter for transient failures
    max_retries = 2
    retry_delay = 0.5
    
    for attempt in range(max_retries + 1):
        try:
            payload = await decode_token_payload(security_service, token)
            logger.info(f"[WS AUTH] Token decoded successfully, payload keys: {list(payload.keys())}")
            
            user_id = validate_user_id_in_payload(payload)
            logger.info(f"[WS AUTH] User ID validated: {user_id}")
            
            async with get_db_session() as db_session:
                logger.info(f"[WS AUTH] Database session acquired, fetching user {user_id} (attempt {attempt + 1})")
                result = await get_and_validate_user(security_service, db_session, user_id, payload)
                logger.info(f"[WS AUTH] User validated successfully: {result}")
                return result
                
        except ValueError as e:
            # Authentication errors - don't retry
            logger.error(f"[WS AUTH ERROR] Authentication validation failed: {e}")
            await _close_websocket_with_auth_error(websocket, str(e))
            raise
            
        except Exception as e:
            # Transient errors - retry if not last attempt
            if attempt < max_retries and _is_retryable_error(e):
                logger.warning(f"[WS AUTH] Retryable error on attempt {attempt + 1}: {e}")
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
            else:
                logger.error(f"[WS AUTH ERROR] Authentication failed after {attempt + 1} attempts: {e}", exc_info=True)
                await _close_websocket_with_auth_error(websocket, f"Authentication failed: {str(e)}")
                raise


async def receive_message_with_timeout(websocket: WebSocket) -> str:
    """Receive WebSocket message with timeout."""
    return await asyncio.wait_for(
        websocket.receive_text(),
        timeout=30  # 30 second timeout for heartbeat
    )


async def handle_pong_message(data: str, user_id_str: str, websocket: WebSocket, manager) -> bool:
    """Handle pong responses and ping messages."""
    # Handle raw pong strings
    if data == "pong":
        await manager.handle_pong(user_id_str, websocket)
        return True
    
    # Handle JSON ping messages
    try:
        if data and data.strip().startswith('{'):
            message = json.loads(data)
            if isinstance(message, dict) and message.get("type") == "ping":
                # Send pong response directly for ping messages
                await _send_pong_response(websocket)
                logger.info(f"[WS PING/PONG] Sent pong response to {user_id_str}")
                return True
    except (json.JSONDecodeError, Exception) as e:
        # Not a JSON ping message, continue normal processing
        logger.debug(f"[WS PING/PONG] Message not a JSON ping: {e}")
        pass
    
    return False


async def parse_json_message(data: str, user_id_str: str, manager):
    """Parse JSON message with comprehensive error handling."""
    try:
        # Handle None/empty data
        if data is None:
            logger.warning(f"Received None data from user {user_id_str}")
            await _send_parsing_error(manager, user_id_str, "Empty message received")
            return None
            
        # Handle coroutine data
        if asyncio.iscoroutine(data):
            logger.error(f"Received coroutine instead of data for user {user_id_str}")
            await _send_parsing_error(manager, user_id_str, "Internal message processing error")
            return None
            
        # Handle empty string
        if isinstance(data, str) and not data.strip():
            logger.warning(f"Received empty string from user {user_id_str}")
            await _send_parsing_error(manager, user_id_str, "Empty message received")
            return None
            
        # Parse JSON with comprehensive error handling
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                # Validate parsed result is a dictionary
                if not isinstance(parsed, dict):
                    logger.warning(f"Parsed JSON is not an object for user {user_id_str}: {type(parsed)}")
                    await _send_parsing_error(manager, user_id_str, "Message must be a JSON object")
                    return None
                return parsed
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error for user {user_id_str}: {e}. Data: {data[:200]}")
                await _send_parsing_error(manager, user_id_str, f"Invalid JSON syntax: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Unexpected JSON parsing error for user {user_id_str}: {e}")
                await _send_parsing_error(manager, user_id_str, "Message parsing failed")
                return None
        else:
            # Already parsed data
            return data if isinstance(data, dict) else None
            
    except Exception as e:
        logger.error(f"Critical error in parse_json_message for user {user_id_str}: {e}", exc_info=True)
        try:
            await _send_parsing_error(manager, user_id_str, "Message processing error")
        except Exception as send_error:
            logger.error(f"Failed to send error message to user {user_id_str}: {send_error}")
        return None


async def _handle_ping_message(message, websocket: WebSocket) -> bool:
    """Handle ping message and return True if handled."""
    # Ensure message is not a coroutine
    if asyncio.iscoroutine(message):
        logger.error("Received coroutine instead of message in ping handler")
        return False
    if isinstance(message, dict) and message.get("type") == "ping":
        await _send_pong_response(websocket)
        return True
    return False

async def _handle_with_manager(user_id_str: str, websocket: WebSocket, message, manager) -> bool:
    """Handle message with manager."""
    if not await manager.handle_message(user_id_str, websocket, message):
        return False
    return True

async def validate_and_handle_message(user_id_str: str, websocket: WebSocket, message, manager) -> bool:
    """Validate message and handle with manager with comprehensive error handling."""
    try:
        # Handle ping messages first
        if await _handle_ping_message(message, websocket):
            return True
        
        # Validate message structure before processing
        if not await _validate_message_structure(user_id_str, message, manager):
            return True  # Keep connection alive after validation error
        
        # Process through manager
        return await _handle_with_manager(user_id_str, websocket, message, manager)
        
    except Exception as e:
        logger.error(f"Error in message validation/handling for user {user_id_str}: {e}", exc_info=True)
        await _send_processing_error(manager, user_id_str, "Message processing failed")
        return True  # Keep connection alive


async def _send_pong_response(websocket: WebSocket) -> None:
    """Send pong response to ping message."""
    pong_message = {"type": "pong", "timestamp": time.time()}
    await websocket.send_json(pong_message)


async def process_agent_message(user_id_str: str, data: str, agent_service):
    """Process message through agent service with proper database session lifecycle."""
    # Validate user_id
    if not user_id_str or not user_id_str.strip():
        raise ValueError("user_id cannot be empty")
    
    # Create dedicated session for each message processing to avoid long-running sessions
    max_retries = 2
    for attempt in range(max_retries + 1):
        db_session = None
        try:
            # Try to get database session - this is what we retry on failure
            async with get_db_session() as db_session:
                # Ensure session is properly initialized
                if not db_session:
                    raise ValueError("Failed to create database session")
                
                # Process message with the session - agent errors propagate immediately
                await agent_service.handle_websocket_message(user_id_str, data, db_session)
                
                # Explicit commit to ensure transactional integrity
                await db_session.commit()
                return
                
        except Exception as e:
            # Classify the error type
            is_db_error = (_is_database_retryable_error(e) or 
                          "Database not configured" in str(e) or 
                          "Failed to create database session" in str(e))
            
            # Debug logging for troubleshooting
            logger.debug(f"Exception in process_agent_message: {e}, is_db_error: {is_db_error}, attempt: {attempt}")
            
            if is_db_error:
                logger.error(f"Database session error for user {user_id_str} (attempt {attempt + 1}): {e}")
                
                # Retry on transient database errors
                if attempt < max_retries:
                    await asyncio.sleep(0.1 * (attempt + 1))  # Brief backoff
                    continue
                else:
                    # Re-raise after max retries
                    raise
            else:
                # Agent processing errors - rollback transaction if we have a session, then re-raise immediately
                logger.debug(f"Agent error detected, not retrying: {e}")
                if db_session:
                    try:
                        await db_session.rollback()
                    except:
                        pass  # Ignore rollback errors, focus on the original error
                raise  # Re-raise agent error immediately without retry


def check_connection_alive(conn_info, user_id_str: str, manager) -> bool:
    """Check if connection is alive."""
    if not manager.connection_manager.is_connection_alive(conn_info):
        logger.warning(f"Connection timeout for user {user_id_str}")
        return False
    return True


async def cleanup_websocket_connection(user_id_str: str, websocket: WebSocket, manager):
    """Ensure comprehensive connection cleanup happens, including abnormal disconnects."""
    if not user_id_str:
        return
        
    try:
        # Check if connection still exists in manager
        if user_id_str in manager.connection_manager.active_connections:
            connections = manager.connection_manager.active_connections.get(user_id_str, [])
            matching_conn = next((conn for conn in connections if conn.websocket == websocket), None)
            
            if matching_conn:
                # Determine disconnect code based on websocket state
                disconnect_code = _determine_disconnect_code(websocket)
                reason = "Final cleanup - abnormal disconnect" if disconnect_code != 1000 else "Normal closure"
                
                logger.info(f"Cleaning up connection for {user_id_str} with code {disconnect_code}: {reason}")
                await manager.disconnect_user(user_id_str, websocket, code=disconnect_code, reason=reason)
                
    except Exception as e:
        logger.error(f"Error during connection cleanup for {user_id_str}: {e}")
        # Force cleanup even on error to prevent resource leaks
        try:
            await manager.disconnect_user(user_id_str, websocket, code=1011, reason="Cleanup error")
        except Exception:
            logger.error(f"Failed to force disconnect for {user_id_str}")

def _determine_disconnect_code(websocket: WebSocket) -> int:
    """Determine appropriate disconnect code based on WebSocket state."""
    try:
        from starlette.websockets import WebSocketState
        
        if hasattr(websocket, 'client_state'):
            if websocket.client_state == WebSocketState.DISCONNECTED:
                return 1006  # Abnormal closure - connection lost
            elif websocket.client_state == WebSocketState.CONNECTING:
                return 1014  # Failed to establish connection
        
        # Use centralized connection check to determine disconnect code
        if not is_websocket_connected(websocket):
            return 1006  # Abnormal closure - connection lost
        
        # Default to normal closure
        return 1000
        
    except Exception:
        # If we can't determine state, assume abnormal closure
        return 1006


async def _close_websocket_with_auth_error(websocket: WebSocket, error_message: str) -> None:
    """Close WebSocket connection with authentication error."""
    try:
        await websocket.close(code=1008, reason=f"Authentication failed: {error_message}")
    except Exception as close_error:
        logger.debug(f"Error closing WebSocket after auth failure: {close_error}")


async def _validate_message_structure(user_id_str: str, message, manager) -> bool:
    """Validate basic message structure and send appropriate error response."""
    if message is None:
        await _send_validation_error(manager, user_id_str, "Message is empty", "EMPTY_MESSAGE")
        return False
    
    if not isinstance(message, dict):
        await _send_validation_error(manager, user_id_str, 
                                   f"Message must be a JSON object, received {type(message).__name__}", 
                                   "INVALID_FORMAT")
        return False
    
    if "type" not in message:
        await _send_validation_error(manager, user_id_str, 
                                   "Message missing required 'type' field", 
                                   "MISSING_TYPE_FIELD")
        return False
    
    if not isinstance(message["type"], str) or not message["type"].strip():
        await _send_validation_error(manager, user_id_str, 
                                   "Message 'type' field must be a non-empty string", 
                                   "INVALID_TYPE_FIELD")
        return False
    
    return True


async def _send_parsing_error(manager, user_id_str: str, error_message: str) -> None:
    """Send parsing error message to user with connection safety."""
    try:
        error_response = {
            "type": "error",
            "error": error_message,
            "code": "PARSING_ERROR",
            "timestamp": time.time(),
            "recoverable": True,
            "help": "Please ensure your message is valid JSON format"
        }
        await manager.send_message(user_id_str, error_response)
    except Exception as e:
        logger.error(f"Failed to send parsing error to user {user_id_str}: {e}")


async def _send_validation_error(manager, user_id_str: str, error_message: str, error_code: str) -> None:
    """Send validation error message to user with helpful information."""
    try:
        error_response = {
            "type": "error",
            "error": error_message,
            "code": error_code,
            "timestamp": time.time(),
            "recoverable": True,
            "help": _get_error_help_text(error_code)
        }
        await manager.send_message(user_id_str, error_response)
    except Exception as e:
        logger.error(f"Failed to send validation error to user {user_id_str}: {e}")


async def _send_processing_error(manager, user_id_str: str, error_message: str) -> None:
    """Send processing error message to user."""
    try:
        error_response = {
            "type": "error",
            "error": error_message,
            "code": "PROCESSING_ERROR",
            "timestamp": time.time(),
            "recoverable": True,
            "help": "Please try sending your message again"
        }
        await manager.send_message(user_id_str, error_response)
    except Exception as e:
        logger.error(f"Failed to send processing error to user {user_id_str}: {e}")


def _get_error_help_text(error_code: str) -> str:
    """Get helpful error message based on error code."""
    help_messages = {
        "EMPTY_MESSAGE": "Please send a non-empty JSON message",
        "INVALID_FORMAT": "Please send a valid JSON object with curly braces {}",
        "MISSING_TYPE_FIELD": "Please include a 'type' field in your message, e.g. {'type': 'ping'}",
        "INVALID_TYPE_FIELD": "The 'type' field must be a non-empty string",
        "PARSING_ERROR": "Please check your JSON syntax and try again"
    }
    return help_messages.get(error_code, "Please check your message format and try again")


def _is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable (transient network/database issues)."""
    error_str = str(error).lower()
    retryable_indicators = [
        'connection', 'timeout', 'network', 'database unavailable',
        'connection reset', 'connection lost', 'temporary failure'
    ]
    return any(indicator in error_str for indicator in retryable_indicators)


def _is_database_retryable_error(error: Exception) -> bool:
    """Check if a database error is retryable."""
    error_str = str(error).lower()
    db_retryable_indicators = [
        'connection lost', 'connection timed out', 'connection timeout', 'connection reset',
        'database is locked', 'deadlock detected', 'connection broken',
        'server closed the connection', 'timeout expired', 'connection pool',
        'no connection available', 'connection invalid'
    ]
    return any(indicator in error_str for indicator in db_retryable_indicators)