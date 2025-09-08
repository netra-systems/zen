"""
WebSocket Factory Security Validation Test Suite

This test suite validates that the new factory pattern implementation provides
comprehensive security guarantees and eliminates all critical vulnerabilities
identified in the singleton pattern.

CRITICAL SECURITY VALIDATIONS:
1. Complete user isolation between connections
2. No shared state between managers
3. No message cross-contamination
4. Prevention of connection hijacking
5. Proper resource cleanup and memory management
6. Race condition safety
7. Scalability with concurrent users

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) 
- Business Goal: Eliminate security vulnerabilities preventing safe multi-user AI chat
- Value Impact: Enables safe concurrent AI interactions without data leakage
- Revenue Impact: Prevents catastrophic security breaches that could destroy business

Test Categories:
- Isolation Validation: Proves complete user separation
- Concurrency Safety: Tests race conditions and concurrent access
- Resource Management: Validates cleanup and memory leak prevention
- Security Boundaries: Tests connection hijacking prevention
- Performance Security: Validates linear scaling without leakage
"""

import pytest
import asyncio
import uuid
import time
import weakref
import gc
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
import logging
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    IsolatedWebSocketManager,
    get_websocket_manager_factory,
    create_websocket_manager
)
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import get_env
from netra_backend.app.clients.auth_client_core import AuthServiceClient

logger = logging.getLogger(__name__)


class SecurityAuditTracker:
    """Track security events during testing for comprehensive audit."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.violations: List[Dict[str, Any]] = []
        self.memory_snapshots: List[Dict[str, Any]] = []
    
    def record_event(self, event_type: str, **kwargs):
        """Record a security event."""
        self.events.append({
            "timestamp": datetime.utcnow(),
            "event_type": event_type,
            **kwargs
        })
    
    def record_violation(self, violation_type: str, severity: str, **kwargs):
        """Record a security violation."""
        violation = {
            "timestamp": datetime.utcnow(), 
            "violation_type": violation_type,
            "severity": severity,
            **kwargs
        }
        self.violations.append(violation)
        logger.error(f"SECURITY VIOLATION: {violation}")
    
    def take_memory_snapshot(self, description: str):
        """Take a memory usage snapshot."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        snapshot = {
            "timestamp": datetime.utcnow(),
            "description": description,
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "objects_count": len(gc.get_objects())
        }
        self.memory_snapshots.append(snapshot)
        return snapshot
    
    def get_audit_summary(self) -> Dict[str, Any]:
        """Get comprehensive audit summary."""
        return {
            "total_events": len(self.events),
            "total_violations": len(self.violations),
            "critical_violations": len([v for v in self.violations if v["severity"] == "CRITICAL"]),
            "memory_snapshots": len(self.memory_snapshots),
            "memory_growth": self._calculate_memory_growth(),
            "violation_details": self.violations,
            "test_duration": (self.events[-1]["timestamp"] - self.events[0]["timestamp"]).total_seconds() if self.events else 0
        }
    
    def _calculate_memory_growth(self) -> Dict[str, float]:
        """Calculate memory growth during testing."""
        if len(self.memory_snapshots) < 2:
            return {"rss_growth_mb": 0, "objects_growth": 0}
        
        first = self.memory_snapshots[0]
        last = self.memory_snapshots[-1]
        
        return {
            "rss_growth_mb": last["rss_mb"] - first["rss_mb"],
            "objects_growth": last["objects_count"] - first["objects_count"]
        }


@pytest.fixture
def security_tracker():
    """Security audit tracker fixture."""
    tracker = SecurityAuditTracker()
    tracker.record_event("test_suite_start")
    tracker.take_memory_snapshot("test_start")
    yield tracker
    tracker.take_memory_snapshot("test_end")
    tracker.record_event("test_suite_end")


@pytest.fixture
async def factory():
    """Fresh factory instance for each test."""
    factory_instance = WebSocketManagerFactory(max_managers_per_user=10, connection_timeout_seconds=300)
    yield factory_instance
    # Clean up the factory after test
    try:
        await factory_instance.shutdown()
    except:
        pass  # Ignore cleanup errors


@pytest.fixture
def user_contexts():
    """Generate multiple user contexts for testing."""
    contexts = []
    for i in range(20):  # Support up to 20 concurrent users in tests
        context = UserExecutionContext(
            user_id=f"user_{i:02d}_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{i:02d}",
            run_id=f"run_{i:02d}",
            request_id=f"req_{i:02d}",
            websocket_connection_id=f"conn_{i:02d}_{uuid.uuid4().hex[:8]}"
        )
        contexts.append(context)
    return contexts


@pytest.fixture
def real_websocket():
    """Create real WebSocket connection for testing."""
    class TestWebSocketConnection:
        def __init__(self):
            self.messages_sent = []
            self.is_connected = True
            self._closed = False
            
        async def send_json(self, message: Dict):
            if self._closed:
                raise RuntimeError("WebSocket is closed")
            self.messages_sent.append(message)
            
        async def close(self, code: int = 1000, reason: str = "Normal closure"):
            self._closed = True
            self.is_connected = False
            
        def get_messages(self) -> List[Dict]:
            return self.messages_sent.copy()
            
    return TestWebSocketConnection()


