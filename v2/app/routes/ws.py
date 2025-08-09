
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.auth.services import security_service
from app.ws_manager import manager
from app.db.models_postgres import User
from app.db.session import get_db

router = APIRouter()

@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    user = security_service.get_current_user_ws(db=db, token=token)
    if user is None:
        await websocket.close(code=4001)
        return

    await manager.connect(user.id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # For now, just echo the message back to the user
            await manager.send_message(user.id, {"message": data})
    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)
