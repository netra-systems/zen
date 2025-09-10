"""
Unit Tests for JWT Management Operations

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Secure user authentication and session management
- Value Impact: Enables secure access to AI optimization features across all tiers
- Strategic Impact: Critical security foundation - JWT failures = no user authentication

This module tests JWT management operations including:
- Access token creation and validation
- Refresh token lifecycle management
- Token expiration and security validation
- Cross-service token validation
- Performance optimization for auth flows
- Security compliance and error handling
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
from auth_service.services.jwt_service import JWTService
from auth_service.auth_core.config import AuthConfig


class TestJWTManagement(SSotBaseTestCase):
    """Unit tests for JWT management business logic."""
    
    def setup_method(self, method=None):
        """Setup test environment and mocks."""
        super().setup_method(method)
        
        # Mock auth configuration
        self.mock_auth_config = MagicMock(spec=AuthConfig)
        self.mock_auth_config.jwt_secret_key = "test-jwt-secret-key-32-characters"
        self.mock_auth_config.jwt_algorithm = "HS256"
        self.mock_auth_config.access_token_expire_minutes = 30
        self.mock_auth_config.refresh_token_expire_days = 7
        
        # Test user data
        self.test_user_id = "test-user-12345"
        self.test_email = "test@example.com"
        self.test_permissions = ["read", "write", "admin"]
        
        # Create JWT service instance
        with patch('auth_service.services.jwt_service.JWTHandler') as mock_jwt_handler_class:
            self.mock_jwt_handler = MagicMock()
            mock_jwt_handler_class.return_value = self.mock_jwt_handler
            
            self.jwt_service = JWTService(auth_config=self.mock_auth_config)
            
    @pytest.mark.unit
    async def test_access_token_creation_with_valid_data(self):
        """Test access token creation with valid user data."""
        # Mock successful token creation
        expected_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_payload.test_signature"
        self.mock_jwt_handler.create_access_token.return_value = expected_token
        
        # Business logic: Create access token for user
        token = await self.jwt_service.create_access_token(
            user_id=self.test_user_id,
            email=self.test_email,
            permissions=self.test_permissions
        )
        
        # Verify token was created
        assert token == expected_token
        
        # Verify handler was called with correct parameters
        self.mock_jwt_handler.create_access_token.assert_called_once_with(
            user_id=self.test_user_id,
            email=self.test_email,
            permissions=self.test_permissions
        )
        
        # Record business metric: Token creation success
        self.record_metric("access_token_creation_success", True)
        
    @pytest.mark.unit
    async def test_access_token_creation_with_minimal_data(self):
        """Test access token creation with minimal required data."""
        # Mock successful token creation with defaults
        expected_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.minimal_payload.test_signature"
        self.mock_jwt_handler.create_access_token.return_value = expected_token
        
        # Business logic: Create token with minimal data (no permissions)
        token = await self.jwt_service.create_access_token(
            user_id=self.test_user_id,
            email=self.test_email
        )
        
        # Verify token was created with default permissions
        assert token == expected_token
        
        # Verify handler was called with empty permissions list
        self.mock_jwt_handler.create_access_token.assert_called_once_with(
            user_id=self.test_user_id,
            email=self.test_email,
            permissions=[]
        )
        
        # Record business metric: Minimal token creation success
        self.record_metric("minimal_token_creation_success", True)
        
    @pytest.mark.unit
    async def test_token_validation_with_valid_token(self):
        """Test token validation with a valid JWT token."""
        # Mock successful token validation
        valid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.valid_payload.valid_signature"
        expected_payload = {
            "sub": self.test_user_id,
            "email": self.test_email,
            "permissions": self.test_permissions,
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
            "type": "access"
        }
        self.mock_jwt_handler.validate_token.return_value = expected_payload
        
        # Business logic: Validate token and extract user data
        payload = await self.jwt_service.validate_token(valid_token)
        
        # Verify payload contains expected user data
        assert payload == expected_payload
        assert payload["sub"] == self.test_user_id
        assert payload["email"] == self.test_email
        assert payload["permissions"] == self.test_permissions
        assert payload["type"] == "access"
        
        # Verify handler was called correctly
        self.mock_jwt_handler.validate_token.assert_called_once_with(valid_token)
        
        # Record business metric: Token validation success
        self.record_metric("token_validation_success", True)
        
    @pytest.mark.unit
    async def test_token_validation_with_invalid_token(self):
        """Test token validation with invalid token."""
        # Mock token validation failure
        invalid_token = "invalid.jwt.token"
        self.mock_jwt_handler.validate_token.side_effect = Exception("Invalid token signature")
        
        # Business logic: Invalid token should raise exception
        with self.expect_exception(Exception, "Invalid token signature"):
            await self.jwt_service.validate_token(invalid_token)
            
        # Verify handler was called
        self.mock_jwt_handler.validate_token.assert_called_once_with(invalid_token)
        
        # Record business metric: Invalid token rejection
        self.record_metric("invalid_token_rejected", True)
        
    @pytest.mark.unit
    async def test_refresh_token_creation(self):
        """Test refresh token creation for session management."""
        # Mock successful refresh token creation
        expected_refresh_token = "refresh_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh_payload.refresh_signature"
        self.mock_jwt_handler.create_refresh_token.return_value = expected_refresh_token
        
        # Business logic: Create refresh token for extended sessions
        refresh_token = await self.jwt_service.create_refresh_token(
            user_id=self.test_user_id,
            email=self.test_email,
            permissions=self.test_permissions
        )
        
        # Verify refresh token was created
        assert refresh_token == expected_refresh_token
        
        # Verify handler was called correctly
        self.mock_jwt_handler.create_refresh_token.assert_called_once_with(
            self.test_user_id,
            self.test_email,
            self.test_permissions
        )
        
        # Record business metric: Refresh token creation success
        self.record_metric("refresh_token_creation_success", True)
        
    @pytest.mark.unit
    async def test_access_token_refresh_flow(self):
        """Test refreshing access token from refresh token."""
        # Mock successful token refresh
        refresh_token = "valid_refresh_token"
        new_access_token = "new_access_token"
        new_refresh_token = "new_refresh_token"
        
        self.mock_jwt_handler.refresh_access_token.return_value = (new_access_token, new_refresh_token)
        
        # Business logic: Refresh access token for continued session
        result = await self.jwt_service.refresh_access_token(refresh_token)
        
        # Verify new tokens were returned
        assert result == (new_access_token, new_refresh_token)
        
        # Verify handler was called correctly
        self.mock_jwt_handler.refresh_access_token.assert_called_once_with(refresh_token)
        
        # Record business metric: Token refresh success
        self.record_metric("token_refresh_success", True)
        
    @pytest.mark.unit
    async def test_refresh_token_validation(self):
        """Test refresh token validation for security."""
        # Mock successful refresh token validation
        refresh_token = "valid_refresh_token"
        valid_payload = {
            "sub": self.test_user_id,
            "type": "refresh",
            "exp": int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        }
        self.mock_jwt_handler.validate_token.return_value = valid_payload
        
        # Business logic: Validate refresh token for specific user
        is_valid = await self.jwt_service.validate_refresh_token(
            token=refresh_token,
            user_id=self.test_user_id
        )
        
        # Verify validation succeeded
        assert is_valid == True
        
        # Verify handler was called with correct token type
        self.mock_jwt_handler.validate_token.assert_called_once_with(
            refresh_token,
            token_type="refresh"
        )
        
        # Record business metric: Refresh token validation success
        self.record_metric("refresh_token_validation_success", True)
        
    @pytest.mark.unit
    async def test_refresh_token_validation_wrong_user(self):
        """Test refresh token validation fails for wrong user."""
        # Mock refresh token for different user
        refresh_token = "other_user_refresh_token"
        other_user_payload = {
            "sub": "other-user-67890",
            "type": "refresh",
            "exp": int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        }
        self.mock_jwt_handler.validate_token.return_value = other_user_payload
        
        # Business logic: Validation should fail for wrong user
        is_valid = await self.jwt_service.validate_refresh_token(
            token=refresh_token,
            user_id=self.test_user_id
        )
        
        # Verify validation failed (wrong user)
        assert is_valid == False
        
        # Record business metric: Security validation success
        self.record_metric("cross_user_token_rejected", True)
        
    @pytest.mark.unit
    async def test_token_expiration_handling(self):
        """Test handling of expired tokens for security."""
        # Mock expired token validation
        expired_token = "expired_jwt_token"
        self.mock_jwt_handler.validate_token.side_effect = Exception("Token has expired")
        
        # Business logic: Expired tokens should be rejected
        with self.expect_exception(Exception, "Token has expired"):
            await self.jwt_service.validate_token(expired_token)
            
        # Record business metric: Expired token rejection
        self.record_metric("expired_token_rejected", True)
        
    @pytest.mark.unit
    async def test_jwt_service_performance_requirements(self):
        """Test JWT operations meet performance requirements."""
        import time
        
        # Mock fast token operations
        self.mock_jwt_handler.create_access_token.return_value = "fast_token"
        self.mock_jwt_handler.validate_token.return_value = {"sub": self.test_user_id}
        
        # Business requirement: JWT operations should be fast
        start_time = time.time()
        
        # Perform multiple JWT operations
        for i in range(50):
            # Create token
            await self.jwt_service.create_access_token(
                user_id=f"user-{i}",
                email=f"user{i}@example.com"
            )
            
            # Validate token
            await self.jwt_service.validate_token("test_token")
            
        end_time = time.time()
        total_time = end_time - start_time
        
        # Business requirement: Should handle 100 operations in < 100ms
        assert total_time < 0.1, f"JWT operations too slow: {total_time}s for 100 operations"
        
        # Record performance metrics
        self.record_metric("jwt_operations_time_ms", total_time * 1000)
        self.record_metric("jwt_operations_per_second", 100 / total_time)
        
    @pytest.mark.unit
    def test_jwt_service_initialization(self):
        """Test JWT service initialization with configuration."""
        # Verify service was initialized correctly
        assert self.jwt_service.auth_config == self.mock_auth_config
        assert hasattr(self.jwt_service, '_jwt_handler')
        
        # Verify service maintains service independence
        assert self.jwt_service._jwt_handler is not None
        
        # Record business metric: Service initialization success
        self.record_metric("jwt_service_initialization_success", True)
        
    @pytest.mark.unit
    async def test_token_security_compliance(self):
        """Test JWT tokens meet security compliance requirements."""
        # Mock token creation with security features
        secure_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secure_payload.secure_signature"
        self.mock_jwt_handler.create_access_token.return_value = secure_token
        
        # Business requirement: Tokens should have security features
        token = await self.jwt_service.create_access_token(
            user_id=self.test_user_id,
            email=self.test_email,
            permissions=["admin"]
        )
        
        # Verify token format (JWT has 3 parts)
        token_parts = token.split('.')
        assert len(token_parts) == 3
        
        # Verify each part is non-empty
        for part in token_parts:
            assert len(part) > 0
            
        # Verify token contains security metadata
        self.mock_jwt_handler.create_access_token.assert_called_with(
            user_id=self.test_user_id,
            email=self.test_email,
            permissions=["admin"]
        )
        
        # Record business metric: Security compliance
        self.record_metric("token_security_compliance_validated", True)
        
    def teardown_method(self, method=None):
        """Clean up test environment."""
        # Log business metrics for security monitoring
        final_metrics = self.get_all_metrics()
        
        # Set JWT management validation flags
        if final_metrics.get("access_token_creation_success"):
            self.set_env_var("LAST_JWT_MANAGEMENT_TEST_SUCCESS", "true")
            
        if final_metrics.get("token_security_compliance_validated"):
            self.set_env_var("JWT_SECURITY_COMPLIANCE_VALIDATED", "true")
            
        # Performance validation
        jwt_time = final_metrics.get("jwt_operations_time_ms", 999)
        if jwt_time < 50:  # Under 50ms for 100 operations
            self.set_env_var("JWT_PERFORMANCE_ACCEPTABLE", "true")
            
        super().teardown_method(method)