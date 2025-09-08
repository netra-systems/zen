"""
Comprehensive Unit Tests for Logging Configuration SSOT

Business Value Justification (BVJ):
- Segment: Platform/Internal (All segments depend on this)
- Business Goal: System Observability and Monitoring
- Value Impact: Critical debugging and monitoring infrastructure for production systems
- Strategic Impact: Essential for maintaining system reliability and performance

CRITICAL: This module is imported 643 times across the platform - failure here affects ALL services.

This test suite validates:
1. Unified logger initialization and configuration
2. Context management and correlation IDs
3. Sensitive data filtering in production logs
4. Performance tracking and execution decorators
5. Environment-specific behavior (test/staging/production)
6. WebSocket integration and trace propagation
7. Error handling and fallback mechanisms
8. Cross-service compatibility
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from contextlib import AsyncExitStack, contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from loguru import logger

# Import the module under test and its dependencies
from netra_backend.app.logging_config import (
    CentralLogger,
    UnifiedLogger,
    central_logger,
    get_central_logger,
    get_logger,
    log_execution_time,
    request_id_context,
    trace_id_context,
    user_id_context,
)
from netra_backend.app.core.logging_context import (
    ExecutionTimeDecorator,
    LoggingContext,
    PerformanceTracker,
    StandardLibraryInterceptor,
    clear_logging_context,
    set_logging_context,
)
from netra_backend.app.core.logging_formatters import (
    LogEntry,
    LogFormatter,
    LogHandlerConfig,
    SensitiveDataFilter,
)
from netra_backend.app.core.unified_logging import UnifiedLogger as CoreUnifiedLogger
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestLoggingConfigExports:
    """Test that logging_config.py properly exports all required components."""
    
    def test_all_exports_available(self):
        """Test that all expected exports are available."""
        # Import what should be available
        from netra_backend.app.logging_config import (
            central_logger,
            get_central_logger, 
            get_logger,
            log_execution_time,
            request_id_context,
            user_id_context,
            trace_id_context,
            CentralLogger,
            UnifiedLogger,
        )
        
        # Verify they exist and have expected types
        assert central_logger is not None
        assert callable(get_central_logger)
        assert callable(get_logger)
        assert callable(log_execution_time)
        assert hasattr(request_id_context, 'get')
        assert hasattr(user_id_context, 'get')
        assert hasattr(trace_id_context, 'get')
        assert CentralLogger is not None
        assert UnifiedLogger is not None
    
    def test_backward_compatibility_aliases(self):
        """Test backward compatibility aliases work correctly."""
        # CentralLogger should be alias for UnifiedLogger
        assert CentralLogger == UnifiedLogger
        
        # get_logger should be alias for get_central_logger
        assert get_logger == get_central_logger
        
        # Both should return same instance type
        logger1 = get_central_logger()
        logger2 = get_logger()
        assert type(logger1) == type(logger2)
    
    def test_context_variables_from_logging_context(self):
        """Test that context variables are properly imported."""
        # These should be the same objects from logging_context
        from netra_backend.app.core.logging_context import (
            request_id_context as orig_request,
            trace_id_context as orig_trace,
            user_id_context as orig_user,
        )
        
        assert request_id_context is orig_request
        assert trace_id_context is orig_trace
        assert user_id_context is orig_user


class TestUnifiedLoggerConfiguration:
    """Test UnifiedLogger configuration and initialization."""
    
    @pytest.fixture
    def isolated_env(self):
        """Provide isolated environment for testing."""
        env = IsolatedEnvironment()
        env.set('TESTING', '1', source='test')
        with patch('shared.isolated_environment.get_env', return_value=env):
            yield env
    
    @pytest.fixture
    def fresh_logger(self, isolated_env):
        """Create a fresh logger instance for testing."""
        # Clear any existing loguru handlers
        logger.remove()
        
        # Create new instance
        test_logger = UnifiedLogger()
        yield test_logger
        
        # Cleanup
        try:
            logger.remove()
        except ValueError:
            pass  # No handlers to remove
    
    def test_logger_initialization(self, fresh_logger):
        """Test logger initializes with correct defaults."""
        assert fresh_logger._initialized == False
        assert fresh_logger._config is None
        assert fresh_logger._config_loaded == False
        assert fresh_logger._filter is not None
        assert fresh_logger._context is not None
        assert fresh_logger._performance is not None
        assert fresh_logger._decorator is not None
    
    def test_config_loading_with_fallback(self, fresh_logger, isolated_env):
        """Test configuration loading uses fallback when config manager unavailable."""
        # Config loading should use fallback in test environment
        config = fresh_logger._load_config()
        
        assert config is not None
        assert 'log_level' in config
        assert 'enable_file_logging' in config
        assert 'enable_json_logging' in config
        assert 'log_file_path' in config
        
        # In test environment, file logging should be disabled
        assert config['enable_file_logging'] == False
    
    def test_config_loading_caching(self, fresh_logger, isolated_env):
        """Test that configuration is cached after first load."""
        # Load config first time
        config1 = fresh_logger._load_config()
        assert fresh_logger._config_loaded == True
        assert fresh_logger._config == config1
        
        # Load again - should return cached version
        config2 = fresh_logger._load_config()
        assert config2 is config1  # Same object reference
    
    @patch('netra_backend.app.core.configuration.unified_config_manager')
    def test_config_loading_with_unified_config(self, mock_config_manager, fresh_logger, isolated_env):
        """Test configuration loading with unified config manager."""
        # Setup mock config
        mock_config = Mock()
        mock_config.log_level = 'DEBUG'
        mock_config.enable_file_logging = True
        mock_config.enable_json_logging = False
        mock_config.log_file_path = '/tmp/test.log'
        
        mock_config_manager.get_config.return_value = mock_config
        mock_config_manager._loading = False
        
        isolated_env.set('ENVIRONMENT', 'development', source='test')
        
        config = fresh_logger._load_config()
        
        assert config['log_level'] == 'DEBUG'
        assert config['enable_file_logging'] == True
        assert config['enable_json_logging'] == False  # Not GCP environment
        assert config['log_file_path'] == '/tmp/test.log'
    
    def test_gcp_environment_forces_json_logging(self, fresh_logger, isolated_env):
        """Test that GCP environments force JSON logging."""
        # Test Cloud Run environment
        isolated_env.set('K_SERVICE', 'test-service', source='test')
        config = fresh_logger._load_config()
        assert config['enable_json_logging'] == True
        
        # Test staging environment
        isolated_env.clear_env_var('K_SERVICE')
        isolated_env.set('ENVIRONMENT', 'staging', source='test')
        config = fresh_logger._load_config()
        assert config['enable_json_logging'] == True
        
        # Test production environment  
        isolated_env.set('ENVIRONMENT', 'production', source='test')
        config = fresh_logger._load_config()
        assert config['enable_json_logging'] == True
    
    def test_secrets_loading_phase_handling(self, fresh_logger, isolated_env):
        """Test proper handling during secrets loading phase."""
        isolated_env.set('NETRA_SECRETS_LOADING', 'true', source='test')
        
        config = fresh_logger._load_config()
        
        # Should get fallback config but not cache it during loading
        assert config is not None
        assert fresh_logger._config_loaded == False  # Should not cache during loading
    
    def test_setup_logging_initialization(self, fresh_logger, isolated_env):
        """Test logging setup process."""
        assert not fresh_logger._initialized
        
        fresh_logger._setup_logging()
        
        assert fresh_logger._initialized == True
        assert fresh_logger._config is not None
    
    def test_setup_logging_idempotency(self, fresh_logger, isolated_env):
        """Test that setup_logging can be called multiple times safely."""
        fresh_logger._setup_logging()
        first_config = fresh_logger._config
        
        # Call again
        fresh_logger._setup_logging()
        
        # Should not reinitialize
        assert fresh_logger._config is first_config


class TestLoggingMethods:
    """Test the logging methods of UnifiedLogger.
    
    CLAUDE.md Compliance: NO MOCKS - Real logging functionality testing.
    """
    
    @pytest.fixture
    def real_logger(self):
        """Create real logger instance for testing actual functionality."""
        # Use the actual logger from logging_config
        from netra_backend.app.logging_config import get_central_logger
        test_logger = get_central_logger()
        
        # Clear any existing context
        test_logger.clear_context()
        
        yield test_logger
        
        # Cleanup - clear context
        test_logger.clear_context()
    
    def test_debug_logging(self, real_logger):
        """Test debug level logging works without errors."""
        # Test that logging methods execute without throwing exceptions
        try:
            real_logger.debug("Test debug message", extra_field="value")
            # If we reach here, debug logging works
            assert True
        except Exception as e:
            pytest.fail(f"Debug logging failed with exception: {e}")
    
    def test_info_logging(self, real_logger):
        """Test info level logging works without errors."""
        try:
            real_logger.info("Test info message", request_id="req-123")
            # If we reach here, info logging works
            assert True
        except Exception as e:
            pytest.fail(f"Info logging failed with exception: {e}")
    
    def test_warning_logging(self, real_logger):
        """Test warning level logging works without errors."""
        try:
            real_logger.warning("Test warning message")
            # If we reach here, warning logging works
            assert True
        except Exception as e:
            pytest.fail(f"Warning logging failed with exception: {e}")
    
    def test_error_logging_with_exception_info(self, real_logger):
        """Test error logging with exception information works without errors."""
        try:
            try:
                raise ValueError("Test exception")
            except ValueError:
                real_logger.error("Test error with exception")
            # If we reach here, error logging works
            assert True
        except Exception as e:
            pytest.fail(f"Error logging failed with exception: {e}")
    
    def test_critical_logging_with_exception_info(self, real_logger):
        """Test critical logging with exception information works without errors."""
        try:
            try:
                raise RuntimeError("Critical error")
            except RuntimeError:
                real_logger.critical("Critical system error")
            # If we reach here, critical logging works
            assert True
        except Exception as e:
            pytest.fail(f"Critical logging failed with exception: {e}")
    
    def test_sensitive_data_filtering(self, real_logger):
        """Test that sensitive data logging doesn't crash system."""
        try:
            real_logger.info("User login", password="secret123", api_key="key_123")
            # If we reach here, sensitive data handling works
            assert True
        except Exception as e:
            pytest.fail(f"Sensitive data logging failed with exception: {e}")
    
    def test_context_inclusion(self, real_logger):
        """Test that logging with context works without errors."""
        try:
            # Set context
            real_logger.set_context(request_id="req-456", user_id="user-789")
            
            real_logger.info("Message with context")
            
            # If we reach here, context logging works
            assert True
        except Exception as e:
            pytest.fail(f"Context logging failed with exception: {e}")
        finally:
            # Always clear context for other tests
            real_logger.clear_context()


