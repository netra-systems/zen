"""WebSocket Performance Components Testing.

Tests for individual WebSocket performance components under load.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import AsyncMock

from app.websocket.memory_manager import WebSocketMemoryManager
from app.websocket.message_batcher import WebSocketMessageBatcher, BatchConfig
from app.websocket.compression import WebSocketCompressor, CompressionConfig
from app.websocket.performance_monitor import PerformanceMonitor
from app.websocket.state_synchronizer import ConnectionStateSynchronizer
from app.schemas.websocket_models import WebSocketMessage


class TestWebSocketMemoryManagerPerformance:
    """Test memory manager performance under load."""
    
    async def test_memory_manager_under_load(self):
        """Test memory manager with high message volume."""
        memory_manager = WebSocketMemoryManager()
        await memory_manager.start_monitoring()
        
        try:
            await self._simulate_high_message_volume(memory_manager)
            await self._verify_memory_management(memory_manager)
        finally:
            await memory_manager.stop_monitoring()
    
    async def test_memory_cleanup_performance(self):
        """Test memory cleanup performance."""
        memory_manager = WebSocketMemoryManager()
        await memory_manager.start_monitoring()
        
        try:
            await self._add_test_messages(memory_manager, 1000)
            
            # Force cleanup and measure time
            cleanup_start = time.time()
            cleanup_stats = await memory_manager.force_cleanup()
            cleanup_time = time.time() - cleanup_start
            
            assert cleanup_time < 1.0  # Should be fast
            assert cleanup_stats["cleanup_time_seconds"] < 1.0
        finally:
            await memory_manager.stop_monitoring()
    
    async def test_memory_health_monitoring(self):
        """Test memory health monitoring under load."""
        memory_manager = WebSocketMemoryManager()
        await memory_manager.start_monitoring()
        
        try:
            await self._add_test_messages(memory_manager, 500)
            await memory_manager._collect_metrics()
            
            health = memory_manager.check_memory_health()
            assert health["status"] in ["healthy", "issues_detected"]
        finally:
            await memory_manager.stop_monitoring()
    
    async def _simulate_high_message_volume(self, memory_manager):
        """Simulate high message volume."""
        for i in range(1000):
            connection_id = f"conn_{i % 10}"  # 10 connections
            memory_manager.register_connection(AsyncMock(connection_id=connection_id))
            
            # Add many messages per connection
            for j in range(100):
                message = {"data": "x" * 1000}  # 1KB message
                memory_manager.track_message(connection_id, message)
    
    async def _verify_memory_management(self, memory_manager):
        """Verify memory management functionality."""
        cleanup_stats = await memory_manager.force_cleanup()
        await memory_manager._collect_metrics()
        
        memory_stats = memory_manager.get_memory_stats()
        assert memory_stats["monitoring_active"] is True
        assert cleanup_stats["cleanup_time_seconds"] < 1.0
    
    async def _add_test_messages(self, memory_manager, count: int):
        """Add test messages to memory manager."""
        for i in range(count):
            connection_id = f"test_conn_{i % 5}"
            message = {"data": f"test_message_{i}"}
            memory_manager.track_message(connection_id, message)


class TestWebSocketMessageBatcherPerformance:
    """Test message batcher performance under high throughput."""
    
    async def test_message_batcher_performance(self):
        """Test message batcher under high throughput."""
        sent_batches = []
        
        async def mock_send_callback(connection_id: str, batch_data: Dict[str, Any]):
            sent_batches.append((connection_id, batch_data))
        
        config = BatchConfig(
            max_batch_size=50,
            max_wait_time_ms=100,
            max_batch_memory_kb=100
        )
        
        batcher = WebSocketMessageBatcher(config)
        await batcher.start(mock_send_callback)
        
        try:
            await self._send_high_volume_messages(batcher)
            await self._verify_batching_performance(batcher)
        finally:
            await batcher.stop()
    
    async def test_batcher_memory_efficiency(self):
        """Test batcher memory efficiency with large messages."""
        sent_batches = []
        
        async def mock_send_callback(connection_id: str, batch_data: Dict[str, Any]):
            sent_batches.append((connection_id, batch_data))
        
        config = BatchConfig(
            max_batch_size=10,
            max_wait_time_ms=50,
            max_batch_memory_kb=50  # Small memory limit
        )
        
        batcher = WebSocketMessageBatcher(config)
        await batcher.start(mock_send_callback)
        
        try:
            await self._send_large_messages(batcher)
            stats = batcher.get_stats()
            assert stats["metrics"]["total_batches_sent"] > 0
        finally:
            await batcher.stop()
    
    async def _send_high_volume_messages(self, batcher):
        """Send high volume of messages."""
        start_time = time.time()
        messages_sent = 0
        
        for i in range(1000):
            message = WebSocketMessage(
                type="ping",
                payload={"data": f"message_{i}", "size": "x" * 100}
            )
            connection_id = f"conn_{i % 5}"  # 5 connections
            
            success = await batcher.add_message(connection_id, message)
            if success:
                messages_sent += 1
        
        # Wait for final batches
        await asyncio.sleep(0.2)
        return messages_sent, time.time() - start_time
    
    async def _send_large_messages(self, batcher):
        """Send large messages to test memory handling."""
        for i in range(50):
            message = WebSocketMessage(
                type="large_data",
                payload={"data": "x" * 5000}  # 5KB message
            )
            connection_id = f"conn_{i % 3}"
            await batcher.add_message(connection_id, message)
    
    async def _verify_batching_performance(self, batcher):
        """Verify batching performance metrics."""
        stats = batcher.get_stats()
        assert stats["metrics"]["total_batches_sent"] > 0
        assert stats["metrics"]["total_messages_batched"] > 0
        assert stats["metrics"]["average_batch_size"] > 1


class TestWebSocketCompressionPerformance:
    """Test compression performance with various message sizes."""
    
    async def test_compression_performance(self):
        """Test compression with various message sizes."""
        compressor = WebSocketCompressor()
        
        test_cases = [
            {"size": 100, "data": "x" * 100},
            {"size": 1000, "data": "x" * 1000},
            {"size": 10000, "data": "x" * 10000},
            {"size": 100000, "data": "x" * 100000}
        ]
        
        results = []
        
        for test_case in test_cases:
            result = await self._test_compression_case(compressor, test_case)
            results.append(result)
        
        self._verify_compression_results(compressor, results)
    
    async def test_compression_throughput(self):
        """Test compression throughput with multiple messages."""
        compressor = WebSocketCompressor()
        
        start_time = time.time()
        for i in range(100):
            message = {
                "type": "throughput_test",
                "payload": "x" * 1000,  # 1KB message
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            compressed_data, compression_result = compressor.compress_message(message)
            decompressed_message = compressor.decompress_message(compressed_data)
            
            # Verify round-trip integrity
            assert decompressed_message["type"] == message["type"]
        
        test_duration = time.time() - start_time
        throughput = 100 / test_duration
        
        # Should handle at least 50 messages per second
        assert throughput >= 50
    
    async def _test_compression_case(self, compressor, test_case):
        """Test compression for a single case."""
        message = {
            "type": "user_message",
            "payload": test_case["data"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Compress message
        start_time = time.time()
        compressed_data, compression_result = compressor.compress_message(message)
        compression_time = (time.time() - start_time) * 1000
        
        # Decompress message
        start_time = time.time()
        decompressed_message = compressor.decompress_message(compressed_data)
        decompression_time = (time.time() - start_time) * 1000
        
        return {
            "original_size": test_case["size"],
            "compression_ratio": compression_result.compression_ratio,
            "compression_time_ms": compression_time,
            "decompression_time_ms": decompression_time,
            "is_compressed": compression_result.is_compressed
        }
    
    def _verify_compression_results(self, compressor, results):
        """Verify compression performance results."""
        stats = compressor.get_compression_stats()
        assert stats["total_messages"] == len(results)
        
        # Check that larger messages get compressed
        large_message_results = [r for r in results if r["original_size"] >= 1000]
        assert any(r["is_compressed"] for r in large_message_results)
        
        # Check compression times are reasonable (< 10ms per message)
        assert all(r["compression_time_ms"] < 10 for r in results)


class TestWebSocketPerformanceMonitorAlerting:
    """Test performance monitor under load conditions."""
    
    async def test_performance_monitor_alerting(self):
        """Test performance monitor under load conditions."""
        monitor = PerformanceMonitor()
        alerts_received = []
        
        async def alert_callback(alert):
            alerts_received.append(alert)
        
        monitor.register_alert_callback(alert_callback)
        await monitor.start_monitoring()
        
        try:
            await self._simulate_performance_issues(monitor)
            await self._verify_alerts_triggered(monitor, alerts_received)
        finally:
            await monitor.stop_monitoring()
    
    async def _simulate_performance_issues(self, monitor):
        """Simulate various performance issues."""
        # Simulate high response times
        for i in range(100):
            monitor.record_message_response_time(f"conn_{i}", 2000.0)  # 2 second response time
        
        # Simulate high memory usage
        monitor.record_memory_usage(600.0)  # 600MB
        
        # Simulate connection errors
        for i in range(15):
            monitor.record_connection_event(f"conn_{i}", "error")
        
        # Wait for monitoring to process
        await asyncio.sleep(6)  # Monitor checks every 5 seconds
    
    async def _verify_alerts_triggered(self, monitor, alerts_received):
        """Verify that appropriate alerts were triggered."""
        assert len(alerts_received) > 0
        
        alert_types = [alert.metric_name for alert in alerts_received]
        assert "high_response_time" in alert_types
        assert "high_memory_usage" in alert_types
        assert "high_error_rate" in alert_types
        
        # Verify performance summary
        summary = monitor.get_current_performance_summary()
        assert summary["response_time"]["average_ms"] >= 2000
        assert summary["active_alerts"]["total"] > 0


class TestWebSocketStateSynchronizerResilience:
    """Test state synchronizer under connection churn."""
    
    async def test_state_synchronizer_resilience(self):
        """Test state synchronizer under connection churn."""
        from app.websocket.connection import ConnectionManager, ConnectionInfo
        from unittest.mock import MagicMock
        
        connection_manager = ConnectionManager()
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        await synchronizer.start_monitoring()
        
        try:
            await self._simulate_connection_churn(synchronizer)
            await self._verify_synchronizer_stats(synchronizer)
        finally:
            await synchronizer.stop_monitoring()
    
    async def _simulate_connection_churn(self, synchronizer):
        """Simulate rapid connection/disconnection cycles."""
        connections = []
        
        # Create connections
        for i in range(50):
            websocket = MagicMock()
            websocket.client_state.name = "CONNECTED"
            
            conn_info = {
                "websocket": websocket,
                "user_id": f"user_{i}",
                "connection_id": f"conn_{i}"
            }
            
            connections.append(conn_info)
            await synchronizer.register_connection(conn_info)
            await synchronizer.update_connection_activity(conn_info["connection_id"])
        
        # Remove some connections
        for i in range(0, 25):
            await synchronizer.unregister_connection(f"conn_{i}")
        
        # Wait for sync checks
        await asyncio.sleep(1)
    
    async def _verify_synchronizer_stats(self, synchronizer):
        """Verify synchronizer statistics."""
        stats = synchronizer.get_sync_stats()
        assert stats["total_monitored_connections"] == 25  # Remaining connections
        assert stats["monitoring_active"] is True
