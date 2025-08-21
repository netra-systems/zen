"""WebSocket message validation orchestrator.

Orchestrates micro-validators for WebSocket message validation and sanitization.
Composed of performance-optimized micro-validators (≤8 lines each).
"""

from typing import Any, Dict, Union

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.websocket_message_types import WebSocketValidationError

# Import micro-validators
from netra_backend.app.websocket.validation_core import (
    DateTimeEncoder,
    check_message_type_supported,
    validate_message_is_dict,
    validate_message_size,
    validate_message_type_enum,
    validate_type_field_exists,
    validate_with_pydantic_model,
)
from netra_backend.app.websocket.validation_errors import (
    create_graceful_validation_result,
    create_unknown_message_fallback,
    handle_validation_exception,
    log_validation_warning,
)
from netra_backend.app.websocket.validation_sanitization import sanitize_message_content
from netra_backend.app.websocket.validation_security import (
    check_text_length_limit,
    validate_payload_security,
)

logger = central_logger.get_logger(__name__)


class MessageValidator:
    """Orchestrates micro-validators for WebSocket message validation."""
    
    def __init__(self, max_message_size: int = 1024 * 1024, max_text_length: int = 10000, 
                 allow_unknown_types: bool = True, strict_mode: bool = False):
        """Initialize validator with performance limits.
        
        Args:
            max_message_size: Maximum message size in bytes
            max_text_length: Maximum text field length
            allow_unknown_types: Whether to allow unknown message types (default: True for pragmatic rigor)
            strict_mode: Whether to use strict validation (default: False for resilience)
        """
        self.max_message_size = max_message_size
        self.max_text_length = max_text_length
        self.allow_unknown_types = allow_unknown_types
        self.strict_mode = strict_mode
    
    def validate_message(self, message: Dict[str, Any]) -> Union[bool, WebSocketValidationError]:
        """Orchestrate validation using micro-validators (graceful by default)."""
        try:
            error = self._run_validation_pipeline(message)
            return error if error else True
        except Exception as e:
            # In pragmatic mode, log warnings but don't fail validation
            if not self.strict_mode:
                log_validation_warning(f"Validation exception (gracefully handled): {e}", message)
                return True
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
# Default to pragmatic rigor: be liberal in what we accept
default_message_validator = MessageValidator(allow_unknown_types=True, strict_mode=False)
flexible_message_validator = MessageValidator(allow_unknown_types=True, strict_mode=False)
strict_message_validator = MessageValidator(allow_unknown_types=False, strict_mode=True)