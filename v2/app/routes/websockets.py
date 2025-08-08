from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect, Query
from app.ws_manager import manager
from app.schemas import User, WebSocketMessage
from app.auth.auth_dependencies import ActiveUserWsDep
import json

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user: User = Depends(ActiveUserWsDep),
):
    if user is None:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = WebSocketMessage.parse_raw(data)
                # Process the message based on its type
                # This is where you would add your business logic
                await manager.send_personal_message(
                    WebSocketMessage(
                        type="user_message",
                        payload={"text": f"Echo: {message.payload.text}", "references": []},
                    ),
                    str(user.id),
                )
            except Exception as e:
                await manager.send_error(str(user.id), f"Invalid message format: {e}")

    except WebSocketDisconnect:
        manager.disconnect(user, websocket)