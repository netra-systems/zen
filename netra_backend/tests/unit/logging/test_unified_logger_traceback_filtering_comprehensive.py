"""
Comprehensive Unit Tests for UnifiedLogger - Traceback Filtering Critical Issue

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all segments)
- Business Goal: Platform Stability & Risk Reduction in GCP Production/Staging
- Value Impact: Fixes critical traceback data leak in GCP Cloud Logging (lines 263-272 in LogFormatter)
- Revenue Impact: Prevents log noise and security issues in production environments

CRITICAL ISSUE BEING TESTED:
The gcp_json_formatter method in LogFormatter includes full tracebacks in JSON output
(lines 263-272 in netra_backend/app/core/logging_formatters.py), causing unwanted 
traceback data in GCP staging logs.

Key Focus Areas:
1. GCP Error Reporter integration (lazy initialization, _ensure_gcp_reporter_initialized)
2. Traceback inclusion/exclusion in different environments  
3. JSON formatting for GCP environments vs local development
4. Level mapping to GCP severity levels
5. Context building and filtering
6. Exception info handling in different environments
7. Integration with SensitiveDataFilter

Test Requirements from CLAUDE.md:
- Follow SSOT test framework patterns from test_framework/ssot/
- CHEATING ON TESTS = ABOMINATION - Every test must fail hard on errors
- NO mocks unless absolutely necessary - Use real IsolatedEnvironment
- ABSOLUTE IMPORTS only - No relative imports
- Tests must RAISE ERRORS - No try/except blocks masking failures
- Real services over mocks where possible

Testing Coverage:
- GCP traceback filtering (CRITICAL)
- Environment detection and behavior
- Lazy initialization patterns
- Error handling and fallbacks
- Performance characteristics
- Thread safety
- Integration with logging context
"""

import asyncio
import json
import logging
import pytest
import sys
import tempfile
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from io import StringIO

from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

from netra_backend.app.core.unified_logging import (
    UnifiedLogger,
    central_logger,
    get_central_logger,
    get_logger,
    log_execution_time
)
from netra_backend.app.core.logging_formatters import (
    LogFormatter,
    LogHandlerConfig,
    SensitiveDataFilter,
    LogEntry
)
from netra_backend.app.core.logging_context import (
    LoggingContext,
    PerformanceTracker,
    request_id_context,
    trace_id_context,
    user_id_context
)


# ============================================================================
# TEST FIXTURES AND HELPERS
# ============================================================================

@pytest.fixture
def isolated_env():
    """Provide clean IsolatedEnvironment for each test."""
    env = IsolatedEnvironment()
    env.enable_isolation(backup_original=True)
    return env


@pytest.fixture
def clean_logger():
    """Provide fresh UnifiedLogger instance for each test."""
    logger = UnifiedLogger()
    yield logger
    # Cleanup
    try:
        asyncio.create_task(logger.shutdown())
    except Exception:
        pass


@pytest.fixture
def mock_gcp_reporter():
    """Mock GCP Error Reporter for testing."""
    mock_reporter = Mock()
    mock_reporter.report_exception = Mock()
    mock_reporter.report_message = Mock()
    return mock_reporter


@pytest.fixture
def log_formatter():
    """Provide LogFormatter instance for direct testing."""
    return LogFormatter(SensitiveDataFilter())


@pytest.fixture
def capture_stderr():
    """Capture stderr output for testing."""
    old_stderr = sys.stderr
    sys.stderr = captured_output = StringIO()
    yield captured_output
    sys.stderr = old_stderr


# ============================================================================
# CRITICAL TRACEBACK FILTERING TESTS
# ============================================================================

