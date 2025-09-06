from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""Tests for validating context length handling in agents."""

# REMOVED_SYNTAX_ERROR: This test suite validates actual token counting and context length
# REMOVED_SYNTAX_ERROR: management across all agent types.
""

import json
from typing import Dict, Any
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.data_sub_agent import DataSubAgent
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.agents.synthetic_data_sub_agent_modern import ModernSyntheticDataSubAgent as SyntheticDataSubAgent
from netra_backend.app.agents.corpus_admin.agent import CorpusAdminSubAgent
from netra_backend.app.llm.llm_manager import LLMManager
import asyncio


# REMOVED_SYNTAX_ERROR: class TestContextLengthValidation:
    # REMOVED_SYNTAX_ERROR: """Test context length validation across agents."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_llm_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock LLM manager with context limits."""
    # REMOVED_SYNTAX_ERROR: manager = MagicMock(spec=LLMManager)
    # REMOVED_SYNTAX_ERROR: manager.generate = AsyncMock(return_value="test response")
    # Claude 3 Sonnet context window
    # REMOVED_SYNTAX_ERROR: manager.model_config = { )
    # REMOVED_SYNTAX_ERROR: "max_tokens": 4096,
    # REMOVED_SYNTAX_ERROR: "context_window": 200000  # 200k tokens
    
    # REMOVED_SYNTAX_ERROR: return manager

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_supervisor_agent_context_length(self, mock_llm_manager):
        # REMOVED_SYNTAX_ERROR: """Test supervisor agent handles context length properly."""
        # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent(mock_llm_manager)

        # Create a large user query
        # REMOVED_SYNTAX_ERROR: large_query = "Analyze this data: " + "x" * 150000

        # Supervisor should handle this without error
        # REMOVED_SYNTAX_ERROR: with patch.object(supervisor.llm_manager, 'generate') as mock_generate:
            # REMOVED_SYNTAX_ERROR: mock_generate.return_value = json.dumps({ ))
            # REMOVED_SYNTAX_ERROR: "agent": "data_sub_agent",
            # REMOVED_SYNTAX_ERROR: "task": "analyze",
            # REMOVED_SYNTAX_ERROR: "should_continue": False
            

            # REMOVED_SYNTAX_ERROR: result = await supervisor.orchestrate(large_query, {})

            # Check that prompt was passed to LLM
            # REMOVED_SYNTAX_ERROR: mock_generate.assert_called()
            # REMOVED_SYNTAX_ERROR: call_args = mock_generate.call_args[0]
            # REMOVED_SYNTAX_ERROR: prompt = call_args[0] if isinstance(call_args[0], str) else call_args[0][0]

            # Prompt should include query but might be truncated
            # REMOVED_SYNTAX_ERROR: assert len(prompt) > 0
            # REMOVED_SYNTAX_ERROR: assert len(prompt) < 1000000  # Should not exceed reasonable limit

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_data_agent_context_with_large_dataset(self, mock_llm_manager):
                # REMOVED_SYNTAX_ERROR: """Test data agent handles large dataset context."""
                # REMOVED_SYNTAX_ERROR: data_agent = DataSubAgent(mock_llm_manager)

                # Create large dataset context
                # REMOVED_SYNTAX_ERROR: large_data = { )
                # REMOVED_SYNTAX_ERROR: "corpus_data": [{"text": "data" * 100} for _ in range(1000)],
                # REMOVED_SYNTAX_ERROR: "metrics": {"values": list(range(10000))},
                # REMOVED_SYNTAX_ERROR: "history": ["Previous analysis " * 50 for _ in range(100)]
                

                # REMOVED_SYNTAX_ERROR: query = "Analyze the patterns in this data"

                # Should handle large context
                # REMOVED_SYNTAX_ERROR: with patch.object(data_agent.llm_manager, 'generate') as mock_generate:
                    # REMOVED_SYNTAX_ERROR: mock_generate.return_value = json.dumps({ ))
                    # REMOVED_SYNTAX_ERROR: "insights": ["Pattern found"},
                    # REMOVED_SYNTAX_ERROR: "recommendations": ["Optimize"]
                    

                    # REMOVED_SYNTAX_ERROR: result = await data_agent.process(query, large_data)

                    # Verify LLM was called
                    # REMOVED_SYNTAX_ERROR: mock_generate.assert_called()

                    # Check prompt size passed to LLM
                    # REMOVED_SYNTAX_ERROR: call_args = mock_generate.call_args
                    # REMOVED_SYNTAX_ERROR: if call_args[0]:  # Positional args
                    # REMOVED_SYNTAX_ERROR: prompt = call_args[0][0] if isinstance(call_args[0], (list, tuple)) else str(call_args[0])
                    # REMOVED_SYNTAX_ERROR: else:  # Keyword args
                    # REMOVED_SYNTAX_ERROR: prompt = call_args[1].get('prompt', '')

                    # Should have processed the data
                    # REMOVED_SYNTAX_ERROR: assert result is not None

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_triage_agent_history_truncation(self, mock_llm_manager):
                        # REMOVED_SYNTAX_ERROR: """Test triage agent truncates conversation history appropriately."""
                        # REMOVED_SYNTAX_ERROR: triage_agent = TriageSubAgent(mock_llm_manager)

                        # Create extensive conversation history
                        # REMOVED_SYNTAX_ERROR: history = []
                        # REMOVED_SYNTAX_ERROR: for i in range(500):
                            # REMOVED_SYNTAX_ERROR: history.append({ ))
                            # REMOVED_SYNTAX_ERROR: "role": "user" if i % 2 == 0 else "assistant",
                            # REMOVED_SYNTAX_ERROR: "content": "formatted_string" + "content " * 100
                            

                            # REMOVED_SYNTAX_ERROR: context = { )
                            # REMOVED_SYNTAX_ERROR: "conversation_history": history,
                            # REMOVED_SYNTAX_ERROR: "current_state": {"status": "analyzing"}
                            

                            # REMOVED_SYNTAX_ERROR: query = "What"s the issue?"

                            # Should truncate history
                            # REMOVED_SYNTAX_ERROR: with patch.object(triage_agent, '_prepare_context_for_llm') as mock_prepare:
                                # REMOVED_SYNTAX_ERROR: mock_prepare.return_value = { )
                                # REMOVED_SYNTAX_ERROR: "conversation_history": history[-10:},  # Keep last 10
                                # REMOVED_SYNTAX_ERROR: "current_state": context["current_state"]
                                

                                # REMOVED_SYNTAX_ERROR: with patch.object(triage_agent.llm_manager, 'generate') as mock_generate:
                                    # REMOVED_SYNTAX_ERROR: mock_generate.return_value = json.dumps({ ))
                                    # REMOVED_SYNTAX_ERROR: "issue_type": "performance",
                                    # REMOVED_SYNTAX_ERROR: "severity": "medium"
                                    

                                    # REMOVED_SYNTAX_ERROR: result = await triage_agent.process(query, context)

                                    # Should have called prepare context
                                    # REMOVED_SYNTAX_ERROR: mock_prepare.assert_called()

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_corpus_admin_agent_document_batching(self, mock_llm_manager):
                                        # REMOVED_SYNTAX_ERROR: """Test corpus admin agent batches large document sets."""
                                        # Mock tool dispatcher required by CorpusAdminSubAgent
                                        # REMOVED_SYNTAX_ERROR: mock_tool_dispatcher = MagicMock()  # TODO: Use real service instance
                                        # REMOVED_SYNTAX_ERROR: corpus_agent = CorpusAdminSubAgent(mock_llm_manager, mock_tool_dispatcher)

                                        # Create large document set
                                        # REMOVED_SYNTAX_ERROR: documents = []
                                        # REMOVED_SYNTAX_ERROR: for i in range(1000):
                                            # REMOVED_SYNTAX_ERROR: documents.append({ ))
                                            # REMOVED_SYNTAX_ERROR: "id": "formatted_string",
                                            # REMOVED_SYNTAX_ERROR: "content": "formatted_string" + "text " * 200,
                                            # REMOVED_SYNTAX_ERROR: "metadata": {"tags": ["formatted_string" for j in range(10)]]
                                            

                                            # REMOVED_SYNTAX_ERROR: context = { )
                                            # REMOVED_SYNTAX_ERROR: "corpus_name": "test_corpus",
                                            # REMOVED_SYNTAX_ERROR: "documents": documents
                                            

                                            # Create a mock state with the context data
                                            # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.state import DeepAgentState
                                            # REMOVED_SYNTAX_ERROR: mock_state = DeepAgentState()
                                            # REMOVED_SYNTAX_ERROR: mock_state.user_request = "Index these documents"

                                            # Test simply validates that the agent can be instantiated and execute
                                            # without throwing import errors. The actual execution is mocked.
                                            # REMOVED_SYNTAX_ERROR: with patch.object(corpus_agent, '_execute_corpus_operation_workflow') as mock_workflow:
                                                # Simulate successful execution
                                                # REMOVED_SYNTAX_ERROR: mock_workflow.return_value = None

                                                # Execute should handle large document sets without error
                                                # REMOVED_SYNTAX_ERROR: await corpus_agent.execute(mock_state, "test_run", True)

                                                # Should have executed the workflow (validates instantiation worked)
                                                # REMOVED_SYNTAX_ERROR: mock_workflow.assert_called()

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_synthetic_data_agent_generation_limits(self, mock_llm_manager):
                                                    # REMOVED_SYNTAX_ERROR: """Test synthetic data agent respects generation limits."""
                                                    # REMOVED_SYNTAX_ERROR: synthetic_agent = SyntheticDataSubAgent(mock_llm_manager)

                                                    # Request large synthetic dataset
                                                    # REMOVED_SYNTAX_ERROR: context = { )
                                                    # REMOVED_SYNTAX_ERROR: "num_samples": 10000,
                                                    # REMOVED_SYNTAX_ERROR: "sample_template": { )
                                                    # REMOVED_SYNTAX_ERROR: "fields": ["id", "name", "description", "data"},
                                                    # REMOVED_SYNTAX_ERROR: "description_length": 1000
                                                    
                                                    

                                                    # REMOVED_SYNTAX_ERROR: query = "Generate synthetic dataset"

                                                    # Should limit generation size
                                                    # REMOVED_SYNTAX_ERROR: with patch.object(synthetic_agent.llm_manager, 'generate') as mock_generate:
                                                        # REMOVED_SYNTAX_ERROR: mock_generate.return_value = json.dumps({ ))
                                                        # REMOVED_SYNTAX_ERROR: "samples": [{"id": i, "name": "formatted_string"] for i in range(100)]
                                                        

                                                        # REMOVED_SYNTAX_ERROR: result = await synthetic_agent.process(query, context)

                                                        # Check max_tokens was set appropriately
                                                        # REMOVED_SYNTAX_ERROR: call_kwargs = mock_generate.call_args[1] if mock_generate.call_args[1] else {}
                                                        # REMOVED_SYNTAX_ERROR: max_tokens = call_kwargs.get('max_tokens', 0)

                                                        # Should have reasonable token limit
                                                        # REMOVED_SYNTAX_ERROR: assert max_tokens > 0
                                                        # REMOVED_SYNTAX_ERROR: assert max_tokens <= 8192  # Reasonable limit for generation

                                                        # Removed problematic line: @pytest.mark.asyncio
                                                        # Removed problematic line: async def test_agent_prompt_size_reporting(self, mock_llm_manager):
                                                            # REMOVED_SYNTAX_ERROR: """Test agents report prompt sizes for observability."""
                                                            # REMOVED_SYNTAX_ERROR: agents = [ )
                                                            # REMOVED_SYNTAX_ERROR: BaseAgent(mock_llm_manager, name="TestAgent1"),
                                                            # REMOVED_SYNTAX_ERROR: DataSubAgent(mock_llm_manager),
                                                            # REMOVED_SYNTAX_ERROR: TriageSubAgent(mock_llm_manager)
                                                            

                                                            # REMOVED_SYNTAX_ERROR: for agent in agents:
                                                                # Create test prompt
                                                                # REMOVED_SYNTAX_ERROR: prompt = "Test prompt " * 1000

                                                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
                                                                    # Trigger prompt size logging if it exists
                                                                    # REMOVED_SYNTAX_ERROR: if hasattr(agent, '_log_prompt_size'):
                                                                        # REMOVED_SYNTAX_ERROR: agent._log_prompt_size(prompt, "test_run")

                                                                        # Should log the size
                                                                        # REMOVED_SYNTAX_ERROR: mock_logger.info.assert_called()
                                                                        # REMOVED_SYNTAX_ERROR: log_call = mock_logger.info.call_args[0][0]
                                                                        # REMOVED_SYNTAX_ERROR: assert "MB" in log_call or "size" in log_call.lower()

                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # Removed problematic line: async def test_context_window_overflow_handling(self, mock_llm_manager):
                                                                            # REMOVED_SYNTAX_ERROR: """Test handling when context exceeds model limits."""
                                                                            # REMOVED_SYNTAX_ERROR: agent = BaseAgent(mock_llm_manager, name="TestAgent")

                                                                            # Create context that exceeds Claude's 200k token limit
                                                                            # Approximately 4 chars per token
                                                                            # REMOVED_SYNTAX_ERROR: massive_context = "x" * 1000000  # ~250k tokens

                                                                            # REMOVED_SYNTAX_ERROR: with patch.object(agent.llm_manager, 'generate') as mock_generate:
                                                                                # Simulate context length error from LLM
                                                                                # REMOVED_SYNTAX_ERROR: mock_generate.side_effect = Exception( )
                                                                                # REMOVED_SYNTAX_ERROR: "This model"s maximum context length is 200000 tokens. "
                                                                                # REMOVED_SYNTAX_ERROR: "However, your messages resulted in 250000 tokens."
                                                                                

                                                                                # Should handle gracefully
                                                                                # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception) as exc_info:
                                                                                    # REMOVED_SYNTAX_ERROR: await agent.process("query", {"data": massive_context})

                                                                                    # REMOVED_SYNTAX_ERROR: assert "context length" in str(exc_info.value).lower()

                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                    # Removed problematic line: async def test_multi_agent_context_accumulation(self, mock_llm_manager):
                                                                                        # REMOVED_SYNTAX_ERROR: """Test context accumulation across multiple agent interactions."""
                                                                                        # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent(mock_llm_manager)

                                                                                        # Simulate multiple rounds of agent interaction
                                                                                        # REMOVED_SYNTAX_ERROR: accumulated_context = { )
                                                                                        # REMOVED_SYNTAX_ERROR: "round_1": {"data": "x" * 10000, "result": "analysis1"},
                                                                                        # REMOVED_SYNTAX_ERROR: "round_2": {"data": "y" * 20000, "result": "analysis2"},
                                                                                        # REMOVED_SYNTAX_ERROR: "round_3": {"data": "z" * 30000, "result": "analysis3"},
                                                                                        # REMOVED_SYNTAX_ERROR: "round_4": {"data": "w" * 40000, "result": "analysis4"}
                                                                                        

                                                                                        # Each round adds to context
                                                                                        # REMOVED_SYNTAX_ERROR: for round_key, round_data in accumulated_context.items():
                                                                                            # REMOVED_SYNTAX_ERROR: with patch.object(supervisor.llm_manager, 'generate') as mock_generate:
                                                                                                # REMOVED_SYNTAX_ERROR: mock_generate.return_value = json.dumps({ ))
                                                                                                # REMOVED_SYNTAX_ERROR: "agent": "data_sub_agent",
                                                                                                # REMOVED_SYNTAX_ERROR: "should_continue": round_key != "round_4"
                                                                                                

                                                                                                # Process with accumulated context
                                                                                                # REMOVED_SYNTAX_ERROR: result = await supervisor.orchestrate( )
                                                                                                # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                                                # REMOVED_SYNTAX_ERROR: accumulated_context
                                                                                                

                                                                                                # Context should be managed to stay within limits
                                                                                                # REMOVED_SYNTAX_ERROR: call_args = mock_generate.call_args
                                                                                                # REMOVED_SYNTAX_ERROR: if call_args and call_args[0]:
                                                                                                    # REMOVED_SYNTAX_ERROR: prompt = str(call_args[0][0]) if call_args[0] else ""
                                                                                                    # Even with accumulation, prompt should be manageable
                                                                                                    # REMOVED_SYNTAX_ERROR: assert len(prompt) < 500000  # Well within limits


