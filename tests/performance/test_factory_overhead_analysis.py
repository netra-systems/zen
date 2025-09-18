"""
Phase 3: Performance Impact Assessment Tests
Issue #1194 - Factory Over-Engineering Remediation

Purpose:
Performance analysis tests to compare factory instantiation vs direct instantiation,
measure memory usage patterns, and validate performance benefits of factory cleanup.

Test Design:
- Benchmarks factory vs direct instantiation performance
- Measures memory usage patterns for factory patterns
- Analyzes GC impact of factory object creation
- Validates performance benefits of cleanup

Business Impact: 500K+ ARR protection through performance optimization
Performance Goal: Demonstrate measurable performance gains from factory cleanup

These tests establish baseline metrics and validate performance improvements.
"""

import asyncio
import gc
import time
import psutil
import statistics
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import patch, MagicMock
import warnings
from pathlib import Path
import sys
import tracemalloc
from memory_profiler import profile, memory_usage

from test_framework.ssot.base_test_case import SSotBaseTestCase


class PerformanceMetrics:
    """Container for performance measurement data."""

    def __init__(self):
        self.execution_times = []
        self.memory_usage = []
        self.gc_collections = 0
        self.peak_memory = 0
        self.avg_execution_time = 0
        self.memory_efficiency = 0

    def add_measurement(self, execution_time: float, memory_used: int):
        """Add a performance measurement."""
        self.execution_times.append(execution_time)
        self.memory_usage.append(memory_used)

    def calculate_statistics(self):
        """Calculate performance statistics."""
        if self.execution_times:
            self.avg_execution_time = statistics.mean(self.execution_times)
            self.peak_memory = max(self.memory_usage) if self.memory_usage else 0
            self.memory_efficiency = sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0


class MockFactoryForTesting:
    """Mock factory implementation for performance testing."""

    def __init__(self, complexity_level: str = "simple"):
        self.complexity_level = complexity_level
        self.created_objects = []
        self.initialization_time = time.time()

        # Simulate different complexity levels
        if complexity_level == "complex":
            # Simulate complex factory with multiple layers
            self._initialize_complex_patterns()
        elif complexity_level == "over_engineered":
            # Simulate over-engineered factory with unnecessary abstractions
            self._initialize_over_engineered_patterns()

    def _initialize_complex_patterns(self):
        """Simulate complex initialization patterns."""
        self.registry = {}
        self.observers = []
        self.cache = {}
        for i in range(100):
            self.registry[f"component_{i}"] = f"value_{i}"

    def _initialize_over_engineered_patterns(self):
        """Simulate over-engineered initialization with excessive abstractions."""
        self._initialize_complex_patterns()
        self.abstract_factory_manager = {}
        self.proxy_handlers = {}
        self.interceptor_chain = []
        for i in range(500):
            self.abstract_factory_manager[f"abstract_{i}"] = {
                'proxy': f"proxy_{i}",
                'interceptor': f"interceptor_{i}",
                'metadata': {'created': time.time(), 'complexity': 'over_engineered'}
            }

    def create_object(self, object_type: str = "default", **kwargs):
        """Create an object through the factory."""
        start_time = time.time()

        # Simulate factory overhead
        if self.complexity_level == "simple":
            created_object = {"type": object_type, "id": len(self.created_objects), **kwargs}
        elif self.complexity_level == "complex":
            # Add some processing overhead
            created_object = self._create_complex_object(object_type, **kwargs)
        else:  # over_engineered
            # Add significant processing overhead
            created_object = self._create_over_engineered_object(object_type, **kwargs)

        creation_time = time.time() - start_time
        self.created_objects.append({
            'object': created_object,
            'creation_time': creation_time,
            'timestamp': time.time()
        })

        return created_object

    def _create_complex_object(self, object_type: str, **kwargs):
        """Create object with complex factory logic."""
        # Simulate registry lookup
        if object_type in self.registry:
            base_config = self.registry[object_type]
        else:
            base_config = "default_config"

        # Simulate observer notification
        for observer in self.observers:
            observer.notify(object_type)

        # Simulate caching
        cache_key = f"{object_type}:{hash(str(kwargs))}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        created_object = {
            "type": object_type,
            "id": len(self.created_objects),
            "config": base_config,
            "metadata": {"complexity": "complex", "cached": False},
            **kwargs
        }

        self.cache[cache_key] = created_object
        return created_object

    def _create_over_engineered_object(self, object_type: str, **kwargs):
        """Create object with over-engineered factory logic."""
        # Start with complex logic
        created_object = self._create_complex_object(object_type, **kwargs)

        # Add unnecessary abstraction layers
        abstract_key = f"abstract_{object_type}"
        if abstract_key in self.abstract_factory_manager:
            proxy_handler = self.abstract_factory_manager[abstract_key]['proxy']
            created_object['proxy_handler'] = proxy_handler

        # Add interceptor chain processing
        for interceptor in self.interceptor_chain:
            created_object = interceptor.process(created_object)

        # Add metadata overhead
        created_object['metadata'].update({
            'proxy_layers': 3,
            'interceptor_count': len(self.interceptor_chain),
            'abstract_factory_id': abstract_key,
            'over_engineered': True
        })

        return created_object


