from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from app.ws_manager import manager
from app.logging_config import central_logger
from app.db.postgres import get_async_db
import asyncio

logger = central_logger.get_logger(__name__)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    db_session = Depends(get_async_db),
):
    # Accept the connection first
    await websocket.accept()
    
    # Get token from query parameters
    token = websocket.query_params.get("token")
    if not token:
        logger.error("No token provided in query parameters")
        await websocket.close(code=1008, reason="No token provided")
        return
    
    # Get services from app state
    app = websocket.app
    security_service = app.state.security_service
    agent_service = app.state.agent_service
    
    # Authenticate the user using the token
    try:
        payload = security_service.decode_access_token(token)
        if payload is None:
            logger.error("Token payload is invalid")
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        user_id = payload.get("sub")
        if user_id is None:
            logger.error("User ID not found in token payload")
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        logger.info(f"Attempting to authenticate user with ID: {user_id}")
        
        # Add retry logic and better error handling
        user = None
        try:
            user = await security_service.get_user_by_id(db_session, user_id)
        except Exception as db_error:
            logger.error(f"Database error while fetching user {user_id}: {db_error}")
            # Try to refresh the database session
            try:
                await db_session.rollback()
                user = await security_service.get_user_by_id(db_session, user_id)
            except Exception as retry_error:
                logger.error(f"Retry failed for user {user_id}: {retry_error}")
        
        if user is None:
            # Check if this might be an email instead of ID (legacy tokens)
            if "@" in user_id:
                logger.warning(f"Token contains email {user_id} instead of user ID, attempting email lookup")
                user = await security_service.get_user(db_session, user_id)
            
            if user is None:
                logger.error(f"User with ID {user_id} not found in database")
                # Log additional debug info
                logger.debug(f"Token payload: {payload}")
                
                # Check if database has any users at all (helpful for debugging empty databases)
                from sqlalchemy import select, func
                from app.db.models_postgres import User
                user_count_result = await db_session.execute(select(func.count()).select_from(User))
                user_count = user_count_result.scalar()
                if user_count == 0:
                    logger.warning("Database has no users. Run 'python create_test_user.py' to create a test user.")
                
                await websocket.close(code=1008, reason="User not found")
                return
        
        if not user.is_active:
            logger.error(f"User {user_id} is not active")
            await websocket.close(code=1008, reason="User not active")
            return
            
    except Exception as e:
        logger.error(f"Error authenticating WebSocket connection: {e}", exc_info=True)
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Connection authenticated successfully
    user_id_str = str(user.id)
    conn_info = await manager.connect(user_id_str, websocket)
    logger.info(f"WebSocket connection established for user {user_id_str}")
    
    try:
        while True:
            try:
                # Receive message with timeout to allow periodic health checks
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=manager.HEARTBEAT_TIMEOUT
                )
                
                # Handle pong responses
                if data == "pong":
                    await manager.handle_pong(user_id_str, websocket)
                    continue
                
                # Update connection statistics
                manager._stats["total_messages_received"] += 1
                
                # Pass the database session to handle_websocket_message
                await agent_service.handle_websocket_message(user_id_str, data, db_session)
                
            except asyncio.TimeoutError:
                # Check if connection is still alive
                if not manager._is_connection_alive(conn_info):
                    logger.warning(f"Connection timeout for user {user_id_str}")
                    break
                continue
                
    except WebSocketDisconnect as e:
        logger.info(f"WebSocket disconnected for user {user_id_str}: {e.code} - {e.reason}")
        await manager.disconnect(user_id_str, websocket, code=e.code, reason=e.reason or "Client disconnect")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id_str}: {e}", exc_info=True)
        await manager.disconnect(user_id_str, websocket, code=1011, reason="Server error")
    finally:
        # Ensure cleanup happens
        if user_id_str in manager.active_connections:
            if any(conn.websocket == websocket for conn in manager.active_connections.get(user_id_str, [])):
                await manager.disconnect(user_id_str, websocket)