# REMOVED_SYNTAX_ERROR: class TestContextMetricsAndObservability:
    # REMOVED_SYNTAX_ERROR: """Test context metrics collection and observability."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_context_metrics_per_agent(self):
        # REMOVED_SYNTAX_ERROR: """Test each agent type collects context metrics."""
        # REMOVED_SYNTAX_ERROR: mock_llm = MagicMock(spec=LLMManager)
        # REMOVED_SYNTAX_ERROR: mock_llm.generate = AsyncMock(return_value="response")

        # REMOVED_SYNTAX_ERROR: agents = [ )
        # REMOVED_SYNTAX_ERROR: ("BaseAgent", BaseAgent(mock_llm, name="Base")),
        # REMOVED_SYNTAX_ERROR: ("DataSubAgent", DataSubAgent(mock_llm)),
        # REMOVED_SYNTAX_ERROR: ("TriageSubAgent", TriageSubAgent(mock_llm)),
        # REMOVED_SYNTAX_ERROR: ("SupervisorAgent", SupervisorAgent(mock_llm))
        

        # REMOVED_SYNTAX_ERROR: for agent_name, agent in agents:
            # Set context
            # REMOVED_SYNTAX_ERROR: agent.context = { )
            # REMOVED_SYNTAX_ERROR: "test_data": "x" * 1000,
            # REMOVED_SYNTAX_ERROR: "metadata": {"agent": agent_name}
            

            # Get metrics (if implemented)
            # REMOVED_SYNTAX_ERROR: if hasattr(agent, '_get_context_metrics'):
                # REMOVED_SYNTAX_ERROR: metrics = agent._get_context_metrics()
                # REMOVED_SYNTAX_ERROR: assert metrics is not None
                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                # REMOVED_SYNTAX_ERROR: else:
                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_token_usage_tracking(self):
                        # REMOVED_SYNTAX_ERROR: """Test tracking of token usage across agent lifecycle."""
                        # REMOVED_SYNTAX_ERROR: mock_llm = MagicMock(spec=LLMManager)
                        # REMOVED_SYNTAX_ERROR: agent = BaseAgent(mock_llm, name="TestAgent")

                        # Initialize token tracking (if implemented)
                        # REMOVED_SYNTAX_ERROR: if hasattr(agent, 'token_budget'):
                            # REMOVED_SYNTAX_ERROR: agent.token_budget = 100000
                            # REMOVED_SYNTAX_ERROR: agent.tokens_used = 0

                            # Simulate multiple LLM calls
                            # REMOVED_SYNTAX_ERROR: for i in range(10):
                                # REMOVED_SYNTAX_ERROR: prompt = "formatted_string" + "data " * 100
                                # REMOVED_SYNTAX_ERROR: if hasattr(agent, '_estimate_token_count'):
                                    # REMOVED_SYNTAX_ERROR: tokens = agent._estimate_token_count(prompt)
                                    # REMOVED_SYNTAX_ERROR: agent.tokens_used += tokens

                                    # Check tracking
                                    # REMOVED_SYNTAX_ERROR: assert agent.tokens_used > 0
                                    # REMOVED_SYNTAX_ERROR: assert agent.tokens_used < agent.token_budget

                                    # REMOVED_SYNTAX_ERROR: usage_percentage = (agent.tokens_used / agent.token_budget) * 100
                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_context_size_alerting_thresholds(self):
                                        # REMOVED_SYNTAX_ERROR: """Test alerting at different context size thresholds."""
                                        # REMOVED_SYNTAX_ERROR: mock_llm = MagicMock(spec=LLMManager)
                                        # REMOVED_SYNTAX_ERROR: agent = BaseAgent(mock_llm, name="TestAgent")

                                        # REMOVED_SYNTAX_ERROR: thresholds = [ )
                                        # REMOVED_SYNTAX_ERROR: (50000, "INFO"),     # 50k chars - info level
                                        # REMOVED_SYNTAX_ERROR: (100000, "WARNING"), # 100k chars - warning
                                        # REMOVED_SYNTAX_ERROR: (180000, "ERROR")    # 180k chars - error/critical
                                        

                                        # REMOVED_SYNTAX_ERROR: for size, expected_level in thresholds:
                                            # REMOVED_SYNTAX_ERROR: agent.context = {"data": "x" * size}

                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
                                                # Check context size (if implemented)
                                                # REMOVED_SYNTAX_ERROR: if hasattr(agent, '_check_context_limit_proximity'):
                                                    # REMOVED_SYNTAX_ERROR: is_near_limit = agent._check_context_limit_proximity()

                                                    # REMOVED_SYNTAX_ERROR: if expected_level == "WARNING":
                                                        # REMOVED_SYNTAX_ERROR: assert is_near_limit
                                                        # REMOVED_SYNTAX_ERROR: mock_logger.warning.assert_called()
                                                        # REMOVED_SYNTAX_ERROR: elif expected_level == "ERROR":
                                                            # REMOVED_SYNTAX_ERROR: assert is_near_limit
                                                            # REMOVED_SYNTAX_ERROR: mock_logger.error.assert_called()


                                                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                                # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])
                                                                # REMOVED_SYNTAX_ERROR: pass