from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.llm.llm_manager import LLMManager
from app.services.apex_optimizer_agent.supervisor import NetraOptimizerAgentSupervisor
from app.db.models_clickhouse import AnalysisRequest

router = APIRouter()

def get_llm_manager_from_state(request: Request) -> LLMManager:
    return request.app.state.llm_manager

def get_agent_supervisor(request: Request, db_session: AsyncSession = Depends(get_db_session), llm_manager: LLMManager = Depends(get_llm_manager_from_state)) -> NetraOptimizerAgentSupervisor:
    return NetraOptimizerAgentSupervisor(db_session, llm_manager)

@router.post("/start_agent")
async def start_agent(
    analysis_request: AnalysisRequest,
    supervisor: NetraOptimizerAgentSupervisor = Depends(get_agent_supervisor),
):
    """
    Starts the Netra Optimizer Agent to analyze the user's request.

    Args:
        analysis_request (AnalysisRequest): The user's request to the agent.
        supervisor (NetraOptimizerAgentSupervisor, optional): The agent supervisor. Defaults to Depends(get_agent_supervisor).

    Raises:
        HTTPException: If there is an error running the agent.

    Returns:
        dict: The result of the agent's analysis.
    """
    try:
        result = await supervisor.start_agent(analysis_request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{run_id}/status")
async def get_agent_status(run_id: str, supervisor: NetraOptimizerAgentSupervisor = Depends(get_agent_supervisor)):
    state = supervisor.agent_states.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Agent run not found")
    
    response = {
        "run_id": run_id,
        "status": state.get("status", "unknown"),
        "current_step": len(state.get("completed_steps", [])),
        "total_steps": len(state.get("todo_list", [])) + len(state.get("completed_steps", [])),
        "last_step_result": state.get("events", [{}])[-1]
    }

    if response["status"] == "failed":
        response["error_message"] = state.get("error_message")

    return response

@router.get("/{run_id}/events")
async def get_agent_events(run_id: str, supervisor: NetraOptimizerAgentSupervisor = Depends(get_agent_supervisor)):
    state = supervisor.agent_states.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Agent run not found")
    
    return state.get("events", [])