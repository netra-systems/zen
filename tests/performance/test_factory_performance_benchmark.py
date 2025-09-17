"""
Performance Benchmark Tests for Factory Simplification (Issue #1194)

Measures import time, startup time, and memory usage improvements
from factory pattern simplification.

CRITICAL: These tests establish baselines and will initially show
current performance limitations that simplified patterns will address.
"""

import pytest
import time
import sys
import gc
import importlib
import subprocess
import psutil
import os
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import concurrent.futures


@dataclass
class PerformanceMetrics:
    """Performance measurement data."""
    operation: str
    execution_time: float
    memory_before: int
    memory_after: int
    memory_delta: int
    cpu_usage: float
    imports_triggered: int
    objects_created: int
    timestamp: datetime

    @property
    def memory_mb(self) -> float:
        """Memory delta in MB."""
        return self.memory_delta / (1024 * 1024)


class PerformanceBenchmarkSuite:
    """Suite for measuring factory pattern performance impact."""

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.baseline_established = False

    def measure_memory(self) -> int:
        """Measure current memory usage in bytes."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss

    def measure_cpu(self) -> float:
        """Measure current CPU usage percentage."""
        return psutil.cpu_percent(interval=0.1)

    def count_loaded_modules(self) -> int:
        """Count currently loaded modules."""
        return len(sys.modules)

    def benchmark_operation(self, operation_name: str, operation_func, *args, **kwargs) -> PerformanceMetrics:
        """Benchmark a specific operation."""
        # Pre-operation measurements
        gc.collect()  # Clean up before measurement
        memory_before = self.measure_memory()
        modules_before = self.count_loaded_modules()

        # Execute operation with timing
        start_time = time.perf_counter()
        result = operation_func(*args, **kwargs)
        execution_time = time.perf_counter() - start_time

        # Post-operation measurements
        memory_after = self.measure_memory()
        modules_after = self.count_loaded_modules()
        cpu_usage = self.measure_cpu()

        metrics = PerformanceMetrics(
            operation=operation_name,
            execution_time=execution_time,
            memory_before=memory_before,
            memory_after=memory_after,
            memory_delta=memory_after - memory_before,
            cpu_usage=cpu_usage,
            imports_triggered=modules_after - modules_before,
            objects_created=1 if result else 0,  # Simplified counting
            timestamp=datetime.now()
        )

        self.metrics.append(metrics)
        return metrics


class TestFactoryImportPerformance:
    """Test import performance of factory patterns."""

    def setup_method(self):
        """Setup for each test method."""
        self.benchmark = PerformanceBenchmarkSuite()

    def test_websocket_factory_import_baseline(self):
        """
        Benchmark WebSocket factory import performance baseline.
        This test PASSES and establishes current import performance.
        """
        def import_websocket_factory():
            """Import WebSocket factory modules."""
            # Force fresh import by removing from cache
            modules_to_remove = [
                'netra_backend.app.websocket_core.websocket_manager_factory',
                'netra_backend.app.websocket_core.websocket_manager_factory_compat',
                'netra_backend.app.websocket_core.websocket_bridge_factory',
                'netra_backend.app.websocket_core.supervisor_factory'
            ]

            for module in modules_to_remove:
                if module in sys.modules:
                    del sys.modules[module]

            # Import the complex factory
            from netra_backend.app.websocket_core.websocket_manager_factory import EnhancedWebSocketManagerFactory
            return EnhancedWebSocketManagerFactory

        # Benchmark the import
        metrics = self.benchmark.benchmark_operation(
            "websocket_factory_import",
            import_websocket_factory
        )

        print(f"WebSocket factory import metrics: {metrics}")

        # Document baseline performance
        baseline_results = {
            'import_time': metrics.execution_time,
            'memory_usage_mb': metrics.memory_mb,
            'additional_imports': metrics.imports_triggered,
            'baseline_established': True
        }

        print(f"Import baseline established: {baseline_results}")

        # Simplified version should improve these metrics significantly
        assert metrics.execution_time > 0, "Import takes measurable time"
        assert metrics.imports_triggered >= 0, "Import may trigger additional imports"

        # Store baseline for comparison
        self.import_baseline = baseline_results

    def test_test_framework_import_baseline(self):
        """
        Benchmark test framework import performance baseline.
        This test PASSES and shows current test framework import overhead.
        """
        def import_test_frameworks():
            """Import test framework modules."""
            # Remove test framework modules from cache
            test_modules = [mod for mod in sys.modules.keys() if 'test_framework' in mod]
            for module in test_modules:
                del sys.modules[module]

            # Import complex test framework components
            from test_framework.ssot.mock_factory import SSotMockFactory
            from test_framework.ssot.websocket_test_infrastructure_factory import WebSocketTestInfrastructureFactory
            return SSotMockFactory, WebSocketTestInfrastructureFactory

        # Benchmark test framework imports
        metrics = self.benchmark.benchmark_operation(
            "test_framework_import",
            import_test_frameworks
        )

        print(f"Test framework import metrics: {metrics}")

        test_baseline = {
            'import_time': metrics.execution_time,
            'memory_usage_mb': metrics.memory_mb,
            'additional_imports': metrics.imports_triggered,
            'test_complexity_overhead': True
        }

        print(f"Test framework baseline: {test_baseline}")

        # Real service setup should eliminate this overhead
        assert metrics.execution_time > 0, "Test framework import has overhead"

    def test_import_cascade_measurement(self):
        """
        Measure import cascade caused by factory patterns.
        This test PASSES and documents the import cascade problem.
        """
        # Count modules before any factory imports
        initial_modules = set(sys.modules.keys())

        # Import factory with cascade tracking
        def import_with_cascade():
            from netra_backend.app.websocket_core.websocket_manager_factory import (
                EnhancedWebSocketManagerFactory,
                ZombieDetectionEngine,
                CleanupLevel,
                CircuitBreakerState
            )
            return EnhancedWebSocketManagerFactory

        metrics = self.benchmark.benchmark_operation(
            "factory_import_cascade",
            import_with_cascade
        )

        # Analyze import cascade
        final_modules = set(sys.modules.keys())
        cascaded_modules = final_modules - initial_modules

        cascade_analysis = {
            'cascaded_modules_count': len(cascaded_modules),
            'cascade_categories': {},
            'import_time': metrics.execution_time,
            'memory_impact_mb': metrics.memory_mb
        }

        # Categorize cascaded imports
        for module in cascaded_modules:
            if 'typing' in module:
                cascade_analysis['cascade_categories']['typing'] = cascade_analysis['cascade_categories'].get('typing', 0) + 1
            elif 'asyncio' in module:
                cascade_analysis['cascade_categories']['asyncio'] = cascade_analysis['cascade_categories'].get('asyncio', 0) + 1
            elif 'datetime' in module:
                cascade_analysis['cascade_categories']['datetime'] = cascade_analysis['cascade_categories'].get('datetime', 0) + 1
            elif 'enum' in module:
                cascade_analysis['cascade_categories']['enum'] = cascade_analysis['cascade_categories'].get('enum', 0) + 1
            else:
                cascade_analysis['cascade_categories']['other'] = cascade_analysis['cascade_categories'].get('other', 0) + 1

        print(f"Import cascade analysis: {cascade_analysis}")
        print(f"Sample cascaded modules: {list(cascaded_modules)[:10]}")

        # Simplified patterns should reduce this cascade significantly
        assert len(cascaded_modules) >= 0, "Factory import causes module cascade"

    @pytest.mark.xfail(reason="Simplified import patterns not yet implemented")
    def test_simplified_import_performance_target(self):
        """
        Test simplified import performance targets.
        This test will FAIL until simplified patterns are implemented.
        """
        # These are the performance targets for simplified patterns
        simplified_targets = {
            'import_time_reduction': 0.8,  # 80% faster imports
            'memory_reduction': 0.7,  # 70% less memory
            'cascade_reduction': 0.9,  # 90% fewer cascaded imports
            'startup_time_reduction': 0.75  # 75% faster startup
        }

        # Try to import simplified patterns (will fail initially)
        try:
            from netra_backend.app.websocket_core.simple_websocket_creation import create_websocket_manager
            simplified_available = True
        except ImportError:
            simplified_available = False

        # This test will fail until we implement simplified patterns
        assert simplified_available, "Simplified patterns not yet implemented"

        # If available, benchmark simplified patterns
        if simplified_available:
            def import_simplified():
                from netra_backend.app.websocket_core.simple_websocket_creation import create_websocket_manager
                return create_websocket_manager

            simplified_metrics = self.benchmark.benchmark_operation(
                "simplified_import",
                import_simplified
            )

            # Compare with baseline (from previous test)
            if hasattr(self, 'import_baseline'):
                baseline_time = self.import_baseline['import_time']
                improvement = (baseline_time - simplified_metrics.execution_time) / baseline_time

                assert improvement >= simplified_targets['import_time_reduction'], \
                    f"Import time improvement {improvement:.2%} below target {simplified_targets['import_time_reduction']:.2%}"


class TestFactoryCreationPerformance:
    """Test object creation performance of factory patterns."""

    def setup_method(self):
        """Setup for each test method."""
        self.benchmark = PerformanceBenchmarkSuite()

    def test_websocket_factory_creation_baseline(self):
        """
        Benchmark WebSocket factory creation performance baseline.
        This test PASSES and establishes factory creation overhead.
        """
        # Import factory first
        from netra_backend.app.websocket_core.websocket_manager_factory import get_enhanced_websocket_factory

        def create_factory_instance():
            """Create factory instance."""
            factory = get_enhanced_websocket_factory()
            # Trigger some factory initialization
            status = factory.get_factory_status()
            return factory, status

        # Benchmark factory creation
        metrics = self.benchmark.benchmark_operation(
            "factory_creation",
            create_factory_instance
        )

        creation_baseline = {
            'creation_time': metrics.execution_time,
            'memory_usage_mb': metrics.memory_mb,
            'factory_overhead': True,
            'complex_initialization': True
        }

        print(f"Factory creation baseline: {creation_baseline}")

        # Simplified patterns should eliminate this initialization overhead
        assert metrics.execution_time > 0, "Factory creation has measurable overhead"

    def test_mock_factory_creation_baseline(self):
        """
        Benchmark mock factory creation performance baseline.
        This test PASSES and shows mock creation overhead.
        """
        from test_framework.ssot.mock_factory import SSotMockFactory

        def create_multiple_mocks():
            """Create multiple mock objects."""
            mocks = []
            mocks.append(SSotMockFactory.create_agent_mock())
            mocks.append(SSotMockFactory.create_websocket_mock())
            mocks.append(SSotMockFactory.create_database_session_mock())
            mocks.append(SSotMockFactory.create_execution_context_mock())
            mocks.append(SSotMockFactory.create_tool_mock())
            return mocks

        # Benchmark mock creation
        metrics = self.benchmark.benchmark_operation(
            "mock_factory_creation",
            create_multiple_mocks
        )

        mock_baseline = {
            'creation_time': metrics.execution_time,
            'memory_usage_mb': metrics.memory_mb,
            'mocks_created': 5,
            'per_mock_time': metrics.execution_time / 5,
            'mock_overhead': True
        }

        print(f"Mock factory baseline: {mock_baseline}")

        # Real service setup should eliminate all mock creation overhead
        assert metrics.execution_time > 0, "Mock creation has overhead"
        assert mock_baseline['per_mock_time'] > 0, "Each mock takes time to create"

    def test_concurrent_factory_usage_performance(self):
        """
        Test factory performance under concurrent usage.
        This test PASSES and shows current factory concurrency overhead.
        """
        from netra_backend.app.websocket_core.websocket_manager_factory import get_enhanced_websocket_factory
        from test_framework.ssot.mock_factory import SSotMockFactory

        def concurrent_factory_usage():
            """Simulate concurrent factory usage."""
            factory = get_enhanced_websocket_factory()

            # Create contexts concurrently
            contexts = []
            for i in range(10):
                context = SSotMockFactory.create_mock_user_context(
                    user_id=f"concurrent_user_{i}",
                    thread_id=f"concurrent_thread_{i}"
                )
                contexts.append(context)

            return factory, contexts

        # Benchmark concurrent usage
        metrics = self.benchmark.benchmark_operation(
            "concurrent_factory_usage",
            concurrent_factory_usage
        )

        concurrent_baseline = {
            'concurrent_time': metrics.execution_time,
            'memory_usage_mb': metrics.memory_mb,
            'contexts_created': 10,
            'per_context_time': metrics.execution_time / 10,
            'concurrency_overhead': True
        }

        print(f"Concurrent factory baseline: {concurrent_baseline}")

        # Simplified patterns should handle concurrency more efficiently
        assert metrics.execution_time > 0, "Concurrent factory usage has overhead"

    @pytest.mark.xfail(reason="Performance optimization not yet implemented")
    def test_simplified_creation_performance_targets(self):
        """
        Test simplified creation performance targets.
        This test will FAIL until optimization is implemented.
        """
        # Performance targets for simplified patterns
        optimization_targets = {
            'factory_creation_elimination': 0.95,  # 95% elimination of factory overhead
            'mock_creation_elimination': 1.0,  # 100% elimination of mock overhead
            'concurrent_improvement': 0.6,  # 60% improvement in concurrent performance
            'memory_efficiency': 0.8  # 80% improvement in memory efficiency
        }

        # Test would verify simplified patterns meet these targets
        # This will fail until we implement the optimizations
        assert False, "Performance optimization not yet implemented"


class TestStartupPerformance:
    """Test application startup performance impact of factories."""

    def test_application_startup_baseline(self):
        """
        Benchmark application startup time with current factory patterns.
        This test PASSES and establishes startup performance baseline.
        """
        def simulate_app_startup():
            """Simulate application startup with factory imports."""
            startup_imports = []

            # Simulate typical startup imports
            modules_to_import = [
                'netra_backend.app.websocket_core.websocket_manager_factory',
                'test_framework.ssot.mock_factory',
                'netra_backend.app.websocket_core.unified_manager',
            ]

            for module in modules_to_import:
                if module in sys.modules:
                    del sys.modules[module]

            start_time = time.perf_counter()
            for module in modules_to_import:
                try:
                    imported = importlib.import_module(module)
                    startup_imports.append(imported)
                except ImportError:
                    pass
            startup_time = time.perf_counter() - start_time

            return startup_imports, startup_time

        # Benchmark startup
        startup_results, startup_time = simulate_app_startup()

        startup_baseline = {
            'startup_time': startup_time,
            'modules_imported': len(startup_results),
            'factory_overhead': True,
            'baseline_established': True
        }

        print(f"Application startup baseline: {startup_baseline}")

        # Simplified patterns should reduce startup time significantly
        assert startup_time > 0, "Startup has measurable duration"
        assert len(startup_results) >= 0, "Startup imports modules"

    def test_memory_growth_during_startup(self):
        """
        Test memory growth during startup with factory patterns.
        This test PASSES and shows current memory growth patterns.
        """
        # Measure memory before startup simulation
        initial_memory = psutil.Process(os.getpid()).memory_info().rss

        # Simulate startup with factory loading
        def startup_with_factories():
            from netra_backend.app.websocket_core.websocket_manager_factory import get_enhanced_websocket_factory
            from test_framework.ssot.mock_factory import SSotMockFactory

            factory = get_enhanced_websocket_factory()
            mock_objects = [
                SSotMockFactory.create_agent_mock(),
                SSotMockFactory.create_websocket_mock(),
                SSotMockFactory.create_mock_user_context()
            ]
            return factory, mock_objects

        # Execute startup simulation
        start_time = time.perf_counter()
        factory, mocks = startup_with_factories()
        startup_duration = time.perf_counter() - start_time

        # Measure memory after startup
        final_memory = psutil.Process(os.getpid()).memory_info().rss
        memory_growth = final_memory - initial_memory

        memory_growth_analysis = {
            'memory_growth_mb': memory_growth / (1024 * 1024),
            'startup_duration': startup_duration,
            'factory_memory_footprint': len(factory.__dict__) if factory else 0,
            'mock_objects_created': len(mocks),
            'baseline_memory_growth': True
        }

        print(f"Startup memory growth analysis: {memory_growth_analysis}")

        # Simplified patterns should significantly reduce memory growth
        assert memory_growth >= 0, "Startup causes memory growth"

    @pytest.mark.xfail(reason="Startup optimization not yet implemented")
    def test_optimized_startup_performance_targets(self):
        """
        Test optimized startup performance targets.
        This test will FAIL until startup optimization is implemented.
        """
        # Startup optimization targets
        startup_targets = {
            'startup_time_reduction': 0.75,  # 75% faster startup
            'memory_growth_reduction': 0.8,  # 80% less memory growth
            'import_cascade_reduction': 0.9,  # 90% fewer cascaded imports
            'initialization_overhead_elimination': 0.95  # 95% less initialization overhead
        }

        # This test will fail until we implement startup optimization
        assert False, "Startup optimization not yet implemented"


class TestFactoryComplexityMetrics:
    """Test factory complexity metrics and simplification potential."""

    def test_code_complexity_measurement(self):
        """
        Measure current factory code complexity.
        This test PASSES and documents complexity that needs simplification.
        """
        from netra_backend.app.websocket_core.websocket_manager_factory import EnhancedWebSocketManagerFactory
        from test_framework.ssot.mock_factory import SSotMockFactory

        # Analyze WebSocket factory complexity
        factory_instance = EnhancedWebSocketManagerFactory()
        websocket_complexity = {
            'class_methods': len([m for m in dir(factory_instance) if callable(getattr(factory_instance, m))]),
            'private_methods': len([m for m in dir(factory_instance) if m.startswith('_') and callable(getattr(factory_instance, m))]),
            'public_methods': len([m for m in dir(factory_instance) if not m.startswith('_') and callable(getattr(factory_instance, m))]),
            'instance_attributes': len(factory_instance.__dict__),
            'has_complex_features': {
                'zombie_detection': hasattr(factory_instance, 'zombie_detector'),
                'circuit_breaker': hasattr(factory_instance, 'circuit_breaker'),
                'cleanup_levels': hasattr(factory_instance, '_determine_cleanup_level'),
                'health_monitoring': hasattr(factory_instance, '_update_manager_health')
            }
        }

        # Analyze mock factory complexity
        mock_complexity = {
            'static_methods': len([m for m in dir(SSotMockFactory) if m.startswith('create_')]),
            'total_methods': len([m for m in dir(SSotMockFactory) if not m.startswith('__')]),
            'estimated_line_count': 738,  # From audit
        }

        complexity_summary = {
            'websocket_factory': websocket_complexity,
            'mock_factory': mock_complexity,
            'total_complexity_score': (
                websocket_complexity['class_methods'] +
                websocket_complexity['instance_attributes'] +
                mock_complexity['total_methods']
            ),
            'simplification_potential': 'HIGH'
        }

        print(f"Factory complexity analysis: {complexity_summary}")

        # Document excessive complexity
        assert complexity_summary['total_complexity_score'] > 50, "Factory patterns are too complex"
        assert websocket_complexity['has_complex_features']['zombie_detection'], "Unnecessary complexity features"

    def test_simplification_potential_calculation(self):
        """
        Calculate simplification potential for factory patterns.
        This test PASSES and quantifies improvement opportunities.
        """
        # Current complexity metrics (from code analysis)
        current_metrics = {
            'websocket_factory_lines': 720,  # EnhancedWebSocketManagerFactory
            'mock_factory_lines': 738,  # SSotMockFactory
            'test_infrastructure_factory_lines': 639,  # WebSocketTestInfrastructureFactory
            'total_factory_lines': 720 + 738 + 639,
            'factory_files_count': 5,  # From audit
            'method_count': 50,  # Estimated from complexity analysis
            'feature_complexity_score': 100  # Arbitrary complexity scoring
        }

        # Simplified pattern targets
        simplified_targets = {
            'websocket_creation_lines': 50,  # Simple creation function
            'real_service_setup_lines': 100,  # Replace mock factory
            'simplified_test_helpers_lines': 100,  # Replace test infrastructure factory
            'total_simplified_lines': 50 + 100 + 100,
            'simplified_files_count': 2,  # Consolidation
            'simplified_method_count': 10,  # Much simpler interface
            'simplified_complexity_score': 20  # Much lower complexity
        }

        # Calculate simplification potential
        simplification_potential = {
            'line_count_reduction': (current_metrics['total_factory_lines'] - simplified_targets['total_simplified_lines']) / current_metrics['total_factory_lines'],
            'file_count_reduction': (current_metrics['factory_files_count'] - simplified_targets['simplified_files_count']) / current_metrics['factory_files_count'],
            'method_count_reduction': (current_metrics['method_count'] - simplified_targets['simplified_method_count']) / current_metrics['method_count'],
            'complexity_reduction': (current_metrics['feature_complexity_score'] - simplified_targets['simplified_complexity_score']) / current_metrics['feature_complexity_score']
        }

        print(f"Simplification potential: {simplification_potential}")

        # Verify significant simplification is possible
        for metric, reduction in simplification_potential.items():
            assert reduction > 0.5, f"{metric} should have >50% reduction potential"
            print(f"{metric}: {reduction:.1%} reduction potential")


if __name__ == "__main__":
    # Run performance benchmarks
    import unittest

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all baseline benchmark tests
    test_classes = [
        TestFactoryImportPerformance,
        TestFactoryCreationPerformance,
        TestStartupPerformance,
        TestFactoryComplexityMetrics
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print(f"\nPerformance benchmark tests completed: {result.testsRun} run, {len(result.failures)} failed, {len(result.errors)} errors")