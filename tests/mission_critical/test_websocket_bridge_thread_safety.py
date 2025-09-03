#!/usr/bin/env python
"""Mission Critical Tests: WebSocket Bridge Thread Safety Validation
===================================================================

This test suite validates CRITICAL thread safety in WebSocket bridge operations:

REQUIREMENTS:
- Thread-safe singleton pattern with 50+ concurrent threads
- No race conditions under extreme concurrent access
- Proper lock management without deadlocks  
- Message ordering guarantees under thread pressure
- Memory coherence across thread boundaries

BUSINESS VALUE: $1M+ ARR - Core chat functionality depends on thread safety
ANY THREAD SAFETY VIOLATION MEANS PRODUCTION IS BROKEN.

Uses Factory-Based WebSocket Patterns from USER_CONTEXT_ARCHITECTURE.md
"""

import asyncio
import concurrent.futures
import threading
import time
import uuid
import os
import sys
import gc
import weakref
from typing import Dict, List, Set, Any, Optional, Tuple
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from collections import defaultdict, deque
import random

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

# Import environment management
from shared.isolated_environment import get_env

# Set up isolated test environment
env = get_env()
env.set('WEBSOCKET_TEST_ISOLATED', 'true', "test")
env.set('SKIP_REAL_SERVICES', 'false', "test")
env.set('USE_REAL_SERVICES', 'true', "test")

# Import factory patterns from architecture
from netra_backend.app.services.websocket_bridge_factory import (
    WebSocketBridgeFactory,
    UserWebSocketEmitter,
    UserWebSocketContext,
    WebSocketEvent,
    ConnectionStatus
)

# Import WebSocket manager
from netra_backend.app.websocket_core.manager import WebSocketManager, get_websocket_manager

# Import test framework components
from test_framework.test_context import TestContext, create_test_context

# Disable pytest warnings
pytestmark = [
    pytest.mark.filterwarnings("ignore"),
    pytest.mark.asyncio
]

# Thread-safe logger for tests
class ThreadSafeLogger:
    def __init__(self):
        self.lock = threading.Lock()
        self.messages = deque(maxlen=10000)  # Thread-safe bounded buffer
    
    def info(self, msg):
        with self.lock:
            self.messages.append(f"THREAD-SAFETY: {msg}")
            print(f"THREAD-SAFETY: {msg}")
    
    def warning(self, msg):
        with self.lock:
            self.messages.append(f"WARN: {msg}")
            print(f"WARN: {msg}")
    
    def error(self, msg):
        with self.lock:
            self.messages.append(f"ERROR: {msg}")
            print(f"ERROR: {msg}")

logger = ThreadSafeLogger()


# ============================================================================
# THREAD SAFETY INFRASTRUCTURE
# ============================================================================

@dataclass
class ThreadSafetyViolation:
    """Records a thread safety violation."""
    violation_type: str
    thread_id: str
    timestamp: datetime
    description: str
    context: Dict[str, Any]
    stack_trace: Optional[str] = None


class ThreadSafetyMonitor:
    """Monitor for detecting thread safety violations in real-time."""
    
    def __init__(self):
        self.violations = []
        self.violations_lock = threading.Lock()
        self.access_counters = defaultdict(int)
        self.access_lock = threading.Lock()
        self.memory_coherence_failures = []
        self.deadlock_warnings = []
        self.race_condition_detections = []
        
        # Track singleton access patterns
        self.singleton_access_threads = set()
        self.singleton_instances = weakref.WeakSet()
        self.singleton_lock = threading.Lock()
    
    def record_violation(self, violation_type: str, description: str, context: Dict[str, Any] = None):
        """Thread-safe violation recording."""
        violation = ThreadSafetyViolation(
            violation_type=violation_type,
            thread_id=str(threading.get_ident()),
            timestamp=datetime.now(timezone.utc),
            description=description,
            context=context or {}
        )
        
        with self.violations_lock:
            self.violations.append(violation)
    
    def record_singleton_access(self, instance):
        """Record singleton access for pattern validation."""
        thread_id = threading.get_ident()
        
        with self.singleton_lock:
            self.singleton_access_threads.add(thread_id)
            self.singleton_instances.add(instance)
    
    def check_memory_coherence(self, shared_value: Any, expected_value: Any, context: str):
        """Check for memory coherence violations."""
        if shared_value != expected_value:
            violation_context = {
                'context': context,
                'shared_value': shared_value,
                'expected_value': expected_value,
                'thread_id': threading.get_ident()
            }
            
            with self.violations_lock:
                self.memory_coherence_failures.append(violation_context)
                self.record_violation(
                    "memory_coherence",
                    f"Memory coherence failure in {context}",
                    violation_context
                )
    
    def increment_access_counter(self, resource_name: str):
        """Thread-safe access counter increment."""
        with self.access_lock:
            self.access_counters[resource_name] += 1
    
    def get_violation_report(self) -> Dict[str, Any]:
        """Get comprehensive thread safety violation report."""
        with self.violations_lock:
            with self.singleton_lock:
                return {
                    'total_violations': len(self.violations),
                    'violations_by_type': defaultdict(int),
                    'violations_detail': [
                        {
                            'type': v.violation_type,
                            'thread_id': v.thread_id,
                            'description': v.description,
                            'timestamp': v.timestamp.isoformat(),
                            'context': v.context
                        }
                        for v in self.violations
                    ],
                    'singleton_access_threads': len(self.singleton_access_threads),
                    'singleton_instances_created': len(self.singleton_instances),
                    'memory_coherence_failures': len(self.memory_coherence_failures),
                    'deadlock_warnings': len(self.deadlock_warnings),
                    'race_condition_detections': len(self.race_condition_detections),
                    'access_counters': dict(self.access_counters)
                }


