"""
Secret Manager Tests
Tests enhanced secret management functionality
"""

import pytest
from app.core.enhanced_secret_manager import EnhancedSecretManager, SecretAccessLevel, EnvironmentType
from app.core.exceptions import NetraSecurityException


class TestSecretManager:
    """Test enhanced secret manager."""
    
    @pytest.fixture
    def secret_manager(self):
        """Create secret manager for testing."""
        return EnhancedSecretManager(EnvironmentType.DEVELOPMENT)
    
    def test_environment_isolation(self, secret_manager):
        """Test environment-based secret isolation."""
        # Production manager should only access prod secrets
        prod_manager = EnhancedSecretManager(EnvironmentType.PRODUCTION)
        
        with pytest.raises(NetraSecurityException):
            prod_manager.get_secret("dev-api-key", "test-component")
    
    def test_secret_encryption(self, secret_manager):
        """Test secret encryption/decryption."""
        secret_name = "test-secret"
        secret_value = "super-secret-value"
        
        # Register secret
        secret_manager._register_secret(
            secret_name, 
            secret_value, 
            SecretAccessLevel.RESTRICTED
        )
        
        # Retrieve and verify
        retrieved_value = secret_manager.get_secret(secret_name, "test-component")
        assert retrieved_value == secret_value
    
    def test_access_control(self, secret_manager):
        """Test secret access control."""
        secret_name = "restricted-secret"
        secret_value = "restricted-value"
        
        secret_manager._register_secret(
            secret_name, 
            secret_value, 
            SecretAccessLevel.CRITICAL
        )
        
        # Test max attempts
        for i in range(6):  # Exceed max attempts (5)
            try:
                secret_manager.get_secret("non-existent", "bad-component")
            except NetraSecurityException:
                pass
        
        # Component should now be blocked
        with pytest.raises(NetraSecurityException) as exc_info:
            secret_manager.get_secret(secret_name, "bad-component")
        
        assert "blocked" in str(exc_info.value).lower()
    
    def test_secret_rotation(self, secret_manager):
        """Test secret rotation functionality."""
        secret_name = "rotatable-secret"
        original_value = "original-value"
        new_value = "new-value"
        
        # Register secret
        secret_manager._register_secret(
            secret_name, 
            original_value, 
            SecretAccessLevel.INTERNAL
        )
        
        # Rotate secret
        success = secret_manager.rotate_secret(secret_name, new_value)
        assert success
        
        # Verify new value
        retrieved_value = secret_manager.get_secret(secret_name, "test-component")
        assert retrieved_value == new_value
    
    def test_security_metrics(self, secret_manager):
        """Test security metrics collection."""
        metrics = secret_manager.get_security_metrics()
        
        assert "total_secrets" in metrics
        assert "secrets_by_access_level" in metrics
        assert "secrets_needing_rotation" in metrics
        assert "blocked_components" in metrics
    
    def test_secret_access_levels(self, secret_manager):
        """Test different secret access levels."""
        # Register secrets with different access levels
        secret_manager._register_secret("public-key", "public-value", SecretAccessLevel.PUBLIC)
        secret_manager._register_secret("internal-key", "internal-value", SecretAccessLevel.INTERNAL)
        secret_manager._register_secret("restricted-key", "restricted-value", SecretAccessLevel.RESTRICTED)
        secret_manager._register_secret("critical-key", "critical-value", SecretAccessLevel.CRITICAL)
        
        # Public should be easily accessible
        public_value = secret_manager.get_secret("public-key", "any-component")
        assert public_value == "public-value"
        
        # Critical should have more restrictions
        critical_value = secret_manager.get_secret("critical-key", "trusted-component")
        assert critical_value == "critical-value"
    
    def test_secret_audit_logging(self, secret_manager):
        """Test secret access audit logging."""
        secret_name = "audit-secret"
        secret_value = "audit-value"
        
        secret_manager._register_secret(secret_name, secret_value, SecretAccessLevel.RESTRICTED)
        
        # Access secret multiple times
        for i in range(3):
            secret_manager.get_secret(secret_name, f"component-{i}")
        
        # Check audit logs
        audit_logs = secret_manager.get_audit_logs(secret_name)
        assert len(audit_logs) >= 3
    
    def test_secret_expiration(self, secret_manager):
        """Test secret expiration functionality."""
        secret_name = "expiring-secret"
        secret_value = "expiring-value"
        
        # Register secret with short expiration
        secret_manager._register_secret(
            secret_name, 
            secret_value, 
            SecretAccessLevel.INTERNAL,
            expires_in_hours=1
        )
        
        # Should be accessible initially
        retrieved_value = secret_manager.get_secret(secret_name, "test-component")
        assert retrieved_value == secret_value
        
        # Mock expiration
        secret_manager._mark_secret_expired(secret_name)
        
        # Should raise exception when expired
        with pytest.raises(NetraSecurityException):
            secret_manager.get_secret(secret_name, "test-component")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])