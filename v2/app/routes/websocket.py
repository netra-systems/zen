import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.services.deepagents.graph import SingleAgentTeam
from app.llm.llm_manager import LLMManager
from app.services.deepagents.tool_dispatcher import ToolDispatcher
from app.services.deepagents.sub_agent import SubAgent
from app.services.deepagents.tools import get_tools
from app.services.deepagents.prompts import get_agent_prompt
from app.config import settings
import json

router = APIRouter()

from app.auth_dependencies import ActiveUserWsDep

@router.websocket("/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str, current_user: ActiveUserWsDep):
    await websocket.accept()
    handshake_completed = False
    try:
        while True:
            data = await websocket.receive_text()
            if not handshake_completed:
                if data == "handshake":
                    await websocket.send_text("handshake_ack")
                    handshake_completed = True
                else:
                    await websocket.close(code=1008)
            else:
                await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for run_id: {run_id}")