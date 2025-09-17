"""
Isolated conftest for WebSocket bridge tests that don't require real services.
This allows us to test the bridge functionality without Docker dependencies.

SSOT COMPLIANCE: Uses IsolatedEnvironment for all environment access
"""

import pytest
import asyncio

# SSOT Environment Access - NO direct os.environ usage
from shared.isolated_environment import get_env

# CRITICAL: Do NOT import heavy backend modules at module level
# This causes Docker to crash on Windows during pytest collection
# These will be imported lazily when needed inside fixtures

# Ensure isolated environment using SSOT pattern
_env = get_env()
_env.set('WEBSOCKET_TEST_ISOLATED', 'true', source='test')
_env.set('SKIP_REAL_SERVICES', 'true', source='test')

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def isolated_environment():
    """Fixture to ensure isolated test environment using SSOT pattern."""
    # Use SSOT IsolatedEnvironment - NO direct os.environ access
    env = get_env()

    # Mock environment variables that might cause real service connections
    old_env = {}
    test_env_vars = {
        'WEBSOCKET_TEST_ISOLATED': 'true',
        'SKIP_REAL_SERVICES': 'true',
        'DATABASE_URL': 'mock://test',
        'REDIS_URL': 'mock://test',
    }

    for key, value in test_env_vars.items():
        old_env[key] = env.get(key)
        env.set(key, value, source='test')

    yield env

    # Restore original environment using SSOT pattern
    for key, old_value in old_env.items():
        if old_value is None:
            env.remove(key)
        else:
            env.set(key, old_value, source='test')

# Auto-use the isolated environment for all tests in this module
pytest_plugins = []
