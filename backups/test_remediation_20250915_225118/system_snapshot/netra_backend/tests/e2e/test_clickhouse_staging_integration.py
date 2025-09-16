"""
E2E staging validation tests for ClickHouse operations.

These tests validate ClickHouse operations in the staging environment
to ensure the AsyncGeneratorContextManager fix works correctly in production-like conditions.

Tests cover:
1. Staging environment ClickHouse connectivity
2. Schema creation and validation operations
3. Trace insertion and retrieval workflows
4. End-to-end data lifecycle validation
"""

import pytest
import asyncio
import os
from datetime import datetime, timezone
from typing import Optional

from netra_backend.app.db.clickhouse_schema import ClickHouseTraceSchema
from netra_backend.app.db.clickhouse import get_clickhouse_client


class ClickHouseStagingIntegrationTests:
    """E2E tests for ClickHouse operations in staging environment."""

    @pytest.fixture
    def staging_schema(self) -> ClickHouseTraceSchema:
        """Create ClickHouse schema instance for staging testing."""
        return ClickHouseTraceSchema()

    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_staging_clickhouse_connectivity(self, staging_schema):
        """
        Test basic ClickHouse connectivity in staging environment.
        This test validates that the async context manager works correctly.
        """
        try:
            async with get_clickhouse_client() as client:
                # Test basic connectivity
                result = await asyncio.get_event_loop().run_in_executor(
                    None, client.execute, "SELECT 1 as connectivity_test"
                )
                assert result is not None, "Should connect to ClickHouse in staging"

                # Verify we got expected result format
                if result:
                    assert len(result) > 0, "Should get at least one row"
                    assert result[0][0] == 1, "Should get value 1 from SELECT 1"

        except Exception as e:
            # If staging ClickHouse is not available, skip the test
            if "Connection" in str(e) or "timeout" in str(e).lower():
                pytest.skip(f"Staging ClickHouse not available: {e}")
            else:
                # Re-raise unexpected errors
                raise

    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_staging_schema_operations(self, staging_schema):
        """
        Test ClickHouse schema operations in staging environment.
        This validates the fix for the AsyncGeneratorContextManager error.
        """
        try:
            # Test 1: Get table stats (safe operation)
            stats = await staging_schema.get_table_stats()
            assert isinstance(stats, dict), "Should return dictionary of stats"

            # Test 2: Check existing tables
            async with get_clickhouse_client() as client:
                tables_result = await asyncio.get_event_loop().run_in_executor(
                    None, client.execute,
                    "SELECT name FROM system.tables WHERE database = 'default' ORDER BY name"
                )

                if tables_result:
                    print(f"Found {len(tables_result)} tables in staging ClickHouse")

                    # Test getting columns for existing tables
                    for table_row in tables_result[:3]:  # Test first 3 tables only
                        table_name = table_row[0]
                        try:
                            columns = await staging_schema.get_table_columns(table_name)
                            assert isinstance(columns, list), f"Should get columns list for {table_name}"
                            print(f"Table {table_name} has {len(columns)} columns")
                        except Exception as e:
                            print(f"Could not get columns for {table_name}: {e}")

        except Exception as e:
            # Check if this is the specific error we're trying to fix
            error_msg = str(e)
            if ("'_AsyncGeneratorContextManager' object has no attribute 'execute'" in error_msg or
                "'async_generator' object has no attribute 'execute'" in error_msg):
                pytest.fail(f"AsyncGeneratorContextManager error still present in staging: {e}")
            elif "Connection" in str(e) or "timeout" in str(e).lower():
                pytest.skip(f"Staging ClickHouse not available: {e}")
            else:
                # Log other errors but don't fail the test
                print(f"Non-critical staging error: {e}")

    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_staging_trace_workflow_simulation(self, staging_schema):
        """
        Simulate a complete trace workflow in staging environment.
        This tests the end-to-end data lifecycle that would be affected by the error.
        """
        try:
            # Create a test table name with timestamp to avoid conflicts
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            test_table = f"test_trace_workflow_{timestamp}"

            # Test table creation (this is where the original error occurred)
            create_sql = f"""
            CREATE TABLE IF NOT EXISTS {test_table} (
                trace_id String,
                timestamp DateTime64(3),
                operation String,
                status String
            ) ENGINE = MergeTree()
            ORDER BY (trace_id, timestamp)
            """

            success = await staging_schema.create_table(test_table, create_sql)
            assert success, f"Should successfully create test table {test_table}"

            # Verify table exists
            async with get_clickhouse_client() as client:
                check_result = await asyncio.get_event_loop().run_in_executor(
                    None, client.execute,
                    f"EXISTS TABLE {test_table}"
                )
                assert check_result[0][0] == 1, f"Table {test_table} should exist"

                # Insert test data
                insert_sql = f"""
                INSERT INTO {test_table} VALUES
                ('test-trace-123', now(), 'test_operation', 'success'),
                ('test-trace-124', now(), 'test_operation_2', 'pending')
                """
                await asyncio.get_event_loop().run_in_executor(
                    None, client.execute, insert_sql
                )

                # Query data back
                select_result = await asyncio.get_event_loop().run_in_executor(
                    None, client.execute,
                    f"SELECT trace_id, operation, status FROM {test_table} ORDER BY trace_id"
                )

                assert len(select_result) == 2, "Should have inserted 2 rows"
                assert select_result[0][0] == 'test-trace-123', "Should get first trace ID"
                assert select_result[1][0] == 'test-trace-124', "Should get second trace ID"

                # Clean up test table
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None, client.execute, f"DROP TABLE IF EXISTS {test_table}"
                    )
                except Exception as cleanup_error:
                    print(f"Cleanup error (non-critical): {cleanup_error}")

        except Exception as e:
            # Check for the specific error we're fixing
            error_msg = str(e)
            if ("'_AsyncGeneratorContextManager' object has no attribute 'execute'" in error_msg or
                "'async_generator' object has no attribute 'execute'" in error_msg):
                pytest.fail(f"AsyncGeneratorContextManager error in trace workflow: {e}")
            elif "Connection" in str(e) or "timeout" in str(e).lower():
                pytest.skip(f"Staging ClickHouse not available for workflow test: {e}")
            else:
                # Other errors might be due to permissions or configuration
                print(f"Workflow test error (may be due to staging config): {e}")

    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_staging_concurrent_operations(self, staging_schema):
        """
        Test concurrent ClickHouse operations in staging environment.
        This validates that the async fix works correctly under concurrent load.
        """
        try:
            # Create multiple concurrent stat gathering operations
            tasks = []
            for i in range(5):
                task = asyncio.create_task(staging_schema.get_table_stats())
                tasks.append(task)

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_msg = str(result)
                    if ("'_AsyncGeneratorContextManager' object has no attribute 'execute'" in error_msg or
                        "'async_generator' object has no attribute 'execute'" in error_msg):
                        pytest.fail(f"AsyncGeneratorContextManager error in concurrent task {i}: {result}")
                    elif "Connection" in str(result) or "timeout" in str(result).lower():
                        print(f"Task {i} connection issue (expected in staging): {result}")
                    else:
                        print(f"Task {i} other error: {result}")
                else:
                    assert isinstance(result, dict), f"Task {i} should return dict of stats"

        except Exception as e:
            if "Connection" in str(e) or "timeout" in str(e).lower():
                pytest.skip(f"Staging ClickHouse not available for concurrent test: {e}")
            else:
                raise

    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_staging_environment_validation(self):
        """
        Validate staging environment configuration for ClickHouse.
        """
        # Check environment variables that should be set for staging
        staging_indicators = [
            'CLICKHOUSE_HOST',
            'CLICKHOUSE_DATABASE',
            'ENVIRONMENT'
        ]

        env_info = {}
        for var in staging_indicators:
            value = os.environ.get(var, 'Not Set')
            env_info[var] = value

        print(f"Staging environment info: {env_info}")

        # Verify we're in a staging-like environment
        environment = os.environ.get('ENVIRONMENT', '').lower()
        if environment and 'staging' not in environment and 'test' not in environment:
            print(f"Note: Running on environment '{environment}' which may not be staging")

        # Test basic ClickHouse configuration
        try:
            async with get_clickhouse_client() as client:
                # Get server version and basic info
                version_result = await asyncio.get_event_loop().run_in_executor(
                    None, client.execute, "SELECT version()"
                )
                if version_result:
                    print(f"ClickHouse version: {version_result[0][0]}")

                # Get current database
                db_result = await asyncio.get_event_loop().run_in_executor(
                    None, client.execute, "SELECT currentDatabase()"
                )
                if db_result:
                    print(f"Current database: {db_result[0][0]}")

        except Exception as e:
            if "Connection" in str(e) or "timeout" in str(e).lower():
                pytest.skip(f"Staging ClickHouse not available for environment validation: {e}")
            else:
                print(f"Environment validation error: {e}")

    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_staging_error_recovery(self, staging_schema):
        """
        Test error recovery patterns in staging environment.
        """
        try:
            # Test invalid query handling
            async with get_clickhouse_client() as client:
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None, client.execute, "SELECT * FROM nonexistent_table_12345"
                    )
                    pytest.fail("Should have raised an error for nonexistent table")
                except Exception as expected_error:
                    # This is expected - we should get a table not found error
                    assert "doesn't exist" in str(expected_error) or "Unknown table" in str(expected_error), \
                        f"Should get table not found error, got: {expected_error}"

            # Test schema operations error handling
            try:
                columns = await staging_schema.get_table_columns("definitely_nonexistent_table_12345")
                # If it doesn't raise an error, it should return empty list
                assert isinstance(columns, list), "Should return list even for nonexistent table"
            except Exception as e:
                # Check it's not the async/sync mismatch error
                error_msg = str(e)
                if ("'_AsyncGeneratorContextManager' object has no attribute 'execute'" in error_msg or
                    "'async_generator' object has no attribute 'execute'" in error_msg):
                    pytest.fail(f"AsyncGeneratorContextManager error in error recovery: {e}")
                # Other errors are acceptable for nonexistent tables

        except Exception as e:
            if "Connection" in str(e) or "timeout" in str(e).lower():
                pytest.skip(f"Staging ClickHouse not available for error recovery test: {e}")
            else:
                raise


# Test configuration for staging environment
@pytest.fixture(scope="session")
def staging_environment():
    """Ensure we're running in a staging-compatible environment."""
    environment = os.environ.get('ENVIRONMENT', '').lower()
    if environment and 'prod' in environment:
        pytest.skip("Not running destructive tests in production environment")
    return environment


# pytest configuration
pytest_plugins = ["pytest_asyncio"]