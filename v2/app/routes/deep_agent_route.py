from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
import uuid

from app.services.deep_agent_v3.main import DeepAgentV3
from app.db.models_clickhouse import AnalysisRequest
from app.dependencies import get_llm_manager, get_db_session
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

AGENT_INSTANCES: Dict[str, DeepAgentV3] = {}

class StartRequest(BaseModel):
    user_id: str
    query: str

LLMManagerDep = Depends(get_llm_manager)
DBSessionDep = Depends(get_db_session)

async def run_agent_in_background(run_id: str, request: AnalysisRequest, db_session: AsyncSession, llm_manager: LLMManager):
    agent = DeepAgentV3(run_id, request, db_session, llm_manager)
    AGENT_INSTANCES[run_id] = agent
    await agent.start_agent()

@router.post("/agent/start", status_code=202)
async def start_agent_run(request: StartRequest, background_tasks: BackgroundTasks, db_session: AsyncSession = DBSessionDep, llm_manager: LLMManager = LLMManagerDep) -> Dict[str, str]:
    """
    Starts a new Deep Agent run in the background.
    """
    run_id = str(uuid.uuid4())
    analysis_request = AnalysisRequest(user_id=request.user_id, query=request.query, workloads=[{"run_id": run_id}])
    
    background_tasks.add_task(run_agent_in_background, run_id, analysis_request, db_session, llm_manager)

    return {"run_id": run_id, "message": "Agent run started in the background."}

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
        "status": agent.status,
        "current_step": agent.state.current_step
    }

@router.get("/agent/{run_id}/report")
async def get_agent_report(run_id: str, db_session: AsyncSession = DBSessionDep) -> Dict[str, Any]:
    """
    Retrieve the final report of an agent run.
    """
    from app.db.models_postgres import DeepAgentRunReport
    from sqlmodel import select

    report_result = await db_session.execute(select(DeepAgentRunReport).where(DeepAgentRunReport.run_id == run_id))
    report = report_result.scalars().first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found for this agent run.")

    return {
        "run_id": run_id,
        "report": report.report
    }
