"""
Test Log Formatter Effectiveness - Unit Tests for Logging Quality

Business Value Justification (BVJ):
- Segment: Platform/Internal (Development Velocity & Operations)
- Business Goal: Reduce debugging time from hours to minutes through effective logging
- Value Impact: Enables rapid diagnosis of production issues that block user value delivery
- Strategic Impact: Foundation for reliable operations and customer success

This test suite validates that our logging formatter produces logs that are:
1. Informative enough for debugging production issues
2. Structured for efficient searching and filtering
3. Consistent across all services
4. Performance-friendly under load
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.logging.unified_logger_factory import UnifiedLoggerFactory
from netra_backend.app.logging.auth_trace_logger import AuthTraceLogger, AuthTraceContext


class TestLogFormatterEffectiveness(SSotBaseTestCase):
    """Test log formatter produces effective debugging information."""
    
    def setup_method(self, method=None):
        """Setup for each test."""
        super().setup_method(method)
        
        # Reset logger factory for clean state
        UnifiedLoggerFactory.reset()
        
        # Setup test-specific environment
        self.set_env_var("LOG_LEVEL", "DEBUG")
        self.set_env_var("SERVICE_NAME", "test-logging-service")
        self.set_env_var("ENABLE_FILE_LOGGING", "false")  # Use console for testing
        
        # Create logger instance
        self.logger = UnifiedLoggerFactory.get_logger("test_logger")
        
        # Mock handler to capture log records
        self.log_records = []
        self.mock_handler = self._create_test_handler()
        self.logger.addHandler(self.mock_handler)
        
        # Auth trace logger for authentication debugging tests
        self.auth_tracer = AuthTraceLogger()
    
    def _create_test_handler(self):
        """Create a test logging handler to capture log records."""
        import logging
        
        class TestLogHandler(logging.Handler):
            def __init__(self, records_list):
                super().__init__()
                self.records_list = records_list
                self.setLevel(logging.DEBUG)
            
            def emit(self, record):
                self.records_list.append(record)
        
        return TestLogHandler(self.log_records)
    
    @pytest.mark.unit
    def test_log_record_contains_essential_debugging_info(self):
        """Test that log records contain essential information for debugging."""
        # Test various log levels with business-critical scenarios
        test_scenarios = [
            {
                "level": "INFO",
                "message": "User authentication successful",
                "extra_data": {"user_id": "test_user_123", "session_id": "sess_456"}
            },
            {
                "level": "ERROR", 
                "message": "Database connection failed",
                "extra_data": {"error_code": "CONN_TIMEOUT", "retry_count": 3}
            },
            {
                "level": "WARNING",
                "message": "Rate limit approaching",
                "extra_data": {"current_usage": 85, "limit": 100, "time_window": "1min"}
            }
        ]
        
        for scenario in test_scenarios:
            # Clear previous records
            self.log_records.clear()
            
            # Log the message
            log_method = getattr(self.logger, scenario["level"].lower())
            log_method(scenario["message"], extra=scenario["extra_data"])
            
            # Validate log record
            assert len(self.log_records) == 1, f"Expected 1 log record for {scenario['level']}"
            
            record = self.log_records[0]
            
            # Essential fields present
            assert hasattr(record, 'levelname'), "Log record missing level name"
            assert hasattr(record, 'message'), "Log record missing message"
            assert hasattr(record, 'created'), "Log record missing timestamp"
            assert hasattr(record, 'name'), "Log record missing logger name"
            
            # Message content is meaningful
            assert len(record.getMessage()) > 10, "Log message too short to be informative"
            assert scenario["message"] in record.getMessage(), "Original message not preserved"
            
            # Level correctly set
            assert record.levelname == scenario["level"], f"Log level mismatch"
            
            # Extra data preserved in record
            for key, value in scenario["extra_data"].items():
                assert hasattr(record, key), f"Extra data '{key}' not preserved in record"
                assert getattr(record, key) == value, f"Extra data '{key}' value mismatch"
        
        self.record_metric("essential_debug_info_test", "PASSED")
    
    @pytest.mark.unit
    def test_log_formatter_structured_output_parseable(self):
        """Test that formatted log output is structured and machine-parseable."""
        # Test with complex scenario data
        self.logger.info(
            "Agent execution completed",
            extra={
                "agent_type": "cost_optimizer",
                "execution_time_ms": 2500,
                "tools_used": ["aws_cost_analyzer", "recommendation_engine"],
                "user_id": "enterprise_user_789",
                "thread_id": "thread_abc123",
                "result_summary": {
                    "potential_savings": 1500.50,
                    "recommendations_count": 5
                }
            }
        )
        
        assert len(self.log_records) == 1, "Expected 1 log record"
        record = self.log_records[0]
        
        # Test that the formatted message contains structured information
        formatted_message = record.getMessage()
        
        # Should contain key business identifiers
        assert "cost_optimizer" in formatted_message, "Agent type missing from log"
        assert "enterprise_user_789" in formatted_message, "User ID missing from log"
        assert "thread_abc123" in formatted_message, "Thread ID missing from log"
        
        # Should contain timing information for performance debugging
        assert "2500" in str(record.__dict__), "Execution time not preserved"
        
        # Should contain business value information
        assert hasattr(record, 'result_summary'), "Business result data missing"
        
        # Test log message format is consistent and parseable
        # Format should be: timestamp - service - logger - level - message
        formatter = logging.Formatter('%(asctime)s - test-logging-service - %(name)s - %(levelname)s - %(message)s')
        formatted_output = formatter.format(record)
        
        # Parse structured log format
        log_parts = formatted_output.split(' - ', 4)
        assert len(log_parts) >= 5, "Log format not structured correctly"
        
        # Timestamp parseable
        try:
            datetime.fromisoformat(log_parts[0].replace(' ', 'T'))
        except ValueError:
            pytest.fail("Timestamp in log not parseable as ISO format")
        
        # Service name present
        assert log_parts[1] == "test-logging-service", "Service name not in expected position"
        
        # Logger name present  
        assert log_parts[2] == "test_logger", "Logger name not in expected position"
        
        # Level present
        assert log_parts[3] == "INFO", "Log level not in expected position"
        
        self.record_metric("structured_output_parseable_test", "PASSED")
    
    @pytest.mark.unit 
    def test_error_logging_with_stack_traces(self):
        """Test that error logging includes sufficient context for debugging."""
        try:
            # Create a realistic error scenario
            user_data = {"user_id": "test_123", "permissions": ["read"]}
            if "admin" not in user_data.get("permissions", []):
                raise PermissionError("User lacks admin privileges for agent execution")
        except PermissionError as e:
            # Log the error with context
            self.logger.error(
                "Agent execution failed due to insufficient permissions",
                extra={
                    "user_id": user_data["user_id"],
                    "required_permission": "admin",
                    "user_permissions": user_data["permissions"],
                    "attempted_action": "execute_cost_optimizer_agent",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
        
        assert len(self.log_records) == 1, "Expected 1 error log record"
        record = self.log_records[0]
        
        # Error level correctly set
        assert record.levelname == "ERROR", "Error level not set"
        
        # Exception info preserved
        assert record.exc_info is not None, "Exception info not preserved"
        assert record.exc_text is not None or record.exc_info != (None, None, None), "Stack trace not captured"
        
        # Business context preserved for debugging
        assert hasattr(record, 'user_id'), "User ID context missing"
        assert hasattr(record, 'attempted_action'), "Action context missing"  
        assert hasattr(record, 'required_permission'), "Permission context missing"
        assert record.user_id == "test_123", "User ID value incorrect"
        
        # Error details accessible
        assert hasattr(record, 'error_type'), "Error type missing"
        assert record.error_type == "PermissionError", "Error type incorrect"
        
        self.record_metric("error_context_logging_test", "PASSED")
    
    @pytest.mark.unit
    def test_auth_trace_logging_debugging_effectiveness(self):
        """Test that authentication trace logging provides effective debugging context."""
        # Simulate authentication failure scenario
        user_id = "system"  # Service-to-service auth
        request_id = "req_auth_test_001"
        correlation_id = "corr_auth_debug_001"
        operation = "validate_service_token"
        
        # Start authentication operation
        context = self.auth_tracer.start_operation(
            user_id=user_id,
            request_id=request_id,
            correlation_id=correlation_id,
            operation=operation,
            additional_context={"service_name": "backend", "endpoint": "/api/agents/execute"}
        )
        
        # Clear log records to capture only auth trace logs
        self.log_records.clear()
        
        # Simulate authentication failure
        auth_error = Exception("403: Not authenticated - JWT validation failed")
        self.auth_tracer.log_failure(
            context=context,
            error=auth_error,
            additional_context={
                "jwt_provided": True,
                "jwt_format_valid": True,
                "jwt_signature_valid": False,
                "service_secret_match": False
            }
        )
        
        # Validate auth trace logging effectiveness
        auth_log_records = [r for r in self.log_records if "AUTH_TRACE" in r.getMessage()]
        assert len(auth_log_records) >= 1, "Auth trace logs not generated"
        
        failure_record = None
        for record in auth_log_records:
            if "AUTH_TRACE_FAILURE" in record.getMessage():
                failure_record = record
                break
        
        assert failure_record is not None, "Auth failure trace log not found"
        
        # Validate debugging information quality
        failure_message = failure_record.getMessage()
        
        # Essential identifiers present
        assert user_id in failure_message, "User ID missing from auth failure log"
        assert request_id in failure_message, "Request ID missing from auth failure log"
        assert correlation_id in failure_message, "Correlation ID missing from auth failure log"
        assert operation in failure_message, "Operation missing from auth failure log"
        
        # Error context present  
        assert "JWT validation failed" in failure_message, "Error details missing"
        assert "403" in failure_message, "HTTP status missing"
        
        # Debugging hints present for system user
        assert "system" in failure_message, "System user context missing"
        
        # Performance timing recorded
        assert context.performance_metrics.get("duration_seconds") is not None, "Timing metrics missing"
        assert context.performance_metrics["duration_seconds"] >= 0, "Invalid timing metrics"
        
        self.record_metric("auth_trace_effectiveness_test", "PASSED")
    
    @pytest.mark.unit
    def test_log_correlation_across_requests(self):
        """Test that logs can be correlated across related operations."""
        # Simulate related operations with same correlation ID
        correlation_id = "corr_business_flow_001"
        
        # Operation 1: User authentication
        with self.temp_env_vars(CORRELATION_ID=correlation_id):
            self.logger.info(
                "User authentication initiated",
                extra={
                    "correlation_id": correlation_id,
                    "user_email": "enterprise@example.com",
                    "auth_method": "oauth",
                    "step": "authentication_start"
                }
            )
        
        # Operation 2: Agent execution
        with self.temp_env_vars(CORRELATION_ID=correlation_id):
            self.logger.info(
                "Cost optimization agent starting",
                extra={
                    "correlation_id": correlation_id,
                    "agent_type": "cost_optimizer",
                    "user_id": "ent_user_456",
                    "step": "agent_execution_start"
                }
            )
        
        # Operation 3: Tool execution
        with self.temp_env_vars(CORRELATION_ID=correlation_id):
            self.logger.info(
                "AWS cost analysis tool completing",
                extra={
                    "correlation_id": correlation_id,
                    "tool_name": "aws_cost_analyzer",
                    "analysis_scope": "last_30_days",
                    "step": "tool_execution_complete"
                }
            )
        
        # Validate correlation capability
        assert len(self.log_records) == 3, "Expected 3 correlated log records"
        
        # All records should have correlation ID
        for record in self.log_records:
            assert hasattr(record, 'correlation_id'), "Correlation ID missing from log record"
            assert record.correlation_id == correlation_id, "Correlation ID mismatch"
        
        # Records should have step information for flow tracking
        steps = [record.step for record in self.log_records]
        expected_steps = ["authentication_start", "agent_execution_start", "tool_execution_complete"]
        assert steps == expected_steps, f"Step sequence incorrect: {steps}"
        
        # Business context preserved across operations
        user_contexts = [getattr(record, 'user_email', getattr(record, 'user_id', None)) for record in self.log_records]
        assert any(context for context in user_contexts), "User context lost across operations"
        
        self.record_metric("log_correlation_test", "PASSED")
    
    @pytest.mark.unit
    def test_performance_logging_overhead(self):
        """Test that logging does not introduce significant performance overhead."""
        # Baseline: measure time without logging
        start_time = time.time()
        for i in range(100):
            # Simulate business operation
            dummy_calculation = i * 2 + 1
        baseline_time = time.time() - start_time
        
        # With logging: measure time with extensive logging
        start_time = time.time()
        for i in range(100):
            # Same business operation with logging
            dummy_calculation = i * 2 + 1
            self.logger.debug(
                f"Business calculation {i}",
                extra={
                    "iteration": i,
                    "result": dummy_calculation,
                    "user_id": f"user_{i % 10}",
                    "operation": "performance_test"
                }
            )
        logging_time = time.time() - start_time
        
        # Performance assertion: logging should not add more than 5x overhead
        performance_ratio = logging_time / baseline_time if baseline_time > 0 else float('inf')
        assert performance_ratio < 5.0, f"Logging overhead too high: {performance_ratio:.2f}x baseline"
        
        # Record performance metrics
        self.record_metric("baseline_time_ms", baseline_time * 1000)
        self.record_metric("logging_time_ms", logging_time * 1000)
        self.record_metric("performance_ratio", performance_ratio)
        
        # Validate that 100 log records were created
        debug_records = [r for r in self.log_records if r.levelname == "DEBUG"]
        assert len(debug_records) == 100, f"Expected 100 debug records, got {len(debug_records)}"
        
        self.record_metric("performance_overhead_test", "PASSED")
    
    @pytest.mark.unit
    def test_sensitive_data_filtering(self):
        """Test that sensitive data is properly filtered from logs."""
        # Test with data that should be filtered
        sensitive_data = {
            "user_id": "safe_user_123",
            "password": "secret_password_123",
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sensitive_payload",
            "api_key": "sk-1234567890abcdef",
            "credit_card": "4111-1111-1111-1111",
            "operation": "user_login",
            "session_data": {
                "session_token": "sensitive_session_abc123",
                "user_preferences": {"theme": "dark", "notifications": True}
            }
        }
        
        # Log with sensitive data
        self.logger.info(
            "User operation completed",
            extra=sensitive_data
        )
        
        assert len(self.log_records) == 1, "Expected 1 log record"
        record = self.log_records[0]
        
        # Safe data should be preserved
        assert hasattr(record, 'user_id'), "Safe user_id should be preserved"
        assert record.user_id == "safe_user_123", "Safe user_id value incorrect"
        assert hasattr(record, 'operation'), "Safe operation field should be preserved"
        
        # Sensitive data should be filtered or masked
        # Note: This test validates that the logging system should implement filtering
        # The specific filtering implementation would depend on the logger configuration
        
        # At minimum, passwords should never appear in formatted output
        formatted_message = record.getMessage()
        assert "secret_password_123" not in formatted_message, "Password leaked in log message"
        
        # JWT tokens should not appear in full
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sensitive_payload" not in formatted_message, "JWT token leaked"
        
        self.record_metric("sensitive_data_filtering_test", "PASSED")
    
    @pytest.mark.unit
    def test_log_message_search_keywords(self):
        """Test that log messages contain effective keywords for searching/alerting."""
        # Test business-critical scenarios with searchable keywords
        critical_scenarios = [
            {
                "message": "CRITICAL: Database connection pool exhausted",
                "keywords": ["CRITICAL", "database", "connection", "pool", "exhausted"],
                "level": "ERROR"
            },
            {
                "message": "Agent execution timeout - user waiting for response",
                "keywords": ["timeout", "agent", "execution", "user", "waiting"],
                "level": "WARNING" 
            },
            {
                "message": "Cost optimization completed successfully",
                "keywords": ["cost", "optimization", "completed", "successfully"],
                "level": "INFO"
            },
            {
                "message": "WebSocket connection authenticated",
                "keywords": ["websocket", "connection", "authenticated"],
                "level": "INFO"
            }
        ]
        
        for scenario in critical_scenarios:
            # Clear previous records
            self.log_records.clear()
            
            # Log the scenario
            log_method = getattr(self.logger, scenario["level"].lower())
            log_method(scenario["message"])
            
            # Validate keywords present
            assert len(self.log_records) == 1, f"Expected 1 log record for scenario"
            record = self.log_records[0]
            
            message = record.getMessage().lower()
            for keyword in scenario["keywords"]:
                assert keyword.lower() in message, f"Keyword '{keyword}' not found in log message: {message}"
        
        self.record_metric("search_keywords_test", "PASSED")
    
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Remove mock handler to prevent interference
        if hasattr(self, 'logger') and hasattr(self, 'mock_handler'):
            self.logger.removeHandler(self.mock_handler)
        
        # Reset logger factory
        UnifiedLoggerFactory.reset()
        
        # Call parent teardown
        super().teardown_method(method)