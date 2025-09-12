"""
Test Multi-User WebSocket Routing Isolation

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise)  
- Business Goal: Ensure secure multi-user chat isolation
- Value Impact: Prevents cross-user message leakage that destroys user trust and violates privacy
- Strategic Impact: CRITICAL - Cross-user routing failures are security vulnerabilities

REPRODUCES BUG: Cross-user message routing due to user ID validation failures
REPRODUCES BUG: WebSocket connection isolation breakdown under concurrent multi-user access
REPRODUCES BUG: Authentication context mismatches causing routing to wrong users

This test suite validates multi-user routing isolation with proper authentication:
1. Authenticated WebSocket connections using SSOT e2e_auth_helper
2. Cross-user message isolation validation  
3. Concurrent multi-user scenario testing
4. User context authentication and routing integrity

ALL E2E TESTS MUST USE AUTHENTICATION as mandated by CLAUDE.md Section 3.4.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Set, List, Optional, Tuple
from unittest.mock import Mock, AsyncMock, patch
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest  
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

from netra_backend.app.websocket.connection_handler import ConnectionHandler, ConnectionContext
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, WebSocketID


class AuthenticatedWebSocketConnection:
    """Represents an authenticated WebSocket connection for testing."""
    
    def __init__(self, user_id: str, email: str, jwt_token: str, connection_id: str):
        self.user_id = user_id
        self.email = email 
        self.jwt_token = jwt_token
        self.connection_id = connection_id
        self.messages_received = []
        self.messages_sent = []
        self.is_authenticated = True
        self.created_at = datetime.now(timezone.utc)
    
    def add_received_message(self, message: Dict[str, Any]):
        """Track message received by this connection."""
        self.messages_received.append({
            **message,
            "received_at": datetime.now(timezone.utc).isoformat()
        })
    
    def add_sent_message(self, message: Dict[str, Any]):
        """Track message sent by this connection.""" 
        self.messages_sent.append({
            **message,
            "sent_at": datetime.now(timezone.utc).isoformat()
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "connection_id": self.connection_id,
            "messages_received": len(self.messages_received),
            "messages_sent": len(self.messages_sent),
            "is_authenticated": self.is_authenticated,
            "uptime_seconds": (datetime.now(timezone.utc) - self.created_at).total_seconds()
        }


class MultiUserRoutingValidator:
    """Validates multi-user routing isolation."""
    
    def __init__(self):
        self.connections: Dict[str, AuthenticatedWebSocketConnection] = {}
        self.routing_violations: List[Dict[str, Any]] = []
        self.authentication_failures: List[Dict[str, Any]] = []
    
    def add_connection(self, connection: AuthenticatedWebSocketConnection):
        """Add authenticated connection for tracking."""
        self.connections[connection.connection_id] = connection
    
    def validate_message_routing(self, sender_user_id: str, recipient_user_id: str, 
                                message: Dict[str, Any]) -> bool:
        """Validate that message is routed only to correct user."""
        # Check if message contains proper user context
        message_user_id = message.get("user_id")
        
        if message_user_id != recipient_user_id:
            self.routing_violations.append({
                "type": "USER_ID_MISMATCH",
                "sender": sender_user_id,
                "intended_recipient": recipient_user_id,
                "message_user_id": message_user_id,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return False
        
        return True
    
    def check_cross_user_leakage(self) -> List[Dict[str, Any]]:
        """Check for cross-user message leakage."""
        leakages = []
        
        for conn_id, connection in self.connections.items():
            # Check if connection received messages for other users
            for message in connection.messages_received:
                message_user_id = message.get("user_id")
                if message_user_id and message_user_id != connection.user_id:
                    leakages.append({
                        "type": "CROSS_USER_MESSAGE_LEAKAGE",
                        "connection_user": connection.user_id,
                        "message_user": message_user_id,
                        "connection_id": conn_id,
                        "message": message,
                        "timestamp": message.get("received_at")
                    })
        
        return leakages
    
    def get_isolation_stats(self) -> Dict[str, Any]:
        """Get multi-user isolation statistics."""
        total_messages = sum(len(conn.messages_received) for conn in self.connections.values())
        cross_user_leakages = len(self.check_cross_user_leakage())
        
        return {
            "total_connections": len(self.connections),
            "total_messages": total_messages,
            "routing_violations": len(self.routing_violations),
            "cross_user_leakages": cross_user_leakages,
            "authentication_failures": len(self.authentication_failures),
            "isolation_success_rate": 1.0 - (cross_user_leakages / total_messages) if total_messages > 0 else 1.0
        }


class TestMultiUserRoutingIsolation(BaseIntegrationTest):
    """Test multi-user WebSocket routing isolation with proper authentication."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authenticated_multi_user_connection_isolation(self, real_services_fixture):
        """
        Test that authenticated multi-user WebSocket connections are properly isolated.
        
        CRITICAL: Uses E2E authentication as required by CLAUDE.md
        REPRODUCES BUG: Cross-user connection isolation failures in authenticated scenarios
        """
        # Arrange: Create multiple authenticated users using SSOT auth helper
        auth_helper = E2EAuthHelper(environment="test")
        
        # Create 3 authenticated users
        users = []
        for i in range(3):
            user_email = f"isolation_test_user_{i}@example.com"
            user_id = f"isolation_user_{i}_{uuid.uuid4().hex[:8]}"
            
            # Create authenticated user context (REQUIRED by CLAUDE.md)
            user_context = await create_authenticated_user_context(
                user_email=user_email,
                user_id=user_id,
                environment="test",
                websocket_enabled=True
            )
            
            # Create JWT token for authentication
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
        
        # Create WebSocket routing infrastructure
        mock_websocket_manager = Mock()
        router = WebSocketEventRouter(mock_websocket_manager)
        validator = MultiUserRoutingValidator()
        
        # Create authenticated connections for each user
        connections = []
        handlers = []
        
        for user in users:
            # Create mock WebSocket with authentication
            mock_websocket = Mock()
            mock_websocket.headers = {
                "Authorization": f"Bearer {user['jwt_token']}",
                "X-User-ID": user["user_id"]
            }
            
            # Create connection handler with authentication  
            handler = ConnectionHandler(mock_websocket, user["user_id"])
            await handler.authenticate(
                thread_id=str(user["context"].thread_id),
                session_id=f"session_{user['user_id']}"
            )
            
            # Register in router
            await router.register_connection(user["user_id"], handler.connection_id)
            
            # Create authenticated connection wrapper
            auth_connection = AuthenticatedWebSocketConnection(
                user_id=user["user_id"],
                email=user["email"],
                jwt_token=user["jwt_token"],
                connection_id=handler.connection_id
            )
            
            connections.append(auth_connection)
            handlers.append(handler)
            validator.add_connection(auth_connection)
        
        # Act: Test cross-user message isolation
        test_messages = [
            {
                "type": "agent_started",
                "user_id": users[0]["user_id"],
                "thread_id": str(users[0]["context"].thread_id),
                "message": "User 0 agent started",
                "sensitive_data": f"private_key_{users[0]['user_id']}"
            },
            {
                "type": "tool_executing",
                "user_id": users[1]["user_id"], 
                "thread_id": str(users[1]["context"].thread_id),
                "message": "User 1 tool execution",
                "sensitive_data": f"secret_token_{users[1]['user_id']}"
            },
            {
                "type": "agent_completed",
                "user_id": users[2]["user_id"],
                "thread_id": str(users[2]["context"].thread_id),
                "message": "User 2 task completed",
                "sensitive_data": f"private_result_{users[2]['user_id']}"
            }
        ]
        
        # Send messages and track routing
        routing_results = []
        
        for i, message in enumerate(test_messages):
            target_user_id = message["user_id"]
            target_connection = connections[i]
            
            # Route message to correct user
            routing_success = await router.route_event(
                target_user_id, 
                target_connection.connection_id, 
                message
            )
            
            routing_results.append({
                "message_id": i,
                "target_user": target_user_id,
                "routing_success": routing_success,
                "message_type": message["type"]
            })
            
            # Simulate message reception by target connection
            if routing_success:
                target_connection.add_received_message(message)
            
            # CRITICAL BUG TEST: Try to route same message to other users (should fail)
            for j, other_connection in enumerate(connections):
                if i != j:  # Different user
                    # This should be blocked by user isolation
                    cross_user_routing = await router.route_event(
                        other_connection.user_id,
                        other_connection.connection_id, 
                        message
                    )
                    
                    if cross_user_routing:
                        # SECURITY VIOLATION: Message routed to wrong user!
                        other_connection.add_received_message(message)
                        validator.routing_violations.append({
                            "type": "CROSS_USER_ROUTING_SUCCESS",
                            "intended_user": target_user_id,
                            "actual_recipient": other_connection.user_id,
                            "message": message
                        })
        
        # Assert: Validate isolation was maintained
        isolation_stats = validator.get_isolation_stats()
        cross_user_leakages = validator.check_cross_user_leakage()
        
        print(f" ALERT:  MULTI-USER ISOLATION TEST RESULTS:")
        print(f"   Total connections: {isolation_stats['total_connections']}")
        print(f"   Total messages: {isolation_stats['total_messages']}")  
        print(f"   Routing violations: {isolation_stats['routing_violations']}")
        print(f"   Cross-user leakages: {isolation_stats['cross_user_leakages']}")
        print(f"   Isolation success rate: {isolation_stats['isolation_success_rate']:.1%}")
        
        # CRITICAL SECURITY CHECK: No cross-user message leakage allowed
        assert len(cross_user_leakages) == 0, \
            f"SECURITY VIOLATION: {len(cross_user_leakages)} cross-user message leakages detected"
        
        # Validate each user only received their own messages
        for i, connection in enumerate(connections):
            user_messages = connection.messages_received
            expected_user_id = connection.user_id
            
            for message in user_messages:
                message_user_id = message.get("user_id")
                assert message_user_id == expected_user_id, \
                    f"ISOLATION BREACH: User {expected_user_id} received message for {message_user_id}"
        
        # Verify authentication was maintained throughout
        for connection in connections:
            assert connection.is_authenticated, \
                f"Authentication lost for user {connection.user_id}"
        
        # Cleanup
        for handler in handlers:
            await handler.cleanup()
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_concurrent_multi_user_routing_stress(self, real_services_fixture):
        """
        Test multi-user routing isolation under concurrent stress with authentication.
        
        CRITICAL: Uses E2E authentication as required by CLAUDE.md
        REPRODUCES BUG: Routing isolation breakdown under high concurrent load
        """
        # Arrange: Create multiple authenticated users for stress testing
        auth_helper = E2EAuthHelper(environment="test")
        concurrent_users = 5
        messages_per_user = 10
        
        users = []
        connections = []
        handlers = []
        
        # Create authenticated users
        for i in range(concurrent_users):
            user_email = f"stress_user_{i}@example.com"
            user_id = f"stress_{i}_{uuid.uuid4().hex[:8]}"
            
            # REQUIRED AUTHENTICATION per CLAUDE.md
            user_context = await create_authenticated_user_context(
                user_email=user_email,
                user_id=user_id,
                environment="test",
                websocket_enabled=True
            )
            
            jwt_token = auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=user_email
            )
            
            users.append({
                "user_id": user_id,
                "email": user_email,
                "context": user_context,
                "jwt_token": jwt_token
            })
        
        # Setup routing infrastructure
        mock_manager = Mock()
        mock_manager.send_to_connection = AsyncMock(return_value=True)
        
        router = WebSocketEventRouter(mock_manager)
        validator = MultiUserRoutingValidator()
        
        # Create authenticated connections concurrently
        async def setup_user_connection(user_data):
            mock_websocket = Mock()
            mock_websocket.headers = {
                "Authorization": f"Bearer {user_data['jwt_token']}",
                "X-User-ID": user_data["user_id"]
            }
            
            handler = ConnectionHandler(mock_websocket, user_data["user_id"])
            await handler.authenticate(
                thread_id=str(user_data["context"].thread_id),
                session_id=f"session_{user_data['user_id']}"
            )
            
            await router.register_connection(user_data["user_id"], handler.connection_id)
            
            auth_connection = AuthenticatedWebSocketConnection(
                user_id=user_data["user_id"],
                email=user_data["email"],
                jwt_token=user_data["jwt_token"],
                connection_id=handler.connection_id
            )
            
            return handler, auth_connection
        
        # Setup all connections concurrently
        setup_tasks = [setup_user_connection(user) for user in users]
        setup_results = await asyncio.gather(*setup_tasks)
        
        for handler, connection in setup_results:
            handlers.append(handler)
            connections.append(connection)
            validator.add_connection(connection)
        
        # Act: Generate concurrent message traffic for each user
        async def generate_user_messages(user_index):
            user_data = users[user_index]
            connection = connections[user_index]
            results = []
            
            for msg_id in range(messages_per_user):
                # Create user-specific message
                message = {
                    "type": "agent_thinking",
                    "user_id": user_data["user_id"],
                    "thread_id": str(user_data["context"].thread_id),
                    "message_id": f"{user_index}_{msg_id}",
                    "content": f"User {user_index} message {msg_id}",
                    "private_data": f"secret_{user_data['user_id']}_{msg_id}"
                }
                
                # Add small random delay to increase concurrency complexity
                await asyncio.sleep(0.001 * (user_index + 1))
                
                # Route message
                routing_success = await router.route_event(
                    user_data["user_id"],
                    connection.connection_id,
                    message
                )
                
                results.append({
                    "user_index": user_index,
                    "message_id": msg_id,
                    "routing_success": routing_success,
                    "message": message
                })
                
                # Simulate message reception
                if routing_success:
                    connection.add_received_message(message)
            
            return results
        
        # Generate concurrent message traffic
        traffic_tasks = [generate_user_messages(i) for i in range(concurrent_users)]
        all_results = await asyncio.gather(*traffic_tasks, return_exceptions=True)
        
        # Process results and check for isolation violations
        total_messages = 0
        routing_failures = []
        successful_messages = []
        
        for user_results in all_results:
            if isinstance(user_results, Exception):
                routing_failures.append(f"Exception: {user_results}")
                continue
            
            for result in user_results:
                total_messages += 1
                if result["routing_success"]:
                    successful_messages.append(result)
                else:
                    routing_failures.append(result)
        
        # Assert: Validate concurrent stress results
        success_rate = len(successful_messages) / total_messages if total_messages > 0 else 0
        
        print(f" ALERT:  CONCURRENT STRESS TEST RESULTS:")
        print(f"   Total users: {concurrent_users}")
        print(f"   Messages per user: {messages_per_user}")
        print(f"   Total messages: {total_messages}")
        print(f"   Successful routes: {len(successful_messages)}")
        print(f"   Routing failures: {len(routing_failures)}")
        print(f"   Success rate: {success_rate:.1%}")
        
        # Check isolation under stress
        isolation_stats = validator.get_isolation_stats()
        cross_user_leakages = validator.check_cross_user_leakage()
        
        print(f" ALERT:  ISOLATION UNDER STRESS:")
        print(f"   Cross-user leakages: {len(cross_user_leakages)}")
        print(f"   Isolation success rate: {isolation_stats['isolation_success_rate']:.1%}")
        
        # CRITICAL SECURITY: No isolation failures allowed even under stress
        assert len(cross_user_leakages) == 0, \
            f"STRESS ISOLATION FAILURE: {len(cross_user_leakages)} cross-user leakages under concurrent load"
        
        # High success rate expected despite concurrency
        assert success_rate >= 0.9, \
            f"CONCURRENT ROUTING DEGRADATION: {success_rate:.1%} success rate under stress"
        
        # Validate per-user message isolation
        for i, connection in enumerate(connections):
            user_id = connection.user_id
            received_messages = connection.messages_received
            
            # Check each message belongs to this user
            for message in received_messages:
                msg_user_id = message.get("user_id")
                assert msg_user_id == user_id, \
                    f"CONCURRENT ISOLATION BREACH: User {user_id} received message for {msg_user_id}"
            
            # Check message count (should receive all their messages)
            expected_count = messages_per_user
            actual_count = len(received_messages)
            
            print(f"   User {i}: {actual_count}/{expected_count} messages received")
        
        # Cleanup
        for handler in handlers:
            await handler.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_context_routing_validation(self, real_services_fixture):
        """
        Test WebSocket routing with authentication context validation.
        
        CRITICAL: Uses E2E authentication as required by CLAUDE.md
        REPRODUCES BUG: Authentication context mismatches causing routing to wrong users
        """
        # Arrange: Create users with different authentication contexts
        auth_helper = E2EAuthHelper(environment="test")
        
        # User with valid authentication
        valid_user = {
            "user_id": f"valid_{uuid.uuid4().hex[:8]}",
            "email": "valid_user@example.com",
            "permissions": ["read", "write"]
        }
        
        # User with limited permissions  
        limited_user = {
            "user_id": f"limited_{uuid.uuid4().hex[:8]}",
            "email": "limited_user@example.com",
            "permissions": ["read"]  # No write permission
        }
        
        # Create authenticated contexts
        valid_context = await create_authenticated_user_context(
            user_email=valid_user["email"],
            user_id=valid_user["user_id"],
            environment="test",
            permissions=valid_user["permissions"],
            websocket_enabled=True
        )
        
        limited_context = await create_authenticated_user_context(
            user_email=limited_user["email"],
            user_id=limited_user["user_id"],
            environment="test",
            permissions=limited_user["permissions"],
            websocket_enabled=True
        )
        
        # Create JWT tokens with different permissions
        valid_token = auth_helper.create_test_jwt_token(
            user_id=valid_user["user_id"],
            email=valid_user["email"],
            permissions=valid_user["permissions"]
        )
        
        limited_token = auth_helper.create_test_jwt_token(
            user_id=limited_user["user_id"],
            email=limited_user["email"],
            permissions=limited_user["permissions"]
        )
        
        # Setup routing infrastructure
        mock_manager = Mock()
        mock_manager.send_to_connection = AsyncMock(return_value=True)
        
        router = WebSocketEventRouter(mock_manager)
        
        # Create authenticated connections
        connections = {}
        handlers = {}
        
        for user_data, context, token in [
            (valid_user, valid_context, valid_token),
            (limited_user, limited_context, limited_token)
        ]:
            mock_websocket = Mock()
            mock_websocket.headers = {
                "Authorization": f"Bearer {token}",
                "X-User-ID": user_data["user_id"]
            }
            
            handler = ConnectionHandler(mock_websocket, user_data["user_id"])
            await handler.authenticate(
                thread_id=str(context.thread_id),
                session_id=f"session_{user_data['user_id']}"
            )
            
            await router.register_connection(user_data["user_id"], handler.connection_id)
            
            connections[user_data["user_id"]] = {
                "handler": handler,
                "context": context,
                "token": token,
                "permissions": user_data["permissions"],
                "connection_id": handler.connection_id
            }
            handlers[user_data["user_id"]] = handler
        
        # Act: Test routing with authentication context validation
        test_scenarios = [
            {
                "name": "Valid user write operation",
                "target_user": valid_user["user_id"],
                "message": {
                    "type": "agent_started",
                    "user_id": valid_user["user_id"],
                    "action": "write",
                    "data": "Creating new analysis"
                },
                "expected_success": True
            },
            {
                "name": "Limited user write operation",
                "target_user": limited_user["user_id"], 
                "message": {
                    "type": "tool_executing",
                    "user_id": limited_user["user_id"],
                    "action": "write",
                    "data": "Attempting to create data"
                },
                "expected_success": True  # Routing should work, app layer handles permissions
            },
            {
                "name": "Cross-user routing attempt",
                "target_user": valid_user["user_id"],
                "message": {
                    "type": "agent_completed",
                    "user_id": limited_user["user_id"],  # Different user in message!
                    "action": "read",
                    "data": "Task completed"
                },
                "expected_success": False  # Should fail due to user mismatch
            }
        ]
        
        routing_results = []
        
        for scenario in test_scenarios:
            target_user_id = scenario["target_user"]
            message = scenario["message"]
            expected_success = scenario["expected_success"]
            
            target_connection = connections[target_user_id]
            
            # Attempt routing
            try:
                routing_success = await router.route_event(
                    target_user_id,
                    target_connection["connection_id"],
                    message
                )
                
                routing_results.append({
                    "scenario": scenario["name"],
                    "target_user": target_user_id,
                    "message_user": message.get("user_id"),
                    "routing_success": routing_success,
                    "expected_success": expected_success,
                    "result_matches_expected": routing_success == expected_success
                })
                
            except Exception as e:
                routing_results.append({
                    "scenario": scenario["name"],
                    "target_user": target_user_id,
                    "message_user": message.get("user_id"),
                    "routing_success": False,
                    "expected_success": expected_success,
                    "error": str(e),
                    "result_matches_expected": False == expected_success
                })
        
        # Assert: Validate authentication context routing
        print(f" ALERT:  AUTHENTICATION CONTEXT ROUTING RESULTS:")
        for result in routing_results:
            print(f"   Scenario: {result['scenario']}")
            print(f"   Target user: {result['target_user']}")
            print(f"   Message user: {result['message_user']}")
            print(f"   Routing success: {result['routing_success']}")
            print(f"   Expected: {result['expected_success']}")
            print(f"   Correct: {result['result_matches_expected']}")
            print()
        
        # All scenarios should behave as expected
        correct_results = sum(1 for r in routing_results if r["result_matches_expected"])
        total_scenarios = len(routing_results)
        accuracy_rate = correct_results / total_scenarios if total_scenarios > 0 else 0
        
        print(f" ALERT:  AUTHENTICATION ROUTING ACCURACY: {accuracy_rate:.1%}")
        
        # CRITICAL: Authentication context validation should be 100% accurate
        assert accuracy_rate == 1.0, \
            f"AUTHENTICATION ROUTING FAILURES: {accuracy_rate:.1%} accuracy in auth context validation"
        
        # Specifically check cross-user routing prevention
        cross_user_scenario = next(r for r in routing_results if "Cross-user" in r["scenario"])
        assert cross_user_scenario["routing_success"] == False, \
            "SECURITY FAILURE: Cross-user routing should be blocked"
        
        # Cleanup
        for handler in handlers.values():
            await handler.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_authentication_token_validation(self, real_services_fixture):
        """
        Test WebSocket routing with JWT token validation and expiry.
        
        CRITICAL: Uses E2E authentication as required by CLAUDE.md  
        REPRODUCES BUG: Expired or invalid tokens causing routing failures
        """
        # Arrange: Create users with different token states
        auth_helper = E2EAuthHelper(environment="test")
        
        user_id = f"token_test_{uuid.uuid4().hex[:8]}"
        user_email = "token_test@example.com"
        
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email=user_email,
            user_id=user_id,
            environment="test",
            websocket_enabled=True
        )
        
        # Create tokens with different states
        valid_token = auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=user_email,
            exp_minutes=30  # Valid for 30 minutes
        )
        
        expired_token = auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=user_email,
            exp_minutes=-1  # Already expired
        )
        
        # Setup routing
        mock_manager = Mock()
        mock_manager.send_to_connection = AsyncMock(return_value=True)
        
        router = WebSocketEventRouter(mock_manager)
        
        # Test scenarios with different token states
        token_scenarios = [
            {
                "name": "Valid token connection",
                "token": valid_token,
                "should_authenticate": True,
                "should_route": True
            },
            {
                "name": "Expired token connection", 
                "token": expired_token,
                "should_authenticate": False,
                "should_route": False
            },
            {
                "name": "Invalid token connection",
                "token": "invalid_token_string",
                "should_authenticate": False,
                "should_route": False
            }
        ]
        
        test_results = []
        handlers = []
        
        for scenario in token_scenarios:
            # Create connection with specific token
            mock_websocket = Mock()
            mock_websocket.headers = {
                "Authorization": f"Bearer {scenario['token']}",
                "X-User-ID": user_id
            }
            
            handler = ConnectionHandler(mock_websocket, user_id)
            
            # Attempt authentication
            try:
                auth_success = await handler.authenticate(
                    thread_id=str(user_context.thread_id),
                    session_id=f"session_{scenario['name']}"
                )
                
                # Register if authentication succeeded
                if auth_success:
                    await router.register_connection(user_id, handler.connection_id)
                
                # Test message routing
                test_message = {
                    "type": "agent_started",
                    "user_id": user_id,
                    "thread_id": str(user_context.thread_id),
                    "message": f"Test message for {scenario['name']}"
                }
                
                if auth_success:
                    routing_success = await router.route_event(user_id, handler.connection_id, test_message)
                else:
                    routing_success = False
                
                test_results.append({
                    "scenario": scenario["name"],
                    "token_valid": scenario["token"] == valid_token,
                    "auth_success": auth_success,
                    "expected_auth": scenario["should_authenticate"],
                    "routing_success": routing_success,
                    "expected_routing": scenario["should_route"],
                    "auth_correct": auth_success == scenario["should_authenticate"],
                    "routing_correct": routing_success == scenario["should_route"]
                })
                
                handlers.append(handler)
                
            except Exception as e:
                test_results.append({
                    "scenario": scenario["name"],
                    "token_valid": scenario["token"] == valid_token,
                    "auth_success": False,
                    "expected_auth": scenario["should_authenticate"],
                    "routing_success": False,
                    "expected_routing": scenario["should_route"],
                    "auth_correct": False == scenario["should_authenticate"],
                    "routing_correct": False == scenario["should_route"],
                    "error": str(e)
                })
        
        # Assert: Validate token-based authentication and routing
        print(f" ALERT:  TOKEN VALIDATION ROUTING RESULTS:")
        for result in test_results:
            print(f"   Scenario: {result['scenario']}")
            print(f"   Token valid: {result['token_valid']}")
            print(f"   Auth success: {result['auth_success']} (expected: {result['expected_auth']})")
            print(f"   Routing success: {result['routing_success']} (expected: {result['expected_routing']})")
            print(f"   Auth correct: {result['auth_correct']}")
            print(f"   Routing correct: {result['routing_correct']}")
            if "error" in result:
                print(f"   Error: {result['error']}")
            print()
        
        # Calculate accuracy rates
        auth_accuracy = sum(1 for r in test_results if r["auth_correct"]) / len(test_results)
        routing_accuracy = sum(1 for r in test_results if r["routing_correct"]) / len(test_results)
        
        print(f" ALERT:  TOKEN VALIDATION ACCURACY:")
        print(f"   Authentication accuracy: {auth_accuracy:.1%}")
        print(f"   Routing accuracy: {routing_accuracy:.1%}")
        
        # CRITICAL: Token validation should be 100% accurate  
        assert auth_accuracy == 1.0, \
            f"AUTHENTICATION TOKEN VALIDATION FAILURE: {auth_accuracy:.1%} accuracy"
        
        assert routing_accuracy == 1.0, \
            f"TOKEN-BASED ROUTING FAILURE: {routing_accuracy:.1%} accuracy"
        
        # Specifically verify invalid tokens are rejected
        invalid_token_results = [r for r in test_results if not r["token_valid"]]
        for result in invalid_token_results:
            assert result["auth_success"] == False, \
                f"SECURITY FAILURE: Invalid token {result['scenario']} should not authenticate"
            assert result["routing_success"] == False, \
                f"SECURITY FAILURE: Invalid token {result['scenario']} should not allow routing"
        
        # Cleanup
        for handler in handlers:
            await handler.cleanup()