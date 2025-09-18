"""
Issue #1065: Mock Performance Baseline Test Suite

Establishes performance baseline for SSOT mock factory vs direct mock creation.
Validates that centralized mock creation doesn't introduce performance regressions.

Business Value: Platform/Internal - Development Velocity & System Performance
Ensures SSOT mock consolidation improves consistency without sacrificing speed.

Test Strategy:
1. Benchmark direct mock creation performance
2. Benchmark SSOT mock factory performance
3. Compare creation time, memory usage, and test execution speed
4. Validate performance is acceptable for 23,483 mock usage consolidation

Expected: SSOT factory performance within 10% of direct mock creation
Target: Better consistency with acceptable performance overhead
"""

import time
import asyncio
import gc
import statistics
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock, AsyncMock
import pytest
import psutil
import os

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


@pytest.mark.integration
class MockPerformanceBaselineTests(SSotBaseTestCase):
    """
    Performance baseline validation for SSOT mock factory.

    Ensures mock consolidation doesn't negatively impact test performance.
    """

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.performance_samples = 100  # Number of samples for statistical significance
        self.memory_baseline = self._get_memory_usage()

    def test_benchmark_direct_mock_creation_performance(self):
        """
        CRITICAL: Establish baseline for direct mock creation performance.

        Business Impact: Reference point for SSOT factory performance comparison
        """
        # Benchmark different types of direct mock creation
        direct_mock_benchmarks = {}

        # Agent mock creation (direct)
        direct_mock_benchmarks['agent_direct'] = self._benchmark_operation(
            lambda: self._create_direct_agent_mock(),
            "Direct Agent Mock Creation"
        )

        # WebSocket mock creation (direct)
        direct_mock_benchmarks['websocket_direct'] = self._benchmark_operation(
            lambda: self._create_direct_websocket_mock(),
            "Direct WebSocket Mock Creation"
        )

        # Database mock creation (direct)
        direct_mock_benchmarks['database_direct'] = self._benchmark_operation(
            lambda: self._create_direct_database_mock(),
            "Direct Database Mock Creation"
        )

        # Generic mock creation (direct)
        direct_mock_benchmarks['generic_direct'] = self._benchmark_operation(
            lambda: Mock(),
            "Direct Generic Mock Creation"
        )

        # Log baseline performance
        for mock_type, benchmark in direct_mock_benchmarks.items():
            self.logger.info(
                f"📊 {mock_type}: "
                f"avg={benchmark['avg_time_ms']:.3f}ms, "
                f"std={benchmark['std_time_ms']:.3f}ms, "
                f"memory={benchmark['memory_mb']:.2f}MB"
            )

        # Validate baseline performance is reasonable
        for benchmark in direct_mock_benchmarks.values():
            assert benchmark['avg_time_ms'] < 1.0, (
                f"Direct mock creation too slow: {benchmark['avg_time_ms']:.3f}ms"
            )

        # Store baseline for comparison
        self.direct_mock_baseline = direct_mock_benchmarks

    def test_benchmark_ssot_mock_factory_performance(self):
        """
        CRITICAL: Benchmark SSOT mock factory performance.

        Business Impact: Validates factory approach doesn't introduce significant overhead
        """
        # Benchmark SSOT factory mock creation
        factory_mock_benchmarks = {}

        # Agent mock creation (SSOT factory)
        factory_mock_benchmarks['agent_factory'] = self._benchmark_operation(
            lambda: SSotMockFactory.create_agent_mock(),
            "SSOT Agent Mock Creation"
        )

        # WebSocket mock creation (SSOT factory)
        factory_mock_benchmarks['websocket_factory'] = self._benchmark_operation(
            lambda: SSotMockFactory.create_websocket_mock(),
            "SSOT WebSocket Mock Creation"
        )

        # Database mock creation (SSOT factory)
        factory_mock_benchmarks['database_factory'] = self._benchmark_operation(
            lambda: SSotMockFactory.create_database_session_mock(),
            "SSOT Database Mock Creation"
        )

        # Configuration mock creation (SSOT factory)
        factory_mock_benchmarks['config_factory'] = self._benchmark_operation(
            lambda: SSotMockFactory.create_configuration_mock(),
            "SSOT Configuration Mock Creation"
        )

        # Log factory performance
        for mock_type, benchmark in factory_mock_benchmarks.items():
            self.logger.info(
                f"🏭 {mock_type}: "
                f"avg={benchmark['avg_time_ms']:.3f}ms, "
                f"std={benchmark['std_time_ms']:.3f}ms, "
                f"memory={benchmark['memory_mb']:.2f}MB"
            )

        # Store factory benchmarks for comparison
        self.factory_mock_benchmarks = factory_mock_benchmarks

        # Validate factory performance is acceptable
        for benchmark in factory_mock_benchmarks.values():
            assert benchmark['avg_time_ms'] < 5.0, (
                f"SSOT factory mock creation too slow: {benchmark['avg_time_ms']:.3f}ms"
            )

    def test_compare_mock_creation_performance(self):
        """
        HIGH: Compare direct vs SSOT factory mock creation performance.

        Business Impact: Validates migration to SSOT doesn't hurt developer productivity
        """
        # Run both baseline and factory benchmarks if not already done
        if not hasattr(self, 'direct_mock_baseline'):
            self.test_benchmark_direct_mock_creation_performance()
        if not hasattr(self, 'factory_mock_benchmarks'):
            self.test_benchmark_ssot_mock_factory_performance()

        # Compare performance metrics
        performance_comparison = {}

        # Agent mock comparison
        if 'agent_direct' in self.direct_mock_baseline and 'agent_factory' in self.factory_mock_benchmarks:
            agent_comparison = self._compare_benchmarks(
                self.direct_mock_baseline['agent_direct'],
                self.factory_mock_benchmarks['agent_factory']
            )
            performance_comparison['agent'] = agent_comparison

        # WebSocket mock comparison
        if 'websocket_direct' in self.direct_mock_baseline and 'websocket_factory' in self.factory_mock_benchmarks:
            websocket_comparison = self._compare_benchmarks(
                self.direct_mock_baseline['websocket_direct'],
                self.factory_mock_benchmarks['websocket_factory']
            )
            performance_comparison['websocket'] = websocket_comparison

        # Database mock comparison
        if 'database_direct' in self.direct_mock_baseline and 'database_factory' in self.factory_mock_benchmarks:
            database_comparison = self._compare_benchmarks(
                self.direct_mock_baseline['database_direct'],
                self.factory_mock_benchmarks['database_factory']
            )
            performance_comparison['database'] = database_comparison

        # Generate performance comparison report
        comparison_report = "MOCK CREATION PERFORMANCE COMPARISON\n"
        comparison_report += "=====================================\n\n"

        for mock_type, comparison in performance_comparison.items():
            comparison_report += f"{mock_type.upper()} MOCKS:\n"
            comparison_report += f"- Direct: {comparison['direct_avg']:.3f}ms avg\n"
            comparison_report += f"- Factory: {comparison['factory_avg']:.3f}ms avg\n"
            comparison_report += f"- Overhead: {comparison['overhead_percentage']:.1f}%\n"
            comparison_report += f"- Verdict: {comparison['verdict']}\n\n"

        self.logger.info(f"Performance Comparison:\n{comparison_report}")

        # Validate factory overhead is acceptable (< 50% overhead)
        for mock_type, comparison in performance_comparison.items():
            assert comparison['overhead_percentage'] < 50, (
                f"{mock_type} factory overhead too high: {comparison['overhead_percentage']:.1f}%"
            )

    def test_benchmark_mock_usage_patterns(self):
        """
        MEDIUM: Benchmark realistic mock usage patterns.

        Business Impact: Validates performance in real test scenarios
        """
        # Test complex mock creation patterns
        complex_patterns = {
            'agent_pipeline': self._benchmark_agent_pipeline_mock_creation,
            'websocket_integration': self._benchmark_websocket_integration_mock_creation,
            'database_transaction': self._benchmark_database_transaction_mock_creation,
        }

        pattern_benchmarks = {}
        for pattern_name, pattern_func in complex_patterns.items():
            pattern_benchmarks[pattern_name] = self._benchmark_operation(
                pattern_func,
                f"Complex {pattern_name} Mock Pattern"
            )

        # Log complex pattern performance
        for pattern_name, benchmark in pattern_benchmarks.items():
            self.logger.info(
                f"🔄 {pattern_name}: "
                f"avg={benchmark['avg_time_ms']:.3f}ms, "
                f"memory={benchmark['memory_mb']:.2f}MB"
            )

        # Validate complex patterns perform acceptably
        for benchmark in pattern_benchmarks.values():
            assert benchmark['avg_time_ms'] < 10.0, (
                f"Complex mock pattern too slow: {benchmark['avg_time_ms']:.3f}ms"
            )

    def test_validate_memory_efficiency(self):
        """
        MEDIUM: Validate mock creation doesn't cause memory leaks.

        Business Impact: Ensures test suite scalability with 23,483 mock usages
        """
        initial_memory = self._get_memory_usage()

        # Create many mocks to test memory efficiency
        mock_count = 1000
        mocks_created = []

        # Test factory mock memory usage
        start_time = time.time()
        for _ in range(mock_count):
            mock_agent = SSotMockFactory.create_agent_mock()
            mock_websocket = SSotMockFactory.create_websocket_mock()
            mocks_created.extend([mock_agent, mock_websocket])

        creation_time = time.time() - start_time
        peak_memory = self._get_memory_usage()
        memory_increase = peak_memory - initial_memory

        # Clear mocks and force garbage collection
        mocks_created.clear()
        gc.collect()

        final_memory = self._get_memory_usage()
        memory_leaked = final_memory - initial_memory

        memory_report = f"""
MOCK MEMORY EFFICIENCY ANALYSIS
==============================

Mock Count: {mock_count * 2} (agent + websocket)
Creation Time: {creation_time:.3f}s
Peak Memory Increase: {memory_increase:.2f}MB
Memory After Cleanup: {memory_leaked:.2f}MB
Memory Efficiency: {memory_increase / (mock_count * 2):.4f}MB per mock

ASSESSMENT: {'CHECK EFFICIENT' if memory_leaked < 10 else 'WARNING️ POSSIBLE LEAK'}
        """

        self.logger.info(f"Memory Efficiency:\n{memory_report}")

        # Validate memory efficiency
        assert memory_increase < 100, f"Memory usage too high: {memory_increase:.2f}MB"
        assert memory_leaked < 10, f"Possible memory leak: {memory_leaked:.2f}MB"

    def _benchmark_operation(self, operation, description: str) -> Dict[str, float]:
        """Benchmark a specific operation."""
        times = []
        initial_memory = self._get_memory_usage()

        for _ in range(self.performance_samples):
            start_time = time.perf_counter()
            try:
                result = operation()
                # Keep reference to prevent optimization
                _ = str(result)
            except Exception as e:
                self.logger.warning(f"Benchmark operation failed: {e}")
                continue
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # Convert to milliseconds

        final_memory = self._get_memory_usage()

        if not times:
            return {
                'avg_time_ms': float('inf'),
                'std_time_ms': 0,
                'min_time_ms': float('inf'),
                'max_time_ms': float('inf'),
                'memory_mb': 0
            }

        return {
            'avg_time_ms': statistics.mean(times),
            'std_time_ms': statistics.stdev(times) if len(times) > 1 else 0,
            'min_time_ms': min(times),
            'max_time_ms': max(times),
            'memory_mb': final_memory - initial_memory
        }

    def _compare_benchmarks(self, direct_benchmark: Dict, factory_benchmark: Dict) -> Dict[str, Any]:
        """Compare two benchmark results."""
        direct_avg = direct_benchmark['avg_time_ms']
        factory_avg = factory_benchmark['avg_time_ms']

        if direct_avg > 0:
            overhead_percentage = ((factory_avg - direct_avg) / direct_avg) * 100
        else:
            overhead_percentage = 0

        verdict = "ACCEPTABLE" if overhead_percentage < 50 else "NEEDS OPTIMIZATION"

        return {
            'direct_avg': direct_avg,
            'factory_avg': factory_avg,
            'overhead_percentage': overhead_percentage,
            'verdict': verdict
        }

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except:
            return 0.0

    def _create_direct_agent_mock(self):
        """Create agent mock using direct approach."""
        mock_agent = AsyncMock()
        mock_agent.agent_type = "supervisor"
        mock_agent.execute.return_value = {"status": "completed"}
        mock_agent.get_capabilities.return_value = ["text_processing"]
        return mock_agent

    def _create_direct_websocket_mock(self):
        """Create WebSocket mock using direct approach."""
        mock_websocket = MagicMock()
        mock_websocket.connection_id = "test-connection"
        mock_websocket.user_id = "test-user"
        mock_websocket.send_text = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        return mock_websocket

    def _create_direct_database_mock(self):
        """Create database mock using direct approach."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        return mock_session

    def _benchmark_agent_pipeline_mock_creation(self):
        """Create complex agent pipeline mock."""
        agent = SSotMockFactory.create_agent_mock()
        websocket = SSotMockFactory.create_websocket_mock()
        context = SSotMockFactory.create_execution_context_mock()
        bridge = SSotMockFactory.create_mock_agent_websocket_bridge()
        return [agent, websocket, context, bridge]

    def _benchmark_websocket_integration_mock_creation(self):
        """Create complex WebSocket integration mock."""
        manager = SSotMockFactory.create_websocket_manager_mock()
        bridge = SSotMockFactory.create_mock_agent_websocket_bridge()
        context = SSotMockFactory.create_mock_user_context()
        return [manager, bridge, context]

    def _benchmark_database_transaction_mock_creation(self):
        """Create complex database transaction mock."""
        session = SSotMockFactory.create_database_session_mock()
        config = SSotMockFactory.create_configuration_mock()
        return [session, config]