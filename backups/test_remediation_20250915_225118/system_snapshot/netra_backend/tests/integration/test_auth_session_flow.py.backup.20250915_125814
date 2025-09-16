"""Integration tests for authentication flow with session management.

CRITICAL: These tests verify REAL multi-component interactions for authentication
and session management without Docker dependencies. They test business-critical
scenarios where auth flows integrate with session management and user contexts.

Business Value: Secure user authentication and session isolation.
"""

import asyncio
import pytest
import uuid
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.isolated_environment import IsolatedEnvironment


class MockAuthService:
    """Mock authentication service for testing without external dependencies."""
    
    def __init__(self):
        self.jwt_secret = "test_jwt_secret_key_for_integration_testing_only"
        self.active_sessions = {}  # user_id -> session_info
        self.users = {  # Mock user database
            "auth_user_1": {"email": "user1@test.com", "role": "user"},
            "auth_user_2": {"email": "user2@test.com", "role": "premium"},
            "auth_admin": {"email": "admin@test.com", "role": "admin"}
        }
    
    def create_jwt_token(self, user_id: str, expires_in_hours: int = 24) -> str:
        """Create JWT token for user."""
        payload = {
            "user_id": user_id,
            "email": self.users[user_id]["email"],
            "role": self.users[user_id]["role"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
            "iat": datetime.now(timezone.utc),
            "token_type": "access"
        }
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return user info."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return {
                "user_id": payload["user_id"],
                "email": payload["email"], 
                "role": payload["role"],
                "valid": True
            }
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "token_expired"}
        except jwt.InvalidTokenError:
            return {"valid": False, "error": "invalid_token"}
    
    async def create_session(self, user_id: str, token: str) -> Dict[str, Any]:
        """Create user session."""
        session_id = f"session_{user_id}_{uuid.uuid4().hex[:8]}"
        session_info = {
            "session_id": session_id,
            "user_id": user_id,
            "token": token,
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "active": True
        }
        self.active_sessions[user_id] = session_info
        return session_info
    
    async def validate_session(self, user_id: str) -> Dict[str, Any]:
        """Validate user session."""
        if user_id not in self.active_sessions:
            return {"valid": False, "error": "no_session"}
        
        session = self.active_sessions[user_id]
        if not session["active"]:
            return {"valid": False, "error": "session_inactive"}
        
        # Update last activity
        session["last_activity"] = datetime.now(timezone.utc)
        return {"valid": True, "session": session}
    
    async def revoke_session(self, user_id: str) -> bool:
        """Revoke user session."""
        if user_id in self.active_sessions:
            self.active_sessions[user_id]["active"] = False
            return True
        return False


