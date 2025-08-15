"""Agent interim artifact validation for handoffs between agents.

This module validates artifacts created by agents during pipeline execution,
ensuring data integrity and schema compliance between agent handoffs.
"""

from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.logging_config import central_logger
from app.agents.state import DeepAgentState, OptimizationsResult
from app.agents.triage_sub_agent.models import TriageResult
from app.agents.data_sub_agent.models import DataAnalysisResponse, AnomalyDetectionResponse

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
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)
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
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        
        if not state.triage_result:
            errors.append("triage_result is None - required for pipeline continuation")
        else:
            errors.extend(self._validate_triage_required_fields(state.triage_result))
            warnings.extend(self._validate_triage_quality(state.triage_result))
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return self._create_validation_result("triage_result", errors, warnings, 
                                            context, duration_ms)
    
    def validate_data_artifact(self, state: DeepAgentState,
                             context: ValidationContext) -> ArtifactValidationResult:
        """Validate data_result artifact for handoff."""
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        
        if not state.data_result:
            errors.append("data_result is None - required for optimization handoff")
        else:
            errors.extend(self._validate_data_required_fields(state.data_result))
            warnings.extend(self._validate_data_quality(state.data_result))
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return self._create_validation_result("data_result", errors, warnings,
                                            context, duration_ms)
    
    def validate_optimization_artifact(self, state: DeepAgentState,
                                     context: ValidationContext) -> ArtifactValidationResult:
        """Validate optimization_result artifact for handoff."""
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        
        if not state.optimizations_result:
            errors.append("optimizations_result is None - required for action planning")
        else:
            errors.extend(self._validate_optimization_required_fields(state.optimizations_result))
            warnings.extend(self._validate_optimization_quality(state.optimizations_result))
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return self._create_validation_result("optimizations_result", errors, warnings,
                                            context, duration_ms)
    
    def _validate_triage_required_fields(self, triage_result: TriageResult) -> List[str]:
        """Check triage result has required fields."""
        errors = []
        if not triage_result.category or triage_result.category == "unknown":
            errors.append("category is required and cannot be 'unknown'")
        if triage_result.confidence_score < 0.5:
            errors.append(f"confidence_score too low: {triage_result.confidence_score}")
        if not triage_result.suggested_workflow.next_agent:
            errors.append("suggested_workflow.next_agent is required")
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
            if not data_result.query:
                errors.append("DataAnalysisResponse.query is required")
            if data_result.execution_time_ms < 0:
                errors.append("execution_time_ms cannot be negative")
        elif isinstance(data_result, AnomalyDetectionResponse):
            if data_result.confidence_score < 0.0 or data_result.confidence_score > 1.0:
                errors.append("AnomalyDetectionResponse.confidence_score must be 0-1")
        return errors
    
    def _validate_data_quality(self, 
                             data_result: Union[DataAnalysisResponse, AnomalyDetectionResponse]) -> List[str]:
        """Check data result quality indicators."""
        warnings = []
        if isinstance(data_result, DataAnalysisResponse):
            if not data_result.insights:
                warnings.append("No insights provided in DataAnalysisResponse")
            if data_result.execution_time_ms > 30000:  # 30 seconds
                warnings.append(f"Long execution time: {data_result.execution_time_ms}ms")
        elif isinstance(data_result, AnomalyDetectionResponse):
            if data_result.confidence_score < 0.7:
                warnings.append(f"Low confidence in anomaly detection: {data_result.confidence_score}")
        return warnings
    
    def _validate_optimization_required_fields(self, opt_result: OptimizationsResult) -> List[str]:
        """Check optimization result has required fields."""
        errors = []
        if not opt_result.optimization_type:
            errors.append("optimization_type is required")
        if not opt_result.recommendations:
            errors.append("recommendations list cannot be empty")
        if opt_result.confidence_score < 0.0 or opt_result.confidence_score > 1.0:
            errors.append("confidence_score must be between 0 and 1")
        return errors
    
    def _validate_optimization_quality(self, opt_result: OptimizationsResult) -> List[str]:
        """Check optimization result quality indicators."""
        warnings = []
        if opt_result.confidence_score < 0.8:
            warnings.append(f"Low optimization confidence: {opt_result.confidence_score}")
        if not opt_result.cost_savings and not opt_result.performance_improvement:
            warnings.append("No quantifiable benefits identified")
        if len(opt_result.recommendations) < 2:
            warnings.append("Few recommendations provided - may need deeper analysis")
        return warnings
    
    def _create_validation_result(self, artifact_type: str, errors: List[str], 
                                warnings: List[str], context: ValidationContext,
                                duration_ms: float) -> ArtifactValidationResult:
        """Create validation result object."""
        return ArtifactValidationResult(
            is_valid=len(errors) == 0,
            artifact_type=artifact_type,
            errors=errors,
            warnings=warnings,
            validation_context=context,
            validation_duration_ms=duration_ms
        )
    
    def store_validation_result(self, result: ArtifactValidationResult) -> None:
        """Store validation result for audit trail."""
        self.validation_history.append(result)
        if len(self.validation_history) > self.MAX_HISTORY_SIZE:
            self.validation_history = self.validation_history[-self.MAX_HISTORY_SIZE:]
        
        log_msg = f"Artifact validation: {result.artifact_type} - "
        log_msg += "PASSED" if result.is_valid else "FAILED"
        if result.errors:
            logger.error(f"{log_msg} - Errors: {result.errors}")
        elif result.warnings:
            logger.warning(f"{log_msg} - Warnings: {result.warnings}")
        else:
            logger.info(log_msg)
    
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
        context = ValidationContext(
            agent_name=from_agent,
            run_id=run_id,
            artifact_type="",
            user_request=state.user_request
        )
        
        # Determine which validation to run based on agent handoff
        if from_agent == "TriageSubAgent":
            context.artifact_type = "triage_result"
            result = self.validate_triage_artifact(state, context)
        elif from_agent == "DataSubAgent":
            context.artifact_type = "data_result"
            result = self.validate_data_artifact(state, context)
        elif from_agent.endswith("OptimizationsCoreSubAgent"):
            context.artifact_type = "optimizations_result"
            result = self.validate_optimization_artifact(state, context)
        else:
            logger.warning(f"No validation defined for handoff from {from_agent}")
            return
        
        self.store_validation_result(result)
        if not result.is_valid:
            raise ArtifactValidationError(
                f"Invalid handoff from {from_agent} to {to_agent}",
                result.artifact_type,
                result.errors
            )


# Global validator instance for use across the application
artifact_validator = ArtifactValidator()