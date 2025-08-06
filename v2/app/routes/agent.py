import json
from fastapi import APIRouter, Depends, WebSocket, Request, HTTPException
from app.services.agent_service import AgentService
from app.auth_dependencies import ActiveUserWsDep
from app.websocket import manager

router = APIRouter()

def get_agent_service(request: Request) -> AgentService:
    return request.app.state.agent_service

@router.websocket("/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str, current_user: ActiveUserWsDep):
    agent_service: AgentService = websocket.app.state.agent_service
    await manager.connect(websocket, run_id)
    try:
        # Handshake
        handshake_message = await websocket.receive_text()
        handshake_data = json.loads(handshake_message)
        if handshake_data.get("type") == "handshake" and handshake_data.get("message") == "Hello from client":
            await websocket.send_text(json.dumps({"type": "handshake", "message": "Hello from server"}))
        else:
            await websocket.close(code=1008, reason="Invalid handshake")
            return

        # Handle incoming messages
        while True:
            data = await websocket.receive_text()
            await agent_service.handle_websocket_message(run_id, data)

    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
    finally:
        manager.disconnect(run_id)