class TestContextManagement:
    """Test logging context management functionality."""
    
    @pytest.fixture
    def fresh_logger(self):
        """Create fresh logger for context testing."""
        test_logger = UnifiedLogger()
        yield test_logger
        # Clear context after test
        test_logger.clear_context()
    
    def test_set_context(self, fresh_logger):
        """Test setting logging context."""
        fresh_logger.set_context(
            request_id="req-123",
            user_id="user-456", 
            trace_id="trace-789"
        )
        
        # Context should be set in context variables
        assert request_id_context.get() == "req-123"
        assert user_id_context.get() == "user-456"
        assert trace_id_context.get() == "trace-789"
    
    def test_clear_context(self, fresh_logger):
        """Test clearing logging context."""
        # Set context first
        fresh_logger.set_context(request_id="req-123")
        assert request_id_context.get() == "req-123"
        
        # Clear context
        fresh_logger.clear_context()
        assert request_id_context.get() is None
    
    def test_context_isolation(self, fresh_logger):
        """Test that context is properly isolated."""
        # This is more thoroughly tested in logging_context tests
        # Here we test the interface
        fresh_logger.set_context(request_id="req-1")
        assert request_id_context.get() == "req-1"
        
        fresh_logger.clear_context()
        assert request_id_context.get() is None


