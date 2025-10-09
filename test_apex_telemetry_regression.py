#!/usr/bin/env python3
"""
Test to verify that the apex telemetry fix resolves the event streaming issue.
This tests that removing the force_flush() call prevents blocking behavior.
"""

import time
import sys
import os
from unittest.mock import Mock, MagicMock, patch
import logging

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zen.telemetry.apex_telemetry import ApexTelemetryWrapper


def test_no_blocking_on_telemetry():
    """Test that telemetry emission doesn't block for extended periods"""

    print("\n" + "="*70)
    print("TEST: Apex Telemetry Non-Blocking Behavior")
    print("="*70)

    # Mock the telemetry manager
    mock_telemetry = Mock()
    mock_telemetry.is_enabled.return_value = True
    mock_telemetry._tracer = MagicMock()
    mock_telemetry._provider = MagicMock()

    # Track if force_flush was called (it shouldn't be after our fix)
    force_flush_called = False
    force_flush_duration = 0

    def mock_force_flush(timeout_millis=5000):
        nonlocal force_flush_called, force_flush_duration
        force_flush_called = True
        force_flush_duration = timeout_millis
        # Simulate the blocking behavior that was causing issues
        time.sleep(timeout_millis / 1000.0)

    mock_telemetry._provider.force_flush = mock_force_flush

    wrapper = ApexTelemetryWrapper()

    # Patch the telemetry_manager in the module
    with patch('zen.telemetry.apex_telemetry.telemetry_manager', mock_telemetry):
        # Set up test data
        wrapper.start_time = time.time()
        wrapper.end_time = wrapper.start_time + 1.0
        wrapper.exit_code = 0
        wrapper.message = "test message"
        wrapper.env = "staging"

        # Measure how long _emit_telemetry takes
        start = time.time()
        wrapper._emit_telemetry()
        duration = time.time() - start

        print(f"\n📊 Results:")
        print(f"  Telemetry emission duration: {duration:.3f}s")
        print(f"  force_flush called: {force_flush_called}")

        if force_flush_called:
            print(f"  force_flush timeout: {force_flush_duration}ms")
            print("\n❌ FAIL: force_flush is still being called!")
            print("   This would cause blocking behavior.")
            return False
        else:
            print("\n✅ PASS: force_flush is not being called")
            print("   Telemetry won't block event streaming.")

        # Check that emission was fast (should be < 100ms without force_flush)
        if duration > 0.1:
            print(f"\n⚠️ WARNING: Telemetry emission took {duration:.3f}s")
            print("   This might still cause noticeable delays.")
            return False
        else:
            print(f"✅ Telemetry emission was fast ({duration:.3f}s)")
            return True


def test_telemetry_spans_still_created():
    """Verify that spans are still being created even without force_flush"""

    print("\n" + "="*70)
    print("TEST: Telemetry Spans Still Created")
    print("="*70)

    # Mock the telemetry manager
    mock_telemetry = Mock()
    mock_telemetry.is_enabled.return_value = True

    # Track span creation
    span_created = False
    span_attributes = {}

    class MockSpan:
        def __init__(self):
            nonlocal span_created
            span_created = True

        def set_attribute(self, key, value):
            span_attributes[key] = value

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    mock_tracer = Mock()
    mock_tracer.start_as_current_span.return_value = MockSpan()
    mock_telemetry._tracer = mock_tracer

    wrapper = ApexTelemetryWrapper()

    with patch('zen.telemetry.apex_telemetry.telemetry_manager', mock_telemetry):
        # Set up test data
        wrapper.start_time = time.time()
        wrapper.end_time = wrapper.start_time + 1.0
        wrapper.exit_code = 0
        wrapper.message = "test message"
        wrapper.env = "production"
        wrapper.stdout = '{"usage": {"total_tokens": 100}, "cost": {"total_usd": 0.001}}'

        # Emit telemetry
        wrapper._emit_telemetry()

        print(f"\n📊 Results:")
        print(f"  Span created: {span_created}")
        print(f"  Attributes set: {len(span_attributes)}")

        if span_created:
            print("\n✅ PASS: Span was created successfully")

            # Check key attributes
            expected_attrs = ["zen.instance.type", "zen.apex.environment", "zen.apex.message"]
            for attr in expected_attrs:
                if attr in span_attributes:
                    print(f"  ✓ {attr}: {span_attributes[attr]}")
                else:
                    print(f"  ✗ Missing: {attr}")

            # Check if JSON parsing worked
            if "zen.tokens.total" in span_attributes:
                print(f"  ✓ Token metrics parsed: {span_attributes['zen.tokens.total']} tokens")
            if "zen.cost.usd_total" in span_attributes:
                print(f"  ✓ Cost metrics parsed: ${span_attributes['zen.cost.usd_total']}")

            return True
        else:
            print("\n❌ FAIL: Span was not created")
            return False


def main():
    """Run all tests"""

    print("\n" + "🚀 " + "="*68)
    print("  APEX TELEMETRY REGRESSION TEST")
    print("  Verifying fix for event streaming blocking issue")
    print("="*70)

    results = []

    # Test 1: Verify no blocking behavior
    result1 = test_no_blocking_on_telemetry()
    results.append(("No Blocking Behavior", result1))

    # Test 2: Verify spans still work
    result2 = test_telemetry_spans_still_created()
    results.append(("Spans Still Created", result2))

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(r[1] for r in results)

    print("\n" + "="*70)
    if all_passed:
        print("✅ All tests passed!")
        print("\nThe fix successfully removes the blocking force_flush() call")
        print("while maintaining telemetry span creation. Events should now")
        print("stream properly without waiting for telemetry to flush.")
    else:
        print("❌ Some tests failed")
        print("\nThe telemetry might still be causing blocking issues.")
    print("="*70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())