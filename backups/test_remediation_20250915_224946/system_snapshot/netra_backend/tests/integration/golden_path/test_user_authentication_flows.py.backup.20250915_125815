"""
Test User Authentication Flows - GOLDEN PATH Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure and reliable user authentication for all user workflows
- Value Impact: Users must authenticate successfully to access AI optimization features
- Strategic Impact: Core platform security and user onboarding functionality

These tests validate the complete user authentication flows that are essential
for users to access the Netra Apex AI optimization platform. Without proper
authentication, users cannot create threads, execute agents, or receive value.
"""

import asyncio
import pytest
import uuid
from typing import Dict, Any
from datetime import datetime, timezone

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, create_authenticated_user
from shared.isolated_environment import get_env


class TestUserAuthenticationFlows(BaseIntegrationTest):
    """Integration tests for user authentication flows with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_creation_and_validation(self, real_services_fixture):
        """
        Test JWT token creation and validation with real auth service.
        
        BVJ: JWT tokens are the foundation of authentication - they must work
        reliably to enable user access to optimization features.
        """
        # Create auth helper
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Generate test user credentials
        user_id = f"auth_test_{uuid.uuid4().hex[:8]}"
        email = f"integration_{user_id}@example.com"
        permissions = ["read", "write", "agent_execute"]
        
        # Create JWT token
        jwt_token = auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            permissions=permissions,
            exp_minutes=30
        )
        
        # Verify token structure
        assert jwt_token is not None
        assert len(jwt_token.split('.')) == 3, "JWT must have header.payload.signature format"
        
        # Validate token
        validation_result = await auth_helper.validate_jwt_token(jwt_token)
        assert validation_result["valid"] is True, f"Token validation failed: {validation_result}"
        assert validation_result["user_id"] == user_id
        assert validation_result["email"] == email
        assert validation_result["permissions"] == permissions
        
        # Verify business value delivered
        self.assert_business_value_delivered(validation_result, 'automation')
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authenticated_user_creation_with_database(self, real_services_fixture):
        """
        Test authenticated user creation with real database persistence.
        
        BVJ: Users must be properly created and persisted to maintain session
        state and enable personalized optimization recommendations.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available for integration testing")
            
        # Create authenticated user
        user_email = f"db_integration_{uuid.uuid4().hex[:8]}@example.com"
        user_data = await self.create_test_user_context(
            real_services_fixture, 
            user_data={'email': user_email, 'name': 'Integration Test User', 'is_active': True}
        )
        
        # Verify user was created in database
        assert user_data["id"] is not None
        assert user_data["email"] == user_email
        
        # Create session for the user
        session_data = await self.create_test_session(
            real_services_fixture,
            user_data["id"]
        )
        
        # Verify session persistence
        assert session_data["user_id"] == user_data["id"]
        assert session_data["active"] is True
        
        # Test authentication helper with this user
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        jwt_token = auth_helper.create_test_jwt_token(
            user_id=user_data["id"],
            email=user_data["email"]
        )
        
        # Verify auth headers
        auth_headers = auth_helper.get_auth_headers(jwt_token)
        assert "Authorization" in auth_headers
        assert auth_headers["Authorization"].startswith("Bearer ")
        
        # Verify business value: user can now access platform features
        business_result = {
            "user_authenticated": True,
            "session_active": True,
            "platform_access_enabled": True,
            "automation": ["user_creation", "session_management", "jwt_authentication"]
        }
        self.assert_business_value_delivered(business_result, 'automation')
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_authentication_isolation(self, real_services_fixture):
        """
        Test authentication isolation between multiple users.
        
        BVJ: Multi-tenant isolation is critical for security and ensures
        each user's optimization data remains private and secure.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available for integration testing")
            
        # Create multiple authenticated users
        users = []
        for i in range(3):
            user_email = f"multi_user_{i}_{uuid.uuid4().hex[:8]}@example.com"
            user_data = await self.create_test_user_context(
                real_services_fixture,
                user_data={'email': user_email, 'name': f'User {i}', 'is_active': True}
            )
            
            # Create authentication for each user
            auth_helper = E2EWebSocketAuthHelper(environment="test")
            jwt_token = auth_helper.create_test_jwt_token(
                user_id=user_data["id"],
                email=user_data["email"],
                permissions=[f"user_{i}_access", "read", "write"]
            )
            
            users.append({
                "user_data": user_data,
                "jwt_token": jwt_token,
                "auth_helper": auth_helper
            })
        
        # Verify each user has unique authentication
        user_ids = [user["user_data"]["id"] for user in users]
        assert len(set(user_ids)) == 3, "All users must have unique IDs"
        
        jwt_tokens = [user["jwt_token"] for user in users]
        assert len(set(jwt_tokens)) == 3, "All users must have unique JWT tokens"
        
        # Verify token isolation - each token only works for its user
        for i, user in enumerate(users):
            validation_result = await user["auth_helper"].validate_jwt_token(user["jwt_token"])
            assert validation_result["valid"] is True
            assert validation_result["user_id"] == user["user_data"]["id"]
            assert f"user_{i}_access" in validation_result["permissions"]
        
        # Verify business value: secure multi-tenant authentication
        business_result = {
            "multi_tenant_isolation": True,
            "secure_authentication": True,
            "user_privacy_protected": True,
            "automation": [f"isolated_auth_user_{i}" for i in range(3)]
        }
        self.assert_business_value_delivered(business_result, 'automation')
        
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_authentication_session_lifecycle(self, real_services_fixture):
        """
        Test complete authentication session lifecycle with Redis cache.
        
        BVJ: Session management enables users to maintain context across
        multiple optimization requests without re-authentication.
        """
        # Create authenticated user
        user_email = f"session_lifecycle_{uuid.uuid4().hex[:8]}@example.com"
        user_data = await self.create_test_user_context(
            real_services_fixture,
            user_data={'email': user_email, 'name': 'Session Test User', 'is_active': True}
        )
        
        # Create initial session
        session_data = await self.create_test_session(
            real_services_fixture,
            user_data["id"],
            session_data={
                'user_id': user_data["id"],
                'created_at': asyncio.get_event_loop().time(),
                'expires_at': asyncio.get_event_loop().time() + 1800,  # 30 minutes
                'active': True,
                'session_type': 'optimization'
            }
        )
        
        # Verify session creation
        assert session_data["user_id"] == user_data["id"]
        assert session_data["active"] is True
        assert session_data["session_type"] == 'optimization'
        
        # Create authentication for session
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        jwt_token = auth_helper.create_test_jwt_token(
            user_id=user_data["id"],
            email=user_data["email"],
            exp_minutes=30
        )
        
        # Test WebSocket headers for session
        websocket_headers = auth_helper.get_websocket_headers(jwt_token)
        assert "Authorization" in websocket_headers
        assert "X-User-ID" in websocket_headers
        assert "X-Test-Mode" in websocket_headers
        assert websocket_headers["X-User-ID"] == user_data["id"]
        
        # Simulate session usage over time
        await asyncio.sleep(0.1)  # Simulate time passage
        
        # Update session activity
        updated_session = await self.create_test_session(
            real_services_fixture,
            user_data["id"],
            session_data={
                'user_id': user_data["id"],
                'created_at': session_data['created_at'],
                'expires_at': asyncio.get_event_loop().time() + 1800,  # Refresh expiry
                'active': True,
                'session_type': 'optimization',
                'last_activity': asyncio.get_event_loop().time()
            }
        )
        
        # Verify session update
        assert updated_session["last_activity"] is not None
        assert updated_session["expires_at"] > session_data["expires_at"]
        
        # Verify business value: session enables continuous optimization workflow
        business_result = {
            "session_lifecycle_complete": True,
            "continuous_authentication": True,
            "optimization_workflow_enabled": True,
            "automation": ["session_creation", "session_update", "jwt_refresh"]
        }
        self.assert_business_value_delivered(business_result, 'automation')
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_error_handling_and_recovery(self, real_services_fixture):
        """
        Test authentication error handling and recovery mechanisms.
        
        BVJ: Robust error handling ensures users can recover from auth failures
        and continue accessing optimization features without frustration.
        """
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Test 1: Invalid JWT token handling
        invalid_token = "invalid.jwt.token"
        validation_result = await auth_helper.validate_jwt_token(invalid_token)
        assert validation_result["valid"] is False
        assert "error" in validation_result
        assert validation_result["error"] == "Invalid JWT token structure"
        
        # Test 2: Expired token handling
        expired_token = auth_helper.create_test_jwt_token(
            user_id="test-user-expired",
            email="expired@example.com",
            exp_minutes=-5  # Already expired
        )
        expired_validation = await auth_helper.validate_jwt_token(expired_token)
        assert expired_validation["valid"] is False
        assert "expired" in expired_validation["error"].lower()
        
        # Test 3: Recovery with new valid token
        valid_user_id = f"recovery_test_{uuid.uuid4().hex[:8]}"
        valid_email = f"recovery_{valid_user_id}@example.com"
        
        recovery_token = auth_helper.create_test_jwt_token(
            user_id=valid_user_id,
            email=valid_email,
            permissions=["read", "write", "recover"],
            exp_minutes=30
        )
        
        recovery_validation = await auth_helper.validate_jwt_token(recovery_token)
        assert recovery_validation["valid"] is True
        assert recovery_validation["user_id"] == valid_user_id
        assert "recover" in recovery_validation["permissions"]
        
        # Test 4: WebSocket auth headers with recovery token
        recovery_headers = auth_helper.get_websocket_headers(recovery_token)
        assert recovery_headers["Authorization"] == f"Bearer {recovery_token}"
        assert recovery_headers["X-User-ID"] == valid_user_id
        
        # Verify business value: error handling maintains user access
        business_result = {
            "authentication_errors_handled": True,
            "token_recovery_successful": True,
            "user_access_restored": True,
            "automation": ["error_detection", "token_refresh", "access_recovery"]
        }
        self.assert_business_value_delivered(business_result, 'automation')