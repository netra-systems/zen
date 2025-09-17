"""
SSOT Test Decorators Module

This module provides Single Source of Truth (SSOT) decorators for test infrastructure.
All test decorators should be imported from this module to maintain consistency
and prevent duplication across the test suite.

Business Value: Platform/Internal - Test Infrastructure Reliability & Development Velocity
Provides consistent test behavior, proper service dependency management, and graceful degradation.

Key Features:
- Service availability decorators
- Environment-aware skipping
- Graceful degradation for missing dependencies
- SSOT compliance for test infrastructure patterns
"""

import functools
import logging
import os
import pytest
from typing import Callable, List, Optional, Union

# Import SSOT orchestration for service availability checks
from test_framework.ssot.orchestration import (
    get_orchestration_config, 
    check_service_available, 
    is_no_services_mode
)

logger = logging.getLogger(__name__)


def skip_if_no_services(reason: str = "Test requires external services") -> Callable:
    """
    Skip test if running in no-services mode.
    
    This decorator automatically skips tests that require external service
    dependencies when TEST_NO_SERVICES environment variable is set.
    
    Args:
        reason: Reason for skipping the test
        
    Returns:
        Test decorator function
        
    Example:
        @skip_if_no_services("Test requires database connection")
        def test_database_integration():
            # Test that needs database
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if is_no_services_mode():
                pytest.skip(f"Skipped in no-services mode: {reason}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def skip_if_service_unavailable(
    service_name: str, 
    host: str = "localhost", 
    port: Optional[int] = None,
    timeout: float = 2.0,
    reason: Optional[str] = None
) -> Callable:
    """
    Skip test if specific service is unavailable.
    
    This decorator checks if a service is responding before running the test.
    If the service is unavailable, the test is skipped with a descriptive message.
    
    Args:
        service_name: Name of the service to check
        host: Service host (default: localhost)
        port: Service port (required)
        timeout: Connection timeout in seconds
        reason: Custom reason for skipping (auto-generated if None)
        
    Returns:
        Test decorator function
        
    Example:
        @skip_if_service_unavailable("redis", port=6379)
        def test_redis_functionality():
            # Test that needs Redis
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Always skip in no-services mode
            if is_no_services_mode():
                pytest.skip(f"Skipped in no-services mode: {service_name} not available")
                
            # Check service availability
            if not check_service_available(service_name, host, port, timeout):
                skip_reason = reason or f"Service {service_name} unavailable at {host}:{port}"
                pytest.skip(skip_reason)
                
            return func(*args, **kwargs)
        return wrapper
    return decorator


def skip_if_docker_unavailable(reason: str = "Test requires Docker") -> Callable:
    """
    Skip test if Docker is unavailable.
    
    This decorator automatically skips tests that require Docker when Docker
    is not available or when running in no-services mode.
    
    Args:
        reason: Reason for skipping the test
        
    Returns:
        Test decorator function
        
    Example:
        @skip_if_docker_unavailable("Test requires Docker containers")
        def test_docker_integration():
            # Test that needs Docker
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            config = get_orchestration_config()
            
            if is_no_services_mode() or not config.docker_available:
                pytest.skip(f"Skipped: {reason} (Docker unavailable or no-services mode)")
                
            return func(*args, **kwargs)
        return wrapper
    return decorator


def skip_if_orchestration_unavailable(
    features: Union[str, List[str]], 
    reason: Optional[str] = None
) -> Callable:
    """
    Skip test if specific orchestration features are unavailable.
    
    This decorator checks for availability of orchestration components like
    TestOrchestratorAgent, MasterOrchestrationController, etc.
    
    Args:
        features: Single feature name or list of required features
        reason: Custom reason for skipping (auto-generated if None)
        
    Returns:
        Test decorator function
        
    Example:
        @skip_if_orchestration_unavailable("orchestrator")
        def test_orchestrator_functionality():
            # Test that needs TestOrchestratorAgent
            pass
            
        @skip_if_orchestration_unavailable(["orchestrator", "master_orchestration"])
        def test_full_orchestration():
            # Test that needs multiple orchestration components
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            config = get_orchestration_config()
            
            # Always skip in no-services mode
            if is_no_services_mode():
                pytest.skip("Skipped in no-services mode: orchestration unavailable")
            
            # Normalize to list
            required_features = features if isinstance(features, list) else [features]
            
            # Check each required feature
            unavailable_features = []
            for feature in required_features:
                if feature == "orchestrator" and not config.orchestrator_available:
                    unavailable_features.append("orchestrator")
                elif feature == "master_orchestration" and not config.master_orchestration_available:
                    unavailable_features.append("master_orchestration")
                elif feature == "background_e2e" and not config.background_e2e_available:
                    unavailable_features.append("background_e2e")
                elif feature == "docker" and not config.docker_available:
                    unavailable_features.append("docker")
            
            if unavailable_features:
                skip_reason = reason or f"Orchestration features unavailable: {unavailable_features}"
                pytest.skip(skip_reason)
                
            return func(*args, **kwargs)
        return wrapper
    return decorator


def requires_environment(env_vars: Union[str, List[str]], reason: Optional[str] = None) -> Callable:
    """
    Skip test if required environment variables are not set.
    
    This decorator ensures tests only run when required environment
    configuration is available.
    
    Args:
        env_vars: Single environment variable name or list of required variables
        reason: Custom reason for skipping (auto-generated if None)
        
    Returns:
        Test decorator function
        
    Example:
        @requires_environment("DATABASE_URL")
        def test_database_connection():
            # Test that needs DATABASE_URL
            pass
            
        @requires_environment(["REDIS_URL", "POSTGRES_URL"])
        def test_multi_service_integration():
            # Test that needs multiple services
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Normalize to list
            required_vars = env_vars if isinstance(env_vars, list) else [env_vars]
            
            # Check each required variable
            missing_vars = []
            for var in required_vars:
                if not os.environ.get(var):
                    missing_vars.append(var)
            
            if missing_vars:
                skip_reason = reason or f"Required environment variables not set: {missing_vars}"
                pytest.skip(skip_reason)
                
            return func(*args, **kwargs)
        return wrapper
    return decorator


def skip_on_windows(reason: str = "Test not supported on Windows") -> Callable:
    """
    Skip test on Windows platforms.
    
    Args:
        reason: Reason for skipping the test
        
    Returns:
        Test decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if os.name == 'nt':
                pytest.skip(f"Skipped on Windows: {reason}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def skip_on_macos(reason: str = "Test not supported on macOS") -> Callable:
    """
    Skip test on macOS platforms.
    
    Args:
        reason: Reason for skipping the test
        
    Returns:
        Test decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import platform
            if platform.system() == 'Darwin':
                pytest.skip(f"Skipped on macOS: {reason}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Export all SSOT decorators
__all__ = [
    'skip_if_no_services',
    'skip_if_service_unavailable', 
    'skip_if_docker_unavailable',
    'skip_if_orchestration_unavailable',
    'requires_environment',
    'skip_on_windows',
    'skip_on_macos'
]