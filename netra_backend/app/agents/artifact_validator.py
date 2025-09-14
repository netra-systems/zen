"""Agent interim artifact validation for handoffs between agents.

This module validates artifacts created by agents during pipeline execution,
ensuring data integrity and schema compliance between agent handoffs.
"""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from netra_backend.app.agents.data_sub_agent.models import (
    AnomalyDetectionResponse,
    DataAnalysisResponse,
)
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.state import OptimizationsResult
from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ArtifactValidationError(Exception):
    """Raised when artifact validation fails."""
    
    def __init__(self, message: str, artifact_type: str, errors: List[str]):
        self.artifact_type = artifact_type
        self.errors = errors
        super().__init__(f"{artifact_type} validation failed: {message}")


class ValidationContext(BaseModel):
    """Context information for artifact validation."""
    agent_name: str
    run_id: str
    artifact_type: str
    validation_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    user_request: Optional[str] = None


class ArtifactValidationResult(BaseModel):
    """Result of artifact validation process."""
    is_valid: bool
    artifact_type: str
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validation_context: ValidationContext
    validation_duration_ms: float = 0.0


class ArtifactValidator:
    """Validates agent artifacts for pipeline handoffs."""
    
    def __init__(self):
        self.validation_history: List[ArtifactValidationResult] = []
        self.MAX_HISTORY_SIZE = 1000
    
    def validate_triage_artifact(self, state: DeepAgentState, 
                               context: ValidationContext) -> ArtifactValidationResult:
        """Validate triage_result artifact for handoff."""
        start_time = datetime.now(UTC)
        errors, warnings = self._collect_triage_validation_issues(state)
        duration_ms = self._calculate_duration_ms(start_time)
        return self._create_validation_result("triage_result", errors, warnings, 
                                            context, duration_ms)
    
    def validate_data_artifact(self, state: DeepAgentState,
                             context: ValidationContext) -> ArtifactValidationResult:
        """Validate data_result artifact for handoff."""
        start_time = datetime.now(UTC)
        errors, warnings = self._collect_data_validation_issues(state)
        duration_ms = self._calculate_duration_ms(start_time)
        return self._create_validation_result("data_result", errors, warnings,
                                            context, duration_ms)
    
    def validate_optimization_artifact(self, state: DeepAgentState,
                                     context: ValidationContext) -> ArtifactValidationResult:
        """Validate optimization_result artifact for handoff."""
        start_time = datetime.now(UTC)
        errors, warnings = self._collect_optimization_validation_issues(state)
        duration_ms = self._calculate_duration_ms(start_time)
        return self._create_validation_result("optimizations_result", errors, warnings,
                                            context, duration_ms)
    
    def _validate_triage_required_fields(self, triage_result: TriageResult) -> List[str]:
        """Check triage result has required fields."""
        errors = []
        errors.extend(self._check_triage_category(triage_result))
        errors.extend(self._check_triage_confidence(triage_result))
        errors.extend(self._check_triage_next_agent(triage_result))
        return errors
    
    def _validate_triage_quality(self, triage_result: TriageResult) -> List[str]:
        """Check triage result quality indicators."""
        warnings = []
        if triage_result.confidence_score < 0.8:
            warnings.append(f"Low confidence score: {triage_result.confidence_score}")
        if not triage_result.tool_recommendations:
            warnings.append("No tool recommendations provided")
        return warnings
    
    def _validate_data_required_fields(self, 
                                     data_result: Union[DataAnalysisResponse, AnomalyDetectionResponse]) -> List[str]:
        """Check data result has required fields."""
        errors = []
        if isinstance(data_result, DataAnalysisResponse):
            errors.extend(self._check_data_analysis_fields(data_result))
        elif isinstance(data_result, AnomalyDetectionResponse):
            errors.extend(self._check_anomaly_detection_fields(data_result))
        return errors
    
    def _validate_data_quality(self, 
                             data_result: Union[DataAnalysisResponse, AnomalyDetectionResponse]) -> List[str]:
        """Check data result quality indicators."""
        warnings = []
        if isinstance(data_result, DataAnalysisResponse):
            warnings.extend(self._check_data_analysis_quality(data_result))
        elif isinstance(data_result, AnomalyDetectionResponse):
            warnings.extend(self._check_anomaly_detection_quality(data_result))
        return warnings
    
    def _validate_optimization_required_fields(self, opt_result: OptimizationsResult) -> List[str]:
        """Check optimization result has required fields."""
        errors = []
        errors.extend(self._check_optimization_type(opt_result))
        errors.extend(self._check_optimization_recommendations(opt_result))
        errors.extend(self._check_optimization_confidence(opt_result))
        return errors
    
    def _validate_optimization_quality(self, opt_result: OptimizationsResult) -> List[str]:
        """Check optimization result quality indicators."""
        warnings = []
        warnings.extend(self._check_optimization_confidence_quality(opt_result))
        warnings.extend(self._check_optimization_benefits(opt_result))
        warnings.extend(self._check_optimization_recommendations_count(opt_result))
        return warnings
    
    def _create_validation_result(self, artifact_type: str, errors: List[str], 
                                warnings: List[str], context: ValidationContext,
                                duration_ms: float) -> ArtifactValidationResult:
        """Create validation result object."""
        return ArtifactValidationResult(
            is_valid=len(errors) == 0, artifact_type=artifact_type,
            errors=errors, warnings=warnings, validation_context=context,
            validation_duration_ms=duration_ms)
    
    def store_validation_result(self, result: ArtifactValidationResult) -> None:
        """Store validation result for audit trail."""
        self._append_to_history(result)
        self._trim_history_if_needed()
        self._log_validation_result(result)
    
    def get_validation_history(self, artifact_type: Optional[str] = None, 
                             limit: int = 100) -> List[ArtifactValidationResult]:
        """Retrieve validation history for audit."""
        history = self.validation_history
        if artifact_type:
            history = [r for r in history if r.artifact_type == artifact_type]
        return history[-limit:]
    
    def validate_pipeline_handoff(self, state: DeepAgentState, from_agent: str,
                                to_agent: str, run_id: str) -> None:
        """Validate artifact for specific agent-to-agent handoff."""
        context = self._create_handoff_context(from_agent, run_id, state)
        result = self._run_agent_specific_validation(state, context, from_agent)
        if result:
            self._process_validation_result(result, from_agent, to_agent)
    
    # Helper functions for timing and validation collection
    def _calculate_duration_ms(self, start_time: datetime) -> float:
        """Calculate duration in milliseconds from start time."""
        return (datetime.now(UTC) - start_time).total_seconds() * 1000
    
    def _collect_triage_validation_issues(self, state: DeepAgentState) -> tuple[List[str], List[str]]:
        """Collect all triage validation errors and warnings."""
        errors, warnings = [], []
        if not state.triage_result:
            errors.append("triage_result is None - required for pipeline continuation")
        else:
            errors.extend(self._validate_triage_required_fields(state.triage_result))
            warnings.extend(self._validate_triage_quality(state.triage_result))
        return errors, warnings
    
    def _collect_data_validation_issues(self, state: DeepAgentState) -> tuple[List[str], List[str]]:
        """Collect all data validation errors and warnings."""
        errors, warnings = [], []
        if not state.data_result:
            errors.append("data_result is None - required for optimization handoff")
        else:
            errors.extend(self._validate_data_required_fields(state.data_result))
            warnings.extend(self._validate_data_quality(state.data_result))
        return errors, warnings
    
    def _collect_optimization_validation_issues(self, state: DeepAgentState) -> tuple[List[str], List[str]]:
        """Collect all optimization validation errors and warnings."""
        errors, warnings = [], []
        if not state.optimizations_result:
            errors.append("optimizations_result is None - required for action planning")
        else:
            errors.extend(self._validate_optimization_required_fields(state.optimizations_result))
            warnings.extend(self._validate_optimization_quality(state.optimizations_result))
        return errors, warnings
    
    # Triage validation helpers
    def _check_triage_category(self, triage_result: TriageResult) -> List[str]:
        """Check if triage category is valid."""
        if not triage_result.category or triage_result.category == "unknown":
            return ["category is required and cannot be 'unknown'"]
        return []
    
    def _check_triage_confidence(self, triage_result: TriageResult) -> List[str]:
        """Check if triage confidence score is acceptable."""
        if triage_result.confidence_score < 0.5:
            return [f"confidence_score too low: {triage_result.confidence_score}"]
        return []
    
    def _check_triage_next_agent(self, triage_result: TriageResult) -> List[str]:
        """Check if next agent is specified."""
        if not triage_result.suggested_workflow.next_agent:
            return ["suggested_workflow.next_agent is required"]
        return []
    
    # Data validation helpers
    def _check_data_analysis_fields(self, data_result: DataAnalysisResponse) -> List[str]:
        """Check data analysis response required fields."""
        errors = []
        if not data_result.query:
            errors.append("DataAnalysisResponse.query is required")
        if data_result.execution_time_ms < 0:
            errors.append("execution_time_ms cannot be negative")
        return errors
    
    def _check_anomaly_detection_fields(self, data_result: AnomalyDetectionResponse) -> List[str]:
        """Check anomaly detection response required fields."""
        if data_result.confidence_score < 0.0 or data_result.confidence_score > 1.0:
            return ["AnomalyDetectionResponse.confidence_score must be 0-1"]
        return []
    
    def _check_data_analysis_quality(self, data_result: DataAnalysisResponse) -> List[str]:
        """Check data analysis quality indicators."""
        warnings = []
        if not data_result.insights:
            warnings.append("No insights provided in DataAnalysisResponse")
        if data_result.execution_time_ms > 30000:  # 30 seconds
            warnings.append(f"Long execution time: {data_result.execution_time_ms}ms")
        return warnings
    
    def _check_anomaly_detection_quality(self, data_result: AnomalyDetectionResponse) -> List[str]:
        """Check anomaly detection quality indicators."""
        if data_result.confidence_score < 0.7:
            return [f"Low confidence in anomaly detection: {data_result.confidence_score}"]
        return []
    
    # Optimization validation helpers
    def _check_optimization_type(self, opt_result: OptimizationsResult) -> List[str]:
        """Check if optimization type is specified."""
        if not opt_result.optimization_type:
            return ["optimization_type is required"]
        return []
    
    def _check_optimization_recommendations(self, opt_result: OptimizationsResult) -> List[str]:
        """Check if optimization recommendations exist."""
        if not opt_result.recommendations:
            return ["recommendations list cannot be empty"]
        return []
    
    def _check_optimization_confidence(self, opt_result: OptimizationsResult) -> List[str]:
        """Check if optimization confidence score is valid."""
        if opt_result.confidence_score < 0.0 or opt_result.confidence_score > 1.0:
            return ["confidence_score must be between 0 and 1"]
        return []
    
    def _check_optimization_confidence_quality(self, opt_result: OptimizationsResult) -> List[str]:
        """Check optimization confidence quality."""
        if opt_result.confidence_score < 0.8:
            return [f"Low optimization confidence: {opt_result.confidence_score}"]
        return []
    
    def _check_optimization_benefits(self, opt_result: OptimizationsResult) -> List[str]:
        """Check if optimization benefits are identified."""
        if not opt_result.cost_savings and not opt_result.performance_improvement:
            return ["No quantifiable benefits identified"]
        return []
    
    def _check_optimization_recommendations_count(self, opt_result: OptimizationsResult) -> List[str]:
        """Check if sufficient recommendations are provided."""
        if len(opt_result.recommendations) < 2:
            return ["Few recommendations provided - may need deeper analysis"]
        return []
    
    # History and logging helpers
    def _append_to_history(self, result: ArtifactValidationResult) -> None:
        """Append validation result to history."""
        self.validation_history.append(result)
    
    def _trim_history_if_needed(self) -> None:
        """Trim history if it exceeds maximum size."""
        if len(self.validation_history) > self.MAX_HISTORY_SIZE:
            self.validation_history = self.validation_history[-self.MAX_HISTORY_SIZE:]
    
    def _log_validation_result(self, result: ArtifactValidationResult) -> None:
        """Log validation result with appropriate level."""
        log_msg = f"Artifact validation: {result.artifact_type} - "
        log_msg += "PASSED" if result.is_valid else "FAILED"
        if result.errors:
            logger.error(f"{log_msg} - Errors: {result.errors}")
        elif result.warnings:
            logger.warning(f"{log_msg} - Warnings: {result.warnings}")
        else:
            logger.info(log_msg)
    
    # Pipeline handoff helpers
    def _create_handoff_context(self, from_agent: str, run_id: str, state: DeepAgentState) -> ValidationContext:
        """Create validation context for pipeline handoff."""
        return ValidationContext(
            agent_name=from_agent, run_id=run_id, artifact_type="",
            user_request=state.user_request)
    
    def _run_agent_specific_validation(self, state: DeepAgentState, context: ValidationContext, 
                                     from_agent: str) -> Optional[ArtifactValidationResult]:
        """Run validation specific to agent type."""
        if from_agent == "TriageSubAgent":
            return self._validate_triage_handoff(state, context)
        elif from_agent == "DataSubAgent":
            return self._validate_data_handoff(state, context)
        elif from_agent.endswith("OptimizationsCoreSubAgent"):
            return self._validate_optimization_handoff(state, context)
        else:
            return self._handle_unknown_agent(from_agent)
    
    def _validate_triage_handoff(self, state: DeepAgentState, context: ValidationContext) -> ArtifactValidationResult:
        """Validate triage agent handoff."""
        context.artifact_type = "triage_result"
        return self.validate_triage_artifact(state, context)
    
    def _validate_data_handoff(self, state: DeepAgentState, context: ValidationContext) -> ArtifactValidationResult:
        """Validate data agent handoff."""
        context.artifact_type = "data_result"
        return self.validate_data_artifact(state, context)
    
    def _validate_optimization_handoff(self, state: DeepAgentState, context: ValidationContext) -> ArtifactValidationResult:
        """Validate optimization agent handoff."""
        context.artifact_type = "optimizations_result"
        return self.validate_optimization_artifact(state, context)
    
    def _handle_unknown_agent(self, from_agent: str) -> None:
        """Handle validation for unknown agent type."""
        logger.warning(f"No validation defined for handoff from {from_agent}")
        return None
    
    def _process_validation_result(self, result: ArtifactValidationResult, 
                                 from_agent: str, to_agent: str) -> None:
        """Process validation result and raise error if invalid."""
        self.store_validation_result(result)
        if not result.is_valid:
            raise ArtifactValidationError(f"Invalid handoff from {from_agent} to {to_agent}",
                                        result.artifact_type, result.errors)


# Global validator instance for use across the application
artifact_validator = ArtifactValidator()