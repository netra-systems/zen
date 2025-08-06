from pydantic import BaseModel, Field
from typing import Optional, Any
from abc import ABC, abstractmethod
from app.llm.llm_manager import LLMManager

class ToolMetadata(BaseModel):
    name: str = Field(..., description="The unique name of the tool.")
    description: str = Field(..., description="A brief description of the tool's purpose and functionality.")
    version: str = Field("1.0.0", description="The version of the tool.")
    status: str = Field("production", description="The operational status of the tool (e.g., 'production', 'mock', 'disabled').")

from app.services.apex_optimizer_agent.tools.context import ToolContext

class BaseTool(ABC):
    metadata: ToolMetadata
    llm_name: Optional[str] = None

    def __init__(self, context: ToolContext):
        self.context = context

    def get_llm(self):
        if not self.context.llm_manager:
            return None
        return self.context.llm_manager.get_llm(self.llm_name or "default")

    def get_metadata(self) -> dict:
        return self.metadata.dict()

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        pass