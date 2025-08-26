"""JWT Validation Failures - Failing Tests

Tests that replicate JWT token validation failures found in staging.
These tests are designed to FAIL to demonstrate current problems.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Token validation reliability and security
- Value Impact: Ensures JWT tokens validate correctly across services
- Strategic Impact: Prevents authentication failures affecting all service communication

Key Issues to Test:
1. JWT token validation with proper secret configuration
2. Handling of malformed tokens (not enough segments)
3. Signature verification failures
4. Cross-service token validation issues
"""

import os
import jwt
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.core.jwt_handler import JWTHandler
class TestJWTValidationSecretIssues:
    """Test JWT validation failures due to secret configuration issues."""
    
    @pytest.fixture
    def jwt_handler(self):
        """JWT handler instance for testing."""
        return JWTHandler()
    
    def test_jwt_validation_with_mismatched_secrets_fails(self, jwt_handler):
        """Test JWT validation when secrets don't match between services.
        
        ISSUE: Auth service and main backend may use different JWT secrets
        This test FAILS to demonstrate secret mismatch between services.
        """
        # Create token with one secret
        auth_secret = "auth-service-secret-12345678901234567890"
        backend_secret = "backend-service-secret-12345678901234567890"
        
        # Simulate auth service creating token with its secret
        payload = {
            "sub": "test-user-123",
            "email": "test@netrasystems.ai",
            "permissions": ["read", "write"],
            "token_type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "iss": "netra-auth-service"
        }
        
        auth_token = jwt.encode(payload, auth_secret, algorithm="HS256")
        
        # Simulate backend service trying to validate with different secret
        with patch.object(jwt_handler, 'secret', backend_secret):
            # EXPECTED: Token should validate if services use same secret
            # ACTUAL: Validation fails due to secret mismatch
            decoded = jwt_handler.validate_token_jwt(auth_token, "access")
            
            assert decoded is not None, \
                "JWT validation should succeed when auth service and backend use same secret"
            
            assert decoded["sub"] == "test-user-123", \
                f"Should decode user ID correctly, got: {decoded.get('sub') if decoded else 'None'}"
        
        # This test will FAIL because different services may use different JWT secrets
    
    def test_jwt_validation_with_environment_secret_mismatch_fails(self, jwt_handler):
        """Test JWT validation when environment-specific secrets are mismatched.
        
        ISSUE: Staging environment may use wrong JWT secret
        This test FAILS to demonstrate environment secret mismatch.
        """
        # Simulate development secret
        dev_env = {
            'ENVIRONMENT': 'development',
            'JWT_SECRET_KEY': 'dev-jwt-secret-1234567890123456789012345'
        }
        
        # Simulate staging secret
        staging_env = {
            'ENVIRONMENT': 'staging', 
            'JWT_SECRET_KEY': 'staging-jwt-secret-1234567890123456789012345',
            'JWT_SECRET_STAGING': 'different-staging-secret-1234567890123456789012345'
        }
        
        # Create token in development environment
        with patch.dict(os.environ, dev_env):
            dev_handler = JWTHandler()
            token = dev_handler.create_access_token(
                "user-123", 
                "user@netrasystems.ai", 
                ["read"]
            )
        
        # Try to validate in staging environment
        with patch.dict(os.environ, staging_env):
            staging_handler = JWTHandler()
            
            # EXPECTED: Token should validate if same secret is used
            # ACTUAL: Validation fails if staging uses different secret
            decoded = staging_handler.validate_token_jwt(token, "access")
            
            assert decoded is not None, \
                "JWT should validate across environments with consistent secret configuration"
        
        # This test will FAIL because environment-specific secrets may be inconsistent
    
    def test_jwt_secret_loading_priority_fails(self, jwt_handler):
        """Test JWT secret loading priority order.
        
        ISSUE: Secret loading may not follow correct priority chain
        This test FAILS to demonstrate incorrect secret priority.
        """
        # Set multiple JWT secret environment variables
        multi_secret_env = {
            'JWT_SECRET': 'legacy-secret-1234567890123456789012345',
            'JWT_SECRET_KEY': 'primary-secret-1234567890123456789012345', 
            'JWT_SECRET_STAGING': 'staging-secret-1234567890123456789012345',
            'ENVIRONMENT': 'staging'
        }
        
        with patch.dict(os.environ, multi_secret_env):
            # Get the secret through the configuration system
            secret = AuthConfig.get_jwt_secret()
            
            # EXPECTED: Should use staging-specific secret first, then JWT_SECRET_KEY
            # ACTUAL: May use wrong priority order
            assert secret == 'staging-secret-1234567890123456789012345', \
                f"Should prioritize JWT_SECRET_STAGING in staging environment, got: {secret}"
            
            # Should NOT use the legacy JWT_SECRET
            assert secret != 'legacy-secret-1234567890123456789012345', \
                "Should not use legacy JWT_SECRET when better options available"
        
        # This test will FAIL because secret loading doesn't follow correct priority


