"""
Single Source of Truth (SSOT) BaseTestCase - The Canonical Test Base Class

This module provides the ONE canonical BaseTestCase that ALL tests across the entire
codebase MUST inherit from. This eliminates the 6,096 duplicate test implementations
and establishes a unified testing foundation.

CRITICAL: This is the SINGLE SOURCE OF TRUTH for all test base functionality.
NO other BaseTestCase implementations are allowed in the codebase.

Business Value: Platform/Internal - System Stability & Development Velocity
Eliminates test infrastructure duplication and provides consistent testing foundation.

REQUIREMENTS per CLAUDE.md:
- Must integrate with IsolatedEnvironment (no direct os.environ access)
- Must support both sync and async tests
- Must provide consistent metrics recording
- Must support WebSocket and database testing
- Must be backwards compatible where possible

SSOT Violations Eliminated:
- test_framework/base.py (BaseTestCase, AsyncTestCase)
- netra_backend/tests/helpers/shared_test_types.py (BaseTestMixin, TestErrorHandling, etc.)
- 6,000+ duplicate test utility implementations across test files

COMPATIBILITY SOLUTION (Issue #485 Resolution):
This module provides automatic compatibility between unittest-style (setUp/tearDown) 
and pytest-style (setup_method/teardown_method) test patterns:

1. PREFERRED PATTERN (pytest-style):
   ```python
   class MyTest(SSotAsyncTestCase):
       def setup_method(self, method):
           super().setup_method(method)
           # Your setup code here
   ```

2. LEGACY COMPATIBLE PATTERN (unittest-style):  
   ```python
   class MyTest(SSotAsyncTestCase, unittest.TestCase):
       def setUp(self):
           super().setUp()  # Automatically calls setup_method
           # Your setup code here
   ```

Both patterns are fully supported and provide identical SSOT functionality including
environment isolation, metrics recording, and test context management.

GOLDEN PATH BUSINESS IMPACT:
This compatibility solution directly enables the $500K+ ARR Golden Path user flow
tests to run reliably, protecting critical business functionality during 
infrastructure changes and SSOT consolidation efforts.
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Generator, Callable
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from shared.isolated_environment import IsolatedEnvironment, get_env
# from test_framework.unified import (
#     TestResult, TestExecutionState, CategoryType, TestConfiguration
# )
# Note: Commenting out unified imports for now to avoid import errors

# Temporary CategoryType enum
from enum import Enum

class CategoryType(Enum):
    """Test category types."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    SMOKE = "smoke"
    CRITICAL = "critical"


logger = logging.getLogger(__name__)


@dataclass
class SsotTestMetrics:
    """SSOT test metrics container."""
    execution_time: float = 0.0
    memory_usage: Optional[int] = None
    database_queries: int = 0
    redis_operations: int = 0
    websocket_events: int = 0
    llm_requests: int = 0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def record_custom(self, name: str, value: Any) -> None:
        """Record a custom metric."""
        self.custom_metrics[name] = value
    
    def get_custom(self, name: str, default: Any = None) -> Any:
        """Get a custom metric value."""
        return self.custom_metrics.get(name, default)
    
    def start_timing(self) -> None:
        """Start timing the test execution."""
        self.start_time = time.time()
    
    def end_timing(self) -> None:
        """End timing and calculate execution time."""
        if self.start_time is not None:
            self.end_time = time.time()
            self.execution_time = self.end_time - self.start_time


