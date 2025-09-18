from shared.isolated_environment import get_env
"""Environment-aware testing markers and utilities.

This module provides decorators and utilities for marking tests with their
compatible environments (test, dev, staging, prod) and managing environment-specific
test execution according to SPEC/environment_aware_testing.xml.
"""

import functools
import os
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import pytest


class TestEnvironment(Enum):
    """Available test execution environments."""
    TEST = "test"      # Local test environment with mocks
    DEV = "dev"        # Development environment with real services
    STAGING = "staging"  # Pre-production environment
    PROD = "prod"      # Production environment (restricted)
    
    @classmethod
    def from_string(cls, value: str) -> 'TestEnvironment':
        """Convert string to TestEnvironment enum."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Invalid environment: {value}. Must be one of: {', '.join([e.value for e in cls])}")
    
    @classmethod
    def get_current(cls) -> 'TestEnvironment':
        """Get the current test environment from env vars."""
        # Check multiple environment variables for compatibility
        env_str = (
            os.environ.get("TEST_ENV") or
            os.environ.get("ENVIRONMENT") or
            os.environ.get("NETRA_ENVIRONMENT") or
            "test"
        ).lower()
        return cls.from_string(env_str)


class EnvironmentCapability:
    """Represents a capability required by a test in a specific environment."""
    
    def __init__(self, 
                 services: Optional[List[str]] = None,
                 features: Optional[List[str]] = None,
                 data: Optional[List[str]] = None):
        """Initialize environment capability requirements.
        
        Args:
            services: Required services (e.g., ["redis", "postgres"])
            features: Required features (e.g., ["oauth_configured", "ssl_enabled"])
            data: Required test data (e.g., ["test_tenant", "sample_threads"])
        """
        self.services = services or []
        self.features = features or []
        self.data = data or []
    
    def is_satisfied(self, environment: TestEnvironment) -> Tuple[bool, Optional[str]]:
        """Check if capabilities are satisfied in the given environment.
        
        Returns:
            Tuple of (is_satisfied, reason_if_not)
        """
        # Check service availability
        for service in self.services:
            if not _is_service_available(service, environment):
                return False, f"Service '{service}' not available in {environment.value}"
        
        # Check feature availability
        for feature in self.features:
            if not _is_feature_enabled(feature, environment):
                return False, f"Feature '{feature}' not enabled in {environment.value}"
        
        # Check data availability
        for data in self.data:
            if not _is_test_data_available(data, environment):
                return False, f"Test data '{data}' not available in {environment.value}"
        
        return True, None


class EnvironmentSafety:
    """Represents safety constraints for test execution."""
    
    def __init__(self,
                 operations: Optional[List[str]] = None,
                 impact: str = "unknown",
                 rollback: bool = False,
                 readonly: bool = False,
                 rate_limit: Optional[int] = None):
        """Initialize environment safety constraints.
        
        Args:
            operations: Allowed operations (e.g., ["read_only", "create"])
            impact: Impact level ("none", "low", "medium", "high")
            rollback: Whether test can rollback changes
            readonly: Whether test is read-only
            rate_limit: Max operations per second
        """
        self.operations = operations or []
        self.impact = impact
        self.rollback = rollback
        self.readonly = readonly
        self.rate_limit = rate_limit
    
    def is_safe_for_environment(self, environment: TestEnvironment) -> Tuple[bool, Optional[str]]:
        """Check if test is safe for the given environment.
        
        Returns:
            Tuple of (is_safe, reason_if_not)
        """
        if environment == TestEnvironment.PROD:
            if not self.readonly and "read_only" not in self.operations:
                return False, "Production tests must be read-only unless explicitly marked safe"
            
            if self.impact in ["medium", "high"]:
                return False, f"Impact level '{self.impact}' too high for production"
            
            if not self.rollback and not self.readonly:
                return False, "Production tests must have rollback capability or be read-only"
        
        return True, None


def env(*environments: Union[str, TestEnvironment], **kwargs):
    """Mark test with compatible environments.
    
    Args:
        *environments: Environments where test can run
        **kwargs: Additional parameters (readonly, rate_limit, etc.)
    
    Usage:
        @env("staging")
        def test_staging_only():
            pass
        
        @env("dev", "staging", "prod")
        def test_multi_env():
            pass
        
        @env("prod", readonly=True, rate_limit=10)
        def test_prod_monitoring():
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Parse environments
        test_envs = set()
        for env_arg in environments:
            if isinstance(env_arg, str):
                test_envs.add(TestEnvironment.from_string(env_arg))
            elif isinstance(env_arg, TestEnvironment):
                test_envs.add(env_arg)
            else:
                raise ValueError(f"Invalid environment type: {type(env_arg)}")
        
        # Default to TEST if no environments specified
        if not test_envs:
            test_envs = {TestEnvironment.TEST}
        
        # Store metadata on function
        func._test_environments = test_envs
        func._env_kwargs = kwargs
        
        # Apply pytest marks
        for test_env in test_envs:
            func = pytest.mark.env(test_env.value)(func)
        
        # Preserve async nature of function
        if getattr(func, '__code__', None) and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            @functools.wraps(func)
            async def async_wrapper(*args, **wrapper_kwargs):
                current_env = TestEnvironment.get_current()
                
                # Check if test should run in current environment
                if current_env not in test_envs:
                    pytest.skip(f"Test not compatible with {current_env.value} environment. "
                              f"Compatible: {', '.join([e.value for e in test_envs])}")
                
                # Apply environment-specific constraints
                if current_env == TestEnvironment.PROD:
                    if not os.environ.get("ALLOW_PROD_TESTS"):
                        pytest.skip("Production tests require ALLOW_PROD_TESTS=true")
                    
                    # Apply rate limiting if specified
                    if rate_limit := kwargs.get("rate_limit"):
                        _apply_rate_limit(rate_limit)
                
                return await func(*args, **wrapper_kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **wrapper_kwargs):
                current_env = TestEnvironment.get_current()
                
                # Check if test should run in current environment
                if current_env not in test_envs:
                    pytest.skip(f"Test not compatible with {current_env.value} environment. "
                              f"Compatible: {', '.join([e.value for e in test_envs])}")
                
                # Apply environment-specific constraints
                if current_env == TestEnvironment.PROD:
                    if not os.environ.get("ALLOW_PROD_TESTS"):
                        pytest.skip("Production tests require ALLOW_PROD_TESTS=true")
                    
                    # Apply rate limiting if specified
                    if rate_limit := kwargs.get("rate_limit"):
                        _apply_rate_limit(rate_limit)
                
                return func(*args, **wrapper_kwargs)
            return wrapper
    
    return decorator


