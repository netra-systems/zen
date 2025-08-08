from app.services.deepagents.sub_agent import SubAgent
from app.llm.llm_manager import LLMManager
from langchain_core.tools import BaseTool
from typing import List

class TriageSubAgent(SubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool]):
        super().__init__(llm_manager, tools)

    @property
    def name(self) -> str:
        return "TriageSubAgent"

    @property
    def description(self) -> str:
        return "This agent triages the user's request and determines which sub-agent should handle it next."

    async def ainvoke(self, state):
        # This is a placeholder implementation. In a real application, this would involve
        # calling the LLM to determine the next agent.
        state["current_agent"] = "DataSubAgent"
        return state