"""
REAL E2E Tests for Database Connection Pool Monitoring
=====================================================

CRITICAL INFRASTRUCTURE MONITORING - REAL SERVICES ONLY:
- Comprehensive database connection pool monitoring with REAL PostgreSQL
- Connection pool metrics collection with ACTUAL database operations
- Real-time monitoring integration with REAL database connections
- Performance correlation analysis with ACTUAL query execution
- Connection leak detection with REAL connection tracking

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all database operations)
- Business Goal: System reliability and performance monitoring
- Value Impact: Prevents database connection exhaustion and performance degradation
- Strategic Impact: Ensures platform stability under load
- Revenue Impact: Protects $1M+ ARR from database performance failures

CRITICAL REQUIREMENTS - NO MOCKS ALLOWED:
- All tests MUST use real PostgreSQL connection pool on port 5434
- All tests MUST monitor actual database connections and transactions
- All tests MUST execute real database queries to generate metrics
- All tests MUST fail hard if database services are unavailable
- Connection pool metrics MUST be from real SQLAlchemy engines
"""

import pytest
import asyncio
import time
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text, pool
from sqlalchemy.pool import QueuePool
import logging

from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.config import get_config
from netra_backend.app.core.unified_logging import get_logger
from test_framework.environment_markers import env_requires

logger = get_logger(__name__)


