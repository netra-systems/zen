"""Agent route helper functions - Supporting utilities for agent routes."""
import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from fastapi import HTTPException, WebSocket
from pydantic import BaseModel

from netra_backend.app.schemas.request import RequestModel
from netra_backend.app.services.agent_service import AgentService


class AttachmentData(BaseModel):
    """Multimodal attachment data model."""
    type: str
    url: Optional[str] = None
    content: Optional[str] = None


class MultimodalInput(BaseModel):
    """Multimodal input containing text and attachments."""
    text: str
    attachments: List[AttachmentData] = []


def format_chunk_output(chunk) -> str:
    """Format chunk for streaming output."""
    if isinstance(chunk, dict):
        return json.dumps(chunk)
    elif isinstance(chunk, str):
        return chunk
    return json.dumps({"type": "data", "content": str(chunk)})


async def stream_with_fallback_service(message: str, thread_id: Optional[str]) -> AsyncGenerator[str, None]:
    """Stream using fallback service for backward compatibility."""
    from netra_backend.app.services.agent_service import generate_stream
    async for chunk in generate_stream(message, thread_id):
        yield format_chunk_output(chunk)
    yield json.dumps({"type": "complete", "status": "finished"})


async def stream_with_agent_service(
    agent_service: AgentService, message: str, thread_id: Optional[str]
) -> AsyncGenerator[str, None]:
    """Stream using provided agent service."""
    async for chunk in agent_service.generate_stream(message, thread_id):
        yield format_chunk_output(chunk)
    yield json.dumps({"type": "complete", "status": "finished"})


async def get_stream_generator(
    agent_service: Optional[AgentService], message: str, thread_id: Optional[str]
):
    """Get appropriate stream generator."""
    if not agent_service:
        return stream_with_fallback_service(message, thread_id)
    return stream_with_agent_service(agent_service, message, thread_id)


async def delegate_streaming(
    agent_service: Optional[AgentService], message: str, thread_id: Optional[str]
) -> AsyncGenerator[str, None]:
    """Delegate streaming to appropriate service."""
    stream_gen = await get_stream_generator(agent_service, message, thread_id)
    async for chunk in stream_gen:
        yield chunk