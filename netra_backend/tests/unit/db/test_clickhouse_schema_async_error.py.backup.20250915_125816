"""
Unit tests to reproduce ClickHouse AsyncGeneratorContextManager error.

This test reproduces the exact error found in Issue #1175:
'_AsyncGeneratorContextManager' object has no attribute 'execute'

The error occurs in clickhouse_schema.py:438 where _get_client() returns
a context manager from get_clickhouse_client(), but the code tries to
call .execute() directly on it instead of using it as async context manager.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from contextlib import asynccontextmanager
from types import AsyncGeneratorType

from netra_backend.app.db.clickhouse_schema import ClickHouseTraceSchema


class TestClickHouseSchemaAsyncError:
    """Test class to reproduce the AsyncGeneratorContextManager error."""

    def test_get_client_returns_context_manager_not_client(self):
        """
        Test that _get_client() returns a context manager, not a direct client.
        This test reproduces the root cause of the error.
        """
        schema = ClickHouseTraceSchema()

        # Mock get_clickhouse_client to return what it actually returns
        async def mock_get_clickhouse_client():
            mock_client = Mock()
            mock_client.execute = Mock(return_value=[])
            yield mock_client

        with patch('netra_backend.app.db.clickhouse_schema.get_clickhouse_client',
                  mock_get_clickhouse_client):
            # This is what the current broken code does
            client_or_context_manager = schema._get_client()

            # Verify it's actually a context manager, not a client
            assert hasattr(client_or_context_manager, '__aenter__')
            assert hasattr(client_or_context_manager, '__aexit__')

            # This should fail because context manager doesn't have execute
            assert not hasattr(client_or_context_manager, 'execute')

    @pytest.mark.asyncio
    async def test_create_table_async_generator_context_manager_error(self):
        """
        Test that reproduces the exact error from staging logs:
        '_AsyncGeneratorContextManager' object has no attribute 'execute'
        """
        schema = ClickHouseTraceSchema()

        # Mock get_clickhouse_client to return an AsyncGeneratorContextManager
        async def mock_get_clickhouse_client():
            mock_client = Mock()
            mock_client.execute = Mock(return_value=True)
            yield mock_client

        with patch('netra_backend.app.db.clickhouse_schema.get_clickhouse_client',
                  mock_get_clickhouse_client):

            # This will reproduce the exact error
            with pytest.raises(AttributeError) as exc_info:
                await schema.create_table("test_table", "CREATE TABLE test (id UInt32)")

            # Verify the exact error message (could be either format depending on Python version)
            error_msg = str(exc_info.value)
            assert ("'_AsyncGeneratorContextManager' object has no attribute 'execute'" in error_msg or
                    "'async_generator' object has no attribute 'execute'" in error_msg), f"Got: {error_msg}"

    @pytest.mark.asyncio
    async def test_get_table_columns_reproduces_same_error(self):
        """
        Test that get_table_columns also reproduces the same error pattern.
        """
        schema = ClickHouseTraceSchema()

        async def mock_get_clickhouse_client():
            mock_client = Mock()
            mock_client.execute = Mock(return_value=[])
            yield mock_client

        with patch('netra_backend.app.db.clickhouse_schema.get_clickhouse_client',
                  mock_get_clickhouse_client):

            # This should also fail with the same error
            with pytest.raises(AttributeError) as exc_info:
                await schema.get_table_columns("test_table")

            error_msg = str(exc_info.value)
            assert ("'_AsyncGeneratorContextManager' object has no attribute 'execute'" in error_msg or
                    "'async_generator' object has no attribute 'execute'" in error_msg), f"Got: {error_msg}"

    @pytest.mark.asyncio
    async def test_get_table_stats_reproduces_same_error(self):
        """
        Test that get_table_stats also reproduces the same error pattern.
        """
        schema = ClickHouseTraceSchema()

        async def mock_get_clickhouse_client():
            mock_client = Mock()
            mock_client.execute = Mock(return_value=[])
            yield mock_client

        with patch('netra_backend.app.db.clickhouse_schema.get_clickhouse_client',
                  mock_get_clickhouse_client):

            # This should also fail with the same error
            with pytest.raises(AttributeError) as exc_info:
                await schema.get_table_stats()

            error_msg = str(exc_info.value)
            assert ("'_AsyncGeneratorContextManager' object has no attribute 'execute'" in error_msg or
                    "'async_generator' object has no attribute 'execute'" in error_msg), f"Got: {error_msg}"

    def test_async_context_manager_type_verification(self):
        """
        Test to verify the type returned by get_clickhouse_client.
        """
        async def mock_get_clickhouse_client():
            yield Mock()

        # Get the context manager
        context_manager = mock_get_clickhouse_client()

        # Verify it's an async generator context manager
        assert hasattr(context_manager, '__aenter__')
        assert hasattr(context_manager, '__aexit__')
        assert not hasattr(context_manager, 'execute')

        # Clean up
        context_manager.close()


class TestCorrectAsyncPattern:
    """Test class showing the correct async pattern that should work."""

    @pytest.mark.asyncio
    async def test_correct_async_context_manager_usage(self):
        """
        Test showing how the async context manager should be used correctly.
        This is the pattern that should fix the error.
        """
        schema = ClickHouseTraceSchema()

        # Mock client that will be yielded by the context manager
        mock_client = Mock()
        mock_client.execute = Mock(return_value=True)

        async def mock_get_clickhouse_client():
            yield mock_client

        with patch('netra_backend.app.db.clickhouse_schema.get_clickhouse_client',
                  mock_get_clickhouse_client):

            # This is the CORRECT way to use the async context manager
            async with mock_get_clickhouse_client() as client:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, client.execute, "CREATE TABLE test (id UInt32)"
                )
                assert result is True

    @pytest.mark.asyncio
    async def test_proposed_fix_pattern(self):
        """
        Test the proposed fix pattern for the _get_client method.
        """
        # This shows how _get_client should be modified to work correctly
        async def fixed_get_client_pattern():
            """Proposed fix for _get_client method."""
            from netra_backend.app.db.clickhouse_schema import get_clickhouse_client

            # Return the context manager correctly
            return get_clickhouse_client()

        # Mock the underlying client
        mock_client = Mock()
        mock_client.execute = Mock(return_value=[])

        async def mock_get_clickhouse_client():
            yield mock_client

        with patch('netra_backend.app.db.clickhouse_schema.get_clickhouse_client',
                  mock_get_clickhouse_client):

            # Use the fixed pattern
            async with await fixed_get_client_pattern() as client:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, client.execute, "SELECT 1"
                )
                assert result == []


# Test configuration
pytest_plugins = ["pytest_asyncio"]