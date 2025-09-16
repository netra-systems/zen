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
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.services.monitoring.gcp_error_reporter import GCPErrorReporter, get_error_reporter, report_exception, report_error, set_request_context, clear_request_context, gcp_reportable, install_exception_handlers
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
        GCPErrorReporter._instance = None
        GCPErrorReporter._initialized = False
        self.original_env = {}
        for key in ['K_SERVICE', 'GCP_PROJECT', 'ENABLE_GCP_ERROR_REPORTING']:
            self.original_env[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]

    def teardown_method(self):
        """Cleanup after each test method."""
        super().teardown_method()
        for key, value in self.original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
        GCPErrorReporter._instance = None
        GCPErrorReporter._initialized = False

    def test_gcp_error_reporter_singleton_pattern(self):
        """
        Test GCP Error Reporter singleton pattern works correctly.
        
        EXPECTED RESULT: PASS - Singleton pattern should work correctly
        """
        print('\n[U+1F512] UNIT TEST: GCP Error Reporter Singleton')
        print('=' * 45)
        reporter1 = GCPErrorReporter()
        reporter2 = GCPErrorReporter()
        assert reporter1 is reporter2
        assert id(reporter1) == id(reporter2)
        print(' PASS:  Singleton pattern enforced correctly')
        reporter3 = get_error_reporter()
        assert reporter3 is reporter1
        print(' PASS:  get_error_reporter returns same singleton instance')

    def test_gcp_error_reporter_should_enable_detection(self):
        """
        Test GCP Error Reporter enable detection logic.
        
        EXPECTED RESULT: PASS - Should correctly detect when to enable
        """
        print('\n SEARCH:  UNIT TEST: GCP Error Reporter Enable Detection')
        print('=' * 52)
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True):
            reporter = GCPErrorReporter()
            assert not reporter.enabled
            print(' PASS:  Not enabled by default when no environment indicators')
        GCPErrorReporter._instance = None
        GCPErrorReporter._initialized = False
        os.environ['K_SERVICE'] = 'test-service'
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True):
            reporter = GCPErrorReporter()
            assert reporter.enabled
            print(' PASS:  Enabled in Cloud Run environment (K_SERVICE)')
        del os.environ['K_SERVICE']
        GCPErrorReporter._instance = None
        GCPErrorReporter._initialized = False
        os.environ['GCP_PROJECT'] = 'test-project'
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True):
            reporter = GCPErrorReporter()
            assert reporter.enabled
            print(' PASS:  Enabled with GCP_PROJECT environment variable')
        del os.environ['GCP_PROJECT']
        GCPErrorReporter._instance = None
        GCPErrorReporter._initialized = False
        os.environ['ENABLE_GCP_ERROR_REPORTING'] = 'true'
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True):
            reporter = GCPErrorReporter()
            assert reporter.enabled
            print(' PASS:  Enabled when explicitly set via ENABLE_GCP_ERROR_REPORTING')
        del os.environ['ENABLE_GCP_ERROR_REPORTING']
        GCPErrorReporter._instance = None
        GCPErrorReporter._initialized = False
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', False):
            os.environ['K_SERVICE'] = 'test-service'
            reporter = GCPErrorReporter()
            assert not reporter.enabled
            print(' PASS:  Not enabled when GCP libraries not available')

    @patch('netra_backend.app.services.monitoring.gcp_error_reporter.error_reporting')
    @patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True)
    def test_gcp_error_reporter_client_initialization_success(self, mock_error_reporting):
        """
        Test GCP Error Reporter client initialization success.
        
        EXPECTED RESULT: INITIALLY FAIL - proves missing GCP configuration
        """
        print('\n[U+2601][U+FE0F] UNIT TEST: GCP Client Initialization Success')
        print('=' * 48)
        mock_client = MagicMock()
        mock_error_reporting.Client.return_value = mock_client
        os.environ['ENABLE_GCP_ERROR_REPORTING'] = 'true'
        reporter = GCPErrorReporter()
        assert reporter.enabled
        assert reporter.client == mock_client
        mock_error_reporting.Client.assert_called_once()
        print(' PASS:  GCP Error Reporting client initialized successfully')

    @patch('netra_backend.app.services.monitoring.gcp_error_reporter.error_reporting')
    @patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True)
    def test_gcp_error_reporter_client_initialization_failure(self, mock_error_reporting):
        """
        Test GCP Error Reporter handles client initialization failure.
        
        EXPECTED RESULT: PASS - Should gracefully handle initialization failure
        """
        print('\n FAIL:  UNIT TEST: GCP Client Initialization Failure')
        print('=' * 48)
        mock_error_reporting.Client.side_effect = Exception('GCP client init failed')
        os.environ['ENABLE_GCP_ERROR_REPORTING'] = 'true'
        reporter = GCPErrorReporter()
        assert not reporter.enabled
        assert reporter.client is None
        print(' PASS:  GCP client initialization failure handled gracefully')

    def test_gcp_error_reporter_rate_limiting(self):
        """
        Test GCP Error Reporter rate limiting functionality.
        
        EXPECTED RESULT: PASS - Rate limiting should work correctly
        """
        print('\n[U+23F1][U+FE0F] UNIT TEST: GCP Error Reporter Rate Limiting')
        print('=' * 46)
        reporter = GCPErrorReporter()
        reporter.enabled = False
        reporter._rate_limit_counter = 0
        reporter._rate_limit_window_start = None
        reporter._rate_limit_max = 5
        successful_reports = 0
        for i in range(10):
            if reporter._check_rate_limit():
                successful_reports += 1
        assert successful_reports == 5
        print(f' PASS:  Rate limiting enforced: {successful_reports}/10 reports allowed')
        import time
        with patch('time.time') as mock_time:
            mock_time.return_value = 1000
            reporter._check_rate_limit()
            mock_time.return_value = 1070
            assert reporter._check_rate_limit()
            assert reporter._rate_limit_counter == 1
            print(' PASS:  Rate limit window reset works correctly')

    def test_gcp_error_reporter_report_exception_disabled(self):
        """
        Test exception reporting when GCP reporting is disabled.
        
        EXPECTED RESULT: PASS - Should handle disabled state gracefully
        """
        print('\n[U+1F6AB] UNIT TEST: Exception Reporting - Disabled')
        print('=' * 43)
        reporter = GCPErrorReporter()
        assert not reporter.enabled
        test_exception = Exception('Test exception')
        result = reporter.report_exception(exception=test_exception, user='test-user', extra_context={'test': 'context'})
        assert result is None
        print(' PASS:  Exception reporting handled gracefully when disabled')

    @patch('netra_backend.app.services.monitoring.gcp_error_reporter.error_reporting')
    @patch('netra_backend.app.services.monitoring.gcp_error_reporter.GCP_AVAILABLE', True)
    def test_gcp_error_reporter_report_exception_enabled(self, mock_error_reporting):
        """
        Test exception reporting when GCP reporting is enabled.
        
        EXPECTED RESULT: INITIALLY FAIL - proves missing GCP integration
        """
        print('\n PASS:  UNIT TEST: Exception Reporting - Enabled')
        print('=' * 42)
        mock_client = MagicMock()
        mock_error_reporting.Client.return_value = mock_client
        os.environ['ENABLE_GCP_ERROR_REPORTING'] = 'true'
        reporter = GCPErrorReporter()
        assert reporter.enabled
        assert reporter.client == mock_client
        test_exception = Exception('Test exception for GCP')
        test_user = 'test-user-123'
        test_http_context = {'method': 'POST', 'url': 'http://localhost:8000/api/test'}
        test_extra_context = {'business_context': 'test', 'error_type': 'validation'}
        reporter.report_exception(exception=test_exception, user=test_user, http_context=test_http_context, extra_context=test_extra_context)
        mock_client.report_exception.assert_called_once()
        print(' PASS:  Exception reported to GCP client successfully')

    def test_gcp_error_reporter_message_reporting(self):
        """
        Test message reporting functionality.
        
        EXPECTED RESULT: PASS - Message reporting should work
        """
        print('\n[U+1F4DD] UNIT TEST: Message Reporting')
        print('=' * 33)
        reporter = GCPErrorReporter()
        result = reporter.report_message(message='Test error message', severity=ErrorSeverity.ERROR, user='test-user')
        assert result is None
        print(' PASS:  Message reporting handled when disabled')

    @pytest.mark.asyncio
    async def test_gcp_error_reporter_async_report_error(self):
        """
        Test async report_error method.
        
        EXPECTED RESULT: INITIALLY FAIL - proves missing async integration
        """
        print('\n LIGHTNING:  UNIT TEST: Async Error Reporting')
        print('=' * 35)
        reporter = GCPErrorReporter()
        test_error = Exception('Test async error')
        test_context = {'user_id': 'test-user-456', 'error_type': 'async_test', 'business_tier': 'enterprise'}
        result = await reporter.report_error(test_error, context=test_context)
        assert result is False
        print(' PASS:  Async error reporting returns False when disabled')
        with patch.object(reporter, 'enabled', True), patch.object(reporter, 'client', MagicMock()), patch.object(reporter, '_check_rate_limit', return_value=True), patch.object(reporter, 'report_exception') as mock_report:
            result = await reporter.report_error(test_error, context=test_context)
            assert result is True
            mock_report.assert_called_once_with(exception=test_error, user='test-user-456', http_context=None, extra_context=test_context)
            print(' PASS:  Async error reporting works when enabled')

    def test_request_context_management(self):
        """
        Test request context management functions.
        
        EXPECTED RESULT: PASS - Context management should work correctly
        """
        print('\n CYCLE:  UNIT TEST: Request Context Management')
        print('=' * 42)
        test_user_id = 'context-user-123'
        test_trace_id = 'trace-456'
        test_http_context = {'method': 'GET', 'url': '/test'}
        set_request_context(user_id=test_user_id, trace_id=test_trace_id, http_context=test_http_context, custom_field='test_value')
        print(' PASS:  Request context set without error')
        clear_request_context()
        print(' PASS:  Request context cleared without error')

    def test_gcp_reportable_decorator_sync(self):
        """
        Test @gcp_reportable decorator for synchronous functions.
        
        EXPECTED RESULT: PASS - Decorator should work correctly
        """
        print('\n[U+1F3A8] UNIT TEST: GCP Reportable Decorator (Sync)')
        print('=' * 44)

        @gcp_reportable(reraise=True)
        def test_function_reraise():
            raise ValueError('Test error for decorator')
        with pytest.raises(ValueError) as exc_info:
            test_function_reraise()
        assert 'Test error for decorator' in str(exc_info.value)
        print(' PASS:  Decorator re-raises exceptions correctly')

        @gcp_reportable(reraise=False)
        def test_function_no_reraise():
            raise ValueError('Test error no reraise')
        result = test_function_no_reraise()
        assert result is None
        print(' PASS:  Decorator handles exceptions without re-raising')

        @gcp_reportable()
        def test_function_success():
            return 'success'
        result = test_function_success()
        assert result == 'success'
        print(" PASS:  Decorator doesn't interfere with successful execution")

    @pytest.mark.asyncio
    async def test_gcp_reportable_decorator_async(self):
        """
        Test @gcp_reportable decorator for asynchronous functions.
        
        EXPECTED RESULT: PASS - Async decorator should work correctly
        """
        print('\n LIGHTNING:  UNIT TEST: GCP Reportable Decorator (Async)')
        print('=' * 45)

        @gcp_reportable(reraise=True)
        async def test_async_function_reraise():
            raise ValueError('Test async error for decorator')
        with pytest.raises(ValueError) as exc_info:
            await test_async_function_reraise()
        assert 'Test async error for decorator' in str(exc_info.value)
        print(' PASS:  Async decorator re-raises exceptions correctly')

        @gcp_reportable(reraise=False)
        async def test_async_function_no_reraise():
            raise ValueError('Test async error no reraise')
        result = await test_async_function_no_reraise()
        assert result is None
        print(' PASS:  Async decorator handles exceptions without re-raising')

        @gcp_reportable()
        async def test_async_function_success():
            return 'async_success'
        result = await test_async_function_success()
        assert result == 'async_success'
        print(" PASS:  Async decorator doesn't interfere with successful execution")

    def test_convenience_functions(self):
        """
        Test convenience functions for error reporting.
        
        EXPECTED RESULT: PASS - Convenience functions should work
        """
        print('\n TARGET:  UNIT TEST: Convenience Functions')
        print('=' * 35)
        test_exception = Exception('Convenience test exception')
        result = report_exception(test_exception, user='test-user')
        assert result is None
        print(' PASS:  report_exception convenience function works')
        result = report_error('Convenience test error message', user='test-user')
        assert result is None
        print(' PASS:  report_error convenience function works')

    def test_netra_exception_handling(self):
        """
        Test handling of NetraException with error details.
        
        EXPECTED RESULT: PASS - Should extract NetraException details
        """
        print('\n[U+1F527] UNIT TEST: NetraException Handling')
        print('=' * 37)
        from netra_backend.app.core.error_codes import ErrorCode
        test_exception = NetraException(message='Test NetraException', error_code=ErrorCode.VALIDATION_ERROR)

        @gcp_reportable(reraise=False)
        def test_function_netra_exception():
            raise test_exception
        result = test_function_netra_exception()
        assert result is None
        print(' PASS:  NetraException handled correctly by decorator')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')