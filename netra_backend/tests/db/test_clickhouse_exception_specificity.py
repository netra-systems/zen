"""
Unit tests for ClickHouse exception handling specificity - Issue #731.

Tests focused on verifying that ClickHouse operations properly classify
and raise specific exception types instead of generic Exception.

Business Value Justification (BVJ):
- Segment: Platform/Enterprise
- Business Goal: Improve system reliability and debugging capabilities
- Value Impact: Clear exception handling enables faster issue resolution
- Revenue Impact: Reduces system downtime and troubleshooting costs
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from netra_backend.app.db.clickhouse import ClickHouseService, get_clickhouse_service
from netra_backend.app.db.transaction_errors import (
    TableNotFoundError, CacheError, ConnectionError, TimeoutError,
    PermissionError, SchemaError, classify_error
)
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestClickHouseExceptionSpecificity(SSotAsyncTestCase):
    """Test ClickHouse exception classification and specificity."""

    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)
        self.service = ClickHouseService(force_mock=True)

    async def test_table_not_found_exception_raised(self):
        """Test that TableNotFoundError is raised for missing table operations."""
        from sqlalchemy.exc import OperationalError

        # Create a mock client that simulates table not found error using OperationalError
        mock_client = AsyncMock()
        mock_client.execute.side_effect = OperationalError(
            "statement", "params", "Table 'non_existent_table_xyz123' doesn't exist"
        )

        self.service._client = mock_client

        with pytest.raises(TableNotFoundError) as exc_info:
            await self.service.execute("SELECT * FROM non_existent_table_xyz123")

        # Verify the exception message contains relevant information
        assert "Table not found error" in str(exc_info.value)
        assert "non_existent_table_xyz123" in str(exc_info.value)

    async def test_cache_error_exception_raised(self):
        """Test that CacheError is raised for cache-related failures."""
        from sqlalchemy.exc import OperationalError

        # Create a mock client that simulates cache error
        mock_client = AsyncMock()
        mock_client.execute.side_effect = OperationalError(
            "statement", "params", "Cache failure: Unable to store result"
        )

        self.service._client = mock_client

        with pytest.raises(CacheError) as exc_info:
            await self.service.execute("SELECT * FROM users")

        # Verify the exception message contains relevant information
        assert "Cache error" in str(exc_info.value)
        assert "Cache failure" in str(exc_info.value)

    async def test_connection_error_specificity(self):
        """Test that ConnectionError is raised for connection issues."""
        from sqlalchemy.exc import OperationalError

        # Create a mock client that simulates connection error
        mock_client = AsyncMock()
        mock_client.execute.side_effect = OperationalError(
            "statement", "params", "Connection timeout to ClickHouse server"
        )

        self.service._client = mock_client

        with pytest.raises(ConnectionError) as exc_info:
            await self.service.execute("SELECT 1")

        # Verify the exception message contains relevant information
        assert "Connection error" in str(exc_info.value)
        assert "timeout" in str(exc_info.value)

    async def test_permission_error_specificity(self):
        """Test that PermissionError is raised for permission issues."""
        from sqlalchemy.exc import OperationalError

        # Create a mock client that simulates permission error
        mock_client = AsyncMock()
        mock_client.execute.side_effect = OperationalError(
            "statement", "params", "Access denied for user 'test'"
        )

        self.service._client = mock_client

        with pytest.raises(PermissionError) as exc_info:
            await self.service.execute("SELECT * FROM system.users")

        # Verify the exception message contains relevant information
        assert "Permission error" in str(exc_info.value)
        assert "Access denied" in str(exc_info.value)

    async def test_timeout_error_specificity(self):
        """Test that TimeoutError is raised for timeout issues."""
        from sqlalchemy.exc import OperationalError

        # Create a mock client that simulates timeout error
        mock_client = AsyncMock()
        mock_client.execute.side_effect = OperationalError(
            "statement", "params", "Query execution timed out after 30 seconds"
        )

        self.service._client = mock_client

        with pytest.raises(TimeoutError) as exc_info:
            await self.service.execute("SELECT * FROM large_table")

        # Verify the exception message contains relevant information
        assert "Timeout error" in str(exc_info.value)
        assert "timed out" in str(exc_info.value)

    async def test_batch_insert_exception_specificity(self):
        """Test that batch_insert raises specific exceptions for different error types."""
        from sqlalchemy.exc import OperationalError

        # Test TableNotFoundError for batch insert
        mock_client = AsyncMock()
        mock_client.execute.side_effect = OperationalError(
            "statement", "params", "Table 'invalid_table' does not exist"
        )

        self.service._client = mock_client

        test_data = [{"id": 1, "name": "test"}]

        with pytest.raises(TableNotFoundError) as exc_info:
            await self.service.batch_insert("invalid_table", test_data)

        # Verify the exception message contains relevant information
        assert "Table not found error" in str(exc_info.value)
        assert "does not exist" in str(exc_info.value)

    def test_error_classification_function(self):
        """Test that the classify_error function properly classifies exceptions."""
        from sqlalchemy.exc import OperationalError

        # Test table not found classification
        table_error = OperationalError("statement", "params", "Table doesn't exist")
        classified = classify_error(table_error)
        assert isinstance(classified, TableNotFoundError)

        # Test cache error classification
        cache_error = OperationalError("statement", "params", "Cache failure occurred")
        classified = classify_error(cache_error)
        assert isinstance(classified, CacheError)

        # Test connection error classification
        conn_error = OperationalError("statement", "params", "Connection refused")
        classified = classify_error(conn_error)
        assert isinstance(classified, ConnectionError)

        # Test permission error classification
        perm_error = OperationalError("statement", "params", "Access denied")
        classified = classify_error(perm_error)
        assert isinstance(classified, PermissionError)

    async def test_service_health_check_exception_handling(self):
        """Test that health_check properly handles and classifies exceptions."""
        from sqlalchemy.exc import OperationalError

        # Create a mock client that raises a specific exception
        mock_client = AsyncMock()
        mock_client.execute.side_effect = OperationalError(
            "statement", "params", "Permission denied for system check"
        )

        self.service._client = mock_client

        # Health check should not raise exception but return error info
        result = await self.service.health_check()

        # Verify health check result includes error information
        assert result["status"] == "unhealthy"
        assert "error" in result
        # The error should contain the permission error information
        assert "Permission" in result["error"] or "denied" in result["error"]

    async def test_execute_with_retry_preserves_exception_specificity(self):
        """Test that retry mechanism preserves specific exception types."""
        from sqlalchemy.exc import OperationalError

        # Create a mock client that consistently raises a specific exception
        mock_client = AsyncMock()
        mock_client.execute.side_effect = OperationalError(
            "statement", "params", "Table 'retry_test_table' doesn't exist"
        )

        self.service._client = mock_client

        # execute_with_retry should preserve the specific exception type
        with pytest.raises(TableNotFoundError) as exc_info:
            await self.service.execute_with_retry("SELECT * FROM retry_test_table", max_retries=2)

        # Verify the exception message contains relevant information
        assert "Table not found error" in str(exc_info.value)
        assert "retry_test_table" in str(exc_info.value)

    async def test_no_generic_exception_escapes(self):
        """Test that generic Exception types don't escape without classification."""
        # This test verifies that our classify_error function is working
        from sqlalchemy.exc import OperationalError

        # Test various error messages to ensure they get classified
        test_cases = [
            ("unknown table 'test'", TableNotFoundError),
            ("cache error occurred", CacheError),
            ("connection failed", ConnectionError),
            ("access denied", PermissionError),
            ("query execution timed out", TimeoutError),
        ]

        for error_msg, expected_exception_type in test_cases:
            original_error = OperationalError("statement", "params", error_msg)
            classified_error = classify_error(original_error)

            # Verify that the error was classified to a specific type
            assert isinstance(classified_error, expected_exception_type), f"Error '{error_msg}' was not classified as {expected_exception_type.__name__}"

    async def test_global_service_exception_handling(self):
        """Test that global service instance handles exceptions properly."""
        from sqlalchemy.exc import OperationalError

        service = get_clickhouse_service()
        service.force_mock = True  # Ensure we use mock mode
        await service.initialize()

        # Mock the client to raise OperationalError
        mock_client = AsyncMock()
        mock_client.execute.side_effect = OperationalError(
            "statement", "params", "Table 'global_test' does not exist"
        )

        service._client = mock_client

        with pytest.raises(TableNotFoundError) as exc_info:
            await service.execute("SELECT * FROM global_test")

        # Verify the exception was properly classified
        assert "Table not found error" in str(exc_info.value)
        assert "global_test" in str(exc_info.value)