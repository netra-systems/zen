from typing import List
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.prompts import get_agent_prompt
from app.services.deepagents.state import DeepAgentState
from app.logging_config import central_logger, LogEntry
import json
from langchain_core.messages import BaseMessage

class MessageEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, BaseMessage):
            return o.dict()
        return super().default(o)

class SubAgent:
    def __init__(self, name: str, description: str, prompt: str, tools: List[BaseTool]):
        self.name = name
        self.description = description
        self.prompt = prompt
        self.tools = tools

    def as_runnable(self, llm_manager: LLMManager):
        def agent_node(state: DeepAgentState):
            central_logger.log(LogEntry(event="agent_node_execution", data={"agent_name": self.name, "state": state}))
            prompt = get_agent_prompt(self.prompt)
            llm = llm_manager.get_llm("default").bind_tools(self.tools)
            chain = prompt | llm
            response = chain.invoke(state)
            central_logger.log(LogEntry(event="agent_node_response", data={"agent_name": self.name, "response": response.dict()}))

            # Update the todo_list in the state
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    if tool_call['name'] == 'update_state':
                        state['todo_list'] = tool_call['args']['new_todo']

            return {"messages": [response]}
        return agent_node