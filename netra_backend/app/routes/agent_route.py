"""Agent routes - Main agent endpoint handlers."""
from typing import Any, Dict, Optional, Annotated

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
    get_request_scoped_supervisor_dependency,
    create_user_execution_context,
    get_request_scoped_user_context
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
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


# Custom dependency functions for creating user contexts
async def get_default_user_context(
    user_id: str = "default_user",
    thread_id: str = "default_thread",
    run_id: Optional[str] = None
) -> "RequestScopedContext":
    """Create default user context for endpoints that don't have user parameters.
    
    This is a temporary solution for legacy endpoint compatibility.
    In production, user_id should come from authentication.
    """
    return await get_request_scoped_user_context(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id
    )


async def get_message_user_context(
    user_id: str = "default_user",
    thread_id: str = "default_thread"
) -> "RequestScopedContext":
    """Create user context for message endpoint."""
    return await get_request_scoped_user_context(
        user_id=user_id,
        thread_id=thread_id
    )


async def get_stream_user_context(
    user_id: str = "default_user",
    thread_id: str = "default_thread",
    run_id: Optional[str] = None
) -> "RequestScopedContext":
    """Create user context for stream endpoint."""
    return await get_request_scoped_user_context(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id
    )


# Type aliases for the custom dependencies
DefaultUserContextDep = Annotated["RequestScopedContext", Depends(get_default_user_context)]
MessageUserContextDep = Annotated["RequestScopedContext", Depends(get_message_user_context)]
StreamUserContextDep = Annotated["RequestScopedContext", Depends(get_stream_user_context)]


async def execute_supervisor_run(supervisor: Supervisor, request_model: RequestModel):
    """Execute supervisor run with request."""
    await supervisor.run(
        request_model.query, request_model.id, stream_updates=True
    )
    return {"run_id": request_model.id, "status": "started"}


@router.post("/run_agent")
async def run_agent(
    request_model: RequestModel,
    context: StreamUserContextDep,
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
    context: DefaultUserContextDep,
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
    context: DefaultUserContextDep,
    db: RequestScopedDbDep
) -> Dict[str, Any]:
    """Get the full agent state for a run using request-scoped dependencies.
    
    UPDATED: Now uses proper request-scoped database session management.
    """
    logger.info(f"Getting agent state for run {run_id}, user {context.user_id}")
    state = await state_persistence_service.load_agent_state(run_id, db)
    validate_agent_state_exists(state, run_id)
    response = build_agent_state_response(run_id, state)
    response["request_scoped"] = True
    response["user_id"] = context.user_id
    return response

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
    context: DefaultUserContextDep,
    db: RequestScopedDbDep,
    limit: int = 10
) -> Dict[str, Any]:
    """Get all runs for a thread using request-scoped dependencies.
    
    UPDATED: Now uses proper request-scoped database session management.
    """
    logger.info(f"Getting thread runs for thread {thread_id}, user {context.user_id}")
    runs = await state_persistence_service.list_thread_runs(thread_id, db, limit)
    response = build_thread_runs_response(thread_id, runs)
    response["request_scoped"] = True
    response["user_id"] = context.user_id
    return response

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
async def process_agent_message(
    request: MessageRequest,
    context: MessageUserContextDep,
    supervisor: RequestScopedSupervisorDep,
    db: RequestScopedDbDep
) -> Dict[str, Any]:
    """Process a message through the agent system using UserExecutionContext pattern.
    
    UPDATED: Now uses request-scoped dependencies and UserExecutionContext for proper isolation.
    """
    try:
        logger.info(f"Processing message with UserExecutionContext for user {context.user_id}")
        
        # Get UserExecutionContext using session management for conversation continuity
        user_context = get_user_execution_context(
            user_id=context.user_id,
            thread_id=request.thread_id or context.thread_id,
            run_id=context.run_id
        )
        
        # Process message using supervisor with proper context
        # Note: The supervisor.run method expects individual parameters for backward compatibility
        await supervisor.run(
            user_prompt=request.message,
            thread_id=user_context.thread_id,
            user_id=user_context.user_id,
            run_id=user_context.run_id
        )
        
        return {
            "message": "Message processed successfully",
            "run_id": user_context.run_id,
            "user_id": user_context.user_id,
            "thread_id": user_context.thread_id,
            "request_scoped": True
        }
        
    except Exception as e:
        logger.error(f"Message processing failed for user {context.user_id}: {e}")
        await handle_agent_message_error(e)


@router.post("/stream")
async def stream_response(
    request_model: RequestModel,
    context: StreamUserContextDep,
    supervisor: RequestScopedSupervisorDep,
    db: RequestScopedDbDep
):
    """Stream agent response with proper SSE format using UserExecutionContext pattern.
    
    UPDATED: Now uses request-scoped dependencies and UserExecutionContext for proper isolation.
    """
    logger.info(f"Creating streaming response with UserExecutionContext for user {context.user_id}")
    
    # Get UserExecutionContext using session management for conversation continuity
    user_context = get_user_execution_context(
        user_id=context.user_id,
        thread_id=context.thread_id,
        run_id=request_model.id or context.run_id
    )
    
    # Create a streaming response that uses the request-scoped supervisor
    # For now, we'll adapt the existing streaming service to work with the new pattern
    try:
        # Start the supervisor run in the background for streaming
        await supervisor.run(
            user_prompt=request_model.query,
            thread_id=user_context.thread_id,
            user_id=user_context.user_id,
            run_id=user_context.run_id
        )
        
        # Return a streaming response
        from fastapi.responses import StreamingResponse
        
        async def generate_stream():
            # Yield initial connection confirmation
            yield f"data: {{\"type\": \"start\", \"run_id\": \"{user_context.run_id}\", \"user_id\": \"{user_context.user_id}\", \"request_scoped\": true}}\n\n"
            
            # For now, yield completion message
            # In a full implementation, this would connect to the actual streaming from supervisor
            yield f"data: {{\"type\": \"complete\", \"message\": \"Stream completed\", \"run_id\": \"{user_context.run_id}\"}}\n\n"
            
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming response failed for user {context.user_id}: {e}")
        raise


