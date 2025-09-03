"""Tests for Agent Context Window Isolation and Management.

This test suite validates:
1. Context window size limits
2. Prompt truncation behavior
3. Context isolation between agents
4. Token counting and limits
5. Context overflow handling
6. Memory management
"""

import asyncio
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.data_sub_agent import DataSubAgent
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.agent import SubAgentLifecycle


class TestContextWindowIsolation:
    """Test context window isolation between agents."""

    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        manager = MagicMock(spec=LLMManager)
        manager.generate = AsyncMock(return_value="test response")
        manager.model_config = {"max_tokens": 4096, "context_window": 128000}
        return manager

    @pytest.fixture
    def base_agent(self, mock_llm_manager):
        """Create base agent instance."""
        return BaseAgent(
            llm_manager=mock_llm_manager,
            name="TestAgent",
            description="Test agent"
        )

    @pytest.mark.asyncio
    async def test_context_isolation_between_agents(self, mock_llm_manager):
        """Test that context is isolated between different agent instances."""
        # Create two agent instances
        agent1 = BaseAgent(mock_llm_manager, name="Agent1")
        agent2 = BaseAgent(mock_llm_manager, name="Agent2")
        
        # Set different context for each agent
        agent1.context = {"data": "agent1_private_data", "sensitive": "secret1"}
        agent2.context = {"data": "agent2_private_data", "sensitive": "secret2"}
        
        # Verify contexts are isolated
        assert agent1.context != agent2.context
        assert agent1.context["sensitive"] == "secret1"
        assert agent2.context["sensitive"] == "secret2"
        
        # Modifying one context should not affect the other
        agent1.context["new_key"] = "new_value"
        assert "new_key" not in agent2.context

    @pytest.mark.asyncio
    async def test_context_window_size_limit(self, mock_llm_manager):
        """Test that prompts exceeding context window are handled."""
        agent = BaseAgent(mock_llm_manager, name="TestAgent")
        
        # Create a prompt that exceeds typical context window
        large_prompt = "x" * 200000  # 200k characters
        
        # This should trigger context window handling
        with pytest.raises(ValueError, match="Context window exceeded"):
            await agent._validate_context_window_size(large_prompt)

    @pytest.mark.asyncio
    async def test_prompt_truncation_on_overflow(self, mock_llm_manager):
        """Test that prompts are truncated when they exceed limits."""
        agent = DataSubAgent(mock_llm_manager)
        
        # Create a large context that needs truncation
        large_context = {
            "history": ["message " * 1000 for _ in range(100)],
            "data": "x" * 50000
        }
        
        # Should truncate without error
        truncated = agent._truncate_context_if_needed(large_context, max_size=10000)
        
        # Verify truncation occurred
        assert len(str(truncated)) <= 10000
        assert "..." in str(truncated) or "truncated" in str(truncated).lower()

    @pytest.mark.asyncio
    async def test_token_counting_accuracy(self, mock_llm_manager):
        """Test accurate token counting for prompts."""
        agent = BaseAgent(mock_llm_manager, name="TestAgent")
        
        test_cases = [
            ("Hello world", 2),  # Simple text
            ("The quick brown fox jumps over the lazy dog", 9),  # Sentence
            ("🚀 Emoji test 🎉", 5),  # With emojis
            ("a" * 1000, 250),  # Repeated characters (approx 4 chars per token)
        ]
        
        for text, expected_tokens in test_cases:
            token_count = agent._estimate_token_count(text)
            # Allow 20% variance in estimation
            assert abs(token_count - expected_tokens) <= expected_tokens * 0.2

    @pytest.mark.asyncio
    async def test_context_memory_leak_prevention(self, mock_llm_manager):
        """Test that agent contexts are properly cleaned up to prevent memory leaks."""
        agents = []
        
        # Create multiple agents
        for i in range(100):
            agent = BaseAgent(mock_llm_manager, name=f"Agent{i}")
            agent.context = {"data": "x" * 10000}  # 10KB per agent
            agents.append(agent)
        
        # Shutdown all agents
        for agent in agents:
            await agent.shutdown()
            # Verify context is cleared
            assert len(agent.context) == 0

    @pytest.mark.asyncio
    async def test_supervisor_agent_context_distribution(self, mock_llm_manager):
        """Test that supervisor properly isolates context for sub-agents."""
        supervisor = SupervisorAgent(mock_llm_manager)
        
        # Create mock sub-agents
        data_agent = MagicMock(spec=DataSubAgent)
        triage_agent = MagicMock(spec=TriageSubAgent)
        
        # Supervisor should maintain separate contexts
        contexts = {
            "data_agent": {"specific": "data_context"},
            "triage_agent": {"specific": "triage_context"}
        }
        
        # Verify context isolation in delegation
        with patch.object(supervisor, '_delegate_to_agent') as mock_delegate:
            await supervisor._distribute_contexts(contexts)
            
            # Each agent should receive only its context
            assert mock_delegate.call_count == 2
            calls = mock_delegate.call_args_list
            
            for call in calls:
                agent_name = call[0][0]
                context = call[0][1]
                assert context == contexts.get(agent_name, {})

    @pytest.mark.asyncio
    async def test_context_size_monitoring(self, mock_llm_manager):
        """Test monitoring and reporting of context sizes."""
        agent = BaseAgent(mock_llm_manager, name="TestAgent")
        
        # Add various data to context
        agent.context = {
            "small": "x" * 100,
            "medium": "y" * 1000,
            "large": "z" * 10000
        }
        
        # Get context metrics
        metrics = agent._get_context_metrics()
        
        assert "total_size_bytes" in metrics
        assert "num_keys" in metrics
        assert "largest_key" in metrics
        assert metrics["num_keys"] == 3
        assert metrics["largest_key"] == "large"

    @pytest.mark.asyncio  
    async def test_parallel_agent_context_isolation(self, mock_llm_manager):
        """Test context isolation when agents run in parallel."""
        agents = [
            BaseAgent(mock_llm_manager, name=f"Agent{i}")
            for i in range(10)
        ]
        
        async def set_context(agent, value):
            """Set context for an agent."""
            agent.context = {"id": value, "data": f"data_{value}"}
            await asyncio.sleep(0.01)  # Simulate processing
            return agent.context
        
        # Run all agents in parallel
        tasks = [set_context(agent, i) for i, agent in enumerate(agents)]
        results = await asyncio.gather(*tasks)
        
        # Verify each agent maintained its own context
        for i, result in enumerate(results):
            assert result["id"] == i
            assert result["data"] == f"data_{i}"

    @pytest.mark.asyncio
    async def test_context_window_with_history(self, mock_llm_manager):
        """Test context window management with conversation history."""
        agent = TriageSubAgent(mock_llm_manager)
        
        # Build up conversation history
        history = []
        for i in range(1000):
            history.append({
                "role": "user",
                "content": f"Message {i} with some content that takes up space"
            })
        
        # Should handle large history gracefully
        context = {"conversation_history": history}
        processed = agent._prepare_context_for_llm(context, max_history=10)
        
        # Should keep only recent history
        assert len(processed.get("conversation_history", [])) <= 10

    @pytest.mark.asyncio
    async def test_context_overflow_error_handling(self, mock_llm_manager):
        """Test graceful handling of context overflow errors."""
        agent = BaseAgent(mock_llm_manager, name="TestAgent")
        
        # Simulate context overflow
        huge_context = {"data": "x" * 1000000}  # 1MB context
        
        with patch.object(agent, 'llm_manager') as mock_llm:
            mock_llm.generate.side_effect = Exception("Context length exceeded")
            
            # Should handle error gracefully
            result = await agent._execute_with_fallback(
                prompt="test",
                context=huge_context
            )
            
            assert result is not None
            assert "fallback" in result.lower() or "error" in result.lower()


