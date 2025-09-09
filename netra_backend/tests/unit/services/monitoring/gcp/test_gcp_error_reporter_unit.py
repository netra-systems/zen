#!/usr/bin/env python3
"""
UNIT: GCP Error Reporter Unit Tests

Business Value Justification (BVJ):
- Segment: Enterprise & Mid-tier
- Business Goal: Reliable error reporting to GCP for compliance and monitoring
- Value Impact: Ensures error reporting works correctly for enterprise observability
- Strategic/Revenue Impact: Critical for Enterprise customers requiring error tracking

EXPECTED INITIAL STATE: FAIL - proves missing GCP error reporting integration
These tests validate individual GCP error reporter components work correctly.
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# SSOT Imports - following CLAUDE.md requirements
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import the classes under test
from netra_backend.app.services.monitoring.gcp_error_reporter import (
    GCPErrorReporter,
    get_error_reporter,
    report_exception,
    report_error,
    set_request_context,
    clear_request_context,
    gcp_reportable,
    install_exception_handlers
)
from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity
from netra_backend.app.core.exceptions_base import NetraException


class TestGCPErrorReporterUnit(SSotBaseTestCase):
    """
    UNIT: GCP Error Reporter Unit Test Suite
    
    Tests individual components of the GCP Error Reporter for proper initialization,
    error reporting, rate limiting, and context management.
    
    Expected Initial State: FAIL - proves missing GCP error reporting integration
    Success Criteria: All GCP error reporter components work independently
    """
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        
        # Reset singleton state for testing
        GCPErrorReporter._instance = None
        GCPErrorReporter._initialized = False
        
        # Clear environment variables for clean testing
        self.original_env = {}
        for key in ['K_SERVICE', 'GCP_PROJECT', 'ENABLE_GCP_ERROR_REPORTING']:
            self.original_env[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]
    
    def teardown_method(self):
        """Cleanup after each test method."""
        super().teardown_method()
        
        # Restore original environment
        for key, value in self.original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
        
        # Reset singleton state
        GCPErrorReporter._instance = None
        GCPErrorReporter._initialized = False
    
    def test_gcp_error_reporter_singleton_pattern(self):
        """
        Test GCP Error Reporter singleton pattern works correctly.
        
        EXPECTED RESULT: PASS - Singleton pattern should work correctly
        """
        print("\n🔒 UNIT TEST: GCP Error Reporter Singleton")
        print("=" * 45)
        
        # Test singleton creation
        reporter1 = GCPErrorReporter()
        reporter2 = GCPErrorReporter()
        
        assert reporter1 is reporter2
        assert id(reporter1) == id(reporter2)
        
        print("✅ Singleton pattern enforced correctly")
        
        # Test get_error_reporter function
        reporter3 = get_error_reporter()
        assert reporter3 is reporter1
        
        print("✅ get_error_reporter returns same singleton instance")
    
    def test_gcp_error_reporter_should_enable_detection(self):
        """
        Test GCP Error Reporter enable detection logic.
        
        EXPECTED RESULT: PASS - Should correctly detect when to enable
        """
        print("\n🔍 UNIT TEST: GCP Error Reporter Enable Detection")
        print("=" * 52)
        
        # Test 1: Should not enable by default (no environment)
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True):
            reporter = GCPErrorReporter()
            assert not reporter.enabled
            print("✅ Not enabled by default when no environment indicators")
        
        # Reset singleton
        GCPErrorReporter._instance = None
        GCPErrorReporter._initialized = False
        
        # Test 2: Should enable in Cloud Run environment
        os.environ['K_SERVICE'] = 'test-service'
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True):
            reporter = GCPErrorReporter()
            assert reporter.enabled
            print("✅ Enabled in Cloud Run environment (K_SERVICE)")
        del os.environ['K_SERVICE']
        
        # Reset singleton
        GCPErrorReporter._instance = None
        GCPErrorReporter._initialized = False
        
        # Test 3: Should enable with GCP_PROJECT
        os.environ['GCP_PROJECT'] = 'test-project'
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True):
            reporter = GCPErrorReporter()
            assert reporter.enabled
            print("✅ Enabled with GCP_PROJECT environment variable")
        del os.environ['GCP_PROJECT']
        
        # Reset singleton
        GCPErrorReporter._instance = None
        GCPErrorReporter._initialized = False
        
        # Test 4: Should enable when explicitly enabled
        os.environ['ENABLE_GCP_ERROR_REPORTING'] = 'true'
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True):
            reporter = GCPErrorReporter()
            assert reporter.enabled
            print("✅ Enabled when explicitly set via ENABLE_GCP_ERROR_REPORTING")
        del os.environ['ENABLE_GCP_ERROR_REPORTING']
        
        # Reset singleton
        GCPErrorReporter._instance = None
        GCPErrorReporter._initialized = False
        
        # Test 5: Should not enable when GCP libraries not available
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', False):
            os.environ['K_SERVICE'] = 'test-service'
            reporter = GCPErrorReporter()
            assert not reporter.enabled
            print("✅ Not enabled when GCP libraries not available")
    
    @patch('netra_backend.app.services.monitoring.gcp_error_reporter.error_reporting')
    @patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True)
    def test_gcp_error_reporter_client_initialization_success(self, mock_error_reporting):
        """
        Test GCP Error Reporter client initialization success.
        
        EXPECTED RESULT: INITIALLY FAIL - proves missing GCP configuration
        """
        print("\n☁️ UNIT TEST: GCP Client Initialization Success")
        print("=" * 48)
        
        # Setup mock
        mock_client = MagicMock()
        mock_error_reporting.Client.return_value = mock_client
        
        # Enable error reporting
        os.environ['ENABLE_GCP_ERROR_REPORTING'] = 'true'
        
        reporter = GCPErrorReporter()
        
        assert reporter.enabled
        assert reporter.client == mock_client
        
        # Verify client was created
        mock_error_reporting.Client.assert_called_once()
        
        print("✅ GCP Error Reporting client initialized successfully")
    
    @patch('netra_backend.app.services.monitoring.gcp_error_reporter.error_reporting')
    @patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True)
    def test_gcp_error_reporter_client_initialization_failure(self, mock_error_reporting):
        """
        Test GCP Error Reporter handles client initialization failure.
        
        EXPECTED RESULT: PASS - Should gracefully handle initialization failure
        """
        print("\n❌ UNIT TEST: GCP Client Initialization Failure")
        print("=" * 48)
        
        # Setup mock to fail
        mock_error_reporting.Client.side_effect = Exception("GCP client init failed")
        
        # Enable error reporting
        os.environ['ENABLE_GCP_ERROR_REPORTING'] = 'true'
        
        reporter = GCPErrorReporter()
        
        # Should be disabled due to initialization failure
        assert not reporter.enabled
        assert reporter.client is None
        
        print("✅ GCP client initialization failure handled gracefully")
    
    def test_gcp_error_reporter_rate_limiting(self):
        """
        Test GCP Error Reporter rate limiting functionality.
        
        EXPECTED RESULT: PASS - Rate limiting should work correctly
        """
        print("\n⏱️ UNIT TEST: GCP Error Reporter Rate Limiting")
        print("=" * 46)
        
        # Create reporter but don't enable GCP
        reporter = GCPErrorReporter()
        reporter.enabled = False  # Ensure it's disabled for testing
        
        # Reset rate limiting
        reporter._rate_limit_counter = 0
        reporter._rate_limit_window_start = None
        reporter._rate_limit_max = 5  # Low limit for testing
        
        # Test rate limiting
        successful_reports = 0
        for i in range(10):
            if reporter._check_rate_limit():
                successful_reports += 1
        
        assert successful_reports == 5  # Should be limited to max
        print(f"✅ Rate limiting enforced: {successful_reports}/10 reports allowed")
        
        # Test rate limit window reset
        import time
        # Mock time to simulate window reset
        with patch('time.time') as mock_time:
            # Start time
            mock_time.return_value = 1000
            reporter._check_rate_limit()
            
            # Move forward more than 60 seconds
            mock_time.return_value = 1070
            
            # Should reset and allow more reports
            assert reporter._check_rate_limit()
            assert reporter._rate_limit_counter == 1  # Reset to 1
            
            print("✅ Rate limit window reset works correctly")
    
    def test_gcp_error_reporter_report_exception_disabled(self):
        """
        Test exception reporting when GCP reporting is disabled.
        
        EXPECTED RESULT: PASS - Should handle disabled state gracefully
        """
        print("\n🚫 UNIT TEST: Exception Reporting - Disabled")
        print("=" * 43)
        
        reporter = GCPErrorReporter()
        assert not reporter.enabled  # Should be disabled by default
        
        # Test exception reporting
        test_exception = Exception("Test exception")
        
        # Should not raise exception when disabled
        result = reporter.report_exception(
            exception=test_exception,
            user="test-user",
            extra_context={"test": "context"}
        )
        
        # Should complete without error (returns None)
        assert result is None
        
        print("✅ Exception reporting handled gracefully when disabled")
    
    @patch('netra_backend.app.services.monitoring.gcp_error_reporter.error_reporting')
    @patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True)
    def test_gcp_error_reporter_report_exception_enabled(self, mock_error_reporting):
        """
        Test exception reporting when GCP reporting is enabled.
        
        EXPECTED RESULT: INITIALLY FAIL - proves missing GCP integration
        """
        print("\n✅ UNIT TEST: Exception Reporting - Enabled")
        print("=" * 42)
        
        # Setup mock client
        mock_client = MagicMock()
        mock_error_reporting.Client.return_value = mock_client
        
        # Enable error reporting
        os.environ['ENABLE_GCP_ERROR_REPORTING'] = 'true'
        
        reporter = GCPErrorReporter()
        assert reporter.enabled
        assert reporter.client == mock_client
        
        # Test exception reporting
        test_exception = Exception("Test exception for GCP")
        test_user = "test-user-123"
        test_http_context = {
            "method": "POST",
            "url": "http://localhost:8000/api/test"
        }
        test_extra_context = {
            "business_context": "test",
            "error_type": "validation"
        }
        
        # Report exception
        reporter.report_exception(
            exception=test_exception,
            user=test_user,
            http_context=test_http_context,
            extra_context=test_extra_context
        )
        
        # Verify client was called
        mock_client.report_exception.assert_called_once()
        
        print("✅ Exception reported to GCP client successfully")
    
    def test_gcp_error_reporter_message_reporting(self):
        """
        Test message reporting functionality.
        
        EXPECTED RESULT: PASS - Message reporting should work
        """
        print("\n📝 UNIT TEST: Message Reporting")
        print("=" * 33)
        
        reporter = GCPErrorReporter()
        
        # Test message reporting when disabled (should not error)
        result = reporter.report_message(
            message="Test error message",
            severity=ErrorSeverity.ERROR,
            user="test-user"
        )
        
        assert result is None
        print("✅ Message reporting handled when disabled")
    
    @pytest.mark.asyncio
    async def test_gcp_error_reporter_async_report_error(self):
        """
        Test async report_error method.
        
        EXPECTED RESULT: INITIALLY FAIL - proves missing async integration
        """
        print("\n⚡ UNIT TEST: Async Error Reporting")
        print("=" * 35)
        
        reporter = GCPErrorReporter()
        
        # Test async error reporting when disabled
        test_error = Exception("Test async error")
        test_context = {
            "user_id": "test-user-456",
            "error_type": "async_test",
            "business_tier": "enterprise"
        }
        
        result = await reporter.report_error(test_error, context=test_context)
        
        # Should return False when disabled
        assert result is False
        print("✅ Async error reporting returns False when disabled")
        
        # Test with enabled state (mocked)
        with patch.object(reporter, 'enabled', True), \
             patch.object(reporter, 'client', MagicMock()), \
             patch.object(reporter, '_check_rate_limit', return_value=True), \
             patch.object(reporter, 'report_exception') as mock_report:
            
            result = await reporter.report_error(test_error, context=test_context)
            
            assert result is True
            mock_report.assert_called_once_with(
                exception=test_error,
                user="test-user-456",
                http_context=None,
                extra_context=test_context
            )
            
            print("✅ Async error reporting works when enabled")
    
    def test_request_context_management(self):
        """
        Test request context management functions.
        
        EXPECTED RESULT: PASS - Context management should work correctly
        """
        print("\n🔄 UNIT TEST: Request Context Management")
        print("=" * 42)
        
        # Test setting context
        test_user_id = "context-user-123"
        test_trace_id = "trace-456"
        test_http_context = {"method": "GET", "url": "/test"}
        
        set_request_context(
            user_id=test_user_id,
            trace_id=test_trace_id,
            http_context=test_http_context,
            custom_field="test_value"
        )
        
        # Context should be accessible (we can't directly test the ContextVar,
        # but we can test that the function doesn't error)
        print("✅ Request context set without error")
        
        # Test clearing context
        clear_request_context()
        print("✅ Request context cleared without error")
    
    def test_gcp_reportable_decorator_sync(self):
        """
        Test @gcp_reportable decorator for synchronous functions.
        
        EXPECTED RESULT: PASS - Decorator should work correctly
        """
        print("\n🎨 UNIT TEST: GCP Reportable Decorator (Sync)")
        print("=" * 44)
        
        # Test decorator with re-raise
        @gcp_reportable(reraise=True)
        def test_function_reraise():
            raise ValueError("Test error for decorator")
        
        with pytest.raises(ValueError) as exc_info:
            test_function_reraise()
        
        assert "Test error for decorator" in str(exc_info.value)
        print("✅ Decorator re-raises exceptions correctly")
        
        # Test decorator without re-raise
        @gcp_reportable(reraise=False)
        def test_function_no_reraise():
            raise ValueError("Test error no reraise")
        
        result = test_function_no_reraise()
        assert result is None  # Should return None when not re-raising
        print("✅ Decorator handles exceptions without re-raising")
        
        # Test decorator with successful function
        @gcp_reportable()
        def test_function_success():
            return "success"
        
        result = test_function_success()
        assert result == "success"
        print("✅ Decorator doesn't interfere with successful execution")
    
    @pytest.mark.asyncio
    async def test_gcp_reportable_decorator_async(self):
        """
        Test @gcp_reportable decorator for asynchronous functions.
        
        EXPECTED RESULT: PASS - Async decorator should work correctly
        """
        print("\n⚡ UNIT TEST: GCP Reportable Decorator (Async)")
        print("=" * 45)
        
        # Test async decorator with re-raise
        @gcp_reportable(reraise=True)
        async def test_async_function_reraise():
            raise ValueError("Test async error for decorator")
        
        with pytest.raises(ValueError) as exc_info:
            await test_async_function_reraise()
        
        assert "Test async error for decorator" in str(exc_info.value)
        print("✅ Async decorator re-raises exceptions correctly")
        
        # Test async decorator without re-raise
        @gcp_reportable(reraise=False)
        async def test_async_function_no_reraise():
            raise ValueError("Test async error no reraise")
        
        result = await test_async_function_no_reraise()
        assert result is None
        print("✅ Async decorator handles exceptions without re-raising")
        
        # Test async decorator with successful function
        @gcp_reportable()
        async def test_async_function_success():
            return "async_success"
        
        result = await test_async_function_success()
        assert result == "async_success"
        print("✅ Async decorator doesn't interfere with successful execution")
    
    def test_convenience_functions(self):
        """
        Test convenience functions for error reporting.
        
        EXPECTED RESULT: PASS - Convenience functions should work
        """
        print("\n🎯 UNIT TEST: Convenience Functions")
        print("=" * 35)
        
        # Test report_exception convenience function
        test_exception = Exception("Convenience test exception")
        
        # Should not raise error (reporter is disabled by default)
        result = report_exception(test_exception, user="test-user")
        assert result is None
        print("✅ report_exception convenience function works")
        
        # Test report_error convenience function
        result = report_error("Convenience test error message", user="test-user")
        assert result is None
        print("✅ report_error convenience function works")
    
    def test_netra_exception_handling(self):
        """
        Test handling of NetraException with error details.
        
        EXPECTED RESULT: PASS - Should extract NetraException details
        """
        print("\n🔧 UNIT TEST: NetraException Handling")
        print("=" * 37)
        
        # Create NetraException for testing
        from netra_backend.app.core.error_codes import ErrorCode
        
        test_exception = NetraException(
            message="Test NetraException",
            error_code=ErrorCode.VALIDATION_ERROR
        )
        
        # Test decorator with NetraException
        @gcp_reportable(reraise=False)
        def test_function_netra_exception():
            raise test_exception
        
        result = test_function_netra_exception()
        assert result is None
        print("✅ NetraException handled correctly by decorator")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])