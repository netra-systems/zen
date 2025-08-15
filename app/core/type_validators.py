"""Runtime type validation using beartype for critical agent paths.

This module provides decorators and utilities for enforcing strict type safety
at runtime across the Netra AI agent system.
"""

from typing import Union, Dict, List, Optional, Callable, TypeVar, Any
from functools import wraps
import inspect
import logging
from beartype import beartype
from beartype.roar import BeartypeException

from app.agents.triage_sub_agent.models import TriageResult
from app.agents.data_sub_agent.models import DataAnalysisResponse, AnomalyDetectionResponse
from app.schemas.shared_types import AgentState

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

logger = logging.getLogger(__name__)


class TypeValidationError(Exception):
    """Raised when runtime type validation fails."""
    
    def __init__(self, message: str, function_name: str, 
                 expected_type: str, actual_type: str):
        self.function_name = function_name
        self.expected_type = expected_type
        self.actual_type = actual_type
        super().__init__(message)


def validate_agent_result(result: Union[TriageResult, DataAnalysisResponse, 
                                      AnomalyDetectionResponse]) -> bool:
    """Validate agent result types at runtime."""
    valid_types = (TriageResult, DataAnalysisResponse, AnomalyDetectionResponse)
    return isinstance(result, valid_types)


def validate_run_id(run_id: str) -> bool:
    """Validate run_id format and constraints."""
    if not isinstance(run_id, str):
        return False
    if len(run_id) == 0 or len(run_id) > 255:
        return False
    return True


def validate_user_request(user_request: str) -> bool:
    """Validate user request constraints."""
    if not isinstance(user_request, str):
        return False
    if len(user_request) == 0 or len(user_request) > 10000:
        return False
    return True


def strict_types(func: F) -> F:
    """Decorator that enforces strict typing with beartype."""
    @beartype
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except BeartypeException as e:
            _log_type_error(func.__name__, str(e))
            raise TypeValidationError(
                message=f"Type validation failed in {func.__name__}: {e}",
                function_name=func.__name__,
                expected_type="See function signature",
                actual_type="Invalid type provided"
            )
    return wrapper


def validate_agent_execute_params(func: F) -> F:
    """Decorator for validating agent execute method parameters."""
    @wraps(func)
    async def wrapper(self, state: AgentState, run_id: str, 
                     stream_updates: bool = False):
        _validate_execute_state(state)
        _validate_execute_run_id(run_id)
        _validate_execute_stream_flag(stream_updates)
        return await func(self, state, run_id, stream_updates)
    return wrapper


def _validate_execute_state(state: AgentState) -> None:
    """Validate agent state parameter."""
    if not hasattr(state, 'user_request'):
        raise TypeValidationError(
            "State missing user_request",
            "execute",
            "AgentState with user_request",
            type(state).__name__
        )


def _validate_execute_run_id(run_id: str) -> None:
    """Validate run_id parameter."""
    if not validate_run_id(run_id):
        raise TypeValidationError(
            "Invalid run_id format",
            "execute",
            "str (1-255 chars)",
            f"str ({len(run_id)} chars)" if isinstance(run_id, str) else type(run_id).__name__
        )


def _validate_execute_stream_flag(stream_updates: bool) -> None:
    """Validate stream_updates parameter."""
    if not isinstance(stream_updates, bool):
        raise TypeValidationError(
            "Invalid stream_updates type",
            "execute", 
            "bool",
            type(stream_updates).__name__
        )


def _log_type_error(function_name: str, error_message: str) -> None:
    """Log type validation errors."""
    logger.error(
        f"Type validation failed in {function_name}: {error_message}",
        extra={
            "function": function_name,
            "error": error_message,
            "validation_type": "beartype"
        }
    )


def validate_websocket_payload(payload: Dict[str, Any]) -> bool:
    """Validate WebSocket message payload structure."""
    required_fields = {'type', 'payload'}
    return all(field in payload for field in required_fields)


def validate_llm_response(response: str) -> bool:
    """Validate LLM response constraints."""
    if not isinstance(response, str):
        return False
    if len(response) == 0 or len(response) > 100000:
        return False
    return True


class StrictTypeChecker:
    """Context manager for strict type checking within code blocks."""
    
    def __init__(self, enable_logging: bool = True):
        self.enable_logging = enable_logging
        self.errors = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is TypeValidationError and self.enable_logging:
            logger.error(f"Type validation failed: {exc_val}")
        return False
    
    def validate(self, value: Any, expected_type: type, 
                 description: str = "") -> bool:
        """Validate a value against expected type."""
        try:
            if not isinstance(value, expected_type):
                error_msg = f"Expected {expected_type.__name__}, got {type(value).__name__}"
                if description:
                    error_msg = f"{description}: {error_msg}"
                self.errors.append(error_msg)
                return False
            return True
        except Exception as e:
            self.errors.append(f"Validation error: {e}")
            return False


def agent_type_safe(func: F) -> F:
    """Combined decorator for agent methods with comprehensive type safety."""
    return strict_types(validate_agent_execute_params(func))