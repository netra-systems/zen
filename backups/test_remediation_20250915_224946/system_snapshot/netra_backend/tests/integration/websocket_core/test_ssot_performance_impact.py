"""SSOT Performance Impact Integration Tests - Issue #1058

Business Value Justification (BVJ):
- Segment: Enterprise/Platform (High-performance systems)
- Business Goal: Performance optimization and scalability validation
- Value Impact: Ensures $500K+ ARR system performance with SSOT consolidation
- Strategic Impact: Validates SSOT improves rather than degrades performance

Integration tests for SSOT performance impact:
- Concurrent user performance under SSOT consolidation
- Memory efficiency with consolidated broadcast service
- Performance comparison vs legacy scattered implementations
- Scalability validation for enterprise deployment

CRITICAL MISSION: Prove SSOT consolidation IMPROVES system performance
compared to maintaining 3 separate broadcast implementations.

Test Strategy: Performance integration testing with real load scenarios
to validate SSOT consolidation benefits for production deployment.
"""
import asyncio
import gc
import json
import pytest
import psutil
import time
import threading
import weakref
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from statistics import mean, median, stdev
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List, Optional, Tuple
from netra_backend.app.services.websocket_broadcast_service import WebSocketBroadcastService, BroadcastResult, create_broadcast_service
from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from shared.types.core_types import UserID, ensure_user_id
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.websocket_ssot
@pytest.mark.non_docker
@pytest.mark.issue_1058_performance_impact
class SSOTPerformanceImpactTests(SSotAsyncTestCase):
    """Integration tests validating SSOT performance impact and optimization.

    CRITICAL: These tests prove SSOT consolidation improves performance
    compared to maintaining multiple separate broadcast implementations.

    Performance test requirements:
    1. Concurrent user performance validation
    2. Memory efficiency with consolidated service
    3. Throughput improvements with SSOT
    4. Scalability validation for enterprise deployment
    """

    @pytest.fixture
    def performance_websocket_manager(self):
        """Create mock WebSocket manager optimized for performance testing."""
        manager = Mock(spec=WebSocketManagerProtocol)

        async def mock_send_with_latency(user_id, event):
            await asyncio.sleep(0.001 + hash(str(user_id)) % 5 * 0.001)
            return True
        manager.send_to_user = AsyncMock(side_effect=mock_send_with_latency)

        def mock_get_connections(user_id):
            connection_count = 1 + hash(str(user_id)) % 3
            return [{'connection_id': f'perf_conn_{user_id}_{i}', 'user_id': user_id} for i in range(connection_count)]
        manager.get_user_connections.side_effect = mock_get_connections
        return manager

    @pytest.fixture
    def performance_ssot_service(self, performance_websocket_manager):
        """Create SSOT service optimized for performance testing."""
        service = WebSocketBroadcastService(performance_websocket_manager)
        service.update_feature_flag('enable_contamination_detection', True)
        service.update_feature_flag('enable_performance_monitoring', True)
        service.update_feature_flag('enable_comprehensive_logging', False)
        return service

    @pytest.fixture
    def performance_test_users(self):
        """Generate users for performance testing."""
        return [f'perf_user_{i:04d}' for i in range(100)]

    @pytest.fixture
    def performance_test_events(self):
        """Generate events for performance testing."""
        base_events = [{'type': 'agent_started', 'category': 'agent_lifecycle'}, {'type': 'agent_thinking', 'category': 'agent_lifecycle'}, {'type': 'tool_executing', 'category': 'tool_operations'}, {'type': 'tool_completed', 'category': 'tool_operations'}, {'type': 'agent_completed', 'category': 'agent_lifecycle'}, {'type': 'system_notification', 'category': 'system_events'}, {'type': 'user_message', 'category': 'chat_events'}, {'type': 'data_update', 'category': 'data_events'}]
        performance_events = []
        for i, event_template in enumerate(base_events):
            event = {**event_template, 'data': {'event_id': f'perf_event_{i}', 'timestamp': datetime.now(timezone.utc).isoformat(), 'performance_test': True, 'payload_size': 'medium'}}
            performance_events.append(event)
        return performance_events

    @pytest.mark.asyncio
    async def test_ssot_concurrent_user_performance(self, performance_ssot_service, performance_test_users, performance_test_events):
        """Test SSOT performance with concurrent multi-user broadcasting.

        PERFORMANCE CRITICAL: SSOT must handle concurrent users efficiently
        without performance degradation compared to legacy implementations.
        """
        concurrent_user_count = 50
        events_per_user = 10
        total_expected_broadcasts = concurrent_user_count * events_per_user
        logger.info(f'Starting concurrent user performance test: {concurrent_user_count} users, {events_per_user} events each')
        start_time = time.time()
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024

        async def concurrent_user_task(user_id: str, user_index: int) -> Dict[str, Any]:
            """Execute concurrent broadcasts for a single user."""
            user_start_time = time.time()
            user_results = []
            user_latencies = []
            for i, event_template in enumerate(performance_test_events[:events_per_user]):
                event = {**event_template, 'data': {**event_template['data'], 'user_id': user_id, 'user_index': user_index, 'event_sequence': i}}
                broadcast_start = time.time()
                result = await performance_ssot_service.broadcast_to_user(user_id, event)
                broadcast_end = time.time()
                broadcast_latency = (broadcast_end - broadcast_start) * 1000
                user_latencies.append(broadcast_latency)
                user_results.append(result)
                if i < events_per_user - 1:
                    await asyncio.sleep(0.001)
            user_end_time = time.time()
            user_total_time = (user_end_time - user_start_time) * 1000
            return {'user_id': user_id, 'user_index': user_index, 'results': user_results, 'latencies': user_latencies, 'total_time_ms': user_total_time, 'avg_latency_ms': mean(user_latencies) if user_latencies else 0, 'successful_broadcasts': len([r for r in user_results if r.successful_sends > 0])}
        concurrent_tasks = [concurrent_user_task(user_id, i) for i, user_id in enumerate(performance_test_users[:concurrent_user_count])]
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        end_time = time.time()
        total_duration_ms = (end_time - start_time) * 1000
        memory_after = psutil.Process().memory_info().rss / 1024 / 1024
        memory_delta = memory_after - memory_before
        successful_user_results = [r for r in concurrent_results if not isinstance(r, Exception)]
        failed_users = len([r for r in concurrent_results if isinstance(r, Exception)])
        assert len(successful_user_results) >= concurrent_user_count * 0.95, f'Too many user task failures: {failed_users} out of {concurrent_user_count}'
        all_latencies = []
        total_successful_broadcasts = 0
        user_performance_stats = []
        for user_result in successful_user_results:
            all_latencies.extend(user_result['latencies'])
            total_successful_broadcasts += user_result['successful_broadcasts']
            user_performance_stats.append({'user_id': user_result['user_id'], 'avg_latency_ms': user_result['avg_latency_ms'], 'total_time_ms': user_result['total_time_ms'], 'success_rate': user_result['successful_broadcasts'] / events_per_user})
        avg_latency_ms = mean(all_latencies) if all_latencies else float('inf')
        p95_latency_ms = sorted(all_latencies)[int(len(all_latencies) * 0.95)] if all_latencies else float('inf')
        throughput_broadcasts_per_second = total_successful_broadcasts / (total_duration_ms / 1000)
        success_rate = total_successful_broadcasts / total_expected_broadcasts
        assert avg_latency_ms < 50, f'Average latency too high: {avg_latency_ms:.2f}ms (should be < 50ms)'
        assert p95_latency_ms < 100, f'P95 latency too high: {p95_latency_ms:.2f}ms (should be < 100ms)'
        assert throughput_broadcasts_per_second > 100, f'Throughput too low: {throughput_broadcasts_per_second:.1f} broadcasts/sec'
        assert success_rate > 0.95, f'Success rate too low: {success_rate:.2%}'
        assert memory_delta < 100, f'Memory usage too high: {memory_delta:.1f}MB increase'
        stats = performance_ssot_service.get_stats()
        assert stats['broadcast_stats']['total_broadcasts'] >= total_successful_broadcasts
        assert stats['performance_metrics']['success_rate_percentage'] >= 95.0
        logger.info(f'✅ Concurrent user performance validated:')
        logger.info(f'   📊 {concurrent_user_count} concurrent users, {total_successful_broadcasts} broadcasts')
        logger.info(f'   ⚡ Avg latency: {avg_latency_ms:.2f}ms, P95: {p95_latency_ms:.2f}ms')
        logger.info(f'   🚀 Throughput: {throughput_broadcasts_per_second:.1f} broadcasts/sec')
        logger.info(f'   ✅ Success rate: {success_rate:.2%}')
        logger.info(f'   💾 Memory delta: {memory_delta:.1f}MB')

    @pytest.mark.asyncio
    async def test_ssot_memory_efficiency_integration(self, performance_ssot_service):
        """Test SSOT memory efficiency during sustained operations.

        PERFORMANCE CRITICAL: SSOT consolidation should be more memory
        efficient than maintaining 3 separate broadcast implementations.
        """
        memory_test_user = 'memory_efficiency_user'
        sustained_operations = 1000
        logger.info(f'Starting memory efficiency test: {sustained_operations} sustained operations')
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_samples = [initial_memory]
        memory_tracking_active = True

        async def memory_tracker():
            """Track memory usage during sustained operations."""
            while memory_tracking_active:
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
                await asyncio.sleep(0.1)
        memory_task = asyncio.create_task(memory_tracker())
        try:
            for i in range(sustained_operations):
                payload_size = 'small' if i % 3 == 0 else 'medium' if i % 3 == 1 else 'large'
                payload_data = {'operation_id': i, 'timestamp': datetime.now(timezone.utc).isoformat(), 'payload_size': payload_size, 'data_bulk': 'x' * (100 if payload_size == 'small' else 500 if payload_size == 'medium' else 1000)}
                event = {'type': f'memory_test_{i}', 'data': payload_data}
                result = await performance_ssot_service.broadcast_to_user(memory_test_user, event)
                assert result.successful_sends > 0, f'Operation {i} failed'
                if i % 100 == 0:
                    gc.collect()
                if i % 10 == 0:
                    await asyncio.sleep(0.001)
        finally:
            memory_tracking_active = False
            await memory_task
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        max_memory = max(memory_samples)
        avg_memory = mean(memory_samples)
        assert memory_growth < 50, f'Memory growth too high: {memory_growth:.1f}MB (should be < 50MB)'
        assert max_memory < initial_memory + 100, f'Peak memory too high: {max_memory:.1f}MB'
        stats = performance_ssot_service.get_stats()
        stats_json_size = len(json.dumps(stats))
        assert stats_json_size < 10000, f'SSOT stats too large: {stats_json_size} bytes'
        logger.info(f'✅ Memory efficiency validated:')
        logger.info(f'   💾 Memory growth: {memory_growth:.1f}MB over {sustained_operations} operations')
        logger.info(f'   📈 Peak memory: {max_memory:.1f}MB (avg: {avg_memory:.1f}MB)')
        logger.info(f'   📊 Stats size: {stats_json_size} bytes')

    @pytest.mark.asyncio
    async def test_ssot_scalability_load_testing(self, performance_test_users):
        """Test SSOT scalability under increasing load.

        PERFORMANCE CRITICAL: SSOT must scale efficiently as user count
        and broadcast volume increases.
        """
        load_test_scenarios = [{'users': 10, 'events_per_user': 5, 'target_latency_ms': 20}, {'users': 25, 'events_per_user': 8, 'target_latency_ms': 30}, {'users': 50, 'events_per_user': 10, 'target_latency_ms': 50}, {'users': 100, 'events_per_user': 5, 'target_latency_ms': 75}]
        scalability_results = []
        for scenario in load_test_scenarios:
            user_count = scenario['users']
            events_per_user = scenario['events_per_user']
            target_latency = scenario['target_latency_ms']
            logger.info(f'Testing scalability: {user_count} users, {events_per_user} events each')
            mock_manager = Mock(spec=WebSocketManagerProtocol)
            mock_manager.send_to_user = AsyncMock()
            mock_manager.get_user_connections = Mock(return_value=[{'connection_id': 'scale_conn', 'user_id': 'scale_user'}])
            scale_service = WebSocketBroadcastService(mock_manager)
            start_time = time.time()
            latencies = []

            async def scale_user_task(user_id: str):
                """Execute broadcasts for scalability testing."""
                for i in range(events_per_user):
                    event = {'type': f'scale_event_{i}', 'data': {'user_id': user_id, 'event_index': i, 'scale_test': True}}
                    broadcast_start = time.time()
                    result = await scale_service.broadcast_to_user(user_id, event)
                    broadcast_end = time.time()
                    latency_ms = (broadcast_end - broadcast_start) * 1000
                    latencies.append(latency_ms)
                    assert result.successful_sends > 0, f'Scale broadcast failed for {user_id}'
            scale_tasks = [scale_user_task(performance_test_users[i]) for i in range(user_count)]
            await asyncio.gather(*scale_tasks)
            end_time = time.time()
            scenario_duration = (end_time - start_time) * 1000
            avg_latency = mean(latencies) if latencies else float('inf')
            total_broadcasts = user_count * events_per_user
            throughput = total_broadcasts / (scenario_duration / 1000)
            scalability_results.append({'users': user_count, 'events_per_user': events_per_user, 'total_broadcasts': total_broadcasts, 'avg_latency_ms': avg_latency, 'throughput_per_sec': throughput, 'duration_ms': scenario_duration, 'target_latency_ms': target_latency, 'meets_target': avg_latency <= target_latency})
            assert avg_latency <= target_latency, f'Scalability failure: {avg_latency:.2f}ms > {target_latency}ms for {user_count} users'
            logger.info(f'   ✅ {user_count} users: {avg_latency:.2f}ms avg latency, {throughput:.1f} broadcasts/sec')
        user_counts = [r['users'] for r in scalability_results]
        latencies = [r['avg_latency_ms'] for r in scalability_results]
        throughputs = [r['throughput_per_sec'] for r in scalability_results]
        max_user_count = max(user_counts)
        max_latency = max(latencies)
        scalability_ratio = max_latency / max_user_count
        assert scalability_ratio < 1.0, f'Poor scalability: {scalability_ratio:.3f}ms per user (should be < 1.0)'
        min_throughput = min(throughputs)
        max_throughput = max(throughputs)
        assert max_throughput > min_throughput, 'Throughput should increase with scale'
        logger.info(f'✅ Scalability load testing validated:')
        logger.info(f'   📈 Max load: {max_user_count} users')
        logger.info(f'   ⚡ Scalability ratio: {scalability_ratio:.3f}ms/user')
        logger.info(f'   🚀 Throughput range: {min_throughput:.1f} - {max_throughput:.1f} broadcasts/sec')

    @pytest.mark.asyncio
    async def test_ssot_performance_monitoring_overhead(self, performance_ssot_service):
        """Test SSOT performance monitoring overhead impact.

        PERFORMANCE CRITICAL: Performance monitoring features should have
        minimal overhead impact on broadcast operations.
        """
        monitoring_user = 'performance_monitoring_user'
        benchmark_broadcasts = 500
        performance_ssot_service.update_feature_flag('enable_performance_monitoring', True)
        start_time = time.time()
        for i in range(benchmark_broadcasts):
            event = {'type': f'monitoring_test_{i}', 'data': {'test': 'monitoring_overhead'}}
            result = await performance_ssot_service.broadcast_to_user(monitoring_user, event)
            assert result.successful_sends > 0
        monitoring_enabled_time = (time.time() - start_time) * 1000
        performance_ssot_service.update_feature_flag('enable_performance_monitoring', False)
        start_time = time.time()
        for i in range(benchmark_broadcasts):
            event = {'type': f'no_monitoring_test_{i}', 'data': {'test': 'no_monitoring'}}
            result = await performance_ssot_service.broadcast_to_user(monitoring_user, event)
            assert result.successful_sends > 0
        monitoring_disabled_time = (time.time() - start_time) * 1000
        monitoring_overhead_ms = monitoring_enabled_time - monitoring_disabled_time
        overhead_per_broadcast = monitoring_overhead_ms / benchmark_broadcasts
        overhead_percentage = monitoring_overhead_ms / monitoring_disabled_time * 100
        assert overhead_per_broadcast < 1.0, f'Monitoring overhead too high: {overhead_per_broadcast:.3f}ms per broadcast'
        assert overhead_percentage < 20, f'Monitoring overhead percentage too high: {overhead_percentage:.1f}%'
        performance_ssot_service.update_feature_flag('enable_performance_monitoring', True)
        stats = performance_ssot_service.get_stats()
        assert 'performance_metrics' in stats
        assert stats['broadcast_stats']['total_broadcasts'] >= benchmark_broadcasts * 2
        logger.info(f'✅ Performance monitoring overhead validated:')
        logger.info(f'   📊 Overhead: {overhead_per_broadcast:.3f}ms per broadcast ({overhead_percentage:.1f}%)')
        logger.info(f'   ⏱️  Enabled: {monitoring_enabled_time:.1f}ms, Disabled: {monitoring_disabled_time:.1f}ms')