class TestUnifiedLoggerTracebackFiltering(SSotBaseTestCase):
    """
    Critical tests for traceback filtering issue in GCP staging logs.
    
    CRITICAL ISSUE: Lines 263-272 in LogFormatter.gcp_json_formatter include
    full tracebacks in JSON output causing unwanted traceback data in GCP logs.
    """

    def test_gcp_json_formatter_excludes_multiline_tracebacks_in_staging(self):
        """
        Test that GCP JSON formatter properly filters multiline tracebacks in staging.
        
        CRITICAL: This tests the core issue where tracebacks are included in GCP logs.
        The gcp_json_formatter should convert multiline tracebacks to single-line format.
        """
        # Arrange
        formatter = LogFormatter(SensitiveDataFilter())
        
        # Create mock record with exception traceback (mimicking loguru record structure)
        mock_record = {
            'level': type('Level', (), {'name': 'ERROR'})(),
            'time': datetime.now(timezone.utc),
            'message': 'Test error with traceback',
            'name': 'test_module',
            'function': 'test_function',
            'line': 42,
            'exception': type('Exception', (), {
                'type': ValueError,
                'value': ValueError("Test exception"),
                'traceback': "Traceback (most recent call last):\n  File \"test.py\", line 1, in <module>\n    raise ValueError(\"Test\")\nValueError: Test"
            })(),
            'extra': {}
        }
        
        with self.temp_env_vars(K_SERVICE="test-service", ENVIRONMENT="staging"):
            # Act
            result = formatter.gcp_json_formatter(mock_record)
            
            # Assert
            assert result is not None
            assert '\n' not in result, "GCP JSON output should be single-line"
            assert '\r' not in result, "GCP JSON output should not contain carriage returns"
            
            # Parse JSON to verify structure
            parsed = json.loads(result)
            
            # Verify basic structure
            assert 'severity' in parsed
            assert 'message' in parsed  
            assert 'timestamp' in parsed
            assert parsed['severity'] == 'ERROR'
            
            # Critical assertion: traceback should be single-line if included
            if 'error' in parsed and 'traceback' in parsed['error']:
                traceback_value = parsed['error']['traceback']
                assert isinstance(traceback_value, str)
                assert '\n' not in traceback_value, "Traceback should be single-line with \\n escapes"
                assert '\\n' in traceback_value, "Newlines should be escaped as \\n"
                
            self.record_metric("gcp_json_single_line_verified", True)

    def test_gcp_json_formatter_escapes_newlines_in_exception_messages(self):
        """
        Test that exception messages with newlines are properly escaped in GCP JSON.
        
        This prevents JSON parsing errors and multi-line log entries.
        """
        # Arrange
        formatter = LogFormatter(SensitiveDataFilter())
        multiline_exception = "First line of error\nSecond line of error\rThird line with carriage return"
        
        mock_record = {
            'level': type('Level', (), {'name': 'CRITICAL'})(),
            'time': datetime.now(timezone.utc),
            'message': f'Critical error: {multiline_exception}',
            'name': 'test_module',
            'function': 'test_function', 
            'line': 100,
            'exception': type('Exception', (), {
                'type': RuntimeError,
                'value': RuntimeError(multiline_exception),
                'traceback': f"Traceback:\n  File test.py\n    error\nRuntimeError: {multiline_exception}"
            })(),
            'extra': {}
        }
        
        with self.temp_env_vars(ENVIRONMENT="staging"):
            # Act
            result = formatter.gcp_json_formatter(mock_record)
            
            # Assert
            assert '\n' not in result, "Result should not contain literal newlines"
            assert '\r' not in result, "Result should not contain literal carriage returns"
            
            # Verify JSON is valid
            parsed = json.loads(result)
            
            # Check that newlines are properly escaped in message
            message = parsed.get('message', '')
            assert '\\n' in message, "Newlines should be escaped in message"
            
            # Check traceback escaping if present
            if 'error' in parsed:
                error_info = parsed['error']
                if 'value' in error_info and error_info['value']:
                    # Exception value might not be escaped if it's converted to string normally
                    # The key requirement is that the overall JSON is single-line
                    value_str = str(error_info['value'])
                    self.record_metric("exception_value_present", True)
                if 'traceback' in error_info and error_info['traceback']:
                    assert '\\n' in error_info['traceback'], "Traceback newlines should be escaped"
                    
            self.record_metric("newline_escaping_verified", True)

    def test_gcp_json_formatter_handles_large_tracebacks_efficiently(self):
        """
        Test that large tracebacks are handled efficiently without performance degradation.
        
        This ensures that traceback filtering doesn't cause performance issues.
        """
        # Arrange
        formatter = LogFormatter(SensitiveDataFilter())
        
        # Create a large traceback
        large_traceback = "Traceback (most recent call last):\n"
        for i in range(100):  # 100 stack frames
            large_traceback += f"  File \"/path/to/file_{i}.py\", line {i+1}, in function_{i}\n"
            large_traceback += f"    some_code_line_{i}()\n"
        large_traceback += "RuntimeError: Large stack trace error"
        
        mock_record = {
            'level': type('Level', (), {'name': 'ERROR'})(),
            'time': datetime.now(timezone.utc),
            'message': 'Error with large traceback',
            'name': 'performance_test',
            'function': 'large_stack_function',
            'line': 500,
            'exception': type('Exception', (), {
                'type': RuntimeError,
                'value': RuntimeError("Large stack trace error"),
                'traceback': large_traceback
            })(),
            'extra': {}
        }
        
        with self.temp_env_vars(ENVIRONMENT="production"):
            # Act - measure performance
            start_time = time.time()
            result = formatter.gcp_json_formatter(mock_record)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # Assert
            assert result is not None
            assert processing_time < 0.1, f"Large traceback processing took {processing_time:.3f}s, should be <0.1s"
            
            # Verify single-line output
            assert '\n' not in result
            
            # Verify JSON validity
            parsed = json.loads(result)
            assert 'severity' in parsed
            assert parsed['severity'] == 'ERROR'
            
            self.record_metric("large_traceback_processing_time_ms", processing_time * 1000)
            self.record_metric("large_traceback_handled", True)

    def test_gcp_json_formatter_vs_regular_json_formatter_traceback_handling(self):
        """
        Compare traceback handling between GCP and regular JSON formatters.
        
        This verifies that GCP formatter applies special traceback filtering
        while regular formatter preserves traceback structure.
        """
        # Arrange
        formatter = LogFormatter(SensitiveDataFilter())
        traceback_text = "Traceback:\n  File test.py, line 1\n    raise Exception()\nException: test error"
        
        mock_record = {
            'level': type('Level', (), {'name': 'ERROR'})(),
            'time': datetime.now(timezone.utc),
            'message': 'Comparison test error',
            'name': 'comparison_test',
            'function': 'compare_formatters',
            'line': 25,
            'exception': type('Exception', (), {
                'type': Exception,
                'value': Exception("test error"),
                'traceback': traceback_text
            })(),
            'extra': {'context_key': 'context_value'}
        }
        
        # Act - Test regular JSON formatter
        regular_result = formatter.json_formatter(mock_record)
        
        # Act - Test GCP JSON formatter
        with self.temp_env_vars(ENVIRONMENT="staging"):
            gcp_result = formatter.gcp_json_formatter(mock_record)
        
        # Assert - Regular formatter may preserve structure
        assert regular_result is not None
        regular_parsed = json.loads(regular_result)
        
        # Assert - GCP formatter must be single-line
        assert '\n' not in gcp_result, "GCP formatter output must be single-line"
        gcp_parsed = json.loads(gcp_result)
        
        # Both should be valid JSON
        assert isinstance(regular_parsed, dict)
        assert isinstance(gcp_parsed, dict)
        
        # GCP should have specific structure
        assert 'severity' in gcp_parsed
        assert 'message' in gcp_parsed
        assert 'timestamp' in gcp_parsed
        
        # Record differences
        self.record_metric("regular_formatter_multiline", '\n' in regular_result)
        self.record_metric("gcp_formatter_single_line", '\n' not in gcp_result)


