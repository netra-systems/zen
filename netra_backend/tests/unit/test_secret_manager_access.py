"""Unit tests for EnhancedSecretManager access control.

Tests secret access control and security enforcement.
SECURITY CRITICAL - Protects enterprise contracts and prevents data breaches.

Business Value: Ensures secure secret access control preventing security
breaches that could result in lost enterprise customers.
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from netra_backend.app.core.exceptions_auth import NetraSecurityException

from netra_backend.app.core.secret_manager_core import EnhancedSecretManager
from netra_backend.app.core.secret_manager_types import SecretAccessLevel
from netra_backend.app.schemas.config_types import EnvironmentType

class TestSecretManagerAccess:
    """Test suite for EnhancedSecretManager access control."""
    
    @pytest.fixture
    def secret_manager(self):
        """Create secret manager with mocked dependencies."""
        with patch('app.core.secret_manager_core.SecretEncryption'), \
             patch('app.core.secret_manager_core.SecretLoader'), \
             patch('app.core.secret_manager_core.SecretManagerAuth'), \
             patch('app.core.secret_manager_core.central_logger'):
            
            manager = EnhancedSecretManager(EnvironmentType.DEVELOPMENT)
            manager.secrets = {}
            manager.metadata = {}
            manager.access_log = []
            return manager
    
    @pytest.fixture
    def prod_secret_manager(self):
        """Create production secret manager."""
        with patch('app.core.secret_manager_core.SecretEncryption'), \
             patch('app.core.secret_manager_core.SecretLoader'), \
             patch('app.core.secret_manager_core.SecretManagerAuth'), \
             patch('app.core.secret_manager_core.central_logger'):
            
            manager = EnhancedSecretManager(EnvironmentType.PRODUCTION)
            manager.secrets = {}
            manager.metadata = {}
            return manager
    
    def test_get_secret_success(self, secret_manager):
        """Test successful secret retrieval."""
        secret_manager._register_secret("test-secret", "secret-value", SecretAccessLevel.STANDARD)
        secret_manager.encryption.decrypt_secret.return_value = "secret-value"
        
        result = secret_manager.get_secret("test-secret", "test-component")
        
        assert result == "secret-value"
        assert len(secret_manager.access_log) == 1
        assert secret_manager.access_log[0]["result"] == "SUCCESS"
    
    def test_get_secret_not_found(self, secret_manager):
        """Test secret retrieval for non-existent secret."""
        with pytest.raises(NetraSecurityException) as exc_info:
            secret_manager.get_secret("nonexistent-secret", "test-component")
        
        assert "Secret nonexistent-secret not found" in str(exc_info.value)
        assert len(secret_manager.access_log) == 1
        assert "FAILED" in secret_manager.access_log[0]["result"]
    
    def test_get_secret_expired(self, secret_manager):
        """Test access to expired secret."""
        secret_manager._register_secret("test-secret", "secret-value", SecretAccessLevel.STANDARD)
        secret_manager._mark_secret_expired("test-secret")
        
        with pytest.raises(NetraSecurityException) as exc_info:
            secret_manager.get_secret("test-secret", "test-component")
        
        assert "is expired" in str(exc_info.value)
    
    def test_get_secret_component_blocked(self, secret_manager):
        """Test access by blocked component."""
        secret_manager._register_secret("test-secret", "secret-value", SecretAccessLevel.STANDARD)
        secret_manager.blocked_components.add("blocked-component")
        
        with pytest.raises(NetraSecurityException) as exc_info:
            secret_manager.get_secret("test-secret", "blocked-component")
        
        assert "is blocked from accessing secrets" in str(exc_info.value)
    
    def test_get_secret_access_attempts_exceeded(self, secret_manager):
        """Test access when component exceeded attempt limit."""
        secret_manager._register_secret("test-secret", "secret-value", SecretAccessLevel.STANDARD)
        secret_manager.access_attempts["test-component"] = 6  # Over limit of 5
        
        with pytest.raises(NetraSecurityException) as exc_info:
            secret_manager.get_secret("test-secret", "test-component")
        
        assert "exceeded access attempts" in str(exc_info.value)
        assert "test-component" in secret_manager.blocked_components
    
    def test_production_environment_isolation(self, prod_secret_manager):
        """Test production environment can only access prod secrets."""
        prod_secret_manager._register_secret("dev-secret", "value", SecretAccessLevel.STANDARD)
        
        with pytest.raises(NetraSecurityException) as exc_info:
            prod_secret_manager.get_secret("dev-secret", "test-component")
        
        assert "Production environment cannot access non-production secret" in str(exc_info.value)
    
    def test_production_environment_allows_prod_secrets(self, prod_secret_manager):
        """Test production environment allows prod-prefixed secrets."""
        prod_secret_manager._register_secret("prod-secret", "value", SecretAccessLevel.STANDARD)
        prod_secret_manager.encryption.decrypt_secret.return_value = "value"
        
        result = prod_secret_manager.get_secret("prod-secret", "test-component")
        
        assert result == "value"
    
    def test_access_log_entries_structure(self, secret_manager):
        """Test access log entries have correct structure."""
        secret_manager._register_secret("test-secret", "value", SecretAccessLevel.STANDARD)
        secret_manager.encryption.decrypt_secret.return_value = "value"
        
        secret_manager.get_secret("test-secret", "test-component")
        
        log_entry = secret_manager.access_log[0]
        assert "timestamp" in log_entry
        assert "secret_name" in log_entry
        assert "component" in log_entry
        assert "result" in log_entry
        assert "environment" in log_entry
        assert log_entry["secret_name"] == "test-secret"
        assert log_entry["component"] == "test-component"
    
    def test_failed_attempt_recording(self, secret_manager):
        """Test recording of failed access attempts."""
        initial_attempts = secret_manager.access_attempts.get("test-comp", 0)
        
        secret_manager._record_failed_attempt("test-comp")
        
        assert secret_manager.access_attempts["test-comp"] == initial_attempts + 1
    
    def test_multiple_failed_attempts_blocking(self, secret_manager):
        """Test component gets blocked after multiple failed attempts."""
        # Simulate multiple failed attempts
        for _ in range(5):
            secret_manager._record_failed_attempt("bad-component")
        
        secret_manager._register_secret("test-secret", "value", SecretAccessLevel.STANDARD)
        
        with pytest.raises(NetraSecurityException) as exc_info:
            secret_manager.get_secret("test-secret", "bad-component")
        
        assert "bad-component" in secret_manager.blocked_components
        assert "exceeded access attempts" in str(exc_info.value)
    
    def test_access_control_validation_order(self, secret_manager):
        """Test access control checks are performed in correct order."""
        secret_manager.blocked_components.add("blocked-comp")
        secret_manager._register_secret("test-secret", "value", SecretAccessLevel.STANDARD)
        
        with pytest.raises(NetraSecurityException) as exc_info:
            secret_manager.get_secret("test-secret", "blocked-comp")
        
        # Should fail on blocked check before other validations
        assert "is blocked from accessing secrets" in str(exc_info.value)
    
    def test_access_log_size_maintenance(self, secret_manager):
        """Test access log size is maintained at maximum."""
        # Fill log beyond limit
        secret_manager.access_log = [{"id": i} for i in range(1200)]
        
        secret_manager._maintain_log_size()
        
        assert len(secret_manager.access_log) == 1000
        assert secret_manager.access_log[0]["id"] == 200  # First 200 removed
    
    def test_environment_specific_access_patterns(self, secret_manager, prod_secret_manager):
        """Test access patterns vary correctly by environment."""
        # Development allows any secret name
        secret_manager._register_secret("any-secret", "value", SecretAccessLevel.STANDARD)
        secret_manager.encryption.decrypt_secret.return_value = "value"
        
        result = secret_manager.get_secret("any-secret", "test-component")
        assert result == "value"
        
        # Production requires prod- prefix
        prod_secret_manager._register_secret("any-secret", "value", SecretAccessLevel.STANDARD)
        
        with pytest.raises(NetraSecurityException):
            prod_secret_manager.get_secret("any-secret", "test-component")
    
    # Helper methods (each ≤8 lines)
    def _simulate_multiple_access_attempts(self, secret_manager, component, count):
        """Helper to simulate multiple failed access attempts."""
        for _ in range(count):
            secret_manager._record_failed_attempt(component)
    
    def _create_access_log_entry(self, secret_name, component, result):
        """Helper to create access log entry."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "secret_name": secret_name, "component": component,
            "result": result, "environment": "development"
        }
    
    def _setup_secret_for_access_test(self, manager, secret_name="test-secret"):
        """Helper to setup secret for access testing."""
        manager._register_secret(secret_name, "test-value", SecretAccessLevel.STANDARD)
        manager.encryption.decrypt_secret.return_value = "test-value"
        return secret_name