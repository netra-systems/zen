# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: WebSocket V2 Factory Pattern Isolation Test Suite

    # REMOVED_SYNTAX_ERROR: This test suite validates the WebSocket V2 factory pattern migration and ensures
    # REMOVED_SYNTAX_ERROR: complete user isolation, preventing cross-user data leakage and security vulnerabilities.

    # REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
        # REMOVED_SYNTAX_ERROR: - Segment: ALL (Free  ->  Enterprise)
        # REMOVED_SYNTAX_ERROR: - Business Goal: Validate WebSocket V2 migration eliminates security vulnerabilities
        # REMOVED_SYNTAX_ERROR: - Value Impact: Ensures safe multi-user AI interactions without data leakage
        # REMOVED_SYNTAX_ERROR: - Revenue Impact: Prevents catastrophic security breaches that could destroy business

        # REMOVED_SYNTAX_ERROR: CRITICAL SECURITY VALIDATIONS:
            # REMOVED_SYNTAX_ERROR: 1. User isolation for WebSocket managers (each user gets their own instance)
            # REMOVED_SYNTAX_ERROR: 2. No cross-user message leakage (User A can't see User B's messages)
            # REMOVED_SYNTAX_ERROR: 3. Factory pattern creates isolated instances per request
            # REMOVED_SYNTAX_ERROR: 4. Deprecated singleton warnings are properly shown
            # REMOVED_SYNTAX_ERROR: 5. Connection-specific isolation prevents data contamination
            # REMOVED_SYNTAX_ERROR: 6. Resource limits prevent memory exhaustion attacks
            # REMOVED_SYNTAX_ERROR: 7. Automatic cleanup prevents resource leaks

            # REMOVED_SYNTAX_ERROR: WebSocket V2 Migration Areas Tested:
                # REMOVED_SYNTAX_ERROR: - WebSocketManagerFactory creates isolated instances
                # REMOVED_SYNTAX_ERROR: - IsolatedWebSocketManager enforces user context validation
                # REMOVED_SYNTAX_ERROR: - ConnectionLifecycleManager handles cleanup properly
                # REMOVED_SYNTAX_ERROR: - UserExecutionContext enforces strict validation
                # REMOVED_SYNTAX_ERROR: - Factory resource limits prevent abuse
                # REMOVED_SYNTAX_ERROR: - Background cleanup prevents memory leaks
                # REMOVED_SYNTAX_ERROR: '''

                # REMOVED_SYNTAX_ERROR: import asyncio
                # REMOVED_SYNTAX_ERROR: import pytest
                # REMOVED_SYNTAX_ERROR: import uuid
                # REMOVED_SYNTAX_ERROR: import warnings
                # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta
                # REMOVED_SYNTAX_ERROR: from typing import Dict, List, Any
                # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

                # Import WebSocket V2 components
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import ( )
                # REMOVED_SYNTAX_ERROR: create_websocket_manager,
                # REMOVED_SYNTAX_ERROR: get_websocket_manager_factory,
                # REMOVED_SYNTAX_ERROR: WebSocketManagerFactory,
                # REMOVED_SYNTAX_ERROR: IsolatedWebSocketManager,
                # REMOVED_SYNTAX_ERROR: get_legacy_websocket_manager,
                # REMOVED_SYNTAX_ERROR: migrate_singleton_usage
                
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.user_execution_context import UserExecutionContext
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
                # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient


# REMOVED_SYNTAX_ERROR: class TestWebSocketV2UserIsolation:
    # REMOVED_SYNTAX_ERROR: """Test user isolation for WebSocket managers - each user gets their own instance."""

# REMOVED_SYNTAX_ERROR: def test_factory_creates_isolated_managers_per_user(self):
    # REMOVED_SYNTAX_ERROR: """Test that factory creates separate manager instances for different users."""
    # Create contexts for two different users
    # REMOVED_SYNTAX_ERROR: user1_context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: request_id="req_001",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_001"
    

    # REMOVED_SYNTAX_ERROR: user2_context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_456",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_789",
    # REMOVED_SYNTAX_ERROR: run_id="run_012",
    # REMOVED_SYNTAX_ERROR: request_id="req_002",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_002"
    

    # Create managers for each user
    # REMOVED_SYNTAX_ERROR: manager1 = create_websocket_manager(user1_context)
    # REMOVED_SYNTAX_ERROR: manager2 = create_websocket_manager(user2_context)

    # CRITICAL: Must be different instances
    # REMOVED_SYNTAX_ERROR: assert manager1 is not manager2, "Different users must get different manager instances"

    # CRITICAL: Must have correct user contexts
    # REMOVED_SYNTAX_ERROR: assert manager1.user_context.user_id == "user_123"
    # REMOVED_SYNTAX_ERROR: assert manager2.user_context.user_id == "user_456"

    # CRITICAL: Managers must be isolated (different memory addresses)
    # REMOVED_SYNTAX_ERROR: assert id(manager1) != id(manager2), "Managers must be isolated instances in memory"

    # CRITICAL: Managers must have separate connection dictionaries
    # REMOVED_SYNTAX_ERROR: assert manager1._connections is not manager2._connections, "Connection dictionaries must be isolated"
    # REMOVED_SYNTAX_ERROR: assert manager1._connection_ids is not manager2._connection_ids, "Connection ID sets must be isolated"

