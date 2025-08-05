from langgraph.graph import StateGraph, END
from app.services.deepagents.state import AgentState
from app.services.deepagents.sub_agent import SubAgent
from app.llm.llm_manager import LLMManager
from app.services.deepagents.tool_dispatcher import ToolDispatcher

class SingleAgentTeam:
    def __init__(self, agent: SubAgent, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        self.agent = agent
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher

    def create_graph(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("agent", self.agent.as_runnable(self.llm_manager))
        workflow.add_node("tool_dispatcher", self.tool_dispatcher.as_runnable())

        workflow.add_edge("agent", "tool_dispatcher")

        workflow.add_conditional_edges(
            "tool_dispatcher",
            self.route_to_agent,
            {
                "continue": "agent",
                "end": END
            }
        )
        
        workflow.set_entry_point("agent")
        return workflow.compile()

    def route_to_agent(self, state: AgentState):
        if state.get("todo_list") and len(state["todo_list"]) > 0:
            return "continue"
        else:
            return "end"
