import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from app.auth.auth_dependencies import ActiveUserWsDep
from app.connection_manager import manager

router = APIRouter()

@router.websocket("/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str, user: ActiveUserWsDep):
    await manager.connect(websocket, run_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60)
                # This is where the agent service would be called
                # await agent_service.handle_websocket_message(run_id, json.dumps(data))
            except asyncio.TimeoutError:
                # No message received within the timeout period, continue listening
                continue
    except WebSocketDisconnect:
        manager.disconnect(run_id)
