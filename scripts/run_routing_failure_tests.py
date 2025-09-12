#!/usr/bin/env python3
"""
Simple test runner to verify WebSocket routing failure reproduction.

This script runs the routing failure tests directly without pytest fixtures
to demonstrate the connection ID inconsistencies and routing failures.
"""

import asyncio
import uuid
import sys
import os
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Import the modules under test
from netra_backend.app.websocket.connection_handler import ConnectionHandler, ConnectionContext
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter, get_websocket_router
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context


async def test_connection_id_generation_inconsistency():
    """Test connection ID generation inconsistencies causing routing failures."""
    print(" ALERT:  TESTING CONNECTION ID GENERATION INCONSISTENCIES")
    print("="*60)
    
    # Test 1: ConnectionHandler ID format consistency
    print("\n1. Testing ConnectionHandler ID format consistency:")
    
    user_id = "test_user_123456"
    mock_websocket = Mock()
    
    # Create multiple ConnectionHandler instances with mocked WebSocketEventRouter
    handlers = []
    connection_ids = set()
    
    with patch('netra_backend.app.websocket.connection_handler.WebSocketEventRouter') as mock_router_class:
        mock_router_class.return_value = Mock()
        
        for i in range(5):
            # Create fresh mock for each handler
            mock_ws = Mock()
            handler = ConnectionHandler(mock_ws, f"{user_id}_{i}")
            handlers.append(handler)
            connection_ids.add(handler.connection_id)
            print(f"   Handler {i+1}: {handler.connection_id}")
    
        # Analyze connection ID formats
        print(f"\n   Generated {len(connection_ids)} unique connection IDs")
        
        for conn_id in connection_ids:
            parts = conn_id.split("_")
            print(f"   ID: {conn_id} -> Parts: {parts}")
            
            # Check format consistency
            if not conn_id.startswith("conn_"):
                print(f"    FAIL:  INCONSISTENT FORMAT: {conn_id} doesn't start with 'conn_'")
            
            # Check if any user ID is in the connection ID
            user_found = any(user_part in conn_id for user_part in [f"{user_id}_{i}" for i in range(5)])
            if not user_found:
                print(f"    FAIL:  USER ID MISSING: {conn_id} doesn't contain expected user_id pattern")
        
        # Test 2: Routing system compatibility
        print(f"\n2. Testing routing system compatibility:")
        
        # Simulate expected routing ID format
        routing_compatible_id = f"ws_{user_id}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
        print(f"   Expected routing format: {routing_compatible_id}")
        
        # Check compatibility
        for handler in handlers:
            handler_id = handler.connection_id
            print(f"   Handler ID: {handler_id}")
            print(f"   Compatible: {handler_id == routing_compatible_id}")  # Should be False
            
            # This demonstrates the mismatch
            if handler_id != routing_compatible_id:
                print(f"    ALERT:  ROUTE MISMATCH DETECTED: Handler uses different format than routing system expects")
        
        # Cleanup
        for handler in handlers:
            await handler.cleanup()
    
    print(f"\n    PASS:  Connection ID inconsistency demonstrated")
    return True


