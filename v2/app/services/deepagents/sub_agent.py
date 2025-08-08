
from app.services.deepagents.subagents.base import BaseSubAgent
from app.llm.llm_manager import LLMManager
from langchain_core.tools import BaseTool
from typing import List

class SubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool]):
        self.llm_manager = llm_manager
        self.tools = tools
        self.llm_manager = llm_manager
        self.tools = tools

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the agent."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A description of the agent's purpose."""
        pass

    @abstractmethod
    async def ainvoke(self, state):
        """Invokes the agent with the given state."""
        pass