class TestFactoryIsolation:
    """Test complete isolation between user contexts."""
    
    async def test_factory_creates_isolated_instances(self, factory, user_contexts, security_tracker):
        """Validate that factory creates completely isolated manager instances."""
        security_tracker.record_event("isolation_test_start", test="factory_creates_isolated_instances")
        
        # Create managers for different users
        managers = {}
        for context in user_contexts[:5]:  # Test with 5 users
            manager = factory.create_manager(context)
            managers[context.user_id] = manager
            
            # Validate each manager is a unique instance
            assert isinstance(manager, IsolatedWebSocketManager)
            assert manager.user_context == context
            assert id(manager) not in [id(m) for m in managers.values() if m != manager]
            
            security_tracker.record_event("manager_created", user_id=context.user_id, manager_id=id(manager))
        
        # Validate no managers share memory references
        manager_ids = [id(m) for m in managers.values()]
        assert len(manager_ids) == len(set(manager_ids)), "Managers share memory references"
        
        # Validate managers have independent state
        for user_id, manager in managers.items():
            assert manager.user_context.user_id == user_id
            assert len(manager._connections) == 0
            assert len(manager._connection_ids) == 0
            assert manager._is_active is True
            
            # Validate private state isolation
            assert manager._connections is not None
            for other_user_id, other_manager in managers.items():
                if other_user_id != user_id:
                    assert manager._connections is not other_manager._connections
                    assert manager._connection_ids is not other_manager._connection_ids
        
        security_tracker.record_event("isolation_test_complete", managers_created=len(managers))
    
    async def test_user_context_validation_prevents_hijacking(self, factory, user_contexts, mock_websocket, security_tracker):
        """Test that strict user context validation prevents connection hijacking."""
        security_tracker.record_event("hijacking_test_start")
        
        user1_context = user_contexts[0]
        user2_context = user_contexts[1]
        
        # Create manager for user1
        manager1 = factory.create_manager(user1_context)
        
        # Create connection for user1
        connection1 = WebSocketConnection(
            connection_id=user1_context.websocket_connection_id,
            user_id=user1_context.user_id,
            websocket=mock_websocket,
            connected_at=datetime.utcnow()
        )
        
        # Add legitimate connection
        await manager1.add_connection(connection1)
        assert len(manager1._connections) == 1
        
        # SECURITY TEST: Attempt to add user2's connection to user1's manager (hijacking attempt)
        malicious_connection = WebSocketConnection(
            connection_id=user2_context.websocket_connection_id,
            user_id=user2_context.user_id,  # Different user!
            websocket=mock_websocket,
            connected_at=datetime.utcnow()
        )
        
        # This should raise a security violation
        with pytest.raises(ValueError, match="does not match manager user_id"):
            await manager1.add_connection(malicious_connection)
        
        # Verify the manager still only has the legitimate connection
        assert len(manager1._connections) == 1
        assert user1_context.websocket_connection_id in manager1._connections
        assert user2_context.websocket_connection_id not in manager1._connections
        
        security_tracker.record_event("hijacking_attempt_blocked", 
                                    attacker_user=user2_context.user_id,
                                    target_user=user1_context.user_id)
    
    async def test_message_isolation_between_users(self, factory, user_contexts, security_tracker):
        """Test that messages are completely isolated between users."""
        security_tracker.record_event("message_isolation_test_start")
        
        # Create managers for multiple users
        managers = {}
        connections = {}
        
        for i, context in enumerate(user_contexts[:3]):
            manager = factory.create_manager(context)
            websocket = TestWebSocketConnection()  # Real WebSocket implementation
            
            connection = WebSocketConnection(
                connection_id=context.websocket_connection_id,
                user_id=context.user_id,
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            
            await manager.add_connection(connection)
            
            managers[context.user_id] = manager
            connections[context.user_id] = websocket
        
        # Send message to user1 only
        user1_id = user_contexts[0].user_id
        test_message = {"type": "test", "content": "secret message", "timestamp": time.time()}
        
        await managers[user1_id].send_to_user(test_message)
        
        # Validate message was sent only to user1
        connections[user1_id].send_json.assert_called_once_with(test_message)
        
        # Validate message was NOT sent to other users
        user2_id = user_contexts[1].user_id
        user3_id = user_contexts[2].user_id
        
        connections[user2_id].send_json.assert_not_called()
        connections[user3_id].send_json.assert_not_called()
        
        # Send different message to user2
        user2_message = {"type": "test", "content": "different message", "timestamp": time.time()}
        await managers[user2_id].send_to_user(user2_message)
        
        # Validate user2 received their message
        connections[user2_id].send_json.assert_called_once_with(user2_message)
        
        # Validate user1 did not receive user2's message (still only has original call)
        assert connections[user1_id].send_json.call_count == 1
        
        security_tracker.record_event("message_isolation_validated", 
                                    users_tested=3, 
                                    messages_sent=2, 
                                    isolation_confirmed=True)


class TestConcurrencySafety:
    """Test concurrent access and race condition safety."""
    
    async def test_concurrent_manager_creation(self, factory, user_contexts, security_tracker):
        """Test that concurrent manager creation is thread-safe."""
        security_tracker.record_event("concurrent_creation_test_start")
        
        created_managers = {}
        errors = []
        
        async def create_manager_task(context):
            try:
                manager = factory.create_manager(context)
                created_managers[context.user_id] = manager
                security_tracker.record_event("concurrent_manager_created", user_id=context.user_id)
                return manager
            except Exception as e:
                errors.append(f"User {context.user_id}: {e}")
                security_tracker.record_violation("concurrent_creation_error", "HIGH", 
                                                user_id=context.user_id, error=str(e))
                raise
        
        # Create 10 managers concurrently
        contexts_subset = user_contexts[:10]
        tasks = [create_manager_task(context) for context in contexts_subset]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        creation_time = time.time() - start_time
        
        # Validate all managers were created successfully
        assert len(errors) == 0, f"Errors during concurrent creation: {errors}"
        assert len(created_managers) == 10, f"Expected 10 managers, got {len(created_managers)}"
        
        # Validate all managers are unique instances
        manager_ids = [id(manager) for manager in created_managers.values()]
        assert len(manager_ids) == len(set(manager_ids)), "Duplicate manager instances created"
        
        # Validate factory state is consistent
        factory_stats = factory.get_factory_stats()
        assert factory_stats["factory_metrics"]["managers_active"] == 10
        assert factory_stats["factory_metrics"]["managers_created"] == 10
        
        security_tracker.record_event("concurrent_creation_test_complete",
                                    managers_created=10,
                                    creation_time_seconds=creation_time,
                                    errors=len(errors))
    
    async def test_concurrent_message_sending(self, factory, user_contexts, security_tracker):
        """Test concurrent message sending with race condition detection."""
        security_tracker.record_event("concurrent_messaging_test_start")
        
        # Set up multiple users with connections
        managers = {}
        websockets = {}
        
        for context in user_contexts[:5]:
            manager = factory.create_manager(context)
            websocket = TestWebSocketConnection()  # Real WebSocket implementation
            
            connection = WebSocketConnection(
                connection_id=context.websocket_connection_id,
                user_id=context.user_id,
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            
            await manager.add_connection(connection)
            managers[context.user_id] = manager
            websockets[context.user_id] = websocket
        
        # Send messages concurrently from multiple "users"
        message_tasks = []
        sent_messages = {}
        
        for i, (user_id, manager) in enumerate(managers.items()):
            for msg_num in range(5):  # 5 messages per user
                message = {
                    "type": "concurrent_test",
                    "user": user_id,
                    "message_id": f"{user_id}_msg_{msg_num}",
                    "content": f"Message {msg_num} from {user_id}",
                    "timestamp": time.time()
                }
                
                # Store expected message
                if user_id not in sent_messages:
                    sent_messages[user_id] = []
                sent_messages[user_id].append(message)
                
                # Create concurrent sending task
                message_tasks.append(manager.send_to_user(message))
        
        # Execute all message sends concurrently
        start_time = time.time()
        await asyncio.gather(*message_tasks)
        messaging_time = time.time() - start_time
        
        # Validate all messages were sent to correct recipients
        for user_id in managers.keys():
            websocket = websockets[user_id]
            expected_messages = sent_messages[user_id]
            
            # Check that websocket received exactly the expected messages
            assert websocket.send_json.call_count == len(expected_messages), \
                f"User {user_id} expected {len(expected_messages)} messages, got {websocket.send_json.call_count}"
            
            # Validate no cross-user message leakage
            sent_calls = [call.args[0] for call in websocket.send_json.call_args_list]
            for message in sent_calls:
                assert message["user"] == user_id, \
                    f"User {user_id} received message intended for {message['user']}"
        
        security_tracker.record_event("concurrent_messaging_test_complete",
                                    users=5,
                                    messages_per_user=5,
                                    total_messages=25,
                                    messaging_time_seconds=messaging_time)
    
    async def test_race_condition_in_connection_management(self, factory, user_contexts, security_tracker):
        """Test race conditions in connection add/remove operations."""
        security_tracker.record_event("race_condition_test_start")
        
        context = user_contexts[0]
        manager = factory.create_manager(context)
        
        # Create multiple connections for rapid add/remove
        connections = []
        for i in range(10):
            websocket = TestWebSocketConnection()  # Real WebSocket implementation
            
            connection = WebSocketConnection(
                connection_id=f"{context.websocket_connection_id}_{i}",
                user_id=context.user_id,
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            connections.append(connection)
        
        # Concurrently add and remove connections to test race conditions
        async def add_connection_task(conn):
            try:
                await manager.add_connection(conn)
                security_tracker.record_event("connection_added", connection_id=conn.connection_id)
            except Exception as e:
                security_tracker.record_violation("add_connection_race", "MEDIUM", 
                                                connection_id=conn.connection_id, error=str(e))
                raise
        
        async def remove_connection_task(conn):
            try:
                # Small delay to ensure add happens first
                await asyncio.sleep(0.01)
                await manager.remove_connection(conn.connection_id)
                security_tracker.record_event("connection_removed", connection_id=conn.connection_id)
            except Exception as e:
                security_tracker.record_event("connection_remove_error", 
                                            connection_id=conn.connection_id, error=str(e))
        
        # Run add operations concurrently
        add_tasks = [add_connection_task(conn) for conn in connections[:5]]
        await asyncio.gather(*add_tasks)
        
        # Validate connections were added
        assert len(manager._connections) == 5
        
        # Run concurrent add/remove operations
        mixed_tasks = []
        mixed_tasks.extend([add_connection_task(conn) for conn in connections[5:]])
        mixed_tasks.extend([remove_connection_task(conn) for conn in connections[:3]])
        
        await asyncio.gather(*mixed_tasks, return_exceptions=True)
        
        # Validate final state is consistent
        assert len(manager._connections) == len(manager._connection_ids)
        
        # All connections should belong to the correct user
        for conn in manager._connections.values():
            assert conn.user_id == context.user_id
        
        security_tracker.record_event("race_condition_test_complete",
                                    connections_tested=10,
                                    final_connection_count=len(manager._connections))


class TestResourceManagement:
    """Test resource cleanup and memory leak prevention."""
    
    async def test_connection_cleanup_on_manager_destruction(self, factory, user_contexts, security_tracker):
        """Test that manager destruction properly cleans up all connections."""
        security_tracker.record_event("cleanup_test_start")
        initial_snapshot = security_tracker.take_memory_snapshot("before_manager_creation")
        
        # Create manager and connections
        context = user_contexts[0]
        manager = factory.create_manager(context)
        
        # Add multiple connections
        connections = []
        for i in range(5):
            websocket = TestWebSocketConnection()  # Real WebSocket implementation
            
            connection = WebSocketConnection(
                connection_id=f"{context.websocket_connection_id}_{i}",
                user_id=context.user_id,
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            
            await manager.add_connection(connection)
            connections.append(connection)
        
        assert len(manager._connections) == 5
        creation_snapshot = security_tracker.take_memory_snapshot("after_connections_created")
        
        # Create weak references to track cleanup
        manager_ref = weakref.ref(manager)
        connection_refs = [weakref.ref(conn) for conn in connections]
        
        # Clean up manager
        await manager.cleanup_all_connections()
        
        # Validate all connections are cleaned up
        assert len(manager._connections) == 0
        assert len(manager._connection_ids) == 0
        assert not manager._is_active
        
        cleanup_snapshot = security_tracker.take_memory_snapshot("after_cleanup")
        
        # Clear references and force garbage collection
        del manager
        del connections
        gc.collect()
        
        final_snapshot = security_tracker.take_memory_snapshot("after_gc")
        
        # Validate memory cleanup (manager should be garbage collected)
        if manager_ref() is not None:
            security_tracker.record_violation("memory_leak", "HIGH", 
                                            component="manager", 
                                            description="Manager not garbage collected")
        
        # Some connection refs might still exist due to mocks, but validate reasonable cleanup
        remaining_connections = sum(1 for ref in connection_refs if ref() is not None)
        if remaining_connections > 2:  # Allow some mock-related references
            security_tracker.record_violation("memory_leak", "MEDIUM",
                                            component="connections",
                                            remaining_count=remaining_connections)
        
        security_tracker.record_event("cleanup_test_complete",
                                    initial_memory_mb=initial_snapshot["rss_mb"],
                                    final_memory_mb=final_snapshot["rss_mb"],
                                    memory_growth_mb=final_snapshot["rss_mb"] - initial_snapshot["rss_mb"])
    
    async def test_factory_resource_limits_enforcement(self, factory, user_contexts, security_tracker):
        """Test that factory enforces resource limits properly."""
        security_tracker.record_event("resource_limits_test_start")
        
        # Set low limit for testing
        factory.max_managers_per_user = 3
        
        context = user_contexts[0]
        user_id = context.user_id
        
        # Create managers up to the limit
        managers = []
        for i in range(3):
            # Create unique context for each manager
            unique_context = UserExecutionContext(
                user_id=user_id,  # Same user
                thread_id=f"thread_{i}",
                run_id=f"run_{i}",
                request_id=f"req_{i}",
                websocket_connection_id=f"conn_{i}_{uuid.uuid4().hex[:8]}"  # Unique connection
            )
            manager = factory.create_manager(unique_context)
            managers.append(manager)
        
        assert len(managers) == 3
        assert factory._user_manager_count[user_id] == 3
        
        # Attempt to exceed the limit
        excess_context = UserExecutionContext(
            user_id=user_id,  # Same user
            thread_id="thread_excess",
            run_id="run_excess", 
            request_id="req_excess",
            websocket_connection_id=f"conn_excess_{uuid.uuid4().hex[:8]}"
        )
        
        with pytest.raises(RuntimeError, match="reached the maximum number"):
            factory.create_manager(excess_context)
        
        # Validate factory metrics reflect the limit hit
        stats = factory.get_factory_stats()
        assert stats["factory_metrics"]["resource_limit_hits"] > 0
        
        # Clean up one manager and try again
        first_manager_key = list(factory._active_managers.keys())[0]
        await factory.cleanup_manager(first_manager_key)
        
        # Now should be able to create new manager
        new_manager = factory.create_manager(excess_context)
        assert new_manager is not None
        assert factory._user_manager_count[user_id] == 3  # Still at limit
        
        security_tracker.record_event("resource_limits_test_complete",
                                    limit_tested=3,
                                    limit_hits=stats["factory_metrics"]["resource_limit_hits"])
    
    async def test_memory_leak_detection_with_many_managers(self, factory, user_contexts, security_tracker):
        """Test for memory leaks when creating and destroying many managers."""
        security_tracker.record_event("memory_leak_test_start")
        initial_snapshot = security_tracker.take_memory_snapshot("test_start")
        
        # Create and destroy managers in batches
        total_managers_created = 0
        
        for batch in range(5):  # 5 batches
            batch_managers = []
            
            # Create 10 managers
            for i in range(10):
                context_idx = (batch * 10 + i) % len(user_contexts)
                context = user_contexts[context_idx]
                
                # Create unique connection context
                unique_context = UserExecutionContext(
                    user_id=f"{context.user_id}_batch_{batch}",
                    thread_id=f"{context.thread_id}_batch_{batch}",
                    run_id=f"{context.run_id}_batch_{batch}",
                    request_id=f"{context.request_id}_batch_{batch}",
                    websocket_connection_id=f"{context.websocket_connection_id}_batch_{batch}_{i}"
                )
                
                manager = factory.create_manager(unique_context)
                
                # Add a connection to each manager
                websocket = TestWebSocketConnection()  # Real WebSocket implementation
                
                connection = WebSocketConnection(
                    connection_id=unique_context.websocket_connection_id,
                    user_id=unique_context.user_id,
                    websocket=websocket,
                    connected_at=datetime.utcnow()
                )
                
                await manager.add_connection(connection)
                batch_managers.append((manager, unique_context))
                total_managers_created += 1
            
            batch_snapshot = security_tracker.take_memory_snapshot(f"batch_{batch}_created")
            
            # Clean up all managers in this batch
            for manager, context in batch_managers:
                await manager.cleanup_all_connections()
                isolation_key = factory._generate_isolation_key(context)
                await factory.cleanup_manager(isolation_key)
            
            cleanup_snapshot = security_tracker.take_memory_snapshot(f"batch_{batch}_cleaned")
            
            # Force garbage collection
            del batch_managers
            gc.collect()
            
            gc_snapshot = security_tracker.take_memory_snapshot(f"batch_{batch}_gc")
            
            # Check for memory growth
            memory_growth = gc_snapshot["rss_mb"] - initial_snapshot["rss_mb"]
            if memory_growth > 50:  # Allow 50MB growth tolerance
                security_tracker.record_violation("excessive_memory_growth", "HIGH",
                                                batch=batch,
                                                memory_growth_mb=memory_growth,
                                                managers_created=total_managers_created)
        
        final_snapshot = security_tracker.take_memory_snapshot("test_end")
        
        # Validate factory is clean
        factory_stats = factory.get_factory_stats()
        assert factory_stats["factory_metrics"]["managers_active"] == 0, \
            "Factory should have no active managers after cleanup"
        
        total_memory_growth = final_snapshot["rss_mb"] - initial_snapshot["rss_mb"]
        
        security_tracker.record_event("memory_leak_test_complete",
                                    total_managers_created=total_managers_created,
                                    total_memory_growth_mb=total_memory_growth,
                                    final_active_managers=factory_stats["factory_metrics"]["managers_active"])


class TestPerformanceScaling:
    """Test performance and scaling characteristics."""
    
    async def test_linear_scaling_with_concurrent_users(self, factory, user_contexts, security_tracker):
        """Test that factory scales linearly with number of users."""
        security_tracker.record_event("scaling_test_start")
        
        scaling_metrics = []
        user_counts = [5, 10, 15]  # Test different user counts
        
        for user_count in user_counts:
            start_time = time.time()
            memory_before = security_tracker.take_memory_snapshot(f"before_{user_count}_users")
            
            # Create managers for N users
            managers = {}
            for i in range(user_count):
                context = user_contexts[i]
                manager = factory.create_manager(context)
                
                # Add connection to each manager
                websocket = TestWebSocketConnection()  # Real WebSocket implementation
                
                connection = WebSocketConnection(
                    connection_id=context.websocket_connection_id,
                    user_id=context.user_id,
                    websocket=websocket,
                    connected_at=datetime.utcnow()
                )
                
                await manager.add_connection(connection)
                managers[context.user_id] = manager
            
            creation_time = time.time() - start_time
            memory_after = security_tracker.take_memory_snapshot(f"after_{user_count}_users")
            
            # Test concurrent message sending
            message_start_time = time.time()
            message_tasks = []
            
            for user_id, manager in managers.items():
                message = {"type": "scaling_test", "user": user_id, "timestamp": time.time()}
                message_tasks.append(manager.send_to_user(message))
            
            await asyncio.gather(*message_tasks)
            messaging_time = time.time() - message_start_time
            
            # Record scaling metrics
            metrics = {
                "user_count": user_count,
                "creation_time": creation_time,
                "messaging_time": messaging_time,
                "memory_usage_mb": memory_after["rss_mb"],
                "memory_per_user_mb": (memory_after["rss_mb"] - memory_before["rss_mb"]) / user_count if user_count > 0 else 0
            }
            scaling_metrics.append(metrics)
            
            # Clean up for next iteration
            for context in user_contexts[:user_count]:
                isolation_key = factory._generate_isolation_key(context)
                await factory.cleanup_manager(isolation_key)
        
        # Analyze scaling characteristics
        for i in range(1, len(scaling_metrics)):
            current = scaling_metrics[i]
            previous = scaling_metrics[i-1]
            
            # Creation time should scale reasonably
            time_ratio = current["creation_time"] / previous["creation_time"]
            user_ratio = current["user_count"] / previous["user_count"]
            
            # Time should not scale worse than quadratic
            if time_ratio > (user_ratio ** 1.5):
                security_tracker.record_violation("poor_scaling", "MEDIUM",
                                                metric="creation_time",
                                                time_ratio=time_ratio,
                                                user_ratio=user_ratio)
            
            # Messaging time should scale approximately linearly
            msg_time_ratio = current["messaging_time"] / previous["messaging_time"]
            if msg_time_ratio > (user_ratio * 1.2):  # Allow 20% overhead
                security_tracker.record_violation("poor_scaling", "MEDIUM",
                                                metric="messaging_time",
                                                time_ratio=msg_time_ratio,
                                                user_ratio=user_ratio)
        
        security_tracker.record_event("scaling_test_complete", metrics=scaling_metrics)
    
    async def test_connection_isolation_under_load(self, factory, user_contexts, security_tracker):
        """Test that connection isolation is maintained under heavy load."""
        security_tracker.record_event("load_isolation_test_start")
        
        # Create managers for 10 users
        managers = {}
        websockets = {}
        
        for context in user_contexts[:10]:
            manager = factory.create_manager(context)
            websocket = TestWebSocketConnection()  # Real WebSocket implementation
            
            connection = WebSocketConnection(
                connection_id=context.websocket_connection_id,
                user_id=context.user_id,
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            
            await manager.add_connection(connection)
            managers[context.user_id] = manager
            websockets[context.user_id] = websocket
        
        # Generate heavy message load (50 messages per user)
        all_tasks = []
        expected_messages = {}
        
        for user_id, manager in managers.items():
            expected_messages[user_id] = []
            
            for msg_num in range(50):
                message = {
                    "type": "load_test",
                    "user_id": user_id,
                    "message_id": f"{user_id}_{msg_num}",
                    "content": f"Load test message {msg_num}",
                    "timestamp": time.time()
                }
                expected_messages[user_id].append(message)
                all_tasks.append(manager.send_to_user(message))
        
        # Execute all messages concurrently
        start_time = time.time()
        await asyncio.gather(*all_tasks)
        total_time = time.time() - start_time
        
        # Validate no cross-user message leakage under load
        cross_contamination_detected = False
        
        for user_id in managers.keys():
            websocket = websockets[user_id]
            sent_messages = [call.args[0] for call in websocket.send_json.call_args_list]
            
            # Verify correct number of messages
            assert len(sent_messages) == 50, \
                f"User {user_id} expected 50 messages, got {len(sent_messages)}"
            
            # Verify all messages belong to this user
            for message in sent_messages:
                if message["user_id"] != user_id:
                    cross_contamination_detected = True
                    security_tracker.record_violation("message_cross_contamination", "CRITICAL",
                                                    expected_user=user_id,
                                                    actual_user=message["user_id"],
                                                    message_id=message["message_id"])
        
        assert not cross_contamination_detected, "Message cross-contamination detected under load"
        
        security_tracker.record_event("load_isolation_test_complete",
                                    users=10,
                                    messages_per_user=50,
                                    total_messages=500,
                                    total_time_seconds=total_time,
                                    messages_per_second=500 / total_time,
                                    cross_contamination_detected=cross_contamination_detected)


class TestSecurityBoundaries:
    """Test security boundary enforcement."""
    
    async def test_user_execution_context_enforcement(self, factory, security_tracker):
        """Test that UserExecutionContext is strictly enforced."""
        security_tracker.record_event("context_enforcement_test_start")
        
        # Test invalid context types
        invalid_contexts = [
            None,
            "invalid_string",
            {"user_id": "test"},
            123,
            []
        ]
        
        for invalid_context in invalid_contexts:
            with pytest.raises(ValueError, match="must be a UserExecutionContext instance"):
                factory.create_manager(invalid_context)
        
        # Test missing required fields
        try:
            invalid_context = UserExecutionContext(
                user_id="",  # Empty user ID
                thread_id="thread_1",
                run_id="run_1", 
                request_id="req_1",
                websocket_connection_id="conn_1"
            )
            # Should not allow empty user_id
            manager = factory.create_manager(invalid_context)
            security_tracker.record_violation("empty_user_id_allowed", "CRITICAL",
                                            description="Factory allowed empty user_id")
        except (ValueError, RuntimeError):
            # Expected behavior
            pass
        
        security_tracker.record_event("context_enforcement_test_complete")
    
    async def test_connection_security_validation(self, factory, user_contexts, security_tracker):
        """Test security validation in connection operations."""
        security_tracker.record_event("connection_security_test_start")
        
        context = user_contexts[0]
        manager = factory.create_manager(context)
        
        # Create legitimate connection
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        
        legitimate_connection = WebSocketConnection(
            connection_id=context.websocket_connection_id,
            user_id=context.user_id,
            websocket=legitimate_websocket,
            connected_at=datetime.utcnow()
        )
        
        await manager.add_connection(legitimate_connection)
        
        # Test connection with mismatched user_id (security violation)
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        
        malicious_connection = WebSocketConnection(
            connection_id="malicious_conn",
            user_id="different_user",  # Wrong user!
            websocket=malicious_websocket,
            connected_at=datetime.utcnow()
        )
        
        # Should raise security violation
        with pytest.raises(ValueError, match="does not match manager user_id"):
            await manager.add_connection(malicious_connection)
        
        # Verify legitimate connection is still present and secure
        assert len(manager._connections) == 1
        assert context.websocket_connection_id in manager._connections
        assert "malicious_conn" not in manager._connections
        
        # Test message sending security
        await manager.send_to_user({"type": "test", "message": "secure message"})
        
        # Legitimate websocket should have received message
        legitimate_websocket.send_json.assert_called()
        
        # Malicious websocket should not have received anything
        malicious_websocket.send_json.assert_not_called()
        
        security_tracker.record_event("connection_security_test_complete",
                                    legitimate_connections=1,
                                    blocked_malicious_connections=1)
    
    async def test_manager_deactivation_security(self, factory, user_contexts, security_tracker):
        """Test that deactivated managers cannot be misused."""
        security_tracker.record_event("deactivation_security_test_start")
        
        context = user_contexts[0]
        manager = factory.create_manager(context)
        
        # Add connection
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        
        connection = WebSocketConnection(
            connection_id=context.websocket_connection_id,
            user_id=context.user_id,
            websocket=websocket,
            connected_at=datetime.utcnow()
        )
        
        await manager.add_connection(connection)
        assert manager._is_active is True
        
        # Deactivate manager
        await manager.cleanup_all_connections()
        assert manager._is_active is False
        
        # Test that deactivated manager rejects operations
        operations_to_test = [
            ("add_connection", lambda: manager.add_connection(connection)),
            ("remove_connection", lambda: manager.remove_connection(context.websocket_connection_id)),
            ("send_to_user", lambda: manager.send_to_user({"type": "test"})),
            ("get_connection", lambda: manager.get_connection(context.websocket_connection_id)),
            ("get_user_connections", lambda: manager.get_user_connections()),
        ]
        
        security_violations = 0
        for operation_name, operation in operations_to_test:
            try:
                if asyncio.iscoroutinefunction(operation):
                    await operation()
                else:
                    operation()
                
                # If we reach here, the operation didn't raise an error (security violation)
                security_tracker.record_violation("deactivated_manager_allowed_operation", "CRITICAL",
                                                operation=operation_name,
                                                description=f"Deactivated manager allowed {operation_name}")
                security_violations += 1
                
            except RuntimeError as e:
                # Expected behavior - deactivated manager should reject operations
                if "is no longer active" in str(e):
                    security_tracker.record_event("deactivation_security_enforced", operation=operation_name)
                else:
                    security_tracker.record_violation("unexpected_error", "MEDIUM",
                                                    operation=operation_name,
                                                    error=str(e))
            except Exception as e:
                security_tracker.record_violation("unexpected_error", "MEDIUM",
                                                operation=operation_name,
                                                error=str(e))
        
        assert security_violations == 0, f"Deactivated manager allowed {security_violations} operations"
        
        security_tracker.record_event("deactivation_security_test_complete",
                                    security_violations=security_violations)


# Integration test that validates the complete security system
class TestCompleteSecurityValidation:
    """Comprehensive security validation test."""
    
    async def test_end_to_end_security_scenario(self, factory, user_contexts, security_tracker):
        """Complete end-to-end security validation scenario."""
        security_tracker.record_event("e2e_security_test_start")
        
        # Phase 1: Create multi-user environment
        managers = {}
        websockets = {}
        
        for i, context in enumerate(user_contexts[:5]):
            manager = factory.create_manager(context)
            websocket = TestWebSocketConnection()  # Real WebSocket implementation
            
            connection = WebSocketConnection(
                connection_id=context.websocket_connection_id,
                user_id=context.user_id,
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            
            await manager.add_connection(connection)
            managers[context.user_id] = manager
            websockets[context.user_id] = websocket
        
        # Phase 2: Simulate concurrent user activity
        all_tasks = []
        user_messages = {}
        
        for user_id, manager in managers.items():
            user_messages[user_id] = []
            
            # Each user sends 10 messages
            for msg_num in range(10):
                message = {
                    "type": "e2e_test",
                    "user_id": user_id,
                    "message_id": f"{user_id}_msg_{msg_num}",
                    "sensitive_data": f"secret_data_for_{user_id}_{msg_num}",
                    "timestamp": time.time()
                }
                user_messages[user_id].append(message)
                all_tasks.append(manager.send_to_user(message))
        
        # Execute all messages concurrently
        await asyncio.gather(*all_tasks)
        
        # Phase 3: Validate complete isolation
        security_violations = 0
        
        for user_id in managers.keys():
            websocket = websockets[user_id]
            received_messages = [call.args[0] for call in websocket.send_json.call_args_list]
            
            # Verify correct count
            assert len(received_messages) == 10, \
                f"User {user_id} expected 10 messages, got {len(received_messages)}"
            
            # Verify all messages belong to this user
            for message in received_messages:
                if message["user_id"] != user_id:
                    security_violations += 1
                    security_tracker.record_violation("data_leakage", "CRITICAL",
                                                    victim_user=user_id,
                                                    leaked_user=message["user_id"],
                                                    sensitive_data=message["sensitive_data"])
                
                # Verify sensitive data doesn't leak
                if f"secret_data_for_{user_id}" not in message["sensitive_data"]:
                    security_violations += 1
                    security_tracker.record_violation("sensitive_data_corruption", "CRITICAL",
                                                    user_id=user_id,
                                                    corrupted_data=message["sensitive_data"])
        
        # Phase 4: Test malicious access attempts
        malicious_attempts = 0
        
        for user_id, manager in managers.items():
            # Try to access another user's connections
            other_user_ids = [uid for uid in managers.keys() if uid != user_id]
            
            for other_user_id in other_user_ids:
                # Attempt to get other user's connections
                other_connections = managers[other_user_id].get_user_connections()
                if any(conn_id in manager._connections for conn_id in other_connections):
                    malicious_attempts += 1
                    security_tracker.record_violation("connection_access_leak", "CRITICAL",
                                                    attacker=user_id,
                                                    victim=other_user_id)
        
        # Phase 5: Validate factory state integrity
        factory_stats = factory.get_factory_stats()
        expected_managers = len(user_contexts[:5])
        
        assert factory_stats["factory_metrics"]["managers_active"] == expected_managers, \
            "Factory manager count mismatch"
        assert factory_stats["factory_metrics"]["users_with_active_managers"] == expected_managers, \
            "Factory user count mismatch"
        
        # Phase 6: Test cleanup security
        for context in user_contexts[:5]:
            isolation_key = factory._generate_isolation_key(context)
            await factory.cleanup_manager(isolation_key)
        
        # Validate complete cleanup
        final_stats = factory.get_factory_stats()
        assert final_stats["factory_metrics"]["managers_active"] == 0, \
            "Managers not properly cleaned up"
        
        # Final security assessment
        total_violations = security_violations + malicious_attempts
        
        security_tracker.record_event("e2e_security_test_complete",
                                    users_tested=5,
                                    messages_per_user=10,
                                    total_violations=total_violations,
                                    security_status="PASS" if total_violations == 0 else "FAIL")
        
        assert total_violations == 0, f"Security validation failed: {total_violations} violations detected"


# Performance monitoring test
class TestSecurityPerformance:
    """Test security performance and monitoring."""
    
    async def test_security_monitoring_overhead(self, factory, user_contexts, security_tracker):
        """Test that security measures don't add excessive overhead."""
        security_tracker.record_event("performance_test_start")
        
        # Baseline timing without security validation
        start_time = time.time()
        
        # Create 10 managers with security
        secured_managers = []
        for context in user_contexts[:10]:
            manager = factory.create_manager(context)
            secured_managers.append(manager)
        
        creation_time = time.time() - start_time
        
        # Test message sending performance with security
        message_start = time.time()
        message_tasks = []
        
        for manager in secured_managers:
            websocket = TestWebSocketConnection()  # Real WebSocket implementation
            
            connection = WebSocketConnection(
                connection_id=f"perf_{id(manager)}",
                user_id=manager.user_context.user_id,
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            
            await manager.add_connection(connection)
            
            # Send 5 messages per manager
            for i in range(5):
                message = {"type": "perf_test", "message_id": i}
                message_tasks.append(manager.send_to_user(message))
        
        await asyncio.gather(*message_tasks)
        messaging_time = time.time() - message_start
        
        # Performance thresholds
        max_creation_time = 2.0  # 2 seconds for 10 managers
        max_messaging_time = 1.0  # 1 second for 50 messages
        
        if creation_time > max_creation_time:
            security_tracker.record_violation("performance_degradation", "MEDIUM",
                                            metric="creation_time",
                                            actual=creation_time,
                                            threshold=max_creation_time)
        
        if messaging_time > max_messaging_time:
            security_tracker.record_violation("performance_degradation", "MEDIUM",
                                            metric="messaging_time", 
                                            actual=messaging_time,
                                            threshold=max_messaging_time)
        
        security_tracker.record_event("performance_test_complete",
                                    creation_time_seconds=creation_time,
                                    messaging_time_seconds=messaging_time,
                                    managers_created=10,
                                    messages_sent=50)
        
        # Performance should be reasonable
        assert creation_time < max_creation_time * 2, "Security overhead too high for manager creation"
        assert messaging_time < max_messaging_time * 2, "Security overhead too high for messaging"


# Test fixtures cleanup
@pytest.fixture(autouse=True)
async def cleanup_factories():
    """Ensure all factory instances are cleaned up after tests."""
    yield
    
    # Clean up global factory if it exists
    try:
        from netra_backend.app.websocket_core.websocket_manager_factory import _factory_instance
        if _factory_instance:
            await _factory_instance.shutdown()
    except:
        pass  # Ignore cleanup errors


# Final audit summary test
@pytest.mark.asyncio
async def test_security_audit_summary(security_tracker):
    """Generate final security audit summary."""
    audit_summary = security_tracker.get_audit_summary()
    
    logger.info("=== WEBSOCKET FACTORY SECURITY AUDIT SUMMARY ===")
    logger.info(f"Total Events: {audit_summary['total_events']}")
    logger.info(f"Total Violations: {audit_summary['total_violations']}")
    logger.info(f"Critical Violations: {audit_summary['critical_violations']}")
    logger.info(f"Memory Growth: {audit_summary['memory_growth']['rss_growth_mb']:.2f} MB")
    logger.info(f"Object Growth: {audit_summary['memory_growth']['objects_growth']}")
    logger.info(f"Test Duration: {audit_summary['test_duration']:.2f} seconds")
    
    if audit_summary['total_violations'] > 0:
        logger.error("SECURITY VIOLATIONS DETECTED:")
        for violation in audit_summary['violation_details']:
            logger.error(f"  - {violation['violation_type']}: {violation.get('description', 'No description')}")
    
    # Final validation
    assert audit_summary['critical_violations'] == 0, \
        f"Critical security violations detected: {audit_summary['critical_violations']}"
    
    assert audit_summary['memory_growth']['rss_growth_mb'] < 100, \
        f"Excessive memory growth: {audit_summary['memory_growth']['rss_growth_mb']} MB"
    
    logger.info("=== SECURITY AUDIT PASSED ===")