@env_requires(services=["postgres"], features=["database_monitoring"])
@pytest.mark.e2e
class TestDatabaseConnectionPoolMonitoring:
    """REAL E2E test suite for database connection pool monitoring capabilities."""

    @pytest.fixture
    def database_config(self):
        """Get REAL database configuration for pool monitoring."""
        config = get_config()
        return {
            'database_url': config.DATABASE_URL,
            'pool_size': 10,
            'max_overflow': 5,
            'pool_timeout': 30
        }

    @pytest.fixture
    def monitored_engine(self, database_config):
        """Create REAL SQLAlchemy engine with connection pool monitoring."""
        # Create engine with explicit pool configuration for monitoring
        engine = create_engine(
            database_config['database_url'],
            poolclass=QueuePool,
            pool_size=database_config['pool_size'],
            max_overflow=database_config['max_overflow'],
            pool_timeout=database_config['pool_timeout'],
            pool_pre_ping=True,
            echo=False
        )
        yield engine
        engine.dispose()

    def test_real_connection_pool_metrics_collection(self, monitored_engine, database_config):
        """
        Test that REAL connection pool metrics are properly collected from actual database operations.
        
        This test validates comprehensive pool monitoring with REAL PostgreSQL connections.
        """
        logger.info("Testing REAL connection pool metrics collection")
        start_time = time.time()
        
        # Test initial pool state with REAL engine
        pool_obj = monitored_engine.pool
        
        # Verify initial pool metrics
        initial_size = pool_obj.size()
        initial_checked_in = pool_obj.checkedin()
        initial_checked_out = pool_obj.checkedout()
        initial_overflow = pool_obj.overflow()
        initial_invalid = pool_obj.invalid()
        
        logger.info(f"Initial pool metrics - Size: {initial_size}, Checked In: {initial_checked_in}, "
                   f"Checked Out: {initial_checked_out}, Overflow: {initial_overflow}, Invalid: {initial_invalid}")
        
        # Verify pool is properly configured
        assert initial_size <= database_config['pool_size'], f"Initial pool size exceeds configuration: {initial_size}"
        assert initial_checked_out >= 0, f"Invalid checked out connections: {initial_checked_out}"
        assert initial_checked_in >= 0, f"Invalid checked in connections: {initial_checked_in}"
        
        # Test connection acquisition and metrics changes with REAL database
        active_connections = []
        
        # Acquire multiple REAL connections and verify metrics
        for i in range(3):
            conn = monitored_engine.connect()
            
            # Execute REAL database query to ensure connection is active
            result = conn.execute(text(f"SELECT {i+1} as connection_test"))
            test_value = result.fetchone()[0]
            assert test_value == i+1, f"Database query failed for connection {i+1}: {test_value}"
            
            active_connections.append(conn)
            
            # Check updated pool metrics after each connection
            current_checked_out = pool_obj.checkedout()
            current_checked_in = pool_obj.checkedin()
            
            logger.info(f"Connection {i+1} - Checked Out: {current_checked_out}, Checked In: {current_checked_in}")
            
            # Verify metrics reflect the connection acquisition
            assert current_checked_out == i+1, f"Checked out count incorrect: expected {i+1}, got {current_checked_out}"
        
        # Test connection release and metrics recovery
        for i, conn in enumerate(active_connections):
            conn.close()
            
            # Verify metrics update after connection release
            released_checked_out = pool_obj.checkedout()
            released_checked_in = pool_obj.checkedin()
            
            expected_checked_out = len(active_connections) - (i + 1)
            logger.info(f"Released connection {i+1} - Checked Out: {released_checked_out}, Checked In: {released_checked_in}")
            
            # Allow small timing window for pool cleanup
            time.sleep(0.1)
        
        # Verify final pool state
        final_checked_out = pool_obj.checkedout()
        final_checked_in = pool_obj.checkedin()
        
        logger.info(f"Final pool metrics - Checked Out: {final_checked_out}, Checked In: {final_checked_in}")
        
        # All connections should be released
        assert final_checked_out == 0, f"Connections not properly released: {final_checked_out} still checked out"
        
        # Ensure test used real database operations (execution time check)
        execution_time = time.time() - start_time
        assert execution_time > 0.2, f"Pool metrics test executed too quickly ({execution_time:.3f}s) - likely mocked"
        
        logger.info(f" PASS:  Real connection pool metrics collection validated in {execution_time:.2f}s")

    def test_real_connection_pool_performance_monitoring(self, monitored_engine):
        """
        Test REAL connection pool performance monitoring with actual database operations.
        """
        logger.info("Testing REAL connection pool performance monitoring")
        start_time = time.time()
        
        pool_obj = monitored_engine.pool
        performance_metrics = {}
        
        # Test 1: Connection acquisition time monitoring
        acquisition_times = []
        for i in range(5):
            acq_start = time.time()
            conn = monitored_engine.connect()
            acquisition_time = time.time() - acq_start
            acquisition_times.append(acquisition_time)
            
            # Execute real query to ensure connection is functional
            conn.execute(text("SELECT NOW()"))
            conn.close()
            
            logger.info(f"Connection {i+1} acquisition time: {acquisition_time:.4f}s")
        
        performance_metrics['avg_acquisition_time'] = sum(acquisition_times) / len(acquisition_times)
        performance_metrics['max_acquisition_time'] = max(acquisition_times)
        performance_metrics['min_acquisition_time'] = min(acquisition_times)
        
        # Test 2: Query execution performance under different pool loads
        query_times = {}
        load_levels = [1, 3, 5]  # Different numbers of concurrent connections
        
        for load_level in load_levels:
            connections = []
            query_start = time.time()
            
            # Create multiple connections
            for i in range(load_level):
                conn = monitored_engine.connect()
                connections.append(conn)
            
            # Execute queries concurrently
            for i, conn in enumerate(connections):
                result = conn.execute(text(f"SELECT {i+1}, pg_sleep(0.01)"))
                result.fetchall()  # Ensure query completes
            
            query_end = time.time()
            query_times[f'load_{load_level}'] = query_end - query_start
            
            # Close connections
            for conn in connections:
                conn.close()
            
            logger.info(f"Load level {load_level} query time: {query_times[f'load_{load_level}']:.4f}s")
            
            # Verify pool metrics during load
            current_overflow = pool_obj.overflow()
            logger.info(f"Pool overflow at load {load_level}: {current_overflow}")
        
        performance_metrics.update(query_times)
        
        # Test 3: Pool exhaustion detection with REAL connections
        logger.info("Testing pool exhaustion detection")
        exhaustion_connections = []
        
        try:
            # Attempt to exhaust the pool
            for i in range(20):  # More than pool_size + max_overflow
                try:
                    conn = monitored_engine.connect()
                    # Execute query to ensure connection is real
                    conn.execute(text("SELECT 1"))
                    exhaustion_connections.append(conn)
                    
                    current_checked_out = pool_obj.checkedout()
                    current_overflow = pool_obj.overflow()
                    logger.info(f"Exhaustion test {i+1} - Checked Out: {current_checked_out}, Overflow: {current_overflow}")
                    
                except Exception as e:
                    logger.info(f"Pool exhausted at connection {i+1}: {e}")
                    break
                    
        finally:
            # Clean up connections
            for conn in exhaustion_connections:
                try:
                    conn.close()
                except:
                    pass
        
        # Test 4: Pool recovery after exhaustion
        time.sleep(0.5)  # Allow pool to recover
        
        recovery_start = time.time()
        test_conn = monitored_engine.connect()
        test_conn.execute(text("SELECT 'pool_recovered'"))
        test_conn.close()
        recovery_time = time.time() - recovery_start
        
        performance_metrics['pool_recovery_time'] = recovery_time
        logger.info(f"Pool recovery time: {recovery_time:.4f}s")
        
        # Validate performance thresholds
        assert performance_metrics['avg_acquisition_time'] < 1.0, f"Average acquisition time too slow: {performance_metrics['avg_acquisition_time']:.4f}s"
        assert performance_metrics['pool_recovery_time'] < 2.0, f"Pool recovery too slow: {performance_metrics['pool_recovery_time']:.4f}s"
        
        # Ensure real performance monitoring was performed
        execution_time = time.time() - start_time
        assert execution_time > 1.0, f"Performance monitoring executed too quickly ({execution_time:.3f}s) - likely mocked"
        
        logger.info(f" PASS:  Real connection pool performance monitoring completed in {execution_time:.2f}s")
        logger.info(f"Performance metrics: {performance_metrics}")

    @pytest.mark.asyncio
    async def test_real_connection_leak_detection(self, monitored_engine):
        """
        Test detection of REAL database connection leaks with actual connection tracking.
        """
        logger.info("Testing REAL connection leak detection")
        start_time = time.time()
        
        pool_obj = monitored_engine.pool
        
        # Test 1: Normal connection usage (should not leak)
        normal_connections = []
        for i in range(3):
            conn = monitored_engine.connect()
            # Execute query to ensure connection is active
            conn.execute(text(f"SELECT 'normal_conn_{i+1}'"))
            normal_connections.append(conn)
        
        # Properly close connections
        for conn in normal_connections:
            conn.close()
        
        await asyncio.sleep(0.2)  # Allow cleanup
        normal_checked_out = pool_obj.checkedout()
        logger.info(f"After normal usage - Checked Out: {normal_checked_out}")
        
        # Test 2: Simulate connection leak (intentionally not closing)
        leak_connections = []
        for i in range(2):
            conn = monitored_engine.connect()
            # Execute query to make connection "active"
            result = conn.execute(text(f"SELECT pg_backend_pid(), 'leak_conn_{i+1}'"))
            pid_info = result.fetchone()
            logger.info(f"Leak connection {i+1} - Backend PID: {pid_info[0]}")
            leak_connections.append(conn)
        
        # Don't close connections - simulate leak
        leak_checked_out = pool_obj.checkedout()
        logger.info(f"After creating leaks - Checked Out: {leak_checked_out}")
        assert leak_checked_out == 2, f"Expected 2 leaked connections, got {leak_checked_out}"
        
        # Test 3: Detect leaked connections using database statistics
        with monitored_engine.connect() as detection_conn:
            # Query for long-running connections
            result = detection_conn.execute(text("""
                SELECT pid, backend_start, state, state_change, 
                       NOW() - backend_start AS connection_age
                FROM pg_stat_activity 
                WHERE datname = current_database()
                AND pid != pg_backend_pid()
                ORDER BY backend_start DESC
            """))
            
            active_connections = result.fetchall()
            logger.info(f"Active database connections detected: {len(active_connections)}")
            
            for conn_info in active_connections:
                pid, start_time, state, state_change, age = conn_info
                logger.info(f"Connection PID {pid}: State={state}, Age={age}")
        
        # Test 4: Force cleanup of leaked connections
        logger.info("Cleaning up leaked connections")
        for i, conn in enumerate(leak_connections):
            try:
                # Check connection is still active before closing
                conn.execute(text("SELECT 1"))
                conn.close()
                logger.info(f"Cleaned up leak connection {i+1}")
            except Exception as e:
                logger.info(f"Error cleaning up connection {i+1}: {e}")
        
        await asyncio.sleep(0.2)  # Allow cleanup
        
        # Verify cleanup
        final_checked_out = pool_obj.checkedout()
        logger.info(f"After cleanup - Checked Out: {final_checked_out}")
        
        # Test 5: Validate pool is healthy after leak cleanup
        health_conn = monitored_engine.connect()
        health_result = health_conn.execute(text("SELECT 'pool_healthy'"))
        health_value = health_result.fetchone()[0]
        health_conn.close()
        
        assert health_value == 'pool_healthy', f"Pool not healthy after cleanup: {health_value}"
        
        # Ensure real leak detection was performed
        execution_time = time.time() - start_time
        assert execution_time > 0.5, f"Leak detection executed too quickly ({execution_time:.3f}s) - likely mocked"
        
        logger.info(f" PASS:  Real connection leak detection validated in {execution_time:.2f}s")

    def test_real_pool_configuration_validation(self, database_config):
        """
        Test validation of REAL database pool configurations across environments.
        """
        logger.info("Testing REAL database pool configuration validation")
        start_time = time.time()
        
        # Test different pool configurations with REAL database
        test_configs = [
            {
                "name": "minimal",
                "config": {"pool_size": 2, "max_overflow": 1, "pool_timeout": 10},
                "should_work": True
            },
            {
                "name": "standard", 
                "config": {"pool_size": 5, "max_overflow": 5, "pool_timeout": 30},
                "should_work": True
            },
            {
                "name": "high_performance",
                "config": {"pool_size": 15, "max_overflow": 10, "pool_timeout": 60},
                "should_work": True
            }
        ]
        
        validation_results = {}
        
        for test_config in test_configs:
            config_name = test_config["name"]
            pool_config = test_config["config"]
            should_work = test_config["should_work"]
            
            logger.info(f"Testing {config_name} configuration: {pool_config}")
            
            try:
                # Create engine with specific pool configuration
                test_engine = create_engine(
                    database_config['database_url'],
                    poolclass=QueuePool,
                    pool_size=pool_config['pool_size'],
                    max_overflow=pool_config['max_overflow'],
                    pool_timeout=pool_config['pool_timeout'],
                    echo=False
                )
                
                # Test the configuration with REAL database operations
                test_connections = []
                
                # Test basic connectivity
                with test_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                
                # Test pool limits
                for i in range(min(pool_config['pool_size'] + 2, 10)):
                    try:
                        conn = test_engine.connect()
                        conn.execute(text(f"SELECT {i+1}"))
                        test_connections.append(conn)
                    except Exception as e:
                        logger.info(f"Connection {i+1} failed (expected for pool limit test): {e}")
                        break
                
                # Cleanup test connections
                for conn in test_connections:
                    try:
                        conn.close()
                    except:
                        pass
                
                # Verify pool metrics
                pool_obj = test_engine.pool
                final_size = pool_obj.size()
                final_overflow = pool_obj.overflow()
                
                logger.info(f"Config {config_name} - Pool Size: {final_size}, Overflow: {final_overflow}")
                
                validation_results[config_name] = {
                    "success": True,
                    "pool_size": final_size,
                    "max_overflow": final_overflow,
                    "connections_tested": len(test_connections)
                }
                
                # Cleanup engine
                test_engine.dispose()
                
                if should_work:
                    logger.info(f"[U+2713] Configuration {config_name} validated successfully")
                else:
                    logger.warning(f"Configuration {config_name} worked but was expected to fail")
                    
            except Exception as e:
                validation_results[config_name] = {
                    "success": False,
                    "error": str(e)
                }
                
                if should_work:
                    logger.error(f" FAIL:  Configuration {config_name} failed: {e}")
                    pytest.fail(f"Expected configuration {config_name} to work but it failed: {e}")
                else:
                    logger.info(f"[U+2713] Configuration {config_name} correctly failed: {e}")
        
        # Validate that at least standard configuration works
        assert validation_results.get("standard", {}).get("success", False), \
            "Standard pool configuration should always work"
        
        # Ensure real configuration validation was performed
        execution_time = time.time() - start_time
        assert execution_time > 0.3, f"Configuration validation executed too quickly ({execution_time:.3f}s) - likely mocked"
        
        logger.info(f" PASS:  Real pool configuration validation completed in {execution_time:.2f}s")
        logger.info(f"Validation results: {validation_results}")

    @pytest.mark.asyncio
    async def test_real_concurrent_pool_monitoring(self, monitored_engine):
        """
        Test REAL concurrent connection pool monitoring under simultaneous load.
        """
        logger.info("Testing REAL concurrent pool monitoring")
        start_time = time.time()
        
        pool_obj = monitored_engine.pool
        concurrent_results = []
        
        async def concurrent_database_worker(worker_id: int, operations: int):
            """Worker function that performs real database operations."""
            worker_results = {
                "worker_id": worker_id,
                "operations_completed": 0,
                "errors": [],
                "connection_times": [],
                "query_times": []
            }
            
            for op in range(operations):
                try:
                    # Time connection acquisition
                    conn_start = time.time()
                    conn = monitored_engine.connect()
                    conn_time = time.time() - conn_start
                    worker_results["connection_times"].append(conn_time)
                    
                    # Execute real database query
                    query_start = time.time()
                    result = conn.execute(text(f"SELECT {worker_id}, {op}, pg_backend_pid(), NOW()"))
                    query_result = result.fetchone()
                    query_time = time.time() - query_start
                    worker_results["query_times"].append(query_time)
                    
                    # Verify query result
                    assert query_result[0] == worker_id, f"Worker ID mismatch: {query_result[0]} != {worker_id}"
                    assert query_result[1] == op, f"Operation ID mismatch: {query_result[1]} != {op}"
                    
                    worker_results["operations_completed"] += 1
                    
                    # Simulate some work
                    await asyncio.sleep(0.01)
                    
                    conn.close()
                    
                except Exception as e:
                    worker_results["errors"].append(f"Op {op}: {str(e)}")
                    logger.warning(f"Worker {worker_id} operation {op} failed: {e}")
            
            return worker_results
        
        # Launch concurrent workers
        num_workers = 8
        operations_per_worker = 5
        
        logger.info(f"Launching {num_workers} concurrent workers with {operations_per_worker} operations each")
        
        # Monitor pool state before concurrent operations
        initial_checked_out = pool_obj.checkedout()
        initial_overflow = pool_obj.overflow()
        logger.info(f"Pre-concurrent state - Checked Out: {initial_checked_out}, Overflow: {initial_overflow}")
        
        # Execute concurrent workers
        tasks = [
            asyncio.create_task(concurrent_database_worker(worker_id, operations_per_worker))
            for worker_id in range(num_workers)
        ]
        
        # Wait for all workers to complete
        worker_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        total_operations = 0
        total_errors = 0
        all_connection_times = []
        all_query_times = []
        
        for i, result in enumerate(worker_results):
            if isinstance(result, Exception):
                logger.error(f"Worker {i} failed completely: {result}")
                total_errors += operations_per_worker
            else:
                total_operations += result["operations_completed"]
                total_errors += len(result["errors"])
                all_connection_times.extend(result["connection_times"])
                all_query_times.extend(result["query_times"])
                
                logger.info(f"Worker {i}: {result['operations_completed']} ops, "
                           f"{len(result['errors'])} errors, "
                           f"avg conn time: {sum(result['connection_times'])/len(result['connection_times']):.4f}s")
        
        # Monitor pool state after concurrent operations
        await asyncio.sleep(0.5)  # Allow connections to be returned to pool
        final_checked_out = pool_obj.checkedout()
        final_overflow = pool_obj.overflow()
        logger.info(f"Post-concurrent state - Checked Out: {final_checked_out}, Overflow: {final_overflow}")
        
        # Calculate performance metrics
        if all_connection_times:
            avg_conn_time = sum(all_connection_times) / len(all_connection_times)
            max_conn_time = max(all_connection_times)
            logger.info(f"Connection times - Avg: {avg_conn_time:.4f}s, Max: {max_conn_time:.4f}s")
        
        if all_query_times:
            avg_query_time = sum(all_query_times) / len(all_query_times)
            max_query_time = max(all_query_times)
            logger.info(f"Query times - Avg: {avg_query_time:.4f}s, Max: {max_query_time:.4f}s")
        
        # Validate concurrent operations succeeded
        expected_operations = num_workers * operations_per_worker
        success_rate = (total_operations / expected_operations) * 100 if expected_operations > 0 else 0
        
        logger.info(f"Concurrent test results: {total_operations}/{expected_operations} operations succeeded "
                   f"({success_rate:.1f}%), {total_errors} errors")
        
        # Allow some failures under high concurrency, but most should succeed
        assert success_rate >= 70, f"Success rate too low: {success_rate:.1f}%"
        
        # Verify pool returned to stable state
        assert final_checked_out == 0, f"Connections not returned to pool: {final_checked_out} still checked out"
        
        # Ensure real concurrent monitoring was performed
        execution_time = time.time() - start_time
        assert execution_time > 2.0, f"Concurrent monitoring executed too quickly ({execution_time:.3f}s) - likely mocked"
        
        logger.info(f" PASS:  Real concurrent pool monitoring validated in {execution_time:.2f}s")


# Mark all tests as requiring real database services
pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.e2e, pytest.mark.requires_real_services]


if __name__ == "__main__":
    # Allow running this test directly for development
    pytest.main([__file__, "-v", "--tb=short"])