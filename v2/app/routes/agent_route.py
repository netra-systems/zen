from fastapi import APIRouter, Depends, HTTPException, Request
from app.agents.supervisor import Supervisor
from app.schemas import AnalysisRequest

router = APIRouter()

def get_agent_supervisor(request: Request) -> Supervisor:
    return request.app.state.agent_supervisor

@router.post("/run_agent")
async def run_agent(
    analysis_request: AnalysisRequest,
    supervisor: Supervisor = Depends(get_agent_supervisor),
):
    """
    Starts the agent to analyze the user's request.
    """
    try:
        result = await supervisor.run(
            analysis_request.model_dump(), 
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
