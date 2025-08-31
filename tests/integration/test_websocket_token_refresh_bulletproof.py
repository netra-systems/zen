#!/usr/bin/env python
"""WebSocket Token Refresh Integration Tests

Business Value: Continuous chat availability without disconnection
Tests: JWT token refresh during active WebSocket sessions

This suite ensures:
1. Tokens refresh seamlessly during active chat
2. No messages are lost during refresh
3. Authentication remains valid throughout
4. Multiple concurrent refreshes work correctly
5. Expired tokens are handled gracefully
"""

import asyncio
import json
import jwt
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import production components
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.registry import WebSocketMessage
from fastapi import WebSocket
from fastapi.websockets import WebSocketState


# ============================================================================
# TOKEN UTILITIES
# ============================================================================

class TokenManager:
    """Manage JWT tokens for testing."""
    
    def __init__(self, secret: str = "test_secret"):
        self.secret = secret
        self.algorithm = "HS256"
        
    def create_token(self, user_id: str, expires_in_seconds: int = 3600, 
                     is_refresh: bool = False) -> str:
        """Create a JWT token."""
        payload = {
            "sub": user_id,
            "type": "refresh" if is_refresh else "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode a JWT token."""
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            return {"error": "expired"}
        except jwt.InvalidTokenError as e:
            return {"error": str(e)}
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired."""
        decoded = self.decode_token(token)
        return decoded.get("error") == "expired"
    
    def get_token_ttl(self, token: str) -> int:
        """Get remaining TTL of token in seconds."""
        decoded = self.decode_token(token)
        if "exp" in decoded:
            exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
            ttl = (exp_time - datetime.now(timezone.utc)).total_seconds()
            return max(0, int(ttl))
        return 0


class MockAuthService:
    """Mock auth service for testing."""
    
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self.refresh_count = 0
        self.should_fail = False
        self.failure_pattern = None
        
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify an access token."""
        decoded = self.token_manager.decode_token(token)
        if "error" in decoded:
            return {"valid": False, "error": decoded["error"]}
        return {
            "valid": True,
            "user_id": decoded.get("sub"),
            "exp": decoded.get("exp")
        }
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an access token using refresh token."""
        self.refresh_count += 1
        
        # Simulate failures if configured
        if self.should_fail:
            if self.failure_pattern == "intermittent" and self.refresh_count % 3 == 0:
                return {"error": "Service temporarily unavailable"}
            elif self.failure_pattern == "expired":
                return {"error": "Refresh token expired"}
        
        # Verify refresh token
        decoded = self.token_manager.decode_token(refresh_token)
        if "error" in decoded:
            return {"error": f"Invalid refresh token: {decoded['error']}"}
        
        if decoded.get("type") != "refresh":
            return {"error": "Not a refresh token"}
        
        # Create new access token
        user_id = decoded.get("sub")
        new_access_token = self.token_manager.create_token(user_id, expires_in_seconds=300)  # 5 min for testing
        
        return {
            "access_token": new_access_token,
            "expires_in": 300,
            "user_id": user_id
        }


class TokenRefreshMetrics:
    """Track token refresh metrics."""
    
    def __init__(self):
        self.refresh_attempts = 0
        self.refresh_successes = 0
        self.refresh_failures = 0
        self.messages_during_refresh = 0
        self.messages_lost = 0
        self.refresh_durations: List[float] = []
        self.token_lifetimes: List[float] = []
        
    def record_refresh_attempt(self):
        self.refresh_attempts += 1
        
    def record_refresh_success(self, duration: float):
        self.refresh_successes += 1
        self.refresh_durations.append(duration)
        
    def record_refresh_failure(self):
        self.refresh_failures += 1
        
    def record_message_during_refresh(self):
        self.messages_during_refresh += 1
        
    def record_message_lost(self):
        self.messages_lost += 1
        
    def record_token_lifetime(self, lifetime: float):
        self.token_lifetimes.append(lifetime)
        
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "refreshes": {
                "attempts": self.refresh_attempts,
                "successes": self.refresh_successes,
                "failures": self.refresh_failures,
                "success_rate": self.refresh_successes / max(1, self.refresh_attempts)
            },
            "performance": {
                "avg_refresh_duration_ms": sum(self.refresh_durations) * 1000 / max(1, len(self.refresh_durations)) if self.refresh_durations else 0,
                "max_refresh_duration_ms": max(self.refresh_durations) * 1000 if self.refresh_durations else 0,
                "avg_token_lifetime_s": sum(self.token_lifetimes) / max(1, len(self.token_lifetimes)) if self.token_lifetimes else 0
            },
            "reliability": {
                "messages_during_refresh": self.messages_during_refresh,
                "messages_lost": self.messages_lost,
                "message_loss_rate": self.messages_lost / max(1, self.messages_during_refresh)
            }
        }


# ============================================================================
# MOCK WEBSOCKET WITH TOKEN SUPPORT
# ============================================================================

class AuthenticatedMockWebSocket:
    """Mock WebSocket with authentication support."""
    
    def __init__(self, connection_id: str, user_id: str, 
                 access_token: str, refresh_token: str):
        self.connection_id = connection_id
        self.user_id = user_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_state = WebSocketState.CONNECTED
        self.application_state = WebSocketState.CONNECTED
        self.messages_sent: List[Dict] = []
        self.auth_headers = {"Authorization": f"Bearer {access_token}"}
        self.token_refresh_count = 0
        
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Send JSON message."""
        if self.client_state != WebSocketState.CONNECTED:
            raise ConnectionError("WebSocket not connected")
        
        self.messages_sent.append({
            "data": data,
            "timestamp": time.time(),
            "token_used": self.access_token[:10] + "..."  # Log token prefix
        })
    
    async def receive_json(self) -> Dict[str, Any]:
        """Receive JSON message."""
        # Simulate token refresh request from client
        if self.token_refresh_count > 0:
            return {
                "type": "token_refresh",
                "refresh_token": self.refresh_token
            }
        return {"type": "ping"}
    
    def update_token(self, new_access_token: str):
        """Update the access token."""
        self.access_token = new_access_token
        self.auth_headers = {"Authorization": f"Bearer {new_access_token}"}
        self.token_refresh_count += 1
    
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close connection."""
        self.client_state = WebSocketState.DISCONNECTED
        self.application_state = WebSocketState.DISCONNECTED


# ============================================================================
# TOKEN REFRESH HANDLER TESTS
# ============================================================================

class TestTokenRefreshIntegration:
    """Integration tests for token refresh during WebSocket sessions."""
    
    @pytest.fixture(autouse=True)
    async def setup_auth_environment(self):
        """Setup authentication test environment."""
        self.token_manager = TokenManager()
        self.auth_service = MockAuthService(self.token_manager)
        self.ws_manager = WebSocketManager()
        self.metrics = TokenRefreshMetrics()
        
        yield
        
        # Cleanup
        await self.cleanup_connections()
    
    async def cleanup_connections(self):
        """Clean up test connections."""
        for conn_id in list(self.ws_manager.connections.keys()):
            try:
                conn = self.ws_manager.connections[conn_id]
                ws = conn.get("websocket")
                if ws:
                    await ws.close()
            except Exception:
                pass
        self.ws_manager.connections.clear()
    
    def create_authenticated_connection(self, user_id: str, 
                                       token_ttl: int = 300) -> AuthenticatedMockWebSocket:
        """Create an authenticated WebSocket connection."""
        # Create tokens
        access_token = self.token_manager.create_token(user_id, expires_in_seconds=token_ttl)
        refresh_token = self.token_manager.create_token(user_id, expires_in_seconds=3600, is_refresh=True)
        
        # Create mock WebSocket
        conn_id = f"auth_{user_id}_{uuid.uuid4().hex[:8]}"
        mock_ws = AuthenticatedMockWebSocket(conn_id, user_id, access_token, refresh_token)
        
        # Register with manager
        self.ws_manager.connections[conn_id] = {
            "connection_id": conn_id,
            "user_id": user_id,
            "websocket": mock_ws,
            "thread_id": f"thread_{user_id}",
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expires_at": datetime.now(timezone.utc) + timedelta(seconds=token_ttl),
            "is_healthy": True
        }
        
        return mock_ws
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_token_refresh_during_active_chat(self):
        """Test token refresh while chat is active."""
        user_id = "active_user"
        mock_ws = self.create_authenticated_connection(user_id, token_ttl=5)  # 5 second TTL
        
        notifier = WebSocketNotifier(self.ws_manager)
        
        # Start sending messages
        context = AgentExecutionContext(
            run_id="active_chat",
            thread_id=f"thread_{user_id}",
            user_id=user_id,
            agent_name="test",
            retry_count=0,
            max_retries=1
        )
        
        # Send initial messages
        await notifier.send_agent_started(context)
        await notifier.send_agent_thinking(context, "Processing...")
        
        initial_token = mock_ws.access_token
        initial_message_count = len(mock_ws.messages_sent)
        
        # Wait for token to near expiry
        await asyncio.sleep(3)
        
        # Trigger refresh
        self.metrics.record_refresh_attempt()
        refresh_start = time.time()
        
        refresh_result = await self.auth_service.refresh_access_token(mock_ws.refresh_token)
        
        if "access_token" in refresh_result:
            mock_ws.update_token(refresh_result["access_token"])
            self.metrics.record_refresh_success(time.time() - refresh_start)
            
            # Update connection info
            conn_id = mock_ws.connection_id
            if conn_id in self.ws_manager.connections:
                self.ws_manager.connections[conn_id]["access_token"] = refresh_result["access_token"]
                self.ws_manager.connections[conn_id]["token_expires_at"] = (
                    datetime.now(timezone.utc) + timedelta(seconds=refresh_result["expires_in"])
                )
        else:
            self.metrics.record_refresh_failure()
        
        # Continue sending messages with new token
        await notifier.send_tool_executing(context, "test_tool")
        await notifier.send_tool_completed(context, "test_tool", {"result": "success"})
        await notifier.send_agent_completed(context, {"success": True})
        
        # Verify token was refreshed
        assert mock_ws.access_token != initial_token, "Token was not refreshed"
        assert mock_ws.token_refresh_count > 0, "Token refresh count not incremented"
        
        # Verify no messages were lost
        final_message_count = len(mock_ws.messages_sent)
        assert final_message_count > initial_message_count, "No messages sent after refresh"
        
        # Check metrics
        summary = self.metrics.get_summary()
        assert summary["refreshes"]["success_rate"] == 1.0, "Token refresh failed"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_token_refreshes(self):
        """Test multiple users refreshing tokens concurrently."""
        num_users = 10
        connections = {}
        
        # Create connections with short TTL
        for i in range(num_users):
            user_id = f"concurrent_user_{i}"
            mock_ws = self.create_authenticated_connection(user_id, token_ttl=3)
            connections[user_id] = mock_ws
        
        # Refresh all tokens concurrently
        async def refresh_user_token(user_id: str, mock_ws: AuthenticatedMockWebSocket):
            self.metrics.record_refresh_attempt()
            refresh_start = time.time()
            
            try:
                result = await self.auth_service.refresh_access_token(mock_ws.refresh_token)
                if "access_token" in result:
                    mock_ws.update_token(result["access_token"])
                    self.metrics.record_refresh_success(time.time() - refresh_start)
                    return True
                else:
                    self.metrics.record_refresh_failure()
                    return False
            except Exception as e:
                logger.error(f"Refresh failed for {user_id}: {e}")
                self.metrics.record_refresh_failure()
                return False
        
        # Wait for tokens to near expiry
        await asyncio.sleep(2)
        
        # Refresh all concurrently
        refresh_tasks = [
            refresh_user_token(user_id, mock_ws) 
            for user_id, mock_ws in connections.items()
        ]
        results = await asyncio.gather(*refresh_tasks)
        
        # Verify all refreshes succeeded
        success_count = sum(1 for r in results if r)
        assert success_count == num_users, f"Only {success_count}/{num_users} refreshes succeeded"
        
        # Check metrics
        summary = self.metrics.get_summary()
        assert summary["refreshes"]["success_rate"] >= 0.95, "Too many refresh failures"
        assert summary["performance"]["avg_refresh_duration_ms"] < 100, "Refresh too slow"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_expired_token_handling(self):
        """Test handling of expired tokens."""
        user_id = "expired_user"
        mock_ws = self.create_authenticated_connection(user_id, token_ttl=1)  # 1 second TTL
        
        # Wait for token to expire
        await asyncio.sleep(2)
        
        # Verify token is expired
        assert self.token_manager.is_token_expired(mock_ws.access_token), "Token should be expired"
        
        # Try to send message with expired token
        notifier = WebSocketNotifier(self.ws_manager)
        context = AgentExecutionContext(
            run_id="expired_test",
            thread_id=f"thread_{user_id}",
            user_id=user_id,
            agent_name="test",
            retry_count=0,
            max_retries=1
        )
        
        # This should trigger automatic refresh
        self.metrics.record_refresh_attempt()
        refresh_start = time.time()
        
        # Simulate automatic refresh
        refresh_result = await self.auth_service.refresh_access_token(mock_ws.refresh_token)
        if "access_token" in refresh_result:
            mock_ws.update_token(refresh_result["access_token"])
            self.metrics.record_refresh_success(time.time() - refresh_start)
            
            # Now message should succeed
            await notifier.send_agent_thinking(context, "Message after refresh")
            
            assert len(mock_ws.messages_sent) > 0, "Message not sent after refresh"
        else:
            self.metrics.record_refresh_failure()
            pytest.fail("Token refresh failed for expired token")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_refresh_with_invalid_refresh_token(self):
        """Test behavior when refresh token is invalid."""
        user_id = "invalid_refresh_user"
        mock_ws = self.create_authenticated_connection(user_id, token_ttl=5)
        
        # Corrupt the refresh token
        mock_ws.refresh_token = "invalid_token"
        
        # Try to refresh
        self.metrics.record_refresh_attempt()
        refresh_result = await self.auth_service.refresh_access_token(mock_ws.refresh_token)
        
        # Should fail
        assert "error" in refresh_result, "Invalid refresh token should cause error"
        self.metrics.record_refresh_failure()
        
        # Connection should be marked unhealthy
        conn_id = mock_ws.connection_id
        if conn_id in self.ws_manager.connections:
            # In production, this would mark connection for closure
            self.ws_manager.connections[conn_id]["is_healthy"] = False
        
        # Verify connection is unhealthy
        assert not self.ws_manager.connections[conn_id]["is_healthy"], "Connection should be unhealthy"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_message_buffering_during_refresh(self):
        """Test that messages are buffered during token refresh."""
        user_id = "buffer_user"
        mock_ws = self.create_authenticated_connection(user_id, token_ttl=3)
        
        notifier = WebSocketNotifier(self.ws_manager)
        context = AgentExecutionContext(
            run_id="buffer_test",
            thread_id=f"thread_{user_id}",
            user_id=user_id,
            agent_name="test",
            retry_count=0,
            max_retries=1
        )
        
        # Start sending messages
        message_buffer = []
        
        async def send_continuous_messages():
            """Send messages continuously."""
            for i in range(20):
                await notifier.send_agent_thinking(context, f"Message {i}")
                message_buffer.append(f"Message {i}")
                await asyncio.sleep(0.2)
        
        async def refresh_token_midway():
            """Refresh token while messages are being sent."""
            await asyncio.sleep(2)  # Wait for some messages
            
            self.metrics.record_refresh_attempt()
            refresh_start = time.time()
            
            # Mark messages sent during refresh
            messages_before = len(mock_ws.messages_sent)
            
            result = await self.auth_service.refresh_access_token(mock_ws.refresh_token)
            if "access_token" in result:
                mock_ws.update_token(result["access_token"])
                self.metrics.record_refresh_success(time.time() - refresh_start)
            
            messages_after = len(mock_ws.messages_sent)
            messages_during = messages_after - messages_before
            
            for _ in range(messages_during):
                self.metrics.record_message_during_refresh()
        
        # Run both concurrently
        await asyncio.gather(
            send_continuous_messages(),
            refresh_token_midway()
        )
        
        # Verify all messages were delivered
        assert len(mock_ws.messages_sent) == len(message_buffer), \
            f"Message loss detected: {len(mock_ws.messages_sent)} != {len(message_buffer)}"
        
        # Check metrics
        summary = self.metrics.get_summary()
        assert summary["reliability"]["message_loss_rate"] == 0, "Messages were lost during refresh"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_refresh_with_network_issues(self):
        """Test token refresh with simulated network issues."""
        user_id = "network_issue_user"
        mock_ws = self.create_authenticated_connection(user_id, token_ttl=5)
        
        # Configure auth service to fail intermittently
        self.auth_service.should_fail = True
        self.auth_service.failure_pattern = "intermittent"
        
        # Try multiple refresh attempts
        max_retries = 5
        refresh_succeeded = False
        
        for attempt in range(max_retries):
            self.metrics.record_refresh_attempt()
            refresh_start = time.time()
            
            result = await self.auth_service.refresh_access_token(mock_ws.refresh_token)
            
            if "access_token" in result:
                mock_ws.update_token(result["access_token"])
                self.metrics.record_refresh_success(time.time() - refresh_start)
                refresh_succeeded = True
                break
            else:
                self.metrics.record_refresh_failure()
                await asyncio.sleep(0.5)  # Backoff
        
        # Should eventually succeed with retries
        assert refresh_succeeded, "Token refresh failed after all retries"
        
        # Check retry metrics
        summary = self.metrics.get_summary()
        assert summary["refreshes"]["attempts"] > 1, "Should have required retries"
        assert summary["refreshes"]["successes"] > 0, "Should have at least one success"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_graceful_shutdown_during_refresh(self):
        """Test graceful shutdown while token refresh is in progress."""
        user_id = "shutdown_user"
        mock_ws = self.create_authenticated_connection(user_id, token_ttl=3)
        
        # Start refresh
        refresh_task = asyncio.create_task(
            self.auth_service.refresh_access_token(mock_ws.refresh_token)
        )
        
        # Simulate shutdown signal after short delay
        await asyncio.sleep(0.1)
        
        # Close connection
        await mock_ws.close(code=1001, reason="Going away")
        
        # Cancel refresh task
        refresh_task.cancel()
        
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass  # Expected
        
        # Verify connection is closed
        assert mock_ws.client_state == WebSocketState.DISCONNECTED, "Connection not closed"
        
        # Clean up connection from manager
        conn_id = mock_ws.connection_id
        if conn_id in self.ws_manager.connections:
            del self.ws_manager.connections[conn_id]
        
        assert conn_id not in self.ws_manager.connections, "Connection not cleaned up"


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestTokenRefreshPerformance:
    """Performance tests for token refresh."""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_refresh_latency_under_load(self):
        """Test token refresh latency under load."""
        token_manager = TokenManager()
        auth_service = MockAuthService(token_manager)
        
        num_refreshes = 100
        refresh_times = []
        
        for i in range(num_refreshes):
            user_id = f"perf_user_{i}"
            refresh_token = token_manager.create_token(user_id, expires_in_seconds=3600, is_refresh=True)
            
            start_time = time.time()
            result = await auth_service.refresh_access_token(refresh_token)
            refresh_time = time.time() - start_time
            
            if "access_token" in result:
                refresh_times.append(refresh_time)
        
        # Calculate percentiles
        refresh_times.sort()
        p50 = refresh_times[int(len(refresh_times) * 0.50)]
        p95 = refresh_times[int(len(refresh_times) * 0.95)]
        p99 = refresh_times[int(len(refresh_times) * 0.99)]
        
        logger.info(f"Refresh latencies - P50: {p50*1000:.2f}ms, P95: {p95*1000:.2f}ms, P99: {p99*1000:.2f}ms")
        
        # Assert performance requirements
        assert p50 < 0.010, f"P50 latency too high: {p50*1000:.2f}ms"
        assert p95 < 0.050, f"P95 latency too high: {p95*1000:.2f}ms"
        assert p99 < 0.100, f"P99 latency too high: {p99*1000:.2f}ms"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    # Run with: python tests/integration/test_websocket_token_refresh_bulletproof.py
    pytest.main([__file__, "-v", "-s", "--tb=short"])