class TestJWTMalformedTokenHandling:
    """Test handling of malformed JWT tokens."""
    
    @pytest.fixture
    def jwt_handler(self):
        """JWT handler instance for testing."""
        return JWTHandler()
    
    def test_malformed_token_not_enough_segments_fails(self, jwt_handler):
        """Test handling of malformed tokens with insufficient segments.
        
        ISSUE: Malformed tokens may cause crashes instead of graceful failures
        This test FAILS to demonstrate improper error handling.
        """
        malformed_tokens = [
            "invalid",  # No segments
            "invalid.token",  # Only 2 segments
            "invalid.token.signature.extra",  # Too many segments
            "",  # Empty string
            ".",  # Just dot
            "..",  # Just dots
            "header..signature"  # Empty payload
        ]
        
        for malformed_token in malformed_tokens:
            # EXPECTED: Should handle malformed tokens gracefully and return None
            # ACTUAL: May raise exceptions or crash
            try:
                decoded = jwt_handler.validate_token_jwt(malformed_token, "access")
                
                assert decoded is None, \
                    f"Malformed token '{malformed_token}' should return None, got: {decoded}"
                
            except Exception as e:
                # EXPECTED: Should not raise exceptions for malformed tokens
                # ACTUAL: May raise exceptions instead of graceful handling
                pytest.fail(f"Should handle malformed token gracefully, but got exception: {e}")
        
        # This test will FAIL if malformed tokens cause exceptions or crashes
    
    def test_token_with_invalid_json_payload_fails(self, jwt_handler):
        """Test handling of tokens with invalid JSON payload.
        
        ISSUE: Invalid JSON in token payload may cause parsing errors
        This test FAILS to demonstrate JSON parsing error handling.
        """
        # Create token with invalid JSON payload
        import base64
        import json
        
        header = {"typ": "JWT", "alg": "HS256"}
        invalid_payload = '{"sub": "user", "exp": 1234567890, "invalid": json}'  # Invalid JSON
        
        encoded_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        encoded_payload = base64.urlsafe_b64encode(invalid_payload.encode()).decode().rstrip('=')
        
        # Create signature with correct secret
        message = f"{encoded_header}.{encoded_payload}"
        signature = jwt_handler._create_signature(message.encode())
        invalid_token = f"{message}.{signature}"
        
        # EXPECTED: Should handle invalid JSON gracefully
        # ACTUAL: May raise JSON parsing exceptions
        try:
            decoded = jwt_handler.validate_token_jwt(invalid_token, "access")
            
            assert decoded is None, \
                "Token with invalid JSON payload should return None"
                
        except Exception as e:
            # Should not crash on invalid JSON
            pytest.fail(f"Should handle invalid JSON gracefully, got: {e}")
        
        # This test will FAIL if invalid JSON causes unhandled exceptions
    
    def test_token_with_missing_required_claims_fails(self, jwt_handler):
        """Test handling of tokens missing required security claims.
        
        ISSUE: Tokens missing required claims may be accepted when they shouldn't be
        This test FAILS to demonstrate insufficient claim validation.
        """
        # Create token missing critical security claims
        incomplete_payload = {
            "sub": "user-123",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            # Missing: jti, iss, aud, token_type, env, svc_id
        }
        
        incomplete_token = jwt.encode(incomplete_payload, jwt_handler.secret, algorithm="HS256")
        
        # EXPECTED: Should reject token missing required security claims
        # ACTUAL: May accept token with insufficient claims
        decoded = jwt_handler.validate_token_jwt(incomplete_token, "access")
        
        assert decoded is None, \
            "Token missing required security claims (jti, iss, aud) should be rejected"
        
        # This test will FAIL if claim validation is not strict enough


