#!/usr/bin/env python3
"""
Quick validation script for ClickHouse logging tests
====================================================

This script runs a simplified version of the key failing tests to validate that:
1. The test framework is working correctly
2. The failing test patterns are properly implemented
3. Current code exhibits the logging issue as expected

Usage:
    python validate_clickhouse_logging_tests.py
"""

import asyncio
import logging
import io
import sys
from contextlib import contextmanager
from unittest.mock import patch

# Add the project root to the path
sys.path.insert(0, '/Users/anthony/Desktop/netra-apex')

from netra_backend.app.db.clickhouse import ClickHouseService, _handle_connection_error
from shared.isolated_environment import IsolatedEnvironment


@contextmanager
def capture_logs():
    """Capture log messages for analysis."""
    log_capture_string = io.StringIO()
    ch = logging.StreamHandler(log_capture_string)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    
    logger = logging.getLogger("netra_backend.app.logging_config")
    original_level = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    
    try:
        yield log_capture_string
    finally:
        logger.removeHandler(ch)
        logger.setLevel(original_level)


def analyze_logs(log_output):
    """Analyze log output for error patterns."""
    lines = [line.strip() for line in log_output.strip().split('\n') if line.strip()]
    
    analysis = {
        'total_lines': len(lines),
        'error_logs': [line for line in lines if 'ERROR' in line],
        'warning_logs': [line for line in lines if 'WARNING' in line],
        'clickhouse_errors': [line for line in lines if 'ERROR' in line and ('ClickHouse' in line or 'clickhouse' in line.lower())],
        'clickhouse_warnings': [line for line in lines if 'WARNING' in line and ('ClickHouse' in line or 'clickhouse' in line.lower())]
    }
    
    return analysis


async def test_optional_service_should_fail_with_current_code():
    """
    Critical test that should FAIL with current code.
    
    This test validates that optional ClickHouse service currently logs ERROR
    instead of WARNING, demonstrating the issue exists.
    """
    print("\n🧪 Testing optional service behavior (should demonstrate the issue)...")
    
    # Configure staging environment with optional ClickHouse
    env = IsolatedEnvironment()
    env.enable_isolation()
    
    env.set('ENVIRONMENT', 'staging', 'test')
    env.set('CLICKHOUSE_REQUIRED', 'false', 'test')  # Optional service
    env.set('CLICKHOUSE_HOST', 'test.unavailable.clickhouse', 'test')
    env.set('USE_MOCK_CLICKHOUSE', 'false', 'test')
    
    try:
        with capture_logs() as log_capture:
            service = ClickHouseService()
            
            # Mock connection failure
            with patch('netra_backend.app.db.clickhouse._create_base_client') as mock_client:
                mock_client.side_effect = ConnectionRefusedError("Test connection failure")
                
                # Test service initialization
                try:
                    await service.initialize()
                    initialization_succeeded = True
                    print("✓ Service initialization succeeded (good - optional service should continue)")
                except Exception as e:
                    initialization_succeeded = False
                    print(f"✗ Service initialization failed: {e} (bad - optional service should not fail)")
                
                # Analyze logs
                log_output = log_capture.getvalue()
                analysis = analyze_logs(log_output)
                
                print(f"\n📊 Log Analysis:")
                print(f"   Total log lines: {analysis['total_lines']}")
                print(f"   ERROR logs: {len(analysis['error_logs'])}")
                print(f"   WARNING logs: {len(analysis['warning_logs'])}")
                print(f"   ClickHouse ERROR logs: {len(analysis['clickhouse_errors'])}")
                print(f"   ClickHouse WARNING logs: {len(analysis['clickhouse_warnings'])}")
                
                # Key test: Optional service should NOT log ERROR
                if len(analysis['clickhouse_errors']) > 0:
                    print(f"\n❌ ISSUE DEMONSTRATED: Optional service logged {len(analysis['clickhouse_errors'])} ERROR messages:")
                    for error_log in analysis['clickhouse_errors']:
                        print(f"      {error_log}")
                    print("   This demonstrates the core issue - ERROR logs for optional services.")
                    return False  # Test "fails" as expected - demonstrates the issue
                else:
                    print(f"\n✅ ISSUE NOT FOUND: Optional service did not log ERROR messages.")
                    if len(analysis['clickhouse_warnings']) > 0:
                        print("   Found appropriate WARNING logs instead:")
                        for warning_log in analysis['clickhouse_warnings']:
                            print(f"      {warning_log}")
                        print("   This suggests the fix may already be implemented.")
                    return True  # Test "passes" - issue may be fixed
                
    finally:
        env.disable_isolation()


