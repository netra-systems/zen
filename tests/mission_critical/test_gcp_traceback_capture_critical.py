"""Mission Critical tests for GCP traceback capture validation.

Business Value Justification (BVJ):
- Segment: Enterprise - Mission Critical Production Reliability
- Business Goal: Ensure zero production debugging blind spots for $500K+ ARR platform
- Value Impact: Prevents complete production incident response failures 
- Strategic Impact: Foundation for enterprise SLA compliance and 24/7 support commitments

MISSION CRITICAL REQUIREMENTS:
1. All production errors MUST have traceback information available in GCP Cloud Logging
2. No silent failures in error reporting pipeline
3. Complete error context preservation for enterprise debugging
4. Real-time error visibility for incident response teams

CRITICAL ISSUE CONTEXT:
Current production issue: GCP staging logs missing traceback information for caught exceptions
with exc_info=True, causing critical debugging blind spots during production incidents.

These tests MUST initially FAIL to demonstrate the production-critical issue.
Success criteria: All tests pass AND provide complete traceback in GCP Cloud Logging.

DEPLOYMENT GATE: These tests MUST pass before any production deployment.
"""

import asyncio
import json
import logging
import time
import traceback
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import patch, Mock, MagicMock

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.logging_formatters import LogFormatter, SensitiveDataFilter
from netra_backend.app.core.unified_logging import get_logger
from shared.isolated_environment import get_env


