from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from app.ws_manager import manager
from app.auth.auth_dependencies import get_current_user
from app.schemas import User

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user: User = Depends(get_current_user)):
    if user is None:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, user)
    try:
        while True:
            data = await websocket.receive_text()
            # Process incoming messages if needed
    except WebSocketDisconnect:
        manager.disconnect(str(user.id), websocket)
