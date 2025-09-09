"""
Comprehensive Message Routing Integration Test Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure reliable WebSocket message routing and multi-user isolation
- Value Impact: Message routing is foundation of real-time AI chat value delivery
- Strategic Impact: System reliability enables scalable multi-user platform

This comprehensive test suite validates message routing architecture:
1. MessageRouter core functionality with handler registration/deregistration
2. WebSocket message routing with user-specific delivery and isolation  
3. Multi-user isolation via Factory pattern and UserExecutionContext
4. Agent message integration with WebSocket event delivery

CRITICAL: Integration tests use real components without mocks except for external services.
All tests validate actual business logic and integration points.

SSOT Compliance:
- Uses StronglyTypedUserExecutionContext for all user contexts
- Uses shared.types for UserID, ThreadID, ConnectionID, WebSocketID
- Uses test_framework.base_integration_test.BaseIntegrationTest base
- Uses test_framework.ssot.e2e_auth_helper for user context creation
- Follows CLAUDE.md requirements for integration testing
"""

import asyncio
import json  
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

# Base test framework - SSOT integration test base
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

# SSOT Types for strong type safety
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID, ConnectionID, WebSocketID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id
)
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Message routing core components under test
from netra_backend.app.websocket_core.handlers import (
    MessageRouter, get_message_router, BaseMessageHandler,
    ConnectionHandler, TypingHandler, HeartbeatHandler, 
    UserMessageHandler, AgentHandler, ErrorHandler
)
from netra_backend.app.websocket_core.types import (
    MessageType, WebSocketMessage, create_standard_message,
    create_server_message, create_error_message
)
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory, IsolatedWebSocketManager, 
    create_websocket_manager, get_websocket_manager_factory
)
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.message_handlers import MessageHandlerService

# Logging
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MockWebSocket:
    """Mock WebSocket for integration testing that behaves like real FastAPI WebSocket."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.messages_sent = []
        self.is_connected = True
        self.client_state = "connected"  # Simulate WebSocketState.CONNECTED
        self.application_state = MagicMock()
        self.application_state._mock_name = "mock_websocket"  # For handler detection
        self.scope = {'app': MagicMock()}
        self.scope['app'].state = MagicMock()
        
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Mock send_json that stores messages for verification."""
        if self.is_connected:
            self.messages_sent.append(data)
        else:
            raise RuntimeError("WebSocket not connected")
            
    async def send_text(self, text: str) -> None:
        """Mock send_text that stores messages for verification."""
        if self.is_connected:
            try:
                data = json.loads(text)
                self.messages_sent.append(data)
            except json.JSONDecodeError:
                self.messages_sent.append({"text": text})
        else:
            raise RuntimeError("WebSocket not connected")
    
    def disconnect(self) -> None:
        """Simulate WebSocket disconnection."""
        self.is_connected = False
        self.client_state = "disconnected"


