"""Performance tests for optimization improvements.

Tests to validate that performance optimizations work correctly and
provide measurable improvements without breaking functionality.
"""

import asyncio
import pytest
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from app.core.performance_optimization_manager import (
    MemoryCache, QueryOptimizer, BatchProcessor, PerformanceOptimizationManager
)
from app.websocket.batch_message_handler import (
    MessageBatcher, BatchConfig, BatchingStrategy, LoadMonitor
)
from app.monitoring.performance_monitor import (
    MetricsCollector, PerformanceMonitor, PerformanceAlertManager
)
from app.db.index_optimizer import PostgreSQLIndexOptimizer, DatabaseIndexManager


class TestMemoryCache:
    """Test memory cache performance and functionality."""
    
    @pytest.fixture
    async def cache(self):
        """Create cache instance for testing."""
        cache = MemoryCache(max_size=100, default_ttl=60)
        yield cache
    
    @pytest.mark.asyncio
    async def test_cache_basic_operations(self, cache):
        """Test basic cache operations."""
        # Test set and get
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"
        
        # Test non-existent key
        result = await cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, cache):
        """Test TTL expiration functionality."""
        # Set with short TTL
        await cache.set("temp_key", "temp_value", ttl=1)
        
        # Should exist immediately
        result = await cache.get("temp_key")
        assert result == "temp_value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        result = await cache.get("temp_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self, cache):
        """Test LRU eviction when cache is full."""
        # Fill cache to capacity
        for i in range(100):
            await cache.set(f"key_{i}", f"value_{i}")
        
        # Add one more item to trigger eviction
        await cache.set("overflow_key", "overflow_value")
        
        # First item should be evicted
        result = await cache.get("key_0")
        assert result is None
        
        # Last item should still exist
        result = await cache.get("overflow_key")
        assert result == "overflow_value"
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, cache):
        """Test cache performance under load."""
        # Populate cache
        items = 1000
        start_time = time.time()
        
        for i in range(items):
            await cache.set(f"perf_key_{i}", f"perf_value_{i}")
        
        set_time = time.time() - start_time
        
        # Read all items
        start_time = time.time()
        
        for i in range(items):
            result = await cache.get(f"perf_key_{i}")
            assert result == f"perf_value_{i}"
        
        get_time = time.time() - start_time
        
        # Performance expectations
        assert set_time < 1.0  # Should set 1000 items in under 1 second
        assert get_time < 0.5  # Should read 1000 items in under 0.5 seconds
        
        # Check cache stats
        stats = cache.get_stats()
        assert stats["total_hits"] >= items


class TestQueryOptimizer:
    """Test database query optimization."""
    
    @pytest.fixture
    def optimizer(self):
        """Create query optimizer for testing."""
        return QueryOptimizer(cache_size=100, cache_ttl=300)
    
    @pytest.mark.asyncio
    async def test_query_caching(self, optimizer):
        """Test query result caching."""
        query = "SELECT * FROM users WHERE id = %s"
        params = {"id": 123}
        
        # Mock executor
        mock_result = {"id": 123, "name": "Test User"}
        executor = AsyncMock(return_value=mock_result)
        
        # First execution should call executor
        result1 = await optimizer.execute_with_cache(query, params, executor)
        assert result1 == mock_result
        assert executor.call_count == 1
        
        # Second execution should use cache
        result2 = await optimizer.execute_with_cache(query, params, executor)
        assert result2 == mock_result
        assert executor.call_count == 1  # Still 1, not called again
    
    @pytest.mark.asyncio
    async def test_query_metrics_tracking(self, optimizer):
        """Test query performance metrics tracking."""
        query = "SELECT * FROM test_table"
        
        # Mock slow executor
        async def slow_executor():
            await asyncio.sleep(0.1)  # 100ms
            return {"result": "data"}
        
        # Execute query multiple times
        for _ in range(5):
            await optimizer.execute_with_cache(query, None, slow_executor)
        
        # Check metrics
        query_hash = optimizer._get_query_hash(query, None)
        metrics = optimizer.query_metrics[query_hash]
        
        assert metrics.execution_count == 5
        assert metrics.avg_execution_time >= 0.1
        assert metrics.total_execution_time >= 0.5
    
    def test_read_query_detection(self, optimizer):
        """Test read query detection logic."""
        assert optimizer._is_read_query("SELECT * FROM users")
        assert optimizer._is_read_query("  select id from table  ")
        assert optimizer._is_read_query("SHOW TABLES")
        assert optimizer._is_read_query("DESCRIBE table_name")
        
        assert not optimizer._is_read_query("INSERT INTO users VALUES (...)")
        assert not optimizer._is_read_query("UPDATE users SET name = 'test'")
        assert not optimizer._is_read_query("DELETE FROM users WHERE id = 1")
    
    def test_cache_ttl_determination(self, optimizer):
        """Test cache TTL determination logic."""
        # User-related queries should have shorter TTL
        assert optimizer._determine_cache_ttl("SELECT * FROM users") == 60
        
        # Config queries should have longer TTL
        assert optimizer._determine_cache_ttl("SELECT * FROM config") == 600
        
        # Audit queries should have very short TTL
        assert optimizer._determine_cache_ttl("SELECT * FROM audit_logs") == 30
        
        # Default TTL for other queries
        assert optimizer._determine_cache_ttl("SELECT * FROM products") == 300


