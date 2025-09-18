"""
Unit tests for AuthTicketManager functionality (Issue #1293)

Tests the ticket-based authentication system for secure temporary access
without exposing long-lived credentials.

Business Value: Enables CI/CD automation and webhook authentication
while maintaining security best practices.
"""

import asyncio
import json
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.websocket_core.unified_auth_ssot import (
    AuthTicket,
    AuthTicketManager,
    generate_auth_ticket,
    validate_auth_ticket,
    revoke_auth_ticket,
    cleanup_expired_tickets,
    get_ticket_manager
)


class TestAuthTicketManager:
    """Test suite for AuthTicketManager core functionality."""

    @pytest.fixture
    def mock_redis_manager(self):
        """Mock Redis manager for isolated testing."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.delete = AsyncMock(return_value=True)
        mock_redis.keys = AsyncMock(return_value=[])
        return mock_redis

    @pytest.fixture
    def ticket_manager(self, mock_redis_manager):
        """Create ticket manager with mocked Redis."""
        manager = AuthTicketManager()
        manager._redis_manager = mock_redis_manager
        return manager

    @pytest.fixture
    def sample_ticket_data(self):
        """Sample ticket data for testing."""
        return {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'permissions': ['read', 'chat', 'websocket'],
            'ttl_seconds': 300,
            'single_use': True,
            'metadata': {'source': 'test_suite'}
        }

    @pytest.mark.asyncio
    async def test_generate_ticket_success(self, ticket_manager, mock_redis_manager, sample_ticket_data):
        """Test successful ticket generation."""
        # Arrange
        mock_redis_manager.set.return_value = True

        # Act
        ticket = await ticket_manager.generate_ticket(**sample_ticket_data)

        # Assert
        assert isinstance(ticket, AuthTicket)
        assert ticket.user_id == sample_ticket_data['user_id']
        assert ticket.email == sample_ticket_data['email']
        assert ticket.permissions == sample_ticket_data['permissions']
        assert ticket.single_use == sample_ticket_data['single_use']
        assert ticket.metadata == sample_ticket_data['metadata']
        assert ticket.ticket_id is not None
        assert len(ticket.ticket_id) > 0
        assert ticket.expires_at > time.time()
        assert ticket.created_at <= time.time()

        # Verify Redis storage was called
        mock_redis_manager.set.assert_called_once()
        call_args = mock_redis_manager.set.call_args
        assert call_args[0][0].startswith('auth:ticket:')  # Key prefix
        assert call_args[1]['ex'] == 300  # TTL

    @pytest.mark.asyncio
    async def test_generate_ticket_missing_required_fields(self, ticket_manager):
        """Test ticket generation with missing required fields."""
        # Test missing user_id
        with pytest.raises(ValueError, match="user_id and email are required"):
            await ticket_manager.generate_ticket(user_id="", email="test@example.com")

        # Test missing email
        with pytest.raises(ValueError, match="user_id and email are required"):
            await ticket_manager.generate_ticket(user_id="test_user", email="")

    @pytest.mark.asyncio
    async def test_generate_ticket_redis_failure(self, ticket_manager, mock_redis_manager, sample_ticket_data):
        """Test ticket generation when Redis storage fails."""
        # Arrange
        mock_redis_manager.set.return_value = False

        # Act & Assert
        with pytest.raises(RuntimeError, match="Failed to store authentication ticket"):
            await ticket_manager.generate_ticket(**sample_ticket_data)

    @pytest.mark.asyncio
    async def test_validate_ticket_success(self, ticket_manager, mock_redis_manager):
        """Test successful ticket validation."""
        # Arrange
        ticket_id = "test_ticket_123"
        current_time = time.time()
        ticket_data = {
            'ticket_id': ticket_id,
            'user_id': 'test_user',
            'email': 'test@example.com',
            'permissions': ['read', 'chat'],
            'expires_at': current_time + 300,  # Valid for 5 minutes
            'created_at': current_time,
            'single_use': True,
            'metadata': {}
        }
        mock_redis_manager.get.return_value = json.dumps(ticket_data)
        mock_redis_manager.delete.return_value = True

        # Act
        ticket = await ticket_manager.validate_ticket(ticket_id)

        # Assert
        assert ticket is not None
        assert isinstance(ticket, AuthTicket)
        assert ticket.ticket_id == ticket_id
        assert ticket.user_id == 'test_user'
        assert ticket.email == 'test@example.com'
        assert ticket.permissions == ['read', 'chat']

        # Verify single-use ticket was deleted
        mock_redis_manager.delete.assert_called_once_with(f"auth:ticket:{ticket_id}")

    @pytest.mark.asyncio
    async def test_validate_ticket_not_found(self, ticket_manager, mock_redis_manager):
        """Test validation of non-existent ticket."""
        # Arrange
        mock_redis_manager.get.return_value = None

        # Act
        ticket = await ticket_manager.validate_ticket("non_existent_ticket")

        # Assert
        assert ticket is None

    @pytest.mark.asyncio
    async def test_validate_ticket_expired(self, ticket_manager, mock_redis_manager):
        """Test validation of expired ticket."""
        # Arrange
        ticket_id = "expired_ticket"
        current_time = time.time()
        ticket_data = {
            'ticket_id': ticket_id,
            'user_id': 'test_user',
            'email': 'test@example.com',
            'permissions': ['read'],
            'expires_at': current_time - 60,  # Expired 1 minute ago
            'created_at': current_time - 360,
            'single_use': True,
            'metadata': {}
        }
        mock_redis_manager.get.return_value = json.dumps(ticket_data)
        mock_redis_manager.delete.return_value = True

        # Act
        ticket = await ticket_manager.validate_ticket(ticket_id)

        # Assert
        assert ticket is None
        # Verify expired ticket was cleaned up
        mock_redis_manager.delete.assert_called_once_with(f"auth:ticket:{ticket_id}")

    @pytest.mark.asyncio
    async def test_validate_ticket_reusable(self, ticket_manager, mock_redis_manager):
        """Test validation of reusable (non-single-use) ticket."""
        # Arrange
        ticket_id = "reusable_ticket"
        current_time = time.time()
        ticket_data = {
            'ticket_id': ticket_id,
            'user_id': 'test_user',
            'email': 'test@example.com',
            'permissions': ['read'],
            'expires_at': current_time + 300,
            'created_at': current_time,
            'single_use': False,  # Reusable ticket
            'metadata': {}
        }
        mock_redis_manager.get.return_value = json.dumps(ticket_data)

        # Act
        ticket = await ticket_manager.validate_ticket(ticket_id)

        # Assert
        assert ticket is not None
        assert ticket.single_use is False
        # Verify ticket was NOT deleted (reusable)
        mock_redis_manager.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_revoke_ticket_success(self, ticket_manager, mock_redis_manager):
        """Test successful ticket revocation."""
        # Arrange
        ticket_id = "ticket_to_revoke"
        mock_redis_manager.delete.return_value = True

        # Act
        result = await ticket_manager.revoke_ticket(ticket_id)

        # Assert
        assert result is True
        mock_redis_manager.delete.assert_called_once_with(f"auth:ticket:{ticket_id}")

    @pytest.mark.asyncio
    async def test_revoke_ticket_not_found(self, ticket_manager, mock_redis_manager):
        """Test revocation of non-existent ticket."""
        # Arrange
        mock_redis_manager.delete.return_value = False

        # Act
        result = await ticket_manager.revoke_ticket("non_existent_ticket")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_tickets(self, ticket_manager, mock_redis_manager):
        """Test cleanup of expired tickets."""
        # Arrange
        current_time = time.time()

        # Mock keys and data
        mock_redis_manager.keys.return_value = [
            'auth:ticket:valid_ticket',
            'auth:ticket:expired_ticket_1',
            'auth:ticket:expired_ticket_2'
        ]

        valid_ticket_data = {
            'expires_at': current_time + 300  # Valid
        }
        expired_ticket_data_1 = {
            'expires_at': current_time - 60  # Expired
        }
        expired_ticket_data_2 = {
            'expires_at': current_time - 120  # Expired
        }

        # Mock get calls for each key
        mock_redis_manager.get.side_effect = [
            json.dumps(valid_ticket_data),
            json.dumps(expired_ticket_data_1),
            json.dumps(expired_ticket_data_2)
        ]
        mock_redis_manager.delete.return_value = True

        # Act
        cleaned_count = await ticket_manager.cleanup_expired_tickets()

        # Assert
        assert cleaned_count == 2  # Two expired tickets cleaned
        # Verify delete was called for expired tickets only
        assert mock_redis_manager.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_ttl_enforcement(self, ticket_manager, mock_redis_manager, sample_ticket_data):
        """Test TTL enforcement (max 1 hour)."""
        # Arrange
        sample_ticket_data['ttl_seconds'] = 7200  # Try to set 2 hours
        mock_redis_manager.set.return_value = True

        # Act
        ticket = await ticket_manager.generate_ticket(**sample_ticket_data)

        # Assert
        # Should be capped at 1 hour (3600 seconds)
        expected_max_expires_at = time.time() + 3600
        assert ticket.expires_at <= expected_max_expires_at + 5  # 5 second tolerance

    @pytest.mark.asyncio
    async def test_secure_ticket_id_generation(self, ticket_manager, mock_redis_manager, sample_ticket_data):
        """Test that ticket IDs are cryptographically secure and unique."""
        # Arrange
        mock_redis_manager.set.return_value = True

        # Act - Generate multiple tickets
        tickets = []
        for i in range(10):
            sample_ticket_data['user_id'] = f'user_{i}'
            ticket = await ticket_manager.generate_ticket(**sample_ticket_data)
            tickets.append(ticket)

        # Assert
        ticket_ids = [t.ticket_id for t in tickets]

        # All ticket IDs should be unique
        assert len(set(ticket_ids)) == len(ticket_ids)

        # All ticket IDs should be non-empty and reasonably long (secure)
        for ticket_id in ticket_ids:
            assert len(ticket_id) >= 32  # URL-safe base64 with 256-bit entropy


class TestTicketAuthenticationAPI:
    """Test suite for module-level ticket authentication API functions."""

    @pytest.fixture
    def mock_ticket_manager(self):
        """Mock the global ticket manager."""
        return AsyncMock()

    @patch('netra_backend.app.websocket_core.unified_auth_ssot.ticket_manager')
    @pytest.mark.asyncio
    async def test_generate_auth_ticket_api(self, mock_ticket_manager):
        """Test the generate_auth_ticket API function."""
        # Arrange
        expected_ticket = AuthTicket(
            ticket_id="test_ticket",
            user_id="test_user",
            email="test@example.com",
            permissions=["read", "chat"],
            expires_at=time.time() + 300,
            created_at=time.time(),
            single_use=True,
            metadata={}
        )
        mock_ticket_manager.generate_ticket.return_value = expected_ticket

        # Act
        result = await generate_auth_ticket(
            user_id="test_user",
            email="test@example.com",
            permissions=["read", "chat"]
        )

        # Assert
        assert result == expected_ticket
        mock_ticket_manager.generate_ticket.assert_called_once_with(
            user_id="test_user",
            email="test@example.com",
            permissions=["read", "chat"],
            ttl_seconds=None,
            single_use=True,
            metadata=None
        )

    @patch('netra_backend.app.websocket_core.unified_auth_ssot.ticket_manager')
    @pytest.mark.asyncio
    async def test_validate_auth_ticket_api(self, mock_ticket_manager):
        """Test the validate_auth_ticket API function."""
        # Arrange
        ticket_id = "test_ticket_123"
        expected_ticket = AuthTicket(
            ticket_id=ticket_id,
            user_id="test_user",
            email="test@example.com",
            permissions=["read"],
            expires_at=time.time() + 300,
            created_at=time.time(),
            single_use=True,
            metadata={}
        )
        mock_ticket_manager.validate_ticket.return_value = expected_ticket

        # Act
        result = await validate_auth_ticket(ticket_id)

        # Assert
        assert result == expected_ticket
        mock_ticket_manager.validate_ticket.assert_called_once_with(ticket_id)

    @patch('netra_backend.app.websocket_core.unified_auth_ssot.ticket_manager')
    @pytest.mark.asyncio
    async def test_revoke_auth_ticket_api(self, mock_ticket_manager):
        """Test the revoke_auth_ticket API function."""
        # Arrange
        ticket_id = "ticket_to_revoke"
        mock_ticket_manager.revoke_ticket.return_value = True

        # Act
        result = await revoke_auth_ticket(ticket_id)

        # Assert
        assert result is True
        mock_ticket_manager.revoke_ticket.assert_called_once_with(ticket_id)

    @patch('netra_backend.app.websocket_core.unified_auth_ssot.ticket_manager')
    @pytest.mark.asyncio
    async def test_cleanup_expired_tickets_api(self, mock_ticket_manager):
        """Test the cleanup_expired_tickets API function."""
        # Arrange
        mock_ticket_manager.cleanup_expired_tickets.return_value = 5

        # Act
        result = await cleanup_expired_tickets()

        # Assert
        assert result == 5
        mock_ticket_manager.cleanup_expired_tickets.assert_called_once()

    def test_get_ticket_manager_api(self):
        """Test the get_ticket_manager API function."""
        # Act
        result = get_ticket_manager()

        # Assert
        assert isinstance(result, AuthTicketManager)


class TestAuthTicketDataClass:
    """Test suite for AuthTicket dataclass."""

    def test_auth_ticket_creation(self):
        """Test AuthTicket creation with all fields."""
        # Arrange
        current_time = time.time()
        ticket_data = {
            'ticket_id': 'test_ticket_123',
            'user_id': 'test_user',
            'email': 'test@example.com',
            'permissions': ['read', 'write', 'chat'],
            'expires_at': current_time + 300,
            'created_at': current_time,
            'single_use': True,
            'metadata': {'source': 'unit_test'}
        }

        # Act
        ticket = AuthTicket(**ticket_data)

        # Assert
        assert ticket.ticket_id == 'test_ticket_123'
        assert ticket.user_id == 'test_user'
        assert ticket.email == 'test@example.com'
        assert ticket.permissions == ['read', 'write', 'chat']
        assert ticket.expires_at == current_time + 300
        assert ticket.created_at == current_time
        assert ticket.single_use is True
        assert ticket.metadata == {'source': 'unit_test'}

    def test_auth_ticket_defaults(self):
        """Test AuthTicket creation with default values."""
        # Arrange
        current_time = time.time()
        required_fields = {
            'ticket_id': 'test_ticket',
            'user_id': 'test_user',
            'email': 'test@example.com',
            'permissions': ['read'],
            'expires_at': current_time + 300,
            'created_at': current_time
        }

        # Act
        ticket = AuthTicket(**required_fields)

        # Assert
        assert ticket.single_use is True  # Default value
        assert ticket.metadata is None   # Default value


if __name__ == '__main__':
    pytest.main([__file__])