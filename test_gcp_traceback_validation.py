#!/usr/bin/env python3
"""
GCP Traceback Capture Validation Test

This test validates that the GCP traceback capture changes maintain system stability
and don't introduce breaking changes.

CHANGES TESTED:
1. Added `_format_traceback_for_gcp()` utility method to `LogFormatter` class
2. Updated line 294 in `gcp_json_formatter` to use new traceback formatter  
3. Fixed traceback extraction to use `traceback.format_tb()` instead of `str(exc.traceback)`
4. Enhanced error handling for edge cases (None traceback, malformed exceptions)

VALIDATION REQUIREMENTS:
1. Existing functionality continues to work
2. No performance degradation
3. Backwards compatibility maintained
4. Error handling graceful
5. Memory/resource usage stable
"""

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import psutil
import os

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
    
def test_traceback_none_handling():
    """Test handling of None traceback."""
    print("🧪 Test: None traceback handling...")
    
    formatter = LogFormatter(SensitiveDataFilter())
    result = formatter._format_traceback_for_gcp(None)
    
    assert result is None, "None traceback should return None"
    
    print("✅ None traceback handling works correctly")

def test_gcp_json_formatter_with_exception():
    """Test GCP JSON formatter with real exception info."""
    print("🧪 Test: GCP JSON formatter with exception...")
    
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
        assert "type" in error_info, "Error should have type"
        assert "value" in error_info, "Error should have value"  
        # Traceback may or may not be present, but if it is, should be properly formatted
        if "traceback" in error_info and error_info["traceback"]:
            assert isinstance(error_info["traceback"], str), "Traceback should be string"
            assert "\\n" in error_info["traceback"], "Traceback should have escaped newlines"
    
    print("✅ GCP JSON formatter with exception works correctly")

def test_backwards_compatibility():
    """Test that existing functionality still works."""
    print("🧪 Test: Backwards compatibility...")
    
    formatter = LogFormatter(SensitiveDataFilter())
    
    # Test regular record without exception
    record = MockLogRecord("INFO", "Regular log message")
    
    # Test both formatters
    json_result = formatter.json_formatter(record)
    gcp_result = formatter.gcp_json_formatter(record)
    
    assert json_result is not None, "JSON formatter should work"
    assert gcp_result is not None, "GCP formatter should work"
    
    # Validate JSON structure
    gcp_parsed = json.loads(gcp_result)
    assert gcp_parsed["severity"] == "INFO", "Severity should be mapped correctly"
    assert gcp_parsed["message"] == "Regular log message", "Message should be preserved"
    
    print("✅ Backwards compatibility maintained")

def test_performance_impact():
    """Test performance impact of traceback changes."""
    print("🧪 Test: Performance impact...")
    
    formatter = LogFormatter(SensitiveDataFilter())
    
    # Create test data
    record = MockLogRecord("INFO", "Performance test message")
    tb = create_test_traceback()
    exc_record = MockLogRecord(
        "ERROR", 
        "Error message",
        MockExceptionInfo(ValueError, ValueError("Error"), tb)
    )
    
    # Measure performance
    iterations = 1000
    
    # Test regular formatting
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
    
    print(f"📊 Regular formatting: {regular_per_call:.2f}ms per call")
    print(f"📊 Exception formatting: {exception_per_call:.2f}ms per call")
    
    # Validate performance is acceptable
    assert regular_per_call < 10.0, f"Regular formatting too slow: {regular_per_call:.2f}ms"
    assert exception_per_call < 50.0, f"Exception formatting too slow: {exception_per_call:.2f}ms"
    
    print("✅ Performance impact within acceptable limits")

def test_memory_usage():
    """Test memory usage doesn't increase significantly."""
    print("🧪 Test: Memory usage...")
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    formatter = LogFormatter(SensitiveDataFilter())
    tb = create_test_traceback()
    
    # Process many records to test for memory leaks
    for i in range(1000):
        exc_record = MockLogRecord(
            "ERROR",
            f"Error message {i}",
            MockExceptionInfo(ValueError, ValueError(f"Error {i}"), tb)
        )
        result = formatter.gcp_json_formatter(exc_record)
        # Don't keep references to results to allow GC
        del result
        del exc_record
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    print(f"📊 Initial memory: {initial_memory:.2f}MB")
    print(f"📊 Final memory: {final_memory:.2f}MB") 
    print(f"📊 Memory increase: {memory_increase:.2f}MB")
    
    # Allow for some reasonable memory increase
    assert memory_increase < 50.0, f"Memory increase too large: {memory_increase:.2f}MB"
    
    print("✅ Memory usage within acceptable limits")

def test_edge_cases():
    """Test various edge cases and error conditions."""
    print("🧪 Test: Edge cases and error handling...")
    
    formatter = LogFormatter(SensitiveDataFilter())
    
    # Test with malformed record
    try:
        result = formatter.gcp_json_formatter({})
        # Should handle gracefully without crashing
        assert isinstance(result, str), "Should return string even for malformed record"
        parsed = json.loads(result)
        assert "severity" in parsed, "Should have fallback severity"
        print("✅ Malformed record handled gracefully")
    except Exception as e:
        print(f"❌ Malformed record handling failed: {e}")
        raise
    
    # Test with missing exception info
    record_no_exc = MockLogRecord("ERROR", "Error without exception")
    record_no_exc.exception = None
    
    result = formatter.gcp_json_formatter(record_no_exc)
    parsed = json.loads(result)
    assert "severity" in parsed, "Should have severity"
    # Error field may or may not be present, but should not crash
    print("✅ Missing exception info handled gracefully")
    
    # Test with invalid traceback
    invalid_exc = MockExceptionInfo(ValueError, ValueError("Test"), "invalid_traceback")
    record_invalid = MockLogRecord("ERROR", "Error with invalid traceback", invalid_exc)
    
    result = formatter.gcp_json_formatter(record_invalid)
    # Should not crash
    assert isinstance(result, str), "Should handle invalid traceback gracefully"
    print("✅ Invalid traceback handled gracefully")

def run_all_tests():
    """Run all validation tests."""
    print("STARTING GCP Traceback Capture Validation Tests")
    print("=" * 60)
    
    test_functions = [
        test_traceback_format_basic,
        test_traceback_none_handling,
        test_gcp_json_formatter_with_exception, 
        test_backwards_compatibility,
        test_performance_impact,
        test_memory_usage,
        test_edge_cases,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
            print()
        except Exception as e:
            print(f"❌ {test_func.__name__} FAILED: {e}")
            failed += 1
            print()
    
    print("=" * 60)
    print(f"🏁 Test Summary: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Changes maintain system stability.")
        return True
    else:
        print("💥 Some tests failed! Changes may introduce regressions.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)