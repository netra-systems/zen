from typing import List
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.prompts import get_agent_prompt
from app.services.deepagents.state import AgentState
from app.logging_config_custom.logger import app_logger

class SubAgent:
    def __init__(self, name: str, description: str, prompt: str, tools: List[BaseTool]):
        self.name = name
        self.description = description
        self.prompt = prompt
        self.tools = tools

    def as_runnable(self, llm_manager: LLMManager):
        def agent_node(state: AgentState):
            app_logger.info(f"Executing agent '{self.name}' with state: {state}")
            prompt = get_agent_prompt(self.prompt)
            llm = llm_manager.get_llm("default").bind_tools(self.tools)
            chain = prompt | llm
            response = chain.invoke(state)
            app_logger.info(f"Agent '{self.name}' produced response: {response}")
            return {"messages": [response]}
        return agent_node