class TestTokenCountingAndLimits:
    """Test token counting and limit enforcement."""

    @pytest.mark.asyncio
    async def test_max_tokens_enforcement(self):
        """Test that max_tokens parameter is enforced."""
        mock_llm = MagicMock(spec=LLMManager)
        agent = BaseAgent(mock_llm, name="TestAgent")
        
        # Configure max tokens
        max_tokens = 1000
        
        with patch.object(agent, 'llm_manager') as mock_manager:
            await agent._generate_with_limit("test prompt", max_tokens=max_tokens)
            
            # Verify max_tokens was passed to LLM
            mock_manager.generate.assert_called_once()
            call_args = mock_manager.generate.call_args
            assert call_args[1].get("max_tokens") == max_tokens

    @pytest.mark.asyncio
    async def test_dynamic_token_allocation(self):
        """Test dynamic token allocation based on context size."""
        mock_llm = MagicMock(spec=LLMManager)
        agent = DataSubAgent(mock_llm)
        
        # Small context should allow more output tokens
        small_context = {"data": "small"}
        output_tokens_small = agent._calculate_output_tokens(small_context)
        
        # Large context should reduce output tokens
        large_context = {"data": "x" * 100000}
        output_tokens_large = agent._calculate_output_tokens(large_context)
        
        assert output_tokens_small > output_tokens_large

    @pytest.mark.asyncio
    async def test_token_budget_tracking(self):
        """Test tracking of token usage against budget."""
        mock_llm = MagicMock(spec=LLMManager)
        agent = BaseAgent(mock_llm, name="TestAgent")
        
        # Set token budget
        agent.token_budget = 10000
        agent.tokens_used = 0
        
        # Simulate token usage
        prompts = ["prompt1", "prompt2", "prompt3"]
        for prompt in prompts:
            tokens = agent._estimate_token_count(prompt)
            agent.tokens_used += tokens
        
        # Check budget tracking
        assert agent.tokens_used > 0
        assert agent.tokens_used < agent.token_budget
        remaining = agent.token_budget - agent.tokens_used
        assert remaining > 0