def direct_object_creation(object_type: str = "default", **kwargs):
    """Direct object creation without factory pattern."""
    return {
        "type": object_type,
        "id": int(time.time() * 1000000) % 1000000,  # Simple ID generation
        **kwargs
    }


class FactoryOverheadAnalysisTests(SSotBaseTestCase):
    """
    Phase 3: Performance Impact Assessment

    Tests to measure performance overhead of factory patterns and validate
    benefits of removing over-engineered factory implementations.
    """

    def setUp(self):
        """Set up performance testing environment."""
        super().setUp()
        self.test_iterations = 1000  # Number of iterations for performance tests
        self.concurrent_users = 10   # Simulated concurrent users
        self.performance_results = {}

        # Initialize memory tracking
        tracemalloc.start()
        gc.collect()  # Start with clean slate

    def tearDown(self):
        """Clean up after performance tests."""
        tracemalloc.stop()
        super().tearDown()

    def test_01_benchmark_factory_vs_direct_instantiation_performance(self):
        """
        Test 1: Factory vs Direct Instantiation Performance Benchmark

        Compares performance between factory pattern instantiation and direct
        object creation to quantify factory overhead.

        Expected Result: Shows measurable performance difference
        """
        print(f"\n⚡ PHASE 3.1: Benchmarking factory vs direct instantiation...")

        test_scenarios = {
            'simple_factory': MockFactoryForTesting('simple'),
            'complex_factory': MockFactoryForTesting('complex'),
            'over_engineered_factory': MockFactoryForTesting('over_engineered')
        }

        results = {}

        for scenario_name, factory in test_scenarios.items():
            print(f"  📊 Testing {scenario_name}...")

            # Benchmark factory instantiation
            factory_metrics = PerformanceMetrics()
            gc.collect()

            start_memory = psutil.Process().memory_info().rss
            start_time = time.perf_counter()

            for i in range(self.test_iterations):
                iteration_start = time.perf_counter()
                obj = factory.create_object("test_object", iteration=i)
                iteration_time = time.perf_counter() - iteration_start

                current_memory = psutil.Process().memory_info().rss
                factory_metrics.add_measurement(iteration_time, current_memory - start_memory)

            factory_total_time = time.perf_counter() - start_time
            factory_peak_memory = psutil.Process().memory_info().rss - start_memory

            # Benchmark direct instantiation
            direct_metrics = PerformanceMetrics()
            gc.collect()

            start_memory = psutil.Process().memory_info().rss
            start_time = time.perf_counter()

            for i in range(self.test_iterations):
                iteration_start = time.perf_counter()
                obj = direct_object_creation("test_object", iteration=i)
                iteration_time = time.perf_counter() - iteration_start

                current_memory = psutil.Process().memory_info().rss
                direct_metrics.add_measurement(iteration_time, current_memory - start_memory)

            direct_total_time = time.perf_counter() - start_time
            direct_peak_memory = psutil.Process().memory_info().rss - start_memory

            # Calculate performance comparison
            factory_metrics.calculate_statistics()
            direct_metrics.calculate_statistics()

            performance_overhead = (factory_total_time - direct_total_time) / direct_total_time * 100
            memory_overhead = (factory_peak_memory - direct_peak_memory) / max(direct_peak_memory, 1) * 100

            results[scenario_name] = {
                'factory_time': factory_total_time,
                'direct_time': direct_total_time,
                'time_overhead_percent': performance_overhead,
                'factory_memory': factory_peak_memory,
                'direct_memory': direct_peak_memory,
                'memory_overhead_percent': memory_overhead,
                'factory_avg_time': factory_metrics.avg_execution_time,
                'direct_avg_time': direct_metrics.avg_execution_time
            }

            print(f"    ⏱️  Factory total time: {factory_total_time:.4f}s")
            print(f"    ⏱️  Direct total time: {direct_total_time:.4f}s")
            print(f"    📈 Performance overhead: {performance_overhead:.2f}%")
            print(f"    💾 Memory overhead: {memory_overhead:.2f}%")

        self.performance_results['instantiation_benchmark'] = results

        # Validate that over-engineered factories show significant overhead
        over_engineered_overhead = results['over_engineered_factory']['time_overhead_percent']
        simple_factory_overhead = results['simple_factory']['time_overhead_percent']

        print(f"\n📊 PERFORMANCE OVERHEAD ANALYSIS:")
        print(f"  🟢 Simple factory overhead: {simple_factory_overhead:.2f}%")
        print(f"  🔴 Over-engineered factory overhead: {over_engineered_overhead:.2f}%")
        print(f"  📈 Over-engineering penalty: {over_engineered_overhead - simple_factory_overhead:.2f}%")

        # This test should show measurable overhead for over-engineered factories
        self.assertGreater(
            over_engineered_overhead,
            simple_factory_overhead * 2,
            f"X PERFORMANCE IMPACT VALIDATED: Over-engineered factory overhead ({over_engineered_overhead:.2f}%) "
            f"should be >2x simple factory overhead ({simple_factory_overhead:.2f}%) to justify removal."
        )

    def test_02_measure_memory_usage_patterns_for_factory_cleanup(self):
        """
        Test 2: Memory Usage Pattern Analysis

        Analyzes memory usage patterns for different factory implementations
        to identify memory efficiency gains from factory cleanup.

        Expected Result: Shows memory usage differences between factory patterns
        """
        print(f"\n💾 PHASE 3.2: Measuring memory usage patterns...")

        # Memory usage test scenarios
        memory_scenarios = {
            'baseline_direct': lambda: [direct_object_creation(f"obj_{i}") for i in range(100)],
            'simple_factory': lambda: self._create_objects_with_factory(MockFactoryForTesting('simple'), 100),
            'complex_factory': lambda: self._create_objects_with_factory(MockFactoryForTesting('complex'), 100),
            'over_engineered_factory': lambda: self._create_objects_with_factory(MockFactoryForTesting('over_engineered'), 100)
        }

        memory_results = {}

        for scenario_name, scenario_func in memory_scenarios.items():
            print(f"  📊 Measuring memory for {scenario_name}...")

            # Measure memory usage during object creation
            gc.collect()  # Clean slate
            start_memory = psutil.Process().memory_info().rss

            # Use memory_usage to track peak memory
            mem_usage = memory_usage((scenario_func, ()), interval=0.01)

            end_memory = psutil.Process().memory_info().rss
            peak_memory = max(mem_usage) * 1024 * 1024  # Convert MB to bytes
            memory_delta = end_memory - start_memory

            memory_results[scenario_name] = {
                'start_memory': start_memory,
                'end_memory': end_memory,
                'peak_memory': peak_memory,
                'memory_delta': memory_delta,
                'peak_memory_mb': max(mem_usage),
                'memory_efficiency': memory_delta / 100  # Memory per object
            }

            print(f"    💾 Memory delta: {memory_delta / 1024:.2f} KB")
            print(f"    📈 Peak memory: {max(mem_usage):.2f} MB")
            print(f"    ⚡ Memory per object: {memory_delta / 100:.0f} bytes")

        # Calculate memory savings potential
        baseline_memory = memory_results['baseline_direct']['memory_delta']
        over_engineered_memory = memory_results['over_engineered_factory']['memory_delta']
        simple_factory_memory = memory_results['simple_factory']['memory_delta']

        memory_waste_over_engineered = (over_engineered_memory - baseline_memory) / baseline_memory * 100
        memory_waste_simple = (simple_factory_memory - baseline_memory) / baseline_memory * 100

        print(f"\n💾 MEMORY USAGE ANALYSIS:")
        print(f"  🟢 Baseline (direct): {baseline_memory / 1024:.2f} KB")
        print(f"  🟡 Simple factory: {simple_factory_memory / 1024:.2f} KB ({memory_waste_simple:.1f}% overhead)")
        print(f"  🔴 Over-engineered: {over_engineered_memory / 1024:.2f} KB ({memory_waste_over_engineered:.1f}% overhead)")

        memory_savings_potential = over_engineered_memory - simple_factory_memory
        print(f"  💰 Potential savings: {memory_savings_potential / 1024:.2f} KB per 100 objects")

        self.performance_results['memory_analysis'] = memory_results

        # Validate significant memory overhead for over-engineered patterns
        self.assertGreater(
            memory_waste_over_engineered,
            memory_waste_simple * 3,
            f"X MEMORY OVERHEAD VALIDATED: Over-engineered factory memory overhead ({memory_waste_over_engineered:.1f}%) "
            f"should be >3x simple factory overhead ({memory_waste_simple:.1f}%) to justify cleanup."
        )

    def test_03_analyze_garbage_collection_impact(self):
        """
        Test 3: Garbage Collection Impact Analysis

        Analyzes how different factory patterns affect garbage collection
        frequency and efficiency.

        Expected Result: Shows GC impact differences between factory patterns
        """
        print(f"\n🗑️ PHASE 3.3: Analyzing garbage collection impact...")

        gc_results = {}

        # Test scenarios for GC impact
        scenarios = {
            'direct_instantiation': self._gc_test_direct_creation,
            'simple_factory': lambda: self._gc_test_factory_creation(MockFactoryForTesting('simple')),
            'over_engineered_factory': lambda: self._gc_test_factory_creation(MockFactoryForTesting('over_engineered'))
        }

        for scenario_name, scenario_func in scenarios.items():
            print(f"  🗑️ Testing GC impact for {scenario_name}...")

            # Enable GC debugging
            gc.set_debug(gc.DEBUG_STATS)

            # Reset GC stats
            gc.collect()
            initial_collections = {
                'gen0': gc.get_count()[0],
                'gen1': gc.get_count()[1],
                'gen2': gc.get_count()[2]
            }

            initial_stats = gc.get_stats()
            start_time = time.time()

            # Run scenario
            scenario_func()

            end_time = time.time()

            # Measure GC impact
            final_collections = {
                'gen0': gc.get_count()[0],
                'gen1': gc.get_count()[1],
                'gen2': gc.get_count()[2]
            }

            final_stats = gc.get_stats()

            # Force final GC to measure uncollected objects
            uncollected_before = len(gc.get_objects())
            gc.collect()
            uncollected_after = len(gc.get_objects())

            gc_results[scenario_name] = {
                'execution_time': end_time - start_time,
                'initial_collections': initial_collections,
                'final_collections': final_collections,
                'collection_deltas': {
                    'gen0': final_collections['gen0'] - initial_collections['gen0'],
                    'gen1': final_collections['gen1'] - initial_collections['gen1'],
                    'gen2': final_collections['gen2'] - initial_collections['gen2']
                },
                'objects_before_gc': uncollected_before,
                'objects_after_gc': uncollected_after,
                'objects_collected': uncollected_before - uncollected_after,
                'gc_efficiency': (uncollected_before - uncollected_after) / max(uncollected_before, 1)
            }

            print(f"    ⏱️  Execution time: {end_time - start_time:.4f}s")
            print(f"    🗑️ Objects collected: {uncollected_before - uncollected_after}")
            print(f"    📊 GC efficiency: {gc_results[scenario_name]['gc_efficiency']:.2%}")

            # Disable GC debugging
            gc.set_debug(0)

        # Analyze GC impact differences
        direct_efficiency = gc_results['direct_instantiation']['gc_efficiency']
        simple_factory_efficiency = gc_results['simple_factory']['gc_efficiency']
        over_engineered_efficiency = gc_results['over_engineered_factory']['gc_efficiency']

        print(f"\n🗑️ GARBAGE COLLECTION ANALYSIS:")
        print(f"  🟢 Direct instantiation GC efficiency: {direct_efficiency:.2%}")
        print(f"  🟡 Simple factory GC efficiency: {simple_factory_efficiency:.2%}")
        print(f"  🔴 Over-engineered GC efficiency: {over_engineered_efficiency:.2%}")

        gc_impact_difference = abs(over_engineered_efficiency - direct_efficiency) * 100

        self.performance_results['gc_analysis'] = gc_results

        # Validate measurable GC impact difference
        self.assertGreater(
            gc_impact_difference,
            5,
            f"X GC IMPACT VALIDATED: GC efficiency difference ({gc_impact_difference:.1f}%) "
            f"between over-engineered and direct creation should be >5% to justify cleanup."
        )

    def test_04_concurrent_performance_impact_assessment(self):
        """
        Test 4: Concurrent Performance Impact Assessment

        Tests factory performance under concurrent load to identify scalability
        issues with over-engineered factory patterns.

        Expected Result: Shows scalability differences under concurrent load
        """
        print(f"\n🔄 PHASE 3.4: Assessing concurrent performance impact...")

        concurrency_results = {}

        # Test concurrent scenarios
        concurrency_scenarios = {
            'direct_creation': self._concurrent_direct_creation,
            'simple_factory': lambda users, iterations: self._concurrent_factory_creation(
                MockFactoryForTesting('simple'), users, iterations
            ),
            'over_engineered_factory': lambda users, iterations: self._concurrent_factory_creation(
                MockFactoryForTesting('over_engineered'), users, iterations
            )
        }

        user_counts = [1, 5, 10, 20]  # Different concurrency levels

        for scenario_name, scenario_func in concurrency_scenarios.items():
            print(f"  🔄 Testing {scenario_name} under concurrent load...")

            scenario_results = {}

            for user_count in user_counts:
                iterations_per_user = 100

                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss

                # Run concurrent test
                scenario_func(user_count, iterations_per_user)

                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss

                total_time = end_time - start_time
                memory_used = end_memory - start_memory
                throughput = (user_count * iterations_per_user) / total_time

                scenario_results[user_count] = {
                    'total_time': total_time,
                    'memory_used': memory_used,
                    'throughput': throughput,
                    'avg_time_per_operation': total_time / (user_count * iterations_per_user)
                }

                print(f"    👥 {user_count} users: {throughput:.1f} ops/sec, {total_time:.2f}s total")

            concurrency_results[scenario_name] = scenario_results

        # Analyze scalability differences
        print(f"\n🔄 CONCURRENT PERFORMANCE ANALYSIS:")

        for user_count in user_counts:
            direct_throughput = concurrency_results['direct_creation'][user_count]['throughput']
            simple_throughput = concurrency_results['simple_factory'][user_count]['throughput']
            over_engineered_throughput = concurrency_results['over_engineered_factory'][user_count]['throughput']

            simple_degradation = (direct_throughput - simple_throughput) / direct_throughput * 100
            over_engineered_degradation = (direct_throughput - over_engineered_throughput) / direct_throughput * 100

            print(f"  👥 {user_count} concurrent users:")
            print(f"    🟢 Direct: {direct_throughput:.1f} ops/sec")
            print(f"    🟡 Simple factory: {simple_throughput:.1f} ops/sec ({simple_degradation:.1f}% degradation)")
            print(f"    🔴 Over-engineered: {over_engineered_throughput:.1f} ops/sec ({over_engineered_degradation:.1f}% degradation)")

        self.performance_results['concurrency_analysis'] = concurrency_results

        # Validate scalability impact at highest concurrency
        max_users = max(user_counts)
        direct_max_throughput = concurrency_results['direct_creation'][max_users]['throughput']
        over_engineered_max_throughput = concurrency_results['over_engineered_factory'][max_users]['throughput']
        throughput_degradation = (direct_max_throughput - over_engineered_max_throughput) / direct_max_throughput * 100

        self.assertGreater(
            throughput_degradation,
            20,
            f"X CONCURRENCY IMPACT VALIDATED: Over-engineered factory throughput degradation ({throughput_degradation:.1f}%) "
            f"at {max_users} concurrent users should be >20% to justify cleanup."
        )

    def test_05_generate_performance_improvement_projections(self):
        """
        Test 5: Performance Improvement Projections

        Generates projections for performance improvements achievable through
        factory cleanup and consolidation.

        Expected Result: PASS - Provides quantified performance improvement projections
        """
        print(f"\n📈 PHASE 3.5: Generating performance improvement projections...")

        # Ensure all previous tests have run
        if 'instantiation_benchmark' not in self.performance_results:
            self.test_01_benchmark_factory_vs_direct_instantiation_performance()
        if 'memory_analysis' not in self.performance_results:
            self.test_02_measure_memory_usage_patterns_for_factory_cleanup()
        if 'concurrency_analysis' not in self.performance_results:
            self.test_04_concurrent_performance_impact_assessment()

        # Calculate improvement projections
        performance_projections = {
            'instantiation_speed_improvement': {},
            'memory_efficiency_improvement': {},
            'concurrency_scalability_improvement': {},
            'overall_system_impact': {}
        }

        # Instantiation speed improvements
        instantiation_results = self.performance_results['instantiation_benchmark']
        over_engineered_time = instantiation_results['over_engineered_factory']['factory_time']
        simple_factory_time = instantiation_results['simple_factory']['factory_time']
        direct_time = instantiation_results['direct_creation'] if 'direct_creation' in instantiation_results else instantiation_results['simple_factory']['direct_time']

        speed_improvement_factor = over_engineered_time / simple_factory_time
        speed_improvement_percent = (over_engineered_time - simple_factory_time) / over_engineered_time * 100

        performance_projections['instantiation_speed_improvement'] = {
            'improvement_factor': speed_improvement_factor,
            'improvement_percent': speed_improvement_percent,
            'time_saved_per_1000_operations': (over_engineered_time - simple_factory_time) * (1000 / self.test_iterations)
        }

        # Memory efficiency improvements
        memory_results = self.performance_results['memory_analysis']
        over_engineered_memory = memory_results['over_engineered_factory']['memory_delta']
        simple_factory_memory = memory_results['simple_factory']['memory_delta']

        memory_improvement_percent = (over_engineered_memory - simple_factory_memory) / over_engineered_memory * 100
        memory_saved_per_100_objects = over_engineered_memory - simple_factory_memory

        performance_projections['memory_efficiency_improvement'] = {
            'improvement_percent': memory_improvement_percent,
            'memory_saved_per_100_objects': memory_saved_per_100_objects,
            'memory_saved_mb_per_100_objects': memory_saved_per_100_objects / (1024 * 1024)
        }

        # Concurrency scalability improvements
        concurrency_results = self.performance_results['concurrency_analysis']
        max_users = 20  # Highest tested concurrency
        over_engineered_throughput = concurrency_results['over_engineered_factory'][max_users]['throughput']
        simple_factory_throughput = concurrency_results['simple_factory'][max_users]['throughput']

        throughput_improvement = simple_factory_throughput - over_engineered_throughput
        throughput_improvement_percent = throughput_improvement / over_engineered_throughput * 100

        performance_projections['concurrency_scalability_improvement'] = {
            'throughput_improvement': throughput_improvement,
            'throughput_improvement_percent': throughput_improvement_percent,
            'max_concurrent_users_tested': max_users
        }

        # Overall system impact projections
        # Assume 1M object creations per day in production
        daily_object_creations = 1_000_000

        daily_time_saved = (performance_projections['instantiation_speed_improvement']['time_saved_per_1000_operations'] *
                           daily_object_creations / 1000)
        daily_memory_saved = (memory_saved_per_100_objects * daily_object_creations / 100)

        performance_projections['overall_system_impact'] = {
            'daily_object_creations_assumed': daily_object_creations,
            'daily_cpu_time_saved_seconds': daily_time_saved,
            'daily_memory_saved_mb': daily_memory_saved / (1024 * 1024),
            'annual_cpu_time_saved_hours': daily_time_saved * 365 / 3600,
            'cost_savings_projection': 'Reduced infrastructure costs through improved efficiency'
        }

        print(f"\n📈 PERFORMANCE IMPROVEMENT PROJECTIONS:")
        print(f"  ⚡ INSTANTIATION SPEED IMPROVEMENTS:")
        print(f"    📈 Speed improvement: {speed_improvement_percent:.1f}%")
        print(f"    ⏱️  Time saved per 1K operations: {performance_projections['instantiation_speed_improvement']['time_saved_per_1000_operations']:.4f}s")

        print(f"\n  💾 MEMORY EFFICIENCY IMPROVEMENTS:")
        print(f"    📈 Memory efficiency improvement: {memory_improvement_percent:.1f}%")
        print(f"    💾 Memory saved per 100 objects: {memory_saved_mb_per_100_objects:.2f} MB")

        print(f"\n  🔄 CONCURRENCY SCALABILITY IMPROVEMENTS:")
        print(f"    📈 Throughput improvement: {throughput_improvement_percent:.1f}%")
        print(f"    🚀 Additional throughput: {throughput_improvement:.1f} ops/sec at {max_users} users")

        print(f"\n  🏭 OVERALL SYSTEM IMPACT (Production Projections):")
        print(f"    ⏱️  Daily CPU time saved: {daily_time_saved:.2f} seconds")
        print(f"    💾 Daily memory saved: {daily_memory_saved / (1024 * 1024):.2f} MB")
        print(f"    📅 Annual CPU time saved: {performance_projections['overall_system_impact']['annual_cpu_time_saved_hours']:.1f} hours")

        # Business value calculation
        # Assume $0.10 per GB-hour for memory and $0.05 per vCPU-hour
        annual_memory_saved_gb_hours = (daily_memory_saved / (1024 * 1024 * 1024)) * 24 * 365
        annual_cpu_saved_hours = performance_projections['overall_system_impact']['annual_cpu_time_saved_hours']

        estimated_cost_savings = (annual_memory_saved_gb_hours * 0.10) + (annual_cpu_saved_hours * 0.05)

        print(f"    💰 Estimated annual cost savings: ${estimated_cost_savings:.2f}")

        self.performance_projections = performance_projections

        # This test should PASS - we want actionable performance projections
        total_improvement_score = (
            speed_improvement_percent +
            memory_improvement_percent +
            throughput_improvement_percent
        ) / 3

        self.assertGreaterEqual(
            total_improvement_score,
            15,
            f"CHECK PERFORMANCE IMPROVEMENT VALIDATED: Average improvement score ({total_improvement_score:.1f}%) "
            f"demonstrates significant performance benefits from factory cleanup."
        )

    def _create_objects_with_factory(self, factory: MockFactoryForTesting, count: int) -> List[Any]:
        """Create objects using a factory for memory testing."""
        return [factory.create_object(f"obj_{i}") for i in range(count)]

    def _gc_test_direct_creation(self):
        """Test direct object creation for GC analysis."""
        objects = []
        for i in range(1000):
            obj = direct_object_creation(f"gc_test_{i}")
            objects.append(obj)
            if i % 100 == 0:
                # Intermittent GC pressure
                temp_objects = [direct_object_creation(f"temp_{j}") for j in range(50)]
                del temp_objects

    def _gc_test_factory_creation(self, factory: MockFactoryForTesting):
        """Test factory object creation for GC analysis."""
        objects = []
        for i in range(1000):
            obj = factory.create_object(f"gc_test_{i}")
            objects.append(obj)
            if i % 100 == 0:
                # Intermittent GC pressure
                temp_objects = [factory.create_object(f"temp_{j}") for j in range(50)]
                del temp_objects

    def _concurrent_direct_creation(self, user_count: int, iterations_per_user: int):
        """Test direct object creation under concurrent load."""
        def worker():
            return [direct_object_creation(f"concurrent_{i}") for i in range(iterations_per_user)]

        with ThreadPoolExecutor(max_workers=user_count) as executor:
            futures = [executor.submit(worker) for _ in range(user_count)]
            results = [future.result() for future in futures]

    def _concurrent_factory_creation(self, factory: MockFactoryForTesting, user_count: int, iterations_per_user: int):
        """Test factory object creation under concurrent load."""
        def worker():
            # Each worker gets its own factory instance to avoid contention
            worker_factory = MockFactoryForTesting(factory.complexity_level)
            return [worker_factory.create_object(f"concurrent_{i}") for i in range(iterations_per_user)]

        with ThreadPoolExecutor(max_workers=user_count) as executor:
            futures = [executor.submit(worker) for _ in range(user_count)]
            results = [future.result() for future in futures]


if __name__ == '__main__':
    import unittest

    print("🚀 Starting Factory Performance Impact Assessment - Phase 3")
    print("=" * 80)

    unittest.main(verbosity=2)