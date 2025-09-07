"""General test fixtures."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from test_framework.ssot.mocks import MockFactory, get_mock_factory
from shared.isolated_environment import IsolatedEnvironment

import pytest


@pytest.fixture
def mock_database():
    """Create a mock database following SSOT patterns.
    
    This fixture provides a comprehensive database mock that includes:
    - Async session operations (add, commit, rollback, close)
    - Query operations (execute, scalar, scalars, get)
    - Transaction support (begin, begin_nested)
    - Context manager support
    """
    factory = get_mock_factory()
    return factory.create_database_session_mock()


@pytest.fixture
def mock_cache():
    """Create a mock cache following SSOT patterns.
    
    This fixture provides a Redis-compatible cache mock that includes:
    - String operations (get, set, delete, exists, expire, ttl)
    - Hash operations (hget, hset, hgetall, hdel)
    - List operations (lpush, rpush, lpop, rpop, lrange)
    - Set operations (sadd, srem, smembers, sismember)
    - Connection operations (ping, close)
    """
    factory = get_mock_factory()
    return factory.create_redis_client_mock()


@pytest.fixture
def real_database():
    """Use real database service instance.
    
    This fixture provides access to real database services for integration testing.
    It uses the DatabaseTestManager to ensure proper test isolation.
    """
    # Initialize real database service with test configuration
    db_manager = DatabaseTestManager()
    return db_manager.get_test_session()


@pytest.fixture
def real_cache():
    """Use real cache service instance.
    
    This fixture provides access to real Redis services for integration testing.
    It uses the RedisTestManager to ensure proper test isolation.
    """
    # Initialize real cache service with test configuration
    redis_manager = RedisTestManager()
    return redis_manager.get_test_client()
