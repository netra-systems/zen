from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class LLMConfig(BaseModel):
    provider: str = Field(..., description="The LLM provider (e.g., 'google', 'openai').")
    model_name: str = Field(..., description="The name of the model.")
    api_key: Optional[str] = Field(None, description="The API key for the LLM provider.")
    generation_config: Dict[str, Any] = Field({}, description="A dictionary of generation parameters, e.g., temperature, max_tokens.")

class ToolConfig(BaseModel):
    name: str = Field(..., description="The name of the tool.")
    llm_config: Optional[LLMConfig] = Field(None, description="LLM configuration for this tool.")