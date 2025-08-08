from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import asyncio

from app.llm.llm_manager import LLMManager
from app.schemas import SubAgentLifecycle

class BaseSubAgent(ABC):
    def __init__(self, llm_manager: Optional[LLMManager] = None, name: str = "BaseSubAgent", description: str = "This is the base sub-agent."):
        self.llm_manager = llm_manager
        self.state = SubAgentLifecycle.PENDING
        self.name = name
        self.description = description

    @abstractmethod
    async def run(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool) -> Dict[str, Any]:
        pass

    def set_state(self, state: SubAgentLifecycle):
        self.state = state

    def get_state(self) -> SubAgentLifecycle:
        return self.state

    async def run_in_background(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool):
        loop = asyncio.get_event_loop()
        loop.create_task(self.run(input_data, run_id, stream_updates))
