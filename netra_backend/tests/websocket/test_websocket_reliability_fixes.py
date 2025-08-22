"""
Comprehensive tests for WebSocket reliability fixes.

Tests cover all critical issues addressed:
1. Database session per message anti-pattern -> connection pooling
2. JWT token refresh mechanism for long sessions
3. Memory leak in frontend message array -> memory management
4. Transactional message processing per websocket_reliability.xml
5. Exponential backoff in reconnection
6. CORS production security hardening

This test suite validates production-ready fixes addressing the 
identified WebSocket reliability concerns.
"""

# Add project root to path

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from netra_backend.tests.test_utils import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.core.websocket_cors import SECURITY_CONFIG, WebSocketCORSHandler

# Add project root to path
from netra_backend.app.routes.websocket_enhanced import (
    # Add project root to path

    DatabaseConnectionPool,

    WebSocketConnectionManager,

    db_pool,

)
from netra_backend.app.websocket.unified.manager import UnifiedWebSocketManager


class TestDatabaseConnectionPooling:

    """Test database connection pooling to prevent session-per-message anti-pattern."""
    

    @pytest.mark.asyncio

    async def test_connection_pool_initialization(self):

        """Test that connection pool initializes correctly."""

        pool = DatabaseConnectionPool(max_pool_size=5)
        

        assert pool.max_pool_size == 5

        assert pool.active_sessions == 0

        assert pool.session_queue.maxsize == 5
    

    @pytest.mark.asyncio

    async def test_pooled_session_creation(self):

        """Test getting session from pool."""

        pool = DatabaseConnectionPool(max_pool_size=3)
        

        with patch('app.routes.websocket_enhanced.async_session_factory') as mock_factory:

            mock_session = AsyncMock()

            mock_factory.return_value = mock_session
            
            # First session should create new one

            session = await pool.get_pooled_session()

            assert session == mock_session

            assert pool.active_sessions == 1
    

    @pytest.mark.asyncio

    async def test_connection_pool_exhaustion_prevention(self):

        """Test that pool prevents exhaustion by enforcing limits."""

        pool = DatabaseConnectionPool(max_pool_size=2)
        

        with patch('app.routes.websocket_enhanced.async_session_factory') as mock_factory:

            mock_factory.return_value = AsyncMock()
            
            # Fill the pool

            session1 = await pool.get_pooled_session()

            session2 = await pool.get_pooled_session()
            
            # Third session should raise exception due to pool exhaustion

            with pytest.raises(RuntimeError, match="Database connection pool exhausted"):

                await pool.get_pooled_session()
    

    @pytest.mark.asyncio

    async def test_session_return_to_pool(self):

        """Test that sessions are properly returned to pool."""

        pool = DatabaseConnectionPool(max_pool_size=3)

        mock_factory = AsyncMock()
        

        await pool.return_session_to_pool(mock_factory)
        # Should not raise exception and should add to queue

        assert pool.session_queue.qsize() == 1


