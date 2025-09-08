"""Simple Test for Enhanced Authentication Debug Logging

This test validates the basic functionality of the enhanced authentication
debug logging system without complex mocking.
"""

import pytest
import logging
from datetime import datetime, timezone

from netra_backend.app.logging.auth_trace_logger import (
    AuthTraceLogger, 
    AuthTraceContext,
    log_authentication_context_dump
)


class TestAuthDebugLoggingBasic:
    """Basic tests for authentication debug logging."""
    
    def setup_method(self):
        """Set up test environment."""
        self.log_messages = []
        
        # Create a simple log handler to capture messages
        class SimpleLogHandler(logging.Handler):
            def __init__(self, message_list):
                super().__init__()
                self.message_list = message_list
                
            def emit(self, record):
                self.message_list.append(record.getMessage())
        
        # Set up logging capture
        self.handler = SimpleLogHandler(self.log_messages)
        self.handler.setLevel(logging.INFO)
        
        # Add to auth trace logger
        logger = logging.getLogger('netra_backend.app.logging.auth_trace_logger')
        logger.addHandler(self.handler)
        logger.setLevel(logging.INFO)
        
        self.auth_tracer = AuthTraceLogger()
    
    def teardown_method(self):
        """Clean up."""
        logger = logging.getLogger('netra_backend.app.logging.auth_trace_logger')
        logger.removeHandler(self.handler)
    
    def test_auth_trace_context_creation(self):
        """Test basic AuthTraceContext creation and data."""
        context = AuthTraceContext(
            user_id="test_user",
            request_id="req_123",
            correlation_id="corr_456",
            operation="test_operation"
        )
        
        assert context.user_id == "test_user"
        assert context.request_id == "req_123"
        assert context.correlation_id == "corr_456"
        assert context.operation == "test_operation"
        assert context.auth_state == "unknown"
        assert isinstance(context.timestamp, datetime)
    
    def test_comprehensive_context_dump_basic(self):
        """Test comprehensive context dump with basic data."""
        context = AuthTraceContext(
            user_id="system",
            request_id="req_789",
            correlation_id="corr_101",
            operation="session_creation"
        )
        
        error = Exception("403: Not authenticated")
        additional_context = {
            "session_id": "sess_123",
            "thread_id": "thread_456"
        }
        
        # Test the comprehensive dump
        dump = self.auth_tracer.dump_all_context_safely(context, error, additional_context)
        
        # Verify key components exist
        assert "ids" in dump
        assert "timing" in dump
        assert "auth_state" in dump
        assert "error_info" in dump
        
        # Verify IDs are captured
        assert dump["ids"]["user_id"] == "system"
        assert dump["ids"]["request_id"] == "req_789"
        assert dump["ids"]["correlation_id"] == "corr_101"
        assert dump["ids"]["session_id"] == "sess_123"
        
        # Verify auth state analysis
        assert dump["auth_state"]["user_type"] == "system"
        assert dump["auth_state"]["is_service_call"] is True
        
        # Verify error analysis
        assert dump["error_info"]["message"] == "403: Not authenticated"
        assert dump["auth_state"]["auth_indicators"]["has_403_error"] is True
        assert dump["auth_state"]["auth_indicators"]["has_not_authenticated"] is True
    
    def test_system_user_detection(self):
        """Test system user detection and classification."""
        # Test exact "system" user
        context_system = AuthTraceContext(
            user_id="system",
            request_id="req_1",
            correlation_id="corr_1",
            operation="test"
        )
        
        dump_system = self.auth_tracer.dump_all_context_safely(context_system, None, None)
        assert dump_system["auth_state"]["user_type"] == "system"
        assert dump_system["auth_state"]["is_service_call"] is True
        
        # Test "system_" prefixed user
        context_system_prefix = AuthTraceContext(
            user_id="system_service_123",
            request_id="req_2", 
            correlation_id="corr_2",
            operation="test"
        )
        
        dump_system_prefix = self.auth_tracer.dump_all_context_safely(context_system_prefix, None, None)
        assert dump_system_prefix["auth_state"]["user_type"] == "regular"  # Only exact "system" gets "system" type
        assert dump_system_prefix["auth_state"]["is_service_call"] is True  # But still detected as service call
        
        # Test regular user
        context_regular = AuthTraceContext(
            user_id="user_456",
            request_id="req_3",
            correlation_id="corr_3", 
            operation="test"
        )
        
        dump_regular = self.auth_tracer.dump_all_context_safely(context_regular, None, None)
        assert dump_regular["auth_state"]["user_type"] == "regular"
        assert dump_regular["auth_state"]["is_service_call"] is False
    
    def test_error_analysis_for_403_errors(self):
        """Test error analysis specifically for 403 authentication errors."""
        context = AuthTraceContext(
            user_id="system",
            request_id="req_403",
            correlation_id="corr_403",
            operation="auth_test"
        )
        
        # Test 403 Not authenticated error
        error_403 = Exception("403: Not authenticated")
        dump = self.auth_tracer.dump_all_context_safely(context, error_403, None)
        
        error_indicators = dump["auth_state"]["auth_indicators"]
        assert error_indicators["has_403_error"] is True
        assert error_indicators["has_not_authenticated"] is True
        assert error_indicators["error_suggests_auth_failure"] is True
        assert error_indicators["user_id_is_system"] is True
        
        # Test other auth-related errors
        error_401 = Exception("401: Unauthorized")
        dump_401 = self.auth_tracer.dump_all_context_safely(context, error_401, None)
        assert dump_401["auth_state"]["auth_indicators"]["has_401_error"] is True
        assert dump_401["auth_state"]["auth_indicators"]["has_403_error"] is False
    
    def test_safe_none_handling(self):
        """Test that None values are handled safely in context dumps."""
        # Create context with None/empty values
        context = AuthTraceContext(
            user_id="",  # Empty string
            request_id=None,  # Will be set to None internally
            correlation_id="corr_safe",
            operation=""  # Empty string
        )
        context.user_id = None  # Explicitly set to None
        context.request_id = None
        
        # Should not crash with None values
        dump = self.auth_tracer.dump_all_context_safely(context, None, None)
        
        # Verify None values are converted to "unknown"
        assert dump["ids"]["user_id"] == "unknown"
        assert dump["ids"]["request_id"] == "unknown" 
        assert dump["ids"]["correlation_id"] == "corr_safe"
        assert dump["ids"]["operation"] == "unknown"
    
    def test_debug_hints_generation(self):
        """Test that appropriate debug hints are generated.""" 
        context = AuthTraceContext(
            user_id="system",
            request_id="req_hints",
            correlation_id="corr_hints", 
            operation="session_creation"
        )
        
        # Test 403 Not authenticated error with system user
        error = Exception("403: Not authenticated")
        
        # Use the log_failure method which adds hints
        self.auth_tracer.log_failure(context, error, None)
        
        # Check that hints were added
        hints = getattr(context, 'debug_hints', [])
        
        # Should have 403-specific hints
        assert any("403 'Not authenticated' suggests JWT validation failed" in hint for hint in hints)
        assert any("Check authentication middleware configuration" in hint for hint in hints)
        
        # Should have system user specific hints
        assert any("System user auth failure indicates service-to-service problem" in hint for hint in hints)
        assert any("Check SERVICE_SECRET environment variable" in hint for hint in hints)
        
        # Should have session-specific hints (operation contains "session")
        assert any("Session-related auth failure may indicate database auth issues" in hint for hint in hints)
    
    def test_log_authentication_context_dump_basic(self):
        """Test the utility function for context dumping."""
        # Clear previous messages
        self.log_messages.clear()
        
        # Test basic context dump without error
        log_authentication_context_dump(
            user_id="test_user_dump",
            request_id="req_dump_123",
            operation="test_dump_operation",
            test_param="test_value"
        )
        
        # Should have generated some log messages
        assert len(self.log_messages) > 0
        
        # Join messages to search across all
        all_messages = " ".join(self.log_messages)
        assert "test_user_dump" in all_messages
        assert "req_dump_123" in all_messages
        assert "test_dump_operation" in all_messages
    
    def test_log_authentication_context_dump_with_error(self):
        """Test context dump utility with error."""
        # Clear previous messages
        self.log_messages.clear()
        
        test_error = Exception("Test auth failure")
        
        # Test context dump with error
        log_authentication_context_dump(
            user_id="error_user_dump", 
            request_id="req_error_123",
            operation="test_error_dump",
            error=test_error,
            error_stage="middleware"
        )
        
        # Should have generated error log messages
        assert len(self.log_messages) > 0
        
        all_messages = " ".join(self.log_messages)
        assert "error_user_dump" in all_messages
        assert "req_error_123" in all_messages
        assert "Test auth failure" in all_messages
    
    def test_environment_detection_methods(self):
        """Test environment detection methods work without crashing."""
        # These should not raise exceptions and should return booleans
        assert isinstance(self.auth_tracer._is_development_env(), bool)
        assert isinstance(self.auth_tracer._is_staging_env(), bool)
        assert isinstance(self.auth_tracer._is_production_env(), bool)
    
    def test_clean_none_values_utility(self):
        """Test the utility method for cleaning None values from dicts."""
        test_dict = {
            "keep_this": "value",
            "remove_this": None,
            "nested": {
                "keep_nested": "nested_value",
                "remove_nested": None,
                "empty_dict": {}
            },
            "empty_string": "",
            "zero": 0,
            "false": False
        }
        
        cleaned = self.auth_tracer._clean_none_values(test_dict)
        
        # Should keep non-None values
        assert cleaned["keep_this"] == "value"
        assert cleaned["nested"]["keep_nested"] == "nested_value"
        assert cleaned["empty_string"] == ""  # Empty string should be kept
        assert cleaned["zero"] == 0  # Zero should be kept
        assert cleaned["false"] is False  # False should be kept
        
        # Should remove None values
        assert "remove_this" not in cleaned
        assert "remove_nested" not in cleaned["nested"]
        
        # Empty dicts should be removed
        assert "empty_dict" not in cleaned["nested"] if "nested" in cleaned else True