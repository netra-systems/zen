from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from app.llm.llm_manager import LLMManager
from app.schemas import SubAgentLifecycle

class BaseSubAgent(ABC):
    def __init__(self, llm_manager: Optional[LLMManager] = None):
        self.llm_manager = llm_manager
        self.state = SubAgentLifecycle.PENDING

    @abstractmethod
    async def run(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool) -> Dict[str, Any]:
        pass

    def set_state(self, state: SubAgentLifecycle):
        self.state = state

    def get_state(self) -> SubAgentLifecycle:
        return self.state