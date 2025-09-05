"""
Request-related type definitions for LLM operations.
Following Netra conventions with strong typing.
"""

from typing import Any, Dict, ForwardRef, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from netra_backend.app.core.serialization.unified_json_handler import parse_dict_field
from netra_backend.app.schemas.core_models import Message as LLMMessage

# Forward reference for LLMConfig to avoid circular imports
LLMConfig = ForwardRef('LLMConfig')


class StructuredOutputSchema(BaseModel):
    """Schema for structured output generation"""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]  # JSON Schema
    strict: bool = Field(default=True)
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    
    @field_validator('parameters', mode='before')
    @classmethod
    def parse_parameters(cls, v: Any) -> Dict[str, Any]:
        """Parse parameters field from JSON string if needed"""
        return parse_dict_field(v)


class LLMFunction(BaseModel):
    """Function definition for function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    required: List[str] = Field(default_factory=list)
    
    @field_validator('parameters', mode='before')
    @classmethod
    def parse_parameters(cls, v: Any) -> Dict[str, Any]:
        """Parse parameters field from JSON string if needed"""
        return parse_dict_field(v)


class LLMTool(BaseModel):
    """Tool definition for tool use"""
    type: Literal["function"]
    function: LLMFunction


class LLMRequest(BaseModel):
    """Request to LLM"""
    messages: List[LLMMessage]
    config: Optional[LLMConfig] = None
    stream: bool = Field(default=False)
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, str]]] = None
    response_format: Optional[Dict[str, str]] = None  # For structured output
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class BatchLLMRequest(BaseModel):
    """Batch request for multiple LLM calls"""
    requests: List[LLMRequest]
    parallel: bool = True
    max_concurrent: int = 5