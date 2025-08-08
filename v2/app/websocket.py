import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from app.auth.auth_dependencies import ActiveUserWsDep
from app.connection_manager import manager
from app.services.agent_service import AgentService, get_agent_service

router = APIRouter()

@router.websocket("/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str, user: ActiveUserWsDep, agent_service: AgentService = Depends(get_agent_service)):
    await manager.connect(websocket, run_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                if data == 'ping':
                    await websocket.send_text('pong')
                    continue
                await agent_service.handle_websocket_message(run_id, data)
            except asyncio.TimeoutError:
                # No message received within the timeout period, continue listening
                continue
    except WebSocketDisconnect:
        manager.disconnect(run_id)