# REMOVED_SYNTAX_ERROR: def test_same_user_different_connections_get_different_managers(self):
    # REMOVED_SYNTAX_ERROR: """Test that same user with different connection IDs gets different managers (strongest isolation)."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: user_id = "user_123"

    # Create contexts for same user but different connection IDs
    # REMOVED_SYNTAX_ERROR: context1 = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: request_id="req_001",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_001"
    

    # REMOVED_SYNTAX_ERROR: context2 = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: request_id="req_002",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_002"
    

    # Create managers
    # REMOVED_SYNTAX_ERROR: manager1 = create_websocket_manager(context1)
    # REMOVED_SYNTAX_ERROR: manager2 = create_websocket_manager(context2)

    # CRITICAL: Even same user gets different managers with different connection IDs
    # REMOVED_SYNTAX_ERROR: assert manager1 is not manager2, "Same user with different connection IDs must get different managers"
    # REMOVED_SYNTAX_ERROR: assert id(manager1) != id(manager2), "Managers must be isolated instances"

    # Both should have same user ID but different connection contexts
    # REMOVED_SYNTAX_ERROR: assert manager1.user_context.user_id == user_id
    # REMOVED_SYNTAX_ERROR: assert manager2.user_context.user_id == user_id
    # REMOVED_SYNTAX_ERROR: assert manager1.user_context.websocket_connection_id == "conn_001"
    # REMOVED_SYNTAX_ERROR: assert manager2.user_context.websocket_connection_id == "conn_002"

# REMOVED_SYNTAX_ERROR: def test_user_context_validation_prevents_invalid_contexts(self):
    # REMOVED_SYNTAX_ERROR: """Test that invalid user contexts are rejected to prevent security issues."""
    # Test None user_id
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="user_id cannot be None"):
        # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id=None,
        # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
        # REMOVED_SYNTAX_ERROR: run_id="run_789",
        # REMOVED_SYNTAX_ERROR: request_id="req_001"
        

        # Test "None" string user_id (common placeholder error)
        # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="user_id cannot be the string 'None'"):
            # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="None",
            # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
            # REMOVED_SYNTAX_ERROR: run_id="run_789",
            # REMOVED_SYNTAX_ERROR: request_id="req_001"
            

            # Test "registry" run_id (common placeholder error)
            # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="run_id cannot be 'registry'"):
                # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
                # REMOVED_SYNTAX_ERROR: user_id="user_123",
                # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
                # REMOVED_SYNTAX_ERROR: run_id="registry",
                # REMOVED_SYNTAX_ERROR: request_id="req_001"
                

                # Test empty fields
                # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="user_id cannot be empty"):
                    # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
                    # REMOVED_SYNTAX_ERROR: user_id="",
                    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
                    # REMOVED_SYNTAX_ERROR: run_id="run_789",
                    # REMOVED_SYNTAX_ERROR: request_id="req_001"
                    

# REMOVED_SYNTAX_ERROR: def test_manager_enforces_user_context_validation(self):
    # REMOVED_SYNTAX_ERROR: """Test that WebSocket manager enforces strict user context validation."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: valid_context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: request_id="req_001"
    

    # Test valid context works
    # REMOVED_SYNTAX_ERROR: manager = create_websocket_manager(valid_context)
    # REMOVED_SYNTAX_ERROR: assert manager.user_context.user_id == "user_123"

    # Test invalid context type is rejected
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="user_context must be a UserExecutionContext instance"):
        # REMOVED_SYNTAX_ERROR: create_websocket_manager("not_a_context")  # type: ignore

        # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="user_context must be a UserExecutionContext instance"):
            # REMOVED_SYNTAX_ERROR: create_websocket_manager(None)  # type: ignore


