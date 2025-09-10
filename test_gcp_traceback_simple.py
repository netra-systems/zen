#!/usr/bin/env python3
"""
GCP Traceback Capture Validation Test - Simple Version

This test validates that the GCP traceback capture changes maintain system stability
and don't introduce breaking changes.
"""

import json
import sys
import time
import traceback
from datetime import datetime, timezone

# Import the components we're testing
sys.path.insert(0, '.')
from netra_backend.app.core.logging_formatters import LogFormatter, SensitiveDataFilter

class MockLogRecord:
    """Mock Loguru record for testing."""
    
    def __init__(self, level_name="INFO", message="Test message", exception_info=None):
        self.level = type('Level', (), {'name': level_name})()
        self.message = message
        self.name = "test_module"
        self.function = "test_function"
        self.line = 123
        self.time = datetime.now(timezone.utc)
        self.exception = exception_info
        self.extra = {}
    
    def get(self, key, default=None):
        return getattr(self, key, default)

class MockExceptionInfo:
    """Mock exception info for testing."""
    
    def __init__(self, exc_type=None, exc_value=None, exc_traceback=None):
        self.type = exc_type
        self.value = exc_value  
        self.traceback = exc_traceback

def create_test_traceback():
    """Create a real traceback for testing."""
    try:
        raise ValueError("Test exception for traceback")
    except Exception:
        return sys.exc_info()[2]

def test_traceback_format_basic():
    """Test basic traceback formatting functionality."""
    print("TEST: Basic traceback formatting...")
    
    formatter = LogFormatter(SensitiveDataFilter())
    tb = create_test_traceback()
    
    # Test the new _format_traceback_for_gcp method
    result = formatter._format_traceback_for_gcp(tb)
    
    assert result is not None, "Traceback formatting should not return None"
    assert isinstance(result, str), "Traceback should be formatted as string"
    assert "\\n" in result, "Traceback should have escaped newlines"
    assert "\n" not in result, "Traceback should not have raw newlines"
    
    print("PASS: Basic traceback formatting works correctly")

def test_gcp_json_formatter_with_exception():
    """Test GCP JSON formatter with real exception info."""
    print("TEST: GCP JSON formatter with exception...")
    
    formatter = LogFormatter(SensitiveDataFilter())
    
    # Create real exception info
    tb = create_test_traceback()
    exc_info = MockExceptionInfo(ValueError, ValueError("Test error"), tb)
    
    # Create mock record with exception
    record = MockLogRecord(
        level_name="ERROR", 
        message="Test error occurred",
        exception_info=exc_info
    )
    
    # Test formatting
    result = formatter.gcp_json_formatter(record)
    
    assert result is not None, "Formatter should return result"
    assert isinstance(result, str), "Result should be string"
    
    # Parse JSON to validate structure
    parsed = json.loads(result)
    assert "severity" in parsed, "Should have severity field"
    assert "message" in parsed, "Should have message field"
    assert "timestamp" in parsed, "Should have timestamp field"
    
    # Check if error info is included
    if "error" in parsed:
        error_info = parsed["error"]
        if "traceback" in error_info and error_info["traceback"]:
            assert isinstance(error_info["traceback"], str), "Traceback should be string"
    
    print("PASS: GCP JSON formatter with exception works correctly")

def test_backwards_compatibility():
    """Test that existing functionality still works."""
    print("TEST: Backwards compatibility...")
    
    formatter = LogFormatter(SensitiveDataFilter())
    
    # Test regular record without exception
    record = MockLogRecord("INFO", "Regular log message")
    
    # Test GCP formatter (main focus)
    gcp_result = formatter.gcp_json_formatter(record)
    
    assert gcp_result is not None, "GCP formatter should work"
    
    # Validate JSON structure
    gcp_parsed = json.loads(gcp_result)
    assert gcp_parsed["severity"] == "INFO", "Severity should be mapped correctly"
    assert gcp_parsed["message"] == "Regular log message", "Message should be preserved"
    
    print("PASS: Backwards compatibility maintained")

def test_performance_impact():
    """Test performance impact of traceback changes."""
    print("TEST: Performance impact...")
    
    formatter = LogFormatter(SensitiveDataFilter())
    
    # Create test data
    record = MockLogRecord("INFO", "Performance test message")
    tb = create_test_traceback()
    exc_record = MockLogRecord(
        "ERROR", 
        "Error message",
        MockExceptionInfo(ValueError, ValueError("Error"), tb)
    )
    
    # Test regular formatting (fewer iterations for speed)
    iterations = 100
    start_time = time.time()
    for _ in range(iterations):
        formatter.gcp_json_formatter(record)
    regular_time = time.time() - start_time
    
    # Test with exception formatting 
    start_time = time.time()
    for _ in range(iterations):
        formatter.gcp_json_formatter(exc_record)
    exception_time = time.time() - start_time
    
    # Calculate performance metrics
    regular_per_call = (regular_time / iterations) * 1000  # ms
    exception_per_call = (exception_time / iterations) * 1000  # ms
    
    print(f"Regular formatting: {regular_per_call:.2f}ms per call")
    print(f"Exception formatting: {exception_per_call:.2f}ms per call")
    
    # Validate performance is acceptable
    assert regular_per_call < 50.0, f"Regular formatting too slow: {regular_per_call:.2f}ms"
    assert exception_per_call < 100.0, f"Exception formatting too slow: {exception_per_call:.2f}ms"
    
    print("PASS: Performance impact within acceptable limits")

def run_all_tests():
    """Run all validation tests."""
    print("STARTING GCP Traceback Capture Validation Tests")
    print("=" * 60)
    
    test_functions = [
        test_traceback_format_basic,
        test_gcp_json_formatter_with_exception, 
        test_backwards_compatibility,
        test_performance_impact,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
            print()
        except Exception as e:
            print(f"FAILED {test_func.__name__}: {e}")
            failed += 1
            print()
    
    print("=" * 60)
    print(f"Test Summary: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("SUCCESS: All tests passed! Changes maintain system stability.")
        return True
    else:
        print("FAILURE: Some tests failed! Changes may introduce regressions.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)