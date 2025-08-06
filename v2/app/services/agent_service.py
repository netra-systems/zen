import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from app.services.streaming_agent.supervisor import StreamingAgentSupervisor
from app.db.models_clickhouse import AnalysisRequest
from app.websocket import manager

class AgentService:
    def __init__(self, supervisor: StreamingAgentSupervisor):
        self.supervisor = supervisor

    async def start_agent(self, analysis_request: AnalysisRequest, run_id: str):
        """
        Starts the agent and streams the logs back to the websocket.
        """
        async for log in self.supervisor.start_agent(analysis_request, run_id):
            await manager.broadcast(run_id, json.dumps(log))

    async def handle_websocket_message(self, run_id: str, data: str):
        """
        Handles a message from the WebSocket.
        """
        message_data = json.loads(data)
        if message_data.get("action") == "start_agent":
            analysis_request = AnalysisRequest(**message_data.get("payload"))
            asyncio.create_task(self.start_agent(analysis_request, run_id))
        else:
            print(f"Received unhandled message for run_id: {run_id}: {message_data}")

    async def handle_websocket(self, websocket: WebSocket, run_id: str):
        """
        Handles the WebSocket connection for the agent.
        """
        await websocket.accept()
        try:
            while True:
                # This is a placeholder for the actual logic to get the agent's status and logs
                # In a real implementation, you would have a way to access the agent's state and logs using the run_id
                await websocket.send_text(f"Message for run_id: {run_id}")
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            print(f"WebSocket disconnected for run_id: {run_id}")