class TestBatchProcessor:
    """Test batch processing functionality."""
    
    @pytest.fixture
    def processor(self):
        """Create batch processor for testing."""
        return BatchProcessor(max_batch_size=5, flush_interval=0.1)
    
    @pytest.mark.asyncio
    async def test_batch_size_flushing(self, processor):
        """Test batch flushing when size limit is reached."""
        processed_batches = []
        
        async def batch_processor(batch):
            processed_batches.append(batch.copy())
        
        # Add items to trigger size-based flush
        for i in range(5):
            await processor.add_to_batch("test_batch", f"item_{i}", batch_processor)
        
        # Wait a moment for processing
        await asyncio.sleep(0.01)
        
        # Should have processed one batch of 5 items
        assert len(processed_batches) == 1
        assert len(processed_batches[0]) == 5
    
    @pytest.mark.asyncio
    async def test_time_based_flushing(self, processor):
        """Test batch flushing based on time interval."""
        processed_batches = []
        
        async def batch_processor(batch):
            processed_batches.append(batch.copy())
        
        # Add fewer items than batch size
        for i in range(3):
            await processor.add_to_batch("test_batch", f"item_{i}", batch_processor)
        
        # Wait for time-based flush
        await asyncio.sleep(0.15)
        
        # Should have processed one batch of 3 items
        assert len(processed_batches) == 1
        assert len(processed_batches[0]) == 3
    
    @pytest.mark.asyncio
    async def test_multiple_batch_keys(self, processor):
        """Test handling multiple batch keys."""
        processed_batches = {"batch1": [], "batch2": []}
        
        async def batch_processor_1(batch):
            processed_batches["batch1"].append(batch.copy())
        
        async def batch_processor_2(batch):
            processed_batches["batch2"].append(batch.copy())
        
        # Add items to different batches
        await processor.add_to_batch("batch1", "item1", batch_processor_1)
        await processor.add_to_batch("batch2", "item2", batch_processor_2)
        await processor.add_to_batch("batch1", "item3", batch_processor_1)
        
        # Flush all batches
        await processor.flush_all()
        
        # Each batch should have been processed separately
        assert len(processed_batches["batch1"]) == 1
        assert len(processed_batches["batch2"]) == 1
        assert len(processed_batches["batch1"][0]) == 2  # item1, item3
        assert len(processed_batches["batch2"][0]) == 1  # item2


