from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect, Query
from app.ws_manager import manager
from app import schemas
from app.auth.auth_dependencies import ActiveUserWsDep
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user: schemas.User = Depends(ActiveUserWsDep),
):
    if user is None:
        await websocket.close(code=1008)
        return

    user_id = str(user.id)
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Here you would typically pass the data to a message handler
            # For now, we'll just log it
            logger.info(f"Received message from {user_id}: {data}")
            # Example of sending a message back to the user
            await manager.send_message(user_id, {"response": "Message received"})

    except WebSocketDisconnect:
        manager.disconnect(user_id)