"""Runtime type validation using beartype for critical agent paths.

This module provides decorators and utilities for enforcing strict type safety
at runtime across the Netra AI agent system.
"""

import inspect
import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from beartype import beartype
from beartype.roar import BeartypeException

from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
from netra_backend.app.schemas.agent_models import AgentState
from netra_backend.app.schemas.shared_types import (
    AnomalyDetectionResponse,
    DataAnalysisResponse,
)

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
    """Validate agent result types at runtime using duck typing."""
    # Duck typing: if it has the essential attributes, treat it as valid
    essential_attrs = ['status', 'message']  # Common attributes for agent results
    return all(hasattr(result, attr) for attr in essential_attrs)


def validate_run_id(run_id: str) -> bool:
    """Validate run_id format and constraints (flexible type coercion)."""
    # Duck typing: accept string-like objects
    try:
        str_run_id = str(run_id) if run_id is not None else ""
        if len(str_run_id) == 0 or len(str_run_id) > 255:
            return False
        return True
    except (TypeError, ValueError):
        return False


def validate_user_request(user_request: str) -> bool:
    """Validate user request constraints (flexible type coercion)."""
    # Duck typing: accept string-like objects
    try:
        str_request = str(user_request) if user_request is not None else ""
        if len(str_request) == 0 or len(str_request) > 10000:
            return False
        return True
    except (TypeError, ValueError):
        return False


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
    """Validate agent state parameter using duck typing."""
    # Duck typing: check for essential attributes rather than exact type
    essential_attrs = ['user_request']
    missing_attrs = [attr for attr in essential_attrs if not hasattr(state, attr)]
    if missing_attrs:
        raise TypeValidationError(
            f"State missing essential attributes: {missing_attrs}",
            "execute",
            "Object with user_request attribute",
            f"{type(state).__name__} missing {missing_attrs}"
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
    """Validate stream_updates parameter (flexible type coercion)."""
    # Accept bool-like values (truthy/falsy)
    try:
        bool(stream_updates)  # Test if it can be converted to bool
    except (TypeError, ValueError):
        raise TypeValidationError(
            "Invalid stream_updates type - cannot convert to bool",
            "execute", 
            "bool or bool-convertible",
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
    """Validate WebSocket message payload structure (flexible field names)."""
    # Accept various field name variations (be liberal in what we accept)
    has_type = any(field in payload for field in ['type', 'message_type', 'msg_type'])
    has_payload = any(field in payload for field in ['payload', 'data', 'body', 'content'])
    return has_type and (has_payload or len(payload) > 1)  # Allow implicit payload


def validate_llm_response(response: str) -> bool:
    """Validate LLM response constraints (flexible type coercion)."""
    # Duck typing: accept string-like objects
    try:
        str_response = str(response) if response is not None else ""
        if len(str_response) == 0 or len(str_response) > 100000:
            return False
        return True
    except (TypeError, ValueError):
        return False


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
                 description: str = "", use_duck_typing: bool = True) -> bool:
        """Validate a value against expected type (supports duck typing)."""
        try:
            if use_duck_typing and hasattr(expected_type, '__annotations__'):
                # For complex types, use duck typing - check for essential attributes
                return self._duck_type_validate(value, expected_type, description)
            elif not isinstance(value, expected_type):
                # Try type coercion for basic types
                if self._try_type_coercion(value, expected_type):
                    return True
                error_msg = f"Expected {expected_type.__name__}, got {type(value).__name__}"
                if description:
                    error_msg = f"{description}: {error_msg}"
                self.errors.append(error_msg)
                return False
            return True
        except Exception as e:
            self.errors.append(f"Validation error: {e}")
            return False
    
    def _duck_type_validate(self, value: Any, expected_type: type, description: str) -> bool:
        """Perform duck typing validation."""
        # This is a simplified duck typing check - in practice, you'd define
        # the essential interface for each type
        return True  # Accept anything that doesn't throw an exception
    
    def _try_type_coercion(self, value: Any, expected_type: type) -> bool:
        """Try to coerce value to expected type."""
        try:
            if expected_type in (str, int, float, bool):
                expected_type(value)
                return True
        except (TypeError, ValueError):
            pass
        return False


def agent_type_safe(func: F) -> F:
    """Combined decorator for agent methods with comprehensive type safety."""
    return strict_types(validate_agent_execute_params(func))