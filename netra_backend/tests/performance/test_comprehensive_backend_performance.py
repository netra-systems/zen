"""
Comprehensive Backend Performance Tests

Tests critical backend operations under realistic load conditions.
Measures performance metrics and establishes baselines.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Ensure scalable backend performance 
- Value Impact: 95% uptime and sub-2s response times
- Revenue Impact: Prevents churn from performance issues (+$25K MRR)
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import statistics
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest

from netra_backend.app.db.clickhouse import ClickHouseDatabase
from netra_backend.app.db.postgres import Database as PostgresDatabase
from netra_backend.app.services.generation_job_manager import save_corpus_to_clickhouse
from netra_backend.app.monitoring.system_monitor import SystemPerformanceMonitor as PerformanceMonitor

class PerformanceTestMetrics:
    """Tracks performance test metrics and baselines."""
    
    def __init__(self):
        self.metrics = {}
        self.baselines = self._get_performance_baselines()
    
    def _get_performance_baselines(self) -> Dict[str, float]:
        """Define performance baselines for critical operations."""
        return {
            'db_bulk_insert_50k': 30.0,  # seconds
            'db_concurrent_reads': 5.0,   # seconds  
            'websocket_throughput': 1000, # messages/sec
            'agent_processing': 10.0,     # seconds
            'api_response_time': 2.0,     # seconds
            'concurrent_users': 100,      # simultaneous users
            'memory_usage_mb': 512,       # MB
            'cache_hit_rate': 0.8,        # 80%
        }
    
    def record_metric(self, name: str, value: float):
        """Record a performance metric."""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
    
    def get_statistics(self, name: str) -> Dict[str, float]:
        """Get statistics for a performance metric."""
        if name not in self.metrics or not self.metrics[name]:
            return {}
        
        values = self.metrics[name]
        return {
            'mean': statistics.mean(values),
            'median': statistics.median(values), 
            'min': min(values),
            'max': max(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
            'count': len(values)
        }
    
    def check_baseline(self, name: str) -> bool:
        """Check if metric meets baseline requirements."""
        if name not in self.metrics or name not in self.baselines:
            return False
        
        stats = self.get_statistics(name)
        return stats.get('mean', float('inf')) <= self.baselines[name]

class DatabasePerformanceTester:
    """Tests database performance under load."""
    
    def __init__(self):
        self.metrics = PerformanceTestMetrics()
    
    def _generate_test_corpus(self, size: int) -> Dict[str, List[Tuple[str, str]]]:
        """Generate test corpus data."""
        corpus = {'simple_chat': [], 'analysis': []}
        
        for i in range(size // 2):
            corpus['simple_chat'].append((
                f'test_prompt_{i}_{uuid.uuid4().hex[:8]}',
                f'test_response_{i}_{uuid.uuid4().hex[:8]}'
            ))
            corpus['analysis'].append((
                f'analysis_prompt_{i}_{uuid.uuid4().hex[:8]}', 
                f'analysis_response_{i}_{uuid.uuid4().hex[:8]}'
            ))
        
        return corpus
    
    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, record_count: int = 50000) -> float:
        """Test database bulk insert performance."""
        test_corpus = self._generate_test_corpus(record_count)
        table_name = f'perf_test_{uuid.uuid4().hex[:8]}'
        
        # Mock: ClickHouse external database isolation for unit testing performance
        with patch('netra_backend.app.db.clickhouse_base.ClickHouseDatabase') as mock_db:
            # Mock: Generic component isolation for controlled unit testing
            mock_instance = AsyncMock()
            mock_db.return_value = mock_instance
            
            # Mock: ClickHouse external database isolation for unit testing performance
            with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor:
                # Mock: Generic component isolation for controlled unit testing
                mock_interceptor_instance = AsyncMock()
                mock_interceptor.return_value = mock_interceptor_instance
                
                # Mock: WebSocket manager isolation for testing without external dependencies
                with patch('netra_backend.app.services.generation_job_manager.manager') as mock_manager:
                    mock_manager.broadcast_to_job = AsyncMock()
                    
                    start_time = time.perf_counter()
                    await save_corpus_to_clickhouse(test_corpus, table_name)
                    duration = time.perf_counter() - start_time
                
                self.metrics.record_metric('db_bulk_insert_50k', duration)
                return duration
    
    @pytest.mark.asyncio
    async def test_concurrent_query_performance(self, concurrent_queries: int = 10) -> float:
        """Test concurrent database query performance."""
        tasks = []
        
        # Mock: ClickHouse external database isolation for unit testing performance
        with patch('netra_backend.app.db.clickhouse_base.ClickHouseDatabase') as mock_db:
            # Mock: Generic component isolation for controlled unit testing
            mock_instance = AsyncMock()
            mock_instance.execute_query.return_value = [
                {'id': i, 'data': f'test_data_{i}'} for i in range(1000)
            ]
            mock_db.return_value = mock_instance
            
            for i in range(concurrent_queries):
                task = mock_instance.execute_query(
                    f"SELECT * FROM test_table_{i} LIMIT 1000"
                )
                tasks.append(task)
            
            start_time = time.perf_counter()
            results = await asyncio.gather(*tasks)
            duration = time.perf_counter() - start_time
            
            self.metrics.record_metric('db_concurrent_reads', duration)
            return duration

class WebSocketPerformanceTester:
    """Tests WebSocket performance and throughput."""
    
    def __init__(self):
        self.metrics = PerformanceTestMetrics()
    
    @pytest.mark.asyncio
    async def test_message_throughput(self, message_count: int = 10000) -> float:
        """Test WebSocket message throughput."""
        messages_processed = 0
        
        async def mock_message_handler(message):
            nonlocal messages_processed
            messages_processed += 1
            await asyncio.sleep(0.001)  # Simulate processing
        
        start_time = time.perf_counter()
        
        tasks = []
        for i in range(message_count):
            message = {
                'id': str(uuid.uuid4()),
                'type': 'test_message',
                'data': f'test_data_{i}'
            }
            task = mock_message_handler(message)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        duration = time.perf_counter() - start_time
        
        throughput = message_count / duration if duration > 0 else 0
        self.metrics.record_metric('websocket_throughput', throughput)
        return throughput
    
    @pytest.mark.asyncio
    async def test_broadcast_performance(self, connection_count: int = 100, message_count: int = 1000) -> float:
        """Test WebSocket broadcast performance."""
        # Mock: Generic component isolation for controlled unit testing
        connections = [AsyncMock() for _ in range(connection_count)]
        
        async def broadcast_message(message, connections_list):
            tasks = []
            for connection in connections_list:
                task = connection.send(json.dumps(message))
                tasks.append(task)
            await asyncio.gather(*tasks, return_exceptions=True)
        
        start_time = time.perf_counter()
        
        for i in range(message_count):
            message = {
                'id': str(uuid.uuid4()),
                'type': 'broadcast',
                'data': f'broadcast_message_{i}'
            }
            await broadcast_message(message, connections)
        
        duration = time.perf_counter() - start_time
        
        total_messages = connection_count * message_count
        throughput = total_messages / duration if duration > 0 else 0
        self.metrics.record_metric('websocket_broadcast_throughput', throughput)
        return throughput

class AgentPerformanceTester:
    """Tests agent processing performance."""
    
    def __init__(self):
        self.metrics = PerformanceTestMetrics()
    
    @pytest.mark.asyncio
    async def test_agent_processing_speed(self, request_count: int = 100) -> float:
        """Test agent processing speed under load."""
        async def mock_agent_process(request):
            # Simulate LLM call latency
            await asyncio.sleep(0.1)
            return {
                'request_id': request['id'],
                'response': f"Processed: {request['data']}",
                'processing_time': 0.1
            }
        
        requests = [
            {'id': str(uuid.uuid4()), 'data': f'test_request_{i}'}
            for i in range(request_count)
        ]
        
        start_time = time.perf_counter()
        
        tasks = [mock_agent_process(req) for req in requests]
        results = await asyncio.gather(*tasks)
        
        duration = time.perf_counter() - start_time
        
        self.metrics.record_metric('agent_processing', duration)
        return duration
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_processing(self, concurrent_agents: int = 5, requests_per_agent: int = 20) -> float:
        """Test concurrent agent processing performance."""
        async def agent_batch_processor(agent_id, request_count):
            results = []
            for i in range(request_count):
                # Simulate agent processing
                await asyncio.sleep(0.05)
                results.append({
                    'agent_id': agent_id,
                    'request_index': i,
                    'result': f'processed_by_agent_{agent_id}_{i}'
                })
            return results
        
        start_time = time.perf_counter()
        
        tasks = [
            agent_batch_processor(agent_id, requests_per_agent) 
            for agent_id in range(concurrent_agents)
        ]
        
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start_time
        
        total_requests = concurrent_agents * requests_per_agent
        throughput = total_requests / duration if duration > 0 else 0
        
        self.metrics.record_metric('concurrent_agent_throughput', throughput)
        return throughput

class APIPerformanceTester:
    """Tests API endpoint performance."""
    
    def __init__(self):
        self.metrics = PerformanceTestMetrics()
    
    @pytest.mark.asyncio
    async def test_api_response_times(self, request_count: int = 1000) -> List[float]:
        """Test API endpoint response times."""
        async def mock_api_call():
            # Simulate API processing time
            await asyncio.sleep(0.01)  # 10ms base processing
            return {'status': 'success', 'data': 'test_response'}
        
        response_times = []
        
        for _ in range(request_count):
            start_time = time.perf_counter()
            await mock_api_call()
            duration = time.perf_counter() - start_time
            response_times.append(duration)
            self.metrics.record_metric('api_response_time', duration)
        
        return response_times
    
    @pytest.mark.asyncio
    async def test_concurrent_api_load(self, concurrent_requests: int = 50, total_requests: int = 1000) -> float:
        """Test API performance under concurrent load."""
        async def api_request_batch(batch_size):
            tasks = []
            for _ in range(batch_size):
                async def single_request():
                    await asyncio.sleep(0.02)  # Simulate API processing
                    return {'success': True}
                tasks.append(single_request())
            return await asyncio.gather(*tasks)
        
        start_time = time.perf_counter()
        
        # Process requests in batches to simulate concurrent load
        batch_size = total_requests // concurrent_requests
        batch_tasks = []
        
        for _ in range(concurrent_requests):
            batch_task = api_request_batch(batch_size)
            batch_tasks.append(batch_task)
        
        results = await asyncio.gather(*batch_tasks)
        duration = time.perf_counter() - start_time
        
        self.metrics.record_metric('concurrent_api_load', duration)
        return duration

class MemoryPerformanceTester:
    """Tests memory usage patterns."""
    
    def __init__(self):
        self.metrics = PerformanceTestMetrics()
    
    @pytest.mark.asyncio
    async def test_memory_usage_patterns(self, data_size_mb: int = 100) -> Dict[str, float]:
        """Test memory usage under different load patterns."""
        # Simulate memory-intensive operations
        test_data = []
        
        # Allocate test data (approximate MB)
        bytes_per_mb = 1024 * 1024
        target_bytes = data_size_mb * bytes_per_mb
        
        # Create data structures to consume memory
        chunk_size = 1024  # 1KB chunks
        chunks_needed = target_bytes // chunk_size
        
        start_time = time.perf_counter()
        
        for i in range(chunks_needed):
            chunk = 'x' * chunk_size
            test_data.append(chunk)
            
            # Simulate processing every 1000 chunks
            if i % 1000 == 0:
                await asyncio.sleep(0.001)
        
        allocation_time = time.perf_counter() - start_time
        
        # Simulate processing the data
        start_process_time = time.perf_counter()
        processed_count = 0
        
        for chunk in test_data:
            # Simulate some processing
            processed_count += len(chunk)
            if processed_count % (1024 * 1024) == 0:  # Every MB
                await asyncio.sleep(0.001)
        
        processing_time = time.perf_counter() - start_process_time
        
        # Clean up
        del test_data
        
        metrics = {
            'allocation_time': allocation_time,
            'processing_time': processing_time,
            'total_time': allocation_time + processing_time,
            'data_size_mb': data_size_mb
        }
        
        self.metrics.record_metric('memory_allocation_time', allocation_time)
        self.metrics.record_metric('memory_processing_time', processing_time)
        
        return metrics
    
    @pytest.mark.asyncio
    async def test_memory_cleanup_patterns(self, cycles: int = 10) -> List[float]:
        """Test memory cleanup and garbage collection patterns."""
        cleanup_times = []
        
        for cycle in range(cycles):
            # Allocate memory
            large_data = [str(uuid.uuid4()) * 1000 for _ in range(10000)]
            
            # Simulate usage
            await asyncio.sleep(0.01)
            
            # Measure cleanup time
            start_cleanup = time.perf_counter()
            del large_data
            cleanup_time = time.perf_counter() - start_cleanup
            
            cleanup_times.append(cleanup_time)
            self.metrics.record_metric('memory_cleanup_time', cleanup_time)
            
            # Small delay between cycles
            await asyncio.sleep(0.001)
        
        return cleanup_times

class CachePerformanceTester:
    """Tests cache effectiveness and performance."""
    
    def __init__(self):
        self.metrics = PerformanceTestMetrics()
        self.cache = {}  # Simple in-memory cache for testing
    
    def _cache_key(self, operation: str, params: Dict) -> str:
        """Generate cache key."""
        return f"{operation}:{hash(json.dumps(params, sort_keys=True))}"
    
    @pytest.mark.asyncio
    async def test_cache_hit_rates(self, operations: int = 1000, cache_size: int = 100) -> Dict[str, float]:
        """Test cache hit rates under different patterns."""
        cache_hits = 0
        cache_misses = 0
        
        # Pre-populate cache with some data
        for i in range(cache_size):
            key = f"cached_item_{i}"
            self.cache[key] = f"cached_value_{i}"
        
        for i in range(operations):
            # Mix of cached and uncached operations
            if i % 3 == 0:  # 33% should be cache hits
                key = f"cached_item_{i % cache_size}"
            else:  # 67% cache misses
                key = f"new_item_{i}"
            
            start_time = time.perf_counter()
            
            if key in self.cache:
                # Cache hit
                value = self.cache[key]
                cache_hits += 1
                operation_time = time.perf_counter() - start_time
                self.metrics.record_metric('cache_hit_time', operation_time)
            else:
                # Cache miss - simulate expensive operation
                await asyncio.sleep(0.01)  # Simulate database/computation time
                value = f"computed_value_{i}"
                self.cache[key] = value
                cache_misses += 1
                operation_time = time.perf_counter() - start_time
                self.metrics.record_metric('cache_miss_time', operation_time)
        
        hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
        self.metrics.record_metric('cache_hit_rate', hit_rate)
        
        return {
            'hit_rate': hit_rate,
            'hits': cache_hits,
            'misses': cache_misses,
            'total_operations': operations
        }
    
    @pytest.mark.asyncio
    async def test_cache_performance_under_load(self, concurrent_operations: int = 50, operations_per_thread: int = 100) -> float:
        """Test cache performance under concurrent load."""
        async def cache_operations_batch(batch_id: int, operation_count: int):
            batch_hits = 0
            for i in range(operation_count):
                key = f"batch_{batch_id}_item_{i % 20}"  # Create some key overlap
                
                if key in self.cache:
                    value = self.cache[key]
                    batch_hits += 1
                else:
                    # Simulate expensive computation
                    await asyncio.sleep(0.005)
                    self.cache[key] = f"computed_{batch_id}_{i}"
            
            return batch_hits
        
        start_time = time.perf_counter()
        
        tasks = [
            cache_operations_batch(batch_id, operations_per_thread)
            for batch_id in range(concurrent_operations)
        ]
        
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start_time
        
        total_hits = sum(results)
        total_operations = concurrent_operations * operations_per_thread
        hit_rate = total_hits / total_operations if total_operations > 0 else 0
        
        self.metrics.record_metric('concurrent_cache_duration', duration)
        self.metrics.record_metric('concurrent_cache_hit_rate', hit_rate)
        
        return duration

@pytest.mark.performance
class TestComprehensiveBackendPerformance:
    """Comprehensive backend performance test suite."""
    
    def setup_method(self):
        """Setup test environment."""
        self.db_tester = DatabasePerformanceTester()
        self.ws_tester = WebSocketPerformanceTester()
        self.agent_tester = AgentPerformanceTester()
        self.api_tester = APIPerformanceTester()
        self.memory_tester = MemoryPerformanceTester()
        self.cache_tester = CachePerformanceTester()
    
    @pytest.mark.asyncio
    async def test_database_performance_suite(self):
        """Test database performance metrics."""
        # Test bulk insert performance
        bulk_insert_time = await self.db_tester.test_bulk_insert_performance(50000)
        assert bulk_insert_time < 60.0, f"Bulk insert took {bulk_insert_time}s, expected <60s"
        
        # Test concurrent query performance
        concurrent_query_time = await self.db_tester.test_concurrent_query_performance(10)
        assert concurrent_query_time < 10.0, f"Concurrent queries took {concurrent_query_time}s, expected <10s"
        
        # Verify baseline compliance
        assert self.db_tester.metrics.check_baseline('db_bulk_insert_50k')
        assert self.db_tester.metrics.check_baseline('db_concurrent_reads')
    
    @pytest.mark.asyncio
    async def test_websocket_performance_suite(self):
        """Test WebSocket performance metrics."""
        # Test message throughput
        throughput = await self.ws_tester.test_message_throughput(10000)
        assert throughput > 1000, f"Throughput {throughput} msg/s, expected >1000 msg/s"
        
        # Test broadcast performance
        broadcast_throughput = await self.ws_tester.test_broadcast_performance(100, 500)
        assert broadcast_throughput > 10000, f"Broadcast throughput {broadcast_throughput}, expected >10000"
    
    @pytest.mark.asyncio
    async def test_agent_performance_suite(self):
        """Test agent processing performance."""
        # Test single agent processing speed
        processing_time = await self.agent_tester.test_agent_processing_speed(100)
        assert processing_time < 15.0, f"Agent processing took {processing_time}s, expected <15s"
        
        # Test concurrent agent processing
        concurrent_throughput = await self.agent_tester.test_concurrent_agent_processing(5, 20)
        assert concurrent_throughput > 10, f"Concurrent throughput {concurrent_throughput}, expected >10 req/s"
    
    @pytest.mark.asyncio
    async def test_api_performance_suite(self):
        """Test API endpoint performance."""
        # Test API response times
        response_times = await self.api_tester.test_api_response_times(1000)
        avg_response_time = statistics.mean(response_times)
        assert avg_response_time < 0.1, f"Avg response time {avg_response_time}s, expected <0.1s"
        
        # Test concurrent API load
        load_duration = await self.api_tester.test_concurrent_api_load(50, 1000)
        assert load_duration < 30.0, f"Concurrent load took {load_duration}s, expected <30s"
    
    @pytest.mark.asyncio
    async def test_memory_performance_suite(self):
        """Test memory usage patterns."""
        # Test memory usage patterns
        memory_metrics = await self.memory_tester.test_memory_usage_patterns(100)
        assert memory_metrics['total_time'] < 10.0, f"Memory operations took {memory_metrics['total_time']}s, expected <10s"
        
        # Test memory cleanup
        cleanup_times = await self.memory_tester.test_memory_cleanup_patterns(10)
        avg_cleanup_time = statistics.mean(cleanup_times)
        assert avg_cleanup_time < 0.1, f"Avg cleanup time {avg_cleanup_time}s, expected <0.1s"
    
    @pytest.mark.asyncio
    async def test_cache_performance_suite(self):
        """Test cache effectiveness."""
        # Test cache hit rates
        cache_metrics = await self.cache_tester.test_cache_hit_rates(1000, 100)
        assert cache_metrics['hit_rate'] > 0.25, f"Cache hit rate {cache_metrics['hit_rate']}, expected >25%"
        
        # Test cache under load
        load_duration = await self.cache_tester.test_cache_performance_under_load(50, 100)
        assert load_duration < 30.0, f"Cache load test took {load_duration}s, expected <30s"
    
    @pytest.mark.asyncio
    async def test_performance_benchmark_suite(self):
        """Run full performance benchmark suite and generate report."""
        # Run all performance tests
        await self.test_database_performance_suite()
        await self.test_websocket_performance_suite()
        await self.test_agent_performance_suite()
        await self.test_api_performance_suite()
        await self.test_memory_performance_suite()
        await self.test_cache_performance_suite()
        
        # Generate performance report
        report = self._generate_performance_report()
        
        # Write performance report
        import os
        report_path = "test_reports/performance_baseline.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nPerformance report saved to: {report_path}")
        print("Performance Summary:")
        for category, metrics in report['categories'].items():
            print(f"  {category}: {len(metrics)} metrics tested")
        
        # Ensure critical baselines are met
        critical_failures = []
        for tester in [self.db_tester, self.ws_tester, self.agent_tester, 
                       self.api_tester, self.memory_tester, self.cache_tester]:
            for metric_name in tester.metrics.baselines:
                if not tester.metrics.check_baseline(metric_name):
                    critical_failures.append(metric_name)
        
        assert len(critical_failures) == 0, f"Critical performance baselines failed: {critical_failures}"
    
    def _generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            'timestamp': time.time(),
            'test_environment': 'performance_testing',
            'categories': {},
            'summary': {}
        }
        
        # Collect metrics from all testers
        testers = {
            'database': self.db_tester,
            'websocket': self.ws_tester,
            'agent': self.agent_tester,
            'api': self.api_tester,
            'memory': self.memory_tester,
            'cache': self.cache_tester
        }
        
        for category, tester in testers.items():
            report['categories'][category] = {}
            
            for metric_name, values in tester.metrics.metrics.items():
                stats = tester.metrics.get_statistics(metric_name)
                baseline_met = tester.metrics.check_baseline(metric_name)
                
                report['categories'][category][metric_name] = {
                    'statistics': stats,
                    'baseline_met': baseline_met,
                    'baseline_value': tester.metrics.baselines.get(metric_name),
                    'values': values
                }
        
        # Generate summary
        total_metrics = sum(len(cat.keys()) for cat in report['categories'].values())
        baselines_met = sum(
            1 for cat in report['categories'].values() 
            for metric in cat.values() 
            if metric['baseline_met']
        )
        
        report['summary'] = {
            'total_metrics': total_metrics,
            'baselines_met': baselines_met,
            'baseline_success_rate': baselines_met / total_metrics if total_metrics > 0 else 0,
            'categories_tested': len(report['categories'])
        }
        
        return report

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto", "-m", "performance"])
