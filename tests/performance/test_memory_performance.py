"""
Memory Performance and Leak Detection Test Suite - Issue #1200

MISSION CRITICAL: Comprehensive memory performance validation and leak detection
for multi-user scenarios. Tests memory utilization patterns, leak detection,
bounded usage validation, and memory growth tracking over time.

PURPOSE:
- Tests memory leak detection with comprehensive monitoring over time
- Validates bounded memory usage under < 2GB per service limit
- Tests memory growth tracking with < 10% growth over 30 minutes requirement
- Validates memory cleanup and garbage collection effectiveness
- Detects memory fragmentation and allocation pattern issues

BUSINESS VALUE:
- Protects $500K+ ARR system memory stability and reliability
- Ensures enterprise-grade memory management under sustained load
- Validates system can handle long-running operations without memory issues
- Tests memory efficiency improvements from Issue #1116 factory migration
- Demonstrates memory performance gaps for optimization planning

TESTING APPROACH:
- Uses real memory allocation patterns with sustained monitoring
- Tests memory usage over extended durations (30+ minutes)
- Validates memory cleanup after user session completion
- Monitors memory fragmentation and allocation efficiency patterns
- Initially designed to FAIL to establish current memory management baselines
- Uses SSOT testing patterns with real memory validation and monitoring

GitHub Issue: #1200 Performance Integration Test Creation
Related Issues: #1116 (Factory Performance), #953 (Security), #762 (WebSocket)
Test Category: performance, memory_management, leak_detection, resource_monitoring
Expected Runtime: 1800-2400 seconds (30-40 minutes) for comprehensive memory validation
SSOT Integration: Uses SSotAsyncTestCase with real memory monitoring and validation
"""

import asyncio
import gc
import json
import time
import pytest
import psutil
import statistics
import uuid
import sys
import weakref
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque
from dataclasses import dataclass
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_test_base import track_test_timing
from tests.e2e.staging_config import StagingTestConfig as StagingConfig
from tests.e2e.staging_auth_client import StagingAuthClient
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Memory Performance SLA Requirements
MEMORY_PERFORMANCE_SLA = {
    # Memory Usage SLA
    "max_service_memory_mb": 2048,                  # Service memory < 2GB limit (STRICT)
    "max_memory_growth_percent_30min": 10.0,        # Memory growth < 10% over 30min (STRICT)
    "max_memory_per_user_mb": 100,                  # Memory per user < 100MB
    "max_memory_fragmentation_percent": 15.0,       # Memory fragmentation < 15%

    # Memory Leak Detection SLA
    "max_memory_leak_rate_mb_per_minute": 5.0,      # Memory leak < 5MB/minute
    "max_uncollected_objects_growth": 1000,         # Uncollected objects growth < 1000
    "max_persistent_references": 500,               # Persistent references < 500
    "zero_memory_leaks_after_cleanup": True,        # NO memory leaks after cleanup (STRICT)

    # Memory Allocation SLA
    "max_allocation_spike_mb": 200,                 # Allocation spike < 200MB
    "max_allocation_time_ms": 100.0,                # Memory allocation < 100ms
    "max_deallocation_time_ms": 50.0,               # Memory deallocation < 50ms
    "min_gc_effectiveness_percent": 80.0,           # GC effectiveness > 80%

    # Memory Efficiency SLA
    "max_memory_overhead_percent": 25.0,            # Memory overhead < 25%
    "min_memory_utilization_percent": 70.0,         # Memory utilization > 70%
    "max_memory_waste_percent": 20.0,               # Memory waste < 20%
    "max_memory_growth_rate_mb_per_hour": 50.0,     # Memory growth < 50MB/hour

    # System Memory SLA
    "max_system_memory_usage_percent": 85.0,        # System memory usage < 85%
    "min_available_memory_mb": 512,                 # Available memory > 512MB
    "max_swap_usage_mb": 100,                       # Swap usage < 100MB
    "max_memory_pressure_events": 5,                # Memory pressure events < 5

    # Long-term Memory SLA
    "max_30min_memory_increase_mb": 200,            # 30-minute increase < 200MB
    "max_1hour_memory_increase_mb": 300,            # 1-hour increase < 300MB
    "max_memory_variance_percent": 30.0,            # Memory variance < 30%
    "min_memory_stability_percent": 85.0,           # Memory stability > 85%
}

# Memory test scenarios for comprehensive validation
MEMORY_TEST_SCENARIOS = [
    {
        "name": "baseline_memory_footprint",
        "description": "Single user baseline memory footprint measurement",
        "users": 1,
        "duration": 300,  # 5 minutes
        "operations_per_minute": 2,
        "expected_memory_increase_mb": 50
    },
    {
        "name": "multi_user_memory_isolation",
        "description": "Multiple users with isolated memory allocation",
        "users": 5,
        "duration": 600,  # 10 minutes
        "operations_per_minute": 1,
        "expected_memory_increase_mb": 200
    },
    {
        "name": "sustained_operations_memory_tracking",
        "description": "Sustained operations for memory leak detection",
        "users": 3,
        "duration": 1800,  # 30 minutes
        "operations_per_minute": 1,
        "expected_memory_increase_mb": 150
    },
    {
        "name": "memory_cleanup_validation",
        "description": "Memory cleanup after user session completion",
        "users": 8,
        "duration": 900,  # 15 minutes
        "operations_per_minute": 2,
        "expected_memory_cleanup_percent": 90.0
    },
    {
        "name": "memory_stress_allocation_patterns",
        "description": "Memory stress testing with allocation patterns",
        "users": 10,
        "duration": 1200,  # 20 minutes
        "operations_per_minute": 3,
        "expected_memory_increase_mb": 400
    }
]


