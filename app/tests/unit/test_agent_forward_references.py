"""Test for Agent forward reference resolution.

This test ensures that AgentCompleted and related models can be properly
instantiated with all their forward references resolved.
"""

import pytest

# Import all required types
from app.agents.triage_sub_agent.models import TriageResult, TriageMetadata
from app.schemas import AgentCompleted, AgentResult, AgentState
from app.schemas.agent_models import DeepAgentState, AgentMetadata


def test_agent_completed_model_rebuild():
    """Test that AgentCompleted can be instantiated after model rebuild."""
    # Create a basic AgentResult
    result = AgentResult(
        success=True,
        output={"test": "data"},
        execution_time_ms=100.0
    )
    
    # Create AgentCompleted instance
    completed = AgentCompleted(
        run_id="test-run-123",
        result=result,
        execution_time_ms=100.0
    )
    
    assert completed.run_id == "test-run-123"
    assert completed.result.success is True
    assert completed.execution_time_ms == 100.0


def test_deep_agent_state_with_triage_result():
    """Test that DeepAgentState can be created with TriageResult."""
    # Create TriageMetadata
    metadata = TriageMetadata(
        triage_duration_ms=50,
        llm_tokens_used=100,
        cache_hit=False,
        fallback_used=False,
        retry_count=0
    )
    
    # Create TriageResult
    triage_result = TriageResult(
        category="optimization",
        confidence_score=0.95,
        metadata=metadata
    )
    
    # Create DeepAgentState with TriageResult
    state = DeepAgentState(
        user_request="Optimize my workload",
        triage_result=triage_result
    )
    
    assert state.user_request == "Optimize my workload"
    assert state.triage_result.category == "optimization"
    assert state.triage_result.confidence_score == 0.95


def test_agent_completed_with_final_state():
    """Test AgentCompleted with final_state containing TriageResult."""
    # Create complete state
    metadata = TriageMetadata(
        triage_duration_ms=75,
        llm_tokens_used=150,
        cache_hit=True,
        fallback_used=False,
        retry_count=1
    )
    
    triage_result = TriageResult(
        category="analysis",
        confidence_score=0.85,
        metadata=metadata
    )
    
    final_state = DeepAgentState(
        user_request="Analyze performance",
        triage_result=triage_result,
        step_count=5
    )
    
    # Create result
    result = AgentResult(
        success=True,
        output=final_state.to_dict(),
        execution_time_ms=200.0,
        metrics={"tokens": 150, "steps": 5}
    )
    
    # Create AgentCompleted with final_state
    completed = AgentCompleted(
        run_id="test-456",
        result=result,
        execution_time_ms=200.0,
        final_state=final_state
    )
    
    assert completed.run_id == "test-456"
    assert completed.result.success is True
    assert completed.final_state.triage_result.category == "analysis"
    assert completed.final_state.step_count == 5


def test_model_handles_circular_dependencies():
    """Test that models properly handle circular dependencies."""
    # Models should work without explicit rebuilds
    result = AgentResult(success=True, output="test")
    completed = AgentCompleted(
        run_id="rebuild-test",
        result=result,
        execution_time_ms=10.0
    )
    
    assert completed.run_id == "rebuild-test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])