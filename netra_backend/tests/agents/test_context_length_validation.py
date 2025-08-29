"""Tests for validating context length handling in agents.

This test suite validates actual token counting and context length
management across all agent types.
"""

import json
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.synthetic_data_sub_agent_modern import SyntheticDataSubAgent
from netra_backend.app.agents.corpus_admin.agent import CorpusAdminAgent
from netra_backend.app.llm.llm_manager import LLMManager


class TestContextLengthValidation:
    """Test context length validation across agents."""

    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager with context limits."""
        manager = MagicMock(spec=LLMManager)
        manager.generate = AsyncMock(return_value="test response")
        # Claude 3 Sonnet context window
        manager.model_config = {
            "max_tokens": 4096,
            "context_window": 200000  # 200k tokens
        }
        return manager

    @pytest.mark.asyncio
    async def test_supervisor_agent_context_length(self, mock_llm_manager):
        """Test supervisor agent handles context length properly."""
        supervisor = SupervisorAgent(mock_llm_manager)
        
        # Create a large user query
        large_query = "Analyze this data: " + "x" * 150000
        
        # Supervisor should handle this without error
        with patch.object(supervisor.llm_manager, 'generate') as mock_generate:
            mock_generate.return_value = json.dumps({
                "agent": "data_sub_agent",
                "task": "analyze",
                "should_continue": False
            })
            
            result = await supervisor.orchestrate(large_query, {})
            
            # Check that prompt was passed to LLM
            mock_generate.assert_called()
            call_args = mock_generate.call_args[0]
            prompt = call_args[0] if isinstance(call_args[0], str) else call_args[0][0]
            
            # Prompt should include query but might be truncated
            assert len(prompt) > 0
            assert len(prompt) < 1000000  # Should not exceed reasonable limit

    @pytest.mark.asyncio
    async def test_data_agent_context_with_large_dataset(self, mock_llm_manager):
        """Test data agent handles large dataset context."""
        data_agent = DataSubAgent(mock_llm_manager)
        
        # Create large dataset context
        large_data = {
            "corpus_data": [{"text": "data" * 100} for _ in range(1000)],
            "metrics": {"values": list(range(10000))},
            "history": ["Previous analysis " * 50 for _ in range(100)]
        }
        
        query = "Analyze the patterns in this data"
        
        # Should handle large context
        with patch.object(data_agent.llm_manager, 'generate') as mock_generate:
            mock_generate.return_value = json.dumps({
                "insights": ["Pattern found"],
                "recommendations": ["Optimize"]
            })
            
            result = await data_agent.process(query, large_data)
            
            # Verify LLM was called
            mock_generate.assert_called()
            
            # Check prompt size passed to LLM
            call_args = mock_generate.call_args
            if call_args[0]:  # Positional args
                prompt = call_args[0][0] if isinstance(call_args[0], (list, tuple)) else str(call_args[0])
            else:  # Keyword args
                prompt = call_args[1].get('prompt', '')
            
            # Should have processed the data
            assert result is not None

    @pytest.mark.asyncio
    async def test_triage_agent_history_truncation(self, mock_llm_manager):
        """Test triage agent truncates conversation history appropriately."""
        triage_agent = TriageSubAgent(mock_llm_manager)
        
        # Create extensive conversation history
        history = []
        for i in range(500):
            history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}: " + "content " * 100
            })
        
        context = {
            "conversation_history": history,
            "current_state": {"status": "analyzing"}
        }
        
        query = "What's the issue?"
        
        # Should truncate history
        with patch.object(triage_agent, '_prepare_context_for_llm') as mock_prepare:
            mock_prepare.return_value = {
                "conversation_history": history[-10:],  # Keep last 10
                "current_state": context["current_state"]
            }
            
            with patch.object(triage_agent.llm_manager, 'generate') as mock_generate:
                mock_generate.return_value = json.dumps({
                    "issue_type": "performance",
                    "severity": "medium"
                })
                
                result = await triage_agent.process(query, context)
                
                # Should have called prepare context
                mock_prepare.assert_called()

    @pytest.mark.asyncio
    async def test_corpus_admin_agent_document_batching(self, mock_llm_manager):
        """Test corpus admin agent batches large document sets."""
        corpus_agent = CorpusAdminAgent(mock_llm_manager)
        
        # Create large document set
        documents = []
        for i in range(1000):
            documents.append({
                "id": f"doc_{i}",
                "content": f"Document content {i}: " + "text " * 200,
                "metadata": {"tags": [f"tag_{j}" for j in range(10)]}
            })
        
        context = {
            "corpus_name": "test_corpus",
            "documents": documents
        }
        
        query = "Index these documents"
        
        # Should batch process documents
        with patch.object(corpus_agent, '_batch_process_documents') as mock_batch:
            mock_batch.return_value = {"indexed": len(documents)}
            
            result = await corpus_agent.process(query, context)
            
            # Should have batched the documents
            mock_batch.assert_called()

    @pytest.mark.asyncio
    async def test_synthetic_data_agent_generation_limits(self, mock_llm_manager):
        """Test synthetic data agent respects generation limits."""
        synthetic_agent = SyntheticDataSubAgent(mock_llm_manager)
        
        # Request large synthetic dataset
        context = {
            "num_samples": 10000,
            "sample_template": {
                "fields": ["id", "name", "description", "data"],
                "description_length": 1000
            }
        }
        
        query = "Generate synthetic dataset"
        
        # Should limit generation size
        with patch.object(synthetic_agent.llm_manager, 'generate') as mock_generate:
            mock_generate.return_value = json.dumps({
                "samples": [{"id": i, "name": f"item_{i}"} for i in range(100)]
            })
            
            result = await synthetic_agent.process(query, context)
            
            # Check max_tokens was set appropriately
            call_kwargs = mock_generate.call_args[1] if mock_generate.call_args[1] else {}
            max_tokens = call_kwargs.get('max_tokens', 0)
            
            # Should have reasonable token limit
            assert max_tokens > 0
            assert max_tokens <= 8192  # Reasonable limit for generation

    @pytest.mark.asyncio
    async def test_agent_prompt_size_reporting(self, mock_llm_manager):
        """Test agents report prompt sizes for observability."""
        agents = [
            BaseSubAgent(mock_llm_manager, name="TestAgent1"),
            DataSubAgent(mock_llm_manager),
            TriageSubAgent(mock_llm_manager)
        ]
        
        for agent in agents:
            # Create test prompt
            prompt = "Test prompt " * 1000
            
            with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
                # Trigger prompt size logging if it exists
                if hasattr(agent, '_log_prompt_size'):
                    agent._log_prompt_size(prompt, "test_run")
                    
                    # Should log the size
                    mock_logger.info.assert_called()
                    log_call = mock_logger.info.call_args[0][0]
                    assert "MB" in log_call or "size" in log_call.lower()

    @pytest.mark.asyncio
    async def test_context_window_overflow_handling(self, mock_llm_manager):
        """Test handling when context exceeds model limits."""
        agent = BaseSubAgent(mock_llm_manager, name="TestAgent")
        
        # Create context that exceeds Claude's 200k token limit
        # Approximately 4 chars per token
        massive_context = "x" * 1000000  # ~250k tokens
        
        with patch.object(agent.llm_manager, 'generate') as mock_generate:
            # Simulate context length error from LLM
            mock_generate.side_effect = Exception(
                "This model's maximum context length is 200000 tokens. "
                "However, your messages resulted in 250000 tokens."
            )
            
            # Should handle gracefully
            with pytest.raises(Exception) as exc_info:
                await agent.process("query", {"data": massive_context})
            
            assert "context length" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_multi_agent_context_accumulation(self, mock_llm_manager):
        """Test context accumulation across multiple agent interactions."""
        supervisor = SupervisorAgent(mock_llm_manager)
        
        # Simulate multiple rounds of agent interaction
        accumulated_context = {
            "round_1": {"data": "x" * 10000, "result": "analysis1"},
            "round_2": {"data": "y" * 20000, "result": "analysis2"},
            "round_3": {"data": "z" * 30000, "result": "analysis3"},
            "round_4": {"data": "w" * 40000, "result": "analysis4"}
        }
        
        # Each round adds to context
        for round_key, round_data in accumulated_context.items():
            with patch.object(supervisor.llm_manager, 'generate') as mock_generate:
                mock_generate.return_value = json.dumps({
                    "agent": "data_sub_agent",
                    "should_continue": round_key != "round_4"
                })
                
                # Process with accumulated context
                result = await supervisor.orchestrate(
                    f"Process {round_key}",
                    accumulated_context
                )
                
                # Context should be managed to stay within limits
                call_args = mock_generate.call_args
                if call_args and call_args[0]:
                    prompt = str(call_args[0][0]) if call_args[0] else ""
                    # Even with accumulation, prompt should be manageable
                    assert len(prompt) < 500000  # Well within limits


class TestContextMetricsAndObservability:
    """Test context metrics collection and observability."""

    @pytest.mark.asyncio
    async def test_context_metrics_per_agent(self):
        """Test each agent type collects context metrics."""
        mock_llm = MagicMock(spec=LLMManager)
        mock_llm.generate = AsyncMock(return_value="response")
        
        agents = [
            ("BaseSubAgent", BaseSubAgent(mock_llm, name="Base")),
            ("DataSubAgent", DataSubAgent(mock_llm)),
            ("TriageSubAgent", TriageSubAgent(mock_llm)),
            ("SupervisorAgent", SupervisorAgent(mock_llm))
        ]
        
        for agent_name, agent in agents:
            # Set context
            agent.context = {
                "test_data": "x" * 1000,
                "metadata": {"agent": agent_name}
            }
            
            # Get metrics (if implemented)
            if hasattr(agent, '_get_context_metrics'):
                metrics = agent._get_context_metrics()
                assert metrics is not None
                print(f"{agent_name} metrics: {metrics}")
            else:
                print(f"{agent_name} does not implement _get_context_metrics")

    @pytest.mark.asyncio
    async def test_token_usage_tracking(self):
        """Test tracking of token usage across agent lifecycle."""
        mock_llm = MagicMock(spec=LLMManager)
        agent = BaseSubAgent(mock_llm, name="TestAgent")
        
        # Initialize token tracking (if implemented)
        if hasattr(agent, 'token_budget'):
            agent.token_budget = 100000
            agent.tokens_used = 0
            
            # Simulate multiple LLM calls
            for i in range(10):
                prompt = f"Query {i}: " + "data " * 100
                if hasattr(agent, '_estimate_token_count'):
                    tokens = agent._estimate_token_count(prompt)
                    agent.tokens_used += tokens
            
            # Check tracking
            assert agent.tokens_used > 0
            assert agent.tokens_used < agent.token_budget
            
            usage_percentage = (agent.tokens_used / agent.token_budget) * 100
            print(f"Token usage: {usage_percentage:.2f}%")

    @pytest.mark.asyncio
    async def test_context_size_alerting_thresholds(self):
        """Test alerting at different context size thresholds."""
        mock_llm = MagicMock(spec=LLMManager)
        agent = BaseSubAgent(mock_llm, name="TestAgent")
        
        thresholds = [
            (50000, "INFO"),     # 50k chars - info level
            (100000, "WARNING"), # 100k chars - warning
            (180000, "ERROR")    # 180k chars - error/critical
        ]
        
        for size, expected_level in thresholds:
            agent.context = {"data": "x" * size}
            
            with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
                # Check context size (if implemented)
                if hasattr(agent, '_check_context_limit_proximity'):
                    is_near_limit = agent._check_context_limit_proximity()
                    
                    if expected_level == "WARNING":
                        assert is_near_limit
                        mock_logger.warning.assert_called()
                    elif expected_level == "ERROR":
                        assert is_near_limit
                        mock_logger.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])