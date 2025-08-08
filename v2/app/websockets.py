import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from app.auth.auth_dependencies import ActiveUserWsDep
from app.agents.supervisor import Supervisor
from app.schemas import WebSocketMessage, RequestModel
from app.ws_manager import manager

websockets_router = APIRouter()

def get_agent_supervisor(request: Request) -> Supervisor:
    return request.app.state.agent_supervisor

@websockets_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user: ActiveUserWsDep = Depends(get_current_active_user_ws), supervisor: Supervisor = Depends(get_agent_supervisor)):
    await manager.connect(websocket, user.id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                if data == 'ping':
                    await websocket.send_text('pong')
                    continue

                try:
                    message = WebSocketMessage.parse_raw(data)
                    if message.type == "analysis_request":
                        request_model = RequestModel.parse_obj(message.payload)
                        await supervisor.run(request_model.model_dump(), request_model.id, stream_updates=True)
                    else:
                        print(f"Received unknown message type: {message.type}")

                except json.JSONDecodeError:
                    print("Failed to decode JSON from WebSocket message.")
                except Exception as e:
                    print(f"Error processing message: {e}")
                    await manager.broadcast_to_client(user.id, {"error": "Internal server error."})

            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for user {user.id}")
    except Exception as e:
        print(f"WebSocket connection failed for user {user.id}: {e}")
    finally:
        manager.disconnect(websocket, user.id)

@websockets_router.websocket("/dev")
async def dev_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json({"echo": data})
    except WebSocketDisconnect:
        print("Dev WebSocket disconnected")