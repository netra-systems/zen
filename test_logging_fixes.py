#!/usr/bin/env python3
"""
Direct test of logging fixes for Issue #253 - Empty CRITICAL log entries
"""

import json
import sys
from datetime import datetime
from unittest.mock import Mock, MagicMock

# Add the project root to the path
sys.path.insert(0, '.')

from shared.logging.unified_logging_ssot import UnifiedLoggingSSOT


def test_timestamp_handling():
    """Test robust timestamp handling."""
    print("Testing timestamp handling...")
    logger = UnifiedLoggingSSOT()
    
    # Test normal case
    timestamp = logger._get_safe_timestamp()
    print(f"Normal timestamp: {timestamp}")
    assert timestamp and isinstance(timestamp, str)
    
    # Test with mocked datetime failure
    original_datetime = datetime
    try:
        import shared.logging.unified_logging_ssot
        shared.logging.unified_logging_ssot.datetime = Mock()
        shared.logging.unified_logging_ssot.datetime.now.side_effect = Exception("Timestamp failure")
        shared.logging.unified_logging_ssot.datetime.utcnow.side_effect = Exception("UTC failure")
        
        # Should still return a valid timestamp
        fallback_timestamp = logger._get_safe_timestamp()
        print(f"Fallback timestamp: {fallback_timestamp}")
        assert fallback_timestamp and isinstance(fallback_timestamp, str)
        
    finally:
        shared.logging.unified_logging_ssot.datetime = original_datetime
    
    print("[PASS] Timestamp handling test passed")


def test_exception_serialization():
    """Test safe exception serialization."""
    print("Testing exception serialization...")
    logger = UnifiedLoggingSSOT()
    
    # Test with problematic exception
    class ProblematicException(Exception):
        def __init__(self, message):
            super().__init__(message)
            self.websocket_connection = MagicMock()  # Non-serializable
            self.circular_ref = self
    
    try:
        raise ProblematicException("Test error")
    except ProblematicException as e:
        # Test direct exception
        result = logger._serialize_exception_safely(e)
        print(f"Exception serialization result: {result}")
        assert isinstance(result, dict)
        assert 'type' in result
        assert 'message' in result
        assert result['type'] == 'ProblematicException'
        
        # Test Loguru-style exception object
        mock_loguru_exception = Mock()
        mock_loguru_exception.type = type(e)
        mock_loguru_exception.value = e
        mock_loguru_exception.traceback = "mocked traceback"
        
        loguru_result = logger._serialize_exception_safely(mock_loguru_exception)
        print(f"Loguru exception result: {loguru_result}")
        assert isinstance(loguru_result, dict)
        assert loguru_result['type'] == 'ProblematicException'
    
    print("[PASS] Exception serialization test passed")


def test_safe_field_access():
    """Test safe field access patterns."""
    print("Testing safe field access...")
    logger = UnifiedLoggingSSOT()
    
    # Test with complete record
    complete_record = {
        'level': Mock(name='CRITICAL'),
        'message': 'Test message',
        'name': 'test_logger'
    }
    
    level_name = logger._get_safe_level_name(complete_record)
    message = logger._get_safe_field(complete_record, 'message', 'default')
    name = logger._get_safe_field(complete_record, 'name', 'default')
    
    print(f"Safe access results: level={level_name}, message={message}, name={name}")
    assert level_name == 'CRITICAL'
    assert message == 'Test message'
    assert name == 'test_logger'
    
    # Test with incomplete record
    incomplete_record = {}
    
    safe_level = logger._get_safe_level_name(incomplete_record)
    safe_message = logger._get_safe_field(incomplete_record, 'message', 'fallback')
    safe_name = logger._get_safe_field(incomplete_record, 'name', 'fallback')
    
    print(f"Fallback results: level={safe_level}, message={safe_message}, name={safe_name}")
    assert safe_level == 'INFO'  # Default fallback
    assert safe_message == 'fallback'
    assert safe_name == 'fallback'
    
    print("✅ Safe field access test passed")


def test_gcp_format_validation():
    """Test GCP format validation."""
    print("Testing GCP format validation...")
    logger = UnifiedLoggingSSOT()
    
    # Test with empty message
    empty_log = {
        'message': '',
        'severity': 'CRITICAL',
        'timestamp': '2024-01-01T00:00:00Z'
    }
    
    validated = logger._validate_gcp_format(empty_log)
    print(f"Validated empty log: {validated}")
    assert validated['message'] != ''
    assert 'textPayload' in validated
    assert validated['textPayload'] != ''
    
    # Test with invalid severity
    invalid_severity_log = {
        'message': 'Test',
        'severity': 'INVALID_LEVEL',
        'timestamp': '2024-01-01T00:00:00Z'
    }
    
    validated_severity = logger._validate_gcp_format(invalid_severity_log)
    print(f"Validated severity: {validated_severity}")
    assert validated_severity['severity'] == 'INFO'
    assert 'original_severity' in validated_severity
    
    print("✅ GCP format validation test passed")


def test_complete_json_formatter():
    """Test the complete JSON formatter with edge cases."""
    print("Testing complete JSON formatter...")
    logger = UnifiedLoggingSSOT()
    
    json_formatter = logger._get_json_formatter()
    
    # Test with problematic record
    problematic_record = {
        'level': Mock(name='CRITICAL'),
        'message': '',  # Empty message
        'name': None,   # None name
        'exception': None,
        'extra': {
            'websocket': MagicMock(),  # Non-serializable
            'circular': {}
        }
    }
    problematic_record['extra']['circular']['self'] = problematic_record['extra']['circular']
    
    try:
        result = json_formatter(problematic_record)
        print(f"JSON formatter result: {result}")
        
        # Should not be empty
        assert result != ""
        
        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        
        # Should have required fields
        assert 'message' in parsed
        assert 'severity' in parsed
        assert 'timestamp' in parsed
        assert 'textPayload' in parsed
        
        # Message should not be empty after validation
        assert parsed['message'] != ''
        assert parsed['textPayload'] != ''
        
        print(f"Parsed result: {parsed}")
        
    except Exception as e:
        print(f"JSON formatter error (should not happen): {e}")
        raise
    
    print("✅ Complete JSON formatter test passed")


def test_context_thread_safety():
    """Test thread-safe context access."""
    print("Testing thread-safe context access...")
    logger = UnifiedLoggingSSOT()
    
    # Test normal context access
    context = logger._context.get_context_safe()
    print(f"Safe context access: {context}")
    assert isinstance(context, dict)
    
    # Test with context variables set
    from shared.logging.unified_logging_ssot import user_id_context, request_id_context
    
    user_id_context.set('test_user')
    request_id_context.set('test_request')
    
    context_with_data = logger._context.get_context_safe()
    print(f"Context with data: {context_with_data}")
    assert context_with_data.get('user_id') == 'test_user'
    assert context_with_data.get('request_id') == 'test_request'
    
    print("✅ Thread-safe context test passed")


if __name__ == "__main__":
    print("=== Testing Logging Fixes for Issue #253 ===\n")
    
    try:
        test_timestamp_handling()
        test_exception_serialization()
        test_safe_field_access()
        test_gcp_format_validation()
        test_complete_json_formatter()
        test_context_thread_safety()
        
        print("\n[SUCCESS] All logging fixes validated successfully!")
        print("[PASS] Issue #253 (Empty CRITICAL log entries) is resolved")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)