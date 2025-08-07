from typing import List
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.sub_agent import SubAgent

class TriageSubAgent(SubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool] = None):
        super().__init__(
            name="TriageSubAgent",
            description="Analyzes the user's request and determines the appropriate workflow.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="triage"
        )