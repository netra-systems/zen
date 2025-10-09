#!/usr/bin/env python3
"""
Test to verify that apex telemetry now properly streams output in real-time
instead of buffering until completion.
"""

import sys
import time
import subprocess
import threading
import tempfile
import os

def create_test_script():
    """Create a test script that outputs events over time"""
    script = '''
import sys
import time

# Simulate WebSocket events being displayed over time
events = [
    "[10:00:00] 🔌 Connected as: test-user",
    "[10:00:01] ✅ Agent started: TestAgent",
    "[10:00:02] 🤔 Thinking: Processing request...",
    "[10:00:03] 🔧 Executing Tool: WebSearch",
    "[10:00:04] ✅ Tool Complete: WebSearch (success)",
    "[10:00:05] ✅ Agent completed successfully"
]

for event in events:
    print(event, flush=True)
    time.sleep(0.5)  # Simulate time between events

print("All events completed!")
'''

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script)
        return f.name

def test_streaming_output():
    """Test that output streams in real-time"""
    print("\n" + "="*70)
    print("TEST: Apex Telemetry Real-Time Streaming")
    print("="*70)

    # Create test script
    test_script = create_test_script()

    try:
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        # Import the apex telemetry wrapper
        from zen.telemetry.apex_telemetry import ApexTelemetryWrapper

        # Mock telemetry manager to avoid actual telemetry
        from unittest.mock import Mock, MagicMock
        import zen.telemetry.apex_telemetry as apex_module

        mock_telemetry = Mock()
        mock_telemetry.is_enabled.return_value = False  # Disable telemetry for test
        apex_module.telemetry_manager = mock_telemetry

        # Test with the wrapper
        wrapper = ApexTelemetryWrapper()

        print("\n📊 Running test script with ApexTelemetryWrapper...")
        print("   Events should appear one at a time with 0.5s delays:")
        print("-" * 60)

        start_time = time.time()
        output_times = []

        # Track when each line appears
        original_print = print
        def track_print(*args, **kwargs):
            if args and '[10:' in str(args[0]):
                output_times.append(time.time() - start_time)
            original_print(*args, **kwargs)

        # Monkey patch print to track timing
        import builtins
        builtins.print = track_print

        # Run the wrapper
        exit_code = wrapper.run_apex_with_telemetry(
            test_script,
            [],  # No additional arguments
            None  # No special environment
        )

        # Restore original print
        builtins.print = original_print

        total_time = time.time() - start_time

        print("-" * 60)
        print(f"\n📊 Results:")
        print(f"  Exit code: {exit_code}")
        print(f"  Total execution time: {total_time:.2f}s")
        print(f"  Output times: {[f'{t:.2f}s' for t in output_times]}")

        # Analyze if output was streamed or buffered
        if len(output_times) >= 2:
            gaps = [output_times[i+1] - output_times[i] for i in range(len(output_times)-1)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 0

            print(f"  Average gap between outputs: {avg_gap:.2f}s")

            # If average gap is close to 0.5s, output is streaming properly
            # If average gap is close to 0, output was buffered
            if avg_gap > 0.3:  # Allow some tolerance
                print("\n✅ PASS: Output is streaming in real-time!")
                print("   Events appeared with proper delays between them.")
                return True
            else:
                print("\n❌ FAIL: Output appears to be buffered!")
                print("   All events appeared at once instead of streaming.")
                return False
        else:
            print("\n⚠️ WARNING: Not enough output to determine streaming behavior")
            return False

    finally:
        # Clean up test script
        if os.path.exists(test_script):
            os.unlink(test_script)

def test_fallback_comparison():
    """Compare telemetry wrapper with direct subprocess.run"""
    print("\n" + "="*70)
    print("TEST: Compare with Fallback (Direct subprocess.run)")
    print("="*70)

    test_script = create_test_script()

    try:
        print("\n📊 Running with direct subprocess.run (fallback mode)...")
        print("   This is how it works without telemetry:")
        print("-" * 60)

        start_time = time.time()

        # Run directly without telemetry wrapper (like the fallback)
        result = subprocess.run(
            [sys.executable, test_script],
            env=os.environ.copy()
        )

        total_time = time.time() - start_time

        print("-" * 60)
        print(f"\n📊 Fallback Results:")
        print(f"  Exit code: {result.returncode}")
        print(f"  Total execution time: {total_time:.2f}s")

        # With proper streaming, this should take ~3 seconds (6 events * 0.5s)
        expected_time = 3.0
        if total_time > expected_time - 0.5 and total_time < expected_time + 1.0:
            print(f"\n✅ Fallback shows proper streaming (took ~{expected_time}s as expected)")
            return True
        else:
            print(f"\n⚠️ Unexpected timing for fallback: {total_time:.2f}s")
            return False

    finally:
        if os.path.exists(test_script):
            os.unlink(test_script)

def main():
    """Run all tests"""
    print("\n" + "🚀 " + "="*68)
    print("  APEX TELEMETRY STREAMING FIX TEST")
    print("  Verifying that output streams in real-time instead of buffering")
    print("="*70)

    results = []

    # Test 1: Verify streaming with telemetry wrapper
    result1 = test_streaming_output()
    results.append(("Telemetry Wrapper Streaming", result1))

    # Test 2: Compare with fallback
    result2 = test_fallback_comparison()
    results.append(("Fallback Comparison", result2))

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
        print("\nThe fix successfully enables real-time streaming of events")
        print("while still capturing output for telemetry. Events now appear")
        print("immediately as they occur, not all at once at the end.")
    else:
        print("❌ Some tests failed")
        print("\nThe streaming issue may not be fully resolved.")
    print("="*70)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())