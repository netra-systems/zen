import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.websocket_manager import manager
from app.auth_dependencies import ActiveUserWsDep

router = APIRouter()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, current_user: ActiveUserWsDep):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # You can add logic here to handle messages from the client if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
