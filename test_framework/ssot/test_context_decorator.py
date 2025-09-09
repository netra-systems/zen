"""
SSOT Test Context Decorator - Ensures Test-Only Code Compliance

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability and Test Isolation
- Value Impact: Prevents test code contamination in production
- Revenue Impact: Avoids CASCADE FAILURES from test infrastructure leakage (+$50K prevented outages)

CRITICAL: This decorator enforces that test-only code can ONLY be called from test contexts.
Violating this principle = ABOMINATION per CLAUDE.md Section 0.
"""

import functools
import inspect
import sys
from typing import Any, Callable, Optional, Type, Union
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger as logger


class ContextValidationError(Exception):
    """Raised when test-only code is called from non-test context."""
    pass


class TestContextValidator:
    """
    SSOT Test Context Validation - Prevents production contamination.
    
    CRITICAL PRINCIPLES:
    1. Test-only code MUST only execute in test contexts
    2. Production code MUST NEVER call test utilities
    3. Context detection MUST be reliable and fail-safe
    4. Violations MUST cause LOUD failures, not silent degradation
    """
    
    @staticmethod
    def is_test_environment() -> bool:
        """
        Comprehensive test environment detection.
        
        Returns True if we're in ANY kind of test context.
        Uses multiple detection methods for reliability.
        """
        env = get_env()
        
        # Method 1: Check TESTING environment variable (pytest compatibility)
        if env.get("TESTING", "").lower() == "true":
            logger.debug("[TestContext] Detected via TESTING=true")
            return True
            
        # Method 2: Check if pytest is in sys.modules
        if 'pytest' in sys.modules:
            logger.debug("[TestContext] Detected via pytest in sys.modules")
            return True
            
        # Method 3: Check PYTEST_CURRENT_TEST environment variable
        if env.get("PYTEST_CURRENT_TEST"):
            logger.debug("[TestContext] Detected via PYTEST_CURRENT_TEST")
            return True
            
        # Method 4: Check if unittest is running
        if 'unittest' in sys.modules:
            # Look for unittest runner in the stack
            frame = inspect.currentframe()
            while frame:
                filename = frame.f_code.co_filename
                if 'unittest' in filename and 'runner' in filename:
                    logger.debug("[TestContext] Detected via unittest runner")
                    return True
                frame = frame.f_back
                
        # Method 5: Check configuration environment
        try:
            from netra_backend.app.core.configuration import get_configuration
            config = get_configuration()
            if config.environment == "testing":
                logger.debug("[TestContext] Detected via configuration.environment=testing")
                return True
        except Exception:
            # Configuration not available, continue with other checks
            pass
            
        # Method 6: Check for test-specific environment variables
        test_env_vars = [
            "PYTEST_RUNNING",
            "TEST_MODE",
            "UNIT_TEST_MODE", 
            "INTEGRATION_TEST_MODE",
            "E2E_TEST_MODE"
        ]
        
        for var in test_env_vars:
            if env.get(var, "").lower() == "true":
                logger.debug(f"[TestContext] Detected via {var}=true")
                return True
                
        logger.debug("[TestContext] No test context detected")
        return False
    
    @staticmethod
    def is_test_file() -> bool:
        """
        Check if the calling code is from a test file.
        
        Inspects the call stack to find test file patterns.
        """
        frame = inspect.currentframe()
        
        try:
            # Walk up the stack looking for test files
            while frame:
                filename = frame.f_code.co_filename
                
                # Common test file patterns
                if any(pattern in filename.lower() for pattern in [
                    '/test_', '\\test_',  # test_something.py
                    '/tests/', '\\tests\\',  # files in tests/ directories
                    'test.py',  # files ending with test.py
                    'conftest.py',  # pytest configuration files
                    '_test.py'  # files ending with _test.py
                ]):
                    logger.debug(f"[TestContext] Test file detected: {filename}")
                    return True
                    
                frame = frame.f_back
                
        finally:
            # Clean up frame references to prevent memory leaks
            del frame
            
        return False
    
    @staticmethod
    def is_pytest_running() -> bool:
        """Check if pytest is currently running."""
        return 'pytest' in sys.modules and get_env().get("PYTEST_CURRENT_TEST") is not None
    
    @staticmethod
    def get_test_context_info() -> dict:
        """
        Get detailed information about the current test context.
        
        Returns comprehensive context information for debugging.
        """
        env = get_env()
        
        context_info = {
            "is_test_environment": TestContextValidator.is_test_environment(),
            "is_test_file": TestContextValidator.is_test_file(),
            "is_pytest_running": TestContextValidator.is_pytest_running(),
            "environment_vars": {
                "TESTING": env.get("TESTING"),
                "PYTEST_CURRENT_TEST": env.get("PYTEST_CURRENT_TEST"),
                "ENVIRONMENT": env.get("ENVIRONMENT")
            },
            "modules_loaded": {
                "pytest": 'pytest' in sys.modules,
                "unittest": 'unittest' in sys.modules
            }
        }
        
        # Get current test name if available
        current_test = env.get("PYTEST_CURRENT_TEST")
        if current_test:
            context_info["current_test"] = current_test.split("::")[-1] if "::" in current_test else current_test
            
        return context_info
    
    @staticmethod
    def validate_test_context(function_name: str, strict_mode: bool = True) -> None:
        """
        Validate that we're in a valid test context.
        
        Args:
            function_name: Name of the function being validated
            strict_mode: If True, requires both environment and file checks to pass
        
        Raises:
            ContextValidationError: If not in valid test context
        """
        is_test_env = TestContextValidator.is_test_environment()
        is_test_file = TestContextValidator.is_test_file()
        
        if strict_mode:
            # Strict mode requires BOTH environment and file checks
            if not (is_test_env and is_test_file):
                context_info = TestContextValidator.get_test_context_info()
                
                logger.error("=" * 80)
                logger.error("TEST CONTEXT VALIDATION FAILURE - ABOMINATION DETECTED")
                logger.error("=" * 80)
                logger.error(f"Function: {function_name}")
                logger.error(f"Test Environment: {is_test_env}")
                logger.error(f"Test File: {is_test_file}")
                logger.error(f"Context Info: {context_info}")
                logger.error("=" * 80)
                logger.error("CRITICAL: Test-only code called from production context!")
                logger.error("This violates CLAUDE.md test isolation principles.")
                logger.error("ACTION REQUIRED: Fix calling code or remove @test_decorator")
                logger.error("=" * 80)
                
                raise ContextValidationError(
                    f"Test-only function '{function_name}' called from non-test context. "
                    f"Test environment: {is_test_env}, Test file: {is_test_file}. "
                    f"This violates test isolation principles and is forbidden."
                )
        else:
            # Lenient mode requires EITHER environment OR file check
            if not (is_test_env or is_test_file):
                context_info = TestContextValidator.get_test_context_info()
                
                logger.error("=" * 80)
                logger.error("TEST CONTEXT VALIDATION FAILURE")
                logger.error("=" * 80)
                logger.error(f"Function: {function_name}")
                logger.error(f"Context Info: {context_info}")
                logger.error("=" * 80)
                
                raise ContextValidationError(
                    f"Test-only function '{function_name}' called from non-test context. "
                    f"Context info: {context_info}"
                )


