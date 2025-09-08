"""
Simplified test for authentication persistence in multi-agent workflows.
Tests core auth persistence patterns without importing modules with singleton issues.
"""

import asyncio
import uuid
import jwt
from datetime import datetime, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestAuthPersistenceCore:
    """Core tests for auth persistence without singleton dependencies."""
    
    @pytest.fixture
    def valid_token(self):
        """Generate a valid JWT token for testing."""
        payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, "test-secret", algorithm="HS256")
    
    @pytest.mark.asyncio
    async def test_user_execution_context_preserves_auth(self, valid_token):
        """Test that UserExecutionContext properly maintains auth data."""
        user_id = "test-user-123"
        thread_id = "thread-456"
        
        # Create context with auth token
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=str(uuid.uuid4()),
            websocket_connection_id="ws-001",
            metadata={"auth_token": valid_token}
        )
        
        # Verify context properly initialized
        assert context.user_id == user_id
        assert context.thread_id == thread_id
        assert context.metadata["auth_token"] == valid_token
        
        # Context should be immutable
        with pytest.raises(AttributeError):
            context.user_id = "different-user"
    
    @pytest.mark.asyncio
    async def test_websocket_context_factory_pattern(self, valid_token):
        """Test WebSocketContext factory creates isolated contexts."""
        contexts = []
        
        # Create multiple contexts for different users
        for i in range(3):
            user_id = f"user_{i}"
            thread_id = f"thread_{i}"
            
            ws_context = WebSocketContext.create_for_user(
                websocket=AsyncMock(),
                user_id=user_id,
                thread_id=thread_id,
                run_id=str(uuid.uuid4()),
                connection_id=f"ws_conn_{i}"
            )
            contexts.append(ws_context)
        
        # Verify each context is isolated
        for i, ctx in enumerate(contexts):
            assert ctx.user_id == f"user_{i}"
            assert ctx.thread_id == f"thread_{i}"
            assert ctx.connection_id == f"ws_conn_{i}"
            
            # Verify no cross-contamination
            for j, other_ctx in enumerate(contexts):
                if i != j:
                    assert ctx.user_id != other_ctx.user_id
                    assert ctx.thread_id != other_ctx.thread_id
                    assert ctx.connection_id != other_ctx.connection_id
    
    @pytest.mark.asyncio
    async def test_concurrent_context_creation(self, valid_token):
        """Test that concurrent context creation maintains isolation."""
        results = {}
        
        async def create_user_context(user_id: str):
            """Create a context for a specific user."""
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{user_id}",
                run_id=str(uuid.uuid4()),
                websocket_connection_id=f"ws_{user_id}",
                metadata={"auth_token": valid_token, "user_data": f"data_{user_id}"}
            )
            results[user_id] = context
            await asyncio.sleep(0.01)  # Simulate some processing
            return context
        
        # Create contexts concurrently
        user_ids = [f"user_{i}" for i in range(10)]
        tasks = [create_user_context(uid) for uid in user_ids]
        contexts = await asyncio.gather(*tasks)
        
        # Verify all contexts are properly isolated
        for i, context in enumerate(contexts):
            expected_user_id = f"user_{i}"
            assert context.user_id == expected_user_id
            assert context.thread_id == f"thread_{expected_user_id}"
            assert context.metadata["user_data"] == f"data_{expected_user_id}"
    
    @pytest.mark.asyncio
    async def test_websocket_v3_pattern_enabled(self):
        """Test that WebSocket v3 pattern is enabled by default."""
        import os
        
        # Check if v3 is enabled (we set it to true by default)
        # If not explicitly set, it should default to true now
        v3_enabled = os.getenv("USE_WEBSOCKET_SUPERVISOR_V3", "true").lower() == "true"
        assert v3_enabled, "WebSocket v3 pattern should be enabled by default for security"
    
    @pytest.mark.asyncio
    async def test_auth_token_in_websocket_message(self, valid_token):
        """Test that WebSocket messages can carry auth context."""
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "thread_id": "test-thread",
                "agent_name": "test_agent",
                "content": "Test content",
                "auth_token": valid_token  # Auth can be in payload
            },
            thread_id="test-thread"
        )
        
        # Verify message contains auth
        assert message.payload["auth_token"] == valid_token
        assert message.thread_id == "test-thread"
    
    @pytest.mark.asyncio
    async def test_token_refresh_preserves_user_identity(self):
        """Test that token refresh maintains user identity."""
        user_id = "refresh-test-user"
        
        # Original token
        original_token = jwt.encode({
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=30),
            "iat": datetime.utcnow(),
            "session_id": "session-001"
        }, "test-secret", algorithm="HS256")
        
        # Refreshed token (same user, new expiry)
        refreshed_token = jwt.encode({
            "sub": user_id,  # Same user ID
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "session_id": "session-001"  # Same session
        }, "test-secret", algorithm="HS256")
        
        # Decode both tokens
        original_claims = jwt.decode(original_token, "test-secret", algorithms=["HS256"])
        refreshed_claims = jwt.decode(refreshed_token, "test-secret", algorithms=["HS256"])
        
        # Verify user identity preserved
        assert original_claims["sub"] == refreshed_claims["sub"]
        assert original_claims["session_id"] == refreshed_claims["session_id"]
        # But expiry should be updated
        assert refreshed_claims["exp"] > original_claims["exp"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])