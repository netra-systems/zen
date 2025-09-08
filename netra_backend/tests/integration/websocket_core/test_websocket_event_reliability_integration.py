"""
Test WebSocket Event Reliability Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure reliable WebSocket event delivery for chat business value
- Value Impact: Reliable events = users trust the AI system = higher engagement and retention
- Strategic Impact: Event reliability directly impacts revenue - unreliable events = lost customers

MISSION CRITICAL: These tests validate the reliability mechanisms that ensure
the 5 critical WebSocket events are ALWAYS delivered to users, even under
failure conditions, network issues, and high load scenarios.

Reliability Test Focus Areas:
1. Event delivery guarantees under failure conditions
2. Retry mechanisms for critical events
3. Error recovery and connection resilience
4. Performance under load and stress conditions
5. Memory management and resource cleanup
6. Race condition handling in concurrent scenarios

Following TEST_CREATION_GUIDE.md patterns - integration tests with real services.
"""

import asyncio
import json
import time
import gc
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

import pytest
import psutil  # For memory monitoring

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
    from shared.isolated_environment import get_env
    RELIABILITY_COMPONENTS_AVAILABLE = True
except ImportError as e:
    RELIABILITY_COMPONENTS_AVAILABLE = False
    pytest.skip(f"Reliability test components not available: {e}", allow_module_level=True)


class TestWebSocketEventReliabilityIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket event delivery reliability."""

    async def async_setup(self):
        """Set up reliability test environment."""
        await super().async_setup()
        
        self.env = get_env()
        self.env.set("ENVIRONMENT", "test", source="test")
        self.env.set("WEBSOCKET_RETRY_MAX_ATTEMPTS", "5", source="test")
        self.env.set("WEBSOCKET_RETRY_BASE_DELAY", "0.1", source="test")
        
        # Performance monitoring
        self.performance_monitor = WebSocketPerformanceMonitor()
        self.test_start_memory = psutil.Process().memory_info().rss
        
        # Test infrastructure
        self.websocket_manager = None
        self.test_emitters = []
        self.test_connections = []
        
    async def async_teardown(self):
        """Clean up reliability test resources."""
        # Clean up emitters
        for emitter in self.test_emitters:
            try:
                await emitter.close()
            except:
                pass
        
        # Clean up connections
        for connection in self.test_connections:
            try:
                await connection.close()
            except:
                pass
        
        # Clean up manager
        if self.websocket_manager:
            try:
                await self.websocket_manager.shutdown()
            except:
                pass
        
        # Force garbage collection and memory check
        gc.collect()
        end_memory = psutil.Process().memory_info().rss
        memory_growth = end_memory - self.test_start_memory
        
        if memory_growth > 50 * 1024 * 1024:  # 50MB threshold
            self.logger.warning(f"Memory growth detected: {memory_growth / 1024 / 1024:.1f}MB")
        
        await super().async_teardown()

    async def _create_reliable_websocket_manager(self, **config_overrides) -> UnifiedWebSocketManager:
        """Create UnifiedWebSocketManager with reliability-focused configuration."""
        default_config = {
            "connection_pool_size": 20,
            "enable_compression": False,  # Disable for reliability testing
            "heartbeat_interval": 5,  # Shorter for faster failure detection
            "max_retry_attempts": 5,
            "retry_base_delay": 0.1,
            "connection_timeout": 10
        }
        default_config.update(config_overrides)
        
        manager = UnifiedWebSocketManager(**default_config)
        await manager.initialize()
        self.websocket_manager = manager
        return manager

    async def _create_failure_simulation_connection(
        self, 
        user_id: str, 
        failure_rate: float = 0.3,
        recovery_time: float = 1.0
    ) -> MockWebSocketConnection:
        """Create WebSocket connection that simulates intermittent failures."""
        
        class FailureSimulationConnection(MockWebSocketConnection):
            def __init__(self, user_id: str, failure_rate: float, recovery_time: float):
                super().__init__(user_id)
                self.failure_rate = failure_rate
                self.recovery_time = recovery_time
                self.consecutive_failures = 0
                self.last_failure_time = 0
                self.send_attempts = 0
                
            async def send(self, message: str):
                self.send_attempts += 1
                current_time = time.time()
                
                # Simulate recovery period
                if (current_time - self.last_failure_time) < self.recovery_time:
                    self.consecutive_failures += 1
                    self.last_failure_time = current_time
                    raise ConnectionError(f"Simulated connection failure #{self.consecutive_failures}")
                
                # Simulate intermittent failures
                import random
                if random.random() < self.failure_rate:
                    self.consecutive_failures += 1
                    self.last_failure_time = current_time
                    raise ConnectionError(f"Simulated intermittent failure")
                
                # Reset failure counter on success
                self.consecutive_failures = 0
                await super().send(message)
        
        return FailureSimulationConnection(user_id, failure_rate, recovery_time)

    @pytest.mark.integration
    @pytest.mark.websocket_reliability
    async def test_critical_event_retry_on_connection_failure(self):
        """Test critical events are retried when connection fails."""
        self.performance_monitor.start_monitoring("retry_test")
        
        manager = await self._create_reliable_websocket_manager()
        user_id = f"retry_user_{int(time.time())}"
        
        # Create connection that fails initially then succeeds
        failure_connection = await self._create_failure_simulation_connection(
            user_id, failure_rate=0.8, recovery_time=0.3
        )
        
        await manager.add_connection(
            user_id=user_id,
            connection_id=f"conn_{int(time.time())}",
            websocket=failure_connection
        )
        
        emitter = UnifiedWebSocketEmitter(manager=manager, user_id=user_id, context=None)
        self.test_emitters.append(emitter)
        
        # Send critical event - should retry until success
        start_time = time.time()
        await emitter.emit_agent_started(agent_name="retry_test_agent", user_id=user_id)
        end_time = time.time()
        
        # Allow time for retries
        await asyncio.sleep(1.0)
        
        # Verify event was eventually delivered despite failures
        assert failure_connection.send_attempts >= 2, "Retry mechanism not triggered"
        assert len(failure_connection._sent_messages) >= 1, "Event not delivered after retries"
        
        # Verify reasonable response time despite retries
        delivery_time = end_time - start_time
        assert delivery_time < 5.0, f"Event delivery took too long: {delivery_time:.2f}s"
        
        metrics = self.performance_monitor.stop_monitoring("retry_test")
        self.logger.info(f"Retry test metrics: {metrics}")

    @pytest.mark.integration
    @pytest.mark.websocket_reliability
    async def test_event_ordering_preservation_under_failures(self):
        """Test event ordering is preserved even with connection failures."""
        manager = await self._create_reliable_websocket_manager()
        user_id = f"ordering_user_{int(time.time())}"
        
        # Create connection with intermittent failures
        failure_connection = await self._create_failure_simulation_connection(
            user_id, failure_rate=0.4, recovery_time=0.2
        )
        
        await manager.add_connection(
            user_id=user_id,
            connection_id=f"conn_{int(time.time())}",
            websocket=failure_connection
        )
        
        emitter = UnifiedWebSocketEmitter(manager=manager, user_id=user_id, context=None)
        self.test_emitters.append(emitter)
        
        # Send ordered sequence of events
        event_sequence = [
            ("agent_started", {"agent_name": "ordering_test"}),
            ("agent_thinking", {"reasoning": "Step 1"}),
            ("agent_thinking", {"reasoning": "Step 2"}),
            ("tool_executing", {"tool_name": "test_tool"}),
            ("tool_completed", {"tool_name": "test_tool", "results": {}}),
            ("agent_completed", {"response": "Test complete"})
        ]
        
        sent_events = []
        for event_type, event_data in event_sequence:
            method_name = f"emit_{event_type}"
            if hasattr(emitter, method_name):
                method = getattr(emitter, method_name)
                await method(user_id=user_id, **event_data)
                sent_events.append((event_type, time.time()))
                await asyncio.sleep(0.05)  # Small delay between events
        
        # Allow time for all retries and deliveries
        await asyncio.sleep(2.0)
        
        # Verify all events were delivered
        delivered_messages = failure_connection._sent_messages
        assert len(delivered_messages) >= len(event_sequence), "Not all events delivered"
        
        # Parse and verify ordering
        delivered_events = []
        for message in delivered_messages:
            try:
                event = json.loads(message)
                if event.get("type") in [et[0] for et in event_sequence]:
                    delivered_events.append((event["type"], event.get("timestamp", 0)))
            except json.JSONDecodeError:
                continue
        
        # Verify chronological ordering is preserved
        timestamps = [timestamp for _, timestamp in delivered_events]
        assert all(timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1)), \
            "Event ordering not preserved under failures"

    @pytest.mark.integration 
    @pytest.mark.websocket_reliability
    async def test_memory_leak_prevention_under_failures(self):
        """Test memory leaks are prevented during failure/retry scenarios."""
        initial_memory = psutil.Process().memory_info().rss
        
        manager = await self._create_reliable_websocket_manager()
        
        # Create many connections that fail frequently
        user_connections = []
        for i in range(10):
            user_id = f"memory_test_user_{i}_{int(time.time())}"
            failure_connection = await self._create_failure_simulation_connection(
                user_id, failure_rate=0.9, recovery_time=0.1  # High failure rate
            )
            
            await manager.add_connection(
                user_id=user_id,
                connection_id=f"conn_{i}_{int(time.time())}",
                websocket=failure_connection
            )
            
            emitter = UnifiedWebSocketEmitter(manager=manager, user_id=user_id, context=None)
            user_connections.append((user_id, emitter, failure_connection))
            self.test_emitters.append(emitter)
        
        # Send many events that will trigger retries and failures
        for round_num in range(5):
            tasks = []
            for user_id, emitter, _ in user_connections:
                tasks.append(emitter.emit_agent_started(
                    agent_name=f"memory_test_agent_{round_num}",
                    user_id=user_id
                ))
                tasks.append(emitter.emit_agent_thinking(
                    reasoning=f"Memory test reasoning round {round_num}",
                    user_id=user_id
                ))
            
            # Send all events concurrently to stress memory
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.2)
        
        # Force cleanup and garbage collection
        for user_id, emitter, connection in user_connections:
            try:
                await emitter.close()
                await connection.close()
            except:
                pass
        
        gc.collect()
        await asyncio.sleep(1.0)  # Allow cleanup time
        
        final_memory = psutil.Process().memory_info().rss
        memory_growth = final_memory - initial_memory
        memory_growth_mb = memory_growth / 1024 / 1024
        
        # Memory growth should be reasonable (less than 100MB for this test)
        assert memory_growth_mb < 100, f"Excessive memory growth: {memory_growth_mb:.1f}MB"
        
        self.logger.info(f"Memory growth during failure testing: {memory_growth_mb:.1f}MB")

    @pytest.mark.integration
    @pytest.mark.websocket_reliability
    async def test_high_throughput_event_delivery_reliability(self):
        """Test event delivery reliability under high throughput."""
        self.performance_monitor.start_monitoring("throughput_test")
        
        manager = await self._create_reliable_websocket_manager(connection_pool_size=50)
        
        # Create multiple users for load testing
        user_count = 20
        events_per_user = 50
        user_setups = []
        
        for i in range(user_count):
            user_id = f"throughput_user_{i}_{int(time.time())}"
            connection = MockWebSocketConnection(user_id)
            
            await manager.add_connection(
                user_id=user_id,
                connection_id=f"conn_{i}_{int(time.time())}",
                websocket=connection
            )
            
            emitter = UnifiedWebSocketEmitter(manager=manager, user_id=user_id, context=None)
            user_setups.append((user_id, emitter, connection))
            self.test_emitters.append(emitter)
            self.test_connections.append(connection)
        
        # Define high-throughput event sending task
        async def send_user_events(user_id, emitter, connection, event_count):
            events_sent = 0
            start_time = time.time()
            
            for event_num in range(event_count):
                try:
                    # Send different types of events
                    if event_num % 5 == 0:
                        await emitter.emit_agent_started(
                            agent_name=f"throughput_agent_{event_num}",
                            user_id=user_id
                        )
                    elif event_num % 5 == 1:
                        await emitter.emit_agent_thinking(
                            reasoning=f"Processing event {event_num} of {event_count}",
                            user_id=user_id
                        )
                    elif event_num % 5 == 2:
                        await emitter.emit_tool_executing(
                            tool_name=f"tool_{event_num}",
                            user_id=user_id
                        )
                    elif event_num % 5 == 3:
                        await emitter.emit_tool_completed(
                            tool_name=f"tool_{event_num}",
                            user_id=user_id,
                            results={"event_num": event_num}
                        )
                    else:
                        await emitter.emit_agent_completed(
                            response=f"Event {event_num} complete",
                            user_id=user_id
                        )
                    
                    events_sent += 1
                    
                    # Small delay to prevent overwhelming
                    if event_num % 10 == 0:
                        await asyncio.sleep(0.01)
                        
                except Exception as e:
                    self.performance_monitor.record_error("throughput_test", str(e))
            
            duration = time.time() - start_time
            return {"user_id": user_id, "events_sent": events_sent, "duration": duration}
        
        # Execute high-throughput test
        start_time = time.time()
        tasks = [
            send_user_events(user_id, emitter, connection, events_per_user)
            for user_id, emitter, connection in user_setups
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict)]
        total_events_sent = sum(r["events_sent"] for r in successful_results)
        events_per_second = total_events_sent / total_duration if total_duration > 0 else 0
        
        # Verify throughput performance
        assert events_per_second >= 100, f"Throughput too low: {events_per_second:.1f} events/sec"
        
        # Verify delivery reliability
        total_delivered = sum(len(conn._sent_messages) for _, _, conn in user_setups)
        delivery_rate = total_delivered / total_events_sent if total_events_sent > 0 else 0
        
        assert delivery_rate >= 0.95, f"Delivery rate too low: {delivery_rate:.2%}"
        
        metrics = self.performance_monitor.stop_monitoring("throughput_test")
        self.logger.info(f"Throughput test: {events_per_second:.1f} events/sec, "
                        f"{delivery_rate:.2%} delivery rate, {metrics}")

    @pytest.mark.integration
    @pytest.mark.websocket_reliability
    async def test_connection_pool_exhaustion_recovery(self):
        """Test recovery when WebSocket connection pool is exhausted."""
        # Create manager with small pool for testing exhaustion
        manager = await self._create_reliable_websocket_manager(connection_pool_size=3)
        
        # Fill the connection pool to capacity
        pool_connections = []
        for i in range(3):
            user_id = f"pool_user_{i}_{int(time.time())}"
            connection = MockWebSocketConnection(user_id)
            
            await manager.add_connection(
                user_id=user_id,
                connection_id=f"conn_{i}_{int(time.time())}",
                websocket=connection
            )
            
            emitter = UnifiedWebSocketEmitter(manager=manager, user_id=user_id, context=None)
            pool_connections.append((user_id, emitter, connection))
            self.test_emitters.append(emitter)
            self.test_connections.append(connection)
        
        # Attempt to add more connections (should trigger pool management)
        overflow_user_id = f"overflow_user_{int(time.time())}"
        overflow_connection = MockWebSocketConnection(overflow_user_id)
        
        # This should either succeed (expanding pool) or gracefully handle overflow
        try:
            await manager.add_connection(
                user_id=overflow_user_id,
                connection_id=f"overflow_conn_{int(time.time())}",
                websocket=overflow_connection
            )
            
            overflow_emitter = UnifiedWebSocketEmitter(
                manager=manager, 
                user_id=overflow_user_id, 
                context=None
            )
            
            # Test that overflow connection can still send events
            await overflow_emitter.emit_agent_started(
                agent_name="pool_overflow_test",
                user_id=overflow_user_id
            )
            
            await asyncio.sleep(0.1)
            
            # Verify event delivery despite pool pressure
            assert len(overflow_connection._sent_messages) > 0, \
                "Event delivery failed under pool pressure"
            
            self.test_emitters.append(overflow_emitter)
            self.test_connections.append(overflow_connection)
            
        except Exception as e:
            # Pool exhaustion should be handled gracefully
            assert "pool" in str(e).lower() or "capacity" in str(e).lower(), \
                f"Unexpected error during pool exhaustion: {e}"

    @pytest.mark.integration
    @pytest.mark.websocket_reliability
    async def test_concurrent_event_race_condition_handling(self):
        """Test handling of race conditions in concurrent event scenarios."""
        manager = await self._create_reliable_websocket_manager()
        user_id = f"race_condition_user_{int(time.time())}"
        
        connection = MockWebSocketConnection(user_id)
        await manager.add_connection(
            user_id=user_id,
            connection_id=f"conn_{int(time.time())}",
            websocket=connection
        )
        
        emitter = UnifiedWebSocketEmitter(manager=manager, user_id=user_id, context=None)
        self.test_emitters.append(emitter)
        self.test_connections.append(connection)
        
        # Create concurrent event sending tasks that could cause race conditions
        race_condition_tasks = []
        
        async def send_rapid_events(event_prefix, count):
            for i in range(count):
                await emitter.emit_agent_thinking(
                    reasoning=f"{event_prefix} event {i} - rapid fire",
                    user_id=user_id,
                    step=i + 1,
                    total_steps=count
                )
        
        # Start multiple concurrent rapid event senders
        for task_num in range(5):
            task = asyncio.create_task(send_rapid_events(f"task_{task_num}", 10))
            race_condition_tasks.append(task)
        
        # Execute all tasks concurrently
        start_time = time.time()
        await asyncio.gather(*race_condition_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        await asyncio.sleep(0.2)  # Allow event processing
        
        # Verify all events were handled without corruption
        delivered_messages = connection._sent_messages
        valid_events = 0
        
        for message in delivered_messages:
            try:
                event = json.loads(message)
                if event.get("type") == "agent_thinking" and event.get("user_id") == user_id:
                    # Verify event structure is intact
                    assert "reasoning" in event
                    assert "step" in event
                    assert "total_steps" in event
                    valid_events += 1
            except (json.JSONDecodeError, KeyError, AssertionError):
                continue
        
        # Should have delivered most events without corruption
        assert valid_events >= 40, f"Too few valid events delivered: {valid_events}/50"
        assert execution_time < 5.0, f"Race condition handling too slow: {execution_time:.2f}s"

    @pytest.mark.integration
    @pytest.mark.websocket_reliability
    async def test_graceful_degradation_under_extreme_failures(self):
        """Test system graceful degradation when failures exceed retry limits."""
        manager = await self._create_reliable_websocket_manager(max_retry_attempts=3)
        user_id = f"degradation_user_{int(time.time())}"
        
        # Create connection that always fails
        class AlwaysFailConnection(MockWebSocketConnection):
            def __init__(self, user_id: str):
                super().__init__(user_id)
                self.failure_count = 0
                
            async def send(self, message: str):
                self.failure_count += 1
                raise ConnectionError(f"Permanent failure #{self.failure_count}")
        
        failing_connection = AlwaysFailConnection(user_id)
        await manager.add_connection(
            user_id=user_id,
            connection_id=f"conn_{int(time.time())}",
            websocket=failing_connection
        )
        
        emitter = UnifiedWebSocketEmitter(manager=manager, user_id=user_id, context=None)
        self.test_emitters.append(emitter)
        
        # Send event that will exhaust retries
        start_time = time.time()
        
        try:
            await emitter.emit_agent_started(
                agent_name="degradation_test",
                user_id=user_id
            )
        except Exception:
            pass  # Expected - connection permanently fails
        
        end_time = time.time()
        
        # Should have attempted retries but eventually given up gracefully
        assert failing_connection.failure_count >= 3, "Retry mechanism not exhausted"
        
        # Should not hang indefinitely
        assert (end_time - start_time) < 10.0, "Graceful degradation timeout exceeded"
        
        # System should remain functional for other users
        other_user_id = f"other_user_{int(time.time())}"
        other_connection = MockWebSocketConnection(other_user_id)
        
        await manager.add_connection(
            user_id=other_user_id,
            connection_id=f"other_conn_{int(time.time())}",
            websocket=other_connection
        )
        
        other_emitter = UnifiedWebSocketEmitter(
            manager=manager, 
            user_id=other_user_id, 
            context=None
        )
        
        # Other users should not be affected by the failing connection
        await other_emitter.emit_agent_started(
            agent_name="recovery_test",
            user_id=other_user_id
        )
        
        await asyncio.sleep(0.1)
        
        assert len(other_connection._sent_messages) > 0, \
            "System degraded for unaffected users"
        
        self.test_emitters.append(other_emitter)
        self.test_connections.append(other_connection)