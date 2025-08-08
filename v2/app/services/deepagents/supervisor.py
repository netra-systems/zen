from typing import List, Dict, Optional
from app.services.deepagents.sub_agent import SubAgent
from app.services.deepagents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.services.tool_registry import ToolRegistry
from app.services.deepagents.subagents.triage_sub_agent import TriageSubAgent
from app.services.deepagents.subagents.data_sub_agent import DataSubAgent
from app.services.deepagents.subagents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.services.deepagents.subagents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.services.deepagents.subagents.reporting_sub_agent import ReportingSubAgent
from langgraph.graph import StateGraph, END
from app.schemas import AnalysisRequest
from app.connection_manager import ConnectionManager
from app.services.deepagents.tool_dispatcher import ToolDispatcher
import logging

logger = logging.getLogger(__name__)

class Supervisor:
    def __init__(self, db_session, llm_manager: LLMManager, manager: ConnectionManager):
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.manager = manager
        self.tool_registry = ToolRegistry(db_session)
        self.sub_agents = self._initialize_sub_agents()
        self.tool_dispatcher = ToolDispatcher(self.tool_registry.get_tools(["triage", "data", "optimizations_core", "actions_to_meet_goals", "reporting"]))
        self.graph = self._define_graph()

    def _initialize_sub_agents(self) -> Dict[str, SubAgent]:
        """Initializes all the sub-agents that will be used in the graph."""
        triage_agent = TriageSubAgent(self.llm_manager, self.tool_registry.get_tools(["triage"]))
        data_agent = DataSubAgent(self.llm_manager, self.tool_registry.get_tools(["data"]))
        optimizations_core_agent = OptimizationsCoreSubAgent(self.llm_manager, self.tool_registry.get_tools(["optimizations_core"]))
        actions_to_meet_goals_agent = ActionsToMeetGoalsSubAgent(self.llm_manager, self.tool_registry.get_tools(["actions_to_meet_goals"]))
        reporting_agent = ReportingSubAgent(self.llm_manager, self.tool_registry.get_tools(["reporting"]))
        
        return {
            triage_agent.name: triage_agent,
            data_agent.name: data_agent,
            optimizations_core_agent.name: optimizations_core_agent,
            actions_to_meet_goals_agent.name: actions_to_meet_goals_agent,
            reporting_agent.name: reporting_agent,
        }

    def _define_graph(self):
        """Defines the execution graph for the agent."""
        workflow = StateGraph(DeepAgentState)

        # Add nodes for each sub-agent
        for name, agent in self.sub_agents.items():
            workflow.add_node(name, agent.ainvoke)
            
        workflow.add_node("tool_node", self.tool_dispatcher.ainvoke)

        # Define the edges
        workflow.add_conditional_edges(
            "TriageSubAgent",
            self.route,
            {agent: agent for agent in self.sub_agents.keys()} | {"__end__": END}
        )
        workflow.add_conditional_edges(
            "DataSubAgent",
            self.route,
            {agent: agent for agent in self.sub_agents.keys()} | {"__end__": END}
        )
        workflow.add_conditional_edges(
            "OptimizationsCoreSubAgent",
            self.route,
            {agent: agent for agent in self.sub_agents.keys()} | {"__end__": END}
        )
        workflow.add_conditional_edges(
            "ActionsToMeetGoalsSubAgent",
            self.route,
            {agent: agent for agent in self.sub_agents.keys()} | {"__end__": END}
        )
        workflow.add_edge("ReportingSubAgent", END)
        
        workflow.add_conditional_edges(
            "tool_node",
            lambda x: x["current_agent"],
            {agent_name: agent_name for agent_name in self.sub_agents.keys()},
        )

        workflow.set_entry_point("TriageSubAgent")
        
        return workflow.compile()

    def route(self, state: DeepAgentState) -> str:
        """Routes the request to the next appropriate sub-agent."""
        if state.get("tool_calls"):
            return "tool_node"

        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tool_node"

        # Check the content of the last message for routing instructions
        if last_message.content:
            for agent_name in self.sub_agents.keys():
                if agent_name in last_message.content:
                    return agent_name

        return "__end__"

    async def start_agent(self, analysis_request: AnalysisRequest, run_id: str, stream_updates: bool = False):
        """Starts the agent with the given analysis request."""
        logger.info(f"Starting agent for run_id: {run_id})")
        initial_state = DeepAgentState(
            messages=[HumanMessage(content=analysis_request.request.data['message'])],
            run_id=run_id,
            stream_updates=stream_updates,
            analysis_request=analysis_request,
            current_agent="TriageSubAgent"
        )
        
        final_state = None
        try:
            async for output in self.graph.astream(initial_state):
                logger.info(f"Supervisor output: {output}")
                final_state = output
                if stream_updates:
                    await self.manager.send_to_run(
                        {
                            "run_id": run_id,
                            "event": "agent_update",
                            "data": {
                                "agent": output.get('current_agent'),
                                "messages": [msg.dict() for msg in output.get('messages', [])]
                            }
                        },
                        run_id
                    )
        except Exception as e:
            logger.error(f"Error in agent execution for run_id: {run_id}", exc_info=True)
            raise
        
        logger.info(f"Supervisor final_state: {final_state}")
        return final_state

    async def get_agent_state(self, run_id: str) -> Optional[Dict]:
        """Gets the current state of the agent."""
        # This is a placeholder. In a real application, you would fetch the state from a persistent store.
        return None

    async def list_agents(self) -> List[Dict]:
        """Lists all available agents."""
        return [
            {
                "name": agent.name,
                "description": agent.description,
                "tools": [tool.name for tool in agent.tools]
            }
            for agent in self.sub_agents.values()
        ]

    async def get_agent_details(self, agent_name: str) -> Optional[Dict]:
        """Gets the details of a specific agent."""
        agent = self.sub_agents.get(agent_name)
        if not agent:
            return None
        
        return {
            "name": agent.name,
            "description": agent.description,
            "tools": [tool.name for tool in agent.tools]
        }

    async def shutdown(self):
        """Shuts down the agent supervisor."""
        logger.info("Shutting down agent supervisor...")
        # In a real application, you would add shutdown logic here
        # For now, we'll just log a message
        logger.info("Agent supervisor shut down.")