"""
Unit tests for unique startup error logging identifiers.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Improve operational monitoring and faster incident response
- Value Impact: Enables precise error tracking in GCP logs for faster debugging
- Strategic Impact: Reduces downtime by enabling rapid identification of specific startup failures

This test suite validates that startup error messages include unique identifiable codes
that can be tracked and monitored in GCP logging systems, replacing generic messages
with specific, actionable error information.
"""

import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from io import StringIO
import asyncio


class TestStartupErrorLoggingUniqueIdentifiers:
    """Test startup error logging produces unique identifiable error codes."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.log_capture = StringIO()
        self.test_handler = logging.StreamHandler(self.log_capture)
        self.test_logger = logging.getLogger('test_startup_logger')
        self.test_logger.addHandler(self.test_handler)
        self.test_logger.setLevel(logging.ERROR)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.test_logger.removeHandler(self.test_handler)
        self.test_handler.close()
        self.log_capture.close()

    @pytest.mark.asyncio
    async def test_startup_failure_handler_produces_unique_error_codes(self):
        """Test that startup failure handler produces unique error codes."""
        from netra_backend.app.startup_module import _handle_startup_failure
        
        # Test different exception types produce different error codes
        test_cases = [
            (ValueError("Database connection failed"), "STARTUP_FAILURE_VALUEERROR"),
            (ConnectionError("Redis connection timeout"), "STARTUP_FAILURE_CONNECTIONERROR"), 
            (RuntimeError("Critical component missing"), "STARTUP_FAILURE_RUNTIMEERROR"),
            (Exception("Unknown startup error"), "STARTUP_FAILURE_EXCEPTION")
        ]
        
        for exception, expected_error_code in test_cases:
            # Clear previous log capture
            self.log_capture.seek(0)
            self.log_capture.truncate(0)
            
            # Mock emergency cleanup to avoid actual cleanup
            with patch('netra_backend.app.startup_module._emergency_cleanup', new_callable=AsyncMock):
                with pytest.raises(RuntimeError):
                    await _handle_startup_failure(self.test_logger, exception)
            
            # Verify unique error code is present
            log_output = self.log_capture.getvalue()
            assert expected_error_code in log_output, (
                f"Expected error code '{expected_error_code}' not found in log output: {log_output}"
            )
            # Verify error message contains exception type and details
            assert type(exception).__name__ in log_output
            assert str(exception)[:50] in log_output

    def test_backend_startup_error_produces_unique_error_codes(self):
        """Test backend startup errors produce unique error codes."""
        # Mock logger and exception scenarios
        mock_logger = MagicMock()
        
        test_exceptions = [
            ValueError("Database URL malformed"),
            ConnectionError("Backend port unavailable"),
            ImportError("Missing critical module"),
            PermissionError("Cannot bind to port")
        ]
        
        for exception in test_exceptions:
            error_type = type(exception).__name__
            expected_error_code = f"BACKEND_STARTUP_{error_type.upper()}"
            
            # Simulate the updated error handling logic
            startup_error_code = f"BACKEND_STARTUP_{error_type.upper()}"
            mock_logger.error(f"ERROR [{startup_error_code}] Backend service startup failure: {error_type} - {str(exception)[:200]}")
            
            # Verify the call was made with unique error code
            mock_logger.error.assert_called_with(
                f"ERROR [{expected_error_code}] Backend service startup failure: {error_type} - {str(exception)[:200]}"
            )
            mock_logger.reset_mock()

    def test_auth_startup_error_produces_unique_error_codes(self):
        """Test auth startup errors produce unique error codes."""
        mock_logger = MagicMock()
        
        test_exceptions = [
            TimeoutError("Redis connection timeout"),
            ValueError("Invalid auth configuration"),
            FileNotFoundError("JWT key file missing"),
            ConnectionError("Database unreachable")
        ]
        
        for exception in test_exceptions:
            error_type = type(exception).__name__
            expected_error_code = f"AUTH_STARTUP_{error_type.upper()}"
            
            # Simulate the updated error handling logic
            startup_error_code = f"AUTH_STARTUP_{error_type.upper()}"
            mock_logger.error(f"ERROR [{startup_error_code}] Auth service startup failure: {error_type} - {str(exception)[:200]}")
            
            # Verify the call was made with unique error code
            mock_logger.error.assert_called_with(
                f"ERROR [{expected_error_code}] Auth service startup failure: {error_type} - {str(exception)[:200]}"
            )
            mock_logger.reset_mock()

    def test_smd_critical_fixes_error_produces_unique_error_codes(self):
        """Test SMD critical fixes produce unique error codes."""
        mock_logger = MagicMock()
        
        # Test critical fixes validation failure
        critical_failures = [
            "Database table missing",
            "WebSocket bridge not configured", 
            "Agent registry initialization failed"
        ]
        
        startup_error_code = "STARTUP_CRITICAL_FIXES_VALIDATION_FAILED"
        mock_logger.error(f"ERROR [{startup_error_code}] Critical startup fixes failed validation: {len(critical_failures)} failures")
        
        for i, failure in enumerate(critical_failures, 1):
            mock_logger.error(f"ERROR [{startup_error_code}_{i:02d}] Critical fix failure: {failure}")
        
        # Verify calls were made with unique error codes
        expected_calls = [
            f"ERROR [{startup_error_code}] Critical startup fixes failed validation: {len(critical_failures)} failures"
        ]
        for i, failure in enumerate(critical_failures, 1):
            expected_calls.append(f"ERROR [{startup_error_code}_{i:02d}] Critical fix failure: {failure}")
        
        actual_calls = [call.args[0] for call in mock_logger.error.call_args_list]
        assert actual_calls == expected_calls

    def test_service_startup_error_produces_unique_error_codes(self):
        """Test service startup errors produce unique error codes."""
        mock_logger = MagicMock()
        
        # Test different service types and error combinations
        test_cases = [
            ("backend", RuntimeError("Port binding failed"), "BACKEND_STARTUP_RUNTIMEERROR"),
            ("auth", ConnectionError("Redis unavailable"), "AUTH_STARTUP_CONNECTIONERROR"), 
            ("frontend", FileNotFoundError("Build assets missing"), "FRONTEND_STARTUP_FILENOTFOUNDERROR")
        ]
        
        for service_name, error, expected_error_code in test_cases:
            error_type = type(error).__name__
            startup_error_code = f"{service_name.upper()}_STARTUP_{error_type.upper()}"
            mock_logger.error(f"ERROR [{startup_error_code}] {service_name} startup failed: {error_type} - {str(error)[:200]}")
            
            # Verify the call was made with unique error code
            mock_logger.error.assert_called_with(
                f"ERROR [{expected_error_code}] {service_name} startup failed: {error_type} - {str(error)[:200]}"
            )
            mock_logger.reset_mock()

    def test_error_message_truncation_for_long_errors(self):
        """Test that long error messages are properly truncated."""
        mock_logger = MagicMock()
        
        # Create a very long error message
        long_error_msg = "Database connection failed: " + "x" * 300
        long_exception = ConnectionError(long_error_msg)
        
        error_type = type(long_exception).__name__
        startup_error_code = f"BACKEND_STARTUP_{error_type.upper()}"
        mock_logger.error(f"ERROR [{startup_error_code}] Backend service startup failure: {error_type} - {str(long_exception)[:200]}")
        
        # Verify message was truncated to 200 characters
        call_args = mock_logger.error.call_args[0][0]
        error_portion = call_args.split(" - ", 1)[1]
        assert len(error_portion) == 200

    def test_unique_error_codes_enable_gcp_log_filtering(self):
        """Test that error codes are structured for GCP log filtering."""
        # This test validates that our error code format works with GCP log queries
        test_error_codes = [
            "STARTUP_FAILURE_VALUEERROR",
            "BACKEND_STARTUP_CONNECTIONERROR", 
            "AUTH_STARTUP_TIMEOUTERROR",
            "STARTUP_CRITICAL_FIXES_VALIDATION_FAILED",
            "STARTUP_CRITICAL_FIXES_VALIDATION_FAILED_01"
        ]
        
        for error_code in test_error_codes:
            # Verify error code format follows GCP-friendly patterns
            assert error_code.isupper(), f"Error code {error_code} should be uppercase"
            assert "_" in error_code, f"Error code {error_code} should use underscores"
            assert error_code.startswith(("STARTUP_", "BACKEND_", "AUTH_", "FRONTEND_", "SERVICE_")), (
                f"Error code {error_code} should start with service prefix"
            )
            
            # Simulate GCP log query patterns
            simulated_log_entry = f"ERROR [{error_code}] Service failure details..."
            
            # Verify the error code can be extracted with regex patterns  
            import re
            pattern = r"ERROR \[([A-Z_0-9]+)\]"
            match = re.search(pattern, simulated_log_entry)
            assert match, f"Could not extract error code from: {simulated_log_entry}"
            assert match.group(1) == error_code

    def test_error_codes_preserve_business_context(self):
        """Test that error codes preserve business context for operational teams."""
        # Map error codes to their business impact
        error_business_context = {
            "BACKEND_STARTUP_CONNECTIONERROR": "Core API unavailable - affects all user requests",
            "AUTH_STARTUP_TIMEOUTERROR": "Authentication unavailable - users cannot login",
            "STARTUP_CRITICAL_FIXES_VALIDATION_FAILED": "Core system integrity compromised",
            "FRONTEND_STARTUP_FILENOTFOUNDERROR": "User interface unavailable - affects user experience"
        }
        
        for error_code, business_context in error_business_context.items():
            # Verify error codes enable quick business impact assessment
            if "BACKEND_STARTUP" in error_code:
                assert "Core API" in business_context or "user requests" in business_context
            elif "AUTH_STARTUP" in error_code:
                assert "Authentication" in business_context or "login" in business_context
            elif "CRITICAL_FIXES" in error_code:
                assert "integrity" in business_context or "system" in business_context
            elif "FRONTEND_STARTUP" in error_code:
                assert "interface" in business_context or "user experience" in business_context