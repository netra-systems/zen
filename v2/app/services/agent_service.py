import json
from app.logging_config import central_logger
from fastapi import Depends
from app.agents.supervisor import Supervisor
from app import schemas
from app.ws_manager import manager
from app.llm.llm_manager import LLMManager
from app.db.postgres import get_async_db

logger = central_logger.get_logger(__name__)

class AgentService:
    def __init__(self, supervisor: Supervisor):
        self.supervisor = supervisor

    async def run(self, request_model: schemas.RequestModel, run_id: str, stream_updates: bool = False):
        """
        Starts the agent. The supervisor will stream logs back to the websocket if requested.
        """
        return await self.supervisor.run(request_model.model_dump(), run_id, stream_updates)

    async def handle_websocket_message(self, user_id: str, message):
        """
        Handles a message from the WebSocket.
        """
        logger.info(f"handle_websocket_message called for user_id: {user_id} with message: {message}")
        try:
            # Handle both string and dict inputs
            if isinstance(message, str):
                data = json.loads(message)
                # If json.loads returns a string, it means the JSON was double-encoded
                if isinstance(data, str):
                    data = json.loads(data)
            else:
                data = message
            
            message_type = data.get("type")
            payload = data.get("payload", {})
            
            if message_type == "start_agent":
                request_model = schemas.RequestModel(**payload.get("request"))
                # When started from a websocket, we always want to stream updates
                response = await self.run(request_model, user_id, stream_updates=True)
                await manager.send_message(
                    user_id,
                    {
                        "event": "agent_finished",
                        "data": response
                    }
                )
            
            elif message_type == "user_message":
                # Handle user messages - could be passed to the supervisor or stored
                text = payload.get("text", "")
                logger.info(f"Received user message from {user_id}: {text}")
                # TODO: Implement user message handling based on your requirements
                await manager.send_message(
                    user_id,
                    {
                        "event": "message_received",
                        "data": {"status": "received", "message": text}
                    }
                )
            
            elif message_type == "stop_agent":
                # Handle stop agent request
                logger.info(f"Received stop agent request from {user_id}")
                # TODO: Implement agent stopping logic if needed
                await manager.send_message(
                    user_id,
                    {
                        "event": "agent_stopped",
                        "data": {"status": "stopped"}
                    }
                )
            
            else:
                logger.warning(f"Received unhandled message type '{message_type}' for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Error in handle_websocket_message for user_id: {user_id}: {e}", exc_info=True)

def get_agent_service(db_session = Depends(get_async_db), llm_manager: LLMManager = Depends(LLMManager)) -> AgentService:
    from app.agents.supervisor import Supervisor
    from app.agents.tool_dispatcher import ToolDispatcher
    tool_dispatcher = ToolDispatcher(db_session)
    supervisor = Supervisor(db_session, llm_manager, manager, tool_dispatcher)
    return AgentService(supervisor)
