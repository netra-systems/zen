from pydantic import BaseModel, Field
from typing import Optional, Any
from abc import ABC, abstractmethod
from app.services.context import ToolContext

class ToolMetadata(BaseModel):
    name: str = Field(..., description="The unique name of the tool.")
    description: str = Field(..., description="A brief description of the tool's purpose and functionality.")
    version: str = Field("1.0.0", description="The version of the tool.")
    status: str = Field("production", description="The operational status of the tool (e.g., 'production', 'mock', 'disabled').")

class BaseTool(ABC):
    metadata: ToolMetadata
    llm_name: Optional[str] = None

    def get_metadata(self) -> dict:
        return self.metadata.dict()

    @abstractmethod
    async def run(self, context: ToolContext, **kwargs) -> Any:
        pass