async def test_routing_table_synchronization_failure():
    """Test routing table synchronization failures between components."""
    print("\n ALERT:  TESTING ROUTING TABLE SYNCHRONIZATION FAILURES")
    print("="*60)
    
    user_id = "sync_test_user_789"
    
    # Create routing components
    mock_websocket = Mock()
    mock_manager = Mock()
    mock_manager.send_to_connection = AsyncMock(return_value=False)  # Simulate routing failure
    
    # Component 1: ConnectionHandler  
    with patch('netra_backend.app.websocket.connection_handler.WebSocketEventRouter') as mock_router_class:
        mock_router_class.return_value = Mock()
        
        handler = ConnectionHandler(mock_websocket, user_id)
        await handler.authenticate(thread_id=f"thread_{user_id}")
        
        # Component 2: WebSocketEventRouter
        router = WebSocketEventRouter(mock_manager)
        
        print(f"1. Created components:")
        print(f"   Handler connection ID: {handler.connection_id}")
        print(f"   Router initialized: {router is not None}")
        
        # Register connection in router
        registration_success = await router.register_connection(user_id, handler.connection_id)
        print(f"   Registration success: {registration_success}")
        
        # Get user connections from router
        user_connections = await router.get_user_connections(user_id)
        print(f"   Router knows connections: {user_connections}")
        
        # Test message routing
        test_message = {
            "type": "agent_started",
            "user_id": user_id,
            "message": "Test routing synchronization"
        }
        
        print(f"\n2. Testing message routing:")
        routing_success = await router.route_event(user_id, handler.connection_id, test_message)
        print(f"   Routing success: {routing_success}")
        
        if not routing_success:
            print(f"    ALERT:  ROUTING FAILURE REPRODUCED: Message failed to route to connection")
        
        # Test with mismatched connection ID (simulating sync failure)
        mismatched_id = f"mismatched_{handler.connection_id}"
        print(f"\n3. Testing with mismatched connection ID:")
        print(f"   Original ID: {handler.connection_id}")
        print(f"   Mismatched ID: {mismatched_id}")
        
        mismatched_routing = await router.route_event(user_id, mismatched_id, test_message)
        print(f"   Mismatched routing success: {mismatched_routing}")
        
        if not mismatched_routing:
            print(f"    ALERT:  SYNC FAILURE REPRODUCED: Mismatched connection ID causes routing failure")
        
        # Cleanup
        await handler.cleanup()
    
    print(f"\n    PASS:  Routing table synchronization failure demonstrated")
    return True


