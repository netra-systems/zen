"""
SSOT Database Skip Conditions for Integration Tests

This module provides centralized database availability checking and skip conditions
for integration tests. It ensures tests gracefully skip when external dependencies
are unavailable rather than hard-failing.

Business Value: Platform/Internal - Test Infrastructure Resilience
Prevents integration test failures from blocking development when databases unavailable.

CRITICAL: This is part of the database connection failure remediation.
Use these decorators to make tests resilient to missing database infrastructure.
"""

import asyncio
import logging
import socket
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class DatabaseAvailabilityChecker:
    """
    Centralized database availability checking for integration tests.
    
    This class provides methods to check if required databases are available
    and provides appropriate skip conditions for tests.
    """
    
    def __init__(self):
        self.env = get_env()
        self.availability_cache: Dict[str, Tuple[bool, float]] = {}
        self.cache_ttl = 30.0  # Cache results for 30 seconds
        
    def _get_cache_key(self, db_type: str, host: str, port: int) -> str:
        """Generate cache key for database availability check."""
        return f"{db_type}_{host}_{port}"
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid."""
        return time.time() - timestamp < self.cache_ttl
    
    def check_port_available(self, host: str, port: int, timeout: float = 5.0) -> bool:
        """Check if a port is accessible on the given host."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.error, OSError, ConnectionRefusedError):
            return False
    
    def check_postgresql_available(self, host: str = None, port: int = None) -> Tuple[bool, str]:
        """
        Check if PostgreSQL is available.
        
        Returns:
            Tuple of (is_available, reason)
        """
        # Get connection details
        host = host or self.env.get("TEST_POSTGRES_HOST", self.env.get("POSTGRES_HOST", "localhost"))
        port = port or int(self.env.get("TEST_POSTGRES_PORT", self.env.get("POSTGRES_PORT", 5432)))
        
        cache_key = self._get_cache_key("postgresql", host, port)
        
        # Check cache first
        if cache_key in self.availability_cache:
            is_available, timestamp = self.availability_cache[cache_key]
            if self._is_cache_valid(timestamp):
                reason = "PostgreSQL available (cached)" if is_available else "PostgreSQL unavailable (cached)"
                return is_available, reason
        
        # Check port availability first (quick check)
        if not self.check_port_available(host, port, timeout=3.0):
            self.availability_cache[cache_key] = (False, time.time())
            return False, f"PostgreSQL port {host}:{port} not accessible"
        
        # Try actual database connection
        try:
            db_user = self.env.get("TEST_POSTGRES_USER", self.env.get("POSTGRES_USER", "postgres"))
            db_password = self.env.get("TEST_POSTGRES_PASSWORD", self.env.get("POSTGRES_PASSWORD", "postgres"))
            db_name = self.env.get("TEST_POSTGRES_DB", self.env.get("POSTGRES_DB", "postgres"))
            
            db_url = f"postgresql://{db_user}:{db_password}@{host}:{port}/{db_name}"
            
            engine = create_engine(db_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
            
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                
            engine.dispose()
            
            self.availability_cache[cache_key] = (True, time.time())
            return True, f"PostgreSQL available at {host}:{port}"
            
        except SQLAlchemyError as e:
            error_reason = f"PostgreSQL connection failed: {str(e)[:100]}"
            self.availability_cache[cache_key] = (False, time.time())
            return False, error_reason
        except Exception as e:
            error_reason = f"PostgreSQL check error: {str(e)[:100]}"
            self.availability_cache[cache_key] = (False, time.time())
            return False, error_reason
    
    def check_clickhouse_available(self, host: str = None, port: int = None) -> Tuple[bool, str]:
        """
        Check if ClickHouse is available.
        
        Returns:
            Tuple of (is_available, reason)
        """
        # Get connection details
        host = host or self.env.get("TEST_CLICKHOUSE_HOST", self.env.get("CLICKHOUSE_HOST", "localhost"))
        port = port or int(self.env.get("TEST_CLICKHOUSE_HTTP_PORT", self.env.get("CLICKHOUSE_HTTP_PORT", 8123)))
        
        cache_key = self._get_cache_key("clickhouse", host, port)
        
        # Check cache first
        if cache_key in self.availability_cache:
            is_available, timestamp = self.availability_cache[cache_key]
            if self._is_cache_valid(timestamp):
                reason = "ClickHouse available (cached)" if is_available else "ClickHouse unavailable (cached)"
                return is_available, reason
        
        # Check port availability first
        if not self.check_port_available(host, port, timeout=3.0):
            self.availability_cache[cache_key] = (False, time.time())
            return False, f"ClickHouse port {host}:{port} not accessible"
        
        # For now, just check port accessibility since ClickHouse connection is more complex
        self.availability_cache[cache_key] = (True, time.time())
        return True, f"ClickHouse port accessible at {host}:{port}"
    
    def check_redis_available(self, host: str = None, port: int = None) -> Tuple[bool, str]:
        """
        Check if Redis is available.
        
        Returns:
            Tuple of (is_available, reason)
        """
        # Get connection details
        host = host or self.env.get("TEST_REDIS_HOST", self.env.get("REDIS_HOST", "localhost"))
        port = port or int(self.env.get("TEST_REDIS_PORT", self.env.get("REDIS_PORT", 6379)))
        
        cache_key = self._get_cache_key("redis", host, port)
        
        # Check cache first
        if cache_key in self.availability_cache:
            is_available, timestamp = self.availability_cache[cache_key]
            if self._is_cache_valid(timestamp):
                reason = "Redis available (cached)" if is_available else "Redis unavailable (cached)"
                return is_available, reason
        
        # Check port availability
        is_available = self.check_port_available(host, port, timeout=3.0)
        self.availability_cache[cache_key] = (is_available, time.time())
        
        if is_available:
            return True, f"Redis available at {host}:{port}"
        else:
            return False, f"Redis port {host}:{port} not accessible"


# Global availability checker instance
_availability_checker = DatabaseAvailabilityChecker()


# Skip condition decorators
def skip_if_postgresql_unavailable(test_func: Callable) -> Callable:
    """
    Skip test if PostgreSQL is unavailable.
    
    Usage:
        @skip_if_postgresql_unavailable
        def test_user_creation():
            # Test that requires PostgreSQL
            pass
    """
    @wraps(test_func)
    def wrapper(*args, **kwargs):
        is_available, reason = _availability_checker.check_postgresql_available()
        if not is_available:
            pytest.skip(f"PostgreSQL unavailable: {reason}")
        return test_func(*args, **kwargs)
    
    return wrapper


def skip_if_clickhouse_unavailable(test_func: Callable) -> Callable:
    """
    Skip test if ClickHouse is unavailable.
    
    Usage:
        @skip_if_clickhouse_unavailable
        def test_analytics_query():
            # Test that requires ClickHouse
            pass
    """
    @wraps(test_func)
    def wrapper(*args, **kwargs):
        is_available, reason = _availability_checker.check_clickhouse_available()
        if not is_available:
            pytest.skip(f"ClickHouse unavailable: {reason}")
        return test_func(*args, **kwargs)
    
    return wrapper


def skip_if_redis_unavailable(test_func: Callable) -> Callable:
    """
    Skip test if Redis is unavailable.
    
    Usage:
        @skip_if_redis_unavailable
        def test_caching():
            # Test that requires Redis
            pass
    """
    @wraps(test_func)
    def wrapper(*args, **kwargs):
        is_available, reason = _availability_checker.check_redis_available()
        if not is_available:
            pytest.skip(f"Redis unavailable: {reason}")
        return test_func(*args, **kwargs)
    
    return wrapper


def skip_if_database_unavailable(*database_types: str):
    """
    Skip test if any of the specified databases are unavailable.
    
    Args:
        database_types: List of database types ('postgresql', 'clickhouse', 'redis')
    
    Usage:
        @skip_if_database_unavailable('postgresql', 'redis')
        def test_full_integration():
            # Test that requires both PostgreSQL and Redis
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        @wraps(test_func)
        def wrapper(*args, **kwargs):
            unavailable_databases = []
            
            for db_type in database_types:
                if db_type.lower() == 'postgresql':
                    is_available, reason = _availability_checker.check_postgresql_available()
                    if not is_available:
                        unavailable_databases.append(f"PostgreSQL: {reason}")
                        
                elif db_type.lower() == 'clickhouse':
                    is_available, reason = _availability_checker.check_clickhouse_available()
                    if not is_available:
                        unavailable_databases.append(f"ClickHouse: {reason}")
                        
                elif db_type.lower() == 'redis':
                    is_available, reason = _availability_checker.check_redis_available()
                    if not is_available:
                        unavailable_databases.append(f"Redis: {reason}")
                        
                else:
                    logger.warning(f"Unknown database type for skip condition: {db_type}")
            
            if unavailable_databases:
                skip_reason = "Required databases unavailable: " + "; ".join(unavailable_databases)
                pytest.skip(skip_reason)
            
            return test_func(*args, **kwargs)
        
        return wrapper
    return decorator


# Async version of skip decorators
def skip_if_postgresql_unavailable_async(test_func: Callable) -> Callable:
    """Async version of skip_if_postgresql_unavailable."""
    @wraps(test_func)
    async def wrapper(*args, **kwargs):
        is_available, reason = _availability_checker.check_postgresql_available()
        if not is_available:
            pytest.skip(f"PostgreSQL unavailable: {reason}")
        return await test_func(*args, **kwargs)
    
    return wrapper


def skip_if_clickhouse_unavailable_async(test_func: Callable) -> Callable:
    """Async version of skip_if_clickhouse_unavailable."""
    @wraps(test_func)
    async def wrapper(*args, **kwargs):
        is_available, reason = _availability_checker.check_clickhouse_available()
        if not is_available:
            pytest.skip(f"ClickHouse unavailable: {reason}")
        return await test_func(*args, **kwargs)
    
    return wrapper


def skip_if_database_unavailable_async(*database_types: str):
    """Async version of skip_if_database_unavailable."""
    def decorator(test_func: Callable) -> Callable:
        @wraps(test_func)
        async def wrapper(*args, **kwargs):
            unavailable_databases = []
            
            for db_type in database_types:
                if db_type.lower() == 'postgresql':
                    is_available, reason = _availability_checker.check_postgresql_available()
                    if not is_available:
                        unavailable_databases.append(f"PostgreSQL: {reason}")
                        
                elif db_type.lower() == 'clickhouse':
                    is_available, reason = _availability_checker.check_clickhouse_available()
                    if not is_available:
                        unavailable_databases.append(f"ClickHouse: {reason}")
                        
                elif db_type.lower() == 'redis':
                    is_available, reason = _availability_checker.check_redis_available()
                    if not is_available:
                        unavailable_databases.append(f"Redis: {reason}")
            
            if unavailable_databases:
                skip_reason = "Required databases unavailable: " + "; ".join(unavailable_databases)
                pytest.skip(skip_reason)
            
            return await test_func(*args, **kwargs)
        
        return wrapper
    return decorator


# Pytest fixtures for database availability
@pytest.fixture
def postgresql_available():
    """Pytest fixture that skips test if PostgreSQL is unavailable."""
    is_available, reason = _availability_checker.check_postgresql_available()
    if not is_available:
        pytest.skip(f"PostgreSQL unavailable: {reason}")
    return True


@pytest.fixture
def clickhouse_available():
    """Pytest fixture that skips test if ClickHouse is unavailable."""
    is_available, reason = _availability_checker.check_clickhouse_available()
    if not is_available:
        pytest.skip(f"ClickHouse unavailable: {reason}")
    return True


@pytest.fixture
def redis_available():
    """Pytest fixture that skips test if Redis is unavailable."""
    is_available, reason = _availability_checker.check_redis_available()
    if not is_available:
        pytest.skip(f"Redis unavailable: {reason}")
    return True


# Context manager for database requirement checking
@asynccontextmanager
async def require_databases(*database_types: str):
    """
    Async context manager that checks database availability before executing code block.
    
    Usage:
        async with require_databases('postgresql', 'redis'):
            # Code that requires both PostgreSQL and Redis
            pass
    """
    unavailable_databases = []
    
    for db_type in database_types:
        if db_type.lower() == 'postgresql':
            is_available, reason = _availability_checker.check_postgresql_available()
            if not is_available:
                unavailable_databases.append(f"PostgreSQL: {reason}")
                
        elif db_type.lower() == 'clickhouse':
            is_available, reason = _availability_checker.check_clickhouse_available()
            if not is_available:
                unavailable_databases.append(f"ClickHouse: {reason}")
                
        elif db_type.lower() == 'redis':
            is_available, reason = _availability_checker.check_redis_available()
            if not is_available:
                unavailable_databases.append(f"Redis: {reason}")
    
    if unavailable_databases:
        skip_reason = "Required databases unavailable: " + "; ".join(unavailable_databases)
        pytest.skip(skip_reason)
    
    try:
        yield
    except Exception as e:
        logger.error(f"Error in require_databases context: {e}")
        raise


def get_availability_checker() -> DatabaseAvailabilityChecker:
    """Get the global database availability checker instance."""
    return _availability_checker


# Export all utilities
__all__ = [
    'DatabaseAvailabilityChecker',
    'skip_if_postgresql_unavailable',
    'skip_if_clickhouse_unavailable', 
    'skip_if_redis_unavailable',
    'skip_if_database_unavailable',
    'skip_if_postgresql_unavailable_async',
    'skip_if_clickhouse_unavailable_async',
    'skip_if_database_unavailable_async',
    'postgresql_available',
    'clickhouse_available',
    'redis_available',
    'require_databases',
    'get_availability_checker'
]