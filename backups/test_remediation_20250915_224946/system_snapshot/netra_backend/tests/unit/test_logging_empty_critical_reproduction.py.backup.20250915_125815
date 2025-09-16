
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Unit Tests for Reproducing Empty CRITICAL Log Entries Issue #253

This test suite reproduces the specific conditions that cause empty CRITICAL log entries
in GCP Cloud Logging by targeting the problematic areas in unified_logging_ssot.py
lines 449-470 (JSON formatter) and context management.

Test Plan Focus:
1. Loguru timestamp KeyError edge cases (Issue #252 connection)
2. Exception serialization failures in JSON formatter
3. Record field access patterns causing empty logs
4. Context corruption during rapid user switches
5. Burst logging scenarios (21+ logs in 2 seconds)

Expected Behavior: These tests will FAIL initially, demonstrating the empty log issue.
After implementing fixes, these tests should PASS.

SSOT Compliance: Inherits from SSotBaseTestCase, uses IsolatedEnvironment.
Business Value: Platform/Internal - System Stability & Observability

Created: 2025-09-10 (Issue #253 Reproduction Test Plan Implementation)
"""

import asyncio
import json
import logging
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
from loguru import logger

# SSOT Test Infrastructure  
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment

# System Under Test
from shared.logging.unified_logging_ssot import (
    UnifiedLoggingSSOT,
    UnifiedLoggingContext, 
    SensitiveDataFilter,
    request_id_context,
    user_id_context, 
    trace_id_context
)


class TestLoggingEmptyCriticalReproduction(SSotBaseTestCase):
    """
    Test suite reproducing empty CRITICAL log entries issue #253.
    
    These tests target the JSON formatter and context management vulnerabilities
    that cause empty log entries in GCP Cloud Logging.
    """
    
    def setup_method(self, method):
        """Setup test environment with clean logging state."""
        super().setup_method(method)
        self.logger = UnifiedLoggingSSOT()
        self.context = UnifiedLoggingContext()
        
        # Track generated log entries for analysis
        self.captured_logs: List[Dict[str, Any]] = []
        self.json_format_errors: List[Exception] = []
        
        # Mock the JSON formatter to capture problematic entries
        self.original_json_formatter = None
        
    def teardown_method(self, method):
        """Clean up logging state."""
        # Clear context variables
        request_id_context.set(None)
        user_id_context.set(None)
        trace_id_context.set(None)
        
        # Reset logger state
        if hasattr(self.logger, '_context'):
            self.logger._context.clear_context()
        
        super().teardown_method(method)
    
    @contextmanager
    def _setup_log_capture(self):
        """Setup log capture to detect empty entries."""
        def capturing_json_formatter(record):
            """Wrapped JSON formatter that captures problematic entries."""
            try:
                # Call the real formatter
                json_formatter = self.logger._get_json_formatter()
                result = json_formatter(record)
                
                # Parse and analyze the result
                try:
                    parsed = json.loads(result)
                    self.captured_logs.append(parsed)
                    
                    # Check for empty critical issues
                    if (parsed.get('severity') == 'CRITICAL' and
                        (not parsed.get('message') or parsed.get('message').strip() == '')):
                        raise ValueError(f"Empty CRITICAL log detected: {parsed}")
                        
                except json.JSONDecodeError as e:
                    self.json_format_errors.append(e)
                    # This would cause empty logs in production
                    return ""
                    
                return result
                
            except Exception as e:
                self.json_format_errors.append(e)
                # Simulate production behavior - return empty on error
                return ""
        
        # Patch the logger's formatter
        with patch.object(self.logger, '_get_json_formatter', return_value=capturing_json_formatter):
            yield
    
    def test_loguru_timestamp_keyerror_edge_case(self):
        """
        Test Case 1: Reproduce Loguru timestamp KeyError causing empty logs.
        
        This test reproduces the timestamp formatting issue from Issue #252
        that causes KeyErrors in the JSON formatter, resulting in empty log entries.
        """
        with self._setup_log_capture():
            # Create a malformed record that triggers timestamp issues
            with patch('shared.logging.unified_logging_ssot.datetime') as mock_datetime:
                # Simulate datetime.utcnow() returning None or invalid data
                mock_datetime.utcnow.return_value = None
                
                try:
                    # This should trigger timestamp KeyError and empty log
                    self.logger.critical("Critical system failure", extra={
                        'component': 'websocket_manager',
                        'error_code': 'TIMESTAMP_FAILURE'
                    })
                    
                    # Expect: Empty log due to timestamp KeyError
                    assert len(self.json_format_errors) > 0, "Expected timestamp formatting error"
                    assert any("timestamp" in str(error).lower() for error in self.json_format_errors), \
                        "Expected timestamp-related error"
                        
                except Exception as e:
                    # This test should FAIL initially - demonstrating the bug
                    pytest.fail(f"Timestamp KeyError reproduced: {e}")
    
    def test_exception_serialization_failure(self):
        """
        Test Case 2: Exception serialization failures in JSON formatter.
        
        Tests lines 465-470 in unified_logging_ssot.py where complex exception
        objects fail to serialize properly, causing empty log entries.
        """
        with self._setup_log_capture():
            # Create an exception with non-serializable data
            class ProblematicException(Exception):
                def __init__(self, message):
                    super().__init__(message)
                    # Add non-serializable attributes that break JSON formatter
                    self.complex_data = {
                        'websocket_connection': MagicMock(),  # Non-serializable
                        'circular_ref': None
                    }
                    self.complex_data['circular_ref'] = self.complex_data  # Circular reference
            
            try:
                raise ProblematicException("WebSocket connection failed")
            except ProblematicException as e:
                # This should trigger exception serialization failure
                with patch('shared.logging.unified_logging_ssot.logger') as mock_loguru:
                    # Make loguru record include the problematic exception
                    mock_record = {
                        'level': Mock(name='CRITICAL'),
                        'message': 'Critical WebSocket failure',
                        'name': 'websocket_test', 
                        'exception': Mock(
                            type=type(e),
                            value=e,
                            traceback=e.__traceback__
                        ),
                        'extra': {'user_id': 'test_user'}
                    }
                    
                    # Call JSON formatter directly - should fail
                    json_formatter = self.logger._get_json_formatter()
                    
                    try:
                        result = json_formatter(mock_record)
                        # This test should FAIL initially - empty result indicates bug
                        assert result != "", "Expected non-empty log result, got empty (reproduces bug)"
                        
                    except Exception as format_error:
                        # This reproduces the bug - exception serialization failure
                        pytest.fail(f"Exception serialization failure reproduced: {format_error}")
    
    def test_record_field_access_patterns_causing_empty_logs(self):
        """
        Test Case 3: Record field access patterns that cause empty logs.
        
        Tests scenarios where accessing record['field'] throws KeyError
        or returns None, causing the JSON formatter to fail silently.
        """
        with self._setup_log_capture():
            # Create incomplete/malformed record
            incomplete_record = {
                'level': Mock(name='CRITICAL'),
                'message': 'System failure',
                # Missing required fields that cause KeyError
                # 'name' field missing
                # 'exception' field missing
            }
            
            json_formatter = self.logger._get_json_formatter()
            
            try:
                result = json_formatter(incomplete_record)
                
                # This test should FAIL initially - demonstrating missing field handling
                assert result != "", "Expected non-empty result, got empty (reproduces missing field bug)"
                
                # Verify required fields are handled gracefully
                parsed = json.loads(result)
                assert 'timestamp' in parsed, "Missing timestamp field"
                assert 'severity' in parsed, "Missing severity field"
                assert 'message' in parsed, "Missing message field"
                
            except KeyError as e:
                # This reproduces the bug - unhandled KeyError for missing fields
                pytest.fail(f"Record field access KeyError reproduced: {e}")
            except Exception as e:
                pytest.fail(f"Unexpected error accessing record fields: {e}")
    
    def test_context_corruption_during_rapid_user_switches(self):
        """
        Test Case 4: Context corruption during rapid user switches.
        
        Tests concurrent context variable updates that can cause corrupted
        logging context, resulting in empty or malformed log entries.
        """
        with self._setup_log_capture():
            # Simulate rapid user context switches
            users = [f"user_{i}" for i in range(10)]
            
            async def rapid_context_switching():
                """Simulate rapid user context changes."""
                for user_id in users:
                    # Rapid context updates
                    user_id_context.set(user_id)
                    request_id_context.set(f"req_{user_id}")
                    trace_id_context.set(f"trace_{user_id}")
                    
                    # Log with context (should not be empty)
                    self.logger.critical(f"Critical event for {user_id}", extra={
                        'user_id': user_id,
                        'event_type': 'rapid_switch_test'
                    })
                    
                    # Rapid switch without proper cleanup
                    await asyncio.sleep(0.001)  # Very short delay
            
            # Run the rapid switching
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(rapid_context_switching())
            finally:
                loop.close()
            
            # Analyze captured logs for corruption
            critical_logs = [log for log in self.captured_logs if log.get('severity') == 'CRITICAL']
            
            # This test should FAIL initially - demonstrating context corruption
            for log_entry in critical_logs:
                assert log_entry.get('message'), f"Empty message in log: {log_entry}"
                assert log_entry.get('user_id'), f"Missing user_id in log: {log_entry}"
            
            # Check for mixed context corruption
            user_ids_in_logs = [log.get('user_id') for log in critical_logs]
            assert len(set(user_ids_in_logs)) == len(users), \
                f"Context corruption detected: expected {len(users)} unique users, got {len(set(user_ids_in_logs))}"
    
    def test_burst_logging_timestamp_collision(self):
        """
        Test Case 5: Burst logging causing timestamp collisions and empty logs.
        
        Tests the specific pattern from Issue #253: 21+ logs in 2 seconds
        causing timestamp formatting issues and empty CRITICAL entries.
        """
        with self._setup_log_capture():
            start_time = time.time()
            burst_count = 25  # More than the observed 21 logs
            
            # Simulate the exact burst pattern observed in production
            for i in range(burst_count):
                self.logger.critical(f"Burst log {i}: WebSocket connection retry", extra={
                    'component': 'websocket_manager',
                    'retry_count': i,
                    'burst_test': True,
                    'timestamp_manual': datetime.utcnow().isoformat()
                })
                
                # Small delay to create rapid burst within 2 seconds
                time.sleep(0.08)  # 25 logs in ~2 seconds
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify we achieved the burst pattern
            assert duration <= 2.5, f"Burst took too long: {duration}s"
            assert len(self.captured_logs) >= burst_count, \
                f"Expected {burst_count} logs, got {len(self.captured_logs)}"
            
            # Analyze for empty entries (the bug we're reproducing)
            critical_logs = [log for log in self.captured_logs if log.get('severity') == 'CRITICAL']
            empty_logs = [log for log in critical_logs if not log.get('message') or log.get('message').strip() == '']
            
            # This test should FAIL initially - demonstrating burst logging issues
            assert len(empty_logs) == 0, \
                f"Found {len(empty_logs)} empty CRITICAL logs during burst (reproduces Issue #253)"
            
            # Check for timestamp collisions
            timestamps = [log.get('timestamp') for log in critical_logs]
            unique_timestamps = set(timestamps)
            
            assert len(unique_timestamps) == len(timestamps), \
                f"Timestamp collision detected: {len(timestamps)} logs, {len(unique_timestamps)} unique timestamps"
    
    def test_gcp_json_formatter_stress_conditions(self):
        """
        Test Case 6: GCP JSON formatter under stress conditions.
        
        Tests the specific JSON formatter used in GCP environments under
        stress conditions that cause empty log generation.
        """
        with self._setup_log_capture():
            # Simulate GCP Cloud Run conditions
            with patch.dict(self._env.get_all_vars(), {
                'ENVIRONMENT': 'staging',
                'GCP_PROJECT': 'netra-staging',
                'SERVICE_NAME': 'netra-backend'
            }):
                
                # Test various problematic record scenarios
                test_scenarios = [
                    {
                        'name': 'missing_level',
                        'record': {'message': 'Test', 'name': 'test'},
                        'expected_error': 'level'
                    },
                    {
                        'name': 'invalid_exception_format',
                        'record': {
                            'level': Mock(name='CRITICAL'),
                            'message': 'Test',
                            'name': 'test',
                            'exception': "invalid_string_instead_of_exception_object"
                        },
                        'expected_error': 'exception'
                    },
                    {
                        'name': 'circular_reference_in_extra',
                        'record': {
                            'level': Mock(name='CRITICAL'),
                            'message': 'Test',
                            'name': 'test',
                            'exception': None,
                            'extra': {}
                        },
                        'expected_error': 'circular'
                    }
                ]
                
                # Make the circular reference
                test_scenarios[2]['record']['extra']['self'] = test_scenarios[2]['record']['extra']
                
                json_formatter = self.logger._get_json_formatter()
                
                for scenario in test_scenarios:
                    with pytest.raises((Exception, ValueError, TypeError, KeyError)) as exc_info:
                        result = json_formatter(scenario['record'])
                        
                        # This should FAIL initially - demonstrating formatter brittleness
                        assert result != "", f"Empty result for scenario {scenario['name']} (reproduces bug)"
                    
                    # Verify we caught the expected type of error
                    error_message = str(exc_info.value).lower()
                    assert scenario['expected_error'] in error_message, \
                        f"Expected {scenario['expected_error']} error in {error_message}"

    def test_production_websocket_failure_reproduction(self):
        """
        Test Case 7: Reproduce exact production WebSocket failure scenario.
        
        This test reproduces the exact scenario that causes empty CRITICAL logs
        in production WebSocket connection failures.
        """
        with self._setup_log_capture():
            # Set up production-like context
            user_id_context.set('prod_user_123')
            request_id_context.set('req_websocket_conn_456')
            trace_id_context.set('trace_ws_failure_789')
            
            # Simulate the exact WebSocket failure that produces empty logs
            try:
                # This mimics the WebSocket connection failure from production
                websocket_mock = Mock()
                websocket_mock.send.side_effect = ConnectionError("Connection lost")
                
                # Try to send critical failure notification
                self.logger.critical(
                    "WebSocket connection critical failure during agent execution",
                    extra={
                        'component': 'websocket_manager',
                        'user_id': 'prod_user_123',
                        'connection_state': 'failed',
                        'retry_attempts': 3,
                        'error_details': {
                            'connection': websocket_mock,  # Non-serializable object
                            'timestamp': datetime.utcnow(),
                            'stack_trace': traceback.format_stack()
                        }
                    }
                )
                
                # Verify the log was not empty
                critical_logs = [log for log in self.captured_logs if log.get('severity') == 'CRITICAL']
                assert len(critical_logs) > 0, "No CRITICAL logs captured"
                
                latest_critical = critical_logs[-1]
                
                # This test should FAIL initially - demonstrating the production issue
                assert latest_critical.get('message'), \
                    f"Empty CRITICAL message in production scenario: {latest_critical}"
                assert latest_critical.get('message').strip() != '', \
                    f"Blank CRITICAL message in production scenario: {latest_critical}"
                
            except Exception as e:
                # This reproduces the production bug
                pytest.fail(f"Production WebSocket failure scenario reproduced error: {e}")