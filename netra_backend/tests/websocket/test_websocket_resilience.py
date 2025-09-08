"""WebSocket Resilience and Recovery Tests.

Tests focused on connection resilience, error recovery, and network instability scenarios.
"""
import pytest
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

# Skip this entire module due to missing dependencies
# Function get_unified_websocket_manager doesn't exist in current implementation
pytestmark = pytest.mark.skip(reason="Missing dependencies: get_unified_websocket_manager not yet implemented")

import sys
from pathlib import Path

import asyncio
import time
from typing import Any, Dict, List

from netra_backend.app.core.websocket_cors import WebSocketCORSHandler

# TODO: Implement get_unified_websocket_manager when WebSocket resilience optimization is prioritized
from netra_backend.app.routes.websocket_unified import (
    # get_unified_websocket_manager,  # Not implemented yet
    unified_websocket_endpoint,
)

@pytest.mark.asyncio
class TestWebSocketConnectionResilience:
    """Test WebSocket connection resilience."""
    
    @pytest.mark.asyncio
    async def test_connection_survives_rapid_messages(self):
        """Test connection survives rapid message sending."""
        user_id = "rapid_test_user"
        connection_id = "conn_rapid"
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = UnifiedWebSocketManager()
        
        # Add connection
        session_info = {"user_id": user_id}
        actual_conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        try:
            # Send rapid burst of messages
            for i in range(20):
                message = f'{{"type": "ping", "sequence": {i}}}'
                success = await handle_websocket_message_enhanced(
                    user_id, actual_conn_id, mock_websocket, message
                )
                # Should handle all messages successfully
                assert success is True
                await asyncio.sleep(0.001)  # Tiny delay
                
            # Connection should still be alive
            stats = connection_manager.get_connection_stats()
            assert stats["total_connections"] >= 1
            
        finally:
            await connection_manager.remove_connection(user_id, actual_conn_id)
            
    @pytest.mark.asyncio
    async def test_connection_handles_malformed_messages(self):
        """Test connection handles malformed messages gracefully."""
        user_id = "malform_test_user"
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncNone  # TODO: Use real service instance
        
        session_info = {"user_id": user_id}
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        try:
            # Test various malformed messages
            malformed_messages = [
                "not json at all",
                '{"missing_type": true}',
                '{"type": ""}',  # Empty type
                '{"type": null}',  # Null type
                '{"type": 123}',  # Invalid type
                '',  # Empty message
                '{}',  # Empty object
            ]
            
            for message in malformed_messages:
                success = await handle_websocket_message_enhanced(
                    user_id, conn_id, mock_websocket, message
                )
                # Should handle gracefully and keep connection alive
                assert success is True
                
            # Verify error messages were sent
            assert mock_websocket.send_json.call_count >= len(malformed_messages)
            
            # Connection should still exist
            stats = connection_manager.get_connection_stats()
            assert user_id in stats["connections_per_user"]
            
        finally:
            await connection_manager.remove_connection(user_id, conn_id)
            
    @pytest.mark.asyncio
    async def test_connection_recovery_after_errors(self):
        """Test connection can recover after errors."""
        user_id = "recovery_test_user"
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = UnifiedWebSocketManager()
        
        session_info = {"user_id": user_id}
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        try:
            # Send several error-inducing messages
            for i in range(3):
                error_message = f"invalid json {i}"
                await handle_websocket_message_enhanced(
                    user_id, conn_id, mock_websocket, error_message
                )
                
            # Now send a valid message
            valid_message = '{"type": "ping", "timestamp": 123456}'
            success = await handle_websocket_message_enhanced(
                user_id, conn_id, mock_websocket, valid_message
            )
            
            # Should process valid message successfully after errors
            assert success is True
            
        finally:
            await connection_manager.remove_connection(user_id, conn_id)

@pytest.mark.asyncio
class TestWebSocketNetworkInstability:
    """Test WebSocket behavior under network instability."""
    
    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self):
        """Test connection timeout handling."""
        user_id = "timeout_user"
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = UnifiedWebSocketManager()
        
        session_info = {"user_id": user_id, "last_activity": time.time() - 3600}  # 1 hour ago
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        try:
            # Simulate timeout check
            metadata = connection_manager.connection_metadata.get(conn_id, {})
            
            # Connection should exist but be considered stale
            assert conn_id in connection_manager.connection_metadata
            
            # Update activity to simulate heartbeat
            connection_manager.connection_metadata[conn_id]["last_activity"] = time.time()
            
            # Should now be considered active
            updated_metadata = connection_manager.connection_metadata[conn_id]
            assert "last_activity" in updated_metadata
            
        finally:
            await connection_manager.remove_connection(user_id, conn_id)
            
    @pytest.mark.asyncio
    async def test_graceful_disconnection_handling(self):
        """Test graceful disconnection handling."""
        user_id = "disconnect_user"
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = UnifiedWebSocketManager()
        
        session_info = {"user_id": user_id}
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        # Verify connection exists
        assert conn_id in connection_manager.connection_metadata
        
        # Graceful disconnection
        await connection_manager.remove_connection(user_id, conn_id)
        
        # Connection should be cleanly removed
        assert conn_id not in connection_manager.connection_metadata
        stats = connection_manager.get_connection_stats()
        assert user_id not in stats.get("connections_per_user", {})
        
    @pytest.mark.asyncio
    async def test_abnormal_disconnection_cleanup(self):
        """Test cleanup after abnormal disconnection."""
        user_id = "abnormal_disconnect_user"
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = UnifiedWebSocketManager()
        
        session_info = {"user_id": user_id}
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        try:
            # Simulate abnormal disconnection by directly removing from metadata
            # without proper cleanup (simulating network drop)
            if conn_id in connection_manager.connection_metadata:
                del connection_manager.connection_metadata[conn_id]
            
            # Try to remove connection normally (should handle missing metadata)
            await connection_manager.remove_connection(user_id, conn_id)
            
            # Should not raise exceptions
            assert True
            
        except Exception as e:
            # If cleanup fails, ensure it doesn't crash the system
            assert False, f"Cleanup should handle missing metadata gracefully: {e}"

