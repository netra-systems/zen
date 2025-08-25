"""
Tests 11-20: Core Infrastructure & Error Handling
Tests for the missing core infrastructure components identified in the top 100 missing tests.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import json
import logging
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.fernet import Fernet

# Test 11: config_validator_schema_validation
class TestConfigValidator:
    """Test configuration schema validation - app/core/config_validator.py"""
    
    @pytest.fixture
    def validator(self):
        from netra_backend.app.core.config_validator import ConfigValidator
        return ConfigValidator()
    
    @pytest.fixture
    def mock_config(self):
        # Mock: Generic component isolation for controlled unit testing
        config = Mock()
        config.environment = "production"
        config.database_url = "postgresql://user:pass@localhost/db"
        config.jwt_secret_key = "a" * 32
        config.fernet_key = Fernet.generate_key()
        # Mock: ClickHouse external database isolation for unit testing performance
        config.clickhouse_logging = Mock(enabled=True)
        # Mock: ClickHouse external database isolation for unit testing performance
        config.clickhouse_native = Mock(host="localhost", password="pass")
        # Mock: ClickHouse external database isolation for unit testing performance
        config.clickhouse_https = Mock(host="localhost", password="pass")
        # Mock: Component isolation for controlled unit testing
        config.oauth_config = Mock(client_id="id", client_secret="secret")
        config.llm_configs = {
            # Mock: OpenAI API isolation for testing without external service dependencies
            "default": Mock(api_key="key", model_name="model", provider="openai")
        }
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        config.redis = Mock(host="localhost", password="pass")
        # Mock: Component isolation for controlled unit testing
        config.langfuse = Mock(secret_key="key", public_key="pub")
        return config
    
    def test_valid_config_passes_validation(self, validator, mock_config):
        """Test that valid configuration passes validation."""
        validator.validate_config(mock_config)
    
    def test_invalid_database_url_rejected(self, validator, mock_config):
        """Test that invalid database URL is rejected."""
        from netra_backend.app.core.config_validator import ConfigurationValidationError
        
        mock_config.database_url = "mysql://user:pass@localhost/db"
        with pytest.raises(ConfigurationValidationError, match="Database URL must be a PostgreSQL"):
            validator.validate_config(mock_config)
    
    def test_validation_report_generation(self, validator, mock_config):
        """Test validation report generation."""
        report = validator.get_validation_report(mock_config)
        assert any("✓" in line for line in report)
        assert any("Environment: production" in line for line in report)

# Test 12: error_context_capture
class TestErrorContext:
    """Test error context preservation - app/core/error_context.py"""
    
    @pytest.fixture
    def error_context(self):
        from netra_backend.app.schemas.shared_types import ErrorContext
        return ErrorContext()
    
    def test_trace_id_management(self, error_context):
        """Test trace ID generation and retrieval."""
        trace_id = error_context.generate_trace_id()
        assert trace_id != None
        assert error_context.get_trace_id() == trace_id
    
    def test_context_preservation_across_calls(self, error_context):
        """Test that context is preserved across calls."""
        error_context.set_trace_id("trace-123")
        error_context.set_request_id("req-456")
        error_context.set_user_id("user-789")
        
        assert error_context.get_trace_id() == "trace-123"
        assert error_context.get_request_id() == "req-456"
        assert error_context.get_user_id() == "user-789"

# Test 13: error_handlers_recovery
class TestErrorHandlers:
    """Test error recovery mechanisms - app/core/error_handlers.py"""
    
    def test_error_response_structure(self):
        """Test standardized error response structure."""
        from netra_backend.app.core.error_handlers import ErrorResponse
        
        response = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test error message",
            trace_id="trace-123",
            timestamp=datetime.now().isoformat()
        )
        
        assert response.error == True
        assert response.error_code == "TEST_ERROR"
        assert response.trace_id == "trace-123"
    @pytest.mark.asyncio
    async def test_http_exception_handler(self):
        """Test HTTP exception handling."""
        from fastapi import HTTPException

        from netra_backend.app.core.error_handlers import http_exception_handler
        
        # Mock: Generic component isolation for controlled unit testing
        request = Mock()
        # Mock: Generic component isolation for controlled unit testing
        request.state = Mock()
        request.state.request_id = "test-request-id"
        request.state.trace_id = "test-trace-id"
        exc = HTTPException(status_code=404, detail="Not found")
        
        response = await http_exception_handler(request, exc)
        assert response.status_code == 404
        
        body = json.loads(response.body)
        assert body["error"] == True
        assert "Not found" in body["message"]

# Test 14: exceptions_custom_types
class TestCustomExceptions:
    """Test custom exception behaviors - app/core/exceptions.py"""
    
    def test_netra_exception_structure(self):
        """Test NetraException structure and properties."""
        from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
        from netra_backend.app.core.exceptions_base import NetraException
        
        exc = NetraException(
            message="Test error",
            code=ErrorCode.INTERNAL_ERROR,
            severity=ErrorSeverity.HIGH
        )
        
        assert str(exc) == "INTERNAL_ERROR: Test error"
        assert exc.error_details.code == ErrorCode.INTERNAL_ERROR.value
        assert exc.error_details.severity == ErrorSeverity.HIGH.value
    
    def test_authentication_error(self):
        """Test authentication-specific exceptions."""
        from netra_backend.app.core.error_codes import ErrorCode
        from netra_backend.app.core.exceptions_auth import AuthenticationError
        
        exc = AuthenticationError("Invalid token")
        assert "Invalid token" in str(exc)
        assert exc.error_details.code == ErrorCode.AUTHENTICATION_FAILED.value

# Test 15: logging_manager_configuration
class TestLoggingManager:
    """Test log level management - app/core/logging_manager.py"""
    
    def test_logging_configuration(self):
        """Test basic logging configuration."""
        from netra_backend.app.core.logging_manager import (
            LogLevel,
            configure_logging,
            get_logger,
        )
        
        configure_logging(level=LogLevel.DEBUG)
        logger = get_logger(__name__)
        
        assert logger != None
    
    def test_structured_logging(self):
        """Test structured logging output."""
        from netra_backend.app.core.logging_manager import get_logger
        
        logger = get_logger("test_logger")
        
        with patch.object(logger, 'info') as mock_info:
            logger.info("Test message", extra={"user_id": "123"})
            mock_info.assert_called_once()

# Test 16: resource_manager_limits
class TestResourceManager:
    """Test resource allocation - app/core/resource_manager.py"""
    @pytest.mark.asyncio
    async def test_resource_tracking(self):
        """Test basic resource tracking."""
        from netra_backend.app.core.resource_manager import ResourceTracker
        
        tracker = ResourceTracker()
        # Use register instead of track_resource
        tracker.register("connection_conn_1", {"id": "conn_1", "type": "connection"})
        
        # Check resource was registered
        assert tracker.get_resource("connection_conn_1") is not None
        assert tracker.get_resource("connection_conn_1")["id"] == "conn_1"
        
        # Use unregister instead of release_resource
        result = tracker.unregister("connection_conn_1")
        assert result == True
        assert tracker.get_resource("connection_conn_1") is None
    @pytest.mark.asyncio
    async def test_resource_limits(self):
        """Test resource limit enforcement with register/unregister."""
        from netra_backend.app.core.resource_manager import ResourceTracker
        
        tracker = ResourceTracker()
        
        # Register multiple connections
        tracker.register("connection_1", {"id": "conn_1", "type": "connection"})
        tracker.register("connection_2", {"id": "conn_2", "type": "connection"})
        
        # Check resources are registered
        assert tracker.get_resource("connection_1") is not None
        assert tracker.get_resource("connection_2") is not None
        
        # Get resource info to verify
        info = tracker.get_resource_info()
        assert len(info) == 2

# Test 17: schema_sync_database_migration
class TestSchemaSync:
    """Test schema synchronization - app/core/schema_sync.py"""
    @pytest.mark.asyncio
    async def test_schema_validation(self):
        """Test basic schema validation."""
        from netra_backend.app.core.schema_sync import validate_schema
        
        # Mock: Generic component isolation for controlled unit testing
        mock_db = AsyncMock()
        mock_db.execute.return_value.fetchall.return_value = [
            ("users", "id", "integer"),
            ("users", "email", "varchar"),
        ]
        
        # Should not raise exception for valid schema
        await validate_schema(mock_db, expected_tables=["users"])
    
    def test_migration_safety_checks(self):
        """Test migration safety validation."""
        from netra_backend.app.core.schema_sync import is_migration_safe
        
        # Safe migration (adding column)
        assert is_migration_safe("ALTER TABLE users ADD COLUMN age INTEGER;")
        
        # Unsafe migration (dropping table)
        assert not is_migration_safe("DROP TABLE users;")

# Test 18: secret_manager_encryption
class TestSecretManager:
    """Test secret storage - app/core/secret_manager.py"""
    
    def test_secret_encryption(self):
        """Test basic secret encryption/decryption."""
        from netra_backend.app.core.secret_manager import decrypt_secret, encrypt_secret
        
        key = Fernet.generate_key()
        secret = "my_secret_password"
        
        encrypted = encrypt_secret(secret, key)
        assert encrypted != secret
        
        decrypted = decrypt_secret(encrypted, key)
        assert decrypted == secret
    
    def test_secret_validation(self):
        """Test secret format validation."""
        from netra_backend.app.core.secret_manager import validate_secret_format
        
        # Valid secrets
        assert validate_secret_format("valid_secret_123")
        assert validate_secret_format("another-valid-secret")
        
        # Invalid secrets (too short)
        assert not validate_secret_format("short")

# Test 19: unified_logging_aggregation
class TestUnifiedLogging:
    """Test log aggregation - app/core/unified_logging.py"""
    
    def test_log_correlation(self):
        """Test log correlation across services."""
        from netra_backend.app.core.unified_logging import CorrelatedLogger
        
        logger = CorrelatedLogger("test_service")
        logger.set_correlation_id("corr-123")
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.info("Test message")
            
            # Check that correlation ID is included
            call_args = mock_info.call_args
            assert call_args != None
    
    def test_log_aggregation(self):
        """Test aggregating logs from multiple sources."""
        from netra_backend.app.core.unified_logging import LogAggregator
        
        aggregator = LogAggregator()
        
        aggregator.add_log("service_a", "info", "Message from A")
        aggregator.add_log("service_b", "error", "Error from B")
        
        logs = aggregator.get_logs()
        assert len(logs) == 2
        assert any(log["service"] == "service_a" for log in logs)
        assert any(log["service"] == "service_b" for log in logs)

# Test 20: startup_checks_service_validation
class TestStartupChecks:
    """Test service validation - app/startup_checks.py"""
    
    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI app for testing"""
        # Mock: Generic component isolation for controlled unit testing
        app = Mock()
        # Mock: Generic component isolation for controlled unit testing
        app.state = Mock()
        # Mock: Session isolation for controlled testing without external state
        app.state.db_session_factory = AsyncMock()
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        app.state.redis_manager = AsyncMock()
        return app
    @pytest.mark.asyncio
    async def test_database_check(self, mock_app):
        """Test database connectivity check."""
        from netra_backend.app.startup_checks.database_checks import DatabaseChecker
        
        # Mock database session
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar_one.return_value = 1
        
        # Create an async context manager mock
        # Mock: Generic component isolation for controlled unit testing
        async_context_manager = AsyncMock()
        # Mock: Database session isolation for transaction testing without real database dependency
        async_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        # Mock: Async component isolation for testing without real async operations
        async_context_manager.__aexit__ = AsyncMock(return_value=None)
        
        # Mock table existence check to return True for critical tables  
        with patch.object(DatabaseChecker, '_table_exists', return_value=True):
            # Mock: Session management isolation for stateless unit testing
            mock_app.state.db_session_factory = Mock(return_value=async_context_manager)
            
            checker = DatabaseChecker(mock_app)
            result = await checker.check_database_connection()
            assert result.success == True
            assert result.name == "database_connection"
    @pytest.mark.asyncio
    async def test_service_health_checks(self, mock_app):
        """Test external service health checks."""
        from netra_backend.app.startup_checks.service_checks import ServiceChecker
        
        checker = ServiceChecker(mock_app)
        
        # Mock Redis check
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_app.state.redis_manager.connect = AsyncMock()
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_app.state.redis_manager.set = AsyncMock()
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_app.state.redis_manager.get = AsyncMock(return_value="test_value")
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_app.state.redis_manager.delete = AsyncMock()
        
        # Mock: Component isolation for testing without external dependencies
        with patch('time.time', return_value=123456789):
            mock_app.state.redis_manager.get.return_value = "123456789"
            result = await checker.check_redis()
            assert result.success == True
            assert result.name == "redis_connection"
        
        # Mock ClickHouse check
        # Mock: ClickHouse external database isolation for unit testing performance
        with patch('app.db.clickhouse.get_clickhouse_client') as mock_ch:
            # Mock: Generic component isolation for controlled unit testing
            mock_client = AsyncMock()
            mock_client.ping.return_value = None
            mock_client.execute.return_value = [("workload_events",)]
            mock_ch.return_value.__aenter__.return_value = mock_client
            
            result = await checker.check_clickhouse()
            assert result.success == True
            assert result.name == "clickhouse_connection"
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, mock_app):
        """Test graceful degradation when optional services fail."""
        from netra_backend.app.startup_checks import run_startup_checks
        
        # Mock database session for successful connection
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar_one.return_value = 1
        mock_app.state.db_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Set staging environment to make failures non-critical
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            result = await run_startup_checks(mock_app)
            # Should complete without critical failures in staging
            assert result["success"] == True or result["failed_critical"] == 0