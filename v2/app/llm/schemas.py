from pydantic import BaseModel, Field
from typing import Optional

class LLMConfig(BaseModel):
    provider: str = Field(..., description="The LLM provider (e.g., 'google', 'openai').")
    model_name: str = Field(..., description="The name of the model.")
    api_key: Optional[str] = Field(None, description="The API key for the LLM provider.")
    temperature: float = 0.7
    max_tokens: int = 1024
