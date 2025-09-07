"""
Unified Agent Testing Framework

This module provides a standardized approach to testing all agent types consistently,
handling both Pydantic model responses and dictionary responses.

Business Value: Ensures reliable agent testing across all system components,
reducing test maintenance burden and improving test reliability.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union, Callable, TypeVar
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel
import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


class ResultType(Enum):
    """Enumeration of agent result types for validation"""
    PYDANTIC_MODEL = "pydantic_model"
    DICTIONARY = "dictionary"
    STATE_MUTATION = "state_mutation"
    NONE_RESULT = "none_result"


class ExecutionStatus(Enum):
    """Standard execution status values"""
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


@dataclass
class ValidationConfig:
    """Configuration for result validation"""
    required_fields: List[str]
    optional_fields: List[str] = None
    status_field: Optional[str] = "status"
    expected_status: str = "success"
    allow_partial: bool = False
    timeout_seconds: float = 30.0
    business_validators: Dict[str, Callable[[Any], bool]] = None

    def __post_init__(self):
        if self.optional_fields is None:
            self.optional_fields = []
        if self.business_validators is None:
            self.business_validators = {}


@dataclass
class ValidationResult:
    """Result of validation operation"""
    success: bool
    result_type: ResultType
    validated_data: Any
    missing_fields: List[str]
    validation_errors: List[str]
    execution_time_ms: float


class AgentResultValidator:
    """
    Unified validator for all agent response types.
    
    Handles:
    - Pydantic model responses (OptimizationsResult, ActionPlanResult, etc.)
    - Dictionary responses with status fields (TriageResult)
    - State mutations without explicit returns
    - Error conditions and partial results
    """
    
    def __init__(self):
        self.logger = central_logger.get_logger(f"{__name__}.AgentResultValidator")
    
    def validate_execution_success(
        self, 
        state: DeepAgentState, 
        result_field: str,
        config: ValidationConfig
    ) -> ValidationResult:
        """
        Validate that agent execution was successful.
        
        Args:
            state: Agent state after execution
            result_field: Field name to check (e.g., 'triage_result', 'optimizations_result')
            config: Validation configuration
            
        Returns:
            ValidationResult with success status and validated data
        """
        start_time = time.time()
        validation_errors = []
        missing_fields = []
        
        try:
            # Get the result from state
            result = getattr(state, result_field, None)
            
            if result is None:
                return ValidationResult(
                    success=False,
                    result_type=ResultType.NONE_RESULT,
                    validated_data=None,
                    missing_fields=[result_field],
                    validation_errors=[f"Result field '{result_field}' is None"],
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Determine result type and validate accordingly
            if isinstance(result, BaseModel):
                return self._validate_pydantic_result(result, config, start_time)
            elif isinstance(result, dict):
                return self._validate_dict_result(result, config, start_time)
            else:
                validation_errors.append(f"Unsupported result type: {type(result)}")
                return ValidationResult(
                    success=False,
                    result_type=ResultType.NONE_RESULT,
                    validated_data=result,
                    missing_fields=missing_fields,
                    validation_errors=validation_errors,
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
        except Exception as e:
            validation_errors.append(f"Validation exception: {str(e)}")
            return ValidationResult(
                success=False,
                result_type=ResultType.NONE_RESULT,
                validated_data=None,
                missing_fields=missing_fields,
                validation_errors=validation_errors,
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _validate_pydantic_result(
        self, 
        result: BaseModel, 
        config: ValidationConfig, 
        start_time: float
    ) -> ValidationResult:
        """Validate Pydantic model result"""
        validation_errors = []
        missing_fields = []
        
        # Check required fields
        for field_name in config.required_fields:
            if not hasattr(result, field_name):
                missing_fields.append(field_name)
            else:
                field_value = getattr(result, field_name)
                if field_value is None:
                    missing_fields.append(f"{field_name} (None value)")
        
        # Check for error field (common pattern)
        if hasattr(result, 'error'):
            error_value = getattr(result, 'error')
            if error_value and error_value != "":
                validation_errors.append(f"Result contains error: {error_value}")
        
        # Apply business logic validators
        for field_name, validator in config.business_validators.items():
            if hasattr(result, field_name):
                field_value = getattr(result, field_name)
                try:
                    if not validator(field_value):
                        validation_errors.append(f"Business validation failed for {field_name}")
                except Exception as e:
                    validation_errors.append(f"Business validator error for {field_name}: {str(e)}")
        
        success = len(missing_fields) == 0 and len(validation_errors) == 0
        
        return ValidationResult(
            success=success,
            result_type=ResultType.PYDANTIC_MODEL,
            validated_data=result,
            missing_fields=missing_fields,
            validation_errors=validation_errors,
            execution_time_ms=(time.time() - start_time) * 1000
        )
    
    def _validate_dict_result(
        self, 
        result: Dict[str, Any], 
        config: ValidationConfig, 
        start_time: float
    ) -> ValidationResult:
        """Validate dictionary result"""
        validation_errors = []
        missing_fields = []
        
        # Check status field if specified
        if config.status_field:
            if config.status_field not in result:
                missing_fields.append(config.status_field)
            else:
                status_value = result[config.status_field]
                if status_value != config.expected_status:
                    if not (config.allow_partial and status_value == "partial"):
                        validation_errors.append(
                            f"Unexpected status: {status_value}, expected: {config.expected_status}"
                        )
        
        # Check required fields
        for field_name in config.required_fields:
            if field_name not in result:
                missing_fields.append(field_name)
            elif result[field_name] is None:
                missing_fields.append(f"{field_name} (None value)")
        
        # Apply business logic validators
        for field_name, validator in config.business_validators.items():
            if field_name in result:
                field_value = result[field_name]
                try:
                    if not validator(field_value):
                        validation_errors.append(f"Business validation failed for {field_name}")
                except Exception as e:
                    validation_errors.append(f"Business validator error for {field_name}: {str(e)}")
        
        success = len(missing_fields) == 0 and len(validation_errors) == 0
        
        return ValidationResult(
            success=success,
            result_type=ResultType.DICTIONARY,
            validated_data=result,
            missing_fields=missing_fields,
            validation_errors=validation_errors,
            execution_time_ms=(time.time() - start_time) * 1000
        )


class AgentTestExecutor:
    """
    Standardized agent execution for tests with error handling and timeout protection.
    """
    
    def __init__(self):
        self.logger = central_logger.get_logger(f"{__name__}.AgentTestExecutor")
    
    async def execute_agent(
        self,
        agent: Any,
        state: DeepAgentState,
        run_id: str,
        stream_updates: bool = False,
        timeout_seconds: float = 30.0
    ) -> tuple[bool, Optional[str]]:
        """
        Execute agent with standardized error handling.
        
        Args:
            agent: Agent instance to execute
            state: Agent state
            run_id: Execution run ID
            stream_updates: Whether to stream updates
            timeout_seconds: Execution timeout
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Execute with timeout
            await asyncio.wait_for(
                agent.execute(state, run_id, stream_updates),
                timeout=timeout_seconds
            )
            return True, None
            
        except asyncio.TimeoutError:
            error_msg = f"Agent execution timed out after {timeout_seconds}s"
            self.logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Agent execution failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    async def execute_with_metrics(
        self,
        agent: Any,
        state: DeepAgentState,
        run_id: str,
        stream_updates: bool = False,
        timeout_seconds: float = 30.0
    ) -> tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Execute agent with performance metrics collection.
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str], metrics: Dict)
        """
        start_time = time.time()
        
        success, error_msg = await self.execute_agent(
            agent, state, run_id, stream_updates, timeout_seconds
        )
        
        execution_time = time.time() - start_time
        
        metrics = {
            "execution_time_ms": execution_time * 1000,
            "success": success,
            "timeout_seconds": timeout_seconds,
            "run_id": run_id
        }
        
        return success, error_msg, metrics


class ResultAssertion:
    """
    Type-safe assertion helpers for agent test validation.
    """
    
    @staticmethod
    def assert_success(validation_result: ValidationResult, custom_message: str = ""):
        """Assert that validation was successful"""
        if not validation_result.success:
            error_details = []
            if validation_result.missing_fields:
                error_details.append(f"Missing fields: {validation_result.missing_fields}")
            if validation_result.validation_errors:
                error_details.append(f"Validation errors: {validation_result.validation_errors}")
            
            full_message = f"Agent validation failed. {custom_message}. Details: {'; '.join(error_details)}"
            raise AssertionError(full_message)
    
    @staticmethod
    def assert_field_exists(result: Union[BaseModel, Dict], field_name: str):
        """Assert that a field exists in the result"""
        if isinstance(result, BaseModel):
            assert hasattr(result, field_name), f"Pydantic model missing field: {field_name}"
        elif isinstance(result, dict):
            assert field_name in result, f"Dictionary missing field: {field_name}"
        else:
            raise AssertionError(f"Unsupported result type for field check: {type(result)}")
    
    @staticmethod
    def assert_field_value(
        result: Union[BaseModel, Dict], 
        field_name: str, 
        expected_type: Type,
        validator: Optional[Callable[[Any], bool]] = None,
        not_empty: bool = False
    ):
        """Assert field value with type safety"""
        ResultAssertion.assert_field_exists(result, field_name)
        
        if isinstance(result, BaseModel):
            field_value = getattr(result, field_name)
        else:
            field_value = result[field_name]
        
        # Type check
        if not isinstance(field_value, expected_type):
            raise AssertionError(f"Field {field_name} has type {type(field_value)}, expected {expected_type}")
        
        # Not empty check
        if not_empty:
            if isinstance(field_value, (str, list, dict)) and len(field_value) == 0:
                raise AssertionError(f"Field {field_name} is empty")
        
        # Custom validator
        if validator and not validator(field_value):
            raise AssertionError(f"Field {field_name} failed custom validation")
    
    @staticmethod
    def assert_business_logic(result: Any, validators: Dict[str, Callable[[Any], bool]]):
        """Assert business logic constraints"""
        for field_name, validator in validators.items():
            ResultAssertion.assert_field_exists(result, field_name)
            
            if isinstance(result, BaseModel):
                field_value = getattr(result, field_name)
            else:
                field_value = result[field_name]
            
            if not validator(field_value):
                raise AssertionError(f"Business logic validation failed for {field_name}")


# Convenience function for common test patterns
def create_standard_validation_config(
    required_fields: List[str],
    business_validators: Optional[Dict[str, Callable]] = None,
    allow_partial: bool = False
) -> ValidationConfig:
    """Create a standard validation configuration"""
    return ValidationConfig(
        required_fields=required_fields,
        optional_fields=[],
        business_validators=business_validators or {},
        allow_partial=allow_partial
    )


# Execution Context for Testing
@dataclass
class TestExecutionContext:
    """Test execution context that matches regression test expectations."""
    user_id: str
    thread_id: str
    message_id: str
    session_id: str
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()

    def dict(self) -> Dict[str, Any]:
        """Return dict representation for backward compatibility."""
        return {
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'message_id': self.message_id,
            'session_id': self.session_id,
            'metadata': self.metadata,
            'created_at': self.created_at
        }


def create_test_execution_context(
    user_id: str = "test-user-123",
    thread_id: str = "test-thread-456", 
    message_id: str = "test-message-789",
    session_id: str = "test-session-000",
    metadata: Optional[Dict[str, Any]] = None
) -> TestExecutionContext:
    """
    Create a test execution context for regression tests.
    
    Args:
        user_id: User identifier
        thread_id: Thread identifier
        message_id: Message identifier
        session_id: Session identifier
        metadata: Optional metadata dictionary
        
    Returns:
        TestExecutionContext instance
    """
    return TestExecutionContext(
        user_id=user_id,
        thread_id=thread_id,
        message_id=message_id,
        session_id=session_id,
        metadata=metadata or {}
    )


# Common business validators
class CommonValidators:
    """Common validation functions for business logic"""
    
    @staticmethod
    def confidence_score(value: float) -> bool:
        """Validate confidence score is between 0 and 1"""
        return isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0
    
    @staticmethod
    def not_empty_list(value: List) -> bool:
        """Validate list is not empty"""
        return isinstance(value, list) and len(value) > 0
    
    @staticmethod
    def not_empty_string(value: str) -> bool:
        """Validate string is not empty"""
        return isinstance(value, str) and len(value.strip()) > 0
    
    @staticmethod
    def positive_number(value: Union[int, float]) -> bool:
        """Validate number is positive"""
        return isinstance(value, (int, float)) and value > 0
    
    @staticmethod
    def non_negative_number(value: Union[int, float]) -> bool:
        """Validate number is non-negative"""
        return isinstance(value, (int, float)) and value >= 0


# =============================================================================
# E2E TEST HELPERS
# =============================================================================

def create_test_agent(agent_type: str = "test_agent", **kwargs):
    """Create a test agent instance for E2E testing."""
    from unittest.mock import MagicMock
    
    # Create a mock agent with common methods
    mock_agent = MagicMock()
    mock_agent.agent_type = agent_type
    mock_agent.name = kwargs.get("name", f"{agent_type}_{int(time.time())}")
    
    # Add common agent methods
    mock_agent.execute = lambda *args, **kwargs: {"result": "test_execution_result"}
    mock_agent.get_capabilities = lambda: ["test_capability_1", "test_capability_2"] 
    mock_agent.is_ready = lambda: True
    
    return mock_agent


def assert_agent_execution(result: Dict[str, Any], expected_status: str = "success"):
    """Assert agent execution completed successfully."""
    assert isinstance(result, dict), f"Expected dict result, got {type(result)}"
    
    # Check for common execution indicators
    if "status" in result:
        assert result["status"] == expected_status, f"Expected status {expected_status}, got {result.get('status')}"
    
    # Check result is not empty
    assert len(result) > 0, "Agent execution result should not be empty"