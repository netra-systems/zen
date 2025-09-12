"""
LLM Fixtures Core - Basic LLM testing fixtures

Core LLM manager mocks for basic, streaming, and structured outputs.
Each function is  <= 8 lines, following modular architecture.
"""

import json
from typing import Any, AsyncIterator, Dict, Type
from unittest.mock import AsyncMock, Mock

from pydantic import BaseModel

from netra_backend.app.llm.llm_manager import LLMManager

# Type alias
MockResponse = Dict[str, Any]

def create_basic_llm_manager() -> Mock:
    """Create basic LLM manager mock with standard responses."""
    manager = Mock(spec=LLMManager)
    _setup_basic_methods(manager)
    _setup_health_methods(manager)
    return manager

def _setup_basic_methods(manager: Mock) -> None:
    """Setup basic LLM manager methods."""
    manager.call_llm = AsyncMock(return_value={"content": "Mock response", "tool_calls": []})
    manager.ask_llm = AsyncMock(return_value=json.dumps({"result": "success"}))
    manager.ask_structured_llm = AsyncMock(return_value={"status": "complete"})
    manager.get_response = AsyncMock(return_value="Mock LLM response")

def _setup_health_methods(manager: Mock) -> None:
    """Setup health check and monitoring methods."""
    manager.check_health = AsyncMock(return_value=True)
    manager.get_metrics = AsyncMock(return_value={"requests": 0, "errors": 0})
    manager.is_available = AsyncMock(return_value=True)

def create_streaming_llm_manager() -> Mock:
    """Create LLM manager with streaming response capabilities."""
    manager = create_basic_llm_manager()
    _setup_streaming_methods(manager)
    return manager

def _setup_streaming_methods(manager: Mock) -> None:
    """Setup streaming response methods."""
    async def mock_stream_response(prompt: str) -> AsyncIterator[MockResponse]:
        words = f"Streaming response for: {prompt[:50]}...".split()
        for word in words:
            yield {"content": word + " ", "done": False}
        yield {"content": "", "done": True}
    
    manager.astream = AsyncMock(side_effect=mock_stream_response)

def create_structured_llm_manager(schema: Type[BaseModel]) -> Mock:
    """Create LLM manager with structured output support."""
    manager = create_basic_llm_manager()
    _setup_structured_methods(manager, schema)
    return manager

def _setup_structured_methods(manager: Mock, schema: Type[BaseModel]) -> None:
    """Setup structured output methods."""
    mock_instance = _create_mock_schema_instance(schema)
    manager.ask_structured_llm = AsyncMock(return_value=mock_instance)
    manager.with_structured_output = Mock(return_value=manager)

def _create_mock_schema_instance(schema: Type[BaseModel]) -> BaseModel:
    """Create mock instance of Pydantic schema."""
    mock_data = {}
    for field_name, field_info in schema.model_fields.items():
        mock_data[field_name] = _get_mock_field_value(field_name, field_info)
    return schema(**mock_data)

def _get_mock_field_value(field_name: str, field_info) -> Any:
    """Generate mock value based on field type."""
    type_defaults = {
        str: f"mock_{field_name}",
        int: 42,
        float: 3.14,
        bool: True,
        list: ["mock", "data"],
        dict: {"key": "value"}
    }
    return type_defaults.get(field_info.annotation, f"mock_{field_name}")