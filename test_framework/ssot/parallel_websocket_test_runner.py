"""
SSOT Parallel WebSocket Test Runner

This module provides parallel execution capabilities for WebSocket isolation tests
that are marked as concurrent-safe, enabling faster test suite execution while
maintaining test isolation and reliability.

Business Value Justification:
- Segment: Platform/Internal - Development Velocity
- Business Goal: Reduce test execution time by 60%
- Value Impact: Faster developer feedback and CI/CD pipeline
- Revenue Impact: Protects development velocity for $2M+ ARR platform

@compliance CLAUDE.md - Real services only, no mocks in parallel execution
@compliance SPEC/core.xml - Maintain user isolation in parallel tests
"""

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Callable, Tuple
from enum import Enum

from test_framework.ssot.real_websocket_connection_manager import RealWebSocketConnectionManager
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient

logger = logging.getLogger(__name__)


class ParallelExecutionMode(Enum):
    """Parallel execution modes for WebSocket tests."""
    SEQUENTIAL = "sequential"
    THREAD_POOL = "thread_pool"
    ASYNC_CONCURRENT = "async_concurrent"
    PROCESS_POOL = "process_pool"  # For CPU-intensive validation


@dataclass
class ParallelTestResult:
    """Result from parallel test execution."""
    test_name: str
    execution_mode: ParallelExecutionMode
    success: bool
    execution_time: float
    connections_used: int
    isolation_violations: int
    error_message: Optional[str] = None
    concurrent_users: int = 0


@dataclass
class ParallelTestSuite:
    """A suite of tests that can be executed in parallel."""
    suite_name: str
    test_functions: List[Callable]
    max_concurrent_tests: int = 5
    execution_mode: ParallelExecutionMode = ParallelExecutionMode.ASYNC_CONCURRENT
    shared_connection_manager: Optional[RealWebSocketConnectionManager] = None


