"""Input validation schemas and utilities for agent execution."""

from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, field_validator, ValidationError, ConfigDict
from app.agents.state import DeepAgentState
from app.logging_config import central_logger

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
        if not hasattr(v, 'user_request') or not v.user_request:
            raise ValueError("user_request is required for triage execution")
        
        user_request = v.user_request.strip()
        if len(user_request) < 3:
            raise ValueError("user_request must be at least 3 characters long")
        if len(user_request) > 10000:
            raise ValueError("user_request must be less than 10000 characters")
            
        return v


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
        # Reporting typically needs some data to report on
        required_fields = ['triage_result', 'data_analysis_result', 'user_request']
        has_data = any(hasattr(v, field) and getattr(v, field) for field in required_fields)
        
        if not has_data:
            raise ValueError("At least one of triage_result, data_analysis_result, or user_request is required for reporting")
        
        return v


class SyntheticDataExecutionInput(AgentExecutionInput):
    """Input validation for Synthetic Data sub-agent."""
    
    @field_validator('state')
    @classmethod
    def validate_synthetic_data_state(cls, v):
        """Validate state for synthetic data operations."""
        if hasattr(v, 'user_request') and v.user_request:
            # Check if request contains data generation parameters
            user_request = v.user_request.lower()
            valid_keywords = ['generate', 'synthetic', 'data', 'create', 'batch']
            if not any(keyword in user_request for keyword in valid_keywords):
                logger.warning("user_request may not be suitable for synthetic data generation")
        
        return v


class ValidationResult(BaseModel):
    """Result of input validation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_input: Optional[AgentExecutionInput] = None


class InputValidator:
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
    def validate_execution_input(
        cls, 
        agent_name: str, 
        state: DeepAgentState, 
        run_id: str, 
        stream_updates: bool = False
    ) -> ValidationResult:
        """Validate execution input for specific agent."""
        
        # Get the appropriate validation schema
        schema_class = cls.VALIDATION_SCHEMAS.get(agent_name, AgentExecutionInput)
        
        try:
            # Create the input object for validation
            input_data = {
                'state': state,
                'run_id': run_id, 
                'stream_updates': stream_updates
            }
            
            validated_input = schema_class(**input_data)
            
            return ValidationResult(
                is_valid=True,
                validated_input=validated_input
            )
            
        except ValidationError as e:
            error_messages = []
            warnings = []
            
            for error in e.errors():
                field = '.'.join(str(loc) for loc in error['loc'])
                message = f"{field}: {error['msg']}"
                
                # Some validations might be warnings rather than hard errors
                if 'warning' in error.get('type', '').lower():
                    warnings.append(message)
                else:
                    error_messages.append(message)
            
            return ValidationResult(
                is_valid=len(error_messages) == 0,
                errors=error_messages,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Unexpected validation error for {agent_name}: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Unexpected validation error: {str(e)}"]
            )
    
    @classmethod
    def validate_and_raise(
        cls, 
        agent_name: str, 
        state: DeepAgentState, 
        run_id: str, 
        stream_updates: bool = False
    ) -> AgentExecutionInput:
        """Validate input and raise exception if invalid."""
        
        result = cls.validate_execution_input(agent_name, state, run_id, stream_updates)
        
        if not result.is_valid:
            error_msg = f"Invalid input for {agent_name}: {'; '.join(result.errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Log warnings if any
        if result.warnings:
            for warning in result.warnings:
                logger.warning(f"{agent_name} validation warning: {warning}")
        
        return result.validated_input


def validate_agent_input(agent_name: str):
    """Decorator to validate agent execute method inputs."""
    def decorator(execute_method):
        async def wrapper(self, state: DeepAgentState, run_id: str, stream_updates: bool = False):
            # Validate inputs before execution
            try:
                InputValidator.validate_and_raise(agent_name, state, run_id, stream_updates)
            except ValueError as e:
                # Log validation failure and raise
                logger.error(f"Input validation failed for {agent_name}: {e}")
                raise e
            
            # Call the original execute method
            return await execute_method(self, state, run_id, stream_updates)
        
        return wrapper
    return decorator