class TestJWTCrossServiceValidation:
    """Test JWT validation across different services."""
    
    @pytest.fixture
    def jwt_handler(self):
        """JWT handler instance for testing."""
        return JWTHandler()
    
    def test_service_token_cross_validation_fails(self, jwt_handler):
        """Test service token validation between auth service and main backend.
        
        ISSUE: Service tokens may not validate properly across services
        This test FAILS to demonstrate cross-service validation issues.
        """
        # Create service token for auth service
        service_token = jwt_handler.create_service_token("auth-svc", "netra-auth-service")
        
        # Simulate main backend trying to validate this token
        backend_jwt_handler = JWTHandler()  # Should use same configuration
        
        # EXPECTED: Backend should validate auth service token
        # ACTUAL: May fail due to configuration differences
        decoded = backend_jwt_handler.validate_token_jwt(service_token, "service")
        
        assert decoded is not None, \
            "Service token should validate across services with same configuration"
        
        assert decoded["service"] == "netra-auth-service", \
            f"Should preserve service name, got: {decoded.get('service') if decoded else 'None'}"
        
        # This test will FAIL if cross-service validation doesn't work
    
    def test_user_token_backend_validation_fails(self, jwt_handler):
        """Test user token validation by main backend service.
        
        ISSUE: User tokens created by auth service may not validate in main backend
        This test FAILS to demonstrate user token validation issues.
        """
        # Create user token in auth service
        user_token = jwt_handler.create_access_token(
            "user-456",
            "cross-service@netrasystems.ai", 
            ["read", "write"]
        )
        
        # Simulate main backend validation
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_KEY': jwt_handler.secret  # Same secret
        }):
            # Main backend should validate auth service tokens
            decoded = jwt_handler.validate_token_jwt(user_token, "access")
            
            assert decoded is not None, \
                "User token from auth service should validate in main backend"
            
            assert decoded["email"] == "cross-service@netrasystems.ai", \
                f"Should preserve user email, got: {decoded.get('email') if decoded else 'None'}"
            
            assert "read" in decoded.get("permissions", []), \
                f"Should preserve permissions, got: {decoded.get('permissions') if decoded else 'None'}"
        
        # This test will FAIL if user tokens don't work across services
    
    def test_token_issuer_validation_fails(self, jwt_handler):
        """Test that token issuer validation works correctly.
        
        ISSUE: Token issuer validation may be too strict or too lenient
        This test FAILS to demonstrate issuer validation problems.
        """
        # Create token with correct issuer
        valid_payload = {
            "sub": "user-789",
            "email": "issuer-test@netrasystems.ai",
            "token_type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "iss": "netra-auth-service",  # Correct issuer
            "aud": "netra-platform"
        }
        
        valid_token = jwt.encode(valid_payload, jwt_handler.secret, algorithm="HS256")
        
        # Should validate with correct issuer
        decoded = jwt_handler.validate_token_jwt(valid_token, "access")
        assert decoded is not None, \
            "Token with correct issuer should validate"
        
        # Create token with wrong issuer
        invalid_payload = valid_payload.copy()
        invalid_payload["iss"] = "fake-service"
        
        invalid_token = jwt.encode(invalid_payload, jwt_handler.secret, algorithm="HS256")
        
        # EXPECTED: Should reject token with wrong issuer
        # ACTUAL: May accept tokens from unauthorized issuers
        decoded_invalid = jwt_handler.validate_token_jwt(invalid_token, "access")
        
        assert decoded_invalid is None, \
            "Token with incorrect issuer should be rejected"
        
        # This test will FAIL if issuer validation is not properly enforced


