from typing import List
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.sub_agent import SubAgent

class DataSubAgent(SubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool] = None):
        super().__init__(
            name="data",
            description="You are a data agent. Your job is to gather and enrich the data needed for the analysis.",
            llm_manager=llm_manager,
            tools=tools
        )