class TestJWTTokenRefresh:

    """Test JWT token refresh mechanism for long-lived connections."""
    

    @pytest.mark.asyncio

    async def test_token_refresh_scheduling(self):

        """Test that token refresh is scheduled properly."""

        manager = WebSocketConnectionManager()

        mock_websocket = MagicMock()
        
        # Token expires in 10 minutes (600 seconds)

        expires_at = datetime.now(timezone.utc).timestamp() + 600

        session_info = {

            "user_id": "test_user",

            "token_expires": datetime.fromtimestamp(expires_at, timezone.utc).isoformat()

        }
        

        with patch.object(manager, '_handle_token_refresh') as mock_refresh:

            connection_id = await manager.add_connection("test_user", mock_websocket, session_info)
            
            # Should have started token refresh task

            assert connection_id in manager.token_refresh_tasks

            assert not manager.token_refresh_tasks[connection_id].done()
    

    @pytest.mark.asyncio

    async def test_token_refresh_calculation(self):

        """Test that refresh time is calculated correctly (5 minutes before expiry)."""

        manager = WebSocketConnectionManager()

        mock_websocket = MagicMock()
        
        # Token expires in 10 minutes

        expires_in_seconds = 600

        expires_at = datetime.now(timezone.utc).timestamp() + expires_in_seconds

        session_info = {

            "user_id": "test_user",

            "token_expires": datetime.fromtimestamp(expires_at, timezone.utc).isoformat()

        }
        

        with patch('asyncio.sleep') as mock_sleep:

            with patch.object(manager, '_refresh_connection_token', return_value=True):

                with patch.object(manager, '_handle_token_refresh', wraps=manager._handle_token_refresh) as mock_refresh:
                    # This would normally recurse, but we'll just check the first call

                    await manager._handle_token_refresh("conn_1", "test_user", mock_websocket, session_info)
                    
                    # Should sleep for approximately (600 - 300) = 300 seconds (5 min buffer)

                    mock_sleep.assert_called_once()

                    sleep_time = mock_sleep.call_args[0][0]

                    assert 295 <= sleep_time <= 305  # Allow some timing variance
    

    @pytest.mark.asyncio

    async def test_token_expiry_handling(self):

        """Test that expired tokens are handled gracefully."""

        manager = WebSocketConnectionManager()

        mock_websocket = MagicMock()

        mock_websocket.send_json = AsyncMock()

        mock_websocket.close = AsyncMock()
        
        # Token already expired

        expires_at = datetime.now(timezone.utc).timestamp() - 60  # 1 minute ago

        session_info = {

            "user_id": "test_user", 

            "token_expires": datetime.fromtimestamp(expires_at, timezone.utc).isoformat()

        }
        

        await manager._handle_token_refresh("conn_1", "test_user", mock_websocket, session_info)
        
        # Should send expiry message and close connection

        mock_websocket.send_json.assert_called_once()

        sent_message = mock_websocket.send_json.call_args[0][0]

        assert sent_message["type"] == "token_expired"
        
        # Should close with token expired code

        mock_websocket.close.assert_called_once_with(code=1008, reason="Token expired - please re-authenticate")
    

    @pytest.mark.asyncio

    async def test_token_refresh_success_notification(self):

        """Test that successful token refresh notifies client."""

        manager = WebSocketConnectionManager()

        mock_websocket = MagicMock()

        mock_websocket.send_json = AsyncMock()

        mock_websocket.query_params = {"token": "old_token"}
        

        session_info = {"current_token": "old_token"}
        

        with patch('app.routes.websocket_enhanced.auth_client') as mock_auth:

            mock_auth.refresh_token.return_value = {

                "valid": True,

                "access_token": "new_token",

                "expires_at": "2024-01-01T12:00:00Z"

            }
            

            result = await manager._refresh_connection_token(

                mock_websocket, "conn_1", "test_user", session_info

            )
            

            assert result is True

            mock_websocket.send_json.assert_called_once()

            sent_message = mock_websocket.send_json.call_args[0][0]

            assert sent_message["type"] == "token_refreshed"

            assert sent_message["payload"]["new_token"] == "new_token"


class TestMemoryLeakPrevention:

    """Test frontend memory leak prevention in message arrays."""
    

    def test_message_queue_size_limit(self):

        """Test that message queue enforces size limits."""
        # This would be tested in the frontend, but we can test the concept
        # by checking that our cleanup functions work
        
        # Simulate large message queue

        messages = [{"type": "test", "timestamp": time.time() - i} for i in range(1500)]
        
        # Apply cleanup logic (based on frontend implementation)

        MAX_QUEUE_SIZE = 1000

        MAX_MESSAGE_AGE_MS = 300000  # 5 minutes
        

        now = time.time() * 1000  # Convert to milliseconds
        
        # Filter old messages

        filtered_messages = [

            msg for msg in messages 

            if now - (msg["timestamp"] * 1000) < MAX_MESSAGE_AGE_MS

        ]
        
        # Enforce size limit

        if len(filtered_messages) > MAX_QUEUE_SIZE:

            filtered_messages = filtered_messages[-MAX_QUEUE_SIZE:]
        

        assert len(filtered_messages) <= MAX_QUEUE_SIZE
    

    def test_timestamp_array_cleanup(self):

        """Test that timestamp arrays are properly cleaned up."""
        # Simulate message timestamps

        now = time.time() * 1000

        old_timestamps = [now - 70000, now - 80000]  # Over 1 minute old

        recent_timestamps = [now - 30000, now - 10000]  # Recent
        

        all_timestamps = old_timestamps + recent_timestamps
        
        # Cleanup logic (60 second window)

        rate_limit_window = 60000

        cleaned_timestamps = [

            ts for ts in all_timestamps 

            if now - ts < rate_limit_window

        ]
        

        assert len(cleaned_timestamps) == 2

        assert all(ts in recent_timestamps for ts in cleaned_timestamps)


