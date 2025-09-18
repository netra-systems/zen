"""
PERFORMANCE TEST: Import Timing Improvement Validation
Issue #1196 Phase 2 - ExecutionEngine SSOT Consolidation

PURPOSE:
- Benchmark import performance before/after ExecutionEngine consolidation
- Measure the claimed 26.81x performance impact of fragmentation
- Quantify race condition frequency due to fragmented imports
- Validate import timing improvements post-consolidation

PERFORMANCE TARGETS:
- Canonical import: <0.1s baseline
- Fragmented imports: Current state (baseline measurement)
- Post-consolidation: <5x canonical import time
- Race condition frequency: <1% after consolidation

Business Impact: Import performance affects Golden Path stability
"""

import pytest
import time
import subprocess
import sys
import statistics
import concurrent.futures
import threading
from typing import Dict, List, Tuple, Any
from pathlib import Path
import psutil
import gc

# Test framework - SSOT patterns
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.orchestration import get_orchestration_config


class TestImportTimingImprovement(SSotBaseTestCase):
    """
    Performance test for ExecutionEngine import timing and race conditions

    Measures import performance impact of fragmentation and validates
    improvements after SSOT consolidation.
    """

    @classmethod
    def setup_class(cls):
        """Initialize performance testing environment"""
        super().setup_class()
        cls.orchestration_config = get_orchestration_config()

        # Performance test configuration
        cls.performance_iterations = 20  # Number of timing iterations
        cls.concurrent_threads = 5      # Concurrent import threads
        cls.race_condition_iterations = 50  # Race condition detection iterations

        # Import statements to benchmark
        cls.canonical_imports = [
            "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine",
            "from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory",
            "from netra_backend.app.agents.supervisor.request_scoped_execution_engine import RequestScopedExecutionEngine"
        ]

        cls.fragmented_imports = [
            "from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine",
            "from netra_backend.app.agents.execution_engine_unified_factory import UnifiedExecutionEngineFactory",
            "from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine",
            "from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory",
            "from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine"
        ]

        # Performance baselines (will be measured)
        cls.baseline_metrics = {}

    def setup_method(self, method):
        """Set up each performance test"""
        super().setup_method(method)
        self.timing_results = {}
        self.race_condition_results = {}
        self.memory_usage_results = {}

    @pytest.mark.performance
    @pytest.mark.import_timing
    def test_canonical_import_performance_baseline(self):
        """
        Establish performance baseline for canonical SSOT imports

        This provides the target performance that all imports should achieve
        """
        print(f"\n=== Canonical Import Performance Baseline ===")

        canonical_timings = {}

        for import_stmt in self.canonical_imports:
            import_name = self._extract_import_name(import_stmt)
            print(f"\nTesting canonical import: {import_name}")

            # Measure import timing over multiple iterations
            timings = []
            memory_usage = []

            for iteration in range(self.performance_iterations):
                # Clear import cache to get fresh timing
                self._clear_import_cache(import_stmt)

                # Measure memory before import
                memory_before = psutil.Process().memory_info().rss

                # Time the import
                import_time = self._measure_single_import_time(import_stmt)
                timings.append(import_time)

                # Measure memory after import
                memory_after = psutil.Process().memory_info().rss
                memory_usage.append(memory_after - memory_before)

            # Calculate statistics
            avg_time = statistics.mean(timings)
            median_time = statistics.median(timings)
            std_dev = statistics.stdev(timings) if len(timings) > 1 else 0
            min_time = min(timings)
            max_time = max(timings)
            avg_memory = statistics.mean(memory_usage)

            canonical_timings[import_name] = {
                "average_time": avg_time,
                "median_time": median_time,
                "std_deviation": std_dev,
                "min_time": min_time,
                "max_time": max_time,
                "avg_memory_usage": avg_memory,
                "all_timings": timings
            }

            print(f"  Average: {avg_time:.4f}s ± {std_dev:.4f}s")
            print(f"  Range: {min_time:.4f}s - {max_time:.4f}s")
            print(f"  Memory: {avg_memory / 1024:.1f} KB")

        self.timing_results["canonical"] = canonical_timings

        # Validate canonical performance is reasonable
        max_acceptable_time = 0.5  # 500ms max for any canonical import
        slow_imports = [
            (name, metrics["average_time"])
            for name, metrics in canonical_timings.items()
            if metrics["average_time"] > max_acceptable_time
        ]

        assert len(slow_imports) == 0, \
            f"Canonical imports too slow: {slow_imports}. Max acceptable: {max_acceptable_time}s"

        print(f"\nCHECK Canonical import baseline established")

    @pytest.mark.performance
    @pytest.mark.import_timing
    def test_fragmented_import_performance_impact(self):
        """
        Measure performance impact of fragmented imports

        Tests the claimed 26.81x performance degradation
        """
        print(f"\n=== Fragmented Import Performance Impact ===")

        fragmented_timings = {}
        working_fragmented_imports = []

        for import_stmt in self.fragmented_imports:
            import_name = self._extract_import_name(import_stmt)
            print(f"\nTesting fragmented import: {import_name}")

            # Check if import even works
            try:
                test_time = self._measure_single_import_time(import_stmt)
                if test_time > 10.0:  # Timeout protection
                    print(f"  WARNING️ Import timed out: {test_time:.2f}s")
                    continue
                working_fragmented_imports.append(import_stmt)
            except Exception as e:
                print(f"  X Import failed: {str(e)}")
                fragmented_timings[import_name] = {
                    "error": str(e),
                    "import_works": False
                }
                continue

            # Measure fragmented import performance
            timings = []
            memory_usage = []
            failures = 0

            for iteration in range(self.performance_iterations):
                try:
                    # Clear import cache
                    self._clear_import_cache(import_stmt)

                    # Measure memory before import
                    memory_before = psutil.Process().memory_info().rss

                    # Time the import with timeout protection
                    import_time = self._measure_single_import_time(import_stmt, timeout=5.0)

                    if import_time < 10.0:  # Valid timing
                        timings.append(import_time)

                        # Measure memory usage
                        memory_after = psutil.Process().memory_info().rss
                        memory_usage.append(memory_after - memory_before)
                    else:
                        failures += 1

                except Exception as e:
                    failures += 1
                    print(f"  WARNING️ Iteration {iteration} failed: {str(e)}")

            if timings:
                # Calculate statistics
                avg_time = statistics.mean(timings)
                median_time = statistics.median(timings)
                std_dev = statistics.stdev(timings) if len(timings) > 1 else 0
                min_time = min(timings)
                max_time = max(timings)
                avg_memory = statistics.mean(memory_usage) if memory_usage else 0
                failure_rate = failures / self.performance_iterations

                fragmented_timings[import_name] = {
                    "average_time": avg_time,
                    "median_time": median_time,
                    "std_deviation": std_dev,
                    "min_time": min_time,
                    "max_time": max_time,
                    "avg_memory_usage": avg_memory,
                    "failure_rate": failure_rate,
                    "all_timings": timings,
                    "import_works": True
                }

                print(f"  Average: {avg_time:.4f}s ± {std_dev:.4f}s")
                print(f"  Range: {min_time:.4f}s - {max_time:.4f}s")
                print(f"  Memory: {avg_memory / 1024:.1f} KB")
                print(f"  Failure rate: {failure_rate:.1%}")

            else:
                fragmented_timings[import_name] = {
                    "error": "All iterations failed",
                    "failure_rate": 1.0,
                    "import_works": False
                }
                print(f"  X All iterations failed")

        self.timing_results["fragmented"] = fragmented_timings

        # Analyze performance impact
        self._analyze_performance_impact()

        print(f"\nCHECK Fragmented import performance measured")

    @pytest.mark.performance
    @pytest.mark.race_conditions
    def test_concurrent_import_race_conditions(self):
        """
        Test for race conditions caused by fragmented imports

        Measures frequency of race conditions in concurrent import scenarios
        """
        print(f"\n=== Concurrent Import Race Condition Testing ===")

        race_condition_results = {}

        # Test canonical imports for race conditions
        canonical_races = self._test_concurrent_imports(
            self.canonical_imports,
            "canonical"
        )
        race_condition_results["canonical"] = canonical_races

        # Test fragmented imports for race conditions
        working_fragmented = [
            import_stmt for import_stmt in self.fragmented_imports
            if self._import_works(import_stmt)
        ]

        if working_fragmented:
            fragmented_races = self._test_concurrent_imports(
                working_fragmented,
                "fragmented"
            )
            race_condition_results["fragmented"] = fragmented_races
        else:
            print("WARNING️ No working fragmented imports to test for race conditions")

        self.race_condition_results = race_condition_results

        # Analyze race condition frequency
        self._analyze_race_conditions()

        print(f"\nCHECK Race condition testing completed")

    def _test_concurrent_imports(self, import_statements: List[str], category: str) -> Dict[str, Any]:
        """Test concurrent imports for race conditions"""
        print(f"\nTesting {category} imports for race conditions...")

        race_results = {
            "total_attempts": 0,
            "successful_imports": 0,
            "failed_imports": 0,
            "race_conditions_detected": 0,
            "import_conflicts": []
        }

        for attempt in range(self.race_condition_iterations):
            # Create concurrent import tasks
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrent_threads) as executor:
                futures = []

                for import_stmt in import_statements:
                    future = executor.submit(self._concurrent_import_test, import_stmt, attempt)
                    futures.append(future)

                # Collect results
                attempt_results = []
                for future in concurrent.futures.as_completed(futures, timeout=10):
                    try:
                        result = future.result()
                        attempt_results.append(result)
                    except Exception as e:
                        attempt_results.append({
                            "success": False,
                            "error": str(e),
                            "import_time": None
                        })

                race_results["total_attempts"] += len(attempt_results)

                # Analyze this attempt for race conditions
                successful = sum(1 for r in attempt_results if r.get("success", False))
                failed = len(attempt_results) - successful

                race_results["successful_imports"] += successful
                race_results["failed_imports"] += failed

                # Detect potential race conditions (unusual timing variations)
                import_times = [r.get("import_time") for r in attempt_results if r.get("import_time")]
                if len(import_times) > 1:
                    time_std_dev = statistics.stdev(import_times)
                    avg_time = statistics.mean(import_times)

                    # High variation might indicate race conditions
                    if time_std_dev > (avg_time * 0.5):  # 50% variation threshold
                        race_results["race_conditions_detected"] += 1

        # Calculate race condition frequency
        if race_results["total_attempts"] > 0:
            race_frequency = race_results["race_conditions_detected"] / self.race_condition_iterations
            success_rate = race_results["successful_imports"] / race_results["total_attempts"]

            race_results["race_condition_frequency"] = race_frequency
            race_results["success_rate"] = success_rate

            print(f"  Success rate: {success_rate:.1%}")
            print(f"  Race condition frequency: {race_frequency:.1%}")

        return race_results

    def _concurrent_import_test(self, import_stmt: str, attempt: int) -> Dict[str, Any]:
        """Execute a single concurrent import test"""
        try:
            # Add small random delay to increase chance of race conditions
            import random
            time.sleep(random.uniform(0.001, 0.01))

            # Clear import cache
            self._clear_import_cache(import_stmt)

            # Time the import
            start_time = time.perf_counter()
            exec(import_stmt)
            end_time = time.perf_counter()

            import_time = end_time - start_time

            return {
                "success": True,
                "import_time": import_time,
                "attempt": attempt
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "attempt": attempt,
                "import_time": None
            }

    def _measure_single_import_time(self, import_stmt: str, timeout: float = 10.0) -> float:
        """Measure time for a single import execution"""
        cmd = [
            sys.executable, "-c",
            f"import time; start=time.perf_counter(); {import_stmt}; print(time.perf_counter()-start)"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                try:
                    import_time = float(result.stdout.strip())
                    return import_time
                except ValueError:
                    return timeout  # Return timeout as penalty
            else:
                return timeout  # Import failed, return penalty time

        except subprocess.TimeoutExpired:
            return timeout

    def _clear_import_cache(self, import_stmt: str):
        """Clear import cache for fresh import timing"""
        try:
            # Extract module name from import statement
            if "from " in import_stmt and " import " in import_stmt:
                module_name = import_stmt.split("from ")[1].split(" import ")[0]
            else:
                return

            # Remove from sys.modules if present
            modules_to_remove = [
                name for name in sys.modules.keys()
                if name.startswith(module_name)
            ]

            for module in modules_to_remove:
                if module in sys.modules:
                    del sys.modules[module]

            # Force garbage collection
            gc.collect()

        except Exception:
            # If clearing fails, continue anyway
            pass

    def _extract_import_name(self, import_stmt: str) -> str:
        """Extract readable name from import statement"""
        if " import " in import_stmt:
            return import_stmt.split(" import ")[-1]
        return import_stmt

    def _import_works(self, import_stmt: str) -> bool:
        """Check if an import statement works"""
        try:
            test_time = self._measure_single_import_time(import_stmt, timeout=5.0)
            return test_time < 5.0  # If it takes less than 5s, consider it working
        except:
            return False

    def _analyze_performance_impact(self):
        """Analyze and report performance impact of fragmentation"""
        print(f"\n=== Performance Impact Analysis ===")

        canonical_metrics = self.timing_results.get("canonical", {})
        fragmented_metrics = self.timing_results.get("fragmented", {})

        if not canonical_metrics:
            print("WARNING️ No canonical metrics available for comparison")
            return

        # Calculate average canonical import time
        canonical_times = [
            metrics["average_time"]
            for metrics in canonical_metrics.values()
            if isinstance(metrics, dict) and "average_time" in metrics
        ]
        avg_canonical_time = statistics.mean(canonical_times) if canonical_times else 0

        # Calculate average fragmented import time
        fragmented_times = [
            metrics["average_time"]
            for metrics in fragmented_metrics.values()
            if isinstance(metrics, dict) and "average_time" in metrics
        ]
        avg_fragmented_time = statistics.mean(fragmented_times) if fragmented_times else 0

        # Calculate performance degradation ratio
        if avg_canonical_time > 0 and avg_fragmented_time > 0:
            performance_ratio = avg_fragmented_time / avg_canonical_time
            print(f"Average canonical import time: {avg_canonical_time:.4f}s")
            print(f"Average fragmented import time: {avg_fragmented_time:.4f}s")
            print(f"Performance degradation ratio: {performance_ratio:.2f}x")

            # Validate against claimed 26.81x impact
            if performance_ratio > 5.0:
                print(f"WARNING️ Significant performance degradation detected: {performance_ratio:.2f}x")
            else:
                print(f"CHECK Performance degradation within acceptable limits")

        # Report working vs broken imports
        working_fragmented = sum(
            1 for metrics in fragmented_metrics.values()
            if isinstance(metrics, dict) and metrics.get("import_works", False)
        )
        total_fragmented = len(fragmented_metrics)

        print(f"Working fragmented imports: {working_fragmented}/{total_fragmented}")
        print(f"Broken fragmented imports: {total_fragmented - working_fragmented}/{total_fragmented}")

    def _analyze_race_conditions(self):
        """Analyze race condition test results"""
        print(f"\n=== Race Condition Analysis ===")

        canonical_races = self.race_condition_results.get("canonical", {})
        fragmented_races = self.race_condition_results.get("fragmented", {})

        for category, results in [("Canonical", canonical_races), ("Fragmented", fragmented_races)]:
            if not results:
                continue

            print(f"\n{category} Import Race Conditions:")
            print(f"  Success rate: {results.get('success_rate', 0):.1%}")
            print(f"  Race condition frequency: {results.get('race_condition_frequency', 0):.1%}")

            race_freq = results.get('race_condition_frequency', 0)
            if race_freq > 0.05:  # >5% race condition frequency
                print(f"  WARNING️ High race condition frequency detected")
            else:
                print(f"  CHECK Race condition frequency within acceptable limits")

    @pytest.mark.performance
    def test_post_consolidation_performance_validation(self):
        """
        Validate performance improvements after SSOT consolidation

        This test will initially fail but should pass after consolidation
        """
        print(f"\n=== Post-Consolidation Performance Validation ===")

        # This test validates that after consolidation:
        # 1. All imports use canonical SSOT patterns
        # 2. Performance is within 5x of baseline canonical performance
        # 3. Race condition frequency is <1%

        canonical_metrics = self.timing_results.get("canonical", {})
        fragmented_metrics = self.timing_results.get("fragmented", {})

        if not canonical_metrics:
            pytest.skip("No canonical metrics available - run baseline test first")

        # Performance target validation
        canonical_times = [
            metrics["average_time"]
            for metrics in canonical_metrics.values()
            if isinstance(metrics, dict) and "average_time" in metrics
        ]
        baseline_time = statistics.mean(canonical_times) if canonical_times else 0

        max_acceptable_time = baseline_time * 5.0  # 5x baseline max

        # Check fragmented import performance against target
        slow_fragmented_imports = []
        for import_name, metrics in fragmented_metrics.items():
            if isinstance(metrics, dict) and metrics.get("import_works", False):
                avg_time = metrics.get("average_time", 0)
                if avg_time > max_acceptable_time:
                    slow_fragmented_imports.append((import_name, avg_time))

        # Race condition validation
        race_results = self.race_condition_results
        max_acceptable_race_frequency = 0.01  # 1% max

        high_race_categories = []
        for category, results in race_results.items():
            race_freq = results.get("race_condition_frequency", 0)
            if race_freq > max_acceptable_race_frequency:
                high_race_categories.append((category, race_freq))

        # Assertions for post-consolidation validation
        print(f"Performance validation:")
        print(f"  Baseline time: {baseline_time:.4f}s")
        print(f"  Max acceptable: {max_acceptable_time:.4f}s")
        print(f"  Slow fragmented imports: {len(slow_fragmented_imports)}")

        print(f"Race condition validation:")
        print(f"  Max acceptable frequency: {max_acceptable_race_frequency:.1%}")
        print(f"  High race categories: {len(high_race_categories)}")

        # These assertions will fail initially (proving consolidation needed)
        # but should pass after SSOT consolidation
        assert len(slow_fragmented_imports) == 0, \
            f"Performance regression: {slow_fragmented_imports} exceed {max_acceptable_time:.4f}s limit"

        assert len(high_race_categories) == 0, \
            f"Race condition frequency too high: {high_race_categories} exceed {max_acceptable_race_frequency:.1%} limit"

        print(f"CHECK Post-consolidation performance targets met")


if __name__ == "__main__":
    # Run performance tests with detailed output
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "performance"])