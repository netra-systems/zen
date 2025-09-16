#!/usr/bin/env python3
"""
UNIT: GCP Error Service Unit Tests

Business Value Justification (BVJ):
- Segment: Enterprise & Mid-tier
- Business Goal: Structured error data management and analysis
- Value Impact: Enables automated error analysis and trend detection
- Strategic/Revenue Impact: +$15K MRR from enhanced reliability monitoring

EXPECTED INITIAL STATE: FAIL - proves missing GCP error service integration
These tests validate individual GCP error service components work correctly.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# SSOT Imports - following CLAUDE.md requirements
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import the classes under test
from netra_backend.app.services.monitoring.gcp_error_service import GCPErrorService
from netra_backend.app.schemas.monitoring_schemas import (
    GCPErrorServiceConfig,
    GCPCredentialsConfig,
    ErrorQuery,
    ErrorResponse,
    ErrorSummary,
    ErrorDetailResponse,
    ErrorResolution,
    ErrorSeverity,
    ErrorStatus,
    GCPError,
    GCPErrorEvent,
    MonitoringErrorContext
)
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.error_codes import ErrorCode


class TestGCPErrorServiceUnit(SSotBaseTestCase):
    """
    UNIT: GCP Error Service Unit Test Suite
    
    Tests individual components of the GCP Error Service for proper configuration,
    error fetching, formatting, and management functionality.
    
    Expected Initial State: FAIL - proves missing GCP error service integration
    Success Criteria: All GCP error service components work independently
    """
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        
        # Create test configuration
        self.test_config = GCPErrorServiceConfig(
            project_id="test-project",
            credentials=GCPCredentialsConfig(project_id="test-project"),
            rate_limit_per_minute=100,
            batch_size=50,
            timeout_seconds=30,
            retry_attempts=3,
            enable_pii_redaction=True
        )
        
        # Test data
        self.test_project_id = "test-project"
        self.test_error_id = "test-error-123"
    
    def test_gcp_error_service_initialization(self):
        """
        Test GCP Error Service initialization with configuration.
        
        EXPECTED RESULT: PASS - Service should initialize correctly with config
        """
        print("\n[U+1F680] UNIT TEST: GCP Error Service Initialization")
        print("=" * 50)
        
        # Create service
        service = GCPErrorService(self.test_config)
        
        # Verify initialization
        assert service.config == self.test_config
        assert service.client is None  # Not initialized yet
        
        # Verify components are created
        assert service.client_manager is not None
        assert service.error_formatter is not None
        assert service.rate_limiter is not None
        
        print(" PASS:  GCP Error Service initialized correctly")
        print(f"   Project ID: {service.config.project_id}")
        print(f"   Rate Limit: {service.config.rate_limit_per_minute}/min")
        print(f"   Batch Size: {service.config.batch_size}")
        print(f"   PII Redaction: {service.config.enable_pii_redaction}")
    
    @pytest.mark.asyncio
    async def test_gcp_error_service_initialize_client(self):
        """
        Test GCP Error Service client initialization.
        
        EXPECTED RESULT: INITIALLY FAIL - proves missing GCP client integration
        """
        print("\n[U+2601][U+FE0F] UNIT TEST: GCP Error Service Client Initialization")
        print("=" * 56)
        
        service = GCPErrorService(self.test_config)
        
        # Mock the client manager
        mock_client = MagicMock()
        service.client_manager.initialize_client = AsyncMock(return_value=mock_client)
        
        # Initialize the service
        await service.initialize()
        
        # Verify client was set
        assert service.client == mock_client
        
        # Verify client manager was called
        service.client_manager.initialize_client.assert_called_once()
        
        print(" PASS:  GCP Error Service client initialized successfully")
    
    def test_time_range_parsing(self):
        """
        Test time range parsing functionality.
        
        EXPECTED RESULT: PASS - Time range parsing should work correctly
        """
        print("\n[U+23F0] UNIT TEST: Time Range Parsing")
        print("=" * 32)
        
        service = GCPErrorService(self.test_config)
        
        # Test different time range formats
        end_time = datetime.now(timezone.utc)
        
        # Test hours
        start_time = service._parse_time_range("24h", end_time)
        expected_start = end_time - timedelta(hours=24)
        assert abs((start_time - expected_start).total_seconds()) < 1
        print(" PASS:  24h time range parsed correctly")
        
        start_time = service._parse_time_range("6h", end_time)
        expected_start = end_time - timedelta(hours=6)
        assert abs((start_time - expected_start).total_seconds()) < 1
        print(" PASS:  6h time range parsed correctly")
        
        # Test days
        start_time = service._parse_time_range("7d", end_time)
        expected_start = end_time - timedelta(days=7)
        assert abs((start_time - expected_start).total_seconds()) < 1
        print(" PASS:  7d time range parsed correctly")
        
        # Test invalid format (should default to 24h)
        start_time = service._parse_time_range("invalid", end_time)
        expected_start = end_time - timedelta(hours=24)
        assert abs((start_time - expected_start).total_seconds()) < 1
        print(" PASS:  Invalid time range defaults to 24h correctly")
    
    def test_build_time_range(self):
        """
        Test building time range for GCP API requests.
        
        EXPECTED RESULT: PASS - Time range building should work correctly
        """
        print("\n[U+1F4C5] UNIT TEST: Build Time Range")
        print("=" * 30)
        
        service = GCPErrorService(self.test_config)
        
        # Test building time range
        time_range = service._build_time_range("12h")
        
        assert "period" in time_range
        assert "start_time" in time_range["period"]
        assert "end_time" in time_range["period"]
        
        start_time = time_range["period"]["start_time"]
        end_time = time_range["period"]["end_time"]
        
        # Verify it's approximately 12 hours difference
        time_diff = end_time - start_time
        assert abs(time_diff.total_seconds() - 12 * 3600) < 60  # Within 1 minute
        
        print(" PASS:  Time range built correctly for GCP API")
    
    def test_build_list_request(self):
        """
        Test building GCP list request with filters.
        
        EXPECTED RESULT: PASS - Request building should work correctly
        """
        print("\n[U+1F4CB] UNIT TEST: Build List Request")
        print("=" * 32)
        
        service = GCPErrorService(self.test_config)
        
        # Create test query
        query = ErrorQuery(
            status=ErrorStatus.OPEN,
            limit=25,
            service="test-service",
            severity=ErrorSeverity.ERROR,
            time_range="6h",
            page_token="test-token"
        )
        
        project_name = f"projects/{self.test_project_id}"
        time_range = {"period": {"start_time": datetime.now(), "end_time": datetime.now()}}
        
        # Build request
        request = service._build_list_request(project_name, time_range, query)
        
        # Verify request structure
        assert request["parent"] == project_name
        assert request["time_range"] == time_range
        assert request["service_filter"]["service"] == "test-service"
        assert request["page_token"] == "test-token"
        assert request["page_size"] == 25  # Should use query limit
        
        print(" PASS:  List request built correctly with all filters")
        
        # Test without optional filters
        query_minimal = ErrorQuery(limit=100)
        request_minimal = service._build_list_request(project_name, time_range, query_minimal)
        
        assert "service_filter" not in request_minimal
        assert "page_token" not in request_minimal
        assert request_minimal["page_size"] == 50  # Should use batch_size limit
        
        print(" PASS:  Minimal list request built correctly")
    
    def test_count_by_severity(self):
        """
        Test counting errors by severity level.
        
        EXPECTED RESULT: PASS - Severity counting should work correctly
        """
        print("\n CHART:  UNIT TEST: Count By Severity")
        print("=" * 31)
        
        service = GCPErrorService(self.test_config)
        
        # Create test errors with different severities
        errors = [
            GCPError(
                id="error1",
                message="Critical error",
                service="test-service",
                severity=ErrorSeverity.CRITICAL,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            ),
            GCPError(
                id="error2",
                message="Regular error",
                service="test-service",
                severity=ErrorSeverity.ERROR,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            ),
            GCPError(
                id="error3",
                message="Another critical",
                service="test-service",
                severity=ErrorSeverity.CRITICAL,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            ),
            GCPError(
                id="error4",
                message="Warning message",
                service="test-service",
                severity=ErrorSeverity.WARNING,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            )
        ]
        
        # Count by severity
        counts = service._count_by_severity(errors)
        
        assert counts["critical_errors"] == 2
        assert counts["error_errors"] == 1
        assert counts["warning_errors"] == 0  # Not counted in this method
        assert counts["info_errors"] == 0
        
        print(" PASS:  Severity counting works correctly")
        print(f"   Critical: {counts['critical_errors']}")
        print(f"   Error: {counts['error_errors']}")
    
    def test_count_by_status(self):
        """
        Test counting errors by status.
        
        EXPECTED RESULT: PASS - Status counting should work correctly
        """
        print("\n[U+1F4C8] UNIT TEST: Count By Status")
        print("=" * 28)
        
        service = GCPErrorService(self.test_config)
        
        # Create test errors with different statuses
        errors = [
            GCPError(
                id="error1",
                message="Open error",
                service="test-service",
                severity=ErrorSeverity.ERROR,
                status=ErrorStatus.OPEN,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            ),
            GCPError(
                id="error2",
                message="Resolved error",
                service="test-service",
                severity=ErrorSeverity.ERROR,
                status=ErrorStatus.RESOLVED,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            ),
            GCPError(
                id="error3",
                message="Another open",
                service="test-service",
                severity=ErrorSeverity.ERROR,
                status=ErrorStatus.OPEN,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            )
        ]
        
        # Count by status
        counts = service._count_by_status(errors)
        
        assert counts["open_errors"] == 2
        assert counts["resolved_errors"] == 1
        
        print(" PASS:  Status counting works correctly")
        print(f"   Open: {counts['open_errors']}")
        print(f"   Resolved: {counts['resolved_errors']}")
    
    @pytest.mark.asyncio
    async def test_create_summary(self):
        """
        Test creating error summary statistics.
        
        EXPECTED RESULT: PASS - Summary creation should work correctly
        """
        print("\n[U+1F4CB] UNIT TEST: Create Error Summary")
        print("=" * 35)
        
        service = GCPErrorService(self.test_config)
        
        # Create test errors
        errors = [
            GCPError(
                id="error1",
                message="Test error 1",
                service="service-a",
                severity=ErrorSeverity.CRITICAL,
                status=ErrorStatus.OPEN,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            ),
            GCPError(
                id="error2",
                message="Test error 2",
                service="service-b",
                severity=ErrorSeverity.ERROR,
                status=ErrorStatus.RESOLVED,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            )
        ]
        
        query = ErrorQuery(time_range="24h")
        
        # Create summary
        summary = await service._create_summary(errors, query)
        
        # Verify summary
        assert summary.total_errors == 2
        assert summary.critical_errors == 1
        assert summary.error_errors == 1
        assert summary.open_errors == 1
        assert summary.resolved_errors == 1
        assert set(summary.affected_services) == {"service-a", "service-b"}
        assert isinstance(summary.time_range_start, datetime)
        assert isinstance(summary.time_range_end, datetime)
        
        print(" PASS:  Error summary created correctly")
        print(f"   Total Errors: {summary.total_errors}")
        print(f"   Affected Services: {summary.affected_services}")
    
    def test_get_query_time_range(self):
        """
        Test getting time range for summary.
        
        EXPECTED RESULT: PASS - Time range extraction should work correctly
        """
        print("\n[U+1F550] UNIT TEST: Get Query Time Range")
        print("=" * 35)
        
        service = GCPErrorService(self.test_config)
        
        # Test time range extraction
        time_range = service._get_query_time_range("12h")
        
        assert "time_range_start" in time_range
        assert "time_range_end" in time_range
        assert isinstance(time_range["time_range_start"], datetime)
        assert isinstance(time_range["time_range_end"], datetime)
        
        # Verify approximately 12 hours difference
        start = time_range["time_range_start"]
        end = time_range["time_range_end"]
        time_diff = end - start
        assert abs(time_diff.total_seconds() - 12 * 3600) < 60
        
        print(" PASS:  Query time range extracted correctly")
    
    @pytest.mark.asyncio
    async def test_fetch_errors_rate_limiting(self):
        """
        Test that fetch_errors respects rate limiting.
        
        EXPECTED RESULT: PASS - Rate limiting should be enforced
        """
        print("\n[U+23F1][U+FE0F] UNIT TEST: Fetch Errors Rate Limiting")
        print("=" * 40)
        
        service = GCPErrorService(self.test_config)
        
        # Mock rate limiter to simulate rate limit exceeded
        service.rate_limiter.enforce_rate_limit = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )
        
        query = ErrorQuery()
        
        # Test rate limiting
        with pytest.raises(Exception) as exc_info:
            await service.fetch_errors(query)
        
        assert "Rate limit exceeded" in str(exc_info.value)
        
        # Verify rate limiter was called
        service.rate_limiter.enforce_rate_limit.assert_called_once()
        
        print(" PASS:  Rate limiting enforced correctly in fetch_errors")
    
    @pytest.mark.asyncio
    async def test_fetch_raw_errors_client_not_initialized(self):
        """
        Test fetching raw errors when client is not initialized.
        
        EXPECTED RESULT: INITIALLY FAIL - proves missing client initialization
        """
        print("\n FAIL:  UNIT TEST: Fetch Raw Errors - No Client")
        print("=" * 41)
        
        service = GCPErrorService(self.test_config)
        
        # Client should be None initially
        assert service.client is None
        
        query = ErrorQuery()
        
        # Should raise exception when client not initialized
        with pytest.raises(AttributeError):
            await service._fetch_raw_errors(query)
        
        print(" PASS:  Proper error when client not initialized")
    
    @pytest.mark.asyncio
    async def test_fetch_raw_errors_with_client(self):
        """
        Test fetching raw errors with initialized client.
        
        EXPECTED RESULT: INITIALLY FAIL - proves missing GCP client integration
        """
        print("\n[U+2601][U+FE0F] UNIT TEST: Fetch Raw Errors - With Client")
        print("=" * 43)
        
        service = GCPErrorService(self.test_config)
        
        # Mock client
        mock_client = MagicMock()
        mock_response = [{"error": "test1"}, {"error": "test2"}]
        mock_client.list_group_stats.return_value = mock_response
        service.client = mock_client
        
        query = ErrorQuery(time_range="6h", service="test-service")
        
        # Fetch raw errors
        raw_errors = await service._fetch_raw_errors(query)
        
        assert raw_errors == mock_response
        
        # Verify client was called with correct parameters
        mock_client.list_group_stats.assert_called_once()
        call_args = mock_client.list_group_stats.call_args[1]["request"]
        
        assert call_args["parent"] == f"projects/{self.test_project_id}"
        assert "time_range" in call_args
        assert call_args["service_filter"]["service"] == "test-service"
        
        print(" PASS:  Raw errors fetched correctly with client")
    
    def test_get_service_status(self):
        """
        Test getting service status and metrics.
        
        EXPECTED RESULT: PASS - Service status should be returned correctly
        """
        print("\n CHART:  UNIT TEST: Get Service Status")
        print("=" * 31)
        
        service = GCPErrorService(self.test_config)
        
        # Mock rate limiter status
        service.rate_limiter.get_current_usage = MagicMock(
            return_value={"requests": 10, "window_start": 1000}
        )
        
        # Get status
        status = service.get_service_status()
        
        # Verify status structure
        assert "initialized" in status
        assert "project_id" in status
        assert "rate_limiter" in status
        assert "pii_redaction_enabled" in status
        
        assert status["initialized"] is False  # Client not initialized
        assert status["project_id"] == self.test_project_id
        assert status["pii_redaction_enabled"] is True
        assert status["rate_limiter"]["requests"] == 10
        
        print(" PASS:  Service status returned correctly")
        print(f"   Initialized: {status['initialized']}")
        print(f"   Project ID: {status['project_id']}")
        print(f"   PII Redaction: {status['pii_redaction_enabled']}")
    
    @pytest.mark.asyncio
    async def test_build_error_context(self):
        """
        Test building error context for error details.
        
        EXPECTED RESULT: PASS - Error context should be built correctly
        """
        print("\n[U+1F527] UNIT TEST: Build Error Context")
        print("=" * 33)
        
        service = GCPErrorService(self.test_config)
        
        # Mock rate limiter
        service.rate_limiter.get_current_usage = MagicMock(
            return_value={"current": 5, "limit": 100}
        )
        
        # Create test error
        test_error = GCPError(
            id=self.test_error_id,
            message="Test error",
            service="test-service",
            severity=ErrorSeverity.ERROR,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc)
        )
        
        # Build context
        context = await service._build_error_context(test_error)
        
        # Verify context
        assert context["error_id"] == self.test_error_id
        assert context["service"] == "test-service"
        assert context["severity"] == ErrorSeverity.ERROR
        assert "rate_limiter_status" in context
        assert context["rate_limiter_status"]["current"] == 5
        
        print(" PASS:  Error context built correctly")
    
    @pytest.mark.asyncio
    async def test_mark_error_resolved(self):
        """
        Test marking error as resolved.
        
        EXPECTED RESULT: PASS - Error resolution should work correctly
        """
        print("\n PASS:  UNIT TEST: Mark Error Resolved")
        print("=" * 33)
        
        service = GCPErrorService(self.test_config)
        
        # Create resolution
        resolution = ErrorResolution(
            resolution_note="Fixed in deployment v1.2.3",
            resolved_by="engineer@company.com"
        )
        
        # Mark error as resolved
        result = await service._mark_error_resolved(self.test_error_id, resolution)
        
        # Should return True (current implementation just logs)
        assert result is True
        
        print(" PASS:  Error marked as resolved successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])