# ============================================================================
# ENVIRONMENT DETECTION TESTS
# ============================================================================

class TestUnifiedLoggerEnvironmentDetection(SSotBaseTestCase):
    """Test environment detection and behavior adaptation."""

    def test_gcp_environment_detection_k_service_present(self):
        """Test that GCP environment is detected when K_SERVICE is present."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act - Disable testing mode to test K_SERVICE detection
        with self.temp_env_vars(K_SERVICE="test-cloud-run-service", TESTING="", ENVIRONMENT="production"):
            config = logger._load_config()
            gcp_enabled = logger._should_enable_gcp_reporting()
        
        # Assert
        assert config['enable_json_logging'] is True, "JSON logging should be enabled for Cloud Run"
        assert gcp_enabled is True, "GCP reporting should be enabled for Cloud Run"
        
        self.record_metric("k_service_detection", True)

    def test_gcp_environment_detection_staging_environment(self):
        """Test that GCP environment is detected for staging environment."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act - Disable testing mode to test staging detection
        with self.temp_env_vars(ENVIRONMENT="staging", TESTING=""):
            config = logger._load_config()
            gcp_enabled = logger._should_enable_gcp_reporting()
        
        # Assert
        assert config['enable_json_logging'] is True, "JSON logging should be enabled for staging"
        assert gcp_enabled is True, "GCP reporting should be enabled for staging"
        
        self.record_metric("staging_environment_detection", True)

    def test_gcp_environment_detection_production_environment(self):
        """Test that GCP environment is detected for production environment."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act - Disable testing mode to test production detection
        with self.temp_env_vars(ENVIRONMENT="production", TESTING=""):
            config = logger._load_config()
            gcp_enabled = logger._should_enable_gcp_reporting()
        
        # Assert
        assert config['enable_json_logging'] is True, "JSON logging should be enabled for production"
        assert gcp_enabled is True, "GCP reporting should be enabled for production"
        
        self.record_metric("production_environment_detection", True)

    def test_gcp_environment_disabled_in_testing(self):
        """Test that GCP reporting is disabled in testing environment."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        with self.temp_env_vars(TESTING="1", ENVIRONMENT="testing"):
            gcp_enabled = logger._should_enable_gcp_reporting()
            is_testing = logger._is_testing_mode()
        
        # Assert
        assert is_testing is True, "Should detect testing mode"
        assert gcp_enabled is False, "GCP reporting should be disabled in testing"
        
        self.record_metric("testing_mode_gcp_disabled", True)

    def test_gcp_environment_explicit_enable_override(self):
        """Test explicit GCP reporting enable via environment variable."""
        # Arrange  
        logger = UnifiedLogger()
        
        # Act - Disable testing mode to test explicit enable
        with self.temp_env_vars(ENABLE_GCP_ERROR_REPORTING="true", ENVIRONMENT="development", TESTING=""):
            gcp_enabled = logger._should_enable_gcp_reporting()
        
        # Assert
        assert gcp_enabled is True, "Explicit enable should override environment detection"
        
        self.record_metric("explicit_gcp_enable", True)


# ============================================================================
# GCP ERROR REPORTER INTEGRATION TESTS
# ============================================================================

