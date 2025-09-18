"""
Database Connectivity Tests for Issue #1278 - Staging Environment

This test suite targets the specific database connectivity issues described in Issue #1278:
- 503 Service Unavailable errors during database connections
- VPC connector routing problems
- Cloud Run container startup failures
- Database timeout configuration issues

These tests are designed to FAIL initially to reproduce the problem.
"""

import asyncio
import time
import os
import socket
from typing import Dict, List, Optional, Tuple
import pytest
import psycopg2
import asyncpg
from contextlib import asynccontextmanager

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from dev_launcher.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.configuration.database import DatabaseConfiguration
from netra_backend.app.db.database_manager import DatabaseManager


class TestDatabaseConnectivityStaging1278(SSotAsyncTestCase):
    """Test database connectivity issues specific to staging environment"""

    def setUp(self):
        super().setUp()
        self.env = IsolatedEnvironment()
        self.database_config = DatabaseConfiguration()

    async def test_staging_database_direct_connection_vs_vpc(self):
        """
        Test direct database connection vs VPC connector routing.

        Issue #1278 suggests VPC connector routing may be causing failures.
        This test compares direct connections with VPC routed connections.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Get database configuration for staging
        db_config = self.database_config.get_connection_config()

        # Test 1: Direct connection attempt (should work)
        direct_connection_success = False
        direct_connection_time = 0

        try:
            start_time = time.time()

            # Attempt direct connection to database
            conn_string = (
                f"postgresql://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
            )

            conn = await asyncpg.connect(conn_string, timeout=30)
            await conn.execute("SELECT 1")
            await conn.close()

            end_time = time.time()
            direct_connection_time = end_time - start_time
            direct_connection_success = True

        except Exception as e:
            print(f"Direct connection failed: {str(e)}")

        # Test 2: VPC connector routed connection (may fail)
        vpc_connection_success = False
        vpc_connection_time = 0

        try:
            start_time = time.time()

            # Use DatabaseManager which routes through VPC connector
            db_manager = DatabaseManager()
            connection = await db_manager.get_connection_async()
            await connection.execute("SELECT 1")

            end_time = time.time()
            vpc_connection_time = end_time - start_time
            vpc_connection_success = True

        except Exception as e:
            print(f"VPC connector connection failed: {str(e)}")

        print(f"Connection Test Results:")
        print(f"  Direct connection: {'Success' if direct_connection_success else 'Failed'} ({direct_connection_time:.2f}s)")
        print(f"  VPC connector: {'Success' if vpc_connection_success else 'Failed'} ({vpc_connection_time:.2f}s)")

        # This assertion SHOULD FAIL if VPC connector is causing issues
        self.assertTrue(vpc_connection_success,
                       "VPC connector routing failure - demonstrates Issue #1278")

        # Check for performance differences
        if direct_connection_success and vpc_connection_success:
            performance_ratio = vpc_connection_time / direct_connection_time
            self.assertLess(performance_ratio, 3.0,
                          f"VPC connector significantly slower ({performance_ratio:.2f}x)")

    async def test_cloud_run_container_startup_database_access(self):
        """
        Test database access during Cloud Run container startup.

        Issue #1278 mentions startup failures. This test simulates the
        database access patterns during container startup.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Simulate container startup database access pattern
        startup_operations = [
            "database_health_check",
            "schema_validation",
            "connection_pool_initialization",
            "migration_check",
            "initial_data_load"
        ]

        startup_results = {}

        for operation in startup_operations:
            start_time = time.time()

            try:
                # Simulate each startup operation
                db_manager = DatabaseManager()

                if operation == "database_health_check":
                    await db_manager.health_check_async()
                elif operation == "schema_validation":
                    connection = await db_manager.get_connection_async()
                    await connection.execute("SELECT table_name FROM information_schema.tables LIMIT 5")
                elif operation == "connection_pool_initialization":
                    # Simulate initializing multiple connections
                    connections = []
                    for i in range(3):
                        conn = await db_manager.get_connection_async()
                        connections.append(conn)
                elif operation == "migration_check":
                    connection = await db_manager.get_connection_async()
                    await connection.execute("SELECT version_num FROM alembic_version LIMIT 1")
                elif operation == "initial_data_load":
                    connection = await db_manager.get_connection_async()
                    await connection.execute("SELECT COUNT(*) FROM users LIMIT 1")

                end_time = time.time()
                operation_time = end_time - start_time

                startup_results[operation] = {
                    "success": True,
                    "duration": operation_time
                }

            except Exception as e:
                end_time = time.time()
                operation_time = end_time - start_time

                startup_results[operation] = {
                    "success": False,
                    "duration": operation_time,
                    "error": str(e)
                }

        # Analyze startup operation results
        print(f"Container Startup Database Operations:")
        failed_operations = []
        slow_operations = []

        for operation, result in startup_results.items():
            status = "SUCCESS" if result["success"] else "FAILED"
            duration = result["duration"]

            print(f"  {operation}: {status} ({duration:.2f}s)")

            if not result["success"]:
                failed_operations.append(operation)
                print(f"    Error: {result.get('error', 'Unknown')}")

            if duration > 10.0:  # Slow operation threshold
                slow_operations.append(operation)

        # These assertions SHOULD FAIL if startup issues exist
        self.assertEqual(len(failed_operations), 0,
                        f"Container startup database failures: {failed_operations}")

        self.assertEqual(len(slow_operations), 0,
                        f"Slow startup operations (>10s): {slow_operations}")

    async def test_concurrent_cloud_run_instances_database_access(self):
        """
        Test concurrent database access from multiple Cloud Run instances.

        Issue #1278 may be triggered when multiple Cloud Run instances
        attempt database connections simultaneously through VPC connector.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Simulate multiple Cloud Run instances accessing database
        instance_count = 5  # Typical number of concurrent instances

        async def simulate_cloud_run_instance(instance_id):
            """Simulate database access pattern from one Cloud Run instance"""
            try:
                # Each instance attempts multiple database operations
                db_manager = DatabaseManager()

                operations = [
                    "initial_connection",
                    "health_check",
                    "user_query",
                    "metrics_insert",
                    "cleanup"
                ]

                instance_results = []

                for operation in operations:
                    start_time = time.time()

                    if operation == "initial_connection":
                        connection = await db_manager.get_connection_async()
                        await connection.execute("SELECT 1")
                    elif operation == "health_check":
                        await db_manager.health_check_async()
                    elif operation == "user_query":
                        connection = await db_manager.get_connection_async()
                        await connection.execute("SELECT id FROM users LIMIT 10")
                    elif operation == "metrics_insert":
                        connection = await db_manager.get_connection_async()
                        # Simulate metrics insertion
                        await connection.execute("SELECT NOW()")
                    elif operation == "cleanup":
                        # Simulate cleanup operations
                        connection = await db_manager.get_connection_async()
                        await connection.execute("SELECT 1")

                    end_time = time.time()
                    operation_time = end_time - start_time

                    instance_results.append({
                        "operation": operation,
                        "success": True,
                        "duration": operation_time
                    })

                return f"Instance {instance_id}: All operations successful"

            except Exception as e:
                return f"Instance {instance_id}: Failed - {str(e)}"

        # Launch multiple "instances" concurrently
        start_time = time.time()
        tasks = [simulate_cloud_run_instance(i) for i in range(instance_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        total_duration = end_time - start_time

        # Analyze results
        successful_instances = [r for r in results if "successful" in str(r)]
        failed_instances = [r for r in results if "Failed" in str(r)]

        print(f"Concurrent Cloud Run Instances Test:")
        print(f"  Total duration: {total_duration:.2f}s")
        print(f"  Successful instances: {len(successful_instances)}")
        print(f"  Failed instances: {len(failed_instances)}")

        if failed_instances:
            print(f"  Failure examples:")
            for failure in failed_instances:
                print(f"    {failure}")

        # This assertion SHOULD FAIL if concurrent access causes issues
        self.assertEqual(len(failed_instances), 0,
                        f"Concurrent Cloud Run database access failures: {failed_instances}")

    async def test_database_connection_timeout_recovery(self):
        """
        Test database connection timeout and recovery scenarios.

        Issue #1278 mentions 600s timeout requirements. This test verifies
        timeout handling and recovery mechanisms.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Test various timeout scenarios
        timeout_scenarios = [
            {"name": "short_timeout", "timeout": 5},
            {"name": "medium_timeout", "timeout": 30},
            {"name": "long_timeout", "timeout": 120}
        ]

        timeout_results = {}

        for scenario in timeout_scenarios:
            scenario_name = scenario["name"]
            timeout_value = scenario["timeout"]

            try:
                start_time = time.time()

                # Attempt connection with specific timeout
                db_manager = DatabaseManager()

                # Override timeout for this test
                connection = await asyncio.wait_for(
                    db_manager.get_connection_async(),
                    timeout=timeout_value
                )

                # Perform a query to verify connection
                await connection.execute("SELECT 1")

                end_time = time.time()
                actual_duration = end_time - start_time

                timeout_results[scenario_name] = {
                    "success": True,
                    "duration": actual_duration,
                    "timeout": timeout_value
                }

            except asyncio.TimeoutError:
                end_time = time.time()
                actual_duration = end_time - start_time

                timeout_results[scenario_name] = {
                    "success": False,
                    "duration": actual_duration,
                    "timeout": timeout_value,
                    "error": "Timeout"
                }

            except Exception as e:
                end_time = time.time()
                actual_duration = end_time - start_time

                timeout_results[scenario_name] = {
                    "success": False,
                    "duration": actual_duration,
                    "timeout": timeout_value,
                    "error": str(e)
                }

        # Analyze timeout results
        print(f"Database Connection Timeout Test Results:")
        for scenario_name, result in timeout_results.items():
            status = "SUCCESS" if result["success"] else "FAILED"
            duration = result["duration"]
            timeout = result["timeout"]

            print(f"  {scenario_name} ({timeout}s timeout): {status} ({duration:.2f}s)")

            if not result["success"]:
                print(f"    Error: {result.get('error', 'Unknown')}")

        # Check if short timeout fails (expected) but longer timeouts succeed
        short_timeout_failed = not timeout_results["short_timeout"]["success"]
        long_timeout_succeeded = timeout_results["long_timeout"]["success"]

        # This assertion SHOULD FAIL if even long timeouts fail
        self.assertTrue(long_timeout_succeeded,
                       "Long timeout connection failed - indicates serious connectivity issues")


if __name__ == "__main__":
    # Run these tests to reproduce Issue #1278 database connectivity problems
    pytest.main([__file__, "-v", "--tb=short"])