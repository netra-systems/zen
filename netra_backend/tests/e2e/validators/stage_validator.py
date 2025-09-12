"""
Stage Validation Framework for E2E Agent Testing
Validates input, processing, and output at each agent stage.
Maximum 300 lines, functions  <= 8 lines.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
from netra_backend.app.schemas.shared_types import (
    AnomalyDetectionResponse,
    DataAnalysisResponse,
)
from netra_backend.tests.e2e.state_validation_utils import StateIntegrityChecker

class InputValidationResult(BaseModel):
    """Result of input validation with sanitization details."""
    is_valid: bool = Field(default=False)
    sanitized_input: Optional[str] = Field(default=None)
    schema_compliant: bool = Field(default=False)
    security_threats: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)

class ProcessingValidationResult(BaseModel):
    """Result of processing validation with state transition details."""
    is_valid: bool = Field(default=False)
    state_transitions_valid: bool = Field(default=False)
    agent_conditions_met: bool = Field(default=False)
    data_transforms_valid: bool = Field(default=False)
    processing_errors: List[str] = Field(default_factory=list)

class OutputValidationResult(BaseModel):
    """Result of output validation with format and completeness checks."""
    is_valid: bool = Field(default=False)
    format_valid: bool = Field(default=False)
    complete: bool = Field(default=False)
    error_handling_valid: bool = Field(default=False)
    output_errors: List[str] = Field(default_factory=list)

class StageValidationResult(BaseModel):
    """Comprehensive stage validation result."""
    stage_name: str
    input_validation: InputValidationResult
    processing_validation: ProcessingValidationResult
    output_validation: OutputValidationResult
    overall_success: bool = Field(default=False)
    checkpoint_passed: bool = Field(default=False)

class InputValidator:
    """Validates input schema compliance and sanitization."""
    
    def __init__(self):
        self.integrity_checker = StateIntegrityChecker()
    
    def validate_user_request(self, user_request: str) -> InputValidationResult:
        """Validate user request input."""
        result = InputValidationResult()
        result.sanitized_input = self._sanitize_input(user_request)
        result.schema_compliant = self._check_schema_compliance(user_request)
        result.security_threats = self._detect_security_threats(user_request)
        result.is_valid = result.schema_compliant and len(result.security_threats) == 0
        return result
    
    def _sanitize_input(self, input_text: str) -> str:
        """Sanitize input text."""
        if not isinstance(input_text, str):
            return str(input_text)
        sanitized = input_text.strip()[:10000]  # Length limit
        return sanitized
    
    def _check_schema_compliance(self, input_text: str) -> bool:
        """Check if input complies with expected schema."""
        if not input_text or len(input_text.strip()) == 0:
            return False
        if len(input_text) > 10000:  # Reasonable limit
            return False
        return True
    
    def _detect_security_threats(self, input_text: str) -> List[str]:
        """Detect potential security threats in input."""
        threats = []
        malicious_patterns = ['<script', 'javascript:', 'eval(', 'exec(']
        for pattern in malicious_patterns:
            if pattern.lower() in input_text.lower():
                threats.append(f"Potential injection: {pattern}")
        return threats

class ProcessingValidator:
    """Validates state transitions and agent conditions."""
    
    def __init__(self):
        self.integrity_checker = StateIntegrityChecker()
    
    def validate_triage_processing(self, state: DeepAgentState) -> ProcessingValidationResult:
        """Validate triage agent processing."""
        result = ProcessingValidationResult()
        try:
            self.integrity_checker.check_triage_completion_integrity(state)
            result.state_transitions_valid = True
            result.agent_conditions_met = self._check_triage_conditions(state)
            result.data_transforms_valid = self._validate_triage_transforms(state)
            result.is_valid = all([result.state_transitions_valid, 
                                 result.agent_conditions_met, 
                                 result.data_transforms_valid])
        except AssertionError as e:
            result.processing_errors.append(str(e))
        return result
    
    def validate_data_processing(self, state: DeepAgentState) -> ProcessingValidationResult:
        """Validate data agent processing."""
        result = ProcessingValidationResult()
        try:
            self.integrity_checker.check_data_completion_integrity(state)
            result.state_transitions_valid = True
            result.agent_conditions_met = self._check_data_conditions(state)
            result.data_transforms_valid = self._validate_data_transforms(state)
            result.is_valid = all([result.state_transitions_valid,
                                 result.agent_conditions_met,
                                 result.data_transforms_valid])
        except AssertionError as e:
            result.processing_errors.append(str(e))
        return result
    
    def _check_triage_conditions(self, state: DeepAgentState) -> bool:
        """Check if triage entry conditions were met."""
        return (state.triage_result is not None and 
                hasattr(state.triage_result, 'category') and
                len(state.triage_result.category) > 0)
    
    def _check_data_conditions(self, state: DeepAgentState) -> bool:
        """Check if data entry conditions were met."""
        return (state.data_result is not None and
                state.triage_result is not None)
    
    def _validate_triage_transforms(self, state: DeepAgentState) -> bool:
        """Validate triage data transformations."""
        if state.triage_result is None:
            return False
        return isinstance(state.triage_result, TriageResult)
    
    def _validate_data_transforms(self, state: DeepAgentState) -> bool:
        """Validate data analysis transformations."""
        if state.data_result is None:
            return False
        valid_types = (DataAnalysisResponse, AnomalyDetectionResponse)
        return isinstance(state.data_result, valid_types)

class OutputValidator:
    """Validates output format, completeness, and error handling."""
    
    def validate_triage_output(self, state: DeepAgentState) -> OutputValidationResult:
        """Validate triage output."""
        result = OutputValidationResult()
        result.format_valid = self._validate_triage_format(state)
        result.complete = self._validate_triage_completeness(state)
        result.error_handling_valid = self._validate_error_handling(state)
        result.is_valid = all([result.format_valid, result.complete, 
                              result.error_handling_valid])
        return result
    
    def validate_data_output(self, state: DeepAgentState) -> OutputValidationResult:
        """Validate data analysis output."""
        result = OutputValidationResult()
        result.format_valid = self._validate_data_format(state)
        result.complete = self._validate_data_completeness(state)
        result.error_handling_valid = self._validate_error_handling(state)
        result.is_valid = all([result.format_valid, result.complete,
                              result.error_handling_valid])
        return result
    
    def _validate_triage_format(self, state: DeepAgentState) -> bool:
        """Validate triage result format."""
        if state.triage_result is None:
            return False
        try:
            TriageResult.model_validate(state.triage_result.model_dump())
            return True
        except ValidationError:
            return False
    
    def _validate_data_format(self, state: DeepAgentState) -> bool:
        """Validate data result format."""
        if state.data_result is None:
            return False
        try:
            if isinstance(state.data_result, DataAnalysisResponse):
                DataAnalysisResponse.model_validate(state.data_result.model_dump())
            elif isinstance(state.data_result, AnomalyDetectionResponse):
                AnomalyDetectionResponse.model_validate(state.data_result.model_dump())
            return True
        except ValidationError:
            return False
    
    def _validate_triage_completeness(self, state: DeepAgentState) -> bool:
        """Validate triage result completeness."""
        if state.triage_result is None:
            return False
        required_fields = ['category', 'priority', 'user_intent']
        return all(hasattr(state.triage_result, field) for field in required_fields)
    
    def _validate_data_completeness(self, state: DeepAgentState) -> bool:
        """Validate data result completeness."""
        if state.data_result is None:
            return False
        if isinstance(state.data_result, DataAnalysisResponse):
            return hasattr(state.data_result, 'query') and hasattr(state.data_result, 'recommendations')
        elif isinstance(state.data_result, AnomalyDetectionResponse):
            return hasattr(state.data_result, 'anomalies_detected') and hasattr(state.data_result, 'confidence_score')
        return False
    
    def _validate_error_handling(self, state: DeepAgentState) -> bool:
        """Validate error handling is appropriate."""
        # Check that errors are properly captured if they exist
        if hasattr(state, 'messages') and state.messages:
            error_messages = [msg for msg in state.messages if 'error' in str(msg).lower()]
            return len(error_messages) == 0  # No unhandled errors
        return True

class StageValidator:
    """Comprehensive stage validation with checkpoints."""
    
    def __init__(self):
        self.input_validator = InputValidator()
        self.processing_validator = ProcessingValidator()
        self.output_validator = OutputValidator()
    
    def validate_triage_stage(self, state: DeepAgentState) -> StageValidationResult:
        """Validate complete triage stage."""
        input_result = self.input_validator.validate_user_request(state.user_request)
        processing_result = self.processing_validator.validate_triage_processing(state)
        output_result = self.output_validator.validate_triage_output(state)
        
        overall_success = all([input_result.is_valid, processing_result.is_valid, 
                              output_result.is_valid])
        
        return StageValidationResult(
            stage_name="triage",
            input_validation=input_result,
            processing_validation=processing_result,
            output_validation=output_result,
            overall_success=overall_success,
            checkpoint_passed=overall_success
        )
    
    def validate_data_stage(self, state: DeepAgentState) -> StageValidationResult:
        """Validate complete data analysis stage."""
        input_result = self.input_validator.validate_user_request(state.user_request)
        processing_result = self.processing_validator.validate_data_processing(state)
        output_result = self.output_validator.validate_data_output(state)
        
        overall_success = all([input_result.is_valid, processing_result.is_valid,
                              output_result.is_valid])
        
        return StageValidationResult(
            stage_name="data",
            input_validation=input_result,
            processing_validation=processing_result,
            output_validation=output_result,
            overall_success=overall_success,
            checkpoint_passed=overall_success
        )
    
    def create_checkpoint_report(self, stage_results: List[StageValidationResult]) -> Dict[str, Any]:
        """Create stage-by-stage checkpoint report."""
        total_stages = len(stage_results)
        passed_stages = sum(1 for result in stage_results if result.checkpoint_passed)
        
        return {
            "total_stages": total_stages,
            "passed_stages": passed_stages,
            "failed_stages": total_stages - passed_stages,
            "success_rate": passed_stages / total_stages if total_stages > 0 else 0,
            "stage_details": [
                {
                    "stage": result.stage_name,
                    "passed": result.checkpoint_passed,
                    "input_valid": result.input_validation.is_valid,
                    "processing_valid": result.processing_validation.is_valid,
                    "output_valid": result.output_validation.is_valid
                } for result in stage_results
            ]
        }