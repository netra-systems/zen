from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ws_manager import manager

router = APIRouter()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", user_id)
            await manager.broadcast(f"Client #{user_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        await manager.broadcast(f"Client #{user_id} left the chat")