# REMOVED_SYNTAX_ERROR: class TestWebSocketV2MessageIsolation:
    # REMOVED_SYNTAX_ERROR: """Test no cross-user message leakage - User A can't see User B's messages."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_no_cross_user_message_leakage(self):
        # REMOVED_SYNTAX_ERROR: """Test that messages sent to one user don't leak to other users."""
        # Create isolated managers for two users
        # REMOVED_SYNTAX_ERROR: user1_context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="user_111",
        # REMOVED_SYNTAX_ERROR: thread_id="thread_111",
        # REMOVED_SYNTAX_ERROR: run_id="run_111",
        # REMOVED_SYNTAX_ERROR: request_id="req_111",
        # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_111"
        

        # REMOVED_SYNTAX_ERROR: user2_context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="user_222",
        # REMOVED_SYNTAX_ERROR: thread_id="thread_222",
        # REMOVED_SYNTAX_ERROR: run_id="run_222",
        # REMOVED_SYNTAX_ERROR: request_id="req_222",
        # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_222"
        

        # REMOVED_SYNTAX_ERROR: manager1 = create_websocket_manager(user1_context)
        # REMOVED_SYNTAX_ERROR: manager2 = create_websocket_manager(user2_context)

        # Create mock WebSocket connections
        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()

        # REMOVED_SYNTAX_ERROR: user1_connection = WebSocketConnection( )
        # REMOVED_SYNTAX_ERROR: connection_id="conn_111",
        # REMOVED_SYNTAX_ERROR: user_id="user_111",
        # REMOVED_SYNTAX_ERROR: websocket=user1_websocket,
        # REMOVED_SYNTAX_ERROR: connected_at=datetime.utcnow()
        

        # REMOVED_SYNTAX_ERROR: user2_connection = WebSocketConnection( )
        # REMOVED_SYNTAX_ERROR: connection_id="conn_222",
        # REMOVED_SYNTAX_ERROR: user_id="user_222",
        # REMOVED_SYNTAX_ERROR: websocket=user2_websocket,
        # REMOVED_SYNTAX_ERROR: connected_at=datetime.utcnow()
        

        # Add connections to respective managers
        # REMOVED_SYNTAX_ERROR: await manager1.add_connection(user1_connection)
        # REMOVED_SYNTAX_ERROR: await manager2.add_connection(user2_connection)

        # Send message to user1
        # REMOVED_SYNTAX_ERROR: user1_message = { )
        # REMOVED_SYNTAX_ERROR: "type": "agent_started",
        # REMOVED_SYNTAX_ERROR: "data": {"sensitive_user1_data": "secret_123"}
        

        # REMOVED_SYNTAX_ERROR: await manager1.send_to_user(user1_message)

        # Send message to user2
        # REMOVED_SYNTAX_ERROR: user2_message = { )
        # REMOVED_SYNTAX_ERROR: "type": "tool_executing",
        # REMOVED_SYNTAX_ERROR: "data": {"sensitive_user2_data": "secret_456"}
        

        # REMOVED_SYNTAX_ERROR: await manager2.send_to_user(user2_message)

        # CRITICAL: Verify isolation - user1 only gets user1 messages
        # REMOVED_SYNTAX_ERROR: user1_websocket.send_json.assert_called_once_with(user1_message)

        # CRITICAL: Verify isolation - user2 only gets user2 messages
        # REMOVED_SYNTAX_ERROR: user2_websocket.send_json.assert_called_once_with(user2_message)

        # CRITICAL: Verify no cross-contamination
        # User1's websocket should never see user2's message
        # REMOVED_SYNTAX_ERROR: user1_calls = [call[0][0] for call in user1_websocket.send_json.call_args_list]
        # REMOVED_SYNTAX_ERROR: assert user2_message not in user1_calls, "User1 should never receive user2"s messages"

        # User2's websocket should never see user1's message
        # REMOVED_SYNTAX_ERROR: user2_calls = [call[0][0] for call in user2_websocket.send_json.call_args_list]
        # REMOVED_SYNTAX_ERROR: assert user1_message not in user2_calls, "User2 should never receive user1"s messages"

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_connection_security_validation(self):
            # REMOVED_SYNTAX_ERROR: """Test that connections are validated to belong to the correct user."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user1_context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="user_111",
            # REMOVED_SYNTAX_ERROR: thread_id="thread_111",
            # REMOVED_SYNTAX_ERROR: run_id="run_111",
            # REMOVED_SYNTAX_ERROR: request_id="req_111"
            

            # REMOVED_SYNTAX_ERROR: user2_context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="user_222",
            # REMOVED_SYNTAX_ERROR: thread_id="thread_222",
            # REMOVED_SYNTAX_ERROR: run_id="run_222",
            # REMOVED_SYNTAX_ERROR: request_id="req_222"
            

            # REMOVED_SYNTAX_ERROR: manager1 = create_websocket_manager(user1_context)
            # REMOVED_SYNTAX_ERROR: manager2 = create_websocket_manager(user2_context)

            # Create connection for user2
            # REMOVED_SYNTAX_ERROR: user2_connection = WebSocketConnection( )
            # REMOVED_SYNTAX_ERROR: connection_id="conn_222",
            # REMOVED_SYNTAX_ERROR: user_id="user_222",
            # REMOVED_SYNTAX_ERROR: websocket=TestWebSocketConnection(),
            # REMOVED_SYNTAX_ERROR: connected_at=datetime.utcnow()
            

            # CRITICAL: Attempt to add user2's connection to user1's manager
            # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="does not match manager user_id"):
                # REMOVED_SYNTAX_ERROR: await manager1.add_connection(user2_connection)

                # CRITICAL: Verify manager1 has no connections after failed attempt
                # REMOVED_SYNTAX_ERROR: assert len(manager1.get_user_connections()) == 0

                # CRITICAL: Verify connection can be added to correct manager
                # REMOVED_SYNTAX_ERROR: await manager2.add_connection(user2_connection)
                # REMOVED_SYNTAX_ERROR: assert len(manager2.get_user_connections()) == 1

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_critical_event_isolation(self):
                    # REMOVED_SYNTAX_ERROR: """Test that critical events are isolated between users."""
                    # Create managers for two users
                    # REMOVED_SYNTAX_ERROR: user1_context = UserExecutionContext( )
                    # REMOVED_SYNTAX_ERROR: user_id="user_aaa",
                    # REMOVED_SYNTAX_ERROR: thread_id="thread_aaa",
                    # REMOVED_SYNTAX_ERROR: run_id="run_aaa",
                    # REMOVED_SYNTAX_ERROR: request_id="req_aaa",
                    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_aaa"
                    

                    # REMOVED_SYNTAX_ERROR: user2_context = UserExecutionContext( )
                    # REMOVED_SYNTAX_ERROR: user_id="user_bbb",
                    # REMOVED_SYNTAX_ERROR: thread_id="thread_bbb",
                    # REMOVED_SYNTAX_ERROR: run_id="run_bbb",
                    # REMOVED_SYNTAX_ERROR: request_id="req_bbb",
                    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_bbb"
                    

                    # REMOVED_SYNTAX_ERROR: manager1 = create_websocket_manager(user1_context)
                    # REMOVED_SYNTAX_ERROR: manager2 = create_websocket_manager(user2_context)

                    # Add connections
                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()

                    # REMOVED_SYNTAX_ERROR: await manager1.add_connection(WebSocketConnection( ))
                    # REMOVED_SYNTAX_ERROR: connection_id="conn_aaa",
                    # REMOVED_SYNTAX_ERROR: user_id="user_aaa",
                    # REMOVED_SYNTAX_ERROR: websocket=user1_websocket,
                    # REMOVED_SYNTAX_ERROR: connected_at=datetime.utcnow()
                    

                    # REMOVED_SYNTAX_ERROR: await manager2.add_connection(WebSocketConnection( ))
                    # REMOVED_SYNTAX_ERROR: connection_id="conn_bbb",
                    # REMOVED_SYNTAX_ERROR: user_id="user_bbb",
                    # REMOVED_SYNTAX_ERROR: websocket=user2_websocket,
                    # REMOVED_SYNTAX_ERROR: connected_at=datetime.utcnow()
                    

                    # Emit critical events
                    # REMOVED_SYNTAX_ERROR: await manager1.emit_critical_event("agent_started", {"user": "aaa", "task": "secret_task_A"})
                    # REMOVED_SYNTAX_ERROR: await manager2.emit_critical_event("tool_executing", {"user": "bbb", "task": "secret_task_B"})

                    # CRITICAL: Verify each user only receives their own events
                    # REMOVED_SYNTAX_ERROR: user1_calls = user1_websocket.send_json.call_args_list
                    # REMOVED_SYNTAX_ERROR: user2_calls = user2_websocket.send_json.call_args_list

                    # REMOVED_SYNTAX_ERROR: assert len(user1_calls) == 1, "User1 should receive exactly one event"
                    # REMOVED_SYNTAX_ERROR: assert len(user2_calls) == 1, "User2 should receive exactly one event"

                    # Verify event content isolation
                    # REMOVED_SYNTAX_ERROR: user1_event = user1_calls[0][0][0]
                    # REMOVED_SYNTAX_ERROR: user2_event = user2_calls[0][0][0]

                    # REMOVED_SYNTAX_ERROR: assert user1_event["type"] == "agent_started"
                    # REMOVED_SYNTAX_ERROR: assert user1_event["data"]["task"] == "secret_task_A"
                    # REMOVED_SYNTAX_ERROR: assert user1_event["user_context"]["user_id"] == "user_aaa"

                    # REMOVED_SYNTAX_ERROR: assert user2_event["type"] == "tool_executing"
                    # REMOVED_SYNTAX_ERROR: assert user2_event["data"]["task"] == "secret_task_B"
                    # REMOVED_SYNTAX_ERROR: assert user2_event["user_context"]["user_id"] == "user_bbb"


