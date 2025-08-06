
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.dev_bypass_service import DevBypassService
import json

router = APIRouter()

@router.websocket("/")
async def dev_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    dev_bypass_service = DevBypassService(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await dev_bypass_service.handle_message(data)
    except WebSocketDisconnect:
        print("Dev WebSocket disconnected")
