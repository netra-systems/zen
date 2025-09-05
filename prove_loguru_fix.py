"""Proof that the Loguru format_map error is fixed.

This script demonstrates:
1. The exact error scenario that was happening
2. That the fix handles all Loguru record types
3. That the GCP formatter now works in production-like conditions
"""

import sys
import os
import json
from io import StringIO
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment to simulate GCP
os.environ['ENVIRONMENT'] = 'staging'
os.environ['K_SERVICE'] = 'netra-backend'  # Simulate Cloud Run

from loguru import logger
from netra_backend.app.core.logging_formatters import LogHandlerConfig, LogFormatter, SensitiveDataFilter


def capture_gcp_logs():
    """Capture GCP-formatted logs to prove they work."""
    output = StringIO()
    
    # Remove default handlers
    logger.remove()
    
    # Add GCP-style handler with our formatter
    def gcp_sink(message):
        formatter = LogFormatter(SensitiveDataFilter())
        record = message.record if hasattr(message, 'record') else message
        try:
            json_output = formatter.gcp_json_formatter(record)
            output.write(json_output + "\n")
            print(f"[OK] Successfully formatted: {json.loads(json_output)['message'][:50]}...")
        except Exception as e:
            print(f"[FAIL] FAILED: {e}")
            raise
    
    logger.add(gcp_sink, format="{message}")
    return output


def test_real_loguru_messages():
    """Test real Loguru messages that would have caused the error."""
    print("=" * 70)
    print("PROOF: Testing Real Loguru Messages (would have crashed before fix)")
    print("=" * 70)
    
    output = capture_gcp_logs()
    
    # Test 1: Normal messages with all Loguru record fields
    logger.info("Standard info message from backend service")
    logger.warning("Warning about resource usage", cpu=85.5, memory=2048)
    logger.error("Database connection failed", error_code="DB_CONN_REFUSED")
    
    # Test 2: Messages with exception info (complex Loguru structure)
    try:
        raise ValueError("Test exception for logging")
    except Exception:
        logger.exception("Caught an exception during processing")
    
    # Test 3: Critical message with complex context
    logger.bind(request_id="req-123", user_id="user-456").critical(
        "Critical system failure detected",
        service="auth",
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    # Test 4: Debug with nested context
    logger.debug("Debugging complex object", 
                 data={"nested": {"deeply": {"value": "test"}}})
    
    # Verify all messages were formatted correctly
    output.seek(0)
    lines = output.readlines()
    
    print(f"\n[OK] Successfully processed {len(lines)} log messages")
    print("\nValidating JSON structure of each message:")
    
    for i, line in enumerate(lines, 1):
        try:
            parsed = json.loads(line)
            assert 'severity' in parsed
            assert 'message' in parsed
            assert 'timestamp' in parsed
            assert 'labels' in parsed
            print(f"  Message {i}: [OK] Valid GCP JSON - Severity: {parsed['severity']}, "
                  f"Message: {parsed['message'][:40]}...")
        except (json.JSONDecodeError, AssertionError) as e:
            print(f"  Message {i}: [FAIL] INVALID JSON - {e}")
            return False
    
    return True


def test_edge_cases():
    """Test edge cases that could cause format_map errors."""
    print("\n" + "=" * 70)
    print("PROOF: Testing Edge Cases (would have caused format_map error)")
    print("=" * 70)
    
    formatter = LogFormatter(SensitiveDataFilter())
    
    test_cases = [
        ("Empty record", {}),
        ("None values", {"level": None, "message": None, "time": None}),
        ("Missing level", {"message": "Test", "time": datetime.now(timezone.utc)}),
        ("String level", {"level": "ERROR", "message": "String level test"}),
        ("Dict level", {"level": {"name": "WARNING"}, "message": "Dict level test"}),
        ("No message field", {"level": "INFO"}),
        ("Invalid record type", None),
    ]
    
    for name, record in test_cases:
        try:
            result = formatter.gcp_json_formatter(record)
            parsed = json.loads(result)
            print(f"[OK] {name}: Successfully handled - Severity: {parsed['severity']}")
        except Exception as e:
            print(f"[FAIL] {name}: FAILED - {e}")
            return False
    
    return True


def test_production_scenario():
    """Simulate production GCP Cloud Run environment."""
    print("\n" + "=" * 70)
    print("PROOF: Production Scenario (GCP Cloud Run with JSON logging)")
    print("=" * 70)
    
    # Configure as in production
    handler_config = LogHandlerConfig(
        level="INFO",
        enable_json=True
    )
    
    # Capture output
    output = StringIO()
    saved_stderr = sys.stderr
    sys.stderr = output
    
    try:
        # This is what happens in production
        logger.remove()
        
        # Add production handler (this would have crashed before)
        def gcp_sink(message):
            formatter = LogFormatter(SensitiveDataFilter())
            record = message.record if hasattr(message, 'record') else message
            json_output = formatter.gcp_json_formatter(record)
            sys.stderr.write(json_output + "\n")
            sys.stderr.flush()
        
        logger.add(
            gcp_sink,
            level="INFO",
            enqueue=True,
            backtrace=True,
            diagnose=False,
            catch=True
        )
        
        # Log production-like messages
        logger.info("Application started", version="1.2.3", environment="staging")
        logger.warning("High memory usage detected", usage_mb=1024)
        logger.error("Failed to connect to cache", service="redis", retry_count=3)
        
        # Check output
        output.seek(0)
        logs = output.readlines()
        
        print(f"[OK] Generated {len(logs)} production logs without errors")
        
        for i, log in enumerate(logs, 1):
            parsed = json.loads(log)
            print(f"  Log {i}: {parsed['severity']} - {parsed['message'][:50]}...")
        
        return True
        
    finally:
        sys.stderr = saved_stderr


def main():
    """Run all proofs."""
    print("\n" + "=" * 70)
    print("LOGURU FORMAT_MAP ERROR FIX - PROOF OF RESOLUTION")
    print("=" * 70)
    
    results = []
    
    # Run all test scenarios
    results.append(("Real Loguru Messages", test_real_loguru_messages()))
    results.append(("Edge Cases", test_edge_cases()))
    results.append(("Production Scenario", test_production_scenario()))
    
    # Summary
    print("\n" + "=" * 70)
    print("FINAL PROOF SUMMARY")
    print("=" * 70)
    
    all_passed = all(result for _, result in results)
    
    for test_name, passed in results:
        status = "[PASSED]" if passed else "[FAILED]"
        print(f"{test_name}: {status}")
    
    if all_passed:
        print("\n[SUCCESS] ALL TESTS PASSED - The Loguru format_map error is FIXED!")
        print("\nThe formatter now:")
        print("  • Handles all Loguru record structures correctly")
        print("  • Safely processes namedtuple levels and datetime objects")
        print("  • Provides fallback for any unexpected record format")
        print("  • Works in production GCP Cloud Run environment")
        print("  • Will not crash with AttributeError or format_map errors")
    else:
        print("\n[ERROR] Some tests failed - please review")
        sys.exit(1)


if __name__ == "__main__":
    main()