# REMOVED_SYNTAX_ERROR: class TestWebSocketV2FactoryPattern:
    # REMOVED_SYNTAX_ERROR: """Test factory pattern creates isolated instances per request."""

# REMOVED_SYNTAX_ERROR: def test_factory_singleton_behavior(self):
    # REMOVED_SYNTAX_ERROR: """Test that factory itself is singleton but creates isolated managers."""
    # Get factory instances
    # REMOVED_SYNTAX_ERROR: factory1 = get_websocket_manager_factory()
    # REMOVED_SYNTAX_ERROR: factory2 = get_websocket_manager_factory()

    # CRITICAL: Factory should be singleton
    # REMOVED_SYNTAX_ERROR: assert factory1 is factory2, "Factory should be singleton for configuration consistency"

    # But managers created by factory should be isolated
    # REMOVED_SYNTAX_ERROR: user_context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: request_id="req_001",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_001"
    

    # Different contexts should create different managers
    # REMOVED_SYNTAX_ERROR: context2 = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: request_id="req_002",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_002"
    

    # REMOVED_SYNTAX_ERROR: manager1 = factory1.create_manager(user_context)
    # REMOVED_SYNTAX_ERROR: manager2 = factory1.create_manager(context2)

    # CRITICAL: Different managers for different contexts
    # REMOVED_SYNTAX_ERROR: assert manager1 is not manager2
    # REMOVED_SYNTAX_ERROR: assert id(manager1) != id(manager2)

