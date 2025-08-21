"""
Performance and Scalability Test Suite for Synthetic Data Service
Testing performance optimization and scalability
"""

import pytest
import asyncio
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.synthetic_data_service import SyntheticDataService
from netra_backend.tests.test_synthetic_data_service_basic import GenerationConfig


@pytest.fixture
def perf_service():
    return SyntheticDataService()


# ==================== Test Suite: Performance and Scalability ====================

class TestPerformanceScalability:
    """Test performance optimization and scalability"""
    async def test_high_throughput_generation(self, perf_service):
        """Test high-throughput data generation"""
        start_time = asyncio.get_event_loop().time()
        
        config = GenerationConfig(
            num_traces=10000,
            parallel_workers=10
        )
        
        records = await perf_service.generate_parallel(config)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        throughput = len(records) / duration
        assert throughput > 1000  # Should generate >1000 records/second
    async def test_memory_efficient_streaming(self, perf_service):
        """Test memory-efficient streaming generation"""
        memory_usage = []
        
        async def monitor_memory():
            import psutil
            process = psutil.Process()
            while True:
                memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
                await asyncio.sleep(0.1)
        
        monitor_task = asyncio.create_task(monitor_memory())
        
        # Generate large dataset in streaming mode
        stream = perf_service.generate_stream(
            GenerationConfig(num_traces=100000)
        )
        
        count = 0
        async for record in stream:
            count += 1
            if count >= 100000:
                break
        
        monitor_task.cancel()
        
        # Memory should not grow linearly with data size
        max_memory = max(memory_usage)
        assert max_memory < 500  # Should stay under 500MB
    async def test_horizontal_scaling(self, perf_service):
        """Test horizontal scaling with multiple workers"""
        worker_counts = [1, 5, 10, 20]
        throughputs = []
        
        for workers in worker_counts:
            config = GenerationConfig(
                num_traces=5000,
                parallel_workers=workers
            )
            
            start = asyncio.get_event_loop().time()
            await perf_service.generate_parallel(config)
            duration = asyncio.get_event_loop().time() - start
            
            throughputs.append(5000 / duration)
        
        # Throughput should increase with workers (with diminishing returns)
        for i in range(1, len(throughputs)):
            assert throughputs[i] > throughputs[i-1]
    async def test_batch_size_optimization(self, perf_service):
        """Test optimal batch size determination"""
        batch_sizes = [10, 50, 100, 500, 1000, 5000]
        best_throughput = 0
        optimal_batch_size = 0
        
        for batch_size in batch_sizes:
            config = GenerationConfig(
                num_traces=10000,
                batch_size=batch_size
            )
            
            start = asyncio.get_event_loop().time()
            await perf_service.generate_batched(config)
            duration = asyncio.get_event_loop().time() - start
            
            throughput = 10000 / duration
            if throughput > best_throughput:
                best_throughput = throughput
                optimal_batch_size = batch_size
        
        # Optimal batch size should be in middle range
        assert 100 <= optimal_batch_size <= 1000
    async def test_connection_pooling_efficiency(self, perf_service):
        """Test connection pool efficiency"""
        pool_metrics = await perf_service.test_connection_pool(
            pool_size=20,
            concurrent_requests=100,
            duration_seconds=10
        )
        
        assert pool_metrics.pool_utilization > 0.7
        assert pool_metrics.connection_wait_time_avg < 100  # ms
        assert pool_metrics.connection_reuse_rate > 0.9
    async def test_cache_effectiveness(self, perf_service):
        """Test corpus cache effectiveness"""
        # First access - cache miss
        start1 = asyncio.get_event_loop().time()
        corpus1 = await perf_service.get_corpus_cached("test_corpus")
        time1 = asyncio.get_event_loop().time() - start1
        
        # Second access - cache hit
        start2 = asyncio.get_event_loop().time()
        corpus2 = await perf_service.get_corpus_cached("test_corpus")
        time2 = asyncio.get_event_loop().time() - start2
        
        assert corpus1 == corpus2
        assert time2 < time1 * 0.1  # Cache hit should be >10x faster
    async def test_auto_scaling_behavior(self, perf_service):
        """Test auto-scaling based on load"""
        config = GenerationConfig(
            num_traces=50000,
            enable_auto_scaling=True,
            min_workers=2,
            max_workers=20
        )
        
        scaling_events = []
        
        async def scaling_callback(event):
            scaling_events.append(event)
        
        await perf_service.generate_with_auto_scaling(
            config,
            scaling_callback=scaling_callback
        )
        
        # Should have scaling events
        scale_up_events = [e for e in scaling_events if e["type"] == "scale_up"]
        scale_down_events = [e for e in scaling_events if e["type"] == "scale_down"]
        
        assert len(scale_up_events) > 0
        assert len(scale_down_events) > 0
    async def test_resource_limit_handling(self, perf_service):
        """Test behavior at resource limits"""
        config = GenerationConfig(
            num_traces=100000,
            memory_limit_mb=100,
            cpu_limit_percent=50
        )
        
        result = await perf_service.generate_with_limits(config)
        
        assert result["completed"] == True
        assert result["memory_exceeded_count"] == 0
        assert result["cpu_throttle_events"] > 0
    async def test_query_optimization(self, perf_service):
        """Test ClickHouse query optimization"""
        # Unoptimized query
        unoptimized_time = await perf_service.benchmark_query(
            "SELECT * FROM corpus WHERE workload_type = 'simple_chat'",
            optimize=False
        )
        
        # Optimized query with projection
        optimized_time = await perf_service.benchmark_query(
            "SELECT prompt, response FROM corpus WHERE workload_type = 'simple_chat'",
            optimize=True
        )
        
        assert optimized_time < unoptimized_time * 0.5
    async def test_burst_load_handling(self, perf_service):
        """Test handling of burst loads"""
        # Normal load
        normal_config = GenerationConfig(
            num_traces=1000,
            arrival_pattern="uniform"
        )
        
        # Burst load
        burst_config = GenerationConfig(
            num_traces=1000,
            arrival_pattern="burst",
            burst_factor=10
        )
        
        normal_result = await perf_service.generate_with_pattern(normal_config)
        burst_result = await perf_service.generate_with_pattern(burst_config)
        
        # Should handle burst without failures
        assert burst_result["success_rate"] > 0.95
        assert burst_result["peak_throughput"] > normal_result["avg_throughput"] * 5


# ==================== Test Runner ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])