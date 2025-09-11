"""
Test Authentication Service Integration with Real Services

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure user authentication across all services
- Value Impact: Protects user accounts and enables secure multi-tenant operations
- Strategic Impact: Core security foundation for customer trust and compliance

CRITICAL COMPLIANCE:
- Uses real authentication service for integration testing
- Validates JWT token flow between services
- Tests OAuth integration for user onboarding
- Ensures session management for user retention
"""

import pytest
import uuid
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotBaseTestCase
from auth_service.auth_core.core.jwt_handler import JWTHandler
from netra_backend.app.clients.auth_client_core import AuthClientCore


class TestAuthServiceIntegrationRealServices(SSotBaseTestCase):
    """Test authentication service integration with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_validation_cross_service(self):
        """Test JWT token validation between auth service and backend."""
        # Given: User authenticated via auth service
        jwt_handler = JWTHandler()
        auth_client = AuthClientCore()
        
        user_id = str(uuid.uuid4())
        user_email = "test@enterprise.com"
        
        # When: Creating JWT token in auth service
        access_token = jwt_handler.create_access_token(
            user_id=user_id,
            email=user_email,
            permissions=["execute_agents", "read_data"]
        )
        
        # Then: Backend should be able to validate token
        validation_result = await auth_client.validate_token(access_token)
        
        assert validation_result is not None
        assert validation_result["valid"] is True
        assert validation_result["user_id"] == user_id
        assert validation_result["email"] == user_email
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_registration_oauth_flow(self):
        """Test user registration via OAuth flow integration."""
        # Given: OAuth user registration scenario
        auth_client = AuthClientCore()
        
        oauth_user_data = {
            "email": "newuser@startup.com",
            "name": "New User",
            "oauth_provider": "google",
            "oauth_id": "google_123456789"
        }
        
        # When: Registering user via OAuth
        registration_result = await auth_client.register_oauth_user(oauth_user_data)
        
        # Then: User should be registered successfully
        assert registration_result["success"] is True
        assert registration_result["user_id"] is not None
        assert registration_result["access_token"] is not None
        
        # Should be able to use access token immediately
        token_validation = await auth_client.validate_token(
            registration_result["access_token"]
        )
        assert token_validation["valid"] is True
        assert token_validation["email"] == oauth_user_data["email"]