from pydantic import BaseModel, Field
from typing import Optional

class ToolMetadata(BaseModel):
    name: str = Field(..., description="The unique name of the tool.")
    description: str = Field(..., description="A brief description of the tool's purpose and functionality.")
    version: str = Field("1.0.0", description="The version of the tool.")
    status: str = Field("production", description="The operational status of the tool (e.g., 'production', 'mock', 'disabled').")

class BaseTool:
    metadata: ToolMetadata

    def __init__(self, llm_connector=None, db_session=None):
        self.llm_connector = llm_connector
        self.db_session = db_session

    def get_metadata(self) -> dict:
        return self.metadata.dict()