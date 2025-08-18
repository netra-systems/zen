"""Agent route WebSocket functions."""
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
import json


async def handle_websocket_json_parse(websocket: WebSocket, data: str) -> Dict:
    """Handle JSON parsing for WebSocket data."""
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        await websocket.send_json({"type": "error", "message": "Invalid JSON"})
        return None


def build_websocket_response(message_data: Dict) -> Dict:
    """Build basic WebSocket response."""
    return {
        "type": "agent_response", 
        "response": f"Processed: {message_data.get('message', '')}"
    }


def add_thread_id_to_response(response: Dict, message_data: Dict) -> Dict:
    """Add thread ID to response if present."""
    if "thread_id" in message_data:
        response["thread_id"] = message_data["thread_id"]
    return response


async def process_websocket_message(websocket: WebSocket, message_data: Dict) -> Dict:
    """Process valid WebSocket message."""
    response = build_websocket_response(message_data)
    return add_thread_id_to_response(response, message_data)


async def handle_websocket_error(websocket: WebSocket, e: Exception) -> None:
    """Handle WebSocket errors gracefully."""
    try:
        await websocket.send_json({"type": "error", "message": f"Server error: {str(e)}"})
    except:
        pass


async def process_websocket_loop(websocket: WebSocket) -> None:
    """Process WebSocket message loop."""
    while True:
        data = await websocket.receive_text()
        message_data = await handle_websocket_json_parse(websocket, data)
        if message_data:
            response = await process_websocket_message(websocket, message_data)
            await websocket.send_json(response)


async def handle_websocket_connection(websocket: WebSocket) -> None:
    """Handle WebSocket connection lifecycle."""
    await websocket.accept()
    await process_websocket_loop(websocket)


async def handle_websocket_exceptions(websocket: WebSocket) -> None:
    """Handle WebSocket connection with error handling."""
    try:
        await handle_websocket_connection(websocket)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await handle_websocket_error(websocket, e)