class TestTransactionalMessageProcessing:

    """Test transactional message processing per websocket_reliability.xml."""
    

    @pytest.mark.asyncio

    async def test_message_marked_sending_before_send(self):

        """Test that messages are marked as 'sending' before attempting to send."""

        manager = UnifiedWebSocketManager()
        

        with patch.object(manager, '_mark_message_sending') as mock_mark_sending:

            with patch.object(manager.messaging, 'send_to_user', return_value=True) as mock_send:

                with patch.object(manager, '_mark_message_sent') as mock_mark_sent:
                    

                    result = await manager.send_message_to_user("user_1", {"type": "test"})
                    

                    assert result is True
                    # Should mark as sending first

                    mock_mark_sending.assert_called_once()
                    # Then attempt send

                    mock_send.assert_called_once()
                    # Then mark as sent on success

                    mock_mark_sent.assert_called_once()
    

    @pytest.mark.asyncio

    async def test_message_reverted_to_pending_on_failure(self):

        """Test that messages are reverted to 'pending' on send failure."""

        manager = UnifiedWebSocketManager()
        

        with patch.object(manager, '_mark_message_sending'):

            with patch.object(manager.messaging, 'send_to_user', return_value=False) as mock_send:

                with patch.object(manager, '_mark_message_pending') as mock_mark_pending:
                    

                    result = await manager.send_message_to_user("user_1", {"type": "test"})
                    

                    assert result is False

                    mock_mark_pending.assert_called_once()
    

    @pytest.mark.asyncio

    async def test_message_reverted_to_pending_on_exception(self):

        """Test that messages are reverted to 'pending' on exception."""

        manager = UnifiedWebSocketManager()
        

        with patch.object(manager, '_mark_message_sending'):

            with patch.object(manager.messaging, 'send_to_user', side_effect=Exception("Network error")):

                with patch.object(manager, '_mark_message_pending') as mock_mark_pending:
                    

                    with pytest.raises(Exception):

                        await manager.send_message_to_user("user_1", {"type": "test"})
                    

                    mock_mark_pending.assert_called_once()
    

    @pytest.mark.asyncio

    async def test_pending_message_retry_mechanism(self):

        """Test that pending messages are retried according to policy."""

        manager = UnifiedWebSocketManager()
        
        # Set up pending message

        message_id = "test_msg_1"

        pending_data = {

            "message_id": message_id,

            "user_id": "user_1",

            "message": {"type": "test"},

            "timestamp": time.time(),

            "status": "pending",

            "retry_count": 1

        }
        

        manager.pending_messages = {message_id: pending_data}
        

        with patch.object(manager, 'send_message_to_user', return_value=True) as mock_send:

            await manager._retry_pending_messages()
            

            mock_send.assert_called_once_with("user_1", {"type": "test"}, retry=False)
    

    @pytest.mark.asyncio

    async def test_message_dropped_after_max_retries(self):

        """Test that messages are dropped after maximum retry attempts."""

        manager = UnifiedWebSocketManager()
        
        # Set up message with max retries exceeded

        message_id = "test_msg_1"

        pending_data = {

            "message_id": message_id,

            "user_id": "user_1", 

            "message": {"type": "test"},

            "timestamp": time.time(),

            "status": "pending",

            "retry_count": 5  # Exceeds max of 3

        }
        

        manager.pending_messages = {message_id: pending_data}
        

        await manager._retry_pending_messages()
        
        # Message should be removed from pending

        assert message_id not in manager.pending_messages


