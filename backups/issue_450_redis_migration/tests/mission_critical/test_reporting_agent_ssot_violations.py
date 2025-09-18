class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass"""
        self.is_connected = True"""
"""
        """Send JSON message.""""""
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection.""""""
        self._closed = True"""
"""
        """Get all sent messages.""""""
        return self.messages_sent.copy()"""
        """"""
        =================================================================="""
        and doesn"t violate any architectural principles.

        CRITICAL: These tests are designed to FAIL if violations exist."""

import asyncio
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional
import pytest
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

    # Add project root to path for imports
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.agent_error_types import AgentValidationError
from netra_backend.app.core.serialization.unified_json_handler import LLMResponseParser
from netra_backend.app.services.cache.cache_helpers import CacheHelpers
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler"""
from netra_backend.app.clients.auth_client_core import AuthServiceClient"""
"""
        """Test suite to detect and validate SSOT violations in ReportingSubAgent."""
        pass"""
        @pytest.fixture"""
        """Use real service instance.""""""
        """Create ReportingSubAgent instance.""""""
        return ReportingSubAgent()"""
        @pytest.fixture"""
        """Use real service instance.""""""
        """Create a mock UserExecutionContext with all required fields."""
        pass"""
        context.user_id = "test_user_123"
        context.thread_id = "test_thread_456"
        context.run_id = "test_run_789"
metadata = {"action_plan_result": {"plan": "test plan"},, "optimizations_result": {"optimizations": "test opts"},, "data_result": {"data": "test data"},, "triage_result": {"triage": "test triage"},, "user_request": "test request"}
        return context

    # ========================================================================
    # VIOLATION #1: JSON HANDLING - Should use unified_json_handler.py
    # ========================================================================

    def test_json_handling_violation_extract_json_from_response(self, agent):
        """"""
from agents.utils instead of unified_json_handler.py"""
        pass
    # Check if the agent is using the wrong JSON extraction method
from netra_backend.app.agents import reporting_sub_agent"""
    # This test SHOULD FAIL if the agent uses the wrong import"""
"""
        assert "from netra_backend.app.agents.utils import extract_json_from_response" in source_code, \
        "VIOLATION DETECTED: Using agents.utils.extract_json_from_response instead of unified_json_handler"

    # CORRECT: Should be using LLMResponseParser
        assert "from netra_backend.app.core.serialization.unified_json_handler import LLMResponseParser" not in source_code, \
        "SSOT VIOLATION: Not using LLMResponseParser from unified_json_handler"

    def test_json_parsing_should_use_llm_response_parser(self, agent, mock_context):
        """"""
        instead of custom implementation."""
        pass"""
        test_response = '{"report": "test", "invalid": json}'

    # This should use LLMResponseParser, not custom extraction
        with patch('netra_backend.app.agents.utils.extract_json_from_response') as mock_extract:
        mock_extract.return_value = None
        result = agent._extract_and_validate_report(test_response, "test_run")

        # VIOLATION: Still using old extraction method
        assert mock_extract.called, "VIOLATION: Using custom JSON extraction"

    def test_json_error_handling_should_use_json_error_fixer(self, agent):
        """
        Test that JSON error handling should use JSONErrorFixer from unified handler.""""""
        malformed_json = '{"report": "test", invalid}'

    # Should use JSONErrorFixer for malformed JSON
        result = agent._extract_and_validate_report(malformed_json, "test_run")

    # Currently returns fallback without attempting to fix
        assert result == {"report": "No report could be generated from LLM response."}, \
        "VIOLATION: Not using JSONErrorFixer for malformed JSON"

    # ========================================================================
    # VIOLATION #2: CACHING & HASHING - Should use CacheHelpers
    # ========================================================================

    def test_caching_key_generation_violation(self, agent):
        """"""
        Currently, the agent doesn"t implement proper caching with user context."""
        pass"""
        assert agent.enable_caching == True, "Caching is enabled"

    # Check if agent uses CacheHelpers for cache key generation
    # This should FAIL because agent doesn't implement proper caching
        assert not hasattr(agent, '_generate_cache_key'), \
        "VIOLATION: No cache key generation method found"

    # Should have a method that uses CacheHelpers
        with pytest.raises(AttributeError):
        # This should fail because the method doesn't exist
        agent._generate_cache_key_with_context( )
    def test_hash_generation_should_use_cache_helpers(self, agent):
        """
        Test that any hash generation should use CacheHelpers, not custom implementation."""
        pass"""
        test_data = "test_data_for_hashing"

    # VIOLATION: Custom hash implementation (if exists)
    # Check source code for hashlib usage