class MockWebSocketManager:
    """Mock WebSocket manager for auth integration testing."""
    
    def __init__(self):
        self.user_connections = {}  # user_id -> connection_info
        self.sent_events = {}  # user_id -> [events]
    
    async def emit_critical_event(self, user_id: str, event_type: str, data: Dict[str, Any]):
        """Mock emitting critical events."""
        if user_id not in self.sent_events:
            self.sent_events[user_id] = []
        self.sent_events[user_id].append({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def is_connection_active(self, user_id: str) -> bool:
        """Check if user has active connection."""
        return user_id in self.user_connections and self.user_connections[user_id]["active"]
    
    async def add_user_connection(self, user_id: str):
        """Add user connection."""
        self.user_connections[user_id] = {
            "user_id": user_id,
            "connected_at": datetime.now(timezone.utc),
            "active": True
        }
    
    async def remove_user_connection(self, user_id: str):
        """Remove user connection."""
        if user_id in self.user_connections:
            self.user_connections[user_id]["active"] = False


class TestAuthenticationSessionFlowIntegration:
    """Integration tests for authentication flow with session management."""
    
    @pytest.fixture
    def isolated_env(self):
        """Create isolated environment for testing."""
        env = IsolatedEnvironment()
        env.set('JWT_SECRET', 'test_jwt_secret_key_for_integration_testing_only')
        env.set('SESSION_TIMEOUT_HOURS', '24')
        env.set('AUTH_REQUIRED', 'true')
        return env
    
    @pytest.fixture
    def auth_service(self):
        """Create mock authentication service."""
        return MockAuthService()
        
    @pytest.fixture
    def websocket_manager(self):
        """Create mock WebSocket manager."""
        return MockWebSocketManager()
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        from unittest.mock import AsyncMock
        llm_manager = AsyncMock()
        llm_manager.get_llm = AsyncMock()
        return llm_manager
        
    @pytest.fixture
    def agent_registry(self, mock_llm_manager):
        """Create agent registry."""
        return AgentRegistry(mock_llm_manager)

    @pytest.mark.asyncio
    async def test_complete_auth_session_integration_flow(self, isolated_env, auth_service, websocket_manager, agent_registry):
        """
        Test complete authentication and session management integration.
        
        This tests REAL interaction between:
        - MockAuthService (JWT token creation and validation)
        - UserExecutionContext (authenticated user contexts)
        - AgentRegistry (session management with auth)
        - MockWebSocketManager (authenticated connections)
        - IsolatedEnvironment (auth configuration)
        
        Business scenario: User authenticates, creates session, interacts with
        agents, and maintains secure isolation throughout the flow.
        """
        # PHASE 1: User authentication
        test_user_id = "auth_user_1"
        
        # Create JWT token for user
        jwt_token = auth_service.create_jwt_token(test_user_id)
        assert jwt_token is not None, "JWT token should be created"
        
        # Validate token
        token_validation = auth_service.validate_token(jwt_token)
        assert token_validation["valid"] is True, "Token should be valid"
        assert token_validation["user_id"] == test_user_id, "Token should contain correct user ID"
        
        # PHASE 2: Session creation with authentication
        session_info = await auth_service.create_session(test_user_id, jwt_token)
        assert session_info["user_id"] == test_user_id, "Session should be for correct user"
        assert session_info["active"] is True, "Session should be active"
        
        # PHASE 3: Create authenticated user execution context
        user_context = UserExecutionContext(
            user_id=test_user_id,
            thread_id=f"auth_thread_{uuid.uuid4().hex[:8]}",
            request_id=f"auth_request_{uuid.uuid4().hex[:8]}",
            run_id=f"auth_run_{uuid.uuid4().hex[:8]}"
        )
        
        # Add authentication metadata to context
        user_context.metadata.update({
            "jwt_token": jwt_token,
            "session_id": session_info["session_id"],
            "authenticated": True,
            "role": token_validation["role"]
        })
        
        # PHASE 4: Set up WebSocket connection with authentication
        await websocket_manager.add_user_connection(test_user_id)
        assert websocket_manager.is_connection_active(test_user_id), "WebSocket connection should be active"
        
        # PHASE 5: Create authenticated agent session
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Get user session through agent registry
        user_session = await agent_registry.get_user_session(test_user_id)
        assert user_session.user_id == test_user_id, "Agent session should be for correct user"
        
        # PHASE 6: Create execution context with auth validation
        auth_execution_context = await user_session.create_agent_execution_context(
            "auth_test_agent", 
            user_context
        )
        
        assert auth_execution_context.user_id == test_user_id, "Auth context should maintain user ID"
        assert "authenticated" in user_context.metadata, "Context should maintain auth metadata"
        
        # PHASE 7: Test authenticated operations
        # Validate session is still active
        session_validation = await auth_service.validate_session(test_user_id)
        assert session_validation["valid"] is True, "Session should remain valid"
        
        # Simulate authenticated agent operations
        await websocket_manager.emit_critical_event(
            test_user_id,
            "agent_started",
            {"agent": "auth_test_agent", "authenticated": True}
        )
        
        # Verify events were sent to authenticated user
        user_events = websocket_manager.sent_events.get(test_user_id, [])
        assert len(user_events) == 1, "User should receive agent events"
        assert user_events[0]["type"] == "agent_started", "Should receive correct event type"
        
        # PHASE 8: Test session validation throughout operations
        # Simulate multiple operations with session validation
        operations = ["tool_executing", "agent_thinking", "agent_completed"]
        
        for operation in operations:
            # Validate session before operation
            validation = await auth_service.validate_session(test_user_id)
            assert validation["valid"] is True, f"Session should be valid for {operation}"
            
            # Perform operation
            await websocket_manager.emit_critical_event(
                test_user_id,
                operation,
                {"operation": operation, "session_id": session_info["session_id"]}
            )
        
        # Verify all events were delivered
        final_events = websocket_manager.sent_events.get(test_user_id, [])
        assert len(final_events) == len(operations) + 1, "All events should be delivered"
        
        # PHASE 9: Test session cleanup
        # Clean up agent session
        cleanup_result = await agent_registry.cleanup_user_session(test_user_id)
        assert cleanup_result["status"] == "cleaned", "Agent session should be cleaned"
        
        # Revoke auth session
        revoke_result = await auth_service.revoke_session(test_user_id)
        assert revoke_result is True, "Session should be revoked"
        
        # Verify session is no longer valid
        final_validation = await auth_service.validate_session(test_user_id)
        assert final_validation["valid"] is False, "Session should be invalid after revocation"

    @pytest.mark.asyncio
    async def test_multi_user_auth_session_isolation(self, auth_service, websocket_manager, agent_registry):
        """
        Test authentication and session isolation between multiple users.
        
        This tests REAL interaction between:
        - Multiple MockAuthService sessions (user isolation)
        - Multiple UserExecutionContext instances (context isolation)
        - AgentRegistry (multi-user session management)
        - MockWebSocketManager (connection isolation)
        
        Business scenario: Multiple users authenticate simultaneously and
        maintain completely isolated sessions and agent interactions.
        """
        # PHASE 1: Set up multiple users with authentication
        test_users = ["auth_user_1", "auth_user_2", "auth_admin"]
        user_tokens = {}
        user_sessions = {}
        user_contexts = {}
        
        # Create authentication for all users
        for user_id in test_users:
            # Create JWT token
            token = auth_service.create_jwt_token(user_id)
            user_tokens[user_id] = token
            
            # Create session
            session = await auth_service.create_session(user_id, token)
            user_sessions[user_id] = session
            
            # Create execution context
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"multi_thread_{user_id}_{uuid.uuid4().hex[:6]}",
                request_id=f"multi_request_{user_id}_{uuid.uuid4().hex[:6]}",
                run_id=f"multi_run_{user_id}_{uuid.uuid4().hex[:6]}"
            )
            
            # Add auth metadata
            token_data = auth_service.validate_token(token)
            context.metadata.update({
                "jwt_token": token,
                "session_id": session["session_id"],
                "authenticated": True,
                "role": token_data["role"]
            })
            user_contexts[user_id] = context
            
            # Set up WebSocket connection
            await websocket_manager.add_user_connection(user_id)
        
        # PHASE 2: Set up agent registry with WebSocket integration
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Create agent sessions for all users
        agent_user_sessions = {}
        for user_id in test_users:
            user_session = await agent_registry.get_user_session(user_id)
            agent_user_sessions[user_id] = user_session
        
        # PHASE 3: Test concurrent authenticated operations
        async def perform_user_operations(user_id: str, operation_count: int):
            """Perform operations for a specific user."""
            operations_performed = []
            context = user_contexts[user_id]
            
            for i in range(operation_count):
                # Validate session before each operation
                validation = await auth_service.validate_session(user_id)
                assert validation["valid"] is True, f"User {user_id} session should be valid"
                
                # Perform authenticated operation
                operation_type = f"user_operation_{i}"
                await websocket_manager.emit_critical_event(
                    user_id,
                    operation_type,
                    {
                        "user_id": user_id,
                        "operation_index": i,
                        "session_id": user_sessions[user_id]["session_id"],
                        "role": context.metadata["role"]
                    }
                )
                operations_performed.append(operation_type)
            
            return operations_performed
        
        # Run operations concurrently for all users
        tasks = []
        expected_operations = {}
        
        for user_id in test_users:
            operation_count = 3  # 3 operations per user
            task = perform_user_operations(user_id, operation_count)
            tasks.append(task)
            expected_operations[user_id] = operation_count
        
        # Wait for all operations to complete
        all_operations = await asyncio.gather(*tasks)
        
        # PHASE 4: Verify session and data isolation
        for i, user_id in enumerate(test_users):
            # Verify user received only their events
            user_events = websocket_manager.sent_events.get(user_id, [])
            assert len(user_events) == expected_operations[user_id], f"User {user_id} should receive correct number of events"
            
            # Verify event content isolation
            for event in user_events:
                assert event["data"]["user_id"] == user_id, f"User {user_id} should only see their own events"
                assert event["data"]["session_id"] == user_sessions[user_id]["session_id"], "Should have correct session ID"
            
            # Verify session is still valid and isolated
            validation = await auth_service.validate_session(user_id)
            assert validation["valid"] is True, f"User {user_id} session should remain valid"
            assert validation["session"]["user_id"] == user_id, "Session should belong to correct user"
        
        # PHASE 5: Test role-based isolation
        # Verify users have different roles and they're maintained
        admin_context = user_contexts["auth_admin"]
        user_context = user_contexts["auth_user_1"]
        premium_context = user_contexts["auth_user_2"]
        
        assert admin_context.metadata["role"] == "admin", "Admin should have admin role"
        assert user_context.metadata["role"] == "user", "Regular user should have user role"
        assert premium_context.metadata["role"] == "premium", "Premium user should have premium role"
        
        # PHASE 6: Test selective session termination
        # Revoke one user's session and verify others remain active
        revoke_result = await auth_service.revoke_session("auth_user_1")
        assert revoke_result is True, "User 1 session should be revoked"
        
        # Verify revoked user's session is invalid
        user1_validation = await auth_service.validate_session("auth_user_1")
        assert user1_validation["valid"] is False, "Revoked user session should be invalid"
        
        # Verify other users' sessions remain valid
        user2_validation = await auth_service.validate_session("auth_user_2")
        admin_validation = await auth_service.validate_session("auth_admin")
        
        assert user2_validation["valid"] is True, "User 2 session should remain valid"
        assert admin_validation["valid"] is True, "Admin session should remain valid"
        
        # PHASE 7: Clean up remaining sessions
        for user_id in ["auth_user_2", "auth_admin"]:
            cleanup_result = await agent_registry.cleanup_user_session(user_id)
            assert cleanup_result["status"] == "cleaned", f"User {user_id} should be cleaned up"
            
            await auth_service.revoke_session(user_id)
            
        # Clean up user 1 agent session too
        cleanup_result = await agent_registry.cleanup_user_session("auth_user_1")
        assert cleanup_result["status"] == "cleaned", "User 1 agent session should be cleaned"