"""
Comprehensive Unit Test Suite for LogFormatter GCP JSON Traceback Issue

CRITICAL FOCUS: GCP JSON Formatting Traceback Issue Prevention
=====================================

This test suite specifically addresses the critical issue where the `gcp_json_formatter` method 
(lines 147-276 in logging_formatters.py) includes full traceback data in JSON output, causing 
unwanted traceback information to appear in GCP staging logs.

The PRIMARY ISSUE is in lines 263-272 where traceback is included in GCP JSON:
```python
if hasattr(exc, 'traceback') and exc.traceback:
    # Replace newlines with 
 to keep JSON on single line
    traceback_str = str(exc.traceback).replace('
', '\\n').replace('\r', '\\r')

gcp_entry['error'] = {
    'type': exc.type.__name__ if hasattr(exc, 'type') and exc.type else None,
    'value': str(exc.value) if hasattr(exc, 'value') and exc.value else None,
    'traceback': traceback_str  # <-- THIS IS THE PROBLEM
}
```

Business Value Justification (BVJ):
- Segment: Platform/Internal (Operations & Production Stability)
- Business Goal: Clean production logs for effective monitoring and cost control
- Value Impact: Prevents log noise that blocks rapid issue diagnosis and increases GCP costs
- Strategic Impact: Foundation for reliable production operations and customer success

TESTING STRATEGY:
1. Test GCP JSON formatter traceback handling specifically
2. Test edge cases that cause formatter errors
3. Test performance with large tracebacks
4. Test proper JSON structure maintenance
5. Test regression prevention for the specific GCP staging issue

COMPLIANCE:
- Follows SSOT test framework patterns from test_framework/ssot/
- Uses SSotBaseTestCase for consistent environment isolation
- Integrates with IsolatedEnvironment (no direct os.environ access)
- Tests real LogFormatter behavior (minimal mocking)
- Focuses on business-critical functionality
"""
import json
import sys
import traceback
import uuid
from datetime import datetime, timezone
from io import StringIO
from types import TracebackType
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock, patch
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.logging_formatters import LogFormatter, SensitiveDataFilter, LogEntry, LogHandlerConfig
from netra_backend.app.core.logging_context import request_id_context, trace_id_context, user_id_context

