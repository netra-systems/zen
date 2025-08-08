import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from app.auth.auth_dependencies import ActiveUserWsDep
from app.connection_manager import manager
from app.services.agents.supervisor import Supervisor
from app.schemas import AnalysisRequest
from app.llm.llm_manager import LLMManager
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

def get_agent_supervisor(request: Request) -> Supervisor:
    return request.app.state.agent_supervisor

@router.websocket("/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str, user: ActiveUserWsDep, supervisor: Supervisor = Depends(get_agent_supervisor)):
    await manager.connect(websocket, run_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                if data == 'ping':
                    await websocket.send_text('pong')
                    continue
                
                try:
                    analysis_request = AnalysisRequest.parse_raw(data)
                    await supervisor.run(analysis_request.model_dump(), run_id, stream_updates=True)
                except Exception as e:
                    await websocket.send_text(f"Error parsing message: {e}")

            except asyncio.TimeoutError:
                # No message received within the timeout period, continue listening
                continue
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)
