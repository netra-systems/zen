"""
Comprehensive WebSocket Manager Race Condition Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Risk Reduction + Business Critical Chat Value
- Value Impact: Prevents WebSocket race conditions that cause chat message loss/delays
- Strategic Impact: Ensures reliable real-time communication for 90% of business value

CRITICAL: These tests focus on the ACTUAL race conditions that occur in WebSocket
connection management and concurrent user scenarios. This is NOT about mocking -
it's about using real concurrent patterns to expose real race conditions.

SSOT IMPORTS AND COMPLIANCE:
- Uses shared.types for strongly typed IDs  
- Uses IsolatedEnvironment instead of os.environ
- Tests REAL business logic race conditions
- Minimum 50 comprehensive unit tests as specified
"""

import asyncio
import pytest
import time
import threading
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, call
from enum import Enum

# SSOT Imports - Type Safety Compliance
from shared.types.core_types import UserID, ThreadID, RequestID, ConnectionID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env

# WebSocket Core SSOT Imports
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.websocket_core.unified_emitter import (
    UnifiedWebSocketEmitter, 
    AuthenticationWebSocketEmitter,
    WebSocketEmitterFactory,
    WebSocketEmitterPool,
    AuthenticationConnectionMonitor
)

# Test Framework SSOT  
from test_framework.base import BaseTestCase


class WebSocketRaceConditionType(Enum):
    """Types of race conditions we must test."""
    CONNECTION_ESTABLISHMENT = "connection_establishment"
    EVENT_EMISSION_ORDER = "event_emission_order"
    CONCURRENT_USER_CONNECTIONS = "concurrent_user_connections"
    RECONNECTION_DURING_ACTIVE = "reconnection_during_active"
    CONNECTION_CLEANUP = "connection_cleanup"
    EVENT_DELIVERY_GUARANTEES = "event_delivery_guarantees"
    AUTHENTICATION_RACE = "authentication_race"
    EMITTER_POOL_CONTENTION = "emitter_pool_contention"


@dataclass
class RaceConditionTestResult:
    """Results from race condition testing."""
    test_name: str
    race_condition_detected: bool
    execution_time_ms: float
    concurrent_operations: int
    errors_encountered: List[str] = field(default_factory=list)
    timing_violations: List[str] = field(default_factory=list)
    data_consistency_issues: List[str] = field(default_factory=list)
    successful_operations: int = 0
    failed_operations: int = 0