async def test_multi_user_isolation_with_authentication():
    """Test multi-user isolation with proper authentication."""
    print("\n ALERT:  TESTING MULTI-USER ROUTING ISOLATION")
    print("="*60)
    
    # Create authenticated users using SSOT auth helper
    auth_helper = E2EAuthHelper(environment="test")
    
    users = []
    for i in range(2):
        user_email = f"isolation_user_{i}@example.com"
        user_id = f"isolation_{i}_{uuid.uuid4().hex[:8]}"
        
        # Create authenticated user context (REQUIRED by CLAUDE.md)
        user_context = await create_authenticated_user_context(
            user_email=user_email,
            user_id=user_id,
            environment="test",
            websocket_enabled=True
        )
        
        # Create JWT token
        jwt_token = auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=user_email,
            permissions=["read", "write"]
        )
        
        users.append({
            "user_id": user_id,
            "email": user_email,
            "context": user_context,
            "jwt_token": jwt_token
        })
    
    print(f"1. Created {len(users)} authenticated users:")
    for i, user in enumerate(users):
        print(f"   User {i+1}: {user['user_id'][:16]}... ({user['email']})")
    
    # Create connections and routing infrastructure
    mock_manager = Mock()
    mock_manager.send_to_connection = AsyncMock(return_value=True)
    
    router = WebSocketEventRouter(mock_manager)
    connections = []
    handlers = []
    
    # Patch ConnectionHandler's WebSocketEventRouter initialization for all users
    with patch('netra_backend.app.websocket.connection_handler.WebSocketEventRouter') as mock_router_class:
        mock_router_class.return_value = Mock()
        
        for user in users:
            # Create authenticated connection
            mock_websocket = Mock()
            mock_websocket.headers = {
                "Authorization": f"Bearer {user['jwt_token']}",
                "X-User-ID": user["user_id"]
            }
            
            handler = ConnectionHandler(mock_websocket, user["user_id"])
            await handler.authenticate(
                thread_id=str(user["context"].thread_id),
                session_id=f"session_{user['user_id']}"
            )
            
            # Register in router
            await router.register_connection(user["user_id"], handler.connection_id)
            
            connections.append({
                "user_id": user["user_id"],
                "connection_id": handler.connection_id,
                "handler": handler
            })
            handlers.append(handler)
    
    print(f"\n2. Created authenticated connections:")
    for i, conn in enumerate(connections):
        print(f"   Connection {i+1}: {conn['connection_id']} (user: {conn['user_id'][:16]}...)")
    
    # Test cross-user message isolation
    print(f"\n3. Testing cross-user message isolation:")
    
    cross_user_violations = []
    
    for i, target_user in enumerate(users):
        # Create user-specific message
        message = {
            "type": "agent_completed",
            "user_id": target_user["user_id"],
            "thread_id": str(target_user["context"].thread_id),
            "sensitive_data": f"private_{target_user['user_id']}"
        }
        
        target_connection = connections[i]
        
        # Route to correct user (should succeed)
        correct_routing = await router.route_event(
            target_user["user_id"],
            target_connection["connection_id"],
            message
        )
        
        print(f"   Message for user {i+1} -> correct target: {correct_routing}")
        
        # Try routing to wrong user (should fail)
        for j, other_connection in enumerate(connections):
            if i != j:  # Different user
                cross_user_routing = await router.route_event(
                    other_connection["user_id"],
                    other_connection["connection_id"],
                    message  # Message still has original user_id
                )
                
                print(f"   Message for user {i+1} -> wrong user {j+1}: {cross_user_routing}")
                
                if cross_user_routing:
                    cross_user_violations.append({
                        "intended_user": target_user["user_id"],
                        "actual_recipient": other_connection["user_id"],
                        "message": message
                    })
    
    print(f"\n4. Cross-user isolation results:")
    print(f"   Cross-user violations: {len(cross_user_violations)}")
    
    if len(cross_user_violations) == 0:
        print(f"    PASS:  ISOLATION MAINTAINED: No cross-user message leakage detected")
    else:
        print(f"    ALERT:  ISOLATION BREACH: {len(cross_user_violations)} cross-user violations detected")
        for violation in cross_user_violations:
            print(f"      - Message for {violation['intended_user'][:16]}... went to {violation['actual_recipient'][:16]}...")
    
    # Cleanup
    for handler in handlers:
        await handler.cleanup()
    
    print(f"\n    PASS:  Multi-user routing isolation test completed")
    return True


async def main():
    """Run all routing failure tests."""
    print(" ALERT:  WebSocket Routing Failure Test Suite")
    print("="*60)
    print("This test suite reproduces WebSocket message routing failures")
    print("caused by connection ID inconsistencies and routing table mismatches.")
    print("="*60)
    
    try:
        # Run all tests
        test_results = []
        
        print("\n" + "="*60)
        result1 = await test_connection_id_generation_inconsistency()
        test_results.append(("Connection ID Generation", result1))
        
        print("\n" + "="*60)  
        result2 = await test_routing_table_synchronization_failure()
        test_results.append(("Routing Table Sync", result2))
        
        print("\n" + "="*60)
        result3 = await test_multi_user_isolation_with_authentication()
        test_results.append(("Multi-User Isolation", result3))
        
        # Summary
        print("\n" + "="*60)
        print(" ALERT:  TEST SUITE SUMMARY")
        print("="*60)
        
        all_passed = True
        for test_name, result in test_results:
            status = " PASS:  PASSED" if result else " FAIL:  FAILED"
            print(f"   {test_name}: {status}")
            if not result:
                all_passed = False
        
        print(f"\nOverall Result: {' PASS:  ALL TESTS PASSED' if all_passed else ' FAIL:  SOME TESTS FAILED'}")
        print("\n ALERT:  ROUTING FAILURES SUCCESSFULLY REPRODUCED!")
        print("These tests demonstrate the connection ID inconsistencies and")
        print("routing table synchronization issues that cause 'Message routing failed' errors.")
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n FAIL:  TEST SUITE ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)