class TestStagingSpecificJWTIssues:
    """Test staging-specific JWT validation issues."""
    
    @pytest.fixture 
    def jwt_handler(self):
        """JWT handler instance for testing."""
        return JWTHandler()
    
    def test_staging_token_expiry_configuration_fails(self, jwt_handler):
        """Test that staging uses appropriate token expiry times.
        
        ISSUE: Staging may use wrong token expiry configuration
        This test FAILS to demonstrate incorrect expiry settings.
        """
        # Create token in staging environment
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            staging_handler = JWTHandler()
            token = staging_handler.create_access_token("staging-user", "staging@netrasystems.ai")
            
            # Decode without verification to check expiry
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            exp_timestamp = decoded.get("exp")
            iat_timestamp = decoded.get("iat")
            
            # Calculate token lifetime
            token_lifetime_seconds = exp_timestamp - iat_timestamp
            token_lifetime_minutes = token_lifetime_seconds / 60
            
            # EXPECTED: Staging should use production-like expiry (15 minutes)
            # ACTUAL: May use development expiry (longer) or wrong configuration
            assert 10 <= token_lifetime_minutes <= 20, \
                f"Staging tokens should have 15-minute expiry, got: {token_lifetime_minutes} minutes"
            
            # Should not use very long development expiries in staging
            assert token_lifetime_minutes < 60, \
                f"Staging should not use long development expiry, got: {token_lifetime_minutes} minutes"
        
        # This test will FAIL if staging uses wrong token expiry configuration
    
    def test_staging_jwt_algorithm_configuration_fails(self, jwt_handler):
        """Test that staging uses secure JWT algorithm.
        
        ISSUE: Staging may use insecure JWT algorithm
        This test FAILS to demonstrate insecure algorithm usage.
        """
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            staging_handler = JWTHandler()
            
            # EXPECTED: Should use secure algorithm (HS256 or RS256)
            # ACTUAL: May use insecure algorithm
            algorithm = staging_handler.algorithm
            
            secure_algorithms = ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']
            
            assert algorithm in secure_algorithms, \
                f"Staging should use secure JWT algorithm, got: {algorithm}"
            
            # Should definitely not use 'none' algorithm
            assert algorithm != 'none', \
                "Staging must not use 'none' algorithm (security vulnerability)"
        
        # This test will FAIL if staging uses insecure JWT algorithms
    
    def test_staging_service_id_validation_fails(self, jwt_handler):
        """Test that staging validates service IDs properly.
        
        ISSUE: Staging service ID validation may be misconfigured
        This test FAILS to demonstrate service ID validation problems.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'SERVICE_ID': 'netra-auth-staging-instance'
        }):
            staging_handler = JWTHandler()
            
            # Create token with service ID
            token = staging_handler.create_access_token("service-user", "service@netrasystems.ai")
            
            # Decode to check service ID claim
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # EXPECTED: Should include correct staging service ID
            # ACTUAL: May use wrong service ID or miss it entirely
            service_id = decoded.get("svc_id")
            
            assert service_id == "netra-auth-staging-instance", \
                f"Expected staging service ID in token, got: {service_id}"
            
            # Should not use development service ID in staging
            assert "dev" not in service_id.lower(), \
                f"Staging should not use dev service ID, got: {service_id}"
        
        # This test will FAIL if staging service ID validation is wrong


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])