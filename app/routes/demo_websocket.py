"""Demo WebSocket handlers with ≤8 line functions for real-time demo interactions."""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, List
import json
import asyncio
import uuid

from app.services.demo_service import DemoService
from app.logging_config import central_logger
from app.schemas.demo_schemas import DemoWSMessage, DemoWSResponse


async def handle_demo_websocket(
    websocket: WebSocket,
    demo_service: DemoService
) -> None:
    """Main WebSocket endpoint handler for real-time demo interactions."""
    await websocket.accept()
    logger = central_logger.get_logger(__name__)
    session_id = _generate_ws_session_id()
    
    try:
        await _send_connection_established(websocket, session_id)
        await _handle_websocket_messages(websocket, demo_service, session_id, logger)
    except WebSocketDisconnect:
        logger.info(f"Demo WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Demo WebSocket error: {str(e)}")
        await _close_websocket_with_error(websocket, e)


def _generate_ws_session_id() -> str:
    """Generate unique session ID for WebSocket connection."""
    return f"demo-ws-{uuid.uuid4()}"


async def _send_connection_established(websocket: WebSocket, session_id: str) -> None:
    """Send connection established message to client."""
    await websocket.send_json({
        "type": "connection_established",
        "session_id": session_id,
        "message": "Connected to Netra AI Demo WebSocket"
    })


async def _handle_websocket_messages(
    websocket: WebSocket,
    demo_service: DemoService,
    session_id: str,
    logger: Any
) -> None:
    """Handle incoming WebSocket messages."""
    while True:
        data = await websocket.receive_text()
        message_data = json.loads(data)
        await _process_message_by_type(websocket, demo_service, session_id, message_data)


async def _process_message_by_type(
    websocket: WebSocket,
    demo_service: DemoService,
    session_id: str,
    message_data: Dict[str, Any]
) -> None:
    """Route message processing based on message type."""
    message_type = message_data.get("type")
    
    if message_type == "chat":
        await _handle_chat_message(websocket, demo_service, session_id, message_data)
    elif message_type == "metrics":
        await _handle_metrics_message(websocket, demo_service, message_data)
    elif message_type == "ping":
        await _handle_ping_message(websocket)


async def _handle_chat_message(
    websocket: WebSocket,
    demo_service: DemoService,
    session_id: str,
    message_data: Dict[str, Any]
) -> None:
    """Handle chat message with agent progression simulation."""
    await _send_processing_started(websocket)
    await _simulate_agent_progression(websocket)
    result = await _process_chat_with_service(demo_service, session_id, message_data)
    await _send_chat_response(websocket, result, session_id)


async def _send_processing_started(websocket: WebSocket) -> None:
    """Send processing started acknowledgment."""
    await websocket.send_json({
        "type": "processing_started",
        "agents": ["triage", "analysis", "optimization"]
    })


async def _simulate_agent_progression(websocket: WebSocket) -> None:
    """Simulate agent progression with real-time updates."""
    agents = ["triage", "analysis", "optimization", "reporting"]
    for i, agent in enumerate(agents):
        await asyncio.sleep(0.8)
        await _send_agent_update(websocket, agent, i, len(agents))


async def _send_agent_update(
    websocket: WebSocket,
    agent: str,
    current_index: int,
    total_agents: int
) -> None:
    """Send agent progression update."""
    await websocket.send_json({
        "type": "agent_update",
        "active_agent": agent,
        "progress": (current_index + 1) / total_agents * 100,
        "message": f"Agent {agent} is processing your request..."
    })


async def _process_chat_with_service(
    demo_service: DemoService,
    session_id: str,
    message_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Process chat message using demo service."""
    return await demo_service.process_demo_chat(
        message=message_data.get("message", ""),
        industry=message_data.get("industry", "technology"),
        session_id=session_id,
        context=message_data.get("context", {})
    )


async def _send_chat_response(
    websocket: WebSocket,
    result: Dict[str, Any],
    session_id: str
) -> None:
    """Send final chat response to client."""
    await websocket.send_json({
        "type": "chat_response",
        "response": result["response"],
        "agents_involved": result["agents"],
        "optimization_metrics": result["metrics"],
        "session_id": session_id
    })


async def _handle_metrics_message(
    websocket: WebSocket,
    demo_service: DemoService,
    message_data: Dict[str, Any]
) -> None:
    """Handle metrics streaming request."""
    metrics = await _generate_streaming_metrics(demo_service, message_data)
    await _stream_metrics_data(websocket, metrics)


async def _generate_streaming_metrics(
    demo_service: DemoService,
    message_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate synthetic metrics for streaming."""
    return await demo_service.generate_synthetic_metrics(
        scenario=message_data.get("scenario", "standard"),
        duration_hours=1
    )


async def _stream_metrics_data(websocket: WebSocket, metrics: Dict[str, Any]) -> None:
    """Stream metrics data points to client."""
    for i in range(len(metrics["timestamps"])):
        await _send_metrics_update(websocket, metrics, i)
        await asyncio.sleep(0.1)


async def _send_metrics_update(
    websocket: WebSocket,
    metrics: Dict[str, Any],
    index: int
) -> None:
    """Send individual metrics update."""
    timestamp = metrics["timestamps"][index]
    timestamp_str = _format_timestamp(timestamp)
    values = _extract_metric_values(metrics["values"], index)
    
    await websocket.send_json({
        "type": "metrics_update",
        "timestamp": timestamp_str,
        "values": values
    })


def _format_timestamp(timestamp: Any) -> str:
    """Format timestamp for JSON serialization."""
    if hasattr(timestamp, 'isoformat'):
        return timestamp.isoformat()
    return str(timestamp)


def _extract_metric_values(values_dict: Dict[str, List], index: int) -> Dict[str, float]:
    """Extract metric values for specific index."""
    return {
        key: values[index] if index < len(values) else 0
        for key, values in values_dict.items()
    }


async def _handle_ping_message(websocket: WebSocket) -> None:
    """Handle ping message for connection keep-alive."""
    await websocket.send_json({"type": "pong"})


async def _close_websocket_with_error(websocket: WebSocket, error: Exception) -> None:
    """Close WebSocket connection with error code."""
    await websocket.close(code=1011, reason=str(error))