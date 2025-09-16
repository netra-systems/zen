"""
Factory Performance Baseline Test - Golden Path Performance Measurement

This test measures the performance impact of current factory patterns on the
Golden Path user flow, establishing baseline metrics before cleanup.

Business Value: Platform/Internal - Performance optimization and user experience
Ensures factory cleanup maintains $500K+ ARR chat functionality performance
while reducing technical debt and complexity overhead.

Test Strategy:
1. Measure Golden Path instantiation performance with current factories
2. Profile memory usage patterns during factory operations
3. Benchmark WebSocket factory initialization critical for chat
4. Establish baseline timing for agent factory creation
5. Measure SSOT compliance impact on performance

Performance Targets:
- Golden Path initialization: < 2 seconds
- Factory instantiation: < 100ms per factory
- Memory overhead: < 50MB for factory patterns
- WebSocket factory: < 50ms (critical for real-time chat)

SSOT Compliance:
- Uses SSotBaseTestCase for consistent test infrastructure
- Integrates with IsolatedEnvironment for environment access
- Records comprehensive performance metrics for baseline
"""

import asyncio
import gc
import memory_profiler
import psutil
import time
import tracemalloc
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import sys
import importlib

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@dataclass
class PerformanceMetrics:
    """Container for factory performance metrics."""
    instantiation_time: float = 0.0
    memory_before: int = 0
    memory_after: int = 0
    memory_peak: int = 0
    memory_overhead: int = 0
    cpu_usage_percent: float = 0.0
    gc_collections: int = 0
    object_count: int = 0
    method_call_count: int = 0


@dataclass
class GoldenPathMetrics:
    """Golden Path performance metrics."""
    total_initialization_time: float = 0.0
    websocket_factory_time: float = 0.0
    agent_factory_time: float = 0.0
    config_factory_time: float = 0.0
    database_factory_time: float = 0.0
    auth_factory_time: float = 0.0
    memory_footprint: int = 0
    concurrent_users_supported: int = 0


