from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.schemas import RequestModel
from typing import Dict, Any, Optional, AsyncGenerator
from app.services.state_persistence_service import state_persistence_service
from app.db.postgres import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession
import json

router = APIRouter()

async def stream_agent_response(message: str) -> AsyncGenerator[str, None]:
    """Stream agent response using the actual agent service."""
    from app.services import agent_service
    async for chunk in agent_service.generate_stream(message):
        yield chunk

def get_agent_supervisor(request: Request) -> Supervisor:
    return request.app.state.agent_supervisor

@router.post("/run_agent")
async def run_agent(
    request_model: RequestModel,
    supervisor: Supervisor = Depends(get_agent_supervisor),
) -> Dict[str, Any]:
    """
    Starts the agent to analyze the user's request.
    """
    try:
        result = await supervisor.run(
            request_model.query, 
            request_model.id, 
            stream_updates=True)
        return {"run_id": request_model.id, "status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{run_id}/status")
async def get_agent_status(run_id: str, supervisor: Supervisor = Depends(get_agent_supervisor)) -> Dict[str, Any]:
    state = await supervisor.get_agent_state(run_id)
    if not state or state.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Agent run not found")
    
    return {
        "run_id": run_id,
        "status": state.get("status", "unknown"),
        "current_step": state.get("current_step", 0),
        "total_steps": state.get("total_steps", 0),
    }

@router.get("/{run_id}/state")
async def get_agent_state(
    run_id: str, 
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Get the full agent state for a run"""
    state = await state_persistence_service.load_agent_state(run_id, db)
    if not state:
        raise HTTPException(status_code=404, detail="Agent state not found")
    
    return {
        "run_id": run_id,
        "state": state.model_dump()
    }

@router.get("/thread/{thread_id}/runs")
async def get_thread_runs(
    thread_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Get all runs for a thread"""
    runs = await state_persistence_service.list_thread_runs(thread_id, db, limit)
    return {
        "thread_id": thread_id,
        "runs": runs
    }


@router.post("/stream")
async def stream_response(request_model: RequestModel):
    """Stream agent response."""
    async def generate():
        async for chunk in stream_agent_response(request_model.query):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")