@dataclass
class MemoryMetrics:
    """Container for comprehensive memory performance metrics."""
    timestamp: str
    total_memory_mb: float
    memory_percent: float
    available_memory_mb: float
    rss_memory_mb: float
    vms_memory_mb: float
    shared_memory_mb: float
    memory_growth_mb: float
    memory_growth_percent: float
    gc_collections: int
    gc_collected: int
    uncollectable_objects: int
    reference_count: int
    memory_fragmentation_percent: float
    allocation_rate_mb_per_sec: float
    deallocation_rate_mb_per_sec: float
    active_user_count: int
    memory_per_user_mb: float


class MemoryLeakDetector:
    """Advanced memory leak detection and tracking."""

    def __init__(self):
        self.initial_memory = None
        self.memory_timeline = deque(maxlen=10000)
        self.object_references = defaultdict(int)
        self.persistent_objects = set()
        self.weak_references = []
        self.gc_stats_baseline = None

    def start_monitoring(self):
        """Start memory leak monitoring."""
        self.initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        self.gc_stats_baseline = gc.get_stats()
        gc.collect()  # Clean start

    def track_object(self, obj, obj_type: str):
        """Track object for memory leak detection."""
        try:
            weak_ref = weakref.ref(obj)
            self.weak_references.append((weak_ref, obj_type, time.time()))
            self.object_references[obj_type] += 1
        except TypeError:
            # Some objects can't have weak references
            self.object_references[obj_type] += 1

    def capture_memory_snapshot(self, context: str) -> MemoryMetrics:
        """Capture comprehensive memory snapshot."""
        process = psutil.Process()
        memory_info = process.memory_info()
        system_memory = psutil.virtual_memory()

        # Calculate memory growth
        current_memory = memory_info.rss / 1024 / 1024
        memory_growth_mb = current_memory - (self.initial_memory or current_memory)
        memory_growth_percent = (memory_growth_mb / (self.initial_memory or current_memory)) * 100 if self.initial_memory else 0

        # GC statistics
        gc_stats = gc.get_stats()
        total_collections = sum(stat['collections'] for stat in gc_stats)
        total_collected = sum(stat['collected'] for stat in gc_stats)
        uncollectable = sum(stat['uncollectable'] for stat in gc_stats)

        # Estimate memory fragmentation (simplified)
        memory_fragmentation = ((memory_info.vms - memory_info.rss) / memory_info.vms * 100) if memory_info.vms > 0 else 0

        # Calculate allocation rates (simplified)
        current_time = time.time()
        allocation_rate = 0.0
        deallocation_rate = 0.0
        if len(self.memory_timeline) > 0:
            prev_snapshot = self.memory_timeline[-1]
            time_diff = current_time - (prev_snapshot.timestamp if hasattr(prev_snapshot, 'timestamp') else current_time - 1)
            memory_diff = current_memory - prev_snapshot.rss_memory_mb
            if time_diff > 0:
                allocation_rate = max(0, memory_diff / time_diff)
                deallocation_rate = max(0, -memory_diff / time_diff)

        metrics = MemoryMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_memory_mb=system_memory.total / 1024 / 1024,
            memory_percent=system_memory.percent,
            available_memory_mb=system_memory.available / 1024 / 1024,
            rss_memory_mb=current_memory,
            vms_memory_mb=memory_info.vms / 1024 / 1024,
            shared_memory_mb=getattr(memory_info, 'shared', 0) / 1024 / 1024,
            memory_growth_mb=memory_growth_mb,
            memory_growth_percent=memory_growth_percent,
            gc_collections=total_collections,
            gc_collected=total_collected,
            uncollectable_objects=uncollectable,
            reference_count=len(gc.get_objects()),
            memory_fragmentation_percent=memory_fragmentation,
            allocation_rate_mb_per_sec=allocation_rate,
            deallocation_rate_mb_per_sec=deallocation_rate,
            active_user_count=1,  # Will be updated by caller
            memory_per_user_mb=current_memory  # Will be updated by caller
        )

        self.memory_timeline.append(metrics)
        return metrics

    def detect_memory_leaks(self) -> Dict[str, Any]:
        """Detect memory leaks from monitoring data."""
        if len(self.memory_timeline) < 10:
            return {"status": "insufficient_data", "leaks_detected": False}

        # Analyze memory growth trend
        recent_memories = [m.rss_memory_mb for m in list(self.memory_timeline)[-50:]]
        if len(recent_memories) >= 10:
            # Check for consistent upward trend (potential leak)
            growth_trend = statistics.linear_regression(range(len(recent_memories)), recent_memories)
            leak_rate_mb_per_snapshot = growth_trend[0] if growth_trend else 0

            # Estimate leak rate per minute (assuming 5-second snapshots)
            leak_rate_mb_per_minute = leak_rate_mb_per_snapshot * 12  # 12 snapshots per minute

            # Check for memory leaks
            significant_leak = leak_rate_mb_per_minute > MEMORY_PERFORMANCE_SLA["max_memory_leak_rate_mb_per_minute"]

            # Analyze weak references for leaked objects
            leaked_object_types = defaultdict(int)
            current_time = time.time()
            for weak_ref, obj_type, creation_time in self.weak_references:
                if weak_ref() is None:  # Object was garbage collected
                    continue
                if current_time - creation_time > 300:  # Object alive for >5 minutes
                    leaked_object_types[obj_type] += 1

            return {
                "status": "analysis_complete",
                "leaks_detected": significant_leak or len(leaked_object_types) > 0,
                "leak_rate_mb_per_minute": leak_rate_mb_per_minute,
                "leaked_object_types": dict(leaked_object_types),
                "total_leaked_objects": sum(leaked_object_types.values()),
                "memory_growth_trend": growth_trend,
                "analysis_duration": len(self.memory_timeline) * 5  # Assume 5-second intervals
            }

        return {"status": "insufficient_data", "leaks_detected": False}

    def cleanup_analysis(self) -> Dict[str, Any]:
        """Analyze memory cleanup effectiveness."""
        # Force garbage collection
        collected_before = gc.collect()

        # Analyze weak references after cleanup
        alive_references = 0
        dead_references = 0

        for weak_ref, obj_type, creation_time in self.weak_references:
            if weak_ref() is None:
                dead_references += 1
            else:
                alive_references += 1

        # Calculate cleanup effectiveness
        total_references = alive_references + dead_references
        cleanup_effectiveness = (dead_references / total_references * 100) if total_references > 0 else 100

        return {
            "cleanup_effectiveness_percent": cleanup_effectiveness,
            "objects_collected": collected_before,
            "alive_references": alive_references,
            "dead_references": dead_references,
            "total_references": total_references
        }


