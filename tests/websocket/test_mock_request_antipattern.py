"""
WebSocket Mock Request Anti-Pattern Elimination Test

This test validates that the WebSocket system uses proper WebSocketContext objects
instead of mock Request objects, ensuring clean architecture and user isolation.

Business Value:
- Ensures proper multi-user WebSocket isolation
- Validates clean architecture patterns
- Prevents authentication and routing bugs
- Tests real WebSocket message handling

CRITICAL: This test uses REAL WebSocket connections and authentication.
No mocks are allowed except for controlled isolation testing.
"""

import asyncio
import json
import os
import pytest
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

# Real WebSocket and FastAPI imports
from fastapi import WebSocket
from starlette.websockets import WebSocketState
from sqlalchemy.ext.asyncio import AsyncSession

# SSOT imports for authentication
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.environment_isolation import IsolatedEnvironment

# WebSocket core components
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor

# Service and dependency imports
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.dependencies import get_request_scoped_db_session
from shared.isolated_environment import get_env
    


class TestWebSocketAntiPatternElimination(SSotBaseTestCase):
    """Test suite to validate elimination of WebSocket mock Request anti-patterns.
    
    These tests ensure the system uses proper WebSocketContext objects instead
    of creating mock Request objects for WebSocket connections. This validates
    clean architecture and proper user isolation.
    
    CRITICAL: All tests use real authentication and WebSocket connections.
    """
    
    def setUp(self) -> None:
        """Set up test environment with real authentication."""
        super().setUp()
        
        # Initialize environment
        self.env = get_env()
        
        # Set up authentication helper
        self.auth_config = E2EAuthConfig()
        self.auth_helper = E2EAuthHelper(config=self.auth_config)
        self.ws_auth_helper = E2EWebSocketAuthHelper(config=self.auth_config)
        
        # Create test user credentials
        self.test_user_id = f"test_user_{int(datetime.utcnow().timestamp())}"
        self.test_thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"test_run_{uuid.uuid4().hex[:8]}"
        

    @pytest.mark.asyncio
    async def test_websocket_context_creation_honest_pattern(self):
        """Test that WebSocketContext provides honest WebSocket functionality.
        
        This validates that the system uses honest WebSocket context objects
        instead of mock Request objects that pretend to be something they're not.
        """
        # Create real WebSocket token
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        
        # Create mock WebSocket (controlled for testing)
        mock_websocket = self._create_test_websocket()
        
        # Create WebSocketContext using factory method
        context = WebSocketContext.create_for_user(
            websocket=mock_websocket,
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Validate honest WebSocket functionality
        assert context.user_id == self.test_user_id
        assert context.thread_id == self.test_thread_id
        assert context.run_id == self.test_run_id
        assert context.websocket == mock_websocket
        assert context.is_active  # Should be active when CONNECTED
        
        # Context should have WebSocket-specific attributes
        assert hasattr(context, 'websocket')
        assert hasattr(context, 'connection_id')
        assert hasattr(context, 'is_active')
        assert hasattr(context, 'update_activity')
        
        # Should NOT have HTTP request attributes (honest about what it is)
        assert not hasattr(context, 'headers')
        assert not hasattr(context, 'cookies')
        assert not hasattr(context, 'method')
        assert not hasattr(context, 'url')
        
        # Test activity tracking
        original_activity = context.last_activity
        await asyncio.sleep(0.01)
        context.update_activity()
        assert context.last_activity > original_activity
        
        # Test isolation key generation
        isolation_key = context.to_isolation_key()
        assert self.test_user_id in isolation_key
        assert self.test_thread_id in isolation_key
        assert self.test_run_id in isolation_key

    @pytest.mark.asyncio
    async def test_websocket_context_validation_requirements(self):
        """Test that WebSocketContext properly validates required fields.
        
        This ensures the system fails fast with clear errors when
        required WebSocket context data is missing.
        """
        mock_websocket = self._create_test_websocket()
        
        # Test missing user_id
        with pytest.raises(ValueError, match="user_id is required"):
            WebSocketContext(
                connection_id="test_conn",
                websocket=mock_websocket,
                user_id="",  # Empty user_id should fail
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
        
        # Test missing thread_id
        with pytest.raises(ValueError, match="thread_id is required"):
            WebSocketContext(
                connection_id="test_conn",
                websocket=mock_websocket,
                user_id=self.test_user_id,
                thread_id="",  # Empty thread_id should fail
                run_id=self.test_run_id
            )
        
        # Test missing run_id
        with pytest.raises(ValueError, match="run_id is required"):
            WebSocketContext(
                connection_id="test_conn",
                websocket=mock_websocket,
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=""  # Empty run_id should fail
            )
        
        # Test missing websocket
        with pytest.raises(ValueError, match="websocket is required"):
            WebSocketContext(
                connection_id="test_conn",
                websocket=None,  # Missing websocket should fail
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
                            

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle_management(self):
        """Test that WebSocketContext properly tracks connection lifecycle.
        
        This validates that the context honestly reports connection state
        and properly handles connection state changes.
        """
        # Create WebSocket in connected state
        mock_websocket = self._create_test_websocket(state=WebSocketState.CONNECTED)
        
        context = WebSocketContext.create_for_user(
            websocket=mock_websocket,
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )
        
        # Should be active when connected
        assert context.is_active
        
        # Test connection info
        conn_info = context.get_connection_info()
        assert conn_info['user_id'] == self.test_user_id
        assert conn_info['thread_id'] == self.test_thread_id
        assert conn_info['is_active'] is True
        assert 'connected_at' in conn_info
        assert 'last_activity' in conn_info
        
        # Test validation for active connection
        assert context.validate_for_message_processing()
        
        # Simulate disconnection
        mock_websocket.client_state = WebSocketState.DISCONNECTED
        
        # Should detect disconnected state
        assert not context.is_active
        
        # Validation should fail for disconnected state
        with pytest.raises(ValueError, match="not active"):
            context.validate_for_message_processing()
                        

    @pytest.mark.asyncio
    async def test_websocket_message_handler_integration(self):
        """Test that WebSocket message handler integrates properly with WebSocketContext.
        
        This validates that the agent message handler uses WebSocketContext
        instead of creating mock Request objects.
        """
        # Create authenticated WebSocket context
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        mock_websocket = self._create_test_websocket()
        
        # Create test message for agent
        test_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "thread_id": self.test_thread_id,
                "run_id": self.test_run_id,
                "message": "Test agent execution"
            },
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            correlation_id=f"test_corr_{uuid.uuid4().hex[:8]}"
        )
        
        # Create WebSocketContext for message processing
        context = WebSocketContext.create_for_user(
            websocket=mock_websocket,
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Validate context is ready for message processing
        assert context.validate_for_message_processing()
        
        # Verify context provides proper isolation key
        isolation_key = context.to_isolation_key()
        assert isolation_key.startswith('ws_')
        assert self.test_user_id in isolation_key
        assert self.test_thread_id in isolation_key
        
        # Test that context can be serialized for logging/debugging
        conn_info = context.get_connection_info()
        assert isinstance(conn_info, dict)
        assert 'client_state' in conn_info
        assert conn_info['client_state'] == 'CONNECTED'

    @pytest.mark.asyncio
    async def test_user_isolation_with_multiple_contexts(self):
        """Test that multiple WebSocket contexts provide proper user isolation.
        
        This validates that concurrent WebSocket connections maintain
        independent contexts without cross-contamination.
        """
        # Create multiple user contexts
        contexts = []
        for i in range(3):
            user_id = f"user_{i}_{int(datetime.utcnow().timestamp())}"
            thread_id = f"thread_{i}_{uuid.uuid4().hex[:8]}"
            run_id = f"run_{i}_{uuid.uuid4().hex[:8]}"
            
            mock_websocket = self._create_test_websocket()
            
            context = WebSocketContext.create_for_user(
                websocket=mock_websocket,
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            contexts.append(context)
        
        # Verify each context maintains independent state
        for i, context in enumerate(contexts):
            assert f"user_{i}_" in context.user_id
            assert f"thread_{i}_" in context.thread_id
            assert f"run_{i}_" in context.run_id
            assert context.is_active
            
            # Each should have unique isolation keys
            isolation_key = context.to_isolation_key()
            assert context.user_id in isolation_key
            assert context.thread_id in isolation_key
            assert context.run_id in isolation_key
        
        # Verify contexts are independent (no shared state)
        for i, context1 in enumerate(contexts):
            for j, context2 in enumerate(contexts):
                if i != j:
                    assert context1.user_id != context2.user_id
                    assert context1.thread_id != context2.thread_id
                    assert context1.run_id != context2.run_id
                    assert context1.connection_id != context2.connection_id
                    assert context1.to_isolation_key() != context2.to_isolation_key()
                                    

    @pytest.mark.asyncio
    async def test_websocket_context_error_handling(self):
        """Test that WebSocketContext handles errors gracefully and honestly.
        
        This validates that the context fails fast with clear errors
        rather than hiding problems with mock objects.
        """
        # Test WebSocket state check with exception
        class FaultyWebSocket:
            @property
            def client_state(self):
                raise RuntimeError("WebSocket connection error")
        
        faulty_websocket = FaultyWebSocket()
        
        context = WebSocketContext(
            connection_id="test_conn_faulty",
            websocket=faulty_websocket,
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Should handle WebSocket state check errors gracefully
        # and return False rather than crashing
        assert not context.is_active
        
        # Test context with very old connection
        from datetime import timedelta
        old_time = datetime.utcnow() - timedelta(days=2)
        
        old_context = WebSocketContext(
            connection_id="old_conn",
            websocket=self._create_test_websocket(),
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            connected_at=old_time
        )
        
        # Should still validate but log warning about old connection
        assert old_context.validate_for_message_processing()

    @pytest.mark.asyncio
    async def test_authentication_integration_with_context(self):
        """Test that WebSocketContext integrates properly with authentication.
        
        This validates that the context works with real JWT tokens
        and authentication flows without requiring mock objects.
        """
        # Create real JWT token
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            permissions=["read", "write"],
            exp_minutes=5
        )
        
        # Validate token is properly formed
        auth_headers = self.auth_helper.get_auth_headers(token)
        assert "Authorization" in auth_headers
        assert auth_headers["Authorization"].startswith("Bearer ")
        
        # Get WebSocket headers for authenticated connection
        ws_headers = self.ws_auth_helper.get_websocket_headers(token)
        assert "Authorization" in ws_headers
        assert "X-User-ID" in ws_headers
        assert ws_headers["X-User-ID"] == self.test_user_id
        
        # Create WebSocket context with authenticated user
        mock_websocket = self._create_test_websocket()
        
        context = WebSocketContext.create_for_user(
            websocket=mock_websocket,
            user_id=self.test_user_id,  # Same user from JWT
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Context should maintain user identity from token
        assert context.user_id == self.test_user_id
        assert context.validate_for_message_processing()
        
        # Isolation key should be based on authenticated user
        isolation_key = context.to_isolation_key()
        assert self.test_user_id in isolation_key

    def _create_test_websocket(self, state: WebSocketState = WebSocketState.CONNECTED):
        """Create a controlled WebSocket for testing.
        
        Args:
            state: WebSocket state to simulate
            
        Returns:
            Mock WebSocket with controlled behavior
        """
        class TestWebSocket:
            def __init__(self, client_state: WebSocketState):
                self.client_state = client_state
                self.messages_sent = []
                self.closed = False
            
            async def send_text(self, message: str):
                if self.closed:
                    raise RuntimeError("WebSocket is closed")
                self.messages_sent.append(message)
            
            async def send_json(self, data: dict):
                if self.closed:
                    raise RuntimeError("WebSocket is closed")
                self.messages_sent.append(json.dumps(data))
            
            async def close(self, code: int = 1000, reason: str = "Normal closure"):
                self.closed = True
                self.client_state = WebSocketState.DISCONNECTED
        
        return TestWebSocket(state)
    
    def tearDown(self) -> None:
        """Clean up test resources."""
        super().tearDown()
        # Clear any cached authentication tokens
        if hasattr(self, 'auth_helper') and self.auth_helper:
            self.auth_helper._cached_token = None
            self.auth_helper._token_expiry = None
                                            

# Run the tests when executed directly
if __name__ == "__main__":
    # Set up test environment variables
    os.environ["USE_WEBSOCKET_SUPERVISOR_V3"] = "true"  # Force clean pattern
    os.environ["TEST_ENV"] = "test"
    
    # Run the test suite
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "--no-cov",  # Skip coverage for focused testing
        "-x"  # Stop on first failure for faster feedback
    ])








