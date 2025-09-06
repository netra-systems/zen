# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: E2E tests for agent interim artifact validation between handoffs.
# REMOVED_SYNTAX_ERROR: Tests validate artifacts at agent boundaries with real state transitions.
# REMOVED_SYNTAX_ERROR: Maximum 300 lines, functions <=8 lines.
""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

import pytest

# REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.artifact_validator import ( )
ArtifactValidationError,
ArtifactValidator,
ValidationContext,
artifact_validator,

# REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.data_sub_agent.models import ( )
AnomalyDetectionResponse,
DataAnalysisResponse,


from netra_backend.app.agents.state import DeepAgentState, OptimizationsResult
# REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.triage.unified_triage_agent import ( )
Complexity,
KeyParameters,
Priority,
SuggestedWorkflow,
TriageResult,
UserIntent,


# REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_triage_result():
    # REMOVED_SYNTAX_ERROR: """Create valid triage result for testing."""
    # REMOVED_SYNTAX_ERROR: return TriageResult( )
    # REMOVED_SYNTAX_ERROR: category="cost_optimization",
    # REMOVED_SYNTAX_ERROR: confidence_score=0.85,
    # REMOVED_SYNTAX_ERROR: priority=Priority.HIGH,
    # REMOVED_SYNTAX_ERROR: complexity=Complexity.MODERATE,
    # REMOVED_SYNTAX_ERROR: key_parameters=KeyParameters(workload_type="batch_processing"),
    # REMOVED_SYNTAX_ERROR: user_intent=UserIntent(primary_intent="optimize_costs"),
    # REMOVED_SYNTAX_ERROR: suggested_workflow=SuggestedWorkflow(next_agent="DataSubAgent")
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_data_result():
    # REMOVED_SYNTAX_ERROR: """Create valid data analysis result for testing."""
    # REMOVED_SYNTAX_ERROR: return DataAnalysisResponse( )
    # REMOVED_SYNTAX_ERROR: query="SELECT cost_metrics FROM workload_data",
    # REMOVED_SYNTAX_ERROR: results=[{"total_cost": 1000, "cpu_usage": 75}],
    # REMOVED_SYNTAX_ERROR: insights={"cost_trend": "increasing", "peak_hours": [14, 15, 16}],
    # REMOVED_SYNTAX_ERROR: recommendations=["Scale down during off-peak", "Use spot instances"],
    # REMOVED_SYNTAX_ERROR: execution_time_ms=1500.0,
    # REMOVED_SYNTAX_ERROR: affected_rows=150
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_optimization_result():
    # REMOVED_SYNTAX_ERROR: """Create valid optimization result for testing."""
    # REMOVED_SYNTAX_ERROR: return OptimizationsResult( )
    # REMOVED_SYNTAX_ERROR: optimization_type="cost_reduction",
    # REMOVED_SYNTAX_ERROR: recommendations=["Use reserved instances", "Implement auto-scaling"],
    # REMOVED_SYNTAX_ERROR: cost_savings=250.0,
    # REMOVED_SYNTAX_ERROR: performance_improvement=15.0,
    # REMOVED_SYNTAX_ERROR: confidence_score=0.8
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def validation_context():
    # REMOVED_SYNTAX_ERROR: """Create validation context for testing."""
    # REMOVED_SYNTAX_ERROR: return ValidationContext( )
    # REMOVED_SYNTAX_ERROR: agent_name="TestAgent",
    # REMOVED_SYNTAX_ERROR: run_id=str(uuid.uuid4()),
    # REMOVED_SYNTAX_ERROR: artifact_type="test_artifact",
    # REMOVED_SYNTAX_ERROR: user_request="Test optimization request"
    

# REMOVED_SYNTAX_ERROR: class TestArtifactValidation:
    # REMOVED_SYNTAX_ERROR: """Test suite for artifact validation functionality."""

