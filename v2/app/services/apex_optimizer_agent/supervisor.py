from typing import Any, Dict
from app.llm.llm_manager import LLMManager
from app.services.apex_optimizer_agent.agent import NetraOptimizerAgent
from app.services.deepagents.supervisor import create_supervisor_graph
from sqlalchemy.ext.asyncio import AsyncSession


from app.db.models_clickhouse import AnalysisRequest

class NetraOptimizerAgentSupervisor:
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager):
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.agent = NetraOptimizerAgent(self.db_session, self.llm_manager)
        self.graph = create_supervisor_graph(self.llm_manager)

    async def start_agent(self, request: AnalysisRequest) -> Dict[str, Any]:
        return await self.graph.ainvoke(self.agent, {"request": request})