class TestMessageBatcher:
    """Test WebSocket message batching."""
    
    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock connection manager."""
        manager = Mock()
        manager.get_user_connections.return_value = [
            Mock(connection_id="conn_1", websocket=AsyncMock()),
            Mock(connection_id="conn_2", websocket=AsyncMock())
        ]
        manager.get_connection_by_id.return_value = Mock(
            websocket=AsyncMock(),
            message_count=0
        )
        return manager
    
    @pytest.fixture
    def batcher(self, mock_connection_manager):
        """Create message batcher for testing."""
        config = BatchConfig(max_batch_size=3, max_wait_time=0.1)
        return MessageBatcher(config, mock_connection_manager)
    
    @pytest.mark.asyncio
    async def test_message_batching_size_trigger(self, batcher, mock_connection_manager):
        """Test message batching triggered by size."""
        # Queue messages
        for i in range(3):
            await batcher.queue_message("user123", {"message": f"test_{i}"})
        
        # Wait for batch processing
        await asyncio.sleep(0.01)
        
        # Should have sent a batch
        conn_mock = mock_connection_manager.get_connection_by_id.return_value
        assert conn_mock.websocket.send_text.called
    
    @pytest.mark.asyncio
    async def test_priority_message_handling(self, batcher, mock_connection_manager):
        """Test high-priority message handling."""
        # Queue high-priority message
        await batcher.queue_message("user123", {"urgent": "data"}, priority=5)
        
        # Wait for processing
        await asyncio.sleep(0.01)
        
        # High-priority messages should be processed quickly
        conn_mock = mock_connection_manager.get_connection_by_id.return_value
        assert conn_mock.websocket.send_text.called
    
    @pytest.mark.asyncio
    async def test_adaptive_batching(self, batcher, mock_connection_manager):
        """Test adaptive batching strategy."""
        batcher.config.strategy = BatchingStrategy.ADAPTIVE
        
        # Simulate high load
        batcher._load_monitor._load_history = [(time.time(), 0.9)]
        
        # Add messages
        for i in range(2):  # Less than max but should trigger due to high load
            await batcher.queue_message("user123", {"message": f"test_{i}"})
        
        await asyncio.sleep(0.01)
        
        # Should have batched due to adaptive strategy
        conn_mock = mock_connection_manager.get_connection_by_id.return_value
        assert conn_mock.websocket.send_text.called


class TestPerformanceMonitoring:
    """Test performance monitoring functionality."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create metrics collector for testing."""
        return MetricsCollector(retention_period=60)
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, metrics_collector):
        """Test basic metrics collection."""
        # Record some metrics
        metrics_collector._record_metric("test.cpu", 50.0)
        metrics_collector._record_metric("test.memory", 75.0)
        
        # Get recent metrics
        cpu_metrics = metrics_collector.get_recent_metrics("test.cpu", 60)
        memory_metrics = metrics_collector.get_recent_metrics("test.memory", 60)
        
        assert len(cpu_metrics) == 1
        assert len(memory_metrics) == 1
        assert cpu_metrics[0].value == 50.0
        assert memory_metrics[0].value == 75.0
    
    @pytest.mark.asyncio
    async def test_metric_summary_calculation(self, metrics_collector):
        """Test metric summary statistics."""
        # Record multiple values
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            metrics_collector._record_metric("test.metric", value)
        
        # Get summary
        summary = metrics_collector.get_metric_summary("test.metric", 60)
        
        assert summary["count"] == 5
        assert summary["min"] == 10.0
        assert summary["max"] == 50.0
        assert summary["avg"] == 30.0
        assert summary["current"] == 50.0
    
    @pytest.mark.asyncio
    async def test_alert_rule_evaluation(self, metrics_collector):
        """Test performance alert rule evaluation."""
        alert_manager = PerformanceAlertManager(metrics_collector)
        
        # Add test rule
        alert_manager.alert_rules["test_alert"] = {
            "metric": "test.cpu",
            "threshold": 80.0,
            "operator": ">", 
            "duration": 5,
            "severity": "warning"
        }
        
        # Record values that exceed threshold
        for _ in range(10):
            metrics_collector._record_metric("test.cpu", 85.0)
        
        # Check alerts
        alerts = await alert_manager.check_alerts()
        
        # Should trigger alert
        assert len(alerts) == 1
        assert alerts[0]["name"] == "test_alert"


class TestDatabaseIndexOptimization:
    """Test database index optimization."""
    
    @pytest.fixture
    def index_optimizer(self):
        """Create index optimizer for testing."""
        return PostgreSQLIndexOptimizer()
    
    def test_performance_indexes_definition(self, index_optimizer):
        """Test that performance indexes are properly defined."""
        indexes = index_optimizer._performance_indexes
        
        # Should have indexes for key tables
        table_names = {idx[0] for idx in indexes}
        assert "userbase" in table_names
        assert "corpus_audit_logs" in table_names
        
        # Should have reasonable index definitions
        user_indexes = [idx for idx in indexes if idx[0] == "userbase"]
        assert len(user_indexes) > 0
        
        # Email index should exist
        email_index = next((idx for idx in user_indexes if "email" in idx[1]), None)
        assert email_index is not None
    
    def test_query_analysis_for_indexes(self, index_optimizer):
        """Test query analysis for index recommendations."""
        query = "SELECT * FROM users WHERE email = 'test@example.com' ORDER BY created_at"
        
        recommendations = index_optimizer._analyze_query_for_indexes(query)
        
        # Should recommend indexes for WHERE and ORDER BY clauses
        assert len(recommendations) >= 1
        
        # Check that table name is extracted correctly
        for rec in recommendations:
            assert rec.table_name == "users"


