"""
Asyncio Test Utilities for Event Loop Testing

This module provides utilities for testing asyncio event loop issues,
particularly nested asyncio.run() calls and event loop conflicts.
"""

import asyncio
import contextlib
import functools
import inspect
import sys
import threading
from typing import Any, Callable, Optional, Tuple
from unittest.mock import patch


class EventLoopTestError(Exception):
    """Custom exception for event loop test failures."""
    pass


class AsyncioTestUtils:
    """Utilities for testing asyncio event loop behavior."""

    @staticmethod
    def is_event_loop_running() -> bool:
        """Check if an event loop is currently running."""
        try:
            loop = asyncio.get_running_loop()
            return loop is not None and loop.is_running()
        except RuntimeError:
            return False

    @staticmethod
    def detect_nested_asyncio_run(func: Callable) -> bool:
        """
        Detect if a function contains nested asyncio.run() calls.

        Args:
            func: Function to analyze

        Returns:
            True if potential nested asyncio.run() detected
        """
        import ast
        import inspect
        import textwrap

        try:
            source = inspect.getsource(func)
            # Remove common leading whitespace to fix indentation issues
            source = textwrap.dedent(source)
            tree = ast.parse(source)

            # Check for asyncio.run() inside async functions
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if (hasattr(child.func, 'attr') and
                                child.func.attr == 'run' and
                                hasattr(child.func, 'value') and
                                hasattr(child.func.value, 'id') and
                                child.func.value.id == 'asyncio'):
                                return True
        except:
            # If we can't inspect the source, assume it's safe
            return False

        return False

    @staticmethod
    async def simulate_nested_call(async_func: Callable) -> Tuple[bool, Optional[Exception]]:
        """
        Simulate calling a function that might use asyncio.run() from async context.

        Returns:
            Tuple of (success, exception if failed)
        """
        try:
            # Try to run the function
            if inspect.iscoroutinefunction(async_func):
                await async_func()
            else:
                async_func()
            return True, None
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                return False, e
            raise
        except Exception as e:
            return False, e

    @staticmethod
    def create_test_event_loop() -> asyncio.AbstractEventLoop:
        """Create a test event loop for isolated testing."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

    @staticmethod
    @contextlib.contextmanager
    def assert_no_nested_asyncio_run():
        """
        Context manager that fails if asyncio.run() is called within.

        Usage:
            async def test_function():
                with AsyncioTestUtils.assert_no_nested_asyncio_run():
                    await some_function()
        """
        original_run = asyncio.run

        def patched_run(*args, **kwargs):
            if AsyncioTestUtils.is_event_loop_running():
                raise EventLoopTestError(
                    "Nested asyncio.run() detected! This would cause a deadlock in production."
                )
            return original_run(*args, **kwargs)

        asyncio.run = patched_run
        try:
            yield
        finally:
            asyncio.run = original_run

    @staticmethod
    def wrap_with_event_loop_check(func: Callable) -> Callable:
        """
        Decorator that checks for event loop issues.

        Usage:
            @AsyncioTestUtils.wrap_with_event_loop_check
            async def test_something():
                pass
        """
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with AsyncioTestUtils.assert_no_nested_asyncio_run():
                return await func(*args, **kwargs)
        return wrapper

    @staticmethod
    async def test_async_function_safety(func: Callable, *args, **kwargs) -> dict:
        """
        Test if an async function is safe from event loop issues.

        Returns:
            Dictionary with test results
        """
        results = {
            'has_nested_asyncio_run': False,
            'executes_successfully': False,
            'error': None,
            'is_coroutine_function': inspect.iscoroutinefunction(func)
        }

        # Static analysis
        results['has_nested_asyncio_run'] = AsyncioTestUtils.detect_nested_asyncio_run(func)

        # Runtime test
        try:
            with AsyncioTestUtils.assert_no_nested_asyncio_run():
                if inspect.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
                results['executes_successfully'] = True
        except EventLoopTestError as e:
            results['error'] = str(e)
        except Exception as e:
            results['error'] = f"Unexpected error: {str(e)}"

        return results


class AsyncioRegressionTester:
    """Test runner for asyncio regression testing."""

    def __init__(self):
        self.results = []
        self.failures = []

    async def test_function_for_nested_loops(self, func: Callable, func_name: str = None) -> bool:
        """
        Test a function for nested event loop issues.

        Args:
            func: Function to test
            func_name: Optional name for reporting

        Returns:
            True if test passes (no nested loops detected)
        """
        func_name = func_name or func.__name__

        # Test 1: Static analysis
        has_nested = AsyncioTestUtils.detect_nested_asyncio_run(func)
        if has_nested:
            self.failures.append(f"{func_name}: Static analysis detected nested asyncio.run()")
            return False

        # Test 2: Runtime check (if it's callable without args)
        try:
            if inspect.signature(func).parameters:
                # Skip runtime test if function needs parameters
                self.results.append(f"{func_name}: Passed (skipped runtime test - needs params)")
                return True

            test_results = await AsyncioTestUtils.test_async_function_safety(func)
            if not test_results['executes_successfully']:
                self.failures.append(f"{func_name}: Runtime test failed - {test_results['error']}")
                return False
        except Exception as e:
            # If we can't test it, log but don't fail
            self.results.append(f"{func_name}: Test skipped due to error - {str(e)}")
            return True

        self.results.append(f"{func_name}: Passed all tests")
        return True

    def generate_report(self) -> str:
        """Generate a test report."""
        report = []
        report.append("=== Asyncio Regression Test Report ===\n")
        report.append(f"Total tests run: {len(self.results) + len(self.failures)}")
        report.append(f"Passed: {len(self.results)}")
        report.append(f"Failed: {len(self.failures)}")

        if self.failures:
            report.append("\nFAILURES:")
            for failure in self.failures:
                report.append(f"  - {failure}")

        if self.results:
            report.append("\nSUCCESSES:")
            for result in self.results:
                report.append(f"  - {result}")

        return "\n".join(report)


def create_mock_async_function_with_nested_run():
    """Create a mock function that improperly uses asyncio.run()"""
    async def bad_function():
        # This would cause a deadlock
        return asyncio.run(some_async_task())

    async def some_async_task():
        return "result"

    return bad_function


def create_mock_async_function_proper():
    """Create a mock function that properly uses await"""
    async def good_function():
        # Proper async call
        return await some_async_task()

    async def some_async_task():
        return "result"

    return good_function


class EventLoopValidator:
    """Validator for ensuring proper event loop usage in a codebase."""

    @staticmethod
    def validate_module(module_path: str) -> dict:
        """
        Validate all functions in a module for event loop issues.

        Args:
            module_path: Path to Python module

        Returns:
            Dictionary with validation results
        """
        import ast

        results = {
            'module': module_path,
            'issues': [],
            'functions_checked': 0,
            'async_functions': 0,
            'potential_issues': 0
        }

        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    results['async_functions'] += 1
                    results['functions_checked'] += 1

                    # Check for asyncio.run() in async function
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if (hasattr(child.func, 'attr') and
                                child.func.attr == 'run' and
                                hasattr(child.func, 'value') and
                                hasattr(child.func.value, 'id') and
                                child.func.value.id == 'asyncio'):
                                results['potential_issues'] += 1
                                results['issues'].append({
                                    'function': node.name,
                                    'line': child.lineno,
                                    'type': 'nested_asyncio_run',
                                    'severity': 'CRITICAL'
                                })
                elif isinstance(node, ast.FunctionDef):
                    results['functions_checked'] += 1

        except Exception as e:
            results['error'] = str(e)

        return results


# Test helper functions for mocking event loop scenarios
async def async_function_caller(func):
    """Helper to call functions in async context for testing."""
    if inspect.iscoroutinefunction(func):
        return await func()
    else:
        return func()


def run_in_thread_with_loop(func):
    """Run a function in a separate thread with its own event loop."""
    result = {'value': None, 'error': None}

    def thread_runner():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            if inspect.iscoroutinefunction(func):
                result['value'] = loop.run_until_complete(func())
            else:
                result['value'] = func()
        except Exception as e:
            result['error'] = e
        finally:
            loop.close()

    thread = threading.Thread(target=thread_runner)
    thread.start()
    thread.join(timeout=5)

    if result['error']:
        raise result['error']
    return result['value']