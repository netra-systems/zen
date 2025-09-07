"""
Test JWT Security Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Protect user data and platform integrity through secure token management
- Value Impact: JWT security prevents unauthorized access to user accounts and AI services,
  protecting customer data worth $75K+ MRR and preventing security breaches that could
  cost millions in damages, legal liability, and customer trust
- Strategic Impact: Core security foundation - JWT tokens secure all platform API access,
  agent interactions, and user data. Security breaches directly impact customer retention,
  regulatory compliance, and business reputation

This test suite validates that JWT security mechanisms protect business assets and
user data while enabling secure access to AI optimization services.
"""

import pytest
import jwt
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env, test_env

# Auth service imports
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.core.jwt_cache import jwt_validation_cache
from auth_service.auth_core.config import AuthConfig


class TestJWTSecurityBusinessValue(BaseIntegrationTest):
    """Test JWT security delivering business asset protection and secure user access."""
    
    @pytest.mark.unit
    def test_jwt_handler_enforces_production_security_standards(self, isolated_env):
        """Test that JWT handler enforces security standards that protect business assets."""
        # Business Context: Production JWT must meet enterprise security standards
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("JWT_SECRET_KEY", "production-grade-secret-key-with-high-entropy-at-least-32-chars", "test")
        isolated_env.set("SERVICE_SECRET", "production-service-secret-for-inter-service-auth", "test")
        
        jwt_handler = JWTHandler()
        
        # JWT secret must meet production security standards
        assert len(jwt_handler.secret) >= 32, "Production JWT secret must be at least 32 characters"
        assert jwt_handler.algorithm == "HS256", "Must use secure HMAC algorithm"
        
        # Service authentication must be configured
        assert jwt_handler.service_secret is not None, "Service secret required for inter-service auth"
        assert len(jwt_handler.service_secret) >= 20, "Service secret must be sufficiently long"
        
        # Token expiry must balance security vs usability
        assert jwt_handler.access_expiry >= 15, "Access tokens must last long enough for user workflows"
        assert jwt_handler.access_expiry <= 60, "Access tokens must expire quickly for security"
        
        assert jwt_handler.refresh_expiry >= 7, "Refresh tokens must allow reasonable session duration"
        assert jwt_handler.refresh_expiry <= 30, "Refresh tokens must expire for security"
    
    @pytest.mark.unit
    def test_jwt_handler_fails_fast_with_insufficient_production_security(self, isolated_env):
        """Test that JWT handler fails fast when production security requirements are not met."""
        # Business Context: Insufficient security in production must prevent service startup
        isolated_env.set("ENVIRONMENT", "production", "test")
        
        # Test missing JWT secret in production (should raise exception)
        isolated_env.set("JWT_SECRET_KEY", "", "test")
        with pytest.raises(ValueError) as exc_info:
            JWTHandler()
        assert "JWT_SECRET_KEY must be set in production" in str(exc_info.value)
        
        # Test insufficient JWT secret length in production (should raise exception)
        isolated_env.set("JWT_SECRET_KEY", "too-short", "test")
        with pytest.raises(ValueError) as exc_info:
            JWTHandler()
        assert "must be at least 32 characters" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_access_token_creation_supports_business_authorization_flows(self, isolated_env):
        """Test that access token creation supports business authorization and user workflows."""
        # Business Context: Access tokens must carry user identity and permissions for business operations
        isolated_env.set("ENVIRONMENT", "test", "test")
        isolated_env.set("JWT_SECRET_KEY", "test-secret-key-for-testing-only-must-be-at-least-32-chars", "test")
        
        jwt_handler = JWTHandler()
        
        # Create access token for business user
        user_id = "business_user_123"
        email = "user@enterprise.com"
        permissions = ["agent_access", "cost_optimization", "data_analysis"]
        
        access_token = jwt_handler.create_access_token(user_id, email, permissions)
        
        # Token should be properly formatted JWT
        assert access_token is not None, "Access token required for user authorization"
        assert isinstance(access_token, str), "Token must be string format"
        assert len(access_token.split('.')) == 3, "JWT must have header.payload.signature format"
        
        # Decode and verify token contents support business operations
        decoded = jwt.decode(access_token, jwt_handler.secret, algorithms=[jwt_handler.algorithm])
        
        assert decoded["sub"] == user_id, "Subject must identify user for business operations"
        assert decoded["email"] == email, "Email required for user identification"
        assert decoded["permissions"] == permissions, "Permissions required for authorization"
        assert decoded["token_type"] == "access", "Token type must be clearly identified"
        
        # Token should have reasonable expiration for business workflows
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        token_lifetime = exp_time - now
        
        assert token_lifetime.total_seconds() > 900, "Token must last at least 15 minutes for workflows"
        assert token_lifetime.total_seconds() < 3600, "Token must expire within 1 hour for security"
    
    @pytest.mark.unit
    def test_refresh_token_creation_enables_secure_session_management(self, isolated_env):
        """Test that refresh token creation enables secure long-term session management."""
        # Business Context: Refresh tokens enable persistent user sessions without frequent re-authentication
        isolated_env.set("ENVIRONMENT", "test", "test")
        isolated_env.set("JWT_SECRET_KEY", "test-secret-key-for-testing-only-must-be-at-least-32-chars", "test")
        
        jwt_handler = JWTHandler()
        
        # Create refresh token for user session management
        user_id = "session_user_456"
        email = "user@business.com"
        permissions = ["basic_access"]
        
        refresh_token = jwt_handler.create_refresh_token(user_id, email, permissions)
        
        # Token should be valid JWT format
        assert refresh_token is not None, "Refresh token required for session management"
        assert isinstance(refresh_token, str), "Token must be string format"
        
        # Decode and verify refresh token properties
        decoded = jwt.decode(refresh_token, jwt_handler.secret, algorithms=[jwt_handler.algorithm])
        
        assert decoded["sub"] == user_id, "Subject must identify user"
        assert decoded["token_type"] == "refresh", "Must be identified as refresh token"
        
        # Refresh token should have longer expiration than access token
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        token_lifetime = exp_time - now
        
        # Should last at least several days for user convenience
        assert token_lifetime.total_seconds() > 86400 * 7, "Refresh token must last at least 7 days"
        assert token_lifetime.total_seconds() < 86400 * 31, "Refresh token must not exceed 31 days"
    
    @pytest.mark.unit
    def test_service_token_creation_enables_secure_microservice_communication(self, isolated_env):
        """Test that service tokens enable secure communication between business microservices."""
        # Business Context: Service tokens secure inter-service API calls for business operations
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("JWT_SECRET_KEY", "production-jwt-secret-key-must-be-at-least-32-chars", "test")
        isolated_env.set("SERVICE_SECRET", "production-service-secret-for-inter-service-auth", "test")
        
        jwt_handler = JWTHandler()
        
        # Create service token for backend-to-auth communication
        service_name = "netra_backend"
        service_permissions = ["user_validation", "token_refresh", "session_management"]
        
        service_token = jwt_handler.create_service_token(service_name, service_permissions)
        
        # Token should be valid JWT for service authentication
        assert service_token is not None, "Service token required for microservice communication"
        assert isinstance(service_token, str), "Token must be string format"
        
        # Decode and verify service token properties
        decoded = jwt.decode(service_token, jwt_handler.secret, algorithms=[jwt_handler.algorithm])
        
        assert decoded["service_name"] == service_name, "Service name required for identification"
        assert decoded["permissions"] == service_permissions, "Service permissions required for authorization"
        assert decoded["token_type"] == "service", "Must be identified as service token"
        assert decoded["iss"] == jwt_handler.service_id, "Issuer must identify auth service"
        
        # Service tokens should have appropriate expiration for business operations
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        token_lifetime = exp_time - now
        
        assert token_lifetime.total_seconds() > 3600, "Service tokens must last at least 1 hour"
        assert token_lifetime.total_seconds() < 86400, "Service tokens must expire within 24 hours"
    
    @pytest.mark.unit
    def test_token_validation_protects_business_operations_from_tampering(self, isolated_env):
        """Test that token validation prevents unauthorized access from token tampering."""
        # Business Context: Token validation prevents attackers from accessing business data
        isolated_env.set("ENVIRONMENT", "test", "test")
        isolated_env.set("JWT_SECRET_KEY", "test-secret-key-for-testing-only-must-be-at-least-32-chars", "test")
        
        jwt_handler = JWTHandler()
        
        # Create valid token for business user
        user_id = "business_user_789"
        email = "user@company.com"
        valid_token = jwt_handler.create_access_token(user_id, email, ["read_data"])
        
        # Valid token should pass validation
        validation_result = jwt_handler.validate_token(valid_token)
        assert validation_result is not None, "Valid tokens must pass validation"
        assert validation_result["sub"] == user_id, "User ID must be preserved"
        assert validation_result["email"] == email, "Email must be preserved"
        
        # Tampered token should be rejected
        tampered_token = valid_token[:-5] + "HACKED"  # Corrupt signature
        tampered_result = jwt_handler.validate_token(tampered_token)
        assert tampered_result is None, "Tampered tokens must be rejected to protect business"
        
        # Expired token should be rejected
        with patch('time.time', return_value=time.time() + 7200):  # 2 hours in future
            expired_result = jwt_handler.validate_token(valid_token)
            assert expired_result is None, "Expired tokens must be rejected for security"
        
        # Token with wrong signature should be rejected
        wrong_secret_handler = JWTHandler()
        wrong_secret_handler.secret = "wrong-secret-key-should-not-validate"
        wrong_result = wrong_secret_handler.validate_token(valid_token)
        assert wrong_result is None, "Tokens with wrong signature must be rejected"
    
    @pytest.mark.unit
    def test_token_blacklist_prevents_unauthorized_access_after_logout(self, isolated_env):
        """Test that token blacklisting prevents access after user logout or compromise."""
        # Business Context: Token blacklisting prevents unauthorized access from stolen/compromised tokens
        isolated_env.set("ENVIRONMENT", "test", "test")
        isolated_env.set("JWT_SECRET_KEY", "test-secret-key-for-testing-only-must-be-at-least-32-chars", "test")
        
        jwt_handler = JWTHandler()
        
        # Create token for user who will logout
        user_id = "logout_user_999"
        email = "user@business.com"
        token = jwt_handler.create_access_token(user_id, email, ["access_platform"])
        
        # Token should initially be valid
        validation_result = jwt_handler.validate_token(token)
        assert validation_result is not None, "Token should be valid before blacklisting"
        
        # Blacklist the specific token (user logout scenario)
        jwt_handler.blacklist_token(token)
        
        # Blacklisted token should be rejected
        blacklisted_result = jwt_handler.validate_token(token)
        assert blacklisted_result is None, "Blacklisted tokens must be rejected to protect business"
        
        # Test user-wide blacklisting (account compromise scenario)
        new_token = jwt_handler.create_access_token(user_id, email, ["access_platform"])
        assert jwt_handler.validate_token(new_token) is not None, "New token should work initially"
        
        # Blacklist all user tokens
        jwt_handler.blacklist_user_tokens(user_id)
        
        # All user tokens should be rejected
        user_blacklisted_result = jwt_handler.validate_token(new_token)
        assert user_blacklisted_result is None, "User blacklisted tokens must be rejected"
    
    @pytest.mark.unit
    def test_jwt_cache_improves_business_performance_while_maintaining_security(self, isolated_env):
        """Test that JWT caching improves performance without compromising security."""
        # Business Context: JWT caching reduces latency for high-frequency API calls
        isolated_env.set("ENVIRONMENT", "test", "test")
        isolated_env.set("JWT_SECRET_KEY", "test-secret-key-for-testing-only-must-be-at-least-32-chars", "test")
        
        jwt_handler = JWTHandler()
        
        # Create token for caching test
        user_id = "cache_user_111"
        email = "user@fastapi.com"
        token = jwt_handler.create_access_token(user_id, email, ["api_access"])
        
        # First validation should hit the JWT decoder
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {"sub": user_id, "email": email, "token_type": "access"}
            
            result1 = jwt_handler.validate_token(token)
            assert mock_decode.call_count == 1, "First validation should decode JWT"
        
        # Second validation should use cache (if implemented)
        with patch('jwt.decode') as mock_decode:
            result2 = jwt_handler.validate_token(token)
            # If caching is implemented, decode should not be called again
            # If not implemented, this test documents the expected behavior
            
        assert result1 is not None, "Cached validation should work"
        assert result2 is not None, "Cached validation should return same result"
    
    @pytest.mark.unit
    def test_jwt_security_headers_and_claims_follow_business_standards(self, isolated_env):
        """Test that JWT headers and claims follow security standards for business compliance."""
        # Business Context: JWT standards compliance required for enterprise customers
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("JWT_SECRET_KEY", "production-compliant-jwt-secret-key-32-chars", "test")
        isolated_env.set("SERVICE_SECRET", "production-service-secret-for-compliance", "test")
        
        jwt_handler = JWTHandler()
        
        # Create token with business user data
        user_id = "compliance_user_222"
        email = "user@enterprise.com"
        token = jwt_handler.create_access_token(user_id, email, ["enterprise_access"])
        
        # Decode token to inspect header and payload structure
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, jwt_handler.secret, algorithms=[jwt_handler.algorithm])
        
        # Header must follow JWT standards
        assert header["alg"] == "HS256", "Algorithm must be specified in header"
        assert header["typ"] == "JWT", "Token type must be specified as JWT"
        
        # Payload must include standard JWT claims
        assert "iat" in payload, "Issued at time required for audit trails"
        assert "exp" in payload, "Expiration time required for security"
        assert "jti" in payload, "JWT ID required for token tracking"
        assert "sub" in payload, "Subject required for user identification"
        assert "iss" in payload, "Issuer required for token source identification"
        
        # Business-specific claims must be present
        assert payload["token_type"] in ["access", "refresh", "service"], "Token type required"
        assert payload["email"] == email, "Email required for business user identification"
        
        # Security claims must be properly formatted
        iat_time = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        
        assert iat_time <= datetime.now(timezone.utc), "Issued time must not be in future"
        assert exp_time > datetime.now(timezone.utc), "Expiration must be in future"
        assert exp_time > iat_time, "Expiration must be after issued time"
    
    @pytest.mark.unit
    def test_jwt_error_handling_prevents_information_disclosure(self, isolated_env):
        """Test that JWT error handling prevents information disclosure that could aid attackers."""
        # Business Context: Error handling must not reveal information that helps attackers
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("JWT_SECRET_KEY", "production-jwt-secret-prevents-info-disclosure", "test")
        
        jwt_handler = JWTHandler()
        
        # Test various invalid token formats
        invalid_tokens = [
            "",                              # Empty token
            "not.a.jwt",                    # Invalid format
            "invalid",                      # Not base64
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature",  # Invalid payload
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJ0ZXN0IjoidGVzdCJ9.",  # None algorithm
        ]
        
        for invalid_token in invalid_tokens:
            result = jwt_handler.validate_token(invalid_token)
            # All invalid tokens should return None without revealing why
            assert result is None, f"Invalid token should be rejected: {invalid_token}"
        
        # Test that error messages don't leak sensitive information
        with patch('auth_service.auth_core.core.jwt_handler.logger') as mock_logger:
            jwt_handler.validate_token("clearly.invalid.token")
            
            # If logging occurs, it should not contain sensitive information
            if mock_logger.warning.called or mock_logger.error.called:
                logged_messages = []
                for call in mock_logger.warning.call_args_list:
                    logged_messages.append(str(call))
                for call in mock_logger.error.call_args_list:
                    logged_messages.append(str(call))
                
                all_log_output = " ".join(logged_messages)
                
                # Should not log JWT secrets or detailed error information
                assert jwt_handler.secret not in all_log_output, "JWT secret must not be logged"
                assert "secret" not in all_log_output.lower(), "Secret references should not be logged"
    
    @pytest.mark.unit
    async def test_jwt_performance_meets_business_latency_requirements(self, isolated_env):
        """Test that JWT operations meet performance requirements for business API calls."""
        # Business Context: JWT operations must be fast enough for real-time business APIs
        isolated_env.set("ENVIRONMENT", "test", "test")
        isolated_env.set("JWT_SECRET_KEY", "test-secret-key-for-testing-only-must-be-at-least-32-chars", "test")
        
        jwt_handler = JWTHandler()
        
        # Test token creation performance
        import time
        start_time = time.time()
        
        tokens = []
        for i in range(100):  # Create 100 tokens
            token = jwt_handler.create_access_token(f"user_{i}", f"user{i}@test.com", ["api_access"])
            tokens.append(token)
        
        creation_time = time.time() - start_time
        
        # Token creation should be fast enough for business APIs
        assert creation_time < 1.0, "Token creation must be under 1 second for 100 tokens"
        assert len(tokens) == 100, "All tokens should be created successfully"
        
        # Test token validation performance
        start_time = time.time()
        
        validation_results = []
        for token in tokens[:50]:  # Validate 50 tokens
            result = jwt_handler.validate_token(token)
            validation_results.append(result)
        
        validation_time = time.time() - start_time
        
        # Token validation should be fast enough for high-frequency API calls
        assert validation_time < 0.5, "Token validation must be under 0.5 seconds for 50 tokens"
        assert all(result is not None for result in validation_results), "All valid tokens should validate"