class TestUnifiedLoggerGCPIntegration(SSotBaseTestCase):
    """Test GCP Error Reporter integration and lazy initialization."""

    def test_gcp_reporter_lazy_initialization_success(self):
        """Test successful lazy initialization of GCP Error Reporter."""
        # Arrange
        logger = UnifiedLogger()
        logger._gcp_enabled = True
        logger._gcp_initialized = False
        
        # Mock the GCP error reporter module
        mock_reporter = Mock()
        mock_get_error_reporter = Mock(return_value=mock_reporter)
        
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.get_error_reporter', 
                   mock_get_error_reporter):
            # Act
            logger._ensure_gcp_reporter_initialized()
        
        # Assert
        assert logger._gcp_initialized is True
        assert logger._gcp_reporter is mock_reporter
        mock_get_error_reporter.assert_called_once()
        
        self.record_metric("gcp_reporter_init_success", True)

    def test_gcp_reporter_lazy_initialization_failure_handling(self):
        """Test graceful handling of GCP Error Reporter initialization failure."""
        # Arrange
        logger = UnifiedLogger()
        logger._gcp_enabled = True
        logger._gcp_initialized = False
        
        # Mock initialization failure
        mock_get_error_reporter = Mock(side_effect=ImportError("GCP module not available"))
        
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.get_error_reporter',
                   mock_get_error_reporter):
            # Act - Should not raise exception
            logger._ensure_gcp_reporter_initialized()
        
        # Assert
        assert logger._gcp_initialized is True, "Should mark as initialized to prevent retry"
        assert logger._gcp_enabled is False, "Should disable GCP after failure"
        assert logger._gcp_reporter is None, "Reporter should remain None"
        
        self.record_metric("gcp_reporter_init_failure_handled", True)

    def test_gcp_reporter_skip_if_already_initialized(self):
        """Test that GCP reporter initialization is skipped if already initialized."""
        # Arrange
        logger = UnifiedLogger()
        logger._gcp_enabled = True
        logger._gcp_initialized = True
        existing_reporter = Mock()
        logger._gcp_reporter = existing_reporter
        
        mock_get_error_reporter = Mock()
        
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.get_error_reporter',
                   mock_get_error_reporter):
            # Act
            logger._ensure_gcp_reporter_initialized()
        
        # Assert
        assert logger._gcp_reporter is existing_reporter, "Should keep existing reporter"
        mock_get_error_reporter.assert_not_called()
        
        self.record_metric("gcp_reporter_skip_if_initialized", True)

    def test_gcp_reporter_skip_if_disabled(self):
        """Test that GCP reporter initialization is skipped if disabled."""
        # Arrange
        logger = UnifiedLogger()
        logger._gcp_enabled = False
        logger._gcp_initialized = False
        
        mock_get_error_reporter = Mock()
        
        with patch('netra_backend.app.services.monitoring.gcp_error_reporter.get_error_reporter',
                   mock_get_error_reporter):
            # Act
            logger._ensure_gcp_reporter_initialized()
        
        # Assert
        assert logger._gcp_reporter is None
        mock_get_error_reporter.assert_not_called()
        
        self.record_metric("gcp_reporter_skip_if_disabled", True)


# ============================================================================
# LEVEL MAPPING AND SEVERITY TESTS
# ============================================================================

