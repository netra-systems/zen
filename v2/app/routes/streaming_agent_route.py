from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.llm.llm_manager import LLMManager
from app.services.streaming_agent.supervisor import StreamingAgentSupervisor
from app.db.models_clickhouse import AnalysisRequest

router = APIRouter()

def get_llm_manager_from_state(request: Request) -> LLMManager:
    return request.app.state.llm_manager

def get_agent_supervisor(request: Request) -> StreamingAgentSupervisor:
    return request.app.state.streaming_agent_supervisor

@router.post("/start_agent/{client_id}")
async def start_agent(
    analysis_request: AnalysisRequest,
    client_id: str,
    supervisor: StreamingAgentSupervisor = Depends(get_agent_supervisor),
):
    """
    Starts the Streaming Agent to analyze the user's request.

    Args:
        analysis_request (AnalysisRequest): The user's request to the agent.
        client_id (str): The client ID to send WebSocket messages to.
        supervisor (StreamingAgentSupervisor, optional): The agent supervisor. Defaults to Depends(get_agent_supervisor).

    Raises:
        HTTPException: If there is an error running the agent.

    Returns:
        dict: The result of the agent's analysis.
    """
    try:
        result = await supervisor.start_agent(analysis_request, client_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
