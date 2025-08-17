"""
Security Configuration Tests
Tests security configuration and environment handling
"""

import pytest
from app.core.enhanced_secret_manager import EnhancedSecretManager, EnvironmentType
from app.core.exceptions import NetraSecurityException


class TestSecurityConfiguration:
    """Test security configuration and environment handling."""
    
    def test_environment_specific_config(self):
        """Test environment-specific security configuration."""
        from app.middleware.security_headers import SecurityHeadersConfig
        
        # Production config should be strictest
        prod_headers = SecurityHeadersConfig.get_headers("production")
        assert "Strict-Transport-Security" in prod_headers
        assert "max-age=31536000" in prod_headers["Strict-Transport-Security"]
        
        # Development config should be more permissive
        dev_headers = SecurityHeadersConfig.get_headers("development")
        dev_csp = dev_headers["Content-Security-Policy"]
        assert "'unsafe-inline'" in dev_csp
        assert "'unsafe-eval'" in dev_csp
    
    def test_secret_environment_isolation(self):
        """Test secret manager environment isolation."""
        # Development manager
        dev_manager = EnhancedSecretManager(EnvironmentType.DEVELOPMENT)
        
        # Production manager  
        prod_manager = EnhancedSecretManager(EnvironmentType.PRODUCTION)
        
        # Each should only access appropriate secrets
        assert dev_manager.environment == EnvironmentType.DEVELOPMENT
        assert prod_manager.environment == EnvironmentType.PRODUCTION
        
        # Cross-environment access should be blocked
        with pytest.raises(NetraSecurityException):
            prod_manager.get_secret("dev-test-secret", "test-component")
    
    def test_security_policy_configuration(self):
        """Test security policy configuration."""
        from app.config.security_policies import SecurityPolicyManager
        
        policy_manager = SecurityPolicyManager()
        
        # Test different policy levels
        strict_policy = policy_manager.get_policy("strict")
        permissive_policy = policy_manager.get_policy("permissive")
        
        assert strict_policy.max_request_size < permissive_policy.max_request_size
        assert strict_policy.rate_limit < permissive_policy.rate_limit
    
    def test_cors_configuration(self):
        """Test CORS configuration for different environments."""
        from app.config.cors_config import get_cors_config
        
        # Production CORS should be restrictive
        prod_cors = get_cors_config("production")
        assert "*" not in prod_cors["allow_origins"]
        
        # Development CORS can be more permissive
        dev_cors = get_cors_config("development")
        assert len(dev_cors["allow_origins"]) >= len(prod_cors["allow_origins"])
    
    def test_encryption_configuration(self):
        """Test encryption configuration."""
        from app.config.encryption_config import EncryptionConfig
        
        config = EncryptionConfig()
        
        # Should have strong encryption settings
        assert config.algorithm == "AES-256-GCM"
        assert config.key_length >= 256
        assert config.salt_length >= 32
    
    def test_logging_security_configuration(self):
        """Test security logging configuration."""
        from app.config.logging_config import get_security_logging_config
        
        config = get_security_logging_config()
        
        # Should log security events
        assert config["security_events"] is True
        assert config["auth_failures"] is True
        assert config["rate_limit_violations"] is True
    
    def test_session_configuration(self):
        """Test session security configuration."""
        from app.config.session_config import SessionConfig
        
        config = SessionConfig()
        
        # Should have secure session settings
        assert config.secure is True
        assert config.httponly is True
        assert config.samesite == "strict"
        assert config.max_age <= 3600  # 1 hour max


if __name__ == "__main__":
    pytest.main([__file__, "-v"])