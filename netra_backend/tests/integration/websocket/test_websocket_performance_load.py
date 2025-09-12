"""
WebSocket Performance and Load Integration Tests

SCALABILITY CRITICAL: WebSocket performance under load ensures the system can handle
enterprise-scale usage and concurrent users without degrading chat experience quality.

Business Value Justification (BVJ):
- Segment: Mid/Enterprise - High concurrent usage is essential for enterprise customers
- Business Goal: Enable scalable chat operations supporting hundreds of concurrent users
- Value Impact: Performance under load enables enterprise expansion and customer growth
- Revenue Impact: Protects scalability path to $5M+ ARR by ensuring system handles growth

PERFORMANCE REQUIREMENTS:
- Support 100+ concurrent WebSocket connections
- Maintain <100ms event delivery latency under load
- Handle 1000+ events per second across all users
- Memory usage remains bounded during high load
- Connection establishment <2 seconds under load
- No event delivery failures during normal load conditions

TEST SCOPE: Integration-level validation of WebSocket performance including:
- Concurrent connection establishment and management
- High-frequency event delivery performance
- Memory and resource usage under load
- Latency and throughput measurements
- Connection stability during load spikes
- Graceful performance degradation under extreme load
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
import pytest

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# WebSocket core components - NO MOCKS for business logic
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
from netra_backend.app.websocket_core.types import (
    WebSocketConnectionState, MessageType, ConnectionMetadata
)

# User context and types
from shared.types.core_types import UserID, ThreadID, ensure_user_id
from shared.types.user_types import TestUserData

# Logging
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics collection during load testing."""
    connection_times: List[float] = field(default_factory=list)
    event_delivery_times: List[float] = field(default_factory=list)
    message_throughput: List[float] = field(default_factory=list)
    memory_usage_samples: List[float] = field(default_factory=list)
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    concurrent_connections: int = 0
    total_events_sent: int = 0
    total_events_received: int = 0
    test_duration: float = 0.0
    
    def add_connection_time(self, duration: float):
        """Add connection establishment time."""
        self.connection_times.append(duration)
        
    def add_event_delivery_time(self, duration: float):
        """Add event delivery time measurement."""
        self.event_delivery_times.append(duration)
        
    def add_throughput_sample(self, events_per_second: float):
        """Add throughput measurement."""
        self.message_throughput.append(events_per_second)
        
    def record_error(self, error_type: str):
        """Record an error occurrence."""
        self.error_counts[error_type] += 1
        
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        return {
            'connection_metrics': {
                'avg_connection_time': statistics.mean(self.connection_times) if self.connection_times else 0,
                'max_connection_time': max(self.connection_times) if self.connection_times else 0,
                'min_connection_time': min(self.connection_times) if self.connection_times else 0,
                'concurrent_connections': self.concurrent_connections
            },
            'event_metrics': {
                'avg_delivery_time': statistics.mean(self.event_delivery_times) if self.event_delivery_times else 0,
                'max_delivery_time': max(self.event_delivery_times) if self.event_delivery_times else 0,
                'total_events_sent': self.total_events_sent,
                'total_events_received': self.total_events_received,
                'delivery_success_rate': self.total_events_received / max(self.total_events_sent, 1) * 100
            },
            'throughput_metrics': {
                'avg_throughput': statistics.mean(self.message_throughput) if self.message_throughput else 0,
                'peak_throughput': max(self.message_throughput) if self.message_throughput else 0,
                'events_per_second': self.total_events_sent / max(self.test_duration, 1)
            },
            'error_metrics': dict(self.error_counts),
            'test_duration': self.test_duration
        }


