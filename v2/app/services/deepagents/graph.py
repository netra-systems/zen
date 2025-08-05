from typing import Any, Dict, List, Optional, Sequence, Tuple, TypedDict, Union

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import Runnable
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.llm.llm_manager import LLMManager

from .state import DeepAgentState
from .sub_agent import SubAgent
from .tool_dispatcher import ToolDispatcher


class SingleAgentTeam:
    def __init__(
        self, agent: SubAgent, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher
    ):
        self.agent = agent
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher

    def _get_agent_runnable(self) -> Runnable:
        llm = self.llm_manager.get_llm(self.agent.name)
        return self.agent.get_runnable(llm)

    def create_graph(self):
        graph = StateGraph(DeepAgentState)
        graph.add_node("agent", self._get_agent_runnable())
        graph.add_node("call_tool", ToolNode(self.tool_dispatcher.tools))

        graph.add_edge("agent", "call_tool")

        graph.set_entry_point("agent")

        def _route_tools(state: DeepAgentState) -> str:
            if isinstance(state["messages"][-1], HumanMessage):
                return END
            tool_calls = state["messages"][-1].tool_calls
            if not tool_calls:
                raise ValueError("No tool calls found in the last message.")
            if tool_calls[0]["name"] == "finish":
                return END
            return "call_tool"

        graph.add_conditional_edges("call_tool", _route_tools)

        return graph.compile()