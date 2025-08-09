import json
import logging
from fastapi import Depends
from app.agents.supervisor import Supervisor
from app import schemas
from app.ws_manager import manager
from app.llm.llm_manager import LLMManager
from app.db.postgres import get_async_db

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self, supervisor: Supervisor):
        self.supervisor = supervisor

    async def run(self, request_model: schemas.RequestModel, run_id: str, stream_updates: bool = False):
        """
        Starts the agent. The supervisor will stream logs back to the websocket if requested.
        """
        return await self.supervisor.run(request_model.model_dump(), run_id, stream_updates)

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
                request_model = schemas.RequestModel(**payload.get("request"))
                # When started from a websocket, we always want to stream updates
                response = await self.run(request_model, run_id, stream_updates=True)
                await manager.broadcast_to_user(
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

def get_agent_service(db_session = Depends(get_async_db), llm_manager: LLMManager = Depends(LLMManager)) -> AgentService:
    from app.agents.supervisor import Supervisor
    from app.agents.tool_dispatcher import ToolDispatcher
    tool_dispatcher = ToolDispatcher(db_session)
    supervisor = Supervisor(db_session, llm_manager, manager, tool_dispatcher)
    return AgentService(supervisor)