
from typing import Any, Dict
from langchain_core.messages import HumanMessage
from app.db.models_clickhouse import AnalysisRequest
from app.llm.llm_manager import LLMManager
from app.services.apex_optimizer_agent.agent import (
    create_netra_optimizer_agent_tools,
    get_netra_optimizer_agent_definition,
)
from app.services.deepagents.graph import Team
from sqlalchemy.ext.asyncio import AsyncSession


class NetraOptimizerAgentSupervisor:
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager):
        self.db_session = db_session
        self.llm_manager = llm_manager

        agent_def = get_netra_optimizer_agent_definition()
        agent_def["tools"] = create_netra_optimizer_agent_tools(llm_manager)

        team = Team(agents=[agent_def], llm_manager=llm_manager)
        self.graph = team.create_graph()

    async def start_agent(self, request: AnalysisRequest) -> Dict[str, Any]:
        initial_state = {
            "messages": [HumanMessage(content=request.query)]
        }
        # The last message in the stream is the final state
        final_state = None
        async for event in self.graph.astream(initial_state, {"recursion_limit": 100}):
            final_state = event
        
        return final_state
