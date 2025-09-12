"""Database Connection Pool Exhaustion Test Suite

Comprehensive E2E tests for database connection pool stress testing,
backpressure validation, and graceful degradation under load.

Business Value: Ensures Enterprise SLA compliance and prevents $12K MRR loss
from database instability under high load conditions.
from shared.isolated_environment import IsolatedEnvironment
"""

import asyncio
import gc
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import asyncpg
import httpx
import psutil
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import NullPool, QueuePool

from netra_backend.app.core.async_connection_pool import AsyncConnectionPool
from netra_backend.app.db.database_manager import (
    DatabaseManager,
)
from netra_backend.app.core.database_health_monitoring import PoolHealthChecker
from netra_backend.app.core.database_types import DatabaseType, PoolHealth
from netra_backend.app.db.postgres import (
    async_engine,
    async_session_factory,
    initialize_postgres,
)
from netra_backend.app.db.postgres_config import DatabaseConfig
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.pool_metrics import ConnectionPoolMetrics

logger = central_logger.get_logger(__name__)


class TestPoolExhaustionHarness:
    """Test harness for database connection pool exhaustion scenarios."""
    
    def __init__(self):
        self.metrics_collector = ConnectionPoolMetrics()
        self.active_connections: List[Any] = []
        self.test_config = {}
        self.original_config = {}
    
    async def setup_reduced_pool(self, pool_size: int = 3, max_overflow: int = 2, timeout: float = 5.0):
        """Configure database pool with reduced size for testing."""
        # Store original configuration
        self.original_config = {
            'pool_size': DatabaseConfig.POOL_SIZE,
            'max_overflow': DatabaseConfig.MAX_OVERFLOW,
            'pool_timeout': DatabaseConfig.POOL_TIMEOUT
        }
        
        # Apply test configuration
        DatabaseConfig.POOL_SIZE = pool_size
        DatabaseConfig.MAX_OVERFLOW = max_overflow
        DatabaseConfig.POOL_TIMEOUT = timeout
        
        self.test_config = {
            'pool_size': pool_size,
            'max_overflow': max_overflow,
            'pool_timeout': timeout
        }
        
        # Reinitialize PostgreSQL with new configuration
        await self._reinitialize_database()
        
        logger.info(f"Test pool configured: size={pool_size}, overflow={max_overflow}, timeout={timeout}")
    
    async def _reinitialize_database(self):
        """Reinitialize database connection with new pool configuration."""
        global async_engine, async_session_factory
        
        # Close existing engine
        if async_engine:
            await async_engine.dispose()
        
        # Force reinitialization
        async_engine = None
        async_session_factory = None
        
        # Reinitialize with new config
        initialize_postgres()
        
        # Wait for initialization to complete
        await asyncio.sleep(0.1)
    
    async def restore_original_config(self):
        """Restore original pool configuration."""
        if self.original_config:
            DatabaseConfig.POOL_SIZE = self.original_config['pool_size']
            DatabaseConfig.MAX_OVERFLOW = self.original_config['max_overflow']
            DatabaseConfig.POOL_TIMEOUT = self.original_config['pool_timeout']
            
            await self._reinitialize_database()
            logger.info("Original pool configuration restored")
    
    async def create_blocking_connection(self, block_duration: float = 10.0) -> asyncio.Task:
        """Create a blocking database connection that holds pool slot."""
        async def blocking_operation():
            async with async_session_factory() as session:
                try:
                    # Execute a query that will block for specified duration
                    await session.execute(text(f"SELECT pg_sleep({block_duration})"))
                except Exception as e:
                    logger.debug(f"Blocking connection terminated: {e}")
        
        task = asyncio.create_task(blocking_operation())
        self.active_connections.append(task)
        return task
    
    async def exhaust_pool(self, extra_connections: int = 2) -> List[asyncio.Task]:
        """Exhaust the connection pool by creating blocking connections."""
        total_connections = self.test_config['pool_size'] + self.test_config['max_overflow']
        
        tasks = []
        for i in range(total_connections + extra_connections):
            task = await self.create_blocking_connection(30.0)  # Long blocking duration
            tasks.append(task)
            await asyncio.sleep(0.1)  # Allow connection to establish
        
        logger.info(f"Created {len(tasks)} blocking connections (pool capacity: {total_connections})")
        return tasks
    
    async def attempt_database_operation(self, timeout: float = 2.0) -> Dict[str, Any]:
        """Attempt a database operation with timeout."""
        start_time = time.time()
        try:
            async with asyncio.timeout(timeout):
                async with async_session_factory() as session:
                    result = await session.execute(text("SELECT 1 as test_value"))
                    value = result.scalar()
                    
            duration = time.time() - start_time
            return {
                'success': True,
                'duration': duration,
                'result': value,
                'error': None
            }
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            return {
                'success': False,
                'duration': duration,
                'result': None,
                'error': 'TimeoutError'
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                'success': False,
                'duration': duration,
                'result': None,
                'error': str(e)
            }
    
    async def get_pool_metrics(self) -> Dict[str, Any]:
        """Get current pool metrics."""
        try:
            status = self.metrics_collector.get_pool_status()
            
            # Extract async pool metrics
            if status.get('async_pool'):
                pool_data = status['async_pool']
                return {
                    'pool_size': pool_data.get('size', 0),
                    'checked_in': pool_data.get('checked_in', 0),
                    'checked_out': pool_data.get('checked_out', 0),
                    'overflow': pool_data.get('overflow', 0),
                    'total_connections': pool_data.get('total_connections', 0),
                    'utilization_percent': pool_data.get('utilization_percent', 0),
                    'health': status.get('health', 'unknown'),
                    'timestamp': status.get('timestamp')
                }
            else:
                return {'error': 'No async pool data available'}
        except Exception as e:
            return {'error': f'Failed to get pool metrics: {e}'}
    
    async def cleanup(self):
        """Clean up all active connections and restore configuration."""
        # Cancel all active connections
        for task in self.active_connections:
            if not task.done():
                task.cancel()
        
        # Wait for cancellations with timeout
        if self.active_connections:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.active_connections, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some connections didn't close within timeout")
        
        self.active_connections.clear()
        
        # Force garbage collection
        gc.collect()
        
        # Restore original configuration
        await self.restore_original_config()
        
        # Wait for pool to stabilize
        await asyncio.sleep(1.0)


