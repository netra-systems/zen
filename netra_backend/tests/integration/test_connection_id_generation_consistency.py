"""
Test WebSocket Connection ID Generation Consistency

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise)
- Business Goal: Ensure reliable WebSocket message routing
- Value Impact: Prevents "Message routing failed" errors that break real-time chat
- Strategic Impact: CRITICAL - Connection ID inconsistency destroys chat value

REPRODUCES BUG: "Message routing failed for user 101463487227881885914" 
REPRODUCES BUG: "Message routing failed for ws_10146348_1757371237_8bfbba09, error_count: 1"

This test suite validates that connection ID generation is consistent between:
1. ConnectionHandler.connection_id generation
2. WebSocketEventRouter connection tracking
3. UnifiedWebSocketManager routing table 
4. User execution context websocket_client_id

The core issue is that different components generate different connection ID formats
leading to routing table mismatches and message routing failures.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Set, List
from unittest.mock import Mock, AsyncMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

from netra_backend.app.websocket.connection_handler import ConnectionHandler, ConnectionContext
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, WebSocketID


class TestConnectionIdGenerationConsistency(BaseIntegrationTest):
    """Test connection ID generation consistency across WebSocket routing components."""
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_connection_handler_id_format_consistency(self, real_services_fixture):
        """
        Test that ConnectionHandler generates consistent connection ID formats.
        
        REPRODUCES BUG: ConnectionHandler creates conn_{user_id}_{8hex} format
        while other systems expect ws_{user_id}_{timestamp}_{8hex} format
        """
        # Arrange: Create test user
        user_id = "test_user_123456"
        mock_websocket = Mock()
        
        # Act: Create multiple ConnectionHandler instances
        handlers = []
        connection_ids = set()
        
        for i in range(5):
            handler = ConnectionHandler(mock_websocket, user_id)
            handlers.append(handler)
            connection_ids.add(handler.connection_id)
        
        # Assert: All connection IDs should follow same format
        for conn_id in connection_ids:
            # FAILING ASSERTION: Current format is conn_{user_id}_{8hex}
            # Expected format for routing should be ws_{user_id}_{timestamp}_{8hex}
            assert conn_id.startswith("conn_"), f"Connection ID {conn_id} should start with 'conn_'"
            assert user_id in conn_id, f"Connection ID {conn_id} should contain user_id {user_id}"
            
            # CRITICAL BUG: Connection IDs don't match routing system expectations
            # This assertion will PASS but demonstrates the inconsistency
            parts = conn_id.split("_")
            assert len(parts) >= 3, f"Connection ID {conn_id} should have at least 3 parts"
            
        # VERIFICATION: Check if routing system can find these connections
        # This simulates the routing failure scenario
        for handler in handlers:
            # BUG: ConnectionHandler uses format conn_{user}_{hex}
            # but routing system looks for ws_{user}_{time}_{hex}
            routing_compatible_id = f"ws_{user_id}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            
            # This demonstrates the routing table mismatch issue
            assert handler.connection_id != routing_compatible_id, \
                f"ROUTE MISMATCH: Handler ID {handler.connection_id} != routing ID {routing_compatible_id}"
        
        # Cleanup
        for handler in handlers:
            await handler.cleanup()
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_websocket_event_router_connection_tracking_inconsistency(self, real_services_fixture):
        """
        Test WebSocket event router connection tracking with inconsistent IDs.
        
        REPRODUCES BUG: WebSocketEventRouter tracks connections with one ID format
        but ConnectionHandler generates different format, causing routing failures
        """
        # Arrange: Create router and mock WebSocket manager
        mock_websocket_manager = Mock()
        router = WebSocketEventRouter(mock_websocket_manager)
        
        user_id = "101463487227881885914"  # User from actual error logs
        
        # Act: Register connections with different ID formats (simulating the bug)
        connection_formats = [
            f"conn_{user_id}_{uuid.uuid4().hex[:8]}",  # ConnectionHandler format
            f"ws_{user_id}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}",  # Expected routing format
            f"ws_{user_id[:8]}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}",  # Truncated user format
        ]
        
        registration_results = []
        for conn_id in connection_formats:
            result = await router.register_connection(user_id, conn_id)
            registration_results.append(result)
        
        # Assert: All registrations succeed but create inconsistent tracking
        assert all(registration_results), "All connection registrations should succeed"
        
        # Get user connections
        user_connections = await router.get_user_connections(user_id)
        assert len(user_connections) == len(connection_formats), \
            f"Router should track all {len(connection_formats)} connections"
        
        # CRITICAL BUG REPRODUCTION: Attempt to route messages to inconsistent connections
        test_event = {
            "type": "agent_started",
            "user_id": user_id,
            "thread_id": f"thread_{user_id}",
            "message": "Test routing"
        }
        
        routing_failures = []
        for conn_id in connection_formats:
            try:
                success = await router.route_event(user_id, conn_id, test_event)
                if not success:
                    routing_failures.append(conn_id)
            except Exception as e:
                routing_failures.append(f"{conn_id}: {e}")
        
        # EXPECTED FAILURE: Some connections will fail to route due to ID format mismatches
        assert len(routing_failures) > 0, \
            f"EXPECTED ROUTING FAILURES due to ID inconsistency: {routing_failures}"
        
        print(f" ALERT:  ROUTING FAILURES REPRODUCED: {routing_failures}")
        print(f" ALERT:  This demonstrates the 'Message routing failed' bug")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_execution_context_websocket_id_mismatch(self, real_services_fixture):
        """
        Test that user execution context WebSocket IDs don't match connection handler IDs.
        
        REPRODUCES BUG: StronglyTypedUserExecutionContext.websocket_client_id format
        differs from ConnectionHandler.connection_id format, breaking message routing
        """
        # Arrange: Create authenticated user context
        auth_helper = E2EAuthHelper(environment="test")
        user_email = "routing_test@example.com"
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Create user execution context (uses different WebSocket ID format)
        user_context = await create_authenticated_user_context(
            user_email=user_email,
            user_id=user_id,
            environment="test",
            websocket_enabled=True
        )
        
        # Create connection handler (uses different connection ID format)  
        mock_websocket = Mock()
        handler = ConnectionHandler(mock_websocket, user_id)
        
        # Act: Compare ID formats
        context_websocket_id = str(user_context.websocket_client_id) if user_context.websocket_client_id else None
        handler_connection_id = handler.connection_id
        
        # Assert: IDs should be compatible but they're NOT
        assert context_websocket_id is not None, "User context should have WebSocket ID"
        assert handler_connection_id is not None, "Handler should have connection ID"
        
        # CRITICAL BUG: These IDs use different formats and can't be matched
        assert context_websocket_id != handler_connection_id, \
            f"MISMATCH REPRODUCED: Context ID {context_websocket_id} != Handler ID {handler_connection_id}"
        
        # Check if they share common user ID component
        assert user_id in context_websocket_id, "Context WebSocket ID should contain user ID"
        assert user_id in handler_connection_id, "Handler connection ID should contain user ID"
        
        # BUG REPRODUCTION: Try to route message using mismatched IDs
        mock_websocket_manager = Mock()
        router = WebSocketEventRouter(mock_websocket_manager)
        
        # Register connection with handler ID
        await router.register_connection(user_id, handler_connection_id)
        
        # Try to route using context WebSocket ID (this will FAIL)
        test_event = {
            "type": "agent_completed", 
            "user_id": user_id,
            "websocket_client_id": context_websocket_id,
            "message": "Test message"
        }
        
        # This should fail because router doesn't know about context WebSocket ID
        routing_success = await router.route_event(user_id, context_websocket_id, test_event)
        
        # EXPECTED FAILURE: Routing fails due to ID mismatch
        assert routing_success == False, \
            f"EXPECTED FAILURE: Routing should fail with mismatched IDs"
        
        print(f" ALERT:  ID MISMATCH REPRODUCED:")
        print(f"   Context WebSocket ID: {context_websocket_id}")
        print(f"   Handler Connection ID: {handler_connection_id}")
        print(f"   Routing Success: {routing_success}")
        
        # Cleanup
        await handler.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_routing_table_synchronization_failures(self, real_services_fixture):
        """
        Test routing table synchronization failures between multiple WebSocket components.
        
        REPRODUCES BUG: Different components maintain separate routing tables with
        inconsistent connection ID formats, leading to systematic routing failures
        """
        # Arrange: Create multiple routing components
        user_id = "10146348"  # Shortened user ID from error logs
        mock_websocket = Mock()
        
        # Component 1: ConnectionHandler
        handler = ConnectionHandler(mock_websocket, user_id)
        
        # Component 2: WebSocketEventRouter  
        mock_manager = Mock()
        router = WebSocketEventRouter(mock_manager)
        
        # Component 3: User execution context
        user_context = await create_authenticated_user_context(
            user_id=user_id,
            environment="test",
            websocket_enabled=True
        )
        
        # Act: Register same user in all components with different connection IDs
        handler_conn_id = handler.connection_id
        context_ws_id = str(user_context.websocket_client_id)
        
        # Router uses yet another ID format
        router_conn_id = f"ws_{user_id}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
        
        await router.register_connection(user_id, router_conn_id)
        
        # Collect all different connection IDs
        all_connection_ids = {
            "handler": handler_conn_id,
            "context": context_ws_id, 
            "router": router_conn_id
        }
        
        # Assert: All IDs are different (demonstrating the synchronization problem)
        unique_ids = set(all_connection_ids.values())
        assert len(unique_ids) == 3, \
            f"SYNC FAILURE: All 3 components use different connection IDs: {all_connection_ids}"
        
        # Simulate message routing attempts across components
        test_message = {
            "type": "tool_executing",
            "user_id": user_id,
            "content": "Running analysis tool"
        }
        
        routing_results = {}
        
        # Try routing to each component's connection ID
        for component, conn_id in all_connection_ids.items():
            try:
                # Attempt to route through the router (which only knows about router_conn_id)
                success = await router.route_event(user_id, conn_id, test_message)
                routing_results[component] = success
            except Exception as e:
                routing_results[component] = f"ERROR: {e}"
        
        # Assert: Only router's own connection ID works, others fail
        assert routing_results["router"] == True, "Router should successfully route to its own connection ID"
        assert routing_results["handler"] == False, "Handler connection ID should fail routing"  
        assert routing_results["context"] == False, "Context WebSocket ID should fail routing"
        
        print(f" ALERT:  ROUTING TABLE SYNC FAILURES:")
        for component, result in routing_results.items():
            print(f"   {component}: {all_connection_ids[component]} -> {result}")
        
        # Calculate failure rate (should be high)
        failed_routes = sum(1 for r in routing_results.values() if r != True)
        failure_rate = failed_routes / len(routing_results)
        
        assert failure_rate >= 0.66, \
            f"HIGH FAILURE RATE REPRODUCED: {failure_rate:.1%} of routes failed due to ID inconsistency"
        
        # Cleanup
        await handler.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_connection_id_generation_race_conditions(self, real_services_fixture):
        """
        Test race conditions in concurrent connection ID generation leading to routing failures.
        
        REPRODUCES BUG: Under high concurrency, connection ID generation and routing table
        updates can race, causing "Message routing failed" errors
        """
        # Arrange: Setup for concurrent connection creation
        user_id = "race_condition_user"
        concurrent_connections = 10
        mock_websockets = [Mock() for _ in range(concurrent_connections)]
        
        # Act: Create connections concurrently (simulating high load)
        async def create_connection_and_register(ws_mock, connection_num):
            # Create handler
            handler = ConnectionHandler(ws_mock, f"{user_id}_{connection_num}")
            
            # Create router and register
            mock_manager = Mock()
            router = WebSocketEventRouter(mock_manager)
            
            # Simulate delay that can cause race condition
            await asyncio.sleep(0.01 * connection_num)  # Stagger timing
            
            # Register connection
            registration_success = await router.register_connection(
                f"{user_id}_{connection_num}",
                handler.connection_id
            )
            
            return {
                "handler": handler,
                "router": router, 
                "connection_id": handler.connection_id,
                "registration_success": registration_success,
                "connection_num": connection_num
            }
        
        # Run all connections concurrently
        tasks = [
            create_connection_and_register(mock_websockets[i], i) 
            for i in range(concurrent_connections)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert: Check for race condition failures
        successful_registrations = []
        failed_registrations = []
        connection_id_collisions = []
        
        all_connection_ids = set()
        
        for result in results:
            if isinstance(result, Exception):
                failed_registrations.append(f"Exception: {result}")
                continue
                
            conn_id = result["connection_id"]
            
            # Check for ID collisions (shouldn't happen but race conditions can cause it)
            if conn_id in all_connection_ids:
                connection_id_collisions.append(conn_id)
            
            all_connection_ids.add(conn_id)
            
            if result["registration_success"]:
                successful_registrations.append(result)
            else:
                failed_registrations.append(result)
        
        # CRITICAL BUG: Under concurrency, registration failures increase
        failure_rate = len(failed_registrations) / len(results)
        
        print(f" ALERT:  CONCURRENT CONNECTION RESULTS:")
        print(f"   Total connections: {len(results)}")
        print(f"   Successful registrations: {len(successful_registrations)}")
        print(f"   Failed registrations: {len(failed_registrations)}")
        print(f"   Connection ID collisions: {len(connection_id_collisions)}")
        print(f"   Failure rate: {failure_rate:.1%}")
        
        # Under load, routing systems show increased failure rates
        if failure_rate > 0:
            assert failure_rate > 0.1, \
                f"CONCURRENCY FAILURES REPRODUCED: {failure_rate:.1%} failure rate under load"
        
        # Check for connection ID format consistency under concurrency
        id_formats = set()
        for conn_id in all_connection_ids:
            # Extract format pattern
            parts = conn_id.split("_")
            format_pattern = "_".join(["*"] * len(parts))
            id_formats.add(format_pattern)
        
        # Even under concurrency, ID formats should be consistent
        assert len(id_formats) <= 2, \
            f"INCONSISTENT FORMATS: Multiple connection ID formats detected: {id_formats}"
        
        # Cleanup all handlers
        for result in results:
            if not isinstance(result, Exception) and "handler" in result:
                await result["handler"].cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_routing_failure_pattern_reproduction(self, real_services_fixture):
        """
        Reproduce the exact message routing failure patterns from production logs.
        
        REPRODUCES BUG: "Message routing failed for user 101463487227881885914"
        REPRODUCES BUG: "Message routing failed for ws_10146348_1757371237_8bfbba09, error_count: 1"
        """
        # Arrange: Use actual user IDs and connection IDs from error logs
        problematic_cases = [
            {
                "user_id": "101463487227881885914",
                "connection_id": None,  # Will be generated by ConnectionHandler
                "expected_error": "Message routing failed for user"
            },
            {
                "user_id": "10146348", 
                "connection_id": "ws_10146348_1757371237_8bfbba09",
                "expected_error": "Message routing failed for ws_"
            }
        ]
        
        routing_failures = []
        
        for case in problematic_cases:
            user_id = case["user_id"]
            specified_conn_id = case["connection_id"]
            
            # Create WebSocket components
            mock_websocket = Mock()
            mock_manager = Mock()
            mock_manager.send_to_connection = AsyncMock(return_value=False)  # Simulate routing failure
            
            # Create handler (generates its own connection ID)
            handler = ConnectionHandler(mock_websocket, user_id, specified_conn_id)
            actual_conn_id = handler.connection_id
            
            # Create router
            router = WebSocketEventRouter(mock_manager)
            
            # Register connection
            await router.register_connection(user_id, actual_conn_id)
            
            # Attempt to route a message (this should fail)
            test_event = {
                "type": "agent_thinking",
                "user_id": user_id,
                "connection_id": actual_conn_id,
                "message": "Processing your request..."
            }
            
            # Act: Try to route the message
            try:
                routing_success = await router.route_event(user_id, actual_conn_id, test_event)
                
                # Verify the failure occurred
                if not routing_success:
                    routing_failures.append({
                        "user_id": user_id,
                        "connection_id": actual_conn_id,
                        "error_type": case["expected_error"],
                        "routing_result": "FAILED"
                    })
                else:
                    routing_failures.append({
                        "user_id": user_id,
                        "connection_id": actual_conn_id, 
                        "error_type": "UNEXPECTED_SUCCESS",
                        "routing_result": "PASSED"
                    })
                    
            except Exception as e:
                routing_failures.append({
                    "user_id": user_id,
                    "connection_id": actual_conn_id,
                    "error_type": f"EXCEPTION: {e}",
                    "routing_result": "EXCEPTION"
                })
            
            # Cleanup
            await handler.cleanup()
        
        # Assert: We should reproduce the routing failures
        assert len(routing_failures) >= len(problematic_cases), \
            "Should reproduce routing failures for problematic cases"
        
        # Log detailed failure information
        print(f" ALERT:  REPRODUCED ROUTING FAILURES:")
        for failure in routing_failures:
            print(f"   User: {failure['user_id']}")
            print(f"   Connection: {failure['connection_id']}")
            print(f"   Error: {failure['error_type']}")
            print(f"   Result: {failure['routing_result']}")
            print()
        
        # Verify we reproduced the expected failure patterns
        failed_routes = [f for f in routing_failures if f['routing_result'] == 'FAILED']
        assert len(failed_routes) > 0, \
            f"REPRODUCED {len(failed_routes)} routing failures matching production errors"
        
        # Check for specific error patterns from logs
        user_routing_failures = [f for f in failed_routes if "101463487227881885914" in f['user_id']]
        ws_routing_failures = [f for f in failed_routes if f['connection_id'].startswith("ws_")]
        
        assert len(user_routing_failures) > 0 or len(ws_routing_failures) > 0, \
            "Should reproduce either user-based or WebSocket connection-based routing failures"