"""Test for Agent forward reference resolution.

This test ensures that AgentCompleted and related models can be properly
instantiated with all their forward references resolved.
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import pytest

# Import all required types
from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
from netra_backend.app.agents.triage.models import TriageMetadata
from netra_backend.app.schemas.agent_models import AgentMetadata, DeepAgentState
from netra_backend.app.schemas.registry import (
    AgentResult,
    AgentState,
)
from netra_backend.app.schemas.agent import AgentCompleted

# Helper functions for 25-line compliance
def create_basic_agent_result():
    """Create a basic AgentResult for testing."""
    return AgentResult(
        success=True,
        output={"test": "data"},
        execution_time_ms=100.0
    )

def create_agent_completed_instance(result, run_id="test-run-123"):
    """Create AgentCompleted instance for testing."""
    return AgentCompleted(
        run_id=run_id,
        result=result,
        execution_time_ms=100.0
    )

def assert_agent_completed_basic(completed):
    """Assert basic AgentCompleted properties."""
    assert completed.run_id == "test-run-123"
    assert completed.result.success is True
    assert completed.execution_time_ms == 100.0

def create_triage_metadata():
    """Create TriageMetadata for testing."""
    return TriageMetadata(
        triage_duration_ms=50,
        cache_hit=False,
        fallback_used=False,
        retry_count=0
    )

def create_triage_result(metadata, category="optimization", confidence=0.95):
    """Create TriageResult for testing."""
    return TriageResult(
        category=category,
        confidence_score=confidence,
        metadata=metadata
    )

def create_deep_agent_state(triage_result, request="Optimize my workload"):
    """Create DeepAgentState for testing."""
    return DeepAgentState(
        user_request=request,
        triage_result=triage_result
    )

def assert_deep_agent_state_basic(state):
    """Assert basic DeepAgentState properties."""
    assert state.user_request == "Optimize my workload"
    assert state.triage_result.category == "optimization"
    assert state.triage_result.confidence_score == 0.95

def create_complete_test_metadata():
    """Create complete metadata for complex testing."""
    return TriageMetadata(
        triage_duration_ms=75,
        cache_hit=True,
        fallback_used=False,
        retry_count=1
    )

def create_complete_agent_result(final_state):
    """Create complete AgentResult with final state."""
    return AgentResult(
        success=True,
        output=final_state.to_dict(),
        execution_time_ms=200.0,
        metrics={"tokens": 150, "steps": 5}
    )

def assert_completed_with_final_state(completed):
    """Assert AgentCompleted with final state properties."""
    assert completed.run_id == "test-456"
    assert completed.result.success is True
    assert completed.final_state.triage_result.category == "analysis"
    assert completed.final_state.step_count == 5

def create_complete_final_state():
    """Create complete final state for complex testing."""
    metadata = create_complete_test_metadata()
    triage_result = create_triage_result(metadata, "analysis", 0.85)
    return DeepAgentState(
        user_request="Analyze performance",
        triage_result=triage_result,
        step_count=5
    )

def create_completed_with_final_state(final_state):
    """Create AgentCompleted with final state."""
    result = create_complete_agent_result(final_state)
    return AgentCompleted(
        run_id="test-456",
        result=result,
        execution_time_ms=200.0,
        final_state=final_state
    )

def test_agent_completed_model_rebuild():
    """Test that AgentCompleted can be instantiated after model rebuild."""
    result = create_basic_agent_result()
    completed = create_agent_completed_instance(result)
    assert_agent_completed_basic(completed)

def test_deep_agent_state_with_triage_result():
    """Test that DeepAgentState can be created with TriageResult."""
    metadata = create_triage_metadata()
    triage_result = create_triage_result(metadata)
    state = create_deep_agent_state(triage_result)
    assert_deep_agent_state_basic(state)

def test_agent_completed_with_final_state():
    """Test AgentCompleted with final_state containing TriageResult."""
    final_state = create_complete_final_state()
    completed = create_completed_with_final_state(final_state)
    assert_completed_with_final_state(completed)

def test_model_handles_circular_dependencies():
    """Test that models properly handle circular dependencies."""
    result = AgentResult(success=True, output="test")
    completed = AgentCompleted(
        run_id="rebuild-test",
        result=result,
        execution_time_ms=10.0
    )
    assert completed.run_id == "rebuild-test"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])