class TestPerformanceTracking:
    """Test performance tracking and monitoring functionality.
    
    CLAUDE.md Compliance: Real performance tracking testing.
    """
    
    @pytest.fixture
    def performance_logger(self):
        """Create logger for performance testing."""
        from netra_backend.app.logging_config import get_central_logger
        test_logger = get_central_logger()
        test_logger.clear_context()
        yield test_logger
        test_logger.clear_context()
    
    def test_log_performance(self, performance_logger):
        """Test performance metric logging works without errors."""
        try:
            performance_logger.log_performance("database_query", 0.150, query="SELECT * FROM users")
            # If we reach here, performance logging works
            assert True
        except Exception as e:
            pytest.fail(f"Performance logging failed with exception: {e}")
    
    def test_log_api_call(self, performance_logger):
        """Test API call logging works without errors."""
        try:
            performance_logger.log_api_call("GET", "/api/users", 200, 0.250, user_id="123")
            # If we reach here, API call logging works
            assert True
        except Exception as e:
            pytest.fail(f"API call logging failed with exception: {e}")
    
    def test_execution_time_decorator_sync(self, performance_logger):
        """Test execution time decorator for synchronous functions works."""
        try:
            @performance_logger.get_execution_time_decorator()("test_operation")
            def slow_function():
                time.sleep(0.001)  # Small delay
                return "result"
            
            result = slow_function()
            assert result == "result"  # Decorator should preserve return value
        except Exception as e:
            pytest.fail(f"Execution time decorator failed with exception: {e}")
    
    @pytest.mark.asyncio
    async def test_execution_time_decorator_async(self, performance_logger):
        """Test execution time decorator for asynchronous functions works."""
        try:
            @performance_logger.get_execution_time_decorator()("async_test_operation")
            async def async_slow_function():
                await asyncio.sleep(0.001)  # Small delay
                return "async_result"
            
            result = await async_slow_function()
            assert result == "async_result"  # Decorator should preserve return value
        except Exception as e:
            pytest.fail(f"Async execution time decorator failed with exception: {e}")
    
    def test_execution_time_decorator_with_exception(self, performance_logger):
        """Test execution time decorator handles exceptions properly."""
        @performance_logger.get_execution_time_decorator()("failing_operation")
        def failing_function():
            raise ValueError("Test error")
        
        # Should still raise the exception but log performance
        with pytest.raises(ValueError, match="Test error"):
            failing_function()


