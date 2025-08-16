from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.schemas import RequestModel
from typing import Dict, Any, Optional, AsyncGenerator
from app.services.state_persistence_service import state_persistence_service
from app.services.agent_service import get_agent_service, AgentService
from app.dependencies import get_llm_manager, DbDep
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import json

router = APIRouter()

class MessageRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

def _format_chunk_output(chunk) -> str:
    """Format chunk for streaming output."""
    if isinstance(chunk, dict):
        return json.dumps(chunk)
    elif isinstance(chunk, str):
        return chunk
    return json.dumps({"type": "data", "content": str(chunk)})

async def _stream_with_fallback_service(message: str, thread_id: Optional[str]) -> AsyncGenerator[str, None]:
    """Stream using fallback service for backward compatibility."""
    from app.services.agent_service import generate_stream
    async for chunk in generate_stream(message, thread_id):
        yield _format_chunk_output(chunk)
    yield json.dumps({"type": "complete", "status": "finished"})

async def _stream_with_agent_service(
    agent_service: AgentService, message: str, thread_id: Optional[str]
) -> AsyncGenerator[str, None]:
    """Stream using provided agent service."""
    async for chunk in agent_service.generate_stream(message, thread_id):
        yield _format_chunk_output(chunk)
    yield json.dumps({"type": "complete", "status": "finished"})

async def _get_stream_generator(
    agent_service: Optional[AgentService], message: str, thread_id: Optional[str]
):
    """Get appropriate stream generator."""
    if not agent_service:
        return _stream_with_fallback_service(message, thread_id)
    return _stream_with_agent_service(agent_service, message, thread_id)

async def _delegate_streaming(
    agent_service: Optional[AgentService], message: str, thread_id: Optional[str]
) -> AsyncGenerator[str, None]:
    """Delegate streaming to appropriate service."""
    stream_gen = await _get_stream_generator(agent_service, message, thread_id)
    async for chunk in stream_gen:
        yield chunk

async def stream_agent_response(
    message: str,
    thread_id: Optional[str] = None,
    agent_service: Optional[AgentService] = None
) -> AsyncGenerator[str, None]:
    """Stream agent response using the actual agent service."""
    async for chunk in _delegate_streaming(agent_service, message, thread_id):
        yield chunk

def get_agent_supervisor(request: Request) -> Supervisor:
    return request.app.state.agent_supervisor

async def _execute_supervisor_run(supervisor: Supervisor, request_model: RequestModel):
    """Execute supervisor run with request."""
    await supervisor.run(
        request_model.query, request_model.id, stream_updates=True
    )
    return {"run_id": request_model.id, "status": "started"}

def _handle_run_agent_error(e: Exception):
    """Handle run agent execution errors."""
    raise HTTPException(status_code=500, detail=str(e))

@router.post("/run_agent")
async def run_agent(request_model: RequestModel, supervisor: Supervisor = Depends(get_agent_supervisor)) -> Dict[str, Any]:
    """Starts the agent to analyze the user's request."""
    try:
        return await _execute_supervisor_run(supervisor, request_model)
    except Exception as e:
        _handle_run_agent_error(e)

def _validate_agent_state(state, run_id: str) -> None:
    """Validate agent state exists and is valid."""
    if not state or state.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Agent run not found")

def _build_agent_status_response(run_id: str, state: Dict) -> Dict[str, Any]:
    """Build agent status response."""
    return {
        "run_id": run_id,
        "status": state.get("status", "unknown"),
        "current_step": state.get("current_step", 0),
        "total_steps": state.get("total_steps", 0),
    }

@router.get("/{run_id}/status")
async def get_agent_status(run_id: str, supervisor: Supervisor = Depends(get_agent_supervisor)) -> Dict[str, Any]:
    state = await supervisor.get_agent_state(run_id)
    _validate_agent_state(state, run_id)
    return _build_agent_status_response(run_id, state)

def _validate_agent_state_exists(state, run_id: str) -> None:
    """Validate agent state exists."""
    if not state:
        raise HTTPException(status_code=404, detail="Agent state not found")

def _build_agent_state_response(run_id: str, state) -> Dict[str, Any]:
    """Build agent state response."""
    return {
        "run_id": run_id,
        "state": state.model_dump()
    }

@router.get("/{run_id}/state")
async def get_agent_state(
    run_id: str, 
    db: DbDep
) -> Dict[str, Any]:
    """Get the full agent state for a run"""
    state = await state_persistence_service.load_agent_state(run_id, db)
    _validate_agent_state_exists(state, run_id)
    return _build_agent_state_response(run_id, state)

def _build_thread_runs_response(thread_id: str, runs) -> Dict[str, Any]:
    """Build thread runs response."""
    return {
        "thread_id": thread_id,
        "runs": runs
    }

@router.get("/thread/{thread_id}/runs")
async def get_thread_runs(
    thread_id: str,
    db: DbDep,
    limit: int = 10
) -> Dict[str, Any]:
    """Get all runs for a thread"""
    runs = await state_persistence_service.list_thread_runs(thread_id, db, limit)
    return _build_thread_runs_response(thread_id, runs)


async def _process_message_with_agent_service(
    agent_service: AgentService, message: str, thread_id: Optional[str]
) -> Dict[str, Any]:
    """Process message using agent service."""
    return await agent_service.process_message(message, thread_id)

async def _handle_agent_message_error(e: Exception):
    """Handle agent message processing errors."""
    raise HTTPException(status_code=500, detail=str(e))

async def _execute_message_processing(
    agent_service: AgentService, request: MessageRequest
) -> Dict[str, Any]:
    """Execute message processing with service."""
    return await _process_message_with_agent_service(
        agent_service, request.message, request.thread_id
    )

@router.post("/message")
async def process_agent_message(request: MessageRequest, agent_service: AgentService = Depends(get_agent_service)) -> Dict[str, Any]:
    """Process a message through the agent system."""
    try:
        return await _execute_message_processing(agent_service, request)
    except Exception as e:
        await _handle_agent_message_error(e)

def _get_agent_service_for_streaming(db_session: DbDep, llm_manager: LLMManager) -> AgentService:
    """Get agent service for streaming."""
    return get_agent_service(db_session, llm_manager)

async def _generate_sse_stream(
    request_model: RequestModel, agent_service: AgentService
) -> AsyncGenerator[str, None]:
    """Generate SSE formatted stream."""
    async for chunk in stream_agent_response(
        request_model.query, request_model.id, agent_service
    ):
        yield f"data: {chunk}\n\n"

def _build_streaming_headers() -> Dict[str, str]:
    """Build headers for streaming response."""
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"  # Disable nginx buffering
    }

def _get_sse_generator(request_model: RequestModel, agent_service: AgentService):
    """Get SSE stream generator."""
    return _generate_sse_stream(request_model, agent_service)

def _create_streaming_response(
    request_model: RequestModel, agent_service: AgentService
) -> StreamingResponse:
    """Create streaming response with headers."""
    return StreamingResponse(
        _get_sse_generator(request_model, agent_service),
        media_type="text/event-stream",
        headers=_build_streaming_headers()
    )

@router.post("/stream")
async def stream_response(
    request_model: RequestModel,
    db_session: DbDep,
    llm_manager: LLMManager = Depends(get_llm_manager)
):
    """Stream agent response with proper SSE format."""
    agent_service = _get_agent_service_for_streaming(db_session, llm_manager)
    return _create_streaming_response(request_model, agent_service)