from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.llm.llm_manager import LLMManager
from app.services.deepagents.supervisor import Supervisor
from app.schemas import AnalysisRequest
from app.ws_manager import manager

router = APIRouter()

def get_llm_manager_from_state(request: Request) -> LLMManager:
    return request.app.state.llm_manager

def get_agent_supervisor(request: Request, db_session: AsyncSession = Depends(get_db_session), llm_manager: LLMManager = Depends(get_llm_manager_from_state)) -> Supervisor:
    # This is a simplified way to get the supervisor. In a real app, you might have a more robust way to manage this.
    return Supervisor(db_session, llm_manager, manager)

@router.post("/start_agent")
async def start_agent(
    analysis_request: AnalysisRequest,
    supervisor: Supervisor = Depends(get_agent_supervisor),
):
    """
    Starts the agent to analyze the user's request.
    """
    try:
        result = await supervisor.start_agent(
            analysis_request, 
            analysis_request.request.id, 
            stream_updates=True)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/{run_id}/status")
async def get_agent_status(run_id: str, supervisor: Supervisor = Depends(get_agent_supervisor)):
    state = await supervisor.get_agent_state(run_id)
    if not state or state.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Agent run not found")
    
    return {
        "run_id": run_id,
        "status": state.get("status", "unknown"),
        "current_step": state.get("current_step", 0),
        "total_steps": state.get("total_steps", 0),
    }