"""Demo WebSocket handlers with ≤8 line functions for real-time demo interactions."""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, List
import json
import asyncio
import uuid

from app.services.demo_service import DemoService
from app.logging_config import central_logger
from app.schemas.demo_schemas import DemoWSMessage, DemoWSResponse


async def _initialize_websocket_session(websocket: WebSocket):
    """Initialize WebSocket session and return session data."""
    await websocket.accept()
    logger = central_logger.get_logger(__name__)
    session_id = _generate_ws_session_id()
    return logger, session_id

async def _handle_websocket_lifecycle(websocket: WebSocket, demo_service: DemoService, session_id: str, logger):
    """Handle WebSocket lifecycle from connection to close."""
    await _send_connection_established(websocket, session_id)
    await _handle_websocket_messages(websocket, demo_service, session_id, logger)

async def _handle_websocket_exceptions(e: Exception, websocket: WebSocket, session_id: str, logger):
    """Handle WebSocket exceptions with proper logging."""
    if isinstance(e, WebSocketDisconnect):
        logger.info(f"Demo WebSocket disconnected: {session_id}")
    else:
        logger.error(f"Demo WebSocket error: {str(e)}")
        await _close_websocket_with_error(websocket, e)

async def handle_demo_websocket(
    websocket: WebSocket, demo_service: DemoService
) -> None:
    """Main WebSocket endpoint handler."""
    logger, session_id = await _initialize_websocket_session(websocket)
    await _manage_websocket_connection(websocket, demo_service, session_id, logger)


async def _manage_websocket_connection(websocket: WebSocket, demo_service: DemoService, session_id: str, logger):
    """Manage WebSocket connection lifecycle."""
    try:
        await _handle_websocket_lifecycle(websocket, demo_service, session_id, logger)
    except Exception as e:
        await _handle_websocket_exceptions(e, websocket, session_id, logger)


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
    websocket: WebSocket, demo_service: DemoService, session_id: str, logger: Any
) -> None:
    """Handle incoming WebSocket messages."""
    while True:
        data = await websocket.receive_text()
        message_data = json.loads(data)
        await _process_message_by_type(websocket, demo_service, session_id, message_data)


async def _route_chat_message(websocket: WebSocket, demo_service: DemoService, session_id: str, message_data: Dict[str, Any]) -> None:
    """Route chat message to handler."""
    await _handle_chat_message(websocket, demo_service, session_id, message_data)

async def _route_metrics_message(websocket: WebSocket, demo_service: DemoService, message_data: Dict[str, Any]) -> None:
    """Route metrics message to handler."""
    await _handle_metrics_message(websocket, demo_service, message_data)

async def _route_ping_message(websocket: WebSocket) -> None:
    """Route ping message to handler."""
    await _handle_ping_message(websocket)

async def _process_message_by_type(
    websocket: WebSocket, demo_service: DemoService, session_id: str, message_data: Dict[str, Any]
) -> None:
    """Route message processing by type."""
    message_type = message_data.get("type")
    await _route_message_by_type(websocket, demo_service, session_id, message_data, message_type)


async def _route_message_by_type(
    websocket: WebSocket, demo_service: DemoService, session_id: str,
    message_data: Dict[str, Any], message_type: str
) -> None:
    """Route message to appropriate handler."""
    routing_map = _build_message_routing_map(websocket, demo_service, session_id, message_data)
    await _execute_message_route(message_type, routing_map)


def _build_message_routing_map(websocket: WebSocket, demo_service: DemoService, session_id: str, message_data: Dict[str, Any]):
    """Build message routing map for different types."""
    return {
        "chat": lambda: _route_chat_message(websocket, demo_service, session_id, message_data),
        "metrics": lambda: _route_metrics_message(websocket, demo_service, message_data),
        "ping": lambda: _route_ping_message(websocket)
    }


async def _execute_message_route(message_type: str, routing_map: Dict):
    """Execute message route based on type."""
    handler = routing_map.get(message_type)
    if handler:
        await handler()


async def _handle_chat_message(
    websocket: WebSocket, demo_service: DemoService, session_id: str, message_data: Dict[str, Any]
) -> None:
    """Handle chat message with progression."""
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
    websocket: WebSocket, agent: str, current_index: int, total_agents: int
) -> None:
    """Send agent progression update."""
    progress = (current_index + 1) / total_agents * 100
    update_data = _build_agent_update_data(agent, progress)
    await websocket.send_json(update_data)


def _build_agent_update_data(agent: str, progress: float) -> Dict[str, Any]:
    """Build agent update data."""
    return {
        "type": "agent_update",
        "active_agent": agent,
        "progress": progress,
        "message": f"Agent {agent} is processing your request..."
    }


async def _process_chat_with_service(
    demo_service: DemoService, session_id: str, message_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Process chat message using service."""
    chat_params = _extract_chat_parameters(message_data, session_id)
    return await demo_service.process_demo_chat(**chat_params)


def _extract_chat_parameters(message_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Extract chat parameters from message."""
    return {
        "message": message_data.get("message", ""),
        "industry": message_data.get("industry", "technology"),
        "session_id": session_id,
        "context": message_data.get("context", {})
    }


async def _send_chat_response(
    websocket: WebSocket, result: Dict[str, Any], session_id: str
) -> None:
    """Send final chat response to client."""
    response_data = _build_chat_response_data(result, session_id)
    await websocket.send_json(response_data)


def _build_chat_response_data(result: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Build chat response data."""
    response_data = _create_base_chat_response(result)
    response_data["session_id"] = session_id
    return response_data


def _create_base_chat_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Create base chat response structure."""
    return {
        "type": "chat_response", "response": result["response"],
        "agents_involved": result["agents"], "optimization_metrics": result["metrics"]
    }


async def _handle_metrics_message(
    websocket: WebSocket,
    demo_service: DemoService,
    message_data: Dict[str, Any]
) -> None:
    """Handle metrics streaming request."""
    metrics = await _generate_streaming_metrics(demo_service, message_data)
    await _stream_metrics_data(websocket, metrics)


async def _generate_streaming_metrics(
    demo_service: DemoService, message_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate synthetic metrics."""
    scenario = message_data.get("scenario", "standard")
    return await demo_service.generate_synthetic_metrics(
        scenario=scenario, duration_hours=1
    )


async def _stream_metrics_data(websocket: WebSocket, metrics: Dict[str, Any]) -> None:
    """Stream metrics data points to client."""
    for i in range(len(metrics["timestamps"])):
        await _send_metrics_update(websocket, metrics, i)
        await asyncio.sleep(0.1)


async def _send_metrics_update(
    websocket: WebSocket, metrics: Dict[str, Any], index: int
) -> None:
    """Send individual metrics update."""
    update_data = _build_metrics_update_data(metrics, index)
    await websocket.send_json(update_data)


def _build_metrics_update_data(metrics: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Build metrics update data."""
    timestamp_str = _format_timestamp(metrics["timestamps"][index])
    values = _extract_metric_values(metrics["values"], index)
    return _create_metrics_response(timestamp_str, values)


def _create_metrics_response(timestamp_str: str, values: Dict[str, float]) -> Dict[str, Any]:
    """Create metrics response structure."""
    return {"type": "metrics_update", "timestamp": timestamp_str, "values": values}


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