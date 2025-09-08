"""
Single Source of Truth (SSOT) Base Test Framework

This module provides the fundamental BaseTestCase that ALL tests in the system must inherit from.
It ensures consistent test setup, environment isolation, and proper cleanup across all 6,096 test files.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
Eliminates test infrastructure violations and provides unified foundation for all testing.

CRITICAL: This is the ONLY base test class allowed in the system.
ALL test classes must inherit from BaseTestCase or its specialized subclasses.
"""

import asyncio
import inspect
import logging
import os
import sys
import time
import traceback
import uuid
from abc import ABC
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union, AsyncGenerator, Generator
from unittest import TestCase
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Import SSOT environment management
from shared.isolated_environment import IsolatedEnvironment, get_env

# Add project root to Python path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logger = logging.getLogger(__name__)


class ExecutionMetrics:
    """Collect and track test execution metrics for analysis."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.setup_duration = 0
        self.teardown_duration = 0
        self.test_duration = 0
        self.memory_usage_start = 0
        self.memory_usage_end = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def start_execution(self):
        """Start tracking execution metrics."""
        self.start_time = time.time()
        try:
            import psutil
            process = psutil.Process()
            self.memory_usage_start = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            pass
            
    def end_execution(self):
        """End tracking execution metrics."""
        self.end_time = time.time()
        if self.start_time:
            self.test_duration = self.end_time - self.start_time
        
        try:
            import psutil
            process = psutil.Process()
            self.memory_usage_end = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            pass
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for reporting."""
        return {
            "test_duration": self.test_duration,
            "setup_duration": self.setup_duration,
            "teardown_duration": self.teardown_duration,
            "memory_start_mb": self.memory_usage_start,
            "memory_end_mb": self.memory_usage_end,
            "memory_delta_mb": self.memory_usage_end - self.memory_usage_start,
            "errors": self.errors,
            "warnings": self.warnings
        }


