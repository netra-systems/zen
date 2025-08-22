"""
E2E Infrastructure Package - Testing framework infrastructure

Provides core infrastructure for E2E testing including LLM testing framework,
response caching, and mock clients.
"""
import os
import sys

# Add the project root directory to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tests.e2e.infrastructure.llm_test_manager import (
    LLMTestConfig,
    LLMTestManager,
    LLMTestModel,
    LLMTestRequest,
    LLMTestResponse,
)
from tests.e2e.infrastructure.llm_mock_client import LLMTestMockClient, MockClientFactory
from tests.e2e.infrastructure.llm_response_cache import (
    CacheEntry,
    CacheStatistics,
    LLMResponseCache,
)

__all__ = [
    "LLMTestManager",
    "LLMTestModel", 
    "LLMTestConfig",
    "LLMTestRequest",
    "LLMTestResponse",
    "LLMResponseCache",
    "CacheEntry",
    "CacheStatistics",
    "LLMTestMockClient",
    "MockClientFactory"
]