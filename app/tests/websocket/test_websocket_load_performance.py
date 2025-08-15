"""WebSocket Load Testing and Performance Validation.

Comprehensive load testing suite to validate WebSocket performance
improvements and stress test the enhanced functionality.
"""

import asyncio
import json
import time
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import websockets
import pytest
from unittest.mock import AsyncMock

from app.websocket.memory_manager import WebSocketMemoryManager
from app.websocket.message_batcher import WebSocketMessageBatcher, BatchConfig
from app.websocket.compression import WebSocketCompressor, CompressionConfig
from app.websocket.performance_monitor import PerformanceMonitor
from app.websocket.state_synchronizer import ConnectionStateSynchronizer
from app.websocket.reconnection import WebSocketReconnectionManager, ReconnectionConfig
from app.schemas.registry import WebSocketMessage


class LoadTestMetrics:
    """Tracks load test metrics."""
    
    def __init__(self):
        self.connection_times: List[float] = []
        self.message_times: List[float] = []
        self.error_count = 0
        self.successful_connections = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0
        self.memory_usage_samples: List[float] = []
        self.start_time = time.time()
    
    def record_connection_time(self, duration: float):
        """Record connection establishment time."""
        self.connection_times.append(duration)
        self.successful_connections += 1
    
    def record_message_time(self, duration: float):
        """Record message round-trip time."""
        self.message_times.append(duration)
    
    def record_error(self):
        """Record an error."""
        self.error_count += 1
    
    def record_message_sent(self):
        """Record a message sent."""
        self.total_messages_sent += 1
    
    def record_message_received(self):
        """Record a message received."""
        self.total_messages_received += 1
    
    def record_memory_usage(self, usage_mb: float):
        """Record memory usage sample."""
        self.memory_usage_samples.append(usage_mb)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test metrics summary."""
        test_duration = time.time() - self.start_time
        
        return {
            "test_duration_seconds": test_duration,
            "successful_connections": self.successful_connections,
            "error_count": self.error_count,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "message_throughput_per_second": self.total_messages_sent / test_duration if test_duration > 0 else 0,
            "connection_times": {
                "min_ms": min(self.connection_times) * 1000 if self.connection_times else 0,
                "max_ms": max(self.connection_times) * 1000 if self.connection_times else 0,
                "avg_ms": statistics.mean(self.connection_times) * 1000 if self.connection_times else 0,
                "p95_ms": sorted(self.connection_times)[int(len(self.connection_times) * 0.95)] * 1000 if self.connection_times else 0
            },
            "message_times": {
                "min_ms": min(self.message_times) * 1000 if self.message_times else 0,
                "max_ms": max(self.message_times) * 1000 if self.message_times else 0,
                "avg_ms": statistics.mean(self.message_times) * 1000 if self.message_times else 0,
                "p95_ms": sorted(self.message_times)[int(len(self.message_times) * 0.95)] * 1000 if self.message_times else 0
            },
            "memory_usage": {
                "min_mb": min(self.memory_usage_samples) if self.memory_usage_samples else 0,
                "max_mb": max(self.memory_usage_samples) if self.memory_usage_samples else 0,
                "avg_mb": statistics.mean(self.memory_usage_samples) if self.memory_usage_samples else 0
            }
        }


class WebSocketLoadTester:
    """Performs load testing on WebSocket connections."""
    
    def __init__(self, server_url: str = "ws://localhost:8000/ws"):
        self.server_url = server_url
        self.metrics = LoadTestMetrics()
    
    async def simulate_connection(self, connection_id: str, duration_seconds: int, 
                                messages_per_second: int) -> Dict[str, Any]:
        """Simulate a single WebSocket connection."""
        connection_start = time.time()
        
        try:
            # Simulate connection establishment
            websocket = AsyncMock()
            websocket.recv = AsyncMock()
            websocket.send = AsyncMock()
            
            connection_time = time.time() - connection_start
            self.metrics.record_connection_time(connection_time)
            
            # Simulate message exchange
            message_interval = 1.0 / messages_per_second if messages_per_second > 0 else 1.0
            end_time = time.time() + duration_seconds
            
            while time.time() < end_time:
                message_start = time.time()
                
                # Create test message
                test_message = {
                    "type": "test_message",
                    "connection_id": connection_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": "x" * 100  # 100 character payload
                }
                
                # Simulate sending message
                await websocket.send(json.dumps(test_message))
                self.metrics.record_message_sent()
                
                # Simulate receiving response
                await websocket.recv()
                self.metrics.record_message_received()
                
                message_time = time.time() - message_start
                self.metrics.record_message_time(message_time)
                
                # Wait for next message
                await asyncio.sleep(message_interval)
            
            return {"status": "success", "connection_id": connection_id}
            
        except Exception as e:
            self.metrics.record_error()
            return {"status": "error", "connection_id": connection_id, "error": str(e)}
    
    async def run_concurrent_connections_test(self, num_connections: int, 
                                            duration_seconds: int = 30,
                                            messages_per_second: int = 1) -> Dict[str, Any]:
        """Test with multiple concurrent connections."""
        print(f"Starting load test: {num_connections} connections, {duration_seconds}s duration, {messages_per_second} msg/s")
        
        # Create tasks for all connections
        tasks = []
        for i in range(num_connections):
            connection_id = f"load_test_conn_{i}"
            task = asyncio.create_task(
                self.simulate_connection(connection_id, duration_seconds, messages_per_second)
            )
            tasks.append(task)
        
        # Run all connections concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_connections = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
        failed_connections = len(results) - successful_connections
        
        return {
            "test_config": {
                "num_connections": num_connections,
                "duration_seconds": duration_seconds,
                "messages_per_second": messages_per_second
            },
            "results": {
                "successful_connections": successful_connections,
                "failed_connections": failed_connections,
                "success_rate": successful_connections / num_connections
            },
            "metrics": self.metrics.get_summary()
        }


@pytest.mark.asyncio
class TestWebSocketPerformanceComponents:
    """Test individual performance components under load."""
    
    async def test_memory_manager_under_load(self):
        """Test memory manager with high message volume."""
        memory_manager = WebSocketMemoryManager()
        await memory_manager.start_monitoring()
        
        try:
            # Simulate high message volume
            for i in range(1000):
                connection_id = f"conn_{i % 10}"  # 10 connections
                memory_manager.register_connection(AsyncMock(connection_id=connection_id))
                
                # Add many messages
                for j in range(100):
                    message = {"data": "x" * 1000}  # 1KB message
                    memory_manager.track_message(connection_id, message)
            
            # Force cleanup
            cleanup_stats = await memory_manager.force_cleanup()
            
            # Verify memory management
            memory_stats = memory_manager.get_memory_stats()
            assert memory_stats["monitoring_active"] is True
            assert cleanup_stats["cleanup_time_seconds"] < 1.0  # Should be fast
            
            # Check memory health
            health = memory_manager.check_memory_health()
            assert health["status"] in ["healthy", "issues_detected"]
            
        finally:
            await memory_manager.stop_monitoring()
    
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
            # Send high volume of messages
            start_time = time.time()
            messages_sent = 0
            
            for i in range(1000):
                message = WebSocketMessage(
                    type="test_message",
                    payload={"data": f"message_{i}", "size": "x" * 100}
                )
                connection_id = f"conn_{i % 5}"  # 5 connections
                
                success = await batcher.add_message(connection_id, message)
                if success:
                    messages_sent += 1
            
            # Wait for final batches
            await asyncio.sleep(0.2)
            
            test_duration = time.time() - start_time
            
            # Verify batching performance
            stats = batcher.get_stats()
            assert stats["metrics"]["total_batches_sent"] > 0
            assert stats["metrics"]["total_messages_batched"] == messages_sent
            assert stats["metrics"]["average_batch_size"] > 1  # Should batch multiple messages
            
            # Check throughput
            throughput = messages_sent / test_duration
            assert throughput > 1000  # Should handle 1000+ messages per second
            
        finally:
            await batcher.stop()
    
    async def test_compression_performance(self):
        """Test compression with various message sizes."""
        compressor = WebSocketCompressor()
        
        # Test different message sizes
        test_cases = [
            {"size": 100, "data": "x" * 100},
            {"size": 1000, "data": "x" * 1000},
            {"size": 10000, "data": "x" * 10000},
            {"size": 100000, "data": "x" * 100000}
        ]
        
        results = []
        
        for test_case in test_cases:
            message = {
                "type": "test_message",
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
            
            results.append({
                "original_size": test_case["size"],
                "compression_ratio": compression_result.compression_ratio,
                "compression_time_ms": compression_time,
                "decompression_time_ms": decompression_time,
                "is_compressed": compression_result.is_compressed
            })
        
        # Verify compression performance
        stats = compressor.get_compression_stats()
        assert stats["total_messages"] == len(test_cases)
        
        # Check that larger messages get compressed
        large_message_results = [r for r in results if r["original_size"] >= 1000]
        assert any(r["is_compressed"] for r in large_message_results)
        
        # Check compression times are reasonable (< 10ms per message)
        assert all(r["compression_time_ms"] < 10 for r in results)
    
    async def test_performance_monitor_alerting(self):
        """Test performance monitor under load conditions."""
        monitor = PerformanceMonitor()
        alerts_received = []
        
        async def alert_callback(alert):
            alerts_received.append(alert)
        
        monitor.register_alert_callback(alert_callback)
        await monitor.start_monitoring()
        
        try:
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
            
            # Verify alerts were triggered
            assert len(alerts_received) > 0
            
            alert_types = [alert.metric_name for alert in alerts_received]
            assert "high_response_time" in alert_types
            assert "high_memory_usage" in alert_types
            assert "high_error_rate" in alert_types
            
            # Verify performance summary
            summary = monitor.get_current_performance_summary()
            assert summary["response_time"]["average_ms"] >= 2000
            assert summary["active_alerts"]["total"] > 0
            
        finally:
            await monitor.stop_monitoring()
    
    async def test_state_synchronizer_resilience(self):
        """Test state synchronizer under connection churn."""
        from app.websocket.connection import ConnectionManager, ConnectionInfo
        from unittest.mock import MagicMock
        
        connection_manager = ConnectionManager()
        synchronizer = ConnectionStateSynchronizer(connection_manager)
        
        await synchronizer.start_monitoring()
        
        try:
            # Simulate rapid connection/disconnection cycles
            connections = []
            
            for i in range(50):
                # Create mock connection
                websocket = MagicMock()
                websocket.client_state.name = "CONNECTED"
                
                conn_info = ConnectionInfo(
                    websocket=websocket,
                    user_id=f"user_{i}",
                    connection_id=f"conn_{i}"
                )
                
                connections.append(conn_info)
                await synchronizer.register_connection(conn_info)
                
                # Simulate some activity
                await synchronizer.update_connection_activity(conn_info.connection_id)
            
            # Simulate some connections becoming stale
            for i in range(0, 25):
                await synchronizer.unregister_connection(f"conn_{i}")
            
            # Wait for sync checks
            await asyncio.sleep(1)
            
            # Verify synchronizer stats
            stats = synchronizer.get_sync_stats()
            assert stats["total_monitored_connections"] == 25  # Remaining connections
            assert stats["monitoring_active"] is True
            
        finally:
            await synchronizer.stop_monitoring()


@pytest.mark.asyncio
class TestWebSocketLoadScenarios:
    """Test realistic load scenarios."""
    
    async def test_moderate_load_scenario(self):
        """Test moderate load: 100 connections, 10 messages/sec each."""
        tester = WebSocketLoadTester()
        
        results = await tester.run_concurrent_connections_test(
            num_connections=100,
            duration_seconds=10,
            messages_per_second=10
        )
        
        # Verify performance targets
        assert results["results"]["success_rate"] >= 0.95  # 95% success rate
        assert results["metrics"]["message_throughput_per_second"] >= 800  # 800+ msg/s
        assert results["metrics"]["connection_times"]["avg_ms"] < 100  # < 100ms connection time
        assert results["metrics"]["message_times"]["avg_ms"] < 50  # < 50ms message round-trip
    
    async def test_high_load_scenario(self):
        """Test high load: 500 connections, 5 messages/sec each."""
        tester = WebSocketLoadTester()
        
        results = await tester.run_concurrent_connections_test(
            num_connections=500,
            duration_seconds=10,
            messages_per_second=5
        )
        
        # Verify system can handle high connection count
        assert results["results"]["success_rate"] >= 0.90  # 90% success rate under high load
        assert results["metrics"]["message_throughput_per_second"] >= 2000  # 2000+ msg/s
        assert results["metrics"]["connection_times"]["avg_ms"] < 200  # < 200ms connection time
        assert results["metrics"]["error_count"] < 50  # Limited errors
    
    async def test_burst_load_scenario(self):
        """Test burst load: rapid message sending."""
        tester = WebSocketLoadTester()
        
        results = await tester.run_concurrent_connections_test(
            num_connections=50,
            duration_seconds=5,
            messages_per_second=50  # High burst rate
        )
        
        # Verify system handles message bursts
        assert results["results"]["success_rate"] >= 0.85  # 85% success rate during bursts
        assert results["metrics"]["message_throughput_per_second"] >= 2000  # High throughput
        assert results["metrics"]["message_times"]["p95_ms"] < 100  # 95th percentile < 100ms


@pytest.mark.asyncio
async def test_integrated_performance_improvements():
    """Integration test of all performance improvements working together."""
    
    # Initialize all components
    memory_manager = WebSocketMemoryManager()
    performance_monitor = PerformanceMonitor()
    
    # Mock send callback for batcher
    sent_messages = []
    async def mock_send_callback(connection_id: str, batch_data: Dict[str, Any]):
        sent_messages.append((connection_id, batch_data))
    
    batcher = WebSocketMessageBatcher()
    compressor = WebSocketCompressor()
    
    # Start monitoring
    await memory_manager.start_monitoring()
    await performance_monitor.start_monitoring()
    await batcher.start(mock_send_callback)
    
    try:
        # Simulate integrated workload
        start_time = time.time()
        
        for i in range(500):
            connection_id = f"conn_{i % 10}"
            
            # Register with memory manager
            memory_manager.register_connection(AsyncMock(connection_id=connection_id))
            
            # Create message
            message_data = {
                "type": "integrated_test",
                "payload": {"data": "x" * 500, "id": i},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Compress message
            compressed_data, compression_result = compressor.compress_message(message_data)
            
            # Track with memory manager
            memory_manager.track_message(connection_id, message_data)
            
            # Add to batcher
            ws_message = WebSocketMessage(type="integrated_test", payload=message_data["payload"])
            await batcher.add_message(connection_id, ws_message)
            
            # Record metrics
            performance_monitor.record_message_response_time(connection_id, 25.0)  # 25ms response time
            performance_monitor.record_message_throughput(1)
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        test_duration = time.time() - start_time
        
        # Verify integrated performance
        
        # Memory management
        memory_stats = memory_manager.get_memory_stats()
        assert memory_stats["monitoring_active"] is True
        
        # Compression
        compression_stats = compressor.get_compression_stats()
        assert compression_stats["total_messages"] == 500
        
        # Batching
        batch_stats = batcher.get_stats()
        assert batch_stats["metrics"]["total_messages_batched"] > 0
        
        # Performance monitoring
        perf_summary = performance_monitor.get_current_performance_summary()
        assert perf_summary["response_time"]["average_ms"] < 100
        
        # Overall throughput
        throughput = 500 / test_duration
        assert throughput > 500  # Should handle 500+ messages per second
        
        print(f"Integrated test completed: {throughput:.1f} msg/s throughput")
        
    finally:
        # Cleanup
        await memory_manager.stop_monitoring()
        await performance_monitor.stop_monitoring()
        await batcher.stop()


if __name__ == "__main__":
    # Run performance tests
    asyncio.run(test_integrated_performance_improvements())