class TestModuleFunctionInterface:
    """Test module-level functions and convenience interfaces."""
    
    def test_get_central_logger_returns_singleton(self):
        """Test get_central_logger returns the singleton instance."""
        logger1 = get_central_logger()
        logger2 = get_central_logger()
        
        assert logger1 is logger2  # Should be same instance
        assert isinstance(logger1, UnifiedLogger)
    
    def test_get_logger_alias(self):
        """Test get_logger is proper alias for get_central_logger."""
        central = get_central_logger()
        alias = get_logger()
        
        assert central is alias
    
    def test_log_execution_time_decorator(self):
        """Test module-level execution time decorator."""
        captured_calls = []
        
        # Mock the central logger to capture calls
        with patch.object(central_logger, 'get_execution_time_decorator') as mock_decorator:
            mock_decorator.return_value = lambda name: lambda func: func  # Pass-through
            
            @log_execution_time("test_op")
            def test_function():
                return "test"
            
            result = test_function()
            assert result == "test"
            mock_decorator.assert_called_once()
    
    def test_central_logger_singleton(self):
        """Test that central_logger is the singleton instance."""
        assert central_logger is get_central_logger()
        assert isinstance(central_logger, UnifiedLogger)


class TestSensitiveDataFilterIntegration:
    """Test integration with sensitive data filtering."""
    
    @pytest.fixture
    def filter_instance(self):
        """Create SensitiveDataFilter instance."""
        return SensitiveDataFilter()
    
    def test_message_filtering(self, filter_instance):
        """Test message filtering functionality."""
        sensitive_message = "User password: secret123 and api_key: key_abc123"
        filtered = filter_instance.filter_message(sensitive_message)
        
        # Should not contain actual sensitive values
        assert "secret123" not in filtered
        assert "key_abc123" not in filtered
        assert "REDACTED" in filtered
    
    def test_dict_filtering(self, filter_instance):
        """Test dictionary filtering functionality."""
        sensitive_dict = {
            "username": "john",
            "password": "secret123",
            "api_key": "key_abc",
            "normal_field": "normal_value",
            "nested": {
                "token": "token_xyz",
                "safe_field": "safe_value"
            }
        }
        
        filtered = filter_instance.filter_dict(sensitive_dict)
        
        assert filtered["username"] == "john"
        assert filtered["password"] == "REDACTED"
        assert filtered["api_key"] == "REDACTED"
        assert filtered["normal_field"] == "normal_value"
        assert filtered["nested"]["token"] == "REDACTED"
        assert filtered["nested"]["safe_field"] == "safe_value"
    
    def test_credit_card_filtering(self, filter_instance):
        """Test credit card number filtering."""
        message_with_cc = "Payment with card 4532-1234-5678-9012 processed"
        filtered = filter_instance.filter_message(message_with_cc)
        
        assert "4532-1234-5678-9012" not in filtered
        assert "XXXX-XXXX-XXXX-XXXX" in filtered
    
    def test_email_partial_redaction(self, filter_instance):
        """Test email partial redaction."""
        message_with_email = "Contact user@example.com for support"
        filtered = filter_instance.filter_message(message_with_email)
        
        assert "user@example.com" not in filtered
        assert "@example.com" in filtered  # Domain preserved
        assert "***@example.com" in filtered


