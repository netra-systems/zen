from typing import List, Dict, Any
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.prompts import get_agent_prompt
from app.services.deepagents.state import DeepAgentState
from app.logging_config import central_logger, LogEntry
import json
from langchain_core.messages import BaseMessage, AIMessage

class MessageEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, BaseMessage):
            return o.dict()
        return super().default(o)

class SubAgent:
    def __init__(self, name: str, description: str, llm_manager: LLMManager, tools: List[BaseTool] = None):
        self.name = name
        self.description = description
        self.llm_manager = llm_manager
        self.tools = tools or []

    async def run(self, state: DeepAgentState) -> Dict[str, Any]:
        central_logger.log(LogEntry(event="agent_node_execution", data={"agent_name": self.name, "state": state}))
        prompt = get_agent_prompt(self.description)
        llm = self.llm_manager.get_llm("default").bind_tools(self.tools)
        chain = prompt | llm
        response = await chain.ainvoke(state)
        central_logger.log(LogEntry(event="agent_node_response", data={"agent_name": self.name, "response": response.dict()}))

        tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []

        return {"messages": [response], "tool_calls": tool_calls}

    def as_runnable(self):
        async def agent_node(state: DeepAgentState):
            return await self.run(state)
        return agent_node
