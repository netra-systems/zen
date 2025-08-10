# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:48:31.172894+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to apex optimizer tools
# Git: v6 | be70ff77 | clean
# Change: Feature | Scope: Module | Risk: High
# Session: f4b153af-998e-4648-bfed-e03ac78b4b8f | Seq: 3
# Review: Pending | Score: 85
# ================================
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
