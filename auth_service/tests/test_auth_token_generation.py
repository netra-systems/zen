"""
Authentication Token Generation Tests - JWT token creation and structure validation

Tests JWT token generation with various claims, token types, and security configurations.
Critical for ensuring secure token creation in the auth service.

Business Value Justification (BVJ):
- Segment: Platform/Security | Goal: Auth Foundation | Impact: Core Security
- Ensures secure JWT token generation for all authentication flows
- Validates token structure and claims for security compliance
- Foundation for all authentication and authorization in the platform

Test Coverage:
- Basic access token generation
- Access tokens with permission claims
- Refresh token generation with proper structure
- Service token generation for microservice communication
- Token structure validation and security compliance
"""

import os
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt

from auth_service.auth_core.core.jwt_handler import JWTHandler


class TestJWTTokenGeneration(unittest.TestCase):
    """Test JWT token generation with various claims"""
    
    def setUp(self):
        """Setup test environment"""
        self.jwt_handler = JWTHandler()
        self.test_user_id = "test-user-123"
        self.test_email = "test@example.com"
        self.test_permissions = ["read", "write", "admin"]
    
    def test_create_access_token_basic(self):
        """Test basic access token generation"""
        token = self.jwt_handler.create_access_token(
            self.test_user_id, 
            self.test_email
        )
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT structure
    
    def test_create_access_token_with_permissions(self):
        """Test access token with permission claims"""
        token = self.jwt_handler.create_access_token(
            self.test_user_id,
            self.test_email,
            self.test_permissions
        )
        payload = jwt.decode(
            token, 
            options={"verify_signature": False}
        )
        assert payload["permissions"] == self.test_permissions
    
    def test_create_access_token_structure(self):
        """Test access token has proper JWT structure and required claims"""
        token = self.jwt_handler.create_access_token(
            self.test_user_id,
            self.test_email,
            self.test_permissions
        )
        
        # Decode without verification to check structure
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Validate required claims
        assert payload["sub"] == self.test_user_id
        assert payload["email"] == self.test_email
        assert payload["permissions"] == self.test_permissions
        assert payload["token_type"] == "access"
        assert payload["iss"] == "netra-auth-service"
        assert "iat" in payload
        assert "exp" in payload
        
        # Validate token expiry is in the future
        exp_time = datetime.fromtimestamp(payload["exp"], timezone.utc)
        assert exp_time > datetime.now(timezone.utc)
    
    def test_create_refresh_token(self):
        """Test refresh token generation"""
        token = self.jwt_handler.create_refresh_token(self.test_user_id)
        payload = jwt.decode(
            token, 
            options={"verify_signature": False}
        )
        assert payload["sub"] == self.test_user_id
        assert payload["token_type"] == "refresh"
    
    def test_create_refresh_token_structure(self):
        """Test refresh token has proper structure and claims"""
        token = self.jwt_handler.create_refresh_token(self.test_user_id)
        
        # Decode without verification to check structure
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Validate required claims for refresh token
        assert payload["sub"] == self.test_user_id
        assert payload["token_type"] == "refresh"
        assert payload["iss"] == "netra-auth-service"
        assert "iat" in payload
        assert "exp" in payload
        
        # Refresh tokens should not have permissions
        assert "permissions" not in payload
        assert "email" not in payload
        
        # Validate refresh token has longer expiry than access token
        refresh_exp_time = datetime.fromtimestamp(payload["exp"], timezone.utc)
        
        # Create access token for comparison
        access_token = self.jwt_handler.create_access_token(self.test_user_id, self.test_email)
        access_payload = jwt.decode(access_token, options={"verify_signature": False})
        access_exp_time = datetime.fromtimestamp(access_payload["exp"], timezone.utc)
        
        assert refresh_exp_time > access_exp_time
    
    def test_create_service_token(self):
        """Test service token generation"""
        service_id = "service-123"
        service_name = "data-service"
        
        token = self.jwt_handler.create_service_token(
            service_id, 
            service_name
        )
        payload = jwt.decode(
            token, 
            options={"verify_signature": False}
        )
        assert payload["sub"] == service_id
        assert payload["service"] == service_name
        assert payload["token_type"] == "service"
    
    def test_create_service_token_structure(self):
        """Test service token has proper structure for microservice auth"""
        service_id = "backend-service"
        service_name = "netra-backend"
        
        token = self.jwt_handler.create_service_token(service_id, service_name)
        
        # Decode without verification to check structure
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Validate required claims for service token
        assert payload["sub"] == service_id
        assert payload["service"] == service_name
        assert payload["token_type"] == "service"
        assert payload["iss"] == "netra-auth-service"
        assert "iat" in payload
        assert "exp" in payload
        
        # Service tokens should not have user-specific claims
        assert "email" not in payload
        assert "permissions" not in payload
    
    def test_token_generation_timing(self):
        """Test token generation timing and consistency"""
        start_time = time.time()
        
        # Generate multiple tokens
        tokens = []
        for i in range(5):
            token = self.jwt_handler.create_access_token(
                f"user-{i}",
                f"user{i}@example.com"
            )
            tokens.append(token)
        
        generation_time = time.time() - start_time
        
        # Token generation should be fast
        assert generation_time < 1.0, f"Token generation took {generation_time:.3f}s, should be <1s"
        
        # All tokens should be unique
        assert len(set(tokens)) == len(tokens)
        
        # All tokens should have different issued at times
        issued_times = []
        for token in tokens:
            payload = jwt.decode(token, options={"verify_signature": False})
            issued_times.append(payload["iat"])
        
        # Due to timing, some might be the same, but most should be different
        unique_times = len(set(issued_times))
        assert unique_times >= len(issued_times) * 0.8
    
    def test_token_type_consistency(self):
        """Test that different token types have consistent structure"""
        user_id = "consistency-test-user"
        email = "consistency@example.com"
        service_id = "consistency-service"
        service_name = "consistency-test-service"
        
        # Generate different token types
        access_token = self.jwt_handler.create_access_token(user_id, email)
        refresh_token = self.jwt_handler.create_refresh_token(user_id)
        service_token = self.jwt_handler.create_service_token(service_id, service_name)
        
        # Decode all tokens
        access_payload = jwt.decode(access_token, options={"verify_signature": False})
        refresh_payload = jwt.decode(refresh_token, options={"verify_signature": False})
        service_payload = jwt.decode(service_token, options={"verify_signature": False})
        
        # All should have consistent basic structure
        for payload in [access_payload, refresh_payload, service_payload]:
            assert "sub" in payload
            assert "iat" in payload
            assert "exp" in payload
            assert "token_type" in payload
            assert "iss" in payload
            assert payload["iss"] == "netra-auth-service"
        
        # Validate token types are correct
        assert access_payload["token_type"] == "access"
        assert refresh_payload["token_type"] == "refresh"
        assert service_payload["token_type"] == "service"
        
        # Validate subject consistency
        assert access_payload["sub"] == user_id
        assert refresh_payload["sub"] == user_id
        assert service_payload["sub"] == service_id
    
    def test_token_expiry_configuration(self):
        """Test token expiry times are configured correctly"""
        # Generate tokens
        access_token = self.jwt_handler.create_access_token(self.test_user_id, self.test_email)
        refresh_token = self.jwt_handler.create_refresh_token(self.test_user_id)
        service_token = self.jwt_handler.create_service_token("test-service", "test")
        
        # Decode tokens
        access_payload = jwt.decode(access_token, options={"verify_signature": False})
        refresh_payload = jwt.decode(refresh_token, options={"verify_signature": False})
        service_payload = jwt.decode(service_token, options={"verify_signature": False})
        
        # Calculate expiry durations
        now = datetime.now(timezone.utc)
        access_exp = datetime.fromtimestamp(access_payload["exp"], timezone.utc)
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"], timezone.utc)
        service_exp = datetime.fromtimestamp(service_payload["exp"], timezone.utc)
        
        # Validate expiry relationships
        assert access_exp > now
        assert refresh_exp > now
        assert service_exp > now
        
        # Refresh tokens should have longer expiry than access tokens
        assert refresh_exp > access_exp
        
        # Validate approximate expiry durations (allowing for timing variations)
        access_duration = (access_exp - now).total_seconds()
        refresh_duration = (refresh_exp - now).total_seconds()
        service_duration = (service_exp - now).total_seconds()
        
        # Access tokens: ~15 minutes (900 seconds), allow ±60 seconds
        assert 840 <= access_duration <= 960, f"Access token duration: {access_duration}s"
        
        # Refresh tokens: ~7 days (604800 seconds), allow ±3600 seconds  
        assert 601200 <= refresh_duration <= 608400, f"Refresh token duration: {refresh_duration}s"
        
        # Service tokens: typically longer lived, at least 1 hour
        assert service_duration >= 3600, f"Service token duration: {service_duration}s"


# Business Impact Summary for Token Generation Tests
"""
Authentication Token Generation Tests - Business Impact

Security Foundation: Core Authentication Infrastructure
- Ensures secure JWT token generation for all authentication flows
- Validates token structure and claims for security compliance  
- Foundation for all authentication and authorization in the platform

Technical Excellence:
- JWT token generation: access, refresh, and service tokens with proper structure
- Token claims validation: user ID, email, permissions, and metadata
- Token timing: consistent generation performance and unique token creation
- Token type consistency: standardized structure across all token types
- Expiry configuration: proper token lifetime management for security

Platform Security:
- Platform: Secure token generation foundation for all authentication
- Security: JWT structure compliance for SOC2/GDPR requirements
- Microservices: Service token generation for inter-service communication
- Performance: Fast token generation (<1s) for responsive authentication
- Consistency: Standardized token structure across all authentication flows
"""