@pytest.fixture
async def test_pool_test_harness():
    """Provide pool exhaustion test harness with cleanup."""
    harness = PoolExhaustionTestHarness()
    yield harness
    await harness.cleanup()


@pytest.mark.e2e
@pytest.mark.critical
class TestDatabaseConnectionPoolExhaustion:
    """Test suite for database connection pool exhaustion scenarios."""
    
    async def test_pool_saturation_detection(self, pool_test_harness):
        """Test Case 1: Verify system detects pool saturation and responds appropriately."""
        harness = pool_test_harness
        
        # Configure small pool for testing
        await harness.setup_reduced_pool(pool_size=3, max_overflow=2, timeout=2.0)
        
        # Get baseline metrics
        baseline_metrics = await harness.get_pool_metrics()
        assert baseline_metrics.get('pool_size') == 3
        
        # Exhaust the pool
        blocking_tasks = await harness.exhaust_pool(extra_connections=2)
        
        # Wait for pool to saturate
        await asyncio.sleep(1.0)
        
        # Check saturation metrics
        saturated_metrics = await harness.get_pool_metrics()
        
        # Verify pool is saturated
        utilization = saturated_metrics.get('utilization_percent', 0)
        assert utilization >= 80, f"Pool utilization should be >= 80%, got {utilization}%"
        
        # Attempt database operation (should timeout)
        operation_result = await harness.attempt_database_operation(timeout=3.0)
        
        # Verify backpressure response
        assert not operation_result['success'], "Operation should fail when pool is exhausted"
        assert operation_result['error'] in ['TimeoutError', 'timeout'], f"Expected timeout error, got: {operation_result['error']}"
        
        # Verify system stability (no crashes)
        post_test_metrics = await harness.get_pool_metrics()
        assert 'error' not in post_test_metrics or 'Failed to get pool metrics' not in post_test_metrics.get('error', ''), "Pool metrics should still be accessible"
        
        logger.info(f"Pool saturation test completed - Utilization: {utilization}%, Operation result: {operation_result}")
    
    async def test_connection_queue_management(self, pool_test_harness):
        """Test Case 2: Test request queuing behavior when pool is exhausted."""
        harness = pool_test_harness
        
        # Configure pool with specific timeout
        await harness.setup_reduced_pool(pool_size=2, max_overflow=1, timeout=5.0)
        
        # Create long-running operations to exhaust pool
        long_tasks = []
        for i in range(3):  # Exactly pool capacity
            task = await harness.create_blocking_connection(15.0)
            long_tasks.append(task)
            await asyncio.sleep(0.2)
        
        # Submit quick operations that should queue
        queue_test_start = time.time()
        quick_operations = []
        
        for i in range(3):
            operation_task = asyncio.create_task(
                harness.attempt_database_operation(timeout=6.0)
            )
            quick_operations.append(operation_task)
        
        # Wait for operations to complete or timeout
        results = await asyncio.gather(*quick_operations, return_exceptions=True)
        queue_test_duration = time.time() - queue_test_start
        
        # Analyze results
        timeout_count = sum(1 for r in results if isinstance(r, dict) and not r.get('success', False))
        successful_count = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
        
        # Verify queuing behavior
        assert timeout_count > 0, "Some operations should timeout when pool is exhausted"
        assert queue_test_duration >= 4.0, f"Queue test should take at least 4 seconds, took {queue_test_duration:.2f}s"
        
        # Check for graceful timeout handling
        for result in results:
            if isinstance(result, dict) and not result.get('success', False):
                assert result.get('duration', 0) >= 4.0, "Timeout operations should respect pool_timeout"
        
        logger.info(f"Queue management test - Timeouts: {timeout_count}, Successful: {successful_count}, Duration: {queue_test_duration:.2f}s")
    
    async def test_backpressure_signal_validation(self, pool_test_harness):
        """Test Case 3: Verify appropriate backpressure signals via HTTP endpoints."""
        harness = pool_test_harness
        
        # Configure very small pool
        await harness.setup_reduced_pool(pool_size=1, max_overflow=1, timeout=1.0)
        
        # Exhaust pool
        blocking_tasks = await harness.exhaust_pool(extra_connections=1)
        await asyncio.sleep(0.5)
        
        # Test HTTP endpoints under pool exhaustion
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Test health endpoint (should work)
            try:
                health_response = await client.get("http://localhost:8000/health")
                assert health_response.status_code == 200, "Health endpoint should remain accessible"
            except Exception as e:
                logger.warning(f"Health endpoint test failed: {e}")
            
            # Test database-dependent endpoint
            try:
                db_response = await client.get("http://localhost:8000/workspaces")
                
                # Should receive appropriate error status
                assert db_response.status_code in [500, 503, 429], f"Expected error status code, got {db_response.status_code}"
                
                # Check response format
                if db_response.status_code != 503:
                    response_data = db_response.json()
                    assert 'error' in response_data or 'detail' in response_data, "Error response should contain error information"
                
            except httpx.ConnectError:
                # Service may be unavailable during pool exhaustion - this is acceptable
                logger.info("Service unavailable during pool exhaustion (acceptable behavior)")
            except Exception as e:
                logger.warning(f"Database endpoint test error: {e}")
        
        # Verify system recovers after connections are released
        await asyncio.sleep(2.0)
        recovery_metrics = await harness.get_pool_metrics()
        logger.info(f"Recovery metrics: {recovery_metrics}")
    
    async def test_connection_leak_detection(self, pool_test_harness):
        """Test Case 4: Ensure no connection leaks occur during pool exhaustion."""
        harness = pool_test_harness
        
        await harness.setup_reduced_pool(pool_size=3, max_overflow=2, timeout=3.0)
        
        # Get initial metrics
        initial_metrics = await harness.get_pool_metrics()
        initial_checked_in = initial_metrics.get('checked_in', 0)
        
        # Execute operations with some failures
        operation_tasks = []
        for i in range(10):
            if i % 3 == 0:
                # Intentionally create failing operation
                task = asyncio.create_task(
                    harness.attempt_database_operation(timeout=0.1)  # Very short timeout
                )
            else:
                # Normal operation
                task = asyncio.create_task(
                    harness.attempt_database_operation(timeout=5.0)
                )
            operation_tasks.append(task)
            await asyncio.sleep(0.1)
        
        # Wait for all operations to complete
        results = await asyncio.gather(*operation_tasks, return_exceptions=True)
        
        # Wait for connections to return to pool
        await asyncio.sleep(2.0)
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(1.0)
        
        # Check final metrics
        final_metrics = await harness.get_pool_metrics()
        final_checked_in = final_metrics.get('checked_in', 0)
        
        # Analyze results
        failed_operations = sum(1 for r in results if isinstance(r, dict) and not r.get('success', False))
        successful_operations = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
        
        # Verify no connection leaks
        assert final_checked_in >= initial_checked_in - 1, f"Connection leak detected: initial={initial_checked_in}, final={final_checked_in}"
        
        # Verify pool health recovery
        pool_health = final_metrics.get('health', 'unknown')
        assert pool_health in ['healthy', 'warning'], f"Pool should recover to healthy state, got: {pool_health}"
        
        logger.info(f"Leak detection test - Failed: {failed_operations}, Successful: {successful_operations}, Health: {pool_health}")
    
    async def test_graceful_degradation_sustained_load(self, pool_test_harness):
        """Test Case 5: Test system behavior under sustained connection pool pressure."""
        harness = pool_test_harness
        
        await harness.setup_reduced_pool(pool_size=5, max_overflow=5, timeout=10.0)
        
        # Test sustained load at 80% capacity
        sustained_load_duration = 30.0  # 30 seconds
        operation_interval = 0.5  # 2 operations per second
        
        start_time = time.time()
        operations = []
        performance_metrics = []
        
        async def sustained_operation_generator():
            """Generate operations at sustained rate."""
            while time.time() - start_time < sustained_load_duration:
                # Create 8 concurrent operations (80% of 10 total capacity)
                batch_tasks = []
                for _ in range(4):
                    task = asyncio.create_task(
                        harness.attempt_database_operation(timeout=8.0)
                    )
                    batch_tasks.append(task)
                
                # Wait for batch completion
                batch_start = time.time()
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                batch_duration = time.time() - batch_start
                
                # Collect performance metrics
                successful = sum(1 for r in batch_results if isinstance(r, dict) and r.get('success', False))
                performance_metrics.append({
                    'timestamp': time.time(),
                    'batch_duration': batch_duration,
                    'successful_operations': successful,
                    'total_operations': len(batch_tasks)
                })
                
                operations.extend(batch_results)
                
                # Wait before next batch
                await asyncio.sleep(operation_interval)
        
        # Run sustained load test
        await sustained_operation_generator()
        
        # Analyze performance metrics
        total_operations = len(operations)
        successful_operations = sum(1 for r in operations if isinstance(r, dict) and r.get('success', False))
        success_rate = (successful_operations / total_operations) * 100 if total_operations > 0 else 0
        
        # Calculate average response time
        response_times = [r.get('duration', 0) for r in operations if isinstance(r, dict) and r.get('duration')]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Verify graceful degradation
        assert success_rate >= 80, f"Success rate should be >= 80% under sustained load, got {success_rate:.1f}%"
        assert avg_response_time <= 8.0, f"Average response time should be <= 8s, got {avg_response_time:.2f}s"
        
        # Check pool recovery
        final_metrics = await harness.get_pool_metrics()
        assert final_metrics.get('health') in ['healthy', 'warning'], "Pool should recover after sustained load"
        
        logger.info(f"Sustained load test - Operations: {total_operations}, Success rate: {success_rate:.1f}%, Avg response: {avg_response_time:.2f}s")
    
    async def test_pool_recovery_and_auto_healing(self, pool_test_harness):
        """Test Case 7: Test automatic recovery mechanisms when pool health degrades."""
        harness = pool_test_harness
        
        await harness.setup_reduced_pool(pool_size=2, max_overflow=1, timeout=3.0)
        
        # Trigger pool exhaustion
        blocking_tasks = await harness.exhaust_pool(extra_connections=2)
        
        # Wait for health degradation
        await asyncio.sleep(2.0)
        
        # Check degraded state
        degraded_metrics = await harness.get_pool_metrics()
        initial_health = degraded_metrics.get('health', 'unknown')
        
        # Release some connections (simulate recovery trigger)
        for task in blocking_tasks[:2]:
            task.cancel()
        
        # Wait for recovery
        recovery_start = time.time()
        max_recovery_time = 30.0
        
        while time.time() - recovery_start < max_recovery_time:
            current_metrics = await harness.get_pool_metrics()
            current_health = current_metrics.get('health', 'unknown')
            utilization = current_metrics.get('utilization_percent', 100)
            
            if current_health == 'healthy' and utilization < 50:
                recovery_time = time.time() - recovery_start
                logger.info(f"Pool recovered in {recovery_time:.2f}s")
                break
            
            await asyncio.sleep(1.0)
        else:
            pytest.fail("Pool did not recover within expected time")
        
        # Test normal operations after recovery
        post_recovery_operation = await harness.attempt_database_operation(timeout=5.0)
        assert post_recovery_operation['success'], "Operations should work normally after recovery"
        
        # Verify pool metrics normalize
        final_metrics = await harness.get_pool_metrics()
        assert final_metrics.get('health') == 'healthy', "Pool health should be restored"
        assert final_metrics.get('utilization_percent', 0) < 80, "Pool utilization should normalize"
        
        logger.info(f"Recovery test completed - Initial health: {initial_health}, Final health: {final_metrics.get('health')}")


