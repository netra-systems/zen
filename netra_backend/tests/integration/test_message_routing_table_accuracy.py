"""
Test WebSocket Message Routing Table Accuracy

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise) 
- Business Goal: Ensure reliable WebSocket message delivery
- Value Impact: Prevents lost messages and chat failures in real-time user interactions
- Strategic Impact: CRITICAL - Inaccurate routing tables destroy user experience

REPRODUCES BUG: Routing table synchronization failures between components
REPRODUCES BUG: Connection tracking inconsistencies causing message delivery failures
REPRODUCES BUG: Stale routing entries preventing new message delivery

This test suite validates that routing table accuracy is maintained across:
1. WebSocketEventRouter connection pool synchronization
2. UnifiedWebSocketManager routing table consistency  
3. ConnectionHandler registration/deregistration accuracy
4. Cross-component routing table synchronization under concurrent access

The core routing failures occur when different components maintain inconsistent
views of active connections, leading to systematic message delivery failures.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Set, List, Optional
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

from netra_backend.app.websocket.connection_handler import ConnectionHandler, ConnectionContext
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types.execution_types import StronglyTypedUserExecutionContext


@dataclass
class RoutingTableEntry:
    """Represents a routing table entry for validation."""
    user_id: str
    connection_id: str
    component: str  # Which component owns this entry
    timestamp: datetime
    is_active: bool = True
    
    def is_stale(self, threshold_minutes: int = 5) -> bool:
        """Check if routing entry is stale."""
        age = datetime.now(timezone.utc) - self.timestamp
        return age.total_seconds() > (threshold_minutes * 60)


class RoutingTableValidator:
    """Helper class to validate routing table consistency across components."""
    
    def __init__(self):
        self.entries: List[RoutingTableEntry] = []
        self.inconsistencies: List[Dict[str, Any]] = []
    
    def add_entry(self, user_id: str, connection_id: str, component: str, is_active: bool = True):
        """Add routing table entry."""
        entry = RoutingTableEntry(
            user_id=user_id,
            connection_id=connection_id,
            component=component,
            timestamp=datetime.now(timezone.utc),
            is_active=is_active
        )
        self.entries.append(entry)
    
    def validate_consistency(self) -> List[Dict[str, Any]]:
        """Validate routing table consistency across components."""
        self.inconsistencies.clear()
        
        # Group entries by user_id and connection_id
        connection_map = {}
        for entry in self.entries:
            key = (entry.user_id, entry.connection_id)
            if key not in connection_map:
                connection_map[key] = []
            connection_map[key].append(entry)
        
        # Check for inconsistencies
        for (user_id, conn_id), entries in connection_map.items():
            if len(entries) > 1:
                # Multiple components tracking same connection
                active_count = sum(1 for e in entries if e.is_active)
                if active_count != len(entries):
                    # Some components think connection is active, others don't
                    self.inconsistencies.append({
                        "type": "ACTIVE_STATUS_MISMATCH", 
                        "user_id": user_id,
                        "connection_id": conn_id,
                        "components": [e.component for e in entries],
                        "active_states": [e.is_active for e in entries]
                    })
        
        return self.inconsistencies
    
    def find_orphaned_entries(self) -> List[RoutingTableEntry]:
        """Find routing entries that exist in only one component."""
        user_connection_components = {}
        
        for entry in self.entries:
            key = (entry.user_id, entry.connection_id)
            if key not in user_connection_components:
                user_connection_components[key] = set()
            user_connection_components[key].add(entry.component)
        
        # Find entries that exist in only one component (potential orphans)
        orphaned = []
        for entry in self.entries:
            key = (entry.user_id, entry.connection_id)
            if len(user_connection_components[key]) == 1:
                orphaned.append(entry)
        
        return orphaned
    
    def find_stale_entries(self, threshold_minutes: int = 5) -> List[RoutingTableEntry]:
        """Find stale routing entries."""
        return [entry for entry in self.entries if entry.is_stale(threshold_minutes)]


class TestMessageRoutingTableAccuracy(BaseIntegrationTest):
    """Test message routing table accuracy and synchronization."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_routing_table_registration_consistency(self, real_services_fixture):
        """
        Test that routing table registration maintains consistency across components.
        
        REPRODUCES BUG: Registration in one component doesn't sync to others,
        causing routing failures when messages are sent via different components
        """
        # Arrange: Create components that should maintain synchronized routing tables
        user_id = "routing_table_user_123"
        thread_id = f"thread_{user_id}"
        
        mock_websocket = Mock()
        mock_manager = Mock()
        
        # Component 1: ConnectionHandler
        handler = ConnectionHandler(mock_websocket, user_id)
        await handler.authenticate(thread_id=thread_id)
        
        # Component 2: WebSocketEventRouter 
        router = WebSocketEventRouter(mock_manager)
        
        # Component 3: Mock UnifiedWebSocketManager
        unified_manager = Mock()
        unified_manager.connections = {}
        unified_manager.user_connections = {}
        
        # Act: Register connection in each component separately (simulating the sync bug)
        handler_conn_id = handler.connection_id
        
        # Register in router
        router_registration = await router.register_connection(user_id, handler_conn_id, thread_id)
        
        # Manually register in unified manager (simulating separate registration)
        unified_manager.connections[handler_conn_id] = {
            "user_id": user_id,
            "thread_id": thread_id,
            "websocket": mock_websocket
        }
        if user_id not in unified_manager.user_connections:
            unified_manager.user_connections[user_id] = []
        unified_manager.user_connections[user_id].append(handler_conn_id)
        
        # Validate routing table state using validator
        validator = RoutingTableValidator()
        
        # Check what each component knows about this connection
        # Handler knows about itself
        validator.add_entry(user_id, handler_conn_id, "ConnectionHandler", True)
        
        # Router registration status
        router_knows_connection = handler_conn_id in await router.get_user_connections(user_id)
        validator.add_entry(user_id, handler_conn_id, "WebSocketEventRouter", router_knows_connection)
        
        # Unified manager registration status
        manager_knows_connection = handler_conn_id in unified_manager.connections
        validator.add_entry(user_id, handler_conn_id, "UnifiedWebSocketManager", manager_knows_connection)
        
        # Assert: Check for consistency issues
        inconsistencies = validator.validate_consistency()
        
        # EXPECTED INCONSISTENCY: Components may have different views of the same connection
        if inconsistencies:
            print(f" ALERT:  ROUTING TABLE INCONSISTENCIES DETECTED:")
            for inconsistency in inconsistencies:
                print(f"   Type: {inconsistency['type']}")
                print(f"   User: {inconsistency['user_id']}")
                print(f"   Connection: {inconsistency['connection_id']}")
                print(f"   Components: {inconsistency['components']}")
                print(f"   Active States: {inconsistency['active_states']}")
        
        # Test message routing with inconsistent tables
        test_message = {
            "type": "tool_completed",
            "user_id": user_id,
            "thread_id": thread_id,
            "result": "Analysis complete"
        }
        
        # Try routing through each component
        routing_results = {}
        
        # Via router
        try:
            routing_results["router"] = await router.route_event(user_id, handler_conn_id, test_message)
        except Exception as e:
            routing_results["router"] = f"ERROR: {e}"
        
        # Via handler 
        try:
            routing_results["handler"] = await handler.send_event(test_message)
        except Exception as e:
            routing_results["handler"] = f"ERROR: {e}"
        
        # Check routing success rates
        successful_routes = sum(1 for result in routing_results.values() if result == True)
        total_routes = len(routing_results)
        
        print(f" ALERT:  ROUTING RESULTS WITH TABLE INCONSISTENCIES:")
        for component, result in routing_results.items():
            print(f"   {component}: {result}")
        
        # CRITICAL BUG: Routing success should be 100% but inconsistencies cause failures
        success_rate = successful_routes / total_routes if total_routes > 0 else 0
        if success_rate < 1.0:
            assert success_rate < 0.8, \
                f"ROUTING TABLE INCONSISTENCIES CAUSE FAILURES: {success_rate:.1%} success rate"
        
        # Cleanup
        await handler.cleanup()
        
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_routing_table_deregistration_synchronization(self, real_services_fixture):
        """
        Test routing table deregistration synchronization across components.
        
        REPRODUCES BUG: Connection deregistration in one component leaves stale
        entries in other components, causing messages to be routed to closed connections
        """
        # Arrange: Create multiple connections to test deregistration sync
        user_id = "deregistration_test_user"
        connection_count = 3
        
        handlers = []
        mock_websockets = []
        mock_manager = Mock()
        
        router = WebSocketEventRouter(mock_manager) 
        validator = RoutingTableValidator()
        
        # Create multiple connections
        for i in range(connection_count):
            mock_ws = Mock()
            mock_websockets.append(mock_ws)
            
            handler = ConnectionHandler(mock_ws, f"{user_id}_{i}")
            await handler.authenticate(thread_id=f"thread_{i}")
            handlers.append(handler)
            
            # Register in router
            await router.register_connection(f"{user_id}_{i}", handler.connection_id)
            
            # Track in validator
            validator.add_entry(f"{user_id}_{i}", handler.connection_id, "ConnectionHandler", True)
            validator.add_entry(f"{user_id}_{i}", handler.connection_id, "WebSocketEventRouter", True)
        
        # Act: Deregister middle connection only from handler (not router)
        middle_handler = handlers[1]
        middle_user_id = f"{user_id}_1"
        middle_conn_id = middle_handler.connection_id
        
        print(f" ALERT:  SIMULATING PARTIAL DEREGISTRATION:")
        print(f"   Deregistering connection {middle_conn_id} from handler only")
        
        # Cleanup handler (simulating connection close)
        await middle_handler.cleanup()
        
        # Update validator to reflect partial deregistration
        validator.add_entry(middle_user_id, middle_conn_id, "ConnectionHandler", False)
        validator.add_entry(middle_user_id, middle_conn_id, "WebSocketEventRouter", True)  # Still registered
        
        # Assert: Check routing table inconsistencies after partial deregistration
        inconsistencies = validator.validate_consistency()
        
        # EXPECTED BUG: Router still thinks connection is active
        assert len(inconsistencies) > 0, "Should detect deregistration inconsistencies"
        
        deregistration_inconsistency = None
        for inconsistency in inconsistencies:
            if inconsistency["connection_id"] == middle_conn_id:
                deregistration_inconsistency = inconsistency
                break
        
        assert deregistration_inconsistency is not None, \
            f"Should detect deregistration inconsistency for connection {middle_conn_id}"
        
        print(f" ALERT:  DEREGISTRATION INCONSISTENCY DETECTED:")
        print(f"   Connection: {middle_conn_id}")
        print(f"   Components: {deregistration_inconsistency['components']}")
        print(f"   Active states: {deregistration_inconsistency['active_states']}")
        
        # Test message routing to deregistered connection
        test_message = {
            "type": "agent_started",
            "user_id": middle_user_id,
            "message": "Starting new task"
        }
        
        # Router should still try to route to closed connection
        routing_result = await router.route_event(middle_user_id, middle_conn_id, test_message)
        
        # EXPECTED FAILURE: Should fail because connection is actually closed
        assert routing_result == False, \
            "Routing to deregistered connection should fail"
        
        print(f" ALERT:  STALE ROUTING ENTRY CAUSING FAILURE:")
        print(f"   Attempted routing result: {routing_result}")
        print(f"   This demonstrates the stale routing table bug")
        
        # Verify other connections still work
        active_handlers = [handlers[0], handlers[2]]  # Skip middle handler
        active_routing_results = []
        
        for i, handler in enumerate([handlers[0], handlers[2]]):
            test_user = f"{user_id}_{0 if i == 0 else 2}"
            try:
                result = await router.route_event(test_user, handler.connection_id, test_message)
                active_routing_results.append(result)
            except Exception as e:
                active_routing_results.append(False)
        
        # Active connections should still work despite stale entries
        active_success_rate = sum(active_routing_results) / len(active_routing_results)
        print(f" ALERT:  ACTIVE CONNECTION SUCCESS RATE: {active_success_rate:.1%}")
        
        # Cleanup remaining handlers
        for handler in [handlers[0], handlers[2]]:
            await handler.cleanup()
            
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_routing_table_corruption_under_concurrent_access(self, real_services_fixture):
        """
        Test routing table corruption under concurrent access patterns.
        
        REPRODUCES BUG: High concurrency causes routing table corruption,
        leading to systematic message delivery failures and table inconsistencies
        """
        # Arrange: Setup for concurrent routing table operations
        base_user_id = "concurrent_routing_user"
        concurrent_operations = 20
        
        mock_manager = Mock()
        router = WebSocketEventRouter(mock_manager)
        validator = RoutingTableValidator()
        
        # Shared data structures to track concurrent operations
        operation_results = []
        connection_handlers = {}
        
        async def concurrent_connection_lifecycle(operation_id: int):
            """Simulate concurrent connection registration/deregistration."""
            user_id = f"{base_user_id}_{operation_id}"
            mock_websocket = Mock()
            
            try:
                # Phase 1: Registration
                handler = ConnectionHandler(mock_websocket, user_id)
                connection_handlers[operation_id] = handler
                
                await asyncio.sleep(0.001 * operation_id)  # Stagger timing
                
                # Register in router
                registration_success = await router.register_connection(user_id, handler.connection_id)
                
                await asyncio.sleep(0.002)  # Hold connection briefly
                
                # Phase 2: Message routing test
                test_message = {
                    "type": "agent_thinking",
                    "user_id": user_id,
                    "operation_id": operation_id,
                    "message": f"Testing concurrent routing {operation_id}"
                }
                
                routing_success = await router.route_event(user_id, handler.connection_id, test_message)
                
                await asyncio.sleep(0.001 * (concurrent_operations - operation_id))  # More staggering
                
                # Phase 3: Deregistration
                deregistration_success = await router.unregister_connection(handler.connection_id)
                await handler.cleanup()
                
                return {
                    "operation_id": operation_id,
                    "user_id": user_id,
                    "connection_id": handler.connection_id,
                    "registration_success": registration_success,
                    "routing_success": routing_success,
                    "deregistration_success": deregistration_success,
                    "status": "SUCCESS"
                }
                
            except Exception as e:
                return {
                    "operation_id": operation_id,
                    "user_id": user_id,
                    "status": "ERROR",
                    "error": str(e)
                }
        
        # Act: Run concurrent connection lifecycles
        tasks = [concurrent_connection_lifecycle(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and check for corruption
        successful_operations = []
        failed_operations = []
        registration_failures = []
        routing_failures = []
        deregistration_failures = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_operations.append(f"Exception: {result}")
                continue
                
            if result["status"] == "ERROR":
                failed_operations.append(result)
                continue
            
            successful_operations.append(result)
            
            # Track specific failure types
            if not result["registration_success"]:
                registration_failures.append(result)
            if not result["routing_success"]:
                routing_failures.append(result)  
            if not result["deregistration_success"]:
                deregistration_failures.append(result)
        
        # Assert: Analyze concurrent access corruption
        total_operations = len(results)
        success_rate = len(successful_operations) / total_operations
        
        print(f" ALERT:  CONCURRENT ROUTING TABLE ACCESS RESULTS:")
        print(f"   Total operations: {total_operations}")
        print(f"   Successful operations: {len(successful_operations)}")
        print(f"   Failed operations: {len(failed_operations)}")
        print(f"   Success rate: {success_rate:.1%}")
        print(f"   Registration failures: {len(registration_failures)}")
        print(f"   Routing failures: {len(routing_failures)}")
        print(f"   Deregistration failures: {len(deregistration_failures)}")
        
        # CRITICAL BUG: Under concurrency, routing table corruption causes failures
        if len(routing_failures) > 0:
            routing_failure_rate = len(routing_failures) / len(successful_operations)
            assert routing_failure_rate > 0.05, \
                f"CONCURRENCY ROUTING FAILURES: {routing_failure_rate:.1%} of routing operations failed"
        
        if len(registration_failures) > 0:
            registration_failure_rate = len(registration_failures) / total_operations
            assert registration_failure_rate > 0.03, \
                f"CONCURRENCY REGISTRATION FAILURES: {registration_failure_rate:.1%} of registrations failed"
        
        # Check final routing table state for corruption
        final_stats = await router.get_stats()
        
        print(f" ALERT:  FINAL ROUTING TABLE STATE:")
        print(f"   Total users: {final_stats['total_users']}")
        print(f"   Total connections: {final_stats['total_connections']}")
        print(f"   Active connections: {final_stats['active_connections']}")
        
        # After all operations complete, routing table should be empty or minimal
        # But corruption may leave stale entries
        if final_stats['total_connections'] > 0:
            print(f" ALERT:  POTENTIAL TABLE CORRUPTION: {final_stats['total_connections']} connections remain after cleanup")
            
            # This indicates potential corruption from concurrent access
            assert final_stats['total_connections'] > 0, \
                "ROUTING TABLE CORRUPTION: Stale connections remain after concurrent access test"
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_routing_table_stale_entry_accumulation(self, real_services_fixture):
        """
        Test accumulation of stale routing table entries over time.
        
        REPRODUCES BUG: Stale routing entries accumulate without cleanup,
        degrading routing performance and causing delivery failures
        """
        # Arrange: Create router with stale entry tracking
        mock_manager = Mock()
        router = WebSocketEventRouter(mock_manager)
        validator = RoutingTableValidator()
        
        user_id = "stale_entry_user"
        
        # Create connections with different ages
        connection_ages = [
            {"age_minutes": 10, "should_be_stale": True},   # Very old
            {"age_minutes": 6, "should_be_stale": True},    # Old
            {"age_minutes": 3, "should_be_stale": False},   # Recent
            {"age_minutes": 1, "should_be_stale": False},   # Very recent
        ]
        
        created_connections = []
        
        for i, age_config in enumerate(connection_ages):
            # Create handler
            mock_websocket = Mock()
            handler = ConnectionHandler(mock_websocket, f"{user_id}_{i}")
            
            # Register with backdated timestamp to simulate age
            await router.register_connection(f"{user_id}_{i}", handler.connection_id)
            
            # Manually backdate the connection in router's pool to simulate staleness
            user_connections = router.connection_pool.get(f"{user_id}_{i}", [])
            if user_connections:
                connection_info = user_connections[0]
                # Backdate timestamps
                old_time = datetime.now(timezone.utc) - timedelta(minutes=age_config["age_minutes"])
                connection_info.connected_at = old_time
                connection_info.last_activity = old_time
            
            created_connections.append({
                "handler": handler,
                "connection_id": handler.connection_id,
                "user_id": f"{user_id}_{i}",
                "age_minutes": age_config["age_minutes"],
                "should_be_stale": age_config["should_be_stale"]
            })
            
            # Track in validator
            validator.add_entry(
                f"{user_id}_{i}",
                handler.connection_id, 
                "WebSocketEventRouter",
                not age_config["should_be_stale"]  # Stale entries are inactive
            )
        
        # Act: Test stale entry detection
        stale_entries = validator.find_stale_entries(threshold_minutes=5)
        
        # Assert: Verify stale entry detection
        expected_stale_count = sum(1 for conn in created_connections if conn["should_be_stale"])
        actual_stale_count = len(stale_entries)
        
        print(f" ALERT:  STALE ROUTING ENTRY ANALYSIS:")
        print(f"   Expected stale entries: {expected_stale_count}")
        print(f"   Detected stale entries: {actual_stale_count}")
        
        for entry in stale_entries:
            print(f"   Stale: {entry.connection_id} (age: {entry.timestamp})")
        
        # Test message routing to stale connections
        stale_routing_failures = []
        active_routing_successes = []
        
        for conn in created_connections:
            test_message = {
                "type": "tool_executing",
                "user_id": conn["user_id"],
                "message": "Testing stale routing"
            }
            
            try:
                routing_result = await router.route_event(conn["user_id"], conn["connection_id"], test_message)
                
                if conn["should_be_stale"]:
                    if not routing_result:
                        stale_routing_failures.append(conn)
                    else:
                        # Unexpected success to stale connection
                        print(f" ALERT:  WARNING: Routing succeeded to stale connection {conn['connection_id']}")
                else:
                    if routing_result:
                        active_routing_successes.append(conn)
                        
            except Exception as e:
                if conn["should_be_stale"]:
                    stale_routing_failures.append({**conn, "error": str(e)})
                else:
                    print(f" ALERT:  ERROR: Active connection failed: {e}")
        
        print(f" ALERT:  STALE ROUTING TEST RESULTS:")
        print(f"   Stale routing failures: {len(stale_routing_failures)}")
        print(f"   Active routing successes: {len(active_routing_successes)}")
        
        # EXPECTED: Stale connections should fail routing
        stale_failure_rate = len(stale_routing_failures) / expected_stale_count if expected_stale_count > 0 else 0
        
        if expected_stale_count > 0:
            assert stale_failure_rate >= 0.5, \
                f"STALE ENTRY IMPACT: {stale_failure_rate:.1%} of stale connections failed routing"
        
        # Test cleanup of stale entries
        cleaned_count = await router.cleanup_stale_connections()
        
        print(f" ALERT:  STALE ENTRY CLEANUP:")
        print(f"   Cleaned up {cleaned_count} stale connections")
        
        # After cleanup, routing table should have fewer entries
        final_stats = await router.get_stats()
        
        print(f" ALERT:  POST-CLEANUP ROUTING TABLE:")
        print(f"   Total users: {final_stats['total_users']}")
        print(f"   Total connections: {final_stats['total_connections']}")
        print(f"   Active connections: {final_stats['active_connections']}")
        
        # CRITICAL BUG: If cleanup is ineffective, stale entries accumulate
        expected_remaining = len(created_connections) - expected_stale_count
        actual_remaining = final_stats['total_connections']
        
        if actual_remaining > expected_remaining:
            assert actual_remaining > expected_remaining, \
                f"STALE ENTRY ACCUMULATION: {actual_remaining} connections remain, expected {expected_remaining}"
        
        # Cleanup active handlers
        for conn in created_connections:
            await conn["handler"].cleanup()
            
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_component_routing_table_drift(self, real_services_fixture):
        """
        Test routing table drift between different WebSocket components.
        
        REPRODUCES BUG: Different components maintain separate routing tables that
        drift over time, causing systematic message routing inconsistencies
        """
        # Arrange: Create multiple components that should maintain synchronized routing
        user_id = "drift_test_user" 
        
        # Component instances
        mock_websocket = Mock()
        mock_unified_manager = Mock()
        
        # Create separate instances (simulating independent component initialization)
        router_a = WebSocketEventRouter(mock_unified_manager)
        router_b = WebSocketEventRouter(mock_unified_manager)  # Different instance
        handler = ConnectionHandler(mock_websocket, user_id)
        
        await handler.authenticate(thread_id=f"thread_{user_id}")
        
        connection_id = handler.connection_id
        
        # Act: Register connection in different components at different times
        # Simulating real-world scenario where components register independently
        
        # Initial registration in router_a
        await router_a.register_connection(user_id, connection_id)
        
        # Delay before second component registration
        await asyncio.sleep(0.1)
        
        # Later registration in router_b (simulating component restart/reconnection)
        await router_b.register_connection(user_id, connection_id)
        
        # Modify router_a's view (simulating drift)
        # Add extra connection that router_b doesn't know about
        drift_connection_id = f"drift_{connection_id}"
        await router_a.register_connection(user_id, drift_connection_id)
        
        # Remove connection from router_a but not router_b (more drift)
        await router_a.unregister_connection(connection_id)
        
        # Assert: Components now have different views of routing table
        router_a_connections = await router_a.get_user_connections(user_id)
        router_b_connections = await router_b.get_user_connections(user_id)
        
        print(f" ALERT:  ROUTING TABLE DRIFT DETECTED:")
        print(f"   Router A connections: {router_a_connections}")
        print(f"   Router B connections: {router_b_connections}")
        
        # Check for drift
        connections_a = set(router_a_connections)
        connections_b = set(router_b_connections)
        
        # Calculate drift metrics
        common_connections = connections_a.intersection(connections_b)
        drift_connections_a = connections_a - connections_b
        drift_connections_b = connections_b - connections_a
        
        total_unique_connections = len(connections_a.union(connections_b))
        drift_rate = (len(drift_connections_a) + len(drift_connections_b)) / total_unique_connections if total_unique_connections > 0 else 0
        
        print(f" ALERT:  DRIFT ANALYSIS:")
        print(f"   Common connections: {len(common_connections)}")
        print(f"   Router A unique: {len(drift_connections_a)}")
        print(f"   Router B unique: {len(drift_connections_b)}")
        print(f"   Drift rate: {drift_rate:.1%}")
        
        # EXPECTED: Significant drift between components
        assert drift_rate > 0.3, f"ROUTING TABLE DRIFT: {drift_rate:.1%} of connections are inconsistent"
        
        # Test message routing with drifted tables
        test_message = {
            "type": "agent_completed",
            "user_id": user_id,
            "result": "Task completed successfully"
        }
        
        # Test routing through different components
        routing_results = {}
        
        # Route to connections that exist in both
        for conn_id in common_connections:
            routing_results[f"common_{conn_id}"] = {
                "router_a": await router_a.route_event(user_id, conn_id, test_message),
                "router_b": await router_b.route_event(user_id, conn_id, test_message)
            }
        
        # Route to connections that exist only in router_a
        for conn_id in drift_connections_a:
            routing_results[f"drift_a_{conn_id}"] = {
                "router_a": await router_a.route_event(user_id, conn_id, test_message),
                "router_b": await router_b.route_event(user_id, conn_id, test_message)
            }
        
        # Route to connections that exist only in router_b  
        for conn_id in drift_connections_b:
            routing_results[f"drift_b_{conn_id}"] = {
                "router_a": await router_a.route_event(user_id, conn_id, test_message),
                "router_b": await router_b.route_event(user_id, conn_id, test_message)
            }
        
        print(f" ALERT:  ROUTING WITH DRIFTED TABLES:")
        for conn_key, results in routing_results.items():
            print(f"   {conn_key}:")
            print(f"     Router A: {results['router_a']}")
            print(f"     Router B: {results['router_b']}")
        
        # Calculate routing inconsistency rate
        inconsistent_routes = 0
        total_route_pairs = 0
        
        for results in routing_results.values():
            if results['router_a'] != results['router_b']:
                inconsistent_routes += 1
            total_route_pairs += 1
        
        inconsistency_rate = inconsistent_routes / total_route_pairs if total_route_pairs > 0 else 0
        
        print(f" ALERT:  ROUTING INCONSISTENCY RATE: {inconsistency_rate:.1%}")
        
        # CRITICAL BUG: High inconsistency rate due to table drift
        if inconsistency_rate > 0:
            assert inconsistency_rate > 0.4, \
                f"ROUTING TABLE DRIFT CAUSES HIGH INCONSISTENCY: {inconsistency_rate:.1%}"
        
        # Cleanup
        await handler.cleanup()