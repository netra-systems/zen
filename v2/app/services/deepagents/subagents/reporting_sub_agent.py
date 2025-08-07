from typing import List
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.sub_agent import SubAgent

class ReportingSubAgent(SubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool] = None):
        super().__init__(
            name="reporting",
            description="You are the reporting agent. Your job is to summarize the results of the analysis and present them to the user.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="reporting"
        )
