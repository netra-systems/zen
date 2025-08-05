
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
    """_summary_

    Args:
        request (AnalysisRequest): _description_
        db (AsyncSession, optional): _description_. Defaults to Depends(get_db_session).
        llm_manager (LLMManager, optional): _description_. Defaults to Depends(LLMManager).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """    
    try:
        supervisor = NetraOptimizerAgentSupervisor(db, llm_manager)
        result = await supervisor.start_agent(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
