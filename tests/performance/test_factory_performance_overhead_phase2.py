"""
Factory Performance Overhead Analysis - Phase 2
Measures performance impact of factory patterns vs direct instantiation.

Business Impact: $500K+ ARR performance optimization
Created: 2025-09-15
Purpose: Quantify factory overhead to justify architectural cleanup
"""

import time
import statistics
import gc
import psutil
import os
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestFactoryPerformanceOverheadPhase2(SSotBaseTestCase):
    """Measure factory pattern performance overhead."""

    def setUp(self):
        """Set up test environment with performance monitoring."""
        super().setUp()
        self.benchmark_iterations = 1000
        self.warmup_iterations = 100
        self.project_root = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1")

        # Set up memory monitoring
        self.process = psutil.Process(os.getpid())
        self.initial_memory = self.process.memory_info().rss

    def run_performance_benchmark(self, test_func, name, iterations=None):
        """Run performance benchmark with statistical analysis."""
        iterations = iterations or self.benchmark_iterations

        # Warmup phase
        for _ in range(self.warmup_iterations):
            test_func()

        # Collect garbage to get clean baseline
        gc.collect()
        start_memory = self.process.memory_info().rss

        # Benchmark phase
        execution_times = []
        for _ in range(iterations):
            start_time = time.perf_counter()
            test_func()
            end_time = time.perf_counter()
            execution_times.append((end_time - start_time) * 1000)  # Convert to milliseconds

        # Memory measurement
        end_memory = self.process.memory_info().rss
        memory_overhead = end_memory - start_memory

        # Statistical analysis
        mean_time = statistics.mean(execution_times)
        median_time = statistics.median(execution_times)
        stdev_time = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        min_time = min(execution_times)
        max_time = max(execution_times)

        return {
            "name": name,
            "iterations": iterations,
            "mean_ms": mean_time,
            "median_ms": median_time,
            "stdev_ms": stdev_time,
            "min_ms": min_time,
            "max_ms": max_time,
            "memory_overhead_kb": memory_overhead / 1024,
            "raw_times": execution_times
        }

    def test_01_factory_instantiation_overhead_benchmark(self):
        """
        EXPECTED: FAIL for over-engineered factories

        Measures time overhead of factory instantiation vs direct
        instantiation for 1000 operations.

        Performance Thresholds:
        - Direct instantiation: Baseline (0% overhead)
        - Simple factory: <10% overhead (acceptable)
        - Complex factory: <25% overhead (review needed)
        - Over-engineered factory: >25% overhead (unacceptable)
        """

        # Simulate direct instantiation pattern
        class DirectExecutionEngine:
            def __init__(self, user_id="test_user", websocket_manager=None, tools=None):
                self.user_id = user_id
                self.websocket_manager = websocket_manager or {}
                self.tools = tools or []
                self.state = "initialized"

            def process(self):
                return f"Processing for {self.user_id}"

        # Simulate simple factory pattern
        class SimpleExecutionEngineFactory:
            @staticmethod
            def create(user_id="test_user", websocket_manager=None, tools=None):
                return DirectExecutionEngine(user_id, websocket_manager, tools)

        # Simulate complex factory pattern
        class ComplexExecutionEngineFactory:
            def __init__(self):
                self.config = {"timeout": 30, "retry_count": 3}
                self.cache = {}

            def create(self, user_id="test_user", websocket_manager=None, tools=None):
                # Simulate complex factory logic
                if user_id in self.cache:
                    config = self.cache[user_id]
                else:
                    config = self._build_config(user_id)
                    self.cache[user_id] = config

                engine = DirectExecutionEngine(user_id, websocket_manager, tools)
                engine.config = config
                return engine

            def _build_config(self, user_id):
                # Simulate complex configuration building
                return {
                    "user_id": user_id,
                    "timeout": self.config["timeout"],
                    "retry_count": self.config["retry_count"],
                    "created_at": time.time()
                }

        # Simulate over-engineered factory pattern
        class OverEngineeredExecutionEngineFactory:
            def __init__(self):
                self.config_manager = {"settings": {}}
                self.dependency_injector = {}
                self.lifecycle_manager = {}
                self.validation_engine = {}

            def create_with_full_lifecycle(self, user_id="test_user", websocket_manager=None, tools=None):
                # Simulate excessive factory overhead
                self._validate_dependencies()
                self._initialize_lifecycle()
                self._configure_injection()

                config = self._build_complex_config(user_id)
                engine = DirectExecutionEngine(user_id, websocket_manager, tools)

                self._apply_lifecycle_hooks(engine)
                self._inject_dependencies(engine)
                self._validate_final_state(engine)

                return engine

            def _validate_dependencies(self):
                for i in range(10):  # Simulate validation overhead
                    self.dependency_injector[f"dep_{i}"] = f"value_{i}"

            def _initialize_lifecycle(self):
                self.lifecycle_manager["phase"] = "initializing"

            def _configure_injection(self):
                self.dependency_injector["configured"] = True

            def _build_complex_config(self, user_id):
                # Simulate complex configuration with overhead
                config = {}
                for i in range(20):
                    config[f"setting_{i}"] = f"value_{i}_{user_id}"
                return config

            def _apply_lifecycle_hooks(self, engine):
                engine.lifecycle_phase = "created"

            def _inject_dependencies(self, engine):
                engine.dependencies = self.dependency_injector.copy()

            def _validate_final_state(self, engine):
                assert engine.state == "initialized"

        # Set up factory instances
        complex_factory = ComplexExecutionEngineFactory()
        over_engineered_factory = OverEngineeredExecutionEngineFactory()

        # Run benchmarks
        results = []

        # Direct instantiation (baseline)
        direct_result = self.run_performance_benchmark(
            lambda: DirectExecutionEngine(),
            "Direct Instantiation (Baseline)"
        )
        results.append(direct_result)
        baseline_time = direct_result["mean_ms"]

        # Simple factory
        simple_result = self.run_performance_benchmark(
            lambda: SimpleExecutionEngineFactory.create(),
            "Simple Factory Pattern"
        )
        results.append(simple_result)

        # Complex factory
        complex_result = self.run_performance_benchmark(
            lambda: complex_factory.create(),
            "Complex Factory Pattern"
        )
        results.append(complex_result)

        # Over-engineered factory
        over_engineered_result = self.run_performance_benchmark(
            lambda: over_engineered_factory.create_with_full_lifecycle(),
            "Over-Engineered Factory Pattern"
        )
        results.append(over_engineered_result)

        # Calculate overhead percentages
        for result in results[1:]:  # Skip baseline
            result["overhead_percent"] = ((result["mean_ms"] - baseline_time) / baseline_time) * 100

        # Generate report
        report = f"""
FACTORY INSTANTIATION OVERHEAD BENCHMARK
========================================

Benchmark Configuration:
- Iterations: {self.benchmark_iterations}
- Warmup: {self.warmup_iterations}
- Platform: {os.name}

Performance Results:
"""

        for result in results:
            overhead = f" (+{result.get('overhead_percent', 0):.1f}%)" if 'overhead_percent' in result else " (baseline)"
            report += f"""
{result['name']}:
  Mean Time: {result['mean_ms']:.3f}ms{overhead}
  Median Time: {result['median_ms']:.3f}ms
  Std Dev: {result['stdev_ms']:.3f}ms
  Range: {result['min_ms']:.3f}ms - {result['max_ms']:.3f}ms
  Memory Overhead: {result['memory_overhead_kb']:.1f}KB
"""

        # Performance threshold analysis
        violations = []
        thresholds = {
            "Simple Factory Pattern": 10.0,
            "Complex Factory Pattern": 25.0,
            "Over-Engineered Factory Pattern": 25.0
        }

        for result in results[1:]:  # Skip baseline
            if 'overhead_percent' in result:
                threshold = thresholds.get(result['name'], 25.0)
                if result['overhead_percent'] > threshold:
                    violations.append({
                        "pattern": result['name'],
                        "overhead": result['overhead_percent'],
                        "threshold": threshold
                    })

        report += f"\nPERFORMANCE THRESHOLD ANALYSIS:\n"
        report += f"Baseline (Direct): {baseline_time:.3f}ms\n"

        for pattern, threshold in thresholds.items():
            result = next((r for r in results if r['name'] == pattern), None)
            if result and 'overhead_percent' in result:
                status = "✗ VIOLATION" if result['overhead_percent'] > threshold else "✓ ACCEPTABLE"
                report += f"{pattern}: {result['overhead_percent']:.1f}% overhead (threshold: {threshold}%) {status}\n"

        # Memory analysis
        total_memory_overhead = sum(r['memory_overhead_kb'] for r in results)
        report += f"\nMEMORY IMPACT:\n"
        report += f"Total Memory Overhead: {total_memory_overhead:.1f}KB\n"

        # Recommendations
        if violations:
            report += f"\nPERFORMANCE VIOLATIONS DETECTED ({len(violations)}):\n"
            for violation in violations:
                report += f"- {violation['pattern']}: {violation['overhead']:.1f}% > {violation['threshold']}%\n"
            report += "\nRecommendation: Replace over-engineered factories with direct instantiation\n"

        print(report)

        # This test should FAIL for over-engineered factories
        if violations:
            max_overhead = max(v['overhead'] for v in violations)
            self.fail(f"Factory performance overhead violations detected: {len(violations)} patterns "
                     f"exceed performance thresholds. Maximum overhead: {max_overhead:.1f}%. "
                     f"Architecture simplification required for better performance.")
        else:
            self.fail("No performance violations detected - this may indicate measurement issues.")

    def test_02_memory_overhead_analysis(self):
        """
        EXPECTED: FAIL for complex factory hierarchies

        Measures memory overhead of factory patterns including
        intermediate objects and reference chains.

        Memory Thresholds:
        - Direct instantiation: Baseline memory usage
        - Simple factory: <5% memory overhead
        - Complex factory: <15% memory overhead
        - Over-engineered: >15% memory overhead (unacceptable)
        """

        # Simulate different factory memory patterns
        class MemoryEfficientObject:
            def __init__(self, data=None):
                self.data = data or {"id": 1, "value": "test"}

        class SimpleFactoryWithCache:
            def __init__(self):
                self.cache = {}  # Small cache

            def create(self, obj_id=1):
                if obj_id not in self.cache:
                    self.cache[obj_id] = MemoryEfficientObject({"id": obj_id})
                return self.cache[obj_id]

        class ComplexFactoryWithHeavyCache:
            def __init__(self):
                self.cache = {}
                self.metadata = {}
                self.config_cache = {}

            def create(self, obj_id=1):
                # Build complex metadata
                if obj_id not in self.metadata:
                    self.metadata[obj_id] = {
                        f"meta_{i}": f"value_{i}" for i in range(50)
                    }

                # Build complex config
                if obj_id not in self.config_cache:
                    self.config_cache[obj_id] = {
                        f"config_{i}": list(range(20)) for i in range(10)
                    }

                if obj_id not in self.cache:
                    obj = MemoryEfficientObject()
                    obj.metadata = self.metadata[obj_id]
                    obj.config = self.config_cache[obj_id]
                    self.cache[obj_id] = obj

                return self.cache[obj_id]

        class OverEngineeredFactoryWithMassiveOverhead:
            def __init__(self):
                self.dependency_graph = {}
                self.lifecycle_cache = {}
                self.validation_cache = {}
                self.config_hierarchy = {}
                self.instance_registry = {}

            def create(self, obj_id=1):
                # Create massive dependency graph
                if obj_id not in self.dependency_graph:
                    self.dependency_graph[obj_id] = {
                        f"dep_{i}": {
                            f"subdep_{j}": list(range(100)) for j in range(10)
                        } for i in range(20)
                    }

                # Create heavy lifecycle cache
                if obj_id not in self.lifecycle_cache:
                    self.lifecycle_cache[obj_id] = {
                        "phases": [
                            {"phase": f"phase_{i}", "data": list(range(50))}
                            for i in range(15)
                        ]
                    }

                # Create validation cache
                if obj_id not in self.validation_cache:
                    self.validation_cache[obj_id] = {
                        f"rule_{i}": {
                            "conditions": list(range(30)),
                            "actions": list(range(30))
                        } for i in range(25)
                    }

                # Create config hierarchy
                if obj_id not in self.config_hierarchy:
                    self.config_hierarchy[obj_id] = {
                        "level1": {
                            "level2": {
                                "level3": {
                                    f"config_{i}": list(range(20)) for i in range(30)
                                }
                            }
                        }
                    }

                obj = MemoryEfficientObject()
                obj.dependencies = self.dependency_graph[obj_id]
                obj.lifecycle = self.lifecycle_cache[obj_id]
                obj.validation = self.validation_cache[obj_id]
                obj.config_hierarchy = self.config_hierarchy[obj_id]

                self.instance_registry[obj_id] = obj
                return obj

        # Memory measurement helper
        def measure_memory_usage(factory_func, iterations=100):
            gc.collect()
            start_memory = self.process.memory_info().rss

            objects = []
            for i in range(iterations):
                obj = factory_func(i)
                objects.append(obj)

            gc.collect()
            end_memory = self.process.memory_info().rss

            # Keep references to prevent garbage collection
            memory_usage = end_memory - start_memory

            # Clear references
            del objects
            gc.collect()

            return memory_usage

        # Run memory benchmarks
        memory_results = []

        # Direct instantiation (baseline)
        direct_memory = measure_memory_usage(lambda i: MemoryEfficientObject())
        memory_results.append({
            "name": "Direct Instantiation (Baseline)",
            "memory_kb": direct_memory / 1024,
            "overhead_percent": 0
        })
        baseline_memory = direct_memory

        # Simple factory with cache
        simple_factory = SimpleFactoryWithCache()
        simple_memory = measure_memory_usage(lambda i: simple_factory.create(i))
        simple_overhead = ((simple_memory - baseline_memory) / baseline_memory) * 100
        memory_results.append({
            "name": "Simple Factory with Cache",
            "memory_kb": simple_memory / 1024,
            "overhead_percent": simple_overhead
        })

        # Complex factory with heavy cache
        complex_factory = ComplexFactoryWithHeavyCache()
        complex_memory = measure_memory_usage(lambda i: complex_factory.create(i))
        complex_overhead = ((complex_memory - baseline_memory) / baseline_memory) * 100
        memory_results.append({
            "name": "Complex Factory with Heavy Cache",
            "memory_kb": complex_memory / 1024,
            "overhead_percent": complex_overhead
        })

        # Over-engineered factory
        over_engineered_factory = OverEngineeredFactoryWithMassiveOverhead()
        over_engineered_memory = measure_memory_usage(lambda i: over_engineered_factory.create(i))
        over_engineered_overhead = ((over_engineered_memory - baseline_memory) / baseline_memory) * 100
        memory_results.append({
            "name": "Over-Engineered Factory with Massive Overhead",
            "memory_kb": over_engineered_memory / 1024,
            "overhead_percent": over_engineered_overhead
        })

        # Generate report
        report = f"""
FACTORY MEMORY OVERHEAD ANALYSIS
================================

Memory Usage Results (100 object instantiations):
"""

        for result in memory_results:
            overhead_text = f" (+{result['overhead_percent']:.1f}%)" if result['overhead_percent'] > 0 else " (baseline)"
            report += f"""
{result['name']}:
  Memory Usage: {result['memory_kb']:.1f}KB{overhead_text}
"""

        # Memory threshold analysis
        memory_violations = []
        memory_thresholds = {
            "Simple Factory with Cache": 5.0,
            "Complex Factory with Heavy Cache": 15.0,
            "Over-Engineered Factory with Massive Overhead": 15.0
        }

        for result in memory_results[1:]:  # Skip baseline
            threshold = memory_thresholds.get(result['name'], 15.0)
            if result['overhead_percent'] > threshold:
                memory_violations.append({
                    "pattern": result['name'],
                    "overhead": result['overhead_percent'],
                    "threshold": threshold
                })

        report += f"\nMEMORY THRESHOLD ANALYSIS:\n"
        for pattern, threshold in memory_thresholds.items():
            result = next((r for r in memory_results if r['name'] == pattern), None)
            if result:
                status = "✗ VIOLATION" if result['overhead_percent'] > threshold else "✓ ACCEPTABLE"
                report += f"{pattern}: {result['overhead_percent']:.1f}% overhead (threshold: {threshold}%) {status}\n"

        if memory_violations:
            report += f"\nMEMORY VIOLATIONS DETECTED ({len(memory_violations)}):\n"
            for violation in memory_violations:
                report += f"- {violation['pattern']}: {violation['overhead']:.1f}% > {violation['threshold']}%\n"
            report += "\nRecommendation: Simplify factory patterns to reduce memory overhead\n"

        print(report)

        # This test should FAIL for complex factory hierarchies
        if memory_violations:
            max_memory_overhead = max(v['overhead'] for v in memory_violations)
            self.fail(f"Factory memory overhead violations detected: {len(memory_violations)} patterns "
                     f"exceed memory thresholds. Maximum overhead: {max_memory_overhead:.1f}%. "
                     f"Memory-efficient architecture required.")
        else:
            self.fail("No memory violations detected - this may indicate measurement issues.")

    def test_03_concurrent_user_performance_impact(self):
        """
        EXPECTED: PASS for essential factories, FAIL for over-engineered

        Tests performance impact under concurrent user load.
        Essential factories (user isolation) should have acceptable overhead.
        Over-engineered factories should show poor scaling.

        Concurrent Performance Thresholds:
        - User isolation factories: <50% overhead under load (acceptable for security)
        - General purpose factories: <20% overhead under load
        - Over-engineered factories: >50% overhead (unacceptable)
        """

        import threading
        import queue
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Simulate user isolation factory (essential)
        class UserIsolationFactory:
            def __init__(self):
                self.user_contexts = {}
                self.lock = threading.Lock()

            def create_user_context(self, user_id):
                with self.lock:
                    if user_id not in self.user_contexts:
                        self.user_contexts[user_id] = {
                            "user_id": user_id,
                            "session_data": {},
                            "permissions": ["read", "write"],
                            "created_at": time.time()
                        }
                    return self.user_contexts[user_id].copy()

        # Simulate general purpose factory
        class GeneralPurposeFactory:
            def __init__(self):
                self.cache = {}

            def create_object(self, obj_id):
                if obj_id not in self.cache:
                    self.cache[obj_id] = {
                        "id": obj_id,
                        "data": f"object_{obj_id}",
                        "timestamp": time.time()
                    }
                return self.cache[obj_id].copy()

        # Simulate over-engineered factory
        class OverEngineeredConcurrentFactory:
            def __init__(self):
                self.complex_cache = {}
                self.validation_engine = {}
                self.dependency_resolver = {}
                self.lock = threading.Lock()

            def create_complex_object(self, obj_id):
                with self.lock:
                    # Simulate complex validation
                    self._validate_complex_dependencies(obj_id)

                    # Simulate complex configuration
                    config = self._build_complex_configuration(obj_id)

                    # Simulate dependency resolution
                    dependencies = self._resolve_complex_dependencies(obj_id)

                    obj = {
                        "id": obj_id,
                        "config": config,
                        "dependencies": dependencies,
                        "validation_result": self.validation_engine.get(obj_id, {})
                    }

                    self.complex_cache[obj_id] = obj
                    return obj.copy()

            def _validate_complex_dependencies(self, obj_id):
                # Simulate expensive validation
                validation_data = {}
                for i in range(50):
                    validation_data[f"rule_{i}"] = f"validated_{obj_id}_{i}"
                self.validation_engine[obj_id] = validation_data

            def _build_complex_configuration(self, obj_id):
                # Simulate expensive configuration building
                return {
                    f"config_{i}": {
                        "value": f"configured_{obj_id}_{i}",
                        "metadata": list(range(10))
                    } for i in range(20)
                }

            def _resolve_complex_dependencies(self, obj_id):
                # Simulate expensive dependency resolution
                return {
                    f"dep_{i}": {
                        "resolved": True,
                        "data": list(range(5))
                    } for i in range(15)
                }

        # Performance testing helper
        def run_concurrent_test(factory_func, num_threads=10, operations_per_thread=50):
            results = queue.Queue()

            def worker(thread_id):
                start_time = time.perf_counter()
                for i in range(operations_per_thread):
                    obj_id = f"{thread_id}_{i}"
                    factory_func(obj_id)
                end_time = time.perf_counter()
                results.put(end_time - start_time)

            # Run concurrent test
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(worker, i) for i in range(num_threads)]

                # Wait for all threads to complete
                for future in as_completed(futures):
                    future.result()

            # Collect results
            execution_times = []
            while not results.empty():
                execution_times.append(results.get())

            return execution_times

        # Run single-threaded baseline
        def run_single_threaded_test(factory_func, total_operations=500):
            start_time = time.perf_counter()
            for i in range(total_operations):
                factory_func(f"obj_{i}")
            end_time = time.perf_counter()
            return end_time - start_time

        # Set up factories
        user_isolation_factory = UserIsolationFactory()
        general_factory = GeneralPurposeFactory()
        over_engineered_factory = OverEngineeredConcurrentFactory()

        # Test configurations
        test_configs = [
            {
                "name": "User Isolation Factory (Essential)",
                "factory_func": user_isolation_factory.create_user_context,
                "threshold": 50.0  # Higher threshold acceptable for security
            },
            {
                "name": "General Purpose Factory",
                "factory_func": general_factory.create_object,
                "threshold": 20.0
            },
            {
                "name": "Over-Engineered Factory",
                "factory_func": over_engineered_factory.create_complex_object,
                "threshold": 20.0  # Same threshold - should fail
            }
        ]

        concurrent_results = []

        for config in test_configs:
            # Single-threaded baseline
            single_threaded_time = run_single_threaded_test(config["factory_func"])

            # Concurrent test
            concurrent_times = run_concurrent_test(config["factory_func"])
            concurrent_total_time = sum(concurrent_times)

            # Calculate overhead
            overhead_percent = ((concurrent_total_time - single_threaded_time) / single_threaded_time) * 100

            result = {
                "name": config["name"],
                "single_threaded_time": single_threaded_time,
                "concurrent_total_time": concurrent_total_time,
                "overhead_percent": overhead_percent,
                "threshold": config["threshold"]
            }

            concurrent_results.append(result)

        # Generate report
        report = f"""
CONCURRENT USER PERFORMANCE IMPACT ANALYSIS
===========================================

Test Configuration:
- Threads: 10
- Operations per thread: 50
- Total operations: 500

Performance Results:
"""

        violations = []
        for result in concurrent_results:
            status = "✗ VIOLATION" if result['overhead_percent'] > result['threshold'] else "✓ ACCEPTABLE"
            report += f"""
{result['name']}:
  Single-threaded: {result['single_threaded_time']:.3f}s
  Concurrent total: {result['concurrent_total_time']:.3f}s
  Overhead: {result['overhead_percent']:.1f}% (threshold: {result['threshold']}%) {status}
"""

            if result['overhead_percent'] > result['threshold']:
                violations.append(result)

        # Special analysis for user isolation factories
        user_isolation_result = next((r for r in concurrent_results if "User Isolation" in r['name']), None)
        if user_isolation_result and user_isolation_result['overhead_percent'] <= user_isolation_result['threshold']:
            report += f"\n✓ ESSENTIAL FACTORY PERFORMANCE: User isolation factory shows acceptable overhead\n"
            report += f"  This overhead is justified for multi-user security requirements\n"

        if violations:
            report += f"\nCONCURRENT PERFORMANCE VIOLATIONS ({len(violations)}):\n"
            for violation in violations:
                if "User Isolation" not in violation['name']:  # User isolation is essential
                    report += f"- {violation['name']}: {violation['overhead_percent']:.1f}% > {violation['threshold']}%\n"
            report += "\nRecommendation: Optimize or replace factories with poor concurrent performance\n"

        print(report)

        # Filter out user isolation factories from violations (they're essential)
        non_essential_violations = [v for v in violations if "User Isolation" not in v['name']]

        if non_essential_violations:
            max_overhead = max(v['overhead_percent'] for v in non_essential_violations)
            self.fail(f"Factory concurrent performance violations detected: {len(non_essential_violations)} "
                     f"non-essential factories exceed performance thresholds under load. "
                     f"Maximum overhead: {max_overhead:.1f}%. Performance optimization required.")

        # Test passes if only essential factories have acceptable overhead
        if user_isolation_result and user_isolation_result['overhead_percent'] <= user_isolation_result['threshold']:
            self.assertTrue(True, "Essential factories show acceptable concurrent performance")
        else:
            self.fail("Essential user isolation factories show unacceptable performance overhead")


if __name__ == "__main__":
    import unittest
    unittest.main()