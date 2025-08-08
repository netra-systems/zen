from app.services.deepagents.subagents.base import BaseSubAgent
from app.llm.llm_manager import LLMManager
from langchain_core.tools import BaseTool
from typing import List

class SubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool]):
        super().__init__(llm_manager, tools)
