"""
SSOT Test-Only Guard System - Enforces test-mode-only execution for mock/test functions.

This module provides a decorator system that ensures certain functions (like mock creators)
can ONLY be executed when the system is in test mode. This enforces SSOT principles by:
- Preventing accidental mock usage in production
- Ensuring test isolation is maintained
- Providing clear runtime errors for misuse

Business Value: Platform/Internal - System Stability & Test Isolation
Prevents production code from accidentally using test/mock implementations.
"""

import os
import sys
import functools
import logging
from typing import Callable, TypeVar, Optional, Any

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class TestModeViolation(Exception):
    """Exception raised when test-only function is called outside test mode."""
    
    __test__ = False  # Tell pytest this is not a test class
    def __init__(self, function_name: str, reason: str, suggestion: str = "Ensure TESTING=true or use unified_test_runner.py"):
        self.function_name = function_name
        self.reason = reason
        self.suggestion = suggestion
        super().__init__(self.__str__())
    
    def __str__(self) -> str:
        return (
            f"SSOT VIOLATION: Function '{self.function_name}' is test-only but called in non-test mode.\n"
            f"Reason: {self.reason}\n"
            f"Suggestion: {self.suggestion}"
        )


class TestModeDetector:
    """Centralized test mode detection following SSOT principles."""
    
    _cached_test_mode: Optional[bool] = None
    
    @classmethod
    def is_test_mode(cls) -> bool:
        """
        Detect if we're running in test mode using multiple indicators.
        
        This follows the same logic as IsolatedEnvironment._is_test_context() but
        is designed for SSOT guard usage without circular dependencies.
        
        Returns:
            bool: True if in test mode, False otherwise
        """
        # Use cached result for performance
        if cls._cached_test_mode is not None:
            return cls._cached_test_mode
        
        # Check pytest active execution
        if 'pytest' in sys.modules and hasattr(sys.modules['pytest'], 'main'):
            if hasattr(sys, '_pytest_running') or os.environ.get('PYTEST_CURRENT_TEST'):
                cls._cached_test_mode = True
                return True
        
        # Check test environment variables
        test_indicators = [
            'PYTEST_CURRENT_TEST',
            'TESTING', 
            'TEST_MODE'
        ]
        
        for indicator in test_indicators:
            value = os.environ.get(indicator, '').lower()
            if value in ['true', '1', 'yes', 'on']:
                cls._cached_test_mode = True
                return True
        
        # Check if ENVIRONMENT is set to testing
        env_value = os.environ.get('ENVIRONMENT', '').lower()
        if env_value in ['test', 'testing']:
            cls._cached_test_mode = True
            return True
        
        # Check if we're running via unified_test_runner
        # This checks for the test runner's process name patterns
        import psutil
        try:
            current_process = psutil.Process()
            cmdline = ' '.join(current_process.cmdline())
            if 'unified_test_runner.py' in cmdline or 'pytest' in cmdline:
                cls._cached_test_mode = True
                return True
        except Exception:
            # If psutil fails, continue with other checks
            pass
        
        # If none of the test indicators are present, we're NOT in test mode
        cls._cached_test_mode = False
        return False
    
    @classmethod
    def reset_cache(cls) -> None:
        """Reset cached test mode detection (useful for testing the detector itself)."""
        cls._cached_test_mode = None


def test_only(reason: Optional[str] = None, allow_override: bool = False) -> Callable[[F], F]:
    """
    Decorator that enforces test-mode-only execution for functions.
    
    This SSOT guard ensures that functions marked with @test_only can ONLY
    be executed when the system detects it's running in test mode.
    
    Args:
        reason: Optional custom reason for test-only restriction
        allow_override: If True, allows ENV variable FORCE_TEST_ONLY_OVERRIDE=true to bypass
        
    Returns:
        Decorated function that validates test mode before execution
        
    Example:
        ```python
        @test_only("Mock creation should only happen in tests")
        def _create_mock_tool_dispatcher(self):
            # This function can only run in test mode
            return MockToolDispatcher()
        ```
        
    Raises:
        TestModeViolation: If called outside test mode
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check for override (dangerous but useful for debugging)
            if allow_override and os.environ.get('FORCE_TEST_ONLY_OVERRIDE', '').lower() == 'true':
                logger.warning(
                    f" WARNING: [U+FE0F]  DANGEROUS: test_only override active for {func.__name__}. "
                    f"This should NEVER happen in production!"
                )
                return func(*args, **kwargs)
            
            # Verify we're in test mode
            if not TestModeDetector.is_test_mode():
                violation_reason = reason or f"Function {func.__name__} contains test/mock code"
                raise TestModeViolation(
                    function_name=func.__name__,
                    reason=violation_reason,
                    suggestion="Set TESTING=true environment variable or run via unified_test_runner.py"
                )
            
            logger.debug(f" PASS:  Test-only function {func.__name__} called in valid test mode")
            return func(*args, **kwargs)
        
        # Add metadata to the wrapped function for introspection
        wrapper._is_test_only = True
        wrapper._test_only_reason = reason
        wrapper._original_func = func
        
        return wrapper
    
    return decorator


def require_test_mode(func_name: str, custom_message: Optional[str] = None) -> None:
    """
    Standalone function to check test mode and raise violation if not in test mode.
    
    Useful for adding guards to existing functions without decorating them.
    
    Args:
        func_name: Name of the function being protected
        custom_message: Optional custom violation message
        
    Raises:
        TestModeViolation: If not in test mode
    """
    if not TestModeDetector.is_test_mode():
        reason = custom_message or f"Function {func_name} requires test mode"
        raise TestModeViolation(
            function_name=func_name,
            reason=reason
        )


def is_test_only_function(func: Callable) -> bool:
    """
    Check if a function is decorated with @test_only.
    
    Args:
        func: Function to check
        
    Returns:
        bool: True if function is test-only, False otherwise
    """
    return getattr(func, '_is_test_only', False)


def get_test_only_reason(func: Callable) -> Optional[str]:
    """
    Get the reason why a function is test-only.
    
    Args:
        func: Function to check
        
    Returns:
        Optional reason string, None if not test-only
    """
    return getattr(func, '_test_only_reason', None)


# Export public interfaces
__all__ = [
    'test_only',
    'require_test_mode', 
    'TestModeViolation',
    'TestModeDetector',
    'is_test_only_function',
    'get_test_only_reason'
]