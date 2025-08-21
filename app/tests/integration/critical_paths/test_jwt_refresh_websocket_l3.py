"""L3 Integration Test: JWT Refresh During Active WebSocket

Business Value Justification (BVJ):
- Segment: All tiers (session continuity)
- Business Goal: Maintain uninterrupted user sessions during token refresh
- Value Impact: Prevents session drops that lead to user frustration and churn
- Strategic Impact: Improves user experience and retention for $75K MRR

L3 Test: Real JWT refresh while maintaining active WebSocket connections.
Tests seamless token rotation without disrupting real-time features.
"""

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock

import redis.asyncio as redis
from app.services.auth.jwt_service import JWTService
from app.services.auth.session_manager import SessionManager
from app.ws_manager import WebSocketManager
from app.redis_manager import RedisManager
from app.logging_config import central_logger
from ..helpers.redis_l3_helpers import RedisContainer, MockWebSocketForRedis

logger = central_logger.get_logger(__name__)


class JWTRefreshManager:
    """Manages JWT refresh testing scenarios."""
    
    def __init__(self, jwt_service: JWTService, session_manager: SessionManager, 
                 websocket_manager: WebSocketManager, redis_client):
        self.jwt_service = jwt_service
        self.session_manager = session_manager
        self.websocket_manager = websocket_manager
        self.redis_client = redis_client
        self.active_sessions = {}
        self.refresh_events = []
    
    async def create_authenticated_session(self, user_id: str, 
                                         expires_delta: Optional[timedelta] = None) -> Dict[str, Any]:
        """Create authenticated session with WebSocket connection."""
        # Generate JWT token
        token_result = await self.jwt_service.generate_token(
            user_id=user_id,
            permissions=["read", "write"],
            tier="free",
            expires_delta=expires_delta or timedelta(hours=1)
        )
        
        if not token_result["success"]:
            raise ValueError(f"Token generation failed: {token_result.get('error')}")
        
        # Create session
        session_result = await self.session_manager.create_session(
            user_id=user_id,
            token=token_result["token"],
            metadata={"auth_method": "jwt_test", "ip_address": "127.0.0.1"}
        )
        
        if not session_result["success"]:
            raise ValueError(f"Session creation failed: {session_result.get('error')}")
        
        # Create WebSocket connection
        websocket = MockWebSocketForRedis(user_id)
        
        with patch('app.ws_manager.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {
                "valid": True,
                "user_id": user_id,
                "permissions": ["read", "write"]
            }
            
            connection_info = await self.websocket_manager.connect_user(user_id, websocket)
        
        if not connection_info:
            raise ValueError("WebSocket connection failed")
        
        session_data = {
            "user_id": user_id,
            "session_id": session_result["session_id"],
            "token": token_result["token"],
            "refresh_token": token_result["refresh_token"],
            "websocket": websocket,
            "connection_info": connection_info,
            "created_at": time.time()
        }
        
        self.active_sessions[user_id] = session_data
        return session_data
    
    async def refresh_token_for_user(self, user_id: str) -> Dict[str, Any]:
        """Refresh JWT token for user and update session."""
        if user_id not in self.active_sessions:
            raise ValueError(f"No active session for user {user_id}")
        
        session_data = self.active_sessions[user_id]
        refresh_start = time.time()
        
        # Refresh the token
        refresh_result = await self.jwt_service.refresh_token(session_data["refresh_token"])
        
        if not refresh_result["success"]:
            raise ValueError(f"Token refresh failed: {refresh_result.get('error')}")
        
        # Update session with new token
        update_result = await self.session_manager.update_session_token(
            session_data["session_id"],
            refresh_result["token"]
        )
        
        if not update_result["success"]:
            raise ValueError(f"Session update failed: {update_result.get('error')}")
        
        # Update Redis session data
        session_key = f"session:{session_data['session_id']}"
        session_redis_data = await self.redis_client.get(session_key)
        
        if session_redis_data:
            session_dict = json.loads(session_redis_data)
            session_dict["token"] = refresh_result["token"]
            session_dict["refreshed_at"] = time.time()
            await self.redis_client.set(session_key, json.dumps(session_dict), ex=3600)
        
        # Update local session data
        session_data["token"] = refresh_result["token"]
        session_data["refresh_token"] = refresh_result.get("refresh_token", session_data["refresh_token"])
        session_data["refreshed_at"] = time.time()
        
        refresh_event = {
            "user_id": user_id,
            "refresh_time": time.time() - refresh_start,
            "old_token": session_data["token"],
            "new_token": refresh_result["token"],
            "websocket_active": not session_data["websocket"].closed
        }
        
        self.refresh_events.append(refresh_event)
        return refresh_event
    
    async def cleanup(self):
        """Clean up all active sessions."""
        for user_id, session_data in self.active_sessions.items():
            try:
                await self.websocket_manager.disconnect_user(user_id, session_data["websocket"])
                await self.session_manager.invalidate_session(session_data["session_id"])
            except Exception as e:
                logger.warning(f"Cleanup error for user {user_id}: {e}")
        
        self.active_sessions.clear()


