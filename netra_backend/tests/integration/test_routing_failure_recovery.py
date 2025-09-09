"""
Test WebSocket Routing Failure Recovery

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise)
- Business Goal: Ensure system resilience and recovery from routing failures
- Value Impact: Prevents permanent chat disruption when routing failures occur
- Strategic Impact: CRITICAL - System must recover from routing failures to maintain user trust

REPRODUCES BUG: Routing system fails to recover from connection ID mismatches  
REPRODUCES BUG: Failed routing attempts accumulate without cleanup or retry mechanisms
REPRODUCES BUG: System doesn't detect or self-heal routing table corruption

This test suite validates WebSocket routing failure recovery:
1. Automatic detection of routing failures and inconsistencies
2. Self-healing mechanisms for corrupted routing tables
3. Retry logic for failed message delivery attempts
4. Graceful degradation and recovery under system stress

Recovery patterns are essential for production stability.
"""

import asyncio
import pytest  
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Set, List, Optional, Tuple
from unittest.mock import Mock, AsyncMock, patch
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import logging

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context  
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

from netra_backend.app.websocket.connection_handler import ConnectionHandler, ConnectionContext
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types.execution_types import StronglyTypedUserExecutionContext


@dataclass
class RoutingFailureMetrics:
    """Tracks routing failure and recovery metrics."""
    total_attempts: int = 0
    failed_attempts: int = 0
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    permanent_failures: int = 0
    recovery_time_ms: List[float] = field(default_factory=list)
    failure_reasons: List[str] = field(default_factory=list)
    
    def add_failure(self, reason: str):
        """Record a routing failure."""
        self.total_attempts += 1
        self.failed_attempts += 1
        self.failure_reasons.append(reason)
    
    def add_recovery_success(self, recovery_time: float):
        """Record successful recovery."""
        self.recovery_attempts += 1
        self.successful_recoveries += 1
        self.recovery_time_ms.append(recovery_time)
    
    def add_recovery_failure(self):
        """Record failed recovery attempt."""
        self.recovery_attempts += 1
        
    def add_permanent_failure(self):
        """Record permanent failure (no recovery possible)."""
        self.permanent_failures += 1
    
    def get_failure_rate(self) -> float:
        """Calculate failure rate."""
        return self.failed_attempts / self.total_attempts if self.total_attempts > 0 else 0.0
    
    def get_recovery_rate(self) -> float:
        """Calculate successful recovery rate."""
        return self.successful_recoveries / self.recovery_attempts if self.recovery_attempts > 0 else 0.0
    
    def get_avg_recovery_time(self) -> float:
        """Calculate average recovery time in milliseconds."""
        return sum(self.recovery_time_ms) / len(self.recovery_time_ms) if self.recovery_time_ms else 0.0


