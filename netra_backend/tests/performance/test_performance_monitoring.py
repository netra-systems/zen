"""
Performance Tests - Monitoring and Integration
Tests for performance monitoring, database optimization, and integration tests.
Compliance: <300 lines, 25-line max functions, modular design.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from netra_backend.app.monitoring.system_monitor import (
    SystemPerformanceMonitor as PerformanceMonitor,
)
from netra_backend.app.monitoring.metrics_collector import MetricsCollector
from netra_backend.app.monitoring.performance_alerting import PerformanceAlertManager

from netra_backend.app.core.performance_optimization_manager import (
    BatchProcessor,
    MemoryCache,
    PerformanceOptimizationManager,
)
from netra_backend.app.db.index_optimizer import (
    DatabaseIndexManager,
    PostgreSQLIndexOptimizer,
)

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
        # Check for other existing tables
        expected_tables = {"userbase", "messages", "threads", "secrets"}
        actual_tables = table_names.intersection(expected_tables)
        assert len(actual_tables) >= 2, f"Expected at least 2 tables with indexes, got: {actual_tables}"
        
        # Should have reasonable index definitions
        user_indexes = [idx for idx in indexes if idx[0] == "userbase"]
        assert len(user_indexes) > 0
        
        # Email index should exist
        email_index = next((idx for idx in user_indexes if "email" in idx[1]), None)
        assert email_index is not None
    
    @pytest.mark.asyncio
    async def test_query_analysis_for_indexes(self, index_optimizer):
        """Test query analysis for index recommendations."""
        # Test the available async method instead of the non-existent method
        recommendations = await index_optimizer.analyze_query_performance()
        
        # Should return recommendations (could be empty if no slow queries detected)
        assert isinstance(recommendations, list)
        
        # Each recommendation should be an IndexRecommendation object
        for rec in recommendations:
            assert hasattr(rec, 'table_name')
            assert hasattr(rec, 'columns')

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
            
            # Manually flush to ensure processing
            await perf_manager.batch_processor.flush_all()
            
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