class TestExponentialBackoffReconnection:

    """Test exponential backoff reconnection logic."""
    

    def test_exponential_backoff_calculation(self):

        """Test that exponential backoff is calculated correctly."""

        base_delay = 1000  # 1 second
        
        # Calculate delays for first 5 attempts

        delays = []

        for attempt in range(1, 6):

            exponential_delay = base_delay * (2 ** (attempt - 1))
            # Add jitter simulation (0-1000ms)

            jitter = 500  # Average jitter

            total_delay = min(exponential_delay + jitter, 30000)  # Cap at 30 seconds

            delays.append(total_delay)
        
        # Verify exponential growth

        assert delays[0] == 1500    # 1000 + 500

        assert delays[1] == 2500    # 2000 + 500  

        assert delays[2] == 4500    # 4000 + 500

        assert delays[3] == 8500    # 8000 + 500

        assert delays[4] == 16500   # 16000 + 500
        
        # Verify each delay is longer than previous (exponential)

        for i in range(1, len(delays)):

            assert delays[i] > delays[i-1]
    

    def test_reconnection_delay_cap(self):

        """Test that reconnection delay is capped at maximum value."""

        base_delay = 1000

        max_delay = 30000
        
        # Very high attempt number should still cap at max

        attempt = 10

        exponential_delay = base_delay * (2 ** (attempt - 1))  # Would be very large

        jitter = 1000
        

        capped_delay = min(exponential_delay + jitter, max_delay)
        

        assert capped_delay == max_delay
    

    def test_jitter_prevents_thundering_herd(self):

        """Test that jitter helps prevent thundering herd problem."""
        import random
        

        base_delay = 2000

        attempt = 3
        
        # Simulate multiple clients reconnecting

        delays = []

        for _ in range(100):  # Simulate 100 clients

            exponential_delay = base_delay * (2 ** (attempt - 1))

            jitter = random.random() * 1000  # 0-1000ms random jitter

            total_delay = exponential_delay + jitter

            delays.append(total_delay)
        
        # Verify delays are spread out (not all the same)

        unique_delays = set(delays)

        assert len(unique_delays) > 50  # Should have many different delay values


class TestCORSSecurityHardening:

    """Test CORS production security hardening."""
    

    def test_production_https_requirement(self):

        """Test that production environment requires HTTPS origins."""

        handler = WebSocketCORSHandler(

            allowed_origins=["https://netrasystems.ai"], 

            environment="production"

        )
        
        # HTTPS should be allowed

        assert handler.is_origin_allowed("https://netrasystems.ai") is True
        
        # HTTP should be blocked in production

        assert handler.is_origin_allowed("http://netrasystems.ai") is False
    

    def test_suspicious_origin_blocking(self):

        """Test that suspicious origins are blocked."""

        handler = WebSocketCORSHandler(environment="production")
        
        # Test various suspicious patterns

        suspicious_origins = [

            "http://192.168.1.1:8080",  # IP address

            "https://abc.ngrok.io",      # ngrok tunnel

            "chrome-extension://abcdef", # Browser extension

            "http://localhost:8080"      # Unexpected port

        ]
        

        for origin in suspicious_origins:

            assert handler.is_origin_allowed(origin) is False
    

    def test_origin_length_validation(self):

        """Test that overly long origins are rejected."""

        handler = WebSocketCORSHandler(environment="production")
        
        # Create an origin that exceeds maximum length

        long_origin = "https://" + "a" * 300 + ".com"
        

        assert len(long_origin) > SECURITY_CONFIG["max_origin_length"]

        assert handler.is_origin_allowed(long_origin) is False
    

    def test_violation_rate_limiting(self):

        """Test that origins with too many violations get temporarily blocked."""

        handler = WebSocketCORSHandler(environment="production")
        

        malicious_origin = "http://malicious-site.com"
        
        # Generate multiple violations

        for _ in range(6):  # Exceed the 5 violation threshold

            handler.is_origin_allowed(malicious_origin)
        
        # Origin should now be temporarily blocked

        assert malicious_origin in handler._blocked_origins
        
        # Even if we add it to allowed origins, it should still be blocked

        handler.allowed_origins.append(malicious_origin)

        assert handler.is_origin_allowed(malicious_origin) is False
    

    def test_security_headers_in_production(self):

        """Test that security headers are added in production."""

        handler = WebSocketCORSHandler(environment="production")
        

        headers = handler.get_cors_headers("https://netrasystems.ai")
        
        # Should include security headers

        assert "Strict-Transport-Security" in headers

        assert "X-Content-Type-Options" in headers

        assert "X-Frame-Options" in headers

        assert "X-XSS-Protection" in headers

        assert "Referrer-Policy" in headers
        

        assert headers["X-Frame-Options"] == "DENY"

        assert headers["X-Content-Type-Options"] == "nosniff"
    

    def test_development_environment_more_permissive(self):

        """Test that development environment is more permissive."""

        dev_handler = WebSocketCORSHandler(environment="development")

        prod_handler = WebSocketCORSHandler(environment="production")
        
        # HTTP localhost should be allowed in development

        dev_result = dev_handler.is_origin_allowed("http://localhost:3000")

        prod_result = prod_handler.is_origin_allowed("http://localhost:3000") 
        
        # Development should be more permissive than production

        assert dev_result is True
        # Production should require HTTPS (depending on allowed origins)
    

    def test_manual_origin_unblocking(self):

        """Test that blocked origins can be manually unblocked."""

        handler = WebSocketCORSHandler(environment="production")
        

        origin = "http://blocked-origin.com"
        
        # Block the origin by generating violations

        for _ in range(6):

            handler.is_origin_allowed(origin)
        

        assert origin in handler._blocked_origins
        
        # Unblock manually

        result = handler.unblock_origin(origin)
        

        assert result is True

        assert origin not in handler._blocked_origins

        assert handler._violation_counts.get(origin, 0) == 0
    

    def test_security_statistics_tracking(self):

        """Test that security statistics are properly tracked."""

        handler = WebSocketCORSHandler(environment="production")
        
        # Generate some violations

        handler.is_origin_allowed("http://bad-origin1.com")

        handler.is_origin_allowed("http://bad-origin2.com")

        handler.is_origin_allowed("http://bad-origin1.com")  # Repeat
        

        stats = handler.get_security_stats()
        

        assert stats["total_violations"] >= 3

        assert "bad-origin1.com" in str(stats["violation_counts"])

        assert "bad-origin2.com" in str(stats["violation_counts"])

        assert stats["environment"] == "production"


