"""Demo chat handlers."""
from fastapi import BackgroundTasks
from typing import Optional, Dict, Any
import uuid

from app.services.demo_service import DemoService
from app.schemas.demo_schemas import DemoChatRequest, DemoChatResponse


async def handle_demo_chat(
    request: DemoChatRequest,
    background_tasks: BackgroundTasks,
    demo_service: DemoService,
    current_user: Optional[Dict]
) -> DemoChatResponse:
    """Handle demo chat interactions."""
    return await execute_demo_chat_flow(request, background_tasks, demo_service, current_user)


async def execute_demo_chat_flow(
    request: DemoChatRequest, background_tasks: BackgroundTasks, 
    demo_service: DemoService, current_user: Optional[Dict]
) -> DemoChatResponse:
    """Execute complete demo chat flow."""
    session_id = get_or_create_session_id(request.session_id)
    result = await process_chat_request(request, session_id, demo_service, current_user)
    track_chat_interaction(background_tasks, demo_service, session_id, request)
    return create_chat_response(result, session_id)


def get_or_create_session_id(session_id: Optional[str]) -> str:
    """Get existing session ID or create a new one."""
    return session_id or str(uuid.uuid4())


async def execute_demo_chat_service(
    request: DemoChatRequest, session_id: str, demo_service: DemoService, current_user: Optional[Dict]
) -> Dict[str, Any]:
    """Execute demo chat through service."""
    user_id = current_user.get("id") if current_user else None
    return await demo_service.process_demo_chat(
        message=request.message, industry=request.industry,
        session_id=session_id, context=request.context, user_id=user_id
    )


async def process_chat_request(
    request: DemoChatRequest, session_id: str, demo_service: DemoService, current_user: Optional[Dict]
) -> Dict[str, Any]:
    """Process the demo chat request using demo service."""
    try:
        return await execute_demo_chat_service(request, session_id, demo_service, current_user)
    except Exception as e:
        from app.routes.demo_handlers_utils import log_and_raise_error
        log_and_raise_error("Demo chat processing failed", e)


def create_chat_tracking_data(request: DemoChatRequest) -> Dict[str, Any]:
    """Create tracking data for chat interaction."""
    return {"industry": request.industry, "message_length": len(request.message)}


def add_chat_tracking_task(
    background_tasks: BackgroundTasks, demo_service: DemoService, session_id: str, data: Dict[str, Any]
) -> None:
    """Add chat tracking task to background."""
    background_tasks.add_task(
        demo_service.track_demo_interaction,
        session_id=session_id, interaction_type="chat", data=data
    )


def track_chat_interaction(
    background_tasks: BackgroundTasks, demo_service: DemoService, session_id: str, request: DemoChatRequest
) -> None:
    """Track demo analytics in background."""
    data = create_chat_tracking_data(request)
    add_chat_tracking_task(background_tasks, demo_service, session_id, data)


def create_chat_response(result: Dict[str, Any], session_id: str) -> DemoChatResponse:
    """Create chat response from service result."""
    return DemoChatResponse(
        response=result["response"],
        agents_involved=result["agents"],
        optimization_metrics=result["metrics"],
        session_id=session_id
    )