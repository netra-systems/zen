"""Agent routes - Main agent endpoint handlers."""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request, WebSocket
from pydantic import BaseModel, Field

from netra_backend.app.agents.supervisor_consolidated import (
    SupervisorAgent as Supervisor,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
from netra_backend.app.dependencies import (
    DbDep, 
    get_llm_manager,
    RequestScopedDbDep,
    RequestScopedContextDep,
    RequestScopedSupervisorDep,
    get_request_scoped_supervisor_dependency
)
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.routes.agent_route_processors import (
    execute_message_processing,
    process_multimodal_message,
    process_with_context,
    process_with_fallback,
)
from netra_backend.app.routes.agent_route_streaming import (
    create_streaming_response,
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
from netra_backend.app.schemas.request import RequestModel
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
    """Get agent supervisor from request state.
    
    DEPRECATED: Use RequestScopedSupervisorDep for new routes.
    """
    logger.warning("Using legacy get_agent_supervisor - consider RequestScopedSupervisorDep")
    return request.app.state.agent_supervisor


async def execute_supervisor_run(supervisor: Supervisor, request_model: RequestModel):
    """Execute supervisor run with request."""
    await supervisor.run(
        request_model.query, request_model.id, stream_updates=True
    )
    return {"run_id": request_model.id, "status": "started"}


@router.post("/run_agent")
async def run_agent(
    request_model: RequestModel,
    context: RequestScopedContextDep,
    supervisor: RequestScopedSupervisorDep
) -> Dict[str, Any]:
    """Starts the agent to analyze the user's request using UserExecutionContext pattern.
    
    UPDATED: Now uses request-scoped dependencies and UserExecutionContext for proper isolation.
    """
    logger.info(f"Processing run_agent with UserExecutionContext for user {context.user_id}, run {context.run_id}")
    try:
        # Execute using request-scoped supervisor with proper session lifecycle
        await supervisor.run(
            request_model.query, 
            request_model.id or context.run_id, 
            stream_updates=True
        )
        return {
            "run_id": request_model.id or context.run_id, 
            "status": "started",
            "user_id": context.user_id,
            "request_scoped": True
        }
    except Exception as e:
        logger.error(f"Request-scoped run_agent failed for user {context.user_id}: {e}")
        handle_run_agent_error(e)

@router.post("/run_agent_v2")
async def run_agent_v2(
    request_model: RequestModel,
    context: RequestScopedContextDep,
    supervisor: RequestScopedSupervisorDep
) -> Dict[str, Any]:
    """Starts the agent to analyze the user's request using request-scoped dependencies.
    
    NEW VERSION: This route uses proper request-scoped database session management.
    Database sessions are never stored globally and are automatically closed after request.
    """
    logger.info(f"Processing run_agent_v2 for user {context.user_id}, run {context.run_id}")
    try:
        # Execute using request-scoped supervisor with proper session lifecycle
        await supervisor.run(
            request_model.query, 
            request_model.id or context.run_id, 
            stream_updates=True
        )
        return {
            "run_id": request_model.id or context.run_id, 
            "status": "started",
            "user_id": context.user_id,
            "session_scoped": True
        }
    except Exception as e:
        logger.error(f"Request-scoped run_agent_v2 failed for user {context.user_id}: {e}")
        handle_run_agent_error(e)


@router.get("/{run_id}/status")
async def get_agent_status(
    run_id: str,
    context: RequestScopedContextDep,
    supervisor: RequestScopedSupervisorDep
) -> Dict[str, Any]:
    """Get agent status for a specific run using request-scoped dependencies.
    
    UPDATED: Now uses proper request-scoped database session management.
    """
    logger.info(f"Getting agent status for run {run_id}, user {context.user_id}")
    state = await supervisor.get_agent_state(run_id)
    validate_agent_state(state, run_id)
    response = build_agent_status_response(run_id, state)
    response["request_scoped"] = True
    response["user_id"] = context.user_id
    return response

@router.get("/v2/{run_id}/status")
async def get_agent_status_v2(
    run_id: str,
    context: RequestScopedContextDep,
    supervisor: RequestScopedSupervisorDep
) -> Dict[str, Any]:
    """Get agent status for a specific run using request-scoped dependencies.
    
    NEW VERSION: Uses proper request-scoped database session management.
    """
    logger.info(f"Getting agent status v2 for run {run_id}, user {context.user_id}")
    state = await supervisor.get_agent_state(run_id)
    validate_agent_state(state, run_id)
    response = build_agent_status_response(run_id, state)
    response["session_scoped"] = True
    response["user_id"] = context.user_id
    return response


@router.get("/{run_id}/state")
async def get_agent_state(
    run_id: str, 
    db: DbDep
) -> Dict[str, Any]:
    """Get the full agent state for a run.
    
    DEPRECATED ROUTE: Uses legacy dependency injection.
    """
    logger.warning("Using legacy get_agent_state route")
    state = await state_persistence_service.load_agent_state(run_id, db)
    validate_agent_state_exists(state, run_id)
    return build_agent_state_response(run_id, state)

@router.get("/v2/{run_id}/state")
async def get_agent_state_v2(
    run_id: str,
    context: RequestScopedContextDep,
    db: RequestScopedDbDep
) -> Dict[str, Any]:
    """Get the full agent state for a run using request-scoped dependencies.
    
    NEW VERSION: Uses proper request-scoped database session management.
    """
    logger.info(f"Getting agent state v2 for run {run_id}, user {context.user_id}")
    state = await state_persistence_service.load_agent_state(run_id, db)
    validate_agent_state_exists(state, run_id)
    response = build_agent_state_response(run_id, state)
    response["session_scoped"] = True
    response["user_id"] = context.user_id
    return response


@router.get("/thread/{thread_id}/runs")
async def get_thread_runs(
    thread_id: str,
    db: DbDep,
    limit: int = 10
) -> Dict[str, Any]:
    """Get all runs for a thread.
    
    DEPRECATED ROUTE: Uses legacy dependency injection.
    """
    logger.warning("Using legacy get_thread_runs route")
    runs = await state_persistence_service.list_thread_runs(thread_id, db, limit)
    return build_thread_runs_response(thread_id, runs)

@router.get("/v2/thread/{thread_id}/runs")
async def get_thread_runs_v2(
    thread_id: str,
    context: RequestScopedContextDep,
    db: RequestScopedDbDep,
    limit: int = 10
) -> Dict[str, Any]:
    """Get all runs for a thread using request-scoped dependencies.
    
    NEW VERSION: Uses proper request-scoped database session management.
    """
    logger.info(f"Getting thread runs v2 for thread {thread_id}, user {context.user_id}")
    runs = await state_persistence_service.list_thread_runs(thread_id, db, limit)
    response = build_thread_runs_response(thread_id, runs)
    response["session_scoped"] = True
    response["user_id"] = context.user_id
    return response


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
    agent_service: AgentService = Depends(get_agent_service)
):
    """Stream agent response with proper SSE format."""
    return create_streaming_response(request_model, agent_service)


