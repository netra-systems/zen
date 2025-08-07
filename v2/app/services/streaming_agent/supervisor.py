import asyncio
import json
import logging
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage
from app.db.models_clickhouse import AnalysisRequest
from app.llm.llm_manager import LLMManager
from app.services.deepagents.graph import SingleAgentTeam
from app.services.deepagents.sub_agent import SubAgent
from app.services.apex_optimizer_agent.tool_builder import ToolBuilder
from app.services.deepagents.tool_dispatcher import ToolDispatcher
from sqlalchemy.ext.asyncio import AsyncSession
from app.connection_manager import manager
from app.services.supply_catalog_service import SupplyCatalogService
from app.services.deepagents.state import DeepAgentState
from app.services.context import ToolContext
from app.utils.log_parser import LogParser

logger = logging.getLogger(__name__)

class StreamingAgentSupervisor:
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager, websocket_manager: manager):
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.agent_states: Dict[str, Dict[str, Any]] = {}
        self.websocket_manager = websocket_manager
        self.graph = None

    def _initialize_graph(self):
        if self.graph is None:
            state = DeepAgentState()
            supply_catalog = SupplyCatalogService()
            context = ToolContext(logs=[], db_session=self.db_session, llm_manager=self.llm_manager, cost_estimator=None, state=state, supply_catalog=supply_catalog)
            all_tools, _ = ToolBuilder.build_all(context)
            agent_def = self._get_agent_definition(self.llm_manager, list(all_tools.values()))
            tool_dispatcher = ToolDispatcher(tools=list(all_tools.values()))

            team = SingleAgentTeam(agent=agent_def, llm_manager=self.llm_manager, tool_dispatcher=tool_dispatcher)
            self.graph = team.create_graph()

    def _get_agent_definition(self, llm_manager: LLMManager, tools: list) -> SubAgent:
        """Returns the definition of the Netra Optimizer Agent."""
        return SubAgent(
            name="streaming_agent",
            description="An agent that streams updates over WebSockets.",
            prompt=(
                "You are an expert in providing real-time updates. Your goal is to process the user's request "
                "and stream updates as they happen. Start by creating a todo list of the steps you will take to address the user's request. "
                "After each step, you must call the `update_state` tool to update the todo list and completed steps. The `update_state` tool has two arguments: `completed_step` and `todo_list`. "
                "When you have completed all the steps in your todo list and have a final answer, output the final answer followed by the word FINISH."
            ),
            tools=tools
        )

    async def start_agent(self, request: AnalysisRequest, run_id: str) -> Dict[str, Any]:
        logger.info(f"start_agent called for run_id: {run_id}")
        try:
            self._initialize_graph()
            initial_state = {
                "messages": [HumanMessage(content=request.request.query)],
                "workloads": request.request.workloads,
                "todo_list": ["triage_request"],
                "completed_steps": [],
                "status": "in_progress",
                "events": []
            }
            self.agent_states[run_id] = initial_state

            # Start the agent asynchronously
            logger.info(f"Creating task for run_agent with run_id: {run_id}")
            asyncio.create_task(self.run_agent(run_id))
            logger.info(f"Task created for run_agent with run_id: {run_id}")
            
            # Immediately return a response to the user
            return {"status": "agent_started", "run_id": run_id}
        except Exception as e:
            logger.error(f"Error in start_agent for run_id: {run_id}: {e}", exc_info=True)
            return {"status": "error", "run_id": run_id, "message": str(e)}

    def _serialize_event_data(self, data: Any, _depth: int = 0) -> Any:
        if _depth > 15:
            return "Max serialization depth exceeded"
        if isinstance(data, dict):
            return {key: self._serialize_event_data(value, _depth + 1) for key, value in data.items()}
        if isinstance(data, list):
            return [self._serialize_event_data(item, _depth + 1) for item in data]
        if isinstance(data, HumanMessage):
            return {"type": "human", "content": data.content}

        if isinstance(data, (str, int, float, bool)) or data is None:
            return data

        stringified_data = str(data)
        # Attempt to parse the stringified data
        parsed_data = LogParser.parse_log_message(stringified_data)

        # If parsing as a tool call is successful, return the structured data
        if parsed_data and parsed_data.get("type") == "tool_call":
            return parsed_data

        # Otherwise, return the original stringified data
        return stringified_data

    async def run_agent(self, run_id: str):
        logger.info(f"Starting agent run for run_id: {run_id}")
        try:
            state = self.agent_states[run_id]
            async for event in self.graph.astream_events(state, {"recursion_limit": 20}):
                state["events"].append(event)
                # Send updates over WebSocket
                serializable_data = self._serialize_event_data(event["data"])
                await self.websocket_manager.send_to_run(json.dumps({"event": event["event"], "data": serializable_data, "run_id": run_id}), run_id)

            state["status"] = "complete"
            await self.websocket_manager.send_to_run(json.dumps({"event": "run_complete", "data": {"status": "complete"}, "run_id": run_id}), run_id)
            logger.info(f"Agent run for run_id: {run_id} completed successfully.")
        except Exception as e:
            logger.error(f"Error during agent run for run_id: {run_id}: {e}", exc_info=True)
            # Optionally, send an error message to the client
            try:
                await self.websocket_manager.send_to_run(json.dumps({"event": "error", "data": {"message": str(e)}, "run_id": run_id}), run_id)
            except Exception as ws_e:
                logger.error(f"Failed to send error message to client for run_id: {run_id}: {ws_e}")


    async def get_agent_state(self, run_id: str) -> Dict[str, Any]:
        return self.agent_states.get(run_id, {"status": "not_found"})