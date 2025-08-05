# v2/app/services/deep_agent_v3/runner.py
from typing import Any
from app.db.models_clickhouse import AnalysisRequest
from app.services.deep_agent_v3.main import DeepAgentV3

async def run_analysis(run_id: str, request: AnalysisRequest, db_session: Any, llm_connector: any):
    """
    Initializes and runs the DeepAgentV3 analysis.
    This function is designed to be called from an async context, like a FastAPI endpoint.
    """
    agent = DeepAgentV3(run_id, request, db_session, llm_connector)
    await agent.run_full_analysis()
    return agent.state