class TestLogFormatterGcpTracebackComprehensive(SSotBaseTestCase):
    """
    Comprehensive test suite for LogFormatter GCP JSON formatting traceback issue.
    
    CRITICAL FOCUS: Prevent traceback information from appearing in GCP staging logs
    while maintaining proper error handling and JSON structure.
    """

    def setup_method(self, method=None):
        """Setup for each test with clean environment isolation."""
        super().setup_method(method)
        self.filter_instance = SensitiveDataFilter()
        self.formatter = LogFormatter(self.filter_instance)
        self.set_env_var('ENVIRONMENT', 'staging')
        self.set_env_var('K_SERVICE', 'netra-backend')
        self.set_env_var('GOOGLE_CLOUD_PROJECT', 'netra-staging')
        request_id_context.set(None)
        trace_id_context.set(None)
        user_id_context.set(None)
        self.test_request_id = f'req_{uuid.uuid4().hex[:8]}'
        self.test_trace_id = f'trace_{uuid.uuid4().hex[:8]}'
        self.test_user_id = f'user_{uuid.uuid4().hex[:8]}'
        self.record_metric('test_setup_completed', True)

    def _create_mock_loguru_record(self, level: str='INFO', message: str='Test message', name: str='test_module', function: str='test_function', line: int=42, exception: Optional[Any]=None, extra: Optional[Dict[str, Any]]=None) -> Dict[str, Any]:
        """
        Create a mock Loguru record structure for testing.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            name: Module name
            function: Function name
            line: Line number
            exception: Exception object (for error testing)
            extra: Extra context data
            
        Returns:
            Dict representing a Loguru record
        """
        level_obj = Mock()
        level_obj.name = level
        level_obj.no = {'DEBUG': 10, 'INFO': 20, 'SUCCESS': 25, 'WARNING': 30, 'ERROR': 40, 'CRITICAL': 50}.get(level, 20)
        time_obj = datetime.now(timezone.utc)
        record = {'level': level_obj, 'message': message, 'time': time_obj, 'name': name, 'function': function, 'line': line, 'exception': exception, 'extra': extra or {}}

        def get_method(key, default=None):
            return record.get(key, default) if hasattr(record, 'get') else record[key] if key in record else default
        record['get'] = get_method
        return record

    def _create_test_exception_with_traceback(self, message: str='Test exception') -> Any:
        """
        Create a test exception with a realistic traceback for testing.
        
        Args:
            message: Exception message
            
        Returns:
            Exception object with traceback information
        """
        try:

            def level_3():
                raise ValueError(message)

            def level_2():
                level_3()

            def level_1():
                level_2()
            level_1()
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            exception_obj = Mock()
            exception_obj.type = exc_type
            exception_obj.value = exc_value
            exception_obj.traceback = exc_traceback
            return exception_obj
        return None

    @pytest.mark.unit
    def test_gcp_json_formatter_excludes_traceback_from_output(self):
        """
        CRITICAL TEST: Ensure GCP JSON formatter does NOT include traceback in output.
        
        This is the primary test for the GCP staging traceback issue.
        The formatter should provide error information without including full tracebacks.
        """
        exception_obj = self._create_test_exception_with_traceback('Database connection failed')
        record = self._create_mock_loguru_record(level='ERROR', message='Database operation failed', exception=exception_obj, extra={'operation': 'user_authentication', 'retry_count': 3})
        json_output = self.formatter.gcp_json_formatter(record)
        try:
            gcp_data = json.loads(json_output)
        except json.JSONDecodeError as e:
            pytest.fail(f'GCP formatter produced invalid JSON: {e}')
        if 'error' in gcp_data:
            error_info = gcp_data['error']
            assert 'traceback' not in error_info or error_info.get('traceback') is None, 'CRITICAL ISSUE: Traceback found in GCP JSON output - this causes staging log noise'
        assert gcp_data.get('severity') == 'ERROR', 'Error severity not properly mapped'
        assert 'Database operation failed' in gcp_data.get('message', ''), 'Error message missing'
        assert '\n' not in json_output, 'GCP JSON output contains newlines'
        assert '\r' not in json_output, 'GCP JSON output contains carriage returns'
        self.record_metric('gcp_traceback_exclusion_test', 'PASSED')
        self.record_metric('critical_gcp_issue_prevented', True)

    @pytest.mark.unit
    def test_gcp_json_formatter_error_handling_without_traceback_pollution(self):
        """
        Test that error handling in GCP formatter doesn't leak traceback details.
        
        This tests the fallback error handling in lines 222-241 of gcp_json_formatter.
        """
        malformed_record = {'invalid': 'record structure'}
        json_output = self.formatter.gcp_json_formatter(malformed_record)
        try:
            gcp_data = json.loads(json_output)
        except json.JSONDecodeError as e:
            pytest.fail(f'GCP formatter fallback produced invalid JSON: {e}')
        assert gcp_data.get('severity') == 'ERROR', 'Fallback severity not set correctly'
        assert 'Logging formatter error' in gcp_data.get('message', ''), 'Fallback message missing'
        labels = gcp_data.get('labels', {})
        if 'traceback' in labels:
            traceback_str = labels['traceback']
            assert '\\n' in traceback_str or len(traceback_str.split('\n')) == 1, 'Traceback not properly escaped to single line'
        self.record_metric('gcp_fallback_error_handling_test', 'PASSED')

    @pytest.mark.unit
    def test_gcp_json_formatter_large_traceback_performance(self):
        """
        Test GCP formatter performance with large tracebacks.
        
        Ensures that large tracebacks don't cause performance issues or break JSON structure.
        """

        def create_deep_stack(depth):
            if depth <= 0:
                raise RuntimeError(f"Deep exception at depth 0 with large data: {'x' * 1000}")
            return create_deep_stack(depth - 1)
        try:
            create_deep_stack(20)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            exception_obj = Mock()
            exception_obj.type = exc_type
            exception_obj.value = exc_value
            exception_obj.traceback = exc_traceback
            record = self._create_mock_loguru_record(level='ERROR', message='Deep stack error occurred', exception=exception_obj)
            import time
            start_time = time.time()
            json_output = self.formatter.gcp_json_formatter(record)
            format_time = time.time() - start_time
            assert format_time < 1.0, f'GCP formatter too slow with large traceback: {format_time:.3f}s'
            try:
                gcp_data = json.loads(json_output)
            except json.JSONDecodeError as e:
                pytest.fail(f'Large traceback broke JSON structure: {e}')
            assert json_output.count('\n') <= 1, 'GCP output contains multiple lines'
            self.record_metric('large_traceback_format_time_ms', format_time * 1000)
            self.record_metric('large_traceback_performance_test', 'PASSED')

    @pytest.mark.unit
    def test_gcp_json_formatter_unicode_in_traceback_handling(self):
        """
        Test GCP formatter handling of Unicode characters in tracebacks.
        
        Ensures proper JSON encoding when tracebacks contain non-ASCII characters.
        """
        try:
            raise ValueError('Unicode error: caf[U+00E9] [U+00F1]o[U+00F1]o [U+4E2D][U+6587] [U+1F680]')
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            exception_obj = Mock()
            exception_obj.type = exc_type
            exception_obj.value = exc_value
            exception_obj.traceback = exc_traceback
            record = self._create_mock_loguru_record(level='ERROR', message='Unicode error occurred: caf[U+00E9] [U+00F1]o[U+00F1]o [U+4E2D][U+6587] [U+1F680]', exception=exception_obj)
            json_output = self.formatter.gcp_json_formatter(record)
            try:
                gcp_data = json.loads(json_output)
            except json.JSONDecodeError as e:
                pytest.fail(f'Unicode in traceback broke JSON parsing: {e}')
            message = gcp_data.get('message', '')
            assert 'caf[U+00E9]' in message or 'caf' in message, 'Unicode characters not handled properly'
            assert isinstance(json_output, str), 'JSON output should be string'
            self.record_metric('unicode_traceback_handling_test', 'PASSED')

    @pytest.mark.unit
    def test_gcp_json_formatter_vs_regular_json_formatter_traceback_difference(self):
        """
        Test that GCP formatter handles tracebacks differently from regular JSON formatter.
        
        This validates that the GCP-specific logic is working as intended.
        """
        exception_obj = self._create_test_exception_with_traceback('Comparison test exception')
        record = self._create_mock_loguru_record(level='ERROR', message='Formatter comparison test', exception=exception_obj)
        gcp_output = self.formatter.gcp_json_formatter(record)
        regular_output = self.formatter.json_formatter(record)
        try:
            gcp_data = json.loads(gcp_output)
            regular_data = json.loads(regular_output)
        except json.JSONDecodeError as e:
            pytest.fail(f'JSON parsing failed: {e}')
        assert 'severity' in gcp_data, 'GCP format should have severity field'
        assert 'level' in regular_data, 'Regular format should have level field'
        gcp_has_traceback = False
        if 'error' in gcp_data and gcp_data['error'].get('traceback'):
            gcp_has_traceback = True
        regular_has_traceback = False
        if 'error_details' in regular_data and regular_data['error_details'].get('traceback'):
            regular_has_traceback = True
        assert not gcp_has_traceback, 'GCP formatter should not include detailed traceback'
        self.record_metric('formatter_comparison_test', 'PASSED')
        self.record_metric('gcp_traceback_differentiation_verified', True)

    @pytest.mark.unit
    def test_gcp_json_formatter_required_fields_present(self):
        """
        Test that GCP JSON formatter includes all required GCP Cloud Logging fields.
        
        GCP expects specific fields: severity, message, timestamp, labels.
        """
        record = self._create_mock_loguru_record(level='WARNING', message='Resource usage approaching limit', extra={'cpu_usage': 85, 'memory_usage': 78})
        json_output = self.formatter.gcp_json_formatter(record)
        gcp_data = json.loads(json_output)
        required_fields = ['severity', 'message', 'timestamp']
        for field in required_fields:
            assert field in gcp_data, f"Required GCP field '{field}' missing"
        assert gcp_data['severity'] == 'WARNING', 'Severity not properly mapped'
        timestamp = gcp_data['timestamp']
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f'Invalid timestamp format: {timestamp}')
        assert 'labels' in gcp_data, 'Labels field missing'
        assert isinstance(gcp_data['labels'], dict), 'Labels should be dict'
        self.record_metric('gcp_required_fields_test', 'PASSED')

    @pytest.mark.unit
    def test_gcp_json_formatter_single_line_output_guarantee(self):
        """
        Test that GCP JSON formatter always produces single-line output.
        
        This is critical for GCP Cloud Logging ingestion.
        """
        test_cases = [self._create_mock_loguru_record(message='Multi-line\nmessage\rwith\r\ncarriage returns'), self._create_mock_loguru_record(level='ERROR', exception=self._create_test_exception_with_traceback('Multi\nline\nexception')), self._create_mock_loguru_record(extra={'nested': {'data': 'with\nnewlines'}, 'list': ['item1\n', 'item2\r', 'item3\r\n']})]
        for i, record in enumerate(test_cases):
            json_output = self.formatter.gcp_json_formatter(record)
            newline_count = json_output.count('\n')
            carriage_return_count = json_output.count('\r')
            assert newline_count <= 1, f'Test case {i}: Too many newlines in output: {newline_count}'
            assert carriage_return_count == 0, f'Test case {i}: Carriage returns found in output'
            try:
                json.loads(json_output.strip())
            except json.JSONDecodeError as e:
                pytest.fail(f'Test case {i}: Single-line escaping broke JSON: {e}')
        self.record_metric('single_line_output_guarantee_test', 'PASSED')

    @pytest.mark.unit
    def test_gcp_json_formatter_context_variable_integration(self):
        """
        Test that GCP formatter properly integrates with logging context variables.
        
        Tests request_id, trace_id, and user_id context propagation.
        """
        request_id_context.set(self.test_request_id)
        trace_id_context.set(self.test_trace_id)
        user_id_context.set(self.test_user_id)
        try:
            record = self._create_mock_loguru_record(message='Context integration test', extra={'business_operation': 'user_authentication'})
            json_output = self.formatter.gcp_json_formatter(record)
            gcp_data = json.loads(json_output)
            assert 'trace' in gcp_data, 'Trace ID not integrated'
            assert gcp_data['trace'] == self.test_trace_id, 'Trace ID value incorrect'
            labels = gcp_data.get('labels', {})
            assert 'request_id' in labels, 'Request ID not in labels'
            assert labels['request_id'] == self.test_request_id, 'Request ID value incorrect'
            assert 'user_id' in labels, 'User ID not in labels'
            assert labels['user_id'] == self.test_user_id, 'User ID value incorrect'
            self.record_metric('context_integration_test', 'PASSED')
        finally:
            request_id_context.set(None)
            trace_id_context.set(None)
            user_id_context.set(None)

    @pytest.mark.unit
    def test_gcp_json_formatter_none_record_handling(self):
        """Test GCP formatter handling of None or invalid record inputs."""
        test_cases = [None, {}, {'invalid': 'structure'}, {'level': None, 'message': None, 'time': None}]
        for i, record in enumerate(test_cases):
            json_output = self.formatter.gcp_json_formatter(record)
            try:
                gcp_data = json.loads(json_output)
            except json.JSONDecodeError as e:
                pytest.fail(f'Test case {i}: Invalid record produced invalid JSON: {e}')
            assert gcp_data.get('severity') == 'ERROR', f'Test case {i}: Invalid record should use ERROR severity'
            message = gcp_data.get('message', '')
            assert 'Logging formatter error' in message, f'Test case {i}: Fallback message missing'
        self.record_metric('none_record_handling_test', 'PASSED')

    @pytest.mark.unit
    def test_gcp_json_formatter_circular_reference_handling(self):
        """Test GCP formatter handling of circular references in extra data."""
        circular_data = {'key1': 'value1'}
        circular_data['self_ref'] = circular_data
        record = self._create_mock_loguru_record(message='Circular reference test', extra=circular_data)
        try:
            json_output = self.formatter.gcp_json_formatter(record)
            gcp_data = json.loads(json_output)
            assert gcp_data.get('message') is not None, 'Message should be preserved despite circular reference'
        except (RecursionError, ValueError) as e:
            pytest.fail(f'Circular reference caused unhandled error: {e}')
        self.record_metric('circular_reference_handling_test', 'PASSED')

    @pytest.mark.unit
    def test_gcp_json_formatter_memory_usage_with_large_data(self):
        """Test memory usage of GCP formatter with large data structures."""
        import psutil
        import os
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        large_data = {f'key_{i}': f'value_{i}' * 100 for i in range(1000)}
        record = self._create_mock_loguru_record(message='Large data test', extra=large_data)
        for _ in range(10):
            json_output = self.formatter.gcp_json_formatter(record)
            try:
                json.loads(json_output)
            except json.JSONDecodeError as e:
                pytest.fail(f'Large data broke JSON structure: {e}')
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        assert memory_increase < 50 * 1024 * 1024, f'Excessive memory usage: {memory_increase / 1024 / 1024:.2f}MB'
        self.record_metric('memory_usage_bytes', memory_increase)
        self.record_metric('large_data_memory_test', 'PASSED')

    @pytest.mark.unit
    def test_gcp_json_formatter_sensitive_data_filtering_integration(self):
        """Test that GCP formatter properly integrates with sensitive data filtering."""
        sensitive_record = self._create_mock_loguru_record(message='Authentication attempt with password: secret123', extra={'user_email': 'user@example.com', 'password': 'secret123', 'api_key': 'sk-1234567890abcdef', 'jwt_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload', 'safe_data': 'this should be preserved'})
        json_output = self.formatter.gcp_json_formatter(sensitive_record)
        gcp_data = json.loads(json_output)
        message = gcp_data.get('message', '')
        assert 'secret123' not in message, 'Password not filtered from message'
        assert 'REDACTED' in message or message != 'Authentication attempt with password: secret123', 'Sensitive data filtering not applied to message'
        context = gcp_data.get('context', {})
        if 'password' in context:
            assert context['password'] == 'REDACTED', 'Password not redacted in context'
        if 'api_key' in context:
            assert context['api_key'] == 'REDACTED', 'API key not redacted in context'
        assert context.get('safe_data') == 'this should be preserved', 'Safe data was incorrectly filtered'
        self.record_metric('sensitive_data_filtering_integration_test', 'PASSED')

    @pytest.mark.unit
    def test_gcp_json_formatter_performance_benchmark(self):
        """Benchmark GCP JSON formatter performance for regression testing."""
        import time
        record = self._create_mock_loguru_record(level='INFO', message='Performance benchmark test message', extra={'data': {'nested': {'structure': 'with multiple levels'}}})
        for _ in range(10):
            self.formatter.gcp_json_formatter(record)
        iterations = 1000
        start_time = time.time()
        for _ in range(iterations):
            json_output = self.formatter.gcp_json_formatter(record)
            assert '"severity":"INFO"' in json_output or '"severity": "INFO"' in json_output
        total_time = time.time() - start_time
        avg_time_ms = total_time / iterations * 1000
        assert total_time < 1.0, f'Performance regression: {total_time:.3f}s for {iterations} records'
        assert avg_time_ms < 1.0, f'Performance regression: {avg_time_ms:.3f}ms per record'
        self.record_metric('gcp_formatter_avg_time_ms', avg_time_ms)
        self.record_metric('gcp_formatter_total_time_s', total_time)
        self.record_metric('performance_benchmark_test', 'PASSED')

    @pytest.mark.unit
    def test_gcp_json_formatter_thread_safety(self):
        """Test that GCP formatter is thread-safe for concurrent usage."""
        import threading
        import queue
        results = queue.Queue()
        exceptions = queue.Queue()

        def format_record(thread_id):
            try:
                record = self._create_mock_loguru_record(message=f'Thread {thread_id} message', extra={'thread_id': thread_id})
                for i in range(10):
                    json_output = self.formatter.gcp_json_formatter(record)
                    gcp_data = json.loads(json_output)
                    results.put((thread_id, i, gcp_data))
            except Exception as e:
                exceptions.put((thread_id, e))
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=format_record, args=(thread_id,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        assert exceptions.empty(), f'Thread safety issues detected: {list(exceptions.queue)}'
        result_count = 0
        while not results.empty():
            thread_id, iteration, gcp_data = results.get()
            result_count += 1
            assert 'severity' in gcp_data, f'Thread {thread_id}, iteration {iteration}: Invalid result'
            assert f'Thread {thread_id} message' in gcp_data.get('message', ''), f'Thread {thread_id}, iteration {iteration}: Message corruption'
        assert result_count == 50, f'Expected 50 results, got {result_count}'
        self.record_metric('thread_safety_test', 'PASSED')
        self.record_metric('concurrent_format_operations', result_count)

    def teardown_method(self, method=None):
        """Cleanup after each test."""
        request_id_context.set(None)
        trace_id_context.set(None)
        user_id_context.set(None)
        self.record_metric('test_teardown_completed', True)
        super().teardown_method(method)

@pytest.fixture
def mock_gcp_environment():
    """Fixture to simulate GCP Cloud Run environment."""
    with patch.dict('os.environ', {'K_SERVICE': 'netra-backend', 'K_REVISION': 'netra-backend-00001-abc', 'K_CONFIGURATION': 'netra-backend', 'PORT': '8080', 'GOOGLE_CLOUD_PROJECT': 'netra-staging'}):
        yield

@pytest.fixture
def sample_complex_exception():
    """Fixture providing a complex exception with nested calls."""

    def create_exception():
        try:

            def inner_function():

                def deeper_function():
                    raise ConnectionError('Database connection timeout after 30 seconds')
                deeper_function()
            inner_function()
        except Exception:
            return sys.exc_info()
    return create_exception()

class TestLogFormatterGcpTracebackRegressionPrevention(SSotBaseTestCase):
    """
    Regression prevention tests to ensure the GCP traceback issue never reoccurs.
    
    These tests are designed to catch any future changes that might re-introduce
    the traceback pollution issue in GCP staging logs.
    """

    def setup_method(self, method=None):
        """Setup for regression tests."""
        super().setup_method(method)
        self.formatter = LogFormatter(SensitiveDataFilter())

    @pytest.mark.unit
    def test_regression_gcp_traceback_never_in_json_output(self):
        """
        REGRESSION TEST: Ensure traceback never appears in GCP JSON output.
        
        This test will fail if anyone re-introduces traceback inclusion in GCP logs.
        """
        distinctive_content = 'REGRESSION_TEST_TRACEBACK_MARKER_SHOULD_NOT_APPEAR_IN_GCP_LOGS'
        try:
            raise ValueError(f'Test exception with marker: {distinctive_content}')
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            exception_obj = Mock()
            exception_obj.type = exc_type
            exception_obj.value = exc_value
            exception_obj.traceback = exc_traceback
            record = {'level': Mock(name='ERROR'), 'message': 'Regression test error', 'time': datetime.now(timezone.utc), 'name': 'regression_test', 'function': 'test_function', 'line': 42, 'exception': exception_obj, 'extra': {}, 'get': lambda k, d=None: record.get(k, d) if k != 'get' else lambda x, y=None: record.get(x, y)}
            record['level'].name = 'ERROR'
            json_output = self.formatter.gcp_json_formatter(record)
            assert distinctive_content not in json_output, f'REGRESSION DETECTED: Traceback content found in GCP JSON output: {distinctive_content}'
            gcp_data = json.loads(json_output)
            if 'error' in gcp_data and isinstance(gcp_data['error'], dict):
                assert gcp_data['error'].get('traceback') is None, 'REGRESSION DETECTED: Traceback field found in GCP JSON error object'
            self.record_metric('regression_traceback_prevention_test', 'PASSED')
            self.record_metric('gcp_traceback_regression_prevented', True)

    @pytest.mark.unit
    def test_regression_gcp_json_structure_validation(self):
        """
        REGRESSION TEST: Validate GCP JSON structure remains consistent.
        
        Ensures future changes don't break the expected GCP Cloud Logging format.
        """
        record = {'level': Mock(name='WARNING'), 'message': 'Regression structure test', 'time': datetime.now(timezone.utc), 'name': 'test_module', 'function': 'test_func', 'line': 123, 'exception': None, 'extra': {'test': 'data'}, 'get': lambda k, d=None: record.get(k, d) if k != 'get' else lambda x, y=None: record.get(x, y)}
        record['level'].name = 'WARNING'
        json_output = self.formatter.gcp_json_formatter(record)
        gcp_data = json.loads(json_output)
        expected_structure = {'severity': str, 'message': str, 'timestamp': str, 'labels': dict}
        for field, expected_type in expected_structure.items():
            assert field in gcp_data, f"REGRESSION: Required GCP field '{field}' missing"
            assert isinstance(gcp_data[field], expected_type), f"REGRESSION: GCP field '{field}' has wrong type: {type(gcp_data[field])}"
        assert gcp_data['severity'] == 'WARNING', 'REGRESSION: Severity mapping changed'
        self.record_metric('regression_structure_validation_test', 'PASSED')

class TestLogFormatterGcpTracebackParametrized(SSotBaseTestCase):
    """Parametrized tests for comprehensive coverage of edge cases."""

    def setup_method(self, method=None):
        """Setup for parametrized tests."""
        super().setup_method(method)
        self.formatter = LogFormatter(SensitiveDataFilter())

    @pytest.mark.parametrize('level,expected_severity', [('TRACE', 'DEBUG'), ('DEBUG', 'DEBUG'), ('INFO', 'INFO'), ('SUCCESS', 'INFO'), ('WARNING', 'WARNING'), ('ERROR', 'ERROR'), ('CRITICAL', 'CRITICAL')])
    @pytest.mark.unit
    def test_gcp_severity_mapping_completeness(self, level, expected_severity):
        """Test all log level to GCP severity mappings."""
        level_obj = Mock()
        level_obj.name = level
        record = {'level': level_obj, 'message': f'Test message for {level}', 'time': datetime.now(timezone.utc), 'name': 'test', 'function': 'test_func', 'line': 1, 'exception': None, 'extra': {}, 'get': lambda k, d=None: record.get(k, d) if k != 'get' else lambda x, y=None: record.get(x, y)}
        json_output = self.formatter.gcp_json_formatter(record)
        gcp_data = json.loads(json_output)
        assert gcp_data['severity'] == expected_severity, f"Severity mapping incorrect for {level}: expected {expected_severity}, got {gcp_data['severity']}"

    @pytest.mark.parametrize('message_content', ['Simple message', 'Message with \'quotes\' and "double quotes"', 'Message with\nnewlines\rand\r\ncarriage returns', 'Message with unicode: caf[U+00E9] [U+00F1]o[U+00F1]o [U+4E2D][U+6587] [U+1F680]', "Message with JSON-like content: {'key': 'value', 'nested': {'data': true}}", 'Very long message: ' + 'x' * 1000, '', None])
    @pytest.mark.unit
    def test_gcp_message_content_handling(self, message_content):
        """Test GCP formatter with various message content types."""
        record = {'level': Mock(name='INFO'), 'message': message_content, 'time': datetime.now(timezone.utc), 'name': 'test', 'function': 'test_func', 'line': 1, 'exception': None, 'extra': {}, 'get': lambda k, d=None: record.get(k, d) if k != 'get' else lambda x, y=None: record.get(x, y)}
        record['level'].name = 'INFO'
        json_output = self.formatter.gcp_json_formatter(record)
        try:
            gcp_data = json.loads(json_output)
        except json.JSONDecodeError as e:
            pytest.fail(f"Message content '{message_content}' broke JSON structure: {e}")
        assert 'message' in gcp_data, 'Message field missing from GCP output'
        assert json_output.count('\n') <= 1, 'GCP output contains multiple lines'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')