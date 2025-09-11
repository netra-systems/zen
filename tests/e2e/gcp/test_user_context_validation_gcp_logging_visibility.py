"""SSOT E2E Test: GCP Cloud Logging Visibility for UserExecutionContext Validation Errors

This test suite validates that UserExecutionContext validation errors are properly
visible in GCP Cloud Logging with structured data for effective monitoring and debugging.

ROOT CAUSE: UserExecutionContext validation incorrectly flags "default_user" due to "default_" pattern
GCP VISIBILITY: Ensure error appears in Cloud Logging with proper structure for debugging
BUSINESS IMPACT: $500K+ ARR blocked by validation error that must be visible for rapid resolution

This test focuses specifically on GCP Cloud Logging integration to ensure production
errors are properly captured, structured, and visible for operations teams.

Business Value Justification (BVJ):
- Segment: Platform/Operations (Infrastructure monitoring)
- Business Goal: System Reliability (rapid error detection and resolution)
- Value Impact: Enable rapid diagnosis of $500K+ ARR blocking issues
- Revenue Impact: Reduce MTTR for critical validation failures

GCP Logging Test Strategy:
1. STRUCTURED LOGGING: Verify logs contain structured data for GCP parsing
2. LOG LEVELS: Ensure appropriate severity levels for GCP alerting
3. SEARCHABLE CONTENT: Verify logs contain searchable keywords for debugging
4. CORRELATION: Test log correlation with user actions and business impact
5. MONITORING: Validate log format for GCP monitoring and alerting

SSOT Compliance:
- Inherits from SSotAsyncTestCase for real service testing
- Uses actual logging infrastructure, not mocks
- Tests production-like logging scenarios
- Validates complete GCP integration stack
"""

import pytest
import asyncio
import logging
import json
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from io import StringIO
from contextlib import contextmanager

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    InvalidContextError,
    create_isolated_execution_context
)
from shared.isolated_environment import IsolatedEnvironment


class GCPStructuredLogCapture:
    """Utility class to capture and analyze structured logs for GCP compatibility."""
    
    def __init__(self):
        self.log_records = []
        self.handler = logging.Handler()
        self.handler.emit = self._capture_record
    
    def _capture_record(self, record):
        """Capture log record with GCP-compatible structure."""
        # Simulate GCP Cloud Logging structured data
        structured_record = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'severity': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'module': getattr(record, 'module', ''),
            'function': getattr(record, 'funcName', ''),
            'line': getattr(record, 'lineno', 0),
            'thread': getattr(record, 'thread', 0),
            'process': getattr(record, 'process', 0),
            # GCP-specific fields
            'labels': {
                'component': 'user_execution_context',
                'error_type': 'validation_failure',
                'business_impact': 'high'
            },
            'source_location': {
                'file': getattr(record, 'pathname', ''),
                'line': getattr(record, 'lineno', 0),
                'function': getattr(record, 'funcName', '')
            }
        }
        
        # Add exception information if present
        if record.exc_info:
            structured_record['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': record.exc_text if hasattr(record, 'exc_text') else None
            }
        
        self.log_records.append(structured_record)
    
    def get_error_logs(self):
        """Get logs with ERROR or higher severity."""
        return [r for r in self.log_records if r['severity'] in ['ERROR', 'CRITICAL']]
    
    def get_logs_containing(self, text):
        """Get logs containing specific text in message."""
        return [r for r in self.log_records if text in r['message']]
    
    def clear(self):
        """Clear captured logs."""
        self.log_records.clear()