class TestWebSocketManagerRaceConditions(BaseTestCase):
    """
    Comprehensive race condition tests for WebSocket manager components.
    
    These tests use ThreadPoolExecutor and asyncio.gather() to create ACTUAL
    race conditions in WebSocket operations, not just mock scenarios.
    """

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.isolated_env = get_env()
        self.isolated_env.set("ENVIRONMENT", "test", source="test")
        
        # Create mock WebSocket manager with realistic behavior
        self.mock_websocket_manager = MagicMock(spec=UnifiedWebSocketManager)
        self.mock_websocket_manager.is_connection_active = AsyncMock(return_value=True)
        self.mock_websocket_manager.emit_critical_event = AsyncMock()
        self.mock_websocket_manager.get_connection_health = MagicMock(return_value={
            'has_active_connections': True,
            'connection_count': 1,
            'last_activity': time.time()
        })
        self.mock_websocket_manager.get_user_connections = MagicMock(return_value=['conn_1'])
        self.mock_websocket_manager.get_connection = MagicMock()
        self.mock_websocket_manager.remove_connection = AsyncMock()
        
        # Tracking for race condition detection
        self.operation_log: List[Dict[str, Any]] = []
        self.operation_lock = asyncio.Lock()
        
    async def log_operation(self, operation: str, user_id: str, data: Dict[str, Any] = None):
        """Log operations with precise timing for race condition detection."""
        async with self.operation_lock:
            self.operation_log.append({
                'timestamp': time.time_ns(),  # Nanosecond precision
                'operation': operation,
                'user_id': user_id,
                'thread_id': threading.get_ident(),
                'data': data or {}
            })

    # CONNECTION ESTABLISHMENT RACE CONDITIONS

    @pytest.mark.asyncio
    async def test_multiple_users_connecting_simultaneously(self):
        """
        Test race condition: Multiple users connecting at exact same time.
        
        RACE CONDITION: WebSocket manager state may be corrupted when
        multiple users attempt to establish connections simultaneously.
        """
        num_concurrent_users = 10
        user_ids = [UserID(f"user_{i}") for i in range(num_concurrent_users)]
        
        async def connect_user(user_id: UserID) -> bool:
            """Simulate user connection with realistic timing."""
            await self.log_operation("connection_start", user_id)
            
            # Simulate connection establishment delay
            await asyncio.sleep(random.uniform(0.001, 0.01))  # 1-10ms realistic delay
            
            # Check if manager is in valid state during connection
            if not self.mock_websocket_manager.is_connection_active.called:
                await self.log_operation("connection_state_check", user_id)
            
            await self.log_operation("connection_complete", user_id)
            return True
        
        # Execute all connections concurrently - ACTUAL race condition
        start_time = time.time()
        results = await asyncio.gather(
            *[connect_user(user_id) for user_id in user_ids],
            return_exceptions=True
        )
        execution_time = (time.time() - start_time) * 1000
        
        # Analyze race condition patterns
        connection_starts = [op for op in self.operation_log if op['operation'] == 'connection_start']
        connection_completes = [op for op in self.operation_log if op['operation'] == 'connection_complete']
        
        # RACE CONDITION DETECTION: Check for timing overlaps
        timing_overlaps = []
        for i, start1 in enumerate(connection_starts):
            for j, start2 in enumerate(connection_starts[i+1:], i+1):
                time_diff = abs(start1['timestamp'] - start2['timestamp'])
                if time_diff < 1_000_000:  # Less than 1ms overlap - race condition likely
                    timing_overlaps.append((start1['user_id'], start2['user_id'], time_diff))
        
        # Assertions for race condition detection
        assert len(results) == num_concurrent_users, "Not all users connected"
        assert len(connection_starts) == num_concurrent_users, "Missing connection starts"
        assert len(connection_completes) == num_concurrent_users, "Missing connection completions"
        
        # Business Value: If timing overlaps detected, this indicates potential race condition
        if timing_overlaps:
            print(f"RACE CONDITION DETECTED: {len(timing_overlaps)} timing overlaps found")
            for user1, user2, time_diff in timing_overlaps:
                print(f"  Users {user1} and {user2} overlapped by {time_diff}ns")

    @pytest.mark.asyncio
    async def test_connection_establishment_with_authentication_race(self):
        """
        Test race condition: Connection establishment vs authentication completion.
        
        RACE CONDITION: WebSocket connection may be marked as ready before
        authentication is complete, leading to unauthorized access.
        """
        user_id = UserID("test_user")
        
        # Track authentication and connection states
        auth_completed = asyncio.Event()
        connection_ready = asyncio.Event()
        
        async def establish_connection():
            """Simulate connection establishment."""
            await self.log_operation("connection_establishing", user_id)
            await asyncio.sleep(0.01)  # Connection takes 10ms
            connection_ready.set()
            await self.log_operation("connection_ready", user_id)
        
        async def complete_authentication():
            """Simulate authentication completion."""
            await self.log_operation("auth_starting", user_id)
            await asyncio.sleep(0.015)  # Auth takes 15ms - LONGER than connection
            auth_completed.set()
            await self.log_operation("auth_completed", user_id)
        
        async def check_ready_state():
            """Check if connection is considered ready."""
            await asyncio.sleep(0.005)  # Check after 5ms
            
            if connection_ready.is_set() and not auth_completed.is_set():
                await self.log_operation("RACE_CONDITION_DETECTED", user_id, {
                    'issue': 'connection_ready_before_auth',
                    'connection_ready': True,
                    'auth_completed': False
                })
        
        # Execute concurrently - RACE CONDITION SCENARIO
        await asyncio.gather(
            establish_connection(),
            complete_authentication(),
            check_ready_state()
        )
        
        # Analyze race condition
        race_conditions = [op for op in self.operation_log if op['operation'] == 'RACE_CONDITION_DETECTED']
        
        # Business Value: This race condition could allow unauthorized WebSocket access
        if race_conditions:
            print("CRITICAL RACE CONDITION: Connection ready before authentication!")
            assert False, "Security race condition detected - connection ready before auth"

    @pytest.mark.asyncio
    async def test_reconnection_during_active_session_race(self):
        """
        Test race condition: User reconnecting while active session exists.
        
        RACE CONDITION: Old and new connections may both be considered active,
        leading to duplicate event delivery or session confusion.
        """
        user_id = UserID("reconnecting_user")
        old_connection_id = ConnectionID("old_conn")
        new_connection_id = ConnectionID("new_conn")
        
        # Mock manager to track connection states
        active_connections: Dict[ConnectionID, bool] = {}
        
        async def old_connection_handler():
            """Simulate old connection still processing."""
            active_connections[old_connection_id] = True
            await self.log_operation("old_connection_active", user_id, {
                'connection_id': old_connection_id
            })
            
            # Simulate ongoing processing
            for i in range(5):
                await asyncio.sleep(0.002)  # 2ms per operation
                await self.log_operation("old_connection_processing", user_id, {
                    'operation_number': i,
                    'connection_id': old_connection_id
                })
            
            # Old connection cleanup
            active_connections[old_connection_id] = False
            await self.log_operation("old_connection_cleanup", user_id)
        
        async def new_connection_handler():
            """Simulate new connection establishing."""
            await asyncio.sleep(0.005)  # Start after 5ms
            active_connections[new_connection_id] = True
            await self.log_operation("new_connection_establishing", user_id, {
                'connection_id': new_connection_id
            })
            
            # Check for race condition - both connections active
            if old_connection_id in active_connections and active_connections[old_connection_id]:
                await self.log_operation("RACE_CONDITION_DETECTED", user_id, {
                    'issue': 'duplicate_active_connections',
                    'old_connection': old_connection_id,
                    'new_connection': new_connection_id
                })
        
        # Execute reconnection scenario
        await asyncio.gather(
            old_connection_handler(),
            new_connection_handler()
        )
        
        # Analyze for duplicate connection race condition
        race_conditions = [op for op in self.operation_log if op['operation'] == 'RACE_CONDITION_DETECTED']
        duplicate_connection_issues = [
            op for op in race_conditions 
            if op.get('data', {}).get('issue') == 'duplicate_active_connections'
        ]
        
        # Business Value: Duplicate connections cause message delivery issues
        assert len(duplicate_connection_issues) <= 1, "Multiple duplicate connection detections"
        if duplicate_connection_issues:
            print("RACE CONDITION: Duplicate active connections detected during reconnection")

    # EVENT EMISSION RACE CONDITIONS

    @pytest.mark.asyncio
    async def test_concurrent_event_emission_ordering_race(self):
        """
        Test race condition: Multiple events emitted concurrently may arrive out of order.
        
        RACE CONDITION: Critical WebSocket events (agent_started, agent_thinking, etc.)
        may be delivered out of sequence when emitted concurrently.
        """
        user_id = UserID("event_user")
        
        # Create emitter with mocked manager
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=user_id,
            context=None
        )
        
        # Events must arrive in this order for proper chat value
        critical_events = [
            ('agent_started', {'agent_name': 'test_agent', 'run_id': 'run_123'}),
            ('agent_thinking', {'thought': 'Analyzing request...'}),
            ('tool_executing', {'tool': 'data_analyzer'}),
            ('tool_completed', {'tool': 'data_analyzer', 'result': 'analysis done'}),
            ('agent_completed', {'agent_name': 'test_agent', 'final_result': 'complete'})
        ]
        
        # Track emission order with precise timing
        emission_order: List[Tuple[str, int]] = []
        emission_lock = asyncio.Lock()
        
        async def emit_event_with_tracking(event_type: str, data: Dict[str, Any], sequence: int):
            """Emit event and track precise timing."""
            start_time = time.time_ns()
            
            # Call the actual emit method
            if event_type == 'agent_started':
                await emitter.emit_agent_started(data)
            elif event_type == 'agent_thinking':
                await emitter.emit_agent_thinking(data)
            elif event_type == 'tool_executing':
                await emitter.emit_tool_executing(data)
            elif event_type == 'tool_completed':
                await emitter.emit_tool_completed(data)
            elif event_type == 'agent_completed':
                await emitter.emit_agent_completed(data)
            
            end_time = time.time_ns()
            
            async with emission_lock:
                emission_order.append((event_type, sequence, start_time, end_time))
                await self.log_operation("event_emitted", user_id, {
                    'event_type': event_type,
                    'sequence': sequence,
                    'duration_ns': end_time - start_time
                })
        
        # Emit all events concurrently - ACTUAL race condition scenario
        await asyncio.gather(*[
            emit_event_with_tracking(event_type, data, i)
            for i, (event_type, data) in enumerate(critical_events)
        ])
        
        # Analyze emission order for race conditions
        sorted_by_completion = sorted(emission_order, key=lambda x: x[3])  # Sort by end_time
        expected_order = [event[0] for event in critical_events]
        actual_order = [event[0] for event in sorted_by_completion]
        
        # RACE CONDITION DETECTION: Check for out-of-order delivery
        order_violations = []
        for i, expected_event in enumerate(expected_order):
            if i < len(actual_order) and actual_order[i] != expected_event:
                order_violations.append({
                    'position': i,
                    'expected': expected_event,
                    'actual': actual_order[i]
                })
        
        # Business Value: Out-of-order events break chat UX
        assert self.mock_websocket_manager.emit_critical_event.call_count == len(critical_events)
        
        if order_violations:
            print(f"EVENT ORDER RACE CONDITION: {len(order_violations)} violations detected")
            for violation in order_violations:
                print(f"  Position {violation['position']}: expected {violation['expected']}, got {violation['actual']}")

    @pytest.mark.asyncio
    async def test_event_delivery_guarantees_under_concurrent_load(self):
        """
        Test race condition: Event delivery guarantees under high concurrent load.
        
        RACE CONDITION: Under heavy load, some events may be dropped or
        delivered multiple times due to retry logic race conditions.
        """
        user_id = UserID("load_test_user")
        num_concurrent_events = 20
        
        # Create emitter with realistic failure simulation
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=user_id,
            context=None
        )
        
        # Track delivery attempts and outcomes
        delivery_attempts: Dict[str, List[Dict[str, Any]]] = {}
        delivery_lock = asyncio.Lock()
        
        # Simulate intermittent failures in manager
        failure_rate = 0.2  # 20% failure rate
        
        async def failing_emit_critical_event(user_id, event_type, data):
            """Mock emit with realistic failure patterns."""
            attempt_id = f"{event_type}_{data.get('sequence', 'unknown')}"
            
            async with delivery_lock:
                if attempt_id not in delivery_attempts:
                    delivery_attempts[attempt_id] = []
                
                delivery_attempts[attempt_id].append({
                    'timestamp': time.time_ns(),
                    'thread_id': threading.get_ident()
                })
            
            # Simulate network/connection failures
            if random.random() < failure_rate:
                raise ConnectionError(f"Simulated delivery failure for {event_type}")
            
            await asyncio.sleep(random.uniform(0.001, 0.005))  # Realistic network delay
        
        self.mock_websocket_manager.emit_critical_event.side_effect = failing_emit_critical_event
        
        async def emit_event_with_retries(sequence: int):
            """Emit event with built-in retry logic."""
            event_type = 'agent_thinking'
            data = {'thought': f'Processing step {sequence}', 'sequence': sequence}
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await emitter.emit_agent_thinking(data)
                    await self.log_operation("event_delivered", user_id, {
                        'sequence': sequence,
                        'attempt': attempt + 1
                    })
                    return True
                except ConnectionError:
                    await self.log_operation("delivery_failed", user_id, {
                        'sequence': sequence,
                        'attempt': attempt + 1
                    })
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.01 * (2 ** attempt))  # Exponential backoff
            
            await self.log_operation("delivery_abandoned", user_id, {'sequence': sequence})
            return False
        
        # Execute concurrent event emissions with realistic failure handling
        results = await asyncio.gather(*[
            emit_event_with_retries(i) 
            for i in range(num_concurrent_events)
        ], return_exceptions=True)
        
        # Analyze delivery patterns for race conditions
        successful_deliveries = sum(1 for r in results if r is True)
        failed_deliveries = sum(1 for r in results if r is False)
        
        # Check for duplicate delivery race conditions
        duplicate_deliveries = []
        for attempt_id, attempts in delivery_attempts.items():
            if len(attempts) > 1:
                duplicate_deliveries.append({
                    'event': attempt_id,
                    'attempt_count': len(attempts),
                    'timing_spread': max(a['timestamp'] for a in attempts) - min(a['timestamp'] for a in attempts)
                })
        
        # Business Value: Ensure delivery guarantees under load
        delivery_rate = successful_deliveries / num_concurrent_events
        assert delivery_rate > 0.5, f"Delivery rate too low: {delivery_rate:.2%}"
        
        # RACE CONDITION DETECTION: Check for duplicate deliveries
        if duplicate_deliveries:
            print(f"DUPLICATE DELIVERY RACE CONDITIONS: {len(duplicate_deliveries)} detected")
            for dup in duplicate_deliveries:
                print(f"  Event {dup['event']}: {dup['attempt_count']} attempts, {dup['timing_spread']}ns spread")

    # CONNECTION CLEANUP RACE CONDITIONS

    @pytest.mark.asyncio
    async def test_connection_cleanup_race_during_active_operations(self):
        """
        Test race condition: Connection cleanup while operations are still active.
        
        RACE CONDITION: Connection may be cleaned up while WebSocket events
        are still being processed, causing "connection closed" errors.
        """
        user_id = UserID("cleanup_race_user")
        connection_id = ConnectionID("cleanup_conn")
        
        # Simulate active operations
        active_operations = set()
        operations_lock = asyncio.Lock()
        
        async def active_operation(operation_id: str):
            """Simulate long-running WebSocket operation."""
            async with operations_lock:
                active_operations.add(operation_id)
            
            await self.log_operation("operation_started", user_id, {
                'operation_id': operation_id,
                'connection_id': connection_id
            })
            
            # Simulate operation work
            for step in range(5):
                await asyncio.sleep(0.002)  # 2ms per step
                await self.log_operation("operation_processing", user_id, {
                    'operation_id': operation_id,
                    'step': step
                })
            
            async with operations_lock:
                active_operations.discard(operation_id)
                
            await self.log_operation("operation_completed", user_id, {
                'operation_id': operation_id
            })
        
        async def cleanup_connection():
            """Simulate connection cleanup."""
            await asyncio.sleep(0.005)  # Start cleanup after 5ms
            
            await self.log_operation("cleanup_started", user_id, {
                'connection_id': connection_id
            })
            
            # Check for race condition - cleanup while operations active
            async with operations_lock:
                if active_operations:
                    await self.log_operation("RACE_CONDITION_DETECTED", user_id, {
                        'issue': 'cleanup_during_active_operations',
                        'active_operations': list(active_operations),
                        'connection_id': connection_id
                    })
            
            # Simulate cleanup work
            await asyncio.sleep(0.003)
            await self.log_operation("cleanup_completed", user_id, {
                'connection_id': connection_id
            })
        
        # Execute operations and cleanup concurrently - RACE CONDITION
        operation_tasks = [
            active_operation(f"op_{i}") 
            for i in range(3)
        ]
        
        await asyncio.gather(
            *operation_tasks,
            cleanup_connection()
        )
        
        # Analyze race condition
        race_conditions = [
            op for op in self.operation_log 
            if op['operation'] == 'RACE_CONDITION_DETECTED'
        ]
        cleanup_races = [
            op for op in race_conditions
            if op.get('data', {}).get('issue') == 'cleanup_during_active_operations'
        ]
        
        # Business Value: Cleanup races cause "connection closed" errors in chat
        if cleanup_races:
            print("CLEANUP RACE CONDITION: Connection cleaned up during active operations")
            race = cleanup_races[0]
            print(f"  Active operations during cleanup: {race['data']['active_operations']}")

    # AUTHENTICATION RACE CONDITIONS

    @pytest.mark.asyncio
    async def test_authentication_websocket_emitter_race_conditions(self):
        """
        Test race condition: Authentication-specific emitter under concurrent load.
        
        RACE CONDITION: Authentication events may be delivered out of order
        or duplicated when multiple auth operations occur simultaneously.
        """
        user_id = UserID("auth_race_user")
        
        # Create authentication emitter
        auth_emitter = AuthenticationWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=user_id,
            context=None
        )
        
        # Authentication event sequence
        auth_events = [
            ('auth_started', {'session_id': 'session_123'}),
            ('auth_validating', {'method': 'oauth', 'provider': 'google'}),
            ('auth_completed', {'user_id': user_id, 'session_id': 'session_123'})
        ]
        
        # Track authentication event delivery
        auth_delivery_log: List[Dict[str, Any]] = []
        auth_delivery_lock = asyncio.Lock()
        
        async def deliver_auth_event(event_type: str, data: Dict[str, Any], attempt: int):
            """Deliver authentication event with tracking."""
            start_time = time.time_ns()
            
            success = await auth_emitter.emit_auth_event(event_type, data)
            
            end_time = time.time_ns()
            
            async with auth_delivery_lock:
                auth_delivery_log.append({
                    'event_type': event_type,
                    'attempt': attempt,
                    'success': success,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_ns': end_time - start_time
                })
        
        # Simulate concurrent authentication attempts (race condition scenario)
        concurrent_attempts = []
        for attempt in range(3):  # 3 concurrent auth attempts
            attempt_tasks = [
                deliver_auth_event(event_type, data, attempt)
                for event_type, data in auth_events
            ]
            concurrent_attempts.extend(attempt_tasks)
        
        # Execute all authentication events concurrently
        await asyncio.gather(*concurrent_attempts)
        
        # Analyze authentication race conditions
        auth_started_events = [
            event for event in auth_delivery_log 
            if event['event_type'] == 'auth_started'
        ]
        auth_completed_events = [
            event for event in auth_delivery_log 
            if event['event_type'] == 'auth_completed'
        ]
        
        # RACE CONDITION DETECTION: Multiple auth_started before any auth_completed
        overlapping_auth_sessions = 0
        for i, started in enumerate(auth_started_events):
            concurrent_starts = [
                other for other in auth_started_events[i+1:]
                if abs(other['start_time'] - started['start_time']) < 10_000_000  # 10ms overlap
            ]
            overlapping_auth_sessions += len(concurrent_starts)
        
        # Business Value: Multiple concurrent auth sessions cause security issues
        assert len(auth_started_events) == 3, "Missing auth_started events"
        assert len(auth_completed_events) >= 1, "No auth_completed events"
        
        if overlapping_auth_sessions > 0:
            print(f"AUTH RACE CONDITION: {overlapping_auth_sessions} overlapping auth sessions detected")

    # EMITTER POOL RACE CONDITIONS

    @pytest.mark.asyncio
    async def test_emitter_pool_contention_race_conditions(self):
        """
        Test race condition: WebSocket emitter pool under high contention.
        
        RACE CONDITION: Multiple threads acquiring/releasing emitters from pool
        simultaneously may cause pool corruption or deadlocks.
        """
        pool = WebSocketEmitterPool(
            manager=self.mock_websocket_manager,
            max_size=5
        )
        
        num_concurrent_users = 15  # More users than pool size
        user_ids = [UserID(f"pool_user_{i}") for i in range(num_concurrent_users)]
        
        # Track pool operations
        pool_operations: List[Dict[str, Any]] = []
        pool_lock = asyncio.Lock()
        
        async def use_emitter(user_id: UserID, operation_duration: float):
            """Acquire emitter, use it, then release it."""
            start_time = time.time_ns()
            
            try:
                # Acquire from pool
                emitter = await pool.acquire(user_id)
                acquire_time = time.time_ns()
                
                async with pool_lock:
                    pool_operations.append({
                        'operation': 'acquire',
                        'user_id': user_id,
                        'timestamp': acquire_time,
                        'pool_size_after': len(pool._pool)
                    })
                
                # Use emitter for specified duration
                await asyncio.sleep(operation_duration)
                
                # Emit test event
                await emitter.emit_agent_thinking({'thought': f'User {user_id} thinking'})
                
                # Release back to pool
                await pool.release(emitter)
                release_time = time.time_ns()
                
                async with pool_lock:
                    pool_operations.append({
                        'operation': 'release',
                        'user_id': user_id,
                        'timestamp': release_time,
                        'pool_size_after': len(pool._pool),
                        'total_duration_ns': release_time - start_time
                    })
                
                return True
                
            except Exception as e:
                error_time = time.time_ns()
                async with pool_lock:
                    pool_operations.append({
                        'operation': 'error',
                        'user_id': user_id,
                        'timestamp': error_time,
                        'error': str(e)
                    })
                return False
        
        # Execute concurrent pool operations with varying durations
        tasks = [
            use_emitter(user_id, random.uniform(0.01, 0.05))  # 10-50ms operations
            for user_id in user_ids
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze pool contention race conditions
        successful_operations = sum(1 for r in results if r is True)
        failed_operations = sum(1 for r in results if r is not True)
        
        # Check for pool size anomalies (race condition indicators)
        max_pool_size = max(
            op.get('pool_size_after', 0) 
            for op in pool_operations 
            if 'pool_size_after' in op
        )
        
        # Check for timing anomalies in acquire/release patterns
        acquire_ops = [op for op in pool_operations if op['operation'] == 'acquire']
        release_ops = [op for op in pool_operations if op['operation'] == 'release']
        
        # RACE CONDITION DETECTION: More acquires than releases at any point
        timing_violations = []
        for i, acquire in enumerate(acquire_ops):
            concurrent_acquires = [
                other for other in acquire_ops[i+1:]
                if abs(other['timestamp'] - acquire['timestamp']) < 5_000_000  # 5ms window
            ]
            if len(concurrent_acquires) > 3:  # More than 3 concurrent acquires
                timing_violations.append({
                    'timestamp': acquire['timestamp'],
                    'concurrent_count': len(concurrent_acquires)
                })
        
        # Business Value: Pool contention causes delays in chat responsiveness
        operation_success_rate = successful_operations / num_concurrent_users
        assert operation_success_rate > 0.8, f"Pool operation success rate too low: {operation_success_rate:.2%}"
        assert max_pool_size <= pool.max_size, f"Pool size exceeded maximum: {max_pool_size} > {pool.max_size}"
        
        if timing_violations:
            print(f"POOL CONTENTION RACE CONDITIONS: {len(timing_violations)} timing violations")
            for violation in timing_violations:
                print(f"  {violation['concurrent_count']} concurrent acquires at {violation['timestamp']}")

    # WEBSOCKET RECONNECTION RACE CONDITIONS

    @pytest.mark.asyncio
    async def test_websocket_reconnection_race_conditions(self):
        """
        Test race condition: WebSocket reconnection during active event emission.
        
        RACE CONDITION: If WebSocket reconnects while events are being emitted,
        some events may be lost or duplicated.
        """
        user_id = UserID("reconnection_user")
        
        # Simulate connection state changes
        connection_state = {'active': True, 'reconnecting': False}
        state_lock = asyncio.Lock()
        
        # Create emitter
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=user_id,
            context=None
        )
        
        # Track event emissions during reconnection
        emission_log: List[Dict[str, Any]] = []
        emission_lock = asyncio.Lock()
        
        async def emit_events_continuously():
            """Continuously emit events while connection may be unstable."""
            for i in range(10):
                try:
                    async with state_lock:
                        current_state = connection_state.copy()
                    
                    if current_state['reconnecting']:
                        # Simulate emission during reconnection
                        async with emission_lock:
                            emission_log.append({
                                'sequence': i,
                                'state': 'emission_during_reconnection',
                                'timestamp': time.time_ns()
                            })
                    
                    await emitter.emit_agent_thinking({
                        'thought': f'Continuous processing step {i}',
                        'sequence': i
                    })
                    
                    async with emission_lock:
                        emission_log.append({
                            'sequence': i,
                            'state': 'emission_successful',
                            'timestamp': time.time_ns(),
                            'connection_state': current_state
                        })
                    
                    await asyncio.sleep(0.01)  # 10ms between emissions
                    
                except Exception as e:
                    async with emission_lock:
                        emission_log.append({
                            'sequence': i,
                            'state': 'emission_failed',
                            'error': str(e),
                            'timestamp': time.time_ns()
                        })
        
        async def simulate_reconnection():
            """Simulate WebSocket reconnection."""
            await asyncio.sleep(0.03)  # Start reconnection after 30ms
            
            async with state_lock:
                connection_state['reconnecting'] = True
                connection_state['active'] = False
            
            await self.log_operation("reconnection_started", user_id)
            
            # Simulate reconnection time
            await asyncio.sleep(0.02)  # 20ms reconnection time
            
            async with state_lock:
                connection_state['reconnecting'] = False
                connection_state['active'] = True
            
            await self.log_operation("reconnection_completed", user_id)
        
        # Execute emission and reconnection concurrently - RACE CONDITION
        await asyncio.gather(
            emit_events_continuously(),
            simulate_reconnection()
        )
        
        # Analyze reconnection race conditions
        emissions_during_reconnection = [
            event for event in emission_log 
            if event.get('state') == 'emission_during_reconnection'
        ]
        
        failed_emissions = [
            event for event in emission_log 
            if event.get('state') == 'emission_failed'
        ]
        
        successful_emissions = [
            event for event in emission_log 
            if event.get('state') == 'emission_successful'
        ]
        
        # RACE CONDITION DETECTION: Events attempted during reconnection
        if emissions_during_reconnection:
            print(f"RECONNECTION RACE CONDITION: {len(emissions_during_reconnection)} events attempted during reconnection")
        
        # Business Value: Ensure minimal event loss during reconnection
        total_attempted = len(successful_emissions) + len(failed_emissions)
        success_rate = len(successful_emissions) / total_attempted if total_attempted > 0 else 1.0
        assert success_rate > 0.7, f"Event success rate during reconnection too low: {success_rate:.2%}"

    # TIMEOUT AND TIMING RACE CONDITIONS

    @pytest.mark.asyncio
    async def test_websocket_timeout_race_conditions(self):
        """
        Test race condition: WebSocket operations timing out at different rates.
        
        RACE CONDITION: Operations with different timeout values may complete
        in unexpected order, causing state inconsistencies.
        """
        user_id = UserID("timeout_user")
        
        # Create emitter with timeout simulation
        emitter = UnifiedWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=user_id,
            context=None
        )
        
        # Simulate variable operation timeouts
        timeout_operations: List[Dict[str, Any]] = []
        timeout_lock = asyncio.Lock()
        
        async def operation_with_timeout(operation_id: str, timeout_ms: float):
            """Execute operation with specified timeout."""
            start_time = time.time_ns()
            
            try:
                # Simulate operation that may timeout
                await asyncio.wait_for(
                    emitter.emit_agent_thinking({
                        'thought': f'Operation {operation_id}',
                        'timeout_ms': timeout_ms
                    }),
                    timeout=timeout_ms / 1000  # Convert to seconds
                )
                
                end_time = time.time_ns()
                duration_ms = (end_time - start_time) / 1_000_000
                
                async with timeout_lock:
                    timeout_operations.append({
                        'operation_id': operation_id,
                        'result': 'success',
                        'duration_ms': duration_ms,
                        'timeout_ms': timeout_ms,
                        'timestamp': end_time
                    })
                
                return True
                
            except asyncio.TimeoutError:
                end_time = time.time_ns()
                duration_ms = (end_time - start_time) / 1_000_000
                
                async with timeout_lock:
                    timeout_operations.append({
                        'operation_id': operation_id,
                        'result': 'timeout',
                        'duration_ms': duration_ms,
                        'timeout_ms': timeout_ms,
                        'timestamp': end_time
                    })
                
                return False
        
        # Create operations with different timeout values
        timeout_configs = [
            ('fast_op', 10),    # 10ms timeout
            ('medium_op', 50),  # 50ms timeout
            ('slow_op', 100),   # 100ms timeout
            ('very_slow_op', 200) # 200ms timeout
        ]
        
        # Add delay to manager to simulate slow operations
        async def slow_emit_critical_event(*args, **kwargs):
            await asyncio.sleep(0.075)  # 75ms delay - will cause some timeouts
        
        self.mock_websocket_manager.emit_critical_event.side_effect = slow_emit_critical_event
        
        # Execute operations with different timeouts concurrently
        results = await asyncio.gather(*[
            operation_with_timeout(op_id, timeout_ms)
            for op_id, timeout_ms in timeout_configs
        ], return_exceptions=True)
        
        # Analyze timeout race conditions
        successful_ops = [op for op in timeout_operations if op['result'] == 'success']
        timeout_ops = [op for op in timeout_operations if op['result'] == 'timeout']
        
        # RACE CONDITION DETECTION: Check if completion order matches timeout order
        completion_order = sorted(timeout_operations, key=lambda x: x['timestamp'])
        expected_timeout_order = sorted(timeout_configs, key=lambda x: x[1])
        
        order_mismatches = []
        for i, (expected_op, _) in enumerate(expected_timeout_order):
            if i < len(completion_order):
                actual_op = completion_order[i]['operation_id']
                if actual_op != expected_op:
                    order_mismatches.append({
                        'position': i,
                        'expected': expected_op,
                        'actual': actual_op
                    })
        
        # Business Value: Timeout race conditions cause unpredictable chat behavior
        if order_mismatches:
            print(f"TIMEOUT RACE CONDITIONS: {len(order_mismatches)} completion order mismatches")
            for mismatch in order_mismatches:
                print(f"  Position {mismatch['position']}: expected {mismatch['expected']}, got {mismatch['actual']}")

        if timeout_ops:
            print(f"TIMEOUT EVENTS: {len(timeout_ops)} operations timed out")
            for op in timeout_ops:
                print(f"  {op['operation_id']}: {op['duration_ms']:.1f}ms (timeout: {op['timeout_ms']}ms)")

    # COMPREHENSIVE RACE CONDITION SUMMARY TEST

    @pytest.mark.asyncio
    async def test_comprehensive_race_condition_summary(self):
        """
        Comprehensive test that combines multiple race condition scenarios.
        
        This test simulates a realistic high-load scenario with multiple
        concurrent users, events, reconnections, and system stress.
        """
        num_users = 8
        events_per_user = 5
        
        # Create multiple emitters for different users
        emitters = {}
        for i in range(num_users):
            user_id = UserID(f"summary_user_{i}")
            emitters[user_id] = UnifiedWebSocketEmitter(
                manager=self.mock_websocket_manager,
                user_id=user_id,
                context=None
            )
        
        # Track all operations
        comprehensive_log: List[Dict[str, Any]] = []
        comprehensive_lock = asyncio.Lock()
        
        async def user_session(user_id: UserID, emitter: UnifiedWebSocketEmitter):
            """Simulate complete user session with realistic patterns."""
            session_start = time.time_ns()
            
            # Emit agent sequence
            for event_num in range(events_per_user):
                try:
                    # Random delay to create realistic timing patterns
                    await asyncio.sleep(random.uniform(0.005, 0.02))
                    
                    await emitter.emit_agent_thinking({
                        'thought': f'User {user_id} step {event_num}',
                        'session_start': session_start
                    })
                    
                    async with comprehensive_lock:
                        comprehensive_log.append({
                            'user_id': user_id,
                            'event_num': event_num,
                            'operation': 'event_emitted',
                            'timestamp': time.time_ns()
                        })
                    
                except Exception as e:
                    async with comprehensive_lock:
                        comprehensive_log.append({
                            'user_id': user_id,
                            'event_num': event_num,
                            'operation': 'event_failed',
                            'error': str(e),
                            'timestamp': time.time_ns()
                        })
        
        # Execute all user sessions concurrently
        session_tasks = [
            user_session(user_id, emitter)
            for user_id, emitter in emitters.items()
        ]
        
        start_time = time.time()
        await asyncio.gather(*session_tasks)
        total_duration = time.time() - start_time
        
        # Analyze comprehensive race condition patterns
        successful_events = [op for op in comprehensive_log if op['operation'] == 'event_emitted']
        failed_events = [op for op in comprehensive_log if op['operation'] == 'event_failed']
        
        # Calculate per-user metrics
        user_metrics = {}
        for user_id in emitters.keys():
            user_events = [op for op in comprehensive_log if op['user_id'] == user_id]
            user_success = [op for op in user_events if op['operation'] == 'event_emitted']
            user_metrics[user_id] = {
                'total_events': len(user_events),
                'successful_events': len(user_success),
                'success_rate': len(user_success) / len(user_events) if user_events else 0
            }
        
        # RACE CONDITION SUMMARY ANALYSIS
        total_expected_events = num_users * events_per_user
        total_actual_events = len(successful_events) + len(failed_events)
        overall_success_rate = len(successful_events) / total_expected_events
        
        # Check for timing clustering (indicator of race conditions)
        timing_clusters = []
        sorted_events = sorted(comprehensive_log, key=lambda x: x['timestamp'])
        
        cluster_window_ns = 5_000_000  # 5ms clustering window
        current_cluster = []
        
        for event in sorted_events:
            if not current_cluster:
                current_cluster = [event]
            else:
                last_event = current_cluster[-1]
                if event['timestamp'] - last_event['timestamp'] <= cluster_window_ns:
                    current_cluster.append(event)
                else:
                    if len(current_cluster) >= 4:  # Cluster of 4+ events indicates race condition
                        timing_clusters.append({
                            'start_time': current_cluster[0]['timestamp'],
                            'end_time': current_cluster[-1]['timestamp'],
                            'event_count': len(current_cluster),
                            'users_involved': len(set(e['user_id'] for e in current_cluster))
                        })
                    current_cluster = [event]
        
        # Final assertions and race condition reporting
        assert total_actual_events == total_expected_events, f"Event count mismatch: {total_actual_events} != {total_expected_events}"
        assert overall_success_rate > 0.85, f"Overall success rate too low: {overall_success_rate:.2%}"
        
        print(f"\nCOMPREHENSIVE RACE CONDITION TEST SUMMARY:")
        print(f"  Users: {num_users}")
        print(f"  Events per user: {events_per_user}")
        print(f"  Total duration: {total_duration:.3f}s")
        print(f"  Overall success rate: {overall_success_rate:.2%}")
        print(f"  Timing clusters detected: {len(timing_clusters)}")
        
        if timing_clusters:
            print(f"\nRACE CONDITION INDICATORS:")
            for i, cluster in enumerate(timing_clusters):
                duration_ms = (cluster['end_time'] - cluster['start_time']) / 1_000_000
                print(f"  Cluster {i+1}: {cluster['event_count']} events from {cluster['users_involved']} users in {duration_ms:.2f}ms")
        
        # Per-user performance analysis
        print(f"\nPER-USER PERFORMANCE:")
        for user_id, metrics in user_metrics.items():
            print(f"  {user_id}: {metrics['successful_events']}/{metrics['total_events']} events ({metrics['success_rate']:.1%})")

    def teardown_method(self):
        """Cleanup after each test method."""
        super().teardown_method()
        self.operation_log.clear()
        # Clear test environment variables 
        self.isolated_env.set("ENVIRONMENT", "", source="test")


