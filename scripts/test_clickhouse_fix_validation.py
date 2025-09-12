#!/usr/bin/env python3
"""
Direct validation of ClickHouse logging fix for GitHub Issue #134.
This tests the critical fix in _handle_connection_error function.
"""

import logging
import io
import os
import sys
from contextlib import contextmanager

# Add the project root to path for imports
sys.path.insert(0, '/Users/anthony/Desktop/netra-apex')

from netra_backend.app.db.clickhouse import _handle_connection_error


@contextmanager
def capture_logs():
    """Capture log messages for analysis."""
    log_capture_string = io.StringIO()
    ch = logging.StreamHandler(log_capture_string)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    
    # Get all loggers to capture all log messages
    loggers = [
        logging.getLogger('netra_backend.app.logging_config'),
        logging.getLogger('netra_backend.app.db.clickhouse'),
        logging.getLogger('__main__'),
        logging.getLogger('')  # root logger
    ]
    original_levels = []
    
    for logger in loggers:
        original_levels.append(logger.level)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(ch)
    
    try:
        yield log_capture_string
    finally:
        for logger, original_level in zip(loggers, original_levels):
            logger.removeHandler(ch)
            logger.setLevel(original_level)


def test_optional_service_behavior():
    """Test that optional ClickHouse service logs WARNING instead of ERROR."""
    print("=== Testing Optional Service Behavior ===")
    
    # Set environment for optional service
    os.environ['ENVIRONMENT'] = 'staging'
    os.environ['CLICKHOUSE_REQUIRED'] = 'false'
    
    with capture_logs() as log_capture:
        test_exception = ConnectionRefusedError("Connection refused for test")
        
        try:
            _handle_connection_error(test_exception)
            exception_raised = False
        except Exception as e:
            exception_raised = True
            print(f" FAIL:  ERROR: Optional service raised exception: {e}")
            return False
            
        log_output = log_capture.getvalue()
        print("Log output:")
        print(log_output)
        
        # Analyze logs
        lines = log_output.strip().split('\n')
        error_logs = [line for line in lines if 'ERROR' in line]
        warning_logs = [line for line in lines if 'WARNING' in line]
        
        print(f"Error logs: {len(error_logs)}")
        print(f"Warning logs: {len(warning_logs)}")
        
        # Check that no exception was raised (graceful degradation)
        if exception_raised:
            print(" FAIL:  FAIL: Optional service should not raise exception")
            return False
            
        # Check that no ERROR logs were generated
        if error_logs:
            print(f" FAIL:  FAIL: Optional service should not log ERROR, found: {error_logs}")
            return False
            
        # Check that WARNING logs were generated
        if not warning_logs:
            print(" FAIL:  FAIL: Optional service should log WARNING for graceful degradation")
            return False
            
        # Check for expected warning patterns
        expected_patterns = ['optional', 'continuing without', 'analytics features disabled']
        found_patterns = []
        for pattern in expected_patterns:
            if any(pattern.lower() in log.lower() for log in warning_logs):
                found_patterns.append(pattern)
                
        if not found_patterns:
            print(f" FAIL:  FAIL: Expected warning patterns not found: {expected_patterns}")
            print(f"Actual warnings: {warning_logs}")
            return False
            
        print(" PASS:  PASS: Optional service behavior correct")
        return True


def test_required_service_behavior():
    """Test that required ClickHouse service still logs ERROR appropriately."""
    print("\n=== Testing Required Service Behavior ===")
    
    # Set environment for required service  
    os.environ['ENVIRONMENT'] = 'production'
    os.environ['CLICKHOUSE_REQUIRED'] = 'true'
    
    with capture_logs() as log_capture:
        test_exception = ConnectionRefusedError("Connection refused for test")
        
        try:
            _handle_connection_error(test_exception)
            exception_raised = False
        except Exception as e:
            exception_raised = True
            print(f"Expected exception for required service: {e}")
            
        log_output = log_capture.getvalue()
        print("Log output:")
        print(log_output)
        
        # Analyze logs
        lines = log_output.strip().split('\n')
        error_logs = [line for line in lines if 'ERROR' in line]
        warning_logs = [line for line in lines if 'WARNING' in line and 'optional' in line.lower()]
        
        print(f"Error logs: {len(error_logs)}")
        print(f"Degradation warning logs: {len(warning_logs)}")
        
        # Check that exception was raised (fail fast for required services)
        if not exception_raised:
            print(" FAIL:  FAIL: Required service should raise exception")
            return False
            
        # Check that ERROR logs were generated
        if not error_logs:
            print(" FAIL:  FAIL: Required service should log ERROR")
            return False
            
        # Check that degradation warnings were NOT generated
        if warning_logs:
            print(f" FAIL:  FAIL: Required service should not log graceful degradation warnings: {warning_logs}")
            return False
            
        print(" PASS:  PASS: Required service behavior correct")
        return True


def test_missing_required_flag():
    """Test default behavior when CLICKHOUSE_REQUIRED is not set."""
    print("\n=== Testing Missing Required Flag Behavior ===")
    
    # Set environment but don't set CLICKHOUSE_REQUIRED
    os.environ['ENVIRONMENT'] = 'staging'
    if 'CLICKHOUSE_REQUIRED' in os.environ:
        del os.environ['CLICKHOUSE_REQUIRED']
    
    with capture_logs() as log_capture:
        test_exception = ConnectionRefusedError("Connection refused for test")
        
        try:
            _handle_connection_error(test_exception)
            exception_raised = False
        except Exception as e:
            exception_raised = True
            print(f"Exception raised: {e}")
            
        log_output = log_capture.getvalue()
        print("Log output:")
        print(log_output)
        
        # Should default to optional behavior (CLICKHOUSE_REQUIRED defaults to false)
        if exception_raised:
            print(" FAIL:  FAIL: Should default to optional behavior when CLICKHOUSE_REQUIRED is not set")
            return False
            
        lines = log_output.strip().split('\n')
        warning_logs = [line for line in lines if 'WARNING' in line]
        
        if not warning_logs:
            print(" FAIL:  FAIL: Should log WARNING when defaulting to optional behavior")
            return False
            
        print(" PASS:  PASS: Missing required flag defaults to optional behavior")
        return True


def main():
    """Run all validation tests."""
    print("ClickHouse Logging Fix Validation")
    print("=" * 50)
    
    tests = [
        test_optional_service_behavior,
        test_required_service_behavior,
        test_missing_required_flag
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f" FAIL:  EXCEPTION in {test.__name__}: {e}")
            failed += 1
    
    print(f"\n=== SUMMARY ===")
    print(f" PASS:  Passed: {passed}")
    print(f" FAIL:  Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("\n CELEBRATION:  ALL TESTS PASSED - Fix is working correctly!")
        return True
    else:
        print(f"\n[U+1F4A5] {failed} TESTS FAILED - Fix needs investigation!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)