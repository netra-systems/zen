"""
Test Environment Isolation Helper

Provides utilities for proper test environment isolation using IsolatedEnvironment.
This replaces direct os.environ patches to prevent test pollution.

Business Value: Platform/Internal - Test Stability & Environment Isolation
Prevents test pollution and configuration leakage between test runs that can cause
cascade failures and flaky tests.
"""

from typing import Dict, Any, Optional, Callable, List
from contextlib import contextmanager
import unittest
import uuid
import logging
from unittest.mock import patch
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.models.user_execution_context import UserExecutionContext

logger = logging.getLogger(__name__)


class IsolatedTestCase(unittest.TestCase):
    """
    Base test case with automatic environment isolation.
    """
    
    def setUp(self):
        """Set up isolated environment for each test."""
        super().setUp()
        self.env = IsolatedEnvironment()
        self.env.enable_isolation_mode()
        self.addCleanup(self.env.reset)
    
    def set_env(self, key: str, value: str) -> None:
        """
        Set an environment variable in the isolated environment.
        
        Args:
            key: Environment variable name
            value: Environment variable value
        """
        self.env.set(key, value)
    
    def set_env_batch(self, env_vars: Dict[str, str]) -> None:
        """
        Set multiple environment variables at once.
        
        Args:
            env_vars: Dictionary of environment variables
        """
        for key, value in env_vars.items():
            self.env.set(key, value)


@contextmanager
def isolated_env(**env_vars):
    """
    Context manager for temporary environment isolation.
    
    Usage:
        with isolated_env(ENVIRONMENT='staging', DEBUG='true'):
            # test code runs with isolated environment
            pass
    """
    env = IsolatedEnvironment()
    env.enable_isolation_mode()
    
    for key, value in env_vars.items():
        env.set(key, value)
    
    try:
        yield env
    finally:
        env.reset()


def patch_env(target: str, **env_vars) -> Callable:
    """
    Decorator for patching environment variables in tests.
    
    Usage:
        @patch_env('netra_backend.app.core.config', ENVIRONMENT='staging')
        def test_something(self):
            # test code
            pass
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with isolated_env(**env_vars):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def create_isolated_user_context(
    user_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    run_id: Optional[str] = None,
    request_id: Optional[str] = None,
    websocket_client_id: Optional[str] = None
) -> UserExecutionContext:
    """
    Create an isolated UserExecutionContext for testing.
    
    This is the SSOT function for creating test UserExecutionContext instances.
    It generates unique values for any fields not provided to ensure proper isolation.
    
    Args:
        user_id: Unique identifier for the user (auto-generated if None)
        thread_id: Unique identifier for the conversation thread (auto-generated if None)
        run_id: Unique identifier for the execution run (auto-generated if None)
        request_id: Unique identifier for the request (auto-generated if None)
        websocket_client_id: Optional WebSocket client identifier
        
    Returns:
        UserExecutionContext: Properly configured context with all required fields
        
    Example:
        >>> context = create_isolated_user_context(user_id="test_user_123")
        >>> assert context.user_id == "test_user_123"
        >>> assert len(context.thread_id) > 0
        >>> assert len(context.run_id) > 0
        >>> assert len(context.request_id) > 0
    """
    # Generate unique values for any missing fields
    if user_id is None:
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    if thread_id is None:
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
    
    if run_id is None:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
    
    if request_id is None:
        request_id = f"req_{uuid.uuid4().hex[:8]}"
    
    # Create and return UserExecutionContext with validation
    return UserExecutionContext(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        request_id=request_id,
        websocket_client_id=websocket_client_id
    )


# MIGRATION GUIDE:
# 
# 1. Replace unittest.TestCase with IsolatedTestCase:
#    class TestMyFeature(IsolatedTestCase):
#        def test_something(self):
#            self.set_env('KEY', 'value')
#
# 2. Replace patch.dict(os.environ) with isolated_env():
#    with isolated_env(KEY='value'):
#        # test code
#
# 3. Use decorator for method-level isolation:
#    @patch_env('module.path', KEY='value')
#    def test_something(self):
#        # test code
#
# 4. Create isolated user context for testing:
#    from test_framework.ssot.isolated_test_helper import create_isolated_user_context
#    context = create_isolated_user_context(user_id="test_user")


class IsolatedTestHelper:
    """
    Advanced helper for managing isolated test environments with context management.
    
    This class provides comprehensive environment isolation for complex integration tests
    where multiple isolated contexts may be needed.
    """
    
    def __init__(self):
        self._active_contexts: List['IsolatedContext'] = []
    
    @contextmanager
    def create_isolated_context(self, context_name: str = None):
        """
        Create an isolated environment context for testing.
        
        Args:
            context_name: Optional name for the context (for debugging)
            
        Returns:
            IsolatedContext: Context manager with isolated environment
        """
        context_name = context_name or f"test_context_{uuid.uuid4().hex[:8]}"
        context = IsolatedContext(context_name)
        self._active_contexts.append(context)
        
        try:
            yield context
        finally:
            if context in self._active_contexts:
                self._active_contexts.remove(context)
            context.cleanup()
    
    def cleanup_all(self):
        """Clean up all active contexts."""
        for context in self._active_contexts[:]:  # Copy list to avoid modification during iteration
            context.cleanup()
            if context in self._active_contexts:
                self._active_contexts.remove(context)


class IsolatedContext:
    """
    Represents a single isolated environment context for testing.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.env = IsolatedEnvironment()
        self.env.enable_isolation_mode()
        logger.debug(f"Created isolated context: {name}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def cleanup(self):
        """Clean up the isolated environment."""
        try:
            self.env.reset()
            logger.debug(f"Cleaned up isolated context: {self.name}")
        except Exception as e:
            logger.warning(f"Error cleaning up isolated context {self.name}: {e}")


__all__ = [
    "IsolatedTestCase",
    "IsolatedTestHelper", 
    "IsolatedContext",
    "isolated_env", 
    "patch_env",
    "create_isolated_user_context"
]
