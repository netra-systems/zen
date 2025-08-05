
from typing import Any, Dict
from app.db.models_clickhouse import AnalysisRequest
from app.llm.llm_manager import LLMManager
from app.services.apex_optimizer_agent.state import AgentState
from app.services.apex_optimizer_agent.triage import Triage
from app.services.deepagents.sub_agent import SubAgent
from sqlalchemy.ext.asyncio import AsyncSession


class NetraOptimizerAgent(SubAgent):
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager):
        super().__init__(
            name="netra_optimizer_agent",
            description="An agent for optimizing LLM usage.",
            prompt="You are an expert in optimizing LLM usage. Your goal is to analyze the user's request and provide a set of recommendations for improving their LLM usage.",
        )
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.triage = Triage(self.llm_manager)

    async def run(self, request: AnalysisRequest) -> Dict[str, Any]:
        triage_result = await self.triage.triage_request(request.query)
        return triage_result
