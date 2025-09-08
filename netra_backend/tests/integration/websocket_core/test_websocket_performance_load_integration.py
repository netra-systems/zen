"""
Test WebSocket Performance and Load Integration

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (high-volume customers)
- Business Goal: Ensure WebSocket system scales to support business growth
- Value Impact: Performance = user satisfaction = revenue retention and growth
- Strategic Impact: Scalability enables platform to grow from 100s to 1000s of concurrent users

MISSION CRITICAL: These tests validate the WebSocket system can handle
real-world production loads while maintaining the 5 critical events that
enable chat business value at scale.

Performance Test Focus Areas:
1. High concurrent user load testing
2. Event throughput and latency under load
3. Memory usage and resource management at scale
4. Connection pool management under stress
5. Event queue performance and backpressure handling
6. Real-time event delivery SLA compliance
7. System recovery and graceful degradation under extreme load

Following TEST_CREATION_GUIDE.md patterns - integration tests with real services.
"""

import asyncio
import json
import time
import statistics
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock

import pytest
import psutil  # For system resource monitoring

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.websocket_helpers import (
    MockWebSocketConnection,
    WebSocketPerformanceMonitor,
    assert_websocket_response_time
)

try:
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from shared.isolated_environment import get_env
    PERFORMANCE_COMPONENTS_AVAILABLE = True
except ImportError as e:
    PERFORMANCE_COMPONENTS_AVAILABLE = False
    pytest.skip(f"Performance test components not available: {e}", allow_module_level=True)


@dataclass
class LoadTestMetrics:
    """Metrics collection for load testing."""
    total_events_sent: int = 0
    total_events_delivered: int = 0
    total_duration: float = 0.0
    average_latency: float = 0.0
    max_latency: float = 0.0
    min_latency: float = float('inf')
    latency_percentiles: Dict[int, float] = field(default_factory=dict)
    error_count: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    successful_connections: int = 0
    failed_connections: int = 0


@dataclass
class PerformanceBenchmarks:
    """Performance benchmarks and SLA targets."""
    max_event_latency_ms: float = 100.0  # 100ms max latency
    min_throughput_events_per_second: float = 1000.0  # 1000 events/sec minimum
    max_memory_growth_mb: float = 200.0  # 200MB max memory growth
    max_cpu_usage_percent: float = 80.0  # 80% max CPU usage
    min_delivery_rate: float = 0.99  # 99% minimum delivery rate


class TestWebSocketPerformanceLoadIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket performance and load handling."""

    async def async_setup(self):
        """Set up performance test environment."""
        await super().async_setup()
        
        self.env = get_env()
        self.env.set("ENVIRONMENT", "test", source="test")
        self.env.set("WEBSOCKET_PERFORMANCE_MODE", "true", source="test")
        self.env.set("WEBSOCKET_CONNECTION_POOL_SIZE", "100", source="test")
        
        # Performance monitoring
        self.performance_monitor = WebSocketPerformanceMonitor()
        self.benchmarks = PerformanceBenchmarks()
        
        # Resource monitoring
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss
        self.initial_cpu_percent = self.process.cpu_percent()
        
        # Test infrastructure
        self.websocket_manager = None
        self.load_test_emitters = []
        self.load_test_connections = []

    async def async_teardown(self):
        """Clean up performance test resources."""
        # Clean up load test resources
        cleanup_tasks = []
        
        for emitter in self.load_test_emitters:
            cleanup_tasks.append(self._safe_cleanup_emitter(emitter))
        
        for connection in self.load_test_connections:
            cleanup_tasks.append(self._safe_cleanup_connection(connection))
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        if self.websocket_manager:
            try:
                await self.websocket_manager.shutdown()
            except Exception:
                pass
        
        # Final resource check
        final_memory = self.process.memory_info().rss
        memory_growth = final_memory - self.initial_memory
        memory_growth_mb = memory_growth / 1024 / 1024
        
        if memory_growth_mb > 100:
            self.logger.warning(f"High memory growth detected: {memory_growth_mb:.1f}MB")
        
        await super().async_teardown()

    async def _safe_cleanup_emitter(self, emitter):
        """Safely clean up emitter."""
        try:
            if hasattr(emitter, 'close'):
                await emitter.close()
        except Exception:
            pass

    async def _safe_cleanup_connection(self, connection):
        """Safely clean up connection."""
        try:
            if hasattr(connection, 'close'):
                await connection.close()
        except Exception:
            pass

    async def _create_high_performance_manager(self, **config_overrides) -> UnifiedWebSocketManager:
        """Create WebSocket manager optimized for high performance."""
        default_config = {
            "connection_pool_size": 100,
            "enable_compression": False,  # Disable for raw performance
            "heartbeat_interval": 30,  # Longer intervals for performance
            "max_retry_attempts": 2,  # Fewer retries for speed
            "enable_rate_limiting": False,  # Disable rate limiting for load test
            "event_queue_size": 10000,  # Large queue for buffering
            "worker_count": 8  # Multiple workers for concurrency
        }
        default_config.update(config_overrides)
        
        manager = UnifiedWebSocketManager(**default_config)
        await manager.initialize()
        self.websocket_manager = manager
        return manager

    async def _create_load_test_users(
        self, 
        user_count: int,
        manager: UnifiedWebSocketManager
    ) -> List[Tuple[str, UserExecutionContext, MockWebSocketConnection, UnifiedWebSocketEmitter]]:
        """Create multiple users for load testing."""
        users = []
        
        for i in range(user_count):
            user_id = f"load_user_{i}_{int(time.time())}"
            
            # Create user context
            context = UserExecutionContext(
                user_id=user_id,
                connection_id=f"load_conn_{i}_{int(time.time())}",
                thread_id=f"load_thread_{i}_{int(time.time())}",
                permissions=["websocket:receive", "agent:execute"],
                is_authenticated=True
            )
            
            # Create connection
            connection = MockWebSocketConnection(user_id)
            
            await manager.add_connection(
                user_id=user_id,
                connection_id=context.connection_id,
                websocket=connection
            )
            
            # Create emitter
            emitter = UnifiedWebSocketEmitter(
                manager=manager,
                user_id=user_id,
                context=context
            )
            
            users.append((user_id, context, connection, emitter))
            self.load_test_emitters.append(emitter)
            self.load_test_connections.append(connection)
        
        return users

    def _collect_system_metrics(self) -> Dict[str, float]:
        """Collect current system performance metrics."""
        memory_info = self.process.memory_info()
        cpu_percent = self.process.cpu_percent()
        
        return {
            "memory_rss_mb": memory_info.rss / 1024 / 1024,
            "memory_vms_mb": memory_info.vms / 1024 / 1024,
            "cpu_percent": cpu_percent,
            "memory_growth_mb": (memory_info.rss - self.initial_memory) / 1024 / 1024
        }

    @pytest.mark.integration
    @pytest.mark.websocket_performance
    async def test_high_concurrent_user_load(self):
        """Test WebSocket system under high concurrent user load."""
        self.performance_monitor.start_monitoring("concurrent_user_load")
        
        manager = await self._create_high_performance_manager()
        
        # Create large number of concurrent users
        user_count = 50
        events_per_user = 20
        
        users = await self._create_load_test_users(user_count, manager)
        
        # Define concurrent event sending task
        async def send_concurrent_events(user_id, emitter, connection, event_count):
            latencies = []
            events_sent = 0
            events_delivered = 0
            
            for event_num in range(event_count):
                try:
                    start_time = time.time()
                    
                    # Send critical WebSocket events
                    if event_num % 5 == 0:
                        await emitter.emit_agent_started(
                            agent_name=f"load_test_agent_{event_num}",
                            user_id=user_id
                        )
                    elif event_num % 5 == 1:
                        await emitter.emit_agent_thinking(
                            reasoning=f"Load test reasoning {event_num}",
                            user_id=user_id
                        )
                    elif event_num % 5 == 2:
                        await emitter.emit_tool_executing(
                            tool_name=f"load_tool_{event_num}",
                            user_id=user_id
                        )
                    elif event_num % 5 == 3:
                        await emitter.emit_tool_completed(
                            tool_name=f"load_tool_{event_num}",
                            user_id=user_id,
                            results={"load_test": True}
                        )
                    else:
                        await emitter.emit_agent_completed(
                            response=f"Load test {event_num} complete",
                            user_id=user_id
                        )
                    
                    events_sent += 1
                    latency = (time.time() - start_time) * 1000  # Convert to ms
                    latencies.append(latency)
                    
                    self.performance_monitor.record_message_sent("concurrent_user_load")
                    
                except Exception as e:
                    self.performance_monitor.record_error("concurrent_user_load", str(e))
            
            # Count delivered events
            await asyncio.sleep(0.5)  # Allow delivery time
            events_delivered = len(connection._sent_messages)
            
            return {
                "user_id": user_id,
                "events_sent": events_sent,
                "events_delivered": events_delivered,
                "latencies": latencies,
                "avg_latency": statistics.mean(latencies) if latencies else 0,
                "max_latency": max(latencies) if latencies else 0
            }
        
        # Execute concurrent load test
        start_time = time.time()
        initial_metrics = self._collect_system_metrics()
        
        tasks = [
            send_concurrent_events(user_id, emitter, connection, events_per_user)
            for user_id, context, connection, emitter in users
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        final_metrics = self._collect_system_metrics()
        
        # Analyze load test results
        successful_results = [r for r in results if isinstance(r, dict)]
        
        load_metrics = LoadTestMetrics()
        load_metrics.total_events_sent = sum(r["events_sent"] for r in successful_results)
        load_metrics.total_events_delivered = sum(r["events_delivered"] for r in successful_results)
        load_metrics.total_duration = total_duration
        load_metrics.successful_connections = len(successful_results)
        load_metrics.failed_connections = user_count - len(successful_results)
        
        # Calculate latency statistics
        all_latencies = []
        for r in successful_results:
            all_latencies.extend(r["latencies"])
        
        if all_latencies:
            load_metrics.average_latency = statistics.mean(all_latencies)
            load_metrics.max_latency = max(all_latencies)
            load_metrics.min_latency = min(all_latencies)
            load_metrics.latency_percentiles = {
                95: statistics.quantiles(all_latencies, n=20)[18],  # 95th percentile
                99: statistics.quantiles(all_latencies, n=100)[98]  # 99th percentile
            }
        
        # System resource metrics
        load_metrics.memory_usage_mb = final_metrics["memory_growth_mb"]
        load_metrics.cpu_usage_percent = final_metrics["cpu_percent"]
        
        # Performance assertions
        events_per_second = load_metrics.total_events_sent / total_duration if total_duration > 0 else 0
        delivery_rate = load_metrics.total_events_delivered / load_metrics.total_events_sent if load_metrics.total_events_sent > 0 else 0
        
        assert events_per_second >= self.benchmarks.min_throughput_events_per_second, \
            f"Throughput below benchmark: {events_per_second:.1f} < {self.benchmarks.min_throughput_events_per_second}"
        
        assert load_metrics.average_latency <= self.benchmarks.max_event_latency_ms, \
            f"Average latency above benchmark: {load_metrics.average_latency:.2f}ms > {self.benchmarks.max_event_latency_ms}ms"
        
        assert load_metrics.memory_usage_mb <= self.benchmarks.max_memory_growth_mb, \
            f"Memory growth above benchmark: {load_metrics.memory_usage_mb:.1f}MB > {self.benchmarks.max_memory_growth_mb}MB"
        
        assert delivery_rate >= self.benchmarks.min_delivery_rate, \
            f"Delivery rate below benchmark: {delivery_rate:.3f} < {self.benchmarks.min_delivery_rate}"
        
        # Log performance results
        self.logger.info(f"Load Test Results: {events_per_second:.1f} events/sec, "
                        f"{load_metrics.average_latency:.2f}ms avg latency, "
                        f"{delivery_rate:.3f} delivery rate, "
                        f"{load_metrics.memory_usage_mb:.1f}MB memory growth")
        
        test_metrics = self.performance_monitor.stop_monitoring("concurrent_user_load")
        self.logger.info(f"Test framework metrics: {test_metrics}")

    @pytest.mark.integration
    @pytest.mark.websocket_performance
    async def test_event_throughput_stress(self):
        """Test maximum event throughput under stress conditions."""
        self.performance_monitor.start_monitoring("throughput_stress")
        
        manager = await self._create_high_performance_manager(
            event_queue_size=50000,  # Very large queue
            worker_count=16  # More workers
        )
        
        # Create moderate number of users with high event volume
        user_count = 20
        events_per_user = 200  # High event count per user
        
        users = await self._create_load_test_users(user_count, manager)
        
        # Stress test with rapid event sending
        async def stress_event_sender(user_id, emitter, connection, event_count):
            events_sent = 0
            start_time = time.time()
            
            # Send events as fast as possible
            for event_num in range(event_count):
                try:
                    # Rotate through all 5 critical event types
                    event_type = event_num % 5
                    
                    if event_type == 0:
                        await emitter.emit_agent_started(
                            agent_name=f"stress_{event_num}",
                            user_id=user_id
                        )
                    elif event_type == 1:
                        await emitter.emit_agent_thinking(
                            reasoning=f"Stress test {event_num}",
                            user_id=user_id
                        )
                    elif event_type == 2:
                        await emitter.emit_tool_executing(
                            tool_name=f"stress_tool_{event_num}",
                            user_id=user_id
                        )
                    elif event_type == 3:
                        await emitter.emit_tool_completed(
                            tool_name=f"stress_tool_{event_num}",
                            user_id=user_id,
                            results={"stress": True}
                        )
                    else:
                        await emitter.emit_agent_completed(
                            response=f"Stress {event_num}",
                            user_id=user_id
                        )
                    
                    events_sent += 1
                    
                    # Minimal delay to prevent overwhelming
                    if event_num % 50 == 0:
                        await asyncio.sleep(0.001)
                    
                except Exception:
                    pass  # Continue sending despite individual failures
            
            duration = time.time() - start_time
            return {"events_sent": events_sent, "duration": duration, "user_id": user_id}
        
        # Execute stress test
        start_time = time.time()
        
        stress_tasks = [
            stress_event_sender(user_id, emitter, connection, events_per_user)
            for user_id, context, connection, emitter in users
        ]
        
        results = await asyncio.gather(*stress_tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # Analyze stress test results
        successful_results = [r for r in results if isinstance(r, dict)]
        total_events_sent = sum(r["events_sent"] for r in successful_results)
        
        # Calculate throughput
        overall_throughput = total_events_sent / total_duration if total_duration > 0 else 0
        
        # Allow time for event delivery
        await asyncio.sleep(2.0)
        
        # Count delivered events
        total_delivered = sum(len(conn._sent_messages) for _, _, conn, _ in users)
        delivery_rate = total_delivered / total_events_sent if total_events_sent > 0 else 0
        
        # Stress test assertions
        assert overall_throughput >= 2000, f"Stress throughput too low: {overall_throughput:.1f} events/sec"
        assert delivery_rate >= 0.95, f"Stress delivery rate too low: {delivery_rate:.3f}"
        
        self.logger.info(f"Stress Test: {overall_throughput:.1f} events/sec throughput, "
                        f"{delivery_rate:.3f} delivery rate")
        
        self.performance_monitor.stop_monitoring("throughput_stress")

    @pytest.mark.integration
    @pytest.mark.websocket_performance
    async def test_memory_efficiency_under_load(self):
        """Test memory efficiency during sustained load."""
        manager = await self._create_high_performance_manager()
        
        initial_memory = self.process.memory_info().rss
        memory_samples = [initial_memory]
        
        # Create users gradually to monitor memory growth
        batch_size = 10
        batches = 5
        events_per_batch = 100
        
        for batch_num in range(batches):
            batch_users = await self._create_load_test_users(batch_size, manager)
            
            # Send events for this batch
            async def batch_event_sender(users, event_count):
                for user_id, context, connection, emitter in users:
                    for event_num in range(event_count):
                        try:
                            await emitter.emit_agent_thinking(
                                reasoning=f"Memory test batch {batch_num} event {event_num}",
                                user_id=user_id
                            )
                        except Exception:
                            pass
                        
                        # Sample memory periodically
                        if event_num % 20 == 0:
                            memory_samples.append(self.process.memory_info().rss)
            
            await batch_event_sender(batch_users, events_per_batch)
            
            # Allow processing and cleanup
            await asyncio.sleep(0.5)
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Sample memory after batch
            current_memory = self.process.memory_info().rss
            memory_samples.append(current_memory)
            
            memory_growth_mb = (current_memory - initial_memory) / 1024 / 1024
            self.logger.info(f"Batch {batch_num + 1}: {memory_growth_mb:.1f}MB memory growth")
        
        # Analyze memory efficiency
        final_memory = memory_samples[-1]
        total_memory_growth = (final_memory - initial_memory) / 1024 / 1024
        
        # Check for memory leaks (growth should be sub-linear with load)
        total_users = batch_size * batches
        total_events = total_users * events_per_batch
        memory_per_event = total_memory_growth / total_events if total_events > 0 else 0
        
        assert total_memory_growth < 500, f"Excessive memory growth: {total_memory_growth:.1f}MB"
        assert memory_per_event < 0.1, f"Memory per event too high: {memory_per_event:.3f}MB/event"
        
        # Check memory is relatively stable (no continuous growth)
        if len(memory_samples) > 10:
            recent_samples = memory_samples[-10:]
            memory_variance = statistics.variance(recent_samples)
            memory_std = statistics.stdev(recent_samples)
            
            # Memory should be relatively stable in recent samples
            assert memory_std / statistics.mean(recent_samples) < 0.1, "Memory usage highly unstable"

    @pytest.mark.integration
    @pytest.mark.websocket_performance
    async def test_connection_pool_scaling_performance(self):
        """Test connection pool performance under scaling scenarios."""
        # Test with increasing connection pool sizes
        pool_sizes = [10, 25, 50, 100]
        scaling_metrics = []
        
        for pool_size in pool_sizes:
            manager = await self._create_high_performance_manager(
                connection_pool_size=pool_size
            )
            
            # Create users up to pool capacity
            user_count = min(pool_size - 2, 20)  # Leave room for pool management
            users = await self._create_load_test_users(user_count, manager)
            
            # Measure connection setup time
            start_time = time.time()
            
            # Send test events to measure pool performance
            async def pool_test_events(emitter, user_id):
                for i in range(10):
                    await emitter.emit_agent_started(
                        agent_name=f"pool_test_{i}",
                        user_id=user_id
                    )
            
            pool_tasks = [
                pool_test_events(emitter, user_id)
                for user_id, context, connection, emitter in users
            ]
            
            await asyncio.gather(*pool_tasks, return_exceptions=True)
            
            pool_duration = time.time() - start_time
            
            # Measure delivery success rate
            await asyncio.sleep(0.5)
            total_delivered = sum(len(conn._sent_messages) for _, _, conn, _ in users)
            expected_events = user_count * 10
            delivery_rate = total_delivered / expected_events if expected_events > 0 else 0
            
            scaling_metrics.append({
                "pool_size": pool_size,
                "user_count": user_count,
                "duration": pool_duration,
                "events_per_second": expected_events / pool_duration if pool_duration > 0 else 0,
                "delivery_rate": delivery_rate
            })
            
            # Clean up manager
            await manager.shutdown()
            self.websocket_manager = None
            
            # Clean up users
            for emitter in self.load_test_emitters:
                await self._safe_cleanup_emitter(emitter)
            
            self.load_test_emitters.clear()
            self.load_test_connections.clear()
        
        # Analyze scaling performance
        for i, metrics in enumerate(scaling_metrics):
            self.logger.info(f"Pool size {metrics['pool_size']}: "
                           f"{metrics['events_per_second']:.1f} events/sec, "
                           f"{metrics['delivery_rate']:.3f} delivery rate")
            
            # Performance should not degrade significantly with larger pools
            assert metrics["delivery_rate"] >= 0.95, \
                f"Pool size {metrics['pool_size']} delivery rate too low: {metrics['delivery_rate']:.3f}"
        
        # Verify scaling efficiency (larger pools should handle more load)
        if len(scaling_metrics) >= 2:
            largest_pool = scaling_metrics[-1]
            smallest_pool = scaling_metrics[0]
            
            # Throughput should scale reasonably with pool size
            throughput_ratio = largest_pool["events_per_second"] / smallest_pool["events_per_second"]
            pool_size_ratio = largest_pool["pool_size"] / smallest_pool["pool_size"]
            
            # Throughput scaling should be at least 50% of pool size scaling
            scaling_efficiency = throughput_ratio / pool_size_ratio
            assert scaling_efficiency >= 0.5, f"Poor scaling efficiency: {scaling_efficiency:.2f}"

    @pytest.mark.integration
    @pytest.mark.websocket_performance
    async def test_real_time_latency_sla_compliance(self):
        """Test real-time latency SLA compliance under various loads."""
        manager = await self._create_high_performance_manager()
        
        # Test latency under increasing loads
        load_levels = [
            {"users": 5, "events_per_user": 20, "send_rate": "normal"},
            {"users": 10, "events_per_user": 30, "send_rate": "fast"},  
            {"users": 20, "events_per_user": 40, "send_rate": "rapid"},
        ]
        
        latency_results = []
        
        for load_level in load_levels:
            users = await self._create_load_test_users(load_level["users"], manager)
            
            # Send events and measure latencies
            async def latency_test_sender(user_id, emitter, event_count, send_rate):
                latencies = []
                
                delay_map = {"normal": 0.1, "fast": 0.05, "rapid": 0.01}
                delay = delay_map.get(send_rate, 0.05)
                
                for event_num in range(event_count):
                    start_time = time.time()
                    
                    await emitter.emit_agent_thinking(
                        reasoning=f"Latency test {event_num}",
                        user_id=user_id,
                        step=event_num + 1,
                        total_steps=event_count
                    )
                    
                    latency = (time.time() - start_time) * 1000  # Convert to ms
                    latencies.append(latency)
                    
                    await asyncio.sleep(delay)
                
                return latencies
            
            # Execute latency tests
            latency_tasks = [
                latency_test_sender(
                    user_id, 
                    emitter, 
                    load_level["events_per_user"], 
                    load_level["send_rate"]
                )
                for user_id, context, connection, emitter in users
            ]
            
            results = await asyncio.gather(*latency_tasks, return_exceptions=True)
            
            # Analyze latencies for this load level
            all_latencies = []
            for result in results:
                if isinstance(result, list):
                    all_latencies.extend(result)
            
            if all_latencies:
                avg_latency = statistics.mean(all_latencies)
                p95_latency = statistics.quantiles(all_latencies, n=20)[18]
                p99_latency = statistics.quantiles(all_latencies, n=100)[98]
                max_latency = max(all_latencies)
                
                latency_results.append({
                    "load": f"{load_level['users']} users, {load_level['send_rate']} rate",
                    "avg_latency": avg_latency,
                    "p95_latency": p95_latency,
                    "p99_latency": p99_latency,
                    "max_latency": max_latency
                })
                
                # SLA compliance checks
                assert avg_latency <= self.benchmarks.max_event_latency_ms, \
                    f"Average latency SLA violation: {avg_latency:.2f}ms > {self.benchmarks.max_event_latency_ms}ms"
                
                assert p95_latency <= self.benchmarks.max_event_latency_ms * 2, \
                    f"P95 latency SLA violation: {p95_latency:.2f}ms > {self.benchmarks.max_event_latency_ms * 2}ms"
            
            # Clean up users for next test
            for emitter in self.load_test_emitters:
                await self._safe_cleanup_emitter(emitter)
            
            self.load_test_emitters.clear()
            self.load_test_connections.clear()
        
        # Log latency results
        for result in latency_results:
            self.logger.info(f"Latency {result['load']}: "
                           f"avg={result['avg_latency']:.2f}ms, "
                           f"p95={result['p95_latency']:.2f}ms, "
                           f"max={result['max_latency']:.2f}ms")

    @pytest.mark.integration
    @pytest.mark.websocket_performance
    async def test_graceful_performance_degradation(self):
        """Test graceful performance degradation under extreme overload."""
        manager = await self._create_high_performance_manager(
            connection_pool_size=20,  # Smaller pool to force overload
            event_queue_size=1000    # Smaller queue to test backpressure
        )
        
        # Create overload scenario
        user_count = 30  # More users than pool can handle efficiently
        events_per_user = 100
        
        users = await self._create_load_test_users(user_count, manager)
        
        # Send overload of events
        async def overload_sender(user_id, emitter, event_count):
            successful_sends = 0
            failed_sends = 0
            
            for event_num in range(event_count):
                try:
                    await emitter.emit_agent_thinking(
                        reasoning=f"Overload test {event_num}",
                        user_id=user_id
                    )
                    successful_sends += 1
                except Exception:
                    failed_sends += 1
                    
                    # Small delay after failure to prevent overwhelming
                    await asyncio.sleep(0.01)
            
            return {"successful": successful_sends, "failed": failed_sends}
        
        # Execute overload test
        start_time = time.time()
        
        overload_tasks = [
            overload_sender(user_id, emitter, events_per_user)
            for user_id, context, connection, emitter in users
        ]
        
        results = await asyncio.gather(*overload_tasks, return_exceptions=True)
        
        duration = time.time() - start_time
        
        # Analyze degradation behavior
        total_successful = sum(r["successful"] for r in results if isinstance(r, dict))
        total_failed = sum(r["failed"] for r in results if isinstance(r, dict))
        total_attempted = total_successful + total_failed
        
        success_rate = total_successful / total_attempted if total_attempted > 0 else 0
        throughput = total_successful / duration if duration > 0 else 0
        
        # Under overload, system should:
        # 1. Continue to function (not crash)
        # 2. Maintain reasonable success rate (graceful degradation)
        # 3. Deliver some events (not complete failure)
        
        assert success_rate >= 0.5, f"System degraded too severely: {success_rate:.3f} success rate"
        assert throughput >= 100, f"Throughput degraded too much: {throughput:.1f} events/sec"
        assert total_successful > 0, "Complete system failure under overload"
        
        self.logger.info(f"Overload handling: {success_rate:.3f} success rate, "
                        f"{throughput:.1f} events/sec under extreme load")
        
        # System should recover after overload
        await asyncio.sleep(2.0)  # Allow recovery time
        
        # Test recovery with light load
        recovery_user = users[0]
        user_id, context, connection, emitter = recovery_user
        
        await emitter.emit_agent_started(
            agent_name="recovery_test",
            user_id=user_id
        )
        
        await asyncio.sleep(0.2)
        
        # Should be able to deliver events normally after recovery
        recent_messages = connection._sent_messages[-5:] if connection._sent_messages else []
        recovery_successful = any("recovery_test" in json.loads(msg).get("agent_name", "") 
                                for msg in recent_messages if msg)
        
        assert recovery_successful, "System did not recover properly after overload"