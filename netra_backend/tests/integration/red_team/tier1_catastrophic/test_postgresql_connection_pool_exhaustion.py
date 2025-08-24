"""
RED TEAM TEST 4: PostgreSQL Connection Pool Exhaustion

CRITICAL: These tests are DESIGNED TO FAIL initially to expose real connection pool issues.
This test validates that connection pool exhaustion is properly handled and that the system
can recover from pool exhaustion scenarios.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform Stability, Service Availability, User Experience
- Value Impact: Connection pool exhaustion causes complete service outage affecting all users
- Strategic Impact: Core infrastructure stability for platform operation

Testing Level: L3 (Real database, real connection pools, load testing)
Expected Initial Result: FAILURE (exposes connection pool management gaps)
"""

import asyncio
import os
import secrets
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
import psutil
from fastapi.testclient import TestClient
from sqlalchemy import text, pool, create_engine
from sqlalchemy.exc import TimeoutError as SQLTimeoutError, DisconnectionError, OperationalError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool

# Real service imports - NO MOCKS
from netra_backend.app.main import app
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.database import get_db_session
from netra_backend.app.db.postgres import initialize_postgres, async_engine, async_session_factory


class TestPostgreSQLConnectionPoolExhaustion:
    """
    RED TEAM TEST 4: PostgreSQL Connection Pool Exhaustion
    
    Tests that connection pool exhaustion scenarios are properly handled.
    MUST use real PostgreSQL - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """

    @pytest.fixture(scope="class")
    def connection_pool_config(self):
        """Configuration for connection pool testing."""
        return {
            "pool_size": 5,          # Small pool for testing
            "max_overflow": 3,       # Small overflow for testing
            "pool_timeout": 2,       # Quick timeout for testing
            "pool_recycle": 300,     # 5 minutes
            "pool_pre_ping": True    # Enable connection health checks
        }

    @pytest.fixture(scope="class")
    @pytest.mark.asyncio
    async def test_database_engine(self, connection_pool_config):
        """Create a test database engine with controlled pool settings."""
        config = get_unified_config()
        
        # Create engine with small pool for testing exhaustion
        engine = create_async_engine(
            config.database_url,
            poolclass=QueuePool,
            pool_size=connection_pool_config["pool_size"],
            max_overflow=connection_pool_config["max_overflow"],
            pool_timeout=connection_pool_config["pool_timeout"],
            pool_recycle=connection_pool_config["pool_recycle"],
            pool_pre_ping=connection_pool_config["pool_pre_ping"],
            echo=False
        )
        
        try:
            # Test connection
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            yield engine
        except Exception as e:
            pytest.fail(f"CRITICAL: Test database engine creation failed: {e}")
        finally:
            await engine.dispose()

    @pytest.fixture
    def pool_monitor(self):
        """Monitor connection pool statistics."""
        return ConnectionPoolMonitor()

    @pytest.mark.asyncio
    async def test_01_connection_pool_basic_exhaustion_fails(self, test_database_engine, pool_monitor, connection_pool_config):
        """
        Test 4A: Basic Connection Pool Exhaustion (EXPECTED TO FAIL)
        
        Tests that the system properly handles when all connections are used.
        Will likely FAIL because pool exhaustion handling may not be implemented.
        """
        max_connections = connection_pool_config["pool_size"] + connection_pool_config["max_overflow"]
        timeout_seconds = connection_pool_config["pool_timeout"]
        
        # Track active connections
        active_connections = []
        connection_results = []
        
        async def acquire_connection(connection_id: int) -> Dict[str, Any]:
            """Acquire and hold a database connection."""
            start_time = time.time()
            try:
                # Acquire connection and hold it
                connection = await test_database_engine.connect()
                active_connections.append(connection)
                
                # Execute a query to ensure connection is active
                result = await connection.execute(text("SELECT :conn_id as connection_id, pg_backend_pid() as pid"), 
                                                {"conn_id": connection_id})
                row = result.fetchone()
                
                acquisition_time = time.time() - start_time
                
                return {
                    "connection_id": connection_id,
                    "success": True,
                    "acquisition_time": acquisition_time,
                    "backend_pid": row.pid if row else None,
                    "connection": connection
                }
                
            except Exception as e:
                acquisition_time = time.time() - start_time
                return {
                    "connection_id": connection_id,
                    "success": False,
                    "acquisition_time": acquisition_time,
                    "error": str(e),
                    "connection": None
                }

        # Try to acquire more connections than the pool allows
        connection_tasks = []
        for i in range(max_connections + 3):  # Exceed pool limit
            task = acquire_connection(i)
            connection_tasks.append(task)
        
        # Execute connection acquisition
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        successful_connections = 0
        failed_connections = 0
        timeout_failures = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_connections += 1
            elif result["success"]:
                successful_connections += 1
                connection_results.append(result)
            else:
                failed_connections += 1
                if "timeout" in result.get("error", "").lower():
                    timeout_failures += 1
        
        # FAILURE EXPECTED HERE - system may not handle pool exhaustion properly
        assert successful_connections <= max_connections, f"Too many connections acquired: {successful_connections} (max: {max_connections})"
        
        # Some connections should fail due to pool exhaustion
        assert failed_connections > 0, "No connection failures - pool exhaustion not working"
        
        # Timeout failures indicate proper pool management
        assert timeout_failures > 0, f"No timeout failures detected - pool timeout not working (failed: {failed_connections})"
        
        # Cleanup connections
        for conn_result in connection_results:
            if conn_result.get("connection"):
                try:
                    await conn_result["connection"].close()
                except Exception:
                    pass  # Ignore cleanup errors

    @pytest.mark.asyncio
    async def test_02_connection_pool_recovery_fails(self, test_database_engine, connection_pool_config):
        """
        Test 4B: Connection Pool Recovery (EXPECTED TO FAIL)
        
        Tests that the pool recovers after connections are released.
        Will likely FAIL because connection pool recovery may not work properly.
        """
        max_connections = connection_pool_config["pool_size"] + connection_pool_config["max_overflow"]
        
        # Phase 1: Exhaust the connection pool
        held_connections = []
        for i in range(max_connections):
            try:
                conn = await test_database_engine.connect()
                # Verify connection works
                await conn.execute(text("SELECT 1"))
                held_connections.append(conn)
            except Exception as e:
                pytest.fail(f"Failed to acquire connection {i}: {e}")
        
        # Phase 2: Try to acquire one more connection (should fail)
        try:
            extra_conn = await asyncio.wait_for(
                test_database_engine.connect(), 
                timeout=connection_pool_config["pool_timeout"] + 1
            )
            await extra_conn.close()
            pytest.fail("Extra connection acquired when pool should be exhausted")
        except (SQLTimeoutError, asyncio.TimeoutError):
            # Expected - pool should be exhausted
            pass
        except Exception as e:
            pytest.fail(f"Unexpected error when pool exhausted: {e}")
        
        # Phase 3: Release all connections
        for conn in held_connections:
            try:
                await conn.close()
            except Exception:
                pass  # Ignore cleanup errors
        
        # Wait for connections to be returned to pool
        await asyncio.sleep(1)
        
        # Phase 4: Try to acquire connections again (should work)
        recovery_connections = []
        try:
            for i in range(max_connections):
                conn = await asyncio.wait_for(
                    test_database_engine.connect(),
                    timeout=5  # Should be quick after recovery
                )
                
                # Verify connection works
                result = await conn.execute(text("SELECT :test_val"), {"test_val": f"recovery_test_{i}"})
                row = result.fetchone()
                assert row is not None, f"Connection {i} not working after recovery"
                
                recovery_connections.append(conn)
                
        except Exception as e:
            # FAILURE EXPECTED HERE - pool recovery may not work
            pytest.fail(f"Connection pool did not recover properly: {e}")
        
        finally:
            # Cleanup
            for conn in recovery_connections:
                try:
                    await conn.close()
                except Exception:
                    pass

    @pytest.mark.asyncio
    async def test_03_concurrent_connection_stress_fails(self, test_database_engine):
        """
        Test 4C: Concurrent Connection Stress Test (EXPECTED TO FAIL)
        
        Tests system behavior under heavy concurrent connection load.
        Will likely FAIL because concurrent connection handling may have issues.
        """
        # High concurrency test
        concurrent_tasks = 50
        operations_per_task = 5
        
        async def database_operation_task(task_id: int) -> Dict[str, Any]:
            """Perform multiple database operations in sequence."""
            task_results = {
                "task_id": task_id,
                "operations": [],
                "total_time": 0,
                "success_count": 0,
                "error_count": 0
            }
            
            start_time = time.time()
            
            for op_num in range(operations_per_task):
                op_start = time.time()
                try:
                    # Acquire connection for each operation
                    async with test_database_engine.begin() as conn:
                        # Simulate typical database operations
                        queries = [
                            ("SELECT :task_id, :op_num, NOW() as timestamp", {"task_id": task_id, "op_num": op_num}),
                            ("SELECT COUNT(*) as count FROM pg_stat_activity WHERE state = 'active'", {}),
                            ("SELECT pg_sleep(0.1)", {}),  # Simulate processing time
                            ("SELECT :task_id * :op_num as calculation", {"task_id": task_id, "op_num": op_num})
                        ]
                        
                        for query, params in queries:
                            result = await conn.execute(text(query), params)
                            # Consume result to ensure query completes
                            result.fetchall()
                    
                    op_time = time.time() - op_start
                    task_results["operations"].append({
                        "operation": op_num,
                        "success": True,
                        "duration": op_time
                    })
                    task_results["success_count"] += 1
                    
                except Exception as e:
                    op_time = time.time() - op_start
                    task_results["operations"].append({
                        "operation": op_num,
                        "success": False,
                        "duration": op_time,
                        "error": str(e)
                    })
                    task_results["error_count"] += 1
            
            task_results["total_time"] = time.time() - start_time
            return task_results

        # Execute concurrent tasks
        start_time = time.time()
        tasks = [database_operation_task(i) for i in range(concurrent_tasks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_tasks = 0
        failed_tasks = 0
        total_operations = 0
        successful_operations = 0
        connection_errors = 0
        timeout_errors = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_tasks += 1
            else:
                total_operations += len(result["operations"])
                successful_operations += result["success_count"]
                
                if result["success_count"] == operations_per_task:
                    successful_tasks += 1
                else:
                    failed_tasks += 1
                    
                # Count specific error types
                for op in result["operations"]:
                    if not op["success"]:
                        error = op.get("error", "").lower()
                        if "connection" in error or "pool" in error:
                            connection_errors += 1
                        elif "timeout" in error:
                            timeout_errors += 1
        
        # FAILURE EXPECTED HERE - concurrent stress may overwhelm the system
        success_rate = successful_operations / total_operations if total_operations > 0 else 0
        task_success_rate = successful_tasks / concurrent_tasks
        
        print(f"Stress Test Results:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Task success rate: {task_success_rate*100:.1f}%")
        print(f"  Operation success rate: {success_rate*100:.1f}%")
        print(f"  Connection errors: {connection_errors}")
        print(f"  Timeout errors: {timeout_errors}")
        
        # These assertions will likely fail initially
        assert success_rate >= 0.85, f"Operation success rate too low: {success_rate*100:.1f}% (should be ≥85%)"
        assert task_success_rate >= 0.80, f"Task success rate too low: {task_success_rate*100:.1f}% (should be ≥80%)"
        assert total_time < 60, f"Stress test took too long: {total_time:.2f}s (should be <60s)"

    @pytest.mark.asyncio
    async def test_04_connection_leak_detection_fails(self, test_database_engine):
        """
        Test 4D: Connection Leak Detection (EXPECTED TO FAIL)
        
        Tests that connection leaks are detected and handled.
        Will likely FAIL because connection leak detection may not be implemented.
        """
        # Get initial pool state
        pool = test_database_engine.pool
        initial_checked_out = pool.checkedout()
        initial_checked_in = pool.checkedin()
        
        async def leaky_operation(operation_id: int) -> Dict[str, Any]:
            """Simulate operations that might leak connections."""
            try:
                # Acquire connection
                conn = await test_database_engine.connect()
                
                # Perform operation
                result = await conn.execute(text("SELECT :op_id, pg_backend_pid()"), {"op_id": operation_id})
                row = result.fetchone()
                
                # Simulate different leak scenarios
                if operation_id % 5 == 0:
                    # Intentional leak - don't close connection
                    return {
                        "operation_id": operation_id,
                        "type": "leaked",
                        "backend_pid": row[1] if row else None,
                        "connection_leaked": True
                    }
                elif operation_id % 7 == 0:
                    # Exception without proper cleanup
                    raise Exception(f"Simulated error in operation {operation_id}")
                else:
                    # Proper cleanup
                    await conn.close()
                    return {
                        "operation_id": operation_id,
                        "type": "clean",
                        "backend_pid": row[1] if row else None,
                        "connection_leaked": False
                    }
                    
            except Exception as e:
                return {
                    "operation_id": operation_id,
                    "type": "error",
                    "error": str(e),
                    "connection_leaked": True  # Assume leaked on error
                }

        # Run operations that may leak connections
        leak_tasks = [leaky_operation(i) for i in range(20)]
        results = await asyncio.gather(*leak_tasks, return_exceptions=True)
        
        # Analyze leak results
        leaked_operations = 0
        clean_operations = 0
        error_operations = 0
        
        for result in results:
            if isinstance(result, Exception):
                error_operations += 1
            elif result.get("connection_leaked"):
                leaked_operations += 1
            else:
                clean_operations += 1
        
        # Check pool state after operations
        await asyncio.sleep(2)  # Allow time for cleanup
        final_checked_out = pool.checkedout()
        final_checked_in = pool.checkedin()
        
        # FAILURE EXPECTED HERE - connection leaks may not be detected/handled
        connection_leak_count = final_checked_out - initial_checked_out
        
        print(f"Connection Leak Analysis:")
        print(f"  Initial checked out: {initial_checked_out}")
        print(f"  Final checked out: {final_checked_out}")
        print(f"  Potential leaks detected: {connection_leak_count}")
        print(f"  Leaked operations: {leaked_operations}")
        print(f"  Clean operations: {clean_operations}")
        print(f"  Error operations: {error_operations}")
        
        # Pool should detect and handle leaks
        assert connection_leak_count <= 2, f"Too many connections leaked: {connection_leak_count} (should be ≤2)"
        
        # Pool should still be functional
        try:
            async with test_database_engine.begin() as conn:
                result = await conn.execute(text("SELECT 'pool_functional' as status"))
                row = result.fetchone()
                assert row.status == 'pool_functional', "Pool not functional after leak test"
        except Exception as e:
            pytest.fail(f"Pool not functional after leak test: {e}")

    @pytest.mark.asyncio
    async def test_05_connection_timeout_handling_fails(self, test_database_engine, connection_pool_config):
        """
        Test 4E: Connection Timeout Handling (EXPECTED TO FAIL)
        
        Tests that connection timeouts are properly handled.
        Will likely FAIL because timeout handling may not be robust.
        """
        timeout_seconds = connection_pool_config["pool_timeout"]
        
        # Exhaust the connection pool first
        held_connections = []
        max_connections = connection_pool_config["pool_size"] + connection_pool_config["max_overflow"]
        
        for i in range(max_connections):
            conn = await test_database_engine.connect()
            await conn.execute(text("SELECT 1"))
            held_connections.append(conn)
        
        # Now test timeout scenarios
        timeout_test_cases = [
            {
                "name": "Quick timeout",
                "timeout": timeout_seconds / 2,
                "should_timeout": True
            },
            {
                "name": "Exact timeout",
                "timeout": timeout_seconds,
                "should_timeout": True
            },
            {
                "name": "Long timeout",
                "timeout": timeout_seconds * 2,
                "should_timeout": True  # Pool still exhausted
            }
        ]
        
        timeout_results = []
        
        for test_case in timeout_test_cases:
            start_time = time.time()
            try:
                # Try to acquire connection with specific timeout
                conn = await asyncio.wait_for(
                    test_database_engine.connect(),
                    timeout=test_case["timeout"]
                )
                
                # If we get here, connection was acquired
                await conn.close()
                actual_time = time.time() - start_time
                
                timeout_results.append({
                    "name": test_case["name"],
                    "expected_timeout": test_case["should_timeout"],
                    "actual_timeout": False,
                    "duration": actual_time
                })
                
            except (SQLTimeoutError, asyncio.TimeoutError) as e:
                actual_time = time.time() - start_time
                
                timeout_results.append({
                    "name": test_case["name"],
                    "expected_timeout": test_case["should_timeout"],
                    "actual_timeout": True,
                    "duration": actual_time,
                    "error_type": type(e).__name__
                })
            
            except Exception as e:
                actual_time = time.time() - start_time
                
                timeout_results.append({
                    "name": test_case["name"],
                    "expected_timeout": test_case["should_timeout"],
                    "actual_timeout": False,
                    "duration": actual_time,
                    "unexpected_error": str(e)
                })
        
        # Release held connections
        for conn in held_connections:
            try:
                await conn.close()
            except Exception:
                pass
        
        # FAILURE EXPECTED HERE - timeout handling may not work properly
        for result in timeout_results:
            if result["expected_timeout"] and not result["actual_timeout"]:
                pytest.fail(f"Timeout test '{result['name']}' should have timed out but didn't: {result}")
            
            if result["actual_timeout"]:
                # Verify timeout timing is reasonable
                expected_max_time = timeout_seconds + 1  # Allow 1 second tolerance
                if result["duration"] > expected_max_time:
                    pytest.fail(f"Timeout took too long for '{result['name']}': {result['duration']:.2f}s (expected ≤{expected_max_time}s)")

    @pytest.mark.asyncio
    async def test_06_connection_pool_health_monitoring_fails(self, test_database_engine):
        """
        Test 4F: Connection Pool Health Monitoring (EXPECTED TO FAIL)
        
        Tests that pool health can be monitored and reported.
        Will likely FAIL because health monitoring may not be implemented.
        """
        pool = test_database_engine.pool
        
        # Capture initial pool metrics
        initial_metrics = {
            "checked_out": pool.checkedout(),
            "checked_in": pool.checkedin(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
        
        # Perform various operations to change pool state
        test_connections = []
        
        # Acquire some connections
        for i in range(3):
            conn = await test_database_engine.connect()
            await conn.execute(text("SELECT :conn_num"), {"conn_num": i})
            test_connections.append(conn)
        
        # Check metrics after acquiring connections
        active_metrics = {
            "checked_out": pool.checkedout(),
            "checked_in": pool.checkedin(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
        
        # Release connections
        for conn in test_connections:
            await conn.close()
        
        # Wait for cleanup
        await asyncio.sleep(1)
        
        # Check final metrics
        final_metrics = {
            "checked_out": pool.checkedout(),
            "checked_in": pool.checkedin(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
        
        # FAILURE EXPECTED HERE - monitoring may not be available or accurate
        print(f"Pool Health Monitoring:")
        print(f"  Initial: {initial_metrics}")
        print(f"  Active:  {active_metrics}")
        print(f"  Final:   {final_metrics}")
        
        # Verify metrics make sense
        assert active_metrics["checked_out"] >= initial_metrics["checked_out"], \
            "Checked out connections should increase when acquiring connections"
        
        assert final_metrics["checked_out"] <= active_metrics["checked_out"], \
            "Checked out connections should decrease when releasing connections"
        
        # Pool should return to stable state
        assert final_metrics["checked_out"] <= initial_metrics["checked_out"] + 1, \
            f"Pool not properly cleaned up: final={final_metrics['checked_out']}, initial={initial_metrics['checked_out']}"
        
        # No invalid connections should exist
        assert final_metrics["invalid"] == 0, f"Invalid connections detected: {final_metrics['invalid']}"

    @pytest.mark.asyncio
    async def test_07_database_server_restart_recovery_fails(self, test_database_engine):
        """
        Test 4G: Database Server Restart Recovery (EXPECTED TO FAIL)
        
        Tests recovery after database connectivity issues.
        Will likely FAIL because restart recovery may not be implemented.
        """
        # Establish baseline connectivity
        baseline_connections = []
        for i in range(3):
            conn = await test_database_engine.connect()
            result = await conn.execute(text("SELECT :conn_id, pg_backend_pid()"), {"conn_id": i})
            row = result.fetchone()
            baseline_connections.append({
                "connection": conn,
                "backend_pid": row[1] if row else None
            })
        
        # Simulate database connectivity issues by forcing connection invalidation
        for conn_info in baseline_connections:
            try:
                # Force connection to be marked as invalid
                await conn_info["connection"].execute(text("SELECT pg_terminate_backend(pg_backend_pid())"))
            except Exception:
                pass  # Expected to fail
        
        # Try to use the connections (should fail)
        connection_failures = 0
        for i, conn_info in enumerate(baseline_connections):
            try:
                await conn_info["connection"].execute(text("SELECT 1"))
            except Exception:
                connection_failures += 1
            finally:
                try:
                    await conn_info["connection"].close()
                except Exception:
                    pass
        
        # Wait for pool to recover
        await asyncio.sleep(2)
        
        # Test recovery by acquiring new connections
        recovery_attempts = []
        for i in range(5):
            start_time = time.time()
            try:
                conn = await asyncio.wait_for(test_database_engine.connect(), timeout=10)
                result = await conn.execute(text("SELECT :recovery_id, 'recovered' as status"), {"recovery_id": i})
                row = result.fetchone()
                
                recovery_time = time.time() - start_time
                recovery_attempts.append({
                    "attempt": i,
                    "success": True,
                    "recovery_time": recovery_time,
                    "backend_pid": row[0] if row else None
                })
                
                await conn.close()
                
            except Exception as e:
                recovery_time = time.time() - start_time
                recovery_attempts.append({
                    "attempt": i,
                    "success": False,
                    "recovery_time": recovery_time,
                    "error": str(e)
                })
        
        # FAILURE EXPECTED HERE - recovery may not work properly
        successful_recoveries = sum(1 for attempt in recovery_attempts if attempt["success"])
        
        print(f"Database Recovery Test:")
        print(f"  Initial connection failures: {connection_failures}/{len(baseline_connections)}")
        print(f"  Successful recoveries: {successful_recoveries}/{len(recovery_attempts)}")
        
        # Pool should recover successfully
        recovery_rate = successful_recoveries / len(recovery_attempts)
        assert recovery_rate >= 0.8, f"Pool recovery rate too low: {recovery_rate*100:.1f}% (should be ≥80%)"
        
        # Recovery should be reasonably fast
        if successful_recoveries > 0:
            avg_recovery_time = sum(
                attempt["recovery_time"] for attempt in recovery_attempts if attempt["success"]
            ) / successful_recoveries
            
            assert avg_recovery_time < 5.0, f"Pool recovery too slow: {avg_recovery_time:.2f}s (should be <5.0s)"

    @pytest.mark.asyncio
    async def test_08_connection_pool_configuration_validation_fails(self, connection_pool_config):
        """
        Test 4H: Connection Pool Configuration Validation (EXPECTED TO FAIL)
        
        Tests that pool configuration is validated and enforced.
        Will likely FAIL because configuration validation may not be implemented.
        """
        config = get_unified_config()
        
        # Test various invalid pool configurations
        invalid_configurations = [
            {
                "name": "Negative pool size",
                "config": {"pool_size": -1, "max_overflow": 5, "pool_timeout": 30},
                "should_fail": True
            },
            {
                "name": "Zero pool size", 
                "config": {"pool_size": 0, "max_overflow": 5, "pool_timeout": 30},
                "should_fail": True
            },
            {
                "name": "Negative overflow",
                "config": {"pool_size": 5, "max_overflow": -1, "pool_timeout": 30},
                "should_fail": True
            },
            {
                "name": "Zero timeout",
                "config": {"pool_size": 5, "max_overflow": 5, "pool_timeout": 0},
                "should_fail": True
            },
            {
                "name": "Extremely large pool",
                "config": {"pool_size": 1000, "max_overflow": 1000, "pool_timeout": 30},
                "should_fail": True  # Should be limited for resource management
            },
            {
                "name": "Valid configuration",
                "config": {"pool_size": 5, "max_overflow": 10, "pool_timeout": 30},
                "should_fail": False
            }
        ]
        
        configuration_results = []
        
        for test_config in invalid_configurations:
            try:
                # Try to create engine with test configuration
                test_engine = create_async_engine(
                    config.database_url,
                    poolclass=QueuePool,
                    **test_config["config"],
                    echo=False
                )
                
                # Try to use the engine
                async with test_engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                
                # If we get here, configuration was accepted
                configuration_results.append({
                    "name": test_config["name"],
                    "expected_failure": test_config["should_fail"],
                    "actual_failure": False,
                    "config": test_config["config"]
                })
                
                await test_engine.dispose()
                
            except Exception as e:
                configuration_results.append({
                    "name": test_config["name"],
                    "expected_failure": test_config["should_fail"],
                    "actual_failure": True,
                    "error": str(e),
                    "config": test_config["config"]
                })
        
        # FAILURE EXPECTED HERE - configuration validation may not be implemented
        for result in configuration_results:
            if result["expected_failure"] and not result["actual_failure"]:
                pytest.fail(f"Invalid configuration '{result['name']}' was accepted: {result['config']}")
            
            if not result["expected_failure"] and result["actual_failure"]:
                pytest.fail(f"Valid configuration '{result['name']}' was rejected: {result.get('error', 'Unknown error')}")


class ConnectionPoolMonitor:
    """Monitors connection pool health and statistics."""
    
    def __init__(self):
        self.metrics_history = []
        self.alerts = []
    
    def capture_metrics(self, pool, timestamp: str = None) -> Dict[str, Any]:
        """Capture current pool metrics."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        
        metrics = {
            "timestamp": timestamp,
            "checked_out": pool.checkedout(),
            "checked_in": pool.checkedin(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
            "size": pool.size()
        }
        
        self.metrics_history.append(metrics)
        
        # Check for alerts
        self._check_alerts(metrics)
        
        return metrics
    
    def _check_alerts(self, metrics: Dict[str, Any]):
        """Check metrics for alert conditions."""
        # High utilization alert
        total_connections = metrics["checked_out"] + metrics["checked_in"]
        if total_connections > 0:
            utilization = metrics["checked_out"] / total_connections
            if utilization > 0.8:  # 80% utilization
                self.alerts.append({
                    "timestamp": metrics["timestamp"],
                    "type": "high_utilization",
                    "message": f"High pool utilization: {utilization*100:.1f}%"
                })
        
        # Invalid connections alert
        if metrics["invalid"] > 0:
            self.alerts.append({
                "timestamp": metrics["timestamp"],
                "type": "invalid_connections",
                "message": f"Invalid connections detected: {metrics['invalid']}"
            })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of monitored metrics."""
        if not self.metrics_history:
            return {"error": "No metrics collected"}
        
        latest = self.metrics_history[-1]
        
        return {
            "latest_metrics": latest,
            "total_snapshots": len(self.metrics_history),
            "alerts_count": len(self.alerts),
            "recent_alerts": self.alerts[-5:] if self.alerts else []
        }