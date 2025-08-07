import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Any
from app.auth_dependencies import ActiveUserWsDep
from app.services.agent_service import AgentService
from app.services.streaming_agent.supervisor import StreamingAgentSupervisor

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, run_id: str):
        await websocket.accept()
        self.active_connections[run_id] = websocket

    def disconnect(self, run_id: str):
        if run_id in self.active_connections:
            del self.active_connections[run_id]

    async def send_to_run(self, message: Dict[str, Any], run_id: str):
        if run_id in self.active_connections:
            await self.active_connections[run_id].send_json(message)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()
router = APIRouter()
agent_service = AgentService(StreamingAgentSupervisor())

@router.websocket("/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str, user: ActiveUserWsDep):
    await manager.connect(websocket, run_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60)
                await agent_service.handle_websocket_message(run_id, json.dumps(data))
            except asyncio.TimeoutError:
                # No message received within the timeout period, continue listening
                continue
    except WebSocketDisconnect:
        manager.disconnect(run_id)
