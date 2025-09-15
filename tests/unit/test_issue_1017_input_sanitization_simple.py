"""
Issue #1017 Security Vulnerability Tests: Input Sanitization Simple

CRITICAL SECURITY TEST SUITE: These tests are designed to FAIL initially to prove
security vulnerabilities exist in the agent_input field processing.

REQUIREMENTS:
- Tests MUST FAIL initially to prove vulnerabilities exist
- Uses SSOT test infrastructure from test_framework/
- Real services only - NO MOCKS in vulnerability testing

Business Value: Enterprise/Platform - Security compliance for HIPAA, SOC2, SEC regulations
"""

import json
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.schemas.agent_models import DeepAgentState


class TestIssue1017InputSanitizationSimple(SSotBaseTestCase):
    """
    Simple security vulnerability tests for Issue #1017.

    These tests are designed to FAIL initially to prove that security
    vulnerabilities exist in the agent_input field processing.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        # Create test context for vulnerability testing
        self.test_user_id = f"vuln_test_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"vuln_test_thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"vuln_test_run_{uuid.uuid4().hex[:8]}"

        # Record business value metrics
        self.record_metric("test_category", "security_vulnerability")
        self.record_metric("issue_number", "1017")
        self.record_metric("vulnerability_type", "input_sanitization")

    def test_xss_payload_injection_vulnerability(self):
        """
        Test XSS payload injection in agent_input field.

        EXPECTS TO FAIL: This test should demonstrate XSS vulnerability
        by showing that malicious JavaScript payloads are not properly sanitized.
        """
        self.record_metric("vulnerability_subtype", "xss_injection")

        # Test XSS payload
        xss_payload = "<script>alert('XSS')</script>"

        # Create DeepAgentState with malicious XSS payload
        malicious_state = DeepAgentState(
            user_request="Analyze this data",
            user_id=self.test_user_id,
            chat_thread_id=self.test_thread_id,
            run_id=f"{self.test_run_id}_xss",
            agent_input={
                "analysis_type": xss_payload,  # Inject XSS payload
                "user_content": xss_payload,   # Multiple injection points
                "description": f"Normal content with {xss_payload} embedded"
            }
        )

        # Convert to dict and JSON to simulate serialization/processing
        state_dict = malicious_state.model_dump()

        # Check the agent_input field specifically (avoid datetime serialization issues)
        agent_input_str = json.dumps(state_dict.get("agent_input", {}))

        # VULNERABILITY CHECK: If this assertion passes, the system is NOT sanitizing XSS
        # This assertion should FAIL to prove vulnerability exists
        self.assertNotIn("<script>", agent_input_str,
            "VULNERABILITY: XSS payload '<script>' was not sanitized in agent_input field")

    def test_sql_injection_vulnerability(self):
        """
        Test SQL injection vulnerability in agent_input field.

        EXPECTS TO FAIL: This test should demonstrate SQL injection vulnerability
        by showing that SQL injection payloads are not properly sanitized.
        """
        self.record_metric("vulnerability_subtype", "sql_injection")

        # Test SQL injection payload
        sql_payload = "'; DROP TABLE users; --"

        # Create DeepAgentState with malicious SQL payload
        malicious_state = DeepAgentState(
            user_request="Query my data",
            user_id=self.test_user_id,
            chat_thread_id=self.test_thread_id,
            run_id=f"{self.test_run_id}_sql",
            agent_input={
                "query_filter": sql_payload,
                "user_name": sql_payload,
                "search_term": sql_payload
            }
        )

        # Convert to dict to simulate database processing
        state_dict = malicious_state.model_dump()
        agent_input_str = json.dumps(state_dict.get("agent_input", {}))

        # VULNERABILITY CHECK: If this passes, SQL injection is possible
        # This assertion should FAIL to prove vulnerability exists
        self.assertNotIn("DROP TABLE", agent_input_str,
            "VULNERABILITY: SQL injection payload 'DROP TABLE' was not sanitized")

    def test_path_traversal_vulnerability(self):
        """
        Test path traversal vulnerability in agent_input field.

        EXPECTS TO FAIL: This test should demonstrate path traversal vulnerability
        by showing that directory traversal payloads are not properly sanitized.
        """
        self.record_metric("vulnerability_subtype", "path_traversal")

        # Test path traversal payload
        path_payload = "../../../etc/passwd"

        # Create DeepAgentState with malicious path payload
        malicious_state = DeepAgentState(
            user_request="Process this file",
            user_id=self.test_user_id,
            chat_thread_id=self.test_thread_id,
            run_id=f"{self.test_run_id}_path",
            agent_input={
                "file_path": path_payload,
                "config_file": path_payload,
                "template_path": path_payload
            }
        )

        # Convert to dict to simulate file processing
        state_dict = malicious_state.model_dump()
        agent_input_str = json.dumps(state_dict.get("agent_input", {}))

        # VULNERABILITY CHECK: If this passes, path traversal is possible
        # This assertion should FAIL to prove vulnerability exists
        self.assertNotIn("../", agent_input_str,
            "VULNERABILITY: Path traversal pattern '../' was not sanitized")
        self.assertNotIn("/etc/passwd", agent_input_str,
            "VULNERABILITY: Sensitive path '/etc/passwd' was not blocked")

    def test_command_injection_vulnerability(self):
        """
        Test system command injection vulnerability in agent_input field.

        EXPECTS TO FAIL: This test should demonstrate command injection vulnerability
        by showing that system command payloads are not properly sanitized.
        """
        self.record_metric("vulnerability_subtype", "command_injection")

        # Test command injection payload
        command_payload = "; rm -rf /"

        # Create DeepAgentState with malicious command payload
        malicious_state = DeepAgentState(
            user_request="Run system analysis",
            user_id=self.test_user_id,
            chat_thread_id=self.test_thread_id,
            run_id=f"{self.test_run_id}_cmd",
            agent_input={
                "system_command": command_payload,
                "shell_exec": command_payload,
                "process_args": command_payload
            }
        )

        # Convert to dict to simulate command processing
        state_dict = malicious_state.model_dump()
        agent_input_str = json.dumps(state_dict.get("agent_input", {}))

        # VULNERABILITY CHECK: If this passes, command injection is possible
        # This assertion should FAIL to prove vulnerability exists
        self.assertNotIn("; rm -rf", agent_input_str,
            "VULNERABILITY: Command injection payload '; rm -rf' was not sanitized")

    def teardown_method(self, method):
        """Cleanup after each test method."""
        try:
            # Record final vulnerability test metrics
            total_metrics = self.get_all_metrics()
            self.record_metric("total_vulnerability_tests_run", len([k for k in total_metrics.keys() if k.startswith("vulnerability_")]))
            self.record_metric("test_execution_time", self.get_metrics().execution_time)

        finally:
            super().teardown_method(method)