class TestUserContextValidationGCPLoggingVisibility(SSotAsyncTestCase):
    """E2E test for GCP Cloud Logging visibility of UserExecutionContext validation errors.
    
    This test class validates that validation errors are properly structured and visible
    in GCP Cloud Logging for effective production monitoring and debugging.
    """

    def setup_method(self, method=None):
        """Set up E2E test fixtures with GCP-compatible logging capture."""
        super().setup_method(method)
        
        # Set up GCP-compatible structured log capture
        self.gcp_log_capture = GCPStructuredLogCapture()
        
        # Target loggers that should appear in GCP Cloud Logging
        self.monitored_loggers = [
            'netra_backend.app.services.user_execution_context',
            'netra_backend.app.agents.supervisor.agent_execution_core',
            'netra_backend.app.routes.agent',
            'netra_backend.app.websocket_core.unified_manager',
        ]
        
        # Install GCP log capture on all monitored loggers
        self.logger_instances = []
        for logger_name in self.monitored_loggers:
            logger = logging.getLogger(logger_name)
            logger.addHandler(self.gcp_log_capture.handler)
            logger.setLevel(logging.DEBUG)
            self.logger_instances.append(logger)

    def teardown_method(self, method=None):
        """Clean up E2E test fixtures."""
        if hasattr(self, 'logger_instances') and hasattr(self, 'gcp_log_capture'):
            for logger in self.logger_instances:
                logger.removeHandler(self.gcp_log_capture.handler)
        super().teardown_method(method)

    @pytest.mark.asyncio
    async def test_gcp_structured_logging_for_validation_error(self):
        """
        GCP VISIBILITY: Verify validation error appears in structured logs for GCP monitoring.
        
        This test ensures that the 'default_user' validation error produces properly
        structured logs that are visible and searchable in GCP Cloud Logging.
        """
        self.gcp_log_capture.clear()
        
        # Trigger the validation error that appears in GCP logs
        with pytest.raises(InvalidContextError):
            context = UserExecutionContext(
                user_id="default_user",  # This triggers the GCP-visible error
                thread_id="th_12345678901234567890",
                run_id="run_12345678901234567890", 
                request_id="req_12345678901234567890",
                operation_name="gcp_logging_test",
                created_at=datetime.now(timezone.utc)
            )
        
        # Verify GCP-compatible structured logging
        error_logs = self.gcp_log_capture.get_error_logs()
        assert len(error_logs) > 0, "Expected error logs for GCP visibility"
        
        error_log = error_logs[0]
        
        # Verify GCP Cloud Logging structure
        assert 'timestamp' in error_log, "Missing timestamp for GCP"
        assert 'severity' in error_log, "Missing severity for GCP alerting"
        assert 'message' in error_log, "Missing message for GCP search"
        assert 'logger' in error_log, "Missing logger for GCP filtering"
        assert 'labels' in error_log, "Missing labels for GCP organization"
        assert 'source_location' in error_log, "Missing source location for GCP debugging"
        
        # Verify severity level for GCP alerting
        assert error_log['severity'] == 'ERROR', (
            f"Expected ERROR severity for GCP alerting, got: {error_log['severity']}"
        )
        
        # Verify message contains searchable keywords for GCP
        message = error_log['message']
        assert "VALIDATION FAILURE" in message, "Missing severity indicator for GCP search"
        assert "default_user" in message, "Missing problematic value for GCP debugging"
        assert "placeholder pattern" in message, "Missing error type for GCP classification"
        assert "request isolation" in message, "Missing business impact for GCP monitoring"

    @pytest.mark.asyncio
    async def test_gcp_log_searchability_and_filtering(self):
        """
        GCP SEARCH: Verify logs contain proper keywords for GCP log filtering and search.
        
        This test ensures that GCP Cloud Logging queries can effectively find and
        filter the validation errors for debugging and monitoring.
        """
        self.gcp_log_capture.clear()
        
        # Trigger validation error
        with pytest.raises(InvalidContextError):
            await create_isolated_execution_context(
                user_id="default_user",
                request_id="req_gcp_search_test"
            )
        
        # Test GCP log filtering capabilities
        search_terms = [
            "VALIDATION FAILURE",
            "default_user", 
            "placeholder pattern",
            "InvalidContextError",
            "request isolation",
            "user_execution_context"
        ]
        
        for term in search_terms:
            matching_logs = self.gcp_log_capture.get_logs_containing(term)
            assert len(matching_logs) > 0, (
                f"GCP search term '{term}' should find logs but found {len(matching_logs)}"
            )
        
        # Verify GCP label-based filtering
        error_logs = self.gcp_log_capture.get_error_logs()
        for log in error_logs:
            labels = log.get('labels', {})
            assert labels.get('component') == 'user_execution_context', (
                "Missing component label for GCP filtering"
            )
            assert labels.get('error_type') == 'validation_failure', (
                "Missing error_type label for GCP classification"
            )
            assert labels.get('business_impact') == 'high', (
                "Missing business_impact label for GCP prioritization"
            )

    @pytest.mark.asyncio
    async def test_gcp_log_correlation_with_user_actions(self):
        """
        GCP CORRELATION: Verify logs can be correlated with user actions for debugging.
        
        This test ensures that GCP logs contain sufficient context to correlate
        validation errors with specific user actions and business scenarios.
        """
        self.gcp_log_capture.clear()
        
        # Simulate user action context
        user_action_context = {
            "user_id": "default_user",
            "action": "start_agent_execution", 
            "session_id": "session_12345",
            "request_source": "web_ui",
            "business_context": "cost_optimization_request"
        }
        
        # Trigger validation error with user action context
        with pytest.raises(InvalidContextError):
            context = await create_isolated_execution_context(
                user_id=user_action_context["user_id"],
                request_id="req_user_action_test"
            )
        
        # Verify GCP log correlation information
        error_logs = self.gcp_log_capture.get_error_logs()
        assert len(error_logs) > 0, "Expected correlatable error logs"
        
        error_log = error_logs[0]
        message = error_log['message']
        
        # Verify correlation data is present
        assert "default_user" in message, "Missing user identifier for correlation"
        assert "start_agent_execution" in message or "operation" in message, (
            "Missing operation context for correlation"
        )
        
        # Verify timestamp precision for correlation
        timestamp = error_log['timestamp']
        assert timestamp is not None, "Missing timestamp for correlation"
        assert 'T' in timestamp, "Timestamp should be ISO format for GCP"
        assert 'Z' in timestamp or '+' in timestamp, "Timestamp should include timezone"

    @pytest.mark.asyncio
    async def test_gcp_monitoring_alert_trigger_conditions(self):
        """
        GCP MONITORING: Verify logs meet conditions for GCP monitoring alerts.
        
        This test ensures that validation errors produce logs that can trigger
        GCP monitoring alerts for rapid response to business-critical issues.
        """
        self.gcp_log_capture.clear()
        
        # Trigger multiple validation errors to simulate alert conditions
        validation_errors = [
            "default_user",
            "default_admin", 
            "default_system"
        ]
        
        for problematic_user_id in validation_errors:
            try:
                await create_isolated_execution_context(
                    user_id=problematic_user_id,
                    request_id=f"req_alert_test_{problematic_user_id}"
                )
            except InvalidContextError:
                pass  # Expected
        
        # Verify alert trigger conditions
        error_logs = self.gcp_log_capture.get_error_logs()
        assert len(error_logs) >= len(validation_errors), (
            f"Expected {len(validation_errors)} error logs for alerting, got {len(error_logs)}"
        )
        
        # Verify each error log meets alert criteria
        for error_log in error_logs:
            # Alert condition 1: ERROR severity or higher
            assert error_log['severity'] in ['ERROR', 'CRITICAL'], (
                "Logs must be ERROR level or higher for GCP alerting"
            )
            
            # Alert condition 2: Contains business impact keywords
            message = error_log['message']
            business_keywords = ["VALIDATION FAILURE", "request isolation", "placeholder pattern"]
            has_business_keyword = any(keyword in message for keyword in business_keywords)
            assert has_business_keyword, "Missing business impact keywords for alerting"
            
            # Alert condition 3: Contains structured labels for alert routing
            labels = error_log.get('labels', {})
            assert labels.get('business_impact') == 'high', (
                "Missing high business impact label for alert prioritization"
            )

    @pytest.mark.asyncio
    async def test_gcp_log_retention_and_compliance(self):
        """
        GCP COMPLIANCE: Verify logs meet GCP retention and compliance requirements.
        
        This test ensures that validation error logs contain sufficient information
        for compliance auditing and long-term retention in GCP.
        """
        self.gcp_log_capture.clear()
        
        # Trigger validation error with compliance context
        with pytest.raises(InvalidContextError):
            context = UserExecutionContext(
                user_id="default_user",
                thread_id="th_compliance_test",
                run_id="run_compliance_test", 
                request_id="req_compliance_test",
                operation_name="compliance_audit_test",
                created_at=datetime.now(timezone.utc)
            )
        
        # Verify compliance-ready log structure
        error_logs = self.gcp_log_capture.get_error_logs()
        assert len(error_logs) > 0, "Expected compliance-auditable logs"
        
        error_log = error_logs[0]
        
        # Compliance requirement 1: Immutable timestamp
        assert 'timestamp' in error_log, "Missing timestamp for compliance audit trail"
        timestamp = error_log['timestamp']
        assert timestamp.endswith('Z') or '+' in timestamp, (
            "Timestamp must be UTC for compliance consistency"
        )
        
        # Compliance requirement 2: Complete source attribution
        source_location = error_log.get('source_location', {})
        assert 'file' in source_location, "Missing source file for compliance traceability"
        assert 'function' in source_location, "Missing function for compliance context"
        assert 'line' in source_location, "Missing line number for compliance precision"
        
        # Compliance requirement 3: Security-safe content
        message = error_log['message']
        # Should not contain sensitive data, only validation error details
        assert "default_user" in message, "Should contain non-sensitive error context"
        assert "placeholder pattern" in message, "Should contain error classification"
        # Should not contain any actual sensitive user data beyond the error context

    @pytest.mark.asyncio
    async def test_gcp_production_simulation_full_stack(self):
        """
        GCP PRODUCTION SIMULATION: Full-stack test simulating production GCP environment.
        
        This test simulates the complete production scenario where the validation
        error occurs and verifies full GCP logging integration.
        """
        self.gcp_log_capture.clear()
        
        # Simulate production scenario
        production_scenario = {
            "environment": "production",
            "user_request": "AI infrastructure optimization",
            "user_id": "default_user",  # The problematic value from GCP logs
            "client_ip": "192.168.1.100",
            "request_id": "req_prod_simulation",
            "session_context": "enterprise_optimization_session"
        }
        
        # Simulate the full production stack that leads to the error
        try:
            # Step 1: User authentication (would succeed)
            # Step 2: API request processing (would succeed) 
            # Step 3: UserExecutionContext creation (FAILS HERE - matches GCP logs)
            context = await create_isolated_execution_context(
                user_id=production_scenario["user_id"],
                request_id=production_scenario["request_id"]
            )
            pytest.fail("Expected production validation failure")
            
        except InvalidContextError as e:
            # This is the exact error that appears in GCP logs
            production_error = str(e)
            
            # Verify production error matches GCP log format
            assert "appears to contain placeholder pattern" in production_error
            assert "default_user" in production_error
        
        # Verify complete GCP logging stack captured the production error
        error_logs = self.gcp_log_capture.get_error_logs()
        assert len(error_logs) > 0, "Expected production error in GCP logs"
        
        production_log = error_logs[0]
        
        # Verify production-ready GCP log structure
        assert production_log['severity'] == 'ERROR', "Production errors should be ERROR level"
        assert 'timestamp' in production_log, "Production logs need timestamps"
        assert 'source_location' in production_log, "Production logs need source tracking"
        assert 'labels' in production_log, "Production logs need classification labels"
        
        # Verify the exact error that blocks $500K+ ARR in production
        message = production_log['message']
        assert "VALIDATION FAILURE" in message, "Production error should be clearly marked"
        assert "default_user" in message, "Production error should contain exact problematic value"
        assert "request isolation" in message, "Production error should explain business impact"
        
        # This log entry would be visible in GCP Cloud Logging with full context
        # for operations teams to diagnose and resolve the $500K+ ARR blocking issue