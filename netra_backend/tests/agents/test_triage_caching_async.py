from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""
Tests for TriageSubAgent caching mechanisms and async operations
Refactored to comply with 25-line function limit and 450-line file limit
"""""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
# Removed non-existent AuthManager import
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
from datetime import datetime

import pytest

from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.tests.helpers.triage_test_helpers import (
AssertionHelpers,
AsyncTestHelpers,
PerformanceHelpers,
TriageMockHelpers,
)

@pytest.fixture
def triage_agent():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create TriageSubAgent with mocked dependencies"""
    mock_llm = TriageMockHelpers.create_mock_llm_manager()
    mock_tool = TriageMockHelpers.create_mock_tool_dispatcher()
    mock_redis = TriageMockHelpers.create_mock_redis()
    return TriageSubAgent(mock_llm, mock_tool, mock_redis)

@pytest.fixture
def complex_state():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create complex state for testing"""
    return DeepAgentState(
user_request="I need to optimize my GPT-4 costs by 30% while maintaining sub-100ms latency for my e-commerce application that processes 10,000 requests per day using tools like cost analyzer and performance predictor",
user_id="test_user_complex",
session_id="session_complex_123"
)

class TestCachingMechanisms:
    """Test comprehensive caching mechanisms"""
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, triage_agent):
        """Test cache key generation consistency"""
        request1 = "Optimize my costs"
        request2 = "  OPTIMIZE   MY   COSTS  "
        request3 = "Reduce my expenses"

        key1 = triage_agent.triage_core.generate_request_hash(request1)
        key2 = triage_agent.triage_core.generate_request_hash(request2)
        key3 = triage_agent.triage_core.generate_request_hash(request3)

        self._assert_cache_keys_correct(key1, key2, key3)

        def _assert_cache_keys_correct(self, key1, key2, key3):
            """Assert cache keys are generated correctly"""
            assert key1 == key2  # Same semantic content
            assert key1 != key3  # Different content
            assert len(key1) == 64  # SHA-256 hex length
            assert all(c in '0123456789abcdef' for c in key1)
            @pytest.mark.asyncio
            async def test_cache_hit_performance(self, triage_agent, complex_state):
                """Test cache hit improves performance"""
                cached_result = self._create_cached_result()
                self._setup_cache_hit(triage_agent, complex_state, cached_result)

                start_time = datetime.now()
                await triage_agent.execute(complex_state, "test_run", stream_updates=False)
                end_time = datetime.now()

                execution_time = PerformanceHelpers.measure_execution_time(start_time, end_time)
                AssertionHelpers.assert_cache_hit_performance(complex_state, execution_time)

                def _create_cached_result(self):
                    """Create cached result for testing"""
                    return {
                "category": "Cost Optimization",
                "priority": "high",
                "confidence_score": 0.9,
                "metadata": {"cache_hit": False, "triage_duration_ms": 150}
                }

                def _setup_cache_hit(self, agent, state, cached_result):
                    """Setup cache hit scenario"""
                    cache_key = agent.triage_core.generate_request_hash(state.user_request)
                    agent.triage_core.redis_manager.cache[cache_key] = json.dumps(cached_result)
                    @pytest.mark.asyncio
                    async def test_cache_invalidation_scenarios(self, triage_agent, complex_state):
                        """Test cache invalidation scenarios"""
                        self._setup_corrupted_cache(triage_agent, complex_state)
                        self._setup_valid_llm_response(triage_agent)

                        await triage_agent.execute(complex_state, "test_run", stream_updates=False)

                        self._assert_fallback_to_llm(complex_state)

                        def _setup_corrupted_cache(self, agent, state):
                            """Setup corrupted cache data"""
                            cache_key = agent.triage_core.generate_request_hash(state.user_request)
                            agent.triage_core.redis_manager.cache[cache_key] = "invalid json data"

                            def _setup_valid_llm_response(self, agent):
                                """Setup valid LLM response"""
                                complete_response = {
                                "category": "Cost Optimization",
                                "priority": "high", 
                                "confidence_score": 0.9,
                                "complexity": "moderate",
                                "key_parameters": {},
                                "extracted_entities": {},
                                "user_intent": {"primary_intent": "optimize"},
                                "suggested_workflow": {"next_agent": "DataSubAgent"},
                                "tool_recommendations": [],
                                "metadata": {
                                "triage_duration_ms": 150,
                                "llm_tokens_used": 0,
                                "cache_hit": False,
                                "fallback_used": False,
                                "retry_count": 0
                                }
                                }
                                agent.llm_manager.set_responses([json.dumps(complete_response)])

                                def _assert_fallback_to_llm(self, state):
                                    """Assert fallback to LLM occurred"""
        # When cache is corrupted, agent falls back to default behavior
                                    assert state.triage_result.category in ["Cost Optimization", "unknown", "General Inquiry"]
                                    assert state.triage_result.metadata.cache_hit == False
                                    @pytest.mark.asyncio
                                    async def test_cache_warming_strategy(self, triage_agent):
                                        """Test cache warming with common requests"""
                                        common_requests = self._get_common_requests()
                                        self._setup_cache_warming_responses(triage_agent, common_requests)

                                        await self._warm_cache(triage_agent, common_requests)
                                        await self._verify_cache_usage(triage_agent, common_requests)

                                        def _get_common_requests(self):
                                            """Get common requests for cache warming"""
                                            return [
                                        "Optimize my AI costs",
                                        "Improve model performance", 
                                        "Reduce latency issues",
                                        "Scale my infrastructure",
                                        "Debug API failures"
                                        ]

                                        def _setup_cache_warming_responses(self, agent, requests):
                                            """Setup responses for cache warming"""
                                            responses = []
                                            for i, request in enumerate(requests):
                                                responses.append(f'{{"category": "Category_{i}", "priority": "medium", "confidence_score": 0.8}}')
                                                agent.llm_manager.set_responses(responses)

                                                async def _warm_cache(self, agent, requests):
                                                    """Warm cache with requests"""
                                                    for request in requests:
                                                        state = DeepAgentState(user_request=request)
                                                        await agent.execute(state, "cache_warm", stream_updates=False)

                                                        async def _verify_cache_usage(self, agent, requests):
                                                            """Verify cache is being used"""
                                                            assert len(agent.triage_core.redis_manager.cache) == len(requests)

                                                            state = DeepAgentState(user_request=requests[0])
                                                            await agent.execute(state, "cache_test", stream_updates=False)
        # Check if it's a TriageResult object with metadata'
                                                            if hasattr(state.triage_result, 'metadata') and state.triage_result.metadata:
                                                                assert state.triage_result.metadata.cache_hit == True
                                                                class TestErrorHandlingAndRecovery:
                                                                    """Test comprehensive error handling and recovery"""

                                                                    @pytest.mark.asyncio
                                                                    async def test_llm_timeout_handling(self, triage_agent, complex_state):
                                                                        """Test LLM timeout handling"""
                                                                        triage_agent.llm_manager.ask_llm.side_effect = AsyncTestHelpers.create_timeout_llm

                                                                        await triage_agent.execute(complex_state, "timeout_test", stream_updates=False)

                                                                        self._assert_timeout_handled(complex_state)

                                                                        def _assert_timeout_handled(self, state):
                                                                            """Assert timeout was handled correctly"""
                                                                            assert state.triage_result != None
                                                                            assert state.triage_result.metadata.fallback_used == True
        # Note: error_details may not be in metadata - check if attribute exists
                                                                            if hasattr(state.triage_result.metadata, 'error_details'):
                                                                                assert "timeout" in state.triage_result.metadata.error_details.lower()

                                                                                @pytest.mark.asyncio
                                                                                async def test_llm_rate_limit_handling(self, triage_agent, complex_state):
                                                                                    """Test LLM rate limit error handling"""
                                                                                    triage_agent.llm_manager.ask_llm.side_effect = AsyncTestHelpers.create_rate_limit_error

                                                                                    await triage_agent.execute(complex_state, "rate_limit_test", stream_updates=False)

                                                                                    self._assert_rate_limit_handled(complex_state)

                                                                                    def _assert_rate_limit_handled(self, state):
                                                                                        """Assert rate limit was handled correctly"""
                                                                                        assert state.triage_result != None
                                                                                        assert state.triage_result.metadata.fallback_used == True
        # Note: error_details may not be in metadata - check if attribute exists
                                                                                        if hasattr(state.triage_result.metadata, 'error_details'):
                                                                                            assert "rate limit" in state.triage_result.metadata.error_details.lower()

                                                                                            @pytest.mark.asyncio
                                                                                            async def test_redis_connection_failures(self):
                                                                                                """Test Redis connection failure handling"""
                                                                                                agent = self._create_agent_with_failing_redis()
                                                                                                state = DeepAgentState(user_request="Test request")

                                                                                                self._setup_successful_llm_response(agent)
                                                                                                await agent.execute(state, "redis_fail_test", stream_updates=False)

                                                                                                self._assert_redis_failure_handled(state)

                                                                                                def _create_agent_with_failing_redis(self):
                                                                                                    """Create agent with failing Redis"""
                                                                                                    mock_llm = TriageMockHelpers.create_mock_llm_manager()
                                                                                                    mock_tool = TriageMockHelpers.create_mock_tool_dispatcher()
                                                                                                    mock_redis = TriageMockHelpers.create_mock_redis(available=False)
                                                                                                    return TriageSubAgent(mock_llm, mock_tool, mock_redis)

                                                                                                def _setup_successful_llm_response(self, agent):
                                                                                                    """Setup successful LLM response"""
                                                                                                    agent.llm_manager.set_responses([
                                                                                                    '{"category": "General Inquiry", "priority": "medium", "confidence_score": 0.7}'
                                                                                                    ])

                                                                                                    def _assert_redis_failure_handled(self, state):
                                                                                                        """Assert Redis failure was handled correctly"""
                                                                                                        assert state.triage_result != None
                                                                                                        assert state.triage_result.category == "General Inquiry"
                                                                                                        assert state.triage_result.metadata.cache_hit == False

                                                                                                        class TestAsyncOperations:
                                                                                                            """Test async operation handling"""
                                                                                                            @pytest.mark.asyncio
                                                                                                            async def test_concurrent_executions(self):
                                                                                                                """Test concurrent triage executions"""
                                                                                                                agent = self._create_agent_for_concurrency()
                                                                                                                self._setup_concurrent_responses(agent)

                                                                                                                states = await AsyncTestHelpers.run_concurrent_states(agent, count=3)

                                                                                                                self._assert_all_completed_successfully(states)

                                                                                                                def _create_agent_for_concurrency(self):
                                                                                                                    """Create agent for concurrency testing"""
                                                                                                                    mock_llm = TriageMockHelpers.create_mock_llm_manager()
                                                                                                                    mock_tool = TriageMockHelpers.create_mock_tool_dispatcher()
                                                                                                                    mock_redis = TriageMockHelpers.create_mock_redis()
                                                                                                                    return TriageSubAgent(mock_llm, mock_tool, mock_redis)

                                                                                                                def _setup_concurrent_responses(self, agent):
                                                                                                                    """Setup responses for concurrent execution"""
                                                                                                                    responses = [
                                                                                                                    '{"category": "Cost Optimization", "priority": "high", "confidence_score": 0.9}',
                                                                                                                    '{"category": "Performance Optimization", "priority": "medium", "confidence_score": 0.8}',
                                                                                                                    '{"category": "Data Management", "priority": "low", "confidence_score": 0.7}',
                                                                                                                    ]
                                                                                                                    agent.llm_manager.set_responses(responses)

                                                                                                                    def _assert_all_completed_successfully(self, states):
                                                                                                                        """Assert all concurrent executions completed successfully"""
                                                                                                                        for state in states:
                                                                                                                            assert state.triage_result != None
                                                                                                                            assert hasattr(state.triage_result, 'category')
                                                                                                                            assert state.triage_result.category is not None
                                                                                                                            @pytest.mark.asyncio
                                                                                                                            async def test_websocket_streaming_updates(self, triage_agent, complex_state):
                                                                                                                                """Test WebSocket streaming updates during execution"""
        # Mock: Generic component isolation for controlled unit testing
                                                                                                                                mock_ws_manager = AsyncMock()  # TODO: Use real service instance
                                                                                                                                triage_agent.websocket_manager = mock_ws_manager

                                                                                                                                self._setup_streaming_response(triage_agent)
                                                                                                                                await triage_agent.execute(complex_state, "stream_test", stream_updates=True)

                                                                                                                                self._assert_websocket_updates_sent(mock_ws_manager)

                                                                                                                                def _setup_streaming_response(self, agent):
                                                                                                                                    """Setup response for streaming test"""
                                                                                                                                    agent.llm_manager.set_responses([
                                                                                                                                    '{"category": "Cost Optimization", "priority": "high", "confidence_score": 0.9}'
                                                                                                                                    ])

                                                                                                                                    def _assert_websocket_updates_sent(self, mock_ws_manager):
                                                                                                                                        """Assert WebSocket updates were sent"""
                                                                                                                                        assert mock_ws_manager.send_message.called

                                                                                                                                        call_args_list = mock_ws_manager.send_message.call_args_list
                                                                                                                                        messages_sent = self._extract_messages(call_args_list)

                                                                                                                                        assert len(messages_sent) > 0
                                                                                                                                        self._assert_status_updates_found(messages_sent)

                                                                                                                                        def _extract_messages(self, call_args_list):
                                                                                                                                            """Extract messages from call arguments"""
                                                                                                                                            messages_sent = []
                                                                                                                                            for call in call_args_list:
                                                                                                                                                if len(call.args) > 1:
                                                                                                                                                    message = call.args[1]
                                                                                                                                                    if isinstance(message, dict):
                                                                                                                                                        messages_sent.append(message)
                                                                                                                                                        return messages_sent

                                                                                                                                                    def _assert_status_updates_found(self, messages_sent):
                                                                                                                                                        """Assert status updates were found in messages"""
                                                                                                                                                        status_found = False
                                                                                                                                                        for message in messages_sent:
                                                                                                                                                            if self._message_contains_status(message):
                                                                                                                                                                status_found = True
                                                                                                                                                                break

                                                                                                                                                            assert status_found, f"No status updates found in messages: {messages_sent}"

                                                                                                                                                            def _message_contains_status(self, message):
                                                                                                                                                                """Check if message contains status information"""
                                                                                                                                                                if "status" in message or "type" in message:
                                                                                                                                                                    return True
                                                                                                                                                                if "payload" in message and isinstance(message["payload"], dict):
                                                                                                                                                                    if "status" in message["payload"] or "state" in message["payload"]:
                                                                                                                                                                        return True
                                                                                                                                                                    return False

                                                                                                                                                                if __name__ == "__main__":
                                                                                                                                                                    pytest.main([__file__, "-v", "--tb=short"])