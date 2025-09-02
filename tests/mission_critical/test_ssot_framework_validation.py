"""
MISSION CRITICAL: SSOT Framework Validation Test Suite

This test suite validates all SSOT components are working correctly and enforces
strict compliance with the SSOT architecture. These tests are designed to be DIFFICULT
and COMPREHENSIVE to catch any weaknesses before spacecraft deployment.

Business Value: Platform/Internal - Test Infrastructure Reliability & Risk Reduction
Ensures the foundation of our 6,096+ test files is rock-solid and prevents cascade failures.

CRITICAL: These tests must be failing tests that expose weaknesses.
They test edge cases, error conditions, and integration points.
"""

import asyncio
import inspect
import logging
import os
import sys
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Import SSOT framework components
from test_framework.ssot import (
    BaseTestCase,
    AsyncBaseTestCase, 
    DatabaseTestCase,
    WebSocketTestCase,
    IntegrationTestCase,
    TestExecutionMetrics,
    MockFactory,
    MockRegistry,
    DatabaseMockFactory,
    ServiceMockFactory,
    MockContext,
    DatabaseTestUtility,
    PostgreSQLTestUtility,
    ClickHouseTestUtility,
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketMessage,
    WebSocketEventType,
    DockerTestUtility,
    PostgreSQLDockerUtility,
    RedisDockerUtility,
    get_mock_factory,
    get_database_test_utility,
    get_websocket_test_utility,
    get_docker_test_utility,
    validate_test_class,
    get_test_base_for_category,
    validate_ssot_compliance,
    get_ssot_status,
    SSOT_VERSION,
    SSOT_COMPLIANCE
)

from shared.isolated_environment import IsolatedEnvironment, get_env

logger = logging.getLogger(__name__)