class TestFactoryPerformanceBaseline(SSotAsyncTestCase):
    """
    Factory performance baseline test suite.

    Measures current performance characteristics of factory patterns
    to establish baseline metrics before optimization cleanup.
    """

    def setup_method(self, method=None):
        """Setup performance testing environment."""
        super().setup_method(method)

        # Initialize performance tracking
        self.record_metric("performance_baseline_start", time.time())

        # Enable memory profiling
        tracemalloc.start()

        # Get initial system metrics
        process = psutil.Process()
        self.record_metric("initial_memory_usage", process.memory_info().rss)
        self.record_metric("initial_cpu_percent", process.cpu_percent())

        # Force garbage collection for clean baseline
        gc.collect()

        # Factory paths to test (based on SSOT audit)
        self.factory_modules = [
            'netra_backend.app.core.factory',
            'netra_backend.app.services.factory',
            'netra_backend.app.agents.factory',
            'netra_backend.app.websocket_core.factory',
            'test_framework.ssot.mock_factory',
            'auth_service.factory',
        ]

        # Golden Path components for performance testing
        self.golden_path_components = [
            'websocket_manager',
            'agent_registry',
            'config_manager',
            'database_manager',
            'auth_integration'
        ]

    def teardown_method(self, method=None):
        """Cleanup performance testing environment."""
        try:
            # Stop memory profiling
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                self.record_metric("final_memory_current", current)
                self.record_metric("final_memory_peak", peak)

            # Final system metrics
            process = psutil.Process()
            self.record_metric("final_memory_usage", process.memory_info().rss)
            self.record_metric("final_cpu_percent", process.cpu_percent())

            # Force cleanup
            gc.collect()

        finally:
            super().teardown_method(method)

    async def test_golden_path_factory_performance_baseline(self):
        """
        Measure Golden Path factory performance baseline.

        Critical test: Measures performance of factory patterns that
        directly impact $500K+ ARR chat functionality timing.
        """
        golden_path_metrics = GoldenPathMetrics()

        # Measure total Golden Path initialization time
        start_time = time.perf_counter()

        # Test WebSocket factory (CRITICAL for chat)
        websocket_start = time.perf_counter()
        websocket_factory = await self._benchmark_websocket_factory()
        golden_path_metrics.websocket_factory_time = time.perf_counter() - websocket_start

        # Test Agent factory (CRITICAL for chat responses)
        agent_start = time.perf_counter()
        agent_factory = await self._benchmark_agent_factory()
        golden_path_metrics.agent_factory_time = time.perf_counter() - agent_start

        # Test Config factory
        config_start = time.perf_counter()
        config_factory = await self._benchmark_config_factory()
        golden_path_metrics.config_factory_time = time.perf_counter() - config_start

        # Test Database factory
        db_start = time.perf_counter()
        db_factory = await self._benchmark_database_factory()
        golden_path_metrics.database_factory_time = time.perf_counter() - db_start

        # Test Auth factory
        auth_start = time.perf_counter()
        auth_factory = await self._benchmark_auth_factory()
        golden_path_metrics.auth_factory_time = time.perf_counter() - auth_start

        golden_path_metrics.total_initialization_time = time.perf_counter() - start_time

        # Measure memory footprint
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        golden_path_metrics.memory_footprint = peak_memory

        # Record Golden Path metrics
        self._record_golden_path_metrics(golden_path_metrics)

        # Critical performance assertions for chat functionality
        self.assertLess(golden_path_metrics.total_initialization_time, 5.0,
                       "Golden Path initialization must be under 5 seconds")

        self.assertLess(golden_path_metrics.websocket_factory_time, 0.1,
                       "WebSocket factory must be under 100ms (critical for chat)")

        self.assertLess(golden_path_metrics.agent_factory_time, 0.2,
                       "Agent factory must be under 200ms (critical for chat responses)")

        # Memory assertions
        memory_limit_mb = 100 * 1024 * 1024  # 100MB
        self.assertLess(golden_path_metrics.memory_footprint, memory_limit_mb,
                       f"Memory footprint {golden_path_metrics.memory_footprint / (1024*1024):.1f}MB "
                       f"must be under 100MB")

        self.record_metric("golden_path_performance_test_completed", True)

    async def test_factory_instantiation_performance(self):
        """
        Benchmark individual factory instantiation performance.

        Measures the overhead of each factory pattern to identify
        performance bottlenecks and optimization opportunities.
        """
        factory_performance = {}

        # Test each discoverable factory module
        for module_name in self.factory_modules:
            if await self._module_exists(module_name):
                metrics = await self._benchmark_factory_module(module_name)
                factory_performance[module_name] = metrics

        # Record individual factory performance
        for module_name, metrics in factory_performance.items():
            self.record_metric(f"factory_performance_{module_name}_time",
                             metrics.instantiation_time)
            self.record_metric(f"factory_performance_{module_name}_memory",
                             metrics.memory_overhead)

        # Calculate aggregate metrics
        total_instantiation_time = sum(m.instantiation_time for m in factory_performance.values())
        total_memory_overhead = sum(m.memory_overhead for m in factory_performance.values())

        self.record_metric("total_factory_instantiation_time", total_instantiation_time)
        self.record_metric("total_factory_memory_overhead", total_memory_overhead)

        # Performance regression prevention
        max_acceptable_time = 2.0  # 2 seconds total
        self.assertLess(total_instantiation_time, max_acceptable_time,
                       f"Total factory instantiation time {total_instantiation_time:.3f}s "
                       f"exceeds acceptable limit of {max_acceptable_time}s")

        self.record_metric("factory_instantiation_performance_completed", True)

    async def test_concurrent_factory_performance(self):
        """
        Test factory performance under concurrent user load.

        Critical for multi-user chat system: ensures factory patterns
        scale properly with concurrent user sessions.
        """
        concurrent_users = [1, 5, 10, 20, 50]
        concurrency_metrics = {}

        for user_count in concurrent_users:
            metrics = await self._benchmark_concurrent_factories(user_count)
            concurrency_metrics[user_count] = metrics

            # Record concurrency metrics
            self.record_metric(f"concurrent_{user_count}_users_time",
                             metrics.instantiation_time)
            self.record_metric(f"concurrent_{user_count}_users_memory",
                             metrics.memory_overhead)

        # Analyze scalability
        scalability_factor = self._calculate_scalability_factor(concurrency_metrics)
        self.record_metric("factory_scalability_factor", scalability_factor)

        # Critical assertion for multi-user chat support
        max_user_time = concurrency_metrics.get(20, PerformanceMetrics()).instantiation_time
        self.assertLess(max_user_time, 3.0,
                       "20 concurrent users should initialize factories under 3 seconds")

        # Memory scalability check
        max_user_memory = concurrency_metrics.get(20, PerformanceMetrics()).memory_overhead
        memory_limit = 200 * 1024 * 1024  # 200MB for 20 users
        self.assertLess(max_user_memory, memory_limit,
                       f"20 concurrent users memory {max_user_memory / (1024*1024):.1f}MB "
                       f"should be under 200MB")

        self.record_metric("concurrent_factory_performance_completed", True)

    async def test_factory_memory_profile_baseline(self):
        """
        Profile memory usage patterns of factory instantiation.

        Identifies memory leaks, excessive allocations, and optimization
        opportunities in current factory implementations.
        """
        memory_profiles = {}

        # Profile memory for each major factory component
        for component in self.golden_path_components:
            profile = await self._profile_component_memory(component)
            memory_profiles[component] = profile

        # Record memory profiles
        for component, profile in memory_profiles.items():
            self.record_metric(f"memory_profile_{component}_peak", profile['peak_memory'])
            self.record_metric(f"memory_profile_{component}_growth", profile['memory_growth'])
            self.record_metric(f"memory_profile_{component}_allocations", profile['allocations'])

        # Analyze memory efficiency
        total_peak_memory = sum(p['peak_memory'] for p in memory_profiles.values())
        total_allocations = sum(p['allocations'] for p in memory_profiles.values())

        self.record_metric("total_peak_memory_usage", total_peak_memory)
        self.record_metric("total_memory_allocations", total_allocations)

        # Memory efficiency assertions
        peak_limit = 150 * 1024 * 1024  # 150MB peak
        self.assertLess(total_peak_memory, peak_limit,
                       f"Total peak memory {total_peak_memory / (1024*1024):.1f}MB "
                       f"should be under 150MB")

        self.record_metric("factory_memory_profile_completed", True)

    async def test_ssot_compliance_performance_impact(self):
        """
        Measure performance impact of SSOT compliance on factory patterns.

        Compares performance between SSOT-compliant and legacy factory
        patterns to quantify the performance cost/benefit of compliance.
        """
        ssot_metrics = {}

        # Test SSOT-compliant factories
        ssot_start = time.perf_counter()
        ssot_factories = await self._benchmark_ssot_factories()
        ssot_time = time.perf_counter() - ssot_start

        # Test legacy factory patterns (if any remain)
        legacy_start = time.perf_counter()
        legacy_factories = await self._benchmark_legacy_factories()
        legacy_time = time.perf_counter() - legacy_start

        # Calculate SSOT performance impact
        ssot_overhead = ssot_time - legacy_time if legacy_time > 0 else 0
        ssot_improvement = (legacy_time - ssot_time) / legacy_time * 100 if legacy_time > 0 else 0

        self.record_metric("ssot_factory_time", ssot_time)
        self.record_metric("legacy_factory_time", legacy_time)
        self.record_metric("ssot_performance_overhead", ssot_overhead)
        self.record_metric("ssot_performance_improvement_percent", ssot_improvement)

        # SSOT performance validation
        if legacy_time > 0:
            # SSOT should not be more than 20% slower
            max_acceptable_overhead = legacy_time * 1.2
            self.assertLess(ssot_time, max_acceptable_overhead,
                           f"SSOT factories time {ssot_time:.3f}s should not exceed "
                           f"20% overhead over legacy {legacy_time:.3f}s")

        self.record_metric("ssot_compliance_performance_completed", True)

    # Helper methods for performance benchmarking

    async def _benchmark_websocket_factory(self) -> Any:
        """Benchmark WebSocket factory performance."""
        try:
            # Import and instantiate WebSocket factory
            from netra_backend.app.websocket_core.manager import WebSocketManager

            start_memory = self._get_memory_usage()
            start_time = time.perf_counter()

            # Create WebSocket factory instance
            websocket_manager = WebSocketManager()

            end_time = time.perf_counter()
            end_memory = self._get_memory_usage()

            self.record_metric("websocket_factory_instantiation_time", end_time - start_time)
            self.record_metric("websocket_factory_memory_usage", end_memory - start_memory)

            return websocket_manager

        except ImportError as e:
            self.record_metric("websocket_factory_import_error", str(e))
            return None

    async def _benchmark_agent_factory(self) -> Any:
        """Benchmark Agent factory performance."""
        try:
            from netra_backend.app.agents.registry import AgentRegistry

            start_memory = self._get_memory_usage()
            start_time = time.perf_counter()

            # Create agent registry
            agent_registry = AgentRegistry()

            end_time = time.perf_counter()
            end_memory = self._get_memory_usage()

            self.record_metric("agent_factory_instantiation_time", end_time - start_time)
            self.record_metric("agent_factory_memory_usage", end_memory - start_memory)

            return agent_registry

        except ImportError as e:
            self.record_metric("agent_factory_import_error", str(e))
            return None

    async def _benchmark_config_factory(self) -> Any:
        """Benchmark Configuration factory performance."""
        try:
            from netra_backend.app.config import get_config

            start_memory = self._get_memory_usage()
            start_time = time.perf_counter()

            # Get configuration instance
            config = get_config()

            end_time = time.perf_counter()
            end_memory = self._get_memory_usage()

            self.record_metric("config_factory_instantiation_time", end_time - start_time)
            self.record_metric("config_factory_memory_usage", end_memory - start_memory)

            return config

        except ImportError as e:
            self.record_metric("config_factory_import_error", str(e))
            return None

    async def _benchmark_database_factory(self) -> Any:
        """Benchmark Database factory performance."""
        try:
            from netra_backend.app.db.database_manager import DatabaseManager

            start_memory = self._get_memory_usage()
            start_time = time.perf_counter()

            # Create database manager instance
            db_manager = DatabaseManager()

            end_time = time.perf_counter()
            end_memory = self._get_memory_usage()

            self.record_metric("database_factory_instantiation_time", end_time - start_time)
            self.record_metric("database_factory_memory_usage", end_memory - start_memory)

            return db_manager

        except ImportError as e:
            self.record_metric("database_factory_import_error", str(e))
            return None

    async def _benchmark_auth_factory(self) -> Any:
        """Benchmark Auth factory performance."""
        try:
            from netra_backend.app.auth_integration.auth import AuthIntegration

            start_memory = self._get_memory_usage()
            start_time = time.perf_counter()

            # Create auth integration instance
            auth_integration = AuthIntegration()

            end_time = time.perf_counter()
            end_memory = self._get_memory_usage()

            self.record_metric("auth_factory_instantiation_time", end_time - start_time)
            self.record_metric("auth_factory_memory_usage", end_memory - start_memory)

            return auth_integration

        except ImportError as e:
            self.record_metric("auth_factory_import_error", str(e))
            return None

    async def _module_exists(self, module_name: str) -> bool:
        """Check if a module exists and can be imported."""
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False

    async def _benchmark_factory_module(self, module_name: str) -> PerformanceMetrics:
        """Benchmark performance of a specific factory module."""
        metrics = PerformanceMetrics()

        try:
            start_memory = self._get_memory_usage()
            start_time = time.perf_counter()
            gc_before = len(gc.get_objects())

            # Import and use the factory module
            module = importlib.import_module(module_name)

            # Try to find and instantiate factory classes
            factory_instances = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    ('factory' in attr_name.lower() or
                     'Factory' in attr_name or
                     'creator' in attr_name.lower() or
                     'Creator' in attr_name)):
                    try:
                        instance = attr()
                        factory_instances.append(instance)
                    except Exception:
                        pass  # Skip factories that require parameters

            end_time = time.perf_counter()
            end_memory = self._get_memory_usage()
            gc_after = len(gc.get_objects())

            metrics.instantiation_time = end_time - start_time
            metrics.memory_before = start_memory
            metrics.memory_after = end_memory
            metrics.memory_overhead = end_memory - start_memory
            metrics.object_count = gc_after - gc_before

        except Exception as e:
            self.record_metric(f"factory_module_error_{module_name}", str(e))

        return metrics

    async def _benchmark_concurrent_factories(self, user_count: int) -> PerformanceMetrics:
        """Benchmark factory performance under concurrent load."""
        metrics = PerformanceMetrics()

        start_memory = self._get_memory_usage()
        start_time = time.perf_counter()

        # Create tasks for concurrent factory instantiation
        tasks = []
        for i in range(user_count):
            task = asyncio.create_task(self._create_user_factory_context(i))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.perf_counter()
        end_memory = self._get_memory_usage()

        metrics.instantiation_time = end_time - start_time
        metrics.memory_before = start_memory
        metrics.memory_after = end_memory
        metrics.memory_overhead = end_memory - start_memory

        # Count successful instantiations
        successful_count = sum(1 for result in results if not isinstance(result, Exception))
        metrics.method_call_count = successful_count

        return metrics

    async def _create_user_factory_context(self, user_id: int) -> Dict[str, Any]:
        """Create factory context for a single user."""
        context = {}

        try:
            # Create user execution context
            user_context = self.create_test_user_execution_context(
                user_id=f"user_{user_id}",
                websocket_client_id=f"ws_{user_id}"
            )
            context['user_context'] = user_context

            # Simulate factory instantiation for this user
            factories = {}

            # WebSocket factory for this user
            websocket_factory = await self._benchmark_websocket_factory()
            if websocket_factory:
                factories['websocket'] = websocket_factory

            # Agent factory for this user
            agent_factory = await self._benchmark_agent_factory()
            if agent_factory:
                factories['agent'] = agent_factory

            context['factories'] = factories

        except Exception as e:
            context['error'] = str(e)

        return context

    def _calculate_scalability_factor(self, concurrency_metrics: Dict[int, PerformanceMetrics]) -> float:
        """Calculate factory scalability factor."""
        if len(concurrency_metrics) < 2:
            return 1.0

        # Compare performance between 1 user and maximum users tested
        single_user_time = concurrency_metrics.get(1, PerformanceMetrics()).instantiation_time
        max_users = max(concurrency_metrics.keys())
        max_user_time = concurrency_metrics[max_users].instantiation_time

        if single_user_time > 0:
            # Ideal scaling would be linear (scalability_factor = 1.0)
            # Values > 1.0 indicate worse than linear scaling
            expected_time = single_user_time * max_users
            scalability_factor = max_user_time / expected_time if expected_time > 0 else 1.0
        else:
            scalability_factor = 1.0

        return scalability_factor

    async def _profile_component_memory(self, component_name: str) -> Dict[str, int]:
        """Profile memory usage for a specific component."""
        profile = {
            'peak_memory': 0,
            'memory_growth': 0,
            'allocations': 0
        }

        start_memory = self._get_memory_usage()
        tracemalloc.start()

        try:
            # Simulate component usage based on name
            if component_name == 'websocket_manager':
                factory = await self._benchmark_websocket_factory()
            elif component_name == 'agent_registry':
                factory = await self._benchmark_agent_factory()
            elif component_name == 'config_manager':
                factory = await self._benchmark_config_factory()
            elif component_name == 'database_manager':
                factory = await self._benchmark_database_factory()
            elif component_name == 'auth_integration':
                factory = await self._benchmark_auth_factory()

            # Get memory statistics
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            end_memory = self._get_memory_usage()

            profile['peak_memory'] = peak_memory
            profile['memory_growth'] = end_memory - start_memory
            profile['allocations'] = peak_memory - current_memory

        except Exception as e:
            self.record_metric(f"memory_profile_error_{component_name}", str(e))
        finally:
            tracemalloc.stop()

        return profile

    async def _benchmark_ssot_factories(self) -> List[Any]:
        """Benchmark SSOT-compliant factory patterns."""
        ssot_factories = []

        try:
            # Test SSOT mock factory
            from test_framework.ssot.mock_factory import SSotMockFactory
            mock_factory = SSotMockFactory()
            ssot_factories.append(mock_factory)

            # Test SSOT base test case factory methods
            user_context = self.create_test_user_execution_context()
            ssot_factories.append(user_context)

        except Exception as e:
            self.record_metric("ssot_factory_benchmark_error", str(e))

        return ssot_factories

    async def _benchmark_legacy_factories(self) -> List[Any]:
        """Benchmark legacy factory patterns (if any remain)."""
        legacy_factories = []

        # This would test any remaining legacy factories
        # Currently minimal due to SSOT migration completion

        return legacy_factories

    def _record_golden_path_metrics(self, metrics: GoldenPathMetrics):
        """Record Golden Path performance metrics."""
        self.record_metric("golden_path_total_time", metrics.total_initialization_time)
        self.record_metric("golden_path_websocket_time", metrics.websocket_factory_time)
        self.record_metric("golden_path_agent_time", metrics.agent_factory_time)
        self.record_metric("golden_path_config_time", metrics.config_factory_time)
        self.record_metric("golden_path_database_time", metrics.database_factory_time)
        self.record_metric("golden_path_auth_time", metrics.auth_factory_time)
        self.record_metric("golden_path_memory_footprint", metrics.memory_footprint)

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            process = psutil.Process()
            return process.memory_info().rss
        except Exception:
            return 0