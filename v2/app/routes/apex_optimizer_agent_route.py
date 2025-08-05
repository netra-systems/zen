
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.llm.llm_manager import LLMManager
from app.services.apex_optimizer_agent.supervisor import NetraOptimizerAgentSupervisor
from app.db.models_clickhouse import AnalysisRequest

router = APIRouter()

@router.post("/start_agent")
async def start_agent(
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db_session),
    llm_manager: LLMManager = Depends(LLMManager),
):
    """
    Starts the Netra Optimizer Agent to analyze the user's request.

    Args:
        request (AnalysisRequest): The user's request to the agent.
        db (AsyncSession, optional): The database session. Defaults to Depends(get_db_session).
        llm_manager (LLMManager, optional): The LLM manager. Defaults to Depends(LLMManager).

    Raises:
        HTTPException: If there is an error running the agent.

    Returns:
        dict: The result of the agent's analysis.
    """
    try:
        supervisor = NetraOptimizerAgentSupervisor(db, llm_manager)
        result = await supervisor.start_agent(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
