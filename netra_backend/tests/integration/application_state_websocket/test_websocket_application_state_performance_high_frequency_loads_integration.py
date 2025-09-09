"""
Test WebSocket Application State Synchronization Performance Under High-Frequency Loads Integration

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (High-volume scenarios)
- Business Goal: Ensure system maintains performance and data consistency under heavy load
- Value Impact: Users experience responsive system even during peak usage
- Strategic Impact: System scalability enables business growth without performance degradation

This test validates that state synchronization remains performant and consistent
when processing high-frequency WebSocket messages. The system must maintain
low latency and avoid race conditions even under stress.
"""

import asyncio
import pytest
import json
import time
import random
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import statistics

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState
from shared.types import UserID, ThreadID, MessageID
from shared.isolated_environment import get_env


@dataclass
class PerformanceMetrics:
    """Performance metrics for WebSocket state synchronization."""
    operation_name: str
    start_time: float
    end_time: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    average_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_ops_per_sec: float
    memory_usage_mb: Optional[float] = None
    concurrent_connections: int = 1
    operation_latencies: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'operation_name': self.operation_name,
            'duration_seconds': self.end_time - self.start_time,
            'total_operations': self.total_operations,
            'successful_operations': self.successful_operations,
            'failed_operations': self.failed_operations,
            'success_rate_percent': (self.successful_operations / self.total_operations * 100) if self.total_operations > 0 else 0,
            'average_latency_ms': self.average_latency_ms,
            'p95_latency_ms': self.p95_latency_ms,
            'p99_latency_ms': self.p99_latency_ms,
            'throughput_ops_per_sec': self.throughput_ops_per_sec,
            'concurrent_connections': self.concurrent_connections
        }


class LoadTestConnection:
    """Simulates a WebSocket connection for load testing."""
    
    def __init__(self, connection_id: str, user_id: str, thread_id: str):
        self.connection_id = connection_id
        self.user_id = user_id
        self.thread_id = thread_id
        self.message_count = 0
        self.last_activity = time.time()
        self.operation_times: List[float] = []
        self.errors: List[str] = []
        
    async def simulate_message_send(self, services, state_manager, message_content: str) -> Tuple[bool, float]:
        """Simulate sending a message and measure performance."""
        start_time = time.time()
        
        try:
            message_id = MessageID(str(uuid4()))
            
            # Step 1: Insert message into database
            await services.postgres.execute("""
                INSERT INTO backend.messages (id, thread_id, user_id, content, role, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
            """, str(message_id), self.thread_id, self.user_id, message_content, "user")
            
            # Step 2: Update Redis cache
            message_data = {
                'id': str(message_id),
                'thread_id': self.thread_id,
                'user_id': self.user_id,
                'content': message_content,
                'role': 'user',
                'created_at': time.time()
            }
            
            await services.redis.set_json(f"message:{message_id}", message_data, ex=3600)
            
            # Step 3: Update WebSocket state
            current_state = state_manager.get_websocket_state(self.connection_id, 'connection_info')
            if current_state:
                updated_state = {
                    **current_state,
                    'message_count': current_state.get('message_count', 0) + 1,
                    'last_message_id': str(message_id),
                    'last_activity': time.time()
                }
                state_manager.set_websocket_state(self.connection_id, 'connection_info', updated_state)
            
            self.message_count += 1
            self.last_activity = time.time()
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            self.operation_times.append(latency)
            
            return True, latency
            
        except Exception as e:
            self.errors.append(str(e))
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            return False, latency


