"""
Test Environment Isolation Helper

Provides utilities for proper test environment isolation using IsolatedEnvironment.
This replaces direct os.environ patches to prevent test pollution.
"""

from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager
import unittest
from unittest.mock import patch
from shared.isolated_environment import IsolatedEnvironment


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
