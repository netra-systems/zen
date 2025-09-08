"""
Isolated Environment Test Fixtures

Provides test fixtures for environment isolation in integration tests.
"""

import pytest
from typing import Dict, Any, Optional
from unittest.mock import patch
from shared.isolated_environment import IsolatedEnvironment


@pytest.fixture
def isolated_env():
    """
    Fixture that provides an isolated environment for testing.
    
    Returns an IsolatedEnvironment instance that can be used in tests
    to ensure proper environment isolation.
    """
    env = IsolatedEnvironment()
    return env


@pytest.fixture
def mock_env_vars():
    """
    Fixture that provides mocked environment variables for testing.
    """
    mock_vars = {
        'NETRA_ENV': 'test',
        'DATABASE_URL': 'postgresql://test:test@localhost:5434/test',
        'REDIS_URL': 'redis://localhost:6381/0',
        'JWT_SECRET_KEY': 'test-jwt-secret-key',
        'SERVICE_SECRET': 'test-service-secret'
    }
    return mock_vars


@pytest.fixture
def patched_env(mock_env_vars):
    """
    Fixture that patches environment variables for the test duration.
    """
    with patch.dict('os.environ', mock_env_vars):
        yield mock_env_vars