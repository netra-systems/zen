"""
OAuth JWT Security Validator Tests

Tests for the JWTSecurityValidator class which provides critical security validations
for JWT tokens in OAuth flows, including algorithm security and token integrity checks.
"""

import base64
import json
import os
import secrets
from unittest.mock import Mock, patch
import pytest
import jwt

from auth_service.auth_core.security.oauth_security import JWTSecurityValidator


class TestOAuthJWTSecurityValidator:
    """Test JWT security validation for OAuth flows"""
    
    def setup_method(self):
        """Setup for each test"""
        # Mock the AuthSecretLoader to provide a test secret
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader') as mock_loader:
            mock_loader.get_jwt_secret.return_value = "test_secret_key_that_is_long_enough_for_security"
            self.validator = JWTSecurityValidator()
    
    def test_jwt_security_validator_initialization_with_strong_secret(self):
        """Test that validator initializes with strong JWT secret"""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader') as mock_loader:
            strong_secret = "a" * 32  # 32+ character secret
            mock_loader.get_jwt_secret.return_value = strong_secret
            
            with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
                validator = JWTSecurityValidator()
                assert validator.strong_secret == strong_secret
    
    def test_jwt_security_validator_rejects_weak_secret_in_production(self):
        """Test that validator rejects weak secrets in production"""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader') as mock_loader:
            weak_secret = "short"  # Less than 32 characters
            mock_loader.get_jwt_secret.return_value = weak_secret
            
            with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
                with pytest.raises(ValueError, match="JWT_SECRET_KEY must be at least 32 characters in production"):
                    JWTSecurityValidator()
    
    def test_jwt_security_validator_allows_weak_secret_in_development(self):
        """Test that validator allows weak secrets in development"""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader') as mock_loader:
            weak_secret = "short"  # Less than 32 characters
            mock_loader.get_jwt_secret.return_value = weak_secret
            
            with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
                validator = JWTSecurityValidator()
                assert validator.strong_secret == weak_secret
    
    def test_jwt_security_validator_requires_configured_secret(self):
        """Test that validator requires JWT secret to be configured"""
        with patch('auth_service.auth_core.secret_loader.AuthSecretLoader') as mock_loader:
            mock_loader.get_jwt_secret.side_effect = ValueError("JWT secret not configured")
            
            with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
                with pytest.raises(ValueError, match="JWT secret not configured for development environment"):
                    JWTSecurityValidator()
    
    def test_validate_token_security_with_safe_algorithm(self):
        """Test token security validation with safe HS256 algorithm"""
        # Create a test token with HS256 algorithm
        test_payload = {"user_id": "123", "exp": 9999999999}
        test_token = jwt.encode(test_payload, self.validator.strong_secret, algorithm="HS256")
        
        is_secure = self.validator.validate_token_security(test_token)
        assert is_secure is True
    
    def test_validate_token_security_with_rs256_algorithm(self):
        """Test token security validation accepts RS256 algorithm"""
        # Mock a token header with RS256
        test_header = {"alg": "RS256", "typ": "JWT"}
        
        with patch('jwt.get_unverified_header', return_value=test_header):
            is_secure = self.validator.validate_token_security("fake_token")
            assert is_secure is True
    
    def test_validate_token_security_rejects_none_algorithm(self):
        """Test token security validation rejects 'none' algorithm (critical security)"""
        # Mock a token header with 'none' algorithm (algorithm confusion attack)
        test_header = {"alg": "none", "typ": "JWT"}
        
        with patch('jwt.get_unverified_header', return_value=test_header):
            is_secure = self.validator.validate_token_security("fake_token")
            assert is_secure is False
    
    def test_validate_token_security_rejects_insecure_algorithms(self):
        """Test token security validation rejects insecure algorithms"""
        insecure_algorithms = ["HS1", "MD5", "SHA1", "custom_algo"]
        
        for algorithm in insecure_algorithms:
            test_header = {"alg": algorithm, "typ": "JWT"}
            
            with patch('jwt.get_unverified_header', return_value=test_header):
                is_secure = self.validator.validate_token_security("fake_token")
                assert is_secure is False, f"Algorithm {algorithm} should be rejected"
    
    def test_validate_token_security_handles_malformed_token(self):
        """Test token security validation handles malformed tokens gracefully"""
        malformed_tokens = [
            "not.a.jwt",
            "invalid_base64.token.here",
            "...",
            "",
            None
        ]
        
        for malformed_token in malformed_tokens:
            if malformed_token is None:
                continue  # Skip None as it would cause different error
                
            is_secure = self.validator.validate_token_security(malformed_token)
            assert is_secure is False
    
    def test_validate_token_security_handles_token_without_header(self):
        """Test token security validation handles token without proper header"""
        # Create a malformed JWT without proper header
        malformed_token = "invalid_header." + base64.b64encode(b'{"exp":999}').decode() + ".signature"
        
        is_secure = self.validator.validate_token_security(malformed_token)
        assert is_secure is False
    
    def test_validate_token_security_algorithm_case_sensitivity(self):
        """Test that algorithm validation is case sensitive (security requirement)"""
        # Test lowercase version of valid algorithm
        test_header = {"alg": "hs256", "typ": "JWT"}  # lowercase instead of HS256
        
        with patch('jwt.get_unverified_header', return_value=test_header):
            is_secure = self.validator.validate_token_security("fake_token")
            assert is_secure is False  # Should reject lowercase
    
    def test_validate_token_security_missing_algorithm_header(self):
        """Test token security validation handles missing algorithm in header"""
        # Token header without 'alg' field
        test_header = {"typ": "JWT"}
        
        with patch('jwt.get_unverified_header', return_value=test_header):
            is_secure = self.validator.validate_token_security("fake_token")
            assert is_secure is False
    
    def test_validate_token_security_empty_algorithm_header(self):
        """Test token security validation handles empty algorithm in header"""
        # Token header with empty 'alg' field
        test_header = {"alg": "", "typ": "JWT"}
        
        with patch('jwt.get_unverified_header', return_value=test_header):
            is_secure = self.validator.validate_token_security("fake_token")
            assert is_secure is False
    
    def test_validate_token_security_algorithm_confusion_attack_prevention(self):
        """Test protection against JWT algorithm confusion attacks"""
        # Test various algorithm confusion attack vectors
        attack_algorithms = [
            "none",           # Most common attack
            "None",           # Case variation
            "NONE",           # Case variation
            "nOnE",           # Mixed case
            "HS256\x00",      # Null byte injection
            "HS256 ",         # Trailing space
            " HS256",         # Leading space
        ]
        
        for attack_alg in attack_algorithms:
            test_header = {"alg": attack_alg, "typ": "JWT"}
            
            with patch('jwt.get_unverified_header', return_value=test_header):
                is_secure = self.validator.validate_token_security("fake_token")
                assert is_secure is False, f"Algorithm confusion attack with '{attack_alg}' should be blocked"
    
    def test_validate_token_security_allowed_algorithms_list(self):
        """Test that only explicitly allowed algorithms are accepted"""
        # Verify the allowed algorithms list
        assert "HS256" in self.validator.allowed_algorithms
        assert "RS256" in self.validator.allowed_algorithms
        assert "none" not in self.validator.allowed_algorithms
        assert len(self.validator.allowed_algorithms) == 2  # Only these two should be allowed
    
    def test_validate_token_security_logging_security_warnings(self):
        """Test that security violations are properly logged"""
        test_header = {"alg": "none", "typ": "JWT"}
        
        with patch('jwt.get_unverified_header', return_value=test_header):
            with patch('auth_service.auth_core.security.oauth_security.logger') as mock_logger:
                self.validator.validate_token_security("fake_token")
                
                # Verify security warning was logged
                mock_logger.warning.assert_called_once()
                logged_message = mock_logger.warning.call_args[0][0]
                assert "insecure jwt algorithm: none" in logged_message.lower()
    
    def test_validate_token_security_exception_handling_and_logging(self):
        """Test that exceptions are properly handled and logged during validation"""
        with patch('jwt.get_unverified_header', side_effect=Exception("JWT parsing error")):
            with patch('auth_service.auth_core.security.oauth_security.logger') as mock_logger:
                is_secure = self.validator.validate_token_security("fake_token")
                
                assert is_secure is False
                mock_logger.error.assert_called_once()
                logged_message = mock_logger.error.call_args[0][0]
                assert "JWT security validation error" in logged_message
    
    def test_validate_token_security_real_jwt_token_validation(self):
        """Test validation with real JWT tokens created with different algorithms"""
        test_payload = {"user_id": "123", "email": "test@example.com"}
        
        # Test with HS256 (should pass)
        hs256_token = jwt.encode(test_payload, "secret", algorithm="HS256")
        assert self.validator.validate_token_security(hs256_token) is True
        
        # Note: RS256 requires key pair, so we'll mock the header check
        # as done in other tests rather than creating real RS256 token
    
    def test_validate_token_security_integration_with_oauth_flow(self):
        """Test JWT security validation integration within OAuth context"""
        # This test ensures the validator works correctly when called
        # during OAuth token validation workflows
        
        # Simulate an OAuth access token
        oauth_payload = {
            "aud": "oauth_client_id",
            "iss": "https://accounts.google.com",
            "email": "user@example.com",
            "sub": "oauth_user_id"
        }
        
        # Create token with secure algorithm
        secure_token = jwt.encode(oauth_payload, self.validator.strong_secret, algorithm="HS256")
        assert self.validator.validate_token_security(secure_token) is True
        
        # Test with insecure algorithm (mocked)
        insecure_header = {"alg": "none", "typ": "JWT"}
        with patch('jwt.get_unverified_header', return_value=insecure_header):
            assert self.validator.validate_token_security("fake_oauth_token") is False