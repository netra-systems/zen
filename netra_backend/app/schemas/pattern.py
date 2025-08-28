from pydantic import BaseModel, Field


class DiscoveredPattern(BaseModel):
    pattern_id: str = Field(..., description="The ID of the pattern.")
    description: str = Field(..., description="A description of the pattern.")
