import asyncio
import json
import logging
from typing import Any, Dict, List, Literal

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage, AIMessageChunk
from langchain_core.prompt_values import ChatPromptValue
from langgraph.graph import END, StateGraph

from app.db.models_clickhouse import AnalysisRequest
from app.llm.llm_manager import LLMManager
from app.services.deepagents.sub_agent import SubAgent
from app.services.apex_optimizer_agent.tool_builder import ToolBuilder
from app.services.deepagents.tool_dispatcher import ToolDispatcher
from sqlalchemy.ext.asyncio import AsyncSession
from app.connection_manager import manager
from app.services.supply_catalog_service import SupplyCatalogService
from app.services.deepagents.state import DeepAgentState
from app.schemas import RunCompleteMessage, ErrorMessage, StreamEventMessage, ErrorData
from app.services.context import ToolContext

# Sub-agent imports
from app.services.deepagents.subagents.triage_sub_agent import TriageSubAgent
from app.services.deepagents.subagents.data_sub_agent import DataSubAgent
from app.services.deepagents.subagents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.services.deepagents.subagents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.services.deepagents.subagents.reporting_sub_agent import ReportingSubAgent

logger = logging.getLogger(__name__)

class OverallSupervisor:
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager, websocket_manager: manager):
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.agent_states: Dict[str, Dict[str, Any]] = {}
        self.websocket_manager = websocket_manager
        self.tasks: Dict[str, asyncio.Task] = {}
        self.sub_agents: Dict[str, SubAgent] = {}
        self.tool_dispatcher = None
        self._initialize_sub_agents_and_tools()
        self.graph = self._create_graph()

    def _initialize_sub_agents_and_tools(self):
        state = DeepAgentState()
        supply_catalog = SupplyCatalogService()
        context = ToolContext(logs=[], db_session=self.db_session, llm_manager=self.llm_manager, cost_estimator=None, state=state, supply_catalog=supply_catalog)
        all_tools, _ = ToolBuilder.build_all(context)
        self.tool_dispatcher = ToolDispatcher(tools=list(all_tools.values()))

        # Initialize sub-agents
        self.sub_agents = {
            'triage': TriageSubAgent(llm_manager=self.llm_manager, tools=list(all_tools.values())),
            'data': DataSubAgent(llm_manager=self.llm_manager, tools=list(all_tools.values())),
            'optimizations_core': OptimizationsCoreSubAgent(llm_manager=self.llm_manager, tools=list(all_tools.values())),
            'actions_to_meet_goals': ActionsToMeetGoalsSubAgent(llm_manager=self.llm_manager, tools=list(all_tools.values())),
            'reporting': ReportingSubAgent(llm_manager=self.llm_manager, tools=list(all_tools.values()))
        }

    def _create_graph(self):
        # Build the graph
        builder = StateGraph(DeepAgentState)

        # Add nodes for each sub-agent
        for name, agent in self.sub_agents.items():
            builder.add_node(name, agent.as_runnable())
        builder.add_node("tool_dispatcher", self.tool_dispatcher.as_runnable())

        # Define the edges
        builder.set_entry_point("triage")

        builder.add_conditional_edges(
            "triage",
            lambda state: "tool_dispatcher" if state.get("tool_calls") else "data"
        )
        builder.add_conditional_edges(
            "data",
            lambda state: "tool_dispatcher" if state.get("tool_calls") else "optimizations_core"
        )
        builder.add_conditional_edges(
            "optimizations_core",
            lambda state: "tool_dispatcher" if state.get("tool_calls") else "actions_to_meet_goals"
        )
        builder.add_conditional_edges(
            "actions_to_meet_goals",
            lambda state: "tool_dispatcher" if state.get("tool_calls") else "reporting"
        )
        builder.add_conditional_edges(
            "reporting",
            lambda state: "tool_dispatcher" if state.get("tool_calls") else END
        )

        sub_agent_names = list(self.sub_agents.keys())
        tool_dispatcher_edges = {name: name for name in sub_agent_names}
        builder.add_conditional_edges(
            "tool_dispatcher",
            lambda state: state.get("current_agent"),
            tool_dispatcher_edges
        )

        return builder.compile()

    def _initialize_sub_agents_and_tools(self):
        state = DeepAgentState()
        supply_catalog = SupplyCatalogService()
        context = ToolContext(logs=[], db_session=self.db_session, llm_manager=self.llm_manager, cost_estimator=None, state=state, supply_catalog=supply_catalog)
        all_tools, _ = ToolBuilder.build_all(context)
        self.tool_dispatcher = ToolDispatcher(tools=list(all_tools.values()))

        self.sub_agents['triage'] = TriageSubAgent(llm_manager=self.llm_manager, tools=list(all_tools.values()))
        self.sub_agents['data'] = DataSubAgent(llm_manager=self.llm_manager, tools=list(all_tools.values()))
        self.sub_agents['optimizations_core'] = OptimizationsCoreSubAgent(llm_manager=self.llm_manager, tools=list(all_tools.values()))
        self.sub_agents['actions_to_meet_goals'] = ActionsToMeetGoalsSubAgent(llm_manager=self.llm_manager, tools=list(all_tools.values()))
        self.sub_agents['reporting'] = ReportingSubAgent(llm_manager=self.llm_manager, tools=list(all_tools.values()))

    async def start_agent(self, request: AnalysisRequest, run_id: str, stream_updates: bool = False) -> Dict[str, Any]:
        logger.info(f"start_agent called for run_id: {run_id}")
        try:
            initial_state = {
                "messages": [HumanMessage(content=request.request.query)],
                "workloads": request.request.workloads,
                "run_id": run_id,
                "stream_updates": stream_updates,
                "next_node": "triage"
            }
            self.agent_states[run_id] = initial_state

            task = asyncio.create_task(self.run_agent(run_id))
            self.tasks[run_id] = task
            
            return {"status": "agent_started", "run_id": run_id}
        except Exception as e:
            logger.error(f"Error in start_agent for run_id: {run_id}: {e}", exc_info=True)
            return {"status": "error", "run_id": run_id, "message": str(e)}

    def _serialize_event_data(self, data: Any, _depth: int = 0) -> Any:
        if _depth > 15:
            return "Max serialization depth exceeded"
        
        if data is None:
            return None

        if isinstance(data, dict):
            return {key: self._serialize_event_data(value, _depth + 1) for key, value in data.items()}
        if isinstance(data, list):
            if len(data) == 1 and isinstance(data[0], list):
                return [self._serialize_event_data(item, _depth + 1) for item in data[0]]
            return [self._serialize_event_data(item, _depth + 1) for item in data]

        if isinstance(data, (BaseMessage, AIMessageChunk)):
            serialized_message = {"type": data.type, "content": str(data.content)}
            
            if isinstance(data, (AIMessage, AIMessageChunk)):
                if hasattr(data, 'tool_calls') and data.tool_calls:
                    serialized_message["tool_calls"] = self._serialize_event_data(data.tool_calls, _depth + 1)
                if hasattr(data, 'additional_kwargs') and data.additional_kwargs:
                    serialized_message["additional_kwargs"] = self._serialize_event_data(data.additional_kwargs, _depth + 1)
                if hasattr(data, 'response_metadata') and data.response_metadata:
                    serialized_message["response_metadata"] = self._serialize_event_data(data.response_metadata, _depth + 1)
                if hasattr(data, 'id') and data.id:
                    serialized_message["id"] = data.id

            if isinstance(data, ToolMessage) and hasattr(data, 'tool_call_id'):
                serialized_message["tool_call_id"] = data.tool_call_id
                
            return serialized_message
        
        if isinstance(data, ChatPromptValue):
            return {"type": "ChatPromptValue", "content": data.to_string()}

        if isinstance(data, (str, int, float, bool)):
            return data

        return {"type": "unknown", "content": f"Unserializable object of type: {type(data).__name__}"}

    async def run_agent(self, run_id: str):
        logger.info(f"Starting agent run for run_id: {run_id}")
        try:
            state = self.agent_states[run_id]
            stream_updates = state.get("stream_updates", False)

            async for event in self.graph.astream_events(state, {"recursion_limit": 50}):
                if stream_updates:
                    serializable_data = self._serialize_event_data(event["data"])
                    await self.websocket_manager.send_to_run(
                        StreamEventMessage(
                            event_type=event["event"],
                            data=serializable_data,
                            run_id=run_id
                        )
                    )

            state["status"] = "complete"
            if stream_updates:
                await self.websocket_manager.send_to_run(
                    RunCompleteMessage(
                        data={"status": "complete"},
                        run_id=run_id
                    )
                )
            logger.info(f"Agent run for run_id: {run_id} completed successfully.")
        except Exception as e:
            logger.error(f"Error during agent run for run_id: {run_id}: {e}", exc_info=True)
            if stream_updates:
                try:
                    error_payload = ErrorMessage(
                        data=ErrorData(
                            type=type(e).__name__,
                            message=str(e.args[0]) if e.args else str(e)
                        ),
                        run_id=run_id
                    )
                    await self.websocket_manager.send_to_run(error_payload)
                except Exception as ws_e:
                    logger.error(f"Failed to send error message to client for run_id: {run_id}: {ws_e}")

    async def get_agent_state(self, run_id: str) -> Dict[str, Any]:
        return self.agent_states.get(run_id, {"status": "not_found"})

    async def shutdown(self):
        for task in self.tasks.values():
            task.cancel()
        
        # Create a gathering of all tasks
        tasks = list(self.tasks.values())
        if not tasks:
            return

        # Wait for all tasks to complete, with a timeout
        # The timeout is a safeguard against tasks that might not respect cancellation
        try:
            await asyncio.wait(tasks, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Timeout expired while waiting for agent tasks to cancel.")

        # Additional check to see which tasks are still running
        for task in tasks:
            if not task.done():
                logger.warning(f"Task {task.get_name()} did not cancel in time.")

        self.tasks.clear()