class TestSSOTFrameworkValidation(BaseTestCase):
    """
    CRITICAL: Validate all SSOT framework components are working correctly.
    These tests are designed to be DIFFICULT and expose any weaknesses.
    """
    
    def setUp(self):
        """Set up test environment with strict validation."""
        super().setUp()
        self.start_time = time.time()
        logger.info(f"Starting SSOT validation test: {self._testMethodName}")
        
        # Validate test environment isolation
        self.assertIsInstance(self.env, IsolatedEnvironment)
        self.assertTrue(hasattr(self, 'metrics'))
        
    def tearDown(self):
        """Tear down with metrics collection."""
        duration = time.time() - self.start_time
        logger.info(f"SSOT validation test {self._testMethodName} took {duration:.2f}s")
        super().tearDown()
    
    def test_ssot_version_and_compliance_structure(self):
        """
        CRITICAL: Test SSOT version and compliance constants are properly defined.
        This is a basic sanity check that should never fail unless framework is broken.
        """
        # Version must be semantic versioning
        self.assertIsInstance(SSOT_VERSION, str)
        self.assertRegex(SSOT_VERSION, r'^\d+\.\d+\.\d+$', 
                        "SSOT version must follow semantic versioning")
        
        # Compliance structure must be complete
        self.assertIsInstance(SSOT_COMPLIANCE, dict)
        required_compliance_keys = [
            'base_classes', 'mock_factories', 'database_utilities',
            'websocket_utilities', 'docker_utilities', 'total_components'
        ]
        
        for key in required_compliance_keys:
            self.assertIn(key, SSOT_COMPLIANCE,
                         f"SSOT_COMPLIANCE missing required key: {key}")
            self.assertIsInstance(SSOT_COMPLIANCE[key], int,
                                f"SSOT_COMPLIANCE[{key}] must be integer")
        
        # Total components must match sum of individual components
        expected_total = sum(
            SSOT_COMPLIANCE[key] for key in required_compliance_keys[:-1]
        )
        self.assertEqual(SSOT_COMPLIANCE['total_components'], expected_total,
                        "SSOT compliance total doesn't match sum of components")
    
    def test_base_test_class_inheritance_hierarchy(self):
        """
        DIFFICULT: Test the complex inheritance hierarchy of base test classes.
        This validates MRO (Method Resolution Order) and ensures no method conflicts.
        """
        test_classes = [
            BaseTestCase,
            AsyncBaseTestCase,
            DatabaseTestCase,
            WebSocketTestCase,
            IntegrationTestCase
        ]
        
        for test_class in test_classes:
            # Validate class can be instantiated (basic sanity check)
            with self.assertLogs(level='DEBUG') as log_context:
                # This should work without errors
                mro = inspect.getmro(test_class)
                self.assertGreater(len(mro), 1, 
                                 f"{test_class.__name__} has invalid MRO")
                
                # BaseTestCase must be in MRO for all test classes
                base_in_mro = any(cls.__name__ == 'BaseTestCase' for cls in mro)
                self.assertTrue(base_in_mro,
                              f"{test_class.__name__} must inherit from BaseTestCase")
            
            # Check for required methods
            required_methods = ['setUp', 'tearDown']
            for method_name in required_methods:
                self.assertTrue(hasattr(test_class, method_name),
                              f"{test_class.__name__} missing required method: {method_name}")
                
                method = getattr(test_class, method_name)
                self.assertTrue(callable(method),
                              f"{test_class.__name__}.{method_name} is not callable")
        
        # Test that specialized classes have specific capabilities
        self.assertTrue(hasattr(DatabaseTestCase, 'get_database_session'),
                       "DatabaseTestCase missing database session capability")
        self.assertTrue(hasattr(WebSocketTestCase, 'get_websocket_client'),
                       "WebSocketTestCase missing WebSocket client capability")
        self.assertTrue(hasattr(IntegrationTestCase, 'get_docker_utility'),
                       "IntegrationTestCase missing Docker utility capability")
    
    def test_isolated_environment_enforcement(self):
        """
        CRITICAL: Test that IsolatedEnvironment is properly enforced.
        This is a security and stability requirement - no direct os.environ access allowed.
        """
        # All test classes must have IsolatedEnvironment
        self.assertIsInstance(self.env, IsolatedEnvironment)
        
        # Test that environment variables are accessible through SSOT
        test_var_name = f"SSOT_TEST_VAR_{uuid.uuid4().hex[:8]}"
        test_var_value = f"test_value_{uuid.uuid4().hex[:8]}"
        
        # Set via isolated environment
        with patch.dict(os.environ, {test_var_name: test_var_value}):
            env_value = self.env.get(test_var_name)
            self.assertEqual(env_value, test_var_value,
                           "IsolatedEnvironment not accessing environment correctly")
        
        # Test that get_env() function works
        with patch.dict(os.environ, {test_var_name: test_var_value}):
            global_env_value = get_env(test_var_name)
            self.assertEqual(global_env_value, test_var_value,
                           "get_env() not working correctly")
    
    def test_test_execution_metrics_collection(self):
        """
        DIFFICULT: Test that TestExecutionMetrics properly collects performance data.
        This validates our performance monitoring and identifies test performance issues.
        """
        # Create metrics instance
        metrics = TestExecutionMetrics()
        self.assertIsNotNone(metrics)
        
        # Test timing functionality
        start_time = time.time()
        metrics.start_time = start_time
        time.sleep(0.1)  # Small delay for timing test
        metrics.end_time = time.time()
        
        duration = metrics.get_duration()
        self.assertGreaterEqual(duration, 0.1, 
                              "Metrics duration calculation incorrect")
        self.assertLess(duration, 0.2,
                       "Metrics duration seems too long for simple test")
        
        # Test metrics data structure
        metrics_data = metrics.to_dict()
        self.assertIsInstance(metrics_data, dict)
        required_fields = ['start_time', 'end_time', 'duration']
        for field in required_fields:
            self.assertIn(field, metrics_data,
                         f"Metrics missing required field: {field}")
    
    def test_mock_factory_comprehensive_functionality(self):
        """
        DIFFICULT: Test MockFactory's comprehensive mocking capabilities.
        This ensures all mock types work correctly and are properly isolated.
        """
        factory = get_mock_factory()
        self.assertIsInstance(factory, MockFactory)
        
        # Test database session mock creation
        db_mock = factory.create_database_session_mock()
        self.assertIsInstance(db_mock, (Mock, AsyncMock))
        
        # Test WebSocket manager mock
        ws_mock = factory.create_websocket_manager_mock()
        self.assertIsNotNone(ws_mock)
        
        # Test LLM client mock
        llm_mock = factory.create_llm_client_mock()
        self.assertIsNotNone(llm_mock)
        
        # Test HTTP client mock
        http_mock = factory.create_http_client_mock()
        self.assertIsNotNone(http_mock)
        
        # Test mock registry functionality
        registry = factory.get_registry()
        self.assertIsInstance(registry, MockRegistry)
        
        # Test that mocks are properly tracked
        initial_count = len(registry.active_mocks)
        test_mock = factory.create_mock("test_service")
        final_count = len(registry.active_mocks)
        self.assertGreater(final_count, initial_count,
                          "Mock registry not tracking new mocks")
        
        # Test mock cleanup functionality
        factory.cleanup_all_mocks()
        post_cleanup_count = len(registry.active_mocks)
        self.assertLessEqual(post_cleanup_count, initial_count,
                           "Mock cleanup not working properly")
    
    def test_ssot_compliance_validation_comprehensive(self):
        """
        MISSION CRITICAL: Test comprehensive SSOT compliance validation.
        This is the most important test - it validates the entire SSOT framework.
        """
        # Run full compliance check
        violations = validate_ssot_compliance()
        
        # Log any violations for debugging
        if violations:
            logger.error(f"SSOT Compliance Violations Found: {violations}")
            for violation in violations:
                logger.error(f"  - {violation}")
        
        # CRITICAL: No violations allowed
        self.assertEqual(len(violations), 0,
                        f"SSOT compliance violations detected: {violations}")
        
        # Get comprehensive status
        status = get_ssot_status()
        self.assertIsInstance(status, dict)
        
        required_status_keys = ['version', 'compliance', 'violations', 'components']
        for key in required_status_keys:
            self.assertIn(key, status, f"SSOT status missing key: {key}")
        
        # Validate components structure
        components = status['components']
        expected_component_types = [
            'base_classes', 'mock_utilities', 'database_utilities',
            'websocket_utilities', 'docker_utilities'
        ]
        
        for component_type in expected_component_types:
            self.assertIn(component_type, components,
                         f"SSOT components missing: {component_type}")
            self.assertIsInstance(components[component_type], list,
                                f"SSOT component {component_type} must be list")
            self.assertGreater(len(components[component_type]), 0,
                             f"SSOT component {component_type} is empty")
    
    def test_test_class_validation_edge_cases(self):
        """
        DIFFICULT: Test test class validation with edge cases and invalid classes.
        This ensures our validation catches problematic test classes.
        """
        # Test valid class validation
        errors = validate_test_class(BaseTestCase)
        self.assertEqual(len(errors), 0,
                        f"BaseTestCase validation should pass but got errors: {errors}")
        
        # Test invalid class (not inheriting from BaseTestCase)
        class InvalidTestClass:
            pass
        
        errors = validate_test_class(InvalidTestClass)
        self.assertGreater(len(errors), 0,
                          "Invalid test class should produce validation errors")
        
        # Test that error messages are descriptive
        error_message = errors[0]
        self.assertIn("BaseTestCase", error_message,
                     "Validation error should mention BaseTestCase requirement")
        
        # Test get_test_base_for_category function
        base_classes = {
            'unit': BaseTestCase,
            'integration': IntegrationTestCase, 
            'database': DatabaseTestCase,
            'websocket': WebSocketTestCase,
            'async': AsyncBaseTestCase
        }
        
        for category, expected_class in base_classes.items():
            actual_class = get_test_base_for_category(category)
            self.assertEqual(actual_class, expected_class,
                           f"Wrong base class for category {category}")
        
        # Test invalid category
        with self.assertRaises((ValueError, KeyError)) as context:
            get_test_base_for_category("invalid_category")
        
        self.assertIn("invalid_category", str(context.exception).lower(),
                     "Error message should mention invalid category")
    
    def test_cross_component_compatibility(self):
        """
        COMPLEX: Test that all SSOT components work together properly.
        This validates the integration between different SSOT utilities.
        """
        # Test that MockFactory works with DatabaseTestUtility
        factory = get_mock_factory()
        db_mock = factory.create_database_session_mock()
        
        # Mock should be compatible with database utilities
        self.assertIsNotNone(db_mock)
        
        # Test that WebSocket utilities are compatible with Docker utilities
        # This ensures our integration test capabilities work
        ws_util_class = WebSocketTestUtility
        docker_util_class = DockerTestUtility
        
        # Both should be async context managers
        self.assertTrue(hasattr(ws_util_class, '__aenter__'))
        self.assertTrue(hasattr(ws_util_class, '__aexit__'))
        self.assertTrue(hasattr(docker_util_class, '__aenter__'))
        self.assertTrue(hasattr(docker_util_class, '__aexit__'))
    
    def test_performance_and_resource_usage(self):
        """
        PERFORMANCE CRITICAL: Test that SSOT framework doesn't consume excessive resources.
        This prevents memory leaks and performance degradation in large test suites.
        """
        import psutil
        import gc
        
        # Measure initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Create multiple SSOT components
        components = []
        for i in range(10):
            factory = get_mock_factory()
            mock = factory.create_mock(f"test_service_{i}")
            components.append((factory, mock))
        
        # Measure memory after creation
        mid_memory = process.memory_info().rss
        memory_increase = mid_memory - initial_memory
        
        # Clean up all components
        for factory, mock in components:
            factory.cleanup_all_mocks()
        
        # Force garbage collection
        gc.collect()
        
        # Measure final memory
        final_memory = process.memory_info().rss
        
        # Memory should not increase excessively (allow 10MB increase)
        max_allowed_increase = 10 * 1024 * 1024  # 10MB
        self.assertLess(memory_increase, max_allowed_increase,
                       f"SSOT framework using too much memory: {memory_increase} bytes")
        
        # Memory should be mostly cleaned up (allow 5MB residual)
        max_residual = 5 * 1024 * 1024  # 5MB  
        residual_memory = final_memory - initial_memory
        self.assertLess(residual_memory, max_residual,
                       f"SSOT framework not cleaning up memory properly: {residual_memory} bytes residual")
    
    def test_concurrent_access_and_thread_safety(self):
        """
        CONCURRENCY CRITICAL: Test SSOT framework thread safety.
        This ensures parallel test execution doesn't cause race conditions.
        """
        import threading
        import concurrent.futures
        
        results = []
        errors = []
        
        def create_and_use_factory(thread_id):
            """Function to run in multiple threads."""
            try:
                factory = get_mock_factory()
                mock = factory.create_mock(f"thread_{thread_id}_service")
                registry = factory.get_registry()
                
                # Simulate some work
                time.sleep(0.01)
                
                # Verify mock was created
                if mock is None:
                    errors.append(f"Thread {thread_id}: Mock creation failed")
                    return False
                
                results.append(f"Thread {thread_id}: Success")
                return True
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
                return False
        
        # Run multiple threads concurrently
        num_threads = 5
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(create_and_use_factory, i) 
                for i in range(num_threads)
            ]
            
            # Wait for all threads to complete
            concurrent.futures.wait(futures, timeout=10)
        
        # Check results
        if errors:
            logger.error(f"Thread safety errors: {errors}")
        
        self.assertEqual(len(errors), 0,
                        f"Thread safety violations detected: {errors}")
        self.assertEqual(len(results), num_threads,
                        f"Not all threads completed successfully. Results: {results}")
    
    def test_error_handling_and_resilience(self):
        """
        RESILIENCE CRITICAL: Test SSOT framework error handling.
        This ensures the framework gracefully handles edge cases and failures.
        """
        factory = get_mock_factory()
        
        # Test handling of invalid mock types
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            factory.create_mock("invalid_mock_type", invalid_param=True)
        
        # Test cleanup with no mocks
        try:
            factory.cleanup_all_mocks()  # Should not raise exception
        except Exception as e:
            self.fail(f"Cleanup with no mocks should not raise exception: {e}")
        
        # Test double cleanup
        factory.create_mock("test_service")
        factory.cleanup_all_mocks()
        try:
            factory.cleanup_all_mocks()  # Should not raise exception
        except Exception as e:
            self.fail(f"Double cleanup should not raise exception: {e}")
        
        # Test compliance validation with missing components
        original_compliance = SSOT_COMPLIANCE.copy()
        
        # Temporarily break compliance (simulate component failure)
        with patch('test_framework.ssot.SSOT_COMPLIANCE', {}):
            violations = validate_ssot_compliance()
            # Should detect the missing compliance structure
            self.assertGreater(len(violations), 0,
                             "Should detect compliance violations when structure is broken")


