"""Mock LLM implementations for development and testing.

Provides mock LLM classes that return predictable responses when real LLM services
are disabled. Each function must be  <= 8 lines as per architecture requirements.
"""
from typing import Any, AsyncIterator, Type, TypeVar

from pydantic import BaseModel

# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

T = TypeVar('T', bound=BaseModel)

class MockLLM:
    """Mock LLM for when LLMs are disabled in dev mode."""
    
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
    
    async def ainvoke(self, prompt: str) -> Any:
        class MockResponse:
            content = f"[Dev Mode - LLM Disabled] Mock response for: {prompt[:100]}..."
        return MockResponse()
    
    async def astream(self, prompt: str) -> AsyncIterator[Any]:
        words = f"[Dev Mode - LLM Disabled] Mock streaming response for: {prompt[:50]}...".split()
        for word in words:
            yield type('obj', (object,), {'content': word + ' '})()
    
    def with_structured_output(self, schema: Type[T], **kwargs) -> 'MockStructuredLLM':
        """Return a mock structured LLM for dev mode."""
        return MockStructuredLLM(self.model_name, schema)

class MockStructuredLLM:
    """Mock structured LLM for when LLMs are disabled in dev mode."""
    
    def __init__(self, model_name: str, schema: Type[T]) -> None:
        self.model_name = model_name
        self.schema = schema
    
    async def ainvoke(self, prompt: str) -> T:
        """Return a mock instance of the schema with default values."""
        return create_mock_structured_response(self.schema)