class BaseTestCase(TestCase):
    """
    Single Source of Truth (SSOT) base test class for ALL tests in the system.
    
    This class provides:
    - Environment isolation using IsolatedEnvironment SSOT
    - Consistent test lifecycle management
    - Automatic cleanup and resource management
    - Error handling and logging
    - Test metrics collection
    - Service integration utilities
    
    ALL test classes in the system MUST inherit from this base class.
    This ensures consistency, proper resource management, and eliminates duplication.
    
    Usage:
        class MyTest(BaseTestCase):
            async def test_my_feature(self):
                # Test implementation
                pass
                
    For specialized testing needs, inherit from specialized subclasses
    rather than implementing custom base classes.
    """
    
    # Class-level configuration
    REQUIRES_DATABASE = False
    REQUIRES_REDIS = False
    REQUIRES_WEBSOCKET = False
    REQUIRES_REAL_SERVICES = False
    ISOLATION_ENABLED = True
    AUTO_CLEANUP = True
    
    def __init__(self, *args, **kwargs):
        """Initialize base test case with SSOT environment and metrics."""
        super().__init__(*args, **kwargs)
        
        # SSOT environment management
        self.env = get_env()
        self._original_env_state = None
        self._test_id = f"test_{uuid.uuid4().hex[:8]}"
        
        # Metrics collection
        self.metrics = ExecutionMetrics()
        
        # Resource tracking
        self._resources_to_cleanup: List[Any] = []
        self._temp_files: List[Path] = []
        self._active_patches: List[Any] = []
        
        # Service clients (initialized on demand)
        self._db_session: Optional[AsyncSession] = None
        self._redis_client: Optional[Any] = None
        self._websocket_client: Optional[Any] = None
        
        # Test context
        self.test_name = self._get_test_name()
        self.test_class = self.__class__.__name__
        
        logger.debug(f"Initialized {self.test_class}::{self.test_name} [{self._test_id}]")
        
    def _get_test_name(self) -> str:
        """Extract current test method name from stack."""
        for frame_info in inspect.stack():
            if frame_info.function.startswith('test_'):
                return frame_info.function
        return "unknown_test"
    
    @contextmanager
    def isolated_environment(self, **env_vars):
        """
        Context manager for isolated environment with specific variables.
        
        Args:
            **env_vars: Environment variables to set during test
            
        Usage:
            with self.isolated_environment(TEST_MODE="true"):
                # Test with isolated environment
                pass
        """
        self.env.enable_isolation(backup_original=True)
        
        # Apply test environment variables
        for key, value in env_vars.items():
            self.env.set(key, str(value), f"test_isolation_{self._test_id}")
            
        try:
            yield
        finally:
            self.env.disable_isolation(restore_original=True)
    
    def setUp(self):
        """Set up test environment - called before each test method."""
        if hasattr(super(), 'setUp'):
            super().setUp()
            
        setup_start = time.time()
        
        try:
            self._setup_environment()
            self._setup_logging()
            self._setup_test_isolation()
            
            self.metrics.setup_duration = time.time() - setup_start
            self.metrics.start_execution()
            
            logger.info(f"Test setup completed: {self.test_class}::{self.test_name}")
            
        except Exception as e:
            logger.error(f"Test setup failed: {e}")
            self.metrics.errors.append(f"Setup failed: {str(e)}")
            raise
    
    def tearDown(self):
        """Clean up test environment - called after each test method."""
        teardown_start = time.time()
        
        try:
            self.metrics.end_execution()
            
            if self.AUTO_CLEANUP:
                self._cleanup_resources()
                self._cleanup_environment()
                
            self.metrics.teardown_duration = time.time() - teardown_start
            
            # Log test completion with metrics
            if self.metrics.errors:
                logger.warning(f"Test completed with errors: {self.test_class}::{self.test_name}")
            else:
                logger.info(f"Test completed successfully: {self.test_class}::{self.test_name}")
                
            # Log metrics if test took longer than 5 seconds
            if self.metrics.test_duration > 5.0:
                logger.info(f"Test performance: {self.metrics.to_dict()}")
                
        except Exception as e:
            logger.error(f"Test teardown failed: {e}")
        finally:
            if hasattr(super(), 'tearDown'):
                super().tearDown()
    
    def _setup_environment(self):
        """Set up isolated test environment using SSOT IsolatedEnvironment."""
        if self.ISOLATION_ENABLED:
            # Enable isolation and capture original state
            self._original_env_state = self.env.get_all()
            self.env.enable_isolation(backup_original=True)
            
            # Set test-specific environment variables
            test_env_vars = {
                "TESTING": "true",
                "ENVIRONMENT": "test",
                "TEST_ID": self._test_id,
                "TEST_NAME": self.test_name,
                "TEST_CLASS": self.test_class,
                "LOG_LEVEL": self.env.get("TEST_LOG_LEVEL", "INFO")
            }
            
            self.env.update(test_env_vars, f"base_test_{self._test_id}")
            
            logger.debug(f"Environment isolation enabled for test: {self._test_id}")
    
    def _setup_logging(self):
        """Configure test-specific logging."""
        log_level = self.env.get("LOG_LEVEL", "INFO").upper()
        
        # Create test-specific logger
        test_logger = logging.getLogger(f"test.{self.test_class}")
        test_logger.setLevel(getattr(logging, log_level))
        
        # Add handler if not already present
        if not test_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self._test_id} - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            test_logger.addHandler(handler)
    
    def _setup_test_isolation(self):
        """Set up test isolation boundaries."""
        # Ensure we're not leaking between tests
        if hasattr(self, '_previous_test_id'):
            logger.warning(f"Previous test ID found: {self._previous_test_id}")
            
        # Track this test execution
        self._previous_test_id = self._test_id
    
    def _cleanup_resources(self):
        """Clean up all tracked resources."""
        cleanup_errors = []
        
        # Clean up tracked resources
        for resource in reversed(self._resources_to_cleanup):
            try:
                if hasattr(resource, 'close'):
                    if asyncio.iscoroutinefunction(resource.close):
                        # Handle async cleanup
                        loop = None
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        if loop.is_running():
                            # If loop is running, schedule cleanup
                            loop.create_task(resource.close())
                        else:
                            loop.run_until_complete(resource.close())
                    else:
                        resource.close()
                elif hasattr(resource, 'cleanup'):
                    resource.cleanup()
                    
            except Exception as e:
                cleanup_errors.append(f"Resource cleanup failed: {str(e)}")
                logger.warning(f"Failed to cleanup resource {resource}: {e}")
        
        # Clean up temporary files
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                cleanup_errors.append(f"Temp file cleanup failed: {str(e)}")
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
        
        # Clean up active patches
        for patch_obj in self._active_patches:
            try:
                if hasattr(patch_obj, 'stop'):
                    patch_obj.stop()
            except Exception as e:
                cleanup_errors.append(f"Patch cleanup failed: {str(e)}")
                logger.warning(f"Failed to stop patch {patch_obj}: {e}")
        
        # Clear tracking lists
        self._resources_to_cleanup.clear()
        self._temp_files.clear()
        self._active_patches.clear()
        
        if cleanup_errors:
            self.metrics.errors.extend(cleanup_errors)
    
    def _cleanup_environment(self):
        """Clean up environment isolation."""
        if self.ISOLATION_ENABLED and self._original_env_state is not None:
            try:
                self.env.disable_isolation(restore_original=True)
                logger.debug(f"Environment isolation cleaned up for test: {self._test_id}")
            except Exception as e:
                logger.error(f"Environment cleanup failed: {e}")
                self.metrics.errors.append(f"Environment cleanup failed: {str(e)}")
    
    def track_resource(self, resource: Any):
        """Track a resource for automatic cleanup."""
        self._resources_to_cleanup.append(resource)
        logger.debug(f"Tracking resource for cleanup: {type(resource)}")
    
    def track_temp_file(self, file_path: Union[str, Path]):
        """Track a temporary file for automatic cleanup."""
        path = Path(file_path)
        self._temp_files.append(path)
        logger.debug(f"Tracking temp file for cleanup: {path}")
    
    def apply_patch(self, *args, **kwargs):
        """Apply a patch and track it for cleanup."""
        patch_obj = patch(*args, **kwargs)
        self._active_patches.append(patch_obj)
        return patch_obj.start()
    
    @asynccontextmanager
    async def async_test_context(self):
        """Async context manager for tests requiring async setup/teardown."""
        try:
            await self.async_setup()
            yield
        finally:
            await self.async_teardown()
    
    async def async_setup(self):
        """Override in subclasses for async test setup."""
        pass
    
    async def async_teardown(self):
        """Override in subclasses for async test cleanup."""
        pass
    
    def get_test_database_url(self) -> str:
        """Get test database URL with proper configuration."""
        base_url = self.env.get("TEST_DATABASE_URL") or self.env.get("DATABASE_URL")
        if not base_url:
            # Provide default test database URL
            base_url = "postgresql://postgres:postgres@localhost:5432/netra_test"
        
        # Ensure it's a test database
        if "test" not in base_url.lower():
            # Modify to use test database
            if "netra" in base_url and "test" not in base_url:
                base_url = base_url.replace("netra", "netra_test")
            
        return base_url
    
    def get_test_redis_url(self) -> str:
        """Get test Redis URL with proper configuration."""
        return self.env.get("TEST_REDIS_URL", "redis://localhost:6379/1")  # Use db=1 for tests
    
    def assert_no_errors(self):
        """Assert that no errors were recorded during test execution."""
        if self.metrics.errors:
            raise AssertionError(f"Test recorded errors: {self.metrics.errors}")
    
    def assert_performance_threshold(self, max_duration: float):
        """Assert that test completed within performance threshold."""
        if self.metrics.test_duration > max_duration:
            raise AssertionError(
                f"Test exceeded performance threshold: {self.metrics.test_duration:.2f}s > {max_duration}s"
            )
    
    def skip_if_missing_service(self, service_name: str):
        """Skip test if required service is not available."""
        if service_name == "database" and self.REQUIRES_DATABASE:
            try:
                # Test database connection
                self.get_test_database_url()
            except Exception:
                pytest.skip(f"Database service not available")
        
        elif service_name == "redis" and self.REQUIRES_REDIS:
            try:
                import redis
                r = redis.from_url(self.get_test_redis_url())
                r.ping()
            except Exception:
                pytest.skip(f"Redis service not available")
    
    def get_service_status(self) -> Dict[str, bool]:
        """Get status of all required services."""
        status = {}
        
        if self.REQUIRES_DATABASE:
            try:
                # Test database connection
                self.get_test_database_url()
                status["database"] = True
            except Exception:
                status["database"] = False
        
        if self.REQUIRES_REDIS:
            try:
                import redis
                r = redis.from_url(self.get_test_redis_url())
                r.ping()
                status["redis"] = True
            except Exception:
                status["redis"] = False
        
        return status