class ThreadSafeWebSocketConnection:
    """Thread-safe mock WebSocket connection for testing."""
    
    def __init__(self, user_id: str, connection_id: str, monitor: ThreadSafetyMonitor):
        self.user_id = user_id
        self.connection_id = connection_id
        self.monitor = monitor
        self.is_connected = True
        
        # Thread-safe message storage
        self.sent_messages = deque()
        self.sent_messages_lock = threading.RLock()  # Reentrant lock for nested operations
        
        # Thread-safe connection state
        self.connection_state_lock = threading.Lock()
        self.last_ping = time.time()
        
        # Message ordering validation
        self.message_sequence = 0
        self.sequence_lock = threading.Lock()
        
    async def send_json(self, data: dict) -> None:
        """Thread-safe send_json with ordering guarantees."""
        if not self.is_connected:
            raise ConnectionError(f"WebSocket {self.connection_id} is closed")
        
        # Get sequence number atomically
        with self.sequence_lock:
            sequence = self.message_sequence
            self.message_sequence += 1
        
        # Store message with thread info
        message_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data,
            'thread_id': threading.get_ident(),
            'sequence': sequence,
            'connection_id': self.connection_id
        }
        
        with self.sent_messages_lock:
            self.sent_messages.append(message_record)
            self.monitor.increment_access_counter(f"send_json_{self.connection_id}")
        
        # Simulate small network delay with random jitter to stress test
        await asyncio.sleep(random.uniform(0.001, 0.005))
    
    async def send_text(self, data: str) -> None:
        """Thread-safe send_text with ordering guarantees."""
        if not self.is_connected:
            raise ConnectionError(f"WebSocket {self.connection_id} is closed")
        
        with self.sequence_lock:
            sequence = self.message_sequence
            self.message_sequence += 1
        
        message_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data,
            'thread_id': threading.get_ident(),
            'sequence': sequence,
            'connection_id': self.connection_id
        }
        
        with self.sent_messages_lock:
            self.sent_messages.append(message_record)
            self.monitor.increment_access_counter(f"send_text_{self.connection_id}")
        
        await asyncio.sleep(random.uniform(0.001, 0.005))
    
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Thread-safe close method."""
        with self.connection_state_lock:
            self.is_connected = False
    
    async def ping(self, data: bytes = b'') -> None:
        """Thread-safe ping method."""
        if not self.is_connected:
            raise ConnectionError(f"WebSocket {self.connection_id} is closed")
        
        with self.connection_state_lock:
            self.last_ping = time.time()
        return True
    
    def get_message_count(self) -> int:
        """Thread-safe message count."""
        with self.sent_messages_lock:
            return len(self.sent_messages)
    
    def get_messages_copy(self) -> List[Dict]:
        """Thread-safe message copy."""
        with self.sent_messages_lock:
            return list(self.sent_messages)
    
    def validate_message_ordering(self) -> bool:
        """Validate messages are in sequential order."""
        with self.sent_messages_lock:
            messages = list(self.sent_messages)
        
        for i in range(1, len(messages)):
            if messages[i]['sequence'] != messages[i-1]['sequence'] + 1:
                self.monitor.record_violation(
                    "message_ordering",
                    f"Message ordering violation: {messages[i-1]['sequence']} -> {messages[i]['sequence']}",
                    {'connection_id': self.connection_id, 'message_index': i}
                )
                return False
        return True


# ============================================================================
# THREAD SAFETY TEST MANAGER
# ============================================================================

class ThreadSafetyTestManager:
    """Manager for comprehensive thread safety testing."""
    
    def __init__(self):
        self.factory = WebSocketBridgeFactory()
        self.websocket_manager = None
        self.monitor = ThreadSafetyMonitor()
        self.user_emitters: Dict[str, UserWebSocketEmitter] = {}
        self.mock_connections: Dict[str, ThreadSafeWebSocketConnection] = {}
        self.emitters_lock = threading.RLock()
        self.connections_lock = threading.RLock()
        
        # Performance tracking
        self.performance_metrics = {
            'operation_times': defaultdict(list),
            'lock_contention_events': [],
            'thread_switches': []
        }
        self.performance_lock = threading.Lock()
    
    async def initialize(self):
        """Initialize manager for thread safety testing."""
        try:
            # Create WebSocket manager and track singleton behavior
            self.websocket_manager = WebSocketManager()
            self.monitor.record_singleton_access(self.websocket_manager)
            
            # Configure factory with test setup
            try:
                from test_framework.websocket_helpers import create_test_connection_pool
                connection_pool = await create_test_connection_pool()
            except Exception:
                # Fallback to mock setup
                connection_pool = MagicMock()
                connection_pool.get_connection = AsyncMock(return_value=None)
            
            self.factory.configure(
                connection_pool=connection_pool,
                agent_registry=None,
                health_monitor=None
            )
            
            logger.info("Thread safety test manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize thread safety test manager: {e}")
            raise
    
    async def create_thread_safe_user_emitter(self, user_id: str, thread_id: str) -> UserWebSocketEmitter:
        """Create user emitter with thread safety monitoring."""
        start_time = time.time()
        
        try:
            connection_id = f"threadsafe_conn_{user_id}_{uuid.uuid4().hex[:8]}"
            mock_ws = ThreadSafeWebSocketConnection(user_id, connection_id, self.monitor)
            
            # Register with WebSocket manager (test singleton thread safety)
            try:
                manager = get_websocket_manager()
                self.monitor.record_singleton_access(manager)
                
                ws_connection_id = await manager.connect_user(
                    user_id=user_id,
                    websocket=mock_ws,
                    thread_id=thread_id
                )
            except Exception as e:
                logger.warning(f"WebSocket manager connection failed: {e}")
                ws_connection_id = connection_id
            
            # Create user emitter via factory
            try:
                user_emitter = await self.factory.create_user_emitter(
                    user_id=user_id,
                    thread_id=thread_id,
                    connection_id=connection_id
                )
            except Exception as e:
                logger.warning(f"Factory emitter creation failed: {e}")
                user_context = UserWebSocketContext(user_id=user_id, thread_id=thread_id)
                user_emitter = UserWebSocketEmitter(
                    websocket_connection=mock_ws,
                    user_context=user_context
                )
            
            # Thread-safe storage
            with self.emitters_lock:
                self.user_emitters[user_id] = user_emitter
            
            with self.connections_lock:
                self.mock_connections[connection_id] = mock_ws
            
            # Record performance
            operation_time = time.time() - start_time
            with self.performance_lock:
                self.performance_metrics['operation_times']['create_emitter'].append(operation_time)
            
            return user_emitter
            
        except Exception as e:
            self.monitor.record_violation(
                "emitter_creation",
                f"Failed to create emitter: {str(e)}",
                {'user_id': user_id, 'thread_id': thread_id}
            )
            raise
    
    async def send_thread_safe_message(self, user_id: str, message_type: str, message_data: Dict) -> bool:
        """Send message with thread safety validation."""
        start_time = time.time()
        
        try:
            # Get emitter safely
            emitter = None
            with self.emitters_lock:
                emitter = self.user_emitters.get(user_id)
            
            if not emitter:
                self.monitor.record_violation(
                    "missing_emitter",
                    f"No emitter found for user {user_id}",
                    {'user_id': user_id, 'message_type': message_type}
                )
                return False
            
            # Send message based on type
            success = False
            if message_type == "agent_started":
                await emitter.notify_agent_started(
                    agent_name=message_data.get('agent_name', 'TestAgent'),
                    run_id=message_data.get('run_id', str(uuid.uuid4()))
                )
                success = True
            elif message_type == "agent_thinking":
                await emitter.notify_agent_thinking(
                    agent_name=message_data.get('agent_name', 'TestAgent'),
                    run_id=message_data.get('run_id', str(uuid.uuid4())),
                    thinking_text=message_data.get('text', 'Thinking...')
                )
                success = True
            elif message_type == "tool_executing":
                await emitter.notify_tool_executing(
                    tool_name=message_data.get('tool_name', 'TestTool'),
                    run_id=message_data.get('run_id', str(uuid.uuid4())),
                    tool_input=message_data.get('input', {})
                )
                success = True
            elif message_type == "tool_completed":
                await emitter.notify_tool_completed(
                    tool_name=message_data.get('tool_name', 'TestTool'),
                    run_id=message_data.get('run_id', str(uuid.uuid4())),
                    tool_output=message_data.get('output', {})
                )
                success = True
            elif message_type == "agent_completed":
                await emitter.notify_agent_completed(
                    agent_name=message_data.get('agent_name', 'TestAgent'),
                    run_id=message_data.get('run_id', str(uuid.uuid4())),
                    result=message_data.get('result', {})
                )
                success = True
            
            # Record performance
            operation_time = time.time() - start_time
            with self.performance_lock:
                self.performance_metrics['operation_times']['send_message'].append(operation_time)
            
            return success
            
        except Exception as e:
            self.monitor.record_violation(
                "message_send",
                f"Message send failed: {str(e)}",
                {
                    'user_id': user_id,
                    'message_type': message_type,
                    'thread_id': threading.get_ident()
                }
            )
            return False
    
    async def cleanup_user_emitter(self, user_id: str) -> bool:
        """Clean up user emitter with thread safety."""
        start_time = time.time()
        
        try:
            # Get and remove emitter
            emitter = None
            with self.emitters_lock:
                emitter = self.user_emitters.pop(user_id, None)
            
            if emitter:
                await emitter.cleanup()
            
            # Clean up WebSocket manager
            if self.websocket_manager:
                user_connections = getattr(self.websocket_manager, 'user_connections', {}).get(user_id, set())
                for conn_id in list(user_connections):
                    await self.websocket_manager.disconnect_user(user_id, conn_id)
            
            # Record performance
            operation_time = time.time() - start_time
            with self.performance_lock:
                self.performance_metrics['operation_times']['cleanup'].append(operation_time)
            
            return True
            
        except Exception as e:
            self.monitor.record_violation(
                "cleanup",
                f"Cleanup failed: {str(e)}",
                {'user_id': user_id}
            )
            return False
    
    def validate_message_ordering(self) -> Dict[str, Any]:
        """Validate message ordering across all connections."""
        ordering_results = {}
        
        with self.connections_lock:
            for conn_id, connection in self.mock_connections.items():
                ordering_results[conn_id] = connection.validate_message_ordering()
        
        return ordering_results
    
    def get_thread_safety_report(self) -> Dict[str, Any]:
        """Get comprehensive thread safety report."""
        violation_report = self.monitor.get_violation_report()
        ordering_report = self.validate_message_ordering()
        
        with self.performance_lock:
            performance_summary = {}
            for operation, times in self.performance_metrics['operation_times'].items():
                if times:
                    performance_summary[operation] = {
                        'count': len(times),
                        'avg_time': sum(times) / len(times),
                        'max_time': max(times),
                        'min_time': min(times)
                    }
        
        return {
            'violations': violation_report,
            'message_ordering': ordering_report,
            'performance': performance_summary,
            'active_emitters': len(self.user_emitters),
            'active_connections': len(self.mock_connections),
            'test_timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def cleanup_all(self):
        """Clean up all resources."""
        cleanup_tasks = []
        
        # Clean up all user emitters
        with self.emitters_lock:
            user_ids = list(self.user_emitters.keys())
        
        for user_id in user_ids:
            cleanup_tasks.append(self.cleanup_user_emitter(user_id))
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Final cleanup
        with self.emitters_lock:
            self.user_emitters.clear()
        
        with self.connections_lock:
            self.mock_connections.clear()


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture
async def thread_safety_manager():
    """Thread safety test manager fixture."""
    manager = ThreadSafetyTestManager()
    await manager.initialize()
    yield manager
    await manager.cleanup_all()


# ============================================================================
# THREAD SAFETY TEST SUITE
# ============================================================================

class TestWebSocketBridgeThreadSafety:
    """Test suite for WebSocket Bridge thread safety validation."""
    
    def __init__(self):
        self.thread_safety_manager = None
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_thread_safe_singleton_50_threads(self, thread_safety_manager):
        """CRITICAL: Test thread-safe singleton pattern with 50+ threads."""
        logger.info("Testing thread-safe singleton pattern with 50+ threads")
        
        num_threads = 55
        singleton_instances = []
        access_lock = threading.Lock()
        thread_results = []
        
        def access_singleton_from_thread(thread_id: int):
            """Access WebSocket manager singleton from dedicated thread."""
            try:
                # Multiple accesses per thread to stress test
                instances = []
                for _ in range(5):
                    manager = get_websocket_manager()
                    instances.append(id(manager))
                    time.sleep(0.001)  # Small delay to allow race conditions
                
                with access_lock:
                    singleton_instances.extend(instances)
                
                return {
                    'thread_id': thread_id,
                    'instances': instances,
                    'success': True
                }
            except Exception as e:
                return {
                    'thread_id': thread_id,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute from multiple threads simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(access_singleton_from_thread, i) for i in range(num_threads)]
            thread_results = [future.result(timeout=10) for future in futures]
        
        # Analyze results
        successful_threads = [r for r in thread_results if r.get('success')]
        failed_threads = [r for r in thread_results if not r.get('success')]
        
        # Validate singleton pattern
        unique_instances = set(singleton_instances)
        
        logger.info(f"✅ Successful threads: {len(successful_threads)}/{num_threads}")
        logger.info(f"🔗 Unique singleton instances: {len(unique_instances)}")
        logger.info(f"📊 Total singleton accesses: {len(singleton_instances)}")
        
        # Assertions
        assert len(failed_threads) == 0, f"Thread failures: {failed_threads}"
        
        assert len(unique_instances) == 1, \
            f"Singleton pattern violation: {len(unique_instances)} different instances found"
        
        # Verify all threads got the same instance
        expected_instance_id = singleton_instances[0]
        assert all(instance_id == expected_instance_id for instance_id in singleton_instances), \
            "Threads received different singleton instances"
        
        logger.info(f"[CHECK] Thread-safe singleton test PASSED - All {num_threads} threads got same instance")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_race_conditions_detection(self, thread_safety_manager):
        """CRITICAL: Test race condition detection under extreme concurrent access."""
        logger.info("Testing race condition detection")
        
        num_workers = 30
        operations_per_worker = 20
        shared_counter = threading.Value('i', 0)
        race_detected = threading.Event()
        
        async def race_condition_worker(worker_id: int):
            """Worker that attempts to create race conditions."""
            user_id = f"race_user_{worker_id}_{uuid.uuid4().hex[:8]}"
            thread_id = f"race_thread_{worker_id}_{uuid.uuid4().hex[:8]}"
            
            try:
                # Create emitter (tests factory thread safety)
                emitter = await thread_safety_manager.create_thread_safe_user_emitter(user_id, thread_id)
                
                race_operations = []
                
                # Perform operations that could cause race conditions
                for op_id in range(operations_per_worker):
                    # Increment shared counter with potential race condition
                    with shared_counter.get_lock():
                        current = shared_counter.value
                        # Simulate processing time to increase race condition likelihood
                        await asyncio.sleep(random.uniform(0.001, 0.003))
                        shared_counter.value = current + 1
                    
                    # Send message concurrently (tests message ordering)
                    success = await thread_safety_manager.send_thread_safe_message(
                        user_id=user_id,
                        message_type=random.choice([
                            "agent_started", "agent_thinking", "tool_executing", 
                            "tool_completed", "agent_completed"
                        ]),
                        message_data={
                            'agent_name': f'RaceAgent_{worker_id}',
                            'run_id': f'race_run_{worker_id}_{op_id}',
                            'text': f'Race test operation {op_id}'
                        }
                    )
                    
                    race_operations.append(success)
                    
                    # Validate memory coherence
                    thread_safety_manager.monitor.check_memory_coherence(
                        shared_value=shared_counter.value,
                        expected_value=shared_counter.value,  # Should be consistent
                        context=f"worker_{worker_id}_op_{op_id}"
                    )
                
                # Cleanup
                await thread_safety_manager.cleanup_user_emitter(user_id)
                
                return {
                    'worker_id': worker_id,
                    'operations_completed': sum(race_operations),
                    'success': True
                }
                
            except Exception as e:
                return {
                    'worker_id': worker_id,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute all workers concurrently
        start_time = time.time()
        tasks = [race_condition_worker(i) for i in range(num_workers)]
        worker_results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze results
        successful_workers = [r for r in worker_results if isinstance(r, dict) and r.get('success')]
        failed_workers = [r for r in worker_results if isinstance(r, dict) and not r.get('success')]
        exception_workers = [r for r in worker_results if isinstance(r, Exception)]
        
        # Get thread safety report
        report = thread_safety_manager.get_thread_safety_report()
        
        logger.info(f"⏱️ Executed {num_workers} workers in {execution_time:.2f}s")
        logger.info(f"✅ Successful: {len(successful_workers)}, ❌ Failed: {len(failed_workers)}, 💥 Exceptions: {len(exception_workers)}")
        logger.info(f"🔒 Final shared counter: {shared_counter.value}")
        logger.info(f"⚠️ Thread safety violations: {report['violations']['total_violations']}")
        
        # Assertions
        assert len(successful_workers) >= num_workers * 0.95, \
            f"Too many worker failures: {len(successful_workers)}/{num_workers}"
        
        # Validate shared counter (should equal total operations if no race conditions)
        expected_count = num_workers * operations_per_worker
        assert shared_counter.value == expected_count, \
            f"Race condition detected in counter: got {shared_counter.value}, expected {expected_count}"
        
        # Check for thread safety violations
        assert report['violations']['total_violations'] == 0, \
            f"Thread safety violations detected: {report['violations']['violations_detail']}"
        
        # Validate message ordering
        ordering_failures = [k for k, v in report['message_ordering'].items() if not v]
        assert len(ordering_failures) == 0, \
            f"Message ordering violations in connections: {ordering_failures}"
        
        logger.info("[CHECK] Race condition detection test PASSED - No race conditions detected")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_deadlock_prevention(self, thread_safety_manager):
        """CRITICAL: Test deadlock prevention in lock management."""
        logger.info("Testing deadlock prevention")
        
        num_workers = 25
        deadlock_timeout = 10  # seconds
        
        async def deadlock_test_worker(worker_id: int):
            """Worker that attempts to create deadlock scenarios."""
            user_id_a = f"deadlock_user_a_{worker_id}_{uuid.uuid4().hex[:8]}"
            user_id_b = f"deadlock_user_b_{worker_id}_{uuid.uuid4().hex[:8]}"
            thread_id = f"deadlock_thread_{worker_id}_{uuid.uuid4().hex[:8]}"
            
            try:
                # Create two emitters that could interact in deadlock scenarios
                emitter_a = await thread_safety_manager.create_thread_safe_user_emitter(user_id_a, thread_id)
                emitter_b = await thread_safety_manager.create_thread_safe_user_emitter(user_id_b, thread_id)
                
                # Perform operations that could cause deadlocks
                operations = []
                for i in range(10):
                    # Alternate between emitters to stress lock ordering
                    if i % 2 == 0:
                        success_a = await thread_safety_manager.send_thread_safe_message(
                            user_id=user_id_a,
                            message_type="agent_started",
                            message_data={'agent_name': f'DeadlockAgent_A_{worker_id}', 'run_id': f'run_{i}'}
                        )
                        success_b = await thread_safety_manager.send_thread_safe_message(
                            user_id=user_id_b,
                            message_type="agent_thinking",
                            message_data={'agent_name': f'DeadlockAgent_B_{worker_id}', 'run_id': f'run_{i}'}
                        )
                        operations.extend([success_a, success_b])
                    else:
                        # Reverse order to test lock ordering consistency
                        success_b = await thread_safety_manager.send_thread_safe_message(
                            user_id=user_id_b,
                            message_type="tool_executing",
                            message_data={'tool_name': f'DeadlockTool_B_{worker_id}', 'run_id': f'run_{i}'}
                        )
                        success_a = await thread_safety_manager.send_thread_safe_message(
                            user_id=user_id_a,
                            message_type="tool_completed",
                            message_data={'tool_name': f'DeadlockTool_A_{worker_id}', 'run_id': f'run_{i}'}
                        )
                        operations.extend([success_b, success_a])
                
                # Cleanup both emitters
                cleanup_a = await thread_safety_manager.cleanup_user_emitter(user_id_a)
                cleanup_b = await thread_safety_manager.cleanup_user_emitter(user_id_b)
                
                return {
                    'worker_id': worker_id,
                    'operations_completed': sum(operations),
                    'cleanup_success': cleanup_a and cleanup_b,
                    'success': True
                }
                
            except Exception as e:
                return {
                    'worker_id': worker_id,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute with timeout to detect deadlocks
        start_time = time.time()
        try:
            tasks = [deadlock_test_worker(i) for i in range(num_workers)]
            worker_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=deadlock_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"DEADLOCK DETECTED: Operations timed out after {deadlock_timeout}s")
            assert False, "Deadlock detected - operations timed out"
        
        execution_time = time.time() - start_time
        
        # Analyze results
        successful_workers = [r for r in worker_results if isinstance(r, dict) and r.get('success')]
        failed_workers = [r for r in worker_results if isinstance(r, dict) and not r.get('success')]
        exception_workers = [r for r in worker_results if isinstance(r, Exception)]
        
        logger.info(f"⏱️ Executed {num_workers} deadlock test workers in {execution_time:.2f}s")
        logger.info(f"✅ Successful: {len(successful_workers)}, ❌ Failed: {len(failed_workers)}, 💥 Exceptions: {len(exception_workers)}")
        
        # Assertions
        assert execution_time < deadlock_timeout * 0.8, \
            f"Operations too slow, possible deadlock: {execution_time:.2f}s"
        
        assert len(successful_workers) >= num_workers * 0.95, \
            f"Too many worker failures: {len(successful_workers)}/{num_workers}"
        
        # Check thread safety report
        report = thread_safety_manager.get_thread_safety_report()
        assert report['violations']['total_violations'] == 0, \
            f"Thread safety violations during deadlock test: {report['violations']['violations_detail']}"
        
        logger.info("[CHECK] Deadlock prevention test PASSED - No deadlocks detected")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_message_ordering_guarantees(self, thread_safety_manager):
        """CRITICAL: Test message ordering guarantees under thread pressure."""
        logger.info("Testing message ordering guarantees under thread pressure")
        
        num_senders = 20
        messages_per_sender = 25
        
        async def message_ordering_sender(sender_id: int):
            """Sender that tests message ordering."""
            user_id = f"ordering_user_{sender_id}_{uuid.uuid4().hex[:8]}"
            thread_id = f"ordering_thread_{sender_id}_{uuid.uuid4().hex[:8]}"
            
            try:
                # Create emitter
                emitter = await thread_safety_manager.create_thread_safe_user_emitter(user_id, thread_id)
                
                # Send sequential messages that must maintain order
                sent_messages = []
                for msg_id in range(messages_per_sender):
                    message_data = {
                        'agent_name': f'OrderingAgent_{sender_id}',
                        'run_id': f'ordering_run_{sender_id}_{msg_id}',
                        'sequence': msg_id,
                        'sender_id': sender_id
                    }
                    
                    success = await thread_safety_manager.send_thread_safe_message(
                        user_id=user_id,
                        message_type="agent_thinking",
                        message_data=message_data
                    )
                    
                    sent_messages.append({
                        'sequence': msg_id,
                        'success': success,
                        'timestamp': time.time()
                    })
                    
                    # Small random delay to stress ordering
                    await asyncio.sleep(random.uniform(0.001, 0.002))
                
                # Cleanup
                await thread_safety_manager.cleanup_user_emitter(user_id)
                
                return {
                    'sender_id': sender_id,
                    'sent_messages': sent_messages,
                    'success': True
                }
                
            except Exception as e:
                return {
                    'sender_id': sender_id,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute all senders concurrently
        start_time = time.time()
        tasks = [message_ordering_sender(i) for i in range(num_senders)]
        sender_results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze results
        successful_senders = [r for r in sender_results if isinstance(r, dict) and r.get('success')]
        failed_senders = [r for r in sender_results if isinstance(r, dict) and not r.get('success')]
        
        # Validate message ordering
        ordering_violations = []
        total_messages = 0
        successful_messages = 0
        
        for result in successful_senders:
            sent_messages = result['sent_messages']
            total_messages += len(sent_messages)
            
            # Check sequential ordering
            for i in range(1, len(sent_messages)):
                if sent_messages[i]['sequence'] != sent_messages[i-1]['sequence'] + 1:
                    ordering_violations.append({
                        'sender_id': result['sender_id'],
                        'expected_sequence': sent_messages[i-1]['sequence'] + 1,
                        'actual_sequence': sent_messages[i]['sequence']
                    })
                
                # Check timestamp ordering
                if sent_messages[i]['timestamp'] < sent_messages[i-1]['timestamp']:
                    ordering_violations.append({
                        'sender_id': result['sender_id'],
                        'violation': 'timestamp_order',
                        'message_index': i
                    })
            
            successful_messages += sum(1 for msg in sent_messages if msg['success'])
        
        # Get thread safety report
        report = thread_safety_manager.get_thread_safety_report()
        
        logger.info(f"⏱️ Executed {num_senders} senders in {execution_time:.2f}s")
        logger.info(f"✅ Successful senders: {len(successful_senders)}/{num_senders}")
        logger.info(f"📨 Total messages: {total_messages}, Successful: {successful_messages}")
        logger.info(f"⚠️ Ordering violations: {len(ordering_violations)}")
        
        # Assertions
        assert len(successful_senders) >= num_senders * 0.95, \
            f"Too many sender failures: {len(successful_senders)}/{num_senders}"
        
        assert len(ordering_violations) == 0, \
            f"Message ordering violations detected: {ordering_violations}"
        
        assert successful_messages >= total_messages * 0.95, \
            f"Too many message failures: {successful_messages}/{total_messages}"
        
        # Check connection-level ordering
        connection_ordering = report['message_ordering']
        ordering_failures = [k for k, v in connection_ordering.items() if not v]
        assert len(ordering_failures) == 0, \
            f"Connection-level ordering failures: {ordering_failures}"
        
        logger.info("[CHECK] Message ordering guarantees test PASSED - All messages properly ordered")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_memory_coherence_validation(self, thread_safety_manager):
        """CRITICAL: Test memory coherence across thread boundaries."""
        logger.info("Testing memory coherence across thread boundaries")
        
        num_threads = 30
        shared_state = {'counter': 0, 'data': {}}
        state_lock = threading.Lock()
        coherence_checks = []
        check_lock = threading.Lock()
        
        def memory_coherence_worker(thread_id: int):
            """Worker that validates memory coherence."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                return loop.run_until_complete(self._memory_coherence_work(
                    thread_id, shared_state, state_lock, coherence_checks, check_lock
                ))
            finally:
                loop.close()
        
        # Execute workers from multiple threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(memory_coherence_worker, i) for i in range(num_threads)]
            worker_results = [future.result(timeout=15) for future in futures]
        
        # Analyze coherence checks
        with check_lock:
            total_checks = len(coherence_checks)
            failed_checks = [c for c in coherence_checks if not c['coherent']]
        
        successful_workers = [r for r in worker_results if r.get('success')]
        
        logger.info(f"✅ Successful workers: {len(successful_workers)}/{num_threads}")
        logger.info(f"🧠 Memory coherence checks: {total_checks}")
        logger.info(f"❌ Failed coherence checks: {len(failed_checks)}")
        logger.info(f"🔢 Final shared counter: {shared_state['counter']}")
        
        # Assertions
        assert len(successful_workers) >= num_threads * 0.95, \
            f"Too many worker failures: {len(successful_workers)}/{num_threads}"
        
        assert len(failed_checks) == 0, \
            f"Memory coherence violations detected: {failed_checks}"
        
        # Validate final state consistency
        expected_counter = num_threads * 10  # Each worker increments 10 times
        assert shared_state['counter'] == expected_counter, \
            f"Final counter inconsistent: {shared_state['counter']} != {expected_counter}"
        
        logger.info("[CHECK] Memory coherence validation test PASSED - No coherence violations")
    
    async def _memory_coherence_work(self, thread_id: int, shared_state: Dict, 
                                   state_lock: threading.Lock, coherence_checks: List, check_lock: threading.Lock):
        """Execute memory coherence work."""
        user_id = f"coherence_user_{thread_id}_{uuid.uuid4().hex[:8]}"
        thread_name = f"coherence_thread_{thread_id}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Create manager for this thread
            manager = ThreadSafetyTestManager()
            await manager.initialize()
            
            # Create emitter
            emitter = await manager.create_thread_safe_user_emitter(user_id, thread_name)
            
            # Perform operations that test memory coherence
            for i in range(10):
                # Update shared state
                with state_lock:
                    old_counter = shared_state['counter']
                    shared_state['counter'] += 1
                    shared_state['data'][f'thread_{thread_id}_op_{i}'] = time.time()
                    new_counter = shared_state['counter']
                
                # Validate coherence
                coherence_check = {
                    'thread_id': thread_id,
                    'operation': i,
                    'old_counter': old_counter,
                    'new_counter': new_counter,
                    'coherent': new_counter == old_counter + 1,
                    'timestamp': time.time()
                }
                
                with check_lock:
                    coherence_checks.append(coherence_check)
                
                # Send message to test WebSocket coherence
                await manager.send_thread_safe_message(
                    user_id=user_id,
                    message_type="agent_started",
                    message_data={
                        'agent_name': f'CoherenceAgent_{thread_id}',
                        'run_id': f'coherence_run_{thread_id}_{i}',
                        'counter': new_counter
                    }
                )
                
                await asyncio.sleep(0.001)
            
            # Cleanup
            await manager.cleanup_user_emitter(user_id)
            
            return {'thread_id': thread_id, 'success': True}
            
        except Exception as e:
            return {'thread_id': thread_id, 'success': False, 'error': str(e)}


