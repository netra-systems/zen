"""Agent route streaming functions."""
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi.responses import StreamingResponse
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.routes.unified_tools.schemas import RequestModel
from netra_backend.app.routes.agent_route_helpers import delegate_streaming


def get_agent_service_for_streaming(db_session, llm_manager) -> AgentService:
    """Get agent service for streaming."""
    from netra_backend.app.services.agent_service import get_agent_service
    return get_agent_service(db_session, llm_manager)


async def generate_sse_stream(
    request_model: RequestModel, agent_service: AgentService
) -> AsyncGenerator[str, None]:
    """Generate SSE formatted stream."""
    async for chunk in stream_agent_response(
        request_model.query, request_model.id, agent_service
    ):
        yield f"data: {chunk}\n\n"


def build_streaming_headers() -> Dict[str, str]:
    """Build headers for streaming response."""
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"  # Disable nginx buffering
    }


def get_sse_generator(request_model: RequestModel, agent_service: AgentService):
    """Get SSE stream generator."""
    return generate_sse_stream(request_model, agent_service)


def create_streaming_response(
    request_model: RequestModel, agent_service: AgentService
) -> StreamingResponse:
    """Create streaming response with headers."""
    generator = get_sse_generator(request_model, agent_service)
    headers = build_streaming_headers()
    return StreamingResponse(generator, media_type="text/event-stream", headers=headers)


async def stream_agent_response(
    message: str,
    thread_id: Optional[str] = None,
    agent_service: Optional[AgentService] = None
) -> AsyncGenerator[str, None]:
    """Stream agent response using the actual agent service."""
    async for chunk in delegate_streaming(agent_service, message, thread_id):
        yield chunk