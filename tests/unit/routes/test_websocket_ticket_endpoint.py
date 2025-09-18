"""
Unit tests for WebSocket ticket endpoint - Issue #1296 Phase 2

Tests the ticket generation endpoint implementation including:
- JWT validation and user context extraction  
- Ticket generation using AuthTicketManager
- Error handling and validation
- Response format compliance
"""

import json
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestWebSocketTicketEndpoint(SSotAsyncTestCase):
    """Test suite for WebSocket ticket generation endpoint."""

    def setUp(self):
        """Set up test dependencies."""
        super().setUp()
        
        # Mock authentication dependencies
        self.mock_auth_client = AsyncMock()
        self.mock_ticket_manager = AsyncMock()
        self.mock_get_current_user = AsyncMock()
        
        # Sample user context for testing
        self.test_user = {
            "user_id": "test_user_123",
            "id": "test_user_123",  # Alternative field name
            "email": "test@example.com",
            "permissions": ["read", "chat", "websocket"]
        }
        
        # Sample JWT validation result
        self.jwt_validation_result = {
            "valid": True,
            "user_id": "test_user_123",
            "email": "test@example.com",
            "permissions": ["read", "chat", "websocket"]
        }
        
        # Sample generated ticket
        self.test_ticket = MagicMock()
        self.test_ticket.ticket_id = "test_ticket_abc123"
        self.test_ticket.user_id = "test_user_123"
        self.test_ticket.email = "test@example.com"
        self.test_ticket.permissions = ["read", "chat", "websocket"]
        self.test_ticket.expires_at = time.time() + 300
        self.test_ticket.created_at = time.time()
        self.test_ticket.single_use = True
        self.test_ticket.metadata = {}
        
    @patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure')
    @patch('netra_backend.app.routes.websocket_ticket.generate_auth_ticket')
    async def test_generate_ticket_success_minimal_request(self, mock_generate_ticket, mock_get_user):
        """Test successful ticket generation with minimal request parameters."""
        # Setup mocks
        mock_get_user.return_value = self.test_user
        mock_generate_ticket.return_value = self.test_ticket
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import generate_websocket_ticket, TicketGenerationRequest
        
        # Create request
        request = TicketGenerationRequest()
        
        # Call endpoint
        result = await generate_websocket_ticket(request, self.test_user)
        
        # Verify response
        self.assertEqual(result.ticket_id, "test_ticket_abc123")
        self.assertEqual(result.ttl_seconds, 300)  # Default TTL
        self.assertTrue(result.single_use)  # Default single use
        self.assertIn("test_ticket_abc123", result.websocket_url)
        
        # Verify ticket generation was called correctly
        mock_generate_ticket.assert_called_once()
        call_args = mock_generate_ticket.call_args
        self.assertEqual(call_args.kwargs['user_id'], "test_user_123")
        self.assertEqual(call_args.kwargs['email'], "test@example.com")
        self.assertEqual(call_args.kwargs['permissions'], ["read", "chat", "websocket", "agent:execute"])
        self.assertEqual(call_args.kwargs['ttl_seconds'], 300)
        self.assertTrue(call_args.kwargs['single_use'])
        
    @patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure')
    @patch('netra_backend.app.routes.websocket_ticket.generate_auth_ticket')
    async def test_generate_ticket_success_custom_parameters(self, mock_generate_ticket, mock_get_user):
        """Test successful ticket generation with custom parameters."""
        # Setup mocks
        mock_get_user.return_value = self.test_user
        mock_generate_ticket.return_value = self.test_ticket
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import generate_websocket_ticket, TicketGenerationRequest
        
        # Create request with custom parameters
        request = TicketGenerationRequest(
            ttl_seconds=600,
            single_use=False,
            permissions=["read", "write", "admin"],
            metadata={"test": "data"}
        )
        
        # Call endpoint
        result = await generate_websocket_ticket(request, self.test_user)
        
        # Verify response
        self.assertEqual(result.ticket_id, "test_ticket_abc123")
        self.assertEqual(result.ttl_seconds, 600)
        self.assertFalse(result.single_use)
        
        # Verify ticket generation was called with custom parameters
        mock_generate_ticket.assert_called_once()
        call_args = mock_generate_ticket.call_args
        self.assertEqual(call_args.kwargs['ttl_seconds'], 600)
        self.assertFalse(call_args.kwargs['single_use'])
        self.assertEqual(call_args.kwargs['permissions'], ["read", "write", "admin"])
        self.assertEqual(call_args.kwargs['metadata'], {"test": "data"})
        
    @patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure')
    async def test_generate_ticket_missing_user_id(self, mock_get_user):
        """Test ticket generation failure when user context is missing user_id."""
        # Setup mock with missing user_id
        mock_get_user.return_value = {"email": "test@example.com"}
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import generate_websocket_ticket, TicketGenerationRequest
        
        # Create request
        request = TicketGenerationRequest()
        
        # Call endpoint and expect error
        with pytest.raises(HTTPException) as exc_info:
            await generate_websocket_ticket(request, {"email": "test@example.com"})
            
        self.assertEqual(exc_info.value.status_code, 401)
        self.assertIn("missing user_id or email", exc_info.value.detail)
        
    @patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure')
    async def test_generate_ticket_missing_email(self, mock_get_user):
        """Test ticket generation failure when user context is missing email."""
        # Setup mock with missing email
        mock_get_user.return_value = {"user_id": "test_user_123"}
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import generate_websocket_ticket, TicketGenerationRequest
        
        # Create request
        request = TicketGenerationRequest()
        
        # Call endpoint and expect error
        with pytest.raises(HTTPException) as exc_info:
            await generate_websocket_ticket(request, {"user_id": "test_user_123"})
            
        self.assertEqual(exc_info.value.status_code, 401)
        self.assertIn("missing user_id or email", exc_info.value.detail)
        
    @patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure')
    @patch('netra_backend.app.routes.websocket_ticket.generate_auth_ticket')
    async def test_generate_ticket_auth_manager_value_error(self, mock_generate_ticket, mock_get_user):
        """Test ticket generation failure when AuthTicketManager raises ValueError."""
        # Setup mocks
        mock_get_user.return_value = self.test_user
        mock_generate_ticket.side_effect = ValueError("Invalid TTL value")
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import generate_websocket_ticket, TicketGenerationRequest
        
        # Create request
        request = TicketGenerationRequest()
        
        # Call endpoint and expect error
        with pytest.raises(HTTPException) as exc_info:
            await generate_websocket_ticket(request, self.test_user)
            
        self.assertEqual(exc_info.value.status_code, 400)
        self.assertEqual(exc_info.value.detail, "Invalid TTL value")
        
    @patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure')
    @patch('netra_backend.app.routes.websocket_ticket.generate_auth_ticket')
    async def test_generate_ticket_auth_manager_runtime_error(self, mock_generate_ticket, mock_get_user):
        """Test ticket generation failure when AuthTicketManager raises RuntimeError."""
        # Setup mocks
        mock_get_user.return_value = self.test_user
        mock_generate_ticket.side_effect = RuntimeError("Redis connection failed")
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import generate_websocket_ticket, TicketGenerationRequest
        
        # Create request
        request = TicketGenerationRequest()
        
        # Call endpoint and expect error
        with pytest.raises(HTTPException) as exc_info:
            await generate_websocket_ticket(request, self.test_user)
            
        self.assertEqual(exc_info.value.status_code, 500)
        self.assertEqual(exc_info.value.detail, "Ticket generation failed")
        
    @patch('netra_backend.app.routes.websocket_ticket.get_ticket_manager')
    async def test_validate_ticket_success(self, mock_get_manager):
        """Test successful ticket validation."""
        # Setup mock
        mock_manager = AsyncMock()
        mock_manager.validate_ticket.return_value = self.test_ticket
        mock_get_manager.return_value = mock_manager
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import validate_websocket_ticket
        
        # Call endpoint
        result = await validate_websocket_ticket("test_ticket_abc123")
        
        # Verify response
        self.assertTrue(result.valid)
        self.assertEqual(result.user_id, "test_user_123")
        self.assertEqual(result.email, "test@example.com")
        self.assertEqual(result.permissions, ["read", "chat", "websocket"])
        self.assertIsNotNone(result.expires_at)
        self.assertIsNone(result.error)
        
        # Verify manager was called
        mock_manager.validate_ticket.assert_called_once_with("test_ticket_abc123")
        
    @patch('netra_backend.app.routes.websocket_ticket.get_ticket_manager')
    async def test_validate_ticket_invalid(self, mock_get_manager):
        """Test ticket validation with invalid ticket."""
        # Setup mock
        mock_manager = AsyncMock()
        mock_manager.validate_ticket.return_value = None  # Invalid ticket
        mock_get_manager.return_value = mock_manager
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import validate_websocket_ticket
        
        # Call endpoint
        result = await validate_websocket_ticket("invalid_ticket")
        
        # Verify response
        self.assertFalse(result.valid)
        self.assertIsNone(result.user_id)
        self.assertIsNone(result.email)
        self.assertIsNone(result.permissions)
        self.assertIsNone(result.expires_at)
        self.assertIn("invalid or expired", result.error.lower())
        
    @patch('netra_backend.app.routes.websocket_ticket.get_ticket_manager')
    async def test_validate_ticket_manager_error(self, mock_get_manager):
        """Test ticket validation when manager raises exception."""
        # Setup mock
        mock_manager = AsyncMock()
        mock_manager.validate_ticket.side_effect = Exception("Redis error")
        mock_get_manager.return_value = mock_manager
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import validate_websocket_ticket
        
        # Call endpoint
        result = await validate_websocket_ticket("test_ticket")
        
        # Verify response
        self.assertFalse(result.valid)
        self.assertIn("Validation error", result.error)
        
    @patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure')
    @patch('netra_backend.app.routes.websocket_ticket.get_ticket_manager')
    async def test_revoke_ticket_success(self, mock_get_manager, mock_get_user):
        """Test successful ticket revocation."""
        # Setup mocks
        mock_get_user.return_value = self.test_user
        mock_manager = AsyncMock()
        mock_manager.validate_ticket.return_value = self.test_ticket
        mock_manager.revoke_ticket.return_value = True
        mock_get_manager.return_value = mock_manager
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import revoke_websocket_ticket
        
        # Call endpoint
        result = await revoke_websocket_ticket("test_ticket_abc123", self.test_user)
        
        # Verify response
        self.assertTrue(result["success"])
        self.assertIn("revoked successfully", result["message"])
        
        # Verify manager calls
        mock_manager.validate_ticket.assert_called_once_with("test_ticket_abc123")
        mock_manager.revoke_ticket.assert_called_once_with("test_ticket_abc123")
        
    @patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure')
    @patch('netra_backend.app.routes.websocket_ticket.get_ticket_manager')
    async def test_revoke_ticket_not_found(self, mock_get_manager, mock_get_user):
        """Test ticket revocation when ticket doesn't exist."""
        # Setup mocks
        mock_get_user.return_value = self.test_user
        mock_manager = AsyncMock()
        mock_manager.validate_ticket.return_value = None  # Ticket not found
        mock_get_manager.return_value = mock_manager
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import revoke_websocket_ticket
        
        # Call endpoint and expect error
        with pytest.raises(HTTPException) as exc_info:
            await revoke_websocket_ticket("nonexistent_ticket", self.test_user)
            
        self.assertEqual(exc_info.value.status_code, 404)
        self.assertIn("not found", exc_info.value.detail)
        
    @patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure')
    @patch('netra_backend.app.routes.websocket_ticket.get_ticket_manager')
    async def test_revoke_ticket_wrong_owner(self, mock_get_manager, mock_get_user):
        """Test ticket revocation when user doesn't own the ticket."""
        # Setup mocks - different user owns the ticket
        mock_get_user.return_value = self.test_user
        other_user_ticket = MagicMock()
        other_user_ticket.user_id = "other_user_456"
        mock_manager = AsyncMock()
        mock_manager.validate_ticket.return_value = other_user_ticket
        mock_get_manager.return_value = mock_manager
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import revoke_websocket_ticket
        
        # Call endpoint and expect error
        with pytest.raises(HTTPException) as exc_info:
            await revoke_websocket_ticket("other_user_ticket", self.test_user)
            
        self.assertEqual(exc_info.value.status_code, 403)
        self.assertIn("Cannot revoke ticket owned by another user", exc_info.value.detail)
        
    @patch('netra_backend.app.routes.websocket_ticket.get_ticket_manager')
    async def test_get_ticket_system_status_success(self, mock_get_manager):
        """Test successful ticket system status retrieval."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager.redis_manager = MagicMock()  # Redis available
        mock_manager._default_ttl = 300
        mock_manager._max_ttl = 3600
        mock_manager._ticket_prefix = "auth:ticket:"
        mock_get_manager.return_value = mock_manager
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import get_ticket_system_status
        
        # Call endpoint
        result = await get_ticket_system_status()
        
        # Verify response
        self.assertTrue(result["ticket_system_enabled"])
        self.assertTrue(result["redis_available"])
        self.assertEqual(result["default_ttl_seconds"], 300)
        self.assertEqual(result["max_ttl_seconds"], 3600)
        self.assertEqual(result["ticket_prefix"], "auth:ticket:")
        self.assertEqual(result["redis_status"], "connected")
        
    @patch('netra_backend.app.routes.websocket_ticket.get_ticket_manager')
    async def test_get_ticket_system_status_redis_unavailable(self, mock_get_manager):
        """Test ticket system status when Redis is unavailable."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager.redis_manager = None  # Redis not available
        mock_manager._default_ttl = 300
        mock_manager._max_ttl = 3600
        mock_manager._ticket_prefix = "auth:ticket:"
        mock_get_manager.return_value = mock_manager
        
        # Import and setup endpoint
        from netra_backend.app.routes.websocket_ticket import get_ticket_system_status
        
        # Call endpoint
        result = await get_ticket_system_status()
        
        # Verify response
        self.assertTrue(result["ticket_system_enabled"])
        self.assertFalse(result["redis_available"])
        self.assertEqual(result["redis_status"], "not_available")
        
    def test_ticket_generation_request_validation(self):
        """Test ticket generation request model validation."""
        from netra_backend.app.routes.websocket_ticket import TicketGenerationRequest
        from pydantic import ValidationError
        
        # Test valid request
        valid_request = TicketGenerationRequest(
            ttl_seconds=600,
            single_use=False,
            permissions=["read", "write"],
            metadata={"source": "test"}
        )
        self.assertEqual(valid_request.ttl_seconds, 600)
        self.assertFalse(valid_request.single_use)
        
        # Test invalid TTL (too low)
        with pytest.raises(ValidationError):
            TicketGenerationRequest(ttl_seconds=10)  # Below minimum 30
            
        # Test invalid TTL (too high)
        with pytest.raises(ValidationError):
            TicketGenerationRequest(ttl_seconds=5000)  # Above maximum 3600
            
        # Test defaults
        default_request = TicketGenerationRequest()
        self.assertEqual(default_request.ttl_seconds, 300)
        self.assertTrue(default_request.single_use)
        self.assertIsNone(default_request.permissions)
        self.assertIsNone(default_request.metadata)
        
    def test_ticket_generation_response_model(self):
        """Test ticket generation response model structure."""
        from netra_backend.app.routes.websocket_ticket import TicketGenerationResponse
        
        response = TicketGenerationResponse(
            ticket_id="test_ticket_123",
            expires_at=time.time() + 300,
            created_at=time.time(),
            ttl_seconds=300,
            single_use=True,
            websocket_url="wss://example.com/ws?ticket=test_ticket_123"
        )
        
        self.assertEqual(response.ticket_id, "test_ticket_123")
        self.assertEqual(response.ttl_seconds, 300)
        self.assertTrue(response.single_use)
        self.assertIn("test_ticket_123", response.websocket_url)
        
    def test_ticket_validation_response_model(self):
        """Test ticket validation response model structure."""
        from netra_backend.app.routes.websocket_ticket import TicketValidationResponse
        
        # Valid ticket response
        valid_response = TicketValidationResponse(
            valid=True,
            user_id="test_user_123",
            email="test@example.com",
            permissions=["read", "chat"],
            expires_at=time.time() + 300
        )
        
        self.assertTrue(valid_response.valid)
        self.assertEqual(valid_response.user_id, "test_user_123")
        self.assertIsNone(valid_response.error)
        
        # Invalid ticket response
        invalid_response = TicketValidationResponse(
            valid=False,
            error="Ticket expired"
        )
        
        self.assertFalse(invalid_response.valid)
        self.assertIsNone(invalid_response.user_id)
        self.assertEqual(invalid_response.error, "Ticket expired")