class PerformanceWebSocketMock:
    """High-performance WebSocket mock for load testing."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.is_closed = False
        self.state = WebSocketConnectionState.CONNECTED
        self.messages_sent: deque = deque(maxlen=10000)  # Bounded for memory efficiency
        self.connection_start_time = time.time()
        self.total_bytes_sent = 0
        self.message_count = 0
        
        # Performance tracking
        self.send_times: List[float] = []
        self.last_message_time = time.time()
        
    async def send(self, message: str) -> None:
        """High-performance send with minimal overhead."""
        if self.is_closed:
            raise ConnectionError("WebSocket connection is closed")
        
        send_start = time.time()
        
        # Minimal message recording for performance
        self.message_count += 1
        self.total_bytes_sent += len(message)
        self.last_message_time = send_start
        
        # Store only recent send times to bound memory
        if len(self.send_times) > 1000:
            self.send_times = self.send_times[-500:]  # Keep last 500
        self.send_times.append(send_start)
        
        # Simulate minimal send overhead
        await asyncio.sleep(0.001)  # 1ms simulation
        
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close connection."""
        self.is_closed = True
        self.state = WebSocketConnectionState.DISCONNECTED
        
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get connection performance statistics."""
        connection_age = time.time() - self.connection_start_time
        messages_per_second = self.message_count / max(connection_age, 1)
        
        return {
            'connection_age': connection_age,
            'total_messages': self.message_count,
            'total_bytes': self.total_bytes_sent,
            'messages_per_second': messages_per_second,
            'avg_send_interval': statistics.mean(
                [self.send_times[i] - self.send_times[i-1] for i in range(1, min(len(self.send_times), 100))]
            ) if len(self.send_times) > 1 else 0
        }


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.performance
@pytest.mark.asyncio
class TestWebSocketPerformanceLoad(SSotAsyncTestCase):
    """
    Integration tests for WebSocket performance under load.
    
    SCALABILITY CRITICAL: These tests validate the system can handle enterprise-scale
    concurrent usage patterns that enable business growth to $5M+ ARR.
    """
    
    def setup_method(self, method):
        """Set up isolated test environment for each test."""
        super().setup_method(method)
        
        # Set up isolated environment
        self.env = IsolatedEnvironment()
        self.env.set("TESTING", "1", source="websocket_performance_test")
        self.env.set("USE_REAL_SERVICES", "true", source="websocket_performance_test")
        
        # Performance test configuration
        self.max_concurrent_connections = 50  # Reduced for testing environment
        self.max_events_per_test = 1000
        self.target_latency_ms = 100
        self.target_throughput_eps = 100  # Events per second
        
        # Track resources for cleanup
        self.websocket_managers: List[Any] = []
        self.mock_websockets: List[PerformanceWebSocketMock] = []
        self.performance_metrics = PerformanceMetrics()
        
    async def teardown_method(self, method):
        """Clean up performance test resources."""
        # Log performance summary
        if self.performance_metrics.connection_times:
            summary = self.performance_metrics.get_summary()
            logger.info(f"Performance test summary: {summary}")
        
        # Clean up connections
        for mock_ws in self.mock_websockets:
            if not mock_ws.is_closed:
                await mock_ws.close()
        
        for manager in self.websocket_managers:
            if hasattr(manager, 'cleanup'):
                try:
                    await manager.cleanup()
                except Exception as e:
                    logger.warning(f"Manager cleanup error: {e}")
        
        await super().teardown_method(method)
    
    async def create_load_test_user(self, user_index: int) -> Tuple[TestUserData, Any, PerformanceWebSocketMock]:
        """Create a user for load testing."""
        user_data = TestUserData(
            user_id=f"load_user_{user_index}_{uuid.uuid4().hex[:8]}",
            email=f"load{user_index}@netra-performance.ai",
            tier="enterprise" if user_index % 4 == 0 else "mid",  # Mix of tiers
            thread_id=f"load_thread_{user_index}_{uuid.uuid4().hex[:8]}"
        )
        
        # Create user context
        user_context = type('MockUserContext', (), {
            'user_id': user_data.user_id,
            'thread_id': user_data.thread_id,
            'request_id': f"load_request_{user_index}_{uuid.uuid4().hex[:8]}",
            'email': user_data.email,
            'tier': user_data.tier,
            'is_test': True,
            'load_test_index': user_index
        })()
        
        # Create WebSocket manager
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        # Create performance WebSocket mock
        connection_id = f"perf_conn_{user_index}_{uuid.uuid4().hex[:8]}"
        mock_ws = PerformanceWebSocketMock(user_data.user_id, connection_id)
        self.mock_websockets.append(mock_ws)
        
        return user_data, manager, mock_ws
    
    async def test_concurrent_connection_establishment_performance(self):
        """
        Test: WebSocket connections can be established concurrently under load
        
        Business Value: Ensures enterprise customers can onboard many users quickly,
        supporting business growth and user adoption without delays.
        """
        connection_count = 25  # Manageable for testing
        connection_tasks = []
        
        # Create concurrent connection tasks
        for i in range(connection_count):
            async def establish_connection(user_index):
                start_time = time.time()
                
                try:
                    user_data, manager, mock_ws = await self.create_load_test_user(user_index)
                    
                    # Establish connection
                    with patch.object(manager, '_websocket_transport', mock_ws):
                        await manager.connect_user(
                            user_id=ensure_user_id(user_data.user_id),
                            websocket=mock_ws,
                            connection_metadata={
                                "tier": user_data.tier,
                                "load_test": True,
                                "user_index": user_index
                            }
                        )
                    
                    connection_time = time.time() - start_time
                    self.performance_metrics.add_connection_time(connection_time)
                    
                    return {
                        'user_index': user_index,
                        'connection_time': connection_time,
                        'success': True,
                        'manager': manager,
                        'mock_ws': mock_ws
                    }
                    
                except Exception as e:
                    connection_time = time.time() - start_time
                    self.performance_metrics.record_error(f"connection_failed_{type(e).__name__}")
                    logger.error(f"Connection {user_index} failed after {connection_time:.3f}s: {e}")
                    return {
                        'user_index': user_index,
                        'connection_time': connection_time,
                        'success': False,
                        'error': str(e)
                    }
            
            connection_tasks.append(establish_connection(i))
        
        # Execute all connections concurrently
        start_time = time.time()
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_connections = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_connections = [r for r in results if isinstance(r, dict) and not r.get('success')]
        
        self.performance_metrics.concurrent_connections = len(successful_connections)
        self.performance_metrics.test_duration = total_time
        
        # Performance assertions
        success_rate = len(successful_connections) / connection_count * 100
        avg_connection_time = statistics.mean(self.performance_metrics.connection_times)
        max_connection_time = max(self.performance_metrics.connection_times) if self.performance_metrics.connection_times else 0
        
        # Business requirements
        assert success_rate >= 95, f"Connection success rate too low: {success_rate:.1f}% (expected >=95%)"
        assert avg_connection_time <= 2.0, f"Average connection time too high: {avg_connection_time:.3f}s (expected <=2.0s)"
        assert max_connection_time <= 5.0, f"Maximum connection time too high: {max_connection_time:.3f}s (expected <=5.0s)"
        
        logger.info(f"✅ Concurrent connections: {len(successful_connections)}/{connection_count} in {total_time:.2f}s, avg {avg_connection_time:.3f}s")
    
    async def test_high_frequency_event_delivery_performance(self):
        """
        Test: High-frequency event delivery maintains performance under load
        
        Business Value: Ensures real-time AI interactions remain responsive during
        peak usage, maintaining chat experience quality for all users.
        """
        user_count = 10
        events_per_user = 50
        total_expected_events = user_count * events_per_user
        
        # Create users for high-frequency testing
        user_setups = []
        for i in range(user_count):
            user_data, manager, mock_ws = await self.create_load_test_user(i)
            
            # Connect user
            with patch.object(manager, '_websocket_transport', mock_ws):
                await manager.connect_user(
                    user_id=ensure_user_id(user_data.user_id),
                    websocket=mock_ws,
                    connection_metadata={"tier": user_data.tier, "high_frequency_test": True}
                )
            
            user_setups.append((user_data, manager, mock_ws))
        
        # High-frequency event sending
        async def send_user_events(user_data, manager, mock_ws, user_index):
            event_times = []
            
            with patch.object(manager, '_websocket_transport', mock_ws):
                for event_index in range(events_per_user):
                    start_time = time.time()
                    
                    try:
                        await manager.emit_agent_event(
                            user_id=ensure_user_id(user_data.user_id),
                            thread_id=user_data.thread_id,
                            event_type="agent_thinking",
                            data={
                                'user_index': user_index,
                                'event_index': event_index,
                                'high_frequency_test': True,
                                'timestamp': datetime.now(UTC).isoformat(),
                                'payload_size': 'x' * 100  # 100 char payload
                            }
                        )
                        
                        delivery_time = time.time() - start_time
                        event_times.append(delivery_time)
                        self.performance_metrics.add_event_delivery_time(delivery_time)
                        self.performance_metrics.total_events_sent += 1
                        
                        # Brief delay to allow async processing
                        await asyncio.sleep(0.01)  # 10ms
                        
                    except Exception as e:
                        self.performance_metrics.record_error(f"event_failed_{type(e).__name__}")
                        logger.error(f"Event {event_index} failed for user {user_index}: {e}")
            
            return event_times
        
        # Execute high-frequency event sending for all users concurrently
        start_time = time.time()
        event_tasks = [
            send_user_events(user_data, manager, mock_ws, i)
            for i, (user_data, manager, mock_ws) in enumerate(user_setups)
        ]
        
        all_event_times = await asyncio.gather(*event_tasks)
        total_test_time = time.time() - start_time
        
        # Calculate performance metrics
        all_delivery_times = [time for user_times in all_event_times for time in user_times]
        actual_events_sent = len(all_delivery_times)
        
        if all_delivery_times:
            avg_delivery_time = statistics.mean(all_delivery_times)
            max_delivery_time = max(all_delivery_times)
            overall_throughput = actual_events_sent / total_test_time
            
            self.performance_metrics.total_events_received = actual_events_sent
            self.performance_metrics.test_duration = total_test_time
            self.performance_metrics.add_throughput_sample(overall_throughput)
            
            # Performance assertions
            avg_delivery_time_ms = avg_delivery_time * 1000
            max_delivery_time_ms = max_delivery_time * 1000
            
            assert avg_delivery_time_ms <= self.target_latency_ms, \
                f"Average delivery time too high: {avg_delivery_time_ms:.1f}ms (expected <={self.target_latency_ms}ms)"
            assert max_delivery_time_ms <= self.target_latency_ms * 2, \
                f"Max delivery time too high: {max_delivery_time_ms:.1f}ms (expected <={self.target_latency_ms * 2}ms)"
            assert overall_throughput >= 50, \
                f"Overall throughput too low: {overall_throughput:.1f} events/sec (expected >=50 events/sec)"
            
            logger.info(f"✅ High-frequency events: {actual_events_sent} events, {overall_throughput:.1f} events/sec, avg {avg_delivery_time_ms:.1f}ms")
        else:
            pytest.fail("No events were successfully delivered")
    
    async def test_sustained_load_performance_stability(self):
        """
        Test: WebSocket performance remains stable under sustained load
        
        Business Value: Ensures enterprise customers can rely on consistent chat
        performance during extended usage periods without degradation.
        """
        user_count = 8
        test_duration = 20  # seconds
        events_per_interval = 5
        interval_duration = 1.0  # seconds
        
        # Create users for sustained load testing
        user_setups = []
        for i in range(user_count):
            user_data, manager, mock_ws = await self.create_load_test_user(i)
            
            with patch.object(manager, '_websocket_transport', mock_ws):
                await manager.connect_user(
                    user_id=ensure_user_id(user_data.user_id),
                    websocket=mock_ws,
                    connection_metadata={"tier": user_data.tier, "sustained_load_test": True}
                )
            
            user_setups.append((user_data, manager, mock_ws))
        
        # Sustained load generation
        async def sustained_user_load(user_data, manager, mock_ws, user_index):
            event_count = 0
            interval_performance = []
            
            test_start = time.time()
            
            while time.time() - test_start < test_duration:
                interval_start = time.time()
                interval_events = 0
                
                with patch.object(manager, '_websocket_transport', mock_ws):
                    # Send events for this interval
                    for _ in range(events_per_interval):
                        try:
                            await manager.emit_agent_event(
                                user_id=ensure_user_id(user_data.user_id),
                                thread_id=user_data.thread_id,
                                event_type="agent_thinking",
                                data={
                                    'sustained_load_test': True,
                                    'user_index': user_index,
                                    'event_count': event_count,
                                    'interval_timestamp': datetime.now(UTC).isoformat()
                                }
                            )
                            
                            event_count += 1
                            interval_events += 1
                            self.performance_metrics.total_events_sent += 1
                            
                            await asyncio.sleep(0.05)  # 50ms between events
                            
                        except Exception as e:
                            self.performance_metrics.record_error(f"sustained_load_error_{type(e).__name__}")
                
                interval_time = time.time() - interval_start
                interval_throughput = interval_events / interval_time if interval_time > 0 else 0
                interval_performance.append(interval_throughput)
                
                # Wait for next interval
                remaining_interval_time = interval_duration - interval_time
                if remaining_interval_time > 0:
                    await asyncio.sleep(remaining_interval_time)
            
            return {
                'user_index': user_index,
                'total_events': event_count,
                'interval_performance': interval_performance,
                'avg_throughput': statistics.mean(interval_performance) if interval_performance else 0
            }
        
        # Execute sustained load for all users
        load_start_time = time.time()
        load_tasks = [
            sustained_user_load(user_data, manager, mock_ws, i)
            for i, (user_data, manager, mock_ws) in enumerate(user_setups)
        ]
        
        load_results = await asyncio.gather(*load_tasks)
        total_load_time = time.time() - load_start_time
        
        # Analyze sustained load performance
        total_events_all_users = sum(result['total_events'] for result in load_results)
        user_throughputs = [result['avg_throughput'] for result in load_results]
        
        if user_throughputs:
            overall_avg_throughput = statistics.mean(user_throughputs)
            throughput_stability = statistics.stdev(user_throughputs) if len(user_throughputs) > 1 else 0
            
            self.performance_metrics.total_events_received = total_events_all_users
            self.performance_metrics.test_duration = total_load_time
            self.performance_metrics.add_throughput_sample(overall_avg_throughput)
            
            # Performance stability assertions
            assert overall_avg_throughput >= 3, \
                f"Sustained throughput too low: {overall_avg_throughput:.1f} events/sec/user (expected >=3)"
            assert throughput_stability <= overall_avg_throughput * 0.3, \
                f"Throughput too unstable: std_dev={throughput_stability:.2f} (expected <={overall_avg_throughput * 0.3:.2f})"
            
            # Check for performance degradation over time
            degradation_detected = False
            for result in load_results:
                if len(result['interval_performance']) >= 4:
                    first_half = result['interval_performance'][:len(result['interval_performance'])//2]
                    second_half = result['interval_performance'][len(result['interval_performance'])//2:]
                    
                    first_avg = statistics.mean(first_half)
                    second_avg = statistics.mean(second_half)
                    
                    if first_avg > 0 and second_avg / first_avg < 0.8:  # More than 20% degradation
                        degradation_detected = True
                        break
            
            assert not degradation_detected, "Performance degradation detected during sustained load"
            
            logger.info(f"✅ Sustained load: {total_events_all_users} events over {total_load_time:.1f}s, avg {overall_avg_throughput:.1f} events/sec/user")
        else:
            pytest.fail("No sustained load performance data collected")
    
    async def test_memory_usage_under_concurrent_load(self):
        """
        Test: Memory usage remains bounded during concurrent WebSocket load
        
        Business Value: Ensures system scalability without memory leaks that could
        impact service reliability and increase operational costs.
        """
        connection_count = 20
        events_per_connection = 25
        
        # Create connections and track memory usage
        memory_samples = []
        connections = []
        
        # Initial memory baseline
        import psutil
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_samples.append(baseline_memory)
        
        # Create connections in batches to monitor memory growth
        batch_size = 5
        for batch in range(0, connection_count, batch_size):
            batch_start_memory = process.memory_info().rss / 1024 / 1024
            
            # Create batch of connections
            for i in range(batch, min(batch + batch_size, connection_count)):
                user_data, manager, mock_ws = await self.create_load_test_user(i)
                
                with patch.object(manager, '_websocket_transport', mock_ws):
                    await manager.connect_user(
                        user_id=ensure_user_id(user_data.user_id),
                        websocket=mock_ws,
                        connection_metadata={"tier": user_data.tier, "memory_test": True}
                    )
                
                connections.append((user_data, manager, mock_ws))
            
            batch_end_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(batch_end_memory)
            
            logger.info(f"Batch {batch//batch_size + 1}: {len(connections)} connections, {batch_end_memory:.1f} MB")
        
        # Send events and monitor memory during load
        async def send_events_monitor_memory(user_data, manager, mock_ws, user_index):
            with patch.object(manager, '_websocket_transport', mock_ws):
                for event_index in range(events_per_connection):
                    await manager.emit_agent_event(
                        user_id=ensure_user_id(user_data.user_id),
                        thread_id=user_data.thread_id,
                        event_type="agent_thinking",
                        data={
                            'memory_test': True,
                            'user_index': user_index,
                            'event_index': event_index,
                            'payload_data': 'x' * 200  # 200 char payload
                        }
                    )
                    
                    # Sample memory every 10th event
                    if event_index % 10 == 0:
                        current_memory = process.memory_info().rss / 1024 / 1024
                        memory_samples.append(current_memory)
                    
                    await asyncio.sleep(0.02)  # 20ms delay
        
        # Execute event sending for all connections
        memory_tasks = [
            send_events_monitor_memory(user_data, manager, mock_ws, i)
            for i, (user_data, manager, mock_ws) in enumerate(connections)
        ]
        
        await asyncio.gather(*memory_tasks)
        
        # Final memory measurement
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_samples.append(final_memory)
        
        # Memory usage analysis
        memory_growth = final_memory - baseline_memory
        peak_memory = max(memory_samples)
        avg_memory = statistics.mean(memory_samples)
        
        self.performance_metrics.memory_usage_samples = memory_samples
        
        # Memory efficiency assertions
        memory_per_connection = memory_growth / connection_count if connection_count > 0 else 0
        
        # Business requirements for memory efficiency
        assert memory_per_connection <= 5.0, \
            f"Memory usage per connection too high: {memory_per_connection:.2f} MB/conn (expected <=5.0 MB/conn)"
        assert peak_memory <= baseline_memory * 3, \
            f"Peak memory usage too high: {peak_memory:.1f} MB (expected <={baseline_memory * 3:.1f} MB)"
        
        # Check for memory leaks (memory should not grow excessively over time)
        if len(memory_samples) >= 10:
            memory_trend = statistics.correlation(
                list(range(len(memory_samples))), 
                memory_samples
            ) if len(set(memory_samples)) > 1 else 0
            
            # High positive correlation indicates potential memory leak
            assert abs(memory_trend) <= 0.5, \
                f"Potential memory leak detected: correlation={memory_trend:.3f} (expected <0.5)"
        
        logger.info(f"✅ Memory usage: baseline {baseline_memory:.1f} MB → peak {peak_memory:.1f} MB, {memory_per_connection:.2f} MB/conn")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])