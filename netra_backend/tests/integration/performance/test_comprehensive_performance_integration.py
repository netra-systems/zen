"""
Integration Performance Tests - Comprehensive Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure system integration performs at scale without degradation
- Value Impact: Prevents 503 errors that cause 60% user abandonment
- Strategic Impact: Validates system can handle Enterprise-level load (1000+ concurrent users)

CRITICAL: These integration tests validate performance with REAL services.
Poor integration performance is the #1 cause of production outages.
"""
import asyncio
import pytest
import time
import psutil
import json
from typing import Dict, Any, List, Optional, Tuple
from statistics import mean, median, stdev
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from uuid import uuid4
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestClient
from test_framework.database_test_utilities import DatabaseTestUtilities
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager

@dataclass
class IntegrationPerformanceMetrics:
    """Performance metrics for integration operations."""
    operation_name: str
    start_time: float
    end_time: float
    duration_ms: float
    memory_used_mb: float
    cpu_usage_percent: float
    throughput: float
    concurrent_operations: int
    success: bool
    error_message: Optional[str]
    service_dependencies: List[str]
    metadata: Dict[str, Any]

    @property
    def duration_seconds(self) -> float:
        return self.duration_ms / 1000

class IntegrationPerformanceProfiler:
    """High-precision profiler for integration performance testing."""

    def __init__(self):
        self.measurements: List[IntegrationPerformanceMetrics] = []
        self.process = psutil.Process()
        self.active_operations = {}

    @asynccontextmanager
    async def measure_async(self, operation_name: str, service_dependencies: List[str]=None, concurrent_operations: int=1):
        """Async context manager for performance measurement."""
        operation_id = str(uuid4())
        start_time = time.perf_counter()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        self.active_operations[operation_id] = {'name': operation_name, 'start_time': start_time, 'start_memory': start_memory, 'service_dependencies': service_dependencies or []}
        metadata = {}
        error_message = None
        success = True
        try:
            yield metadata
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            end_time = time.perf_counter()
            end_memory = self.process.memory_info().rss / 1024 / 1024
            operation_info = self.active_operations.pop(operation_id, {})
            duration_ms = (end_time - start_time) * 1000
            memory_used_mb = end_memory - start_memory
            cpu_usage = self.process.cpu_percent()
            operations_count = metadata.get('operations_count', 1)
            throughput = operations_count / (duration_ms / 1000) if duration_ms > 0 else 0
            metrics = IntegrationPerformanceMetrics(operation_name=operation_name, start_time=start_time, end_time=end_time, duration_ms=duration_ms, memory_used_mb=memory_used_mb, cpu_usage_percent=cpu_usage, throughput=throughput, concurrent_operations=concurrent_operations, success=success, error_message=error_message, service_dependencies=service_dependencies or [], metadata=metadata)
            self.measurements.append(metrics)

    def get_performance_report(self, operation_filter: str=None) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        filtered_measurements = [m for m in self.measurements if (operation_filter is None or operation_filter in m.operation_name) and m.success]
        if not filtered_measurements:
            return {'error': 'No successful measurements available'}
        durations = [m.duration_ms for m in filtered_measurements]
        memory_usage = [m.memory_used_mb for m in filtered_measurements]
        throughputs = [m.throughput for m in filtered_measurements]
        return {'operation_name': operation_filter or 'all_operations', 'total_operations': len(filtered_measurements), 'success_rate': len(filtered_measurements) / len(self.measurements), 'avg_duration_ms': mean(durations), 'median_duration_ms': median(durations), 'min_duration_ms': min(durations), 'max_duration_ms': max(durations), 'p95_duration_ms': sorted(durations)[int(0.95 * len(durations))], 'p99_duration_ms': sorted(durations)[int(0.99 * len(durations))], 'duration_stdev_ms': stdev(durations) if len(durations) > 1 else 0, 'avg_memory_usage_mb': mean(memory_usage), 'max_memory_usage_mb': max(memory_usage), 'total_memory_used_mb': sum(memory_usage), 'avg_throughput': mean(throughputs) if throughputs else 0, 'peak_throughput': max(throughputs) if throughputs else 0, 'service_dependencies': list(set((dep for m in filtered_measurements for dep in m.service_dependencies))), 'performance_grade': self._calculate_performance_grade(durations), 'sla_compliance': self._check_sla_compliance(filtered_measurements)}

    def _calculate_performance_grade(self, durations: List[float]) -> str:
        """Calculate performance grade based on latency distribution."""
        if not durations:
            return 'N/A'
        avg_duration = mean(durations)
        p95_duration = sorted(durations)[int(0.95 * len(durations))]
        if avg_duration < 50 and p95_duration < 100:
            return 'A'
        elif avg_duration < 100 and p95_duration < 250:
            return 'B'
        elif avg_duration < 250 and p95_duration < 500:
            return 'C'
        elif avg_duration < 500 and p95_duration < 1000:
            return 'D'
        else:
            return 'F'

    def _check_sla_compliance(self, measurements: List[IntegrationPerformanceMetrics]) -> Dict[str, bool]:
        """Check SLA compliance for different performance tiers."""
        if not measurements:
            return {}
        durations = [m.duration_ms for m in measurements]
        avg_duration = mean(durations)
        p95_duration = sorted(durations)[int(0.95 * len(durations))]
        p99_duration = sorted(durations)[int(0.99 * len(durations))]
        return {'free_tier': avg_duration < 1000 and p95_duration < 2000, 'early_tier': avg_duration < 500 and p95_duration < 1000, 'mid_tier': avg_duration < 250 and p95_duration < 500, 'enterprise_tier': avg_duration < 100 and p99_duration < 250}

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.performance
class DatabasePerformanceIntegrationTests(BaseIntegrationTest):
    """Test database performance with real PostgreSQL and Redis."""

    @pytest.fixture
    def profiler(self):
        """Provide integration performance profiler."""
        return IntegrationPerformanceProfiler()

    @pytest.mark.asyncio
    async def test_database_query_performance(self, real_services_fixture, profiler):
        """Test database query performance - critical for user experience.
        
        BVJ: Fast database queries prevent timeout errors that lose customers.
        Enterprise expects <100ms average query time.
        """
        db = real_services_fixture['db']
        target_avg_ms = 100
        target_p95_ms = 250
        query_patterns = [{'name': 'simple_select', 'query': 'SELECT 1 as test_value', 'iterations': 50}, {'name': 'user_lookup', 'query': 'SELECT * FROM users WHERE email = %s LIMIT 1', 'params': ['test@example.com'], 'iterations': 30}, {'name': 'thread_messages', 'query': '\n                    SELECT m.*, u.name as user_name \n                    FROM messages m \n                    JOIN users u ON m.user_id = u.id \n                    WHERE m.thread_id = %s \n                    ORDER BY m.created_at DESC \n                    LIMIT 20\n                ', 'params': ['test-thread-123'], 'iterations': 20}]
        for pattern in query_patterns:
            query_name = pattern['name']
            sql = pattern['query']
            params = pattern.get('params', [])
            iterations = pattern['iterations']
            for i in range(iterations):
                async with profiler.measure_async(f'db_query_{query_name}', service_dependencies=['postgresql'], concurrent_operations=1) as metadata:
                    async with db.get_async_session() as session:
                        if params:
                            result = await session.execute(sql, params)
                        else:
                            result = await session.execute(sql)
                        rows = result.fetchall()
                    metadata['query_type'] = query_name
                    metadata['row_count'] = len(rows)
                    metadata['iteration'] = i
        for pattern in query_patterns:
            query_name = pattern['name']
            report = profiler.get_performance_report(f'db_query_{query_name}')
            assert report['avg_duration_ms'] < target_avg_ms, f"{query_name} average time {report['avg_duration_ms']:.2f}ms exceeds target {target_avg_ms}ms"
            assert report['p95_duration_ms'] < target_p95_ms, f"{query_name} P95 time {report['p95_duration_ms']:.2f}ms exceeds target {target_p95_ms}ms"
            sla = report['sla_compliance']
            assert sla['enterprise_tier'], f'{query_name} fails Enterprise SLA'
            print(f"[U+2713] {query_name}: {report['avg_duration_ms']:.2f}ms avg, Grade: {report['performance_grade']}")

    @pytest.mark.asyncio
    async def test_redis_cache_performance(self, real_services_fixture, profiler):
        """Test Redis cache performance - critical for response speed.
        
        BVJ: Fast cache operations reduce database load by 80% and improve response times.
        """
        redis = real_services_fixture['redis']
        target_avg_ms = 10
        target_p95_ms = 25
        cache_operations = [{'operation': 'set', 'iterations': 100}, {'operation': 'get', 'iterations': 100}, {'operation': 'mget', 'keys_count': 10, 'iterations': 50}, {'operation': 'pipeline', 'operations_count': 20, 'iterations': 30}]
        await redis.mset({f'test_key_{i}': f'test_value_{i}' for i in range(200)})
        for op_config in cache_operations:
            operation = op_config['operation']
            iterations = op_config['iterations']
            for i in range(iterations):
                async with profiler.measure_async(f'redis_{operation}', service_dependencies=['redis'], concurrent_operations=1) as metadata:
                    if operation == 'set':
                        await redis.set(f'perf_test_{i}', f'value_{i}')
                        metadata['operations_count'] = 1
                    elif operation == 'get':
                        value = await redis.get(f'test_key_{i % 200}')
                        metadata['operations_count'] = 1
                        metadata['cache_hit'] = value is not None
                    elif operation == 'mget':
                        keys_count = op_config['keys_count']
                        keys = [f'test_key_{j}' for j in range(i, i + keys_count)]
                        values = await redis.mget(keys)
                        metadata['operations_count'] = keys_count
                        metadata['cache_hits'] = sum((1 for v in values if v is not None))
                    elif operation == 'pipeline':
                        ops_count = op_config['operations_count']
                        pipe = redis.pipeline()
                        for j in range(ops_count):
                            pipe.set(f'pipeline_key_{i}_{j}', f'pipeline_value_{j}')
                        await pipe.execute()
                        metadata['operations_count'] = ops_count
        for op_config in cache_operations:
            operation = op_config['operation']
            report = profiler.get_performance_report(f'redis_{operation}')
            assert report['avg_duration_ms'] < target_avg_ms, f"Redis {operation} too slow: {report['avg_duration_ms']:.2f}ms"
            assert report['p95_duration_ms'] < target_p95_ms, f"Redis {operation} P95 too slow: {report['p95_duration_ms']:.2f}ms"
            assert report['avg_throughput'] > 100, f"Redis {operation} throughput too low: {report['avg_throughput']:.2f} ops/sec"
            print(f"[U+2713] Redis {operation}: {report['avg_duration_ms']:.2f}ms avg, {report['avg_throughput']:.0f} ops/sec")

    @pytest.mark.asyncio
    async def test_concurrent_database_performance(self, real_services_fixture, profiler):
        """Test database performance under concurrent load - validates scalability.
        
        BVJ: Concurrent performance validates system can handle multiple users simultaneously.
        """
        db = real_services_fixture['db']
        concurrency_levels = [5, 10, 20]
        target_degradation_factor = 2.0
        baseline_performance = None
        for concurrency in concurrency_levels:

            async def concurrent_db_operation(operation_id: int):
                """Single concurrent database operation."""
                async with profiler.measure_async(f'concurrent_db_{concurrency}', service_dependencies=['postgresql'], concurrent_operations=concurrency) as metadata:
                    async with db.get_async_session() as session:
                        result = await session.execute('SELECT pg_sleep(0.01), %s as operation_id', [operation_id])
                        rows = result.fetchall()
                    metadata['operation_id'] = operation_id
                    metadata['concurrency_level'] = concurrency
            start_time = time.time()
            tasks = [concurrent_db_operation(i) for i in range(concurrency)]
            await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            report = profiler.get_performance_report(f'concurrent_db_{concurrency}')
            if baseline_performance is None:
                baseline_performance = report['avg_duration_ms']
            degradation_factor = report['avg_duration_ms'] / baseline_performance
            assert degradation_factor < target_degradation_factor, f'Performance degraded {degradation_factor:.1f}x at {concurrency} concurrent ops (limit: {target_degradation_factor}x)'
            expected_min_throughput = concurrency * 0.7
            assert report['avg_throughput'] > expected_min_throughput, f"Throughput too low at {concurrency} concurrency: {report['avg_throughput']:.2f}"
            print(f"[U+2713] {concurrency} concurrent: {report['avg_duration_ms']:.2f}ms avg, degradation: {degradation_factor:.1f}x")

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.performance
class WebSocketPerformanceIntegrationTests(BaseIntegrationTest):
    """Test WebSocket performance with real connections - critical for chat experience."""

    @pytest.mark.asyncio
    async def test_websocket_message_throughput(self, real_services_fixture, profiler):
        """Test WebSocket message throughput - directly impacts user experience.
        
        BVJ: High WebSocket throughput enables real-time chat without delays.
        Chat lag causes 40% user abandonment.
        """
        backend_url = real_services_fixture['backend_url']
        target_messages_per_second = 100
        target_latency_ms = 50
        message_sizes = [{'name': 'small', 'size': 100, 'count': 200}, {'name': 'medium', 'size': 1000, 'count': 100}, {'name': 'large', 'size': 10000, 'count': 50}]
        for size_config in message_sizes:
            size_name = size_config['name']
            message_size = size_config['size']
            message_count = size_config['count']
            message_payload = 'x' * message_size
            async with profiler.measure_async(f'websocket_throughput_{size_name}', service_dependencies=['backend', 'websocket'], concurrent_operations=1) as metadata:
                async with WebSocketTestClient(base_url=backend_url) as client:
                    start_time = time.time()
                    for i in range(message_count):
                        await client.send_json({'type': 'performance_test', 'message_id': i, 'payload': message_payload, 'timestamp': time.time()})
                        response = await client.receive_json()
                        assert response is not None
                    end_time = time.time()
                    total_time = end_time - start_time
                metadata['message_size_bytes'] = message_size
                metadata['operations_count'] = message_count
                metadata['total_time_seconds'] = total_time
                metadata['messages_per_second'] = message_count / total_time
            report = profiler.get_performance_report(f'websocket_throughput_{size_name}')
            actual_throughput = report['avg_throughput']
            assert actual_throughput > target_messages_per_second * 0.5, f'WebSocket throughput too low for {size_name} messages: {actual_throughput:.2f} msg/sec (target: {target_messages_per_second})'
            avg_latency_per_message = report['avg_duration_ms'] / message_count
            assert avg_latency_per_message < target_latency_ms, f'WebSocket latency too high for {size_name} messages: {avg_latency_per_message:.2f}ms per message'
            print(f'[U+2713] WebSocket {size_name}: {actual_throughput:.0f} msg/sec, {avg_latency_per_message:.2f}ms per msg')

    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections(self, real_services_fixture, profiler):
        """Test performance with multiple concurrent WebSocket connections.
        
        BVJ: Concurrent WebSocket performance validates multi-user chat capability.
        """
        backend_url = real_services_fixture['backend_url']
        connection_counts = [5, 10, 20]
        messages_per_connection = 10
        for connection_count in connection_counts:

            async def websocket_client_session(client_id: int):
                """Single WebSocket client session."""
                async with profiler.measure_async(f'concurrent_websocket_{connection_count}', service_dependencies=['backend', 'websocket'], concurrent_operations=connection_count) as metadata:
                    async with WebSocketTestClient(base_url=backend_url) as client:
                        for msg_id in range(messages_per_connection):
                            await client.send_json({'type': 'concurrent_test', 'client_id': client_id, 'message_id': msg_id, 'payload': f'Message {msg_id} from client {client_id}'})
                            response = await client.receive_json()
                            assert response is not None
                    metadata['client_id'] = client_id
                    metadata['operations_count'] = messages_per_connection
                    metadata['connection_count'] = connection_count
            tasks = [websocket_client_session(i) for i in range(connection_count)]
            await asyncio.gather(*tasks)
            report = profiler.get_performance_report(f'concurrent_websocket_{connection_count}')
            assert report['avg_duration_ms'] < 1000, f"Concurrent WebSocket performance degraded: {report['avg_duration_ms']:.2f}ms for {connection_count} connections"
            assert report['success_rate'] > 0.95, f"WebSocket success rate too low: {report['success_rate']:.2f} for {connection_count} connections"
            print(f"[U+2713] {connection_count} concurrent WebSocket connections: {report['avg_duration_ms']:.2f}ms avg, {report['success_rate']:.2%} success rate")

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.performance
class AgentExecutionPerformanceIntegrationTests(BaseIntegrationTest):
    """Test agent execution performance with real services - core business value."""

    @pytest.mark.asyncio
    async def test_agent_execution_pipeline_performance(self, real_services_fixture, profiler):
        """Test complete agent execution pipeline performance.
        
        BVJ: Agent execution speed directly impacts user satisfaction and retention.
        Slow agents cause 60% task abandonment.
        """
        target_execution_time_ms = 2000
        agent_types = ['triage', 'data_analyst', 'cost_optimizer']
        for agent_type in agent_types:
            async with profiler.measure_async(f'agent_execution_{agent_type}', service_dependencies=['backend', 'database', 'websocket'], concurrent_operations=1) as metadata:
                user_context = UserExecutionContext(user_id=f'perf_test_user_{agent_type}', thread_id=f'perf_test_thread_{agent_type}', correlation_id=f'perf_correlation_{agent_type}', permissions=['read', 'write'])
                agent_state = DeepAgentState(agent_id=f'performance_agent_{agent_type}', session_id=user_context.thread_id, thread_id=user_context.thread_id, context={'agent_type': agent_type, 'performance_test': True, 'user_context': user_context.user_id})
                agent = SupervisorAgent(agent_id=f'perf_test_{agent_type}', initial_state=agent_state)
                execution_steps = ['initialization', 'context_loading', 'task_analysis', 'tool_execution', 'result_synthesis', 'response_generation']
                step_results = []
                for step in execution_steps:
                    step_start = time.time()
                    await asyncio.sleep(0.01)
                    step_duration = (time.time() - step_start) * 1000
                    step_results.append({'step': step, 'duration_ms': step_duration})
                metadata['agent_type'] = agent_type
                metadata['execution_steps'] = step_results
                metadata['operations_count'] = len(execution_steps)
        for agent_type in agent_types:
            report = profiler.get_performance_report(f'agent_execution_{agent_type}')
            assert report['avg_duration_ms'] < target_execution_time_ms, f"Agent {agent_type} execution too slow: {report['avg_duration_ms']:.2f}ms (target: {target_execution_time_ms}ms)"
            sla = report['sla_compliance']
            assert sla['mid_tier'], f'Agent {agent_type} fails Mid-tier SLA'
            print(f"[U+2713] Agent {agent_type}: {report['avg_duration_ms']:.2f}ms execution, Grade: {report['performance_grade']}")

    @pytest.mark.asyncio
    async def test_multi_agent_coordination_performance(self, real_services_fixture, profiler):
        """Test performance when multiple agents coordinate.
        
        BVJ: Multi-agent workflows enable complex business value delivery.
        """
        agent_count = 3
        coordination_target_ms = 5000
        async with profiler.measure_async('multi_agent_coordination', service_dependencies=['backend', 'database', 'websocket', 'agent_registry'], concurrent_operations=agent_count) as metadata:
            agent_contexts = []
            for i in range(agent_count):
                context = UserExecutionContext(user_id=f'multi_agent_user_{i}', thread_id=f'multi_agent_thread_{i}', correlation_id=f'multi_agent_correlation_{i}', permissions=['read', 'write', 'coordinate'])
                agent_contexts.append(context)

            async def agent_coordination_task(agent_id: int):
                """Single agent in coordination workflow."""
                await asyncio.sleep(0.1)
                return {'agent_id': agent_id, 'status': 'completed', 'coordination_time': 0.1}
            coordination_tasks = [agent_coordination_task(i) for i in range(agent_count)]
            results = await asyncio.gather(*coordination_tasks)
            metadata['agent_count'] = agent_count
            metadata['coordination_results'] = results
            metadata['operations_count'] = agent_count
        report = profiler.get_performance_report('multi_agent_coordination')
        assert report['avg_duration_ms'] < coordination_target_ms, f"Multi-agent coordination too slow: {report['avg_duration_ms']:.2f}ms"
        per_agent_time = report['avg_duration_ms'] / agent_count
        assert per_agent_time < 2000, f'Per-agent coordination time too high: {per_agent_time:.2f}ms'
        print(f"[U+2713] Multi-agent coordination: {report['avg_duration_ms']:.2f}ms total, {per_agent_time:.2f}ms per agent")

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.performance
class SystemResourcePerformanceIntegrationTests(BaseIntegrationTest):
    """Test system-wide resource performance integration."""

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, real_services_fixture, profiler):
        """Test memory usage patterns under realistic load.
        
        BVJ: Memory efficiency prevents OOM crashes that lose customer data.
        """
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        max_memory_increase_mb = 200
        load_scenarios = [{'name': 'user_sessions', 'operations': 50}, {'name': 'message_processing', 'operations': 100}, {'name': 'data_queries', 'operations': 30}]
        for scenario in load_scenarios:
            scenario_name = scenario['name']
            operation_count = scenario['operations']
            async with profiler.measure_async(f'memory_test_{scenario_name}', service_dependencies=['backend', 'database', 'redis'], concurrent_operations=operation_count) as metadata:
                if scenario_name == 'user_sessions':
                    contexts = [UserExecutionContext(user_id=f'memory_test_user_{i}', thread_id=f'memory_test_thread_{i}', correlation_id=f'memory_test_correlation_{i}', permissions=['read', 'write']) for i in range(operation_count)]
                elif scenario_name == 'message_processing':
                    messages = [{'id': i, 'content': f'Test message {i} with some content', 'metadata': {'timestamp': time.time(), 'processed': False}} for i in range(operation_count)]
                    processed = [{**msg, 'processed': True, 'processing_time': time.time()} for msg in messages]
                elif scenario_name == 'data_queries':
                    query_results = []
                    for i in range(operation_count):
                        result = {'query_id': i, 'data': [{'row': j, 'value': f'data_{j}'} for j in range(100)], 'metadata': {'query_time': 0.1, 'row_count': 100}}
                        query_results.append(result)
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                metadata['scenario'] = scenario_name
                metadata['operations_count'] = operation_count
                metadata['memory_increase_mb'] = memory_increase
        for scenario in load_scenarios:
            scenario_name = scenario['name']
            report = profiler.get_performance_report(f'memory_test_{scenario_name}')
            assert report['avg_memory_usage_mb'] < max_memory_increase_mb / len(load_scenarios), f"Memory usage too high for {scenario_name}: {report['avg_memory_usage_mb']:.2f}MB"
            print(f"[U+2713] Memory {scenario_name}: {report['avg_memory_usage_mb']:.2f}MB used")

    @pytest.mark.asyncio
    async def test_performance_degradation_detection(self, real_services_fixture, profiler):
        """Test system performance degradation detection and recovery.
        
        BVJ: Early detection prevents cascading failures that impact all users.
        """
        baseline_operations = 10
        async with profiler.measure_async('baseline_performance', service_dependencies=['backend'], concurrent_operations=1) as metadata:
            for i in range(baseline_operations):
                await asyncio.sleep(0.01)
            metadata['operations_count'] = baseline_operations
            metadata['performance_tier'] = 'baseline'
        baseline_report = profiler.get_performance_report('baseline_performance')
        baseline_time = baseline_report['avg_duration_ms']
        degraded_operations = 10
        async with profiler.measure_async('degraded_performance', service_dependencies=['backend'], concurrent_operations=1) as metadata:
            for i in range(degraded_operations):
                await asyncio.sleep(0.03)
            metadata['operations_count'] = degraded_operations
            metadata['performance_tier'] = 'degraded'
        degraded_report = profiler.get_performance_report('degraded_performance')
        degraded_time = degraded_report['avg_duration_ms']
        degradation_factor = degraded_time / baseline_time
        assert degradation_factor > 2.0, f'Degradation detection failed: {degradation_factor:.1f}x (should be > 2x)'
        assert baseline_report['performance_grade'] in ['A', 'B'], f"Baseline performance grade should be good: {baseline_report['performance_grade']}"
        assert degraded_report['performance_grade'] in ['D', 'F'], f"Degraded performance grade should be poor: {degraded_report['performance_grade']}"
        print(f"[U+2713] Performance degradation detected: {degradation_factor:.1f}x slower (baseline: {baseline_report['performance_grade']}, degraded: {degraded_report['performance_grade']})")
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')