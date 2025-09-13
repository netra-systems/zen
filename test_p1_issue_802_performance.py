#!/usr/bin/env python3
"""
P1 Issue #802 Performance Test - Legacy execution engine blocking chat performance
Test compatibility bridge overhead and removal impact.
"""

import asyncio
import time
import warnings
from contextlib import asynccontextmanager

# Suppress deprecation warnings during performance testing
warnings.simplefilter("ignore", DeprecationWarning)

from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


def measure_performance(func, iterations=10):
    """Measure function performance over multiple iterations."""
    times = []
    for _ in range(iterations):
        start_time = time.time()
        result = func()
        end_time = time.time()
        times.append(end_time - start_time)

    avg_time = sum(times) / len(times)
    return avg_time, times


async def test_legacy_compatibility_overhead():
    """Test the performance overhead of legacy compatibility bridge."""
    print("=" * 60)
    print("P1 Issue #802: Testing Legacy Compatibility Bridge Overhead")
    print("=" * 60)

    # Setup
    id_manager = UnifiedIDManager()

    # Create UserExecutionContext for modern approach
    user_context = UserExecutionContext.from_request_supervisor(
        user_id=id_manager.generate_id(IDType.USER, prefix="test"),
        thread_id=id_manager.generate_id(IDType.THREAD, prefix="test"),
        run_id=id_manager.generate_id(IDType.EXECUTION, prefix="test"),
        request_id=id_manager.generate_id(IDType.REQUEST, prefix="test"),
    )

    # Test 1: Modern constructor performance (baseline)
    print("\n1. Testing Modern Constructor Performance (Baseline)")

    def create_modern_engine():
        try:
            # Use modern constructor - should be fastest
            engine = UserExecutionEngine(
                user_context,      # Positional argument
                None,             # agent_factory mock for performance test
                None              # websocket_emitter mock for performance test
            )
            return engine
        except Exception as e:
            print(f"Modern constructor error: {e}")
            return None

    modern_avg, modern_times = measure_performance(create_modern_engine, 100)
    print(f"Modern constructor average: {modern_avg:.6f}s")
    print(f"Modern constructor times: min={min(modern_times):.6f}s, max={max(modern_times):.6f}s")

    # Test 2: Legacy compatibility bridge overhead
    print("\n2. Testing Legacy Compatibility Bridge Overhead")

    @asynccontextmanager
    async def mock_registry():
        class MockRegistry:
            def get(self, name):
                return None
        yield MockRegistry()

    @asynccontextmanager
    async def mock_websocket_bridge():
        class MockBridge:
            def notify_agent_started(self, *args, **kwargs):
                pass
        yield MockBridge()

    async def create_legacy_engine():
        try:
            async with mock_registry() as registry:
                async with mock_websocket_bridge() as bridge:
                    # Use legacy create_from_legacy - should have overhead
                    engine = await UserExecutionEngine.create_from_legacy(
                        registry, bridge, user_context
                    )
                    return engine
        except Exception as e:
            print(f"Legacy create_from_legacy error: {e}")
            return None

    # Measure legacy bridge performance
    legacy_times = []
    for _ in range(10):  # Fewer iterations for async test
        start_time = time.time()
        engine = await create_legacy_engine()
        end_time = time.time()
        legacy_times.append(end_time - start_time)

    legacy_avg = sum(legacy_times) / len(legacy_times)
    print(f"Legacy bridge average: {legacy_avg:.6f}s")
    print(f"Legacy bridge times: min={min(legacy_times):.6f}s, max={max(legacy_times):.6f}s")

    # Test 3: Legacy signature detection overhead (constructor duck typing)
    print("\n3. Testing Legacy Signature Detection Overhead")

    def create_legacy_constructor():
        try:
            # This triggers lines 523-567 compatibility bridge detection
            class MockRegistry:
                def get(self, name):
                    return None

            class MockBridge:
                def notify_agent_started(self, *args, **kwargs):
                    pass

            registry = MockRegistry()
            bridge = MockBridge()

            # This should trigger compatibility mode detection (lines 523-567)
            engine = UserExecutionEngine(registry, bridge, user_context)
            return engine
        except Exception as e:
            print(f"Legacy constructor error: {e}")
            return None

    legacy_construct_avg, legacy_construct_times = measure_performance(create_legacy_constructor, 100)
    print(f"Legacy constructor detection average: {legacy_construct_avg:.6f}s")
    print(f"Legacy constructor detection times: min={min(legacy_construct_times):.6f}s, max={max(legacy_construct_times):.6f}s")

    # Calculate performance impact
    print("\n" + "=" * 60)
    print("PERFORMANCE ANALYSIS RESULTS")
    print("=" * 60)

    if modern_avg and legacy_construct_avg:
        overhead_factor = legacy_construct_avg / modern_avg
        overhead_ms = (legacy_construct_avg - modern_avg) * 1000
        print(f"Legacy signature detection overhead: {overhead_factor:.2f}x slower")
        print(f"Absolute overhead: {overhead_ms:.3f}ms per engine creation")

    if modern_avg and legacy_avg:
        bridge_overhead_factor = legacy_avg / modern_avg
        bridge_overhead_ms = (legacy_avg - modern_avg) * 1000
        print(f"Legacy bridge creation overhead: {bridge_overhead_factor:.2f}x slower")
        print(f"Absolute bridge overhead: {bridge_overhead_ms:.3f}ms per engine creation")

    # Business impact calculation
    print("\n" + "=" * 60)
    print("BUSINESS IMPACT ASSESSMENT")
    print("=" * 60)

    if legacy_construct_avg and modern_avg:
        # Assume 1000 chat messages per hour (busy system)
        messages_per_hour = 1000
        total_overhead_ms = overhead_ms * messages_per_hour
        total_overhead_seconds = total_overhead_ms / 1000

        print(f"For {messages_per_hour} chat messages/hour:")
        print(f"- Total compatibility overhead: {total_overhead_seconds:.2f}s/hour")
        print(f"- Performance degradation: {overhead_factor:.1f}x slower chat responses")
        print(f"- User impact: Each chat response delayed by {overhead_ms:.3f}ms")

        if overhead_factor > 1.5:
            print("🔴 CRITICAL: Significant performance impact detected!")
            print("   Chat performance degraded by > 50% due to compatibility bridge")
        elif overhead_factor > 1.2:
            print("🟡 WARNING: Noticeable performance impact detected")
            print("   Chat performance degraded due to compatibility bridge")
        else:
            print("🟢 ACCEPTABLE: Minimal performance impact")

    return {
        'modern_avg': modern_avg,
        'legacy_avg': legacy_avg,
        'legacy_construct_avg': legacy_construct_avg,
        'overhead_factor': overhead_factor if 'overhead_factor' in locals() else 0,
        'overhead_ms': overhead_ms if 'overhead_ms' in locals() else 0
    }


if __name__ == "__main__":
    results = asyncio.run(test_legacy_compatibility_overhead())

    print("\n" + "=" * 60)
    print("NEXT STEPS FOR P1 ISSUE #802")
    print("=" * 60)
    print("1. Remove lines 523-567 legacy signature detection")
    print("2. Remove create_from_legacy compatibility bridge")
    print("3. Update all imports to use modern constructor")
    print("4. Re-run performance test to validate improvement")
    print("5. Deploy to staging and validate chat performance")