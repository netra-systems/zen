"""
Test Decorators for Netra Apex Test Framework

This module provides decorator functions that wrap pytest markers for test configuration.
These decorators enable tests to declare their service dependencies clearly and enable
automatic test collection and categorization.

Usage:
    @requires_real_database
    async def test_database_functionality():
        # Test code that needs real database
        pass
    
    @requires_real_redis  
    async def test_redis_functionality():
        # Test code that needs real Redis
        pass

Business Value:
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Test Configuration Clarity & Collection Success 
- Value Impact: Enables test discovery and execution validation
- Strategic Impact: Critical for test infrastructure reliability
"""

import functools
import logging
from typing import Callable, Any
import pytest

logger = logging.getLogger(__name__)


def requires_real_database(func: Callable) -> Callable:
    """Decorator to mark tests that require real database connections.
    
    This decorator applies the 'real_database' pytest marker and logs
    the requirement for test infrastructure planning.
    
    Args:
        func: Test function to decorate
        
    Returns:
        Decorated test function with real_database marker
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Apply pytest marker
    marked_func = pytest.mark.real_database(wrapper)
    
    # Add metadata for test discovery
    marked_func._requires_real_database = True
    marked_func._test_dependency = 'database'
    
    logger.debug(f"Test {func.__name__} marked as requiring real database")
    
    return marked_func


def requires_real_redis(func: Callable) -> Callable:
    """Decorator to mark tests that require real Redis connections.
    
    This decorator applies the 'real_redis' pytest marker and logs
    the requirement for test infrastructure planning.
    
    Args:
        func: Test function to decorate
        
    Returns:
        Decorated test function with real_redis marker
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Apply pytest marker
    marked_func = pytest.mark.real_redis(wrapper)
    
    # Add metadata for test discovery
    marked_func._requires_real_redis = True
    marked_func._test_dependency = 'redis'
    
    logger.debug(f"Test {func.__name__} marked as requiring real Redis")
    
    return marked_func


def requires_real_services(func: Callable) -> Callable:
    """Decorator to mark tests that require real external services.
    
    This decorator applies the 'real_services' pytest marker and logs
    the requirement for test infrastructure planning.
    
    Args:
        func: Test function to decorate
        
    Returns:
        Decorated test function with real_services marker
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Apply pytest marker
    marked_func = pytest.mark.real_services(wrapper)
    
    # Add metadata for test discovery
    marked_func._requires_real_services = True
    marked_func._test_dependency = 'external_services'
    
    logger.debug(f"Test {func.__name__} marked as requiring real services")
    
    return marked_func


def requires_docker(func: Callable) -> Callable:
    """Decorator to mark tests that require Docker services.
    
    This decorator applies the 'requires_docker' pytest marker and logs
    the requirement for test infrastructure planning.
    
    Args:
        func: Test function to decorate
        
    Returns:
        Decorated test function with requires_docker marker
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Apply pytest marker
    marked_func = pytest.mark.requires_docker(wrapper)
    
    # Add metadata for test discovery
    marked_func._requires_docker = True
    marked_func._test_dependency = 'docker'
    
    logger.debug(f"Test {func.__name__} marked as requiring Docker services")
    
    return marked_func


def requires_websocket(func: Callable) -> Callable:
    """Decorator to mark tests that require WebSocket connections.
    
    This decorator applies the 'requires_websocket' pytest marker and logs
    the requirement for test infrastructure planning.
    
    Args:
        func: Test function to decorate
        
    Returns:
        Decorated test function with requires_websocket marker
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Apply pytest marker
    marked_func = pytest.mark.requires_websocket(wrapper)
    
    # Add metadata for test discovery
    marked_func._requires_websocket = True
    marked_func._test_dependency = 'websocket'
    
    logger.debug(f"Test {func.__name__} marked as requiring WebSocket connections")
    
    return marked_func


def mission_critical(func: Callable) -> Callable:
    """Decorator to mark tests as mission critical.
    
    This decorator applies the 'mission_critical' pytest marker and logs
    the critical nature of the test for business continuity.
    
    Args:
        func: Test function to decorate
        
    Returns:
        Decorated test function with mission_critical marker
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Apply pytest marker
    marked_func = pytest.mark.mission_critical(wrapper)
    
    # Add metadata for test discovery
    marked_func._mission_critical = True
    marked_func._test_priority = 'critical'
    
    logger.debug(f"Test {func.__name__} marked as mission critical")
    
    return marked_func


