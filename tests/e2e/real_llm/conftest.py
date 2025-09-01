"""Shared fixtures for Real LLM Test Suite.

Provides common fixtures and utilities for all real LLM tests.
Enforces real API usage and validates environment setup.
"""

import asyncio
import os
import time
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest

from netra_backend.app.config import get_config
from shared.isolated_environment import get_env
from netra_backend.app.llm.llm_manager import LLMManager


class RealLLMTestManager:
    """Manages real LLM testing with cost controls and validation."""
    
    def __init__(self):
        self.config = get_config()
        self.max_cost_per_test = 0.50  # $0.50 max per test
        self.max_daily_cost = 10.0  # $10 daily limit
        self.total_tokens_used = 0
        self.current_daily_cost = 0.0
        self.request_count = 0
        self.last_reset_time = time.time()
        self._validate_required_environment()
        
    def _validate_required_environment(self):
        """Validate that required API keys are available."""
        env = get_env()
        
        # At minimum, require GEMINI_API_KEY for Google AI
        gemini_key = env.get("GEMINI_API_KEY")
        if not gemini_key:
            raise AssertionError(
                "GEMINI_API_KEY environment variable is required for real LLM testing. "
                "Please set GEMINI_API_KEY to run these tests. "
                "MOCKS ARE FORBIDDEN - real LLM API integration is mandatory."
            )
        
        if len(gemini_key) < 10:
            raise AssertionError(
                "GEMINI_API_KEY appears to be invalid (too short). "
                "Please provide a valid API key for real LLM testing."
            )
            
        # Warn about optional keys
        optional_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
        missing_optional = [key for key in optional_keys if not env.get(key)]
        if missing_optional:
            print(f"Warning: Optional API keys missing: {missing_optional}")
            print("Some tests may be skipped if specific providers are not available.")
    
    def get_llm_timeout(self) -> int:
        """Get LLM timeout in seconds for tests."""
        return int(get_env().get("TEST_LLM_TIMEOUT", "60"))
    
    def validate_cost_limits(self, tokens_used: int) -> bool:
        """Validate token usage within cost limits."""
        estimated_cost = tokens_used * 0.000002  # Conservative estimate
        return estimated_cost <= self.max_cost_per_test
    
    def check_daily_cost_limits(self, estimated_tokens: int) -> bool:
        """Check if request would exceed daily cost limits."""
        estimated_cost = estimated_tokens * 0.000002
        return (self.current_daily_cost + estimated_cost) <= self.max_daily_cost
    
    def record_usage(self, tokens_used: int):
        """Record token usage for cost tracking."""
        self.total_tokens_used += tokens_used
        estimated_cost = tokens_used * 0.000002
        self.current_daily_cost += estimated_cost
        self.request_count += 1


@pytest.fixture(scope="session")
def real_llm_test_manager():
    """Session-scoped real LLM test manager."""
    return RealLLMTestManager()


@pytest.fixture(scope="function")
def llm_manager(real_llm_test_manager):
    """Function-scoped LLM manager with API key validation."""
    config = get_config()
    env = get_env()
    
    # Ensure API keys are populated
    gemini_key = env.get("GEMINI_API_KEY")
    if not gemini_key:
        raise AssertionError(
            "GEMINI_API_KEY environment variable is required for LLM manager initialization. "
            "Please set GEMINI_API_KEY to run these tests. "
            "MOCKS ARE FORBIDDEN - real LLM API integration is mandatory."
        )
    
    # Configure LLM manager with real API keys
    if config.llm_configs:
        for config_name, llm_config in config.llm_configs.items():
            if not llm_config.api_key and llm_config.provider.value == "google":
                llm_config.api_key = gemini_key
    else:
        raise AssertionError(
            "LLM configurations not found in config. "
            "Please ensure proper LLM configuration is available for real API testing."
        )
            
    return LLMManager(config)


@pytest.fixture(scope="function")
def cost_validator(real_llm_test_manager):
    """Cost validation fixture for individual tests."""
    def validate(tokens_used: int) -> bool:
        return real_llm_test_manager.validate_cost_limits(tokens_used)
    return validate


@pytest.fixture(scope="function") 
def mock_prevention():
    """Fixture that prevents accidental mock usage in real LLM tests."""
    original_patch = patch
    
    def forbidden_patch(*args, **kwargs):
        raise AssertionError(
            "MOCKS ARE FORBIDDEN in real LLM tests. "
            "All tests must use real API calls. "
            "Remove any mock.patch usage from this test."
        )
    
    # Temporarily replace patch to prevent accidental mock usage
    import unittest.mock
    unittest.mock.patch = forbidden_patch
    
    yield
    
    # Restore original patch after test
    unittest.mock.patch = original_patch


@pytest.fixture(autouse=True)
def enforce_real_services():
    """Auto-applied fixture that enforces real service usage."""
    # Check environment for test execution context
    env = get_env()
    
    # Ensure we're not in a mocked environment
    if env.get("USE_MOCKS") == "true":
        pytest.skip("Real LLM tests cannot run in mocked environment")
    
    # Ensure required services are available
    if not env.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY required for real LLM tests")


def pytest_configure(config):
    """Configure pytest markers for real LLM tests."""
    config.addinivalue_line(
        "markers", "api_integration: Tests real API integration"
    )
    config.addinivalue_line(
        "markers", "cost_tracking: Tests real cost tracking and optimization"
    )
    config.addinivalue_line(
        "markers", "error_handling: Tests real error recovery and rate limits"
    )
    config.addinivalue_line(
        "markers", "performance: Tests real performance SLAs"
    )
    config.addinivalue_line(
        "markers", "streaming: Tests real streaming responses"
    )


def pytest_runtest_setup(item):
    """Setup for each test run - validate real service requirements."""
    # Check if test requires real LLM
    if item.get_closest_marker("real_llm"):
        env = get_env()
        if not env.get("GEMINI_API_KEY"):
            pytest.skip("Real LLM tests require GEMINI_API_KEY")