from app.services.deepagents.sub_agent import SubAgent
from typing import List
from app.llm.llm_manager import LLMManager
from langchain_core.tools import BaseTool

class ReportingSubAgent(SubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool]):
        super().__init__(llm_manager, tools)

    @property
    def name(self) -> str:
        return "ReportingSubAgent"

    @property
    def description(self) -> str:
        return "This agent is responsible for summarizing the results and reporting them to the user."

    async def ainvoke(self, state):
        # This is a placeholder implementation. In a real application, this would involve
        # calling the LLM to generate a report.
        state["current_agent"] = "__end__"
        return state