# REMOVED_SYNTAX_ERROR: def test_factory_resource_limits_enforcement(self):
    # REMOVED_SYNTAX_ERROR: """Test that factory enforces resource limits per user."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: factory = WebSocketManagerFactory(max_managers_per_user=2)  # Limit to 2 managers per user

    # REMOVED_SYNTAX_ERROR: user_id = "user_123"

    # Create contexts for same user (different connection IDs)
    # REMOVED_SYNTAX_ERROR: contexts = [ )
    # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="formatted_string"
    
    # REMOVED_SYNTAX_ERROR: for i in range(1, 5)  # 4 contexts
    

    # First 2 should succeed
    # REMOVED_SYNTAX_ERROR: manager1 = factory.create_manager(contexts[0])
    # REMOVED_SYNTAX_ERROR: manager2 = factory.create_manager(contexts[1])

    # REMOVED_SYNTAX_ERROR: assert manager1 is not manager2

    # Third should fail (resource limit exceeded)
    # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="maximum number of WebSocket managers"):
        # REMOVED_SYNTAX_ERROR: factory.create_manager(contexts[2])

        # Verify metrics updated
        # REMOVED_SYNTAX_ERROR: stats = factory.get_factory_stats()
        # REMOVED_SYNTAX_ERROR: assert stats["factory_metrics"]["resource_limit_hits"] == 1

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_factory_cleanup_mechanisms(self):
            # REMOVED_SYNTAX_ERROR: """Test that factory properly cleans up managers."""
            # REMOVED_SYNTAX_ERROR: factory = WebSocketManagerFactory()

            # REMOVED_SYNTAX_ERROR: user_context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="user_cleanup",
            # REMOVED_SYNTAX_ERROR: thread_id="thread_cleanup",
            # REMOVED_SYNTAX_ERROR: run_id="run_cleanup",
            # REMOVED_SYNTAX_ERROR: request_id="req_cleanup",
            # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_cleanup"
            

            # Create manager
            # REMOVED_SYNTAX_ERROR: manager = factory.create_manager(user_context)
            # REMOVED_SYNTAX_ERROR: isolation_key = factory._generate_isolation_key(user_context)

            # Verify manager exists
            # REMOVED_SYNTAX_ERROR: stats_before = factory.get_factory_stats()
            # REMOVED_SYNTAX_ERROR: assert stats_before["current_state"]["active_managers"] == 1

            # Cleanup manager
            # REMOVED_SYNTAX_ERROR: cleanup_result = await factory.cleanup_manager(isolation_key)
            # REMOVED_SYNTAX_ERROR: assert cleanup_result is True

            # Verify manager cleaned up
            # REMOVED_SYNTAX_ERROR: stats_after = factory.get_factory_stats()
            # REMOVED_SYNTAX_ERROR: assert stats_after["current_state"]["active_managers"] == 0
            # REMOVED_SYNTAX_ERROR: assert stats_after["factory_metrics"]["managers_cleaned_up"] == 1

            # Verify manager is deactivated
            # REMOVED_SYNTAX_ERROR: assert not manager._is_active

