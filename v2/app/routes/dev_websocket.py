import asyncio
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
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30)
                await dev_bypass_service.handle_message(data)
            except asyncio.TimeoutError:
                # No message received within the timeout period, continue listening
                continue
    except WebSocketDisconnect:
        print("Dev WebSocket disconnected")