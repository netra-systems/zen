"""
Integration tests for TriageSubAgent ExecutionResult handling.

This test suite validates the end-to-end ExecutionResult handling in the TriageSubAgent
after the ExecutionStatus consolidation regression (commit e32a97b31). 

Tests focus on:
1. Full agent execution with proper ExecutionResult creation
2. Status handling consistency across execution paths
3. WebSocket integration with ExecutionResult
4. Error scenarios with proper ExecutionResult error handling
5. Integration with other agent components

Uses real components where possible to catch integration issues.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from netra_backend.app.agents.triage.triage_sub_agent import TriageSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.base.interface import ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.triage.models import Priority, Complexity
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.redis_manager import RedisManager


@pytest.fixture
def mock_llm_manager():
    """Create a mock LLM manager with realistic responses."""
    mock = Mock(spec=LLMManager)
    
    # Default successful response
    default_response = json.dumps({
        "category": "Cost Optimization",
        "sub_category": "Model Selection",
        "priority": "high",
        "complexity": "medium",
        "confidence_score": 0.85,
        "next_steps": ["analyze_usage", "recommend_models"]
    })
    
    mock.ask_llm = AsyncMock(return_value=default_response)
    mock.ask_structured_llm = AsyncMock(side_effect=Exception("Fallback to regular LLM"))
    return mock


@pytest.fixture
def mock_tool_dispatcher():
    """Create a mock tool dispatcher."""
    return Mock(spec=ToolDispatcher)


@pytest.fixture
def mock_redis_manager():
    """Create a mock Redis manager."""
    mock = Mock(spec=RedisManager)
    mock.get = AsyncMock(return_value=None)  # Cache miss by default
    mock.set = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_websocket_manager():
    """Create a mock WebSocket manager."""
    mock = AsyncMock()
    mock.send_message = AsyncMock()
    mock.send_agent_update = AsyncMock()
    mock.send_agent_thinking = AsyncMock()
    mock.send_agent_completed = AsyncMock()
    return mock


@pytest.fixture
def triage_agent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
    """Create a TriageSubAgent instance with mocked dependencies."""
    return TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)


@pytest.fixture
def sample_state():
    """Create a sample DeepAgentState with a realistic request."""
    return DeepAgentState(
        user_request="Optimize my GPT-4 costs by reducing tokens while maintaining quality"
    )


class TestTriageAgentExecutionResultIntegration:
    """Integration tests for TriageSubAgent ExecutionResult handling."""
    
    @pytest.mark.asyncio
    async def test_successful_execution_creates_proper_execution_result(
        self, triage_agent, sample_state, mock_llm_manager
    ):
        """Test that successful execution creates ExecutionResult with COMPLETED status."""
        # Configure LLM response
        llm_response = json.dumps({
            "category": "Cost Optimization",
            "priority": "high", 
            "complexity": "medium",
            "confidence_score": 0.9,
            "extracted_entities": {
                "models_mentioned": ["gpt-4"],
                "metrics_mentioned": ["cost", "tokens", "quality"]
            }
        })
        mock_llm_manager.ask_llm.return_value = llm_response
        
        # Execute the agent
        start_time = asyncio.get_event_loop().time()
        result = await triage_agent.execute(sample_state, "integration_test_001", stream_updates=False)
        end_time = asyncio.get_event_loop().time()
        
        # Verify ExecutionResult structure
        assert isinstance(result, ExecutionResult)
        assert result.status == ExecutionStatus.COMPLETED  # Key regression prevention
        assert result.request_id == "integration_test_001"
        assert result.is_success is True
        assert result.is_complete is True
        
        # Verify data content
        assert result.data is not None
        assert "category" in result.result  # Using compatibility property
        assert result.result["category"] == "Cost Optimization"
        
        # Verify timing information
        assert result.execution_time_ms is not None
        assert result.execution_time_ms > 0
        
        # Verify compatibility properties
        assert result.error is None
        assert result.result == result.data
        
        # Verify state was updated
        assert sample_state.triage_result is not None
        assert sample_state.triage_result.category == "Cost Optimization"
    
    @pytest.mark.asyncio
    async def test_execution_with_llm_failure_creates_fallback_result(
        self, triage_agent, sample_state, mock_llm_manager
    ):
        """Test that LLM failure results in fallback ExecutionResult."""
        # Configure LLM to fail
        mock_llm_manager.ask_llm.side_effect = Exception("LLM service unavailable")
        
        # Execute the agent (should use fallback)
        result = await triage_agent.execute(sample_state, "fallback_test_001", stream_updates=False)
        
        # Should still create ExecutionResult, but with fallback indicators
        assert isinstance(result, ExecutionResult)
        assert result.status == ExecutionStatus.COMPLETED  # Fallback still succeeds
        assert result.request_id == "fallback_test_001"
        assert result.is_success is True
        
        # Check fallback indicators
        if hasattr(sample_state.triage_result, 'metadata'):
            assert sample_state.triage_result.metadata.fallback_used is True
        
        # Should have lower confidence due to fallback
        assert sample_state.triage_result.confidence_score == 0.5
    
    @pytest.mark.asyncio
    async def test_execution_with_websocket_updates(
        self, triage_agent, sample_state, mock_llm_manager, mock_websocket_manager
    ):
        """Test ExecutionResult integration with WebSocket updates."""
        # Set up WebSocket manager
        triage_agent.websocket_manager = mock_websocket_manager
        
        # Configure successful LLM response
        llm_response = json.dumps({
            "category": "Performance Optimization",
            "priority": "medium",
            "confidence_score": 0.8
        })
        mock_llm_manager.ask_llm.return_value = llm_response
        
        # Execute with WebSocket updates
        result = await triage_agent.execute(sample_state, "websocket_test_001", stream_updates=True)
        
        # Verify ExecutionResult
        assert result.status == ExecutionStatus.COMPLETED
        assert result.request_id == "websocket_test_001"
        
        # Verify WebSocket updates were sent
        assert mock_websocket_manager.send_agent_update.called
        
        # Check that final completion message includes ExecutionResult info
        completion_calls = [
            call for call in mock_websocket_manager.send_agent_completed.call_args_list
        ]
        assert len(completion_calls) > 0
    
    @pytest.mark.asyncio
    async def test_execution_result_with_cache_hit(
        self, triage_agent, sample_state, mock_redis_manager, mock_llm_manager
    ):
        """Test ExecutionResult creation with cached results."""
        # Set up cached result
        cached_result = {
            "category": "Security Audit",
            "priority": "high",
            "confidence_score": 0.95,
            "metadata": {"cache_hit": False}  # Will be updated to True
        }
        mock_redis_manager.get.return_value = json.dumps(cached_result)
        
        # Execute (should hit cache)
        result = await triage_agent.execute(sample_state, "cache_test_001", stream_updates=False)
        
        # Verify ExecutionResult from cache
        assert result.status == ExecutionStatus.COMPLETED
        assert result.request_id == "cache_test_001"
        
        # LLM should not have been called
        mock_llm_manager.ask_llm.assert_not_called()
        
        # Cache metadata should be updated
        assert sample_state.triage_result.metadata.cache_hit is True
    
    @pytest.mark.asyncio
    async def test_execution_result_error_scenarios(
        self, triage_agent, sample_state
    ):
        """Test ExecutionResult creation in error scenarios."""
        # Test with invalid user request
        invalid_state = DeepAgentState(user_request="")
        
        # Should handle gracefully
        result = await triage_agent.execute(invalid_state, "error_test_001", stream_updates=False)
        
        # For invalid requests, agent might return early or create error result
        # The important thing is it creates a proper ExecutionResult
        assert isinstance(result, ExecutionResult)
        assert result.request_id == "error_test_001"
        
        # Status could be COMPLETED (with validation errors) or FAILED
        assert result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]


class TestTriageExecutionResultCrossAgentIntegration:
    """Test ExecutionResult integration with other agent components."""
    
    @pytest.mark.asyncio
    async def test_execution_result_state_persistence(
        self, triage_agent, sample_state, mock_llm_manager
    ):
        """Test that ExecutionResult properly updates agent state."""
        llm_response = json.dumps({
            "category": "Data Analysis",
            "sub_category": "Usage Patterns", 
            "priority": "medium",
            "complexity": "low",
            "confidence_score": 0.75,
            "user_intent": {
                "primary_intent": "analyze",
                "action_required": True
            }
        })
        mock_llm_manager.ask_llm.return_value = llm_response
        
        # Execute agent
        result = await triage_agent.execute(sample_state, "state_test_001", stream_updates=False)
        
        # Verify ExecutionResult
        assert result.status == ExecutionStatus.COMPLETED
        
        # Verify state was properly updated
        assert sample_state.triage_result is not None
        assert sample_state.triage_result.category == "Data Analysis"
        assert sample_state.triage_result.priority == Priority.MEDIUM
        assert sample_state.triage_result.complexity == Complexity.LOW
        
        # Verify the ExecutionResult data matches state
        assert result.result["category"] == sample_state.triage_result.category
    
    @pytest.mark.asyncio
    async def test_execution_result_timing_accuracy(
        self, triage_agent, sample_state, mock_llm_manager
    ):
        """Test that ExecutionResult timing information is accurate."""
        # Add delay to LLM response to test timing
        async def delayed_llm_response(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return json.dumps({"category": "Test", "priority": "low"})
        
        mock_llm_manager.ask_llm.side_effect = delayed_llm_response
        
        # Execute agent
        start_time = asyncio.get_event_loop().time()
        result = await triage_agent.execute(sample_state, "timing_test_001", stream_updates=False)
        end_time = asyncio.get_event_loop().time()
        
        # Verify timing in ExecutionResult
        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 100.0  # Should include the delay
        
        # Should be reasonably close to actual execution time
        actual_time_ms = (end_time - start_time) * 1000
        # Allow some variance for test execution overhead
        assert abs(result.execution_time_ms - actual_time_ms) < 50.0  # Within 50ms
    
    @pytest.mark.asyncio
    async def test_execution_result_metadata_preservation(
        self, triage_agent, sample_state, mock_llm_manager, mock_redis_manager
    ):
        """Test that ExecutionResult preserves all metadata properly."""
        # Configure for cache miss to test full metadata
        mock_redis_manager.get.return_value = None
        
        llm_response = json.dumps({
            "category": "Infrastructure Optimization",
            "priority": "critical", 
            "complexity": "high",
            "confidence_score": 0.88
        })
        mock_llm_manager.ask_llm.return_value = llm_response
        
        # Execute agent
        result = await triage_agent.execute(sample_state, "metadata_test_001", stream_updates=False)
        
        # Verify basic ExecutionResult
        assert result.status == ExecutionStatus.COMPLETED
        
        # Verify metadata is preserved and accessible
        triage_result = sample_state.triage_result
        assert triage_result.metadata is not None
        assert triage_result.metadata.cache_hit is False
        assert triage_result.metadata.fallback_used is False
        assert triage_result.metadata.triage_duration_ms > 0
        
        # Verify ExecutionResult includes all necessary data
        assert "category" in result.result
        assert result.result["confidence_score"] == 0.88
    
    @pytest.mark.asyncio 
    async def test_execution_result_serialization_for_websockets(
        self, triage_agent, sample_state, mock_llm_manager, mock_websocket_manager
    ):
        """Test that ExecutionResult can be properly serialized for WebSocket transmission."""
        triage_agent.websocket_manager = mock_websocket_manager
        
        llm_response = json.dumps({
            "category": "Model Comparison",
            "priority": "high",
            "complexity": "medium", 
            "confidence_score": 0.82,
            "next_steps": ["compare_models", "benchmark_performance"],
            "extracted_entities": {
                "models_mentioned": ["gpt-4", "claude-3"],
                "metrics_mentioned": ["performance", "cost"]
            }
        })
        mock_llm_manager.ask_llm.return_value = llm_response
        
        # Execute with WebSocket updates
        result = await triage_agent.execute(sample_state, "serialization_test_001", stream_updates=True)
        
        # Verify ExecutionResult
        assert result.status == ExecutionStatus.COMPLETED
        
        # Check that WebSocket messages can be created from ExecutionResult
        # The agent should be able to serialize the result for transmission
        serializable_result = {
            "status": result.status.value,
            "request_id": result.request_id,
            "data": result.result,  # Using compatibility property
            "execution_time_ms": result.execution_time_ms,
            "error": result.error,
            "is_success": result.is_success
        }
        
        # Should be JSON serializable
        json_result = json.dumps(serializable_result, default=str)
        assert json_result is not None
        
        # Verify WebSocket manager was called with appropriate data
        assert mock_websocket_manager.send_agent_completed.called


class TestTriageExecutionResultErrorHandling:
    """Test error handling scenarios with ExecutionResult."""
    
    @pytest.mark.asyncio
    async def test_execution_result_with_validation_errors(
        self, triage_agent
    ):
        """Test ExecutionResult creation when request validation fails."""
        # Create state with invalid request
        invalid_state = DeepAgentState(user_request="x")  # Too short
        
        # Execute agent
        result = await triage_agent.execute(invalid_state, "validation_error_test", stream_updates=False)
        
        # Should create ExecutionResult even for validation errors
        assert isinstance(result, ExecutionResult)
        assert result.request_id == "validation_error_test"
        
        # Could be COMPLETED with validation errors or FAILED
        assert result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]
        
        # If FAILED, should have error information
        if result.status == ExecutionStatus.FAILED:
            assert result.error is not None
            assert len(result.error) > 0
    
    @pytest.mark.asyncio
    async def test_execution_result_with_llm_timeout(
        self, triage_agent, sample_state, mock_llm_manager
    ):
        """Test ExecutionResult creation when LLM times out."""
        # Simulate LLM timeout
        mock_llm_manager.ask_llm.side_effect = asyncio.TimeoutError("LLM request timed out")
        
        # Execute agent
        result = await triage_agent.execute(sample_state, "timeout_test", stream_updates=False)
        
        # Should handle timeout gracefully with ExecutionResult
        assert isinstance(result, ExecutionResult)
        assert result.request_id == "timeout_test"
        
        # Should either succeed with fallback or fail gracefully
        if result.status == ExecutionStatus.FAILED:
            assert result.error is not None
        elif result.status == ExecutionStatus.COMPLETED:
            # Used fallback - should have lower confidence
            assert sample_state.triage_result.confidence_score <= 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])