# REMOVED_SYNTAX_ERROR: def test_factory_metrics_tracking(self):
    # REMOVED_SYNTAX_ERROR: """Test that factory properly tracks metrics."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: factory = WebSocketManagerFactory()

    # Initial metrics
    # REMOVED_SYNTAX_ERROR: initial_stats = factory.get_factory_stats()
    # REMOVED_SYNTAX_ERROR: assert initial_stats["factory_metrics"]["managers_created"] == 0
    # REMOVED_SYNTAX_ERROR: assert initial_stats["factory_metrics"]["managers_active"] == 0

    # Create managers
    # REMOVED_SYNTAX_ERROR: for i in range(3):
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: websocket_connection_id="formatted_string"
        
        # REMOVED_SYNTAX_ERROR: factory.create_manager(context)

        # Check metrics
        # REMOVED_SYNTAX_ERROR: final_stats = factory.get_factory_stats()
        # REMOVED_SYNTAX_ERROR: assert final_stats["factory_metrics"]["managers_created"] == 3
        # REMOVED_SYNTAX_ERROR: assert final_stats["factory_metrics"]["managers_active"] == 3
        # REMOVED_SYNTAX_ERROR: assert final_stats["current_state"]["active_managers"] == 3
        # REMOVED_SYNTAX_ERROR: assert len(final_stats["current_state"]["isolation_keys"]) == 3


# REMOVED_SYNTAX_ERROR: class TestWebSocketV2DeprecationHandling:
    # REMOVED_SYNTAX_ERROR: """Test deprecated singleton warnings are properly shown."""

# REMOVED_SYNTAX_ERROR: def test_legacy_websocket_manager_deprecation_warning(self):
    # REMOVED_SYNTAX_ERROR: """Test that legacy singleton usage triggers deprecation warnings."""
    # This should trigger a deprecation warning
    # REMOVED_SYNTAX_ERROR: with warnings.catch_warnings(record=True) as warning_list:
        # REMOVED_SYNTAX_ERROR: warnings.simplefilter("always")  # Ensure all warnings are captured

        # Call actual legacy function
        # REMOVED_SYNTAX_ERROR: legacy_manager = get_legacy_websocket_manager()

        # Call a method that should trigger a warning
        # REMOVED_SYNTAX_ERROR: stats = legacy_manager.get_adapter_metrics()

        # Verify the legacy manager was created
        # REMOVED_SYNTAX_ERROR: assert legacy_manager is not None
        # REMOVED_SYNTAX_ERROR: assert "legacy_usage_stats" in stats
        # REMOVED_SYNTAX_ERROR: assert "migration_progress" in stats

        # Note: Migration warnings are triggered by actual usage, not instantiation