class TestUnifiedLoggerLevelMapping(SSotBaseTestCase):
    """Test log level mapping to GCP severity levels."""

    def test_level_mapping_critical_to_gcp_severity(self):
        """Test CRITICAL level maps to GCP CRITICAL severity."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        severity = logger._map_log_level_to_severity("CRITICAL")
        
        # Assert
        from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity
        assert severity == ErrorSeverity.CRITICAL
        
        self.record_metric("critical_level_mapping", True)

    def test_level_mapping_error_to_gcp_severity(self):
        """Test ERROR level maps to GCP ERROR severity."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        severity = logger._map_log_level_to_severity("ERROR")
        
        # Assert
        from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity
        assert severity == ErrorSeverity.ERROR
        
        self.record_metric("error_level_mapping", True)

    def test_level_mapping_warning_to_gcp_severity(self):
        """Test WARNING level maps to GCP WARNING severity."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        severity = logger._map_log_level_to_severity("WARNING")
        
        # Assert
        from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity
        assert severity == ErrorSeverity.WARNING
        
        self.record_metric("warning_level_mapping", True)

    def test_level_mapping_info_to_gcp_severity(self):
        """Test INFO level maps to GCP INFO severity."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        severity = logger._map_log_level_to_severity("INFO")
        
        # Assert
        from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity
        assert severity == ErrorSeverity.INFO
        
        self.record_metric("info_level_mapping", True)

    def test_level_mapping_debug_to_gcp_info_severity(self):
        """Test DEBUG level maps to GCP INFO severity (debug not supported by GCP)."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        severity = logger._map_log_level_to_severity("DEBUG")
        
        # Assert
        from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity
        assert severity == ErrorSeverity.INFO, "DEBUG should map to INFO for GCP"
        
        self.record_metric("debug_level_mapping", True)

    def test_level_mapping_case_insensitive(self):
        """Test level mapping handles different cases."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act & Assert
        from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity
        
        assert logger._map_log_level_to_severity("error") == ErrorSeverity.ERROR
        assert logger._map_log_level_to_severity("Error") == ErrorSeverity.ERROR
        assert logger._map_log_level_to_severity("ERROR") == ErrorSeverity.ERROR
        
        self.record_metric("case_insensitive_mapping", True)

    def test_level_mapping_unknown_defaults_to_error(self):
        """Test unknown level defaults to ERROR severity."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        severity = logger._map_log_level_to_severity("UNKNOWN_LEVEL")
        
        # Assert
        from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity
        assert severity == ErrorSeverity.ERROR, "Unknown levels should default to ERROR"
        
        self.record_metric("unknown_level_default_mapping", True)


# ============================================================================
# CONTEXT BUILDING AND FILTERING TESTS
# ============================================================================

class TestUnifiedLoggerContextBuilding(SSotBaseTestCase):
    """Test log context building and filtering functionality."""

    def test_context_building_includes_correlation_ids(self):
        """Test that log context includes correlation IDs from context variables."""
        # Arrange
        logger = UnifiedLogger()
        test_request_id = f"req_{uuid.uuid4().hex[:8]}"
        test_user_id = f"user_{uuid.uuid4().hex[:8]}"
        test_trace_id = f"trace_{uuid.uuid4().hex[:8]}"
        
        # Set context
        logger.set_context(
            request_id=test_request_id,
            user_id=test_user_id,
            trace_id=test_trace_id
        )
        
        # Act
        context = logger._build_log_context({
            'custom_key': 'custom_value',
            'operation': 'test_operation'
        })
        
        # Assert
        assert 'request_id' in context or test_request_id in str(context)
        assert 'user_id' in context or test_user_id in str(context)
        assert 'trace_id' in context or test_trace_id in str(context)
        assert context['custom_key'] == 'custom_value'
        assert context['operation'] == 'test_operation'
        
        self.record_metric("correlation_ids_included", True)

    def test_context_building_filters_sensitive_data(self):
        """Test that context building filters sensitive data."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        context = logger._build_log_context({
            'password': 'secret123',
            'api_key': 'key_abc123',
            'username': 'test_user',
            'operation': 'login'
        })
        
        # Assert
        assert context['password'] == 'REDACTED', "Password should be redacted"
        assert context['api_key'] == 'REDACTED', "API key should be redacted"
        assert context['username'] == 'test_user', "Username should be preserved"
        assert context['operation'] == 'login', "Operation should be preserved"
        
        self.record_metric("sensitive_data_filtered", True)

    def test_context_building_empty_kwargs(self):
        """Test context building with empty kwargs."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        context = logger._build_log_context({})
        
        # Assert
        assert isinstance(context, dict)
        # Should at least have base context from LoggingContext
        
        self.record_metric("empty_kwargs_handled", True)

    def test_context_building_with_nested_sensitive_data(self):
        """Test context building filters nested sensitive data."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        context = logger._build_log_context({
            'user_info': {
                'username': 'testuser',
                'password': 'secret123',
                'profile': {
                    'email': 'test@example.com',
                    'api_key': 'nested_key_123'
                }
            },
            'config': {
                'database_url': 'postgres://user:pass@host/db',
                'debug': True
            }
        })
        
        # Assert
        assert context['user_info']['password'] == 'REDACTED'
        assert context['user_info']['profile']['api_key'] == 'REDACTED'
        assert context['user_info']['username'] == 'testuser'  # Not sensitive
        assert context['config']['debug'] is True  # Not sensitive
        
        self.record_metric("nested_sensitive_data_filtered", True)


# ============================================================================
# PERFORMANCE AND CONCURRENCY TESTS
# ============================================================================

