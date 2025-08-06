from langgraph.graph import StateGraph, END
from app.services.deepagents.state import DeepAgentState
from app.services.deepagents.sub_agent import SubAgent
from app.llm.llm_manager import LLMManager
from app.services.deepagents.tool_dispatcher import ToolDispatcher
from app.logging_config_custom.logger import app_logger
import json
from langchain_core.messages import BaseMessage

class MessageEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, BaseMessage):
            return o.dict()
        return super().default(o)

class SingleAgentTeam:
    def __init__(self, agent: SubAgent, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        self.agent = agent
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher

    def create_graph(self):
        workflow = StateGraph(DeepAgentState)
        
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

    def route_to_agent(self, state: DeepAgentState):
        app_logger.info(f"Routing agent with state: {json.dumps(state, indent=2, cls=MessageEncoder)}")
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            if "FINISH" in last_message.content:
                app_logger.info("FINISH detected, ending execution.")
                return "end"

        if state.get("todo_list") and len(state["todo_list"]) > 0:
            app_logger.info("TODO list is not empty, continuing execution.")
            return "continue"
        else:
            app_logger.info("TODO list is empty, ending execution.")
            return "end"