def env_requires(services: Optional[List[str]] = None,
                features: Optional[List[str]] = None,
                data: Optional[List[str]] = None):
    """Declare environment-specific requirements for a test.
    
    Args:
        services: Required services
        features: Required features
        data: Required test data
    
    Usage:
        @env("staging")
        @env_requires(
            services=["auth_service", "redis"],
            features=["oauth_configured"],
            data=["test_tenant"]
        )
        def test_oauth_flow():
            pass
    """
    def decorator(func: Callable) -> Callable:
        capability = EnvironmentCapability(services, features, data)
        func._env_capability = capability
        
        # Preserve async nature of function
        if getattr(func, '__code__', None) and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                current_env = TestEnvironment.get_current()
                is_satisfied, reason = capability.is_satisfied(current_env)
                
                if not is_satisfied:
                    pytest.skip(f"Environment requirements not met: {reason}")
                
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                current_env = TestEnvironment.get_current()
                is_satisfied, reason = capability.is_satisfied(current_env)
                
                if not is_satisfied:
                    pytest.skip(f"Environment requirements not met: {reason}")
                
                return func(*args, **kwargs)
            return wrapper
    
    return decorator


def env_safe(operations: Optional[List[str]] = None,
            impact: str = "unknown",
            rollback: bool = False):
    """Mark test as safe for higher environments with specific constraints.
    
    Args:
        operations: Allowed operations
        impact: Impact level
        rollback: Rollback capability
    
    Usage:
        @env("prod")
        @env_safe(
            operations=["read_only"],
            impact="none",
            rollback=True
        )
        def test_production_metrics():
            pass
    """
    def decorator(func: Callable) -> Callable:
        safety = EnvironmentSafety(
            operations=operations,
            impact=impact,
            rollback=rollback,
            readonly="read_only" in (operations or [])
        )
        func._env_safety = safety
        
        # Preserve async nature of function
        if getattr(func, '__code__', None) and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                current_env = TestEnvironment.get_current()
                is_safe, reason = safety.is_safe_for_environment(current_env)
                
                if not is_safe:
                    pytest.skip(f"Test not safe for {current_env.value}: {reason}")
                
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                current_env = TestEnvironment.get_current()
                is_safe, reason = safety.is_safe_for_environment(current_env)
                
                if not is_safe:
                    pytest.skip(f"Test not safe for {current_env.value}: {reason}")
                
                return func(*args, **kwargs)
            return wrapper
    
    return decorator


