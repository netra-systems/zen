from typing import List
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.prompts import get_agent_prompt
from app.services.deepagents.state import AgentState

class SubAgent:
    def __init__(self, name: str, description: str, prompt: str, tools: List[BaseTool]):
        self.name = name
        self.description = description
        self.prompt = prompt
        self.tools = tools

    def as_runnable(self, llm_manager: LLMManager):
        def agent_node(state: AgentState):
            prompt = get_agent_prompt(self.prompt)
            llm = llm_manager.get_llm("default").bind_tools(self.tools)
            chain = prompt | llm
            response = chain.invoke(state)
            return {"messages": [response]}
        return agent_node
