"""Test decorators for feature flags and conditional testing.

This module provides decorators for managing test execution based on feature flags,
enabling TDD workflows and ensuring 100% pass rates for enabled features.
"""

import os
import pytest
import functools
from typing import Optional, Callable, Any, Union
from .feature_flags import (
    get_feature_flag_manager, 
    is_feature_enabled, 
    should_skip_feature,
    FeatureStatus
)


def feature_flag(feature_name: str, *, reason: Optional[str] = None):
    """Decorator to skip tests based on feature flags.
    
    This decorator enables TDD by allowing tests to be written for features
    that are not yet complete, while maintaining 100% pass rate for CI/CD.
    
    Args:
        feature_name: Name of the feature flag
        reason: Optional custom skip reason
        
    Usage:
        @feature_flag("new_authentication")
        def test_new_auth_flow():
            # Test for feature in development
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_feature_flag_manager()
            
            if manager.should_skip(feature_name):
                skip_reason = reason or manager.get_skip_reason(feature_name)
                pytest.skip(skip_reason)
            
            return func(*args, **kwargs)
        
        # Mark the test with feature metadata
        wrapper._feature_flag = feature_name
        return wrapper
    
    return decorator


def requires_feature(*features: str):
    """Decorator to require one or more features to be enabled.
    
    Tests decorated with this will only run if ALL specified features are enabled.
    
    Args:
        *features: Feature names that must be enabled
        
    Usage:
        @requires_feature("feature_a", "feature_b")
        def test_integrated_features():
            # Test requiring multiple features
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_feature_flag_manager()
            disabled_features = [f for f in features if not manager.is_enabled(f)]
            
            if disabled_features:
                skip_reason = f"Required features not enabled: {', '.join(disabled_features)}"
                pytest.skip(skip_reason)
            
            return func(*args, **kwargs)
        
        wrapper._required_features = features
        return wrapper
    
    return decorator


def experimental_test(reason: Optional[str] = None):
    """Decorator for experimental tests that may be unstable.
    
    These tests run only when ENABLE_EXPERIMENTAL_TESTS=true or when
    the specific feature is marked as experimental and opted into.
    
    Args:
        reason: Optional description of why test is experimental
        
    Usage:
        @experimental_test("Testing new ML model integration")
        def test_ml_model_prediction():
            # Experimental test
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check global experimental flag
            if not os.environ.get("ENABLE_EXPERIMENTAL_TESTS", "").lower() == "true":
                skip_reason = reason or "Experimental tests disabled"
                pytest.skip(skip_reason)
            
            return func(*args, **kwargs)
        
        wrapper._experimental = True
        wrapper._experimental_reason = reason
        return wrapper
    
    return decorator


def tdd_test(feature_name: str, expected_to_fail: bool = True):
    """Decorator for TDD tests that are expected to fail initially.
    
    This decorator helps with Test-Driven Development by marking tests
    that should fail until the feature is implemented.
    
    Args:
        feature_name: Name of the feature being developed
        expected_to_fail: Whether test is expected to fail
        
    Usage:
        @tdd_test("user_profile_api")
        def test_user_can_update_profile():
            # Test written before implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        manager = get_feature_flag_manager()
        
        # If feature is in development and expected to fail, mark with xfail
        if expected_to_fail and feature_name in manager.flags:
            flag = manager.flags[feature_name]
            if flag.status == FeatureStatus.IN_DEVELOPMENT:
                return pytest.mark.xfail(
                    reason=f"TDD: Feature '{feature_name}' in development",
                    strict=False  # Don't fail if test unexpectedly passes
                )(func)
        
        # Otherwise, apply normal feature flag logic
        return feature_flag(feature_name)(func)
    
    return decorator


def performance_test(threshold_ms: float = 1000):
    """Decorator for performance-sensitive tests.
    
    These tests are skipped in fast mode unless ENABLE_PERFORMANCE_TESTS=true.
    
    Args:
        threshold_ms: Performance threshold in milliseconds
        
    Usage:
        @performance_test(threshold_ms=500)
        def test_api_response_time():
            # Test that checks performance
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Skip in fast mode unless explicitly enabled
            if os.environ.get("FAST_MODE") == "true" and \
               not os.environ.get("ENABLE_PERFORMANCE_TESTS") == "true":
                pytest.skip("Performance tests disabled in fast mode")
            
            import time
            start = time.time()
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000
            
            if duration_ms > threshold_ms:
                pytest.fail(f"Performance threshold exceeded: {duration_ms:.2f}ms > {threshold_ms}ms")
            
            return result
        
        wrapper._performance_test = True
        wrapper._threshold_ms = threshold_ms
        return wrapper
    
    return decorator


def integration_only():
    """Decorator for tests that should only run during integration testing.
    
    Usage:
        @integration_only()
        def test_database_transaction():
            # Integration test
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if os.environ.get("TEST_LEVEL") not in ["integration", "comprehensive", "all"]:
                pytest.skip("Integration tests only")
            return func(*args, **kwargs)
        
        wrapper._integration_only = True
        return wrapper
    
    return decorator


def unit_only():
    """Decorator for tests that should only run during unit testing.
    
    Usage:
        @unit_only()
        def test_utility_function():
            # Unit test
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if os.environ.get("TEST_LEVEL") not in ["unit", "comprehensive", "all"]:
                pytest.skip("Unit tests only")
            return func(*args, **kwargs)
        
        wrapper._unit_only = True
        return wrapper
    
    return decorator


def requires_env(*env_vars: str):
    """Decorator to skip tests if required environment variables are not set.
    
    Args:
        *env_vars: Environment variable names that must be set
        
    Usage:
        @requires_env("DATABASE_URL", "REDIS_URL")
        def test_with_external_services():
            # Test requiring external services
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            missing_vars = [var for var in env_vars if not os.environ.get(var)]
            
            if missing_vars:
                pytest.skip(f"Required environment variables not set: {', '.join(missing_vars)}")
            
            return func(*args, **kwargs)
        
        wrapper._required_env_vars = env_vars
        return wrapper
    
    return decorator


def flaky_test(max_retries: int = 3, reason: Optional[str] = None):
    """Decorator for tests that may fail intermittently.
    
    These tests will be retried up to max_retries times before failing.
    
    Args:
        max_retries: Maximum number of retry attempts
        reason: Optional description of why test is flaky
        
    Usage:
        @flaky_test(max_retries=3, reason="Network dependency")
        def test_external_api_call():
            # Test that may fail due to network issues
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(0.5 * (attempt + 1))  # Exponential backoff
            
            # All retries failed
            if last_exception:
                raise last_exception
        
        wrapper._flaky = True
        wrapper._max_retries = max_retries
        wrapper._flaky_reason = reason
        return wrapper
    
    return decorator


# Conditional skip decorators based on common conditions
skip_if_ci = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Skipped in CI environment"
)

skip_unless_ci = pytest.mark.skipif(
    os.environ.get("CI") != "true",
    reason="Only runs in CI environment"
)

skip_if_fast_mode = pytest.mark.skipif(
    os.environ.get("FAST_MODE") == "true",
    reason="Skipped in fast mode"
)

skip_if_no_redis = pytest.mark.skipif(
    os.environ.get("TEST_DISABLE_REDIS") == "true",
    reason="Redis disabled for testing"
)

skip_if_no_database = pytest.mark.skipif(
    os.environ.get("TEST_DISABLE_DATABASE") == "true",
    reason="Database disabled for testing"
)