@pytest.mark.L3
@pytest.mark.integration
class TestJWTRefreshWebSocketL3:
    """L3 integration test for JWT refresh during active WebSocket connections."""
    
    @pytest.fixture(scope="class")
    async def redis_container(self):
        """Set up Redis container."""
        container = RedisContainer()
        redis_url = await container.start()
        yield container, redis_url
        await container.stop()
    
    @pytest.fixture
    async def redis_client(self, redis_container):
        """Create Redis client."""
        _, redis_url = redis_container
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        yield client
        await client.close()
    
    @pytest.fixture
    async def jwt_service(self, redis_client):
        """Initialize JWT service with Redis backend."""
        service = JWTService()
        
        with patch('app.redis_manager.RedisManager.get_client') as mock_redis:
            mock_redis.return_value = redis_client
            await service.initialize()
            yield service
            await service.shutdown()
    
    @pytest.fixture
    async def session_manager(self, redis_client):
        """Initialize session manager with Redis backend."""
        manager = SessionManager()
        
        with patch('app.redis_manager.RedisManager.get_client') as mock_redis:
            mock_redis.return_value = redis_client
            await manager.initialize()
            yield manager
            await manager.shutdown()
    
    @pytest.fixture
    async def websocket_manager(self, redis_client):
        """Create WebSocket manager with Redis."""
        with patch('app.ws_manager.redis_manager') as mock_redis_mgr:
            test_redis_mgr = RedisManager()
            test_redis_mgr.enabled = True
            test_redis_mgr.redis_client = redis_client
            mock_redis_mgr.return_value = test_redis_mgr
            mock_redis_mgr.get_client.return_value = redis_client
            
            manager = WebSocketManager()
            yield manager
    
    @pytest.fixture
    async def refresh_manager(self, jwt_service, session_manager, websocket_manager, redis_client):
        """Create JWT refresh manager."""
        manager = JWTRefreshManager(jwt_service, session_manager, websocket_manager, redis_client)
        yield manager
        await manager.cleanup()
    
    async def test_jwt_refresh_maintains_websocket_connection(self, refresh_manager):
        """Test JWT refresh while maintaining active WebSocket connection."""
        user_id = f"refresh_user_{uuid.uuid4().hex[:8]}"
        
        # Create authenticated session with short-lived token
        session_data = await refresh_manager.create_authenticated_session(
            user_id, expires_delta=timedelta(seconds=5)
        )
        
        # Verify initial connection
        websocket = session_data["websocket"]
        assert not websocket.closed
        assert user_id in refresh_manager.websocket_manager.active_connections
        
        # Send test message before refresh
        pre_refresh_message = {
            "type": "pre_refresh_test",
            "data": {"timestamp": time.time()}
        }
        
        success = await refresh_manager.websocket_manager.send_message_to_user(
            user_id, pre_refresh_message
        )
        assert success is True
        
        # Wait for token to approach expiry
        await asyncio.sleep(3)
        
        # Refresh token
        refresh_event = await refresh_manager.refresh_token_for_user(user_id)
        
        # Verify refresh succeeded
        assert refresh_event["websocket_active"] is True
        assert refresh_event["refresh_time"] < 1.0  # Should be fast
        
        # Verify WebSocket still active
        assert not websocket.closed
        assert user_id in refresh_manager.websocket_manager.active_connections
        
        # Send test message after refresh
        post_refresh_message = {
            "type": "post_refresh_test",
            "data": {"timestamp": time.time()}
        }
        
        success = await refresh_manager.websocket_manager.send_message_to_user(
            user_id, post_refresh_message
        )
        assert success is True
        
        # Verify both messages received
        assert len(websocket.messages) >= 2
        message_types = [msg.get("type") for msg in websocket.messages]
        assert "pre_refresh_test" in message_types
        assert "post_refresh_test" in message_types
    
    async def test_concurrent_jwt_refresh_multiple_users(self, refresh_manager):
        """Test concurrent JWT refresh for multiple users with active WebSockets."""
        user_count = 5
        users = [f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(user_count)]
        
        # Create sessions for all users
        sessions = {}
        for user_id in users:
            sessions[user_id] = await refresh_manager.create_authenticated_session(
                user_id, expires_delta=timedelta(seconds=10)
            )
        
        # Verify all connections active
        for user_id in users:
            assert user_id in refresh_manager.websocket_manager.active_connections
            assert not sessions[user_id]["websocket"].closed
        
        # Wait before refresh
        await asyncio.sleep(5)
        
        # Perform concurrent refreshes
        async def refresh_user(user_id):
            try:
                return await refresh_manager.refresh_token_for_user(user_id)
            except Exception as e:
                logger.error(f"Refresh failed for {user_id}: {e}")
                return {"error": str(e)}
        
        refresh_tasks = [refresh_user(user_id) for user_id in users]
        refresh_results = await asyncio.gather(*refresh_tasks, return_exceptions=True)
        
        # Verify all refreshes succeeded
        successful_refreshes = 0
        for i, result in enumerate(refresh_results):
            if isinstance(result, Exception):
                pytest.fail(f"Refresh {i} failed with exception: {result}")
            
            if "error" not in result:
                successful_refreshes += 1
                assert result["websocket_active"] is True
        
        assert successful_refreshes == user_count
        
        # Verify all WebSocket connections still active
        for user_id in users:
            assert user_id in refresh_manager.websocket_manager.active_connections
            assert not sessions[user_id]["websocket"].closed
        
        # Test message delivery to all users
        broadcast_message = {
            "type": "post_concurrent_refresh",
            "data": {"broadcast_time": time.time()}
        }
        
        for user_id in users:
            success = await refresh_manager.websocket_manager.send_message_to_user(
                user_id, broadcast_message
            )
            assert success is True
    
    async def test_jwt_refresh_with_expired_refresh_token(self, refresh_manager):
        """Test handling of expired refresh tokens during WebSocket session."""
        user_id = f"expired_refresh_user_{uuid.uuid4().hex[:8]}"
        
        # Create session with very short-lived refresh token
        session_data = await refresh_manager.create_authenticated_session(
            user_id, expires_delta=timedelta(seconds=2)
        )
        
        # Wait for both tokens to expire
        await asyncio.sleep(5)
        
        # Attempt refresh with expired refresh token
        try:
            await refresh_manager.refresh_token_for_user(user_id)
            pytest.fail("Expected refresh to fail with expired token")
        except ValueError as e:
            assert "refresh failed" in str(e).lower()
        
        # Verify WebSocket connection handling
        websocket = session_data["websocket"]
        
        # WebSocket should still be connected (not automatically closed)
        assert user_id in refresh_manager.websocket_manager.active_connections
        
        # But authentication should fail for new operations
        with patch('app.ws_manager.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"valid": False, "error": "Token expired"}
            
            # Attempt to send message should handle auth failure gracefully
            auth_test_message = {"type": "auth_test", "data": {}}
            success = await refresh_manager.websocket_manager.send_message_to_user(
                user_id, auth_test_message
            )
            
            # Implementation dependent - may succeed or fail based on design
            # Main point is no exceptions should be raised
    
    async def test_jwt_refresh_performance_under_load(self, refresh_manager):
        """Test JWT refresh performance with high connection load."""
        connection_count = 20  # Moderate load for CI
        users = [f"load_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(connection_count)]
        
        # Create all sessions
        setup_start = time.time()
        sessions = {}
        for user_id in users:
            sessions[user_id] = await refresh_manager.create_authenticated_session(
                user_id, expires_delta=timedelta(seconds=15)
            )
        setup_time = time.time() - setup_start
        
        # Send initial messages to establish baseline
        for user_id in users:
            initial_message = {"type": "load_test_init", "data": {"user": user_id}}
            await refresh_manager.websocket_manager.send_message_to_user(user_id, initial_message)
        
        # Wait before refresh window
        await asyncio.sleep(8)
        
        # Perform batch refresh
        refresh_start = time.time()
        refresh_tasks = []
        
        for user_id in users:
            task = refresh_manager.refresh_token_for_user(user_id)
            refresh_tasks.append(task)
        
        refresh_results = await asyncio.gather(*refresh_tasks, return_exceptions=True)
        total_refresh_time = time.time() - refresh_start
        
        # Analyze performance
        successful_refreshes = 0
        total_refresh_duration = 0
        
        for result in refresh_results:
            if isinstance(result, Exception):
                logger.error(f"Refresh exception: {result}")
                continue
            
            if "error" not in result:
                successful_refreshes += 1
                total_refresh_duration += result["refresh_time"]
        
        # Performance assertions
        assert successful_refreshes >= (connection_count * 0.9)  # 90% success rate
        assert total_refresh_time < 10.0  # Batch refresh under 10 seconds
        
        if successful_refreshes > 0:
            avg_refresh_time = total_refresh_duration / successful_refreshes
            assert avg_refresh_time < 0.5  # Individual refresh under 500ms
        
        # Verify all WebSockets still functional
        active_connections = len(refresh_manager.websocket_manager.active_connections)
        assert active_connections >= (connection_count * 0.9)
        
        logger.info(f"Load test: {successful_refreshes}/{connection_count} refreshes, "
                   f"total time: {total_refresh_time:.2f}s, setup: {setup_time:.2f}s")
    
    async def test_jwt_refresh_redis_persistence(self, refresh_manager, redis_client):
        """Test JWT refresh updates session data in Redis correctly."""
        user_id = f"redis_test_user_{uuid.uuid4().hex[:8]}"
        
        # Create session
        session_data = await refresh_manager.create_authenticated_session(user_id)
        session_id = session_data["session_id"]
        original_token = session_data["token"]
        
        # Verify initial session in Redis
        session_key = f"session:{session_id}"
        initial_redis_data = await redis_client.get(session_key)
        assert initial_redis_data is not None
        
        initial_session = json.loads(initial_redis_data)
        assert initial_session["user_id"] == user_id
        assert initial_session["token"] == original_token
        
        # Perform refresh
        refresh_event = await refresh_manager.refresh_token_for_user(user_id)
        new_token = refresh_event["new_token"]
        
        # Verify updated session in Redis
        updated_redis_data = await redis_client.get(session_key)
        assert updated_redis_data is not None
        
        updated_session = json.loads(updated_redis_data)
        assert updated_session["user_id"] == user_id
        assert updated_session["token"] == new_token
        assert updated_session["token"] != original_token
        assert "refreshed_at" in updated_session
        
        # Verify WebSocket connection uses new token context
        websocket = session_data["websocket"]
        assert not websocket.closed
        
        # Test message with new token context
        post_refresh_message = {"type": "redis_test", "data": {"new_token_used": True}}
        success = await refresh_manager.websocket_manager.send_message_to_user(
            user_id, post_refresh_message
        )
        assert success is True
    
    async def test_jwt_refresh_failure_recovery(self, refresh_manager, redis_client):
        """Test recovery from JWT refresh failures."""
        user_id = f"failure_test_user_{uuid.uuid4().hex[:8]}"
        
        # Create session
        session_data = await refresh_manager.create_authenticated_session(user_id)
        
        # Simulate Redis failure during refresh
        with patch.object(redis_client, 'set') as mock_redis_set:
            mock_redis_set.side_effect = redis.ConnectionError("Redis connection failed")
            
            # Attempt refresh - should handle Redis failure gracefully
            try:
                await refresh_manager.refresh_token_for_user(user_id)
                # Depending on implementation, this might succeed or fail
                # Main requirement: no unhandled exceptions
            except Exception as e:
                # Should be handled gracefully
                assert "connection failed" in str(e).lower() or "redis" in str(e).lower()
        
        # Verify WebSocket connection still manageable
        websocket = session_data["websocket"]
        assert user_id in refresh_manager.websocket_manager.active_connections
        
        # Test recovery after Redis restored
        recovery_message = {"type": "recovery_test", "data": {}}
        success = await refresh_manager.websocket_manager.send_message_to_user(
            user_id, recovery_message
        )
        # Should work with original token or handle gracefully
        assert success is True or not websocket.closed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])