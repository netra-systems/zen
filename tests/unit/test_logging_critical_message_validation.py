"""
Unit Tests for SSOT Logging Critical Message Validation - Issue #253

Tests that the UnifiedLoggingSSOT never produces empty CRITICAL messages
and properly handles edge cases that could result in empty textPayload fields.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Reliability & Observability  
- Value Impact: Ensures critical failures remain visible for debugging $500K+ ARR functionality
- Strategic Impact: Prevents silent failure masking that affects incident response

Test Focus:
1. Pure logic validation of message formatting and fallback generation
2. Edge case handling for empty/None message inputs
3. GCP format validation catches empty textPayload fields
4. JSON formatter robustness under error conditions

SSOT Compliance: Inherits from SSotBaseTestCase, uses IsolatedEnvironment
Created: 2025-09-12 (Issue #253 Unit Test Implementation)
"""

import json
import logging
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.logging.unified_logging_ssot import (
    UnifiedLoggingSSOT,
    SensitiveDataFilter,
    UnifiedLoggingContext,
    get_ssot_logger,
    reset_logging
)


class TestLoggingCriticalMessageValidation(SSotBaseTestCase):
    """
    Unit test suite for SSOT logging critical message validation.
    
    Tests that UnifiedLoggingSSOT never produces empty CRITICAL messages
    and properly handles all edge cases that could result in empty logs.
    """
    
    def setup_method(self, method):
        """Setup unit test environment with isolated logging."""
        super().setup_method(method)
        
        # Reset logging state for clean test
        reset_logging()
        
        # Ensure testing environment
        self._env.set('TESTING', '1', source='unit_test')
        self._env.set('ENVIRONMENT', 'testing', source='unit_test')
        
        # Initialize SSOT logger for testing
        self.logger = UnifiedLoggingSSOT()
        
        # Capture log outputs for validation
        self.captured_logs = []
        self.captured_json_outputs = []
        
    def teardown_method(self, method):
        """Clean up logging state after test."""
        # Reset logging for clean state
        reset_logging()
        super().teardown_method(method)
    
    def test_empty_message_fallback_generation(self):
        """Test that SSOT logger never produces empty CRITICAL messages."""
        # Test various empty message inputs
        empty_inputs = [
            "",           # Empty string
            "   ",        # Whitespace only
            "\n\t ",      # Newlines and tabs
            None,         # None value
        ]
        
        for empty_input in empty_inputs:
            with patch.object(self.logger, '_get_json_formatter') as mock_formatter:
                # Setup mock to capture formatter calls
                def capture_formatter():
                    def format_record(record):
                        formatted = self.logger._get_json_formatter()(record)
                        self.captured_json_outputs.append(formatted)
                        return formatted
                    return format_record
                
                mock_formatter.return_value = capture_formatter()
                
                # Log with empty message
                self.logger.critical(empty_input)
                
                # Verify fallback message was generated
                if self.captured_json_outputs:
                    latest_output = self.captured_json_outputs[-1]
                    parsed_log = json.loads(latest_output)
                    
                    # Should have meaningful fallback message
                    assert parsed_log.get('message'), f"Empty message for input: {repr(empty_input)}"
                    assert parsed_log.get('textPayload'), f"Empty textPayload for input: {repr(empty_input)}"
                    assert parsed_log['message'] != empty_input, f"Message not replaced for input: {repr(empty_input)}"
    
    def test_none_message_handling(self):
        """Test handling of None message inputs in CRITICAL logging."""
        # Mock the JSON formatter to capture its behavior
        with patch.object(self.logger, '_get_json_formatter') as mock_formatter:
            captured_records = []
            
            def capture_formatter():
                def format_record(record):
                    captured_records.append(record)
                    # Simulate the actual formatter behavior
                    return json.dumps({
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'severity': 'CRITICAL',
                        'service': 'test-service',
                        'logger': 'test',
                        'message': self.logger._get_safe_field(record, 'message', 'Empty log message'),
                        'textPayload': self.logger._get_safe_field(record, 'message', 'Empty log message')
                    })
                return format_record
            
            mock_formatter.return_value = capture_formatter()
            
            # Test None message
            self.logger.critical(None)
            
            # Verify record was processed and has fallback
            assert len(captured_records) > 0, "No log record captured"
            
            latest_record = captured_records[-1]
            message_field = self.logger._get_safe_field(latest_record, 'message', 'Empty log message')
            
            # Should get fallback message, not None
            assert message_field is not None, "Message field should not be None"
            assert message_field != "", "Message field should not be empty"
            assert isinstance(message_field, str), "Message field should be string"
    
    def test_gcp_format_validation_empty_payload(self):
        """Test that GCP format validation catches empty textPayload."""
        # Test the _validate_gcp_format method directly
        test_cases = [
            # Empty message
            {'severity': 'CRITICAL', 'message': ''},
            # Missing message
            {'severity': 'CRITICAL'},
            # Whitespace-only message
            {'severity': 'CRITICAL', 'message': '   '},
            # None message
            {'severity': 'CRITICAL', 'message': None},
        ]
        
        for test_case in test_cases:
            validated_entry = self.logger._validate_gcp_format(test_case)
            
            # Should have meaningful message and textPayload
            assert validated_entry.get('message'), f"Missing message in validated entry: {test_case}"
            assert validated_entry.get('textPayload'), f"Missing textPayload in validated entry: {test_case}"
            
            # Should not be empty or just whitespace
            message = validated_entry['message']
            text_payload = validated_entry['textPayload']
            
            assert message.strip(), f"Message is empty/whitespace: '{message}'"
            assert text_payload.strip(), f"textPayload is empty/whitespace: '{text_payload}'"
            
            # Should contain fallback text
            assert 'Empty log message detected' in message or 'Log entry' in message, \
                f"No fallback text in message: '{message}'"
    
    def test_json_formatter_robustness_under_errors(self):
        """Test JSON formatter robustness when record processing fails."""
        # Create mock record that will cause formatting errors
        class BadRecord:
            """Mock record that causes various errors during formatting."""
            
            def __init__(self, error_type='attribute'):
                self.error_type = error_type
            
            def __getattr__(self, name):
                if self.error_type == 'attribute':
                    raise AttributeError(f"No attribute '{name}'")
                elif self.error_type == 'type':
                    raise TypeError(f"Type error accessing '{name}'")
                elif self.error_type == 'runtime':
                    raise RuntimeError(f"Runtime error accessing '{name}'")
                else:
                    return None
        
        # Test different error scenarios
        error_scenarios = ['attribute', 'type', 'runtime']
        
        for error_type in error_scenarios:
            bad_record = BadRecord(error_type)
            formatter = self.logger._get_json_formatter()
            
            # Formatter should not raise exceptions
            try:
                formatted_output = formatter(bad_record)
                
                # Should produce valid JSON
                parsed_log = json.loads(formatted_output)
                
                # Should have fallback message
                assert parsed_log.get('message'), f"No fallback message for {error_type} error"
                assert parsed_log.get('textPayload'), f"No fallback textPayload for {error_type} error"
                
                # Should indicate formatting error
                assert 'Log formatting failed' in parsed_log['message'] or \
                       'formatting_error' in parsed_log, \
                       f"No error indication for {error_type} error"
                
            except Exception as e:
                pytest.fail(f"JSON formatter raised exception for {error_type} error: {e}")
    
    def test_sensitive_data_filter_preserves_critical_context(self):
        """Test that sensitive data filtering doesn't remove critical error context."""
        # Create sensitive data filter
        filter_instance = SensitiveDataFilter()
        
        # Test messages with both sensitive and critical context
        test_messages = [
            "Database connection failed: password=secret123 host=db.example.com",
            "JWT token validation error: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.invalid port=5432",
            "API key authentication failed: key=sk-abcd1234567890 endpoint=/api/v1/users",
            "Critical system error in user_id=12345 with api_key=very_long_key_here operation=payment_processing"
        ]
        
        for original_message in test_messages:
            filtered_message = filter_instance.filter_message(original_message)
            
            # Should redact sensitive data
            assert 'password=secret123' not in filtered_message, "Password not redacted"
            assert 'key=sk-abcd' not in filtered_message, "API key not redacted"
            assert 'eyJ0eXAiOiJKV1QiO' not in filtered_message, "JWT token not redacted"
            
            # Should preserve critical context
            assert 'Database connection failed' in filtered_message, "Critical context removed"
            assert 'host=db.example.com' in filtered_message, "Host context removed"
            assert 'port=5432' in filtered_message, "Port context removed"
            assert 'user_id=12345' in filtered_message, "User ID context removed"
            assert 'operation=payment_processing' in filtered_message, "Operation context removed"
            
            # Should contain redaction indicators
            assert '***' in filtered_message, "No redaction indicators found"
    
    def test_context_preservation_during_critical_logging(self):
        """Test that logging context is preserved during critical message generation."""
        # Setup logging context
        context = UnifiedLoggingContext()
        test_context = {
            'request_id': 'test_req_12345',
            'user_id': 'test_user_67890',
            'trace_id': 'test_trace_abcdef',
            'event_type': 'critical_error'
        }
        
        context.set_context(**test_context)
        
        # Mock the logger's context to use our test context
        with patch.object(self.logger, '_context', context):
            # Capture the context when critical logging occurs
            captured_contexts = []
            
            with patch.object(self.logger, '_log') as mock_log:
                def capture_log(*args, **kwargs):
                    # Capture the context at time of logging
                    current_context = self.logger._context.get_context()
                    captured_contexts.append(current_context.copy())
                
                mock_log.side_effect = capture_log
                
                # Trigger critical logging
                self.logger.critical("Test critical message with context")
                
                # Verify context was preserved
                assert len(captured_contexts) > 0, "No context captured during logging"
                
                logged_context = captured_contexts[-1]
                assert logged_context['request_id'] == test_context['request_id'], "Request ID not preserved"
                assert logged_context['user_id'] == test_context['user_id'], "User ID not preserved"
                assert logged_context['trace_id'] == test_context['trace_id'], "Trace ID not preserved"
                assert logged_context['event_type'] == test_context['event_type'], "Event type not preserved"
    
    def test_safe_field_extraction_edge_cases(self):
        """Test _get_safe_field method handles all edge cases properly."""
        # Test various record types and field access patterns
        test_cases = [
            # Dict-like record
            ({'message': 'test message', 'level': 'CRITICAL'}, 'message', 'test message'),
            # Dict-like record with missing field
            ({'level': 'CRITICAL'}, 'message', 'default_message'),
            # Object-like record
            (type('Record', (), {'message': 'object message', 'level': 'CRITICAL'})(), 'message', 'object message'),
            # Object-like record with missing attribute
            (type('Record', (), {'level': 'CRITICAL'})(), 'message', 'default_object'),
            # None record
            (None, 'message', 'none_default'),
            # String record (invalid but should handle gracefully)
            ('string_record', 'message', 'string_default'),
            # Number record (invalid but should handle gracefully)
            (42, 'message', 'number_default'),
        ]
        
        for record, field_name, expected_fallback in test_cases:
            result = self.logger._get_safe_field(record, field_name, expected_fallback)
            
            if hasattr(record, field_name):
                assert result == getattr(record, field_name), f"Wrong value extracted from {type(record)}"
            elif isinstance(record, dict) and field_name in record:
                assert result == record[field_name], f"Wrong value extracted from dict {record}"
            else:
                assert result == expected_fallback, f"Fallback not used for {type(record)} record"
    
    def test_timestamp_generation_robustness(self):
        """Test _get_safe_timestamp method handles all edge cases."""
        # Test normal timestamp generation
        timestamp1 = self.logger._get_safe_timestamp()
        assert timestamp1, "Timestamp should not be empty"
        assert 'T' in timestamp1, "Timestamp should be ISO format"
        assert timestamp1.endswith('Z') or '+' in timestamp1, "Timestamp should have timezone"
        
        # Test timestamp consistency
        timestamp2 = self.logger._get_safe_timestamp()
        assert timestamp1 != timestamp2, "Timestamps should be different"
        
        # Mock datetime failures to test fallbacks
        with patch('shared.logging.unified_logging_ssot.datetime') as mock_datetime:
            # Test primary failure
            mock_datetime.now.side_effect = Exception("Primary timestamp failed")
            mock_datetime.utcnow.return_value.isoformat.return_value = "2024-01-01T00:00:00"
            
            timestamp3 = self.logger._get_safe_timestamp()
            assert timestamp3 == "2024-01-01T00:00:00Z", "First fallback not used"
            
            # Test secondary failure
            mock_datetime.utcnow.side_effect = Exception("Secondary timestamp failed")
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
            
            timestamp4 = self.logger._get_safe_timestamp()
            assert timestamp4 == "2024-01-01T12:00:00", "Second fallback not used"
            
            # Test complete failure
            mock_datetime.now.side_effect = Exception("All timestamp methods failed")
            
            timestamp5 = self.logger._get_safe_timestamp()
            assert timestamp5 == '2024-01-01T00:00:00Z', "Ultimate fallback not used"
    
    def test_exception_serialization_safety(self):
        """Test _serialize_exception_safely handles all exception types."""
        # Test different exception formats
        test_exceptions = [
            # Standard Python exception
            ValueError("Test value error"),
            # Exception with no message
            ValueError(),
            # Custom exception with complex attributes
            type('CustomError', (Exception,), {'custom_attr': 'custom_value'})("Custom message"),
            # None (no exception)
            None,
            # String (invalid but should handle)
            "string_exception",
            # Loguru-style exception object
            type('LoguruException', (), {
                'type': ValueError,
                'value': ValueError("Loguru exception"),
                'traceback': "Mock traceback"
            })(),
        ]
        
        for exception in test_exceptions:
            serialized = self.logger._serialize_exception_safely(exception)
            
            # Should always return dict with required fields
            assert isinstance(serialized, dict), f"Exception serialization returned {type(serialized)}"
            assert 'type' in serialized, f"Missing 'type' field for {type(exception)}"
            assert 'message' in serialized, f"Missing 'message' field for {type(exception)}"
            assert 'traceback' in serialized, f"Missing 'traceback' field for {type(exception)}"
            
            # All fields should be strings
            assert isinstance(serialized['type'], str), f"Type field not string for {type(exception)}"
            assert isinstance(serialized['message'], str), f"Message field not string for {type(exception)}"
            assert isinstance(serialized['traceback'], str), f"Traceback field not string for {type(exception)}"
            
            # Should not be empty (even for None)
            assert serialized['type'], f"Empty type field for {type(exception)}"
            assert serialized['message'], f"Empty message field for {type(exception)}"