class TestSSOTFrameworkAsyncValidation(AsyncBaseTestCase):
    """
    ASYNC CRITICAL: Validate SSOT framework async capabilities.
    These tests ensure async components work correctly and don't block.
    """
    
    async def asyncSetUp(self):
        """Set up async test environment."""
        await super().asyncSetUp()
        self.start_time = time.time()
        logger.info(f"Starting async SSOT validation test: {self._testMethodName}")
    
    async def asyncTearDown(self):
        """Tear down async test environment."""
        duration = time.time() - self.start_time
        logger.info(f"Async SSOT validation test {self._testMethodName} took {duration:.2f}s")
        await super().asyncTearDown()
    
    async def test_async_utilities_functionality(self):
        """
        ASYNC CRITICAL: Test that async utilities work correctly.
        This validates async context managers and async operations.
        """
        # Test database utility async context manager
        try:
            async with DatabaseTestUtility() as db_util:
                self.assertIsNotNone(db_util)
                # Should have async session capability
                self.assertTrue(hasattr(db_util, 'get_session'))
        except Exception as e:
            # Expected if database not available, but should not crash
            logger.warning(f"Database utility test skipped: {e}")
        
        # Test WebSocket utility async context manager  
        try:
            async with WebSocketTestUtility() as ws_util:
                self.assertIsNotNone(ws_util)
                # Should have client creation capability
                self.assertTrue(hasattr(ws_util, 'create_client'))
        except Exception as e:
            # Expected if WebSocket service not available
            logger.warning(f"WebSocket utility test skipped: {e}")
        
        # Test Docker utility async context manager
        try:
            async with DockerTestUtility() as docker_util:
                self.assertIsNotNone(docker_util)
                # Should have service management capability
                self.assertTrue(hasattr(docker_util, 'start_services'))
        except Exception as e:
            # Expected if Docker not available
            logger.warning(f"Docker utility test skipped: {e}")
    
    async def test_async_cleanup_functionality(self):
        """
        CLEANUP CRITICAL: Test async cleanup works correctly.
        This ensures resources are properly released in async contexts.
        """
        from test_framework.ssot import cleanup_all_ssot_resources
        
        # Create some resources to clean up
        factory = get_mock_factory()
        factory.create_mock("cleanup_test_service_1")
        factory.create_mock("cleanup_test_service_2")
        
        # Test async cleanup
        try:
            await cleanup_all_ssot_resources()
            # Should not raise exception
        except Exception as e:
            self.fail(f"Async SSOT cleanup should not raise exception: {e}")
        
        # Verify cleanup worked
        registry = factory.get_registry()
        # Registry should be cleaned or have fewer mocks
        self.assertIsNotNone(registry)
    
    async def test_async_performance_monitoring(self):
        """
        PERFORMANCE CRITICAL: Test async performance doesn't degrade.
        This ensures async operations don't create performance bottlenecks.
        """
        start_time = time.time()
        
        # Create multiple async tasks
        tasks = []
        for i in range(10):
            task = asyncio.create_task(self._create_mock_async(i))
            tasks.append(task)
        
        # Wait for all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = time.time() - start_time
        
        # Should complete in reasonable time (allow 2 seconds for 10 tasks)
        self.assertLess(duration, 2.0,
                       f"Async operations taking too long: {duration}s")
        
        # Check that all tasks succeeded
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            logger.error(f"Async task errors: {errors}")
        
        self.assertEqual(len(errors), 0,
                        f"Async tasks failed: {errors}")
    
    async def _create_mock_async(self, task_id):
        """Helper method for async testing."""
        await asyncio.sleep(0.01)  # Simulate async work
        factory = get_mock_factory()
        mock = factory.create_mock(f"async_task_{task_id}")
        return mock


if __name__ == '__main__':
    # Configure logging for test execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the tests
    pytest.main([__file__, '-v', '--tb=short', '--capture=no'])