from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from app.ws_manager import manager
from app.logging_config import central_logger
from app.db.postgres import get_async_db

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
        
        user = await security_service.get_user_by_id(db_session, user_id)
        if user is None:
            logger.error(f"User with ID {user_id} not found")
            await websocket.close(code=1008, reason="User not found")
            return
        
        if not user.is_active:
            logger.error(f"User {user_id} is not active")
            await websocket.close(code=1008, reason="User not active")
            return
            
    except Exception as e:
        logger.error(f"Error authenticating WebSocket connection: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Connection authenticated successfully
    user_id_str = str(user.id)
    await manager.connect(user_id_str, websocket)
    logger.info(f"WebSocket connection established for user {user_id_str}")
    
    try:
        while True:
            data = await websocket.receive_text()
            await agent_service.handle_websocket_message(user_id_str, data)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id_str}")
        manager.disconnect(user_id_str, websocket)