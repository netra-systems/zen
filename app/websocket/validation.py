"""WebSocket message validation orchestrator.

Orchestrates micro-validators for WebSocket message validation and sanitization.
Composed of performance-optimized micro-validators (≤8 lines each).
"""

from typing import Dict, Any, Union

from app.logging_config import central_logger
from app.schemas.websocket_message_types import WebSocketValidationError

# Import micro-validators
from app.websocket.validation_core import (
    DateTimeEncoder, validate_message_is_dict, validate_type_field_exists,
    validate_message_type_enum, validate_with_pydantic_model,
    validate_message_size, check_message_type_supported
)
from app.websocket.validation_security import (
    validate_payload_security, check_text_length_limit
)
from app.websocket.validation_sanitization import (
    sanitize_message_content
)
from app.websocket.validation_errors import (
    handle_validation_exception, create_unknown_message_fallback,
    create_graceful_validation_result, log_validation_warning
)

logger = central_logger.get_logger(__name__)


class MessageValidator:
    """Orchestrates micro-validators for WebSocket message validation."""
    
    def __init__(self, max_message_size: int = 1024 * 1024, max_text_length: int = 10000, 
                 allow_unknown_types: bool = False):
        """Initialize validator with performance limits."""
        self.max_message_size = max_message_size
        self.max_text_length = max_text_length
        self.allow_unknown_types = allow_unknown_types
    
    def validate_message(self, message: Dict[str, Any]) -> Union[bool, WebSocketValidationError]:
        """Orchestrate validation using micro-validators."""
        try:
            error = self._run_validation_pipeline(message)
            return error if error else True
        except Exception as e:
            return handle_validation_exception(e, message)
    
    def _run_validation_pipeline(self, message: Dict[str, Any]) -> Union[None, WebSocketValidationError]:
        """Run complete validation pipeline using micro-validators."""
        checks = self._create_validation_checks(message)
        return self._run_validation_checks(checks)
    
    def _run_validation_checks(self, checks: list) -> Union[None, WebSocketValidationError]:
        """Run validation checks and return first error found."""
        for check in checks:
            error = check()
            if error:
                return error
        return None
    
    def sanitize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize message using micro-sanitizers."""
        return sanitize_message_content(message)
    
    def validate_message_type(self, message_type: str) -> bool:
        """Validate message type support using micro-validator."""
        return check_message_type_supported(message_type)
    
    def handle_unknown_message_type(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown message type using micro-handlers."""
        return create_unknown_message_fallback(message)
    
    def _create_validation_checks(self, message: Dict[str, Any]) -> list:
        """Create list of validation checks to run."""
        basic_checks = self._create_basic_checks(message)
        advanced_checks = self._create_advanced_checks(message)
        return basic_checks + advanced_checks
    
    def _create_basic_checks(self, message: Dict[str, Any]) -> list:
        """Create basic validation checks."""
        return [
            lambda: validate_message_is_dict(message),
            lambda: validate_type_field_exists(message),
            lambda: validate_payload_security(message)
        ]
    
    def _create_advanced_checks(self, message: Dict[str, Any]) -> list:
        """Create advanced validation checks."""
        return [
            lambda: validate_message_type_enum(message.get('type'), self.allow_unknown_types),
            lambda: validate_with_pydantic_model(message),
            lambda: validate_message_size(message, self.max_message_size)
        ]
    
    def create_graceful_validation_result(self, message: Dict[str, Any], 
                                        validation_error: WebSocketValidationError) -> Dict[str, Any]:
        """Create graceful validation result using micro-handlers."""
        return create_graceful_validation_result(message, validation_error)
    


# Performance-optimized validator instances using micro-validators
default_message_validator = MessageValidator()
flexible_message_validator = MessageValidator(allow_unknown_types=True)