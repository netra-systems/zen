import json
import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect, Depends
from app.services.agents.supervisor import Supervisor
from app import schemas
from app.connection_manager import manager
from app.llm.llm_manager import LLMManager
from app.db.session import get_db_session

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self, supervisor: Supervisor):
        self.supervisor = supervisor

    async def run(self, analysis_request: schemas.AnalysisRequest, run_id: str, stream_updates: bool = False):
        """
        Starts the agent. The supervisor will stream logs back to the websocket if requested.
        """
        return await self.supervisor.run(analysis_request.model_dump(), run_id, stream_updates)

    async def handle_websocket_message(self, run_id: str, message: str):
        """
        Handles a message from the WebSocket.
        """
        logger.info(f"handle_websocket_message called for run_id: {run_id} with message: {message}")
        try:
            data = json.loads(message)
            message_type = data.get("type")
            if message_type == "start_agent":
                payload = data.get("payload")
                analysis_request = schemas.AnalysisRequest(
                    settings=payload.get("settings"),
                    request=payload.get("request")
                )
                # When started from a websocket, we always want to stream updates
                response = await self.run(analysis_request, run_id, stream_updates=True)
                await manager.broadcast_to_client(
                    run_id,
                    {
                        "event": "agent_finished",
                        "data": response
                    }
                )

            else:
                logger.warning(f"Received unhandled message for run_id: {run_id}: {message}")
        except Exception as e:
            logger.error(f"Error in handle_websocket_message for run_id: {run_id}: {e}", exc_info=True)

def get_agent_service(db_session = Depends(get_db_session), llm_manager: LLMManager = Depends(LLMManager)) -> AgentService:
    from app.services.agents.supervisor import Supervisor
    supervisor = Supervisor(db_session, llm_manager, manager)
    return AgentService(supervisor)
