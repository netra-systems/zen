import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.websocket_manager import manager
from app.auth_dependencies import ActiveUserWsDep
from typing import Dict, Any

router = APIRouter()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, current_user: ActiveUserWsDep):
    await manager.connect(websocket, client_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30)
                # You can add logic here to handle messages from the client if needed
            except asyncio.TimeoutError:
                # No message received within the timeout period, continue listening
                continue
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)


async def send_update_to_client(client_id: str, message: Dict[str, Any]):
    await manager.broadcast_to_client(client_id, message)