def get_test_environments(test_func: Callable) -> Set[TestEnvironment]:
    """Get the environments where a test can run.
    
    Args:
        test_func: Test function to inspect
    
    Returns:
        Set of compatible TestEnvironment values
    """
    if hasattr(test_func, "_test_environments"):
        return test_func._test_environments
    
    # Check for pytest marks
    if hasattr(test_func, "pytestmark"):
        envs = set()
        for mark in test_func.pytestmark:
            if mark.name == "env":
                for arg in mark.args:
                    envs.add(TestEnvironment.from_string(arg))
        if envs:
            return envs
    
    # Default to TEST environment
    return {TestEnvironment.TEST}


def filter_tests_by_environment(tests: List[Any], 
                               target_env: TestEnvironment) -> List[Any]:
    """Filter tests to only those compatible with target environment.
    
    Args:
        tests: List of test functions/methods
        target_env: Target environment to filter for
    
    Returns:
        Filtered list of tests
    """
    filtered = []
    for test in tests:
        test_envs = get_test_environments(test)
        if target_env in test_envs:
            filtered.append(test)
    
    return filtered


def get_environment_config(environment: TestEnvironment) -> Dict[str, Any]:
    """Get configuration for a specific environment.
    
    Args:
        environment: Target environment
    
    Returns:
        Environment-specific configuration
    """
    configs = {
        TestEnvironment.TEST: {
            "database_url": "postgresql://test:test@localhost:5432/test_db",
            "redis_url": "redis://localhost:6379/0",
            "use_mocks": True,
            "cleanup_strategy": "immediate"
        },
        TestEnvironment.DEV: {
            "database_url": os.environ.get("DEV_DATABASE_URL", "postgresql://dev:dev@localhost:5432/dev_db"),
            "redis_url": os.environ.get("DEV_REDIS_URL", "redis://localhost:6379/1"),
            "use_mocks": False,
            "cleanup_strategy": "daily"
        },
        TestEnvironment.STAGING: {
            "database_url": os.environ.get("STAGING_DATABASE_URL"),
            "redis_url": os.environ.get("STAGING_REDIS_URL"),
            "use_mocks": False,
            "cleanup_strategy": "weekly"
        },
        TestEnvironment.PROD: {
            "database_url": os.environ.get("PROD_DATABASE_URL"),
            "redis_url": os.environ.get("PROD_REDIS_URL"),
            "use_mocks": False,
            "cleanup_strategy": "manual_only",
            "readonly": True
        }
    }
    
    return configs.get(environment, configs[TestEnvironment.TEST])


# Helper functions (private)