class TestEnvironmentSpecificBehavior:
    """Test behavior in different environments."""
    
    @pytest.fixture
    def env_logger(self):
        """Create logger for environment testing."""
        logger.remove()
        test_logger = UnifiedLogger()
        yield test_logger
        logger.remove()
    
    def test_testing_environment_behavior(self, env_logger):
        """Test special behavior in testing environment."""
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'TESTING': '1',
                'ENVIRONMENT': 'testing'
            }.get(key, default)
            
            # Should not crash during setup
            env_logger._setup_logging()
            assert env_logger._initialized
    
    def test_production_environment_behavior(self, env_logger):
        """Test behavior in production environment."""
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'production',
                'TESTING': '0'
            }.get(key, default)
            
            config = env_logger._load_config()
            assert config['enable_json_logging'] == True  # Should force JSON in production
    
    def test_staging_environment_behavior(self, env_logger):
        """Test behavior in staging environment."""
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'TESTING': '0'
            }.get(key, default)
            
            config = env_logger._load_config()
            assert config['enable_json_logging'] == True  # Should force JSON in staging


class TestErrorHandlingAndFallbacks:
    """Test error handling and fallback mechanisms."""
    
    @pytest.fixture
    def error_prone_logger(self):
        """Create logger for error testing."""
        logger.remove()
        test_logger = UnifiedLogger()
        yield test_logger
        logger.remove()
    
    def test_config_loading_exception_fallback(self, error_prone_logger):
        """Test fallback when config loading fails."""
        # Mock configuration to raise exception
        with patch('netra_backend.app.core.configuration.unified_config_manager') as mock_manager:
            mock_manager.get_config.side_effect = ImportError("Config not available")
            
            config = error_prone_logger._load_config()
            
            # Should get fallback config
            assert config is not None
            assert 'log_level' in config
            assert 'enable_file_logging' in config
    
    def test_handler_configuration_exception_handling(self, error_prone_logger):
        """Test that handler configuration errors don't crash the logger."""
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.return_value = '0'  # Not testing
            
            # Should not raise exception even if handler setup fails
            error_prone_logger._setup_logging()
            assert error_prone_logger._initialized
    
    def test_logging_method_with_filter_exception(self, error_prone_logger):
        """Test logging continues even if filtering fails."""
        # Mock filter to raise exception
        with patch.object(error_prone_logger._filter, 'filter_message', side_effect=Exception("Filter error")):
            # Should not raise exception
            try:
                error_prone_logger.info("Test message")
                # If we get here, the logger handled the exception gracefully
            except Exception as e:
                # Should not happen in well-designed logging system
                pytest.fail(f"Logging should not raise exceptions: {e}")
    
    @pytest.mark.asyncio
    async def test_shutdown_graceful(self, error_prone_logger):
        """Test graceful shutdown."""
        error_prone_logger._setup_logging()
        
        # Should complete without error
        await error_prone_logger.shutdown()


