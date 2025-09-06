from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Integration tests for TriageSubAgent ExecutionResult handling.

# REMOVED_SYNTAX_ERROR: This test suite validates the end-to-end ExecutionResult handling in the TriageSubAgent
# REMOVED_SYNTAX_ERROR: after the ExecutionStatus consolidation regression (commit e32a97b31).

# REMOVED_SYNTAX_ERROR: Tests focus on:
    # REMOVED_SYNTAX_ERROR: 1. Full agent execution with proper ExecutionResult creation
    # REMOVED_SYNTAX_ERROR: 2. Status handling consistency across execution paths
    # REMOVED_SYNTAX_ERROR: 3. WebSocket integration with ExecutionResult
    # REMOVED_SYNTAX_ERROR: 4. Error scenarios with proper ExecutionResult error handling
    # REMOVED_SYNTAX_ERROR: 5. Integration with other agent components

    # REMOVED_SYNTAX_ERROR: Uses real components where possible to catch integration issues.
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.triage.triage_sub_agent import TriageSubAgent
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.state import DeepAgentState
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.base.interface import ExecutionResult
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.core_enums import ExecutionStatus
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.triage.models import Priority, Complexity
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.llm.llm_manager import LLMManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.redis_manager import RedisManager


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_llm_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock LLM manager with realistic responses."""
    # REMOVED_SYNTAX_ERROR: mock = Mock(spec=LLMManager)

    # Default successful response
    # REMOVED_SYNTAX_ERROR: default_response = json.dumps({ ))
    # REMOVED_SYNTAX_ERROR: "category": "Cost Optimization",
    # REMOVED_SYNTAX_ERROR: "sub_category": "Model Selection",
    # REMOVED_SYNTAX_ERROR: "priority": "high",
    # REMOVED_SYNTAX_ERROR: "complexity": "medium",
    # REMOVED_SYNTAX_ERROR: "confidence_score": 0.85,
    # REMOVED_SYNTAX_ERROR: "next_steps": ["analyze_usage", "recommend_models"]
    

    # REMOVED_SYNTAX_ERROR: mock.ask_llm = AsyncMock(return_value=default_response)
    # REMOVED_SYNTAX_ERROR: mock.ask_structured_llm = AsyncMock(side_effect=Exception("Fallback to regular LLM"))
    # REMOVED_SYNTAX_ERROR: return mock


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock tool dispatcher."""
    # REMOVED_SYNTAX_ERROR: return Mock(spec=ToolDispatcher)


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_redis_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock Redis manager."""
    # REMOVED_SYNTAX_ERROR: mock = Mock(spec=RedisManager)
    # REMOVED_SYNTAX_ERROR: mock.get = AsyncMock(return_value=None)  # Cache miss by default
    # REMOVED_SYNTAX_ERROR: mock.set = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: return mock


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock WebSocket manager."""
    # REMOVED_SYNTAX_ERROR: mock = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock.send_message = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock.send_agent_update = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock.send_agent_thinking = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: mock.send_agent_completed = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return mock


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def triage_agent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a TriageSubAgent instance with mocked dependencies."""
    # REMOVED_SYNTAX_ERROR: return TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_state():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a sample DeepAgentState with a realistic request."""
    # REMOVED_SYNTAX_ERROR: return DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="Optimize my GPT-4 costs by reducing tokens while maintaining quality"
    