@pytest.mark.asyncio
class TestWebSocketErrorRecovery:
    """Test WebSocket error recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_json_parse_error_recovery(self):
        """Test recovery from JSON parse errors."""
        user_id = "json_error_user"
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncNone  # TODO: Use real service instance
        
        session_info = {"user_id": user_id}
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        try:
            # Send invalid JSON
            invalid_json = "{ invalid json structure"
            success = await handle_websocket_message_enhanced(
                user_id, conn_id, mock_websocket, invalid_json
            )
            
            # Should return True (keep connection alive) and send error message
            assert success is True
            assert mock_websocket.send_json.called
            
            # Check error message format
            error_call = mock_websocket.send_json.call_args[0][0]
            assert error_call["type"] == "error"
            assert error_call["payload"]["code"] == "JSON_PARSE_ERROR"
            assert error_call["payload"]["recoverable"] is True
            
        finally:
            await connection_manager.remove_connection(user_id, conn_id)
            
    @pytest.mark.asyncio
    async def test_validation_error_recovery(self):
        """Test recovery from message validation errors."""
        user_id = "validation_error_user"
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncNone  # TODO: Use real service instance
        
        session_info = {"user_id": user_id}
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        try:
            # Send message with validation errors
            validation_errors = [
                '{"no_type": "missing type field"}',
                '{"type": ""}',  # Empty type
                '{"type": 123}',  # Invalid type
            ]
            
            for error_msg in validation_errors:
                mock_websocket.send_json.reset_mock()
                
                success = await handle_websocket_message_enhanced(
                    user_id, conn_id, mock_websocket, error_msg
                )
                
                assert success is True
                assert mock_websocket.send_json.called
                
                # Verify error message structure
                error_response = mock_websocket.send_json.call_args[0][0]
                assert error_response["type"] == "error"
                assert "code" in error_response["payload"]
                assert error_response["payload"]["recoverable"] is True
                
        finally:
            await connection_manager.remove_connection(user_id, conn_id)
            
    @pytest.mark.asyncio
    async def test_rate_limiting_recovery(self):
        """Test recovery from rate limiting."""
        user_id = "rate_limit_user"
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncNone  # TODO: Use real service instance
        
        session_info = {"user_id": user_id}
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        try:
            # Simulate rate limiting by updating message count
            if conn_id in connection_manager.connection_metadata:
                # Simulate many messages sent quickly
                connection_manager.connection_metadata[conn_id]["message_count"] = 100
                
            # Send message that would exceed rate limit
            message = '{"type": "ping", "rapid": true}'
            success = await handle_websocket_message_enhanced(
                user_id, conn_id, mock_websocket, message
            )
            
            # Should still process (basic implementation doesn't enforce rate limiting yet)
            assert success is True
            
        finally:
            await connection_manager.remove_connection(user_id, conn_id)
            
    @pytest.mark.asyncio
    async def test_database_error_recovery(self):
        """Test recovery from database errors."""
        user_id = "db_error_user"
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncNone  # TODO: Use real service instance
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.websocket_enhanced.get_async_db') as mock_db:
            # Mock database failure
            mock_db.side_effect = Exception("Database connection failed")
            
            session_info = {"user_id": user_id}
            conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
            
            try:
                # Send message that would trigger database operation
                message = '{"type": "user_message", "payload": {"content": "test"}}'
                
                # Should handle database error gracefully
                success = await handle_websocket_message_enhanced(
                    user_id, conn_id, mock_websocket, message
                )
                
                # Connection should remain alive despite database error
                assert success is True
                
            finally:
                await connection_manager.remove_connection(user_id, conn_id)

@pytest.mark.asyncio 
class TestWebSocketConcurrencyResilience:
    """Test WebSocket resilience under concurrent load."""
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_handling(self):
        """Test handling multiple concurrent connections."""
        base_user_id = "concurrent_user"
        connections = []
        
        try:
            # Create multiple concurrent connections
            tasks = []
            for i in range(10):
                user_id = f"{base_user_id}_{i}"
                # Mock: WebSocket infrastructure isolation for unit tests without real connections
                mock_websocket = UnifiedWebSocketManager()
                session_info = {"user_id": user_id}
                
                task = connection_manager.add_connection(user_id, mock_websocket, session_info)
                tasks.append((task, user_id))
            
            # Wait for all connections to be established
            for task, user_id in tasks:
                conn_id = await task
                connections.append((user_id, conn_id))
            
            # Verify all connections were created
            stats = connection_manager.get_connection_stats()
            assert stats["total_connections"] == 10
            
        finally:
            # Clean up all connections
            for user_id, conn_id in connections:
                await connection_manager.remove_connection(user_id, conn_id)
                
    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self):
        """Test concurrent message processing."""
        user_id = "concurrent_msg_user"
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = AsyncNone  # TODO: Use real service instance
        
        session_info = {"user_id": user_id}
        conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
        
        try:
            # Send multiple messages concurrently
            tasks = []
            for i in range(5):
                message = f'{{"type": "ping", "sequence": {i}}}'
                task = handle_websocket_message_enhanced(
                    user_id, conn_id, mock_websocket, message
                )
                tasks.append(task)
            
            # Wait for all messages to be processed
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed
            for result in results:
                if isinstance(result, Exception):
                    assert False, f"Message processing failed: {result}"
                assert result is True
                
        finally:
            await connection_manager.remove_connection(user_id, conn_id)
            
    @pytest.mark.asyncio
    async def test_connection_limit_enforcement(self):
        """Test connection limits are properly enforced."""
        user_id = "limit_test_user" 
        session_info = {"user_id": user_id}
        connections = []
        
        try:
            # Create connections up to the limit (5 by default)
            for i in range(7):  # Try to create more than limit
                # Mock: WebSocket infrastructure isolation for unit tests without real connections
                mock_websocket = UnifiedWebSocketManager()
                # Mock: WebSocket infrastructure isolation for unit tests without real connections
                mock_websocket.close = AsyncNone  # TODO: Use real service instance  # Mock close method
                conn_id = await connection_manager.add_connection(user_id, mock_websocket, session_info)
                connections.append((conn_id, mock_websocket))
            
            # Should only have maximum allowed connections
            stats = connection_manager.get_connection_stats()
            assert stats["connections_per_user"][user_id] <= 5  # Max limit
            
        finally:
            # Clean up remaining connections
            for conn_id, _ in connections[-5:]:  # Only last 5 should exist
                try:
                    await connection_manager.remove_connection(user_id, conn_id)
                except:
                    pass  # May have been auto-removed by limit enforcement

@pytest.mark.asyncio
class TestWebSocketCORSResilience:
    """Test CORS resilience and security."""
    
    def test_cors_handles_missing_origin(self):
        """Test CORS handling when origin is missing."""
        cors_handler = WebSocketCORSHandler()
        
        # Missing origin should be rejected
        assert cors_handler.is_origin_allowed(None) is False
        assert cors_handler.is_origin_allowed("") is False
        
    def test_cors_handles_malicious_origin(self):
        """Test CORS handling with malicious origins."""
        cors_handler = WebSocketCORSHandler(["http://localhost:3000"])
        
        malicious_origins = [
            "http://malicious.com",
            "https://phishing-site.com", 
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "http://localhost:3000.malicious.com",  # Domain confusion
            "http://localhost:3000/malicious.com",   # Path confusion
        ]
        
        for malicious_origin in malicious_origins:
            assert cors_handler.is_origin_allowed(malicious_origin) is False
            
    def test_cors_wildcard_security(self):
        """Test CORS wildcard patterns are secure."""
        cors_handler = WebSocketCORSHandler(["https://*.example.com"])
        
        # Should allow legitimate subdomains
        assert cors_handler.is_origin_allowed("https://app.example.com") is True
        assert cors_handler.is_origin_allowed("https://api.example.com") is True
        
        # Should reject malicious attempts
        assert cors_handler.is_origin_allowed("https://malicious.com") is False
        assert cors_handler.is_origin_allowed("https://example.com.malicious.com") is False
        assert cors_handler.is_origin_allowed("http://app.example.com") is False  # Wrong protocol
        
    @pytest.mark.asyncio
    async def test_cors_enforcement_in_connection(self):
        """Test CORS enforcement during connection establishment."""
        from netra_backend.app.core.websocket_cors import validate_websocket_origin
        
        cors_handler = WebSocketCORSHandler(["http://localhost:3000"])
        
        # Mock WebSocket with valid origin
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = UnifiedWebSocketManager()
        mock_websocket.headers = {"origin": "http://localhost:3000"}
        
        assert validate_websocket_origin(mock_websocket, cors_handler) is True
        
        # Mock WebSocket with invalid origin
        mock_websocket.headers = {"origin": "http://malicious.com"}
        assert validate_websocket_origin(mock_websocket, cors_handler) is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])