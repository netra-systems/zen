"""Input validation schemas and utilities for agent execution."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import ValidationResult

logger = central_logger.get_logger(__name__)


class AgentExecutionInput(BaseModel):
    """Base input validation for agent execution."""
    state: DeepAgentState
    run_id: str = Field(..., min_length=1, max_length=255, pattern="^[a-zA-Z0-9_-]+$")
    stream_updates: bool = Field(default=False)
    
    @field_validator('run_id')
    @classmethod
    def validate_run_id(cls, v):
        """Validate run_id format."""
        if not v or not v.strip():
            raise ValueError("run_id cannot be empty or whitespace")
        return v.strip()

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TriageExecutionInput(AgentExecutionInput):
    """Input validation for Triage sub-agent."""
    
    @field_validator('state')
    @classmethod
    def validate_triage_state(cls, v):
        """Validate state has required fields for triage."""
        cls._check_user_request_exists(v)
        user_request = v.user_request.strip()
        cls._validate_user_request_length(user_request)
        return v
    
    @classmethod
    def _check_user_request_exists(cls, v):
        """Check if user_request field exists and is not empty."""
        if not hasattr(v, 'user_request') or not v.user_request:
            raise ValueError("user_request is required for triage execution")
    
    @classmethod
    def _validate_user_request_length(cls, user_request: str):
        """Validate user_request length requirements."""
        if len(user_request) < 3:
            raise ValueError("user_request must be at least 3 characters long")
        if len(user_request) > 10000:
            raise ValueError("user_request must be less than 10000 characters")


class DataExecutionInput(AgentExecutionInput):
    """Input validation for Data sub-agent."""
    
    @field_validator('state')
    @classmethod
    def validate_data_state(cls, v):
        """Validate state for data analysis operations."""
        # Data agent can work with minimal state, but validate what's there
        if hasattr(v, 'user_request') and v.user_request:
            if len(v.user_request) > 10000:
                raise ValueError("user_request must be less than 10000 characters")
        
        return v


class OptimizationExecutionInput(AgentExecutionInput):
    """Input validation for Optimization sub-agent."""
    
    @field_validator('state')
    @classmethod
    def validate_optimization_state(cls, v):
        """Validate state for optimization operations."""
        if hasattr(v, 'triage_result') and v.triage_result:
            # Optimization works better with triage results
            if not isinstance(v.triage_result, dict):
                raise ValueError("triage_result must be a dictionary")
        
        return v


class ActionsExecutionInput(AgentExecutionInput):
    """Input validation for Actions sub-agent."""
    
    @field_validator('state')
    @classmethod
    def validate_actions_state(cls, v):
        """Validate state for actions execution."""
        if hasattr(v, 'user_request') and v.user_request:
            user_request = v.user_request.strip()
            if len(user_request) < 1:
                raise ValueError("user_request cannot be empty for actions")
        
        return v


class ReportingExecutionInput(AgentExecutionInput):
    """Input validation for Reporting sub-agent."""
    
    @field_validator('state')
    @classmethod
    def validate_reporting_state(cls, v):
        """Validate state for reporting operations."""
        required_fields = ['triage_result', 'data_analysis_result', 'user_request']
        has_data = cls._check_reporting_data_exists(v, required_fields)
        cls._validate_reporting_requirements(has_data)
        return v
    
    @classmethod
    def _check_reporting_data_exists(cls, v, required_fields: list) -> bool:
        """Check if any required reporting data exists."""
        return any(hasattr(v, field) and getattr(v, field) for field in required_fields)
    
    @classmethod
    def _validate_reporting_requirements(cls, has_data: bool):
        """Validate that reporting has required data."""
        if not has_data:
            raise ValueError("At least one of triage_result, data_analysis_result, or user_request is required for reporting")


class SyntheticDataExecutionInput(AgentExecutionInput):
    """Input validation for Synthetic Data sub-agent."""
    
    @field_validator('state')
    @classmethod
    def validate_synthetic_data_state(cls, v):
        """Validate state for synthetic data operations."""
        if hasattr(v, 'user_request') and v.user_request:
            cls._validate_synthetic_data_keywords(v.user_request)
        return v
    
    @classmethod
    def _validate_synthetic_data_keywords(cls, user_request: str):
        """Validate that user request contains synthetic data keywords."""
        user_request_lower = user_request.lower()
        valid_keywords = ['generate', 'synthetic', 'data', 'create', 'batch']
        if not any(keyword in user_request_lower for keyword in valid_keywords):
            logger.warning("user_request may not be suitable for synthetic data generation")


# ValidationResult now imported from shared_types.py


class AgentInputValidator:
    """Central input validator for all agents."""
    
    # Mapping of agent names to their validation schemas
    VALIDATION_SCHEMAS = {
        'TriageSubAgent': TriageExecutionInput,
        'DataSubAgent': DataExecutionInput, 
        'OptimizationsCoreSubAgent': OptimizationExecutionInput,
        'ActionsToMeetGoalsSubAgent': ActionsExecutionInput,
        'ReportingSubAgent': ReportingExecutionInput,
        'SyntheticDataSubAgent': SyntheticDataExecutionInput,
    }
    
    @classmethod
    def validate_execution_input(cls, agent_name: str, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> ValidationResult:
        """Validate execution input for specific agent."""
        return cls._execute_validation_flow(agent_name, state, run_id, stream_updates)
    
    @classmethod
    def _get_validation_schema(cls, agent_name: str):
        """Get the appropriate validation schema for agent."""
        return cls.VALIDATION_SCHEMAS.get(agent_name, AgentExecutionInput)
    
    @classmethod
    def _create_input_data(cls, state: DeepAgentState, run_id: str, stream_updates: bool) -> dict:
        """Create input data dictionary for validation."""
        return {
            'state': state,
            'run_id': run_id, 
            'stream_updates': stream_updates
        }
    
    @classmethod
    def _create_success_result(cls, validated_input) -> ValidationResult:
        """Create successful validation result."""
        return ValidationResult(
            is_valid=True,
            validated_input=validated_input
        )
    
    @classmethod
    def _handle_validation_error(cls, e: ValidationError) -> ValidationResult:
        """Handle Pydantic validation errors."""
        error_messages, warnings = cls._process_validation_errors(e)
        return ValidationResult(
            is_valid=len(error_messages) == 0,
            errors=error_messages,
            warnings=warnings
        )
    
    @classmethod
    def _process_validation_errors(cls, e: ValidationError) -> tuple[list, list]:
        """Process validation errors into messages and warnings."""
        error_messages = []
        warnings = []
        
        for error in e.errors():
            field, message = cls._format_validation_error(error)
            cls._categorize_validation_message(error, message, error_messages, warnings)
        
        return error_messages, warnings
    
    @classmethod
    def _format_validation_error(cls, error: dict) -> tuple[str, str]:
        """Format validation error into field and message."""
        field = '.'.join(str(loc) for loc in error['loc'])
        message = f"{field}: {error['msg']}"
        return field, message
    
    @classmethod
    def _categorize_validation_message(cls, error: dict, message: str, error_messages: list, warnings: list):
        """Categorize validation message as error or warning."""
        if 'warning' in error.get('type', '').lower():
            warnings.append(message)
        else:
            error_messages.append(message)
    
    @classmethod
    def _execute_validation_flow(cls, agent_name: str, state: DeepAgentState, run_id: str, stream_updates: bool) -> ValidationResult:
        """Execute complete validation flow."""
        schema_class = cls._get_validation_schema(agent_name)
        input_data = cls._create_input_data(state, run_id, stream_updates)
        return cls._perform_validation(schema_class, input_data, agent_name)
    
    @classmethod
    def _perform_validation(cls, schema_class, input_data: dict, agent_name: str) -> ValidationResult:
        """Perform actual validation with error handling."""
        try:
            validated_input = schema_class(**input_data)
            return cls._create_success_result(validated_input)
        except ValidationError as e:
            return cls._handle_validation_error(e)
        except Exception as e:
            return cls._handle_unexpected_error(agent_name, e)
    
    @classmethod
    def _handle_unexpected_error(cls, agent_name: str, e: Exception) -> ValidationResult:
        """Handle unexpected validation errors."""
        logger.error(f"Unexpected validation error for {agent_name}: {e}")
        return ValidationResult(
            is_valid=False,
            errors=[f"Unexpected validation error: {str(e)}"]
        )

    @classmethod
    def validate_and_raise(cls, agent_name: str, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> AgentExecutionInput:
        """Validate input and raise exception if invalid."""
        result = cls.validate_execution_input(agent_name, state, run_id, stream_updates)
        return cls._process_validation_result(result, agent_name)
    
    @classmethod
    def _process_validation_result(cls, result: ValidationResult, agent_name: str) -> object:
        """Process validation result and return validated input."""
        cls._check_validation_result(result, agent_name)
        cls._log_validation_warnings(result, agent_name)
        return result.validated_input
    
    @classmethod
    def _check_validation_result(cls, result: ValidationResult, agent_name: str) -> None:
        """Check validation result and raise if invalid."""
        if not result.is_valid:
            error_msg = f"Invalid input for {agent_name}: {'; '.join(result.errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    @classmethod
    def _log_validation_warnings(cls, result: ValidationResult, agent_name: str) -> None:
        """Log validation warnings if any."""
        if result.warnings:
            for warning in result.warnings:
                logger.warning(f"{agent_name} validation warning: {warning}")


# Keep backward compatibility with InputValidator alias
InputValidator = AgentInputValidator


def validate_agent_input(agent_name: str):
    """Decorator to validate agent execute method inputs."""
    def decorator(execute_method):
        async def wrapper(self, state: DeepAgentState, run_id: str, stream_updates: bool = False):
            _validate_inputs_with_logging(agent_name, state, run_id, stream_updates)
            return await execute_method(self, state, run_id, stream_updates)
        return wrapper
    return decorator

def _validate_inputs_with_logging(agent_name: str, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
    """Validate inputs with proper error logging."""
    try:
        AgentInputValidator.validate_and_raise(agent_name, state, run_id, stream_updates)
    except ValueError as e:
        logger.error(f"Input validation failed for {agent_name}: {e}")
        raise e