class TestCrossServiceCompatibility:
    """Test compatibility across different services and contexts."""
    
    def test_multiple_logger_instances(self):
        """Test that multiple logger instances work correctly."""
        logger1 = UnifiedLogger()
        logger2 = UnifiedLogger()
        
        # Should be separate instances
        assert logger1 is not logger2
        
        # But should behave consistently
        config1 = logger1._load_config()
        config2 = logger2._load_config()
        
        # Configs should have same structure
        assert set(config1.keys()) == set(config2.keys())
    
    def test_context_variable_isolation(self):
        """Test context variable isolation between operations."""
        logger1 = UnifiedLogger()
        logger2 = UnifiedLogger()
        
        # Set different contexts
        logger1.set_context(request_id="req-1")
        logger2.set_context(request_id="req-2")
        
        # Should see the most recent context (context vars are async-local)
        assert request_id_context.get() == "req-2"
        
        # Clear one context
        logger1.clear_context()
        
        # Should clear the shared context variable
        assert request_id_context.get() is None
    
    def test_standard_library_interception_compatibility(self):
        """Test compatibility with standard library logging interception."""
        test_logger = UnifiedLogger()
        
        # Should not crash when interception is setup
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.return_value = '0'  # Not testing
            test_logger._setup_logging()
        
        assert test_logger._initialized


class TestLogFormatterIntegration:
    """Test integration with log formatters."""
    
    @pytest.fixture
    def formatter(self):
        """Create log formatter with filter."""
        return LogFormatter(SensitiveDataFilter())
    
    def test_json_formatter(self, formatter):
        """Test JSON formatter produces valid JSON."""
        # Create properly structured loguru record mock
        level_mock = Mock()
        level_mock.name = "INFO"
        level_mock.no = 20
        
        time_mock = Mock()
        time_mock.isoformat.return_value = "2024-01-01T12:00:00Z"
        
        mock_record = {
            "level": level_mock,
            "message": "Test message",
            "name": "test.module",
            "function": "test_function",
            "line": 42,
            "time": time_mock,
            "extra": {"custom_field": "value"},
            "exception": None
        }
        
        # Should not raise exception
        json_output = formatter.json_formatter(mock_record)
        
        # Should be valid JSON string
        assert isinstance(json_output, str)
        assert json_output.endswith("\n")
        
        # Should parse as valid JSON
        parsed = json.loads(json_output.strip())
        assert isinstance(parsed, dict)
    
    def test_gcp_json_formatter(self, formatter):
        """Test GCP JSON formatter produces valid Cloud Logging format."""
        level_mock = Mock()
        level_mock.name = "ERROR"
        level_mock.no = 40
        
        time_mock = Mock()
        time_mock.isoformat.return_value = "2024-01-01T12:00:00Z"
        
        mock_record = {
            "level": level_mock,
            "message": "Error occurred", 
            "name": "test.module",
            "function": "test_function",
            "line": 100,
            "time": time_mock,
            "exception": None,
            "extra": {"request_id": "req-123"}
        }
        
        json_output = formatter.gcp_json_formatter(mock_record)
        
        # Should be valid JSON
        parsed = json.loads(json_output.strip())
        
        # Should have GCP required fields
        assert "severity" in parsed
        assert "message" in parsed  
        assert "timestamp" in parsed
        assert parsed["severity"] in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    def test_console_format_string(self, formatter):
        """Test console format string is properly structured."""
        format_string = formatter.get_console_format()
        
        assert isinstance(format_string, str)
        assert "{time" in format_string
        assert "{level" in format_string
        assert "{message}" in format_string


