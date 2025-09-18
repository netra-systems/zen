"""Unit tests for PerformanceCollector (Issue #966)

Tests the performance collector functionality for the new monitoring API endpoints.
Follows existing test patterns and uses SSOT test infrastructure.
"""

import asyncio
import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.monitoring.performance_collector import (
    PerformanceCollector,
    ResponseTimeMetrics,
    ThroughputMetrics,
    ResourceMetrics,
    get_performance_collector,
    record_request_performance
)


class TestPerformanceCollector(SSotAsyncTestCase):
    """Test PerformanceCollector functionality."""
    
    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.collector = PerformanceCollector(window_size=100, retention_hours=1)
    
    async def asyncTearDown(self):
        """Clean up test environment."""
        await self.collector.stop_collection()
        await super().asyncTearDown()
    
    async def test_collector_initialization(self):
        """Test PerformanceCollector initializes correctly."""
        self.assertEqual(self.collector.window_size, 100)
        self.assertEqual(self.collector.retention_hours, 1)
        self.assertEqual(len(self.collector.response_times), 0)
        self.assertEqual(len(self.collector.request_timestamps), 0)
        self.assertEqual(self.collector.error_count, 0)
        self.assertEqual(self.collector.success_count, 0)
    
    async def test_start_stop_collection(self):
        """Test starting and stopping background collection."""
        # Start collection
        await self.collector.start_collection()
        self.assertTrue(self.collector._is_collecting)
        self.assertIsNotNone(self.collector._collection_task)
        
        # Stop collection
        await self.collector.stop_collection()
        self.assertFalse(self.collector._is_collecting)
    
    async def test_record_request_success(self):
        """Test recording successful requests."""
        # Record a successful request
        await self.collector.record_request("/api/test", 250.5, 200)
        
        # Check that metrics were recorded
        self.assertEqual(len(self.collector.response_times), 1)
        self.assertEqual(len(self.collector.request_timestamps), 1)
        self.assertEqual(self.collector.success_count, 1)
        self.assertEqual(self.collector.error_count, 0)
        
        # Check response time was recorded
        timestamp, response_time = self.collector.response_times[0]
        self.assertEqual(response_time, 250.5)
        self.assertAlmostEqual(timestamp, time.time(), delta=1.0)
    
    async def test_record_request_error(self):
        """Test recording error requests."""
        # Record an error request
        await self.collector.record_request("/api/error", 500.0, 500)
        
        # Check that error was recorded
        self.assertEqual(self.collector.success_count, 0)
        self.assertEqual(self.collector.error_count, 1)
    
    async def test_response_time_percentiles_calculation(self):
        """Test response time percentile calculations."""
        # Record multiple response times
        response_times = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        for rt in response_times:
            await self.collector.record_request("/api/test", rt, 200)
        
        # Calculate percentiles
        metrics = self.collector._calculate_response_time_percentiles()
        
        # Verify percentile calculations
        self.assertIsInstance(metrics, ResponseTimeMetrics)
        self.assertEqual(metrics.count, 10)
        self.assertEqual(metrics.min_ms, 100)
        self.assertEqual(metrics.max_ms, 1000)
        self.assertEqual(metrics.p50_ms, 500)  # Median of 10 items
        self.assertAlmostEqual(metrics.mean_ms, 550, delta=1)
    
    async def test_throughput_calculation(self):
        """Test throughput metric calculations."""
        # Record multiple requests over time
        for i in range(10):
            await self.collector.record_request(f"/api/test{i}", 100, 200)
        
        # Manually trigger throughput calculation
        await self.collector._calculate_throughput()
        
        # Check throughput history
        self.assertEqual(len(self.collector.throughput_history), 1)
        
        # Get throughput summary
        throughput = self.collector._calculate_throughput_summary()
        self.assertIsInstance(throughput, ThroughputMetrics)
        self.assertGreaterEqual(throughput.total_requests_1h, 10)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.Process')
    @patch('psutil.disk_usage')
    async def test_resource_collection(self, mock_disk, mock_process, mock_memory, mock_cpu):
        """Test resource metrics collection."""
        # Mock system resource data
        mock_cpu.return_value = 45.5
        mock_memory.return_value = MagicMock(used=1024*1024*1024, percent=75.0)
        mock_process.return_value.num_threads.return_value = 8
        mock_disk.return_value = MagicMock(percent=60.0)
        
        # Mock database connections
        with patch.object(self.collector, '_get_active_connections', return_value=5):
            await self.collector._collect_resource_metrics()
        
        # Check resource history
        self.assertEqual(len(self.collector.resource_history), 1)
        
        # Get resource summary
        resources = self.collector._calculate_resource_summary()
        self.assertIsInstance(resources, ResourceMetrics)
        self.assertEqual(resources.cpu_percent, 45.5)
        self.assertEqual(resources.memory_percent, 75.0)
        self.assertEqual(resources.thread_count, 8)
        self.assertEqual(resources.disk_usage_percent, 60.0)
        self.assertEqual(resources.active_connections, 5)
    
    async def test_health_score_calculation(self):
        """Test health score calculation based on metrics."""
        # Test perfect health score (no metrics)
        score = self.collector._calculate_health_score()
        self.assertEqual(score, 100.0)
        
        # Add some good response times
        for rt in [50, 100, 150, 200]:
            await self.collector.record_request("/api/fast", rt, 200)
        
        score = self.collector._calculate_health_score()
        self.assertEqual(score, 100.0)  # All fast responses
        
        # Add slow response times
        for rt in [1500, 2500]:  # Over thresholds
            await self.collector.record_request("/api/slow", rt, 200)
        
        score = self.collector._calculate_health_score()
        self.assertLess(score, 100.0)  # Should be penalized
    
    async def test_performance_summary(self):
        """Test comprehensive performance summary generation."""
        # Add some test data
        await self.collector.record_request("/api/test1", 100, 200)
        await self.collector.record_request("/api/test2", 200, 200)
        await self.collector.record_request("/api/error", 500, 500)
        
        # Mock resource collection
        with patch.object(self.collector, '_calculate_resource_summary') as mock_resources:
            mock_resources.return_value = ResourceMetrics(
                cpu_percent=50.0,
                memory_mb=512.0,
                memory_percent=60.0,
                active_connections=3,
                thread_count=5,
                disk_usage_percent=40.0
            )
            
            summary = await self.collector.get_performance_summary()
        
        # Verify summary structure
        self.assertIn('response_times', summary)
        self.assertIn('throughput', summary)
        self.assertIn('resources', summary)
        self.assertIn('health_score', summary)
        self.assertIn('error_rate', summary)
        self.assertIn('timestamp', summary)
        
        # Verify response time data
        response_times = summary['response_times']
        self.assertEqual(response_times['sample_count'], 3)
        self.assertGreater(response_times['mean_ms'], 0)
        
        # Verify error rate calculation
        self.assertAlmostEqual(summary['error_rate'], 1/3, places=2)
    
    async def test_reset_metrics(self):
        """Test metrics reset functionality."""
        # Add some data
        await self.collector.record_request("/api/test", 100, 200)
        await self.collector.record_request("/api/error", 200, 500)
        
        # Verify data exists
        self.assertGreater(len(self.collector.response_times), 0)
        self.assertGreater(self.collector.success_count + self.collector.error_count, 0)
        
        # Reset metrics
        await self.collector.reset_metrics()
        
        # Verify data is cleared
        self.assertEqual(len(self.collector.response_times), 0)
        self.assertEqual(len(self.collector.request_timestamps), 0)
        self.assertEqual(self.collector.success_count, 0)
        self.assertEqual(self.collector.error_count, 0)
    
    @patch('netra_backend.app.services.database.connection_monitor.connection_metrics')
    async def test_get_active_connections(self, mock_connection_metrics):
        """Test active database connections retrieval."""
        # Mock connection pool status
        mock_connection_metrics.get_pool_status.return_value = {
            "async_pool": {"checked_out": 3},
            "sync_pool": {"checked_out": 2}
        }
        
        connections = await self.collector._get_active_connections()
        self.assertEqual(connections, 5)
        
        # Test error handling
        mock_connection_metrics.get_pool_status.side_effect = Exception("Connection error")
        connections = await self.collector._get_active_connections()
        self.assertEqual(connections, 0)


