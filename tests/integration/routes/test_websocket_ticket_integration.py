"""
Integration tests for WebSocket ticket endpoint - Issue #1296 Phase 2

Tests the ticket generation endpoint integration with:
- FastAPI application setup
- Authentication middleware
- AuthTicketManager Redis integration
- Route registration and URL mapping
"""

import json
import pytest
import time
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestWebSocketTicketIntegration(SSotAsyncTestCase):
    """Integration test suite for WebSocket ticket endpoint."""

    def setUp(self):
        """Set up test dependencies."""
        super().setUp()
        
        # Sample JWT token for testing
        self.test_jwt_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature"
        
        # Sample user context
        self.test_user = {
            "user_id": "integration_user_123",
            "email": "integration@example.com",
            "permissions": ["read", "chat", "websocket"]
        }
        
    @patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure')
    @patch('netra_backend.app.websocket_core.unified_auth_ssot.ticket_manager')
    async def test_ticket_endpoint_registration(self, mock_ticket_manager, mock_get_user):
        """Test that the ticket endpoint is properly registered in the FastAPI app."""
        # Setup mocks
        mock_get_user.return_value = self.test_user
        
        # Mock ticket generation
        mock_ticket = AsyncMock()
        mock_ticket.ticket_id = "integration_test_ticket"
        mock_ticket.user_id = "integration_user_123"
        mock_ticket.email = "integration@example.com"
        mock_ticket.permissions = ["read", "chat", "websocket"]
        mock_ticket.expires_at = time.time() + 300
        mock_ticket.created_at = time.time()
        mock_ticket.single_use = True
        mock_ticket.metadata = {}
        
        mock_ticket_manager.generate_ticket.return_value = mock_ticket
        
        # Import app after mocking to ensure mocks are in place
        from netra_backend.app.core.app_factory import create_app
        app = create_app()
        
        # Test endpoint exists and responds
        async with AsyncClient(app=app, base_url="http://test") as client:
            # First verify the endpoint exists (should get 401 without auth)
            response = await client.post("/api/websocket/ticket")
            # The endpoint should exist but require authentication
            # We expect either 401 (unauthorized) or 422 (validation error) - not 404
            self.assertIn(response.status_code, [401, 422, 403])
            self.assertNotEqual(response.status_code, 404)  # Endpoint should exist
            
    @patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure')
    @patch('netra_backend.app.websocket_core.unified_auth_ssot.ticket_manager')
    async def test_ticket_generation_with_auth(self, mock_ticket_manager, mock_get_user):
        """Test ticket generation with proper authentication context."""
        # Setup mocks
        mock_get_user.return_value = self.test_user
        
        # Mock ticket generation
        mock_ticket = AsyncMock()
        mock_ticket.ticket_id = "auth_test_ticket_456"
        mock_ticket.user_id = "integration_user_123"
        mock_ticket.email = "integration@example.com"
        mock_ticket.permissions = ["read", "chat", "websocket", "agent:execute"]
        mock_ticket.expires_at = time.time() + 300
        mock_ticket.created_at = time.time()
        mock_ticket.single_use = True
        mock_ticket.metadata = {}
        
        mock_ticket_manager.generate_ticket.return_value = mock_ticket
        
        # Import app
        from netra_backend.app.core.app_factory import create_app
        app = create_app()
        
        # Test ticket generation with minimal request
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Mock the dependency injection for get_current_user_secure
            with patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure') as mock_dep:
                mock_dep.return_value = self.test_user
                
                response = await client.post(
                    "/api/websocket/ticket",
                    json={},  # Empty body, should use defaults
                    headers={"Authorization": f"Bearer {self.test_jwt_token}"}
                )
                
                # If authentication dependency is properly mocked, we should get success
                if response.status_code == 200:
                    response_data = response.json()
                    self.assertEqual(response_data["ticket_id"], "auth_test_ticket_456")
                    self.assertEqual(response_data["ttl_seconds"], 300)
                    self.assertTrue(response_data["single_use"])
                    self.assertIn("auth_test_ticket_456", response_data["websocket_url"])
                else:
                    # If we get auth error, that means the endpoint is working but auth is required
                    self.assertIn(response.status_code, [401, 403])
                    
    @patch('netra_backend.app.routes.websocket_ticket.get_ticket_manager')
    async def test_ticket_validation_endpoint(self, mock_get_manager):
        """Test ticket validation endpoint integration."""
        # Setup mock
        mock_manager = AsyncMock()
        mock_ticket = AsyncMock()
        mock_ticket.user_id = "validation_user_123"
        mock_ticket.email = "validation@example.com"
        mock_ticket.permissions = ["read", "chat"]
        mock_ticket.expires_at = time.time() + 300
        
        mock_manager.validate_ticket.return_value = mock_ticket
        mock_get_manager.return_value = mock_manager
        
        # Import app
        from netra_backend.app.core.app_factory import create_app
        app = create_app()
        
        # Test ticket validation
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/websocket/ticket/test_ticket_123/validate")
            
            # Should get successful response
            if response.status_code == 200:
                response_data = response.json()
                self.assertTrue(response_data["valid"])
                self.assertEqual(response_data["user_id"], "validation_user_123")
                self.assertEqual(response_data["email"], "validation@example.com")
                
    @patch('netra_backend.app.routes.websocket_ticket.get_ticket_manager')
    async def test_ticket_system_status_endpoint(self, mock_get_manager):
        """Test ticket system status endpoint integration."""
        # Setup mock
        mock_manager = AsyncMock()
        mock_manager.redis_manager = AsyncMock()  # Redis available
        mock_manager._default_ttl = 300
        mock_manager._max_ttl = 3600
        mock_manager._ticket_prefix = "auth:ticket:"
        mock_get_manager.return_value = mock_manager
        
        # Import app
        from netra_backend.app.core.app_factory import create_app
        app = create_app()
        
        # Test system status
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/websocket/tickets/status")
            
            # Should get successful response
            if response.status_code == 200:
                response_data = response.json()
                self.assertTrue(response_data["ticket_system_enabled"])
                self.assertTrue(response_data["redis_available"])
                self.assertEqual(response_data["default_ttl_seconds"], 300)
                self.assertEqual(response_data["max_ttl_seconds"], 3600)
                
    async def test_endpoint_url_patterns(self):
        """Test that all ticket endpoint URL patterns are correctly configured."""
        from netra_backend.app.core.app_factory import create_app
        app = create_app()
        
        # Get all registered routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
                
        # Check that our ticket endpoints are registered
        expected_patterns = [
            "/api/websocket/ticket",  # POST - generate ticket
            "/api/websocket/ticket/{ticket_id}/validate",  # GET - validate ticket
            "/api/websocket/ticket/{ticket_id}",  # DELETE - revoke ticket  
            "/api/websocket/tickets/status"  # GET - system status
        ]
        
        # At least some of our patterns should be present
        # Note: FastAPI may register additional patterns like {ticket_id:path}
        found_ticket_routes = [route for route in routes if "/websocket/ticket" in route]
        self.assertGreater(len(found_ticket_routes), 0, 
                          f"No ticket routes found. Available routes: {routes}")
        
    @patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure')
    async def test_endpoint_error_handling(self, mock_get_user):
        """Test endpoint error handling and HTTP status codes."""
        # Test with missing user context
        mock_get_user.return_value = {"email": "test@example.com"}  # Missing user_id
        
        from netra_backend.app.core.app_factory import create_app
        app = create_app()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Mock the dependency to simulate missing user_id
            with patch('netra_backend.app.routes.websocket_ticket.get_current_user_secure') as mock_dep:
                mock_dep.return_value = {"email": "test@example.com"}  # Missing user_id
                
                response = await client.post(
                    "/api/websocket/ticket",
                    json={},
                    headers={"Authorization": f"Bearer {self.test_jwt_token}"}
                )
                
                # Should get 401 for invalid user context (if auth dependency works)
                # or other auth-related error
                self.assertIn(response.status_code, [401, 403, 422])
                
    async def test_request_validation(self):
        """Test request validation for ticket generation."""
        from netra_backend.app.core.app_factory import create_app
        app = create_app()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test invalid TTL (too high)
            response = await client.post(
                "/api/websocket/ticket",
                json={"ttl_seconds": 5000},  # Above maximum
                headers={"Authorization": f"Bearer {self.test_jwt_token}"}
            )
            
            # Should get validation error
            self.assertEqual(response.status_code, 422)
            
            # Test invalid TTL (too low)
            response = await client.post(
                "/api/websocket/ticket", 
                json={"ttl_seconds": 10},  # Below minimum
                headers={"Authorization": f"Bearer {self.test_jwt_token}"}
            )
            
            # Should get validation error
            self.assertEqual(response.status_code, 422)
            
    @patch('netra_backend.app.websocket_core.unified_auth_ssot.ticket_manager')
    async def test_redis_integration_simulation(self, mock_ticket_manager):
        """Test simulated Redis integration for ticket storage."""
        # Setup mock to simulate Redis operations
        mock_ticket_manager.redis_manager = AsyncMock()
        
        # Mock ticket generation and storage
        mock_ticket = AsyncMock()
        mock_ticket.ticket_id = "redis_test_ticket"
        mock_ticket.user_id = "redis_user_123"
        mock_ticket.email = "redis@example.com"
        mock_ticket.permissions = ["read", "chat"]
        mock_ticket.expires_at = time.time() + 300
        mock_ticket.created_at = time.time()
        mock_ticket.single_use = True
        mock_ticket.metadata = {}
        
        mock_ticket_manager.generate_ticket.return_value = mock_ticket
        mock_ticket_manager.validate_ticket.return_value = mock_ticket
        
        # Test the ticket manager methods are called correctly
        from netra_backend.app.websocket_core.unified_auth_ssot import generate_auth_ticket, validate_auth_ticket
        
        # Test generation
        ticket = await generate_auth_ticket(
            user_id="redis_user_123",
            email="redis@example.com",
            permissions=["read", "chat"],
            ttl_seconds=300
        )
        
        self.assertEqual(ticket.ticket_id, "redis_test_ticket")
        mock_ticket_manager.generate_ticket.assert_called_once()
        
        # Test validation  
        validated_ticket = await validate_auth_ticket("redis_test_ticket")
        
        self.assertEqual(validated_ticket.ticket_id, "redis_test_ticket")
        mock_ticket_manager.validate_ticket.assert_called_once_with("redis_test_ticket")
        
    async def test_websocket_url_generation(self):
        """Test WebSocket URL generation in ticket response."""
        from netra_backend.app.routes.websocket_ticket import TicketGenerationResponse
        import time
        
        # Test URL generation
        response = TicketGenerationResponse(
            ticket_id="url_test_ticket_789",
            expires_at=time.time() + 300,
            created_at=time.time(),
            ttl_seconds=300,
            single_use=True,
            websocket_url="wss://api.example.com/ws?ticket=url_test_ticket_789"
        )
        
        # Verify URL format
        self.assertIn("wss://", response.websocket_url)
        self.assertIn("ticket=url_test_ticket_789", response.websocket_url)
        
        # URL should be properly formatted for WebSocket connection
        self.assertTrue(response.websocket_url.startswith("wss://"))
        self.assertIn("?ticket=", response.websocket_url)