"""
Mission Critical Business Value Protection Tests for ClickHouse Exception Handling - Issue #731.

These tests protect business-critical functionality by ensuring that ClickHouse
exception handling maintains system stability and prevents revenue-impacting failures.

Business Value Protection:
- $500K+ ARR: Protects analytics pipeline reliability
- Customer Experience: Ensures clear error reporting and graceful degradation
- System Stability: Prevents cascading failures from ClickHouse issues
- Operational Efficiency: Enables faster troubleshooting through specific exceptions
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


class TestClickHouseExceptionBusinessValue(SSotAsyncTestCase):
    """Mission Critical: Business Value Protection for ClickHouse Exception Handling."""

    def setup_method(self, method):
        """Set up mission critical test fixtures."""
        super().setup_method(method)
        self.service = ClickHouseService(force_mock=True)

    async def test_analytics_pipeline_exception_resilience(self):
        """MISSION CRITICAL: Analytics pipeline must handle ClickHouse failures gracefully."""
        # Test scenario: Analytics data collection failure should not break user experience
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Table 'user_analytics' does not exist")

        self.service._client = mock_client

        # Analytics failure should raise specific exception for proper handling
        with pytest.raises(TableNotFoundError) as exc_info:
            await self.service.execute(
                "INSERT INTO user_analytics (user_id, action, timestamp) VALUES (%s, %s, %s)",
                {"user_id": "user123", "action": "login", "timestamp": "2024-01-01"},
                user_id="user123",
                operation_context="analytics_collection"
            )

        # Verify exception provides actionable information for operations team
        error_message = str(exc_info.value)
        assert "Table not found error" in error_message
        assert "user_analytics" in error_message

        # BUSINESS VALUE: Operations team can immediately identify missing table issue
        # rather than generic "something went wrong" error

    async def test_revenue_metrics_collection_exception_handling(self):
        """MISSION CRITICAL: Revenue metrics collection must handle exceptions properly."""
        # Test scenario: Revenue tracking failure should not impact customer operations
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Permission denied for revenue_metrics table")

        self.service._client = mock_client

        # Revenue metrics failure should raise specific exception
        with pytest.raises(PermissionError) as exc_info:
            await self.service.execute(
                "SELECT SUM(revenue) FROM revenue_metrics WHERE date >= %s",
                {"date": "2024-01-01"},
                user_id="admin_user",
                operation_context="revenue_calculation"
            )

        # Verify exception enables proper escalation
        error_message = str(exc_info.value)
        assert "Permission error" in error_message
        assert "Permission denied" in error_message

        # BUSINESS VALUE: Immediate escalation to security team for access issues
        # prevents revenue calculation downtime

    async def test_customer_data_access_exception_specificity(self):
        """MISSION CRITICAL: Customer data access failures must be highly specific."""
        # Test scenario: Customer data query failure needs specific classification
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Connection timeout while accessing customer_data")

        self.service._client = mock_client

        # Customer data access failure should raise specific timeout exception
        with pytest.raises(TimeoutError) as exc_info:
            await self.service.execute(
                "SELECT * FROM customer_data WHERE customer_id = %s",
                {"customer_id": "cust_12345"},
                user_id="support_agent",
                operation_context="customer_support_query"
            )

        # Verify exception provides specific guidance
        error_message = str(exc_info.value)
        assert "Timeout error" in error_message
        assert "timeout" in error_message

        # BUSINESS VALUE: Support agents get immediate feedback on system performance
        # enabling proper customer communication about delays

    async def test_system_health_monitoring_exception_classification(self):
        """MISSION CRITICAL: System health monitoring must classify exceptions for alerting."""
        # Test scenario: Health check failures need proper classification for alerting systems
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Cache eviction failure during health check")

        self.service._client = mock_client

        # Health check should handle cache errors gracefully
        result = await self.service.health_check()

        # Verify health check provides actionable error information
        assert result["status"] == "unhealthy"
        assert "Cache eviction failure" in result["error"]

        # BUSINESS VALUE: Monitoring systems get specific error types for proper alerting
        # and automated escalation to appropriate teams

    async def test_batch_processing_exception_business_impact(self):
        """MISSION CRITICAL: Batch processing failures must provide clear error classification."""
        # Test scenario: Large data processing job failure needs specific error handling
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Table 'batch_processing_temp' doesn't exist")

        self.service._client = mock_client

        large_dataset = [{"id": i, "data": f"batch_data_{i}"} for i in range(1000)]

        # Batch processing failure should raise specific exception
        with pytest.raises(TableNotFoundError) as exc_info:
            await self.service.batch_insert("batch_processing_temp", large_dataset, user_id="batch_processor")

        # Verify exception enables proper batch job recovery
        error_message = str(exc_info.value)
        assert "Table not found error" in error_message
        assert "batch_processing_temp" in error_message

        # BUSINESS VALUE: Batch job orchestration can automatically retry with table creation
        # preventing manual intervention and data processing delays

    async def test_multi_tenant_exception_isolation(self):
        """MISSION CRITICAL: Multi-tenant environment must isolate exceptions properly."""
        # Test scenario: One tenant's ClickHouse issues must not affect others
        mock_client = AsyncMock()

        def tenant_specific_errors(query, params=None):
            if "tenant_a" in str(params):
                raise Exception("Permission denied for tenant_a")
            elif "tenant_b" in str(params):
                raise Exception("Table 'tenant_b_data' does not exist")
            else:
                return [{"status": "success"}]

        mock_client.execute.side_effect = tenant_specific_errors
        self.service._client = mock_client

        # Tenant A should get permission error
        with pytest.raises(PermissionError):
            await self.service.execute(
                "SELECT * FROM tenant_data WHERE tenant_id = %s",
                {"tenant_id": "tenant_a"},
                user_id="tenant_a_user",
                operation_context="tenant_data_access"
            )

        # Tenant B should get table not found error
        with pytest.raises(TableNotFoundError):
            await self.service.execute(
                "SELECT * FROM tenant_b_data",
                {"tenant_id": "tenant_b"},
                user_id="tenant_b_user",
                operation_context="tenant_data_access"
            )

        # Other tenants should continue working
        result = await self.service.execute(
            "SELECT * FROM tenant_data WHERE tenant_id = %s",
            {"tenant_id": "tenant_c"},
            user_id="tenant_c_user",
            operation_context="tenant_data_access"
        )
        assert result == [{"status": "success"}]

        # BUSINESS VALUE: Tenant isolation prevents one customer's issues from affecting others
        # maintaining SLA compliance across all customers

    async def test_performance_degradation_exception_handling(self):
        """MISSION CRITICAL: Performance degradation must be properly classified for scaling decisions."""
        # Test scenario: System slowdown needs proper exception classification
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Query execution timed out - system overloaded")

        self.service._client = mock_client

        # Performance degradation should raise timeout exception
        with pytest.raises(TimeoutError) as exc_info:
            await self.service.execute(
                "SELECT * FROM large_analytics_table ORDER BY timestamp DESC LIMIT 1000000",
                user_id="analytics_user",
                operation_context="performance_critical_query"
            )

        # Verify exception provides performance context
        error_message = str(exc_info.value)
        assert "Timeout error" in error_message
        assert "overloaded" in error_message

        # BUSINESS VALUE: Auto-scaling systems can detect performance issues
        # and trigger infrastructure scaling before customer impact

    async def test_data_consistency_exception_classification(self):
        """MISSION CRITICAL: Data consistency issues must be properly classified."""
        # Test scenario: Data integrity problems need specific error handling
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Cache corruption detected during data validation")

        self.service._client = mock_client

        # Data consistency issues should raise cache error
        with pytest.raises(CacheError) as exc_info:
            await self.service.execute(
                "SELECT * FROM critical_data_table WHERE validation_status = 'active'",
                user_id="data_validator",
                operation_context="data_consistency_check"
            )

        # Verify exception provides data integrity context
        error_message = str(exc_info.value)
        assert "Cache error" in error_message
        assert "corruption" in error_message

        # BUSINESS VALUE: Data integrity monitoring can trigger immediate cache rebuild
        # maintaining data accuracy for business decisions

    async def test_compliance_audit_exception_handling(self):
        """MISSION CRITICAL: Compliance audit queries must handle exceptions with full context."""
        # Test scenario: Audit trail access failure needs detailed error reporting
        mock_client = AsyncMock()
        mock_client.execute.side_effect = Exception("Access denied for audit_trail table - insufficient privileges")

        self.service._client = mock_client

        # Compliance audit failure should raise permission error
        with pytest.raises(PermissionError) as exc_info:
            await self.service.execute(
                "SELECT * FROM audit_trail WHERE date >= %s AND action_type = 'data_access'",
                {"date": "2024-01-01"},
                user_id="compliance_officer",
                operation_context="compliance_audit"
            )

        # Verify exception provides compliance context
        error_message = str(exc_info.value)
        assert "Permission error" in error_message
        assert "audit_trail" in error_message
        assert "insufficient privileges" in error_message

        # BUSINESS VALUE: Compliance team gets immediate notification of access issues
        # ensuring audit requirements are met and regulatory compliance maintained

    async def test_disaster_recovery_exception_scenarios(self):
        """MISSION CRITICAL: Disaster recovery scenarios must handle exceptions properly."""
        # Test scenario: System recovery operations need proper exception classification
        test_scenarios = [
            ("Table 'backup_validation' does not exist", TableNotFoundError),
            ("Connection failed during recovery", ConnectionError),
            ("Recovery operation timed out", TimeoutError),
            ("Permission denied for recovery operations", PermissionError),
            ("Cache restoration failed", CacheError)
        ]

        for error_message, expected_exception_type in test_scenarios:
            # Test each error message scenario
                mock_client = AsyncMock()
                mock_client.execute.side_effect = Exception(error_message)
                self.service._client = mock_client

                with pytest.raises(expected_exception_type):
                    await self.service.execute(
                        "SELECT * FROM recovery_test_table",
                        user_id="disaster_recovery_system",
                        operation_context="disaster_recovery_validation"
                    )

        # BUSINESS VALUE: Disaster recovery automation can make appropriate decisions
        # based on specific error types, improving system recovery times