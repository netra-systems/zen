from typing import List
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.sub_agent import SubAgent

class ReportingSubAgent(SubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool] = None):
        super().__init__(
            name="ReportingAgent",
            description="Summarizes the results and presents them to the user.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="reporting"
        )