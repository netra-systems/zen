"""
Integration tests for ClickHouse exception handling across service boundaries - Issue #731.

Tests exception propagation through service layers and validates that specific
exceptions are properly raised and handled throughout the system integration points.

Business Value Justification (BVJ):
- Segment: Platform/Enterprise
- Business Goal: Ensure reliable cross-service exception handling
- Value Impact: Maintains system stability during error conditions
- Revenue Impact: Prevents cascading failures that could impact revenue
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from netra_backend.app.db.clickhouse import ClickHouseService, get_clickhouse_service
from netra_backend.app.db.transaction_errors import (
    TableNotFoundError, CacheError, ConnectionError, TimeoutError,
    PermissionError, SchemaError, classify_error
)
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class ClickHouseExceptionIntegrationTests(SSotAsyncTestCase):
    """Test ClickHouse exception handling integration across service boundaries."""

    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)
        self.service = ClickHouseService(force_mock=True)

    async def test_exception_propagation_through_service_layers(self):
        """Test that specific exceptions propagate through service abstraction layers."""
        from sqlalchemy.exc import OperationalError

        # Test that exceptions propagate from low-level client through service layer
        mock_client = AsyncMock()
        mock_client.execute.side_effect = OperationalError(
            "statement", "params", "Table 'integration_test' doesn't exist"
        )

        self.service._client = mock_client

        # Exception should propagate through service.execute() method
        with pytest.raises(TableNotFoundError) as exc_info:
            await self.service.execute(
                "SELECT * FROM integration_test",
                user_id="test_user",
                operation_context="integration_test"
            )

        # Verify exception details are preserved through the layers
        assert "Table not found error" in str(exc_info.value)
        assert "integration_test" in str(exc_info.value)

    async def test_circuit_breaker_preserves_exception_types(self):
        """Test that circuit breaker mechanism preserves specific exception types."""
        # Mock the circuit breaker to pass through exceptions
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Permission denied for user 'circuit_test'")

        self.service._client = mock_client

        # Circuit breaker should preserve the specific exception type
        with pytest.raises(PermissionError) as exc_info:
            await self.service._execute_with_circuit_breaker(
                "SELECT * FROM restricted_table",
                user_id="circuit_test"
            )

        # Verify exception type and details are preserved
        assert "Permission error" in str(exc_info.value)
        assert "Permission denied" in str(exc_info.value)

    async def test_cache_layer_exception_handling(self):
        """Test that cache layer properly handles and propagates exceptions."""
        # Test cache miss followed by execution error
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Cache corruption detected")

        self.service._client = mock_client

        with pytest.raises(CacheError) as exc_info:
            await self.service.execute(
                "SELECT * FROM cached_table",
                user_id="cache_test",
                operation_context="cache_integration_test"
            )

        # Verify cache-specific error is properly classified
        assert "Cache error" in str(exc_info.value)
        assert "Cache corruption" in str(exc_info.value)

    async def test_retry_mechanism_exception_preservation(self):
        """Test that retry mechanisms preserve specific exception types."""
        # Mock consistent failure with specific exception type
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Connection timeout after 30 seconds")

        self.service._client = mock_client

        # Retry should preserve exception type after all attempts fail
        with pytest.raises(TimeoutError) as exc_info:
            await self.service.execute_with_retry(
                "SELECT * FROM timeout_table",
                max_retries=2,
                user_id="retry_test"
            )

        # Verify the final exception is still the specific type
        assert "Timeout error" in str(exc_info.value)
        assert "timeout" in str(exc_info.value)

    @patch('netra_backend.app.db.clickhouse.get_clickhouse_connection_manager')
    async def test_connection_manager_exception_integration(self, mock_get_manager):
        """Test exception handling through connection manager integration."""
        # Mock connection manager to raise specific exception
        mock_manager = Mock()
        mock_manager.execute_with_retry.side_effect = Exception("Table 'manager_test' does not exist")
        mock_manager.connection_health.state.value = "connected"

        mock_get_manager.return_value = mock_manager

        # Exception should propagate through connection manager layer
        with pytest.raises(TableNotFoundError) as exc_info:
            await self.service.execute(
                "SELECT * FROM manager_test",
                user_id="manager_integration"
            )

        # Verify exception classification is preserved
        assert "Table not found error" in str(exc_info.value)
        assert "manager_test" in str(exc_info.value)

    async def test_batch_operations_exception_handling(self):
        """Test that batch operations properly handle and classify exceptions."""
        # Test batch insert with permission error
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Insufficient privileges for batch operation")

        self.service._client = mock_client

        test_data = [
            {"id": 1, "name": "test1"},
            {"id": 2, "name": "test2"}
        ]

        with pytest.raises(PermissionError) as exc_info:
            await self.service.batch_insert("restricted_batch_table", test_data, user_id="batch_test")

        # Verify batch operation exception is properly classified
        assert "Permission error" in str(exc_info.value)
        assert "Insufficient privileges" in str(exc_info.value)

    async def test_health_check_integration_exception_handling(self):
        """Test health check integration with exception classification."""
        # Mock client to raise connection error during health check
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Network connection failed")

        self.service._client = mock_client

        # Health check should handle exceptions gracefully
        result = await self.service.health_check()

        # Verify health check properly reports the error
        assert result["status"] == "unhealthy"
        assert "Network connection failed" in result["error"]

    async def test_multi_user_exception_isolation(self):
        """Test that exceptions are properly isolated per user context."""
        # Test that user-specific exceptions don't interfere with each other
        mock_client = AsyncMock()

        # Set up different exceptions for different operations
        def execute_side_effect(query, params=None):
            if "user1_table" in query:
                raise Exception("Table 'user1_table' doesn't exist")
            elif "user2_table" in query:
                raise Exception("Permission denied for user2")
            else:
                return []

        mock_client.execute.side_effect = execute_side_effect
        self.service._client = mock_client

        # Test user1 gets TableNotFoundError
        with pytest.raises(TableNotFoundError):
            await self.service.execute(
                "SELECT * FROM user1_table",
                user_id="user1",
                operation_context="multi_user_test"
            )

        # Test user2 gets PermissionError
        with pytest.raises(PermissionError):
            await self.service.execute(
                "SELECT * FROM user2_table",
                user_id="user2",
                operation_context="multi_user_test"
            )

    async def test_concurrent_exception_handling(self):
        """Test exception handling under concurrent operations."""
        # Set up mock client with different exceptions for concurrent requests
        mock_client = AsyncMock()

        def concurrent_execute(query, params=None):
            if "concurrent1" in query:
                raise Exception("Table 'concurrent1' does not exist")
            elif "concurrent2" in query:
                raise Exception("Connection timeout for concurrent2")
            else:
                return []

        mock_client.execute.side_effect = concurrent_execute
        self.service._client = mock_client

        # Run concurrent operations that should raise different specific exceptions
        async def operation1():
            with pytest.raises(TableNotFoundError):
                await self.service.execute("SELECT * FROM concurrent1", user_id="conc1")

        async def operation2():
            with pytest.raises(TimeoutError):
                await self.service.execute("SELECT * FROM concurrent2", user_id="conc2")

        # Execute operations concurrently
        await asyncio.gather(operation1(), operation2())

    @patch('netra_backend.app.db.clickhouse._clickhouse_cache')
    async def test_cache_integration_exception_scenarios(self, mock_cache):
        """Test cache integration with various exception scenarios."""
        # Mock cache to simulate different cache-related errors
        mock_cache.get.side_effect = Exception("Cache key invalid for operation")

        mock_client = AsyncMock()
        mock_client.execute.return_value = [{"result": "success"}]

        self.service._client = mock_client

        # Cache error during get should be handled gracefully
        result = await self.service.execute(
            "SELECT * FROM cache_integration_test",
            user_id="cache_integration"
        )

        # Operation should succeed despite cache error
        assert result == [{"result": "success"}]

    async def test_error_context_preservation(self):
        """Test that error context is preserved through integration layers."""
        # Mock client with detailed error context
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Table 'context_test' doesn't exist in database 'test_db'")

        self.service._client = mock_client

        with pytest.raises(TableNotFoundError) as exc_info:
            await self.service.execute(
                "SELECT * FROM context_test",
                user_id="context_user",
                operation_context="context_preservation_test"
            )

        # Verify that context information is preserved in the exception
        error_str = str(exc_info.value)
        assert "Table not found error" in error_str
        assert "context_test" in error_str
        assert "test_db" in error_str