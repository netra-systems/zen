from langgraph.graph import StateGraph, END
from app.services.deepagents.state import DeepAgentState
from app.services.deepagents.sub_agent import SubAgent
from app.llm.llm_manager import LLMManager
from app.services.deepagents.tool_dispatcher import ToolDispatcher
from app.logging_config import central_logger, LogEntry
import json
from langchain_core.messages import BaseMessage, ToolMessage

class MessageEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, BaseMessage):
            return o.dict()
        return super().default(o)

class Supervisor:
    def __init__(self, sub_agents: list[SubAgent], llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        self.sub_agents = sub_agents
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher

    def create_graph(self):
        workflow = StateGraph(DeepAgentState)
        
        for sub_agent in self.sub_agents:
            workflow.add_node(sub_agent.name, sub_agent.as_runnable())
        workflow.add_node("tool_dispatcher", self.tool_dispatcher.as_runnable())

        for i in range(len(self.sub_agents) - 1):
            workflow.add_edge(self.sub_agents[i].name, self.sub_agents[i+1].name)

        workflow.add_conditional_edges(
            self.sub_agents[-1].name,
            lambda x: "__end__" if not x.get("tool_calls") else "tool_dispatcher",
            {"__end__": END, "tool_dispatcher": "tool_dispatcher"}
        )

        workflow.add_conditional_edges(
            "tool_dispatcher",
            lambda x: x["current_agent"],
            {sub_agent.name: sub_agent.name for sub_agent in self.sub_agents}
        )
        
        workflow.set_entry_point(self.sub_agents[0].name)
        return workflow.compile()