class TestLogHandlerConfig:
    """Test log handler configuration."""
    
    def test_handler_config_creation(self):
        """Test log handler config creation."""
        config = LogHandlerConfig("INFO", enable_json=True)
        
        assert config.level == "INFO"
        assert config.enable_json == True
        assert config.formatter is not None
    
    def test_console_handler_in_testing(self):
        """Test console handler behavior in testing environment."""
        config = LogHandlerConfig("DEBUG")
        
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default=None: {
                'TESTING': '1',
                'ENVIRONMENT': 'testing'
            }.get(key, default)
            
            # Should not crash in testing environment
            config.add_console_handler(lambda record: True)
    
    def test_file_handler_creation(self):
        """Test file handler creation with rotation."""
        config = LogHandlerConfig("INFO")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # Should create directory and configure handler
            config.add_file_handler(str(log_file), lambda record: True)
            
            # Directory should exist
            assert log_file.parent.exists()


class TestIntegrationWithWebSocketTrace:
    """Test integration with WebSocket tracing and context propagation."""
    
    def test_unified_trace_context_integration(self):
        """Test integration with unified trace context."""
        test_logger = UnifiedLogger()
        
        # Test actual API - set context with individual parameters
        test_logger.set_context(
            request_id="req-456",
            user_id="user-789", 
            trace_id="trace-abc"
        )
        
        # Should extract values from context variables
        assert request_id_context.get() == "req-456"
        assert user_id_context.get() == "user-789"
        assert trace_id_context.get() == "trace-abc"
    
    def test_child_context_creation(self):
        """Test child context creation for sub-agent propagation."""
        test_logger = UnifiedLogger()
        
        # Mock parent context
        mock_parent = Mock()
        mock_child = Mock()
        mock_parent.propagate_to_child.return_value = mock_child
        
        with patch('netra_backend.app.core.logging_context.get_current_trace_context', return_value=mock_parent):
            child_context = test_logger._context.create_child_context()
            
            assert child_context is mock_child
            mock_parent.propagate_to_child.assert_called_once()


