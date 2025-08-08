from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from app.llm.llm_manager import LLMManager
from app.schemas import AnalysisRequest
from sqlalchemy.ext.asyncio import AsyncSession

class BaseAgent(ABC):
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager, websocket_manager: any):
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.websocket_manager = websocket_manager

    @abstractmethod
    async def run(self, analysis_request: AnalysisRequest, run_id: str, stream_updates: bool) -> Dict[str, Any]:
        pass
