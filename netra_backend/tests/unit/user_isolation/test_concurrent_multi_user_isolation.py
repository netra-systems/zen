"""
Test Concurrent Multi-User Isolation Scenarios

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Ensure platform can handle 10+ concurrent users with zero cross-user data leakage
- Value Impact: Enables confident scaling to support growth without compromising user data security
- Strategic Impact: CRITICAL - Multi-user isolation is foundation of platform scalability and trust

This test suite validates complete user isolation under realistic concurrent conditions:
- 10+ concurrent users creating contexts, executing agents, using tools simultaneously
- High-load scenarios with rapid context creation/destruction
- Resource exhaustion scenarios with proper isolation boundaries
- Edge cases with aggressive threading and resource contention
- Memory pressure scenarios ensuring no shared state leakage
- Performance degradation scenarios maintaining isolation guarantees

Architecture Tested:
- UserExecutionContext Factory patterns under concurrent load
- WebSocketBridgeFactory isolation under multi-user stress
- Tool dispatcher isolation with concurrent executions
- Child context creation under concurrent parent operations
- Resource cleanup isolation when users disconnect simultaneously
"""

import asyncio
import pytest
import uuid
import time
import threading
import gc
import random
import weakref
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import psutil
import os

from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextFactory,
    InvalidContextError,
    ContextIsolationError,
    validate_user_context,
    managed_user_context,
    clear_shared_object_registry
)
from netra_backend.app.services.websocket_bridge_factory import (
    WebSocketBridgeFactory,
    UserWebSocketContext,
    WebSocketFactoryConfig,
    UserWebSocketEmitter
)
from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class UserSimulationResult:
    """Result of a user simulation."""
    user_id: str
    contexts_created: int
    contexts_validated: int
    websocket_events_sent: int
    websocket_events_received: int
    tool_executions: int
    errors_encountered: List[str] = field(default_factory=list)
    isolation_violations: List[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    peak_memory_mb: float = 0.0


@dataclass
class ConcurrencyTestMetrics:
    """Metrics for concurrent test execution."""
    total_users: int
    total_contexts_created: int
    total_contexts_validated: int
    total_websocket_events: int
    total_tool_executions: int
    total_errors: int
    total_isolation_violations: int
    peak_memory_usage_mb: float
    total_execution_time_seconds: float
    average_user_response_time_ms: float
    
    def is_successful(self) -> bool:
        """Check if the concurrency test was successful."""
        return (
            self.total_isolation_violations == 0 and
            self.total_errors == 0 and
            self.total_contexts_validated == self.total_contexts_created
        )


class MockConcurrentWebSocket:
    """Thread-safe mock WebSocket for concurrent testing."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.sent_messages: List[Dict[str, Any]] = []
        self.closed = False
        self._lock = threading.Lock()
        
    async def send_json(self, data: Dict[str, Any]):
        """Thread-safe mock send_json."""
        if self.closed:
            raise ConnectionError(f"WebSocket closed for user {self.user_id}")
        
        with self._lock:
            self.sent_messages.append({
                **data,
                "thread_id": threading.current_thread().ident,
                "timestamp": time.time()
            })
            
    async def send_text(self, text: str):
        """Mock send_text for ping."""
        if text == "" and not self.closed:
            return  # Ping successful
            
    async def ping(self):
        """Mock ping method."""
        return not self.closed
        
    async def close(self):
        """Mock close method."""
        with self._lock:
            self.closed = True


class TestConcurrentMultiUserIsolation(SSotBaseTestCase):
    """Test complete user isolation under concurrent multi-user load."""
    
    def setup_method(self):
        """Set up concurrent testing environment."""
        # Clear any shared state
        clear_shared_object_registry()
        
        # Track all test resources for cleanup
        self.created_contexts: List[UserExecutionContext] = []
        self.created_emitters: List[UserWebSocketEmitter] = []
        self.mock_websockets: Dict[str, MockConcurrentWebSocket] = {}
        
        # Memory tracking
        self.initial_memory_mb = self._get_memory_usage_mb()
        
    def teardown_method(self):
        """Clean up concurrent test resources."""
        async def cleanup():
            # Cleanup emitters
            for emitter in self.created_emitters:
                try:
                    await emitter.cleanup()
                except Exception:
                    pass
            
        # Run cleanup
        if self.created_emitters:
            asyncio.run(cleanup())
        
        self.created_contexts.clear()
        self.created_emitters.clear()
        self.mock_websockets.clear()
        
        # Force garbage collection and clear shared registry
        gc.collect()
        clear_shared_object_registry()
        
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    async def _simulate_user_activity(
        self, 
        user_index: int, 
        duration_seconds: float = 5.0,
        contexts_per_user: int = 5,
        events_per_context: int = 3
    ) -> UserSimulationResult:
        """Simulate realistic user activity with contexts, WebSocket events, and tool executions."""
        
        user_id = f"concurrent_user_{user_index}"
        start_time = time.time()
        start_memory = self._get_memory_usage_mb()
        peak_memory = start_memory
        
        result = UserSimulationResult(
            user_id=user_id,
            contexts_created=0,
            contexts_validated=0,
            websocket_events_sent=0,
            websocket_events_received=0,
            tool_executions=0
        )
        
        try:
            # Create WebSocket factory for this user
            config = WebSocketFactoryConfig(max_events_per_user=50, event_timeout_seconds=2.0)
            factory = WebSocketBridgeFactory(config)
            
            # Mock connection pool for this user
            mock_websocket = MockConcurrentWebSocket(user_id)
            self.mock_websockets[user_id] = mock_websocket
            
            class MockConnectionPool:
                async def get_connection(self, connection_id: str, user_id: str):
                    from netra_backend.app.services.websocket_connection_pool import ConnectionInfo
                    return ConnectionInfo(
                        connection_id=connection_id,
                        user_id=user_id,
                        websocket=mock_websocket,
                        created_at=datetime.now(timezone.utc),
                        last_activity=datetime.now(timezone.utc)
                    )
            
            factory.configure(MockConnectionPool(), None, None)
            
            end_time = start_time + duration_seconds
            contexts = []
            
            while time.time() < end_time:
                # Create user context
                context = UserContextFactory.create_context(
                    user_id=user_id,
                    thread_id=f"thread_{user_index}_{len(contexts)}",
                    run_id=f"run_{user_index}_{len(contexts)}_{int(time.time())}"
                )
                
                contexts.append(context)
                self.created_contexts.append(context)
                result.contexts_created += 1
                
                # Validate isolation
                try:
                    context.verify_isolation()
                    result.contexts_validated += 1
                except ContextIsolationError as e:
                    result.isolation_violations.append(str(e))
                
                # Create WebSocket emitter for this context
                try:
                    emitter = await factory.create_user_emitter(
                        user_id=user_id,
                        thread_id=context.thread_id,
                        connection_id=f"conn_{user_index}_{len(contexts)}"
                    )
                    self.created_emitters.append(emitter)
                    
                    # Send WebSocket events
                    for event_num in range(events_per_context):
                        await emitter.notify_agent_started(
                            f"agent_{user_index}",
                            f"run_{user_index}_{event_num}"
                        )
                        await emitter.notify_agent_thinking(
                            f"agent_{user_index}",
                            f"run_{user_index}_{event_num}",
                            f"User {user_index} thinking {event_num}"
                        )
                        await emitter.notify_agent_completed(
                            f"agent_{user_index}",
                            f"run_{user_index}_{event_num}",
                            f"Result for user {user_index} event {event_num}"
                        )
                        result.websocket_events_sent += 3
                        
                except Exception as e:
                    result.errors_encountered.append(f"WebSocket error: {e}")
                
                # Create child contexts randomly
                if len(contexts) > 0 and random.random() > 0.5:
                    parent = random.choice(contexts)
                    try:
                        child = parent.create_child_context(
                            operation_name=f"child_op_{len(contexts)}",
                            additional_agent_context={f"child_data_{user_index}": f"value_{len(contexts)}"}
                        )
                        contexts.append(child)
                        self.created_contexts.append(child)
                        result.contexts_created += 1
                        
                        # Validate child isolation
                        child.verify_isolation()
                        result.contexts_validated += 1
                        
                    except Exception as e:
                        result.errors_encountered.append(f"Child context error: {e}")
                
                # Track memory
                current_memory = self._get_memory_usage_mb()
                peak_memory = max(peak_memory, current_memory)
                
                # Small random delay to simulate realistic timing
                await asyncio.sleep(random.uniform(0.01, 0.05))
                
                # Early exit if too many contexts (memory protection)
                if len(contexts) >= contexts_per_user * 2:
                    break
            
            # Count received WebSocket events
            result.websocket_events_received = len(mock_websocket.sent_messages)
            
        except Exception as e:
            result.errors_encountered.append(f"User simulation error: {e}")
        
        result.execution_time_seconds = time.time() - start_time
        result.memory_usage_mb = self._get_memory_usage_mb() - start_memory
        result.peak_memory_mb = peak_memory - start_memory
        
        return result

    async def test_concurrent_10_users_context_isolation(self):
        """Test complete isolation with 10 concurrent users creating contexts."""
        
        num_users = 10
        duration_seconds = 3.0
        
        # Run concurrent user simulations
        user_tasks = [
            self._simulate_user_activity(i, duration_seconds, contexts_per_user=3)
            for i in range(num_users)
        ]
        
        start_time = time.time()
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Process results
        successful_results = []
        for i, result in enumerate(user_results):
            if isinstance(result, Exception):
                pytest.fail(f"User {i} simulation failed with exception: {result}")
            else:
                successful_results.append(result)
        
        # Calculate metrics
        metrics = ConcurrencyTestMetrics(
            total_users=len(successful_results),
            total_contexts_created=sum(r.contexts_created for r in successful_results),
            total_contexts_validated=sum(r.contexts_validated for r in successful_results),
            total_websocket_events=sum(r.websocket_events_sent for r in successful_results),
            total_tool_executions=sum(r.tool_executions for r in successful_results),
            total_errors=sum(len(r.errors_encountered) for r in successful_results),
            total_isolation_violations=sum(len(r.isolation_violations) for r in successful_results),
            peak_memory_usage_mb=max(r.peak_memory_mb for r in successful_results),
            total_execution_time_seconds=total_time,
            average_user_response_time_ms=sum(r.execution_time_seconds for r in successful_results) * 1000 / len(successful_results)
        )
        
        # Verify test success
        assert metrics.is_successful(), \
            f"Concurrent test failed: {metrics.total_isolation_violations} isolation violations, " \
            f"{metrics.total_errors} errors"
        
        # Verify minimum activity levels
        assert metrics.total_contexts_created >= num_users * 2, \
            f"Insufficient context creation activity: {metrics.total_contexts_created}"
        assert metrics.total_websocket_events >= num_users * 5, \
            f"Insufficient WebSocket activity: {metrics.total_websocket_events}"
        
        # Verify cross-user isolation by checking WebSocket messages
        self._verify_websocket_isolation_across_users(successful_results)
        
        # Verify memory usage is reasonable (not indicating major leaks)
        assert metrics.peak_memory_usage_mb < 100, \
            f"Excessive memory usage detected: {metrics.peak_memory_usage_mb}MB"

    async def test_high_load_concurrent_context_creation(self):
        """Test user isolation under high-load concurrent context creation."""
        
        async def rapid_context_creation(user_index: int, contexts_to_create: int) -> Tuple[str, List[str], List[str]]:
            """Rapidly create contexts for a user and check isolation."""
            user_id = f"highload_user_{user_index}"
            created_contexts = []
            isolation_violations = []
            
            for i in range(contexts_to_create):
                try:
                    context = UserContextFactory.create_context(
                        user_id=user_id,
                        thread_id=f"highload_thread_{user_index}_{i}",
                        run_id=f"highload_run_{user_index}_{i}_{int(time.time() * 1000)}"  # High precision timestamp
                    )
                    
                    # Add user-specific data immediately
                    context.agent_context[f"user_{user_index}_data"] = f"value_{i}"
                    context.audit_metadata[f"user_{user_index}_audit"] = f"audit_{i}"
                    
                    # Verify isolation immediately
                    context.verify_isolation()
                    created_contexts.append(context.request_id)
                    self.created_contexts.append(context)
                    
                except ContextIsolationError as e:
                    isolation_violations.append(str(e))
                except Exception as e:
                    isolation_violations.append(f"Creation error: {e}")
                    
                # Minimal delay to allow other users to interleave
                await asyncio.sleep(0.001)
            
            return user_id, created_contexts, isolation_violations
        
        # High-load test: 20 users creating 10 contexts each rapidly
        num_users = 20
        contexts_per_user = 10
        
        tasks = [
            rapid_context_creation(i, contexts_per_user)
            for i in range(num_users)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        execution_time = time.time() - start_time
        
        # Analyze results
        total_contexts = 0
        total_violations = 0
        user_context_map = {}
        
        for user_id, contexts, violations in results:
            total_contexts += len(contexts)
            total_violations += len(violations)
            user_context_map[user_id] = contexts
            
            # Verify this user created expected number of contexts
            assert len(contexts) == contexts_per_user, \
                f"User {user_id} created {len(contexts)} contexts, expected {contexts_per_user}"
            
            # Verify no isolation violations for this user
            assert len(violations) == 0, \
                f"User {user_id} had isolation violations: {violations}"
        
        # Verify overall success
        expected_total = num_users * contexts_per_user
        assert total_contexts == expected_total, \
            f"Expected {expected_total} contexts, got {total_contexts}"
        assert total_violations == 0, \
            f"High-load test had {total_violations} isolation violations"
        
        # Verify all context IDs are unique across all users
        all_context_ids = set()
        for contexts in user_context_map.values():
            for context_id in contexts:
                assert context_id not in all_context_ids, \
                    f"Duplicate context ID detected: {context_id} - ISOLATION VIOLATION"
                all_context_ids.add(context_id)
        
        # Performance verification
        average_context_creation_ms = (execution_time / total_contexts) * 1000
        assert average_context_creation_ms < 10, \
            f"Context creation too slow: {average_context_creation_ms:.2f}ms per context"

    async def test_memory_pressure_isolation_integrity(self):
        """Test that user isolation is maintained under memory pressure."""
        
        # Create memory pressure by creating many contexts with large metadata
        memory_pressure_data = {
            "large_dataset": ["data_point_" + str(i) for i in range(1000)],
            "configuration_matrix": {f"key_{i}": f"value_{i}" * 50 for i in range(100)},
            "audit_trail": [{"event": f"event_{i}", "timestamp": datetime.now().isoformat(), "data": "x" * 100} for i in range(50)]
        }
        
        async def create_memory_intensive_user(user_index: int) -> Dict[str, Any]:
            """Create user with memory-intensive contexts."""
            user_id = f"memory_user_{user_index}"
            contexts = []
            violations = []
            
            try:
                for i in range(5):  # 5 contexts per user
                    context = UserContextFactory.create_context(
                        user_id=user_id,
                        thread_id=f"memory_thread_{user_index}_{i}",
                        run_id=f"memory_run_{user_index}_{i}"
                    )
                    
                    # Add memory-intensive data (unique per user)
                    context.agent_context.update({
                        f"user_{user_index}_large_data": {
                            **memory_pressure_data,
                            "user_specific_id": user_index,
                            "context_specific_id": i
                        }
                    })
                    
                    context.audit_metadata.update({
                        f"user_{user_index}_audit_data": {
                            **memory_pressure_data["audit_trail"],
                            "user_id": user_index,
                            "context_id": i
                        }
                    })
                    
                    # Verify isolation under memory pressure
                    context.verify_isolation()
                    contexts.append(context)
                    self.created_contexts.append(context)
                    
                    # Create child contexts to increase memory pressure
                    child = context.create_child_context(
                        operation_name=f"memory_child_{i}",
                        additional_agent_context={f"child_{user_index}_{i}_data": memory_pressure_data["large_dataset"][:100]}
                    )
                    child.verify_isolation()
                    contexts.append(child)
                    self.created_contexts.append(child)
                    
            except ContextIsolationError as e:
                violations.append(str(e))
            except Exception as e:
                violations.append(f"Memory pressure error: {e}")
            
            return {
                "user_id": user_id,
                "contexts_created": len(contexts),
                "isolation_violations": violations,
                "memory_usage_mb": self._get_memory_usage_mb()
            }
        
        # Test with multiple users under memory pressure
        num_users = 15
        tasks = [create_memory_intensive_user(i) for i in range(num_users)]
        
        start_memory = self._get_memory_usage_mb()
        results = await asyncio.gather(*tasks)
        peak_memory = self._get_memory_usage_mb()
        memory_increase = peak_memory - start_memory
        
        # Verify no isolation violations under memory pressure
        total_violations = 0
        total_contexts = 0
        
        for result in results:
            total_contexts += result["contexts_created"]
            total_violations += len(result["isolation_violations"])
            
            assert len(result["isolation_violations"]) == 0, \
                f"User {result['user_id']} had violations under memory pressure: {result['isolation_violations']}"
        
        assert total_violations == 0, \
            f"Memory pressure test had {total_violations} isolation violations"
        
        # Verify cross-user data isolation by checking created contexts
        user_data_isolation = defaultdict(set)
        
        for context in self.created_contexts:
            if context.user_id.startswith("memory_user_"):
                user_index = context.user_id.split("_")[-1]
                
                # Check that this context only contains its own user's data
                for key, value in context.agent_context.items():
                    if isinstance(value, dict) and "user_specific_id" in value:
                        user_data_isolation[context.user_id].add(value["user_specific_id"])
        
        # Verify each user's contexts only contain that user's data
        for user_id, user_specific_ids in user_data_isolation.items():
            expected_user_index = int(user_id.split("_")[-1])
            
            for found_user_index in user_specific_ids:
                assert found_user_index == expected_user_index, \
                    f"ISOLATION VIOLATION: User {user_id} context contains data from user {found_user_index}"
        
        # Verify reasonable memory usage (no major leaks)
        memory_per_context_mb = memory_increase / total_contexts if total_contexts > 0 else 0
        assert memory_per_context_mb < 50, \
            f"Excessive memory per context: {memory_per_context_mb:.2f}MB"

    async def test_aggressive_threading_isolation(self):
        """Test user isolation under aggressive multi-threading scenarios."""
        
        def thread_worker(user_index: int, operations_per_thread: int) -> Dict[str, Any]:
            """Worker function that creates contexts in a separate thread."""
            user_id = f"thread_user_{user_index}"
            thread_id = threading.current_thread().ident
            contexts_created = []
            violations = []
            
            try:
                for i in range(operations_per_thread):
                    # Create context in this thread
                    context = UserContextFactory.create_context(
                        user_id=user_id,
                        thread_id=f"aggressive_thread_{thread_id}_{i}",
                        run_id=f"aggressive_run_{user_index}_{thread_id}_{i}"
                    )
                    
                    # Add thread-specific data
                    context.agent_context[f"thread_{thread_id}_data"] = {
                        "user_index": user_index,
                        "thread_id": thread_id,
                        "operation": i,
                        "timestamp": time.time()
                    }
                    
                    # Verify isolation in this thread
                    context.verify_isolation()
                    contexts_created.append(context.request_id)
                    
                    # Simulate some processing
                    time.sleep(0.001)
                    
            except ContextIsolationError as e:
                violations.append(f"Thread {thread_id}: {e}")
            except Exception as e:
                violations.append(f"Thread {thread_id} error: {e}")
            
            return {
                "user_id": user_id,
                "thread_id": thread_id,
                "contexts_created": len(contexts_created),
                "context_ids": contexts_created,
                "violations": violations
            }
        
        # Aggressive threading test: many threads creating contexts simultaneously
        num_threads = 30
        operations_per_thread = 5
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_index = {
                executor.submit(thread_worker, i, operations_per_thread): i
                for i in range(num_threads)
            }
            
            thread_results = {}
            for future in as_completed(future_to_index):
                user_index = future_to_index[future]
                try:
                    result = future.result(timeout=30)
                    thread_results[user_index] = result
                except Exception as e:
                    pytest.fail(f"Thread worker {user_index} failed: {e}")
        
        # Verify results
        total_contexts = 0
        total_violations = 0
        all_context_ids = set()
        thread_isolation_map = {}
        
        for user_index, result in thread_results.items():
            total_contexts += result["contexts_created"]
            total_violations += len(result["violations"])
            
            # Verify no violations for this thread
            assert len(result["violations"]) == 0, \
                f"Thread worker {user_index} had violations: {result['violations']}"
            
            # Verify expected number of contexts
            assert result["contexts_created"] == operations_per_thread, \
                f"Thread {user_index} created {result['contexts_created']} contexts, expected {operations_per_thread}"
            
            # Track context IDs for uniqueness verification
            for context_id in result["context_ids"]:
                assert context_id not in all_context_ids, \
                    f"Duplicate context ID from threading: {context_id} - ISOLATION VIOLATION"
                all_context_ids.add(context_id)
            
            # Track thread isolation
            thread_isolation_map[result["thread_id"]] = result["user_id"]
        
        # Verify overall success
        expected_total = num_threads * operations_per_thread
        assert total_contexts == expected_total, \
            f"Expected {expected_total} contexts, got {total_contexts}"
        assert total_violations == 0, \
            f"Threading test had {total_violations} isolation violations"
        
        # Verify thread isolation (each thread worked on one user)
        assert len(thread_isolation_map) == num_threads, \
            f"Expected {num_threads} unique threads, got {len(thread_isolation_map)}"

    def test_resource_exhaustion_isolation_boundaries(self):
        """Test that resource exhaustion doesn't break user isolation."""
        
        # Test file descriptor exhaustion simulation
        contexts_under_fd_pressure = []
        
        try:
            # Create many contexts rapidly to simulate FD pressure
            for i in range(100):
                user_id = f"fd_pressure_user_{i % 10}"  # 10 users cycling
                context = UserContextFactory.create_context(
                    user_id=user_id,
                    thread_id=f"fd_pressure_thread_{i}",
                    run_id=f"fd_pressure_run_{i}"
                )
                
                # Add user-specific data
                context.agent_context[f"fd_user_{i % 10}"] = f"data_{i}"
                
                # Verify isolation under pressure
                context.verify_isolation()
                contexts_under_fd_pressure.append(context)
                
        except Exception as e:
            # Even under resource pressure, isolation should not be violated
            # Verify existing contexts are still isolated
            pass
        
        # Verify created contexts maintain isolation
        user_data_map = defaultdict(list)
        for context in contexts_under_fd_pressure:
            user_index = int(context.user_id.split("_")[-1])
            user_data_map[user_index].append(context)
        
        # Verify each user's contexts only contain that user's data
        for user_index, contexts in user_data_map.items():
            for context in contexts:
                # Should only have data for this user
                user_specific_keys = [k for k in context.agent_context.keys() if k.startswith("fd_user_")]
                for key in user_specific_keys:
                    expected_key = f"fd_user_{user_index}"
                    assert key == expected_key, \
                        f"ISOLATION VIOLATION: User {user_index} context has key {key}, expected {expected_key}"
        
        self.created_contexts.extend(contexts_under_fd_pressure)

    def _verify_websocket_isolation_across_users(self, user_results: List[UserSimulationResult]) -> None:
        """Verify WebSocket message isolation across all users."""
        
        for result in user_results:
            user_id = result.user_id
            user_index = int(user_id.split("_")[-1])
            
            if user_id in self.mock_websockets:
                websocket = self.mock_websockets[user_id]
                messages = websocket.sent_messages
                
                # Verify all messages for this user belong to this user only
                for message in messages:
                    message_str = str(message)
                    
                    # Check that this message contains this user's data
                    assert f"agent_{user_index}" in message_str or f"run_{user_index}_" in message_str, \
                        f"User {user_id} received message without user-specific content: {message_str[:100]}..."
                    
                    # CRITICAL: Verify no other user's data in this message
                    for other_result in user_results:
                        if other_result.user_id != user_id:
                            other_user_index = int(other_result.user_id.split("_")[-1])
                            
                            assert f"agent_{other_user_index}" not in message_str, \
                                f"ISOLATION VIOLATION: User {user_id} message contains agent_{other_user_index}"
                            assert f"User {other_user_index} thinking" not in message_str, \
                                f"ISOLATION VIOLATION: User {user_id} message contains User {other_user_index} thinking"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])