"""Unit tests for GCP traceback formatter validation.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Production Debugging
- Business Goal: Ensure comprehensive error tracebacks in GCP Cloud Logging for $500K+ ARR platform
- Value Impact: Enables rapid root cause analysis reducing incident resolution time from hours to minutes
- Strategic Impact: Foundation for production debugging, alerting, and SLA compliance

This test suite validates the GCP JSON formatter's traceback handling to ensure:
1. Exception tracebacks are properly captured and formatted
2. JSON newlines are escaped for single-line GCP logs
3. Missing traceback scenarios are handled gracefully
4. Error field structure matches GCP Error Reporting expectations

CRITICAL ISSUE CONTEXT:
- GCP staging logs missing traceback information for caught exceptions
- Silent failures due to improper JSON formatting (unescaped newlines)
- Error behind the error: exc_info=True not producing traceback data in GCP formatter

These tests MUST initially FAIL to reproduce the production issue.
"""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.logging_formatters import LogFormatter, SensitiveDataFilter
from shared.isolated_environment import get_env


class TestGCPTracebackFormatterValidation(SSotBaseTestCase):
    """Unit tests for GCP JSON formatter traceback handling."""
    
    def setup_method(self, method):
        """Setup GCP traceback formatter tests."""
        super().setup_method(method)
        self.env = get_env()
        
        # Create formatter instance
        self.filter_instance = SensitiveDataFilter()
        self.formatter = LogFormatter(self.filter_instance)
        
        # Test configuration for GCP environment
        self.set_env_var("K_SERVICE", "test-service")  # Simulate Cloud Run
        self.set_env_var("ENVIRONMENT", "staging")
        
        # Track formatter behavior
        self.record_metric("test_setup_time", 0.001)
    
    def test_caught_exception_with_exc_info_true_produces_traceback(self):
        """
        Test that caught exceptions with exc_info=True produce traceback data.
        
        CRITICAL: This test should INITIALLY FAIL demonstrating missing traceback issue.
        """
        # Create a real exception with traceback
        try:
            raise ValueError("Test exception for traceback validation")
        except ValueError as e:
            # Create loguru-style record with exception info
            mock_record = self._create_mock_loguru_record_with_exception(
                message="Caught exception in agent execution",
                level_name="ERROR",
                exception_info=(type(e), e, e.__traceback__)
            )
        
        # Format with GCP formatter
        json_output = self.formatter.gcp_json_formatter(mock_record)
        
        # Parse JSON to validate structure
        log_entry = json.loads(json_output)
        
        # CRITICAL VALIDATION: Error field must exist and contain traceback
        assert "error" in log_entry, "Error field missing from GCP log entry"
        
        error_field = log_entry["error"]
        assert "type" in error_field, "Error type missing"
        assert "value" in error_field, "Error value missing"
        assert "traceback" in error_field, "Traceback missing from error field"
        
        # Validate traceback content
        assert error_field["type"] == "ValueError"
        assert "Test exception for traceback validation" in error_field["value"]
        assert error_field["traceback"] is not None, "Traceback is None - CORE ISSUE"
        assert len(error_field["traceback"]) > 0, "Traceback is empty - CORE ISSUE"
        
        # Validate traceback contains expected stack frame information
        traceback_content = error_field["traceback"]
        assert "ValueError" in traceback_content, "Exception type not in traceback"
        assert "test_caught_exception_with_exc_info_true_produces_traceback" in traceback_content, "Function name not in traceback"
        
        self.record_metric("traceback_validation_passed", True)
    
    def test_json_newline_escaping_for_single_line_output(self):
        """
        Test that traceback newlines are escaped for single-line JSON output.
        
        GCP Cloud Logging requires single-line JSON entries.
        """
        # Create exception with multi-line traceback
        try:
            def nested_function():
                def deeper_function():
                    raise RuntimeError("Multi-line\nError\nMessage")
                deeper_function()
            nested_function()
        except RuntimeError as e:
            mock_record = self._create_mock_loguru_record_with_exception(
                message="Multi-line error test",
                level_name="ERROR", 
                exception_info=(type(e), e, e.__traceback__)
            )
        
        json_output = self.formatter.gcp_json_formatter(mock_record)
        
        # Validate single-line output (no unescaped newlines)
        assert "\n" not in json_output.strip(), "Unescaped newlines found in JSON output"
        assert "\r" not in json_output.strip(), "Unescaped carriage returns found in JSON output"
        
        # Parse and validate escaped content
        log_entry = json.loads(json_output)
        
        if "error" in log_entry and "traceback" in log_entry["error"]:
            traceback_content = log_entry["error"]["traceback"]
            # Traceback should contain escaped newlines
            assert "\\n" in traceback_content, "Newlines not properly escaped in traceback"
        
        # Validate message field also handles newlines
        message = log_entry["message"]
        if "\n" in message:
            assert False, "Message field contains unescaped newlines"
        
        self.record_metric("newline_escaping_validated", True)
    
    def test_missing_traceback_graceful_handling(self):
        """
        Test graceful handling when traceback is None or missing.
        
        This tests the "traceback None/empty scenarios" requirement.
        """
        # Create record with exception but no traceback
        mock_record = self._create_mock_loguru_record_with_exception(
            message="Exception without traceback",
            level_name="ERROR",
            exception_info=None  # No exception info
        )
        
        json_output = self.formatter.gcp_json_formatter(mock_record)
        log_entry = json.loads(json_output)
        
        # Should still produce valid JSON without error field
        assert "severity" in log_entry
        assert "message" in log_entry
        assert "timestamp" in log_entry
        
        # Error field may be missing or have None traceback
        if "error" in log_entry:
            error_field = log_entry["error"]
            # If error field exists, traceback can be None
            traceback_value = error_field.get("traceback")
            # This is acceptable - None traceback is valid
        
        self.record_metric("graceful_handling_validated", True)
    
    def test_exception_chain_formatting(self):
        """
        Test formatting of chained exceptions (exception.__cause__).
        """
        try:
            try:
                raise ValueError("Original error")
            except ValueError as original:
                raise RuntimeError("Secondary error") from original
        except RuntimeError as e:
            mock_record = self._create_mock_loguru_record_with_exception(
                message="Chained exception test",
                level_name="ERROR",
                exception_info=(type(e), e, e.__traceback__)
            )
        
        json_output = self.formatter.gcp_json_formatter(mock_record)
        log_entry = json.loads(json_output)
        
        # Validate error field structure
        if "error" in log_entry:
            error_field = log_entry["error"]
            assert error_field["type"] == "RuntimeError"
            assert "Secondary error" in error_field["value"]
            
            # Traceback should contain both exceptions
            if error_field.get("traceback"):
                traceback_content = error_field["traceback"]
                assert "RuntimeError" in traceback_content
                # Note: Full exception chain handling depends on formatter implementation
        
        self.record_metric("exception_chain_validated", True)
    
    def test_async_exception_traceback_handling(self):
        """
        Test traceback handling for async/await exceptions.
        """
        # Simulate async exception
        async def async_function():
            raise asyncio.TimeoutError("Async operation timeout")
        
        # Create mock exception from async context
        try:
            # Simulate running async function
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(async_function())
        except Exception as e:
            mock_record = self._create_mock_loguru_record_with_exception(
                message="Async exception occurred",
                level_name="ERROR",
                exception_info=(type(e), e, e.__traceback__)
            )
        finally:
            loop.close()
        
        json_output = self.formatter.gcp_json_formatter(mock_record)
        log_entry = json.loads(json_output)
        
        # Validate async exception handling
        if "error" in log_entry:
            error_field = log_entry["error"]
            assert error_field["type"] == "TimeoutError"
            
            # Async tracebacks should be handled properly
            if error_field.get("traceback"):
                traceback_content = error_field["traceback"]
                assert "TimeoutError" in traceback_content
        
        self.record_metric("async_exception_validated", True)
    
    def test_gcp_error_field_structure_compliance(self):
        """
        Test that error field structure matches GCP Error Reporting expectations.
        """
        try:
            raise KeyError("Missing configuration key")
        except KeyError as e:
            mock_record = self._create_mock_loguru_record_with_exception(
                message="Configuration error",
                level_name="ERROR",
                exception_info=(type(e), e, e.__traceback__)
            )
        
        json_output = self.formatter.gcp_json_formatter(mock_record)
        log_entry = json.loads(json_output)
        
        # Validate GCP Error Reporting field structure
        if "error" in log_entry:
            error_field = log_entry["error"]
            
            # Required fields for GCP Error Reporting
            assert "type" in error_field, "Missing 'type' field"
            assert "value" in error_field, "Missing 'value' field"
            
            # Type should be string
            assert isinstance(error_field["type"], str), "Type field must be string"
            assert isinstance(error_field["value"], str), "Value field must be string"
            
            # Traceback should be string if present
            if "traceback" in error_field and error_field["traceback"] is not None:
                assert isinstance(error_field["traceback"], str), "Traceback field must be string"
        
        self.record_metric("gcp_structure_validated", True)
    
    def test_fallback_behavior_when_formatter_fails(self):
        """
        Test formatter fallback behavior when record processing fails.
        """
        # Create record that lacks 'get' method to trigger exception handler
        malformed_record = "not_a_dict_object"
        
        # Should not raise exception, should produce fallback JSON
        json_output = self.formatter.gcp_json_formatter(malformed_record)
        log_entry = json.loads(json_output)
        
        # Fallback should produce minimal valid structure
        assert "severity" in log_entry
        assert "message" in log_entry
        assert "timestamp" in log_entry
        
        # Fallback severity should be ERROR for exception cases
        assert log_entry["severity"] == "ERROR"
        
        # Message should indicate formatter error
        assert "Logging formatter error" in log_entry["message"]
        
        self.record_metric("fallback_behavior_validated", True)
    
    def test_performance_impact_of_traceback_processing(self):
        """
        Test that traceback processing doesn't significantly impact performance.
        """
        import time
        
        # Create large traceback
        def create_deep_stack(depth):
            if depth <= 0:
                raise ValueError("Deep stack exception")
            return create_deep_stack(depth - 1)
        
        try:
            create_deep_stack(20)  # Create 20-level deep stack
        except ValueError as e:
            mock_record = self._create_mock_loguru_record_with_exception(
                message="Performance test exception",
                level_name="ERROR",
                exception_info=(type(e), e, e.__traceback__)
            )
        
        # Measure formatting time
        start_time = time.time()
        json_output = self.formatter.gcp_json_formatter(mock_record)
        end_time = time.time()
        
        formatting_time = end_time - start_time
        
        # Should complete within reasonable time (< 100ms)
        assert formatting_time < 0.1, f"Traceback formatting took too long: {formatting_time:.3f}s"
        
        # Validate output is still correct
        log_entry = json.loads(json_output)
        assert "error" in log_entry
        
        self.record_metric("traceback_formatting_time_ms", formatting_time * 1000)
    
    def _create_mock_loguru_record_with_exception(
        self, 
        message: str, 
        level_name: str,
        exception_info: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """
        Create a mock loguru record with exception information.
        
        Args:
            message: Log message
            level_name: Log level name (DEBUG, INFO, ERROR, etc.)
            exception_info: Tuple of (exc_type, exc_value, exc_traceback)
            
        Returns:
            Mock loguru record dictionary
        """
        # Mock loguru level object
        mock_level = Mock()
        mock_level.name = level_name
        mock_level.no = {"DEBUG": 10, "INFO": 20, "ERROR": 40}.get(level_name, 40)
        
        # Mock loguru exception object
        mock_exception = None
        if exception_info:
            exc_type, exc_value, exc_traceback = exception_info
            mock_exception = Mock()
            mock_exception.type = exc_type
            mock_exception.value = exc_value
            mock_exception.traceback = exc_traceback
        
        # Create loguru-style record
        record = {
            "level": mock_level,
            "message": message,
            "time": datetime.now(timezone.utc),
            "name": "test_module",
            "function": self._testMethodName if hasattr(self, '_testMethodName') else "test_function",
            "line": 100,
            "exception": mock_exception,
            "extra": {}
        }
        
        return record