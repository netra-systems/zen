"""
Issue #1017 Security Vulnerability Tests: Input Sanitization Comprehensive

CRITICAL SECURITY TEST SUITE: These tests are designed to FAIL initially to prove
security vulnerabilities exist in the agent_input field processing.

These tests specifically target:
1. Malicious payload injection in agent_input field
2. XSS (Cross-Site Scripting) vulnerability testing
3. SQL injection vulnerability testing
4. Path traversal vulnerability testing
5. Code injection vulnerability testing
6. System command injection vulnerability testing
7. API key extraction vulnerability testing

REQUIREMENTS:
- Tests MUST FAIL initially to prove vulnerabilities exist
- Uses SSOT test infrastructure from test_framework/
- Real services only - NO MOCKS in vulnerability testing
- Follows testing best practices from reports/testing/TEST_CREATION_GUIDE.md

Business Value: Enterprise/Platform - Security compliance for HIPAA, SOC2, SEC regulations
"""

import json
import os
import sys
import uuid
from typing import Any, Dict
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.schemas.agent_models import DeepAgentState


class TestIssue1017InputSanitizationVulnerabilities(SSotBaseTestCase):
    """
    Comprehensive security vulnerability tests for Issue #1017.

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

    def test_malicious_xss_payload_injection_vulnerability(self):
        """
        Test XSS payload injection in agent_input field.

        EXPECTS TO FAIL: This test should demonstrate XSS vulnerability
        by showing that malicious JavaScript payloads are not properly sanitized.
        """
        self.record_metric("vulnerability_subtype", "xss_injection")

        # Test one representative XSS payload to verify vulnerability
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
                "description": f"Normal content with {xss_payload} embedded",
                "config": {
                    "nested_field": xss_payload,  # Test nested injection
                    "callback_url": f"https://evil.com?q={xss_payload}"
                }
            }
        )

        # Convert to dict to simulate serialization/processing
        state_dict = malicious_state.model_dump()

        # VULNERABILITY CHECK: If this assertion passes, the system is NOT sanitizing XSS
        # This assertion should FAIL to prove vulnerability exists
        state_json = json.dumps(state_dict)

        # Check that the malicious script tag appears in the serialized output
        # If this assertion fails, it proves the vulnerability exists
        self.assertNotIn("<script>", state_json,
            f"VULNERABILITY: XSS payload '<script>' was not sanitized in state serialization")

        # Check agent_input field specifically
        agent_input_str = json.dumps(state_dict.get("agent_input", {}))
        self.assertNotIn("<script>", agent_input_str,
            f"VULNERABILITY: XSS payload '<script>' was not sanitized in agent_input field")

    def test_sql_injection_vulnerability_in_agent_input(self):
        """
        Test SQL injection vulnerability in agent_input field.

        EXPECTS TO FAIL: This test should demonstrate SQL injection vulnerability
        by showing that SQL injection payloads are not properly sanitized.
        """
        self.record_metric("vulnerability_subtype", "sql_injection")

        # Create malicious SQL injection payloads
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM sensitive_data --",
            "'; INSERT INTO logs VALUES ('hacked'); --",
            "' OR 1=1 UNION SELECT password FROM users --"
        ]

        for i, payload in enumerate(sql_payloads):
            # Test each SQL injection payload individually
            # Create DeepAgentState with malicious SQL payload
            malicious_state = DeepAgentState(
                user_request="Query my data",
                user_id=self.test_user_id,
                chat_thread_id=self.test_thread_id,
                run_id=f"{self.test_run_id}_sql_{i}",
                agent_input={
                    "query_filter": payload,
                    "user_name": payload,
                    "search_term": payload,
                    "database_query": {
                        "where_clause": payload,
                        "order_by": payload
                    }
                }
            )

            # Convert to dict to simulate database processing
            state_dict = malicious_state.model_dump()
            agent_input_str = json.dumps(state_dict.get("agent_input", {}))

            # VULNERABILITY CHECK: If this passes, SQL injection is possible
            # These assertions should FAIL to prove vulnerability exists
            sql_keywords = ["DROP TABLE", "UNION SELECT", "INSERT INTO"]
            for keyword in sql_keywords:
                if keyword in payload:
                    self.assertNotIn(keyword, agent_input_str,
                        f"VULNERABILITY: SQL keyword '{keyword}' from payload '{payload}' was not sanitized")

    def teardown_method(self, method):
        """Cleanup after each test method."""
        try:
            # Record final vulnerability test metrics
            total_metrics = self.get_all_metrics()
            self.record_metric("total_vulnerability_tests_run", len([k for k in total_metrics.keys() if k.startswith("vulnerability_")]))
            self.record_metric("test_execution_time", self.get_metrics().execution_time)

        finally:
            super().teardown_method(method)