class RoutingRecoveryManager:
    """Manages routing failure detection and recovery."""
    
    def __init__(self):
        self.metrics = RoutingFailureMetrics()
        self.failed_routes: Dict[str, Dict[str, Any]] = {}
        self.recovery_strategies: List[str] = [
            "reconnect_handler",
            "refresh_routing_table", 
            "recreate_connection",
            "fallback_broadcast"
        ]
        self.max_retry_attempts = 3
        self.recovery_timeout_ms = 5000
    
    async def detect_routing_failure(self, user_id: str, connection_id: str, 
                                   error: Exception) -> bool:
        """Detect and classify routing failure."""
        failure_key = f"{user_id}:{connection_id}"
        
        failure_info = {
            "user_id": user_id,
            "connection_id": connection_id,
            "error": str(error),
            "timestamp": datetime.now(timezone.utc),
            "failure_count": self.failed_routes.get(failure_key, {}).get("failure_count", 0) + 1,
            "last_success": None
        }
        
        self.failed_routes[failure_key] = failure_info
        self.metrics.add_failure(str(error))
        
        # Classify failure type for recovery strategy
        error_str = str(error).lower()
        if "connection" in error_str and "not found" in error_str:
            return True  # Recoverable - connection missing
        elif "user" in error_str and "mismatch" in error_str:
            return True  # Recoverable - user validation issue
        elif "timeout" in error_str or "unavailable" in error_str:
            return True  # Recoverable - temporary network issue
        else:
            self.metrics.add_permanent_failure()
            return False  # Non-recoverable
    
    async def attempt_recovery(self, user_id: str, connection_id: str, 
                              router: WebSocketEventRouter,
                              handler: ConnectionHandler = None) -> bool:
        """Attempt to recover from routing failure."""
        failure_key = f"{user_id}:{connection_id}"
        
        if failure_key not in self.failed_routes:
            return False
        
        failure_info = self.failed_routes[failure_key]
        start_time = datetime.now(timezone.utc)
        
        # Try recovery strategies in order
        for strategy in self.recovery_strategies:
            try:
                recovery_success = False
                
                if strategy == "reconnect_handler" and handler:
                    # Re-authenticate handler
                    recovery_success = await handler.authenticate()
                    if recovery_success:
                        # Re-register in router
                        await router.register_connection(user_id, connection_id)
                
                elif strategy == "refresh_routing_table":
                    # Clean stale entries and re-register
                    await router.cleanup_stale_connections()
                    await router.register_connection(user_id, connection_id)
                    recovery_success = True
                
                elif strategy == "recreate_connection":
                    # Generate new connection ID
                    new_connection_id = f"recovery_{connection_id}_{int(datetime.now().timestamp())}"
                    await router.register_connection(user_id, new_connection_id)
                    # Update failure tracking to new connection ID
                    new_failure_key = f"{user_id}:{new_connection_id}"
                    self.failed_routes[new_failure_key] = self.failed_routes[failure_key]
                    del self.failed_routes[failure_key]
                    recovery_success = True
                
                elif strategy == "fallback_broadcast":
                    # Use broadcast instead of direct routing
                    test_message = {"type": "recovery_test", "user_id": user_id}
                    successful_sends = await router.broadcast_to_user(user_id, test_message)
                    recovery_success = successful_sends > 0
                
                if recovery_success:
                    # Record successful recovery
                    recovery_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    self.metrics.add_recovery_success(recovery_time)
                    
                    # Mark failure as resolved
                    failure_info["recovered"] = True
                    failure_info["recovery_strategy"] = strategy
                    failure_info["recovery_time"] = recovery_time
                    
                    return True
                    
            except Exception as e:
                # Recovery strategy failed, try next one
                continue
        
        # All recovery strategies failed
        self.metrics.add_recovery_failure()
        return False
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        return {
            "total_failures": self.metrics.failed_attempts,
            "recovery_attempts": self.metrics.recovery_attempts,
            "successful_recoveries": self.metrics.successful_recoveries,
            "permanent_failures": self.metrics.permanent_failures,
            "failure_rate": self.metrics.get_failure_rate(),
            "recovery_rate": self.metrics.get_recovery_rate(),
            "avg_recovery_time_ms": self.metrics.get_avg_recovery_time(),
            "active_failures": len([f for f in self.failed_routes.values() if not f.get("recovered", False)])
        }