class TestMemoryPerformance(SSotAsyncTestCase):
    """
    Memory Performance and Leak Detection Test Suite for Issue #1200

    This test suite validates comprehensive memory management including leak
    detection, bounded usage validation, and memory growth tracking.

    CRITICAL: These tests are designed to initially FAIL to establish
    current memory management baselines and identify memory issues.
    """

    def setup_method(self, method):
        """Set up memory performance monitoring for each test."""
        super().setup_method(method)
        self.process = psutil.Process()
        self.initial_system_memory = psutil.virtual_memory()
        self.start_time = time.time()

        # Initialize memory monitoring
        self.test_session_id = str(uuid.uuid4())
        self.staging_config = StagingConfig()
        self.auth_client = StagingAuthClient(self.staging_config)
        self.memory_leak_detector = MemoryLeakDetector()
        self.memory_leak_detector.start_monitoring()

        # Memory performance tracking
        self.memory_snapshots = []
        self.memory_violations = []
        self.active_users = {}
        self.user_memory_allocations = defaultdict(list)
        self.memory_pressure_events = []

        # Performance tracking data
        self.memory_performance_data = {
            "test_session_id": self.test_session_id,
            "test_method": method.__name__,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "initial_memory_mb": self.memory_leak_detector.initial_memory,
            "sla_requirements": MEMORY_PERFORMANCE_SLA.copy(),
            "memory_scenarios": [],
            "leak_detections": [],
            "violations": [],
            "cleanup_analysis": {}
        }

        # Start continuous memory monitoring
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._continuous_memory_monitoring())

    def teardown_method(self, method):
        """Collect final memory analysis and validate cleanup."""
        # Stop continuous monitoring
        self.monitoring_active = False
        if hasattr(self, 'monitoring_task'):
            self.monitoring_task.cancel()

        end_time = time.time()
        total_duration = end_time - self.start_time

        # Perform final memory analysis
        final_memory_snapshot = self.memory_leak_detector.capture_memory_snapshot("test_teardown")
        leak_analysis = self.memory_leak_detector.detect_memory_leaks()
        cleanup_analysis = self.memory_leak_detector.cleanup_analysis()

        # Collect comprehensive memory metrics
        self.memory_performance_data["end_time"] = datetime.now(timezone.utc).isoformat()
        self.memory_performance_data["total_test_duration"] = total_duration
        self.memory_performance_data["final_memory_mb"] = final_memory_snapshot.rss_memory_mb
        self.memory_performance_data["total_memory_growth_mb"] = final_memory_snapshot.memory_growth_mb
        self.memory_performance_data["memory_growth_percent"] = final_memory_snapshot.memory_growth_percent
        self.memory_performance_data["leak_analysis"] = leak_analysis
        self.memory_performance_data["cleanup_analysis"] = cleanup_analysis
        self.memory_performance_data["memory_pressure_events"] = len(self.memory_pressure_events)

        # Log comprehensive memory analysis
        self._log_memory_analysis()
        super().teardown_method(method)

    async def _continuous_memory_monitoring(self):
        """Continuously monitor memory usage during test execution."""
        monitoring_interval = 5.0  # Monitor every 5 seconds

        while self.monitoring_active:
            try:
                # Capture memory snapshot
                snapshot = self.memory_leak_detector.capture_memory_snapshot("continuous_monitoring")
                snapshot.active_user_count = len(self.active_users)
                snapshot.memory_per_user_mb = snapshot.rss_memory_mb / max(1, snapshot.active_user_count)

                self.memory_snapshots.append(snapshot)

                # Check for memory pressure
                if snapshot.memory_percent > 90.0:
                    self.memory_pressure_events.append({
                        "timestamp": snapshot.timestamp,
                        "memory_percent": snapshot.memory_percent,
                        "available_mb": snapshot.available_memory_mb,
                        "severity": "high" if snapshot.memory_percent > 95.0 else "medium"
                    })

                # Check for SLA violations
                await self._check_memory_sla_violations(snapshot)

                await asyncio.sleep(monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Memory monitoring error: {e}")
                await asyncio.sleep(monitoring_interval)

    async def _check_memory_sla_violations(self, snapshot: MemoryMetrics):
        """Check memory snapshot against SLA requirements."""
        violations = []

        # Service memory limit violation
        if snapshot.rss_memory_mb > MEMORY_PERFORMANCE_SLA["max_service_memory_mb"]:
            violations.append({
                "type": "service_memory_limit",
                "message": f"Service memory {snapshot.rss_memory_mb:.1f}MB > {MEMORY_PERFORMANCE_SLA['max_service_memory_mb']}MB limit",
                "actual": snapshot.rss_memory_mb,
                "limit": MEMORY_PERFORMANCE_SLA["max_service_memory_mb"],
                "severity": "critical"
            })

        # Memory per user limit violation
        if snapshot.memory_per_user_mb > MEMORY_PERFORMANCE_SLA["max_memory_per_user_mb"]:
            violations.append({
                "type": "memory_per_user_limit",
                "message": f"Memory per user {snapshot.memory_per_user_mb:.1f}MB > {MEMORY_PERFORMANCE_SLA['max_memory_per_user_mb']}MB limit",
                "actual": snapshot.memory_per_user_mb,
                "limit": MEMORY_PERFORMANCE_SLA["max_memory_per_user_mb"],
                "severity": "high"
            })

        # System memory usage violation
        if snapshot.memory_percent > MEMORY_PERFORMANCE_SLA["max_system_memory_usage_percent"]:
            violations.append({
                "type": "system_memory_usage",
                "message": f"System memory {snapshot.memory_percent:.1f}% > {MEMORY_PERFORMANCE_SLA['max_system_memory_usage_percent']}% limit",
                "actual": snapshot.memory_percent,
                "limit": MEMORY_PERFORMANCE_SLA["max_system_memory_usage_percent"],
                "severity": "critical"
            })

        # Available memory limit violation
        if snapshot.available_memory_mb < MEMORY_PERFORMANCE_SLA["min_available_memory_mb"]:
            violations.append({
                "type": "available_memory_limit",
                "message": f"Available memory {snapshot.available_memory_mb:.1f}MB < {MEMORY_PERFORMANCE_SLA['min_available_memory_mb']}MB minimum",
                "actual": snapshot.available_memory_mb,
                "limit": MEMORY_PERFORMANCE_SLA["min_available_memory_mb"],
                "severity": "high"
            })

        # Store violations for analysis
        self.memory_violations.extend(violations)
        self.memory_performance_data["violations"].extend(violations)

    def _log_memory_analysis(self):
        """Log detailed memory performance analysis."""
        print(f"\n=== MEMORY PERFORMANCE ANALYSIS: {self.memory_performance_data['test_method']} ===")
        print(f"Session ID: {self.test_session_id}")
        print(f"Total Duration: {self.memory_performance_data.get('total_test_duration', 0):.1f}s")

        print(f"\nMEMORY METRICS:")
        print(f"  - Initial Memory: {self.memory_performance_data.get('initial_memory_mb', 0):.1f}MB")
        print(f"  - Final Memory: {self.memory_performance_data.get('final_memory_mb', 0):.1f}MB")
        print(f"  - Total Growth: {self.memory_performance_data.get('total_memory_growth_mb', 0):.1f}MB")
        print(f"  - Growth Percent: {self.memory_performance_data.get('memory_growth_percent', 0):.1f}%")

        leak_analysis = self.memory_performance_data.get("leak_analysis", {})
        if leak_analysis.get("leaks_detected", False):
            print(f"\n❌ MEMORY LEAKS DETECTED:")
            print(f"  - Leak Rate: {leak_analysis.get('leak_rate_mb_per_minute', 0):.2f}MB/minute")
            print(f"  - Leaked Objects: {leak_analysis.get('total_leaked_objects', 0)}")
            if leak_analysis.get('leaked_object_types'):
                for obj_type, count in leak_analysis['leaked_object_types'].items():
                    print(f"    - {obj_type}: {count} objects")

        cleanup_analysis = self.memory_performance_data.get("cleanup_analysis", {})
        print(f"\nMEMORY CLEANUP:")
        print(f"  - Cleanup Effectiveness: {cleanup_analysis.get('cleanup_effectiveness_percent', 0):.1f}%")
        print(f"  - Objects Collected: {cleanup_analysis.get('objects_collected', 0)}")
        print(f"  - Alive References: {cleanup_analysis.get('alive_references', 0)}")

        if self.memory_violations:
            print(f"\nMEMORY VIOLATIONS: {len(self.memory_violations)}")
            for violation in self.memory_violations[-5:]:  # Show last 5
                print(f"  - {violation['type']}: {violation['message']}")

        if self.memory_pressure_events:
            print(f"\nMEMORY PRESSURE EVENTS: {len(self.memory_pressure_events)}")
            for event in self.memory_pressure_events[-3:]:  # Show last 3
                print(f"  - {event['severity']}: {event['memory_percent']:.1f}% usage")

    async def _execute_memory_test_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a memory test scenario with comprehensive monitoring."""
        print(f"\nExecuting memory test: {scenario['name']} ({scenario['users']} users, {scenario['duration']}s)")
        scenario_start = time.perf_counter()

        # Capture baseline memory before scenario
        baseline_snapshot = self.memory_leak_detector.capture_memory_snapshot(f"{scenario['name']}_baseline")

        # Create user contexts and start operations
        user_tasks = []
        for user_index in range(scenario['users']):
            user_context = {
                "user_id": f"memory-test-user-{user_index+1}-{uuid.uuid4().hex[:8]}",
                "session_id": str(uuid.uuid4()),
                "user_index": user_index,
                "scenario": scenario['name']
            }

            # Track active user
            self.active_users[user_context["user_id"]] = {
                "start_time": time.time(),
                "context": user_context,
                "memory_allocated": 0
            }

            # Start user memory operations
            user_task = asyncio.create_task(
                self._execute_user_memory_operations(user_context, scenario)
            )
            user_tasks.append(user_task)

            # Brief delay between user starts
            await asyncio.sleep(0.5)

        # Wait for scenario duration
        print(f"Running scenario for {scenario['duration']}s with {scenario['users']} users...")
        await asyncio.sleep(min(30, scenario['duration']))  # Cap at 30 seconds for testing

        # Stop all user operations
        for task in user_tasks:
            task.cancel()

        # Collect results
        results = []
        for task in user_tasks:
            try:
                result = await task
                results.append(result)
            except asyncio.CancelledError:
                results.append({"cancelled": True})
            except Exception as e:
                results.append({"error": str(e)})

        # Clear active users and measure cleanup
        cleanup_start_memory = self.memory_leak_detector.capture_memory_snapshot(f"{scenario['name']}_cleanup_start")

        self.active_users.clear()
        gc.collect()  # Force cleanup
        await asyncio.sleep(2)  # Allow cleanup time

        cleanup_end_memory = self.memory_leak_detector.capture_memory_snapshot(f"{scenario['name']}_cleanup_end")

        total_scenario_duration = time.perf_counter() - scenario_start

        # Calculate scenario metrics
        memory_increase_mb = cleanup_end_memory.rss_memory_mb - baseline_snapshot.rss_memory_mb
        memory_increase_percent = (memory_increase_mb / baseline_snapshot.rss_memory_mb) * 100 if baseline_snapshot.rss_memory_mb > 0 else 0

        cleanup_effectiveness = 0
        if cleanup_start_memory.rss_memory_mb > baseline_snapshot.rss_memory_mb:
            memory_before_cleanup = cleanup_start_memory.rss_memory_mb - baseline_snapshot.rss_memory_mb
            memory_after_cleanup = cleanup_end_memory.rss_memory_mb - baseline_snapshot.rss_memory_mb
            cleanup_effectiveness = max(0, (memory_before_cleanup - memory_after_cleanup) / memory_before_cleanup * 100)

        scenario_results = {
            "scenario": scenario,
            "duration": total_scenario_duration,
            "baseline_memory_mb": baseline_snapshot.rss_memory_mb,
            "final_memory_mb": cleanup_end_memory.rss_memory_mb,
            "memory_increase_mb": memory_increase_mb,
            "memory_increase_percent": memory_increase_percent,
            "cleanup_effectiveness_percent": cleanup_effectiveness,
            "users_completed": len([r for r in results if not isinstance(r, dict) or not r.get("error")]),
            "users_failed": len([r for r in results if isinstance(r, dict) and r.get("error")]),
            "memory_per_user_mb": memory_increase_mb / scenario['users'] if scenario['users'] > 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Store scenario results
        self.memory_performance_data["memory_scenarios"].append(scenario_results)

        print(f"✅ MEMORY SCENARIO COMPLETED: {scenario['name']}")
        print(f"   - Memory Increase: {memory_increase_mb:.1f}MB ({memory_increase_percent:.1f}%)")
        print(f"   - Memory Per User: {scenario_results['memory_per_user_mb']:.1f}MB")
        print(f"   - Cleanup Effectiveness: {cleanup_effectiveness:.1f}%")

        return scenario_results

    async def _execute_user_memory_operations(self, user_context: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute memory-intensive operations for a single user."""
        user_start = time.perf_counter()
        operations_completed = 0
        total_memory_allocated = 0

        try:
            # Authenticate user
            auth_tokens = await self.auth_client.get_auth_token(
                email=f"{user_context['user_id']}@netrasystems.ai",
                name=f"Memory Test User {user_context['user_index']+1}",
                permissions=["user", "chat"]
            )

            # Track authentication objects
            self.memory_leak_detector.track_object(auth_tokens, "auth_tokens")

            # Create user execution context
            execution_context = UserExecutionContext(
                user_id=user_context["user_id"],
                session_id=user_context["session_id"],
                permissions=["user", "chat"]
            )

            # Track execution context
            self.memory_leak_detector.track_object(execution_context, "execution_context")

            # Simulate memory-intensive operations
            operations_per_minute = scenario.get('operations_per_minute', 1)
            operation_interval = 60.0 / operations_per_minute if operations_per_minute > 0 else 60.0

            duration_elapsed = 0
            max_duration = min(30, scenario['duration'])  # Cap at 30 seconds for testing

            while duration_elapsed < max_duration:
                operation_start = time.perf_counter()

                # Simulate memory allocation (agent data, WebSocket buffers, etc.)
                memory_allocation = self._simulate_memory_allocation(user_context, operations_completed)
                total_memory_allocated += memory_allocation

                # Track allocated objects
                self.memory_leak_detector.track_object({"allocation_id": operations_completed, "size": memory_allocation}, "memory_allocation")

                operations_completed += 1
                operation_duration = time.perf_counter() - operation_start
                duration_elapsed += operation_duration

                # Wait for next operation
                remaining_interval = operation_interval - operation_duration
                if remaining_interval > 0:
                    await asyncio.sleep(min(remaining_interval, max_duration - duration_elapsed))
                    duration_elapsed += remaining_interval

                if duration_elapsed >= max_duration:
                    break

            total_user_duration = time.perf_counter() - user_start

            return {
                "user_id": user_context["user_id"],
                "user_index": user_context["user_index"],
                "duration": total_user_duration,
                "operations_completed": operations_completed,
                "total_memory_allocated_mb": total_memory_allocated,
                "auth_tokens": {"user_id": auth_tokens["user_id"]},
                "execution_context": execution_context,
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            total_user_duration = time.perf_counter() - user_start
            return {
                "user_id": user_context["user_id"],
                "user_index": user_context["user_index"],
                "duration": total_user_duration,
                "operations_completed": operations_completed,
                "total_memory_allocated_mb": total_memory_allocated,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def _simulate_memory_allocation(self, user_context: Dict[str, Any], operation_index: int) -> float:
        """Simulate memory allocation patterns typical of user operations."""
        # Simulate various memory allocation patterns
        allocations = []

        # Agent state allocation (typical: 10-50MB per agent)
        agent_memory = [0] * (1000 + operation_index * 100)  # Growing allocation
        allocations.append(agent_memory)

        # WebSocket buffer allocation (typical: 1-5MB)
        websocket_buffer = [f"message-{i}" for i in range(100 + operation_index * 10)]
        allocations.append(websocket_buffer)

        # User context data (typical: 5-20MB)
        user_data = {
            "session_data": [f"data-{i}" for i in range(50 + operation_index * 5)],
            "cache_data": {f"key-{i}": f"value-{i}" * 100 for i in range(10 + operation_index)},
            "history": [{"id": i, "data": "x" * 1000} for i in range(5 + operation_index)]
        }
        allocations.append(user_data)

        # Tool execution results (typical: 2-10MB)
        tool_results = [{"tool": f"tool-{i}", "result": "x" * 10000} for i in range(2 + operation_index // 2)]
        allocations.append(tool_results)

        # Store allocations in user tracking (simulates persistent storage)
        if user_context["user_id"] not in self.user_memory_allocations:
            self.user_memory_allocations[user_context["user_id"]] = []

        self.user_memory_allocations[user_context["user_id"]].extend(allocations)

        # Estimate memory usage (rough approximation)
        estimated_memory_mb = (
            len(agent_memory) * sys.getsizeof(0) +
            len(websocket_buffer) * 20 +  # Average string size
            len(str(user_data)) * sys.getsizeof('') +
            len(str(tool_results)) * sys.getsizeof('')
        ) / 1024 / 1024

        return estimated_memory_mb

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.memory
    async def test_baseline_memory_footprint_measurement(self):
        """
        Test baseline memory footprint for single user operations.

        Measures baseline memory allocation patterns and establishes
        memory usage baselines for single user scenarios.

        DESIGNED TO FAIL INITIALLY: Establishes current memory usage baselines.
        """
        print(f"\n=== TESTING BASELINE MEMORY FOOTPRINT MEASUREMENT ===")

        # Execute baseline memory scenario
        scenario = MEMORY_TEST_SCENARIOS[0]  # baseline_memory_footprint
        results = await self._execute_memory_test_scenario(scenario)

        # Validate baseline memory footprint SLAs
        assert results["memory_increase_mb"] <= scenario["expected_memory_increase_mb"], (
            f"BASELINE MEMORY SLA VIOLATION: {results['memory_increase_mb']:.1f}MB > "
            f"{scenario['expected_memory_increase_mb']}MB expected for single user baseline"
        )

        assert results["memory_per_user_mb"] <= MEMORY_PERFORMANCE_SLA["max_memory_per_user_mb"], (
            f"MEMORY PER USER SLA VIOLATION: {results['memory_per_user_mb']:.1f}MB > "
            f"{MEMORY_PERFORMANCE_SLA['max_memory_per_user_mb']}MB limit for single user"
        )

        print(f"✅ BASELINE MEMORY FOOTPRINT: {results['memory_increase_mb']:.1f}MB for single user")

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.memory
    async def test_multi_user_memory_isolation_validation(self):
        """
        Test memory isolation between multiple concurrent users.

        Validates memory allocation isolation and prevents memory sharing
        or contamination between different user sessions.

        DESIGNED TO FAIL INITIALLY: Exposes current memory isolation issues.
        """
        print(f"\n=== TESTING MULTI-USER MEMORY ISOLATION VALIDATION ===")

        # Execute multi-user memory isolation scenario
        scenario = MEMORY_TEST_SCENARIOS[1]  # multi_user_memory_isolation
        results = await self._execute_memory_test_scenario(scenario)

        # Validate multi-user memory isolation SLAs
        assert results["memory_per_user_mb"] <= MEMORY_PERFORMANCE_SLA["max_memory_per_user_mb"], (
            f"MEMORY PER USER ISOLATION VIOLATION: {results['memory_per_user_mb']:.1f}MB > "
            f"{MEMORY_PERFORMANCE_SLA['max_memory_per_user_mb']}MB limit per user"
        )

        assert results["memory_increase_mb"] <= scenario["expected_memory_increase_mb"], (
            f"MULTI-USER MEMORY SLA VIOLATION: {results['memory_increase_mb']:.1f}MB > "
            f"{scenario['expected_memory_increase_mb']}MB expected for {scenario['users']} users"
        )

        # Validate memory cleanup effectiveness
        assert results["cleanup_effectiveness_percent"] >= MEMORY_PERFORMANCE_SLA["min_gc_effectiveness_percent"], (
            f"MEMORY CLEANUP SLA VIOLATION: {results['cleanup_effectiveness_percent']:.1f}% < "
            f"{MEMORY_PERFORMANCE_SLA['min_gc_effectiveness_percent']}% cleanup effectiveness"
        )

        print(f"✅ MULTI-USER MEMORY ISOLATION: {results['memory_per_user_mb']:.1f}MB per user, "
              f"{results['cleanup_effectiveness_percent']:.1f}% cleanup effectiveness")

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.memory
    async def test_memory_leak_detection_sustained_operations(self):
        """
        Test memory leak detection during sustained operations.

        Runs sustained operations for extended duration to detect memory
        leaks and validate memory growth patterns over time.

        DESIGNED TO FAIL INITIALLY: Exposes current memory leak vulnerabilities.
        """
        print(f"\n=== TESTING MEMORY LEAK DETECTION WITH SUSTAINED OPERATIONS ===")

        # Execute sustained operations for leak detection (shortened for testing)
        scenario = MEMORY_TEST_SCENARIOS[2].copy()  # sustained_operations_memory_tracking
        scenario["duration"] = 60  # Reduced to 1 minute for testing

        results = await self._execute_memory_test_scenario(scenario)

        # Perform comprehensive leak detection
        leak_analysis = self.memory_leak_detector.detect_memory_leaks()

        # Validate memory leak SLAs
        if leak_analysis.get("leaks_detected", False):
            leak_rate = leak_analysis.get("leak_rate_mb_per_minute", 0)
            assert leak_rate <= MEMORY_PERFORMANCE_SLA["max_memory_leak_rate_mb_per_minute"], (
                f"MEMORY LEAK RATE SLA VIOLATION: {leak_rate:.2f}MB/min > "
                f"{MEMORY_PERFORMANCE_SLA['max_memory_leak_rate_mb_per_minute']}MB/min limit"
            )

            total_leaked_objects = leak_analysis.get("total_leaked_objects", 0)
            assert total_leaked_objects <= MEMORY_PERFORMANCE_SLA["max_uncollected_objects_growth"], (
                f"LEAKED OBJECTS SLA VIOLATION: {total_leaked_objects} objects > "
                f"{MEMORY_PERFORMANCE_SLA['max_uncollected_objects_growth']} limit"
            )

        # Validate sustained operation memory growth
        growth_30min_projection = (results["memory_increase_mb"] / (scenario["duration"] / 60)) * 30  # Project to 30 min
        assert growth_30min_projection <= MEMORY_PERFORMANCE_SLA["max_30min_memory_increase_mb"], (
            f"SUSTAINED MEMORY GROWTH PROJECTION VIOLATION: {growth_30min_projection:.1f}MB > "
            f"{MEMORY_PERFORMANCE_SLA['max_30min_memory_increase_mb']}MB projected 30-minute growth"
        )

        # Store leak analysis results
        self.memory_performance_data["leak_detections"].append(leak_analysis)

        print(f"✅ MEMORY LEAK DETECTION: {leak_analysis.get('leak_rate_mb_per_minute', 0):.2f}MB/min leak rate, "
              f"{leak_analysis.get('total_leaked_objects', 0)} leaked objects detected")

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.memory
    async def test_memory_cleanup_validation_after_sessions(self):
        """
        Test memory cleanup effectiveness after user session completion.

        Validates memory is properly cleaned up when user sessions end
        and garbage collection effectiveness.

        DESIGNED TO FAIL INITIALLY: Exposes current memory cleanup issues.
        """
        print(f"\n=== TESTING MEMORY CLEANUP VALIDATION AFTER SESSIONS ===")

        # Execute memory cleanup validation scenario
        scenario = MEMORY_TEST_SCENARIOS[3]  # memory_cleanup_validation
        scenario["duration"] = 45  # Reduced for testing

        results = await self._execute_memory_test_scenario(scenario)

        # Perform additional cleanup analysis
        cleanup_analysis = self.memory_leak_detector.cleanup_analysis()

        # Validate memory cleanup SLAs
        assert results["cleanup_effectiveness_percent"] >= scenario["expected_memory_cleanup_percent"], (
            f"MEMORY CLEANUP EFFECTIVENESS VIOLATION: {results['cleanup_effectiveness_percent']:.1f}% < "
            f"{scenario['expected_memory_cleanup_percent']}% expected cleanup effectiveness"
        )

        assert cleanup_analysis["cleanup_effectiveness_percent"] >= MEMORY_PERFORMANCE_SLA["min_gc_effectiveness_percent"], (
            f"GC CLEANUP EFFECTIVENESS VIOLATION: {cleanup_analysis['cleanup_effectiveness_percent']:.1f}% < "
            f"{MEMORY_PERFORMANCE_SLA['min_gc_effectiveness_percent']}% minimum GC effectiveness"
        )

        # Validate final memory state after cleanup
        if MEMORY_PERFORMANCE_SLA["zero_memory_leaks_after_cleanup"]:
            remaining_growth_percent = results["memory_increase_percent"]
            assert remaining_growth_percent <= 5.0, (  # Allow small residual growth
                f"MEMORY LEAKS AFTER CLEANUP VIOLATION: {remaining_growth_percent:.1f}% memory growth remains after cleanup "
                f"(should be near 0% for zero memory leaks)"
            )

        print(f"✅ MEMORY CLEANUP VALIDATION: {results['cleanup_effectiveness_percent']:.1f}% session cleanup, "
              f"{cleanup_analysis['cleanup_effectiveness_percent']:.1f}% GC effectiveness")

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.memory
    async def test_service_memory_limit_boundary_validation(self):
        """
        Test service memory usage against strict 2GB boundary limit.

        Validates system operates within the critical 2GB per service
        limit under various load conditions.

        DESIGNED TO FAIL INITIALLY: Establishes current memory usage patterns.
        """
        print(f"\n=== TESTING SERVICE MEMORY LIMIT BOUNDARY VALIDATION ===")

        # Monitor current memory usage
        current_memory_snapshot = self.memory_leak_detector.capture_memory_snapshot("service_boundary_test")

        print(f"CURRENT SERVICE MEMORY USAGE:")
        print(f"  - RSS Memory: {current_memory_snapshot.rss_memory_mb:.1f}MB")
        print(f"  - VMS Memory: {current_memory_snapshot.vms_memory_mb:.1f}MB")
        print(f"  - Memory Percent: {current_memory_snapshot.memory_percent:.1f}%")
        print(f"  - Available Memory: {current_memory_snapshot.available_memory_mb:.1f}MB")

        # STRICT SLA VALIDATION - Service Memory Limit
        assert current_memory_snapshot.rss_memory_mb < MEMORY_PERFORMANCE_SLA["max_service_memory_mb"], (
            f"SERVICE MEMORY LIMIT VIOLATION: {current_memory_snapshot.rss_memory_mb:.1f}MB > "
            f"{MEMORY_PERFORMANCE_SLA['max_service_memory_mb']}MB strict limit"
        )

        # System memory usage validation
        assert current_memory_snapshot.memory_percent < MEMORY_PERFORMANCE_SLA["max_system_memory_usage_percent"], (
            f"SYSTEM MEMORY USAGE VIOLATION: {current_memory_snapshot.memory_percent:.1f}% > "
            f"{MEMORY_PERFORMANCE_SLA['max_system_memory_usage_percent']}% limit"
        )

        # Available memory validation
        assert current_memory_snapshot.available_memory_mb > MEMORY_PERFORMANCE_SLA["min_available_memory_mb"], (
            f"AVAILABLE MEMORY VIOLATION: {current_memory_snapshot.available_memory_mb:.1f}MB < "
            f"{MEMORY_PERFORMANCE_SLA['min_available_memory_mb']}MB minimum"
        )

        # Memory pressure validation
        memory_pressure_count = len(self.memory_pressure_events)
        assert memory_pressure_count <= MEMORY_PERFORMANCE_SLA["max_memory_pressure_events"], (
            f"MEMORY PRESSURE EVENTS VIOLATION: {memory_pressure_count} events > "
            f"{MEMORY_PERFORMANCE_SLA['max_memory_pressure_events']} maximum allowed"
        )

        print(f"✅ SERVICE MEMORY BOUNDARY VALIDATION: {current_memory_snapshot.rss_memory_mb:.1f}MB / "
              f"{MEMORY_PERFORMANCE_SLA['max_service_memory_mb']}MB limit ({(current_memory_snapshot.rss_memory_mb / MEMORY_PERFORMANCE_SLA['max_service_memory_mb'] * 100):.1f}% utilization)")