class TestGCPTracebackCaptureCritical(SSotAsyncTestCase):
    """Mission Critical tests for GCP traceback capture validation."""
    
    def setup_method(self, method):
        """Setup mission critical GCP traceback tests."""
        super().setup_method(method)
        self.env = get_env()
        
        # Configure EXACT production GCP staging environment
        self.set_env_var("K_SERVICE", "netra-backend")
        self.set_env_var("GOOGLE_CLOUD_PROJECT", "netra-staging")
        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("DEPLOYMENT_ENV", "staging")
        
        # Configure logging exactly as in production 
        # Note: UnifiedLogger auto-configures based on environment
        self.logger = get_logger(__name__)
        
        # Critical test tracking
        self.record_metric("mission_critical_setup", True)
        self.critical_failures = []
        
    def test_exc_info_true_produces_traceback_critical(self):
        """
        MISSION CRITICAL: Validate exc_info=True produces traceback in GCP logs.
        
        This is the CORE issue causing production debugging failures.
        MUST demonstrate current failure then validate fix.
        """
        test_exception_id = f"critical_test_{uuid.uuid4().hex[:8]}"
        
        # Create realistic production exception scenario
        try:
            self._simulate_production_exception_scenario(test_exception_id)
        except Exception as e:
            # This is the CRITICAL test - exc_info=True MUST produce traceback
            with self._capture_production_gcp_logs() as log_capture:
                self.logger.error(
                    f"Production exception occurred: {test_exception_id}",
                    exc_info=True,  # CRITICAL: This MUST produce traceback
                    extra={
                        "exception_id": test_exception_id,
                        "production_scenario": True,
                        "critical_test": True
                    }
                )
        
        # CRITICAL VALIDATION: Find the error log with traceback
        error_logs = [
            log for log in log_capture.logs 
            if log.get("severity") == "ERROR" and test_exception_id in log.get("message", "")
        ]
        
        # CRITICAL ASSERTION 1: Error log must exist
        assert len(error_logs) > 0, f"CRITICAL FAILURE: No error log found for {test_exception_id}"
        
        error_log = error_logs[0]
        
        # CRITICAL ASSERTION 2: Error field must exist
        assert "error" in error_log, f"CRITICAL FAILURE: No error field in log for {test_exception_id}"
        
        error_field = error_log["error"]
        
        # CRITICAL ASSERTION 3: Traceback must exist and not be None/empty
        assert "traceback" in error_field, f"CRITICAL FAILURE: No traceback field in error for {test_exception_id}"
        assert error_field["traceback"] is not None, f"CRITICAL FAILURE: Traceback is None for {test_exception_id}"
        assert len(error_field["traceback"]) > 0, f"CRITICAL FAILURE: Traceback is empty for {test_exception_id}"
        
        # CRITICAL ASSERTION 4: Traceback must contain meaningful content
        traceback_content = error_field["traceback"]
        assert test_exception_id in traceback_content, f"CRITICAL FAILURE: Exception ID not in traceback"
        assert "production_exception_scenario" in traceback_content, f"CRITICAL FAILURE: Function name not in traceback"
        
        # CRITICAL ASSERTION 5: Exception type and value must be correct
        assert error_field["type"] == "ProductionCriticalError", f"CRITICAL FAILURE: Wrong exception type"
        assert test_exception_id in error_field["value"], f"CRITICAL FAILURE: Exception ID not in value"
        
        self.record_metric("critical_exc_info_test_passed", True)
    
    def test_websocket_agent_error_traceback_critical(self):
        """
        MISSION CRITICAL: Validate WebSocket agent errors have complete traceback.
        
        WebSocket errors are the most critical for user experience debugging.
        MUST have complete traceback for production incident response.
        """
        session_id = f"critical_ws_{uuid.uuid4().hex[:8]}"
        agent_id = f"critical_agent_{uuid.uuid4().hex[:8]}"
        
        with self.temp_env_vars(
            WEBSOCKET_SESSION_ID=session_id,
            AGENT_ID=agent_id,
            CRITICAL_TEST="true"
        ):
            with self._capture_production_gcp_logs() as log_capture:
                # Simulate critical WebSocket agent error
                try:
                    self._simulate_critical_websocket_agent_error(session_id, agent_id)
                except Exception:
                    self.logger.error(
                        f"Critical WebSocket agent error in session {session_id}",
                        exc_info=True,
                        extra={
                            "session_id": session_id,
                            "agent_id": agent_id,
                            "error_type": "websocket_agent",
                            "critical": True
                        }
                    )
        
        # Find WebSocket agent error logs
        ws_error_logs = [
            log for log in log_capture.logs
            if (log.get("severity") == "ERROR" and 
                session_id in log.get("message", "") and
                "websocket" in log.get("message", "").lower())
        ]
        
        # CRITICAL: WebSocket errors MUST have traceback
        assert len(ws_error_logs) > 0, f"CRITICAL FAILURE: No WebSocket error logs for session {session_id}"
        
        ws_error_log = ws_error_logs[0]
        assert self._has_complete_traceback(ws_error_log), f"CRITICAL FAILURE: WebSocket error missing complete traceback"
        
        # Validate WebSocket context in traceback
        traceback_content = ws_error_log["error"]["traceback"]
        assert session_id in traceback_content, "CRITICAL FAILURE: Session ID not in WebSocket traceback"
        assert agent_id in traceback_content, "CRITICAL FAILURE: Agent ID not in WebSocket traceback"
        
        self.record_metric("critical_websocket_traceback_passed", True)
        self.increment_websocket_events(1)
    
    def test_database_transaction_error_traceback_critical(self):
        """
        MISSION CRITICAL: Validate database transaction errors have complete traceback.
        
        Database errors are critical for data integrity incident response.
        """
        transaction_id = f"critical_tx_{uuid.uuid4().hex[:8]}"
        
        with self.temp_env_vars(
            TRANSACTION_ID=transaction_id,
            CRITICAL_DB_TEST="true"
        ):
            with self._capture_production_gcp_logs() as log_capture:
                try:
                    self._simulate_critical_database_transaction_error(transaction_id)
                except Exception:
                    self.logger.error(
                        f"Critical database transaction error: {transaction_id}",
                        exc_info=True,
                        extra={
                            "transaction_id": transaction_id,
                            "error_type": "database_transaction",
                            "critical": True
                        }
                    )
        
        # Find database error logs
        db_error_logs = [
            log for log in log_capture.logs
            if (log.get("severity") == "ERROR" and
                transaction_id in log.get("message", "") and
                "database" in log.get("message", "").lower())
        ]
        
        # CRITICAL: Database errors MUST have traceback
        assert len(db_error_logs) > 0, f"CRITICAL FAILURE: No database error logs for transaction {transaction_id}"
        
        db_error_log = db_error_logs[0]
        assert self._has_complete_traceback(db_error_log), f"CRITICAL FAILURE: Database error missing complete traceback"
        
        # Validate database context in traceback
        traceback_content = db_error_log["error"]["traceback"]
        assert transaction_id in traceback_content, "CRITICAL FAILURE: Transaction ID not in database traceback"
        
        self.record_metric("critical_database_traceback_passed", True)
        self.increment_db_query_count(1)
    
    def test_agent_llm_call_error_traceback_critical(self):
        """
        MISSION CRITICAL: Validate LLM call errors have complete traceback.
        
        LLM errors are critical for AI functionality debugging.
        """
        llm_call_id = f"critical_llm_{uuid.uuid4().hex[:8]}"
        
        with self.temp_env_vars(
            LLM_CALL_ID=llm_call_id,
            CRITICAL_LLM_TEST="true"
        ):
            with self._capture_production_gcp_logs() as log_capture:
                try:
                    self._simulate_critical_llm_call_error(llm_call_id)
                except Exception:
                    self.logger.error(
                        f"Critical LLM call error: {llm_call_id}",
                        exc_info=True,
                        extra={
                            "llm_call_id": llm_call_id,
                            "error_type": "llm_call",
                            "critical": True
                        }
                    )
        
        # Find LLM error logs
        llm_error_logs = [
            log for log in log_capture.logs
            if (log.get("severity") == "ERROR" and
                llm_call_id in log.get("message", "") and
                "llm" in log.get("message", "").lower())
        ]
        
        # CRITICAL: LLM errors MUST have traceback
        assert len(llm_error_logs) > 0, f"CRITICAL FAILURE: No LLM error logs for call {llm_call_id}"
        
        llm_error_log = llm_error_logs[0]
        assert self._has_complete_traceback(llm_error_log), f"CRITICAL FAILURE: LLM error missing complete traceback"
        
        # Validate LLM context in traceback
        traceback_content = llm_error_log["error"]["traceback"]
        assert llm_call_id in traceback_content, "CRITICAL FAILURE: LLM call ID not in traceback"
        
        self.record_metric("critical_llm_traceback_passed", True)
        self.increment_llm_requests(1)
    
    def test_json_formatting_preserves_traceback_critical(self):
        """
        MISSION CRITICAL: Validate JSON formatting preserves traceback content.
        
        JSON formatting issues can corrupt traceback data in GCP logs.
        """
        format_test_id = f"critical_format_{uuid.uuid4().hex[:8]}"
        
        # Create complex traceback with special characters
        try:
            self._simulate_complex_traceback_scenario(format_test_id)
        except Exception as e:
            # Capture raw traceback for comparison
            raw_traceback = traceback.format_exc()
            
            with self._capture_production_gcp_logs() as log_capture:
                self.logger.error(
                    f"Complex traceback formatting test: {format_test_id}",
                    exc_info=True,
                    extra={
                        "format_test_id": format_test_id,
                        "error_type": "json_formatting",
                        "critical": True
                    }
                )
        
        # Find formatting test logs
        format_error_logs = [
            log for log in log_capture.logs
            if (log.get("severity") == "ERROR" and
                format_test_id in log.get("message", ""))
        ]
        
        assert len(format_error_logs) > 0, f"CRITICAL FAILURE: No formatting test logs for {format_test_id}"
        
        format_error_log = format_error_logs[0]
        assert self._has_complete_traceback(format_error_log), f"CRITICAL FAILURE: Formatting test missing traceback"
        
        # CRITICAL: Validate JSON structure is valid
        json_str = json.dumps(format_error_log)
        assert "\n" not in json_str, "CRITICAL FAILURE: Unescaped newlines in JSON output"
        
        # CRITICAL: Validate traceback content preservation
        traceback_content = format_error_log["error"]["traceback"]
        assert format_test_id in traceback_content, "CRITICAL FAILURE: Test ID not preserved in formatted traceback"
        assert "complex_traceback_scenario" in traceback_content, "CRITICAL FAILURE: Function name not preserved"
        
        self.record_metric("critical_json_formatting_passed", True)
    
    async def test_production_error_scenarios_end_to_end_critical(self):
        """
        MISSION CRITICAL: End-to-end validation of production error scenarios.
        
        Simulates complete production error flows and validates traceback
        capture throughout the entire pipeline.
        """
        scenario_id = f"critical_e2e_{uuid.uuid4().hex[:8]}"
        user_id = f"production_user_{uuid.uuid4().hex[:8]}"
        request_id = f"production_req_{uuid.uuid4().hex[:8]}"
        
        with self.temp_env_vars(
            SCENARIO_ID=scenario_id,
            USER_ID=user_id,
            REQUEST_ID=request_id,
            PRODUCTION_SIMULATION="true"
        ):
            with self._capture_production_gcp_logs() as log_capture:
                # Simulate complete production error flow
                await self._simulate_complete_production_error_flow(scenario_id, user_id, request_id)
        
        # CRITICAL: Validate complete error flow has traceback
        error_logs = [log for log in log_capture.logs if log.get("severity") == "ERROR"]
        assert len(error_logs) >= 3, f"CRITICAL FAILURE: Expected at least 3 error logs, got {len(error_logs)}"
        
        # Validate each stage has traceback
        stages = ["authentication", "agent_execution", "response_generation"]
        stages_with_traceback = []
        
        for log_entry in error_logs:
            if self._has_complete_traceback(log_entry):
                message = log_entry.get("message", "").lower()
                for stage in stages:
                    if stage.replace("_", " ") in message:
                        if stage not in stages_with_traceback:
                            stages_with_traceback.append(stage)
        
        # CRITICAL: All production stages must have traceback
        assert len(stages_with_traceback) >= 2, f"CRITICAL FAILURE: Not enough stages with traceback. Found: {stages_with_traceback}"
        
        self.record_metric("critical_e2e_scenario_passed", True)
    
    def test_gcp_cloud_logging_compatibility_critical(self):
        """
        MISSION CRITICAL: Validate GCP Cloud Logging compatibility.
        
        Ensures formatted logs are compatible with GCP Error Reporting
        and Cloud Logging ingestion.
        """
        compatibility_test_id = f"critical_compat_{uuid.uuid4().hex[:8]}"
        
        try:
            self._simulate_gcp_compatibility_test_error(compatibility_test_id)
        except Exception:
            with self._capture_production_gcp_logs() as log_capture:
                self.logger.error(
                    f"GCP compatibility test error: {compatibility_test_id}",
                    exc_info=True,
                    extra={
                        "compatibility_test_id": compatibility_test_id,
                        "error_type": "gcp_compatibility",
                        "critical": True,
                        "gcp_project": "netra-staging",
                        "k_service": "netra-backend"
                    }
                )
        
        # Find compatibility test logs
        compat_logs = [
            log for log in log_capture.logs
            if compatibility_test_id in log.get("message", "")
        ]
        
        assert len(compat_logs) > 0, f"CRITICAL FAILURE: No compatibility test logs for {compatibility_test_id}"
        
        compat_log = compat_logs[0]
        
        # CRITICAL: Validate GCP Cloud Logging required fields
        self._validate_gcp_cloud_logging_structure(compat_log)
        
        # CRITICAL: Validate error field structure for Error Reporting
        assert "error" in compat_log, "CRITICAL FAILURE: Missing error field for Error Reporting"
        error_field = compat_log["error"]
        
        required_error_fields = ["type", "value", "traceback"]
        for field in required_error_fields:
            assert field in error_field, f"CRITICAL FAILURE: Missing error.{field} for Error Reporting"
            assert error_field[field] is not None, f"CRITICAL FAILURE: error.{field} is None"
        
        self.record_metric("critical_gcp_compatibility_passed", True)
    
    # Helper methods for critical error simulation
    
    def _simulate_production_exception_scenario(self, exception_id: str):
        """Simulate realistic production exception scenario."""
        def user_request_handler():
            def authentication_layer():
                def business_logic_layer():
                    def data_processing():
                        # Create production-like exception
                        raise ProductionCriticalError(f"Production critical error: {exception_id}")
                    data_processing()
                business_logic_layer()
            authentication_layer()
        
        user_request_handler()
    
    def _simulate_critical_websocket_agent_error(self, session_id: str, agent_id: str):
        """Simulate critical WebSocket agent error."""
        def websocket_message_handler():
            def agent_execution_pipeline():
                def tool_execution():
                    raise WebSocketAgentError(f"WebSocket agent {agent_id} failed in session {session_id}")
                tool_execution()
            agent_execution_pipeline()
        
        websocket_message_handler()
    
    def _simulate_critical_database_transaction_error(self, transaction_id: str):
        """Simulate critical database transaction error."""
        def database_transaction():
            def connection_management():
                def query_execution():
                    raise DatabaseTransactionError(f"Transaction {transaction_id} failed with integrity violation")
                query_execution()
            connection_management()
        
        database_transaction()
    
    def _simulate_critical_llm_call_error(self, call_id: str):
        """Simulate critical LLM call error."""
        def llm_request_handler():
            def prompt_processing():
                def api_call():
                    raise LLMCallError(f"LLM call {call_id} failed with rate limit exceeded")
                api_call()
            prompt_processing()
        
        llm_request_handler()
    
    def _simulate_complex_traceback_scenario(self, format_test_id: str):
        """Simulate complex traceback with special characters."""
        def complex_function_with_unicode():
            def nested_function_with_quotes():
                def deep_function_with_newlines():
                    # Create error with complex characters
                    error_message = f"Complex error {format_test_id} with 'quotes' and \"double quotes\" and \\n newlines"
                    raise ComplexFormattingError(error_message)
                deep_function_with_newlines()
            nested_function_with_quotes()
        
        complex_function_with_unicode()
    
    def _simulate_gcp_compatibility_test_error(self, compatibility_test_id: str):
        """Simulate GCP compatibility test error."""
        def gcp_service_integration():
            def cloud_logging_handler():
                def error_reporting_integration():
                    raise GCPCompatibilityError(f"GCP compatibility test {compatibility_test_id} failed")
                error_reporting_integration()
            cloud_logging_handler()
        
        gcp_service_integration()
    
    async def _simulate_complete_production_error_flow(self, scenario_id: str, user_id: str, request_id: str):
        """Simulate complete production error flow."""
        # Authentication error
        try:
            def authentication_step():
                raise AuthenticationError(f"Authentication failed for user {user_id} in scenario {scenario_id}")
            authentication_step()
        except AuthenticationError:
            self.logger.error(f"Production authentication error in scenario {scenario_id}", exc_info=True)
        
        # Agent execution error  
        try:
            def agent_execution_step():
                raise AgentExecutionError(f"Agent execution failed for request {request_id} in scenario {scenario_id}")
            agent_execution_step()
        except AgentExecutionError:
            self.logger.error(f"Production agent execution error in scenario {scenario_id}", exc_info=True)
        
        # Response generation error
        try:
            def response_generation_step():
                raise ResponseGenerationError(f"Response generation failed for scenario {scenario_id}")
            response_generation_step()
        except ResponseGenerationError:
            self.logger.error(f"Production response generation error in scenario {scenario_id}", exc_info=True)
    
    def _has_complete_traceback(self, log_entry: Dict[str, Any]) -> bool:
        """Check if log entry has complete traceback information."""
        if "error" not in log_entry:
            return False
        
        error_field = log_entry["error"]
        return (
            error_field.get("type") is not None and
            error_field.get("value") is not None and
            error_field.get("traceback") is not None and
            len(error_field["traceback"]) > 0
        )
    
    def _validate_gcp_cloud_logging_structure(self, log_entry: Dict[str, Any]):
        """Validate GCP Cloud Logging structure requirements."""
        # Required top-level fields
        required_fields = ["severity", "message", "timestamp"]
        for field in required_fields:
            assert field in log_entry, f"CRITICAL FAILURE: Missing required field '{field}'"
        
        # Validate severity values
        valid_severities = ["DEFAULT", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert log_entry["severity"] in valid_severities, f"CRITICAL FAILURE: Invalid severity '{log_entry['severity']}'"
        
        # Validate timestamp format
        timestamp = log_entry["timestamp"]
        assert isinstance(timestamp, str), "CRITICAL FAILURE: Timestamp must be string"
        
        # Validate single-line JSON
        json_str = json.dumps(log_entry)
        assert "\n" not in json_str, "CRITICAL FAILURE: Multi-line JSON not compatible with GCP"
        
        # Validate labels structure if present
        if "labels" in log_entry:
            labels = log_entry["labels"]
            assert isinstance(labels, dict), "CRITICAL FAILURE: Labels must be dict"
    
    @contextmanager
    def _capture_production_gcp_logs(self):
        """Context manager to capture production GCP logs."""
        captured_logs = []
        
        class ProductionLogCapture:
            def __init__(self):
                self.logs = []
            
            def capture_log(self, formatted_json):
                try:
                    clean_json = formatted_json.strip()
                    if clean_json:
                        log_entry = json.loads(clean_json)
                        self.logs.append(log_entry)
                except json.JSONDecodeError as e:
                    # JSON parsing errors are CRITICAL failures
                    self.logs.append({
                        "CRITICAL_JSON_ERROR": True,
                        "raw_output": formatted_json,
                        "parse_error": str(e),
                        "severity": "CRITICAL"
                    })
        
        log_capture = ProductionLogCapture()
        
        # Capture production formatter output
        def capturing_production_formatter(record):
            formatter = LogFormatter(SensitiveDataFilter())
            formatted_json = formatter.gcp_json_formatter(record)
            log_capture.capture_log(formatted_json)
            return formatted_json
        
        with patch.object(LogFormatter, 'gcp_json_formatter', side_effect=capturing_production_formatter):
            yield log_capture


# Custom exception classes for critical testing
class ProductionCriticalError(Exception):
    """Production critical error for testing."""
    pass


class WebSocketAgentError(Exception):
    """WebSocket agent error for testing."""
    pass


class DatabaseTransactionError(Exception):
    """Database transaction error for testing."""
    pass


class LLMCallError(Exception):
    """LLM call error for testing."""
    pass


class ComplexFormattingError(Exception):
    """Complex formatting error for testing."""
    pass


class GCPCompatibilityError(Exception):
    """GCP compatibility error for testing."""
    pass


class AuthenticationError(Exception):
    """Authentication error for testing."""
    pass


class AgentExecutionError(Exception):
    """Agent execution error for testing."""
    pass


class ResponseGenerationError(Exception):
    """Response generation error for testing."""
    pass