from netra_backend.app.agents import reporting_sub_agent
        source_code = Path(reporting_sub_agent.__file__).read_text()

        assert "import hashlib" not in source_code, \
        "VIOLATION: Direct hashlib import found - should use CacheHelpers"

    # ========================================================================
    # VIOLATION #3: USER EXECUTION CONTEXT - Proper integration required
    # ========================================================================

    def test_context_not_optional_in_constructor(self, agent):
        """"""
        Currently VIOLATES this - constructor doesn"t accept context."""
        pass
    # VIOLATION: Constructor doesn't accept context parameter"""
        # This SHOULD work but doesn't"""
"""
        """
        Test that user-specific data should NOT be stored in instance variables."""
        pass"""
        asyncio.run(agent.execute(mock_context))"""
    # Check for stored user data (VIOLATION if found)"""
        "VIOLATION: user_id stored in instance variable"
        assert not hasattr(agent, 'thread_id'), \
        "VIOLATION: thread_id stored in instance variable"
        assert not hasattr(agent, 'run_id'), \
        "VIOLATION: run_id stored in instance variable"

    def test_context_passed_to_subcomponents(self, agent, mock_context):
        """
        Test that context is properly passed to all sub-components."""
        pass"""
        mock_llm.return_value = '{"report": "test"}'

        asyncio.run(agent.execute(mock_context))

        # Context should be passed through to all methods
        # Currently VIOLATES - doesn't pass context to LLM execution
        assert mock_llm.call_count == 1
        call_args = mock_llm.call_args
        # This will FAIL - context not passed to LLM method
        # assert any(isinstance(arg, UserExecutionContext) for arg in call_args[0])

        # ========================================================================
        # VIOLATION #4: ENVIRONMENT ACCESS - Should use IsolatedEnvironment
        # ========================================================================

    def test_direct_environment_access_violation(self):
        """
        Test that agent should NOT use os.environ directly.""""""
from netra_backend.app.agents import reporting_sub_agent"""
"""
        assert "os.environ" not in source_code, \
        "VIOLATION: Direct os.environ access found - should use IsolatedEnvironment"

    Should import IsolatedEnvironment
        assert "from shared.isolated_environment import IsolatedEnvironment" not in source_code, \
        "VIOLATION: Not using IsolatedEnvironment for environment access"

    # ========================================================================
    # VIOLATION #5: RETRY LOGIC - Should use UnifiedRetryHandler
    # ========================================================================

    def test_custom_retry_logic_violation(self):
        """
        Test that agent should use UnifiedRetryHandler for retry logic.""""""
from netra_backend.app.agents import reporting_sub_agent"""
"""
        assert "for attempt in range" not in source_code, \
        "VIOLATION: Custom retry loop found - should use UnifiedRetryHandler"

    Should import UnifiedRetryHandler if using retries
        assert "from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler" not in source_code, \
        "WARNING: Not using UnifiedRetryHandler for resilience"

    # ========================================================================
    # VIOLATION #6: DATABASE SESSION - Should use DatabaseSessionManager properly
    # ========================================================================

    def test_database_session_storage_violation(self, agent, mock_context):
        """
        Test that database sessions should NOT be stored in instance variables."""
        pass"""
        asyncio.run(agent.execute(mock_context))"""
    # Check for stored session (VIOLATION if found)"""
        "VIOLATION: db_session stored in instance variable"
        assert not hasattr(agent, '_db_session'), \
        "VIOLATION: _db_session stored in instance variable"

    # ========================================================================
    # VIOLATION #7: WEBSOCKET INTEGRATION - Should use WebSocketBridgeAdapter
    # ========================================================================

    def test_websocket_event_emission_pattern(self, agent):
        """
        Test that WebSocket events should use WebSocketBridgeAdapter pattern.""""""
    Agent should have WebSocket adapter from BaseAgent"""
        "Should have WebSocket adapter from BaseAgent"

    # Check that direct WebSocket manipulation is not used
