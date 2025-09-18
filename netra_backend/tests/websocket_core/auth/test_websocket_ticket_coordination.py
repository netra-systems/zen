"""
Unit Tests for WebSocket Ticket Coordination - Issue #1313

Test suite for the race condition prevention system that coordinates WebSocket 
handshake authentication to eliminate 1011 errors in Cloud Run environments.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

# Import test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import the modules under test
from netra_backend.app.websocket_core.auth.websocket_ticket import (
    WebSocketTicketCoordinator,
    WebSocketHandshakeState,
    websocket_ticket_coordinator,
    prepare_websocket_auth,
    get_prepared_auth_context,
    mark_handshake_completed,
    cleanup_connection,
    get_websocket_ticket_coordinator
)


class TestWebSocketHandshakeState(SSotAsyncTestCase):
    """Test WebSocket handshake state tracking."""
    
    def test_handshake_state_creation(self):
        """Test creation of handshake state."""
        connection_id = "test-connection-123"
        state = WebSocketHandshakeState(
            connection_id=connection_id,
            handshake_started=time.time()
        )
        
        assert state.connection_id == connection_id
        assert not state.auth_verified
        assert state.ticket_id is None
        assert state.user_context is None
        assert not state.handshake_completed
        
    def test_handshake_state_expiration(self):
        """Test handshake state expiration logic."""
        # Create expired state
        expired_state = WebSocketHandshakeState(
            connection_id="expired-connection",
            handshake_started=time.time() - 60  # 60 seconds ago
        )
        
        # Create fresh state
        fresh_state = WebSocketHandshakeState(
            connection_id="fresh-connection", 
            handshake_started=time.time()
        )
        
        # Test expiration (default 30 second timeout)
        assert expired_state.is_expired()
        assert not fresh_state.is_expired()
        
        # Test custom timeout
        assert not expired_state.is_expired(timeout_seconds=120)


class TestWebSocketTicketCoordinator(SSotAsyncTestCase):
    """Test WebSocket ticket coordination for race condition prevention."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.coordinator = WebSocketTicketCoordinator()
        self.test_connection_id = "test-connection-456"
        self.test_ticket_id = "test-ticket-789"
        self.test_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"
        
    async def test_prepare_websocket_authentication_with_ticket(self):
        """Test authentication preparation with valid ticket."""
        # Mock the ticket manager
        mock_ticket = MagicMock()
        mock_ticket.user_id = "user123"
        mock_ticket.email = "user@example.com"
        mock_ticket.permissions = ["read", "chat", "websocket"]
        mock_ticket.metadata = {"source": "test"}
        
        with patch.object(self.coordinator._ticket_manager, 'validate_ticket', 
                         new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = mock_ticket
            
            success, user_context = await self.coordinator.prepare_websocket_authentication(
                connection_id=self.test_connection_id,
                ticket_id=self.test_ticket_id
            )
            
            assert success is True
            assert user_context is not None
            assert user_context["user_id"] == "user123"
            assert user_context["email"] == "user@example.com"
            assert user_context["auth_method"] == "ticket-fast-path"
            assert user_context["ticket_id"] == self.test_ticket_id
            
            # Verify handshake state was created
            handshake_state = self.coordinator._handshake_states.get(self.test_connection_id)
            assert handshake_state is not None
            assert handshake_state.auth_verified is True
            assert handshake_state.ticket_id == self.test_ticket_id
            
    async def test_prepare_websocket_authentication_with_jwt_fallback(self):
        """Test authentication preparation with JWT fallback."""
        mock_validation_result = {
            'valid': True,
            'user_id': 'jwt-user456',
            'email': 'jwt@example.com',
            'permissions': ['read', 'write']
        }
        
        with patch('netra_backend.app.websocket_core.auth.websocket_ticket.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation_result)
            
            success, user_context = await self.coordinator.prepare_websocket_authentication(
                connection_id=self.test_connection_id,
                jwt_token=self.test_jwt_token
            )
            
            assert success is True
            assert user_context is not None
            assert user_context["user_id"] == "jwt-user456"
            assert user_context["email"] == "jwt@example.com"
            assert user_context["auth_method"] == "jwt-fallback"
            
    async def test_prepare_websocket_authentication_failure(self):
        """Test authentication preparation failure handling."""
        # Mock ticket validation failure
        with patch.object(self.coordinator._ticket_manager, 'validate_ticket',
                         new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = None  # Ticket not found/expired
            
            success, user_context = await self.coordinator.prepare_websocket_authentication(
                connection_id=self.test_connection_id,
                ticket_id="invalid-ticket"
            )
            
            assert success is False
            assert user_context is None
            
    async def test_get_prepared_auth_context_success(self):
        """Test retrieval of prepared authentication context."""
        # First prepare authentication
        mock_ticket = MagicMock()
        mock_ticket.user_id = "user789"
        mock_ticket.email = "user789@example.com"
        mock_ticket.permissions = ["read", "chat"]
        mock_ticket.metadata = {}
        
        with patch.object(self.coordinator._ticket_manager, 'validate_ticket',
                         new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = mock_ticket
            
            # Prepare authentication
            success, _ = await self.coordinator.prepare_websocket_authentication(
                connection_id=self.test_connection_id,
                ticket_id=self.test_ticket_id
            )
            assert success is True
            
            # Retrieve prepared context
            user_context = await self.coordinator.get_prepared_auth_context(self.test_connection_id)
            
            assert user_context is not None
            assert user_context["user_id"] == "user789"
            assert user_context["auth_method"] == "ticket-fast-path"
            
    async def test_get_prepared_auth_context_not_found(self):
        """Test retrieval of non-existent authentication context."""
        user_context = await self.coordinator.get_prepared_auth_context("non-existent-connection")
        assert user_context is None
        
    async def test_get_prepared_auth_context_expired(self):
        """Test retrieval of expired authentication context."""
        # Create expired handshake state directly
        expired_state = WebSocketHandshakeState(
            connection_id=self.test_connection_id,
            handshake_started=time.time() - 60,  # 60 seconds ago
            auth_verified=True,
            user_context={"user_id": "expired-user"}
        )
        self.coordinator._handshake_states[self.test_connection_id] = expired_state
        
        # Should return None and cleanup expired state
        user_context = await self.coordinator.get_prepared_auth_context(self.test_connection_id)
        assert user_context is None
        assert self.test_connection_id not in self.coordinator._handshake_states
        
    async def test_mark_handshake_completed_success(self):
        """Test marking handshake as completed."""
        # Create handshake state
        state = WebSocketHandshakeState(
            connection_id=self.test_connection_id,
            handshake_started=time.time(),
            auth_verified=True
        )
        self.coordinator._handshake_states[self.test_connection_id] = state
        
        # Mark as completed
        result = await self.coordinator.mark_handshake_completed(self.test_connection_id)
        assert result is True
        assert state.handshake_completed is True
        
    async def test_mark_handshake_completed_not_found(self):
        """Test marking non-existent handshake as completed."""
        result = await self.coordinator.mark_handshake_completed("non-existent-connection")
        assert result is False
        
    async def test_cleanup_connection(self):
        """Test connection cleanup."""
        # Create handshake state
        state = WebSocketHandshakeState(
            connection_id=self.test_connection_id,
            handshake_started=time.time()
        )
        self.coordinator._handshake_states[self.test_connection_id] = state
        
        # Cleanup connection
        await self.coordinator.cleanup_connection(self.test_connection_id)
        assert self.test_connection_id not in self.coordinator._handshake_states
        
    async def test_get_handshake_statistics(self):
        """Test handshake statistics generation."""
        # Create multiple handshake states
        state1 = WebSocketHandshakeState(
            connection_id="conn1",
            handshake_started=time.time(),
            auth_verified=True,
            ticket_id="ticket1",
            handshake_completed=True
        )
        
        state2 = WebSocketHandshakeState(
            connection_id="conn2", 
            handshake_started=time.time() - 60,  # Expired
            auth_verified=True
        )
        
        state3 = WebSocketHandshakeState(
            connection_id="conn3",
            handshake_started=time.time(),
            auth_verified=False
        )
        
        self.coordinator._handshake_states.update({
            "conn1": state1,
            "conn2": state2,
            "conn3": state3
        })
        
        stats = await self.coordinator.get_handshake_statistics()
        
        assert stats["active_handshakes"] == 3
        assert stats["completed_handshakes"] == 1
        assert stats["expired_handshakes"] == 1
        assert stats["ticket_auth_count"] == 1
        assert stats["jwt_auth_count"] == 2
        assert stats["coordination_enabled"] is True
        assert "timestamp" in stats
        
    async def test_cleanup_expired_handshakes(self):
        """Test cleanup of expired handshake states."""
        # Create expired and fresh states
        expired_state = WebSocketHandshakeState(
            connection_id="expired-conn",
            handshake_started=time.time() - 60
        )
        
        fresh_state = WebSocketHandshakeState(
            connection_id="fresh-conn",
            handshake_started=time.time()
        )
        
        self.coordinator._handshake_states.update({
            "expired-conn": expired_state,
            "fresh-conn": fresh_state
        })
        
        cleaned_count = await self.coordinator.cleanup_expired_handshakes()
        
        assert cleaned_count == 1
        assert "expired-conn" not in self.coordinator._handshake_states
        assert "fresh-conn" in self.coordinator._handshake_states


class TestWebSocketTicketSSotFunctions(SSotAsyncTestCase):
    """Test SSOT functions for WebSocket ticket coordination."""
    
    async def test_prepare_websocket_auth_function(self):
        """Test SSOT prepare_websocket_auth function."""
        test_connection_id = "test-conn-func"
        test_ticket_id = "test-ticket-func"
        
        # Mock successful ticket validation
        mock_ticket = MagicMock()
        mock_ticket.user_id = "func-user"
        mock_ticket.email = "func@example.com"
        mock_ticket.permissions = ["read"]
        mock_ticket.metadata = {}
        
        with patch.object(websocket_ticket_coordinator._ticket_manager, 'validate_ticket',
                         new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = mock_ticket
            
            success, user_context = await prepare_websocket_auth(
                connection_id=test_connection_id,
                ticket_id=test_ticket_id
            )
            
            assert success is True
            assert user_context["user_id"] == "func-user"
            
    async def test_get_prepared_auth_context_function(self):
        """Test SSOT get_prepared_auth_context function."""
        test_connection_id = "test-conn-get"
        
        # Prepare context first
        mock_ticket = MagicMock()
        mock_ticket.user_id = "get-user"
        mock_ticket.email = "get@example.com"
        mock_ticket.permissions = ["read"]
        mock_ticket.metadata = {}
        
        with patch.object(websocket_ticket_coordinator._ticket_manager, 'validate_ticket',
                         new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = mock_ticket
            
            await prepare_websocket_auth(
                connection_id=test_connection_id,
                ticket_id="test-ticket"
            )
            
            # Get prepared context
            user_context = await get_prepared_auth_context(test_connection_id)
            assert user_context is not None
            assert user_context["user_id"] == "get-user"
            
    async def test_mark_handshake_completed_function(self):
        """Test SSOT mark_handshake_completed function."""
        test_connection_id = "test-conn-mark"
        
        # Create handshake state directly
        state = WebSocketHandshakeState(
            connection_id=test_connection_id,
            handshake_started=time.time(),
            auth_verified=True
        )
        websocket_ticket_coordinator._handshake_states[test_connection_id] = state
        
        result = await mark_handshake_completed(test_connection_id)
        assert result is True
        assert state.handshake_completed is True
        
    async def test_cleanup_connection_function(self):
        """Test SSOT cleanup_connection function."""
        test_connection_id = "test-conn-cleanup"
        
        # Create handshake state
        state = WebSocketHandshakeState(
            connection_id=test_connection_id,
            handshake_started=time.time()
        )
        websocket_ticket_coordinator._handshake_states[test_connection_id] = state
        
        await cleanup_connection(test_connection_id)
        assert test_connection_id not in websocket_ticket_coordinator._handshake_states
        
    def test_get_websocket_ticket_coordinator_function(self):
        """Test SSOT get_websocket_ticket_coordinator function."""
        coordinator = get_websocket_ticket_coordinator()
        assert coordinator is websocket_ticket_coordinator
        assert isinstance(coordinator, WebSocketTicketCoordinator)


class TestRaceConditionPrevention(SSotAsyncTestCase):
    """Test race condition prevention scenarios."""
    
    async def test_concurrent_authentication_preparation(self):
        """Test concurrent authentication preparation doesn't cause race conditions."""
        coordinator = WebSocketTicketCoordinator()
        
        # Create multiple concurrent authentication preparations
        tasks = []
        for i in range(10):
            connection_id = f"concurrent-conn-{i}"
            ticket_id = f"ticket-{i}"
            
            # Mock ticket validation
            mock_ticket = MagicMock()
            mock_ticket.user_id = f"user{i}"
            mock_ticket.email = f"user{i}@example.com"
            mock_ticket.permissions = ["read"]
            mock_ticket.metadata = {}
            
            with patch.object(coordinator._ticket_manager, 'validate_ticket',
                             new_callable=AsyncMock) as mock_validate:
                mock_validate.return_value = mock_ticket
                
                task = coordinator.prepare_websocket_authentication(
                    connection_id=connection_id,
                    ticket_id=ticket_id
                )
                tasks.append((task, connection_id, f"user{i}"))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*[task for task, _, _ in tasks], return_exceptions=True)
        
        # Verify all succeeded
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Task {i} failed: {result}"
            success, user_context = result
            assert success is True
            
        # Verify all handshake states were created correctly
        assert len(coordinator._handshake_states) == 10
        
    async def test_handshake_timing_coordination(self):
        """Test that handshake timing is properly coordinated."""
        coordinator = WebSocketTicketCoordinator()
        connection_id = "timing-test-conn"
        
        # Mock successful ticket validation
        mock_ticket = MagicMock()
        mock_ticket.user_id = "timing-user"
        mock_ticket.email = "timing@example.com"
        mock_ticket.permissions = ["read", "chat"]
        mock_ticket.metadata = {}
        
        with patch.object(coordinator._ticket_manager, 'validate_ticket',
                         new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = mock_ticket
            
            # Step 1: Prepare authentication (should happen BEFORE handshake)
            prep_start = time.time()
            success, user_context = await coordinator.prepare_websocket_authentication(
                connection_id=connection_id,
                ticket_id="timing-ticket"
            )
            prep_duration = time.time() - prep_start
            
            assert success is True
            assert prep_duration < 1.0  # Should be fast
            
            # Step 2: Get prepared context (should be instant)
            get_start = time.time()
            retrieved_context = await coordinator.get_prepared_auth_context(connection_id)
            get_duration = time.time() - get_start
            
            assert retrieved_context is not None
            assert retrieved_context["user_id"] == "timing-user"
            assert get_duration < 0.1  # Should be very fast (no auth validation)
            
            # Step 3: Mark handshake completed
            await coordinator.mark_handshake_completed(connection_id)
            
            # Verify the timing sequence worked correctly
            handshake_state = coordinator._handshake_states[connection_id]
            assert handshake_state.auth_verified is True
            assert handshake_state.handshake_completed is True


if __name__ == "__main__":
    pytest.main([__file__])