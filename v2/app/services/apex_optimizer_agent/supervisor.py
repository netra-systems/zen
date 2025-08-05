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
        self.agent_states: Dict[str, Dict[str, Any]] = {}

        all_tools, _ = ToolBuilder.build_all(self.db_session, self.llm_manager)
        agent_def = self._get_agent_definition(self.llm_manager, list(all_tools.values()))
        tool_dispatcher = ToolDispatcher(tools=list(all_tools.values()))

        team = SingleAgentTeam(agent=agent_def, llm_manager=self.llm_manager, tool_dispatcher=tool_dispatcher)
        self.graph = team.create_graph()

    def _get_agent_definition(self, llm_manager: LLMManager, tools: list) -> SubAgent:
        """Returns the definition of the Netra Optimizer Agent."""
        return SubAgent(
            name="netra_optimizer_agent",
            description="An agent for optimizing LLM usage.",
            prompt=(
                "You are an expert in optimizing LLM usage. Your goal is to analyze the user's request "
                "and provide a set of recommendations for improving their LLM usage. Start by creating a todo list of the steps you will take to address the user's request. "
                "After each step, you must call the `update_state` tool to update the todo list and completed steps. "
                "When you have completed all the steps in your todo list and have a final answer, output the final answer followed by the word FINISH."
            ),
            tools=tools
        )

    async def start_agent(self, request: AnalysisRequest) -> Dict[str, Any]:
        request_id = request.request.id
        initial_state = {
            "messages": [HumanMessage(content=request.request.query)],
            "workloads": request.request.workloads,
            "todo_list": ["triage_request"],
            "completed_steps": [],
            "status": "in_progress",
            "events": []
        }
        self.agent_states[request_id] = initial_state

        # Start the agent asynchronously
        asyncio.create_task(self.run_agent(request_id))
        
        # Immediately return a response to the user
        return {"status": "agent_started", "request_id": request_id}

    async def run_agent(self, request_id: str):
        state = self.agent_states[request_id]
        async for event in self.graph.astream_events(state, {"recursion_limit": 20}):
            state["events"].append(event)
            # Update status based on event type if needed

        state["status"] = "complete"