from netra_backend.app.agents import reporting_sub_agent
        source_code = Path(reporting_sub_agent.__file__).read_text()

    # Removed problematic line: assert "await websocket.send_json" not in source_code, \
        "VIOLATION: Direct WebSocket manipulation found"

    # ========================================================================
    # VIOLATION #8: ERROR HANDLING - Should use agent_error_handler
    # ========================================================================

    def test_error_handling_pattern_violation(self, agent, mock_context):
        """
        Test that error handling should use unified patterns."""
        pass
    # Force an error
        mock_context.metadata = {}  # Missing required fields

        with pytest.raises(AgentValidationError):
        asyncio.run(agent.execute(mock_context))
"""
from netra_backend.app.agents import reporting_sub_agent"""
"""
        assert "from netra_backend.app.core.unified_error_handler import agent_error_handler" not in source_code, \
        "WARNING: Not using unified error handler"

        # ========================================================================
        # VIOLATION #9: CONFIGURATION ACCESS - Should use config architecture
        # ========================================================================

    def test_configuration_access_pattern(self):
        """
        Test that configuration should be accessed through proper architecture.""""""
from netra_backend.app.agents import reporting_sub_agent"""
"""
        assert "open(" not in source_code or "config" not in source_code, \
        "VIOLATION: Direct config file reading detected"

        assert "json.load" not in source_code or "config" not in source_code, \
        "VIOLATION: Direct JSON config loading detected"

    # ========================================================================
    # VIOLATION #10: BASE CLASS DUPLICATION - Should not duplicate BaseAgent
    # ========================================================================

    def test_base_class_functionality_duplication(self, agent):
        """
        Test that agent doesn"t duplicate BaseAgent functionality.""""""
    Check that agent properly inherits from BaseAgent"""
        assert isinstance(agent, BaseAgent), "Should inherit from BaseAgent"

    Check for duplicated methods that should come from BaseAgent
        base_methods = dir(BaseAgent)
        agent_methods = dir(agent)

    # These methods should be inherited, not redefined
    # (unless explicitly overriding for business logic)
        infrastructure_methods = [ )
        '_setup_reliability_manager',
        '_setup_execution_engine',
        '_setup_caching',
        '_setup_monitoring'
    

        for method in infrastructure_methods:
        if method in base_methods and method in agent_methods:
            # Check if it's the same implementation (inherited) or overridden
        base_impl = getattr(BaseAgent, method, None)
        agent_impl = getattr(agent.__class__, method, None)
        if agent_impl and base_impl and agent_impl != base_impl:
        pytest.fail("formatted_string")


