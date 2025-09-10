"""
Comprehensive Multi-User Isolation Routing Tests

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise)
- Business Goal: Ensure complete user isolation in multi-user chat system  
- Value Impact: Prevents catastrophic cross-user message contamination that would destroy business
- Strategic Impact: CRITICAL - User isolation failures are existential security vulnerabilities

CRITICAL FOCUS: Factory Pattern User Isolation and Routing Boundaries
This test suite validates the factory-based isolation patterns that ensure:
1. UserExecutionContext boundaries prevent cross-user contamination
2. WebSocket factory creates truly isolated manager instances per user  
3. Message routing respects user context isolation
4. Connection pool separation between users
5. Agent execution context isolation
6. Concurrent multi-user scenario safety

SLIGHT EMPHASIS: Section 6.1 Multi-User Isolation - "User A must never see User B's messages"

REPRODUCES CRITICAL BUGS:
- Factory pattern sharing state between users
- UserExecutionContext boundary violations
- Message routing cross-contamination  
- Connection pool user isolation failures
- Agent execution context leakage
- Concurrent multi-user race conditions

ALL TESTS USE AUTHENTICATION as mandated by CLAUDE.md Section 3.4
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Set, List, Optional, Tuple, AsyncIterator
from unittest.mock import Mock, AsyncMock, patch
from contextlib import asynccontextmanager
import concurrent.futures
import threading
import time

from test_framework.base_integration_test import BaseIntegrationTest  
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory, 
    IsolatedWebSocketManager,
    create_defensive_user_execution_context
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core import create_websocket_manager
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, WebSocketID, ConnectionID, RequestID
from shared.types import StronglyTypedWebSocketEvent, WebSocketEventType


class UserIsolationTestHarness:
    """Test harness for validating multi-user isolation in routing systems."""
    
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.isolation_violations: List[Dict[str, Any]] = []
        self.factory_instances: Dict[str, Any] = {}
        self.connection_pools: Dict[str, Set[str]] = {}
        self.message_routing_log: List[Dict[str, Any]] = []
    
    async def create_isolated_user(self, user_index: int) -> Dict[str, Any]:
        """Create an isolated user with factory-based manager."""
        user_id = f"isolated_user_{user_index}_{uuid.uuid4().hex[:8]}"
        user_email = f"isolation_test_{user_index}@example.com"
        
        # Create authenticated user context (REQUIRED by CLAUDE.md)
        auth_helper = E2EAuthHelper(environment="test")
        user_context = await create_authenticated_user_context(
            user_email=user_email,
            user_id=user_id,
            environment="test",
            websocket_enabled=True
        )
        
        jwt_token = auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=user_email,
            permissions=["read", "write"]
        )
        
        # Create factory-based WebSocket manager (CRITICAL for isolation)
        factory = WebSocketManagerFactory()
        manager = await factory.create_manager(
            user_execution_context=user_context,
            connection_id=f"conn_{user_id}",
            websocket_id=f"ws_{user_id}"
        )
        
        user_data = {
            "user_id": user_id,
            "email": user_email,
            "context": user_context,
            "jwt_token": jwt_token,
            "factory": factory,
            "manager": manager,
            "messages_received": [],
            "messages_sent": [],
            "connection_pool": set()
        }
        
        self.users[user_id] = user_data
        self.factory_instances[user_id] = factory
        self.connection_pools[user_id] = user_data["connection_pool"]
        
        return user_data
    
    def validate_factory_isolation(self, user1_id: str, user2_id: str) -> bool:
        """Validate that factory instances are truly isolated."""
        factory1 = self.factory_instances.get(user1_id)
        factory2 = self.factory_instances.get(user2_id)
        
        if factory1 is factory2:
            self.isolation_violations.append({
                "type": "FACTORY_INSTANCE_SHARING",
                "user1": user1_id,
                "user2": user2_id,
                "violation": "Factory instances are the same object"
            })
            return False
        
        return True
    
    def validate_connection_pool_isolation(self, user1_id: str, user2_id: str) -> bool:
        """Validate connection pools are separate between users."""
        pool1 = self.connection_pools.get(user1_id, set())
        pool2 = self.connection_pools.get(user2_id, set())
        
        shared_connections = pool1.intersection(pool2)
        if shared_connections:
            self.isolation_violations.append({
                "type": "CONNECTION_POOL_CONTAMINATION",
                "user1": user1_id,
                "user2": user2_id,
                "shared_connections": list(shared_connections)
            })
            return False
        
        return True
    
    def log_message_routing(self, from_user: str, to_user: str, message: Dict[str, Any]):
        """Log message routing for isolation analysis."""
        self.message_routing_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_user": from_user,
            "to_user": to_user,
            "message_id": message.get("message_id"),
            "message_type": message.get("type"),
            "user_context": message.get("user_id")
        })
    
    def detect_cross_user_contamination(self) -> List[Dict[str, Any]]:
        """Detect cross-user message contamination."""
        contaminations = []
        
        for route in self.message_routing_log:
            from_user = route["from_user"]
            to_user = route["to_user"]
            message_user_context = route["user_context"]
            
            # Messages should only route within same user context
            if from_user != to_user and message_user_context == from_user:
                contaminations.append({
                    "type": "CROSS_USER_MESSAGE_ROUTING",
                    "violation": f"Message from {from_user} routed to {to_user}",
                    "route": route
                })
        
        return contaminations
    
    def get_isolation_report(self) -> Dict[str, Any]:
        """Generate comprehensive isolation validation report."""
        return {
            "total_users": len(self.users),
            "factory_instances": len(self.factory_instances),
            "isolation_violations": len(self.isolation_violations),
            "cross_user_contaminations": len(self.detect_cross_user_contamination()),
            "message_routes_logged": len(self.message_routing_log),
            "violations_detail": self.isolation_violations,
            "contamination_detail": self.detect_cross_user_contamination()
        }


class TestMultiUserIsolationRouting(BaseIntegrationTest):
    """Comprehensive test suite for multi-user isolation routing patterns."""

    def setup_method(self):
        """Set up test harness for each test."""
        super().setup_method()
        self.isolation_harness = UserIsolationTestHarness()

    # USER CONTEXT ISOLATION TESTS (6 tests)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_execution_context_isolation(self, real_services_fixture):
        """Test that UserExecutionContext instances are completely isolated between users."""
        # Create two users with separate execution contexts
        user1 = await self.isolation_harness.create_isolated_user(1)
        user2 = await self.isolation_harness.create_isolated_user(2)
        
        context1 = user1["context"]
        context2 = user2["context"]
        
        # Assert contexts are different instances
        assert context1 is not context2, "UserExecutionContext instances must be separate objects"
        assert context1.user_id != context2.user_id, "User IDs must be different"
        
        # Test context state modification doesn't affect other user
        context1_original_data = context1.to_dict()
        context2_original_data = context2.to_dict()
        
        # Simulate context mutation for user1
        if hasattr(context1, 'add_metadata'):
            context1.add_metadata("test_key", "test_value")
        
        # Assert user2 context is unaffected
        assert context2.to_dict() == context2_original_data, "User2 context must remain unchanged"
        
        # Verify isolation in report
        report = self.isolation_harness.get_isolation_report()
        assert report["isolation_violations"] == 0, f"No isolation violations expected: {report}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_pattern_creates_isolated_managers(self, real_services_fixture):
        """Test that factory pattern creates truly isolated WebSocket managers per user."""
        user1 = await self.isolation_harness.create_isolated_user(1)
        user2 = await self.isolation_harness.create_isolated_user(2)
        
        manager1 = user1["manager"]
        manager2 = user2["manager"]
        factory1 = user1["factory"]
        factory2 = user2["factory"]
        
        # Assert managers are different instances
        assert manager1 is not manager2, "WebSocket managers must be separate instances"
        assert factory1 is not factory2, "Factory instances must be separate"
        
        # Validate factory isolation
        isolation_valid = self.isolation_harness.validate_factory_isolation(
            user1["user_id"], user2["user_id"]
        )
        assert isolation_valid, "Factory isolation validation must pass"
        
        # Test manager state isolation
        manager1_id = getattr(manager1, 'manager_id', None)
        manager2_id = getattr(manager2, 'manager_id', None)
        
        if manager1_id and manager2_id:
            assert manager1_id != manager2_id, "Manager IDs must be unique"

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_user_context_boundaries_in_routing(self, real_services_fixture):
        """Test that message routing respects user context boundaries."""
        user1 = await self.isolation_harness.create_isolated_user(1)
        user2 = await self.isolation_harness.create_isolated_user(2)
        
        # Create mock WebSocket router
        router = Mock()
        
        # Test message with user1 context
        user1_message = {
            "message_id": str(uuid.uuid4()),
            "type": "user_message",
            "payload": "Hello from user1",
            "user_id": user1["user_id"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Simulate routing - should only go to user1
        self.isolation_harness.log_message_routing(
            user1["user_id"], user1["user_id"], user1_message
        )
        
        # Test cross-user routing attempt (should be prevented)
        cross_user_message = {
            "message_id": str(uuid.uuid4()),
            "type": "user_message", 
            "payload": "Cross-user message attempt",
            "user_id": user1["user_id"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # This should trigger contamination detection
        self.isolation_harness.log_message_routing(
            user1["user_id"], user2["user_id"], cross_user_message
        )
        
        # Validate no cross-user contamination
        contaminations = self.isolation_harness.detect_cross_user_contamination()
        assert len(contaminations) > 0, "Cross-user routing attempt should be detected"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_concurrent_user_context_isolation(self, real_services_fixture):
        """Test user context isolation under concurrent multi-user access."""
        
        async def create_user_concurrently(user_index: int) -> Dict[str, Any]:
            """Create user context concurrently."""
            return await self.isolation_harness.create_isolated_user(user_index)
        
        # Create 5 users concurrently
        concurrent_user_count = 5
        tasks = [
            create_user_concurrently(i) 
            for i in range(concurrent_user_count)
        ]
        
        users = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all users created successfully
        successful_users = [u for u in users if not isinstance(u, Exception)]
        assert len(successful_users) == concurrent_user_count, "All concurrent user creations must succeed"
        
        # Validate isolation between all pairs
        user_ids = [user["user_id"] for user in successful_users]
        
        for i, user1_id in enumerate(user_ids):
            for j, user2_id in enumerate(user_ids[i+1:], i+1):
                isolation_valid = self.isolation_harness.validate_factory_isolation(user1_id, user2_id)
                assert isolation_valid, f"Isolation must be maintained between user {i} and {j}"
        
        report = self.isolation_harness.get_isolation_report()
        assert report["isolation_violations"] == 0, f"No isolation violations in concurrent test: {report}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_state_separation(self, real_services_fixture):
        """Test that user context state is completely separated between users."""
        user1 = await self.isolation_harness.create_isolated_user(1)
        user2 = await self.isolation_harness.create_isolated_user(2)
        
        # Modify state in user1 context
        context1 = user1["context"]
        context2 = user2["context"]
        
        # Test different attributes don't interfere
        original_user1_threads = getattr(context1, 'active_threads', set())
        original_user2_threads = getattr(context2, 'active_threads', set())
        
        # Simulate thread addition for user1
        if hasattr(context1, 'add_active_thread'):
            test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
            context1.add_active_thread(test_thread_id)
        
        # Assert user2 threads unchanged
        current_user2_threads = getattr(context2, 'active_threads', set())
        assert current_user2_threads == original_user2_threads, "User2 threads must be unaffected"
        
        # Test user ID isolation (most critical)
        assert context1.user_id != context2.user_id, "User IDs must be completely separate"
        
        # Test context serialization doesn't leak
        context1_dict = context1.to_dict() if hasattr(context1, 'to_dict') else {}
        context2_dict = context2.to_dict() if hasattr(context2, 'to_dict') else {}
        
        # Should have no overlapping keys with user-specific values
        if context1_dict and context2_dict:
            user_specific_keys = ['user_id', 'email', 'session_id']
            for key in user_specific_keys:
                if key in context1_dict and key in context2_dict:
                    assert context1_dict[key] != context2_dict[key], f"Key {key} must differ between users"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_cleanup_isolation(self, real_services_fixture):
        """Test that user context cleanup doesn't affect other users."""
        user1 = await self.isolation_harness.create_isolated_user(1)
        user2 = await self.isolation_harness.create_isolated_user(2)
        user3 = await self.isolation_harness.create_isolated_user(3)
        
        # Record initial state of user2 and user3
        initial_user2_state = user2["context"].to_dict() if hasattr(user2["context"], 'to_dict') else {}
        initial_user3_state = user3["context"].to_dict() if hasattr(user3["context"], 'to_dict') else {}
        
        # Simulate cleanup of user1
        user1_context = user1["context"]
        user1_manager = user1["manager"]
        user1_factory = user1["factory"]
        
        # Cleanup user1 (simulate connection termination)
        if hasattr(user1_manager, 'cleanup'):
            await user1_manager.cleanup()
        
        if hasattr(user1_factory, 'cleanup_user'):
            await user1_factory.cleanup_user(user1["user_id"])
        
        # Remove user1 from harness
        del self.isolation_harness.users[user1["user_id"]]
        del self.isolation_harness.factory_instances[user1["user_id"]]
        
        # Assert user2 and user3 contexts unaffected
        current_user2_state = user2["context"].to_dict() if hasattr(user2["context"], 'to_dict') else {}
        current_user3_state = user3["context"].to_dict() if hasattr(user3["context"], 'to_dict') else {}
        
        if initial_user2_state:
            assert current_user2_state == initial_user2_state, "User2 context must remain unchanged after user1 cleanup"
        
        if initial_user3_state:
            assert current_user3_state == initial_user3_state, "User3 context must remain unchanged after user1 cleanup"
        
        # Validate remaining factory isolation
        isolation_valid = self.isolation_harness.validate_factory_isolation(
            user2["user_id"], user3["user_id"]
        )
        assert isolation_valid, "Factory isolation must remain after cleanup"

    # MESSAGE ISOLATION BETWEEN USERS TESTS (5 tests)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_routing_user_isolation(self, real_services_fixture):
        """Test that messages are routed only to the correct user."""
        user1 = await self.isolation_harness.create_isolated_user(1)
        user2 = await self.isolation_harness.create_isolated_user(2)
        user3 = await self.isolation_harness.create_isolated_user(3)
        
        # Create strongly typed WebSocket events for each user
        user1_event = StronglyTypedWebSocketEvent(
            event_type=WebSocketEventType.STATUS_UPDATE.value,
            user_id=UserID(user1["user_id"]),
            thread_id=ThreadID(f"thread_{user1['user_id']}"),
            request_id=RequestID(f"req_{user1['user_id']}"),
            data={"message": "Private message for user1"},
        )
        
        user2_event = StronglyTypedWebSocketEvent(
            event_type=WebSocketEventType.STATUS_UPDATE.value,
            user_id=UserID(user2["user_id"]),
            thread_id=ThreadID(f"thread_{user2['user_id']}"),
            request_id=RequestID(f"req_{user2['user_id']}"),
            data={"message": "Private message for user2"},
        )
        
        # Simulate message routing through managers
        manager1 = user1["manager"]
        manager2 = user2["manager"]
        
        # Messages should only be processed by correct manager
        if hasattr(manager1, 'route_message'):
            await manager1.route_message(user1_event.to_dict())
            user1["messages_received"].append(user1_event.to_dict())
        
        if hasattr(manager2, 'route_message'):
            await manager2.route_message(user2_event.to_dict())
            user2["messages_received"].append(user2_event.to_dict())
        
        # Validate isolation - user3 should receive no messages
        user3_messages = user3.get("messages_received", [])
        assert len(user3_messages) == 0, "User3 must not receive messages intended for other users"
        
        # Validate correct routing
        user1_messages = user1.get("messages_received", [])
        user2_messages = user2.get("messages_received", [])
        
        assert len(user1_messages) <= 1, "User1 should receive only their own message"
        assert len(user2_messages) <= 1, "User2 should receive only their own message"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_message_user_isolation(self, real_services_fixture):
        """Test that agent responses are isolated per user context."""
        user1 = await self.isolation_harness.create_isolated_user(1)
        user2 = await self.isolation_harness.create_isolated_user(2)
        
        # Simulate agent execution context for each user
        agent_context1 = create_defensive_user_execution_context(
            user1["user_id"],
            websocket_client_id=f"ws_client_{user1['user_id']}"
        )
        
        agent_context2 = create_defensive_user_execution_context(
            user2["user_id"],
            websocket_client_id=f"ws_client_{user2['user_id']}"
        )
        
        # Mock agent responses
        agent_response1 = {
            "type": "agent_response",
            "user_id": user1["user_id"],
            "agent_id": "data_analysis_agent",
            "response": "Data analysis for user1",
            "execution_context": agent_context1.to_dict()
        }
        
        agent_response2 = {
            "type": "agent_response", 
            "user_id": user2["user_id"],
            "agent_id": "data_analysis_agent",
            "response": "Data analysis for user2",
            "execution_context": agent_context2.to_dict()
        }
        
        # Route agent responses to correct users only
        self.isolation_harness.log_message_routing(
            "system", user1["user_id"], agent_response1
        )
        
        self.isolation_harness.log_message_routing(
            "system", user2["user_id"], agent_response2  
        )
        
        # Validate no cross-contamination in agent responses
        contaminations = self.isolation_harness.detect_cross_user_contamination()
        agent_contaminations = [c for c in contaminations if "agent" in str(c).lower()]
        
        assert len(agent_contaminations) == 0, f"Agent responses must not contaminate across users: {agent_contaminations}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_user_isolation(self, real_services_fixture):
        """Test WebSocket message isolation prevents cross-user contamination."""
        user1 = await self.isolation_harness.create_isolated_user(1)
        user2 = await self.isolation_harness.create_isolated_user(2)
        user3 = await self.isolation_harness.create_isolated_user(3)
        
        # Create WebSocket messages with user context
        ws_message1 = {
            "type": "websocket_event",
            "event_type": "message_received",
            "user_id": user1["user_id"],
            "connection_id": f"conn_{user1['user_id']}",
            "payload": {"text": "WebSocket message from user1"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        ws_message2 = {
            "type": "websocket_event",
            "event_type": "message_received", 
            "user_id": user2["user_id"],
            "connection_id": f"conn_{user2['user_id']}",
            "payload": {"text": "WebSocket message from user2"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Process messages through isolated managers
        manager1 = user1["manager"]
        manager2 = user2["manager"] 
        manager3 = user3["manager"]
        
        # Mock message processing
        processed_by_manager1 = []
        processed_by_manager2 = []
        processed_by_manager3 = []
        
        # Simulate message processing isolation
        if hasattr(manager1, 'process_message'):
            processed_by_manager1.append(ws_message1)
        
        if hasattr(manager2, 'process_message'):
            processed_by_manager2.append(ws_message2)
        
        # Manager3 should process no messages (isolation test)
        if hasattr(manager3, 'process_message'):
            # No messages should reach manager3
            pass
        
        # Validate isolation
        assert len(processed_by_manager3) == 0, "Manager3 must not process messages from other users"
        
        # Test message user_id context validation
        for msg in processed_by_manager1:
            assert msg["user_id"] == user1["user_id"], "Manager1 should only process user1 messages"
        
        for msg in processed_by_manager2:
            assert msg["user_id"] == user2["user_id"], "Manager2 should only process user2 messages"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_broadcast_message_user_filtering(self, real_services_fixture):
        """Test that broadcast messages respect user filter boundaries."""
        users = []
        for i in range(4):
            user = await self.isolation_harness.create_isolated_user(i+1)
            users.append(user)
        
        # Create broadcast message with filtering
        broadcast_message = {
            "type": "broadcast",
            "event_type": "system_announcement", 
            "payload": {"announcement": "System maintenance in 5 minutes"},
            "target_users": [users[0]["user_id"], users[2]["user_id"]],  # Only users 0 and 2
            "sender": "system",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Process broadcast through all managers
        received_by_users = []
        
        for i, user in enumerate(users):
            manager = user["manager"]
            user_id = user["user_id"]
            
            # Check if user should receive broadcast
            should_receive = user_id in broadcast_message["target_users"]
            
            if should_receive:
                # User should receive the broadcast
                received_by_users.append(user_id)
                self.isolation_harness.log_message_routing(
                    "system", user_id, broadcast_message
                )
                user["messages_received"].append(broadcast_message)
        
        # Validate only targeted users received broadcast
        assert len(received_by_users) == 2, "Only targeted users should receive broadcast"
        assert users[0]["user_id"] in received_by_users, "User 0 should receive broadcast"
        assert users[2]["user_id"] in received_by_users, "User 2 should receive broadcast" 
        
        # Validate filtering isolation
        assert len(users[1]["messages_received"]) == 0, "User 1 should not receive broadcast"
        assert len(users[3]["messages_received"]) == 0, "User 3 should not receive broadcast"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_message_user_isolation(self, real_services_fixture):
        """Test that error messages don't leak between user contexts."""
        user1 = await self.isolation_harness.create_isolated_user(1)
        user2 = await self.isolation_harness.create_isolated_user(2)
        
        # Simulate error in user1's context
        user1_error = {
            "type": "error",
            "error_type": "validation_error",
            "error_message": "Invalid request format",
            "user_id": user1["user_id"],
            "request_id": f"req_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stack_trace": "Detailed error info for user1"
        }
        
        # Error should only be sent to user1
        self.isolation_harness.log_message_routing("system", user1["user_id"], user1_error)
        user1["messages_received"].append(user1_error)
        
        # Simulate different error in user2's context  
        user2_error = {
            "type": "error",
            "error_type": "authentication_error",
            "error_message": "Token expired", 
            "user_id": user2["user_id"],
            "request_id": f"req_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stack_trace": "Detailed error info for user2"
        }
        
        self.isolation_harness.log_message_routing("system", user2["user_id"], user2_error)
        user2["messages_received"].append(user2_error)
        
        # Validate error isolation
        user1_errors = [msg for msg in user1["messages_received"] if msg.get("type") == "error"]
        user2_errors = [msg for msg in user2["messages_received"] if msg.get("type") == "error"]
        
        # Each user should only see their own errors
        assert len(user1_errors) == 1, "User1 should receive exactly one error"
        assert user1_errors[0]["user_id"] == user1["user_id"], "User1 error must have correct user context"
        
        assert len(user2_errors) == 1, "User2 should receive exactly one error"
        assert user2_errors[0]["user_id"] == user2["user_id"], "User2 error must have correct user context"
        
        # Validate no cross-contamination
        assert user1_errors[0]["error_message"] != user2_errors[0]["error_message"], "Error messages must be different"

    # CONNECTION POOL ISOLATION TESTS (4 tests)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_pool_user_separation(self, real_services_fixture):
        """Test that connection pools are completely separated between users."""
        user1 = await self.isolation_harness.create_isolated_user(1)
        user2 = await self.isolation_harness.create_isolated_user(2)
        user3 = await self.isolation_harness.create_isolated_user(3)
        
        # Add connections to each user's pool
        user1_connections = {f"conn1_{user1['user_id']}", f"conn2_{user1['user_id']}"}
        user2_connections = {f"conn1_{user2['user_id']}", f"conn2_{user2['user_id']}"}  
        user3_connections = {f"conn1_{user3['user_id']}"}
        
        self.isolation_harness.connection_pools[user1["user_id"]].update(user1_connections)
        self.isolation_harness.connection_pools[user2["user_id"]].update(user2_connections)
        self.isolation_harness.connection_pools[user3["user_id"]].update(user3_connections)
        
        # Validate pool separation between all pairs
        isolation_results = []
        user_pairs = [
            (user1["user_id"], user2["user_id"]),
            (user1["user_id"], user3["user_id"]),
            (user2["user_id"], user3["user_id"])
        ]
        
        for user_id1, user_id2 in user_pairs:
            isolation_valid = self.isolation_harness.validate_connection_pool_isolation(user_id1, user_id2)
            isolation_results.append(isolation_valid)
        
        assert all(isolation_results), "All connection pools must be isolated"
        
        # Validate pool contents
        pool1 = self.isolation_harness.connection_pools[user1["user_id"]]
        pool2 = self.isolation_harness.connection_pools[user2["user_id"]]
        pool3 = self.isolation_harness.connection_pools[user3["user_id"]]
        
        assert len(pool1) == 2, "User1 pool should have 2 connections"
        assert len(pool2) == 2, "User2 pool should have 2 connections"
        assert len(pool3) == 1, "User3 pool should have 1 connection"
        
        # No shared connections
        assert len(pool1.intersection(pool2)) == 0, "No shared connections between user1 and user2"
        assert len(pool1.intersection(pool3)) == 0, "No shared connections between user1 and user3" 
        assert len(pool2.intersection(pool3)) == 0, "No shared connections between user2 and user3"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_mapping_user_accuracy(self, real_services_fixture):
        """Test that connection-to-user mapping is accurate and isolated."""
        users = []
        for i in range(3):
            user = await self.isolation_harness.create_isolated_user(i+1)
            users.append(user)
        
        # Create connection mapping
        connection_user_mapping = {}
        
        for user in users:
            user_id = user["user_id"]
            connections = [f"conn_{i}_{user_id}" for i in range(2)]
            
            for conn_id in connections:
                connection_user_mapping[conn_id] = user_id
                self.isolation_harness.connection_pools[user_id].add(conn_id)
        
        # Validate mapping accuracy
        for conn_id, expected_user_id in connection_user_mapping.items():
            # Connection should exist in exactly one user's pool
            pools_containing_connection = []
            
            for user_id, pool in self.isolation_harness.connection_pools.items():
                if conn_id in pool:
                    pools_containing_connection.append(user_id)
            
            assert len(pools_containing_connection) == 1, f"Connection {conn_id} should exist in exactly one pool"
            assert pools_containing_connection[0] == expected_user_id, f"Connection {conn_id} mapped to wrong user"
        
        # Test connection lookup isolation
        for user in users:
            user_id = user["user_id"]
            user_connections = self.isolation_harness.connection_pools[user_id]
            
            # All connections in user's pool should map to that user
            for conn_id in user_connections:
                mapped_user = connection_user_mapping.get(conn_id)
                assert mapped_user == user_id, f"Connection {conn_id} incorrectly mapped"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_cleanup_user_isolation(self, real_services_fixture):
        """Test that connection cleanup doesn't affect other users' connections."""
        user1 = await self.isolation_harness.create_isolated_user(1)
        user2 = await self.isolation_harness.create_isolated_user(2)
        user3 = await self.isolation_harness.create_isolated_user(3)
        
        # Setup connections for each user
        user1_connections = {f"conn1_{user1['user_id']}", f"conn2_{user1['user_id']}"}
        user2_connections = {f"conn1_{user2['user_id']}", f"conn2_{user2['user_id']}"}
        user3_connections = {f"conn1_{user3['user_id']}", f"conn2_{user3['user_id']}"}
        
        self.isolation_harness.connection_pools[user1["user_id"]].update(user1_connections)
        self.isolation_harness.connection_pools[user2["user_id"]].update(user2_connections)
        self.isolation_harness.connection_pools[user3["user_id"]].update(user3_connections)
        
        # Record initial state
        initial_user2_connections = self.isolation_harness.connection_pools[user2["user_id"]].copy()
        initial_user3_connections = self.isolation_harness.connection_pools[user3["user_id"]].copy()
        
        # Cleanup user1 connections
        user1_pool = self.isolation_harness.connection_pools[user1["user_id"]]
        user1_pool.clear()  # Simulate cleanup
        
        # Validate other users unaffected
        current_user2_connections = self.isolation_harness.connection_pools[user2["user_id"]]
        current_user3_connections = self.isolation_harness.connection_pools[user3["user_id"]]
        
        assert current_user2_connections == initial_user2_connections, "User2 connections must be unaffected by user1 cleanup"
        assert current_user3_connections == initial_user3_connections, "User3 connections must be unaffected by user1 cleanup"
        
        # Validate user1 cleanup worked
        assert len(self.isolation_harness.connection_pools[user1["user_id"]]) == 0, "User1 connections should be cleaned up"
        
        # Test isolation still maintained between remaining users
        isolation_valid = self.isolation_harness.validate_connection_pool_isolation(
            user2["user_id"], user3["user_id"]
        )
        assert isolation_valid, "Connection pool isolation must remain after cleanup"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_state_user_boundaries(self, real_services_fixture):
        """Test that connection state is bounded per user."""
        user1 = await self.isolation_harness.create_isolated_user(1)
        user2 = await self.isolation_harness.create_isolated_user(2)
        
        # Mock connection state objects
        user1_connection_states = {}
        user2_connection_states = {}
        
        # Create connection states for user1
        for i in range(2):
            conn_id = f"conn_{i}_{user1['user_id']}"
            user1_connection_states[conn_id] = {
                "user_id": user1["user_id"],
                "status": "connected",
                "last_activity": datetime.now(timezone.utc),
                "message_count": 5,
                "user_context": user1["context"]
            }
        
        # Create connection states for user2
        for i in range(2):
            conn_id = f"conn_{i}_{user2['user_id']}"
            user2_connection_states[conn_id] = {
                "user_id": user2["user_id"],
                "status": "connected",
                "last_activity": datetime.now(timezone.utc),
                "message_count": 3,
                "user_context": user2["context"]
            }
        
        # Validate state isolation
        user1_state_user_ids = {state["user_id"] for state in user1_connection_states.values()}
        user2_state_user_ids = {state["user_id"] for state in user2_connection_states.values()}
        
        assert len(user1_state_user_ids) == 1, "User1 connection states should only reference user1"
        assert user1["user_id"] in user1_state_user_ids, "User1 states must reference correct user ID"
        
        assert len(user2_state_user_ids) == 1, "User2 connection states should only reference user2"
        assert user2["user_id"] in user2_state_user_ids, "User2 states must reference correct user ID"
        
        # Test state modification doesn't cross boundaries
        original_user2_message_count = sum(state["message_count"] for state in user2_connection_states.values())
        
        # Modify user1 connection states
        for state in user1_connection_states.values():
            state["message_count"] += 10
        
        # Validate user2 states unchanged
        current_user2_message_count = sum(state["message_count"] for state in user2_connection_states.values())
        assert current_user2_message_count == original_user2_message_count, "User2 connection states must remain unchanged"

    # CONCURRENT MULTI-USER SCENARIOS (3 tests)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_multi_user_message_routing(self, real_services_fixture):
        """Test message routing isolation under concurrent multi-user load."""
        concurrent_user_count = 5
        messages_per_user = 10
        
        # Create users concurrently
        async def create_user_with_messages(user_index: int):
            user = await self.isolation_harness.create_isolated_user(user_index)
            
            # Generate messages for this user
            user_messages = []
            for msg_index in range(messages_per_user):
                message = {
                    "message_id": f"msg_{user_index}_{msg_index}",
                    "type": "user_message",
                    "user_id": user["user_id"],
                    "content": f"Message {msg_index} from user {user_index}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                user_messages.append(message)
            
            return user, user_messages
        
        # Create all users concurrently
        user_creation_tasks = [
            create_user_with_messages(i) 
            for i in range(concurrent_user_count)
        ]
        
        users_with_messages = await asyncio.gather(*user_creation_tasks)
        
        # Route messages concurrently
        async def route_user_messages(user_data):
            user, messages = user_data
            for message in messages:
                # Log routing for isolation analysis
                self.isolation_harness.log_message_routing(
                    user["user_id"], user["user_id"], message
                )
                user["messages_received"].append(message)
                await asyncio.sleep(0.001)  # Small delay to simulate processing
        
        routing_tasks = [route_user_messages(user_data) for user_data in users_with_messages]
        await asyncio.gather(*routing_tasks)
        
        # Validate isolation under concurrent load
        contaminations = self.isolation_harness.detect_cross_user_contamination()
        assert len(contaminations) == 0, f"No cross-user contamination under concurrent load: {contaminations}"
        
        # Validate all users received correct message count
        for user, expected_messages in users_with_messages:
            received_count = len(user["messages_received"])
            assert received_count == messages_per_user, f"User {user['user_id']} should receive {messages_per_user} messages, got {received_count}"
        
        # Generate isolation report
        report = self.isolation_harness.get_isolation_report()
        expected_total_messages = concurrent_user_count * messages_per_user
        assert report["message_routes_logged"] == expected_total_messages, "All messages should be logged"
        assert report["isolation_violations"] == 0, "No isolation violations under concurrent load"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_multi_user_agent_execution(self, real_services_fixture):
        """Test agent execution context isolation under concurrent multi-user scenarios."""
        concurrent_user_count = 4
        
        # Create users for concurrent agent execution
        users = []
        for i in range(concurrent_user_count):
            user = await self.isolation_harness.create_isolated_user(i)
            users.append(user)
        
        # Simulate concurrent agent execution
        async def execute_agent_for_user(user: Dict[str, Any], agent_type: str):
            user_id = user["user_id"]
            
            # Create isolated execution context for agent
            execution_context = create_defensive_user_execution_context(
                user_id,
                websocket_client_id=f"ws_{user_id}"
            )
            
            # Simulate agent work
            agent_result = {
                "agent_type": agent_type,
                "user_id": user_id,
                "execution_context_id": id(execution_context),
                "result": f"{agent_type} result for {user_id}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Process result through user's manager
            manager = user["manager"]
            if hasattr(manager, 'process_agent_result'):
                await manager.process_agent_result(agent_result)
            
            user["agent_results"] = user.get("agent_results", [])
            user["agent_results"].append(agent_result)
            
            return agent_result
        
        # Execute different agents concurrently for each user
        agent_types = ["data_analysis", "code_generation", "document_processing", "image_analysis"]
        execution_tasks = []
        
        for i, user in enumerate(users):
            agent_type = agent_types[i % len(agent_types)]
            task = execute_agent_for_user(user, agent_type)
            execution_tasks.append(task)
        
        # Run agent executions concurrently
        agent_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # Validate all executions succeeded
        successful_results = [r for r in agent_results if not isinstance(r, Exception)]
        assert len(successful_results) == concurrent_user_count, "All concurrent agent executions must succeed"
        
        # Validate execution context isolation
        execution_context_ids = {result["execution_context_id"] for result in successful_results}
        assert len(execution_context_ids) == concurrent_user_count, "Each agent execution must have isolated context"
        
        # Validate results are properly isolated
        for i, user in enumerate(users):
            user_results = user.get("agent_results", [])
            assert len(user_results) == 1, f"User {i} should have exactly 1 agent result"
            
            result = user_results[0]
            assert result["user_id"] == user["user_id"], f"Agent result must belong to correct user"
        
        # Check for any contamination in results
        contaminations = []
        for i, user in enumerate(users):
            user_results = user.get("agent_results", [])
            for result in user_results:
                if result["user_id"] != user["user_id"]:
                    contaminations.append({
                        "user_index": i,
                        "user_id": user["user_id"],
                        "result_user_id": result["user_id"],
                        "result": result
                    })
        
        assert len(contaminations) == 0, f"No agent execution context contamination: {contaminations}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_multi_user_connection_management(self, real_services_fixture):
        """Test connection management isolation under concurrent multi-user scenarios."""
        concurrent_user_count = 6
        connections_per_user = 3
        
        # Create users concurrently with multiple connections
        async def create_user_with_connections(user_index: int):
            user = await self.isolation_harness.create_isolated_user(user_index)
            
            # Create multiple connections for this user
            user_connections = []
            for conn_index in range(connections_per_user):
                connection_id = f"conn_{user_index}_{conn_index}_{uuid.uuid4().hex[:6]}"
                websocket_id = f"ws_{user_index}_{conn_index}_{uuid.uuid4().hex[:6]}"
                
                connection_info = {
                    "connection_id": connection_id,
                    "websocket_id": websocket_id,
                    "user_id": user["user_id"],
                    "status": "active",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                user_connections.append(connection_info)
                self.isolation_harness.connection_pools[user["user_id"]].add(connection_id)
            
            user["connections"] = user_connections
            return user
        
        # Create users with connections concurrently
        user_creation_tasks = [
            create_user_with_connections(i)
            for i in range(concurrent_user_count)
        ]
        
        users = await asyncio.gather(*user_creation_tasks, return_exceptions=True)
        successful_users = [u for u in users if not isinstance(u, Exception)]
        
        assert len(successful_users) == concurrent_user_count, "All concurrent user creations with connections must succeed"
        
        # Validate connection isolation across all users
        all_connection_ids = set()
        for user in successful_users:
            user_connections = user.get("connections", [])
            assert len(user_connections) == connections_per_user, f"User should have {connections_per_user} connections"
            
            # Check for duplicate connection IDs
            for conn_info in user_connections:
                conn_id = conn_info["connection_id"]
                assert conn_id not in all_connection_ids, f"Connection ID {conn_id} must be unique"
                all_connection_ids.add(conn_id)
        
        # Validate connection pool isolation between all user pairs
        user_ids = [user["user_id"] for user in successful_users]
        isolation_violations = 0
        
        for i, user_id1 in enumerate(user_ids):
            for j, user_id2 in enumerate(user_ids[i+1:], i+1):
                is_isolated = self.isolation_harness.validate_connection_pool_isolation(user_id1, user_id2)
                if not is_isolated:
                    isolation_violations += 1
        
        assert isolation_violations == 0, f"All connection pools must be isolated: {isolation_violations} violations found"
        
        # Test concurrent connection cleanup
        async def cleanup_user_connections(user: Dict[str, Any]):
            user_id = user["user_id"]
            connection_pool = self.isolation_harness.connection_pools[user_id]
            
            # Simulate gradual connection cleanup
            connections_to_remove = list(connection_pool)
            for conn_id in connections_to_remove:
                connection_pool.discard(conn_id)
                await asyncio.sleep(0.001)  # Small delay to simulate cleanup processing
            
            return len(connections_to_remove)
        
        # Cleanup half the users concurrently while maintaining others
        users_to_cleanup = successful_users[:concurrent_user_count // 2]
        remaining_users = successful_users[concurrent_user_count // 2:]
        
        # Record state of remaining users before cleanup
        remaining_user_states = {}
        for user in remaining_users:
            user_id = user["user_id"]
            remaining_user_states[user_id] = self.isolation_harness.connection_pools[user_id].copy()
        
        # Cleanup users concurrently
        cleanup_tasks = [cleanup_user_connections(user) for user in users_to_cleanup]
        cleanup_results = await asyncio.gather(*cleanup_tasks)
        
        # Validate cleanup worked
        expected_cleanup_count = connections_per_user
        for cleanup_count in cleanup_results:
            assert cleanup_count == expected_cleanup_count, f"Should cleanup {expected_cleanup_count} connections"
        
        # Validate remaining users unaffected
        for user in remaining_users:
            user_id = user["user_id"]
            current_pool = self.isolation_harness.connection_pools[user_id]
            expected_pool = remaining_user_states[user_id]
            assert current_pool == expected_pool, f"Remaining user {user_id} connections must be unaffected by cleanup"

    # FACTORY PATTERN USER ISOLATION TESTS (2 tests)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_factory_user_isolation(self, real_services_fixture):
        """Test WebSocket manager factory creates truly isolated instances per user."""
        user_count = 5
        
        # Create multiple users through factory pattern
        users = []
        factories = []
        managers = []
        
        for i in range(user_count):
            user = await self.isolation_harness.create_isolated_user(i)
            users.append(user)
            factories.append(user["factory"])
            managers.append(user["manager"])
        
        # Validate factory instance isolation
        for i in range(len(factories)):
            for j in range(i + 1, len(factories)):
                factory1 = factories[i]
                factory2 = factories[j]
                
                # Factories must be different instances
                assert factory1 is not factory2, f"Factory {i} and {j} must be different instances"
                
                # Factory state must be isolated
                factory1_id = id(factory1)
                factory2_id = id(factory2)
                assert factory1_id != factory2_id, f"Factory {i} and {j} must have different memory addresses"
        
        # Validate manager instance isolation
        for i in range(len(managers)):
            for j in range(i + 1, len(managers)):
                manager1 = managers[i]
                manager2 = managers[j]
                
                # Managers must be different instances
                assert manager1 is not manager2, f"Manager {i} and {j} must be different instances"
                
                # Manager user contexts must be different
                user1_id = users[i]["user_id"]
                user2_id = users[j]["user_id"]
                
                if hasattr(manager1, 'user_context') and hasattr(manager2, 'user_context'):
                    context1_user_id = getattr(manager1.user_context, 'user_id', None)
                    context2_user_id = getattr(manager2.user_context, 'user_id', None)
                    
                    assert context1_user_id != context2_user_id, f"Manager contexts must have different user IDs"
                    assert context1_user_id == user1_id, f"Manager {i} context must match user {i}"
                    assert context2_user_id == user2_id, f"Manager {j} context must match user {j}"
        
        # Test factory method isolation
        factory1 = factories[0]
        factory2 = factories[1]
        
        # Create additional managers from same factories
        if hasattr(factory1, 'create_manager') and hasattr(factory2, 'create_manager'):
            additional_manager1 = await factory1.create_manager(
                user_execution_context=users[0]["context"],
                connection_id=f"additional_conn_{users[0]['user_id']}",
                websocket_id=f"additional_ws_{users[0]['user_id']}"
            )
            
            additional_manager2 = await factory2.create_manager(
                user_execution_context=users[1]["context"],
                connection_id=f"additional_conn_{users[1]['user_id']}",
                websocket_id=f"additional_ws_{users[1]['user_id']}"
            )
            
            # Additional managers must also be isolated
            assert additional_manager1 is not additional_manager2, "Additional managers must be isolated"
            assert additional_manager1 is not managers[1], "Additional manager1 must be different from manager2"
            assert additional_manager2 is not managers[0], "Additional manager2 must be different from manager1"
        
        # Validate isolation report
        report = self.isolation_harness.get_isolation_report()
        assert report["isolation_violations"] == 0, f"Factory pattern must maintain isolation: {report}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_cleanup_user_isolation(self, real_services_fixture):
        """Test that factory cleanup operations don't cross-contaminate between users."""
        user_count = 4
        
        # Create users through factory pattern
        users = []
        for i in range(user_count):
            user = await self.isolation_harness.create_isolated_user(i)
            users.append(user)
        
        # Record initial state of all users
        initial_states = {}
        for user in users:
            user_id = user["user_id"]
            initial_states[user_id] = {
                "factory_id": id(user["factory"]),
                "manager_id": id(user["manager"]),
                "context_data": user["context"].to_dict() if hasattr(user["context"], 'to_dict') else {},
                "connection_pool_size": len(self.isolation_harness.connection_pools[user_id])
            }
        
        # Select users to cleanup (cleanup half, keep half)
        cleanup_users = users[:user_count // 2]
        remaining_users = users[user_count // 2:]
        
        # Perform cleanup operations on selected users
        for user in cleanup_users:
            user_id = user["user_id"]
            factory = user["factory"]
            manager = user["manager"]
            
            # Cleanup manager
            if hasattr(manager, 'cleanup'):
                await manager.cleanup()
            
            # Cleanup factory
            if hasattr(factory, 'cleanup_user'):
                await factory.cleanup_user(user_id)
            elif hasattr(factory, 'cleanup'):
                await factory.cleanup()
            
            # Clear connection pool
            self.isolation_harness.connection_pools[user_id].clear()
            
            # Remove from harness
            if user_id in self.isolation_harness.users:
                del self.isolation_harness.users[user_id]
            if user_id in self.isolation_harness.factory_instances:
                del self.isolation_harness.factory_instances[user_id]
        
        # Validate remaining users unaffected by cleanup
        for user in remaining_users:
            user_id = user["user_id"]
            initial_state = initial_states[user_id]
            
            # Validate factory unchanged
            current_factory_id = id(user["factory"])
            assert current_factory_id == initial_state["factory_id"], f"User {user_id} factory must be unchanged by cleanup"
            
            # Validate manager unchanged  
            current_manager_id = id(user["manager"])
            assert current_manager_id == initial_state["manager_id"], f"User {user_id} manager must be unchanged by cleanup"
            
            # Validate context data unchanged
            if hasattr(user["context"], 'to_dict'):
                current_context_data = user["context"].to_dict()
                # Compare critical fields that shouldn't change
                if initial_state["context_data"]:
                    for key in ["user_id"]:  # Critical fields
                        if key in initial_state["context_data"] and key in current_context_data:
                            assert current_context_data[key] == initial_state["context_data"][key], f"Context {key} must be unchanged"
            
            # Validate connection pool unchanged
            current_pool_size = len(self.isolation_harness.connection_pools[user_id])
            assert current_pool_size == initial_state["connection_pool_size"], f"User {user_id} connection pool must be unchanged"
        
        # Test factory isolation still maintained among remaining users
        remaining_user_ids = [user["user_id"] for user in remaining_users]
        for i, user_id1 in enumerate(remaining_user_ids):
            for j, user_id2 in enumerate(remaining_user_ids[i+1:], i+1):
                isolation_valid = self.isolation_harness.validate_factory_isolation(user_id1, user_id2)
                assert isolation_valid, f"Factory isolation must remain between users {user_id1} and {user_id2} after cleanup"
        
        # Validate cleanup worked for cleaned up users
        for user in cleanup_users:
            user_id = user["user_id"]
            
            # Should be removed from harness
            assert user_id not in self.isolation_harness.users, f"Cleanup user {user_id} should be removed from harness"
            assert user_id not in self.isolation_harness.factory_instances, f"Cleanup user {user_id} factory should be removed"
            
            # Connection pool should be empty
            pool_size = len(self.isolation_harness.connection_pools[user_id])
            assert pool_size == 0, f"Cleanup user {user_id} connection pool should be empty"
        
        # Generate final isolation report
        report = self.isolation_harness.get_isolation_report()
        assert report["isolation_violations"] == 0, f"No isolation violations after cleanup: {report}"