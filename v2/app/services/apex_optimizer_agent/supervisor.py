import asyncio
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage
from app.db.models_clickhouse import AnalysisRequest
from app.llm.llm_manager import LLMManager
from app.services.deepagents.graph import SingleAgentTeam
from app.services.deepagents.sub_agent import SubAgent
from app.services.apex_optimizer_agent.tool_builder import ToolBuilder
from app.services.deepagents.tool_dispatcher import ToolDispatcher
from sqlalchemy.ext.asyncio import AsyncSession

class NetraOptimizerAgentSupervisor:
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager):
        self.db_session = db_session
        self.llm_manager = llm_manager

    def _get_agent_definition(self, llm_manager: LLMManager) -> SubAgent:
        """Returns the definition of the Netra Optimizer Agent."""
        all_tools, _ = ToolBuilder.build_all(self.db_session, llm_manager)
        
        return SubAgent(
            name="netra_optimizer_agent",
            description="An agent for optimizing LLM usage.",
            prompt=(
                "You are an expert in optimizing LLM usage. Your goal is to analyze the user's request "
                "and provide a set of recommendations for improving their LLM usage. Start by creating a todo list of the steps you will take to address the user's request. "
                "When you have completed all the steps in your todo list and have a final answer, output the final answer followed by the word FINISH."
            ),
            tools=list(all_tools.values())
        )

    async def start_agent(self, request: AnalysisRequest) -> Dict[str, Any]:
        agent_def = self._get_agent_definition(self.llm_manager)
        all_tools, _ = ToolBuilder.build_all(self.db_session, self.llm_manager)
        tool_dispatcher = ToolDispatcher(tools=list(all_tools.values()))

        team = SingleAgentTeam(agent=agent_def, llm_manager=self.llm_manager, tool_dispatcher=tool_dispatcher)
        self.graph = team.create_graph()
        initial_state = {
            "messages": [HumanMessage(content=request.request.query)],
            "workloads": request.request.workloads,
            "todo_list": ["triage_request"],
            "completed_steps": []
        }
        # Start the agent asynchronously
        asyncio.create_task(self.graph.ainvoke(initial_state, {"recursion_limit": 100}))
        
        # Immediately return a response to the user
        return {"status": "agent_started", "request_id": request.request.id}