class TestReportingAgentComplexScenarios:
        """Complex, difficult test scenarios for ReportingSubAgent.""""""
        @pytest.fixture"""
        """Use real service instance.""""""
        return ReportingSubAgent()"""
        @pytest.fixture"""
        """Use real service instance."""
    # TODO: Initialize real service"""
        """Create complex context with edge cases.""""""
        context.user_id = "user_" + "x" * 100  # Long user ID
        context.thread_id = "thread_[U+1F600]_unicode"  # Unicode in ID
        context.run_id = "run_" + str(time.time())
metadata = {"action_plan_result": {"plan": "a" * 10000},  # Large data, "optimizations_result": {"nested": {"deeply": {"nested": {"data": "test"}}}},, "data_result": {"unicode": "[U+6D4B][U+8BD5][U+6570][U+636E] [U+1F680]"},, "triage_result": {"special_chars": "";DROP TABLE users;--"},, "user_request": None  # Null value}
        return context

    def test_concurrent_execution_isolation(self, agent):
        """
        Test that concurrent executions don"t share state.
        CRITICAL: Multiple users must be isolated."""
        pass"""
        for i in range(10):"""
        ctx.user_id = "formatted_string"
        ctx.thread_id = "formatted_string"
        ctx.run_id = "formatted_string"
metadata = {"action_plan_result": "formatted_string",, "optimizations_result": "formatted_string",, "data_result": "formatted_string",, "triage_result": "formatted_string",, "user_request": "formatted_string"}
        contexts.append(ctx)

    async def execute_with_delay(ctx, delay):
        pass
        await asyncio.sleep(delay)
        with patch.object(agent, '_execute_reporting_llm_with_observability') as mock_llm:
        mock_llm.return_value = 'formatted_string'
        await asyncio.sleep(0)
        return await agent.execute(ctx)

        # Execute all contexts concurrently
        loop = asyncio.new_event_loop()
        # Verify isolation - each result should match its context
        for i, result in enumerate(results):
        expected_user = "formatted_string"
        assert "formatted_string" in str(result), \
        "formatted_string"

    def test_memory_leak_with_large_payloads(self, agent):
        """
        Test that agent doesn"t leak memory with large payloads."""
        pass
import gc
import sys"""
        initial_objects = len(gc.get_objects())"""
        for i in range(100):"""
        context.user_id = "formatted_string"
        context.thread_id = "formatted_string"
        context.run_id = "formatted_string"
        context.db_session = Magic            # Large payload
        large_data = "x" * 1000000  # 1MB string
metadata = {"action_plan_result": large_data,, "optimizations_result": large_data,, "data_result": large_data,, "triage_result": large_data,, "user_request": large_data}
        with patch.object(agent, '_execute_reporting_llm_with_observability') as mock_llm:
        mock_llm.return_value = '{"report": "test"}'
        asyncio.run(agent.execute(context))

            # Force garbage collection
        context = None
        gc.collect()

        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

            # Should not grow significantly (allowing some growth for caches)
        assert object_growth < 1000, \
        "formatted_string"

    def test_resilience_to_malformed_inputs(self, agent):
        """
        Test agent resilience to various malformed inputs.""""""
        malformed_contexts = [ )"""
        "not_a_context",  # Wrong type
        Magic            MagicMock(spec=UserExecutionContext, metadata=None),  # Null metadata
        MagicMock(spec=UserExecutionContext, metadata={}),  # Empty metadata
        MagicMock(spec=UserExecutionContext, metadata={"wrong": "keys"}),  # Wrong keys
    

        for bad_context in malformed_contexts:
        with pytest.raises((AgentValidationError, AttributeError, TypeError)):
        asyncio.run(agent.execute(bad_context))

    def test_race_condition_in_state_updates(self, agent):
        """
        Test for race conditions in state updates."""
        pass"""
        context.user_id = "race_user"
        context.thread_id = "race_thread"
        context.run_id = "race_run"
metadata = {"action_plan_result": "plan",, "optimizations_result": "opt",, "data_result": "data",, "triage_result": "triage",, "user_request": "request"}
    # Simulate rapid sequential calls that might cause race conditions
    async def rapid_calls():
        pass
        tasks = []
        for i in range(50):
        with patch.object(agent, '_execute_reporting_llm_with_observability') as mock_llm:
        mock_llm.return_value = 'formatted_string'
        task = agent.execute(context)
        tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0)
        return results

        results = asyncio.run(rapid_calls())

            # All should complete without race condition errors
        errors = [item for item in []]
        assert len(errors) == 0, "formatted_string"


        if __name__ == "__main__":
                # Run tests with verbose output
        pytest.main([__file__, "-v", "-s", "--tb=short"])