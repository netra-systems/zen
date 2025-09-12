"""
LLM Test Fixtures - Core modular LLM testing infrastructure

Consolidates 85+ duplicated AsyncMock LLM Manager setups into reusable fixtures.
Each function is  <= 8 lines. Imports specialized fixtures from sub-modules.

Business Value Justification:
- Segment: Engineering efficiency  
- Business Goal: Reduce test maintenance cost by 80%
- Value Impact: Faster test execution and debugging
- Revenue Impact: Reduced engineering time = faster feature delivery
"""

import json
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type
from unittest.mock import AsyncMock, Mock
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from pydantic import BaseModel

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.tests.llm_fixtures_advanced import (
    create_circuit_breaker_manager,
    create_error_simulating_manager,
    create_performance_monitoring_manager,
    create_provider_switching_manager,
)

# Import specialized fixtures
from netra_backend.tests.llm_fixtures_core import (
    create_basic_llm_manager,
    create_streaming_llm_manager,
    create_structured_llm_manager,
)

# Type aliases for better readability
MockResponse = Dict[str, Any]
ProviderKey = str
ModelName = str

class LLMProvider(Enum):
    """LLM provider types for testing."""
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    MOCK = "mock"

class MockResponseType(Enum):
    """Types of mock responses available."""
    BASIC = "basic"
    STRUCTURED = "structured"
    STREAMING = "streaming"
    ERROR = "error"
    TIMEOUT = "timeout"

def create_token_counting_manager() -> Mock:
    """Create LLM manager with token counting capabilities."""
    manager = create_basic_llm_manager()
    _setup_token_counting(manager)
    return manager

def _setup_token_counting(manager: Mock) -> None:
    """Setup token counting methods."""
    # Mock: Component isolation for controlled unit testing
    manager.count_tokens = Mock(return_value=100)
    # Mock: Component isolation for controlled unit testing
    manager.estimate_cost = Mock(return_value=0.002)
    # Mock: Async component isolation for testing without real async operations
    manager.get_token_usage = AsyncMock(return_value={"prompt": 50, "completion": 50})

def create_caching_llm_manager() -> Mock:
    """Create LLM manager with response caching."""
    manager = create_basic_llm_manager()
    cache = {}
    _setup_caching_methods(manager, cache)
    return manager

def _setup_caching_methods(manager: Mock, cache: Dict[str, Any]) -> None:
    """Setup caching functionality."""
    async def cached_call(prompt: str, *args, **kwargs):
        if prompt in cache:
            return cache[prompt]
        response = {"content": f"Cached response for: {prompt}", "cached": False}
        cache[prompt] = response
        return response
    
    # Mock: Async component isolation for testing without real async operations
    manager.call_llm = AsyncMock(side_effect=cached_call)

def create_model_specific_manager(model_configs: Dict[ModelName, Dict[str, Any]]) -> Mock:
    """Create LLM manager with model-specific configurations."""
    manager = create_basic_llm_manager()
    _setup_model_specific_behavior(manager, model_configs)
    return manager

def _setup_model_specific_behavior(manager: Mock, model_configs: Dict[ModelName, Dict[str, Any]]) -> None:
    """Setup model-specific response behavior."""
    async def model_specific_call(prompt: str, model: str = "default", *args, **kwargs):
        config = model_configs.get(model, {"response": "default response"})
        return {"content": config["response"], "model": model}
    
    # Mock: Async component isolation for testing without real async operations
    manager.call_llm = AsyncMock(side_effect=model_specific_call)

def create_comprehensive_test_manager() -> Mock:
    """Create comprehensive LLM manager for integration testing."""
    manager = create_basic_llm_manager()
    _setup_comprehensive_features(manager)
    return manager

def _setup_comprehensive_features(manager: Mock) -> None:
    """Setup all features for comprehensive testing."""
    # Mock: Generic component isolation for controlled unit testing
    manager.stream_response = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    manager.batch_process = AsyncMock()
    # Mock: Async component isolation for testing without real async operations
    manager.health_check = AsyncMock(return_value=True)
    # Mock: Async component isolation for testing without real async operations
    manager.get_available_models = AsyncMock(return_value=[LLMModel.GEMINI_2_5_FLASH.value, "claude-3"])
    # Mock: Component isolation for controlled unit testing
    manager.estimate_tokens = Mock(return_value=150)
    # Mock: Component isolation for controlled unit testing
    manager.validate_request = Mock(return_value=True)

# Factory function for common test scenarios
def llm_manager_factory(
    response_type: MockResponseType = MockResponseType.BASIC,
    error_rate: float = 0.0,
    providers: Optional[List[LLMProvider]] = None,
    **kwargs
) -> Mock:
    """Factory function to create LLM managers for different test scenarios."""
    if response_type == MockResponseType.STREAMING:
        return create_streaming_llm_manager()
    elif response_type == MockResponseType.ERROR:
        return create_error_simulating_manager(error_rate)
    elif providers:
        return create_provider_switching_manager(providers)
    else:
        return create_basic_llm_manager()

def quick_mock_responses(count: int = 3) -> List[MockResponse]:
    """Generate quick mock responses for testing."""
    return [
        {"content": f"Mock response {i}", "id": str(uuid.uuid4())}
        for i in range(count)
    ]

def mock_triage_result() -> Dict[str, Any]:
    """Create mock triage result for agent testing."""
    return {
        "category": "optimization",
        "confidence": 0.95,
        "requires_data": True,
        "priority": "high",
        "analysis": "User needs AI workload optimization"
    }

def mock_agent_state() -> Dict[str, Any]:
    """Create mock agent state for persistence testing."""
    return {
        "agent_id": str(uuid.uuid4()),
        "state": "processing",
        "last_update": datetime.now(UTC).isoformat(),
        "context": {"user_query": "optimize my model"}
    }