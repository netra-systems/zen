#!/usr/bin/env python3
"""
Test Script for Issue #1171 - WebSocket Startup Phase Race Condition Fix

This script validates that the fixed timing implementation eliminates the 2.8s
variance in WebSocket connection establishment by testing the timing consistency
of the startup phase validation.
"""

import asyncio
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

try:
    from netra_backend.app.websocket_core.gcp_initialization_validator import (
        GCPWebSocketInitializationValidator,
        GCPReadinessState
    )
except ImportError as e:
    print(f"Import failed: {e}")
    print("This test requires the backend modules to be available")
    sys.exit(1)

class MockAppState:
    """Mock app state for testing"""
    def __init__(self, startup_phase='services'):
        self.startup_phase = startup_phase
        self.startup_complete = True
        self.startup_failed = False

async def test_timing_consistency():
    """Test that the fixed timing approach provides consistent results"""
    print("🔧 Testing WebSocket Race Condition Fix (Issue #1171)")
    print("=" * 60)

    # Create mock app state that's already in services phase
    app_state = MockAppState('services')

    # Test multiple runs to measure timing variance
    timing_results = []

    for i in range(5):
        print(f"\n📊 Test run {i+1}/5")

        validator = GCPWebSocketInitializationValidator(app_state)

        start_time = time.time()
        try:
            # Run the validation with a short timeout since services are "ready"
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=2.0)
            elapsed = time.time() - start_time

            timing_results.append(elapsed)

            print(f"  ✅ Validation completed in {elapsed:.3f}s")
            print(f"  📋 Result ready: {result.ready}")
            print(f"  🏷️ State: {result.state}")

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  ❌ Validation failed after {elapsed:.3f}s: {e}")
            timing_results.append(elapsed)

    # Analyze timing variance
    if timing_results:
        min_time = min(timing_results)
        max_time = max(timing_results)
        avg_time = sum(timing_results) / len(timing_results)
        variance = max_time - min_time

        print(f"\n📈 TIMING ANALYSIS:")
        print(f"   Min time: {min_time:.3f}s")
        print(f"   Max time: {max_time:.3f}s")
        print(f"   Average:  {avg_time:.3f}s")
        print(f"   Variance: {variance:.3f}s")

        # The fix should reduce variance significantly
        if variance < 0.5:  # Less than 500ms variance
            print(f"   ✅ SUCCESS: Low variance ({variance:.3f}s) indicates race condition fixed")
            return True
        else:
            print(f"   ❌ CONCERN: High variance ({variance:.3f}s) may indicate timing issues persist")
            return False

    return False

async def test_phase_transition_timing():
    """Test timing during phase transitions"""
    print(f"\n🔄 Testing Phase Transition Timing")
    print("-" * 40)

    # Test with app state that transitions from 'cache' to 'services'
    app_state = MockAppState('cache')  # Start in cache phase
    validator = GCPWebSocketInitializationValidator(app_state)

    async def simulate_phase_transition():
        """Simulate a phase transition after 0.5s"""
        await asyncio.sleep(0.5)
        app_state.startup_phase = 'services'  # Transition to services
        print("  🔄 Simulated phase transition: cache -> services")

    # Start the phase transition simulation
    transition_task = asyncio.create_task(simulate_phase_transition())

    start_time = time.time()
    try:
        result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)
        elapsed = time.time() - start_time

        print(f"  ✅ Phase transition handled in {elapsed:.3f}s")
        print(f"  📋 Result ready: {result.ready}")

        # With fixed interval of 0.1s, should detect transition within ~0.6s
        if 0.5 <= elapsed <= 1.0:
            print(f"  ✅ SUCCESS: Transition detected within expected timeframe")
            return True
        else:
            print(f"  ❌ TIMING: Transition took {elapsed:.3f}s (expected 0.5-1.0s)")
            return False

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Phase transition test failed after {elapsed:.3f}s: {e}")
        return False
    finally:
        # Cleanup
        if not transition_task.done():
            transition_task.cancel()

async def main():
    """Main test runner"""
    print("Issue #1171 - WebSocket Race Condition Fix Validation")
    print("=" * 60)
    print("Testing fixed-interval timing approach vs. exponential backoff")

    # Test 1: Timing consistency
    test1_result = await test_timing_consistency()

    # Test 2: Phase transition handling
    test2_result = await test_phase_transition_timing()

    # Overall results
    print(f"\n🏁 FINAL RESULTS:")
    print(f"   Timing Consistency: {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"   Phase Transitions:  {'✅ PASS' if test2_result else '❌ FAIL'}")

    if test1_result and test2_result:
        print(f"\n✅ SUCCESS: Race condition fix appears to be working!")
        print(f"   Fixed 0.1s intervals eliminate timing variance")
        print(f"   WebSocket connections should now be consistent")
        return 0
    else:
        print(f"\n❌ ISSUES DETECTED: Race condition fix may need refinement")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        sys.exit(1)