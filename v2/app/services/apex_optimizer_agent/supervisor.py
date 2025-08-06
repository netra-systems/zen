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
from app.services.apex_optimizer_agent.models import ToolInvocation, ToolStatus

from app.services.apex_optimizer_agent.tools.context import ToolContext

class NetraOptimizerAgentSupervisor:
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager):
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.agent_states: Dict[str, Dict[str, Any]] = {}

        context = ToolContext(logs=[], db_session=self.db_session, llm_manager=self.llm_manager, cost_estimator=None)
        all_tools, _ = ToolBuilder.build_all(context)
        agent_def = self._get_agent_definition(self.llm_manager, list(all_tools.values()))
        tool_dispatcher = ToolDispatcher(tools=list(all_tools.values()))

        team = SingleAgentTeam(agent=agent_def, llm_manager=self.llm_manager, tool_dispatcher=tool_dispatcher)
        self.graph = team.create_graph()

    def _get_agent_definition(self, llm_manager: LLMManager, tools: list) -> SubAgent:
        """Returns the definition of the Netra Optimizer Agent."""
        description = (
            "An agent for optimizing LLM usage. Your goal is to analyze the user's request "
            "and provide a set of recommendations for improving their LLM usage. Start by creating a todo list "
            "of the steps you will take to address the user's request. After each step, you must call the "
            "`update_state` tool to update the todo list and completed steps. When you have completed all the "
            "steps in your todo list and have a final answer, output the final answer followed by the word FINISH."
        )
        return SubAgent(
            name="netra_optimizer_agent",
            description=description,
            prompt="You are a helpful assistant that analyzes LLM usage and provides optimization recommendations.",
            tools=tools
        )

    async def start_agent(self, request: AnalysisRequest) -> Dict[str, Any]:
        run_id = request.request.id
        initial_state = {
            "messages": [HumanMessage(content=request.request.query)],
            "workloads": request.request.workloads,
            "todo_list": ["triage_request"],
            "completed_steps": [],
            "status": "in_progress",
            "events": []
        }
        self.agent_states[run_id] = initial_state

        # Start the agent asynchronously without blocking the response
        asyncio.create_task(self.run_agent(run_id))
        
        # Immediately return a response to the user
        return {"status": "agent_started", "run_id": run_id}

    async def run_agent(self, run_id: str):
        state = self.agent_states.get(run_id)
        if not state:
            print(f"Error: Agent state not found for run_id: {run_id}")
            return

        try:
            async for event in self.graph.astream_events(state, {"recursion_limit": 20}):
                state["events"].append(event)
                if event["event"] == "on_tool_end":
                    tool_invocation = event["data"].get("output")
                    if isinstance(tool_invocation, ToolInvocation):
                        if tool_invocation.tool_result.status == ToolStatus.ERROR:
                            state["status"] = "failed"
                            state["error_message"] = tool_invocation.tool_result.message
                            # Stop processing on critical error
                            return
                        elif tool_invocation.tool_result.status == ToolStatus.PARTIAL_SUCCESS:
                            # Log partial success and continue
                            print(f"Tool {tool_invocation.tool_result.tool_input.tool_name} partially succeeded: {tool_invocation.tool_result.message}")
            
            # If the loop completes without critical errors, mark as complete
            state["status"] = "complete"

        except Exception as e:
            # Catch any other exceptions during the agent run
            state["status"] = "failed"
            state["error_message"] = f"An unexpected error occurred during agent execution: {str(e)}"
            print(f"Error in run_agent for run_id {run_id}: {e}")