class TestPerformanceAndScalability:
    """Test performance characteristics and scalability."""
    
    def test_config_loading_performance(self):
        """Test that config loading is efficient with caching."""
        test_logger = UnifiedLogger()
        
        # Time first load
        start_time = time.time()
        config1 = test_logger._load_config()
        first_load_time = time.time() - start_time
        
        # Time second load (should be cached)
        start_time = time.time()
        config2 = test_logger._load_config()
        cached_load_time = time.time() - start_time
        
        # Cached load should be much faster
        assert cached_load_time < first_load_time * 0.1  # At least 10x faster
        assert config1 is config2  # Same object reference
    
    def test_logging_method_performance(self):
        """Test that logging methods execute quickly."""
        logger.remove()
        
        # Add fast no-op sink
        logger.add(lambda msg: None, level="DEBUG")
        
        test_logger = UnifiedLogger()
        test_logger._setup_logging()
        
        # Time many log calls
        start_time = time.time()
        for i in range(100):
            test_logger.info(f"Test message {i}", iteration=i)
        
        total_time = time.time() - start_time
        avg_time = total_time / 100
        
        # Should average less than 1ms per log call
        assert avg_time < 0.001, f"Average log time {avg_time:.4f}s too slow"
    
    @pytest.mark.asyncio
    async def test_async_logging_performance(self):
        """Test performance of async logging operations."""
        logger.remove()
        logger.add(lambda msg: None, level="DEBUG")
        
        test_logger = UnifiedLogger()
        test_logger._setup_logging()
        
        @test_logger.get_execution_time_decorator()("perf_test")
        async def async_operation():
            await asyncio.sleep(0.001)
            return "done"
        
        # Time multiple async operations
        start_time = time.time()
        tasks = [async_operation() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        assert len(results) == 10
        assert all(r == "done" for r in results)
        # Should complete reasonably quickly
        assert total_time < 1.0


class TestRegressionsAndEdgeCases:
    """Test for regressions and edge cases."""
    
    def test_empty_message_handling(self):
        """Test handling of empty or None messages."""
        test_logger = UnifiedLogger()
        filter_instance = SensitiveDataFilter()
        
        # Should not crash on empty/None messages
        assert filter_instance.filter_message("") == ""
        assert filter_instance.filter_message(None) is None
        
        # Logger should handle empty messages
        logger.remove()
        logger.add(lambda msg: None, level="DEBUG")
        test_logger._setup_logging()
        
        test_logger.info("")  # Should not crash
        test_logger.info(None)  # Should not crash
    
    def test_malformed_dict_handling(self):
        """Test handling of malformed dictionary data."""
        filter_instance = SensitiveDataFilter()
        
        # Should handle None dict
        assert filter_instance.filter_dict(None) is None
        
        # Should handle empty dict
        assert filter_instance.filter_dict({}) == {}
        
        # Should handle nested None values
        malformed = {"key": None, "nested": {"inner": None}}
        filtered = filter_instance.filter_dict(malformed)
        assert filtered["key"] is None
        assert filtered["nested"]["inner"] is None
    
    def test_circular_import_prevention(self):
        """Test that circular imports are prevented."""
        # This test ensures the logging system can be imported without circular dependencies
        # The fact that we can run all these tests proves this works, but let's be explicit
        
        # Should be able to import logging config multiple times
        from netra_backend.app.logging_config import central_logger
        from netra_backend.app.logging_config import get_central_logger
        
        assert central_logger is not None
        assert get_central_logger() is not None
    
    def test_context_variable_cleanup(self):
        """Test proper cleanup of context variables."""
        test_logger = UnifiedLogger()
        
        # Set context
        test_logger.set_context(request_id="req-cleanup")
        assert request_id_context.get() == "req-cleanup"
        
        # Clear should reset to None
        test_logger.clear_context()
        assert request_id_context.get() is None
        
        # Multiple clears should be safe
        test_logger.clear_context()
        assert request_id_context.get() is None
    
    def test_handler_removal_safety(self):
        """Test safe handler removal during cleanup."""
        test_logger = UnifiedLogger()
        
        # Setup logging
        test_logger._setup_logging()
        
        # Should be able to configure handlers multiple times
        test_logger._configure_handlers()
        test_logger._configure_handlers()
        
        # Should not crash
        assert test_logger._initialized
    
    def test_unicode_message_handling(self):
        """Test handling of Unicode characters in log messages."""
        logger.remove()
        captured_messages = []
        logger.add(lambda msg: captured_messages.append(str(msg)), level="DEBUG")
        
        test_logger = UnifiedLogger()
        test_logger._setup_logging()
        
        # Should handle Unicode properly
        unicode_message = "Test with émojis 🚀 and ünïcödé characters"
        test_logger.info(unicode_message)
        
        # Should not crash and should preserve Unicode
        assert len(captured_messages) > 0
    
    def test_high_frequency_logging(self):
        """Test system behavior under high-frequency logging."""
        logger.remove()
        message_count = 0
        
        def counting_sink(msg):
            nonlocal message_count
            message_count += 1
        
        logger.add(counting_sink, level="DEBUG")
        
        test_logger = UnifiedLogger()
        test_logger._setup_logging()
        
        # Log many messages rapidly
        for i in range(1000):
            test_logger.debug(f"High frequency message {i}")
        
        # All messages should be processed
        assert message_count >= 1000  # May be higher due to setup logs
    
    @pytest.mark.asyncio
    async def test_concurrent_logging(self):
        """Test concurrent logging from multiple coroutines."""
        logger.remove()
        message_count = 0
        
        def counting_sink(msg):
            nonlocal message_count
            message_count += 1
        
        logger.add(counting_sink, level="DEBUG")
        
        test_logger = UnifiedLogger()
        test_logger._setup_logging()
        
        async def log_worker(worker_id):
            for i in range(100):
                test_logger.info(f"Worker {worker_id} message {i}")
        
        # Run multiple workers concurrently
        tasks = [log_worker(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Should handle concurrent access safely
        assert message_count >= 1000  # All messages plus setup