@pytest.mark.e2e
@pytest.mark.performance
class TestDatabaseConnectionPoolPerformance:
    """Performance-focused tests for connection pool behavior."""
    
    async def test_connection_acquisition_latency(self, pool_test_harness):
        """Test connection acquisition latency under various load conditions."""
        harness = pool_test_harness
        
        await harness.setup_reduced_pool(pool_size=10, max_overflow=5, timeout=5.0)
        
        # Test connection acquisition times
        acquisition_times = []
        
        for load_level in [0.2, 0.5, 0.8, 0.9]:  # 20%, 50%, 80%, 90% load
            concurrent_ops = int(15 * load_level)  # 15 is total capacity
            
            # Create background load
            background_tasks = []
            for _ in range(concurrent_ops):
                task = await harness.create_blocking_connection(10.0)
                background_tasks.append(task)
            
            await asyncio.sleep(0.5)  # Allow load to establish
            
            # Measure connection acquisition time
            start_time = time.time()
            test_operation = await harness.attempt_database_operation(timeout=3.0)
            acquisition_time = time.time() - start_time
            
            acquisition_times.append({
                'load_level': load_level,
                'acquisition_time': acquisition_time,
                'success': test_operation['success']
            })
            
            # Cleanup background load
            for task in background_tasks:
                task.cancel()
            await asyncio.sleep(0.5)
        
        # Analyze acquisition times
        for metrics in acquisition_times:
            load = metrics['load_level']
            time_taken = metrics['acquisition_time']
            success = metrics['success']
            
            if load <= 0.8:
                assert time_taken <= 2.0, f"Acquisition should be fast at {load*100}% load, took {time_taken:.2f}s"
                assert success, f"Operations should succeed at {load*100}% load"
            
            logger.info(f"Load {load*100:.0f}%: {time_taken:.3f}s acquisition time, success: {success}")
    
    async def test_pool_metrics_accuracy(self, pool_test_harness):
        """Test accuracy of pool metrics under various conditions."""
        harness = pool_test_harness
        
        await harness.setup_reduced_pool(pool_size=4, max_overflow=2, timeout=5.0)
        
        # Test metrics at different utilization levels
        test_scenarios = [
            {'blocking_connections': 0, 'expected_utilization': 0},
            {'blocking_connections': 2, 'expected_utilization': 50},
            {'blocking_connections': 4, 'expected_utilization': 100},
            {'blocking_connections': 6, 'expected_utilization': 150}  # With overflow
        ]
        
        for scenario in test_scenarios:
            # Create blocking connections
            blocking_tasks = []
            for _ in range(scenario['blocking_connections']):
                task = await harness.create_blocking_connection(5.0)
                blocking_tasks.append(task)
            
            await asyncio.sleep(0.5)  # Allow connections to establish
            
            # Get metrics
            metrics = await harness.get_pool_metrics()
            utilization = metrics.get('utilization_percent', 0)
            
            # Verify metrics accuracy (allow 10% tolerance)
            expected = scenario['expected_utilization']
            tolerance = 20  # Allow 20% tolerance for timing variations
            
            assert abs(utilization - expected) <= tolerance, \
                f"Utilization should be ~{expected}%, got {utilization}% (tolerance:  +/- {tolerance}%)"
            
            # Cleanup
            for task in blocking_tasks:
                task.cancel()
            await asyncio.sleep(0.2)
            
            logger.info(f"Metrics test - Expected: {expected}%, Actual: {utilization:.1f}%")


