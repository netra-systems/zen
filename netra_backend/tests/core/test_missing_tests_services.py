"""
Service Layer Tests - Focused module for business logic and service operations
Tests 15, 18, 19 from original missing tests covering:
- Logging manager configuration
- Secret manager encryption
- Unified logging aggregation
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import json
import logging
import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from cryptography.fernet import Fernet

# Test 15: logging_manager_configuration
class TestLoggingManagerService:
    """Test log level management and formatting service."""
    
    @pytest.fixture
    def logging_manager(self):
        from netra_backend.app.core.logging_manager import LoggingManager
        return LoggingManager()
    
    def test_log_level_configuration(self, logging_manager):
        """Test log level can be configured."""
        logging_manager.set_log_level("DEBUG")
        assert logging_manager.get_log_level() == logging.DEBUG
        
        logging_manager.set_log_level("ERROR")
        assert logging_manager.get_log_level() == logging.ERROR
    
    def test_log_rotation_setup(self, logging_manager, tmp_path):
        """Test log rotation is properly configured."""
        log_file = tmp_path / "test.log"
        handler = logging_manager.setup_rotation(
            str(log_file),
            max_bytes=1024,
            backup_count=3
        )
        assert handler.maxBytes == 1024
        assert handler.backupCount == 3
    
    def test_structured_logging_format(self, logging_manager):
        """Test structured logging format."""
        formatter = logging_manager.get_json_formatter()
        record = self._create_test_log_record()
        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
    
    def _create_test_log_record(self):
        """Helper to create test log record."""
        return logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=10, msg="Test message", args=(), exc_info=None
        )
    
    def test_service_logger_creation(self, logging_manager):
        """Test service-specific logger creation."""
        service_logger = logging_manager.get_service_logger("test_service")
        assert service_logger.name == "test_service"
        assert service_logger.level <= logging.INFO
    
    def test_log_filtering_by_service(self, logging_manager):
        """Test filtering logs by service name."""
        filter_func = logging_manager.create_service_filter("api")
        
        api_record = Mock()
        api_record.name = "api.routes"
        
        other_record = Mock()
        other_record.name = "worker.tasks"
        
        assert filter_func(api_record) == True
        assert filter_func(other_record) == False

# Test 18: secret_manager_encryption
class TestSecretManagerService:
    """Test secret storage and retrieval service."""
    
    @pytest.fixture
    def secret_manager(self):
        from netra_backend.app.core.secret_manager import SecretManager
        key = Fernet.generate_key()
        return SecretManager(key)
    
    def test_secret_encryption_decryption(self, secret_manager):
        """Test secret encryption and decryption."""
        secret = "my_secret_password"
        encrypted = secret_manager.encrypt_secret(secret)
        
        assert encrypted != secret
        assert secret_manager.decrypt_secret(encrypted) == secret
    
    def test_secret_rotation(self, secret_manager):
        """Test secret key rotation."""
        secret = "test_secret"
        encrypted = secret_manager.encrypt_secret(secret)
        
        # Rotate key
        new_key = Fernet.generate_key()
        secret_manager.rotate_key(new_key)
        
        # Should still be able to decrypt with rotation
        assert secret_manager.decrypt_secret(encrypted) == secret
    
    def test_secure_secret_storage(self, secret_manager, tmp_path):
        """Test secure storage of secrets."""
        secrets = {
            "api_key": "secret_key_123",
            "db_password": "password_456"
        }
        
        secret_file = tmp_path / "secrets.enc"
        secret_manager.store_secrets(secrets, str(secret_file))
        
        loaded = secret_manager.load_secrets(str(secret_file))
        assert loaded == secrets
    
    def test_secret_versioning(self, secret_manager):
        """Test secret versioning for rollback."""
        secret = "version_1_secret"
        version_1 = secret_manager.store_versioned_secret("api_key", secret)
        
        updated_secret = "version_2_secret"
        version_2 = secret_manager.store_versioned_secret("api_key", updated_secret)
        
        assert secret_manager.get_secret_version("api_key", version_1) == secret
        assert secret_manager.get_secret_version("api_key", version_2) == updated_secret
    
    def test_secret_access_logging(self, secret_manager):
        """Test secret access is logged for audit."""
        with patch('app.core.secret_manager.logger') as mock_logger:
            secret_manager.get_secret("api_key")
            mock_logger.info.assert_called_with(
                "Secret accessed",
                extra={"secret_key": "api_key", "action": "read"}
            )

# Test 19: unified_logging_aggregation
class TestUnifiedLoggingService:
    """Test log aggregation service across services."""
    
    @pytest.fixture
    def unified_logger(self):
        from netra_backend.app.core.unified_logging import UnifiedLogger
        return UnifiedLogger()
    
    def test_correlation_id_propagation(self, unified_logger):
        """Test correlation ID is propagated."""
        correlation_id = "req-123-456"
        unified_logger.set_correlation_id(correlation_id)
        
        log_entry = unified_logger.log("info", "Test message")
        assert log_entry["correlation_id"] == correlation_id
    
    def test_log_aggregation_from_multiple_sources(self, unified_logger):
        """Test aggregating logs from multiple services."""
        unified_logger.log("info", "Service A message", service="service_a")
        unified_logger.log("error", "Service B error", service="service_b")
        unified_logger.log("debug", "Service C debug", service="service_c")
        
        logs = unified_logger.get_aggregated_logs()
        assert len(logs) == 3
        assert any(log["service"] == "service_a" for log in logs)
        assert any(log["service"] == "service_b" for log in logs)
    
    def test_structured_context_addition(self, unified_logger):
        """Test adding structured context to logs."""
        context = {
            "user_id": "123",
            "request_path": "/api/users",
            "method": "GET"
        }
        
        unified_logger.add_context(context)
        log_entry = unified_logger.log("info", "Request processed")
        
        assert log_entry["user_id"] == "123"
        assert log_entry["request_path"] == "/api/users"
    
    def test_log_buffering_and_flushing(self, unified_logger):
        """Test log buffering for performance."""
        unified_logger.enable_buffering(buffer_size=100)
        
        for i in range(50):
            unified_logger.log("debug", f"Message {i}")
        
        # Logs should be buffered
        assert unified_logger.get_buffer_size() == 50
        
        # Flush and verify
        unified_logger.flush_buffer()
        assert unified_logger.get_buffer_size() == 0
    
    def test_log_filtering_by_level(self, unified_logger):
        """Test filtering logs by severity level."""
        unified_logger.set_min_level("error")
        
        unified_logger.log("debug", "Debug message")
        unified_logger.log("info", "Info message")
        unified_logger.log("error", "Error message")
        
        filtered_logs = unified_logger.get_logs_by_level("error")
        assert len(filtered_logs) == 1
        assert filtered_logs[0]["message"] == "Error message"
    
    def test_cross_service_trace_linking(self, unified_logger):
        """Test linking traces across services."""
        trace_id = "trace-abc-123"
        unified_logger.start_trace(trace_id)
        
        unified_logger.log("info", "Service A start", service="service_a")
        unified_logger.log("info", "Service B called", service="service_b")
        unified_logger.log("info", "Service A complete", service="service_a")
        
        trace_logs = unified_logger.get_trace_logs(trace_id)
        assert len(trace_logs) == 3
        assert all(log["trace_id"] == trace_id for log in trace_logs)

# Additional service helper tests
class TestServiceUtilities:
    """Test service utility functions."""
    
    def test_service_health_monitoring(self):
        """Test service health check utilities."""
        from netra_backend.app.core.service_utils import ServiceHealthMonitor
        
        monitor = ServiceHealthMonitor()
        monitor.register_service("api", health_check_url="/health")
        monitor.register_service("worker", health_check_function=lambda: True)
        
        health_status = monitor.check_all_services()
        assert "api" in health_status
        assert "worker" in health_status
    
    def test_service_dependency_injection(self):
        """Test service dependency injection container."""
        from netra_backend.app.core.service_container import ServiceContainer
        
        container = ServiceContainer()
        container.register("logger", Mock())
        container.register("db", Mock())
        
        logger = container.get("logger")
        db = container.get("db")
        
        assert logger is not None
        assert db is not None
    
    def test_service_configuration_management(self):
        """Test service configuration management."""
        from netra_backend.app.core.service_config import ServiceConfigManager
        
        config_manager = ServiceConfigManager()
        config_manager.set_service_config("api", {
            "port": 8000,
            "workers": 4,
            "timeout": 30
        })
        
        config = config_manager.get_service_config("api")
        assert config["port"] == 8000
        assert config["workers"] == 4

# Run service tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-k", "service"])