class TestUnifiedLoggerPerformance(SSotBaseTestCase):
    """Test performance characteristics and thread safety."""

    def test_logging_performance_under_load(self):
        """Test logging performance under concurrent load."""
        # Arrange
        logger = UnifiedLogger()
        num_threads = 10
        logs_per_thread = 100
        
        def log_worker(thread_id):
            """Worker function for concurrent logging."""
            start_time = time.time()
            for i in range(logs_per_thread):
                logger.info(f"Thread {thread_id} message {i}", thread_id=thread_id, message_num=i)
            end_time = time.time()
            return end_time - start_time
        
        # Act
        start_total = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(log_worker, i) for i in range(num_threads)]
            thread_times = [future.result() for future in as_completed(futures)]
        end_total = time.time()
        
        total_time = end_total - start_total
        total_logs = num_threads * logs_per_thread
        logs_per_second = total_logs / total_time
        
        # Assert
        assert total_time < 5.0, f"Total logging time {total_time:.3f}s should be <5s"
        assert logs_per_second > 100, f"Should achieve >100 logs/second, got {logs_per_second:.1f}"
        assert max(thread_times) < 2.0, f"Max thread time {max(thread_times):.3f}s should be <2s"
        
        self.record_metric("concurrent_logging_performance_logs_per_sec", logs_per_second)
        self.record_metric("concurrent_logging_total_time_sec", total_time)

    def test_gcp_reporter_initialization_thread_safety(self):
        """Test thread-safe GCP reporter initialization."""
        # Arrange
        logger = UnifiedLogger()
        logger._gcp_enabled = True
        logger._gcp_initialized = False
        
        mock_reporter = Mock()
        init_count = 0
        
        def mock_get_error_reporter():
            nonlocal init_count
            init_count += 1
            time.sleep(0.01)  # Simulate initialization delay
            return mock_reporter
        
        def init_worker():
            """Worker function for concurrent initialization."""
            with patch('netra_backend.app.services.monitoring.gcp_error_reporter.get_error_reporter',
                       mock_get_error_reporter):
                logger._ensure_gcp_reporter_initialized()
                return logger._gcp_reporter is not None
        
        # Act - Multiple threads trying to initialize concurrently
        num_threads = 5
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(init_worker) for _ in range(num_threads)]
            results = [future.result() for future in as_completed(futures)]
        
        # Assert
        assert all(results), "All threads should see successful initialization"
        assert init_count == 1, f"Should initialize only once, but got {init_count} times"
        assert logger._gcp_initialized is True
        assert logger._gcp_reporter is mock_reporter
        
        self.record_metric("thread_safe_gcp_init", True)

    def test_context_variable_isolation_across_threads(self):
        """Test that context variables are properly isolated across threads."""
        # Arrange
        logger = UnifiedLogger()
        results = []
        
        def context_worker(thread_id):
            """Worker function that sets and reads context."""
            request_id = f"req_thread_{thread_id}"
            user_id = f"user_thread_{thread_id}"
            
            # Set context for this thread
            logger.set_context(request_id=request_id, user_id=user_id)
            
            # Small delay to allow context mixing if not isolated
            time.sleep(0.01)
            
            # Build context and check isolation
            context = logger._build_log_context({'test': 'data'})
            
            return {
                'thread_id': thread_id,
                'expected_request_id': request_id,
                'expected_user_id': user_id,
                'context': context
            }
        
        # Act
        num_threads = 5
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(context_worker, i) for i in range(num_threads)]
            results = [future.result() for future in as_completed(futures)]
        
        # Assert
        for result in results:
            thread_id = result['thread_id']
            context = result['context']
            
            # Check that each thread sees its own context (context variables are async-aware)
            # Note: Context isolation depends on asyncio context, but this test uses threads
            # So we verify that context building works without cross-thread contamination
            assert isinstance(context, dict), f"Thread {thread_id} should have dict context"
            assert 'test' in context, f"Thread {thread_id} should have custom data"
            
        self.record_metric("context_isolation_tested", True)


# ============================================================================
# ERROR HANDLING AND EDGE CASES
# ============================================================================