# REMOVED_SYNTAX_ERROR: def test_validator_initialization(self):
    # REMOVED_SYNTAX_ERROR: """Test validator initializes correctly."""
    # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()
    # REMOVED_SYNTAX_ERROR: assert validator.validation_history == []
    # REMOVED_SYNTAX_ERROR: assert validator.MAX_HISTORY_SIZE == 1000

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_valid_triage_artifact_validation(self, sample_triage_result, validation_context):
        # REMOVED_SYNTAX_ERROR: """Test validation of valid triage artifact."""
        # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()
        # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
        # REMOVED_SYNTAX_ERROR: user_request="Optimize costs",
        # REMOVED_SYNTAX_ERROR: triage_result=sample_triage_result
        

        # REMOVED_SYNTAX_ERROR: result = validator.validate_triage_artifact(state, validation_context)
        # REMOVED_SYNTAX_ERROR: assert result.is_valid
        # REMOVED_SYNTAX_ERROR: assert len(result.errors) == 0
        # REMOVED_SYNTAX_ERROR: assert result.artifact_type == "triage_result"

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_invalid_triage_artifact_validation(self, validation_context):
            # REMOVED_SYNTAX_ERROR: """Test validation of invalid triage artifact."""
            # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()
            # REMOVED_SYNTAX_ERROR: invalid_triage = TriageResult( )
            # REMOVED_SYNTAX_ERROR: category="unknown",  # Invalid category
            # REMOVED_SYNTAX_ERROR: confidence_score=0.3,  # Too low confidence
            # REMOVED_SYNTAX_ERROR: suggested_workflow=SuggestedWorkflow(next_agent="")  # Missing next agent
            
            # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
            # REMOVED_SYNTAX_ERROR: user_request="Test request",
            # REMOVED_SYNTAX_ERROR: triage_result=invalid_triage
            

            # REMOVED_SYNTAX_ERROR: result = validator.validate_triage_artifact(state, validation_context)
            # REMOVED_SYNTAX_ERROR: assert not result.is_valid
            # REMOVED_SYNTAX_ERROR: assert len(result.errors) >= 2  # Multiple validation failures
            # REMOVED_SYNTAX_ERROR: assert any("unknown" in error for error in result.errors)

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_missing_triage_artifact_validation(self, validation_context):
                # REMOVED_SYNTAX_ERROR: """Test validation when triage artifact is missing."""
                # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()
                # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="Test request")

                # REMOVED_SYNTAX_ERROR: result = validator.validate_triage_artifact(state, validation_context)
                # REMOVED_SYNTAX_ERROR: assert not result.is_valid
                # REMOVED_SYNTAX_ERROR: assert any("triage_result is None" in error for error in result.errors)

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_valid_data_artifact_validation(self, sample_data_result, validation_context):
                    # REMOVED_SYNTAX_ERROR: """Test validation of valid data artifact."""
                    # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()
                    # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                    # REMOVED_SYNTAX_ERROR: user_request="Analyze data",
                    # REMOVED_SYNTAX_ERROR: data_result=sample_data_result
                    

                    # REMOVED_SYNTAX_ERROR: result = validator.validate_data_artifact(state, validation_context)
                    # REMOVED_SYNTAX_ERROR: assert result.is_valid
                    # REMOVED_SYNTAX_ERROR: assert len(result.errors) == 0
                    # REMOVED_SYNTAX_ERROR: assert result.artifact_type == "data_result"

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_invalid_data_artifact_validation(self, validation_context):
                        # REMOVED_SYNTAX_ERROR: """Test validation of invalid data artifact."""
                        # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()

                        # Test that creating invalid data raises expected validation error
                        # REMOVED_SYNTAX_ERROR: from pydantic_core import ValidationError
                        # REMOVED_SYNTAX_ERROR: try:
                            # REMOVED_SYNTAX_ERROR: invalid_data = DataAnalysisResponse( )
                            # REMOVED_SYNTAX_ERROR: query="",  # Empty query
                            # REMOVED_SYNTAX_ERROR: execution_time_ms=-100.0  # Negative execution time
                            
                            # If no error raised, fail the test
                            # REMOVED_SYNTAX_ERROR: assert False, "Expected ValidationError for negative execution time"
                            # REMOVED_SYNTAX_ERROR: except ValidationError as e:
                                # This is expected - validation should catch negative execution time
                                # REMOVED_SYNTAX_ERROR: assert "execution_time_ms" in str(e)
                                # REMOVED_SYNTAX_ERROR: assert "non-negative" in str(e)

                                # Test with valid data but empty query (different validation level)
                                # REMOVED_SYNTAX_ERROR: valid_structure_data = DataAnalysisResponse( )
                                # REMOVED_SYNTAX_ERROR: query="",  # Empty query - should be caught by artifact validator
                                # REMOVED_SYNTAX_ERROR: execution_time_ms=100.0  # Valid execution time
                                
                                # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                                # REMOVED_SYNTAX_ERROR: user_request="Test request",
                                # REMOVED_SYNTAX_ERROR: data_result=valid_structure_data
                                

                                # REMOVED_SYNTAX_ERROR: result = validator.validate_data_artifact(state, validation_context)
                                # REMOVED_SYNTAX_ERROR: assert not result.is_valid
                                # REMOVED_SYNTAX_ERROR: assert len(result.errors) >= 1
                                # REMOVED_SYNTAX_ERROR: assert any("query is required" in error for error in result.errors)

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_valid_optimization_artifact_validation(self, sample_optimization_result, validation_context):
                                    # REMOVED_SYNTAX_ERROR: """Test validation of valid optimization artifact."""
                                    # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()
                                    # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                                    # REMOVED_SYNTAX_ERROR: user_request="Optimize workload",
                                    # REMOVED_SYNTAX_ERROR: optimizations_result=sample_optimization_result
                                    

                                    # REMOVED_SYNTAX_ERROR: result = validator.validate_optimization_artifact(state, validation_context)
                                    # REMOVED_SYNTAX_ERROR: assert result.is_valid
                                    # REMOVED_SYNTAX_ERROR: assert len(result.errors) == 0
                                    # REMOVED_SYNTAX_ERROR: assert result.artifact_type == "optimizations_result"

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_invalid_optimization_artifact_validation(self, validation_context):
                                        # REMOVED_SYNTAX_ERROR: """Test validation of invalid optimization artifact."""
                                        # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()

                                        # Test Pydantic validation catches invalid confidence score
                                        # REMOVED_SYNTAX_ERROR: from pydantic_core import ValidationError
                                        # REMOVED_SYNTAX_ERROR: try:
                                            # REMOVED_SYNTAX_ERROR: invalid_opt = OptimizationsResult( )
                                            # REMOVED_SYNTAX_ERROR: optimization_type="test",
                                            # REMOVED_SYNTAX_ERROR: recommendations=["test"],
                                            # REMOVED_SYNTAX_ERROR: confidence_score=1.5  # Invalid confidence score > 1.0
                                            
                                            # REMOVED_SYNTAX_ERROR: assert False, "Expected ValidationError for confidence_score > 1.0"
                                            # REMOVED_SYNTAX_ERROR: except ValidationError as e:
                                                # REMOVED_SYNTAX_ERROR: assert "confidence_score" in str(e)
                                                # REMOVED_SYNTAX_ERROR: assert "less than or equal to 1" in str(e)

                                                # Test artifact-level validation with valid Pydantic but invalid business logic
                                                # REMOVED_SYNTAX_ERROR: valid_structure_opt = OptimizationsResult( )
                                                # REMOVED_SYNTAX_ERROR: optimization_type="",  # Empty type - should be caught by artifact validator
                                                # REMOVED_SYNTAX_ERROR: recommendations=[],  # Empty recommendations - should be caught by artifact validator
                                                # REMOVED_SYNTAX_ERROR: confidence_score=0.9  # Valid Pydantic range but we"ll test artifact validation
                                                
                                                # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                                                # REMOVED_SYNTAX_ERROR: user_request="Test request",
                                                # REMOVED_SYNTAX_ERROR: optimizations_result=valid_structure_opt
                                                

                                                # REMOVED_SYNTAX_ERROR: result = validator.validate_optimization_artifact(state, validation_context)
                                                # REMOVED_SYNTAX_ERROR: assert not result.is_valid
                                                # REMOVED_SYNTAX_ERROR: assert len(result.errors) >= 2
                                                # REMOVED_SYNTAX_ERROR: assert any("optimization_type is required" in error for error in result.errors)

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_validation_history_storage(self, sample_triage_result, validation_context):
                                                    # REMOVED_SYNTAX_ERROR: """Test validation results are stored in history."""
                                                    # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()
                                                    # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                                                    # REMOVED_SYNTAX_ERROR: user_request="Test request",
                                                    # REMOVED_SYNTAX_ERROR: triage_result=sample_triage_result
                                                    

                                                    # REMOVED_SYNTAX_ERROR: result = validator.validate_triage_artifact(state, validation_context)
                                                    # REMOVED_SYNTAX_ERROR: validator.store_validation_result(result)

                                                    # REMOVED_SYNTAX_ERROR: history = validator.get_validation_history()
                                                    # REMOVED_SYNTAX_ERROR: assert len(history) == 1
                                                    # REMOVED_SYNTAX_ERROR: assert history[0].artifact_type == "triage_result"
                                                    # REMOVED_SYNTAX_ERROR: assert history[0].is_valid

                                                    # Removed problematic line: @pytest.mark.asyncio
                                                    # Removed problematic line: async def test_validation_history_limit(self, validation_context):
                                                        # REMOVED_SYNTAX_ERROR: """Test validation history respects size limit."""
                                                        # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()
                                                        # REMOVED_SYNTAX_ERROR: validator.MAX_HISTORY_SIZE = 3

                                                        # Add 5 validation results
                                                        # REMOVED_SYNTAX_ERROR: for i in range(5):
                                                            # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="formatted_string")
                                                            # REMOVED_SYNTAX_ERROR: result = validator.validate_triage_artifact(state, validation_context)
                                                            # REMOVED_SYNTAX_ERROR: validator.store_validation_result(result)

                                                            # REMOVED_SYNTAX_ERROR: history = validator.get_validation_history()
                                                            # REMOVED_SYNTAX_ERROR: assert len(history) == 3  # Should be limited to MAX_HISTORY_SIZE

                                                            # Removed problematic line: @pytest.mark.asyncio
                                                            # Removed problematic line: async def test_pipeline_handoff_validation_triage_to_data(self, sample_triage_result):
                                                                # REMOVED_SYNTAX_ERROR: """Test pipeline handoff validation from triage to data agent."""
                                                                # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()
                                                                # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                                                                # REMOVED_SYNTAX_ERROR: user_request="Optimize costs",
                                                                # REMOVED_SYNTAX_ERROR: triage_result=sample_triage_result
                                                                
                                                                # REMOVED_SYNTAX_ERROR: run_id = str(uuid.uuid4())

                                                                # Should not raise exception for valid handoff
                                                                # REMOVED_SYNTAX_ERROR: validator.validate_pipeline_handoff(state, "TriageSubAgent", "DataSubAgent", run_id)

                                                                # Check validation was stored
                                                                # REMOVED_SYNTAX_ERROR: history = validator.get_validation_history()
                                                                # REMOVED_SYNTAX_ERROR: assert len(history) == 1
                                                                # REMOVED_SYNTAX_ERROR: assert history[0].artifact_type == "triage_result"

                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_pipeline_handoff_validation_failure(self):
                                                                    # REMOVED_SYNTAX_ERROR: """Test pipeline handoff validation raises error for invalid artifacts."""
                                                                    # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()
                                                                    # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="Test request")  # Missing triage_result
                                                                    # REMOVED_SYNTAX_ERROR: run_id = str(uuid.uuid4())

                                                                    # REMOVED_SYNTAX_ERROR: with pytest.raises(ArtifactValidationError) as exc_info:
                                                                        # REMOVED_SYNTAX_ERROR: validator.validate_pipeline_handoff(state, "TriageSubAgent", "DataSubAgent", run_id)

                                                                        # REMOVED_SYNTAX_ERROR: assert "TriageSubAgent" in str(exc_info.value)
                                                                        # REMOVED_SYNTAX_ERROR: assert "DataSubAgent" in str(exc_info.value)
                                                                        # REMOVED_SYNTAX_ERROR: assert exc_info.value.artifact_type == "triage_result"

                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # Removed problematic line: async def test_anomaly_detection_artifact_validation(self, validation_context):
                                                                            # REMOVED_SYNTAX_ERROR: """Test validation of anomaly detection artifacts."""
                                                                            # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()
                                                                            # REMOVED_SYNTAX_ERROR: anomaly_result = AnomalyDetectionResponse( )
                                                                            # REMOVED_SYNTAX_ERROR: anomalies_detected=True,
                                                                            # REMOVED_SYNTAX_ERROR: anomaly_count=3,
                                                                            # REMOVED_SYNTAX_ERROR: confidence_score=0.9
                                                                            
                                                                            # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                                                                            # REMOVED_SYNTAX_ERROR: user_request="Detect anomalies",
                                                                            # REMOVED_SYNTAX_ERROR: data_result=anomaly_result
                                                                            

                                                                            # REMOVED_SYNTAX_ERROR: result = validator.validate_data_artifact(state, validation_context)
                                                                            # REMOVED_SYNTAX_ERROR: assert result.is_valid
                                                                            # REMOVED_SYNTAX_ERROR: assert result.artifact_type == "data_result"

                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                            # Removed problematic line: async def test_global_validator_instance(self):
                                                                                # REMOVED_SYNTAX_ERROR: """Test global validator instance is available."""
                                                                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.artifact_validator import artifact_validator
                                                                                # REMOVED_SYNTAX_ERROR: assert isinstance(artifact_validator, ArtifactValidator)
                                                                                # REMOVED_SYNTAX_ERROR: assert artifact_validator.validation_history == []

                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                # Removed problematic line: async def test_validation_context_creation(self):
                                                                                    # REMOVED_SYNTAX_ERROR: """Test validation context creates properly."""
                                                                                    # REMOVED_SYNTAX_ERROR: context = ValidationContext( )
                                                                                    # REMOVED_SYNTAX_ERROR: agent_name="TestAgent",
                                                                                    # REMOVED_SYNTAX_ERROR: run_id="test-run-123",
                                                                                    # REMOVED_SYNTAX_ERROR: artifact_type="test_artifact",
                                                                                    # REMOVED_SYNTAX_ERROR: user_request="Test request"
                                                                                    

                                                                                    # REMOVED_SYNTAX_ERROR: assert context.agent_name == "TestAgent"
                                                                                    # REMOVED_SYNTAX_ERROR: assert context.run_id == "test-run-123"
                                                                                    # REMOVED_SYNTAX_ERROR: assert context.artifact_type == "test_artifact"
                                                                                    # REMOVED_SYNTAX_ERROR: assert context.user_request == "Test request"
                                                                                    # REMOVED_SYNTAX_ERROR: assert isinstance(context.validation_timestamp, datetime)

                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                    # Removed problematic line: async def test_validation_warnings_and_errors_separation(self, validation_context):
                                                                                        # REMOVED_SYNTAX_ERROR: """Test validation properly separates warnings from errors."""
                                                                                        # REMOVED_SYNTAX_ERROR: validator = ArtifactValidator()
                                                                                        # REMOVED_SYNTAX_ERROR: low_confidence_triage = TriageResult( )
                                                                                        # REMOVED_SYNTAX_ERROR: category="optimization",
                                                                                        # REMOVED_SYNTAX_ERROR: confidence_score=0.6,  # Low but valid confidence
                                                                                        # REMOVED_SYNTAX_ERROR: suggested_workflow=SuggestedWorkflow(next_agent="DataSubAgent")
                                                                                        
                                                                                        # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                                                                                        # REMOVED_SYNTAX_ERROR: user_request="Test request",
                                                                                        # REMOVED_SYNTAX_ERROR: triage_result=low_confidence_triage
                                                                                        

                                                                                        # REMOVED_SYNTAX_ERROR: result = validator.validate_triage_artifact(state, validation_context)
                                                                                        # REMOVED_SYNTAX_ERROR: assert result.is_valid  # Should be valid despite warnings
                                                                                        # REMOVED_SYNTAX_ERROR: assert len(result.warnings) > 0  # Should have warnings about low confidence
                                                                                        # REMOVED_SYNTAX_ERROR: assert len(result.errors) == 0  # Should have no errors