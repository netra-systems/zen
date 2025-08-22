"""
LLM Manager Integration Tests Package

BVJ:
- Segment: ALL (Free, Early, Mid, Enterprise) - Core AI functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from LLM integration failures
- Value Impact: Ensures agent request → LLM call → response handling → error recovery
- Revenue Impact: Prevents customer AI requests from failing due to broken LLM integration

This package contains focused integration tests for:
- LLM Providers: Provider integration, fallback mechanisms, and performance
- Response Handling: Response formatting, validation, and agent integration
- Error Recovery: Timeout recovery, circuit breakers, and graceful degradation

All tests maintain ≤8 lines per test function and ≤300 lines per module.
"""

from tests.integration.llm.shared_fixtures import (
    MockLLMManagerWithIntegration,
    MockLLMProvider,
    llm_test_agent,
    mock_llm_manager,
    mock_llm_provider,
)

__all__ = [
    "MockLLMProvider",
    "MockLLMManagerWithIntegration",
    "mock_llm_provider",
    "mock_llm_manager",
    "llm_test_agent"
]