class ParallelWebSocketTestRunner:
    """
    SSOT Parallel Test Runner for WebSocket Isolation Tests.
    
    This runner enables safe parallel execution of WebSocket tests that are
    marked with @pytest.mark.concurrent_safe, significantly reducing test
    execution time while maintaining isolation guarantees.
    
    CRITICAL SAFETY FEATURES:
    - Each parallel test gets isolated connection manager
    - User isolation validation across parallel executions
    - Resource management to prevent Docker overload
    - Failure isolation (one test failure doesn't affect others)
    """
    
    def __init__(
        self,
        backend_url: str = "ws://localhost:8000",
        environment: str = "test",
        max_parallel_tests: int = 5,
        resource_limit_connections: int = 50
    ):
        """Initialize parallel test runner.
        
        Args:
            backend_url: WebSocket URL for backend service
            environment: Test environment
            max_parallel_tests: Maximum tests to run concurrently
            resource_limit_connections: Total connection limit across all tests
        """
        self.backend_url = backend_url
        self.environment = environment
        self.max_parallel_tests = max_parallel_tests
        self.resource_limit_connections = resource_limit_connections
        
        # Test execution state
        self.runner_id = f"parallel_runner_{uuid.uuid4().hex[:8]}"
        self.active_tests: Dict[str, asyncio.Task] = {}
        self.completed_results: List[ParallelTestResult] = []
        self.total_connections_used = 0
        
        # Resource management
        self.connection_semaphore = asyncio.Semaphore(resource_limit_connections)
        self.test_semaphore = asyncio.Semaphore(max_parallel_tests)
        
        logger.info(f"Initialized ParallelWebSocketTestRunner: {self.runner_id}")
    
    async def execute_parallel_test_suite(
        self,
        test_suite: ParallelTestSuite
    ) -> List[ParallelTestResult]:
        """Execute a suite of tests in parallel.
        
        Args:
            test_suite: Test suite configuration
            
        Returns:
            List of test results from parallel execution
            
        Raises:
            RuntimeError: If parallel execution setup fails
        """
        logger.info(f"[U+1F680] Starting parallel execution of {test_suite.suite_name}")
        start_time = time.time()
        
        if test_suite.execution_mode == ParallelExecutionMode.ASYNC_CONCURRENT:
            results = await self._execute_async_concurrent(test_suite)
        elif test_suite.execution_mode == ParallelExecutionMode.THREAD_POOL:
            results = await self._execute_thread_pool(test_suite)
        elif test_suite.execution_mode == ParallelExecutionMode.PROCESS_POOL:
            results = await self._execute_process_pool(test_suite)
        else:
            # Fallback to sequential
            results = await self._execute_sequential(test_suite)
        
        total_time = time.time() - start_time
        successful_tests = sum(1 for r in results if r.success)
        
        logger.info(
            f" PASS:  Parallel test suite completed: {test_suite.suite_name}\n"
            f"   Execution mode: {test_suite.execution_mode.value}\n"
            f"   Tests run: {len(results)}\n"
            f"   Successful: {successful_tests}/{len(results)}\n"
            f"   Total time: {total_time:.2f}s\n"
            f"   Connections used: {sum(r.connections_used for r in results)}"
        )
        
        return results
    
    async def _execute_async_concurrent(
        self,
        test_suite: ParallelTestSuite
    ) -> List[ParallelTestResult]:
        """Execute tests using async concurrency (fastest)."""
        tasks = []
        
        for test_func in test_suite.test_functions:
            task = asyncio.create_task(
                self._run_single_test_async(test_func, test_suite)
            )
            tasks.append(task)
        
        # Execute all tasks concurrently with semaphore limiting
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed test results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ParallelTestResult(
                    test_name=test_suite.test_functions[i].__name__,
                    execution_mode=test_suite.execution_mode,
                    success=False,
                    execution_time=0.0,
                    connections_used=0,
                    isolation_violations=0,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _run_single_test_async(
        self,
        test_func: Callable,
        test_suite: ParallelTestSuite
    ) -> ParallelTestResult:
        """Run a single test with async isolation."""
        async with self.test_semaphore:  # Limit concurrent tests
            test_start = time.time()
            test_name = test_func.__name__
            
            logger.debug(f"Starting parallel test: {test_name}")
            
            # Create isolated connection manager for this test
            connection_manager = RealWebSocketConnectionManager(
                backend_url=self.backend_url,
                environment=self.environment,
                max_connections=10  # Limit per test
            )
            
            try:
                # Enable connection pooling for efficiency
                connection_manager.enable_connection_pool(True)
                
                # Execute the test function
                await test_func(connection_manager)
                
                # Get test metrics
                isolation_summary = connection_manager.get_isolation_summary()
                pool_stats = connection_manager.get_pool_statistics()
                
                execution_time = time.time() - test_start
                
                result = ParallelTestResult(
                    test_name=test_name,
                    execution_mode=test_suite.execution_mode,
                    success=isolation_summary['test_passed'],
                    execution_time=execution_time,
                    connections_used=isolation_summary['total_connections'],
                    isolation_violations=isolation_summary['global_violations'],
                    concurrent_users=isolation_summary['total_connections']
                )
                
                logger.debug(
                    f" PASS:  Parallel test completed: {test_name} "
                    f"({execution_time:.2f}s, {result.connections_used} connections)"
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - test_start
                logger.error(f" FAIL:  Parallel test failed: {test_name}: {e}")
                
                return ParallelTestResult(
                    test_name=test_name,
                    execution_mode=test_suite.execution_mode,
                    success=False,
                    execution_time=execution_time,
                    connections_used=0,
                    isolation_violations=0,
                    error_message=str(e)
                )
            
            finally:
                # Always cleanup the connection manager
                await connection_manager.cleanup_all_connections()
    
    async def _execute_sequential(
        self,
        test_suite: ParallelTestSuite
    ) -> List[ParallelTestResult]:
        """Fallback sequential execution."""
        results = []
        
        for test_func in test_suite.test_functions:
            result = await self._run_single_test_async(test_func, test_suite)
            result.execution_mode = ParallelExecutionMode.SEQUENTIAL
            results.append(result)
        
        return results
    
    async def _execute_thread_pool(
        self,
        test_suite: ParallelTestSuite
    ) -> List[ParallelTestResult]:
        """Execute tests using thread pool (for I/O bound tests)."""
        # For now, delegate to async concurrent
        # Thread pool execution would require more complex setup
        # with sync wrappers for async functions
        return await self._execute_async_concurrent(test_suite)
    
    async def _execute_process_pool(
        self,
        test_suite: ParallelTestSuite
    ) -> List[ParallelTestResult]:
        """Execute tests using process pool (for CPU intensive validation)."""
        # For now, delegate to async concurrent
        # Process pool would require serializable test functions
        return await self._execute_async_concurrent(test_suite)
    
    def create_test_suite(
        self,
        suite_name: str,
        test_functions: List[Callable],
        execution_mode: ParallelExecutionMode = ParallelExecutionMode.ASYNC_CONCURRENT
    ) -> ParallelTestSuite:
        """Create a parallel test suite.
        
        Args:
            suite_name: Name for the test suite
            test_functions: List of test functions to execute
            execution_mode: How to execute the tests in parallel
            
        Returns:
            Configured ParallelTestSuite
        """
        return ParallelTestSuite(
            suite_name=suite_name,
            test_functions=test_functions,
            max_concurrent_tests=self.max_parallel_tests,
            execution_mode=execution_mode
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary of parallel execution.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.completed_results:
            return {"no_tests_executed": True}
        
        total_time = sum(r.execution_time for r in self.completed_results)
        successful_tests = sum(1 for r in self.completed_results if r.success)
        total_connections = sum(r.connections_used for r in self.completed_results)
        total_violations = sum(r.isolation_violations for r in self.completed_results)
        
        # Estimate sequential execution time (rough approximation)
        estimated_sequential_time = total_time  # Would be sum if truly sequential
        actual_parallel_time = max(r.execution_time for r in self.completed_results)
        speedup_factor = estimated_sequential_time / actual_parallel_time if actual_parallel_time > 0 else 1.0
        
        return {
            "runner_id": self.runner_id,
            "total_tests": len(self.completed_results),
            "successful_tests": successful_tests,
            "failed_tests": len(self.completed_results) - successful_tests,
            "total_execution_time": total_time,
            "estimated_parallel_speedup": speedup_factor,
            "total_connections_used": total_connections,
            "total_isolation_violations": total_violations,
            "average_test_time": total_time / len(self.completed_results),
            "tests_passed_isolation": total_violations == 0
        }


# Convenience functions for common parallel test patterns

async def run_isolation_tests_parallel(
    test_functions: List[Callable],
    backend_url: str = "ws://localhost:8000",
    max_concurrent: int = 5
) -> List[ParallelTestResult]:
    """Run a list of isolation test functions in parallel.
    
    Args:
        test_functions: List of test functions marked @concurrent_safe
        backend_url: WebSocket backend URL
        max_concurrent: Maximum concurrent tests
        
    Returns:
        List of test results
    """
    runner = ParallelWebSocketTestRunner(
        backend_url=backend_url,
        max_parallel_tests=max_concurrent
    )
    
    test_suite = runner.create_test_suite(
        suite_name="parallel_isolation_tests",
        test_functions=test_functions,
        execution_mode=ParallelExecutionMode.ASYNC_CONCURRENT
    )
    
    return await runner.execute_parallel_test_suite(test_suite)


def mark_concurrent_safe(test_func):
    """Decorator to mark a test function as safe for concurrent execution.
    
    Usage:
    @mark_concurrent_safe
    async def test_user_isolation():
        # Test implementation that doesn't interfere with other tests
        pass
    """
    # Add metadata to indicate concurrent safety
    test_func._concurrent_safe = True
    test_func._requires_isolation = True
    return test_func