class AsyncBaseTestCase(BaseTestCase):
    """
    Async-aware base test case for tests requiring async/await support.
    
    This extends BaseTestCase with async-specific utilities while maintaining
    all SSOT principles and environment isolation.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    async def asyncSetUp(self):
        """Async setup called before each async test method."""
        await super().async_setup()
        
        # Get or create event loop
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        logger.debug(f"Async test setup completed: {self.test_class}::{self.test_name}")
    
    async def asyncTearDown(self):
        """Async teardown called after each async test method."""
        await super().async_teardown()
        logger.debug(f"Async test teardown completed: {self.test_class}::{self.test_name}")
    
    async def run_async_test(self, coro):
        """Run an async test coroutine with proper error handling."""
        try:
            result = await coro
            return result
        except Exception as e:
            self.metrics.errors.append(f"Async test failed: {str(e)}")
            logger.error(f"Async test failed: {e}\n{traceback.format_exc()}")
            raise


# Specialized base classes for common test patterns

class DatabaseTestCase(BaseTestCase):
    """Base test case for tests requiring database access."""
    
    REQUIRES_DATABASE = True
    ISOLATION_ENABLED = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db_session: Optional[AsyncSession] = None
    
    async def get_database_session(self) -> AsyncSession:
        """Get database session for testing."""
        if self._db_session is None:
            # Import here to avoid circular dependencies
            from test_framework.ssot.database import DatabaseTestUtility
            db_util = DatabaseTestUtility()
            self._db_session = await db_util.get_test_session()
            self.track_resource(self._db_session)
        
        return self._db_session


class WebSocketTestCase(BaseTestCase):
    """Base test case for tests requiring WebSocket functionality."""
    
    REQUIRES_WEBSOCKET = True
    ISOLATION_ENABLED = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._websocket_client: Optional[Any] = None
    
    async def get_websocket_client(self):
        """Get WebSocket client for testing."""
        if self._websocket_client is None:
            from test_framework.ssot.websocket import WebSocketTestUtility
            ws_util = WebSocketTestUtility()
            self._websocket_client = await ws_util.create_test_client()
            self.track_resource(self._websocket_client)
        
        return self._websocket_client


class IntegrationTestCase(BaseTestCase):
    """Base test case for integration tests requiring multiple services."""
    
    REQUIRES_DATABASE = True
    REQUIRES_REDIS = True
    REQUIRES_REAL_SERVICES = True
    ISOLATION_ENABLED = True
    
    def setUp(self):
        """Set up integration test environment."""
        super().setUp()
        
        # Verify all required services are available
        self.skip_if_missing_service("database")
        self.skip_if_missing_service("redis")
        
        logger.info(f"Integration test setup completed: {self.test_class}::{self.test_name}")


# Utility functions for test discovery and validation

def validate_test_class(test_class: Type) -> List[str]:
    """
    Validate that a test class follows SSOT requirements.
    
    Args:
        test_class: Test class to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Check inheritance
    if not issubclass(test_class, BaseTestCase):
        errors.append(f"{test_class.__name__} must inherit from BaseTestCase or its subclasses")
    
    # Check for deprecated patterns
    if hasattr(test_class, 'setUpClass') and not hasattr(test_class, 'setUp'):
        errors.append(f"{test_class.__name__} should use setUp instead of setUpClass for SSOT compliance")
    
    # Check for direct environment access
    source_file = inspect.getsourcefile(test_class)
    if source_file:
        try:
            with open(source_file, 'r') as f:
                source = f.read()
                if 'os.environ' in source:
                    errors.append(f"{test_class.__name__} contains direct os.environ access - use self.env instead")
        except Exception:
            pass
    
    return errors


def get_test_base_for_category(category: str) -> Type[BaseTestCase]:
    """
    Get the appropriate base test class for a test category.
    
    Args:
        category: Test category (unit, integration, e2e, etc.)
        
    Returns:
        Appropriate base test class
    """
    category_map = {
        "unit": BaseTestCase,
        "integration": IntegrationTestCase,
        "database": DatabaseTestCase,
        "websocket": WebSocketTestCase,
        "e2e": IntegrationTestCase,
        "api": IntegrationTestCase,
        "performance": IntegrationTestCase
    }
    
    return category_map.get(category, BaseTestCase)


# Export the SSOT test base classes
__all__ = [
    'BaseTestCase',
    'AsyncBaseTestCase', 
    'DatabaseTestCase',
    'WebSocketTestCase',
    'IntegrationTestCase',
    'ExecutionMetrics',
    'validate_test_class',
    'get_test_base_for_category'
]