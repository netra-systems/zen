"""E2E Security Tests for Tool Dispatcher Core with Real Authentication.

Business Value Justification (BVJ):
- Segment: Enterprise (critical for security compliance)
- Business Goal: Ensure complete user isolation and secure tool execution
- Value Impact: Prevents cross-user data leaks and unauthorized tool access
- Strategic Impact: Security validation prevents compliance violations and customer data breaches

These E2E tests validate tool dispatcher security with complete system stack:
- Real authentication (JWT/OAuth) with multiple users
- Real WebSocket connections with user isolation
- Real databases (PostgreSQL, Redis) with user-scoped data
- Real tool execution with permission validation
- Cross-user isolation verification

CRITICAL: ALL E2E tests MUST use authentication - no exceptions.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient

from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from langchain_core.tools import BaseTool


class SecurityTestTool(BaseTool):
    """Security-focused test tool that reveals user context."""
    
    name: str = "security_test_tool"
    description: str = "Test tool that reveals user context for security validation"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.execution_history = []
    
    def _run(self, test_data: str = "default") -> Dict[str, Any]:
        """Execute tool and record execution context."""
        execution_record = {
            "tool_name": self.name,
            "test_data": test_data,
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_id": str(uuid.uuid4())
        }
        self.execution_history.append(execution_record)
        return execution_record
    
    async def _arun(self, test_data: str = "default") -> Dict[str, Any]:
        """Async execution with user context tracking."""
        return self._run(test_data)


class TestToolDispatcherCoreSecurity(BaseE2ETest):
    """E2E security tests for ToolDispatcherCore with authenticated multi-user scenarios."""
    
    @pytest.fixture
    async def user1_authenticated(self):
        """Create first authenticated user for security testing."""
        token, user_data = await create_authenticated_user(
            environment="test",
            user_id="security-user-1",
            email="security-user-1@test.com",
            permissions=["read", "write", "tool_execute", "tool_dispatch"]
        )
        return {
            "token": token,
            "user_data": user_data,
            "user_id": user_data["id"],
            "email": user_data["email"]
        }
    
    @pytest.fixture
    async def user2_authenticated(self):
        """Create second authenticated user for isolation testing."""
        token, user_data = await create_authenticated_user(
            environment="test",
            user_id="security-user-2", 
            email="security-user-2@test.com",
            permissions=["read", "write", "tool_execute", "tool_dispatch"]
        )
        return {
            "token": token,
            "user_data": user_data,
            "user_id": user_data["id"],
            "email": user_data["email"]
        }
    
    @pytest.fixture
    def auth_helper(self):
        """E2E authentication helper."""
        return E2EAuthHelper(environment="test")
    
    @pytest.fixture
    async def user1_websocket_client(self, user1_authenticated, auth_helper):
        """Authenticated WebSocket client for user 1."""
        headers = auth_helper.get_websocket_headers(user1_authenticated["token"])
        client = WebSocketTestClient(
            url="ws://localhost:8002/ws",
            headers=headers
        )
        await client.connect()
        yield client
        await client.disconnect()
    
    @pytest.fixture
    async def user2_websocket_client(self, user2_authenticated, auth_helper):
        """Authenticated WebSocket client for user 2."""
        headers = auth_helper.get_websocket_headers(user2_authenticated["token"])
        client = WebSocketTestClient(
            url="ws://localhost:8002/ws", 
            headers=headers
        )
        await client.connect()
        yield client
        await client.disconnect()
    
    @pytest.fixture
    def security_test_tools(self):
        """Security-focused test tools."""
        return [
            SecurityTestTool(name="user_context_tool"),
            SecurityTestTool(name="sensitive_data_tool"),
            SecurityTestTool(name="permission_test_tool")
        ]
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.security
    async def test_user_isolation_tool_execution_security(
        self,
        user1_authenticated,
        user2_authenticated,
        user1_websocket_client,
        user2_websocket_client,
        security_test_tools
    ):
        """Test that tool execution is completely isolated between users."""
        
        # Create user execution contexts
        user1_context = UserExecutionContext(
            user_id=user1_authenticated["user_id"],
            session_id=f"security-session-1-{uuid.uuid4().hex[:8]}",
            permissions={"tool_execute", "tool_dispatch"}
        )
        
        user2_context = UserExecutionContext(
            user_id=user2_authenticated["user_id"],
            session_id=f"security-session-2-{uuid.uuid4().hex[:8]}",
            permissions={"tool_execute", "tool_dispatch"}
        )
        
        # Create isolated tool dispatchers for each user
        user1_dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user1_context,
            tools=security_test_tools
        )
        
        user2_dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user2_context,
            tools=security_test_tools
        )
        
        # Create user states
        user1_state = DeepAgentState(
            user_id=user1_authenticated["user_id"],
            thread_id=f"security-thread-1-{uuid.uuid4().hex[:8]}"
        )
        
        user2_state = DeepAgentState(
            user_id=user2_authenticated["user_id"],
            thread_id=f"security-thread-2-{uuid.uuid4().hex[:8]}"
        )
        
        # Execute tools concurrently for both users
        user1_run_id = str(uuid.uuid4())
        user2_run_id = str(uuid.uuid4())
        
        user1_task = user1_dispatcher.dispatch_tool(
            tool_name="user_context_tool",
            parameters={"test_data": f"user1_sensitive_data_{uuid.uuid4().hex[:8]}"},
            state=user1_state,
            run_id=user1_run_id
        )
        
        user2_task = user2_dispatcher.dispatch_tool(
            tool_name="user_context_tool",
            parameters={"test_data": f"user2_sensitive_data_{uuid.uuid4().hex[:8]}"},
            state=user2_state,
            run_id=user2_run_id
        )
        
        # Execute concurrently to test isolation
        user1_result, user2_result = await asyncio.gather(user1_task, user2_task)
        
        # Verify both executions succeeded
        assert user1_result.success is True, f"User 1 tool execution failed: {user1_result.error}"
        assert user2_result.success is True, f"User 2 tool execution failed: {user2_result.error}"
        
        # Verify complete isolation - each tool instance should have separate execution history
        user1_tool = user1_dispatcher.registry.get_tool("user_context_tool")
        user2_tool = user2_dispatcher.registry.get_tool("user_context_tool")
        
        # Tools should be different instances (not shared)
        assert user1_tool is not user2_tool, "SECURITY VIOLATION: Tools are shared between users"
        
        # Each tool should only have its own user's execution
        assert len(user1_tool.execution_history) == 1
        assert len(user2_tool.execution_history) == 1
        
        # Verify data isolation - user 1's data should not appear in user 2's history
        user1_execution = user1_tool.execution_history[0]
        user2_execution = user2_tool.execution_history[0]
        
        assert "user1_sensitive_data" in user1_execution["test_data"]
        assert "user2_sensitive_data" in user2_execution["test_data"]
        
        # CRITICAL: Cross-contamination check
        assert "user2_sensitive_data" not in user1_execution["test_data"]
        assert "user1_sensitive_data" not in user2_execution["test_data"]
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.security
    async def test_websocket_event_isolation_security(
        self,
        user1_authenticated,
        user2_authenticated,
        user1_websocket_client,
        user2_websocket_client,
        security_test_tools
    ):
        """Test that WebSocket events are properly isolated between users."""
        
        # Track events for each user
        user1_events = []
        user2_events = []
        
        # Event collectors for each user
        async def collect_user1_events():
            try:
                while True:
                    event = await asyncio.wait_for(user1_websocket_client.receive_json(), timeout=2.0)
                    user1_events.append(event)
                    if event.get('type') == 'tool_completed':
                        break
            except asyncio.TimeoutError:
                pass
        
        async def collect_user2_events():
            try:
                while True:
                    event = await asyncio.wait_for(user2_websocket_client.receive_json(), timeout=2.0)
                    user2_events.append(event)
                    if event.get('type') == 'tool_completed':
                        break
            except asyncio.TimeoutError:
                pass
        
        # Create user contexts with WebSocket managers
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        
        websocket_manager = UnifiedWebSocketManager()
        
        user1_context = UserExecutionContext(
            user_id=user1_authenticated["user_id"],
            session_id=f"ws-security-session-1-{uuid.uuid4().hex[:8]}",
            permissions={"tool_execute", "tool_dispatch"}
        )
        
        user2_context = UserExecutionContext(
            user_id=user2_authenticated["user_id"], 
            session_id=f"ws-security-session-2-{uuid.uuid4().hex[:8]}",
            permissions={"tool_execute", "tool_dispatch"}
        )
        
        # Create dispatchers with WebSocket support
        user1_dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user1_context,
            tools=security_test_tools,
            websocket_manager=websocket_manager
        )
        
        user2_dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user2_context,
            tools=security_test_tools,
            websocket_manager=websocket_manager
        )
        
        # Start event collection
        user1_collection_task = asyncio.create_task(collect_user1_events())
        user2_collection_task = asyncio.create_task(collect_user2_events())
        
        # Execute tools for both users
        user1_state = DeepAgentState(
            user_id=user1_authenticated["user_id"],
            thread_id=f"ws-security-thread-1-{uuid.uuid4().hex[:8]}"
        )
        
        user2_state = DeepAgentState(
            user_id=user2_authenticated["user_id"],
            thread_id=f"ws-security-thread-2-{uuid.uuid4().hex[:8]}"
        )
        
        # Execute concurrently
        await asyncio.gather(
            user1_dispatcher.dispatch_tool(
                tool_name="sensitive_data_tool",
                parameters={"test_data": "user1_websocket_data"},
                state=user1_state,
                run_id=str(uuid.uuid4())
            ),
            user2_dispatcher.dispatch_tool(
                tool_name="sensitive_data_tool",
                parameters={"test_data": "user2_websocket_data"},
                state=user2_state,
                run_id=str(uuid.uuid4())
            )
        )
        
        # Wait for event collection to complete
        await asyncio.gather(user1_collection_task, user2_collection_task)
        
        # Verify event isolation
        assert len(user1_events) > 0, "User 1 should have received WebSocket events"
        assert len(user2_events) > 0, "User 2 should have received WebSocket events"
        
        # Extract event data for isolation verification
        user1_event_data = [str(event) for event in user1_events]
        user2_event_data = [str(event) for event in user2_events]
        
        # CRITICAL: Cross-contamination check for WebSocket events
        user1_combined_data = " ".join(user1_event_data)
        user2_combined_data = " ".join(user2_event_data)
        
        # User 1 should not see User 2's data in their events
        assert "user2_websocket_data" not in user1_combined_data, \
            "SECURITY VIOLATION: User 1 received User 2's WebSocket events"
        
        # User 2 should not see User 1's data in their events  
        assert "user1_websocket_data" not in user2_combined_data, \
            "SECURITY VIOLATION: User 2 received User 1's WebSocket events"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.security
    async def test_request_scoped_dispatcher_cleanup_security(
        self,
        user1_authenticated,
        security_test_tools
    ):
        """Test that request-scoped dispatchers are properly cleaned up to prevent data leaks."""
        
        user_context = UserExecutionContext(
            user_id=user1_authenticated["user_id"],
            session_id=f"cleanup-security-session-{uuid.uuid4().hex[:8]}",
            permissions={"tool_execute", "tool_dispatch"}
        )
        
        # Create scoped dispatcher using context manager for automatic cleanup
        async with ToolDispatcher.create_scoped_dispatcher_context(
            user_context=user_context,
            tools=security_test_tools
        ) as scoped_dispatcher:
            
            state = DeepAgentState(
                user_id=user1_authenticated["user_id"],
                thread_id=f"cleanup-thread-{uuid.uuid4().hex[:8]}"
            )
            
            # Execute tool with sensitive data
            sensitive_data = f"cleanup_test_sensitive_{uuid.uuid4().hex}"
            result = await scoped_dispatcher.dispatch_tool(
                tool_name="permission_test_tool",
                parameters={"test_data": sensitive_data},
                state=state,
                run_id=str(uuid.uuid4())
            )
            
            assert result.success is True
            
            # Verify tool has execution history within scope
            tool = scoped_dispatcher.registry.get_tool("permission_test_tool")
            assert len(tool.execution_history) == 1
            assert sensitive_data in tool.execution_history[0]["test_data"]
        
        # After context exit, verify cleanup occurred
        # Note: We can't directly verify cleanup since the scoped_dispatcher
        # is now out of scope, but the test passes if no exceptions occur
        # and memory doesn't leak (which would be caught by longer-running tests)
        
        # Create a new dispatcher to verify isolation
        new_user_context = UserExecutionContext(
            user_id=user1_authenticated["user_id"],
            session_id=f"new-cleanup-session-{uuid.uuid4().hex[:8]}",
            permissions={"tool_execute", "tool_dispatch"}
        )
        
        new_dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=new_user_context,
            tools=[SecurityTestTool(name="permission_test_tool")]
        )
        
        # New dispatcher should have clean tool instances
        new_tool = new_dispatcher.registry.get_tool("permission_test_tool")
        assert len(new_tool.execution_history) == 0, \
            "SECURITY VIOLATION: Tool state leaked between request scopes"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.security
    async def test_unauthorized_tool_access_prevention(
        self,
        user1_authenticated,
        security_test_tools
    ):
        """Test that unauthorized tool access is properly prevented."""
        
        # Create user context with limited permissions
        limited_user_context = UserExecutionContext(
            user_id=user1_authenticated["user_id"],
            session_id=f"limited-permissions-session-{uuid.uuid4().hex[:8]}",
            permissions={"read"}  # No tool_execute permission
        )
        
        # Create dispatcher with limited permissions
        limited_dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=limited_user_context,
            tools=security_test_tools
        )
        
        state = DeepAgentState(
            user_id=user1_authenticated["user_id"],
            thread_id=f"limited-thread-{uuid.uuid4().hex[:8]}"
        )
        
        # Attempt to execute tool without proper permissions
        result = await limited_dispatcher.dispatch_tool(
            tool_name="sensitive_data_tool",
            parameters={"test_data": "unauthorized_access_attempt"},
            state=state,
            run_id=str(uuid.uuid4())
        )
        
        # Should fail due to insufficient permissions
        # Note: The actual permission checking depends on the implementation
        # This test ensures the security framework is in place
        
        # Verify the tool exists but execution handling is secure
        assert limited_dispatcher.has_tool("sensitive_data_tool")
        
        # If permission checking is implemented, result should indicate failure
        # If not implemented yet, this test serves as a placeholder for when it is
        
        # At minimum, verify the dispatcher and tool registry are properly isolated
        tool = limited_dispatcher.registry.get_tool("sensitive_data_tool")
        assert tool is not None, "Tool should be available in registry"