@pytest.mark.integration
class TestPerformanceOptimizationIntegration:
    """Integration tests for performance optimizations."""
    
    @pytest.mark.asyncio
    async def test_full_optimization_pipeline(self):
        """Test complete optimization pipeline."""
        # Initialize performance manager
        perf_manager = PerformanceOptimizationManager()
        await perf_manager.initialize()
        
        try:
            # Test query optimization
            async def mock_query():
                await asyncio.sleep(0.01)  # Simulate query time
                return {"result": "data"}
            
            # Execute query with optimization
            result = await perf_manager.query_optimizer.execute_with_cache(
                "SELECT * FROM test", None, mock_query
            )
            assert result == {"result": "data"}
            
            # Test batch processing
            processed_items = []
            
            async def batch_processor(items):
                processed_items.extend(items)
            
            # Add items to batch
            for i in range(5):
                await perf_manager.batch_processor.add_to_batch(
                    "test_batch", f"item_{i}", batch_processor
                )
            
            # Wait for processing
            await asyncio.sleep(0.2)
            
            # Should have processed items
            assert len(processed_items) == 5
            
            # Get performance stats
            stats = perf_manager.get_performance_stats()
            assert "query_optimizer" in stats
            assert "cache_stats" in stats
            
        finally:
            await perf_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self):
        """Test performance monitoring integration."""
        monitor = PerformanceMonitor()
        
        try:
            # Start monitoring
            await monitor.start_monitoring()
            
            # Wait for some metrics collection
            await asyncio.sleep(1.0)
            
            # Get dashboard data
            dashboard = monitor.get_performance_dashboard()
            
            assert "timestamp" in dashboard
            assert "system" in dashboard
            assert "memory" in dashboard
            
            # Test operation measurement
            async with monitor.measure_operation("test_operation"):
                await asyncio.sleep(0.1)
            
            # Should have recorded metrics for the operation
            operation_metrics = monitor.metrics_collector.get_recent_metrics(
                "operation.test_operation.duration", 60
            )
            assert len(operation_metrics) > 0
            
        finally:
            await monitor.stop_monitoring()


if __name__ == "__main__":
    # Run performance benchmarks
    import sys
    
    async def run_performance_benchmarks():
        """Run performance benchmarks."""
        print("Running performance optimization benchmarks...")
        
        # Cache performance test
        cache = MemoryCache(max_size=10000, default_ttl=300)
        
        start_time = time.time()
        for i in range(10000):
            await cache.set(f"key_{i}", f"value_{i}")
        set_time = time.time() - start_time
        
        start_time = time.time()
        for i in range(10000):
            await cache.get(f"key_{i}")
        get_time = time.time() - start_time
        
        print(f"Cache Performance:")
        print(f"  Set 10K items: {set_time:.3f}s ({10000/set_time:.0f} ops/sec)")
        print(f"  Get 10K items: {get_time:.3f}s ({10000/get_time:.0f} ops/sec)")
        
        # Batch processing performance test
        processor = BatchProcessor(max_batch_size=100, flush_interval=0.1)
        processed_count = 0
        
        async def counter_processor(batch):
            nonlocal processed_count
            processed_count += len(batch)
        
        start_time = time.time()
        for i in range(1000):
            await processor.add_to_batch("perf_batch", f"item_{i}", counter_processor)
        
        await processor.flush_all()
        batch_time = time.time() - start_time
        
        print(f"Batch Processing Performance:")
        print(f"  Processed {processed_count} items in {batch_time:.3f}s ({processed_count/batch_time:.0f} items/sec)")
        
        print("Performance benchmarks completed!")
    
    if len(sys.argv) > 1 and sys.argv[1] == "benchmark":
        asyncio.run(run_performance_benchmarks())