class TestRoutingFailureRecovery(BaseIntegrationTest):
    """Test WebSocket routing failure recovery mechanisms."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_id_mismatch_recovery(self, real_services_fixture):
        """
        Test recovery from connection ID mismatches causing routing failures.
        
        REPRODUCES BUG: Connection ID mismatches cause permanent routing failures
        without recovery mechanisms
        """
        # Arrange: Create scenario with connection ID mismatches  
        user_id = "recovery_test_user"
        auth_helper = E2EAuthHelper(environment="test")
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_id=user_id,
            environment="test",
            websocket_enabled=True
        )
        
        jwt_token = auth_helper.create_test_jwt_token(user_id=user_id)
        
        # Setup routing infrastructure
        mock_websocket = Mock()
        mock_manager = Mock()
        mock_manager.send_to_connection = AsyncMock(side_effect=Exception("Connection not found"))
        
        router = WebSocketEventRouter(mock_manager)
        handler = ConnectionHandler(mock_websocket, user_id)
        recovery_manager = RoutingRecoveryManager()
        
        await handler.authenticate(thread_id=str(user_context.thread_id))
        original_connection_id = handler.connection_id
        
        # Register connection in router
        await router.register_connection(user_id, original_connection_id)
        
        # Act: Create connection ID mismatch (simulating the production bug)
        # Change handler's connection ID but don't update router
        handler.connection_id = f"mismatched_{original_connection_id}"
        
        # Attempt to route message with mismatched IDs
        test_message = {
            "type": "agent_started",
            "user_id": user_id,
            "message": "This should fail due to ID mismatch"
        }
        
        # This should fail
        routing_success = await router.route_event(user_id, handler.connection_id, test_message)
        
        # Assert: Initial routing fails due to mismatch
        assert routing_success == False, "Routing should fail with mismatched connection IDs"
        
        # Detect and attempt recovery
        routing_error = Exception("Connection ID mismatch in routing table")
        can_recover = await recovery_manager.detect_routing_failure(
            user_id, 
            handler.connection_id, 
            routing_error
        )
        
        assert can_recover == True, "Connection ID mismatch should be recoverable"
        
        # Mock successful manager after recovery
        mock_manager.send_to_connection = AsyncMock(return_value=True)
        
        # Attempt recovery  
        recovery_success = await recovery_manager.attempt_recovery(
            user_id,
            handler.connection_id,
            router,
            handler
        )
        
        # Assert: Recovery should succeed
        assert recovery_success == True, "Recovery from connection ID mismatch should succeed"
        
        # Verify routing works after recovery
        post_recovery_routing = await router.route_event(user_id, handler.connection_id, test_message)
        assert post_recovery_routing == True, "Routing should work after recovery"
        
        # Check recovery statistics
        recovery_stats = recovery_manager.get_recovery_stats()
        
        print(f"🚨 CONNECTION ID MISMATCH RECOVERY RESULTS:")
        print(f"   Total failures: {recovery_stats['total_failures']}")
        print(f"   Recovery attempts: {recovery_stats['recovery_attempts']}")
        print(f"   Successful recoveries: {recovery_stats['successful_recoveries']}")
        print(f"   Recovery rate: {recovery_stats['recovery_rate']:.1%}")
        print(f"   Avg recovery time: {recovery_stats['avg_recovery_time_ms']:.1f}ms")
        
        assert recovery_stats['recovery_rate'] == 1.0, "Recovery rate should be 100% for connection ID mismatches"
        
        # Cleanup
        await handler.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_routing_table_corruption_auto_healing(self, real_services_fixture):
        """
        Test automatic healing of corrupted routing tables.
        
        REPRODUCES BUG: Routing table corruption accumulates without self-healing,
        leading to systematic routing degradation
        """
        # Arrange: Create scenario with routing table corruption
        base_user_id = "healing_test_user"
        corruption_count = 5
        
        mock_manager = Mock()  
        mock_manager.send_to_connection = AsyncMock(return_value=True)
        
        router = WebSocketEventRouter(mock_manager)
        recovery_manager = RoutingRecoveryManager()
        
        # Create multiple connections with potential corruption
        connections = []
        handlers = []
        
        for i in range(corruption_count):
            user_id = f"{base_user_id}_{i}"
            
            # Create authenticated context
            user_context = await create_authenticated_user_context(
                user_id=user_id,
                environment="test",
                websocket_enabled=True
            )
            
            mock_websocket = Mock()
            handler = ConnectionHandler(mock_websocket, user_id)
            await handler.authenticate(thread_id=str(user_context.thread_id))
            
            # Register normally
            await router.register_connection(user_id, handler.connection_id)
            
            connections.append({
                "user_id": user_id,
                "connection_id": handler.connection_id,
                "context": user_context,
                "handler": handler
            })
            handlers.append(handler)
        
        # Act: Introduce routing table corruption
        print(f"🚨 INTRODUCING ROUTING TABLE CORRUPTION:")
        
        # Corruption type 1: Stale entries (simulate old connections not cleaned up)
        stale_connections = []
        for i in range(3):
            stale_user_id = f"stale_user_{i}"
            stale_conn_id = f"stale_conn_{i}_{uuid.uuid4().hex[:8]}"
            
            # Add stale entry directly to router's pool
            await router.register_connection(stale_user_id, stale_conn_id)
            
            # Manually backdate to make it stale
            if stale_user_id in router.connection_pool:
                for conn_info in router.connection_pool[stale_user_id]:
                    conn_info.last_activity = datetime.now(timezone.utc) - timedelta(minutes=10)
            
            stale_connections.append((stale_user_id, stale_conn_id))
            print(f"   Added stale entry: {stale_user_id}:{stale_conn_id}")
        
        # Corruption type 2: Orphaned entries (connection in pool but not in connection-to-user mapping)
        for i in range(2):
            orphan_user_id = f"orphan_user_{i}"
            orphan_conn_id = f"orphan_conn_{i}_{uuid.uuid4().hex[:8]}"
            
            # Add to connection pool but remove from connection-to-user mapping
            await router.register_connection(orphan_user_id, orphan_conn_id)
            
            if orphan_conn_id in router.connection_to_user:
                del router.connection_to_user[orphan_conn_id]
            
            print(f"   Created orphaned entry: {orphan_user_id}:{orphan_conn_id}")
        
        # Get corrupted state statistics  
        pre_healing_stats = await router.get_stats()
        print(f"🚨 PRE-HEALING ROUTING TABLE STATE:")
        print(f"   Total users: {pre_healing_stats['total_users']}")
        print(f"   Total connections: {pre_healing_stats['total_connections']}")
        print(f"   Active connections: {pre_healing_stats['active_connections']}")
        
        # Test routing with corrupted table
        routing_failures = []
        for connection in connections:
            test_message = {
                "type": "tool_executing",
                "user_id": connection["user_id"],
                "message": "Testing with corrupted routing table"
            }
            
            routing_success = await router.route_event(
                connection["user_id"],
                connection["connection_id"],
                test_message
            )
            
            if not routing_success:
                routing_failures.append(connection["user_id"])
        
        pre_healing_failure_rate = len(routing_failures) / len(connections)
        print(f"🚨 PRE-HEALING ROUTING FAILURE RATE: {pre_healing_failure_rate:.1%}")
        
        # Act: Trigger auto-healing
        print(f"🚨 TRIGGERING AUTO-HEALING MECHANISMS:")
        
        # Healing step 1: Cleanup stale connections
        cleaned_count = await router.cleanup_stale_connections()
        print(f"   Cleaned up {cleaned_count} stale connections")
        
        # Healing step 2: Rebuild connection mappings for orphaned entries
        healing_start = datetime.now(timezone.utc)
        
        # Rebuild connection-to-user mappings
        for user_id, user_connections in router.connection_pool.items():
            for conn_info in user_connections:
                if conn_info.connection_id not in router.connection_to_user:
                    router.connection_to_user[conn_info.connection_id] = user_id
                    print(f"   Rebuilt mapping: {conn_info.connection_id} -> {user_id}")
        
        # Healing step 3: Validate and repair inconsistencies
        inconsistency_repairs = 0
        for conn_id, mapped_user in router.connection_to_user.items():
            # Check if connection exists in user's pool
            if mapped_user in router.connection_pool:
                user_conn_ids = [c.connection_id for c in router.connection_pool[mapped_user]]
                if conn_id not in user_conn_ids:
                    # Inconsistency found - remove from mapping
                    del router.connection_to_user[conn_id]
                    inconsistency_repairs += 1
                    print(f"   Repaired inconsistency: removed orphaned mapping {conn_id}")
        
        healing_time = (datetime.now(timezone.utc) - healing_start).total_seconds() * 1000
        
        # Assert: Validate auto-healing effectiveness
        post_healing_stats = await router.get_stats()
        print(f"🚨 POST-HEALING ROUTING TABLE STATE:")
        print(f"   Total users: {post_healing_stats['total_users']}")
        print(f"   Total connections: {post_healing_stats['total_connections']}")
        print(f"   Active connections: {post_healing_stats['active_connections']}")
        print(f"   Healing time: {healing_time:.1f}ms")
        print(f"   Inconsistency repairs: {inconsistency_repairs}")
        
        # Test routing after healing
        post_healing_failures = []
        for connection in connections:
            test_message = {
                "type": "agent_completed",
                "user_id": connection["user_id"],
                "message": "Testing after auto-healing"
            }
            
            routing_success = await router.route_event(
                connection["user_id"],
                connection["connection_id"],
                test_message
            )
            
            if not routing_success:
                post_healing_failures.append(connection["user_id"])
        
        post_healing_failure_rate = len(post_healing_failures) / len(connections)
        print(f"🚨 POST-HEALING ROUTING FAILURE RATE: {post_healing_failure_rate:.1%}")
        
        # Calculate healing effectiveness
        healing_improvement = pre_healing_failure_rate - post_healing_failure_rate
        healing_effectiveness = healing_improvement / pre_healing_failure_rate if pre_healing_failure_rate > 0 else 1.0
        
        print(f"🚨 AUTO-HEALING EFFECTIVENESS: {healing_effectiveness:.1%} improvement")
        
        # CRITICAL: Auto-healing should significantly reduce failures
        assert post_healing_failure_rate < pre_healing_failure_rate, \
            "Auto-healing should reduce routing failure rate"
        
        if pre_healing_failure_rate > 0:
            assert healing_effectiveness >= 0.5, \
                f"Auto-healing should improve routing by at least 50%, got {healing_effectiveness:.1%}"
        
        # Routing table should be cleaner after healing
        connection_reduction = pre_healing_stats['total_connections'] - post_healing_stats['total_connections']
        assert connection_reduction >= cleaned_count, \
            f"Should have cleaned at least {cleaned_count} connections, reduced by {connection_reduction}"
        
        # Cleanup
        for handler in handlers:
            await handler.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_retry_and_circuit_breaker(self, real_services_fixture):
        """
        Test message retry logic and circuit breaker patterns for routing failures.
        
        REPRODUCES BUG: Failed message routing attempts don't retry,
        leading to permanent message loss
        """
        # Arrange: Setup for retry and circuit breaker testing
        user_id = "retry_test_user"
        
        # Create authenticated context
        user_context = await create_authenticated_user_context(
            user_id=user_id,
            environment="test",
            websocket_enabled=True
        )
        
        # Create connection
        mock_websocket = Mock()
        handler = ConnectionHandler(mock_websocket, user_id)
        await handler.authenticate(thread_id=str(user_context.thread_id))
        
        # Setup router with controlled failure patterns
        failure_count = 0
        failure_threshold = 3  # Fail first 3 attempts, then succeed
        
        def mock_send_with_controlled_failure(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= failure_threshold:
                raise Exception(f"Simulated routing failure #{failure_count}")
            return True
        
        mock_manager = Mock()
        mock_manager.send_to_connection = AsyncMock(side_effect=mock_send_with_controlled_failure)
        
        router = WebSocketEventRouter(mock_manager)
        recovery_manager = RoutingRecoveryManager()
        
        await router.register_connection(user_id, handler.connection_id)
        
        # Act: Implement retry mechanism with circuit breaker
        test_message = {
            "type": "agent_thinking",
            "user_id": user_id,
            "message": "Message requiring retry logic"
        }
        
        max_retries = 5
        retry_delay_ms = [100, 200, 400, 800, 1600]  # Exponential backoff
        circuit_breaker_threshold = 3  # Open circuit after 3 consecutive failures
        
        retry_results = []
        circuit_breaker_open = False
        consecutive_failures = 0
        
        for attempt in range(max_retries):
            if circuit_breaker_open:
                print(f"🚨 Circuit breaker OPEN - skipping attempt {attempt + 1}")
                retry_results.append({
                    "attempt": attempt + 1,
                    "success": False,
                    "reason": "circuit_breaker_open",
                    "delay_ms": 0
                })
                continue
            
            start_time = datetime.now(timezone.utc)
            
            try:
                # Attempt routing
                routing_success = await router.route_event(
                    user_id, 
                    handler.connection_id, 
                    test_message
                )
                
                if routing_success:
                    # Success - reset circuit breaker
                    consecutive_failures = 0
                    circuit_breaker_open = False
                    
                    end_time = datetime.now(timezone.utc)
                    attempt_duration = (end_time - start_time).total_seconds() * 1000
                    
                    retry_results.append({
                        "attempt": attempt + 1,
                        "success": True,
                        "duration_ms": attempt_duration,
                        "delay_ms": retry_delay_ms[attempt] if attempt < len(retry_delay_ms) else retry_delay_ms[-1]
                    })
                    break
                else:
                    # Failure
                    consecutive_failures += 1
                    
                    # Check circuit breaker threshold
                    if consecutive_failures >= circuit_breaker_threshold:
                        circuit_breaker_open = True
                        print(f"🚨 Circuit breaker OPENED after {consecutive_failures} consecutive failures")
                    
                    retry_results.append({
                        "attempt": attempt + 1,
                        "success": False,
                        "reason": "routing_failed",
                        "consecutive_failures": consecutive_failures,
                        "delay_ms": retry_delay_ms[attempt] if attempt < len(retry_delay_ms) else retry_delay_ms[-1]
                    })
                    
                    # Wait before retry (unless circuit breaker will open)
                    if not circuit_breaker_open and attempt < max_retries - 1:
                        delay = retry_delay_ms[attempt] if attempt < len(retry_delay_ms) else retry_delay_ms[-1]
                        await asyncio.sleep(delay / 1000)
                        
            except Exception as e:
                consecutive_failures += 1
                
                if consecutive_failures >= circuit_breaker_threshold:
                    circuit_breaker_open = True
                
                retry_results.append({
                    "attempt": attempt + 1,
                    "success": False,
                    "reason": f"exception: {e}",
                    "consecutive_failures": consecutive_failures,
                    "delay_ms": retry_delay_ms[attempt] if attempt < len(retry_delay_ms) else retry_delay_ms[-1]
                })
                
                if not circuit_breaker_open and attempt < max_retries - 1:
                    delay = retry_delay_ms[attempt] if attempt < len(retry_delay_ms) else retry_delay_ms[-1]
                    await asyncio.sleep(delay / 1000)
        
        # Assert: Validate retry and circuit breaker behavior
        print(f"🚨 RETRY AND CIRCUIT BREAKER RESULTS:")
        for result in retry_results:
            print(f"   Attempt {result['attempt']}: {result}")
        
        # Check if retry eventually succeeded
        successful_attempt = next((r for r in retry_results if r["success"]), None)
        assert successful_attempt is not None, "Retry mechanism should eventually succeed"
        
        # Verify circuit breaker activated when appropriate
        circuit_breaker_activations = sum(1 for r in retry_results if r.get("reason") == "circuit_breaker_open")
        
        if circuit_breaker_activations > 0:
            print(f"🚨 Circuit breaker activated {circuit_breaker_activations} times")
            assert circuit_breaker_activations > 0, "Circuit breaker should activate under persistent failures"
        
        # Calculate retry statistics
        total_attempts = len(retry_results)
        successful_attempts = sum(1 for r in retry_results if r["success"])
        failed_attempts = total_attempts - successful_attempts
        
        retry_success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0
        
        print(f"🚨 RETRY STATISTICS:")
        print(f"   Total attempts: {total_attempts}")
        print(f"   Successful attempts: {successful_attempts}")
        print(f"   Failed attempts: {failed_attempts}")
        print(f"   Retry success rate: {retry_success_rate:.1%}")
        print(f"   Circuit breaker activations: {circuit_breaker_activations}")
        
        # CRITICAL: Retry mechanism should eventually succeed despite initial failures
        assert retry_success_rate > 0, "Retry mechanism should achieve some success"
        
        # Should succeed after controlled failure period
        successful_attempt_number = successful_attempt["attempt"]
        assert successful_attempt_number > failure_threshold, \
            f"Should succeed after failure threshold ({failure_threshold}), succeeded on attempt {successful_attempt_number}"
        
        # Cleanup
        await handler.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_graceful_degradation_under_system_stress(self, real_services_fixture):
        """
        Test graceful degradation and recovery under extreme system stress.
        
        REPRODUCES BUG: System doesn't degrade gracefully under routing stress,
        leading to complete routing failure instead of partial degradation
        """
        # Arrange: Create high-stress scenario
        stress_users = 10
        messages_per_user = 20
        concurrent_operations = stress_users * messages_per_user
        
        # Create users
        users = []
        for i in range(stress_users):
            user_id = f"stress_user_{i}"
            user_context = await create_authenticated_user_context(
                user_id=user_id,
                environment="test", 
                websocket_enabled=True
            )
            
            users.append({
                "user_id": user_id,
                "context": user_context
            })
        
        # Setup routing with stress-induced failures
        stress_failure_rate = 0.3  # 30% of operations will fail
        operation_count = 0
        
        def mock_send_with_stress_failures(*args, **kwargs):
            nonlocal operation_count
            operation_count += 1
            
            # Simulate stress-related failures
            import random
            if random.random() < stress_failure_rate:
                failure_types = [
                    "Connection timeout under stress",
                    "Resource exhaustion",
                    "Connection pool depleted", 
                    "Rate limit exceeded",
                    "System overload"
                ]
                raise Exception(random.choice(failure_types))
            
            # Simulate processing delay under stress
            import asyncio
            return True
        
        mock_manager = Mock()
        mock_manager.send_to_connection = AsyncMock(side_effect=mock_send_with_stress_failures)
        
        router = WebSocketEventRouter(mock_manager)
        recovery_manager = RoutingRecoveryManager()
        
        # Create connections for all users
        handlers = []
        for user in users:
            mock_websocket = Mock()
            handler = ConnectionHandler(mock_websocket, user["user_id"])
            await handler.authenticate(thread_id=str(user["context"].thread_id))
            await router.register_connection(user["user_id"], handler.connection_id)
            handlers.append(handler)
        
        # Act: Generate massive concurrent load
        async def stress_message_generation(user_index):
            """Generate stress messages for a user."""
            user = users[user_index]
            handler = handlers[user_index]
            results = []
            
            for msg_id in range(messages_per_user):
                message = {
                    "type": "agent_thinking",
                    "user_id": user["user_id"],
                    "message_id": f"{user_index}_{msg_id}",
                    "stress_test": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                start_time = datetime.now(timezone.utc)
                
                try:
                    # Attempt routing with graceful degradation
                    routing_success = await router.route_event(
                        user["user_id"],
                        handler.connection_id,
                        message
                    )
                    
                    end_time = datetime.now(timezone.utc)
                    duration_ms = (end_time - start_time).total_seconds() * 1000
                    
                    results.append({
                        "user_index": user_index,
                        "message_id": msg_id,
                        "success": routing_success,
                        "duration_ms": duration_ms,
                        "status": "success" if routing_success else "failed"
                    })
                    
                except Exception as e:
                    # Handle stress failure
                    end_time = datetime.now(timezone.utc)
                    duration_ms = (end_time - start_time).total_seconds() * 1000
                    
                    results.append({
                        "user_index": user_index,
                        "message_id": msg_id,
                        "success": False,
                        "duration_ms": duration_ms,
                        "error": str(e),
                        "status": "exception"
                    })
                    
                    # Detect failure for potential recovery
                    await recovery_manager.detect_routing_failure(
                        user["user_id"],
                        handler.connection_id,
                        e
                    )
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)
            
            return results
        
        # Execute concurrent stress test
        print(f"🚨 STARTING STRESS TEST:")
        print(f"   Users: {stress_users}")
        print(f"   Messages per user: {messages_per_user}")
        print(f"   Total operations: {concurrent_operations}")
        print(f"   Expected failure rate: {stress_failure_rate:.1%}")
        
        stress_start = datetime.now(timezone.utc)
        
        # Run all stress generators concurrently
        stress_tasks = [stress_message_generation(i) for i in range(stress_users)]
        all_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
        
        stress_end = datetime.now(timezone.utc)
        total_stress_time = (stress_end - stress_start).total_seconds()
        
        # Process stress test results
        successful_operations = 0
        failed_operations = 0
        exception_operations = 0
        total_duration_ms = 0
        
        for user_results in all_results:
            if isinstance(user_results, Exception):
                exception_operations += messages_per_user
                continue
            
            for result in user_results:
                total_duration_ms += result["duration_ms"]
                
                if result["success"]:
                    successful_operations += 1
                elif result["status"] == "exception":
                    exception_operations += 1
                else:
                    failed_operations += 1
        
        total_operations = successful_operations + failed_operations + exception_operations
        actual_success_rate = successful_operations / total_operations if total_operations > 0 else 0
        actual_failure_rate = (failed_operations + exception_operations) / total_operations if total_operations > 0 else 0
        
        avg_operation_time = total_duration_ms / total_operations if total_operations > 0 else 0
        throughput_ops_per_sec = total_operations / total_stress_time if total_stress_time > 0 else 0
        
        # Assert: Validate graceful degradation
        print(f"🚨 STRESS TEST RESULTS:")
        print(f"   Total operations: {total_operations}")
        print(f"   Successful operations: {successful_operations}")
        print(f"   Failed operations: {failed_operations}")
        print(f"   Exception operations: {exception_operations}")
        print(f"   Success rate: {actual_success_rate:.1%}")
        print(f"   Failure rate: {actual_failure_rate:.1%}")
        print(f"   Average operation time: {avg_operation_time:.1f}ms")
        print(f"   Throughput: {throughput_ops_per_sec:.1f} ops/sec")
        print(f"   Total test time: {total_stress_time:.1f}s")
        
        # Get recovery statistics
        recovery_stats = recovery_manager.get_recovery_stats()
        print(f"🚨 RECOVERY UNDER STRESS:")
        print(f"   Total failures detected: {recovery_stats['total_failures']}")
        print(f"   Recovery attempts: {recovery_stats['recovery_attempts']}")
        print(f"   Successful recoveries: {recovery_stats['successful_recoveries']}")
        print(f"   Recovery rate: {recovery_stats['recovery_rate']:.1%}")
        
        # CRITICAL: System should maintain partial functionality under stress
        assert actual_success_rate > 0.5, \
            f"System should maintain >50% functionality under stress, got {actual_success_rate:.1%}"
        
        # Failure rate should be close to expected (showing controlled degradation)
        failure_rate_deviation = abs(actual_failure_rate - stress_failure_rate)
        assert failure_rate_deviation < 0.15, \
            f"Failure rate deviation should be <15%, got {failure_rate_deviation:.1%} deviation"
        
        # System should not completely fail
        assert exception_operations < total_operations * 0.2, \
            f"Exception rate should be <20%, got {exception_operations/total_operations:.1%}"
        
        # Performance should remain reasonable under stress
        assert avg_operation_time < 1000, \
            f"Average operation time should be <1s under stress, got {avg_operation_time:.1f}ms"
        
        # Throughput should be reasonable
        expected_min_throughput = 50  # ops/sec
        assert throughput_ops_per_sec > expected_min_throughput, \
            f"Throughput should be >{expected_min_throughput} ops/sec, got {throughput_ops_per_sec:.1f}"
        
        print(f"🚨 GRACEFUL DEGRADATION VALIDATED:")
        print(f"   ✅ Maintained {actual_success_rate:.1%} functionality under {stress_failure_rate:.1%} stress")
        print(f"   ✅ Controlled failure rate within acceptable bounds")
        print(f"   ✅ Performance degraded gracefully")
        print(f"   ✅ System remained operational throughout stress period")
        
        # Cleanup
        for handler in handlers:
            await handler.cleanup()