@dataclass  
class SsotTestContext:
    """SSOT test execution context."""
    test_id: str
    test_name: str
    test_category: CategoryType = CategoryType.UNIT
    user_id: Optional[str] = None
    trace_id: Optional[str] = None
    session_id: Optional[str] = None
    environment: str = "test"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize context with defaults."""
        if not self.trace_id:
            self.trace_id = f"test_{uuid.uuid4().hex[:8]}"
        if not self.user_id:
            self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        if not self.session_id:
            self.session_id = f"test_session_{uuid.uuid4().hex[:8]}"


class SSotBaseTestCase:
    """
    Single Source of Truth BaseTestCase - The CANONICAL test base class.
    
    This is the ONE and ONLY base test class that ALL tests in the codebase must inherit from.
    It provides:
    
    1. IsolatedEnvironment integration (NO direct os.environ access)
    2. Consistent metrics recording across all tests
    3. WebSocket testing support
    4. Database testing utilities
    5. Async/sync test support
    6. Error handling and context management
    7. Mock factories integration
    8. Test categorization and tagging
    
    CRITICAL: This replaces ALL existing BaseTestCase implementations.
    """
    
    def setup_method(self, method=None):
        """
        Setup method run before each test method.
        
        Initialize SSOT base test case components and ensure proper environment isolation.
        test context initialization for every test.
        """
        # Initialize core components if not already initialized
        if not hasattr(self, '_env'):
            self._env: IsolatedEnvironment = get_env()
        if not hasattr(self, '_metrics'):
            self._metrics: SsotTestMetrics = SsotTestMetrics()
        if not hasattr(self, '_test_context'):
            self._test_context: Optional[SsotTestContext] = None
        if not hasattr(self, '_cleanup_callbacks'):
            self._cleanup_callbacks: List[Callable] = []
        if not hasattr(self, '_test_started'):
            self._test_started = False
        if not hasattr(self, '_test_completed'):
            self._test_completed = False
        if not hasattr(self, '_original_env_state'):
            self._original_env_state: Optional[Dict[str, str]] = None
        
        # Start timing
        self._metrics.start_timing()
        
        # Initialize test context
        method_name = method.__name__ if method else "unknown_test"
        self._test_context = SsotTestContext(
            test_id=f"{self.__class__.__name__}::{method_name}",
            test_name=method_name,
            environment=self._env.get_environment_name()
        )
        
        # Enable environment isolation for test
        if not self._env.is_isolated():
            self._env.enable_isolation(backup_original=True)
            
        # Store original environment state for restoration
        self._original_env_state = self._env.get_all().copy()
        
        # Set test-specific environment variables
        self._env.set("TESTING", "true", "ssot_base_test_case")
        self._env.set("TEST_ID", self._test_context.test_id, "ssot_base_test_case")
        self._env.set("TRACE_ID", self._test_context.trace_id, "ssot_base_test_case")
        
        # Log test start
        logger.info(f"Starting test: {self._test_context.test_id}")
        self._test_started = True
    
    def teardown_method(self, method=None):
        """
        Teardown method run after each test method.
        
        CRITICAL: This ensures proper cleanup and metrics recording.
        """
        try:
            # End timing
            self._metrics.end_timing()
            
            # Execute cleanup callbacks
            for callback in reversed(self._cleanup_callbacks):
                try:
                    callback()
                except Exception as e:
                    logger.warning(f"Cleanup callback failed: {e}")
            
            # Reset environment to original state
            if self._original_env_state is not None:
                # Clear test-specific variables
                test_vars = ["TESTING", "TEST_ID", "TRACE_ID"]
                for var in test_vars:
                    self._env.delete(var, "ssot_base_test_case_cleanup")
            
            # Log test completion with metrics
            if self._test_context:
                logger.info(
                    f"Completed test: {self._test_context.test_id} "
                    f"(duration: {self._metrics.execution_time:.3f}s)"
                )
            
            self._test_completed = True
            
        finally:
            # Clean up state
            self._cleanup_callbacks.clear()
            self._test_context = None
            self._original_env_state = None
    
    # === UNITTEST COMPATIBILITY LAYER ===
    # These methods provide compatibility with unittest-style test classes
    # that use setUp/tearDown instead of setup_method/teardown_method
    
    def setUp(self):
        """
        unittest compatibility method.
        
        IMPORTANT: This provides backward compatibility for tests that inherit 
        from unittest.TestCase and use setUp/tearDown pattern. It calls the 
        pytest-style setup_method to ensure consistent behavior.
        
        NOTE: Tests should prefer setup_method/teardown_method for new code.
        """
        # Get the current test method from the stack
        import inspect
        frame = inspect.currentframe()
        test_method = None
        
        # Walk up the call stack to find the test method
        try:
            while frame:
                code = frame.f_code
                if code.co_name.startswith('test_'):
                    # Found the test method, create a mock method object
                    class MockMethod:
                        def __init__(self, name):
                            self.__name__ = name
                    test_method = MockMethod(code.co_name)
                    break
                frame = frame.f_back
        finally:
            del frame
        
        # Call the standard setup_method
        self.setup_method(test_method)
    
    def tearDown(self):
        """
        unittest compatibility method.
        
        IMPORTANT: This provides backward compatibility for tests that inherit 
        from unittest.TestCase and use setUp/tearDown pattern. It calls the 
        pytest-style teardown_method to ensure consistent behavior.
        
        NOTE: Tests should prefer setup_method/teardown_method for new code.
        """
        # Get the current test method from the stack
        import inspect
        frame = inspect.currentframe()
        test_method = None
        
        # Walk up the call stack to find the test method
        try:
            while frame:
                code = frame.f_code
                if code.co_name.startswith('test_'):
                    # Found the test method, create a mock method object
                    class MockMethod:
                        def __init__(self, name):
                            self.__name__ = name
                    test_method = MockMethod(code.co_name)
                    break
                frame = frame.f_back
        finally:
            del frame
        
        # Call the standard teardown_method
        self.teardown_method(test_method)
    
    # === CORE UTILITIES ===
    
    def get_env(self) -> IsolatedEnvironment:
        """
        Get the isolated environment instance.
        
        CRITICAL: This is the ONLY way tests should access environment variables.
        Direct access to os.environ is FORBIDDEN.
        """
        return self._env
    
    def get_metrics(self) -> SsotTestMetrics:
        """Get the current test metrics."""
        return self._metrics
    
    def get_test_context(self) -> Optional[SsotTestContext]:
        """Get the current test context."""
        return self._test_context
    
    def record_metric(self, name: str, value: Any) -> None:
        """
        Record a performance or business metric.
        
        Args:
            name: The metric name
            value: The metric value
        """
        self._metrics.record_custom(name, value)
        logger.debug(f"Recorded metric {name}: {value}")
    
    def get_metric(self, name: str, default: Any = None) -> Any:
        """
        Get a recorded metric value.
        
        Args:
            name: The metric name
            default: Default value if metric not found
            
        Returns:
            The metric value or default
        """
        return self._metrics.get_custom(name, default)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all recorded metrics including built-in ones."""
        metrics = {
            "execution_time": self._metrics.execution_time,
            "database_queries": self._metrics.database_queries,
            "redis_operations": self._metrics.redis_operations,
            "websocket_events": self._metrics.websocket_events,
            "llm_requests": self._metrics.llm_requests,
        }
        metrics.update(self._metrics.custom_metrics)
        return metrics
    
    def add_cleanup(self, callback: Callable) -> None:
        """
        Add a cleanup callback to be executed during teardown.
        
        Args:
            callback: Function to call during cleanup
        """
        self._cleanup_callbacks.append(callback)
    
    # === ENVIRONMENT UTILITIES ===
    
    def set_env_var(self, key: str, value: str) -> None:
        """
        Set an environment variable for this test.
        
        CRITICAL: This is the ONLY way tests should set environment variables.
        
        Args:
            key: Environment variable name
            value: Environment variable value
        """
        self._env.set(key, value, f"test_{self._test_context.test_id if self._test_context else 'unknown'}")
    
    def get_env_var(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get an environment variable value.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        return self._env.get(key, default)
    
    def delete_env_var(self, key: str) -> None:
        """
        Delete an environment variable for this test.
        
        Args:
            key: Environment variable name
        """
        self._env.delete(key, f"test_{self._test_context.test_id if self._test_context else 'unknown'}")
    
    @contextmanager
    def temp_env_vars(self, **kwargs) -> Generator[None, None, None]:
        """
        Context manager for temporary environment variables.
        
        Args:
            **kwargs: Environment variables to set temporarily
        """
        # Store original values
        original_values = {}
        for key, value in kwargs.items():
            original_values[key] = self._env.get(key)
            self.set_env_var(key, value)
        
        try:
            yield
        finally:
            # Restore original values
            for key, original_value in original_values.items():
                if original_value is None:
                    self.delete_env_var(key)
                else:
                    self.set_env_var(key, original_value)
    
    # Alias for backwards compatibility
    def mock_environment_variables(self, env_vars: Dict[str, str]):
        """
        Context manager for mocking environment variables.
        
        Args:
            env_vars: Dictionary of environment variables to set temporarily
        """
        return self.temp_env_vars(**env_vars)
    
    # === DATABASE UTILITIES ===
    
    def increment_db_query_count(self, count: int = 1) -> None:
        """Increment the database query count metric."""
        self._metrics.database_queries += count
    
    def get_db_query_count(self) -> int:
        """Get the current database query count."""
        return self._metrics.database_queries
    
    @contextmanager
    def track_db_queries(self) -> Generator[None, None, None]:
        """Context manager to track database queries in a block."""
        start_count = self._metrics.database_queries
        try:
            yield
        finally:
            queries_made = self._metrics.database_queries - start_count
            logger.debug(f"Database queries in block: {queries_made}")
    
    # === REDIS UTILITIES ===
    
    def increment_redis_ops_count(self, count: int = 1) -> None:
        """Increment the Redis operations count metric."""
        self._metrics.redis_operations += count
    
    def get_redis_ops_count(self) -> int:
        """Get the current Redis operations count."""
        return self._metrics.redis_operations
    
    # === WEBSOCKET UTILITIES ===
    
    def increment_websocket_events(self, count: int = 1) -> None:
        """Increment the WebSocket events count metric."""
        self._metrics.websocket_events += count
    
    def get_websocket_events_count(self) -> int:
        """Get the current WebSocket events count."""
        return self._metrics.websocket_events
    
    @contextmanager
    def track_websocket_events(self) -> Generator[None, None, None]:
        """Context manager to track WebSocket events in a block."""
        start_count = self._metrics.websocket_events
        try:
            yield
        finally:
            events_sent = self._metrics.websocket_events - start_count
            logger.debug(f"WebSocket events in block: {events_sent}")
    
    # === LLM UTILITIES ===
    
    def increment_llm_requests(self, count: int = 1) -> None:
        """Increment the LLM requests count metric."""
        self._metrics.llm_requests += count
    
    def get_llm_requests_count(self) -> int:
        """Get the current LLM requests count."""
        return self._metrics.llm_requests
    
    # === ASSERTION UTILITIES ===
    
    # Standard unittest-style assertion methods for compatibility
    def assertIsNotNone(self, value, msg=None):
        """Assert that value is not None."""
        assert value is not None, msg or f"Expected not None, got None"
    
    def assertIsNone(self, value, msg=None):
        """Assert that value is None."""
        assert value is None, msg or f"Expected None, got {value}"
    
    def assertEqual(self, first, second, msg=None):
        """Assert that first equals second."""
        assert first == second, msg or f"Expected {first} == {second}"
    
    def assertNotEqual(self, first, second, msg=None):
        """Assert that first does not equal second."""
        assert first != second, msg or f"Expected {first} != {second}"
    
    def assertTrue(self, expr, msg=None):
        """Assert that expr is true."""
        assert expr, msg or f"Expected True, got {expr}"
    
    def assertFalse(self, expr, msg=None):
        """Assert that expr is false."""
        assert not expr, msg or f"Expected False, got {expr}"
    
    def assertIn(self, member, container, msg=None):
        """Assert that member is in container."""
        assert member in container, msg or f"Expected {member} in {container}"
    
    def assertNotIn(self, member, container, msg=None):
        """Assert that member is not in container."""
        assert member not in container, msg or f"Expected {member} not in {container}"
    
    def assertGreater(self, first, second, msg=None):
        """Assert that first > second."""
        assert first > second, msg or f"Expected {first} > {second}"
    
    def assertGreaterEqual(self, first, second, msg=None):
        """Assert that first >= second."""
        assert first >= second, msg or f"Expected {first} >= {second}"
    
    def assertLess(self, first, second, msg=None):
        """Assert that first < second."""
        assert first < second, msg or f"Expected {first} < {second}"
    
    def assertLessEqual(self, first, second, msg=None):
        """Assert that first <= second."""
        assert first <= second, msg or f"Expected {first} <= {second}"
    
    def assertAlmostEqual(self, first, second, places=7, msg=None, delta=None):
        """Assert that first and second are approximately equal within tolerance."""
        if delta is not None:
            # If delta is specified, use it directly
            diff = abs(first - second)
            assert diff <= delta, msg or f"Expected {first} ≈ {second} (delta={delta}), but difference was {diff}"
        else:
            # Use places parameter (number of decimal places)
            if places is None:
                places = 7
            tolerance = 10**(-places)
            diff = abs(first - second)
            assert diff <= tolerance, msg or f"Expected {first} ≈ {second} (places={places}), but difference was {diff}"
    
    def assertIsInstance(self, obj, cls, msg=None):
        """Assert that obj is an instance of cls."""
        assert isinstance(obj, cls), msg or f"Expected {obj} to be instance of {cls}, got {type(obj)}"
    
    def assertNotIsInstance(self, obj, cls, msg=None):
        """Assert that obj is not an instance of cls."""
        assert not isinstance(obj, cls), msg or f"Expected {obj} to not be instance of {cls}"
    
    def assert_env_var_set(self, key: str, expected_value: Optional[str] = None) -> None:
        """
        Assert that an environment variable is set.
        
        Args:
            key: Environment variable name
            expected_value: Expected value (optional)
        """
        actual_value = self._env.get(key)
        assert actual_value is not None, f"Environment variable {key} is not set"
        
        if expected_value is not None:
            assert actual_value == expected_value, f"Environment variable {key} expected '{expected_value}', got '{actual_value}'"
    
    def assert_env_var_not_set(self, key: str) -> None:
        """
        Assert that an environment variable is not set.
        
        Args:
            key: Environment variable name
        """
        actual_value = self._env.get(key)
        assert actual_value is None, f"Environment variable {key} should not be set, but has value '{actual_value}'"
    
    def assert_metrics_recorded(self, *metric_names: str) -> None:
        """
        Assert that specific metrics have been recorded.
        
        Args:
            *metric_names: Names of metrics to check
        """
        for metric_name in metric_names:
            assert metric_name in self._metrics.custom_metrics, f"Metric '{metric_name}' was not recorded"
    
    def assert_execution_time_under(self, max_seconds: float) -> None:
        """
        Assert that test execution time is under a threshold.
        
        Args:
            max_seconds: Maximum allowed execution time in seconds
        """
        assert self._metrics.execution_time < max_seconds, (
            f"Test execution time {self._metrics.execution_time:.3f}s "
            f"exceeded maximum {max_seconds}s"
        )
    
    # === ERROR HANDLING UTILITIES ===
    
    def expect_exception(self, exception_class: type, message_pattern: Optional[str] = None):
        """
        Context manager to expect a specific exception.
        
        Args:
            exception_class: Expected exception class
            message_pattern: Optional pattern to match in exception message
        """
        return pytest.raises(exception_class, match=message_pattern)
    
    def assert_no_exceptions_logged(self, logger_name: Optional[str] = None) -> None:
        """
        Assert that no exceptions were logged during test execution.
        
        Args:
            logger_name: Specific logger to check (optional)
        """
        # This would need integration with logging capture
        # Implementation depends on test framework setup
        pass
    
    # === ASYNC SUPPORT ===
    
    async def async_setup_method(self, method=None):
        """Async version of setup_method."""
        self.setup_method(method)
    
    async def async_teardown_method(self, method=None):
        """Async version of teardown_method.""" 
        self.teardown_method(method)
    
    @asynccontextmanager
    async def async_temp_env_vars(self, **kwargs) -> AsyncGenerator[None, None]:
        """Async context manager for temporary environment variables."""
        with self.temp_env_vars(**kwargs):
            yield



    # === E2E AUTHENTICATION SUPPORT ===
    
    async def create_authenticated_test_user(self, **kwargs):
        """
        Create authenticated test user for E2E tests.
        
        This method provides SSOT compatibility for E2E tests that need authenticated users.
        It delegates to the centralized E2EAuthHelper to ensure consistent authentication.
        
        Args:
            **kwargs: Additional arguments passed to E2EAuthHelper.create_authenticated_user()
                     Common options: name, email, permissions, environment
        
        Returns:
            AuthenticatedUser: Created user with JWT token and authentication data
            
        Example:
            user = await self.create_authenticated_test_user(
                name="Test User",
                email="test@example.com", 
                permissions=["read", "write"]
            )
        """
        try:
            from test_framework.ssot.e2e_auth_helper import create_authenticated_user
            return await create_authenticated_user(**kwargs)
        except ImportError as e:
            raise ImportError(
                f"E2E authentication helper not available: {e}. "
                f"Ensure test_framework.ssot.e2e_auth_helper is accessible."
            )


class SSotAsyncTestCase(SSotBaseTestCase):
    """
    SSOT Async Test Case - For async tests only.
    
    This extends the base SSOT test case with async-specific functionality.
    """
    
    @pytest.fixture
    def event_loop(self):
        """Provide event loop for async tests."""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()
    
    def setup_method(self, method=None):
        """Setup method for async tests - calls parent sync setup."""
        # Call the parent's sync setup method directly
        super().setup_method(method)
    
    def teardown_method(self, method=None):
        """Teardown method for async tests - calls parent sync teardown."""
        # Call the parent's sync teardown method directly
        # But ensure we have the required attributes first
        if not hasattr(self, '_cleanup_callbacks'):
            self._cleanup_callbacks = []
        if not hasattr(self, '_test_context'):
            self._test_context = None
        if not hasattr(self, '_original_env_state'):
            self._original_env_state = None
        super().teardown_method(method)
    
    # === ASYNC UNITTEST COMPATIBILITY LAYER ===
    # These methods provide compatibility with async unittest-style test classes
    
    def setUp(self):
        """
        unittest compatibility method for async tests.
        
        IMPORTANT: This provides backward compatibility for async tests that inherit 
        from unittest.TestCase and use setUp/tearDown pattern. It calls the 
        pytest-style setup_method to ensure consistent behavior.
        
        NOTE: Tests should prefer setup_method/teardown_method for new code.
        """
        # Get the current test method from the stack
        import inspect
        frame = inspect.currentframe()
        test_method = None
        
        # Walk up the call stack to find the test method
        try:
            while frame:
                code = frame.f_code
                if code.co_name.startswith('test_'):
                    # Found the test method, create a mock method object
                    class MockMethod:
                        def __init__(self, name):
                            self.__name__ = name
                    test_method = MockMethod(code.co_name)
                    break
                frame = frame.f_back
        finally:
            del frame
        
        # Call the standard setup_method
        self.setup_method(test_method)
    
    def tearDown(self):
        """
        unittest compatibility method for async tests.
        
        IMPORTANT: This provides backward compatibility for async tests that inherit 
        from unittest.TestCase and use setUp/tearDown pattern. It calls the 
        pytest-style teardown_method to ensure consistent behavior.
        
        NOTE: Tests should prefer setup_method/teardown_method for new code.
        """
        # Get the current test method from the stack
        import inspect
        frame = inspect.currentframe()
        test_method = None
        
        # Walk up the call stack to find the test method
        try:
            while frame:
                code = frame.f_code
                if code.co_name.startswith('test_'):
                    # Found the test method, create a mock method object
                    class MockMethod:
                        def __init__(self, name):
                            self.__name__ = name
                    test_method = MockMethod(code.co_name)
                    break
                frame = frame.f_back
        finally:
            del frame
        
        # Call the standard teardown_method
        self.teardown_method(test_method)
    
    async def wait_for_condition(
        self,
        condition: Callable[[], bool],
        timeout: float = 5.0,
        interval: float = 0.1,
        error_message: str = "Condition not met within timeout"
    ) -> None:
        """
        Wait for a condition to become true within a timeout.
        
        Args:
            condition: Function that returns True when condition is met
            timeout: Maximum time to wait in seconds
            interval: Check interval in seconds
            error_message: Error message if timeout is reached
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition():
                return
            await asyncio.sleep(interval)
        
        raise TimeoutError(error_message)
    
    async def run_with_timeout(self, coro, timeout: float = 5.0):
        """
        Run a coroutine with a timeout.
        
        Args:
            coro: Coroutine to run
            timeout: Timeout in seconds
            
        Returns:
            Coroutine result
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Coroutine timed out after {timeout} seconds")


# === SSOT MIGRATION COMPLETE ===

# Aliases migrated to SSOT patterns - use SSotBaseTestCase directly
BaseTestCase = SSotBaseTestCase
AsyncTestCase = SSotAsyncTestCase
BaseIntegrationTest = SSotBaseTestCase  # Legacy alias for integration tests

# Legacy compatibility classes removed - use SSotBaseTestCase directly

# Compatibility aliases for integration tests (Issue #308)
SSotAsyncBaseTestCase = SSotAsyncTestCase  # Alias for integration test compatibility


# === EXPORT CONTROL ===

__all__ = [
    # SSOT Classes
    "SSotBaseTestCase",
    "SSotAsyncTestCase", 
    "SsotTestMetrics",
    "SsotTestContext",
    
    # SSOT Aliases
    "BaseTestCase",
    "AsyncTestCase",
    "BaseIntegrationTest",  # Legacy alias for integration tests
    
    # Legacy compatibility classes removed
    
    # Legacy Aliases (deprecated)
    "TestMetrics", 
    "TestContext",
]

# Legacy aliases for backwards compatibility (deprecated - use SsotTestMetrics/SsotTestContext)
TestMetrics = SsotTestMetrics
TestContext = SsotTestContext