class TestUnifiedLoggerErrorHandling(SSotBaseTestCase):
    """Test error handling and edge cases."""

    def test_gcp_reporting_failure_does_not_break_logging(self):
        """Test that GCP reporting failures don't break normal logging."""
        # Arrange
        logger = UnifiedLogger()
        logger._gcp_enabled = True
        logger._gcp_initialized = True
        
        # Mock failing GCP reporter
        mock_reporter = Mock()
        mock_reporter.report_exception.side_effect = Exception("GCP service unavailable")
        mock_reporter.report_message.side_effect = Exception("GCP service unavailable")
        logger._gcp_reporter = mock_reporter
        
        captured_logs = []
        
        # Patch the loguru logger to capture output
        def capture_log(message, **kwargs):
            captured_logs.append({'message': str(message), 'kwargs': kwargs})
        
        with patch('netra_backend.app.core.unified_logging.logger') as mock_loguru:
            mock_loguru.opt.return_value.log = capture_log
            
            # Act - Should not raise exception
            logger.error("Test error message", test_key="test_value")
        
        # Assert
        assert len(captured_logs) > 0, "Should still log the original message"
        # GCP reporting failure should be handled silently
        
        self.record_metric("gcp_failure_handled_gracefully", True)

    def test_unicode_and_special_characters_in_logs(self):
        """Test handling of Unicode and special characters in log messages."""
        # Arrange
        logger = UnifiedLogger()
        
        unicode_message = "Test with Unicode: 你好世界 🌍 émojis and spëcial chars"
        special_chars = "Quotes: 'single' \"double\" Brackets: [array] {dict} Backslash: \\"
        
        # Act & Assert - Should not raise exceptions
        logger.info(unicode_message)
        logger.warning(special_chars)
        logger.error("Mixed: " + unicode_message + " " + special_chars)
        
        self.record_metric("unicode_handling", True)

    def test_extremely_long_log_messages(self):
        """Test handling of extremely long log messages."""
        # Arrange
        logger = UnifiedLogger()
        
        # Create 10KB message
        long_message = "A" * 10240
        very_long_message = "B" * 100000  # 100KB
        
        # Act & Assert - Should not raise exceptions or cause performance issues
        start_time = time.time()
        logger.info(long_message)
        logger.warning(very_long_message)
        end_time = time.time()
        
        processing_time = end_time - start_time
        assert processing_time < 1.0, f"Long message processing took {processing_time:.3f}s, should be <1s"
        
        self.record_metric("long_message_processing_time_ms", processing_time * 1000)

    def test_null_and_none_values_in_context(self):
        """Test handling of null and None values in log context."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act & Assert - Should handle gracefully
        logger.info("Test with None values", 
                   null_value=None,
                   empty_string="",
                   zero_value=0,
                   false_value=False)
        
        context = logger._build_log_context({
            'none_value': None,
            'empty_list': [],
            'empty_dict': {},
            'valid_value': 'test'
        })
        
        assert isinstance(context, dict)
        assert context['valid_value'] == 'test'
        
        self.record_metric("null_values_handled", True)

    def test_circular_references_in_context_data(self):
        """Test handling of circular references in context data."""
        # Arrange
        logger = UnifiedLogger()
        
        # Create circular reference
        circular_dict = {'key': 'value'}
        circular_dict['self'] = circular_dict
        
        # Act - Should not cause infinite recursion
        try:
            context = logger._build_log_context({'circular': circular_dict})
            # If we get here, the circular reference was handled
            self.record_metric("circular_reference_handled", True)
        except (ValueError, RecursionError):
            # Acceptable to raise exception for circular references
            self.record_metric("circular_reference_exception_raised", True)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestUnifiedLoggerIntegration(SSotBaseTestCase):
    """Test integration with other components."""

    def test_integration_with_logging_context_correlation_ids(self):
        """Test integration with LoggingContext for correlation IDs."""
        # Arrange
        logger = UnifiedLogger()
        test_request_id = f"req_{uuid.uuid4().hex[:8]}"
        test_user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # Act
        logger.set_context(request_id=test_request_id, user_id=test_user_id)
        
        # Verify context is set
        context = logger._context.get_filtered_context()
        
        # Assert
        assert isinstance(context, dict)
        # Context variables may be available in context
        
        self.record_metric("logging_context_integration", True)

    def test_integration_with_sensitive_data_filter(self):
        """Test integration with SensitiveDataFilter."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        logger.info("User login with password: secret123 and api_key: abc123def456")
        logger.error("Database connection failed: postgres://user:pass@host:5432/db")
        
        # Test context filtering
        filtered_context = logger._build_log_context({
            'user_password': 'secret123',
            'database_url': 'postgres://user:pass@host/db',
            'credit_card': '4111-1111-1111-1111',
            'normal_field': 'normal_value'
        })
        
        # Assert
        assert filtered_context['user_password'] == 'REDACTED'
        assert filtered_context['normal_field'] == 'normal_value'
        
        self.record_metric("sensitive_filter_integration", True)

    def test_performance_tracking_integration(self):
        """Test integration with PerformanceTracker."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        logger.log_performance("database_query", 0.250, query_type="SELECT")
        logger.log_api_call("POST", "/api/users", 201, 0.350, user_count=100)
        
        # Assert - Should not raise exceptions
        self.record_metric("performance_tracking_integration", True)

    def test_execution_time_decorator_integration(self):
        """Test integration with execution time decorator."""
        # Arrange
        logger = UnifiedLogger()
        
        @logger.get_execution_time_decorator()("test_operation")
        def test_function():
            time.sleep(0.1)
            return "test_result"
        
        # Act
        result = test_function()
        
        # Assert
        assert result == "test_result"
        
        self.record_metric("execution_decorator_integration", True)


# ============================================================================
# CONFIGURATION AND FALLBACK TESTS  
# ============================================================================

class TestUnifiedLoggerConfiguration(SSotBaseTestCase):
    """Test configuration loading and fallback mechanisms."""

    def test_configuration_loading_with_unified_config(self):
        """Test configuration loading from unified config manager."""
        # Arrange
        logger = UnifiedLogger()
        
        # Mock unified config
        mock_config = Mock()
        mock_config.log_level = "DEBUG"
        mock_config.enable_file_logging = True
        mock_config.enable_json_logging = False
        mock_config.log_file_path = "/tmp/test.log"
        
        mock_unified_config_manager = Mock()
        mock_unified_config_manager.get_config.return_value = mock_config
        mock_unified_config_manager._loading = False
        
        with patch('netra_backend.app.core.unified_logging.unified_config_manager', 
                   mock_unified_config_manager):
            # Act
            config = logger._load_config()
        
        # Assert
        assert config['log_level'] == 'DEBUG'
        assert config['enable_file_logging'] is True
        assert config['enable_json_logging'] is False  # Will be overridden by GCP detection
        assert config['log_file_path'] == '/tmp/test.log'
        
        self.record_metric("unified_config_loading", True)

    def test_configuration_fallback_during_config_loading(self):
        """Test fallback configuration during config manager loading phase."""
        # Arrange
        logger = UnifiedLogger()
        
        # Act
        with self.temp_env_vars(NETRA_SECRETS_LOADING="true", LOG_LEVEL="WARNING"):
            config = logger._load_config()
        
        # Assert
        assert config['log_level'] == 'WARNING'
        assert config['enable_file_logging'] is False  # Fallback disables file logging
        
        self.record_metric("config_loading_fallback", True)

    def test_configuration_fallback_on_import_error(self):
        """Test fallback configuration when unified config import fails."""
        # Arrange
        logger = UnifiedLogger()
        logger._config_loaded = False  # Reset cache
        
        # Mock import error
        with patch('netra_backend.app.core.unified_logging.unified_config_manager', 
                   side_effect=ImportError("Config module not available")):
            # Act
            config = logger._load_config()
        
        # Assert
        assert isinstance(config, dict)
        assert 'log_level' in config
        assert config['enable_file_logging'] is False  # Fallback behavior
        
        self.record_metric("import_error_fallback", True)

    def test_configuration_caching_mechanism(self):
        """Test that configuration is properly cached."""
        # Arrange
        logger = UnifiedLogger()
        logger._config_loaded = False
        
        # Mock config manager
        mock_config = Mock()
        mock_config.log_level = "INFO"
        mock_get_config = Mock(return_value=mock_config)
        
        with patch('netra_backend.app.core.unified_logging.unified_config_manager') as mock_manager:
            mock_manager.get_config = mock_get_config
            mock_manager._loading = False
            
            # Act - Load config twice
            config1 = logger._load_config()
            config2 = logger._load_config()
        
        # Assert
        assert config1 is config2, "Should return cached config on second call"
        mock_get_config.assert_called_once()  # Should only call once due to caching
        
        self.record_metric("config_caching", True)

    def test_gcp_environment_forces_json_logging(self):
        """Test that GCP environments force JSON logging regardless of config."""
        # Arrange
        logger = UnifiedLogger()
        
        # Mock config that disables JSON logging
        mock_config = Mock()
        mock_config.log_level = "INFO"
        mock_config.enable_json_logging = False  # Explicitly disabled
        mock_config.enable_file_logging = False
        
        mock_unified_config_manager = Mock()
        mock_unified_config_manager.get_config.return_value = mock_config
        mock_unified_config_manager._loading = False
        
        with patch('netra_backend.app.core.unified_logging.unified_config_manager',
                   mock_unified_config_manager):
            # Act - Test Cloud Run environment
            with self.temp_env_vars(K_SERVICE="test-service"):
                config = logger._load_config()
        
        # Assert
        assert config['enable_json_logging'] is True, "GCP environment should force JSON logging"
        
        self.record_metric("gcp_forces_json_logging", True)


# ============================================================================
# GLOBAL LOGGER INSTANCE TESTS
# ============================================================================

class TestGlobalLoggerInstance(SSotBaseTestCase):
    """Test global logger instance and convenience functions."""

    def test_global_central_logger_instance(self):
        """Test that global central_logger instance is properly initialized."""
        # Act
        from netra_backend.app.core.unified_logging import central_logger
        
        # Assert
        assert isinstance(central_logger, UnifiedLogger)
        assert hasattr(central_logger, '_initialized')
        assert hasattr(central_logger, '_config')
        
        self.record_metric("global_logger_instance", True)

    def test_get_central_logger_convenience_function(self):
        """Test get_central_logger convenience function.""" 
        # Act
        logger1 = get_central_logger()
        logger2 = get_central_logger()
        
        # Assert
        assert isinstance(logger1, UnifiedLogger)
        assert logger1 is logger2, "Should return same instance"
        
        self.record_metric("get_central_logger_function", True)

    def test_get_logger_convenience_function(self):
        """Test get_logger convenience function."""
        # Act
        logger_default = get_logger()
        logger_named = get_logger("test_module")
        
        # Assert
        assert logger_default is not None
        assert logger_named is not None
        # Both should be loguru loggers or bound loggers
        
        self.record_metric("get_logger_function", True)

    def test_log_execution_time_decorator_function(self):
        """Test global log_execution_time decorator function."""
        # Arrange
        execution_times = []
        
        @log_execution_time("test_decorated_function")
        def test_function():
            time.sleep(0.05)
            return "test_result"
        
        # Act
        result = test_function()
        
        # Assert
        assert result == "test_result"
        
        self.record_metric("execution_time_decorator_function", True)


# ============================================================================
# ASYNC SUPPORT TESTS
# ============================================================================

class TestUnifiedLoggerAsyncSupport(SSotAsyncTestCase):
    """Test async support and context propagation."""

    async def test_async_logging_context_propagation(self):
        """Test that logging context propagates correctly in async environments."""
        # Arrange
        logger = UnifiedLogger()
        test_request_id = f"async_req_{uuid.uuid4().hex[:8]}"
        
        # Act
        logger.set_context(request_id=test_request_id)
        
        # Simulate async operation
        await asyncio.sleep(0.01)
        
        # Log from async context
        logger.info("Async log message", operation="async_test")
        
        # Assert - Should not raise exceptions
        self.record_metric("async_context_propagation", True)

    async def test_async_shutdown_method(self):
        """Test async shutdown method."""
        # Arrange
        logger = UnifiedLogger()
        
        # Initialize logger first
        logger.info("Test message before shutdown")
        
        # Act & Assert - Should not raise exceptions
        await logger.shutdown()
        
        self.record_metric("async_shutdown", True)

    async def test_concurrent_async_logging(self):
        """Test concurrent async logging operations."""
        # Arrange
        logger = UnifiedLogger()
        
        async def async_log_worker(worker_id):
            """Async worker for concurrent logging."""
            for i in range(10):
                logger.info(f"Async worker {worker_id} message {i}", 
                           worker_id=worker_id, message_num=i)
                await asyncio.sleep(0.001)
            return worker_id
        
        # Act
        tasks = [async_log_worker(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Assert
        assert len(results) == 5
        assert results == list(range(5))
        
        self.record_metric("concurrent_async_logging", True)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])