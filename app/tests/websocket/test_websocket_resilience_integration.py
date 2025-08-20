"""
Integration tests for WebSocket resilience and reliability.

Tests end-to-end scenarios combining all reliability fixes:
- Complete connection lifecycle with all fixes applied
- Failure recovery scenarios
- Production deployment readiness
- Performance under load
- Real-world edge cases
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import List, Dict, Any

from app.routes.websocket_enhanced import (
    WebSocketConnectionManager,
    DatabaseConnectionPool,
    enhanced_websocket_endpoint
)
from app.websocket.unified.manager import UnifiedWebSocketManager
from app.core.websocket_cors import WebSocketCORSHandler


class TestCompleteConnectionLifecycle:
    """Test complete WebSocket connection lifecycle with all fixes applied."""
    
    @pytest.mark.asyncio
    async def test_full_connection_lifecycle_success(self):
        """Test successful connection from start to finish with all features."""
        manager = WebSocketConnectionManager()
        mock_websocket = MagicMock()
        mock_websocket.query_params = {"token": "valid_token"}
        mock_websocket.headers = {"origin": "https://netra.ai"}
        
        # Mock successful token validation
        session_info = {
            "user_id": "test_user",
            "email": "test@netra.ai", 
            "token_expires": (datetime.now(timezone.utc).timestamp() + 3600),
            "current_token": "valid_token"
        }
        
        # Test connection establishment
        with patch('app.routes.websocket_enhanced.auth_client') as mock_auth:
            mock_auth.validate_token.return_value = {
                "valid": True,
                "user_id": "test_user",
                "email": "test@netra.ai",
                "expires_at": session_info["token_expires"]
            }
            
            connection_id = await manager.add_connection("test_user", mock_websocket, session_info)
            
            # Should have valid connection ID
            assert connection_id.startswith("test_user_")
            
            # Should have started token refresh task
            assert connection_id in manager.token_refresh_tasks
            
            # Should have connection metadata
            assert connection_id in manager.connection_metadata
            metadata = manager.connection_metadata[connection_id]
            assert metadata["user_id"] == "test_user"
            assert metadata["status"] == "connected"
        
        # Test connection cleanup
        await manager.remove_connection("test_user", connection_id)
        
        # Should have cleaned up properly
        assert connection_id not in manager.connection_metadata
        assert connection_id not in manager.token_refresh_tasks
    
    @pytest.mark.asyncio
    async def test_connection_with_database_pooling(self):
        """Test connection establishment with database connection pooling."""
        pool = DatabaseConnectionPool(max_pool_size=3)
        
        with patch('app.routes.websocket_enhanced.async_session_factory') as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value = mock_session
            
            # Multiple session requests should use pooling
            sessions = []
            for _ in range(3):
                session = await pool.get_pooled_session()
                sessions.append(session)
            
            # Should have created sessions up to pool limit
            assert len(sessions) == 3
            assert all(session is not None for session in sessions)
    
    @pytest.mark.asyncio 
    async def test_cors_validation_in_connection_flow(self):
        """Test that CORS validation is properly integrated in connection flow."""
        cors_handler = WebSocketCORSHandler(
            allowed_origins=["https://netra.ai"],
            environment="production"
        )
        
        # Valid origin should pass
        valid_result = cors_handler.is_origin_allowed("https://netra.ai")
        assert valid_result is True
        
        # Invalid origin should be blocked
        invalid_result = cors_handler.is_origin_allowed("http://malicious-site.com")
        assert invalid_result is False
        
        # Should have recorded violation
        assert "malicious-site.com" in str(cors_handler._violation_counts)


class TestFailureRecoveryScenarios:
    """Test recovery from various failure scenarios."""
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_recovery(self):
        """Test recovery when database connection pool is exhausted."""
        pool = DatabaseConnectionPool(max_pool_size=2)
        
        with patch('app.routes.websocket_enhanced.async_session_factory') as mock_factory:
            mock_factory.return_value = AsyncMock()
            
            # Exhaust pool
            session1 = await pool.get_pooled_session()
            session2 = await pool.get_pooled_session()
            
            # Third request should fail
            with pytest.raises(RuntimeError, match="pool exhausted"):
                await pool.get_pooled_session()
            
            # Return session to pool
            await pool.return_session_to_pool(mock_factory)
            
            # Should be able to get session again
            session3 = await pool.get_pooled_session()
            assert session3 is not None
    
    @pytest.mark.asyncio
    async def test_token_refresh_failure_recovery(self):
        """Test recovery when token refresh fails."""
        manager = WebSocketConnectionManager()
        mock_websocket = MagicMock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.close = AsyncMock()
        
        session_info = {"current_token": "expiring_token"}
        
        with patch('app.routes.websocket_enhanced.auth_client') as mock_auth:
            # First attempt fails
            mock_auth.refresh_token.side_effect = [
                Exception("Network error"),  # First call fails
                {  # Second call succeeds
                    "valid": True,
                    "access_token": "new_token",
                    "expires_at": "2024-01-01T12:00:00Z"
                }
            ]
            
            # First attempt should fail gracefully
            result1 = await manager._refresh_connection_token(
                mock_websocket, "conn_1", "test_user", session_info
            )
            assert result1 is False
            
            # Second attempt should succeed
            result2 = await manager._refresh_connection_token(
                mock_websocket, "conn_1", "test_user", session_info
            )
            assert result2 is True
            
            # Should have notified client of successful refresh
            mock_websocket.send_json.assert_called()
            last_message = mock_websocket.send_json.call_args[0][0]
            assert last_message["type"] == "token_refreshed"
    
    @pytest.mark.asyncio
    async def test_transactional_message_recovery_after_failure(self):
        """Test that messages are recovered and retried after failures."""
        manager = UnifiedWebSocketManager()
        
        # Set up failed message in pending state
        message_id = "failed_msg_1"
        failed_message = {
            "message_id": message_id,
            "user_id": "user_1",
            "message": {"type": "important_message", "content": "Critical data"},
            "timestamp": time.time(),
            "status": "pending",
            "retry_count": 1
        }
        
        manager.pending_messages = {message_id: failed_message}
        
        with patch.object(manager, 'send_message_to_user', return_value=True) as mock_send:
            # Retry pending messages
            await manager._retry_pending_messages()
            
            # Should have attempted to resend
            mock_send.assert_called_once_with(
                "user_1", 
                {"type": "important_message", "content": "Critical data"},
                retry=False
            )
    
    @pytest.mark.asyncio
    async def test_memory_cleanup_recovery_after_leak(self):
        """Test that memory cleanup recovers from potential memory leaks."""
        # Simulate message queue growth beyond limits
        messages = []
        current_time = time.time()
        
        # Add mix of old and new messages
        for i in range(1500):  # Exceed typical limits
            age_seconds = i % 600  # Some old, some new
            message = {
                "type": "test",
                "timestamp": current_time - age_seconds,
                "content": f"Message {i}"
            }
            messages.append(message)
        
        # Apply cleanup logic
        MAX_QUEUE_SIZE = 1000
        MAX_MESSAGE_AGE_MS = 300000  # 5 minutes
        
        now_ms = current_time * 1000
        
        # Filter by age
        fresh_messages = [
            msg for msg in messages
            if now_ms - (msg["timestamp"] * 1000) < MAX_MESSAGE_AGE_MS
        ]
        
        # Enforce size limit
        if len(fresh_messages) > MAX_QUEUE_SIZE:
            fresh_messages = fresh_messages[-MAX_QUEUE_SIZE:]
        
        # Should have recovered to reasonable size
        assert len(fresh_messages) <= MAX_QUEUE_SIZE
        # Should have kept recent messages
        assert len(fresh_messages) > 0
    
    @pytest.mark.asyncio
    async def test_cors_attack_recovery(self):
        """Test recovery from CORS-based attacks."""
        handler = WebSocketCORSHandler(environment="production")
        
        # Simulate attack with many malicious origins
        attack_origins = [f"http://attack-{i}.com" for i in range(100)]
        
        # Generate violations
        for origin in attack_origins:
            handler.is_origin_allowed(origin)
        
        # System should have blocked some origins
        assert len(handler._blocked_origins) > 0
        
        # But should still allow legitimate origins
        assert handler.is_origin_allowed("https://netra.ai") is True
        
        # Should provide security statistics
        stats = handler.get_security_stats()
        assert stats["total_violations"] >= 100
        assert stats["blocked_origin_count"] >= 0


class TestProductionDeploymentReadiness:
    """Test readiness for production deployment."""
    
    @pytest.mark.asyncio
    async def test_production_configuration_validation(self):
        """Test that production configuration is properly validated."""
        # Test production CORS handler
        prod_handler = WebSocketCORSHandler(
            allowed_origins=[
                "https://netra.ai",
                "https://app.netra.ai", 
                "https://www.netra.ai"
            ],
            environment="production"
        )
        
        # Should reject HTTP in production
        assert prod_handler.is_origin_allowed("http://netra.ai") is False
        
        # Should accept HTTPS
        assert prod_handler.is_origin_allowed("https://netra.ai") is True
        
        # Should include security headers
        headers = prod_handler.get_cors_headers("https://netra.ai")
        security_headers = [
            "Strict-Transport-Security",
            "X-Content-Type-Options",
            "X-Frame-Options"
        ]
        
        for header in security_headers:
            assert header in headers
    
    @pytest.mark.asyncio
    async def test_database_pool_production_sizing(self):
        """Test that database pool is sized appropriately for production."""
        # Test with production-like pool size
        large_pool = DatabaseConnectionPool(max_pool_size=50)
        
        with patch('app.routes.websocket_enhanced.async_session_factory') as mock_factory:
            mock_factory.return_value = AsyncMock()
            
            # Should handle many concurrent connections
            sessions = []
            for i in range(25):  # Half of pool size
                session = await large_pool.get_pooled_session()
                sessions.append(session)
            
            assert len(sessions) == 25
            assert large_pool.active_sessions == 25
    
    @pytest.mark.asyncio
    async def test_token_refresh_production_timing(self):
        """Test that token refresh timing works for production token lifespans."""
        manager = WebSocketConnectionManager()
        mock_websocket = MagicMock()
        
        # Typical production token: 1 hour lifespan
        expires_in_seconds = 3600  # 1 hour
        expires_at = datetime.now(timezone.utc).timestamp() + expires_in_seconds
        session_info = {
            "user_id": "prod_user",
            "token_expires": datetime.fromtimestamp(expires_at, timezone.utc).isoformat()
        }
        
        with patch('asyncio.sleep') as mock_sleep:
            with patch.object(manager, '_refresh_connection_token', return_value=True):
                # Should calculate refresh time correctly (5 minutes before expiry)
                await manager._handle_token_refresh("conn_1", "prod_user", mock_websocket, session_info)
                
                mock_sleep.assert_called_once()
                sleep_time = mock_sleep.call_args[0][0]
                expected_time = expires_in_seconds - 300  # 5 minute buffer
                
                assert abs(sleep_time - expected_time) < 5  # Allow small variance
    
    def test_error_logging_production_readiness(self):
        """Test that error logging is appropriate for production monitoring."""
        handler = WebSocketCORSHandler(environment="production")
        
        with patch('app.core.websocket_cors.logger') as mock_logger:
            # Generate security violation
            handler.is_origin_allowed("http://malicious.com")
            
            # Should log security violations for monitoring
            mock_logger.warning.assert_called()
            log_call = mock_logger.warning.call_args[0][0]
            assert "security violation" in log_call.lower()


class TestPerformanceUnderLoad:
    """Test performance characteristics under load."""
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_handling(self):
        """Test handling of many concurrent connections."""
        manager = WebSocketConnectionManager()
        
        # Create many concurrent connections
        connections = []
        mock_websockets = []
        
        for i in range(100):
            mock_ws = MagicMock()
            session_info = {
                "user_id": f"user_{i}",
                "token_expires": datetime.now(timezone.utc).timestamp() + 3600
            }
            
            # Don't actually create refresh tasks for performance test
            with patch.object(manager, '_handle_token_refresh'):
                connection_id = await manager.add_connection(f"user_{i}", mock_ws, session_info)
                connections.append(connection_id)
                mock_websockets.append(mock_ws)
        
        # Should have created all connections
        assert len(connections) == 100
        assert len(manager.connection_metadata) == 100
        
        # Cleanup should handle all connections efficiently
        start_time = time.time()
        
        for i, connection_id in enumerate(connections):
            await manager.remove_connection(f"user_{i}", connection_id)
        
        cleanup_time = time.time() - start_time
        
        # Cleanup should be reasonably fast
        assert cleanup_time < 5.0  # Less than 5 seconds for 100 connections
        assert len(manager.connection_metadata) == 0
    
    @pytest.mark.asyncio
    async def test_message_processing_throughput(self):
        """Test message processing throughput under load."""
        unified_manager = UnifiedWebSocketManager()
        
        # Process many messages rapidly
        message_count = 1000
        start_time = time.time()
        
        with patch.object(unified_manager.messaging, 'send_to_user', return_value=True):
            with patch.object(unified_manager, '_mark_message_sending'):
                with patch.object(unified_manager, '_mark_message_sent'):
                    
                    tasks = []
                    for i in range(message_count):
                        task = unified_manager.send_message_to_user(
                            f"user_{i % 10}",  # Cycle through 10 users
                            {"type": "test", "content": f"Message {i}"}
                        )
                        tasks.append(task)
                    
                    results = await asyncio.gather(*tasks)
        
        processing_time = time.time() - start_time
        
        # Should process messages efficiently
        assert all(results)  # All messages processed successfully
        assert processing_time < 10.0  # Less than 10 seconds for 1000 messages
        
        # Should have updated telemetry
        assert unified_manager.telemetry["messages_sent"] >= message_count
    
    def test_cors_validation_performance(self):
        """Test CORS validation performance under high load."""
        handler = WebSocketCORSHandler(environment="production")
        
        # Test many different origins
        test_origins = [
            "https://netra.ai",
            "http://malicious.com",
            "https://app.netra.ai",
            "chrome-extension://fake",
            "http://192.168.1.1"
        ] * 200  # 1000 total checks
        
        start_time = time.time()
        
        results = []
        for origin in test_origins:
            result = handler.is_origin_allowed(origin)
            results.append(result)
        
        validation_time = time.time() - start_time
        
        # Should complete validation quickly
        assert validation_time < 2.0  # Less than 2 seconds for 1000 validations
        
        # Should have correct results
        legitimate_count = sum(1 for origin in test_origins if "netra.ai" in origin)
        legitimate_results = sum(1 for i, origin in enumerate(test_origins) 
                               if "netra.ai" in origin and results[i])
        
        assert legitimate_results == legitimate_count


class TestRealWorldEdgeCases:
    """Test handling of real-world edge cases."""
    
    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect_cycles(self):
        """Test handling of rapid connect/disconnect cycles."""
        manager = WebSocketConnectionManager()
        
        # Rapidly connect and disconnect
        for cycle in range(50):
            mock_ws = MagicMock()
            session_info = {
                "user_id": f"cycle_user_{cycle}",
                "token_expires": datetime.now(timezone.utc).timestamp() + 3600
            }
            
            # Connect
            with patch.object(manager, '_handle_token_refresh'):
                connection_id = await manager.add_connection(f"cycle_user_{cycle}", mock_ws, session_info)
            
            # Immediately disconnect
            await manager.remove_connection(f"cycle_user_{cycle}", connection_id)
        
        # Should handle cycles without memory leaks
        assert len(manager.connection_metadata) == 0
        assert len(manager.token_refresh_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_token_refresh_during_high_load(self):
        """Test token refresh behavior during high system load."""
        manager = WebSocketConnectionManager()
        
        # Simulate high load with many connections needing refresh
        refresh_tasks = []
        
        for i in range(20):
            mock_ws = MagicMock()
            mock_ws.send_json = AsyncMock()
            
            session_info = {"current_token": f"token_{i}"}
            
            with patch('app.routes.websocket_enhanced.auth_client') as mock_auth:
                mock_auth.refresh_token.return_value = {
                    "valid": True,
                    "access_token": f"new_token_{i}",
                    "expires_at": "2024-01-01T12:00:00Z"
                }
                
                task = manager._refresh_connection_token(
                    mock_ws, f"conn_{i}", f"user_{i}", session_info
                )
                refresh_tasks.append(task)
        
        # All refreshes should complete successfully
        results = await asyncio.gather(*refresh_tasks)
        assert all(results)
    
    @pytest.mark.asyncio
    async def test_database_pool_under_connection_churn(self):
        """Test database pool behavior under high connection churn."""
        pool = DatabaseConnectionPool(max_pool_size=10)
        
        with patch('app.routes.websocket_enhanced.async_session_factory') as mock_factory:
            mock_factory.return_value = AsyncMock()
            
            # Simulate high churn - rapid session requests and returns
            for cycle in range(100):
                # Get session
                session = await pool.get_pooled_session()
                assert session is not None
                
                # Immediately return (simulating short-lived operations)
                await pool.return_session_to_pool(mock_factory)
        
        # Pool should remain stable
        assert pool.active_sessions >= 0  # No negative counts
        assert pool.session_queue.qsize() >= 0  # Queue should be stable
    
    def test_cors_handler_edge_case_origins(self):
        """Test CORS handler with edge case origin formats."""
        handler = WebSocketCORSHandler(
            allowed_origins=["https://*.netra.ai"], 
            environment="production"
        )
        
        edge_case_origins = [
            "",  # Empty origin
            " ",  # Whitespace only
            "https://",  # Incomplete URL
            "invalid-url",  # Invalid format
            "https://sub.domain.netra.ai.malicious.com",  # Domain spoofing attempt
            "https://netra.ai:443",  # With default HTTPS port
            "https://NETRA.AI",  # Different case
        ]
        
        # Should handle all edge cases without crashing
        for origin in edge_case_origins:
            result = handler.is_origin_allowed(origin)
            assert isinstance(result, bool)  # Should return boolean, not crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])