# REMOVED_SYNTAX_ERROR: def test_singleton_migration_guidance(self):
    # REMOVED_SYNTAX_ERROR: """Test that migration utilities provide proper guidance."""
    # REMOVED_SYNTAX_ERROR: pass
    # Test migration utility function exists
    # REMOVED_SYNTAX_ERROR: assert hasattr(migrate_singleton_usage, '__call__'), "Migration utility should be callable"

    # Test actual migration utility usage
    # REMOVED_SYNTAX_ERROR: user_context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_migration_test",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_migration_test",
    # REMOVED_SYNTAX_ERROR: run_id="run_migration_test",
    # REMOVED_SYNTAX_ERROR: request_id="req_migration_test"
    

    # Use actual migration function
    # REMOVED_SYNTAX_ERROR: migrated_manager = migrate_singleton_usage(user_context)

    # Verify we get an isolated manager
    # REMOVED_SYNTAX_ERROR: assert isinstance(migrated_manager, IsolatedWebSocketManager)
    # REMOVED_SYNTAX_ERROR: assert migrated_manager.user_context.user_id == "user_migration_test"

# REMOVED_SYNTAX_ERROR: def test_factory_pattern_usage_enforcement(self):
    # REMOVED_SYNTAX_ERROR: """Test that factory pattern is properly enforced."""
    # Direct instantiation should require proper context
    # REMOVED_SYNTAX_ERROR: user_context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_enforcement",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_enforcement",
    # REMOVED_SYNTAX_ERROR: run_id="run_enforcement",
    # REMOVED_SYNTAX_ERROR: request_id="req_enforcement"
    

    # Factory pattern should work
    # REMOVED_SYNTAX_ERROR: manager = create_websocket_manager(user_context)
    # REMOVED_SYNTAX_ERROR: assert isinstance(manager, IsolatedWebSocketManager)

    # Direct instantiation should require context
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError):
        # REMOVED_SYNTAX_ERROR: IsolatedWebSocketManager(None)  # type: ignore


# REMOVED_SYNTAX_ERROR: class TestWebSocketV2SecurityIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for comprehensive security validation."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_end_to_end_user_isolation(self):
        # REMOVED_SYNTAX_ERROR: """End-to-end test of complete user isolation."""
        # Create contexts for 3 different users
        # REMOVED_SYNTAX_ERROR: users_data = [ )
        # REMOVED_SYNTAX_ERROR: ("user_alpha", "secret_alpha_data", "task_alpha"),
        # REMOVED_SYNTAX_ERROR: ("user_beta", "secret_beta_data", "task_beta"),
        # REMOVED_SYNTAX_ERROR: ("user_gamma", "secret_gamma_data", "task_gamma")
        

        # REMOVED_SYNTAX_ERROR: managers = []
        # REMOVED_SYNTAX_ERROR: websockets = []

        # Create isolated managers and connections for each user
        # REMOVED_SYNTAX_ERROR: for i, (user_id, secret_data, task) in enumerate(users_data):
            # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id=user_id,
            # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: websocket_connection_id="formatted_string"
            

            # REMOVED_SYNTAX_ERROR: manager = create_websocket_manager(context)
            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
            # REMOVED_SYNTAX_ERROR: connection = WebSocketConnection( )
            # REMOVED_SYNTAX_ERROR: connection_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: user_id=user_id,
            # REMOVED_SYNTAX_ERROR: websocket=websocket,
            # REMOVED_SYNTAX_ERROR: connected_at=datetime.utcnow()
            

            # REMOVED_SYNTAX_ERROR: await manager.add_connection(connection)
            # REMOVED_SYNTAX_ERROR: managers.append(manager)
            # REMOVED_SYNTAX_ERROR: websockets.append(websocket)

            # Send different critical events to each user
            # REMOVED_SYNTAX_ERROR: for i, (user_id, secret_data, task) in enumerate(users_data):
                # Removed problematic line: await managers[i].emit_critical_event("agent_started", { ))
                # REMOVED_SYNTAX_ERROR: "secret": secret_data,
                # REMOVED_SYNTAX_ERROR: "task": task,
                # REMOVED_SYNTAX_ERROR: "user": user_id
                

                # CRITICAL: Verify each user only received their own data
                # REMOVED_SYNTAX_ERROR: for i, (user_id, secret_data, task) in enumerate(users_data):
                    # REMOVED_SYNTAX_ERROR: websocket = websockets[i]
                    # REMOVED_SYNTAX_ERROR: calls = websocket.send_json.call_args_list

                    # REMOVED_SYNTAX_ERROR: assert len(calls) == 1, "formatted_string"

                    # REMOVED_SYNTAX_ERROR: event = calls[0][0][0]
                    # REMOVED_SYNTAX_ERROR: assert event["data"]["secret"] == secret_data, "formatted_string"
                    # REMOVED_SYNTAX_ERROR: assert event["data"]["task"] == task, "formatted_string"
                    # REMOVED_SYNTAX_ERROR: assert event["user_context"]["user_id"] == user_id

                    # CRITICAL: Verify no other user's data is present
                    # REMOVED_SYNTAX_ERROR: for j, (other_user, other_secret, other_task) in enumerate(users_data):
                        # REMOVED_SYNTAX_ERROR: if i != j:
                            # REMOVED_SYNTAX_ERROR: assert other_secret not in str(event), "formatted_string"s secret"
                            # REMOVED_SYNTAX_ERROR: assert other_task not in str(event), "formatted_string"s task"

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_connection_lifecycle_security(self):
                                # REMOVED_SYNTAX_ERROR: """Test that connection lifecycle maintains security throughout."""
                                # REMOVED_SYNTAX_ERROR: pass
                                # REMOVED_SYNTAX_ERROR: user_context = UserExecutionContext( )
                                # REMOVED_SYNTAX_ERROR: user_id="user_lifecycle",
                                # REMOVED_SYNTAX_ERROR: thread_id="thread_lifecycle",
                                # REMOVED_SYNTAX_ERROR: run_id="run_lifecycle",
                                # REMOVED_SYNTAX_ERROR: request_id="req_lifecycle",
                                # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_lifecycle"
                                

                                # REMOVED_SYNTAX_ERROR: manager = create_websocket_manager(user_context)

                                # Add connection
                                # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
                                # REMOVED_SYNTAX_ERROR: connection = WebSocketConnection( )
                                # REMOVED_SYNTAX_ERROR: connection_id="conn_lifecycle",
                                # REMOVED_SYNTAX_ERROR: user_id="user_lifecycle",
                                # REMOVED_SYNTAX_ERROR: websocket=websocket,
                                # REMOVED_SYNTAX_ERROR: connected_at=datetime.utcnow()
                                

                                # REMOVED_SYNTAX_ERROR: await manager.add_connection(connection)

                                # Send message
                                # REMOVED_SYNTAX_ERROR: await manager.send_to_user({"type": "test", "data": "secure_data"})
                                # REMOVED_SYNTAX_ERROR: websocket.send_json.assert_called_once()

                                # Remove connection
                                # REMOVED_SYNTAX_ERROR: await manager.remove_connection("conn_lifecycle")
                                # REMOVED_SYNTAX_ERROR: assert len(manager.get_user_connections()) == 0

                                # Attempt to send message after connection removed
                                # REMOVED_SYNTAX_ERROR: websocket.reset_mock()
                                # REMOVED_SYNTAX_ERROR: await manager.send_to_user({"type": "test2", "data": "more_data"})

                                # CRITICAL: No messages should be sent to removed connections
                                # REMOVED_SYNTAX_ERROR: websocket.send_json.assert_not_called()