class TestContextObservability:
    """Test context observability and metrics."""

    @pytest.mark.asyncio
    async def test_context_size_metrics_collection(self):
        """Test collection of context size metrics."""
        mock_llm = MagicMock(spec=LLMManager)
        agent = BaseAgent(mock_llm, name="TestAgent")
        
        # Add data to context
        agent.context = {
            "messages": ["msg1", "msg2", "msg3"],
            "metadata": {"key": "value"},
            "large_data": "x" * 5000
        }
        
        # Collect metrics
        metrics = agent._collect_context_metrics()
        
        assert "context_size_bytes" in metrics
        assert "context_keys" in metrics
        assert "timestamp" in metrics
        assert metrics["context_size_bytes"] > 5000

    @pytest.mark.asyncio
    async def test_context_metrics_reporting(self):
        """Test reporting of context metrics to monitoring system."""
        mock_llm = MagicMock(spec=LLMManager)
        agent = BaseAgent(mock_llm, name="TestAgent")
        
        with patch('netra_backend.app.agents.base_agent.metrics_collector') as mock_metrics:
            # Trigger metrics reporting
            agent._report_context_metrics()
            
            # Verify metrics were reported
            mock_metrics.record_metric.assert_called()
            calls = mock_metrics.record_metric.call_args_list
            
            # Check for expected metrics
            metric_names = [call[0][0] for call in calls]
            assert "agent_context_size" in metric_names
            assert "agent_context_keys" in metric_names

    @pytest.mark.asyncio
    async def test_context_overflow_alerting(self):
        """Test alerting when context approaches limits."""
        mock_llm = MagicMock(spec=LLMManager)
        agent = BaseAgent(mock_llm, name="TestAgent")
        
        # Set context near limit
        agent.context = {"data": "x" * 120000}  # Near 128k limit
        
        with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
            # Check context size
            is_near_limit = agent._check_context_limit_proximity()
            
            assert is_near_limit
            # Should log warning
            mock_logger.warning.assert_called()


class TestAgentContextIsolationFailures:
    """Test cases designed to fail and expose context isolation issues."""

    @pytest.mark.xfail(reason="Context window validation not implemented")
    @pytest.mark.asyncio
    async def test_missing_context_window_validation(self):
        """Test that context window validation is missing."""
        mock_llm = MagicMock(spec=LLMManager)
        agent = BaseAgent(mock_llm, name="TestAgent")
        
        # This should fail because validation is not implemented
        huge_prompt = "x" * 200000
        await agent._validate_context_window_size(huge_prompt)

    @pytest.mark.xfail(reason="Token counting not implemented")
    @pytest.mark.asyncio
    async def test_missing_token_counting(self):
        """Test that token counting is not implemented."""
        mock_llm = MagicMock(spec=LLMManager)
        agent = BaseAgent(mock_llm, name="TestAgent")
        
        # This should fail because method doesn't exist
        token_count = agent._estimate_token_count("test text")
        assert token_count > 0

    @pytest.mark.xfail(reason="Context metrics not implemented")
    @pytest.mark.asyncio
    async def test_missing_context_metrics(self):
        """Test that context metrics collection is missing."""
        mock_llm = MagicMock(spec=LLMManager)
        agent = BaseAgent(mock_llm, name="TestAgent")
        
        # This should fail because method doesn't exist
        metrics = agent._get_context_metrics()
        assert "total_size_bytes" in metrics

    @pytest.mark.xfail(reason="Context truncation not implemented")
    @pytest.mark.asyncio
    async def test_missing_context_truncation(self):
        """Test that context truncation is not implemented."""
        mock_llm = MagicMock(spec=LLMManager)
        agent = DataSubAgent(mock_llm)
        
        # This should fail because method doesn't exist
        large_context = {"data": "x" * 100000}
        truncated = agent._truncate_context_if_needed(large_context, max_size=1000)
        assert len(str(truncated)) <= 1000

    @pytest.mark.xfail(reason="Prompt size logging not implemented")
    @pytest.mark.asyncio
    async def test_missing_prompt_size_logging(self):
        """Test that prompt size logging exists but lacks detail."""
        mock_llm = MagicMock(spec=LLMManager)
        from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
        
        agent = ActionsToMeetGoalsSubAgent(mock_llm)
        
        # The method exists but only logs size in MB, not tokens
        prompt = "test " * 1000
        agent._log_prompt_size(prompt, "test_run")
        
        # Should log token count, not just MB
        with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
            agent._log_prompt_size_with_tokens(prompt, "test_run")
            mock_logger.info.assert_called_with(
                match=r".*tokens.*"  # Should mention tokens
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])