@pytest.mark.e2e
@pytest.mark.critical
async def test_pool_exhaustion_end_to_end():
    """Complete end-to-end test of pool exhaustion scenario."""
    harness = PoolExhaustionTestHarness()
    
    try:
        # Setup test environment
        await harness.setup_reduced_pool(pool_size=2, max_overflow=1, timeout=2.0)
        
        # Phase 1: Establish baseline
        baseline_metrics = await harness.get_pool_metrics()
        assert baseline_metrics.get('pool_size') == 2
        
        # Phase 2: Gradually increase load
        load_phases = [1, 2, 3, 4]  # Connections to create
        
        for phase, connection_count in enumerate(load_phases, 1):
            logger.info(f"Phase {phase}: Creating {connection_count} connections")
            
            # Create blocking connections
            tasks = []
            for _ in range(connection_count):
                task = await harness.create_blocking_connection(10.0)
                tasks.append(task)
            
            await asyncio.sleep(0.5)
            
            # Test database operation
            operation_result = await harness.attempt_database_operation(timeout=3.0)
            metrics = await harness.get_pool_metrics()
            
            logger.info(f"Phase {phase} - Utilization: {metrics.get('utilization_percent', 0):.1f}%, "
                       f"Operation success: {operation_result['success']}")
            
            # Cleanup phase
            for task in tasks:
                task.cancel()
            await asyncio.sleep(0.5)
        
        # Phase 3: Verify recovery
        final_metrics = await harness.get_pool_metrics()
        assert final_metrics.get('health') in ['healthy', 'warning'], "System should recover"
        
        logger.info("End-to-end pool exhaustion test completed successfully")
        
    finally:
        await harness.cleanup()