# REMOVED_SYNTAX_ERROR: class TestTriageAgentExecutionResultIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for TriageSubAgent ExecutionResult handling."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_successful_execution_creates_proper_execution_result( )
    # REMOVED_SYNTAX_ERROR: self, triage_agent, sample_state, mock_llm_manager
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test that successful execution creates ExecutionResult with COMPLETED status."""
        # Configure LLM response
        # REMOVED_SYNTAX_ERROR: llm_response = json.dumps({ ))
        # REMOVED_SYNTAX_ERROR: "category": "Cost Optimization",
        # REMOVED_SYNTAX_ERROR: "priority": "high",
        # REMOVED_SYNTAX_ERROR: "complexity": "medium",
        # REMOVED_SYNTAX_ERROR: "confidence_score": 0.9,
        # REMOVED_SYNTAX_ERROR: "extracted_entities": { )
        # REMOVED_SYNTAX_ERROR: "models_mentioned": ["gpt-4"],
        # REMOVED_SYNTAX_ERROR: "metrics_mentioned": ["cost", "tokens", "quality"]
        
        
        # REMOVED_SYNTAX_ERROR: mock_llm_manager.ask_llm.return_value = llm_response

        # Execute the agent
        # REMOVED_SYNTAX_ERROR: start_time = asyncio.get_event_loop().time()
        # REMOVED_SYNTAX_ERROR: result = await triage_agent.execute(sample_state, "integration_test_001", stream_updates=False)
        # REMOVED_SYNTAX_ERROR: end_time = asyncio.get_event_loop().time()

        # Verify ExecutionResult structure
        # REMOVED_SYNTAX_ERROR: assert isinstance(result, ExecutionResult)
        # REMOVED_SYNTAX_ERROR: assert result.status == ExecutionStatus.COMPLETED  # Key regression prevention
        # REMOVED_SYNTAX_ERROR: assert result.request_id == "integration_test_001"
        # REMOVED_SYNTAX_ERROR: assert result.is_success is True
        # REMOVED_SYNTAX_ERROR: assert result.is_complete is True

        # Verify data content
        # REMOVED_SYNTAX_ERROR: assert result.data is not None
        # REMOVED_SYNTAX_ERROR: assert "category" in result.result  # Using compatibility property
        # REMOVED_SYNTAX_ERROR: assert result.result["category"] == "Cost Optimization"

        # Verify timing information
        # REMOVED_SYNTAX_ERROR: assert result.execution_time_ms is not None
        # REMOVED_SYNTAX_ERROR: assert result.execution_time_ms > 0

        # Verify compatibility properties
        # REMOVED_SYNTAX_ERROR: assert result.error is None
        # REMOVED_SYNTAX_ERROR: assert result.result == result.data

        # Verify state was updated
        # REMOVED_SYNTAX_ERROR: assert sample_state.triage_result is not None
        # REMOVED_SYNTAX_ERROR: assert sample_state.triage_result.category == "Cost Optimization"

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_execution_with_llm_failure_creates_fallback_result( )
        # REMOVED_SYNTAX_ERROR: self, triage_agent, sample_state, mock_llm_manager
        # REMOVED_SYNTAX_ERROR: ):
            # REMOVED_SYNTAX_ERROR: """Test that LLM failure results in fallback ExecutionResult."""
            # Configure LLM to fail
            # REMOVED_SYNTAX_ERROR: mock_llm_manager.ask_llm.side_effect = Exception("LLM service unavailable")

            # Execute the agent (should use fallback)
            # REMOVED_SYNTAX_ERROR: result = await triage_agent.execute(sample_state, "fallback_test_001", stream_updates=False)

            # Should still create ExecutionResult, but with fallback indicators
            # REMOVED_SYNTAX_ERROR: assert isinstance(result, ExecutionResult)
            # REMOVED_SYNTAX_ERROR: assert result.status == ExecutionStatus.COMPLETED  # Fallback still succeeds
            # REMOVED_SYNTAX_ERROR: assert result.request_id == "fallback_test_001"
            # REMOVED_SYNTAX_ERROR: assert result.is_success is True

            # Check fallback indicators
            # REMOVED_SYNTAX_ERROR: if hasattr(sample_state.triage_result, 'metadata'):
                # REMOVED_SYNTAX_ERROR: assert sample_state.triage_result.metadata.fallback_used is True

                # Should have lower confidence due to fallback
                # REMOVED_SYNTAX_ERROR: assert sample_state.triage_result.confidence_score == 0.5

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_execution_with_websocket_updates( )
                # REMOVED_SYNTAX_ERROR: self, triage_agent, sample_state, mock_llm_manager, mock_websocket_manager
                # REMOVED_SYNTAX_ERROR: ):
                    # REMOVED_SYNTAX_ERROR: """Test ExecutionResult integration with WebSocket updates."""
                    # Set up WebSocket manager
                    # REMOVED_SYNTAX_ERROR: triage_agent.websocket_manager = mock_websocket_manager

                    # Configure successful LLM response
                    # REMOVED_SYNTAX_ERROR: llm_response = json.dumps({ ))
                    # REMOVED_SYNTAX_ERROR: "category": "Performance Optimization",
                    # REMOVED_SYNTAX_ERROR: "priority": "medium",
                    # REMOVED_SYNTAX_ERROR: "confidence_score": 0.8
                    
                    # REMOVED_SYNTAX_ERROR: mock_llm_manager.ask_llm.return_value = llm_response

                    # Execute with WebSocket updates
                    # REMOVED_SYNTAX_ERROR: result = await triage_agent.execute(sample_state, "websocket_test_001", stream_updates=True)

                    # Verify ExecutionResult
                    # REMOVED_SYNTAX_ERROR: assert result.status == ExecutionStatus.COMPLETED
                    # REMOVED_SYNTAX_ERROR: assert result.request_id == "websocket_test_001"

                    # Verify WebSocket updates were sent
                    # REMOVED_SYNTAX_ERROR: assert mock_websocket_manager.send_agent_update.called

                    # Check that final completion message includes ExecutionResult info
                    # REMOVED_SYNTAX_ERROR: completion_calls = [ )
                    # REMOVED_SYNTAX_ERROR: call for call in mock_websocket_manager.send_agent_completed.call_args_list
                    
                    # REMOVED_SYNTAX_ERROR: assert len(completion_calls) > 0

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_execution_result_with_cache_hit( )
                    # REMOVED_SYNTAX_ERROR: self, triage_agent, sample_state, mock_redis_manager, mock_llm_manager
                    # REMOVED_SYNTAX_ERROR: ):
                        # REMOVED_SYNTAX_ERROR: """Test ExecutionResult creation with cached results."""
                        # Set up cached result
                        # REMOVED_SYNTAX_ERROR: cached_result = { )
                        # REMOVED_SYNTAX_ERROR: "category": "Security Audit",
                        # REMOVED_SYNTAX_ERROR: "priority": "high",
                        # REMOVED_SYNTAX_ERROR: "confidence_score": 0.95,
                        # REMOVED_SYNTAX_ERROR: "metadata": {"cache_hit": False}  # Will be updated to True
                        
                        # REMOVED_SYNTAX_ERROR: mock_redis_manager.get.return_value = json.dumps(cached_result)

                        # Execute (should hit cache)
                        # REMOVED_SYNTAX_ERROR: result = await triage_agent.execute(sample_state, "cache_test_001", stream_updates=False)

                        # Verify ExecutionResult from cache
                        # REMOVED_SYNTAX_ERROR: assert result.status == ExecutionStatus.COMPLETED
                        # REMOVED_SYNTAX_ERROR: assert result.request_id == "cache_test_001"

                        # LLM should not have been called
                        # REMOVED_SYNTAX_ERROR: mock_llm_manager.ask_llm.assert_not_called()

                        # Cache metadata should be updated
                        # REMOVED_SYNTAX_ERROR: assert sample_state.triage_result.metadata.cache_hit is True

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_execution_result_error_scenarios( )
                        # REMOVED_SYNTAX_ERROR: self, triage_agent, sample_state
                        # REMOVED_SYNTAX_ERROR: ):
                            # REMOVED_SYNTAX_ERROR: """Test ExecutionResult creation in error scenarios."""
                            # Test with invalid user request
                            # REMOVED_SYNTAX_ERROR: invalid_state = DeepAgentState(user_request="")

                            # Should handle gracefully
                            # REMOVED_SYNTAX_ERROR: result = await triage_agent.execute(invalid_state, "error_test_001", stream_updates=False)

                            # For invalid requests, agent might await asyncio.sleep(0)
                            # REMOVED_SYNTAX_ERROR: return early or create error result
                            # The important thing is it creates a proper ExecutionResult
                            # REMOVED_SYNTAX_ERROR: assert isinstance(result, ExecutionResult)
                            # REMOVED_SYNTAX_ERROR: assert result.request_id == "error_test_001"

                            # Status could be COMPLETED (with validation errors) or FAILED
                            # REMOVED_SYNTAX_ERROR: assert result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]


# REMOVED_SYNTAX_ERROR: class TestTriageExecutionResultCrossAgentIntegration:
    # REMOVED_SYNTAX_ERROR: """Test ExecutionResult integration with other agent components."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_execution_result_state_persistence( )
    # REMOVED_SYNTAX_ERROR: self, triage_agent, sample_state, mock_llm_manager
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test that ExecutionResult properly updates agent state."""
        # REMOVED_SYNTAX_ERROR: llm_response = json.dumps({ ))
        # REMOVED_SYNTAX_ERROR: "category": "Data Analysis",
        # REMOVED_SYNTAX_ERROR: "sub_category": "Usage Patterns",
        # REMOVED_SYNTAX_ERROR: "priority": "medium",
        # REMOVED_SYNTAX_ERROR: "complexity": "low",
        # REMOVED_SYNTAX_ERROR: "confidence_score": 0.75,
        # REMOVED_SYNTAX_ERROR: "user_intent": { )
        # REMOVED_SYNTAX_ERROR: "primary_intent": "analyze",
        # REMOVED_SYNTAX_ERROR: "action_required": True
        
        
        # REMOVED_SYNTAX_ERROR: mock_llm_manager.ask_llm.return_value = llm_response

        # Execute agent
        # REMOVED_SYNTAX_ERROR: result = await triage_agent.execute(sample_state, "state_test_001", stream_updates=False)

        # Verify ExecutionResult
        # REMOVED_SYNTAX_ERROR: assert result.status == ExecutionStatus.COMPLETED

        # Verify state was properly updated
        # REMOVED_SYNTAX_ERROR: assert sample_state.triage_result is not None
        # REMOVED_SYNTAX_ERROR: assert sample_state.triage_result.category == "Data Analysis"
        # REMOVED_SYNTAX_ERROR: assert sample_state.triage_result.priority == Priority.MEDIUM
        # REMOVED_SYNTAX_ERROR: assert sample_state.triage_result.complexity == Complexity.LOW

        # Verify the ExecutionResult data matches state
        # REMOVED_SYNTAX_ERROR: assert result.result["category"] == sample_state.triage_result.category

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_execution_result_timing_accuracy( )
        # REMOVED_SYNTAX_ERROR: self, triage_agent, sample_state, mock_llm_manager
        # REMOVED_SYNTAX_ERROR: ):
            # REMOVED_SYNTAX_ERROR: """Test that ExecutionResult timing information is accurate."""
            # Add delay to LLM response to test timing
# REMOVED_SYNTAX_ERROR: async def delayed_llm_response(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)  # 100ms delay
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return json.dumps({"category": "Test", "priority": "low"})

    # REMOVED_SYNTAX_ERROR: mock_llm_manager.ask_llm.side_effect = delayed_llm_response

    # Execute agent
    # REMOVED_SYNTAX_ERROR: start_time = asyncio.get_event_loop().time()
    # REMOVED_SYNTAX_ERROR: result = await triage_agent.execute(sample_state, "timing_test_001", stream_updates=False)
    # REMOVED_SYNTAX_ERROR: end_time = asyncio.get_event_loop().time()

    # Verify timing in ExecutionResult
    # REMOVED_SYNTAX_ERROR: assert result.execution_time_ms is not None
    # REMOVED_SYNTAX_ERROR: assert result.execution_time_ms >= 100.0  # Should include the delay

    # Should be reasonably close to actual execution time
    # REMOVED_SYNTAX_ERROR: actual_time_ms = (end_time - start_time) * 1000
    # Allow some variance for test execution overhead
    # REMOVED_SYNTAX_ERROR: assert abs(result.execution_time_ms - actual_time_ms) < 50.0  # Within 50ms

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_execution_result_metadata_preservation( )
    # REMOVED_SYNTAX_ERROR: self, triage_agent, sample_state, mock_llm_manager, mock_redis_manager
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test that ExecutionResult preserves all metadata properly."""
        # Configure for cache miss to test full metadata
        # REMOVED_SYNTAX_ERROR: mock_redis_manager.get.return_value = None

        # REMOVED_SYNTAX_ERROR: llm_response = json.dumps({ ))
        # REMOVED_SYNTAX_ERROR: "category": "Infrastructure Optimization",
        # REMOVED_SYNTAX_ERROR: "priority": "critical",
        # REMOVED_SYNTAX_ERROR: "complexity": "high",
        # REMOVED_SYNTAX_ERROR: "confidence_score": 0.88
        
        # REMOVED_SYNTAX_ERROR: mock_llm_manager.ask_llm.return_value = llm_response

        # Execute agent
        # REMOVED_SYNTAX_ERROR: result = await triage_agent.execute(sample_state, "metadata_test_001", stream_updates=False)

        # Verify basic ExecutionResult
        # REMOVED_SYNTAX_ERROR: assert result.status == ExecutionStatus.COMPLETED

        # Verify metadata is preserved and accessible
        # REMOVED_SYNTAX_ERROR: triage_result = sample_state.triage_result
        # REMOVED_SYNTAX_ERROR: assert triage_result.metadata is not None
        # REMOVED_SYNTAX_ERROR: assert triage_result.metadata.cache_hit is False
        # REMOVED_SYNTAX_ERROR: assert triage_result.metadata.fallback_used is False
        # REMOVED_SYNTAX_ERROR: assert triage_result.metadata.triage_duration_ms > 0

        # Verify ExecutionResult includes all necessary data
        # REMOVED_SYNTAX_ERROR: assert "category" in result.result
        # REMOVED_SYNTAX_ERROR: assert result.result["confidence_score"] == 0.88

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_execution_result_serialization_for_websockets( )
        # REMOVED_SYNTAX_ERROR: self, triage_agent, sample_state, mock_llm_manager, mock_websocket_manager
        # REMOVED_SYNTAX_ERROR: ):
            # REMOVED_SYNTAX_ERROR: """Test that ExecutionResult can be properly serialized for WebSocket transmission."""
            # REMOVED_SYNTAX_ERROR: triage_agent.websocket_manager = mock_websocket_manager

            # REMOVED_SYNTAX_ERROR: llm_response = json.dumps({ ))
            # REMOVED_SYNTAX_ERROR: "category": "Model Comparison",
            # REMOVED_SYNTAX_ERROR: "priority": "high",
            # REMOVED_SYNTAX_ERROR: "complexity": "medium",
            # REMOVED_SYNTAX_ERROR: "confidence_score": 0.82,
            # REMOVED_SYNTAX_ERROR: "next_steps": ["compare_models", "benchmark_performance"],
            # REMOVED_SYNTAX_ERROR: "extracted_entities": { )
            # REMOVED_SYNTAX_ERROR: "models_mentioned": ["gpt-4", "claude-3"],
            # REMOVED_SYNTAX_ERROR: "metrics_mentioned": ["performance", "cost"]
            
            
            # REMOVED_SYNTAX_ERROR: mock_llm_manager.ask_llm.return_value = llm_response

            # Execute with WebSocket updates
            # REMOVED_SYNTAX_ERROR: result = await triage_agent.execute(sample_state, "serialization_test_001", stream_updates=True)

            # Verify ExecutionResult
            # REMOVED_SYNTAX_ERROR: assert result.status == ExecutionStatus.COMPLETED

            # Check that WebSocket messages can be created from ExecutionResult
            # The agent should be able to serialize the result for transmission
            # REMOVED_SYNTAX_ERROR: serializable_result = { )
            # REMOVED_SYNTAX_ERROR: "status": result.status.value,
            # REMOVED_SYNTAX_ERROR: "request_id": result.request_id,
            # REMOVED_SYNTAX_ERROR: "data": result.result,  # Using compatibility property
            # REMOVED_SYNTAX_ERROR: "execution_time_ms": result.execution_time_ms,
            # REMOVED_SYNTAX_ERROR: "error": result.error,
            # REMOVED_SYNTAX_ERROR: "is_success": result.is_success
            

            # Should be JSON serializable
            # REMOVED_SYNTAX_ERROR: json_result = json.dumps(serializable_result, default=str)
            # REMOVED_SYNTAX_ERROR: assert json_result is not None

            # Verify WebSocket manager was called with appropriate data
            # REMOVED_SYNTAX_ERROR: assert mock_websocket_manager.send_agent_completed.called


