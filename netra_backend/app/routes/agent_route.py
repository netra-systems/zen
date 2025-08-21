"""Agent routes - Main agent endpoint handlers."""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request, WebSocket
from pydantic import BaseModel, Field

from netra_backend.app.agents.supervisor_consolidated import (
    SupervisorAgent as Supervisor,
)
from netra_backend.app.dependencies import DbDep, get_llm_manager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.routes.agent_route_processors import (
    execute_message_processing,
    process_multimodal_message,
    process_with_context,
    process_with_fallback,
)
from netra_backend.app.routes.agent_route_streaming import (
    create_streaming_response,
    get_agent_service_for_streaming,
    stream_agent_response,
)
from netra_backend.app.routes.agent_route_validators import (
    build_agent_state_response,
    build_agent_status_response,
    build_thread_runs_response,
    handle_agent_message_error,
    handle_run_agent_error,
    validate_agent_state,
    validate_agent_state_exists,
)
from netra_backend.app.schemas.Request import RequestModel
from netra_backend.app.services.agent_service import AgentService, get_agent_service
from netra_backend.app.services.state_persistence import state_persistence_service

router = APIRouter()

# Export all public functions for proper module imports
__all__ = [
    'router',
    'process_multimodal_message',
    'process_with_context', 
    'process_with_fallback',
    'stream_agent_response'
]


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Message cannot be empty")
    thread_id: Optional[str] = None


def get_agent_supervisor(request: Request) -> Supervisor:
    """Get agent supervisor from request state."""
    return request.app.state.agent_supervisor


async def execute_supervisor_run(supervisor: Supervisor, request_model: RequestModel):
    """Execute supervisor run with request."""
    await supervisor.run(
        request_model.query, request_model.id, stream_updates=True
    )
    return {"run_id": request_model.id, "status": "started"}


@router.post("/run_agent")
async def run_agent(request_model: RequestModel, supervisor: Supervisor = Depends(get_agent_supervisor)) -> Dict[str, Any]:
    """Starts the agent to analyze the user's request."""
    try:
        return await execute_supervisor_run(supervisor, request_model)
    except Exception as e:
        handle_run_agent_error(e)


@router.get("/{run_id}/status")
async def get_agent_status(run_id: str, supervisor: Supervisor = Depends(get_agent_supervisor)) -> Dict[str, Any]:
    """Get agent status for a specific run."""
    state = await supervisor.get_agent_state(run_id)
    validate_agent_state(state, run_id)
    return build_agent_status_response(run_id, state)


@router.get("/{run_id}/state")
async def get_agent_state(
    run_id: str, 
    db: DbDep
) -> Dict[str, Any]:
    """Get the full agent state for a run"""
    state = await state_persistence_service.load_agent_state(run_id, db)
    validate_agent_state_exists(state, run_id)
    return build_agent_state_response(run_id, state)


@router.get("/thread/{thread_id}/runs")
async def get_thread_runs(
    thread_id: str,
    db: DbDep,
    limit: int = 10
) -> Dict[str, Any]:
    """Get all runs for a thread"""
    runs = await state_persistence_service.list_thread_runs(thread_id, db, limit)
    return build_thread_runs_response(thread_id, runs)


@router.post("/message")
async def process_agent_message(request: MessageRequest, agent_service: AgentService = Depends(get_agent_service)) -> Dict[str, Any]:
    """Process a message through the agent system."""
    try:
        return await execute_message_processing(agent_service, request.message, request.thread_id)
    except Exception as e:
        await handle_agent_message_error(e)


@router.post("/stream")
async def stream_response(
    request_model: RequestModel,
    db_session: DbDep,
    llm_manager: LLMManager = Depends(get_llm_manager)
):
    """Stream agent response with proper SSE format."""
    agent_service = get_agent_service_for_streaming(db_session, llm_manager)
    return create_streaming_response(request_model, agent_service)


