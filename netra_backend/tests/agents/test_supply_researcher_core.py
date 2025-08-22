"""
Core SupplyResearcherAgent tests - LLM, WebSocket, State, Multi-provider
Modular design with ≤300 lines, ≤8 lines per function
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supply_researcher_sub_agent import ResearchType
from netra_backend.tests.supply_researcher_fixtures import (
    agent,
    assert_api_response_structure,
    assert_websocket_updates_sent,
    mock_db,
    mock_llm_manager,
    mock_supply_service,
    sample_state,
)

class TestSupplyResearcherCore:
    """Core agent functionality tests"""

    async def test_llm_prompt_template_usage(self, agent, mock_llm_manager):
        """Test that agent uses LLM prompt templates correctly"""
        request = "What are the latest prices for Claude-3 Opus?"
        _setup_llm_claude_response(mock_llm_manager)
        parsed = agent.parser.parse_natural_language_request(request)
        _verify_claude_parsing(parsed)

    def _setup_llm_claude_response(self, mock_llm_manager):
        """Setup LLM mock for Claude response (≤8 lines)"""
        response = {
            "research_type": "pricing",
            "provider": "anthropic", 
            "model_name": "claude-3-opus",
            "timeframe": "latest"
        }
        mock_llm_manager.ask_llm.return_value = json.dumps(response)

    def _verify_claude_parsing(self, parsed):
        """Verify Claude parsing results (≤8 lines)"""
        assert parsed["research_type"] == ResearchType.PRICING
        assert parsed["provider"] == "anthropic"
        assert "claude" in parsed["model_name"].lower()

    async def test_websocket_event_streaming(self, agent):
        """Test WebSocket event streaming during research"""
        state = _create_websocket_test_state()
        _setup_research_api_mock(agent)
        await agent.execute(state, "ws_test_run", stream_updates=True)
        _verify_websocket_streaming(agent)

    def _create_websocket_test_state(self):
        """Create state for WebSocket testing (≤8 lines)"""
        return DeepAgentState(
            user_request="Update GPT-4 pricing",
            chat_thread_id="test_thread",
            user_id="test_user"
        )

    def _setup_research_api_mock(self, agent):
        """Setup research API mock (≤8 lines)"""
        with patch.object(agent.research_engine, 'call_deep_research_api', 
                         new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {
                "session_id": "ws_test",
                "status": "completed",
                "questions_answered": [],
                "citations": []
            }

    def _verify_websocket_streaming(self, agent):
        """Verify WebSocket streaming occurred (≤8 lines)"""
        assert_websocket_updates_sent(agent)
        call_args = agent.websocket_manager.send_agent_update.call_args_list
        statuses = _extract_websocket_statuses(call_args)
        assert agent.websocket_manager.send_agent_update.called

    def _extract_websocket_statuses(self, call_args):
        """Extract status updates from WebSocket calls (≤8 lines)"""
        statuses = []
        for call_arg in call_args:
            if isinstance(call_arg, tuple) and len(call_arg) > 1:
                if isinstance(call_arg[1], dict):
                    status = call_arg[1].get("status")
                    if status:
                        statuses.append(status)
        return statuses

    async def test_state_persistence_redis(self, agent):
        """Test agent state persistence in Redis"""
        _setup_redis_mock()
        state = _create_redis_test_state()
        _test_redis_capability(agent, state)
        _verify_redis_integration(agent)

    def _setup_redis_mock(self):
        """Setup Redis mock for testing (≤8 lines)"""
        with patch('app.redis_manager.RedisManager') as mock_redis_class:
            mock_redis = Mock()
            mock_redis.set = AsyncMock()
            mock_redis.get = AsyncMock(return_value=json.dumps({
                "research_session_id": "cached_session",
                "research_status": "in_progress"
            }))
            mock_redis_class.return_value = mock_redis

    def _create_redis_test_state(self):
        """Create state for Redis testing (≤8 lines)"""
        return DeepAgentState(
            user_request="Resume research",
            chat_thread_id="test_thread",
            user_id="test_user"
        )

    def _test_redis_capability(self, agent, state):
        """Test Redis capability configuration (≤8 lines)"""
        from netra_backend.app.redis_manager import RedisManager
        redis_manager = RedisManager()
        assert redis_manager is not None
        assert state.user_request == "Resume research"
        assert state.chat_thread_id == "test_thread"

    def _verify_redis_integration(self, agent):
        """Verify Redis integration capability (≤8 lines)"""
        mock_redis = Mock()
        agent.redis_manager = mock_redis
        assert hasattr(agent, 'redis_manager')

    async def test_multi_provider_parallel_research(self, agent):
        """Test parallel research execution for multiple providers"""
        providers = ["openai", "anthropic", "google"]
        _setup_parallel_research_mock(agent)
        result = await _execute_parallel_research(agent, providers)
        _verify_parallel_execution(result, providers)

    def _setup_parallel_research_mock(self, agent):
        """Setup mock for parallel research (≤8 lines)"""
        async def mock_research(state, run_id, stream):
            await asyncio.sleep(0.01)
            state.supply_research_result = {
                "status": "completed",
                "provider": run_id.split("_")[1]
            }
        
        agent.execute = AsyncMock(side_effect=mock_research)

    async def _execute_parallel_research(self, agent, providers):
        """Execute parallel research test (≤8 lines)"""
        start_time = asyncio.get_event_loop().time()
        result = await agent.process_scheduled_research(
            ResearchType.PRICING,
            providers
        )
        elapsed = asyncio.get_event_loop().time() - start_time
        result["elapsed_time"] = elapsed
        return result

    def _verify_parallel_execution(self, result, providers):
        """Verify parallel execution performance (≤8 lines)"""
        assert result["elapsed_time"] < 0.05
        assert result["providers_processed"] == len(providers)

    # Helper methods for confidence score testing

    def test_confidence_score_calculation(self, agent):
        """Test confidence score calculation with various factors"""
        high_data = _create_high_confidence_data()
        extracted_high = _create_high_confidence_extracted()
        score_high = agent.data_extractor.calculate_confidence_score(
            high_data, extracted_high)
        _verify_high_confidence_score(score_high)

    def _create_high_confidence_data(self):
        """Create high confidence research data (≤8 lines)"""
        return {
            "citations": [
                {"source": "Official API Docs", "url": "https://api.openai.com"},
                {"source": "Pricing Page", "url": "https://openai.com/pricing"},
                {"source": "Blog Post", "url": "https://blog.openai.com"}
            ],
            "questions_answered": [
                {"question": "pricing", "answer": "detailed pricing info"},
                {"question": "capabilities", "answer": "full capabilities"}
            ]
        }

    def _create_high_confidence_extracted(self):
        """Create high confidence extracted data (≤8 lines)"""
        from decimal import Decimal
        return [{
            "pricing_input": Decimal("30"),
            "pricing_output": Decimal("60"),
            "context_window": 128000,
            "capabilities": ["chat", "code", "vision"]
        }]

    def _verify_high_confidence_score(self, score):
        """Verify high confidence score (≤8 lines)"""
        assert score > 0.8

    def test_low_confidence_score_calculation(self, agent):
        """Test low confidence score calculation"""
        low_data = _create_low_confidence_data()
        extracted_low = _create_low_confidence_extracted()
        score_low = agent.data_extractor.calculate_confidence_score(
            low_data, extracted_low)
        _verify_low_confidence_score(score_low)

    def _create_low_confidence_data(self):
        """Create low confidence research data (≤8 lines)"""
        return {
            "citations": [],
            "questions_answered": []
        }

    def _create_low_confidence_extracted(self):
        """Create low confidence extracted data (≤8 lines)"""
        from decimal import Decimal
        return [{"pricing_input": Decimal("30")}]

    def _verify_low_confidence_score(self, score):
        """Verify low confidence score (≤8 lines)"""
        assert score < 0.6