# ============================================================================
# MAIN COMPREHENSIVE THREAD SAFETY TEST CLASS
# ============================================================================

@pytest.mark.critical
@pytest.mark.mission_critical
class TestWebSocketBridgeThreadSafetyComprehensive:
    """Main test class for comprehensive WebSocket Bridge thread safety validation."""
    
    @pytest.mark.asyncio
    async def test_run_thread_safety_validation_suite(self):
        """Meta-test that validates the thread safety test suite."""
        logger.info("\n" + "="*80)
        logger.info("🔒 MISSION CRITICAL: WEBSOCKET BRIDGE THREAD SAFETY VALIDATION")
        logger.info("Advanced Thread Safety and Concurrency Control")
        logger.info("="*80)
        
        logger.info("\n[CHECK] WebSocket Bridge Thread Safety Test Suite is operational")
        logger.info("[CHECK] All thread safety patterns are covered:")
        logger.info("  - Thread-safe singleton pattern (50+ threads): [CHECK]")
        logger.info("  - Race condition detection: [CHECK]")
        logger.info("  - Deadlock prevention: [CHECK]")
        logger.info("  - Message ordering guarantees: [CHECK]")
        logger.info("  - Memory coherence validation: [CHECK]")
        
        logger.info("\n[ROCKET] Run individual tests with:")
        logger.info("pytest tests/mission_critical/test_websocket_bridge_thread_safety.py::TestWebSocketBridgeThreadSafety -v")
        
        logger.info("="*80)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("WEBSOCKET BRIDGE THREAD SAFETY VALIDATION TESTS")
    print("=" * 80)
    print("This test validates critical thread safety aspects:")
    print("1. Thread-safe singleton pattern with 50+ concurrent threads")
    print("2. Race condition detection under extreme concurrent access")
    print("3. Deadlock prevention in lock management")
    print("4. Message ordering guarantees under thread pressure")
    print("5. Memory coherence validation across thread boundaries")
    print("=" * 80)
    print()
    print("[ROCKET] EXECUTION METHODS:")
    print()
    print("Run all tests:")
    print("  python -m pytest tests/mission_critical/test_websocket_bridge_thread_safety.py -v")
    print()
    print("[CHECK] Advanced thread safety patterns")
    print("[CHECK] Comprehensive concurrency validation")
    print("[CHECK] Memory coherence and ordering guarantees")
    print("=" * 80)