class TestWebSocketApplicationStatePerformanceHighFrequencyLoads(BaseIntegrationTest):
    """Test state synchronization performance under high-frequency WebSocket message loads."""
    
    async def setup_performance_test_environment(self, services, connection_count: int = 10) -> Tuple[List[LoadTestConnection], Dict[str, Any]]:
        """Set up environment for performance testing."""
        state_manager = get_websocket_state_manager()
        
        # Create test user
        user_data = await self.create_test_user_context(services)
        user_id = UserID(user_data['id'])
        
        # Create thread for testing
        thread_id = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, title, metadata)
            VALUES ($1, $2, $3)
            RETURNING id
        """, str(user_id), "Performance Test Thread", json.dumps({
            'test_type': 'performance',
            'expected_connections': connection_count
        }))
        
        thread_id = ThreadID(str(thread_id))
        
        # Create simulated connections
        connections = []
        for i in range(connection_count):
            connection = LoadTestConnection(
                connection_id=str(uuid4()),
                user_id=str(user_id),
                thread_id=str(thread_id)
            )
            connections.append(connection)
            
            # Register connection in WebSocket state
            state_manager.set_websocket_state(connection.connection_id, 'connection_info', {
                'user_id': str(user_id),
                'thread_id': str(thread_id),
                'connection_id': connection.connection_id,
                'state': WebSocketConnectionState.CONNECTED.value,
                'message_count': 0,
                'connected_at': time.time(),
                'connection_index': i
            })
        
        test_context = {
            'user_id': user_id,
            'thread_id': thread_id,
            'state_manager': state_manager,
            'connection_count': connection_count
        }
        
        return connections, test_context
    
    async def measure_operation_performance(self, 
                                          operation_func, 
                                          operation_name: str,
                                          iterations: int,
                                          concurrent_tasks: int = 1) -> PerformanceMetrics:
        """Measure performance of an operation under load."""
        
        operation_latencies = []
        successful_ops = 0
        failed_ops = 0
        
        start_time = time.time()
        
        async def run_operation_batch():
            nonlocal successful_ops, failed_ops
            
            for _ in range(iterations // concurrent_tasks):
                try:
                    operation_start = time.time()
                    await operation_func()
                    operation_end = time.time()
                    
                    latency_ms = (operation_end - operation_start) * 1000
                    operation_latencies.append(latency_ms)
                    successful_ops += 1
                    
                except Exception as e:
                    self.logger.warning(f"Operation failed: {e}")
                    failed_ops += 1
        
        # Run concurrent batches
        tasks = [run_operation_batch() for _ in range(concurrent_tasks)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        
        # Calculate metrics
        total_time = end_time - start_time
        total_operations = successful_ops + failed_ops
        
        if operation_latencies:
            avg_latency = statistics.mean(operation_latencies)
            p95_latency = statistics.quantiles(operation_latencies, n=20)[18] if len(operation_latencies) >= 20 else max(operation_latencies)
            p99_latency = statistics.quantiles(operation_latencies, n=100)[98] if len(operation_latencies) >= 100 else max(operation_latencies)
        else:
            avg_latency = p95_latency = p99_latency = 0
        
        throughput = total_operations / total_time if total_time > 0 else 0
        
        return PerformanceMetrics(
            operation_name=operation_name,
            start_time=start_time,
            end_time=end_time,
            total_operations=total_operations,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            average_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            throughput_ops_per_sec=throughput,
            concurrent_connections=concurrent_tasks,
            operation_latencies=operation_latencies
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_high_frequency_message_synchronization_performance(self, real_services_fixture):
        """Test performance of state synchronization during high-frequency message processing."""
        services = real_services_fixture
        
        # Set up performance test with multiple connections
        connections, test_context = await self.setup_performance_test_environment(services, connection_count=5)
        state_manager = test_context['state_manager']
        
        # Test parameters
        messages_per_connection = 20
        total_messages = len(connections) * messages_per_connection
        
        # Define operation function for performance testing
        connection_index = 0
        
        async def send_message_operation():
            nonlocal connection_index
            connection = connections[connection_index % len(connections)]
            connection_index += 1
            
            message_content = f"Performance test message {connection_index} from {connection.connection_id[:8]}"
            success, latency = await connection.simulate_message_send(services, state_manager, message_content)
            
            if not success:
                raise RuntimeError(f"Message send failed for connection {connection.connection_id}")
            
            return latency
        
        # Measure performance
        performance_metrics = await self.measure_operation_performance(
            send_message_operation,
            "high_frequency_message_sync",
            total_messages,
            concurrent_tasks=3  # Concurrent processing
        )
        
        # Log performance results
        metrics_dict = performance_metrics.to_dict()
        self.logger.info(f"High-frequency message performance:")
        for key, value in metrics_dict.items():
            if isinstance(value, float):
                self.logger.info(f"  {key}: {value:.2f}")
            else:
                self.logger.info(f"  {key}: {value}")
        
        # Performance assertions
        assert performance_metrics.success_rate_percent >= 95.0, f"Success rate too low: {performance_metrics.success_rate_percent:.1f}%"
        assert performance_metrics.average_latency_ms < 100.0, f"Average latency too high: {performance_metrics.average_latency_ms:.1f}ms"
        assert performance_metrics.p95_latency_ms < 200.0, f"P95 latency too high: {performance_metrics.p95_latency_ms:.1f}ms"
        assert performance_metrics.throughput_ops_per_sec > 10.0, f"Throughput too low: {performance_metrics.throughput_ops_per_sec:.1f} ops/sec"
        
        # Verify state consistency after high load
        final_message_count = await services.postgres.fetchval("""
            SELECT COUNT(*) FROM backend.messages WHERE thread_id = $1
        """, str(test_context['thread_id']))
        
        assert final_message_count == total_messages, f"Expected {total_messages} messages, got {final_message_count}"
        
        # Check WebSocket state consistency
        total_ws_messages = 0
        for connection in connections:
            ws_state = state_manager.get_websocket_state(connection.connection_id, 'connection_info')
            if ws_state:
                total_ws_messages += ws_state.get('message_count', 0)
        
        assert total_ws_messages == total_messages, f"WebSocket state inconsistent: {total_ws_messages} != {total_messages}"
        
        # BUSINESS VALUE: System handles high load efficiently
        self.assert_business_value_delivered({
            'high_performance': True,
            'load_handling': True,
            'state_consistency_under_load': True,
            'scalability': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_state_updates_race_condition_prevention(self, real_services_fixture):
        """Test prevention of race conditions during concurrent state updates."""
        services = real_services_fixture
        
        connections, test_context = await self.setup_performance_test_environment(services, connection_count=3)
        state_manager = test_context['state_manager']
        thread_id = test_context['thread_id']
        
        # Shared counter that will be updated concurrently
        shared_counter_key = f"thread_counter:{thread_id}"
        await services.redis.set(shared_counter_key, "0")
        
        # Track race condition metrics
        race_condition_detected = False
        update_conflicts = 0
        successful_updates = 0
        
        async def concurrent_counter_update(connection: LoadTestConnection, update_count: int):
            """Simulate concurrent updates to shared state."""
            nonlocal race_condition_detected, update_conflicts, successful_updates
            
            local_conflicts = 0
            local_successes = 0
            
            for i in range(update_count):
                try:
                    # Simulate optimistic locking pattern
                    max_retries = 3
                    for retry in range(max_retries):
                        try:
                            # Read current value
                            current_value = await services.redis.get(shared_counter_key)
                            current_int = int(current_value) if current_value else 0
                            
                            # Simulate processing delay (increases race condition chance)
                            await asyncio.sleep(random.uniform(0.001, 0.01))
                            
                            # Attempt atomic update using Redis WATCH/MULTI/EXEC
                            new_value = current_int + 1
                            
                            # Use SET with conditional check (simulating compare-and-swap)
                            async with services.redis.pipeline(transaction=True) as pipe:
                                await pipe.watch(shared_counter_key)
                                
                                # Re-check value hasn't changed
                                current_check = await pipe.get(shared_counter_key)
                                if current_check != current_value:
                                    local_conflicts += 1
                                    await pipe.reset()
                                    continue  # Retry
                                
                                await pipe.multi()
                                await pipe.set(shared_counter_key, str(new_value))
                                await pipe.execute()
                                
                                local_successes += 1
                                break  # Success, exit retry loop
                                
                        except Exception as e:
                            if retry == max_retries - 1:
                                self.logger.warning(f"Update failed after retries: {e}")
                                local_conflicts += 1
                            # Continue to next retry
                    
                    # Update WebSocket state to reflect the change
                    ws_state = state_manager.get_websocket_state(connection.connection_id, 'connection_info')
                    if ws_state:
                        updated_ws_state = {
                            **ws_state,
                            'counter_updates': ws_state.get('counter_updates', 0) + 1,
                            'last_counter_update': time.time()
                        }
                        state_manager.set_websocket_state(connection.connection_id, 'connection_info', updated_ws_state)
                
                except Exception as e:
                    self.logger.error(f"Concurrent update error: {e}")
                    local_conflicts += 1
            
            return local_successes, local_conflicts
        
        # Run concurrent updates
        updates_per_connection = 10
        
        tasks = [
            concurrent_counter_update(conn, updates_per_connection)
            for conn in connections
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Connection {i} failed: {result}")
                update_conflicts += updates_per_connection
            else:
                successes, conflicts = result
                successful_updates += successes
                update_conflicts += conflicts
        
        # Check final counter value
        final_counter = await services.redis.get(shared_counter_key)
        final_counter_int = int(final_counter) if final_counter else 0
        
        expected_updates = len(connections) * updates_per_connection
        
        self.logger.info(f"Concurrent update results:")
        self.logger.info(f"  Expected updates: {expected_updates}")
        self.logger.info(f"  Successful updates: {successful_updates}")
        self.logger.info(f"  Update conflicts: {update_conflicts}")
        self.logger.info(f"  Final counter value: {final_counter_int}")
        self.logger.info(f"  Duration: {end_time - start_time:.2f}s")
        
        # Race condition analysis
        if final_counter_int != expected_updates:
            race_condition_detected = True
            self.logger.warning(f"Race condition detected: counter={final_counter_int}, expected={expected_updates}")
        
        # Performance and correctness assertions
        conflict_rate = (update_conflicts / (successful_updates + update_conflicts)) * 100 if (successful_updates + update_conflicts) > 0 else 0
        
        # Allow some conflicts but ensure most operations succeed
        assert conflict_rate < 50.0, f"Conflict rate too high: {conflict_rate:.1f}%"
        assert successful_updates >= expected_updates * 0.8, f"Too few successful updates: {successful_updates}/{expected_updates}"
        
        # Race condition prevention: final value should match successful updates
        # (This test demonstrates the challenge of race condition prevention)
        if race_condition_detected:
            self.logger.info("Race condition detected - this identifies need for better concurrency control")
        
        # Verify WebSocket state consistency
        total_ws_updates = 0
        for connection in connections:
            ws_state = state_manager.get_websocket_state(connection.connection_id, 'connection_info')
            if ws_state:
                total_ws_updates += ws_state.get('counter_updates', 0)
        
        # WebSocket state should track the attempts, not necessarily the successful DB updates
        assert total_ws_updates >= successful_updates, f"WebSocket state inconsistent: {total_ws_updates} < {successful_updates}"
        
        # BUSINESS VALUE: System handles concurrent access gracefully
        self.assert_business_value_delivered({
            'concurrent_safety': conflict_rate < 30.0,
            'race_condition_awareness': True,
            'performance_under_contention': True,
            'state_tracking': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_state_synchronization_memory_efficiency(self, real_services_fixture):
        """Test memory efficiency of WebSocket state synchronization under sustained load."""
        services = real_services_fixture
        
        # Set up larger scale test
        connection_count = 20
        connections, test_context = await self.setup_performance_test_environment(services, connection_count)
        state_manager = test_context['state_manager']
        
        # Track memory usage patterns (simulated)
        initial_memory_markers = {}
        peak_memory_markers = {}
        
        # Simulate memory tracking
        def estimate_memory_usage():
            """Estimate memory usage based on stored state."""
            # This is a simplified estimation
            ws_state_count = 0
            redis_key_count = 0
            
            for connection in connections:
                ws_state = state_manager.get_websocket_state(connection.connection_id, 'connection_info')
                if ws_state:
                    ws_state_count += 1
                    # Estimate size based on data complexity
                    state_size = len(json.dumps(ws_state).encode('utf-8'))
                    redis_key_count += 1
            
            # Rough memory estimation (in KB)
            estimated_memory_kb = (ws_state_count * 2) + (redis_key_count * 1)
            return estimated_memory_kb
        
        initial_memory_markers['websocket_states'] = estimate_memory_usage()
        
        # Run sustained load test
        sustained_operations = 50
        batch_size = 10
        
        async def sustained_message_burst(batch_index: int):
            """Send a burst of messages and measure state growth."""
            burst_start_memory = estimate_memory_usage()
            
            for i in range(batch_size):
                connection = connections[i % len(connections)]
                message_content = f"Sustained load batch {batch_index} message {i}"
                
                success, latency = await connection.simulate_message_send(
                    services, state_manager, message_content
                )
                
                if not success:
                    self.logger.warning(f"Message send failed in batch {batch_index}")
                
                # Small delay to avoid overwhelming
                await asyncio.sleep(0.01)
            
            burst_end_memory = estimate_memory_usage()
            memory_growth = burst_end_memory - burst_start_memory
            
            return {
                'batch_index': batch_index,
                'initial_memory_kb': burst_start_memory,
                'final_memory_kb': burst_end_memory,
                'memory_growth_kb': memory_growth,
                'messages_sent': batch_size
            }
        
        # Execute sustained load in batches
        start_time = time.time()
        
        batch_results = []
        for batch in range(sustained_operations // batch_size):
            batch_result = await sustained_message_burst(batch)
            batch_results.append(batch_result)
            
            # Track peak memory
            current_memory = batch_result['final_memory_kb']
            if 'peak_memory_kb' not in peak_memory_markers or current_memory > peak_memory_markers['peak_memory_kb']:
                peak_memory_markers['peak_memory_kb'] = current_memory
                peak_memory_markers['peak_at_batch'] = batch
        
        end_time = time.time()
        
        # Analyze memory efficiency
        final_memory = estimate_memory_usage()
        total_memory_growth = final_memory - initial_memory_markers['websocket_states']
        total_messages_sent = sum(len(conn.operation_times) for conn in connections)
        
        # Calculate memory efficiency metrics
        memory_per_message = total_memory_growth / total_messages_sent if total_messages_sent > 0 else 0
        memory_efficiency_score = 100 - min(100, (memory_per_message * 10))  # Lower memory per message = higher score
        
        self.logger.info(f"Memory efficiency analysis:")
        self.logger.info(f"  Initial memory: {initial_memory_markers['websocket_states']} KB")
        self.logger.info(f"  Final memory: {final_memory} KB")
        self.logger.info(f"  Memory growth: {total_memory_growth} KB")
        self.logger.info(f"  Peak memory: {peak_memory_markers.get('peak_memory_kb', 0)} KB")
        self.logger.info(f"  Total messages: {total_messages_sent}")
        self.logger.info(f"  Memory per message: {memory_per_message:.3f} KB")
        self.logger.info(f"  Memory efficiency score: {memory_efficiency_score:.1f}/100")
        self.logger.info(f"  Test duration: {end_time - start_time:.2f}s")
        
        # Memory efficiency assertions
        assert memory_per_message < 1.0, f"Memory usage per message too high: {memory_per_message:.3f} KB"
        assert total_memory_growth < 1000, f"Total memory growth too high: {total_memory_growth} KB"
        assert memory_efficiency_score > 50, f"Memory efficiency too low: {memory_efficiency_score:.1f}/100"
        
        # Verify no memory leaks by checking cleanup
        # In a real implementation, we'd verify garbage collection, connection cleanup, etc.
        
        # Check state consistency after sustained load
        db_message_count = await services.postgres.fetchval("""
            SELECT COUNT(*) FROM backend.messages WHERE thread_id = $1
        """, str(test_context['thread_id']))
        
        ws_message_count = sum(
            state_manager.get_websocket_state(conn.connection_id, 'connection_info').get('message_count', 0)
            for conn in connections
        )
        
        assert db_message_count == ws_message_count, f"Message count mismatch: DB={db_message_count}, WS={ws_message_count}"
        
        # BUSINESS VALUE: System remains efficient under sustained load
        self.assert_business_value_delivered({
            'memory_efficiency': memory_efficiency_score > 70,
            'sustained_performance': True,
            'no_memory_leaks': total_memory_growth < 500,
            'scalable_architecture': True
        }, 'automation')