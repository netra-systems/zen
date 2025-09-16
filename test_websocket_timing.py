#!/usr/bin/env python3
"""
Direct Test for Issue #1171 - WebSocket Startup Timing Consistency

This script directly tests the _wait_for_startup_phase_completion method
to ensure the fixed interval approach eliminates timing variance.
"""

import asyncio
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

try:
    from netra_backend.app.websocket_core.gcp_initialization_validator import (
        GCPWebSocketInitializationValidator
    )
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

class SimulatedAppState:
    """Simulated app state that transitions through phases"""
    def __init__(self):
        self.startup_phase = 'cache'  # Start in cache phase
        self.startup_complete = False
        self.startup_failed = False
        self._phase_transition_time = None

    def simulate_phase_transition_after_delay(self, delay_seconds=0.5):
        """Schedule a phase transition after a delay"""
        async def transition():
            await asyncio.sleep(delay_seconds)
            self.startup_phase = 'services'
            print(f"  🔄 Phase transitioned to 'services' after {delay_seconds}s")

        return asyncio.create_task(transition())

async def test_fixed_interval_timing():
    """Test that fixed interval timing is consistent"""
    print("🧪 Testing Fixed Interval Timing Consistency")
    print("=" * 50)

    timing_results = []

    for i in range(5):
        print(f"\n🔍 Test Run {i+1}/5")

        # Create fresh app state for each test
        app_state = SimulatedAppState()
        validator = GCPWebSocketInitializationValidator(app_state)

        # Start phase transition simulation
        transition_task = app_state.simulate_phase_transition_after_delay(0.3)

        start_time = time.time()

        try:
            # This should use fixed 0.1s intervals now
            success = await validator._wait_for_startup_phase_completion(
                minimum_phase='services',
                timeout_seconds=2.0
            )
            elapsed = time.time() - start_time
            timing_results.append(elapsed)

            print(f"  ⏱️  Completed in: {elapsed:.3f}s")
            print(f"  ✅ Success: {success}")

        except Exception as e:
            elapsed = time.time() - start_time
            timing_results.append(elapsed)
            print(f"  ❌ Failed after {elapsed:.3f}s: {e}")
        finally:
            # Cleanup
            if not transition_task.done():
                transition_task.cancel()

    # Analyze consistency
    if len(timing_results) >= 3:
        min_time = min(timing_results)
        max_time = max(timing_results)
        avg_time = sum(timing_results) / len(timing_results)
        variance = max_time - min_time

        print(f"\n📊 TIMING ANALYSIS:")
        print(f"   Min: {min_time:.3f}s")
        print(f"   Max: {max_time:.3f}s")
        print(f"   Avg: {avg_time:.3f}s")
        print(f"   Variance: {variance:.3f}s")

        # Since phase transitions at 0.3s and we check every 0.1s,
        # we should detect within 0.4s consistently
        expected_min = 0.3  # Minimum time for phase transition
        expected_max = 0.7  # Maximum with some overhead

        if variance < 0.2:  # Less than 200ms variance
            print(f"   ✅ SUCCESS: Low variance indicates consistent timing")
        else:
            print(f"   ⚠️  WARNING: High variance may indicate timing issues")

        if expected_min <= avg_time <= expected_max:
            print(f"   ✅ EXPECTED: Average time within expected range")
        else:
            print(f"   ⚠️  TIMING: Average time outside expected range ({expected_min}-{expected_max}s)")

        return variance < 0.2 and expected_min <= avg_time <= expected_max

    return False

async def test_consistent_intervals():
    """Test that intervals are actually fixed at 0.1s"""
    print(f"\n🎯 Testing Fixed 0.1s Interval Implementation")
    print("=" * 50)

    app_state = SimulatedAppState()
    app_state.startup_phase = 'init'  # Start in early phase
    validator = GCPWebSocketInitializationValidator(app_state)

    # Track when we check the phase
    check_times = []
    original_hasattr = hasattr

    def mock_hasattr(obj, attr):
        if attr == 'startup_phase' and obj is app_state:
            check_times.append(time.time())
            return True
        return original_hasattr(obj, attr)

    import builtins
    builtins.hasattr = mock_hasattr

    start_time = time.time()

    # Set phase to transition after 1 second
    transition_task = app_state.simulate_phase_transition_after_delay(1.0)

    try:
        success = await validator._wait_for_startup_phase_completion(
            minimum_phase='services',
            timeout_seconds=1.5
        )

        # Analyze intervals between checks
        if len(check_times) >= 2:
            intervals = []
            for i in range(1, len(check_times)):
                interval = check_times[i] - check_times[i-1]
                intervals.append(interval)

            avg_interval = sum(intervals) / len(intervals)

            print(f"  📏 Measured intervals: {len(intervals)} samples")
            print(f"  ⏱️  Average interval: {avg_interval:.3f}s")
            print(f"  🎯 Expected: 0.100s (fixed)")

            if 0.09 <= avg_interval <= 0.11:  # Within 10ms tolerance
                print(f"  ✅ SUCCESS: Intervals are consistent with fixed 0.1s")
                return True
            else:
                print(f"  ❌ ISSUE: Intervals not matching fixed 0.1s expectation")
                return False
        else:
            print(f"  ⚠️  Not enough samples to analyze intervals")
            return False

    except Exception as e:
        print(f"  ❌ Test failed: {e}")
        return False
    finally:
        # Restore original hasattr
        builtins.hasattr = original_hasattr
        if not transition_task.done():
            transition_task.cancel()

async def main():
    """Run all tests"""
    print("Issue #1171 - WebSocket Fixed Interval Timing Validation")
    print("=" * 60)

    test1 = await test_fixed_interval_timing()
    test2 = await test_consistent_intervals()

    print(f"\n🏆 FINAL RESULTS:")
    print(f"   Timing Consistency: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"   Fixed Intervals:    {'✅ PASS' if test2 else '❌ FAIL'}")

    if test1 and test2:
        print(f"\n✅ RACE CONDITION FIX VALIDATED!")
        print(f"   - Fixed 0.1s intervals eliminate timing variance")
        print(f"   - WebSocket connections should be consistent")
        print(f"   - Issue #1171 resolved")
        return 0
    else:
        print(f"\n❌ ISSUES REMAIN:")
        print(f"   - Race condition fix may need further refinement")
        print(f"   - Issue #1171 may not be fully resolved")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        sys.exit(1)