def race_condition_test(func: Callable) -> Callable:
    """Decorator to mark tests that validate race conditions.
    
    This decorator applies the 'race_conditions' pytest marker and logs
    the race condition testing nature of the test.
    
    Args:
        func: Test function to decorate
        
    Returns:
        Decorated test function with race_conditions marker
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Apply pytest marker
    marked_func = pytest.mark.race_conditions(wrapper)
    
    # Add metadata for test discovery
    marked_func._race_condition_test = True
    marked_func._test_type = 'race_condition'
    
    logger.debug(f"Test {func.__name__} marked as race condition test")
    
    return marked_func


def experimental_test(description: str = None):
    """Decorator to mark tests as experimental.
    
    This decorator applies the 'experimental' pytest marker and logs
    the experimental nature of the test for test infrastructure planning.
    Experimental tests may be unstable or under development.
    
    Args:
        description: Optional description of the experimental test
        
    Returns:
        Decorator function or decorated test function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Apply pytest marker
        marker_args = {"description": description} if description else {}
        marked_func = pytest.mark.experimental(**marker_args)(wrapper)
        
        # Add metadata for test discovery
        marked_func._experimental_test = True
        marked_func._experimental_description = description
        marked_func._test_type = 'experimental'
        
        desc_str = f" ({description})" if description else ""
        logger.debug(f"Test {func.__name__} marked as experimental test{desc_str}")
        
        return marked_func
    
    # If called without parentheses (as @experimental_test)
    if callable(description):
        func = description
        description = None
        return decorator(func)
    
    # If called with parentheses (as @experimental_test("description"))
    return decorator


def feature_flag(flag_name: str, enabled: bool = True):
    """Decorator to mark tests that depend on feature flags.
    
    This decorator applies the 'feature_flag' pytest marker and allows
    conditional test execution based on feature flag state.
    
    Args:
        flag_name: Name of the feature flag
        enabled: Whether the test should run when flag is enabled (default True)
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Apply pytest marker with flag information
        marked_func = pytest.mark.feature_flag(flag_name=flag_name, enabled=enabled)(wrapper)
        
        # Add metadata for test discovery
        marked_func._feature_flag = flag_name
        marked_func._feature_flag_enabled = enabled
        marked_func._test_type = 'feature_flag'
        
        logger.debug(f"Test {func.__name__} marked with feature flag: {flag_name} (enabled: {enabled})")
        
        return marked_func
    
    return decorator


def requires_feature(*feature_names: str):
    """Decorator to mark tests that require specific features to be enabled.
    
    This decorator applies the 'requires_feature' pytest marker and allows
    conditional test execution based on feature availability.
    
    Args:
        *feature_names: Names of the features required for the test
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Apply pytest marker with feature information
        marked_func = pytest.mark.requires_feature(feature_names=list(feature_names))(wrapper)
        
        # Add metadata for test discovery
        marked_func._requires_feature = list(feature_names)
        marked_func._test_type = 'feature_dependent'
        
        logger.debug(f"Test {func.__name__} marked as requiring features: {', '.join(feature_names)}")
        
        return marked_func
    
    return decorator


def tdd_test(func: Callable) -> Callable:
    """Decorator to mark tests as part of TDD (Test-Driven Development) workflow.
    
    This decorator applies the 'tdd' pytest marker and identifies tests
    written as part of test-driven development process.
    
    Args:
        func: Test function to decorate
        
    Returns:
        Decorated test function with tdd marker
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Apply pytest marker
    marked_func = pytest.mark.tdd(wrapper)
    
    # Add metadata for test discovery
    marked_func._tdd_test = True
    marked_func._test_type = 'tdd'
    
    logger.debug(f"Test {func.__name__} marked as TDD test")
    
    return marked_func


# Export all decorators for easy importing
__all__ = [
    'requires_real_database',
    'requires_real_redis', 
    'requires_real_services',
    'requires_docker',
    'requires_websocket',
    'mission_critical',
    'race_condition_test',
    'experimental_test',
    'feature_flag',
    'requires_feature',
    'tdd_test'
]