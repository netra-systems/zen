
from app.services.deepagents.sub_agent import SubAgent
from app.llm.llm_manager import LLMManager
from langchain_core.tools import BaseTool
from typing import List

class DataSubAgent(SubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool]):
        super().__init__(llm_manager, tools)

    @property
    def name(self) -> str:
        return "DataSubAgent"

    @property
    def description(self) -> str:
        return "This agent is responsible for fetching and processing data."

    async def ainvoke(self, state):
        # This is a placeholder implementation. In a real application, this would involve
        # calling the LLM to process the data.
        state["current_agent"] = "OptimizationsCoreSubAgent"
        return state
