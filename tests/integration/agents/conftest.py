"""Configuration for AgentRegistry integration tests.

This module provides test configuration and fixtures for AgentRegistry integration tests,
ensuring proper test isolation and resource management.
"""

import asyncio
import pytest
from typing import Any, Dict, Generator

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_test_environment():
    """Setup isolated test environment for each test."""
    # Ensure we have proper environment isolation
    env = get_env()
    
    # Set test-specific environment variables
    test_env_vars = {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "INFO",
        "TEST_MODE": "integration"
    }
    
    # Apply test environment
    for key, value in test_env_vars.items():
        env.set(key, value)
    
    yield
    
    # Cleanup after test
    # Environment cleanup is handled by IsolatedEnvironment


@pytest.fixture
def mock_llm_manager():
    """Provide mock LLM manager for testing."""
    from tests.integration.agents.test_agent_registry_integration import MockLLMManager
    return MockLLMManager()


@pytest.fixture
def mock_websocket_manager():
    """Provide mock WebSocket manager for testing."""
    from tests.integration.agents.test_agent_registry_integration import MockWebSocketManager
    return MockWebSocketManager()


# Pytest configuration for integration tests
def pytest_configure(config):
    """Configure pytest for AgentRegistry integration tests."""
    config.addinivalue_line(
        "markers", 
        "agent_registry_integration: mark test as AgentRegistry integration test"
    )
    config.addinivalue_line(
        "markers",
        "user_isolation: mark test as user isolation test" 
    )
    config.addinivalue_line(
        "markers",
        "enterprise_critical: mark test as Enterprise customer critical"
    )
    config.addinivalue_line(
        "markers", 
        "golden_path: mark test as Golden Path business validation"
    )
    config.addinivalue_line(
        "markers",
        "memory_management: mark test as memory/resource management test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add appropriate markers."""
    for item in items:
        # Add markers based on test name patterns
        if "user_isolation" in item.name or "isolation" in item.name:
            item.add_marker(pytest.mark.user_isolation)
        
        if "enterprise" in item.name.lower():
            item.add_marker(pytest.mark.enterprise_critical)
            
        if "golden_path" in item.name.lower() or "orchestration" in item.name.lower():
            item.add_marker(pytest.mark.golden_path)
            
        if "memory" in item.name.lower() or "resource" in item.name.lower():
            item.add_marker(pytest.mark.memory_management)
            
        # All tests in this module are agent registry integration tests
        item.add_marker(pytest.mark.agent_registry_integration)