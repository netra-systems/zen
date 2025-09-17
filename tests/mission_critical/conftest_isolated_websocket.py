from shared.isolated_environment import get_env
"""
Isolated conftest for WebSocket bridge tests that don't require real services.
This allows us to test the bridge functionality without Docker dependencies.
"""

import pytest
import os
import asyncio

# CRITICAL: Do NOT import heavy backend modules at module level
# This causes Docker to crash on Windows during pytest collection
# These will be imported lazily when needed inside fixtures

# Ensure isolated environment
os.environ['WEBSOCKET_TEST_ISOLATED'] = 'true'
os.environ['SKIP_REAL_SERVICES'] = 'true'

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def isolated_environment():
    """Fixture to ensure isolated test environment."""
    # Mock environment variables that might cause real service connections
    old_env = {}
    test_env_vars = {
        'WEBSOCKET_TEST_ISOLATED': 'true',
        'SKIP_REAL_SERVICES': 'true',
        'DATABASE_URL': 'mock://test',
        'REDIS_URL': 'mock://test',
    }
    
    for key, value in test_env_vars.items():
        old_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    for key, old_value in old_env.items():
        if old_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_value

# Auto-use the isolated environment for all tests in this module
pytest_plugins = []
