from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from app.ws_manager import manager
from app import schemas
from app.auth.auth_dependencies import ActiveUserWsDep
from app.services.agent_service import AgentService, get_agent_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user: schemas.User = Depends(ActiveUserWsDep),
    agent_service: AgentService = Depends(get_agent_service),
):
    if user is None:
        await websocket.close(code=1008)
        return

    user_id = str(user.id)
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await agent_service.handle_websocket_message(user_id, data)

    except WebSocketDisconnect:
        manager.disconnect(user_id)