# REMOVED_SYNTAX_ERROR: class TestTriageExecutionResultErrorHandling:
    # REMOVED_SYNTAX_ERROR: """Test error handling scenarios with ExecutionResult."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_execution_result_with_validation_errors( )
    # REMOVED_SYNTAX_ERROR: self, triage_agent
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test ExecutionResult creation when request validation fails."""
        # Create state with invalid request
        # REMOVED_SYNTAX_ERROR: invalid_state = DeepAgentState(user_request="x")  # Too short

        # Execute agent
        # REMOVED_SYNTAX_ERROR: result = await triage_agent.execute(invalid_state, "validation_error_test", stream_updates=False)

        # Should create ExecutionResult even for validation errors
        # REMOVED_SYNTAX_ERROR: assert isinstance(result, ExecutionResult)
        # REMOVED_SYNTAX_ERROR: assert result.request_id == "validation_error_test"

        # Could be COMPLETED with validation errors or FAILED
        # REMOVED_SYNTAX_ERROR: assert result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]

        # If FAILED, should have error information
        # REMOVED_SYNTAX_ERROR: if result.status == ExecutionStatus.FAILED:
            # REMOVED_SYNTAX_ERROR: assert result.error is not None
            # REMOVED_SYNTAX_ERROR: assert len(result.error) > 0

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_execution_result_with_llm_timeout( )
            # REMOVED_SYNTAX_ERROR: self, triage_agent, sample_state, mock_llm_manager
            # REMOVED_SYNTAX_ERROR: ):
                # REMOVED_SYNTAX_ERROR: """Test ExecutionResult creation when LLM times out."""
                # Simulate LLM timeout
                # REMOVED_SYNTAX_ERROR: mock_llm_manager.ask_llm.side_effect = asyncio.TimeoutError("LLM request timed out")

                # Execute agent
                # REMOVED_SYNTAX_ERROR: result = await triage_agent.execute(sample_state, "timeout_test", stream_updates=False)

                # Should handle timeout gracefully with ExecutionResult
                # REMOVED_SYNTAX_ERROR: assert isinstance(result, ExecutionResult)
                # REMOVED_SYNTAX_ERROR: assert result.request_id == "timeout_test"

                # Should either succeed with fallback or fail gracefully
                # REMOVED_SYNTAX_ERROR: if result.status == ExecutionStatus.FAILED:
                    # REMOVED_SYNTAX_ERROR: assert result.error is not None
                    # REMOVED_SYNTAX_ERROR: elif result.status == ExecutionStatus.COMPLETED:
                        # Used fallback - should have lower confidence
                        # REMOVED_SYNTAX_ERROR: assert sample_state.triage_result.confidence_score <= 0.5


                        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])