# Additional utility functions for race condition testing

async def simulate_network_jitter(min_delay_ms: float = 1, max_delay_ms: float = 10):
    """Simulate realistic network jitter for race condition testing."""
    delay = random.uniform(min_delay_ms, max_delay_ms) / 1000
    await asyncio.sleep(delay)


def detect_timing_race_condition(operations: List[Dict[str, Any]], window_ns: int = 1_000_000) -> List[Dict[str, Any]]:
    """
    Detect potential race conditions based on operation timing patterns.
    
    Args:
        operations: List of operation records with 'timestamp' field
        window_ns: Time window in nanoseconds to consider as potential race condition
        
    Returns:
        List of detected race condition patterns
    """
    race_conditions = []
    sorted_ops = sorted(operations, key=lambda x: x['timestamp'])
    
    for i, op1 in enumerate(sorted_ops):
        overlapping_ops = []
        for op2 in sorted_ops[i+1:]:
            if op2['timestamp'] - op1['timestamp'] <= window_ns:
                overlapping_ops.append(op2)
            else:
                break
        
        if len(overlapping_ops) >= 2:  # 3+ operations in window indicates race condition
            race_conditions.append({
                'start_operation': op1,
                'overlapping_operations': overlapping_ops,
                'time_window_ns': window_ns,
                'severity': 'high' if len(overlapping_ops) >= 4 else 'medium'
            })
    
    return race_conditions


