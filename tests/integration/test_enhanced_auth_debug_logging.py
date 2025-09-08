"""Test Enhanced Authentication Debug Logging

This test suite validates that the enhanced authentication debug logging
provides comprehensive context for 403 "Not authenticated" errors.

Business Value: Reduces authentication debugging time from hours to minutes
by providing 10x more context and actionable debugging information.
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.exc import OperationalError

from netra_backend.app.dependencies import get_request_scoped_db_session
from netra_backend.app.logging.auth_trace_logger import auth_tracer, log_authentication_context_dump
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestEnhancedAuthDebugLogging(SSotBaseTestCase):
    """Test enhanced authentication debug logging functionality."""
    
    def setup_method(self):
        """Set up test environment with logging capture."""
        super().setup_method()
        
        # Set up logging capture
        self.log_capture = []
        
        # Create a custom handler to capture logs
        class LogCapture(logging.Handler):
            def __init__(self, log_list):
                super().__init__()
                self.log_list = log_list
                
            def emit(self, record):
                self.log_list.append(record.getMessage())
        
        self.log_handler = LogCapture(self.log_capture)
        self.log_handler.setLevel(logging.INFO)
        
        # Add handler to relevant loggers
        for logger_name in [
            'netra_backend.app.dependencies',
            'netra_backend.app.database.request_scoped_session_factory',
            'netra_backend.app.logging.auth_trace_logger'
        ]:
            logger = logging.getLogger(logger_name)
            logger.addHandler(self.log_handler)
            logger.setLevel(logging.INFO)
    
    def teardown_method(self):
        """Clean up logging handlers."""
        for logger_name in [
            'netra_backend.app.dependencies',
            'netra_backend.app.database.request_scoped_session_factory',
            'netra_backend.app.logging.auth_trace_logger'
        ]:
            logger = logging.getLogger(logger_name)
            logger.removeHandler(self.log_handler)
        
        super().teardown_method()
    
    @pytest.mark.asyncio
    async def test_enhanced_logging_on_403_error(self):
        """Test that 403 'Not authenticated' errors trigger comprehensive logging."""
        # Mock the session factory to raise a 403 error
        with patch('netra_backend.app.dependencies.get_session_factory') as mock_factory:
            # Create a mock factory that raises 403 error
            mock_factory_instance = AsyncMock()
            mock_factory.return_value = mock_factory_instance
            
            # Configure the mock to raise a 403 error with "Not authenticated"
            mock_factory_instance.get_request_scoped_session.side_effect = Exception("403: Not authenticated")
            
            # Attempt to get a session, which should trigger enhanced logging
            with pytest.raises(Exception, match="403: Not authenticated"):
                async for session in get_request_scoped_db_session():
                    pass  # This shouldn't execute due to the exception
            
            # Verify comprehensive logging was triggered
            log_messages = ' '.join(self.log_capture)
            
            # Check for key logging enhancements
            assert "FUNCTION_START: get_request_scoped_db_session called" in log_messages
            assert "THIS IS WHERE 'system' COMES FROM!" in log_messages
            assert "CRITICAL_403_NOT_AUTHENTICATED_ERROR" in log_messages
            assert "hardcoded_system_placeholder" in log_messages
            assert "authentication_middleware_blocked_system_user" in log_messages
            
            # Verify correlation ID was generated and logged
            assert any("correlation_id" in msg for msg in self.log_capture)
            assert any("request_id" in msg for msg in self.log_capture)
            
            # Verify debugging steps are provided
            assert any("Check authentication middleware logs" in msg for msg in self.log_capture)
            assert any("Verify SERVICE_SECRET configuration" in msg for msg in self.log_capture)
    
    @pytest.mark.asyncio
    async def test_system_user_success_logging(self):
        """Test comprehensive logging when system user authentication succeeds."""
        # Mock successful session creation
        with patch('netra_backend.app.dependencies.get_session_factory') as mock_factory:
            mock_factory_instance = AsyncMock()
            mock_factory.return_value = mock_factory_instance
            
            # Create a mock session
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            mock_factory_instance.get_request_scoped_session.return_value = mock_session
            
            # Mock _validate_session_type to pass
            with patch('netra_backend.app.dependencies._validate_session_type'):
                # Get session successfully
                async for session in get_request_scoped_db_session():
                    assert session is mock_session
                    break
                
                # Verify success logging
                log_messages = ' '.join(self.log_capture)
                
                assert "SUCCESS: Database session" in log_messages
                assert "SYSTEM USER SESSION: Created session for user_id='system'" in log_messages
                assert "Service-to-service authentication" in log_messages
                assert "create_request_scoped_db_session_SUCCESS" in log_messages
    
    def test_auth_trace_logger_comprehensive_dump(self):
        """Test the comprehensive context dump functionality."""
        from netra_backend.app.logging.auth_trace_logger import AuthTraceContext
        from datetime import datetime, timezone
        
        # Create a test context
        context = AuthTraceContext(
            user_id="system",
            request_id="test_req_123",
            correlation_id="test_corr_456",
            operation="test_operation"
        )
        
        # Create a test error
        test_error = Exception("403: Not authenticated")
        
        # Test comprehensive context dump
        comprehensive_dump = auth_tracer.dump_all_context_safely(
            context, 
            test_error,
            {
                "session_id": "test_session_789",
                "thread_id": "test_thread_101", 
                "function_name": "test_function"
            }
        )
        
        # Verify all expected context is included
        assert comprehensive_dump["ids"]["user_id"] == "system"
        assert comprehensive_dump["ids"]["request_id"] == "test_req_123"
        assert comprehensive_dump["ids"]["correlation_id"] == "test_corr_456"
        assert comprehensive_dump["ids"]["session_id"] == "test_session_789"
        
        assert comprehensive_dump["auth_state"]["user_type"] == "system"
        assert comprehensive_dump["auth_state"]["is_service_call"] is True
        
        assert comprehensive_dump["error_info"]["message"] == "403: Not authenticated"
        assert comprehensive_dump["auth_state"]["auth_indicators"]["has_403_error"] is True
        assert comprehensive_dump["auth_state"]["auth_indicators"]["has_not_authenticated"] is True
        
        # Verify environment detection works
        assert "environment" in comprehensive_dump
        
        # Verify additional context is included
        assert comprehensive_dump["additional"]["function_name"] == "test_function"
    
    def test_log_authentication_context_dump_utility(self):
        """Test the utility function for quick context dumping."""
        # Clear previous logs
        self.log_capture.clear()
        
        # Test successful context dump
        log_authentication_context_dump(
            user_id="test_user",
            request_id="test_req_999",
            operation="test_auth_operation",
            test_param="test_value",
            debugging_info={"key": "value"}
        )
        
        # Verify logging occurred
        log_messages = ' '.join(self.log_capture)
        assert "AUTH_CONTEXT_DUMP: test_auth_operation for user 'test_user'" in log_messages
        assert "test_req_999" in log_messages
        assert "FULL_CONTEXT:" in log_messages
    
    def test_log_authentication_context_dump_with_error(self):
        """Test context dump with error information."""
        # Clear previous logs  
        self.log_capture.clear()
        
        test_error = Exception("Test authentication error")
        
        # Test error context dump
        log_authentication_context_dump(
            user_id="error_user",
            request_id="error_req_123",
            operation="test_error_operation", 
            error=test_error,
            error_stage="middleware_validation"
        )
        
        # Verify error logging occurred
        log_messages = ' '.join(self.log_capture)
        assert "AUTH_TRACE_FAILURE: test_error_operation failed" in log_messages
        assert "error_user" in log_messages
        assert "Test authentication error" in log_messages
        assert "COMPREHENSIVE_CONTEXT_DUMP:" in log_messages
    
    @pytest.mark.asyncio
    async def test_database_connection_error_logging(self):
        """Test enhanced logging when database connection fails."""
        # Mock database connection failure
        with patch('netra_backend.app.dependencies.get_session_factory') as mock_factory:
            mock_factory.side_effect = OperationalError("Database connection failed", None, None)
            
            # Attempt to get session
            with pytest.raises(OperationalError):
                async for session in get_request_scoped_db_session():
                    pass
            
            # Verify database connection error logging
            log_messages = ' '.join(self.log_capture)
            assert "CRITICAL ERROR: Failed to create request-scoped database session" in log_messages
            assert "Database connection failed" in log_messages
            assert "COMPREHENSIVE CONTEXT DUMP" in log_messages or "FALLBACK_DEBUG" in log_messages
    
    def test_safe_context_extraction_with_none_values(self):
        """Test that context extraction handles None values safely."""
        from netra_backend.app.logging.auth_trace_logger import AuthTraceContext
        
        # Create context with missing/None values
        context = AuthTraceContext(
            user_id=None,  # None user_id
            request_id="",  # Empty request_id
            correlation_id="test_corr",
            operation=""  # Empty operation
        )
        
        # Test that comprehensive dump handles None values safely
        comprehensive_dump = auth_tracer.dump_all_context_safely(context, None, None)
        
        # Verify None values are handled properly
        assert comprehensive_dump["ids"]["user_id"] == "unknown"  # None converted to "unknown"
        assert comprehensive_dump["ids"]["request_id"] == "unknown"  # Empty converted to "unknown"
        assert comprehensive_dump["ids"]["correlation_id"] == "test_corr"
        assert comprehensive_dump["ids"]["operation"] == "unknown"  # Empty converted to "unknown"
    
    def test_authentication_failure_hint_generation(self):
        """Test that appropriate debugging hints are generated for different error types."""
        from netra_backend.app.logging.auth_trace_logger import AuthTraceContext
        
        context = AuthTraceContext(
            user_id="system",
            request_id="test_req",
            correlation_id="test_corr",
            operation="test_op"
        )
        
        # Test 403 Not authenticated error
        error_403 = Exception("403: Not authenticated")
        auth_tracer.log_failure(context, error_403)
        
        # Check that appropriate hints were added
        hints = getattr(context, 'debug_hints', [])
        
        assert any("403 'Not authenticated' suggests JWT validation failed" in hint for hint in hints)
        assert any("System user auth failure indicates service-to-service problem" in hint for hint in hints)
        assert any("Check SERVICE_SECRET environment variable" in hint for hint in hints)
        
        # Verify comprehensive logging occurred
        log_messages = ' '.join(self.log_capture)
        assert "CRITICAL_AUTH_FAILURE: 403 'Not authenticated' error detected" in log_messages
        assert "SYSTEM_USER_AUTH_FAILURE: The 'system' user failed authentication" in log_messages
    
    def test_environment_detection(self):
        """Test environment detection in auth tracer."""
        # Test environment detection methods
        assert hasattr(auth_tracer, '_is_development_env')
        assert hasattr(auth_tracer, '_is_staging_env') 
        assert hasattr(auth_tracer, '_is_production_env')
        
        # These should not raise exceptions
        is_dev = auth_tracer._is_development_env()
        is_staging = auth_tracer._is_staging_env()
        is_prod = auth_tracer._is_production_env()
        
        # Should return boolean values
        assert isinstance(is_dev, bool)
        assert isinstance(is_staging, bool)
        assert isinstance(is_prod, bool)