"""Core unit tests for EnhancedSecretManager.

Tests core secret management functionality and rotation.
SECURITY CRITICAL - Protects enterprise contracts and prevents data breaches.

Business Value: Ensures secure secret management core features preventing
security breaches and enabling secure secret rotation.
"""

import sys
from pathlib import Path

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest

from netra_backend.app.core.exceptions_auth import NetraSecurityException

from netra_backend.app.core.secret_manager_core import EnhancedSecretManager
from netra_backend.app.core.secret_manager_types import (
    SecretAccessLevel,
    SecretMetadata,
)
from netra_backend.app.schemas.config_types import EnvironmentType

class TestSecretManagerCore:
    """Test suite for EnhancedSecretManager core functionality."""
    
    @pytest.fixture
    def secret_manager(self):
        """Create secret manager with mocked dependencies."""
        # Mock: Component isolation for testing without external dependencies
        with patch('app.core.secret_manager_core.SecretEncryption'), \
             # Mock: Component isolation for testing without external dependencies
             patch('app.core.secret_manager_core.SecretLoader'), \
             # Mock: Component isolation for testing without external dependencies
             patch('app.core.secret_manager_core.SecretManagerAuth'), \
             # Mock: Component isolation for testing without external dependencies
             patch('app.core.secret_manager_core.central_logger'):
            
            manager = EnhancedSecretManager(EnvironmentType.DEVELOPMENT)
            manager.secrets = {}
            manager.metadata = {}
            manager.access_log = []
            return manager
    
    def test_rotate_secret_success(self, secret_manager):
        """Test successful secret rotation."""
        secret_manager._register_secret("test-secret", "old-value", SecretAccessLevel.STANDARD)
        new_value = "new-secret-value-456"
        secret_manager.encryption.encrypt_secret.return_value = "encrypted-new"
        
        success = secret_manager.rotate_secret("test-secret", new_value)
        
        assert success is True
        metadata = secret_manager.metadata["test-secret"]
        assert metadata.last_rotated is not None
    
    def test_rotate_secret_nonexistent(self, secret_manager):
        """Test rotation of non-existent secret."""
        success = secret_manager.rotate_secret("nonexistent", "new-value")
        
        assert success is False
    
    def test_get_secrets_needing_rotation(self, secret_manager):
        """Test getting list of secrets needing rotation."""
        secret_manager._register_secret("secret1", "value1", SecretAccessLevel.STANDARD)
        secret_manager._register_secret("secret2", "value2", SecretAccessLevel.STANDARD)
        
        # Mark one as needing rotation
        secret_manager.metadata["secret1"].needs_rotation = True
        
        needing_rotation = secret_manager.get_secrets_needing_rotation()
        
        assert len(needing_rotation) == 1
        assert "secret1" in needing_rotation
    
    def test_get_security_metrics(self, secret_manager):
        """Test security metrics collection."""
        secret_manager._register_secret("secret1", "value1", SecretAccessLevel.STANDARD)
        secret_manager._register_secret("secret2", "value2", SecretAccessLevel.HIGH)
        secret_manager.blocked_components.add("blocked-comp")
        secret_manager.access_attempts["comp1"] = 3
        
        metrics = secret_manager.get_security_metrics()
        
        assert metrics["total_secrets"] == 2
        assert metrics["blocked_components"] == 1
        assert metrics["total_access_attempts"] == 3
        assert "secrets_by_access_level" in metrics
    
    def test_cleanup_access_log(self, secret_manager):
        """Test cleanup of old access log entries."""
        old_time = datetime.now(timezone.utc) - timedelta(days=40)
        recent_time = datetime.now(timezone.utc) - timedelta(days=10)
        
        secret_manager.access_log = [
            {"timestamp": old_time.isoformat(), "secret_name": "old"},
            {"timestamp": recent_time.isoformat(), "secret_name": "recent"}
        ]
        
        secret_manager.cleanup_access_log(days_to_keep=30)
        
        assert len(secret_manager.access_log) == 1
        assert secret_manager.access_log[0]["secret_name"] == "recent"
    
    def test_get_audit_logs_all(self, secret_manager):
        """Test getting all audit logs."""
        secret_manager.access_log = [
            {"secret_name": "secret1", "component": "comp1"},
            {"secret_name": "secret2", "component": "comp2"}
        ]
        
        logs = secret_manager.get_audit_logs()
        
        assert len(logs) == 2
        assert logs != secret_manager.access_log  # Should be a copy
    
    def test_get_audit_logs_filtered(self, secret_manager):
        """Test getting audit logs filtered by secret name."""
        secret_manager.access_log = [
            {"secret_name": "secret1", "component": "comp1"},
            {"secret_name": "secret2", "component": "comp2"},
            {"secret_name": "secret1", "component": "comp3"}
        ]
        
        logs = secret_manager.get_audit_logs("secret1")
        
        assert len(logs) == 2
        assert all(log["secret_name"] == "secret1" for log in logs)
    
    def test_register_secret_with_encryption(self, secret_manager):
        """Test secret registration with encryption."""
        secret_manager.encryption.encrypt_secret.return_value = "encrypted-value"
        
        secret_manager._register_secret("test-secret", "plain-value", SecretAccessLevel.STANDARD)
        
        secret_manager.encryption.encrypt_secret.assert_called_once_with("plain-value")
        assert "test-secret" in secret_manager.secrets
        assert "test-secret" in secret_manager.metadata
    
    def test_register_secret_with_expiration(self, secret_manager):
        """Test secret registration with expiration time."""
        secret_manager.encryption.encrypt_secret.return_value = "encrypted"
        
        secret_manager._register_secret(
            "expiring-secret", "value", SecretAccessLevel.STANDARD,
            rotation_days=90, expires_in_hours=24
        )
        
        metadata = secret_manager.metadata["expiring-secret"]
        assert metadata.expires_at is not None
        expected_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        assert abs((metadata.expires_at - expected_expiry).total_seconds()) < 60
    
    def test_secret_metadata_access_recording(self, secret_manager):
        """Test that secret metadata records access correctly."""
        secret_manager._register_secret("test-secret", "test-value", SecretAccessLevel.STANDARD)
        
        metadata = secret_manager.metadata["test-secret"]
        metadata.record_access("test-component")
        
        assert metadata.access_count > 0
        assert metadata.last_accessed is not None
    
    def test_initialization_with_environment(self):
        """Test secret manager initialization with different environments."""
        # Mock: Component isolation for testing without external dependencies
        with patch('app.core.secret_manager_core.SecretEncryption'), \
             # Mock: Component isolation for testing without external dependencies
             patch('app.core.secret_manager_core.SecretLoader'), \
             # Mock: Component isolation for testing without external dependencies
             patch('app.core.secret_manager_core.SecretManagerAuth'), \
             # Mock: Component isolation for testing without external dependencies
             patch('app.core.secret_manager_core.central_logger'):
            
            manager = EnhancedSecretManager(EnvironmentType.PRODUCTION)
            
            assert manager.environment == EnvironmentType.PRODUCTION
            assert manager.max_access_attempts == 5
            assert isinstance(manager.blocked_components, set)
    
    def test_secret_rotation_metadata_update(self, secret_manager):
        """Test that secret rotation updates metadata correctly."""
        secret_manager._register_secret("rotation-test", "old-value", SecretAccessLevel.STANDARD)
        secret_manager.encryption.encrypt_secret.return_value = "encrypted-new"
        
        # Get initial metadata state
        metadata = secret_manager.metadata["rotation-test"]
        initial_rotation_time = metadata.last_rotated
        
        # Perform rotation
        success = secret_manager.rotate_secret("rotation-test", "new-value")
        
        assert success is True
        assert metadata.last_rotated != initial_rotation_time
        assert metadata.last_rotated is not None
    
    def test_security_metrics_by_access_level(self, secret_manager):
        """Test security metrics correctly categorize by access level."""
        secret_manager._register_secret("std1", "value", SecretAccessLevel.STANDARD)
        secret_manager._register_secret("std2", "value", SecretAccessLevel.STANDARD)
        secret_manager._register_secret("high1", "value", SecretAccessLevel.HIGH)
        
        metrics = secret_manager.get_security_metrics()
        
        by_level = metrics["secrets_by_access_level"]
        assert by_level[SecretAccessLevel.STANDARD.value] == 2
        assert by_level[SecretAccessLevel.HIGH.value] == 1
    
    def test_audit_log_filtering_accuracy(self, secret_manager):
        """Test audit log filtering returns accurate results."""
        test_logs = [
            {"secret_name": "target", "component": "comp1", "action": "read"},
            {"secret_name": "other", "component": "comp2", "action": "read"},
            {"secret_name": "target", "component": "comp3", "action": "write"},
            {"secret_name": "another", "component": "comp1", "action": "read"}
        ]
        secret_manager.access_log = test_logs
        
        filtered_logs = secret_manager.get_audit_logs("target")
        
        assert len(filtered_logs) == 2
        assert all(log["secret_name"] == "target" for log in filtered_logs)
        assert {log["component"] for log in filtered_logs} == {"comp1", "comp3"}
    
    # Helper methods (each ≤8 lines)
    def _create_test_metadata(self, secret_name, access_level):
        """Helper to create test secret metadata."""
        return SecretMetadata(secret_name, access_level, EnvironmentType.DEVELOPMENT)
    
    def _setup_secret_with_rotation_need(self, manager, secret_name):
        """Helper to setup secret that needs rotation."""
        manager._register_secret(secret_name, "value", SecretAccessLevel.STANDARD)
        manager.metadata[secret_name].needs_rotation = True
        return secret_name
    
    def _verify_secret_registered(self, manager, secret_name):
        """Helper to verify secret was properly registered."""
        assert secret_name in manager.secrets
        assert secret_name in manager.metadata
        assert isinstance(manager.metadata[secret_name], SecretMetadata)