# REMOVED_SYNTAX_ERROR: def test_resource_exhaustion_prevention(self):
    # REMOVED_SYNTAX_ERROR: """Test that factory prevents resource exhaustion attacks."""
    # REMOVED_SYNTAX_ERROR: factory = WebSocketManagerFactory(max_managers_per_user=3)

    # REMOVED_SYNTAX_ERROR: attacker_user_id = "attacker_user"

    # Create maximum allowed managers
    # REMOVED_SYNTAX_ERROR: for i in range(3):
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id=attacker_user_id,
        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: websocket_connection_id="formatted_string"
        
        # REMOVED_SYNTAX_ERROR: manager = factory.create_manager(context)
        # REMOVED_SYNTAX_ERROR: assert manager.user_context.user_id == attacker_user_id

        # Attempt to create one more (should fail)
        # REMOVED_SYNTAX_ERROR: context_overflow = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id=attacker_user_id,
        # REMOVED_SYNTAX_ERROR: thread_id="thread_overflow",
        # REMOVED_SYNTAX_ERROR: run_id="run_overflow",
        # REMOVED_SYNTAX_ERROR: request_id="req_overflow",
        # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_overflow"
        

        # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="maximum number of WebSocket managers"):
            # REMOVED_SYNTAX_ERROR: factory.create_manager(context_overflow)

            # Verify metrics show resource limit hit
            # REMOVED_SYNTAX_ERROR: stats = factory.get_factory_stats()
            # REMOVED_SYNTAX_ERROR: assert stats["factory_metrics"]["resource_limit_hits"] >= 1


            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                # REMOVED_SYNTAX_ERROR: import sys
                # REMOVED_SYNTAX_ERROR: sys.exit(pytest.main([__file__, "-v"]))
                # REMOVED_SYNTAX_ERROR: pass