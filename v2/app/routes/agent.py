import json
from fastapi import APIRouter, Depends, WebSocket, Request, HTTPException
from app.services.agent_service import AgentService
from app.auth.auth_dependencies import ActiveUserWsDep
from app.websocket import manager

router = APIRouter()

def get_agent_service(request: Request) -> AgentService:
    return request.app.state.agent_service

@router.websocket("/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str, current_user: ActiveUserWsDep, agent_service: AgentService = Depends(get_agent_service)):
    await manager.connect(websocket, run_id)
    try:
        # The first message is the start_agent command
        initial_message = await websocket.receive_text()
        await agent_service.handle_websocket_message(run_id, initial_message)

        # Keep the connection alive to allow the agent to send messages
        while True:
            await websocket.receive_text() # Keep the connection open

    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
    finally:
        manager.disconnect(run_id)