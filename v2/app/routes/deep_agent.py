
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any

from app.services.deep_agent.graph import create_agent_graph
from app.services.deep_agent.supervisor import create_supervisor_graph
from app.services.deep_agent.state import DeepAgentState
from app.db.models_clickhouse import AnalysisRequest
from app.dependencies import get_llm_manager
from app.llm.llm_manager import LLMManager

router = APIRouter()

AGENT_INSTANCES: Dict[str, Any] = {}

class ConfirmationRequest(BaseModel):
    confirmation: bool

LLMManagerDep = Depends(get_llm_manager)

async def run_agent_in_background(run_id: str, request: AnalysisRequest, llm_manager: LLMManager):
    agent_graph = create_agent_graph(llm_manager=llm_manager, instructions="", tools=[])
    supervisor_graph = create_supervisor_graph(llm_manager, agent_graph)
    
    initial_state = DeepAgentState(messages=[("user", request.query)])
    
    AGENT_INSTANCES[run_id] = {"status": "running", "state": initial_state}
    
    async for event in supervisor_graph.astream(initial_state):
        AGENT_INSTANCES[run_id]["state"] = event
        

@router.post("/agent/create", status_code=202)
async def create_agent_run(request: AnalysisRequest, background_tasks: BackgroundTasks, llm_manager: LLMManager = LLMManagerDep) -> Dict[str, str]:
    """
    Creates and starts a new Deep Agent analysis run in the background.
    """
    run_id = request.workloads[0].get('run_id')
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id not found in workload.")

    background_tasks.add_task(run_agent_in_background, run_id, request, llm_manager)

    return {"run_id": run_id, "message": "Agent run created and started in the background."}

@router.get("/agent/{run_id}/history")
async def get_agent_history(run_id: str) -> Dict[str, Any]:
    """
    Retrieves the full execution history of an agent run.
    """
    agent = AGENT_INSTANCES.get(run_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent run not found.")

    return {
        "run_id": run_id,
        "status": agent["status"],
        "history": agent["state"]
    }

@router.get("/agent/{run_id}/status")
async def get_agent_status(run_id: str) -> Dict[str, Any]:
    """
    Retrieves the current status of an agent run.
    """
    agent = AGENT_INSTANCES.get(run_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent run not found.")

    return {
        "run_id": run_id,
        "status": agent["status"],
    }
