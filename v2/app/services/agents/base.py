from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseSubAgent(ABC):
    @abstractmethod
    async def run(self, input_data: Dict[str, Any], run_id: str, stream_updates: bool) -> Dict[str, Any]:
        pass
