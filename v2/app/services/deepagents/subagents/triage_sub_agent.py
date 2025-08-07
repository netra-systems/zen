from typing import List
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.sub_agent import SubAgent

class TriageSubAgent(SubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool] = None):
        super().__init__(
            name="triage",
            description="You are a triage agent. Your job is to analyze the user's request and determine the next steps.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="triage"
        )
