from pydantic import BaseModel, Field
from typing import Optional, Any
from abc import ABC, abstractmethod
from app.llm.llm_manager import LLMManager

class ToolMetadata(BaseModel):
    name: str = Field(..., description="The unique name of the tool.")
    description: str = Field(..., description="A brief description of the tool's purpose and functionality.")
    version: str = Field("1.0.0", description="The version of the tool.")
    status: str = Field("production", description="The operational status of the tool (e.g., 'production', 'mock', 'disabled').")

class BaseTool(ABC):
    metadata: ToolMetadata
    llm_name: Optional[str] = None

    def __init__(self, llm_manager: Optional[LLMManager] = None, db_session=None):
        self.llm_manager = llm_manager
        self.db_session = db_session

    def get_llm(self):
        if not self.llm_manager:
            return None
        return self.llm_manager.get_llm(self.llm_name or "default")

    def get_metadata(self) -> dict:
        return self.metadata.dict()

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        pass