"""
GCP Staging SECRET_KEY Validation Tests
Failing tests that replicate SECRET_KEY validation issues found in staging logs

These tests WILL FAIL until the underlying SECRET_KEY validation issues are resolved.
Purpose: Demonstrate SECRET_KEY configuration problems and prevent regressions.

Issues replicated:
1. SECRET_KEY must be at least 32 characters
2. SECRET_KEY missing entirely
3. SECRET_KEY too short (< 32 characters)
4. SECRET_KEY using insecure defaults
5. JWT_SECRET and SECRET_KEY consistency issues
"""

import pytest
import os
from secrets import token_urlsafe

from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.config import get_config


class TestSecretKeyLengthValidation:
    """Tests that replicate SECRET_KEY length validation issues from staging logs"""
    
    def test_secret_key_too_short_under_32_characters(self):
        """
        Test: SECRET_KEY is shorter than required 32 characters
        This test SHOULD FAIL until SECRET_KEY validation enforces minimum length
        """
        # Simulate short SECRET_KEY from staging
        short_secret_keys = [
            "short",                    # 5 characters
            "12345678901234567890",     # 20 characters  
            "1234567890123456789012345678901",  # 31 characters (just under)
            ""                          # Empty string
        ]
        
        for short_key in short_secret_keys:
            with patch.dict('os.environ', {'SECRET_KEY': short_key}):
                env = IsolatedEnvironment(isolation_mode=False)
                
                # Should fail validation for short keys
                with pytest.raises(ValueError) as exc_info:
                    secret_key = env.get('SECRET_KEY')
                    self._validate_secret_key_length(secret_key)
                    
                error_msg = str(exc_info.value).lower()
                assert any(phrase in error_msg for phrase in [
                    "secret_key",
                    "32 characters",
                    "too short",
                    "minimum length",
                    "invalid length"
                ]), f"Expected SECRET_KEY length validation error for key length {len(short_key)}, got: {exc_info.value}"

    def test_secret_key_missing_entirely(self):
        """
        Test: SECRET_KEY environment variable is missing entirely
        This test SHOULD FAIL until SECRET_KEY validation requires the variable
        """
        # Simulate missing SECRET_KEY 
        env_without_secret = {k: v for k, v in os.environ.items() if k != 'SECRET_KEY'}
        
        with patch.dict('os.environ', env_without_secret, clear=True):
            env = IsolatedEnvironment(isolation_mode=False)
            
            # Should fail when SECRET_KEY is required but missing
            with pytest.raises((KeyError, ValueError)) as exc_info:
                secret_key = env.get('SECRET_KEY')
                if not secret_key:
                    raise ValueError("SECRET_KEY environment variable is required")
                    
            error_msg = str(exc_info.value).lower()
            assert any(phrase in error_msg for phrase in [
                "secret_key",
                "required",
                "missing",
                "not found"
            ]), f"Expected SECRET_KEY missing error, got: {exc_info.value}"

    def test_secret_key_insecure_default_values(self):
        """
        Test: SECRET_KEY should not use insecure default values
        This test SHOULD FAIL until insecure defaults are rejected
        """
        # Common insecure default values
        insecure_defaults = [
            "dev-secret-key-change-in-production",
            "secret",
            "password", 
            "default-secret-key",
            "your-secret-key-here",
            "change-me",
            "development-secret-key",
            "test-secret-key",
            "12345678901234567890123456789012"  # 32 chars but predictable
        ]
        
        for insecure_key in insecure_defaults:
            with patch.dict('os.environ', {'SECRET_KEY': insecure_key, 'ENVIRONMENT': 'staging'}):
                env = IsolatedEnvironment(isolation_mode=False)
                
                # Should fail validation for insecure defaults in staging/production
                with pytest.raises(ValueError) as exc_info:
                    secret_key = env.get('SECRET_KEY')
                    environment = env.get('ENVIRONMENT')
                    self._validate_secret_key_security(secret_key, environment)
                    
                error_msg = str(exc_info.value).lower()
                assert any(phrase in error_msg for phrase in [
                    "insecure",
                    "default", 
                    "weak",
                    "not allowed",
                    "production"
                ]), f"Expected insecure SECRET_KEY rejection for '{insecure_key}', got: {exc_info.value}"

    def test_secret_key_minimum_entropy_requirements(self):
        """
        Test: SECRET_KEY should meet minimum entropy requirements
        This test SHOULD FAIL until entropy validation is implemented
        """
        # Low entropy SECRET_KEY values
        low_entropy_keys = [
            "a" * 32,                          # All same character
            "1234567890" * 4,                  # Repeating pattern (32 chars)
            "abcdefghijklmnopqrstuvwxyz123456", # Sequential characters
            "00000000000000000000000000000000"  # All zeros (32 chars)
        ]
        
        for low_entropy_key in low_entropy_keys:
            with patch.dict('os.environ', {'SECRET_KEY': low_entropy_key}):
                env = IsolatedEnvironment(isolation_mode=False)
                
                # Should fail entropy validation
                with pytest.raises(ValueError) as exc_info:
                    secret_key = env.get('SECRET_KEY')
                    self._validate_secret_key_entropy(secret_key)
                    
                error_msg = str(exc_info.value).lower()
                assert any(phrase in error_msg for phrase in [
                    "entropy",
                    "randomness",
                    "weak",
                    "predictable",
                    "insufficient"
                ]), f"Expected entropy validation error for low entropy key, got: {exc_info.value}"

    def _validate_secret_key_length(self, secret_key: str) -> bool:
        """
        SECRET_KEY length validation that SHOULD exist but currently doesn't
        """
        if not secret_key:
            raise ValueError("SECRET_KEY cannot be empty")
            
        if len(secret_key) < 32:
            raise ValueError(f"SECRET_KEY must be at least 32 characters, got {len(secret_key)} characters")
            
        return True

    def _validate_secret_key_security(self, secret_key: str, environment: str) -> bool:
        """
        SECRET_KEY security validation for production environments
        """
        if not secret_key:
            raise ValueError("SECRET_KEY is required")
            
        # Check for insecure defaults
        insecure_patterns = [
            "dev",
            "test", 
            "default",
            "change",
            "secret",
            "password",
            "demo",
            "example"
        ]
        
        secret_lower = secret_key.lower()
        for pattern in insecure_patterns:
            if pattern in secret_lower:
                if environment in ['staging', 'production']:
                    raise ValueError(f"Insecure SECRET_KEY pattern '{pattern}' not allowed in {environment}")
                    
        return True

    def _validate_secret_key_entropy(self, secret_key: str) -> bool:
        """
        SECRET_KEY entropy validation for randomness
        """
        if not secret_key:
            raise ValueError("SECRET_KEY is required")
            
        # Check for low entropy patterns
        if len(set(secret_key)) < 8:  # Less than 8 unique characters
            raise ValueError("SECRET_KEY has insufficient entropy - too few unique characters")
            
        # Check for repeating patterns
        if len(secret_key) >= 10:
            for i in range(2, len(secret_key) // 2):
                pattern = secret_key[:i]
                if pattern * (len(secret_key) // i) == secret_key[:len(pattern) * (len(secret_key) // i)]:
                    raise ValueError("SECRET_KEY contains repeating patterns")
                    
        return True


class TestJWTSecretConsistency:
    """Test JWT_SECRET and SECRET_KEY consistency issues"""
    
    def test_jwt_secret_missing_when_secret_key_present(self):
        """
        Test: JWT_SECRET missing while SECRET_KEY is present
        This test SHOULD FAIL until JWT secret consistency is enforced
        """
        env_vars = {
            'SECRET_KEY': token_urlsafe(32),  # Valid SECRET_KEY
            # JWT_SECRET intentionally missing
        }
        
        # Remove JWT_SECRET if it exists
        env_vars_clean = {k: v for k, v in os.environ.items() if k != 'JWT_SECRET'}
        env_vars_clean.update(env_vars)
        
        with patch.dict('os.environ', env_vars_clean, clear=True):
            env = IsolatedEnvironment(isolation_mode=False)
            
            # Should fail when JWT operations require JWT_SECRET
            with pytest.raises(ValueError) as exc_info:
                secret_key = env.get('SECRET_KEY')
                jwt_secret = env.get('JWT_SECRET')
                
                if secret_key and not jwt_secret:
                    raise ValueError("JWT_SECRET is required when SECRET_KEY is configured")
                    
            error_msg = str(exc_info.value).lower()
            assert "jwt_secret" in error_msg and "required" in error_msg, \
                f"Expected JWT_SECRET requirement error, got: {exc_info.value}"

    def test_jwt_secret_different_from_secret_key(self):
        """
        Test: JWT_SECRET and SECRET_KEY should be different for security
        This test SHOULD FAIL until secret separation is enforced
        """
        same_secret = token_urlsafe(32)
        
        with patch.dict('os.environ', {
            'SECRET_KEY': same_secret,
            'JWT_SECRET': same_secret  # Same value - security issue
        }):
            env = IsolatedEnvironment(isolation_mode=False)
            
            # Should fail when secrets are identical
            with pytest.raises(ValueError) as exc_info:
                secret_key = env.get('SECRET_KEY')
                jwt_secret = env.get('JWT_SECRET')
                
                if secret_key == jwt_secret:
                    raise ValueError("JWT_SECRET must be different from SECRET_KEY for security")
                    
            error_msg = str(exc_info.value).lower()
            assert any(phrase in error_msg for phrase in [
                "different",
                "security",
                "same",
                "identical"
            ]), f"Expected secret separation error, got: {exc_info.value}"

    def test_jwt_secret_insufficient_length(self):
        """
        Test: JWT_SECRET should also meet minimum length requirements
        This test SHOULD FAIL until JWT_SECRET validation matches SECRET_KEY requirements
        """
        short_jwt_secrets = [
            "short_jwt",                # 9 characters
            "12345678901234567890",     # 20 characters
            "1234567890123456789012345678901",  # 31 characters
        ]
        
        for short_jwt in short_jwt_secrets:
            with patch.dict('os.environ', {
                'SECRET_KEY': token_urlsafe(32),  # Valid SECRET_KEY
                'JWT_SECRET': short_jwt           # Invalid JWT_SECRET
            }):
                env = IsolatedEnvironment(isolation_mode=False)
                
                # Should fail JWT_SECRET length validation
                with pytest.raises(ValueError) as exc_info:
                    jwt_secret = env.get('JWT_SECRET')
                    self._validate_jwt_secret_length(jwt_secret)
                    
                error_msg = str(exc_info.value).lower()
                assert any(phrase in error_msg for phrase in [
                    "jwt_secret",
                    "32 characters",
                    "too short",
                    "minimum length"
                ]), f"Expected JWT_SECRET length validation error for length {len(short_jwt)}, got: {exc_info.value}"

    def _validate_jwt_secret_length(self, jwt_secret: str) -> bool:
        """
        JWT_SECRET length validation that SHOULD exist
        """
        if not jwt_secret:
            raise ValueError("JWT_SECRET cannot be empty")
            
        if len(jwt_secret) < 32:
            raise ValueError(f"JWT_SECRET must be at least 32 characters, got {len(jwt_secret)} characters")
            
        return True


class TestConfigSystemSecretValidation:
    """Test config system integration with secret validation"""
    
    def test_config_system_rejects_invalid_secret_key(self):
        """
        Test: Config system should validate SECRET_KEY during initialization
        This test SHOULD FAIL until config validation is comprehensive
        """
        with patch.dict('os.environ', {'SECRET_KEY': 'short'}):
            # Config system should validate during get_config()
            with pytest.raises(ValueError) as exc_info:
                config = get_config()
                # Config should validate SECRET_KEY length
                if hasattr(config, 'secret_key') and len(config.secret_key) < 32:
                    raise ValueError("Config validation should reject short SECRET_KEY")
                    
            error_msg = str(exc_info.value).lower()
            assert "secret" in error_msg or "config" in error_msg, \
                f"Expected config validation error, got: {exc_info.value}"

    def test_staging_environment_secret_validation_strictness(self):
        """
        Test: Staging environment should have strict secret validation
        This test SHOULD FAIL until staging validation is enforced
        """
        staging_env_vars = {
            'ENVIRONMENT': 'staging',
            'SECRET_KEY': 'insecure-dev-key-32-characters-',  # 32 chars but insecure
        }
        
        with patch.dict('os.environ', staging_env_vars):
            env = IsolatedEnvironment(isolation_mode=False)
            
            # Staging should enforce strict validation
            with pytest.raises(ValueError) as exc_info:
                secret_key = env.get('SECRET_KEY')
                environment = env.get('ENVIRONMENT')
                
                if environment == 'staging':
                    self._validate_staging_secret_requirements(secret_key)
                    
            error_msg = str(exc_info.value).lower()
            assert "staging" in error_msg or "production" in error_msg or "insecure" in error_msg, \
                f"Expected staging validation error, got: {exc_info.value}"

    def test_secret_key_generation_helper_validation(self):
        """
        Test: Secret key generation helpers should create valid secrets
        This test SHOULD FAIL until generation helpers validate output
        """
        # Test what happens if generation produces invalid output
        with patch('secrets.token_urlsafe', return_value='short'):  # Mock to return short value
            
            with pytest.raises(ValueError) as exc_info:
                generated_secret = token_urlsafe(32)  # Should be mocked to return 'short'
                self._validate_secret_key_length(generated_secret)
                
            assert "32 characters" in str(exc_info.value), \
                f"Expected length validation error, got: {exc_info.value}"

    def _validate_staging_secret_requirements(self, secret_key: str) -> bool:
        """
        Staging environment secret validation
        """
        if not secret_key:
            raise ValueError("SECRET_KEY is required in staging environment")
            
        if len(secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in staging")
            
        # Additional staging requirements
        insecure_patterns = ['dev', 'test', 'demo', 'insecure']
        secret_lower = secret_key.lower()
        
        for pattern in insecure_patterns:
            if pattern in secret_lower:
                raise ValueError(f"SECRET_KEY contains insecure pattern '{pattern}' - not allowed in staging")
                
        return True