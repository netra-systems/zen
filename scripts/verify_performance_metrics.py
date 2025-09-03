#!/usr/bin/env python
"""Verification Script for Performance Metrics Implementation

This script verifies that the performance metrics system is properly integrated
and doesn't break any existing functionality.

Business Value: Ensures reliable performance monitoring without regressions.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import asyncio
from uuid import uuid4
from datetime import datetime, timezone

def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

def test_imports():
    """Test that all imports work correctly."""
    print_section("Testing Imports")
    
    try:
        # Core performance metrics
        from netra_backend.app.core.performance_metrics import (
            EnhancedExecutionTimingCollector,
            PhaseTimer,
            TimingBreakdown,
            PerformanceMetric,
            MetricType,
            PerformanceAnalyzer
        )
        print("OK: Core performance metrics imports")
        
        # Metrics aggregator
        from netra_backend.app.monitoring.metrics_aggregator import (
            MetricsAggregator,
            AggregationWindow,
            ResourceMetrics,
            AggregatedMetrics,
            get_global_aggregator
        )
        print("OK: Metrics aggregator imports OK")
        
        # Supervisor observability
        from netra_backend.app.agents.supervisor.comprehensive_observability import (
            SupervisorObservability
        )
        print("OK: Supervisor observability imports OK")
        
        # Backward compatibility
        from netra_backend.app.agents.base.timing_collector import ExecutionTimingCollector
        print("OK: Backward compatibility imports OK")
        
        return True
    except ImportError as e:
        print(f"ERROR: Import failed: {e}")
        return False

def test_enhanced_timing_collector():
    """Test the enhanced timing collector functionality."""
    print_section("Testing Enhanced Timing Collector")
    
    from netra_backend.app.core.performance_metrics import (
        EnhancedExecutionTimingCollector,
        MetricType
    )
    
    try:
        # Create collector
        execution_id = uuid4()
        collector = EnhancedExecutionTimingCollector(
            execution_id=execution_id,
            agent_name="test_agent"
        )
        print(f"OK: Created collector for execution {execution_id}")
        
        # Test phase tracking
        collector.start_phase("initialization")
        time.sleep(0.01)
        init_duration = collector.stop_phase("initialization")
        print(f"OK: Initialization phase: {init_duration:.2f}ms")
        
        # Test parallel tasks
        collector.start_parallel_task("task1")
        collector.start_parallel_task("task2")
        time.sleep(0.01)
        collector.stop_parallel_task("task1")
        collector.stop_parallel_task("task2")
        print("OK: Parallel task tracking works")
        
        # Test TTFT
        ttft = collector.record_first_token()
        print(f"OK: Time to First Token: {ttft:.2f}ms")
        
        # Test custom metrics
        collector.add_metric(MetricType.DATABASE_QUERY, 150.5)
        print("OK: Custom metrics added")
        
        # Get breakdown
        breakdown = collector.get_breakdown()
        print(f"OK: Timing breakdown: total={breakdown.total_ms:.2f}ms, "
              f"efficiency={breakdown.calculate_efficiency():.1f}%")
        
        return True
    except Exception as e:
        print(f"ERROR: Enhanced collector test failed: {e}")
        return False

def test_metrics_aggregator():
    """Test the metrics aggregator functionality."""
    print_section("Testing Metrics Aggregator")
    
    from netra_backend.app.monitoring.metrics_aggregator import (
        get_global_aggregator,
        AggregationWindow
    )
    from netra_backend.app.core.performance_metrics import (
        PerformanceMetric,
        MetricType
    )
    
    try:
        # Get global aggregator
        aggregator = get_global_aggregator()
        print("OK: Got global aggregator instance")
        
        # Add metrics
        for i in range(10):
            metric = PerformanceMetric(
                metric_type=MetricType.LLM_PROCESSING,
                value=1000 + i * 100
            )
            aggregator.add_metric(metric)
        
        # Get aggregated stats
        stats = aggregator.get_aggregated_metrics(
            MetricType.LLM_PROCESSING,
            AggregationWindow.MINUTE
        )
        
        if stats:
            print(f"OK: Aggregated stats: count={stats.count}, "
                  f"mean={stats.mean:.2f}ms, p95={stats.p95:.2f}ms")
        else:
            print("OK: Aggregator ready (no stats yet)")
        
        # Get performance summary
        summary = aggregator.get_performance_summary()
        print(f"OK: Performance summary has {len(summary)} sections")
        
        return True
    except Exception as e:
        print(f"ERROR: Aggregator test failed: {e}")
        return False

def test_backward_compatibility():
    """Test backward compatibility with existing timing collector."""
    print_section("Testing Backward Compatibility")
    
    from netra_backend.app.agents.base.timing_collector import (
        ExecutionTimingCollector,
        TimingCategory
    )
    
    try:
        # Create old-style collector
        collector = ExecutionTimingCollector(agent_name="legacy_agent")
        
        # Start execution
        tree = collector.start_execution(str(uuid4()))
        print("OK: Started execution tree")
        
        # Use existing API
        with collector.time_operation("database_query", TimingCategory.DATABASE):
            time.sleep(0.01)
        print("OK: time_operation context manager works")
        
        # Complete execution
        tree = collector.complete_execution()
        print(f"OK: Completed execution: {tree.get_total_duration_ms():.2f}ms")
        
        # Get timing summary (old API)
        summary = collector.get_timing_summary()
        print(f"OK: Timing summary has {len(summary)} operations")
        
        return True
    except Exception as e:
        print(f"ERROR: Backward compatibility test failed: {e}")
        return False

def test_supervisor_integration():
    """Test supervisor observability integration."""
    print_section("Testing Supervisor Integration")
    
    from netra_backend.app.agents.supervisor.comprehensive_observability import (
        SupervisorObservability
    )
    from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
    from netra_backend.app.agents.state import DeepAgentState
    
    try:
        # Create observability
        observability = SupervisorObservability()
        print("OK: Created SupervisorObservability")
        
        # Create execution context
        state = DeepAgentState()
        context = ExecutionContext(
            run_id=str(uuid4()),
            agent_name="test_supervisor",
            state=state,
            user_id="test_user"
        )
        
        # Start workflow
        observability.start_workflow_trace(context)
        print("OK: Started workflow trace")
        
        # Track phases
        observability.start_phase(context.run_id, "processing")
        time.sleep(0.01)
        observability.stop_phase(context.run_id, "processing")
        print("OK: Phase tracking works")
        
        # Record TTFT
        ttft = observability.record_first_token(context.run_id)
        if ttft:
            print(f"OK: TTFT recorded: {ttft:.2f}ms")
        
        # Get timing breakdown
        breakdown = observability.get_timing_breakdown(context.run_id)
        if breakdown:
            print(f"OK: Got timing breakdown: {breakdown.total_ms:.2f}ms")
        
        # Complete workflow
        result = ExecutionResult(success=True, data={})
        observability.complete_workflow_trace(context, result)
        print("OK: Completed workflow trace")
        
        # Get performance summary
        summary = observability.get_performance_summary()
        print(f"OK: Performance summary available with {len(summary)} keys")
        
        return True
    except Exception as e:
        print(f"ERROR: Supervisor integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_async_operations():
    """Test async operation tracking."""
    print_section("Testing Async Operations")
    
    from netra_backend.app.core.performance_metrics import (
        EnhancedExecutionTimingCollector
    )
    
    try:
        collector = EnhancedExecutionTimingCollector(uuid4(), "async_agent")
        
        # Track async phase
        collector.start_phase("async_operation")
        await asyncio.sleep(0.01)
        duration = collector.stop_phase("async_operation")
        print(f"OK: Async phase tracked: {duration:.2f}ms")
        
        # Concurrent operations
        async def async_task(name, delay):
            collector.start_parallel_task(name)
            await asyncio.sleep(delay)
            return collector.stop_parallel_task(name)
        
        results = await asyncio.gather(
            async_task("async1", 0.01),
            async_task("async2", 0.02),
            async_task("async3", 0.015)
        )
        
        print(f"OK: Concurrent tasks tracked: {[f'{r:.1f}ms' for r in results]}")
        
        return True
    except Exception as e:
        print(f"ERROR: Async operations test failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("\n" + "="*60)
    print(" PERFORMANCE METRICS VERIFICATION")
    print("="*60)
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    
    results = []
    
    # Run synchronous tests
    results.append(("Imports", test_imports()))
    results.append(("Enhanced Timing Collector", test_enhanced_timing_collector()))
    results.append(("Metrics Aggregator", test_metrics_aggregator()))
    results.append(("Backward Compatibility", test_backward_compatibility()))
    results.append(("Supervisor Integration", test_supervisor_integration()))
    
    # Run async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        async_result = loop.run_until_complete(test_async_operations())
        results.append(("Async Operations", async_result))
    finally:
        loop.close()
    
    # Print summary
    print_section("VERIFICATION SUMMARY")
    
    all_passed = True
    for test_name, passed in results:
        status = "OK: PASSED" if passed else "ERROR: FAILED"
        print(f"{test_name:.<40} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print(" OK: ALL TESTS PASSED - NO BREAKING CHANGES DETECTED")
    else:
        print(" ERROR: SOME TESTS FAILED - REVIEW IMPLEMENTATION")
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())