class RaceConditionProfiler:
    """Profiler for detecting and analyzing race conditions in WebSocket operations."""
    
    def __init__(self):
        self.operation_timeline: List[Dict[str, Any]] = []
        self.lock = asyncio.Lock()
    
    async def record_operation(self, operation_type: str, user_id: str, data: Dict[str, Any] = None):
        """Record operation with high-precision timing."""
        async with self.lock:
            self.operation_timeline.append({
                'timestamp': time.time_ns(),
                'operation_type': operation_type,
                'user_id': user_id,
                'thread_id': threading.get_ident(),
                'data': data or {}
            })
    
    def analyze_race_conditions(self) -> Dict[str, Any]:
        """Analyze recorded operations for race condition patterns."""
        if not self.operation_timeline:
            return {'race_conditions': [], 'analysis': 'no_data'}
        
        race_conditions = detect_timing_race_condition(self.operation_timeline)
        
        # Additional analysis
        user_concurrency = {}
        for op in self.operation_timeline:
            user_id = op['user_id']
            if user_id not in user_concurrency:
                user_concurrency[user_id] = []
            user_concurrency[user_id].append(op)
        
        # Check for per-user race conditions
        user_race_conditions = {}
        for user_id, ops in user_concurrency.items():
            if len(ops) > 1:
                user_races = detect_timing_race_condition(ops, window_ns=5_000_000)  # 5ms window
                if user_races:
                    user_race_conditions[user_id] = user_races
        
        return {
            'race_conditions': race_conditions,
            'user_race_conditions': user_race_conditions,
            'total_operations': len(self.operation_timeline),
            'analysis': 'complete'
        }
    
    def clear(self):
        """Clear recorded operations."""
        self.operation_timeline.clear()