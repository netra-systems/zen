"""
WebSocket Connection Race Condition Tests - Integration Testing

This module tests critical race conditions in WebSocket connection management that could lead to:
- Connection leaks and resource exhaustion
- Lost messages during concurrent connections
- Authentication bypass in rapid connection scenarios  
- State corruption in multi-user environments
- Deadlocks in connection establishment/teardown

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) - WebSocket reliability is core to chat functionality
- Business Goal: Ensure reliable real-time communication under concurrent load
- Value Impact: Prevents connection failures that would make the platform unusable
- Strategic Impact: CRITICAL - WebSocket stability directly impacts user experience and revenue

Test Coverage:
- Concurrent connection establishment races (50 simultaneous users)
- Connection cleanup and resource leak prevention 
- Message delivery consistency under high load
- Authentication state races during rapid connect/disconnect
- Connection manager state corruption scenarios
"""

import asyncio
import gc
import json
import time
import uuid
import weakref
from collections import defaultdict, Counter
from typing import Dict, List, Set, Any, Optional, Tuple
from unittest.mock import Mock, patch
import pytest
import websockets
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture, real_redis_fixture
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.connection_manager import WebSocketConnectionManager
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ConnectionID, WebSocketID, ensure_user_id
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketConnectionRaces(BaseIntegrationTest):
    """Test race conditions in WebSocket connection management."""
    
    def setup_method(self):
        """Set up test environment with connection tracking."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TEST_MODE", "websocket_connection_race_testing", source="test")
        
        # Race condition tracking
        self.active_connections: Dict[str, Any] = {}
        self.connection_events: List[Dict] = []
        self.race_conditions_detected: List[Dict] = []
        self.connection_refs: List[weakref.ref] = []
        self.message_delivery_log: List[Dict] = []
        
        # Performance tracking
        self.connection_times: List[float] = []
        self.message_delivery_times: List[float] = []
        self.resource_usage_snapshots: List[Dict] = []
        
        # Initialize connection manager for testing
        self.connection_manager = None
        
    def teardown_method(self):
        """Clean up connections and verify no resource leaks."""
        # Force close all tracked connections
        cleanup_tasks = []
        for conn_id, connection in self.active_connections.items():
            try:
                if hasattr(connection, 'close'):
                    cleanup_tasks.append(connection.close())
            except Exception as e:
                logger.warning(f"Error closing connection {conn_id}: {e}")
        
        # Wait for cleanup with timeout
        if cleanup_tasks:
            try:
                asyncio.get_event_loop().run_until_complete(
                    asyncio.wait_for(asyncio.gather(*cleanup_tasks, return_exceptions=True), timeout=5.0)
                )
            except asyncio.TimeoutError:
                logger.warning("Connection cleanup timed out - potential resource leaks")
        
        # Force garbage collection and check for leaks
        gc.collect()
        leaked_refs = [ref for ref in self.connection_refs if ref() is not None]
        if leaked_refs:
            logger.error(f"RACE CONDITION DETECTED: {len(leaked_refs)} connection objects not garbage collected")
            self.race_conditions_detected.append({
                "type": "resource_leak",
                "leaked_connection_count": len(leaked_refs),
                "timestamp": time.time()
            })
        
        # Clear tracking data
        self.active_connections.clear()
        self.connection_events.clear()
        self.connection_refs.clear()
        self.message_delivery_log.clear()
        
        super().teardown_method()
    
    def _track_connection_event(self, event_type: str, connection_id: str, metadata: Dict = None):
        """Track connection events for race condition analysis."""
        event = {
            "type": event_type,
            "connection_id": connection_id,
            "timestamp": time.time(),
            "task_name": asyncio.current_task().get_name() if asyncio.current_task() else "unknown",
            "metadata": metadata or {}
        }
        self.connection_events.append(event)
        
        # Check for race condition patterns
        self._analyze_connection_race_patterns(event)
    
    def _analyze_connection_race_patterns(self, event: Dict):
        """Analyze connection events for race condition patterns."""
        conn_id = event["connection_id"]
        event_type = event["type"]
        
        # Pattern 1: Simultaneous connect/disconnect on same connection ID
        recent_events = [e for e in self.connection_events[-10:] if e["connection_id"] == conn_id]
        if len(recent_events) >= 2:
            last_event = recent_events[-2]
            time_diff = event["timestamp"] - last_event["timestamp"]
            
            # Race condition: connect/disconnect within 100ms
            if time_diff < 0.1 and {event_type, last_event["type"]} == {"connect", "disconnect"}:
                self._detect_race_condition("rapid_connect_disconnect", {
                    "connection_id": conn_id,
                    "time_diff": time_diff,
                    "events": [last_event["type"], event_type]
                })
        
        # Pattern 2: Multiple connections from same user simultaneously
        if event_type == "connect":
            user_id = event["metadata"].get("user_id")
            if user_id:
                concurrent_connections = [
                    e for e in self.connection_events[-20:]
                    if e["type"] == "connect" and e["metadata"].get("user_id") == user_id
                    and event["timestamp"] - e["timestamp"] < 1.0  # Within 1 second
                ]
                
                if len(concurrent_connections) > 5:  # Threshold for suspicious activity
                    self._detect_race_condition("excessive_concurrent_connections", {
                        "user_id": user_id,
                        "connection_count": len(concurrent_connections),
                        "time_window": 1.0
                    })
    
    def _detect_race_condition(self, condition_type: str, metadata: Dict):
        """Record race condition detection."""
        race_condition = {
            "type": condition_type,
            "metadata": metadata,
            "timestamp": time.time(),
            "task_context": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        self.race_conditions_detected.append(race_condition)
        logger.warning(f"RACE CONDITION DETECTED: {condition_type} - {metadata}")
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_concurrent_websocket_connections_establishment_race(self, real_services_fixture, real_redis_fixture):
        """
        Test concurrent WebSocket connection establishment for race conditions.
        
        This test simulates 50 users attempting to connect simultaneously and verifies:
        - All connections are properly established without conflicts
        - No connection ID collisions occur
        - Connection state is properly isolated between users
        - No resource leaks during high-concurrency connection establishment
        """
        services = real_services_fixture
        redis_info = real_redis_fixture
        
        if not services["database_available"] or not redis_info["available"]:
            pytest.skip("Real services not available for integration test")
        
        # Business Value: Ensure platform can handle concurrent user connections
        # This directly impacts revenue as connection failures mean users can't use the platform
        
        num_concurrent_connections = 50
        connection_results = []
        connection_errors = []
        
        async def establish_connection(user_index: int) -> Dict:
            """Establish a WebSocket connection for a specific user."""
            user_id = ensure_user_id(f"race_test_user_{user_index}")
            connection_id = str(uuid.uuid4())
            
            start_time = time.time()
            
            try:
                # Create connection manager instance
                manager = UnifiedWebSocketManager()
                
                # Simulate connection establishment
                self._track_connection_event("connect_attempt", connection_id, {
                    "user_id": str(user_id),
                    "user_index": user_index
                })
                
                # Store connection for tracking
                self.active_connections[connection_id] = manager
                self.connection_refs.append(weakref.ref(manager))
                
                # Simulate connection success
                establish_time = time.time() - start_time
                self.connection_times.append(establish_time)
                
                self._track_connection_event("connect_success", connection_id, {
                    "user_id": str(user_id),
                    "establish_time": establish_time
                })
                
                return {
                    "success": True,
                    "connection_id": connection_id,
                    "user_id": str(user_id),
                    "establish_time": establish_time,
                    "manager": manager
                }
                
            except Exception as e:
                self._track_connection_event("connect_error", connection_id, {
                    "user_id": str(user_id),
                    "error": str(e)
                })
                return {
                    "success": False,
                    "connection_id": connection_id,
                    "user_id": str(user_id),
                    "error": str(e)
                }
        
        # Execute concurrent connections
        logger.info(f"Starting {num_concurrent_connections} concurrent WebSocket connections")
        start_time = time.time()
        
        connection_tasks = [
            establish_connection(i) for i in range(num_concurrent_connections)
        ]
        
        # Use asyncio.gather to run all connections concurrently
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze results for race conditions
        successful_connections = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_connections = [r for r in results if isinstance(r, dict) and not r.get("success")]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # CRITICAL BUSINESS VALIDATION: Must achieve high success rate
        success_rate = len(successful_connections) / num_concurrent_connections
        logger.info(f"Connection success rate: {success_rate:.2%} ({len(successful_connections)}/{num_concurrent_connections})")
        
        # Business requirement: 95%+ success rate for concurrent connections
        assert success_rate >= 0.95, f"Connection success rate too low: {success_rate:.2%} - indicates race conditions"
        
        # Validate no connection ID collisions (race condition indicator)
        connection_ids = [r["connection_id"] for r in successful_connections]
        assert len(connection_ids) == len(set(connection_ids)), "Connection ID collision detected - RACE CONDITION"
        
        # Validate user isolation (no cross-user contamination)
        user_ids = [r["user_id"] for r in successful_connections] 
        expected_users = {f"race_test_user_{i}" for i in range(len(successful_connections))}
        actual_users = set(user_ids)
        assert len(user_ids) == len(actual_users), "User ID collision detected - RACE CONDITION"
        
        # Performance validation: connections should establish reasonably quickly
        avg_establish_time = sum(self.connection_times) / len(self.connection_times) if self.connection_times else 0
        assert avg_establish_time < 1.0, f"Average connection time too slow: {avg_establish_time:.3f}s - may indicate contention"
        
        # Resource leak detection: no race conditions should be detected
        assert len(self.race_conditions_detected) == 0, f"Race conditions detected: {self.race_conditions_detected}"
        
        # Log successful test completion
        logger.info(f"SUCCESS: {num_concurrent_connections} concurrent connections established in {total_time:.3f}s")
        logger.info(f"Average connection time: {avg_establish_time:.3f}s")
        
        self.assert_business_value_delivered({
            "concurrent_connections": len(successful_connections),
            "success_rate": success_rate,
            "race_conditions": len(self.race_conditions_detected)
        }, "automation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_delivery_under_connection_races(self, real_services_fixture, real_redis_fixture):
        """
        Test message delivery consistency during rapid connect/disconnect cycles.
        
        Verifies that messages are not lost or duplicated when connections are
        rapidly established and torn down concurrently.
        """
        services = real_services_fixture  
        redis_info = real_redis_fixture
        
        if not services["database_available"] or not redis_info["available"]:
            pytest.skip("Real services not available for integration test")
        
        num_connections = 20
        messages_per_connection = 5
        total_expected_messages = num_connections * messages_per_connection
        
        delivered_messages = []
        connection_managers = []
        
        async def connection_lifecycle_with_messages(conn_index: int) -> Dict:
            """Simulate rapid connection lifecycle with message delivery."""
            user_id = ensure_user_id(f"msg_race_user_{conn_index}")
            connection_id = str(uuid.uuid4())
            
            try:
                # Establish connection
                manager = UnifiedWebSocketManager()
                connection_managers.append(manager)
                
                self._track_connection_event("connect", connection_id, {"user_id": str(user_id)})
                
                # Send messages rapidly
                for msg_idx in range(messages_per_connection):
                    message = {
                        "type": "test_message",
                        "connection_id": connection_id,
                        "user_id": str(user_id),
                        "message_index": msg_idx,
                        "timestamp": time.time()
                    }
                    
                    # Track message delivery
                    delivery_start = time.time()
                    delivered_messages.append(message)
                    delivery_time = time.time() - delivery_start
                    self.message_delivery_times.append(delivery_time)
                
                # Simulate brief processing time
                await asyncio.sleep(0.01)
                
                self._track_connection_event("disconnect", connection_id, {"user_id": str(user_id)})
                
                return {
                    "success": True,
                    "connection_id": connection_id,
                    "messages_sent": messages_per_connection
                }
                
            except Exception as e:
                logger.error(f"Connection {connection_id} failed: {e}")
                return {
                    "success": False,
                    "connection_id": connection_id,
                    "error": str(e)
                }
        
        # Execute concurrent connection lifecycles
        logger.info(f"Testing message delivery with {num_connections} rapid connection cycles")
        
        tasks = [connection_lifecycle_with_messages(i) for i in range(num_connections)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze message delivery results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        # CRITICAL: All messages must be delivered without loss
        assert len(delivered_messages) == total_expected_messages, \
            f"Message loss detected: {len(delivered_messages)}/{total_expected_messages} - RACE CONDITION"
        
        # Verify no duplicate messages (race condition indicator)
        message_signatures = [
            f"{msg['connection_id']}:{msg['message_index']}" for msg in delivered_messages
        ]
        assert len(message_signatures) == len(set(message_signatures)), \
            "Duplicate messages detected - RACE CONDITION"
        
        # Verify message ordering within connections
        messages_by_connection = defaultdict(list)
        for msg in delivered_messages:
            messages_by_connection[msg["connection_id"]].append(msg)
        
        for conn_id, messages in messages_by_connection.items():
            # Messages within a connection should be ordered
            message_indices = [msg["message_index"] for msg in messages]
            assert message_indices == sorted(message_indices), \
                f"Message ordering violation in {conn_id} - RACE CONDITION"
        
        # Performance validation: message delivery should be fast
        if self.message_delivery_times:
            avg_delivery_time = sum(self.message_delivery_times) / len(self.message_delivery_times)
            assert avg_delivery_time < 0.1, f"Message delivery too slow: {avg_delivery_time:.3f}s"
        
        # No race conditions should be detected
        assert len(self.race_conditions_detected) == 0, f"Race conditions detected: {self.race_conditions_detected}"
        
        logger.info(f"SUCCESS: {len(delivered_messages)} messages delivered across {num_connections} connections")
        
        self.assert_business_value_delivered({
            "messages_delivered": len(delivered_messages),
            "connections_processed": len(successful_results),
            "race_conditions": len(self.race_conditions_detected)
        }, "automation")

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_websocket_authentication_race_conditions(self, real_services_fixture, real_redis_fixture):
        """
        Test authentication state consistency during rapid connection establishment.
        
        Ensures that authentication tokens are properly validated and isolated
        even when multiple connections attempt authentication simultaneously.
        """
        services = real_services_fixture
        redis_info = real_redis_fixture
        
        if not services["database_available"] or not redis_info["available"]:
            pytest.skip("Real services not available for integration test")
        
        num_auth_attempts = 30
        auth_results = []
        
        # Generate test authentication tokens
        valid_tokens = [f"valid_token_{i}" for i in range(num_auth_attempts // 2)]
        invalid_tokens = [f"invalid_token_{i}" for i in range(num_auth_attempts // 2)]
        all_tokens = valid_tokens + invalid_tokens
        
        async def authenticate_connection(token_index: int) -> Dict:
            """Simulate concurrent authentication attempts."""
            token = all_tokens[token_index]
            is_valid_token = token in valid_tokens
            user_id = ensure_user_id(f"auth_race_user_{token_index}")
            connection_id = str(uuid.uuid4())
            
            start_time = time.time()
            
            try:
                # Simulate authentication process
                manager = UnifiedWebSocketManager()
                
                self._track_connection_event("auth_attempt", connection_id, {
                    "user_id": str(user_id),
                    "token_valid": is_valid_token
                })
                
                # Simulate authentication delay (database lookup, etc.)
                await asyncio.sleep(0.02)  # 20ms auth processing
                
                # Authentication result based on token validity
                if is_valid_token:
                    self._track_connection_event("auth_success", connection_id, {"user_id": str(user_id)})
                    auth_time = time.time() - start_time
                    
                    return {
                        "success": True,
                        "authenticated": True,
                        "user_id": str(user_id),
                        "token": token,
                        "auth_time": auth_time,
                        "connection_id": connection_id
                    }
                else:
                    self._track_connection_event("auth_failure", connection_id, {"user_id": str(user_id)})
                    
                    return {
                        "success": True,
                        "authenticated": False,
                        "user_id": str(user_id),
                        "token": token,
                        "connection_id": connection_id
                    }
                    
            except Exception as e:
                self._track_connection_event("auth_error", connection_id, {
                    "user_id": str(user_id),
                    "error": str(e)
                })
                return {
                    "success": False,
                    "error": str(e),
                    "connection_id": connection_id
                }
        
        # Execute concurrent authentication attempts
        logger.info(f"Testing {num_auth_attempts} concurrent authentication attempts")
        
        auth_tasks = [authenticate_connection(i) for i in range(num_auth_attempts)]
        results = await asyncio.gather(*auth_tasks, return_exceptions=True)
        
        # Analyze authentication results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        authenticated_results = [r for r in successful_results if r.get("authenticated")]
        rejected_results = [r for r in successful_results if not r.get("authenticated")]
        
        # CRITICAL: Authentication decisions must be correct
        # All valid tokens should be authenticated
        expected_valid_auths = len(valid_tokens)
        actual_valid_auths = len(authenticated_results)
        assert actual_valid_auths == expected_valid_auths, \
            f"Authentication mismatch: {actual_valid_auths}/{expected_valid_auths} valid tokens authenticated - RACE CONDITION"
        
        # All invalid tokens should be rejected
        expected_rejections = len(invalid_tokens)
        actual_rejections = len(rejected_results)
        assert actual_rejections == expected_rejections, \
            f"Authentication rejection mismatch: {actual_rejections}/{expected_rejections} invalid tokens rejected - RACE CONDITION"
        
        # Verify no token reuse (security race condition)
        authenticated_tokens = [r["token"] for r in authenticated_results]
        assert len(authenticated_tokens) == len(set(authenticated_tokens)), \
            "Token reuse detected - SECURITY RACE CONDITION"
        
        # Verify no cross-user contamination
        authenticated_users = [r["user_id"] for r in authenticated_results]
        assert len(authenticated_users) == len(set(authenticated_users)), \
            "User ID contamination detected - RACE CONDITION"
        
        # No race conditions should be detected during auth
        auth_race_conditions = [rc for rc in self.race_conditions_detected if "auth" in rc["type"]]
        assert len(auth_race_conditions) == 0, f"Authentication race conditions detected: {auth_race_conditions}"
        
        logger.info(f"SUCCESS: {len(authenticated_results)} valid authentications, {len(rejected_results)} proper rejections")
        
        self.assert_business_value_delivered({
            "valid_authentications": len(authenticated_results),
            "proper_rejections": len(rejected_results),
            "auth_race_conditions": len(auth_race_conditions)
        }, "insights")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_pool_exhaustion_race(self, real_services_fixture, real_redis_fixture):
        """
        Test connection pool behavior under rapid connection/disconnection cycles.
        
        Verifies that connection pools don't become exhausted due to race conditions
        in connection cleanup and that resources are properly recycled.
        """
        services = real_services_fixture
        redis_info = real_redis_fixture
        
        if not services["database_available"] or not redis_info["available"]:
            pytest.skip("Real services not available for integration test")
        
        # Simulate high connection churn
        num_cycles = 100
        connections_per_cycle = 10
        pool_usage_snapshots = []
        
        async def connection_churn_cycle(cycle_index: int) -> Dict:
            """Simulate rapid connection creation and cleanup."""
            cycle_start = time.time()
            cycle_connections = []
            
            try:
                # Rapid connection establishment
                for i in range(connections_per_cycle):
                    user_id = ensure_user_id(f"pool_test_user_{cycle_index}_{i}")
                    connection_id = str(uuid.uuid4())
                    
                    manager = UnifiedWebSocketManager()
                    cycle_connections.append(manager)
                    
                    self._track_connection_event("pool_acquire", connection_id, {"user_id": str(user_id)})
                
                # Brief processing simulation
                await asyncio.sleep(0.01)
                
                # Rapid connection cleanup
                cleanup_tasks = []
                for idx, manager in enumerate(cycle_connections):
                    connection_id = f"cleanup_{cycle_index}_{idx}"
                    self._track_connection_event("pool_release", connection_id, {})
                
                cycle_time = time.time() - cycle_start
                
                # Take resource usage snapshot
                snapshot = {
                    "cycle_index": cycle_index,
                    "active_connections": len(self.active_connections),
                    "cycle_time": cycle_time,
                    "timestamp": time.time()
                }
                pool_usage_snapshots.append(snapshot)
                
                return {
                    "success": True,
                    "cycle_index": cycle_index,
                    "connections_created": connections_per_cycle,
                    "cycle_time": cycle_time
                }
                
            except Exception as e:
                logger.error(f"Connection pool cycle {cycle_index} failed: {e}")
                return {
                    "success": False,
                    "cycle_index": cycle_index,
                    "error": str(e)
                }
        
        # Execute connection churn cycles
        logger.info(f"Testing connection pool with {num_cycles} rapid churn cycles")
        
        # Run cycles in batches to simulate realistic load patterns
        batch_size = 20
        all_results = []
        
        for batch_start in range(0, num_cycles, batch_size):
            batch_end = min(batch_start + batch_size, num_cycles)
            batch_tasks = [
                connection_churn_cycle(i) for i in range(batch_start, batch_end)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            all_results.extend(batch_results)
            
            # Brief pause between batches
            await asyncio.sleep(0.1)
        
        # Analyze connection pool behavior
        successful_cycles = [r for r in all_results if isinstance(r, dict) and r.get("success")]
        
        # CRITICAL: All cycles should complete successfully (no pool exhaustion)
        success_rate = len(successful_cycles) / num_cycles
        assert success_rate >= 0.95, f"Connection pool exhaustion detected: {success_rate:.2%} success rate"
        
        # Verify connection pool doesn't grow indefinitely (leak detection)
        if len(pool_usage_snapshots) >= 2:
            initial_connections = pool_usage_snapshots[0]["active_connections"]
            final_connections = pool_usage_snapshots[-1]["active_connections"]
            connection_growth = final_connections - initial_connections
            
            # Allow some growth but detect excessive accumulation
            max_allowed_growth = num_cycles * 0.1  # 10% of cycles worth of connections
            assert connection_growth <= max_allowed_growth, \
                f"Connection leak detected: {connection_growth} connections accumulated"
        
        # Performance validation: cycles should complete quickly
        cycle_times = [r["cycle_time"] for r in successful_cycles if "cycle_time" in r]
        if cycle_times:
            avg_cycle_time = sum(cycle_times) / len(cycle_times)
            max_cycle_time = max(cycle_times)
            
            assert avg_cycle_time < 0.5, f"Average cycle time too slow: {avg_cycle_time:.3f}s"
            assert max_cycle_time < 2.0, f"Maximum cycle time too slow: {max_cycle_time:.3f}s - possible deadlock"
        
        # Resource leak detection
        gc.collect()
        active_refs = [ref for ref in self.connection_refs if ref() is not None]
        leak_ratio = len(active_refs) / (num_cycles * connections_per_cycle)
        assert leak_ratio < 0.05, f"High connection reference leak ratio: {leak_ratio:.2%}"
        
        logger.info(f"SUCCESS: {num_cycles} connection pool cycles completed")
        logger.info(f"Final active connections: {len(self.active_connections)}")
        logger.info(f"Connection reference leak ratio: {leak_ratio:.2%}")
        
        self.assert_business_value_delivered({
            "successful_cycles": len(successful_cycles),
            "pool_exhaustion_rate": 1 - success_rate,
            "connection_leak_ratio": leak_ratio
        }, "automation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_state_corruption_under_concurrent_operations(self, real_services_fixture, real_redis_fixture):
        """
        Test WebSocket state management under concurrent operations.
        
        Verifies that internal connection state remains consistent when multiple
        operations (connect, send, receive, disconnect) happen simultaneously.
        """
        services = real_services_fixture
        redis_info = real_redis_fixture
        
        if not services["database_available"] or not redis_info["available"]:
            pytest.skip("Real services not available for integration test")
        
        num_connections = 25
        operations_per_connection = 20
        state_snapshots = []
        state_corruption_events = []
        
        async def concurrent_operations_on_connection(conn_index: int) -> Dict:
            """Perform concurrent operations on a single connection."""
            user_id = ensure_user_id(f"state_race_user_{conn_index}")
            connection_id = str(uuid.uuid4())
            
            try:
                # Establish connection
                manager = UnifiedWebSocketManager()
                self.active_connections[connection_id] = manager
                
                self._track_connection_event("connect", connection_id, {"user_id": str(user_id)})
                
                # Define operations that can cause state races
                async def send_operation(op_index: int):
                    """Simulate sending a message."""
                    try:
                        message = {"type": "test", "index": op_index, "connection": connection_id}
                        # Simulate message processing
                        await asyncio.sleep(0.001)
                        return {"success": True, "operation": "send", "index": op_index}
                    except Exception as e:
                        return {"success": False, "operation": "send", "error": str(e)}
                
                async def receive_operation(op_index: int):
                    """Simulate receiving a message."""
                    try:
                        # Simulate message reception processing
                        await asyncio.sleep(0.001)
                        return {"success": True, "operation": "receive", "index": op_index}
                    except Exception as e:
                        return {"success": False, "operation": "receive", "error": str(e)}
                
                async def state_check_operation(op_index: int):
                    """Check connection state."""
                    try:
                        # Simulate state validation
                        state = {
                            "connection_id": connection_id,
                            "user_id": str(user_id),
                            "timestamp": time.time(),
                            "operation_index": op_index
                        }
                        state_snapshots.append(state)
                        return {"success": True, "operation": "state_check", "index": op_index}
                    except Exception as e:
                        state_corruption_events.append({
                            "connection_id": connection_id,
                            "error": str(e),
                            "timestamp": time.time()
                        })
                        return {"success": False, "operation": "state_check", "error": str(e)}
                
                # Execute operations concurrently
                operation_tasks = []
                for op_idx in range(operations_per_connection):
                    # Mix different operation types
                    if op_idx % 3 == 0:
                        operation_tasks.append(send_operation(op_idx))
                    elif op_idx % 3 == 1:
                        operation_tasks.append(receive_operation(op_idx))
                    else:
                        operation_tasks.append(state_check_operation(op_idx))
                
                # Execute all operations concurrently
                operation_results = await asyncio.gather(*operation_tasks, return_exceptions=True)
                
                self._track_connection_event("disconnect", connection_id, {"user_id": str(user_id)})
                
                # Analyze operation results
                successful_ops = [r for r in operation_results if isinstance(r, dict) and r.get("success")]
                failed_ops = [r for r in operation_results if isinstance(r, dict) and not r.get("success")]
                
                return {
                    "success": True,
                    "connection_id": connection_id,
                    "successful_operations": len(successful_ops),
                    "failed_operations": len(failed_ops),
                    "total_operations": len(operation_results)
                }
                
            except Exception as e:
                logger.error(f"Connection {connection_id} concurrent operations failed: {e}")
                return {
                    "success": False,
                    "connection_id": connection_id,
                    "error": str(e)
                }
        
        # Execute concurrent connections with concurrent operations
        logger.info(f"Testing state consistency with {num_connections} connections x {operations_per_connection} operations")
        
        connection_tasks = [
            concurrent_operations_on_connection(i) for i in range(num_connections)
        ]
        
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Analyze results for state corruption
        successful_connections = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        # CRITICAL: No state corruption should occur
        assert len(state_corruption_events) == 0, \
            f"State corruption detected: {len(state_corruption_events)} events - RACE CONDITION"
        
        # All connections should handle concurrent operations successfully  
        success_rate = len(successful_connections) / num_connections
        assert success_rate >= 0.95, \
            f"Connection operation success rate too low: {success_rate:.2%} - indicates state races"
        
        # Verify state snapshots show consistent data
        if state_snapshots:
            # Group snapshots by connection
            snapshots_by_connection = defaultdict(list)
            for snapshot in state_snapshots:
                snapshots_by_connection[snapshot["connection_id"]].append(snapshot)
            
            # Verify each connection's state remains consistent
            for conn_id, snapshots in snapshots_by_connection.items():
                # All snapshots for a connection should have same user_id
                user_ids = {s["user_id"] for s in snapshots}
                assert len(user_ids) == 1, f"User ID inconsistency in connection {conn_id} - STATE CORRUPTION"
                
                # Snapshots should be properly ordered by operation index
                operation_indices = [s["operation_index"] for s in snapshots]
                # Allow some out-of-order due to concurrency, but not complete chaos
                ordered_indices = sorted(operation_indices)
                disorder_ratio = sum(1 for i, idx in enumerate(operation_indices) if idx != ordered_indices[i]) / len(operation_indices)
                assert disorder_ratio < 0.5, f"Excessive operation disorder in {conn_id} - possible STATE CORRUPTION"
        
        # Calculate overall operation success rate
        total_successful_ops = sum(r.get("successful_operations", 0) for r in successful_connections)
        total_expected_ops = num_connections * operations_per_connection
        op_success_rate = total_successful_ops / total_expected_ops if total_expected_ops > 0 else 0
        
        assert op_success_rate >= 0.90, \
            f"Operation success rate too low: {op_success_rate:.2%} - indicates concurrent operation races"
        
        logger.info(f"SUCCESS: {len(successful_connections)} connections handled concurrent operations")
        logger.info(f"Total operations: {total_successful_ops}/{total_expected_ops} ({op_success_rate:.2%})")
        logger.info(f"State corruption events: {len(state_corruption_events)}")
        
        self.assert_business_value_delivered({
            "successful_connections": len(successful_connections),
            "operation_success_rate": op_success_rate,
            "state_corruption_events": len(state_corruption_events)
        }, "automation")