class TestPerformanceCollectorGlobal(SSotAsyncTestCase):
    """Test global performance collector functionality."""
    
    async def asyncTearDown(self):
        """Clean up global state."""
        # Reset global collector
        import netra_backend.app.monitoring.performance_collector as module
        module._performance_collector = None
        await super().asyncTearDown()
    
    async def test_get_performance_collector_singleton(self):
        """Test global performance collector singleton pattern."""
        # Get collector twice
        collector1 = await get_performance_collector()
        collector2 = await get_performance_collector()
        
        # Should be the same instance
        self.assertIs(collector1, collector2)
        self.assertTrue(collector1._is_collecting)
    
    async def test_record_request_performance_convenience(self):
        """Test convenience function for recording request performance."""
        # Use convenience function
        await record_request_performance("/api/test", 150.5, 200)
        
        # Get collector and verify data was recorded
        collector = await get_performance_collector()
        self.assertEqual(len(collector.response_times), 1)
        self.assertEqual(collector.success_count, 1)


class TestPerformanceCollectorErrorHandling(SSotAsyncTestCase):
    """Test error handling in PerformanceCollector."""
    
    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.collector = PerformanceCollector()
    
    async def asyncTearDown(self):
        """Clean up test environment."""
        await self.collector.stop_collection()
        await super().asyncTearDown()
    
    async def test_collection_loop_error_recovery(self):
        """Test that collection loop recovers from errors."""
        # Mock an error in resource collection
        with patch.object(self.collector, '_collect_resource_metrics', 
                         side_effect=Exception("Resource error")):
            
            # Start collection
            await self.collector.start_collection()
            
            # Wait briefly for loop to handle error
            await asyncio.sleep(0.1)
            
            # Collection should still be running
            self.assertTrue(self.collector._is_collecting)
    
    async def test_empty_data_handling(self):
        """Test handling of empty data in calculations."""
        # Test with no data
        response_metrics = self.collector._calculate_response_time_percentiles()
        self.assertEqual(response_metrics.count, 0)
        self.assertEqual(response_metrics.mean_ms, 0.0)
        
        throughput_metrics = self.collector._calculate_throughput_summary()
        self.assertEqual(throughput_metrics.requests_per_second, 0.0)
        
        resource_metrics = self.collector._calculate_resource_summary()
        self.assertEqual(resource_metrics.cpu_percent, 0.0)
    
    @patch('psutil.cpu_percent', side_effect=Exception("CPU error"))
    async def test_resource_collection_failure(self, mock_cpu):
        """Test graceful handling of resource collection failures."""
        # Should not raise exception
        await self.collector._collect_resource_metrics()
        
        # Resource history should be empty
        self.assertEqual(len(self.collector.resource_history), 0)


if __name__ == '__main__':
    # Run tests
    import unittest
    unittest.main()