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


# Export all decorators for easy importing
__all__ = [
    'requires_real_database',
    'requires_real_redis', 
    'requires_real_services',
    'requires_docker',
    'requires_websocket',
    'mission_critical',
    'race_condition_test'
]