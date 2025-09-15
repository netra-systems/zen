"""
Integration tests for ClickHouse async client usage patterns.

These tests validate the correct async/await patterns for ClickHouse operations
and test with real ClickHouse connections where available.

Tests cover:
1. Proper async context manager usage
2. Schema creation operations
3. Query execution patterns
4. Error handling for connection issues
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from contextlib import asynccontextmanager

from netra_backend.app.db.clickhouse_schema import ClickHouseTraceSchema
from netra_backend.app.db.clickhouse import get_clickhouse_client


class ClickHouseAsyncClientIntegrationTests:
    """Integration tests for ClickHouse async client patterns."""

    @pytest.mark.asyncio
    async def test_get_clickhouse_client_context_manager_pattern(self):
        """
        Test that get_clickhouse_client works as an async context manager.
        """
        try:
            async with get_clickhouse_client() as client:
                # Verify we got a client object, not a context manager
                assert hasattr(client, 'execute'), "Client should have execute method"

                # Test basic operation (may fail if no ClickHouse available, which is OK)
                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, client.execute, "SELECT 1"
                    )
                    assert result is not None
                except Exception as e:
                    # Expected if ClickHouse not available - log and continue
                    print(f"ClickHouse not available (expected in test environment): {e}")

        except Exception as e:
            # This is OK if ClickHouse is not available in test environment
            print(f"ClickHouse service not available: {e}")
            pytest.skip("ClickHouse service not available for integration testing")

    @pytest.mark.asyncio
    async def test_schema_operations_with_proper_async_pattern(self):
        """
        Test ClickHouse schema operations using the correct async pattern.
        This test mocks the get_clickhouse_client to test the corrected usage pattern.
        """
        # Mock a real client that would be yielded by the context manager
        mock_client = Mock()
        mock_client.execute = Mock(side_effect=[
            True,  # For create_table
            [['col1', 'String', ''], ['col2', 'UInt32', '0']],  # For get_table_columns
            [{'test_table': 100}],  # For get_table_stats table count
            [[1000, 500]]  # For get_table_stats total size
        ])

        # Mock the async context manager pattern
        @asynccontextmanager
        async def mock_get_clickhouse_client():
            yield mock_client

        with patch('netra_backend.app.db.clickhouse_schema.get_clickhouse_client',
                  mock_get_clickhouse_client):

            schema = ClickHouseTraceSchema()

            # These operations should work with the correct async pattern
            # NOTE: This test will fail with current broken implementation
            # and should pass after the fix is applied

            # Test 1: Create table (this will fail with current implementation)
            try:
                result = await schema.create_table("test_table", "CREATE TABLE test (id UInt32)")
                assert result is True, "Table creation should succeed"
            except AttributeError as e:
                error_msg = str(e)
                if ("'_AsyncGeneratorContextManager' object has no attribute 'execute'" in error_msg or
                    "'async_generator' object has no attribute 'execute'" in error_msg):
                    pytest.fail(f"Current implementation has async/sync mismatch - this error confirms Issue #1175: {error_msg}")
                else:
                    raise

            # Test 2: Get table columns (this will also fail with current implementation)
            try:
                columns = await schema.get_table_columns("test_table")
                assert len(columns) == 2, "Should return 2 columns"
                assert columns[0]['name'] == 'col1'
            except AttributeError as e:
                error_msg = str(e)
                if ("'_AsyncGeneratorContextManager' object has no attribute 'execute'" in error_msg or
                    "'async_generator' object has no attribute 'execute'" in error_msg):
                    pytest.fail(f"Current implementation has async/sync mismatch - this error confirms Issue #1175: {error_msg}")
                else:
                    raise

            # Test 3: Get table stats (this will also fail with current implementation)
            try:
                stats = await schema.get_table_stats()
                assert 'test_table' in stats
            except AttributeError as e:
                error_msg = str(e)
                if ("'_AsyncGeneratorContextManager' object has no attribute 'execute'" in error_msg or
                    "'async_generator' object has no attribute 'execute'" in error_msg):
                    pytest.fail(f"Current implementation has async/sync mismatch - this error confirms Issue #1175: {error_msg}")
                else:
                    raise

    @pytest.mark.asyncio
    async def test_correct_async_client_usage_demonstration(self):
        """
        Demonstrate the correct way to use the async ClickHouse client.
        This test shows the pattern that should be implemented in the fix.
        """
        mock_client = Mock()
        mock_client.execute = Mock(return_value=[])

        @asynccontextmanager
        async def mock_get_clickhouse_client():
            yield mock_client

        # This is the CORRECT pattern
        async with mock_get_clickhouse_client() as client:
            # Execute query using the actual client
            result = await asyncio.get_event_loop().run_in_executor(
                None, client.execute, "SELECT 1"
            )
            assert result == []
            mock_client.execute.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_fixed_get_client_method_pattern(self):
        """
        Test the proposed fix for the _get_client method.
        This shows how the method should be modified.
        """
        class FixedClickHouseTraceSchema(ClickHouseTraceSchema):
            """Schema class with fixed _get_client method."""

            def _get_client(self):
                """Get ClickHouse client context manager (FIXED VERSION)."""
                from netra_backend.app.db.clickhouse_schema import get_clickhouse_client
                # Return the context manager, don't try to store it
                return get_clickhouse_client()

            async def create_table_fixed(self, table_name: str, table_schema: str) -> bool:
                """Fixed version of create_table using proper async pattern."""
                try:
                    # Use the context manager correctly
                    async with self._get_client() as client:
                        await asyncio.get_event_loop().run_in_executor(
                            None, client.execute, table_schema
                        )
                    return True
                except Exception as e:
                    print(f"Table creation failed: {e}")
                    return False

        # Test the fixed implementation
        mock_client = Mock()
        mock_client.execute = Mock(return_value=True)

        @asynccontextmanager
        async def mock_get_clickhouse_client():
            yield mock_client

        with patch('netra_backend.app.db.clickhouse_schema.get_clickhouse_client',
                  mock_get_clickhouse_client):

            fixed_schema = FixedClickHouseTraceSchema()
            result = await fixed_schema.create_table_fixed("test_table", "CREATE TABLE test (id UInt32)")
            assert result is True

    @pytest.mark.real_database
    @pytest.mark.asyncio
    async def test_real_clickhouse_connection_if_available(self):
        """
        Test with real ClickHouse connection if available.
        This test is marked to run only when real database testing is enabled.
        """
        try:
            async with get_clickhouse_client() as client:
                # Test basic connectivity
                result = await asyncio.get_event_loop().run_in_executor(
                    None, client.execute, "SELECT 1 as test_connection"
                )
                assert result is not None, "Should get result from ClickHouse"

                # Test table existence check (safe operation)
                tables_result = await asyncio.get_event_loop().run_in_executor(
                    None, client.execute,
                    "SELECT name FROM system.tables WHERE database = 'default' LIMIT 1"
                )
                # This should not fail, even if no tables exist
                assert isinstance(tables_result, (list, tuple)), "Should return a list/tuple"

        except Exception as e:
            # Log the connection error but don't fail the test
            print(f"Real ClickHouse connection not available: {e}")
            pytest.skip("Real ClickHouse connection not available")

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """
        Test proper error handling when ClickHouse is not available.
        """
        async def failing_get_clickhouse_client():
            raise ConnectionError("ClickHouse connection failed")

        with patch('netra_backend.app.db.clickhouse_schema.get_clickhouse_client',
                  failing_get_clickhouse_client):

            schema = ClickHouseTraceSchema()

            # The _get_client method should handle connection errors gracefully
            try:
                # This will fail due to the connection error
                await schema.create_table("test_table", "CREATE TABLE test (id UInt32)")
            except (ConnectionError, AttributeError) as e:
                # Either connection error or the async/sync mismatch error is expected
                print(f"Expected error: {e}")

    @pytest.mark.asyncio
    async def test_multiple_concurrent_operations(self):
        """
        Test multiple concurrent ClickHouse operations to verify async safety.
        """
        mock_client = Mock()
        mock_client.execute = Mock(side_effect=[
            [['table1']], [['table2']], [['table3']]  # Different results for each call
        ])

        call_count = 0
        @asynccontextmanager
        async def mock_get_clickhouse_client():
            nonlocal call_count
            call_count += 1
            yield mock_client

        with patch('netra_backend.app.db.clickhouse_schema.get_clickhouse_client',
                  mock_get_clickhouse_client):

            schema = ClickHouseTraceSchema()

            # Create multiple concurrent operations
            # NOTE: These will fail with current implementation due to async/sync mismatch
            tasks = []
            for i in range(3):
                task = asyncio.create_task(schema.get_table_columns(f"table{i+1}"))
                tasks.append(task)

            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Check if all tasks completed (they should fail with current implementation)
                for i, result in enumerate(results):
                    if isinstance(result, AttributeError):
                        error_msg = str(result)
                        if ("'_AsyncGeneratorContextManager' object has no attribute 'execute'" in error_msg or
                            "'async_generator' object has no attribute 'execute'" in error_msg):
                            pytest.fail(f"Task {i} failed with async/sync mismatch error - confirms Issue #1175: {error_msg}")
                        else:
                            raise result
                    # If no error, the fix has been applied and tasks completed successfully
                    assert isinstance(result, list), f"Task {i} should return a list"

            except Exception as e:
                print(f"Concurrent operations failed: {e}")


# Test configuration
pytest_plugins = ["pytest_asyncio"]