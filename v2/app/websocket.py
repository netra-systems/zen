import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from app.auth.auth_dependencies import ActiveUserWsDep
from app.services.deepagents.supervisor import Supervisor
from app.schemas import AnalysisRequest
from app.llm.llm_manager import LLMManager
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Any

from app.ws_manager import manager

router = APIRouter()
logger = logging.getLogger(__name__)

def get_llm_manager_from_state(request: Request) -> LLMManager:
    return request.app.state.llm_manager

def get_agent_supervisor(request: Request, db_session: AsyncSession = Depends(get_db_session), llm_manager: LLMManager = Depends(get_llm_manager_from_state)) -> Supervisor:
    return Supervisor(db_session, llm_manager, manager)

@router.websocket("/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str, user: ActiveUserWsDep, supervisor: Supervisor = Depends(get_agent_supervisor)):
    await manager.connect(websocket, run_id)
    logger.info(f"WebSocket connection established for run_id: {run_id}")
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                if data == 'ping':
                    await websocket.send_text('pong')
                    logger.info(f"Sent pong to run_id: {run_id}")
                    continue
                
                logger.info(f"Received message from run_id: {run_id}, message: {data}")
                try:
                    analysis_request = AnalysisRequest.parse_raw(data)
                    await supervisor.start_agent(analysis_request, run_id, stream_updates=True)
                except Exception as e:
                    logger.error(f"Error parsing message for run_id: {run_id}", exc_info=True)
                    await websocket.send_text(f"Error parsing message: {e}")

            except asyncio.TimeoutError:
                logger.debug(f"WebSocket timeout for run_id: {run_id}, sending ping")
                await websocket.send_text('ping')
                try:
                    pong_response = await asyncio.wait_for(websocket.receive_text(), timeout=5)
                    if pong_response != 'pong':
                        logger.warning(f"WebSocket pong not received from run_id: {run_id}")
                        break
                except asyncio.TimeoutError:
                    logger.warning(f"WebSocket pong not received from run_id: {run_id}")
                    break
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection disconnected for run_id: {run_id}")
        manager.disconnect(run_id)
    except Exception as e:
        logger.error(f"An unexpected error occurred in the WebSocket endpoint for run_id: {run_id}", exc_info=True)
        manager.disconnect(run_id)