def _is_service_available(service: str, environment: TestEnvironment) -> bool:
    """Check if a service is available in the environment."""
    # Production environment uses explicit service list
    if environment == TestEnvironment.PROD:
        return service in os.environ.get("PROD_AVAILABLE_SERVICES", "").split(",")
    
    # For other environments, actually check service availability
    if service == "postgres":
        return _check_postgres_available()
    elif service == "redis":
        return _check_redis_available()
    elif service == "auth_service":
        return _check_http_service_available("http://localhost:8001/health")
    elif service == "backend_service":
        return _check_http_service_available("http://localhost:8000/health")
    
    # Unknown service, assume available for test environments
    return True


def _check_postgres_available() -> bool:
    """Check if PostgreSQL is available."""
    import socket
    try:
        # Check common PostgreSQL ports
        for port in [5432, 5433]:
            sock = socket.create_connection(("localhost", port), timeout=2)
            sock.close()
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        pass
    return False


def _check_redis_available() -> bool:
    """Check if Redis is available."""
    import socket
    try:
        sock = socket.create_connection(("localhost", 6379), timeout=2)
        sock.close()
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def _check_http_service_available(url: str) -> bool:
    """Check if HTTP service is available."""
    try:
        import urllib.request
        urllib.request.urlopen(url, timeout=2)
        return True
    except Exception:
        return False


def _is_feature_enabled(feature: str, environment: TestEnvironment) -> bool:
    """Check if a feature is enabled in the environment."""
    # This would check feature flags
    # For now, return True for non-prod environments
    if environment == TestEnvironment.PROD:
        return feature in os.environ.get("PROD_ENABLED_FEATURES", "").split(",")
    return True


def _is_test_data_available(data: str, environment: TestEnvironment) -> bool:
    """Check if test data is available in the environment."""
    # This would check data availability
    # For now, return True for test/dev, False for prod
    return environment in [TestEnvironment.TEST, TestEnvironment.DEV, TestEnvironment.STAGING]


def _apply_rate_limit(limit: int):
    """Apply rate limiting to test execution."""
    import time
    time.sleep(1.0 / limit)  # Simple rate limiting


# Utility functions for skipif conditions

def is_environment(env_name: str) -> bool:
    """Check if current environment matches the given name.
    
    Args:
        env_name: Environment name to check (e.g., "staging", "dev", "test")
    
    Returns:
        True if current environment matches
    """
    try:
        current_env = TestEnvironment.get_current()
        return current_env.value == env_name.lower()
    except ValueError:
        return False


def requires_environment(env_name: str) -> bool:
    """Check if test should run in the given environment.
    
    Used in pytest.mark.skipif conditions.
    
    Args:
        env_name: Environment name required (e.g., "staging")
    
    Returns:
        True if test should run (environment matches)
    """
    return is_environment(env_name)


def skip_unless_environment(env_name: str) -> bool:
    """Check if test should be skipped unless in given environment.
    
    Used in pytest.mark.skipif conditions.
    
    Args:
        env_name: Environment name required
    
    Returns:
        True if test should be skipped (environment doesn't match)
    """
    return not is_environment(env_name)


# Convenience decorators for common patterns

test_only = env(TestEnvironment.TEST)
dev_only = env(TestEnvironment.DEV)
staging_only = env(TestEnvironment.STAGING)
prod_safe = env(TestEnvironment.PROD, readonly=True)

# Multi-environment patterns
dev_and_staging = env(TestEnvironment.DEV, TestEnvironment.STAGING)
non_prod = env(TestEnvironment.TEST, TestEnvironment.DEV, TestEnvironment.STAGING)
all_envs = env(TestEnvironment.TEST, TestEnvironment.DEV, TestEnvironment.STAGING, TestEnvironment.PROD)

# Service-specific decorators
requires_backend_service = env_requires(services=["backend_service"])
requires_auth_service = env_requires(services=["auth_service"])
requires_database = env_requires(services=["postgres"])
requires_redis = env_requires(services=["redis"])