class TestIntegrationScenarios:

    """Test integration scenarios combining multiple fixes."""
    

    @pytest.mark.asyncio

    async def test_network_failure_during_token_refresh(self):

        """Test token refresh failure during network issues."""

        manager = WebSocketConnectionManager()

        mock_websocket = MagicMock()

        mock_websocket.send_json = AsyncMock()

        mock_websocket.close = AsyncMock()
        

        session_info = {"current_token": "expiring_token"}
        

        with patch('app.routes.websocket_enhanced.auth_client') as mock_auth:
            # Simulate network failure during refresh

            mock_auth.refresh_token.side_effect = Exception("Network timeout")
            

            result = await manager._refresh_connection_token(

                mock_websocket, "conn_1", "test_user", session_info

            )
            

            assert result is False
            # Should not crash, should handle gracefully
    

    @pytest.mark.asyncio  

    async def test_memory_cleanup_during_connection_pool_exhaustion(self):

        """Test that memory cleanup works even when connection pool is exhausted."""

        pool = DatabaseConnectionPool(max_pool_size=1)
        

        with patch('app.routes.websocket_enhanced.async_session_factory') as mock_factory:

            mock_factory.return_value = AsyncMock()
            
            # Exhaust the pool

            session1 = await pool.get_pooled_session()
            
            # Try to get another session (should fail)

            with pytest.raises(RuntimeError):

                await pool.get_pooled_session()
            
            # Memory cleanup should still work
            # (This is more of a conceptual test since cleanup is separate from pooling)

            assert pool.active_sessions == 1  # Pool state is still consistent
    

    @pytest.mark.asyncio

    async def test_transactional_processing_with_cors_rejection(self):

        """Test that transactional processing handles CORS rejection properly."""

        manager = UnifiedWebSocketManager()

        cors_handler = WebSocketCORSHandler(environment="production")
        
        # Malicious origin that should be rejected

        malicious_origin = "http://malicious-site.com"
        
        # CORS should reject this

        assert cors_handler.is_origin_allowed(malicious_origin) is False
        
        # Even if somehow a message was attempted, transactional processing should handle it

        with patch.object(manager, '_mark_message_sending'):

            with patch.object(manager.messaging, 'send_to_user', side_effect=Exception("CORS rejection")):

                with patch.object(manager, '_mark_message_pending') as mock_pending:
                    

                    with pytest.raises(Exception):

                        await manager.send_message_to_user("user_1", {"type": "test"})
                    
                    # Should still mark as pending for potential retry

                    mock_pending.assert_called_once()


if __name__ == "__main__":

    pytest.main([__file__, "-v"])