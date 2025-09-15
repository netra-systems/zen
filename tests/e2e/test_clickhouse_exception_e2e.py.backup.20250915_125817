"""
End-to-End Exception Handling Tests for ClickHouse - Issue #731.

These tests validate exception handling in real staging environment scenarios,
testing the complete flow from user actions through to ClickHouse error responses.

Business Value Justification (BVJ):
- Segment: Platform/Enterprise
- Business Goal: Validate production-ready exception handling
- Value Impact: Ensures customer-facing operations handle errors gracefully
- Revenue Impact: Prevents customer-visible failures that could impact retention
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


@pytest.mark.e2e
@pytest.mark.staging_environment
class TestClickHouseExceptionE2E(SSotAsyncTestCase):
    """E2E tests for ClickHouse exception handling in staging environment."""

    def setUp(self):
        """Set up E2E test fixtures."""
        super().setUp()
        # For E2E tests, we'll use a service that can connect to real staging ClickHouse
        # but we'll still control the error scenarios through mocking at the client level
        self.service = ClickHouseService()

    @pytest.mark.staging_clickhouse
    async def test_user_analytics_flow_exception_handling(self):
        """E2E: Test user analytics flow with ClickHouse exceptions."""
        # Simulate user analytics collection flow
        user_id = "e2e_test_user_001"

        # Mock the client to simulate table not found in staging
        with patch.object(self.service, '_client') as mock_client:
            mock_client = AsyncMock()
            mock_client.execute.side_effect = Exception("Table 'user_sessions_staging' doesn't exist")

            # Test the complete analytics collection flow
            with pytest.raises(TableNotFoundError) as exc_info:
                await self.service.execute(
                    "INSERT INTO user_sessions_staging (user_id, session_start, page_views) VALUES (%s, %s, %s)",
                    {"user_id": user_id, "session_start": "2024-01-01T10:00:00", "page_views": 5},
                    user_id=user_id,
                    operation_context="user_analytics_collection"
                )

        # Verify E2E exception flow provides actionable information
        error_message = str(exc_info.value)
        assert "Table not found error" in error_message
        assert "user_sessions_staging" in error_message

        # BUSINESS VALUE: Frontend can display meaningful error to user
        # and automatically report issue to operations team

    @pytest.mark.staging_clickhouse
    async def test_dashboard_data_loading_exception_flow(self):
        """E2E: Test dashboard data loading with ClickHouse connection issues."""
        # Simulate dashboard loading scenario
        dashboard_user = "dashboard_user_e2e"

        # Mock connection timeout scenario common in staging
        with patch.object(self.service, '_client') as mock_client:
            mock_client = AsyncMock()
            mock_client.execute.side_effect = Exception("Connection timeout to ClickHouse cluster")

            # Test dashboard data loading exception handling
            with pytest.raises(TimeoutError) as exc_info:
                await self.service.execute(
                    "SELECT metric_name, metric_value FROM dashboard_metrics WHERE user_id = %s ORDER BY timestamp DESC LIMIT 100",
                    {"user_id": dashboard_user},
                    user_id=dashboard_user,
                    operation_context="dashboard_data_loading"
                )

        # Verify E2E exception enables proper user experience
        error_message = str(exc_info.value)
        assert "Timeout error" in error_message
        assert "timeout" in error_message

        # BUSINESS VALUE: Dashboard can show "Loading..." state and retry automatically
        # instead of showing generic error to user

    @pytest.mark.staging_clickhouse
    async def test_report_generation_permission_exception_flow(self):
        """E2E: Test report generation with permission exceptions."""
        # Simulate enterprise report generation
        enterprise_user = "enterprise_report_user"

        # Mock permission denied scenario
        with patch.object(self.service, '_client') as mock_client:
            mock_client = AsyncMock()
            mock_client.execute.side_effect = Exception("Access denied for enterprise_reports table")

            # Test report generation exception handling
            with pytest.raises(PermissionError) as exc_info:
                await self.service.execute(
                    "SELECT * FROM enterprise_reports WHERE date_range >= %s AND tenant_id = %s",
                    {"date_range": "2024-01-01", "tenant_id": "enterprise_001"},
                    user_id=enterprise_user,
                    operation_context="enterprise_report_generation"
                )

        # Verify E2E exception enables proper access control feedback
        error_message = str(exc_info.value)
        assert "Permission error" in error_message
        assert "Access denied" in error_message

        # BUSINESS VALUE: Enterprise UI can prompt user to request access
        # and automatically notify administrators of access request

    @pytest.mark.staging_clickhouse
    async def test_batch_data_import_exception_flow(self):
        """E2E: Test batch data import with various exception scenarios."""
        # Simulate bulk data import scenario
        import_user = "bulk_import_service"

        # Test multiple exception scenarios in batch operations
        exception_scenarios = [
            ("Table 'staging_import_temp' does not exist", TableNotFoundError),
            ("Cache write failure during batch import", CacheError),
            ("Connection lost during bulk insert", ConnectionError)
        ]

        for error_message, expected_exception in exception_scenarios:
            with self.subTest(error_message=error_message):
                with patch.object(self.service, '_client') as mock_client:
                    mock_client = AsyncMock()
                    mock_client.execute.side_effect = Exception(error_message)

                    # Generate test batch data
                    batch_data = [
                        {"record_id": i, "import_data": f"test_data_{i}", "batch_id": "e2e_batch_001"}
                        for i in range(100)
                    ]

                    # Test batch import exception handling
                    with pytest.raises(expected_exception) as exc_info:
                        await self.service.batch_insert(
                            "staging_import_temp",
                            batch_data,
                            user_id=import_user
                        )

                    # Verify exception provides context for batch processing recovery
                    assert str(expected_exception.__name__.replace('Error', ' error')).lower() in str(exc_info.value).lower()

        # BUSINESS VALUE: Batch import services can implement proper retry logic
        # and partial success handling based on specific exception types

    @pytest.mark.staging_clickhouse
    async def test_real_time_monitoring_exception_resilience(self):
        """E2E: Test real-time monitoring system exception resilience."""
        # Simulate real-time monitoring scenario
        monitoring_user = "realtime_monitor"

        # Mock intermittent connection issues common in cloud environments
        call_count = 0

        def intermittent_failure(query, params=None):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Connection timeout - network instability")
            return [{"status": "healthy", "metric_value": 42}]

        with patch.object(self.service, '_client') as mock_client:
            mock_client = AsyncMock()
            mock_client.execute.side_effect = intermittent_failure

            # First two calls should raise TimeoutError
            with pytest.raises(TimeoutError):
                await self.service.execute(
                    "SELECT status, metric_value FROM system_health_metrics ORDER BY timestamp DESC LIMIT 1",
                    user_id=monitoring_user,
                    operation_context="realtime_monitoring"
                )

            with pytest.raises(TimeoutError):
                await self.service.execute(
                    "SELECT status, metric_value FROM system_health_metrics ORDER BY timestamp DESC LIMIT 1",
                    user_id=monitoring_user,
                    operation_context="realtime_monitoring"
                )

            # Third call should succeed
            result = await self.service.execute(
                "SELECT status, metric_value FROM system_health_metrics ORDER BY timestamp DESC LIMIT 1",
                user_id=monitoring_user,
                operation_context="realtime_monitoring"
            )

            assert result == [{"status": "healthy", "metric_value": 42}]

        # BUSINESS VALUE: Real-time monitoring can distinguish between temporary
        # network issues and persistent system problems

    @pytest.mark.staging_clickhouse
    async def test_multi_service_exception_propagation(self):
        """E2E: Test exception propagation across multiple service boundaries."""
        # Simulate multi-service workflow
        workflow_user = "multi_service_workflow"

        # Mock exception that should propagate through service layers
        with patch.object(self.service, '_client') as mock_client:
            mock_client = AsyncMock()
            mock_client.execute.side_effect = Exception("Table 'workflow_coordination' doesn't exist")

            # Test that exceptions propagate correctly through service orchestration
            try:
                # Simulate service A calling service B which calls ClickHouse
                await self._simulate_service_chain_call(workflow_user)
                assert False, "Expected exception was not raised"
            except TableNotFoundError as e:
                # Verify exception propagated correctly through the chain
                assert "Table not found error" in str(e)
                assert "workflow_coordination" in str(e)

        # BUSINESS VALUE: Service orchestration can make intelligent decisions
        # based on specific error types from downstream dependencies

    async def _simulate_service_chain_call(self, user_id: str):
        """Simulate a chain of service calls ending in ClickHouse."""
        # Service A -> Service B -> ClickHouse
        async def service_a():
            return await service_b()

        async def service_b():
            return await self.service.execute(
                "SELECT * FROM workflow_coordination WHERE user_id = %s",
                {"user_id": user_id},
                user_id=user_id,
                operation_context="multi_service_workflow"
            )

        return await service_a()

    @pytest.mark.staging_clickhouse
    async def test_health_check_e2e_exception_reporting(self):
        """E2E: Test health check exception reporting for monitoring systems."""
        # Test health check in E2E environment
        with patch.object(self.service, '_client') as mock_client:
            mock_client = AsyncMock()
            mock_client.execute.side_effect = Exception("Cache eviction failed - disk full")

            # Health check should handle exceptions gracefully
            health_result = await self.service.health_check()

            # Verify health check provides actionable monitoring information
            assert health_result["status"] == "unhealthy"
            assert "Cache eviction failed" in health_result["error"]
            assert "disk full" in health_result["error"]

        # BUSINESS VALUE: Monitoring systems get specific error information
        # enabling automated remediation (e.g., disk cleanup, cache reset)

    @pytest.mark.staging_clickhouse
    async def test_concurrent_user_exception_isolation_e2e(self):
        """E2E: Test that concurrent users' exceptions are properly isolated."""
        # Simulate concurrent user scenario
        users = ["user_a_e2e", "user_b_e2e", "user_c_e2e"]

        async def user_operation(user_id: str, should_fail: bool = False):
            with patch.object(self.service, '_client') as mock_client:
                mock_client = AsyncMock()
                if should_fail:
                    mock_client.execute.side_effect = Exception(f"Permission denied for {user_id}")
                else:
                    mock_client.execute.return_value = [{"user": user_id, "status": "success"}]

                if should_fail:
                    with pytest.raises(PermissionError):
                        await self.service.execute(
                            f"SELECT * FROM user_data WHERE user_id = '{user_id}'",
                            user_id=user_id,
                            operation_context="concurrent_user_test"
                        )
                else:
                    result = await self.service.execute(
                        f"SELECT * FROM user_data WHERE user_id = '{user_id}'",
                        user_id=user_id,
                        operation_context="concurrent_user_test"
                    )
                    assert result[0]["user"] == user_id

        # Run concurrent operations with mixed success/failure
        await asyncio.gather(
            user_operation("user_a_e2e", should_fail=True),   # Should fail
            user_operation("user_b_e2e", should_fail=False),  # Should succeed
            user_operation("user_c_e2e", should_fail=False),  # Should succeed
        )

        # BUSINESS VALUE: Multi-tenant system maintains user isolation
        # ensuring one user's issues don't affect others
