from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any

from app.services.deep_agent_v3.main import DeepAgentV3
from app.db.models_clickhouse import AnalysisRequest
from app.dependencies import get_async_db as get_db_session, get_llm_connector

router = APIRouter()

# A simple in-memory store for active agent instances
# In a production environment, this would be replaced with a more robust solution like Redis
AGENT_INSTANCES: Dict[str, DeepAgentV3] = {}

class ConfirmationRequest(BaseModel):
    confirmation: bool

from app.services.security_service import security_service
from app.config import settings
from app.services.deep_agent_v3.dev_utils import get_or_create_dev_user

@router.post("/agent/create", status_code=202)
async def create_agent_run(request: AnalysisRequest, background_tasks: BackgroundTasks, db_session: Any = Depends(get_db_session), llm_connector: Any = Depends(get_llm_connector)) -> Dict[str, str]:
    """
    Creates and starts a new Deep Agent analysis run in the background.
    """
    if not request.workloads:
        raise HTTPException(status_code=400, detail="No workloads provided in the request.")

    user_id = request.user_id
    if settings.app_env == "development" and not user_id:
        dev_user = get_or_create_dev_user(db_session)
        user_id = dev_user.id

    # Pre-flight check for credentials
    if not security_service.get_user_credentials(user_id, db_session):
        raise HTTPException(status_code=400, detail="User credentials are not configured. Please set them up before running an analysis.")

    # Assuming a single workload for now, as per the new structure
    run_id = request.workloads[0].get('run_id')
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id not found in workload.")
    agent = DeepAgentV3(run_id=run_id, request=request, db_session=db_session, llm_connector=llm_connector)
    AGENT_INSTANCES[run_id] = agent

    # Run the full analysis in the background to not block the API
    background_tasks.add_task(agent.run_full_analysis)

    return {"run_id": run_id, "message": "Agent run created and started in the background."}

@router.get("/agent/{run_id}/step")
async def get_agent_step(run_id: str) -> Dict[str, Any]:
    """
    Retrieves the current state and step of an active agent run.
    """
    agent = AGENT_INSTANCES.get(run_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent run not found.")

    if agent.is_complete():
        return {
            "run_id": run_id,
            "status": "complete",
            "current_step": len(agent.steps),
            "total_steps": len(agent.steps),
            "final_report": agent.state.final_report
        }

    return {
        "run_id": run_id,
        "status": agent.status,
        "current_step": agent.current_step_index,
        "total_steps": len(agent.steps),
        "last_step_result": agent.state.get('messages', [])[-1] if agent.state.get('messages') else None
    }

@router.post("/agent/{run_id}/next")
async def trigger_agent_next_step(run_id: str, request: ConfirmationRequest) -> Dict[str, Any]:
    """
    Triggers the agent to execute the next step in its analysis pipeline.
    
    NOTE: This endpoint is designed for a manual, step-by-step progression.
    The create endpoint already runs the full analysis in the background.
    This can be used for debugging or a more controlled execution flow.
    """
    agent = AGENT_INSTANCES.get(run_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent run not found.")

    if agent.is_complete():
        return {"status": "complete", "message": "Analysis is already complete."}

    result = await agent.run_next_step(request.confirmation)
    return result

@router.get("/agent/{run_id}/history")
async def get_agent_history(run_id: str) -> Dict[str, Any]:
    """
    Retrieves the full execution history of an agent run.
    
    NOTE: This currently returns the final state. A more detailed history
    would require storing each state transition.
    """
    agent = AGENT_INSTANCES.get(run_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent run not found.")

    return {
        "run_id": run_id,
        "is_complete": agent.is_complete(),
        "history": agent.state
    }