@pytest.mark.integration_benchmark
class SSOTPerformanceBenchmarksTests:
    """Performance benchmark tests for SSOT consolidation."""

    @pytest.mark.asyncio
    async def test_ssot_consolidation_benchmark_comparison(self):
        """Benchmark SSOT consolidation vs simulated legacy implementations.

        BENCHMARK: Demonstrate SSOT consolidation performance benefits
        compared to maintaining separate broadcast implementations.
        """
        benchmark_users = [f'benchmark_user_{i}' for i in range(20)]
        benchmark_events_per_user = 25
        mock_manager = Mock(spec=WebSocketManagerProtocol)
        mock_manager.send_to_user = AsyncMock()
        mock_manager.get_user_connections = Mock(return_value=[{'connection_id': 'bench_conn', 'user_id': 'bench_user'}])
        ssot_service = WebSocketBroadcastService(mock_manager)
        start_time = time.time()
        ssot_broadcasts = 0
        for user_id in benchmark_users:
            for i in range(benchmark_events_per_user):
                event = {'type': f'ssot_benchmark_{i}', 'data': {'benchmark': 'ssot'}}
                result = await ssot_service.broadcast_to_user(user_id, event)
                if result.successful_sends > 0:
                    ssot_broadcasts += 1
        ssot_duration = time.time() - start_time
        legacy_service_1 = WebSocketBroadcastService(mock_manager)
        legacy_service_2 = WebSocketBroadcastService(mock_manager)
        legacy_service_3 = WebSocketBroadcastService(mock_manager)
        legacy_services = [legacy_service_1, legacy_service_2, legacy_service_3]
        start_time = time.time()
        legacy_broadcasts = 0
        for user_id in benchmark_users:
            for i in range(benchmark_events_per_user):
                service_choice = i % len(legacy_services)
                chosen_service = legacy_services[service_choice]
                event = {'type': f'legacy_benchmark_{i}', 'data': {'benchmark': 'legacy'}}
                result = await chosen_service.broadcast_to_user(user_id, event)
                if result.successful_sends > 0:
                    legacy_broadcasts += 1
        legacy_duration = time.time() - start_time
        total_expected_broadcasts = len(benchmark_users) * benchmark_events_per_user
        ssot_throughput = ssot_broadcasts / ssot_duration
        legacy_throughput = legacy_broadcasts / legacy_duration
        performance_improvement = (ssot_throughput - legacy_throughput) / legacy_throughput * 100
        assert ssot_broadcasts == total_expected_broadcasts, 'SSOT should complete all broadcasts'
        assert legacy_broadcasts == total_expected_broadcasts, 'Legacy should complete all broadcasts'
        assert ssot_throughput >= legacy_throughput, 'SSOT should match or exceed legacy throughput'
        ssot_stats = ssot_service.get_stats()
        logger.info(f'🏆 SSOT CONSOLIDATION BENCHMARK RESULTS:')
        logger.info(f'   📊 Total broadcasts: {total_expected_broadcasts}')
        logger.info(f'   ✅ SSOT throughput: {ssot_throughput:.1f} broadcasts/sec ({ssot_duration:.3f}s)')
        logger.info(f'   🔄 Legacy throughput: {legacy_throughput:.1f} broadcasts/sec ({legacy_duration:.3f}s)')
        logger.info(f'   🚀 Performance improvement: {performance_improvement:+.1f}%')
        logger.info(f"   🎯 SSOT replaces: {', '.join(ssot_stats['service_info']['replaces'])}")
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')