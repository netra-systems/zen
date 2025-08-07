import json
import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect
from app.services.deepagents.overall_supervisor import OverallSupervisor
from app.db.models_clickhouse import AnalysisRequest, Settings, RequestModel
from app.schemas import WebSocketMessage

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self, supervisor: OverallSupervisor):
        self.supervisor = supervisor

    async def start_agent(self, analysis_request: AnalysisRequest, run_id: str, stream_updates: bool = False):
        """
        Starts the agent. The supervisor will stream logs back to the websocket if requested.
        """
        return await self.supervisor.start_agent(analysis_request, run_id, stream_updates)

    async def handle_websocket_message(self, run_id: str, data: str):
        """
        Handles a message from the WebSocket.
        """
        logger.info(f"handle_websocket_message called for run_id: {run_id} with data: {data}")
        try:
            message_data = json.loads(data)
            if message_data.get("action") == "start_agent":
                payload = message_data.get("payload")
                settings = payload.get("settings")
                request_data = payload.get("request")
                
                analysis_request = AnalysisRequest(
                    settings=Settings(**settings),
                    request=RequestModel(**request_data)
                )
                # When started from a websocket, we always want to stream updates
                response = await self.start_agent(analysis_request, run_id, stream_updates=True)
                await manager.send_to_run(
                    WebSocketMessage(
                        event="agent_started",
                        data=response,
                        run_id=run_id
                    )
                )

            else:
                logger.warning(f"Received unhandled message for run_id: {run_id}: {message_data}")
        except Exception as e:
            logger.error(f"Error in handle_websocket_message for run_id: {run_id}: {e}", exc_info=True)

    async def handle_websocket(self, websocket: WebSocket, run_id: str):
        """
        Handles the WebSocket connection for the agent.
        """
        await websocket.accept()
        try:
            while True:
                await asyncio.sleep(0.1)  # Keep the connection alive
        except WebSocketDisconnect:
            manager.disconnect(run_id)
            print(f"WebSocket disconnected for run_id: {run_id}")