async def test_required_service_should_pass():
    """
    Test that should PASS with current code.
    
    This validates that required services correctly log ERROR.
    """
    print("\n🧪 Testing required service behavior (should work correctly)...")
    
    # Configure production environment with required ClickHouse
    env = IsolatedEnvironment()
    env.enable_isolation()
    
    env.set('ENVIRONMENT', 'production', 'test')
    env.set('CLICKHOUSE_REQUIRED', 'true', 'test')  # Required service
    env.set('CLICKHOUSE_HOST', 'test.unavailable.clickhouse', 'test')
    env.set('USE_MOCK_CLICKHOUSE', 'false', 'test')
    
    try:
        with capture_logs() as log_capture:
            service = ClickHouseService()
            
            # Mock connection failure
            with patch('netra_backend.app.db.clickhouse._create_base_client') as mock_client:
                mock_client.side_effect = ConnectionRefusedError("Test connection failure")
                
                # Test service initialization
                try:
                    await service.initialize()
                    initialization_succeeded = True
                    print("✗ Service initialization succeeded (bad - required service should fail)")
                except Exception as e:
                    initialization_succeeded = False
                    print("✓ Service initialization failed (good - required service should fail hard)")
                
                # Analyze logs
                log_output = log_capture.getvalue()
                analysis = analyze_logs(log_output)
                
                print(f"\n📊 Log Analysis:")
                print(f"   Total log lines: {analysis['total_lines']}")
                print(f"   ERROR logs: {len(analysis['error_logs'])}")
                print(f"   ClickHouse ERROR logs: {len(analysis['clickhouse_errors'])}")
                
                # Key test: Required service should log ERROR
                if len(analysis['clickhouse_errors']) > 0:
                    print(f"\n✅ CORRECT BEHAVIOR: Required service logged {len(analysis['clickhouse_errors'])} ERROR messages:")
                    for error_log in analysis['clickhouse_errors']:
                        print(f"      {error_log}")
                    return True  # Test passes - correct behavior
                else:
                    print(f"\n❌ MISSING ERROR LOGS: Required service should log ERROR but found none.")
                    return False  # Test fails - missing expected errors
                
    finally:
        env.disable_isolation()


def test_error_handler_context_awareness():
    """
    Test _handle_connection_error function for context awareness.
    
    This should demonstrate that the error handler is not context-aware.
    """
    print("\n🧪 Testing error handler context awareness...")
    
    # Test optional service scenario
    env = IsolatedEnvironment()
    env.enable_isolation()
    
    env.set('ENVIRONMENT', 'staging', 'test')
    env.set('CLICKHOUSE_REQUIRED', 'false', 'test')  # Optional
    
    try:
        with capture_logs() as log_capture:
            test_exception = ConnectionRefusedError("Test error handler")
            
            try:
                _handle_connection_error(test_exception)
                error_handler_raised = False
                print("✓ Error handler did not raise (good for optional service)")
            except ConnectionRefusedError:
                error_handler_raised = True
                print("✗ Error handler raised exception (bad for optional service)")
            
            # Analyze logs
            log_output = log_capture.getvalue()
            analysis = analyze_logs(log_output)
            
            print(f"\n📊 Error Handler Log Analysis:")
            print(f"   Total log lines: {analysis['total_lines']}")
            print(f"   ERROR logs: {len(analysis['error_logs'])}")
            print(f"   WARNING logs: {len(analysis['warning_logs'])}")
            
            # Check if error handler is context-aware
            if len(analysis['error_logs']) == 0 and len(analysis['warning_logs']) > 0:
                print("✅ Error handler appears context-aware - uses WARNING for optional service")
                return True
            elif len(analysis['error_logs']) > 0:
                print("❌ Error handler not context-aware - uses ERROR for optional service")
                print("   ERROR logs found:")
                for error_log in analysis['error_logs']:
                    print(f"      {error_log}")
                return False
            else:
                print("⚠️  No clear logging pattern detected")
                return False
                
    finally:
        env.disable_isolation()


async def main():
    """Run validation tests."""
    print("🚀 ClickHouse Logging Test Validation")
    print("=====================================")
    print("This script validates that our failing tests correctly demonstrate the logging issue.")
    print()
    
    # Run validation tests
    results = {}
    
    try:
        results['optional_service'] = await test_optional_service_should_fail_with_current_code()
        results['required_service'] = await test_required_service_should_pass()
        results['error_handler'] = test_error_handler_context_awareness()
        
        # Summary
        print("\n" + "="*60)
        print("📋 VALIDATION SUMMARY")
        print("="*60)
        
        if not results['optional_service']:
            print("✅ Optional service test FAILED as expected - demonstrates the issue exists")
        else:
            print("⚠️  Optional service test PASSED - issue may already be fixed")
            
        if results['required_service']:
            print("✅ Required service test PASSED as expected - correct ERROR behavior")
        else:
            print("❌ Required service test FAILED - unexpected behavior")
            
        if not results['error_handler']:
            print("✅ Error handler test shows lack of context awareness - demonstrates the issue")
        else:
            print("⚠️  Error handler test shows context awareness - fix may be implemented")
        
        # Overall assessment
        issues_demonstrated = sum(1 for result in [
            not results['optional_service'],  # Should fail to demonstrate issue
            results['required_service'],      # Should pass (correct behavior)
            not results['error_handler']      # Should fail to demonstrate issue
        ])
        
        print(f"\n🎯 ASSESSMENT: {issues_demonstrated}/3 tests demonstrate expected behavior")
        
        if issues_demonstrated >= 2:
            print("✅ Test suite successfully demonstrates the ClickHouse logging issue")
            print("   Ready for fix implementation!")
        else:
            print("⚠️  Test results suggest issue may already be partially addressed")
            print("   Review current implementation before proceeding with fix")
            
    except Exception as e:
        print(f"\n❌ VALIDATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)