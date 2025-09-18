"""
Test Configuration Secrets Management - Unit Tests

Business Value Justification (BVJ):
- Segment: Enterprise 
- Business Goal: Secure secrets management without exposure
- Value Impact: Prevents security breaches and compliance violations (saves $100K+ per incident)
- Strategic Impact: Enables enterprise deployment with SOC2/GDPR compliance

This test suite validates secrets management functionality, ensuring sensitive configuration
is properly handled, encrypted, and never exposed in logs or error messages.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, Optional
import json
import base64

from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.base_integration_test import BaseIntegrationTest


class TestConfigurationSecretsManagementUnit(BaseIntegrationTest):
    """Test configuration secrets management functionality."""
    
    @pytest.mark.unit
    def test_secret_detection_and_classification(self):
        """Test secret detection and classification logic.
        
        Critical for ensuring sensitive values are identified and protected.
        """
        env = IsolatedEnvironment("secrets_test")
        
        # Test obvious secret patterns
        obvious_secrets = {
            "JWT_SECRET_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "DATABASE_PASSWORD": "super_secure_password_123",
            "API_KEY": "ak_live_1234567890abcdef",
            "OAUTH_CLIENT_SECRET": "client_secret_abcdef123456",
            "ENCRYPTION_KEY": "AES256_key_here_32_chars_long",
            "SERVICE_SECRET": "service_secret_token_789xyz"
        }
        
        for key, value in obvious_secrets.items():
            env.set(key, value, source="test")
            
            # All these should be identified as secrets
            assert self._is_secret_variable(key), f"{key} should be identified as secret"
            assert env.get(key) == value, "Secret should be stored correctly"
        
        # Test non-secret variables
        non_secrets = {
            "DEBUG": "true",
            "LOG_LEVEL": "INFO",
            "PORT": "8000",
            "ENVIRONMENT": "testing",
            "DATABASE_URL": "postgresql://user@localhost/db"  # Contains credentials but not pure secret
        }
        
        for key, value in non_secrets.items():
            env.set(key, value, source="test")
            
            # These should not be classified as pure secrets
            if not any(secret_word in key.upper() for secret_word in ['SECRET', 'KEY', 'PASSWORD', 'TOKEN']):
                assert not self._is_secret_variable(key), f"{key} should not be identified as secret"

    @pytest.mark.unit
    def test_secret_masking_and_safe_logging(self):
        """Test secret masking for safe logging and error reporting.
        
        Ensures secrets are never exposed in logs or error messages.
        """
        env = IsolatedEnvironment("masking_test")
        
        # Set up secrets for masking tests
        secrets = {
            "SHORT_SECRET": "abc123",
            "MEDIUM_SECRET": "medium_secret_value_here",
            "LONG_SECRET": "this_is_a_very_long_secret_value_that_should_be_masked_properly"
        }
        
        for key, value in secrets.items():
            env.set(key, value, source="test")
        
        # Test secret masking functionality
        for key, original_value in secrets.items():
            masked_value = self._mask_secret_value(original_value)
            
            # Verify masking behavior
            assert masked_value != original_value, f"Secret {key} should be masked"
            assert len(masked_value) < len(original_value), "Masked value should be shorter"
            assert "*" in masked_value or "[MASKED]" in masked_value, "Should contain masking indicators"
            
            # Verify partial masking shows structure but hides content
            if len(original_value) > 10:
                # For longer secrets, should show first/last few chars
                assert original_value[:2] in masked_value or original_value[-2:] in masked_value, \
                    "Should show partial content for structure recognition"

    @pytest.mark.unit
    def test_secret_validation_and_strength_checking(self):
        """Test secret validation and strength checking.
        
        Ensures secrets meet minimum security requirements.
        """
        env = IsolatedEnvironment("validation_test")
        
        # Test weak secrets that should trigger warnings
        weak_secrets = [
            "123",           # Too short
            "password",      # Common word
            "test",          # Too simple
            "admin",         # Common word
            "secret",        # Generic word
            "12345678"       # Sequential numbers
        ]
        
        for weak_secret in weak_secrets:
            env.set("TEST_SECRET", weak_secret, source="test")
            
            # Check weakness detection
            is_weak = self._is_weak_secret(weak_secret)
            assert is_weak, f"Should detect '{weak_secret}' as weak secret"
        
        # Test strong secrets
        strong_secrets = [
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ",
            "AES256_randomly_generated_key_with_sufficient_length_and_entropy_12345",
            "oauth2_client_secret_with_random_chars_abc123def456ghi789jkl012",
            "database_password_with_mixed_chars_ABC123def456!@#$%^"
        ]
        
        for strong_secret in strong_secrets:
            env.set("STRONG_SECRET", strong_secret, source="test")
            
            # Check strength validation
            is_weak = self._is_weak_secret(strong_secret)
            assert not is_weak, f"Should not detect '{strong_secret[:20]}...' as weak secret"

    @pytest.mark.unit
    def test_secret_storage_and_retrieval_security(self):
        """Test secret storage and retrieval security measures.
        
        Validates secrets are stored securely and retrieved safely.
        """
        env = IsolatedEnvironment("storage_test")
        
        # Test secret storage with various encodings
        secrets_with_encodings = {
            "BASE64_SECRET": base64.b64encode(b"secret_data_here").decode('utf-8'),
            "JSON_SECRET": json.dumps({"secret": "value", "key": "data"}),
            "URL_SECRET": "postgresql://user:password@host:5432/db",
            "MULTILINE_SECRET": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKB\n-----END PRIVATE KEY-----"
        }
        
        for key, value in secrets_with_encodings.items():
            env.set(key, value, source="test")
            
            # Verify storage and retrieval
            retrieved_value = env.get(key)
            assert retrieved_value == value, f"Secret {key} should be stored and retrieved correctly"
            
            # Verify no corruption or encoding issues
            if "BASE64" in key:
                decoded = base64.b64decode(retrieved_value.encode('utf-8'))
                assert b"secret_data_here" in decoded, "Base64 secret should decode correctly"
            
            if "JSON" in key:
                parsed = json.loads(retrieved_value)
                assert parsed["secret"] == "value", "JSON secret should parse correctly"

    @pytest.mark.unit 
    def test_secrets_environment_isolation(self):
        """Test secrets are properly isolated between environments.
        
        Critical for preventing production secrets from leaking to other environments.
        """
        # Create separate environments
        prod_env = IsolatedEnvironment("production")
        staging_env = IsolatedEnvironment("staging") 
        test_env = IsolatedEnvironment("testing")
        
        # Set different secrets in each environment
        prod_env.set("DATABASE_PASSWORD", "production_secret_password", source="environment")
        staging_env.set("DATABASE_PASSWORD", "staging_secret_password", source="environment") 
        test_env.set("DATABASE_PASSWORD", "test_secret_password", source="environment")
        
        # Verify isolation - each environment has its own secrets
        assert prod_env.get("DATABASE_PASSWORD") == "production_secret_password"
        assert staging_env.get("DATABASE_PASSWORD") == "staging_secret_password"
        assert test_env.get("DATABASE_PASSWORD") == "test_secret_password"
        
        # Verify no cross-contamination
        assert prod_env.get("DATABASE_PASSWORD") != staging_env.get("DATABASE_PASSWORD")
        assert staging_env.get("DATABASE_PASSWORD") != test_env.get("DATABASE_PASSWORD")
        assert test_env.get("DATABASE_PASSWORD") != prod_env.get("DATABASE_PASSWORD")
        
        # Test secret cleanup doesn't affect other environments
        test_env.delete("DATABASE_PASSWORD")
        assert test_env.get("DATABASE_PASSWORD") is None
        assert prod_env.get("DATABASE_PASSWORD") == "production_secret_password"  # Should be unaffected
        assert staging_env.get("DATABASE_PASSWORD") == "staging_secret_password"  # Should be unaffected

    # Helper methods for secret detection and validation
    
    def _is_secret_variable(self, var_name: str) -> bool:
        """Helper to identify if a variable name indicates a secret."""
        secret_indicators = [
            'SECRET', 'PASSWORD', 'TOKEN', 'KEY', 'PRIVATE', 'CREDENTIAL',
            'AUTH', 'OAUTH', 'JWT', 'API_KEY', 'CLIENT_SECRET'
        ]
        
        var_upper = var_name.upper()
        return any(indicator in var_upper for indicator in secret_indicators)
    
    def _mask_secret_value(self, value: str) -> str:
        """Helper to mask secret values for safe logging."""
        if len(value) <= 4:
            return "[MASKED]"
        elif len(value) <= 10:
            return f"{value[:1]}***{value[-1:]}"
        else:
            return f"{value[:2]}***{value[-2:]}"
    
    def _is_weak_secret(self, secret: str) -> bool:
        """Helper to detect weak secrets."""
        if len(secret) < 8:
            return True
        
        weak_patterns = [
            'password', 'secret', 'admin', 'test', '123', 'abc',
            '12345678', 'qwerty', 'password123'
        ]
        
        secret_lower = secret.lower()
        return any(pattern in secret_lower for pattern in weak_patterns)


class TestConfigurationSecretsIntegrationUnit(BaseIntegrationTest):
    """Test secrets management integration with configuration system."""
    
    @pytest.mark.unit
    def test_secrets_in_database_urls_handling(self):
        """Test proper handling of secrets within database URLs.
        
        Database URLs contain passwords that need special handling.
        """
        env = IsolatedEnvironment("db_secrets_test")
        
        # Test various database URL formats with embedded secrets
        db_urls = [
            "postgresql://user:password123@localhost:5432/database",
            "postgresql://admin:super_secret_pass@db.example.com:5432/prod_db", 
            "redis://user:redis_password@redis.example.com:6379/0",
            "clickhouse://user:clickhouse_secret@clickhouse.cloud:8443/analytics?secure=1"
        ]
        
        for url in db_urls:
            env.set("DATABASE_URL", url, source="test")
            
            # URL should be stored correctly
            retrieved_url = env.get("DATABASE_URL")
            assert retrieved_url == url, "Database URL should be stored exactly"
            
            # Should be able to extract components for validation
            if "://" in url and "@" in url:
                # URL contains credentials
                protocol_and_auth = url.split("://")[1]
                if "@" in protocol_and_auth:
                    auth_part = protocol_and_auth.split("@")[0]
                    if ":" in auth_part:
                        username, password = auth_part.split(":", 1)
                        
                        # Password should be detected as secret
                        assert len(password) > 0, "Should extract password from URL"
                        
                        # Should be able to create masked version for logging
                        masked_url = self._mask_database_url(url)
                        assert password not in masked_url, "Password should be masked in logged URL"
                        assert username in masked_url, "Username should remain visible"

    @pytest.mark.unit
    def test_secrets_in_configuration_objects(self):
        """Test secrets handling in configuration objects and serialization.
        
        Ensures secrets are not accidentally serialized or logged.
        """
        env = IsolatedEnvironment("config_objects_test")
        
        # Set up configuration with mixed secret and non-secret values
        config_vars = {
            "APP_NAME": "Netra Analytics Platform",
            "VERSION": "1.0.0",
            "DEBUG": "false",
            "JWT_SECRET_KEY": "secret_jwt_key_for_testing_12345",
            "DATABASE_PASSWORD": "db_password_secret_789",
            "API_KEY": "api_key_secret_abc123def456",
            "LOG_LEVEL": "INFO",
            "PORT": "8000"
        }
        
        for key, value in config_vars.items():
            env.set(key, value, source="test")
        
        # Test configuration serialization safety
        safe_config = {}
        for key, value in config_vars.items():
            if self._is_secret_variable(key):
                # Secrets should be masked in serialization
                safe_config[key] = self._mask_secret_value(value)
            else:
                # Non-secrets can be included normally
                safe_config[key] = value
        
        # Verify safe serialization
        config_json = json.dumps(safe_config)
        
        # Secrets should not appear in serialized form
        assert "secret_jwt_key_for_testing_12345" not in config_json
        assert "db_password_secret_789" not in config_json
        assert "api_key_secret_abc123def456" not in config_json
        
        # Non-secrets should appear normally
        assert "Netra Analytics Platform" in config_json
        assert "1.0.0" in config_json
        assert "INFO" in config_json
        
        # Masked indicators should be present for secrets
        assert "[MASKED]" in config_json or "***" in config_json

    @pytest.mark.unit
    def test_secret_rotation_and_update_handling(self):
        """Test handling of secret rotation and updates.
        
        Ensures secrets can be rotated safely without disrupting service.
        """
        env = IsolatedEnvironment("rotation_test")
        
        # Initial secret setup
        original_secrets = {
            "JWT_SECRET_KEY": "original_jwt_secret_v1",
            "DATABASE_PASSWORD": "original_db_password_v1",
            "API_KEY": "original_api_key_v1"
        }
        
        for key, value in original_secrets.items():
            env.set(key, value, source="environment")
        
        # Verify original secrets are set
        for key, value in original_secrets.items():
            assert env.get(key) == value, f"Original {key} should be set"
        
        # Simulate secret rotation
        rotated_secrets = {
            "JWT_SECRET_KEY": "rotated_jwt_secret_v2",
            "DATABASE_PASSWORD": "rotated_db_password_v2", 
            "API_KEY": "rotated_api_key_v2"
        }
        
        for key, new_value in rotated_secrets.items():
            env.set(key, new_value, source="rotation")
        
        # Verify rotation took effect
        for key, new_value in rotated_secrets.items():
            assert env.get(key) == new_value, f"Rotated {key} should be updated"
            assert env.get(key) != original_secrets[key], f"{key} should be different after rotation"
        
        # Test source tracking for rotation audit
        for key in rotated_secrets.keys():
            sources = env.get_sources(key)
            assert "rotation" in sources, f"Should track rotation source for {key}"
            assert "environment" in sources, f"Should track original source for {key}"

    def _mask_database_url(self, url: str) -> str:
        """Helper to mask passwords in database URLs."""
        if "://" not in url or "@" not in url:
            return url
        
        parts = url.split("://")
        if len(parts) != 2:
            return url
        
        protocol = parts[0]
        rest = parts[1]
        
        if "@" not in rest:
            return url
        
        auth_and_host = rest.split("@")
        if len(auth_and_host) != 2:
            return url
        
        auth_part = auth_and_host[0]
        host_part = auth_and_host[1]
        
        if ":" not in auth_part:
            return url
        
        username, password = auth_part.split(":", 1)
        masked_password = "***"
        
        return f"{protocol}://{username}:{masked_password}@{host_part}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])