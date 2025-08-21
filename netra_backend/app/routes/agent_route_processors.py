"""Agent route processing functions."""
from typing import Dict, Any, Optional, Union, List
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.routes.agent_route_helpers import MultimodalInput, AttachmentData


async def process_message_with_agent_service(
    agent_service: AgentService, message: str, thread_id: Optional[str]
) -> Dict[str, Any]:
    """Process message using agent service."""
    return await agent_service.process_message(message, thread_id)


async def execute_message_processing(
    agent_service: AgentService, message: str, thread_id: Optional[str]
) -> Dict[str, Any]:
    """Execute message processing with service."""
    return await process_message_with_agent_service(
        agent_service, message, thread_id
    )


async def process_multimodal_attachments(attachments: List[AttachmentData]) -> Dict[str, Any]:
    """Process multimodal attachments and return processing metadata."""
    processed_count = len(attachments)
    attachment_types = [att.type for att in attachments]
    return {"processed_attachments": processed_count, "types": attachment_types}


async def execute_multimodal_processing(multimodal_input: MultimodalInput) -> Dict[str, Any]:
    """Execute multimodal message processing with attachments."""
    from netra_backend.app.services.agent_service import process_multimodal
    attachment_data = await process_multimodal_attachments(multimodal_input.attachments)
    result = await process_multimodal(multimodal_input.model_dump())
    return {**result, **attachment_data}


async def process_multimodal_message(multimodal_input: Union[Dict[str, Any], MultimodalInput]) -> Dict[str, Any]:
    """Process multimodal message with text and attachments."""
    if isinstance(multimodal_input, dict):
        multimodal_input = MultimodalInput(**multimodal_input)
    return await execute_multimodal_processing(multimodal_input)


async def execute_context_processing(message: str, thread_id: str, agent_service: AgentService) -> Dict[str, Any]:
    """Execute message processing with context management."""
    result = await agent_service.process_message(message, thread_id)
    context_data = {"thread_id": thread_id, "message_count": 1}
    return {**result, "context": context_data}


async def process_with_context(message: str, thread_id: str, agent_service: AgentService) -> Dict[str, Any]:
    """Process message with context and thread management."""
    return await execute_context_processing(message, thread_id, agent_service)


async def attempt_primary_processing(message: str) -> Dict[str, Any]:
    """Attempt processing with primary agent."""
    from netra_backend.app.services.agent_service import get_primary_agent
    primary_agent = get_primary_agent()
    return await primary_agent.process_message(message)


async def attempt_fallback_processing(message: str) -> Dict[str, Any]:
    """Attempt processing with fallback agent."""
    from netra_backend.app.services.agent_service import get_fallback_agent
    fallback_agent = get_fallback_agent()
    result = await fallback_agent.process_message(message)
    return {**result, "agent": "fallback", "status": "recovered"}


async def process_with_fallback(message: str) -> Dict[str, Any]:
    """Process message with fallback and recovery mechanisms."""
    try:
        return await attempt_primary_processing(message)
    except Exception:
        return await attempt_fallback_processing(message)