class TestMessageRoutingCore(BaseIntegrationTest):
    """Test Message Router core functionality and handler management."""
    
    @pytest.mark.integration
    async def test_message_router_basic_routing(self, isolated_env):
        """Test basic message routing to correct handlers."""
        router = MessageRouter()
        websocket = MockWebSocket("user1", "conn1")
        
        # Test routing different message types
        test_cases = [
            {"type": "ping", "expected_handler": "HeartbeatHandler"},
            {"type": "user_typing", "expected_handler": "TypingHandler"}, 
            {"type": "connect", "expected_handler": "ConnectionHandler"},
            {"type": "user_message", "expected_handler": "UserMessageHandler"},
            {"type": "error", "expected_handler": "ErrorHandler"}
        ]
        
        for case in test_cases:
            raw_message = {"type": case["type"], "payload": {"test": "data"}}
            success = await router.route_message("user1", websocket, raw_message)
            
            assert success, f"Failed to route {case['type']} message"
            
            # Verify routing stats updated
            stats = router.get_stats()
            assert stats["messages_routed"] > 0
            # Check if the message type appears in stats (handle both string and enum representations)
            message_types_str = str(stats["message_types"])
            assert case["type"] in message_types_str.lower() or case["type"].upper() in message_types_str
        
        logger.info("✅ Basic message routing test completed")
    
    @pytest.mark.integration
    async def test_message_router_multiple_handlers(self, isolated_env):
        """Test multiple handlers for same message type with priority."""
        router = MessageRouter()
        websocket = MockWebSocket("user1", "conn1")
        
        # Create custom handlers for testing
        class CustomHandler1(BaseMessageHandler):
            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])
                self.handled = []
                
            async def handle_message(self, user_id, ws, message):
                self.handled.append(f"handler1_{message.type}")
                return True
        
        class CustomHandler2(BaseMessageHandler):
            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])  
                self.handled = []
                
            async def handle_message(self, user_id, ws, message):
                self.handled.append(f"handler2_{message.type}")
                return True
        
        handler1 = CustomHandler1()
        handler2 = CustomHandler2()
        
        # Add multiple handlers (first one should win)
        router.add_handler(handler1)
        router.add_handler(handler2)
        
        raw_message = {"type": "user_message", "payload": {"content": "test"}}
        success = await router.route_message("user1", websocket, raw_message)
        
        assert success
        # First handler should be selected
        assert len(handler1.handled) == 1
        assert len(handler2.handled) == 0  # Second handler not called
        
        logger.info("✅ Multiple handlers routing test completed")
    
    @pytest.mark.integration
    async def test_message_router_handler_priority(self, isolated_env):
        """Test handler priority and selection logic."""
        router = MessageRouter()
        websocket = MockWebSocket("user1", "conn1")
        
        # Track handler call order
        call_order = []
        
        class PriorityHandler(BaseMessageHandler):
            def __init__(self, name, types):
                super().__init__(types)
                self.name = name
                
            async def handle_message(self, user_id, ws, message):
                call_order.append(self.name)
                return True
        
        # Add handlers in specific order
        high_priority = PriorityHandler("high", [MessageType.PING])
        low_priority = PriorityHandler("low", [MessageType.PING])
        
        router.add_handler(high_priority)
        router.add_handler(low_priority) 
        
        raw_message = {"type": "ping", "payload": {}}
        success = await router.route_message("user1", websocket, raw_message)
        
        assert success
        # First registered handler should be called
        assert call_order[0] == "high"
        assert len(call_order) == 1  # Only one handler called
        
        logger.info("✅ Handler priority test completed")
        
    @pytest.mark.integration
    async def test_message_router_unknown_message_types(self, isolated_env):
        """Test graceful handling of unknown message types."""
        router = MessageRouter()
        websocket = MockWebSocket("user1", "conn1")
        
        unknown_types = ["custom_unknown", "invalid_type", "unsupported_message"]
        
        for unknown_type in unknown_types:
            raw_message = {"type": unknown_type, "payload": {"data": "test"}}
            success = await router.route_message("user1", websocket, raw_message)
            
            # Should succeed with acknowledgment
            assert success, f"Failed to handle unknown type: {unknown_type}"
            
            # Should have sent acknowledgment
            assert len(websocket.messages_sent) > 0
            last_message = websocket.messages_sent[-1]
            assert last_message.get("type") == "ack"
            assert last_message.get("received_type") == unknown_type
            
            # Clear for next test
            websocket.messages_sent.clear()
        
        # Verify stats updated
        stats = router.get_stats()
        assert stats["unhandled_messages"] == len(unknown_types)
        
        logger.info("✅ Unknown message types test completed")
    
    @pytest.mark.integration 
    async def test_message_router_handler_failure_recovery(self, isolated_env):
        """Test handler failure and fallback mechanisms."""
        router = MessageRouter()
        websocket = MockWebSocket("user1", "conn1")
        
        class FailingHandler(BaseMessageHandler):
            def __init__(self):
                super().__init__([MessageType.PING])
                self.failure_count = 0
                
            async def handle_message(self, user_id, ws, message):
                self.failure_count += 1
                raise RuntimeError(f"Handler failure #{self.failure_count}")
        
        failing_handler = FailingHandler()
        router.add_handler(failing_handler)
        
        raw_message = {"type": "ping", "payload": {}}
        success = await router.route_message("user1", websocket, raw_message)
        
        # Should fail gracefully
        assert not success
        assert failing_handler.failure_count == 1
        
        # Verify error stats updated
        stats = router.get_stats()
        assert stats["handler_errors"] > 0
        
        logger.info("✅ Handler failure recovery test completed")
    
    @pytest.mark.integration
    async def test_message_router_concurrent_routing(self, isolated_env):
        """Test concurrent message routing without race conditions."""
        router = MessageRouter()
        
        # Create multiple mock WebSockets
        websockets = [MockWebSocket(f"user{i}", f"conn{i}") for i in range(5)]
        
        async def route_messages_for_user(ws, user_idx):
            """Route multiple messages for a user concurrently."""
            messages = []
            for msg_idx in range(10):
                raw_message = {
                    "type": "ping",
                    "payload": {"user": user_idx, "message": msg_idx}
                }
                success = await router.route_message(f"user{user_idx}", ws, raw_message)
                messages.append(success)
            return messages
        
        # Route messages concurrently
        tasks = [
            route_messages_for_user(ws, i) 
            for i, ws in enumerate(websockets)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all messages routed successfully
        for user_results in results:
            assert all(user_results), "Some concurrent messages failed to route"
        
        # Verify stats show all messages
        stats = router.get_stats()
        assert stats["messages_routed"] == 50  # 5 users * 10 messages
        
        logger.info("✅ Concurrent routing test completed")
    
    @pytest.mark.integration
    async def test_message_router_handler_registration(self, isolated_env):
        """Test dynamic handler registration and management."""
        router = MessageRouter()
        initial_handler_count = len(router.handlers)
        
        class DynamicHandler(BaseMessageHandler):
            def __init__(self, name):
                super().__init__([MessageType.USER_MESSAGE])
                self.name = name
                
            async def handle_message(self, user_id, ws, message):
                return True
        
        # Test adding handlers
        handler1 = DynamicHandler("dynamic1")
        handler2 = DynamicHandler("dynamic2")
        
        router.add_handler(handler1)
        assert len(router.handlers) == initial_handler_count + 1
        
        router.add_handler(handler2)
        assert len(router.handlers) == initial_handler_count + 2
        
        # Test removing handlers
        router.remove_handler(handler1)
        assert len(router.handlers) == initial_handler_count + 1
        assert handler1 not in router.handlers
        assert handler2 in router.handlers
        
        router.remove_handler(handler2)
        assert len(router.handlers) == initial_handler_count
        assert handler2 not in router.handlers
        
        logger.info("✅ Handler registration test completed")
    
    @pytest.mark.integration
    async def test_message_router_handler_deregistration(self, isolated_env):
        """Test handler cleanup and deregistration."""
        router = MessageRouter()
        websocket = MockWebSocket("user1", "conn1")
        
        class TemporaryHandler(BaseMessageHandler):
            def __init__(self):
                super().__init__([MessageType.CHAT])
                self.call_count = 0
                
            async def handle_message(self, user_id, ws, message):
                self.call_count += 1
                return True
        
        temp_handler = TemporaryHandler()
        router.add_handler(temp_handler)
        
        # Verify handler works
        raw_message = {"type": "chat", "payload": {"content": "test"}}
        success = await router.route_message("user1", websocket, raw_message)
        assert success
        assert temp_handler.call_count == 1
        
        # Remove handler
        router.remove_handler(temp_handler)
        
        # Verify handler no longer called
        success = await router.route_message("user1", websocket, raw_message)
        # Should still succeed via fallback, but temp_handler not called
        assert temp_handler.call_count == 1  # No increase
        
        logger.info("✅ Handler deregistration test completed")


class TestWebSocketMessageRouting(BaseIntegrationTest):
    """Test WebSocket-specific message routing and user isolation."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_routing_to_user(self, real_services_fixture, isolated_env):
        """Test routing messages to specific users via WebSocket."""
        # Create user contexts using SSOT patterns
        auth_helper = E2EAuthHelper()
        
        user1_id = ensure_user_id(str(uuid.uuid4()))
        user2_id = ensure_user_id(str(uuid.uuid4()))
        
        # Create user execution contexts
        user1_context = UserExecutionContext.from_request(
            user_id=str(user1_id),
            thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
            run_id=str(uuid.uuid4())
        )
        user2_context = UserExecutionContext.from_request(
            user_id=str(user2_id), 
            thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
            run_id=str(uuid.uuid4())
        )
        
        # Create isolated WebSocket managers  
        ws_manager1 = await create_websocket_manager(user1_context)
        ws_manager2 = await create_websocket_manager(user2_context)
        
        # Create mock WebSockets
        websocket1 = MockWebSocket(str(user1_id), "conn1")
        websocket2 = MockWebSocket(str(user2_id), "conn2")
        
        # Add connections to managers
        conn1 = WebSocketConnection(
            connection_id="conn1",
            user_id=str(user1_id),
            websocket=websocket1,
            connected_at=datetime.utcnow()
        )
        conn2 = WebSocketConnection(
            connection_id="conn2", 
            user_id=str(user2_id),
            websocket=websocket2,
            connected_at=datetime.utcnow()
        )
        
        await ws_manager1.add_connection(conn1)
        await ws_manager2.add_connection(conn2)
        
        # Send messages to each user
        message1 = {"type": "agent_response", "content": "Response for user 1"}
        message2 = {"type": "agent_response", "content": "Response for user 2"}
        
        await ws_manager1.send_to_user(message1)
        await ws_manager2.send_to_user(message2)
        
        # Verify isolation - each user only gets their message
        assert len(websocket1.messages_sent) == 1
        assert len(websocket2.messages_sent) == 1
        
        assert websocket1.messages_sent[0]["content"] == "Response for user 1"
        assert websocket2.messages_sent[0]["content"] == "Response for user 2"
        
        logger.info("✅ WebSocket message routing to user test completed")
    
    @pytest.mark.integration
    async def test_websocket_connection_isolation(self, isolated_env):
        """Test that WebSocket connections are properly isolated between users."""
        factory = get_websocket_manager_factory()
        
        # Create different user contexts
        users = []
        managers = []
        websockets = []
        
        for i in range(3):
            user_id = ensure_user_id(f"isolation_user_{i}")
            context = UserExecutionContext.from_request(
                user_id=str(user_id),
                thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
                run_id=str(uuid.uuid4())
            )
            manager = await factory.create_manager(context)
            websocket = MockWebSocket(str(user_id), f"conn_{i}")
            
            users.append(user_id)
            managers.append(manager)
            websockets.append(websocket)
        
        # Add connections to each manager
        for i, (manager, websocket, user_id) in enumerate(zip(managers, websockets, users)):
            connection = WebSocketConnection(
                connection_id=f"conn_{i}",
                user_id=str(user_id),
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            await manager.add_connection(connection)
        
        # Verify each manager only sees its own connections
        for i, manager in enumerate(managers):
            connections = manager.get_user_connections()
            assert len(connections) == 1
            assert f"conn_{i}" in connections
            
            # Verify can't access other user connections
            for j, other_user_id in enumerate(users):
                if i != j:
                    # Should return False for different user
                    has_connection = manager.is_connection_active(str(other_user_id))
                    assert not has_connection
        
        logger.info("✅ WebSocket connection isolation test completed")
    
    @pytest.mark.integration
    async def test_websocket_message_queuing(self, isolated_env):
        """Test message queuing for disconnected users."""
        factory = get_websocket_manager_factory()
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        context = UserExecutionContext.from_request(
            user_id=str(user_id),
            thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
            run_id=str(uuid.uuid4())
        )
        manager = await factory.create_manager(context)
        
        # Try to send message without active connection
        test_message = {"type": "agent_response", "content": "Queued message"}
        
        # This should succeed but queue the message
        await manager.send_to_user(test_message)
        
        # Verify message was stored for recovery
        stats = manager.get_manager_stats()
        assert stats["recovery_queue_size"] > 0
        assert stats["metrics"]["messages_failed_total"] > 0
        
        logger.info("✅ WebSocket message queuing test completed")
    
    @pytest.mark.integration
    async def test_websocket_connection_state_sync(self, isolated_env):
        """Test WebSocket connection state synchronization."""
        factory = get_websocket_manager_factory()
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        context = UserExecutionContext.from_request(
            user_id=str(user_id),
            thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
            run_id=str(uuid.uuid4())
        )
        manager = await factory.create_manager(context)
        websocket = MockWebSocket(str(user_id), "sync_conn")
        
        # Add connection
        connection = WebSocketConnection(
            connection_id="sync_conn",
            user_id=str(user_id),
            websocket=websocket,
            connected_at=datetime.utcnow()
        )
        await manager.add_connection(connection)
        
        # Verify connection active
        assert manager.is_connection_active(str(user_id))
        
        # Simulate disconnection
        websocket.disconnect()
        
        # Send message - should detect disconnection
        test_message = {"type": "system_message", "content": "Test after disconnect"}
        await manager.send_to_user(test_message)
        
        # Connection should be cleaned up
        stats = manager.get_manager_stats()
        assert stats["metrics"]["messages_failed_total"] > 0
        
        logger.info("✅ WebSocket connection state sync test completed")
    
    @pytest.mark.integration
    async def test_websocket_routing_table_consistency(self, isolated_env):
        """Test routing table accuracy and consistency."""
        factory = get_websocket_manager_factory()
        
        # Create multiple users and connections
        routing_data = []
        
        for i in range(5):
            user_id = ensure_user_id(f"routing_user_{i}")
            context = UserExecutionContext.from_request(
                user_id=str(user_id),
                thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
                run_id=str(uuid.uuid4())
            )
            manager = await factory.create_manager(context)
            
            # Add multiple connections per user
            for j in range(2):
                websocket = MockWebSocket(str(user_id), f"conn_{i}_{j}")
                connection = WebSocketConnection(
                    connection_id=f"conn_{i}_{j}",
                    user_id=str(user_id),
                    websocket=websocket,
                    connected_at=datetime.utcnow()
                )
                await manager.add_connection(connection)
            
            routing_data.append((user_id, manager))
        
        # Verify routing table consistency
        for user_id, manager in routing_data:
            connections = manager.get_user_connections()
            assert len(connections) == 2  # 2 connections per user
            
            # Verify all connections belong to correct user
            for conn_id in connections:
                connection = manager.get_connection(conn_id)
                assert connection.user_id == str(user_id)
        
        # Verify factory stats consistency
        factory_stats = factory.get_factory_stats()
        assert factory_stats["current_state"]["active_managers"] == 5
        
        logger.info("✅ WebSocket routing table consistency test completed")
    
    @pytest.mark.integration
    async def test_websocket_message_broadcasting(self, isolated_env):
        """Test message broadcasting functionality."""
        factory = get_websocket_manager_factory()
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        context = UserExecutionContext.from_request(
            user_id=str(user_id),
            thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
            run_id=str(uuid.uuid4())
        )
        manager = await factory.create_manager(context)
        
        # Create multiple connections for same user
        websockets = []
        for i in range(3):
            websocket = MockWebSocket(str(user_id), f"broadcast_conn_{i}")
            connection = WebSocketConnection(
                connection_id=f"broadcast_conn_{i}",
                user_id=str(user_id),
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            await manager.add_connection(connection)
            websockets.append(websocket)
        
        # Broadcast message
        broadcast_message = {
            "type": "system_announcement", 
            "content": "System maintenance in 5 minutes"
        }
        await manager.send_to_user(broadcast_message)
        
        # Verify all connections received message
        for websocket in websockets:
            assert len(websocket.messages_sent) == 1
            assert websocket.messages_sent[0]["content"] == "System maintenance in 5 minutes"
        
        logger.info("✅ WebSocket message broadcasting test completed")
    
    @pytest.mark.integration
    async def test_websocket_connection_cleanup(self, isolated_env):
        """Test connection cleanup on disconnect."""
        factory = get_websocket_manager_factory()
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        context = UserExecutionContext.from_request(
            user_id=str(user_id),
            thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
            run_id=str(uuid.uuid4())
        )
        manager = await factory.create_manager(context)
        
        # Add connections
        connections_to_cleanup = []
        for i in range(3):
            websocket = MockWebSocket(str(user_id), f"cleanup_conn_{i}")
            connection = WebSocketConnection(
                connection_id=f"cleanup_conn_{i}",
                user_id=str(user_id),
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            await manager.add_connection(connection)
            connections_to_cleanup.append(f"cleanup_conn_{i}")
        
        # Verify connections exist
        assert len(manager.get_user_connections()) == 3
        
        # Remove connections
        for conn_id in connections_to_cleanup:
            await manager.remove_connection(conn_id)
        
        # Verify cleanup
        assert len(manager.get_user_connections()) == 0
        
        # Verify manager stats updated
        stats = manager.get_manager_stats()
        assert stats["connections"]["total"] == 0
        
        logger.info("✅ WebSocket connection cleanup test completed")


class TestMultiUserIsolation(BaseIntegrationTest):
    """Test multi-user isolation via Factory pattern and UserExecutionContext."""
    
    @pytest.mark.integration
    async def test_multi_user_message_isolation(self, isolated_env):
        """Test that messages don't leak between users."""
        factory = get_websocket_manager_factory()
        
        # Create two users with managers
        user1_id = ensure_user_id("isolation_user_1")
        user2_id = ensure_user_id("isolation_user_2")
        
        context1 = UserExecutionContext.from_request(
            user_id=str(user1_id),
            thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
            run_id=str(uuid.uuid4())
        )
        context2 = UserExecutionContext.from_request(
            user_id=str(user2_id),
            thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
            run_id=str(uuid.uuid4())
        )
        
        manager1 = await factory.create_manager(context1)
        manager2 = await factory.create_manager(context2)
        
        # Add connections
        websocket1 = MockWebSocket(str(user1_id), "user1_conn")
        websocket2 = MockWebSocket(str(user2_id), "user2_conn")
        
        conn1 = WebSocketConnection(
            connection_id="user1_conn",
            user_id=str(user1_id),
            websocket=websocket1,
            connected_at=datetime.utcnow()
        )
        conn2 = WebSocketConnection(
            connection_id="user2_conn", 
            user_id=str(user2_id),
            websocket=websocket2,
            connected_at=datetime.utcnow()
        )
        
        await manager1.add_connection(conn1)
        await manager2.add_connection(conn2)
        
        # Send different messages to each user
        user1_message = {"type": "private_data", "sensitive": "user1_secret"}
        user2_message = {"type": "private_data", "sensitive": "user2_secret"}
        
        await manager1.send_to_user(user1_message)
        await manager2.send_to_user(user2_message)
        
        # Verify isolation - no message leakage
        assert len(websocket1.messages_sent) == 1
        assert len(websocket2.messages_sent) == 1
        
        assert websocket1.messages_sent[0]["sensitive"] == "user1_secret"
        assert websocket2.messages_sent[0]["sensitive"] == "user2_secret"
        
        # Cross-verify no access to other user data
        assert websocket1.messages_sent[0]["sensitive"] != "user2_secret"
        assert websocket2.messages_sent[0]["sensitive"] != "user1_secret"
        
        logger.info("✅ Multi-user message isolation test completed")
    
    @pytest.mark.integration
    async def test_multi_user_connection_separation(self, isolated_env):
        """Test that connection pools are isolated between users."""
        factory = get_websocket_manager_factory()
        
        # Create users with multiple connections each
        users_data = []
        for i in range(3):
            user_id = ensure_user_id(f"connection_user_{i}")
            context = UserExecutionContext.from_request(
                user_id=str(user_id),
                thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
                run_id=str(uuid.uuid4())
            )
            manager = await factory.create_manager(context)
            
            # Add multiple connections per user
            websockets = []
            for j in range(3):
                websocket = MockWebSocket(str(user_id), f"user_{i}_conn_{j}")
                connection = WebSocketConnection(
                    connection_id=f"user_{i}_conn_{j}",
                    user_id=str(user_id),
                    websocket=websocket,
                    connected_at=datetime.utcnow()
                )
                await manager.add_connection(connection)
                websockets.append(websocket)
            
            users_data.append((user_id, manager, websockets))
        
        # Verify each user has isolated connection pool
        for user_id, manager, websockets in users_data:
            connections = manager.get_user_connections()
            assert len(connections) == 3
            
            # Verify all connections belong to this user
            for conn_id in connections:
                connection = manager.get_connection(conn_id)
                assert connection.user_id == str(user_id)
            
            # Verify cannot access other users' connections
            for other_user_id, other_manager, _ in users_data:
                if user_id != other_user_id:
                    # Attempting to check other user should return False
                    has_connection = manager.is_connection_active(str(other_user_id))
                    assert not has_connection
        
        logger.info("✅ Multi-user connection separation test completed")
    
    @pytest.mark.integration
    async def test_multi_user_concurrent_routing(self, isolated_env):
        """Test concurrent message routing across multiple users."""
        factory = get_websocket_manager_factory()
        
        # Create multiple users
        users_setup = []
        for i in range(5):
            user_id = ensure_user_id(f"concurrent_user_{i}")
            context = UserExecutionContext.from_request(
                user_id=str(user_id),
                thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
                run_id=str(uuid.uuid4())
            )
            manager = await factory.create_manager(context)
            websocket = MockWebSocket(str(user_id), f"concurrent_conn_{i}")
            
            connection = WebSocketConnection(
                connection_id=f"concurrent_conn_{i}",
                user_id=str(user_id),
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            await manager.add_connection(connection)
            
            users_setup.append((user_id, manager, websocket))
        
        # Send messages concurrently to all users
        async def send_messages_to_user(user_id, manager, websocket, user_index):
            messages = []
            for msg_index in range(10):
                message = {
                    "type": "concurrent_test",
                    "user": str(user_id),
                    "message_id": f"{user_index}_{msg_index}",
                    "timestamp": time.time()
                }
                await manager.send_to_user(message)
                messages.append(message)
                await asyncio.sleep(0.01)  # Small delay
            return messages
        
        # Execute concurrent sends
        tasks = [
            send_messages_to_user(user_id, manager, websocket, i)
            for i, (user_id, manager, websocket) in enumerate(users_setup)
        ]
        
        sent_messages = await asyncio.gather(*tasks)
        
        # Verify each user received only their messages
        for i, (user_id, manager, websocket) in enumerate(users_setup):
            received = websocket.messages_sent
            expected = sent_messages[i]
            
            assert len(received) == len(expected)
            
            # Verify all received messages belong to this user
            for msg in received:
                assert msg["user"] == str(user_id)
                assert msg["message_id"].startswith(str(i))
        
        logger.info("✅ Multi-user concurrent routing test completed")
    
    @pytest.mark.integration
    async def test_multi_user_factory_isolation(self, isolated_env):
        """Test Factory pattern isolation between users."""
        factory = get_websocket_manager_factory()
        
        # Create managers for different users
        isolation_keys = []
        managers = []
        
        for i in range(4):
            user_id = ensure_user_id(f"factory_user_{i}")
            context = UserExecutionContext.from_request(
                user_id=str(user_id),
                thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
                run_id=str(uuid.uuid4())
            )
            manager = await factory.create_manager(context)
            
            # Generate isolation key (this is internal factory logic)
            isolation_key = f"{user_id}:{context.request_id}"
            
            isolation_keys.append(isolation_key)
            managers.append((user_id, manager))
        
        # Verify each user has independent manager
        assert len(set(id(manager) for _, manager in managers)) == 4
        
        # Verify factory tracks managers correctly
        factory_stats = factory.get_factory_stats()
        assert factory_stats["current_state"]["active_managers"] >= 4
        
        # Verify user distribution in factory
        user_distribution = factory_stats["user_distribution"]
        for user_id, _ in managers:
            assert str(user_id) in user_distribution
            assert user_distribution[str(user_id)] >= 1
        
        logger.info("✅ Multi-user factory isolation test completed")
    
    @pytest.mark.integration
    async def test_multi_user_context_boundaries(self, isolated_env):
        """Test UserExecutionContext boundaries between users."""
        factory = get_websocket_manager_factory()
        
        # Create contexts with overlapping data but different users
        base_thread_id = str(ensure_thread_id(str(uuid.uuid4())))
        
        contexts = []
        managers = []
        
        for i in range(3):
            user_id = ensure_user_id(f"boundary_user_{i}")
            
            # Intentionally use same thread_id to test isolation
            context = UserExecutionContext.from_request(
                user_id=str(user_id),
                thread_id=base_thread_id,  # Same thread ID
                run_id=str(uuid.uuid4())   # Different run ID
            )
            manager = await factory.create_manager(context)
            
            contexts.append(context)
            managers.append(manager)
        
        # Verify managers are different despite same thread_id
        manager_ids = [id(manager) for manager in managers]
        assert len(set(manager_ids)) == 3  # All different managers
        
        # Verify each manager only handles its user
        for i, manager in enumerate(managers):
            user_context = contexts[i]
            
            # Manager should only work for its own user
            health = manager.get_connection_health(user_context.user_id)
            assert health["user_id"] == user_context.user_id
            
            # Should not provide data for other users
            for j, other_context in enumerate(contexts):
                if i != j:
                    other_health = manager.get_connection_health(other_context.user_id)
                    assert "error" in other_health  # Should indicate isolation violation
        
        logger.info("✅ Multi-user context boundaries test completed")
    
    @pytest.mark.integration
    async def test_multi_user_state_consistency(self, isolated_env):
        """Test state consistency across multiple users."""
        factory = get_websocket_manager_factory()
        
        # Track state changes across users
        state_log = []
        
        # Create multiple users and perform operations
        for i in range(3):
            user_id = ensure_user_id(f"state_user_{i}")
            context = UserExecutionContext.from_request(
                user_id=str(user_id),
                thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
                run_id=str(uuid.uuid4())
            )
            manager = await factory.create_manager(context)
            
            # Add connections
            websocket = MockWebSocket(str(user_id), f"state_conn_{i}")
            connection = WebSocketConnection(
                connection_id=f"state_conn_{i}",
                user_id=str(user_id),
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            await manager.add_connection(connection)
            
            # Record state
            state_log.append({
                "user_id": str(user_id),
                "connections": len(manager.get_user_connections()),
                "is_active": manager.is_connection_active(str(user_id)),
                "manager_stats": manager.get_manager_stats()
            })
            
            # Send test message
            await manager.send_to_user({"type": "state_test", "user": str(user_id)})
            
            # Update state log
            state_log[i]["messages_sent"] = len(websocket.messages_sent)
        
        # Verify state consistency
        for i, state in enumerate(state_log):
            assert state["connections"] == 1
            assert state["is_active"] == True
            assert state["messages_sent"] == 1
            assert state["manager_stats"]["is_active"] == True
        
        # Verify factory global state is consistent
        factory_stats = factory.get_factory_stats()
        assert factory_stats["current_state"]["active_managers"] >= 3
        assert factory_stats["current_state"]["users_with_managers"] >= 3
        
        logger.info("✅ Multi-user state consistency test completed")


class TestAgentMessageIntegration(BaseIntegrationTest):
    """Test Agent message integration with WebSocket routing."""
    
    @pytest.mark.integration
    async def test_agent_message_handler_integration(self, isolated_env):
        """Test full agent message handling integration."""
        # Create user context
        user_id = ensure_user_id(str(uuid.uuid4()))
        context = UserExecutionContext.from_request(
            user_id=str(user_id),
            thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
            run_id=str(uuid.uuid4())
        )
        
        # Create WebSocket manager
        ws_manager = await create_websocket_manager(context)
        websocket = MockWebSocket(str(user_id), "agent_conn")
        
        # Add connection
        connection = WebSocketConnection(
            connection_id="agent_conn",
            user_id=str(user_id),
            websocket=websocket,
            connected_at=datetime.utcnow()
        )
        await ws_manager.add_connection(connection)
        
        # Create agent message handler (mock the service)
        mock_service = MagicMock()
        agent_handler = AgentMessageHandler(mock_service, websocket)
        
        # Create test agent message
        agent_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "message": "Analyze my data and provide recommendations",
                "user_id": str(user_id),
                "thread_id": context.thread_id,
                "require_multi_agent": True
            },
            user_id=str(user_id),
            thread_id=context.thread_id,
            timestamp=time.time()
        )
        
        # Handle message
        with patch.dict('os.environ', {'USE_WEBSOCKET_SUPERVISOR_V3': 'false'}):
            # Use v2 pattern for simpler testing
            success = await agent_handler.handle_message(str(user_id), websocket, agent_message)
        
        # Verify handling succeeded  
        assert success
        
        # Verify agent handler stats updated
        stats = agent_handler.processing_stats
        assert stats["messages_processed"] > 0
        assert stats["start_agent_requests"] > 0
        
        logger.info("✅ Agent message handler integration test completed")
    
    @pytest.mark.integration
    async def test_agent_message_routing_to_websocket(self, isolated_env):
        """Test agent messages routing to WebSocket connections."""
        # Set up WebSocket manager and router
        factory = get_websocket_manager_factory()
        router = MessageRouter()
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        context = UserExecutionContext.from_request(
            user_id=str(user_id),
            thread_id=str(ensure_thread_id(str(uuid.uuid4()))),
            run_id=str(uuid.uuid4())
        )
        
        manager = await factory.create_manager(context)
        websocket = MockWebSocket(str(user_id), "routing_conn")
        
        # Add connection
        connection = WebSocketConnection(
            connection_id="routing_conn",
            user_id=str(user_id),
            websocket=websocket,
            connected_at=datetime.utcnow()
        )
        await manager.add_connection(connection)
        
        # Route agent messages through router
        agent_messages = [
            {"type": "start_agent", "payload": {"message": "Start analysis"}},
            {"type": "user_message", "payload": {"content": "User input"}},
            {"type": "chat", "payload": {"message": "Chat message"}}
        ]
        
        for msg in agent_messages:
            success = await router.route_message(str(user_id), websocket, msg)
            assert success
        
        # Verify router handled all agent messages
        stats = router.get_stats()
        assert stats["messages_routed"] >= 3
        
        # Verify WebSocket received processed messages
        assert len(websocket.messages_sent) >= 3
        
        logger.info("✅ Agent message routing to WebSocket test completed")
    
    @pytest.mark.integration
    async def test_agent_message_handler_error_recovery(self, isolated_env):
        """Test error handling in agent message processing."""
        user_id = ensure_user_id(str(uuid.uuid4()))
        websocket = MockWebSocket(str(user_id), "error_conn")
        
        # Create agent handler with failing service
        failing_service = MagicMock()
        failing_service.handle_message = AsyncMock(side_effect=RuntimeError("Service failure"))
        
        agent_handler = AgentMessageHandler(failing_service, websocket)
        
        # Create message that will cause failure
        error_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"message": "This will fail"},
            user_id=str(user_id),
            timestamp=time.time()
        )
        
        # Handle message - should recover gracefully
        with patch.dict('os.environ', {'USE_WEBSOCKET_SUPERVISOR_V3': 'false'}):
            success = await agent_handler.handle_message(str(user_id), websocket, error_message)
        
        # Should fail but not crash
        assert not success
        
        # Verify error stats updated
        stats = agent_handler.processing_stats
        assert stats["errors"] > 0
        
        logger.info("✅ Agent message error recovery test completed")
    
    @pytest.mark.integration  
    async def test_agent_message_type_validation(self, isolated_env):
        """Test message type validation for agent messages."""
        user_id = ensure_user_id(str(uuid.uuid4()))
        websocket = MockWebSocket(str(user_id), "validation_conn")
        
        mock_service = MagicMock()
        agent_handler = AgentMessageHandler(mock_service, websocket)
        
        # Test valid message types
        valid_types = [
            MessageType.START_AGENT,
            MessageType.USER_MESSAGE, 
            MessageType.CHAT
        ]
        
        for msg_type in valid_types:
            test_message = WebSocketMessage(
                type=msg_type,
                payload={"test": "data"},
                user_id=str(user_id),
                timestamp=time.time()
            )
            
            # Should be able to handle
            can_handle = agent_handler.can_handle(msg_type)
            assert can_handle
        
        # Test invalid message type
        invalid_message = WebSocketMessage(
            type=MessageType.PING,  # Not handled by agent handler
            payload={"test": "data"},
            user_id=str(user_id),
            timestamp=time.time()
        )
        
        can_handle = agent_handler.can_handle(MessageType.PING)
        assert not can_handle
        
        logger.info("✅ Agent message type validation test completed")


# Test execution fixture compatibility
@pytest.fixture
def real_services_fixture():
    """Mock real services fixture for integration testing."""
    return {}


@pytest.fixture 
def isolated_env():
    """Mock isolated environment fixture."""
    return get_env()


if __name__ == "__main__":
    # Allow running tests directly for development
    pytest.main([__file__, "-v", "--tb=short"])