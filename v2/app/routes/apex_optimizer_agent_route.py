from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.llm.llm_manager import LLMManager
from app.services.apex_optimizer_agent.supervisor import NetraOptimizerAgentSupervisor
from app.db.models_clickhouse import AnalysisRequest
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

def get_llm_manager_from_state(request: Request) -> LLMManager:
    return request.app.state.llm_manager

@router.post("/start_agent")
async def start_agent(
    analysis_request: AnalysisRequest,
    db: AsyncSession = Depends(get_db_session),
    llm_manager: LLMManager = Depends(get_llm_manager_from_state),
):
    """
    Starts the Netra Optimizer Agent to analyze the user's request.

    Args:
        analysis_request (AnalysisRequest): The user's request to the agent.
        db (AsyncSession, optional): The database session. Defaults to Depends(get_db_session).
        llm_manager (LLMManager, optional): The LLM manager. Defaults to Depends(get_llm_manager_from_state).

    Raises:
        HTTPException: If there is an error running the agent.

    Returns:
        dict: The result of the agent's analysis.
    """
    try:
        supervisor = NetraOptimizerAgentSupervisor(db, llm_manager)
        result = await supervisor.start_agent(analysis_request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{req_id}/events")
async def stream_events(req_id: str, request: Request):
    """
    Streams events for a given request ID.

    Args:
        req_id (str): The request ID.
        request (Request): The request object.

    Returns:
        EventSourceResponse: The server-sent events.
    """
    # Placeholder for event streaming logic
    async def event_generator():
        # In a real implementation, you would fetch events for req_id
        # from a message queue or a database.
        yield {"data": f"Streaming events for {req_id}"}

    return EventSourceResponse(event_generator())