def test_decorator(
    strict: bool = True,
    message: Optional[str] = None,
    allow_production: bool = False
) -> Callable:
    """
    SSOT Test Context Decorator - Enforces test-only execution.
    
    This decorator ensures that decorated functions can ONLY be called from test contexts.
    Violating this = ABOMINATION per CLAUDE.md.
    
    Args:
        strict: If True (default), requires both test environment AND test file detection
        message: Optional custom error message for violations
        allow_production: If True, allows production usage (use with extreme caution)
    
    Usage:
        @test_decorator()
        def _is_testing_environment():
            # This function can ONLY be called from tests
            return True
            
        @test_decorator(strict=False)
        def some_test_helper():
            # Lenient mode - either test env OR test file is sufficient
            pass
            
        @test_decorator(allow_production=True, message="Legacy usage - being migrated")
        def legacy_function():
            # Temporarily allows production usage with warning
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            function_name = f"{func.__module__}.{func.__name__}"
            
            # Skip validation if explicitly allowed in production
            if allow_production:
                logger.warning(f"[TestContext] Production usage allowed for {function_name}: {message or 'No message provided'}")
                return func(*args, **kwargs)
            
            # Validate test context
            try:
                TestContextValidator.validate_test_context(function_name, strict_mode=strict)
                logger.debug(f"[TestContext] Validated test context for {function_name}")
                
            except ContextValidationError as e:
                if message:
                    custom_message = f"{message}. Original error: {str(e)}"
                    logger.error(f"[TestContext] Custom validation failure: {custom_message}")
                    raise ContextValidationError(custom_message) from e
                else:
                    raise
            
            # Execute the function in validated test context
            return func(*args, **kwargs)
            
        # Add metadata to the wrapper for introspection
        wrapper._is_test_only = True
        wrapper._test_decorator_config = {
            "strict": strict,
            "message": message,
            "allow_production": allow_production
        }
        
        return wrapper
        
    return decorator


class TestOnlyMixin:
    """
    Mixin class for test-only functionality.
    
    Classes that inherit from this mixin are marked as test-only
    and their methods are automatically validated for test context.
    """
    
    def __init_subclass__(cls, **kwargs):
        """
        Automatically apply test context validation to all methods.
        
        This ensures that any class inheriting from TestOnlyMixin
        has all its methods protected by test context validation.
        """
        super().__init_subclass__(**kwargs)
        
        # Mark the class as test-only
        cls._is_test_only_class = True
        
        # Apply test_decorator to all public methods
        for name, method in cls.__dict__.items():
            if callable(method) and not name.startswith('_'):
                # Skip already decorated methods
                if not hasattr(method, '_is_test_only'):
                    decorated_method = test_decorator()(method)
                    setattr(cls, name, decorated_method)


def validate_no_test_imports_in_production():
    """
    Utility to scan for test imports in production code.
    
    This can be used in CI/CD pipelines to prevent test code leakage.
    Should be called during build validation.
    """
    import ast
    import os
    from pathlib import Path
    
    production_directories = [
        "netra_backend/app",
        "auth_service", 
        "shared"
    ]
    
    test_import_patterns = [
        "test_framework",
        "pytest",
        "unittest.mock",
        "mock",
        "_test",
        "conftest"
    ]
    
    violations = []
    
    for directory in production_directories:
        if not os.path.exists(directory):
            continue
            
        for py_file in Path(directory).rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse the AST to find imports
                tree = ast.parse(content, filename=str(py_file))
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        module_name = None
                        
                        if isinstance(node, ast.Import):
                            module_name = node.names[0].name
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            module_name = node.module
                            
                        if module_name and any(pattern in module_name for pattern in test_import_patterns):
                            violations.append({
                                "file": str(py_file),
                                "line": node.lineno,
                                "import": module_name
                            })
                            
            except Exception as e:
                logger.warning(f"Could not analyze {py_file}: {e}")
    
    if violations:
        logger.error("=" * 80)
        logger.error("TEST IMPORT VIOLATIONS IN PRODUCTION CODE")
        logger.error("=" * 80)
        
        for violation in violations:
            logger.error(f"File: {violation['file']}")
            logger.error(f"Line: {violation['line']}")
            logger.error(f"Import: {violation['import']}")
            logger.error("-" * 40)
            
        logger.error("=" * 80)
        logger.error("CRITICAL: Production code must not import test utilities")
        logger.error("ACTION REQUIRED: Remove test imports from production code")
        logger.error("=" * 80)
        
        raise ContextValidationError(f"Found {len(violations)} test import violations in production code")
    
    logger.info("[TestContext] No test import violations found in production code")


# Convenience functions for common patterns
def require_test_context(func: Callable = None, *, strict: bool = True, message: str = None):
    """
    Convenience decorator that's equivalent to @test_decorator.
    
    Can be used with or without parentheses:
        @require_test_context
        def my_function():
            pass
            
        @require_test_context(strict=False)
        def my_other_function():
            pass
    """
    if func is None:
        # Called with parameters: @require_test_context(strict=False)
        return test_decorator(strict=strict, message=message)
    else:
        # Called without parameters: @require_test_context
        return test_decorator(strict=strict, message=message)(func)


def mark_test_only(cls: Type) -> Type:
    """
    Class decorator to mark an entire class as test-only.
    
    This is equivalent to inheriting from TestOnlyMixin but can be
    applied to existing classes without changing their inheritance.
    
    Usage:
        @mark_test_only
        class MyTestUtility:
            def helper_method(self):
                pass
    """
    # Mark the class as test-only
    cls._is_test_only_class = True
    
    # Apply test_decorator to all public methods
    for name in dir(cls):
        if not name.startswith('_'):
            attr = getattr(cls, name)
            if callable(attr) and not hasattr(attr, '_is_test_only'):
                decorated_attr = test_decorator()(attr)
                setattr(cls, name, decorated_attr)
    
    return cls


# Export public interface
__all__ = [
    'test_decorator',
    'require_test_context', 
    'mark_test_only',
    'TestOnlyMixin',
    'TestContextValidator',
    'ContextValidationError',
    'validate_no_test_imports_in_production'
]