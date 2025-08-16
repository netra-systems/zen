"""
E2E tests for agent interim artifact validation between handoffs.
Tests validate artifacts at agent boundaries with real state transitions.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
import asyncio
import uuid
from typing import Dict, Any
from datetime import datetime

from app.agents.state import DeepAgentState, OptimizationsResult
from app.agents.triage_sub_agent.models import (
    TriageResult, Priority, Complexity, KeyParameters, UserIntent, SuggestedWorkflow
)
from app.agents.data_sub_agent.models import DataAnalysisResponse, AnomalyDetectionResponse
from app.agents.artifact_validator import (
    ArtifactValidator, ValidationContext, ArtifactValidationError, artifact_validator
)


@pytest.fixture
def sample_triage_result():
    """Create valid triage result for testing."""
    return TriageResult(
        category="cost_optimization",
        confidence_score=0.85,
        priority=Priority.HIGH,
        complexity=Complexity.MODERATE,
        key_parameters=KeyParameters(workload_type="batch_processing"),
        user_intent=UserIntent(primary_intent="optimize_costs"),
        suggested_workflow=SuggestedWorkflow(next_agent="DataSubAgent")
    )


@pytest.fixture  
def sample_data_result():
    """Create valid data analysis result for testing."""
    return DataAnalysisResponse(
        query="SELECT cost_metrics FROM workload_data",
        results=[{"total_cost": 1000, "cpu_usage": 75}],
        insights={"cost_trend": "increasing", "peak_hours": [14, 15, 16]},
        recommendations=["Scale down during off-peak", "Use spot instances"],
        execution_time_ms=1500.0,
        affected_rows=150
    )


@pytest.fixture
def sample_optimization_result():
    """Create valid optimization result for testing."""
    return OptimizationsResult(
        optimization_type="cost_reduction",
        recommendations=["Use reserved instances", "Implement auto-scaling"],
        cost_savings=250.0,
        performance_improvement=15.0,
        confidence_score=0.8
    )


@pytest.fixture
def validation_context():
    """Create validation context for testing."""
    return ValidationContext(
        agent_name="TestAgent",
        run_id=str(uuid.uuid4()),
        artifact_type="test_artifact",
        user_request="Test optimization request"
    )


class TestArtifactValidation:
    """Test suite for artifact validation functionality."""
    
    def test_validator_initialization(self):
        """Test validator initializes correctly."""
        validator = ArtifactValidator()
        assert validator.validation_history == []
        assert validator.MAX_HISTORY_SIZE == 1000
    
    async def test_valid_triage_artifact_validation(self, sample_triage_result, validation_context):
        """Test validation of valid triage artifact."""
        validator = ArtifactValidator()
        state = DeepAgentState(
            user_request="Optimize costs",
            triage_result=sample_triage_result
        )
        
        result = validator.validate_triage_artifact(state, validation_context)
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.artifact_type == "triage_result"
    
    async def test_invalid_triage_artifact_validation(self, validation_context):
        """Test validation of invalid triage artifact."""
        validator = ArtifactValidator()
        invalid_triage = TriageResult(
            category="unknown",  # Invalid category
            confidence_score=0.3,  # Too low confidence
            suggested_workflow=SuggestedWorkflow(next_agent="")  # Missing next agent
        )
        state = DeepAgentState(
            user_request="Test request",
            triage_result=invalid_triage
        )
        
        result = validator.validate_triage_artifact(state, validation_context)
        assert not result.is_valid
        assert len(result.errors) >= 2  # Multiple validation failures
        assert any("unknown" in error for error in result.errors)
    
    async def test_missing_triage_artifact_validation(self, validation_context):
        """Test validation when triage artifact is missing."""
        validator = ArtifactValidator()
        state = DeepAgentState(user_request="Test request")
        
        result = validator.validate_triage_artifact(state, validation_context)
        assert not result.is_valid
        assert any("triage_result is None" in error for error in result.errors)
    
    async def test_valid_data_artifact_validation(self, sample_data_result, validation_context):
        """Test validation of valid data artifact."""
        validator = ArtifactValidator()
        state = DeepAgentState(
            user_request="Analyze data",
            data_result=sample_data_result
        )
        
        result = validator.validate_data_artifact(state, validation_context)
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.artifact_type == "data_result"
    
    async def test_invalid_data_artifact_validation(self, validation_context):
        """Test validation of invalid data artifact."""
        validator = ArtifactValidator()
        
        # Test that creating invalid data raises expected validation error
        from pydantic_core import ValidationError
        try:
            invalid_data = DataAnalysisResponse(
                query="",  # Empty query  
                execution_time_ms=-100.0  # Negative execution time
            )
            # If no error raised, fail the test
            assert False, "Expected ValidationError for negative execution time"
        except ValidationError as e:
            # This is expected - validation should catch negative execution time
            assert "execution_time_ms" in str(e)
            assert "non-negative" in str(e)
        
        # Test with valid data but empty query (different validation level)
        valid_structure_data = DataAnalysisResponse(
            query="",  # Empty query - should be caught by artifact validator
            execution_time_ms=100.0  # Valid execution time
        )
        state = DeepAgentState(
            user_request="Test request",
            data_result=valid_structure_data
        )
        
        result = validator.validate_data_artifact(state, validation_context)
        assert not result.is_valid
        assert len(result.errors) >= 1
        assert any("query is required" in error for error in result.errors)
    
    async def test_valid_optimization_artifact_validation(self, sample_optimization_result, validation_context):
        """Test validation of valid optimization artifact.""" 
        validator = ArtifactValidator()
        state = DeepAgentState(
            user_request="Optimize workload",
            optimizations_result=sample_optimization_result
        )
        
        result = validator.validate_optimization_artifact(state, validation_context)
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.artifact_type == "optimizations_result"
    
    async def test_invalid_optimization_artifact_validation(self, validation_context):
        """Test validation of invalid optimization artifact."""
        validator = ArtifactValidator()
        
        # Test Pydantic validation catches invalid confidence score
        from pydantic_core import ValidationError
        try:
            invalid_opt = OptimizationsResult(
                optimization_type="test",
                recommendations=["test"],
                confidence_score=1.5  # Invalid confidence score > 1.0
            )
            assert False, "Expected ValidationError for confidence_score > 1.0"
        except ValidationError as e:
            assert "confidence_score" in str(e)
            assert "less than or equal to 1" in str(e)
        
        # Test artifact-level validation with valid Pydantic but invalid business logic
        valid_structure_opt = OptimizationsResult(
            optimization_type="",  # Empty type - should be caught by artifact validator
            recommendations=[],  # Empty recommendations - should be caught by artifact validator
            confidence_score=0.9  # Valid Pydantic range but we'll test artifact validation
        )
        state = DeepAgentState(
            user_request="Test request",
            optimizations_result=valid_structure_opt
        )
        
        result = validator.validate_optimization_artifact(state, validation_context)
        assert not result.is_valid
        assert len(result.errors) >= 2
        assert any("optimization_type is required" in error for error in result.errors)
    
    async def test_validation_history_storage(self, sample_triage_result, validation_context):
        """Test validation results are stored in history."""
        validator = ArtifactValidator()
        state = DeepAgentState(
            user_request="Test request",
            triage_result=sample_triage_result
        )
        
        result = validator.validate_triage_artifact(state, validation_context)
        validator.store_validation_result(result)
        
        history = validator.get_validation_history()
        assert len(history) == 1
        assert history[0].artifact_type == "triage_result"
        assert history[0].is_valid
    
    async def test_validation_history_limit(self, validation_context):
        """Test validation history respects size limit."""
        validator = ArtifactValidator()
        validator.MAX_HISTORY_SIZE = 3
        
        # Add 5 validation results
        for i in range(5):
            state = DeepAgentState(user_request=f"Request {i}")
            result = validator.validate_triage_artifact(state, validation_context)
            validator.store_validation_result(result)
        
        history = validator.get_validation_history()
        assert len(history) == 3  # Should be limited to MAX_HISTORY_SIZE
    
    async def test_pipeline_handoff_validation_triage_to_data(self, sample_triage_result):
        """Test pipeline handoff validation from triage to data agent."""
        validator = ArtifactValidator()
        state = DeepAgentState(
            user_request="Optimize costs",
            triage_result=sample_triage_result
        )
        run_id = str(uuid.uuid4())
        
        # Should not raise exception for valid handoff
        validator.validate_pipeline_handoff(state, "TriageSubAgent", "DataSubAgent", run_id)
        
        # Check validation was stored
        history = validator.get_validation_history()
        assert len(history) == 1
        assert history[0].artifact_type == "triage_result"
    
    async def test_pipeline_handoff_validation_failure(self):
        """Test pipeline handoff validation raises error for invalid artifacts."""
        validator = ArtifactValidator()
        state = DeepAgentState(user_request="Test request")  # Missing triage_result
        run_id = str(uuid.uuid4())
        
        with pytest.raises(ArtifactValidationError) as exc_info:
            validator.validate_pipeline_handoff(state, "TriageSubAgent", "DataSubAgent", run_id)
        
        assert "TriageSubAgent" in str(exc_info.value)
        assert "DataSubAgent" in str(exc_info.value)
        assert exc_info.value.artifact_type == "triage_result"
    
    async def test_anomaly_detection_artifact_validation(self, validation_context):
        """Test validation of anomaly detection artifacts."""
        validator = ArtifactValidator()
        anomaly_result = AnomalyDetectionResponse(
            anomalies_detected=True,
            anomaly_count=3,
            confidence_score=0.9
        )
        state = DeepAgentState(
            user_request="Detect anomalies",
            data_result=anomaly_result
        )
        
        result = validator.validate_data_artifact(state, validation_context)
        assert result.is_valid
        assert result.artifact_type == "data_result"
    
    async def test_global_validator_instance(self):
        """Test global validator instance is available."""
        from app.agents.artifact_validator import artifact_validator
        assert isinstance(artifact_validator, ArtifactValidator)
        assert artifact_validator.validation_history == []
    
    async def test_validation_context_creation(self):
        """Test validation context creates properly."""
        context = ValidationContext(
            agent_name="TestAgent",
            run_id="test-run-123",
            artifact_type="test_artifact",
            user_request="Test request"
        )
        
        assert context.agent_name == "TestAgent"
        assert context.run_id == "test-run-123"
        assert context.artifact_type == "test_artifact"
        assert context.user_request == "Test request"
        assert isinstance(context.validation_timestamp, datetime)
    
    async def test_validation_warnings_and_errors_separation(self, validation_context):
        """Test validation properly separates warnings from errors."""
        validator = ArtifactValidator()
        low_confidence_triage = TriageResult(
            category="optimization",
            confidence_score=0.6,  # Low but valid confidence
            suggested_workflow=SuggestedWorkflow(next_agent="DataSubAgent")
        )
        state = DeepAgentState(
            user_request="Test request",
            triage_result=low_confidence_triage
        )
        
        result = validator.validate_triage_artifact(state, validation_context)
        assert result.is_valid  # Should be valid despite warnings
        assert len(result.warnings) > 0  # Should have warnings about low confidence
        assert len(result.errors) == 0  # Should have no errors