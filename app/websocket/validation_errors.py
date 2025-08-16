"""WebSocket validation error handling micro-functions.

Focused micro-functions for creating validation errors and handling edge cases.
Each function ≤8 lines for performance-critical WebSocket error path.
"""

from typing import Dict, Any
from datetime import datetime, UTC

from app.logging_config import central_logger
from app.schemas.websocket_message_types import WebSocketValidationError

logger = central_logger.get_logger(__name__)


def handle_validation_exception(e: Exception, message: Dict[str, Any]) -> WebSocketValidationError:
    """Handle unexpected validation exceptions safely."""
    logger.error(f"Error validating message: {e}")
    return WebSocketValidationError(
        error_type="validation_error",
        message=f"Unexpected validation error: {str(e)}",
        received_data=message
    )


def create_unknown_message_fallback(message: Dict[str, Any]) -> Dict[str, Any]:
    """Create fallback structure for unknown message type."""
    original_type = message.get('type', 'undefined')
    fallback_message = build_error_message_structure(
        create_unknown_type_payload(message, original_type)
    )
    log_unknown_type_fallback(original_type)
    return fallback_message


def create_unknown_type_payload(message: Dict[str, Any], original_type: str) -> Dict[str, Any]:
    """Create payload for unknown message type fallback."""
    base_payload = {
        "error": f"Unknown message type: {original_type}",
        "original_type": original_type,
        "original_payload": message.get('payload', {})
    }
    return add_fallback_metadata(base_payload)


def create_graceful_validation_result(message: Dict[str, Any], 
                                    validation_error: WebSocketValidationError) -> Dict[str, Any]:
    """Create graceful validation result for invalid messages."""
    return {
        "type": "error",
        "payload": create_validation_error_payload(message, validation_error)
    }


def create_validation_error_payload(message: Dict[str, Any], 
                                  validation_error: WebSocketValidationError) -> Dict[str, Any]:
    """Create validation error payload structure."""
    base_payload = build_validation_error_base(message, validation_error)
    return add_error_metadata(base_payload)


def log_validation_warning(message_type: str) -> None:
    """Log validation warning for unknown message type."""
    logger.warning(f"Unknown message type allowed: {message_type}")


def log_unknown_type_fallback(original_type: str) -> None:
    """Log unknown message type fallback."""
    logger.warning(f"Applied fallback for unknown message type: {original_type}")


def add_fallback_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Add fallback metadata to payload."""
    payload.update({
        "fallback_applied": True,
        "timestamp": datetime.now(UTC).isoformat()
    })
    return payload


def add_error_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Add error metadata to payload."""
    payload["timestamp"] = datetime.now(UTC).isoformat()
    return payload


def build_error_message_structure(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build error message structure."""
    return {"type": "error", "payload": payload}


def build_validation_error_base(message: Dict[str, Any], 
                               validation_error: WebSocketValidationError) -> Dict[str, Any]:
    """Build base validation error payload."""
    base_fields = extract_error_fields(validation_error)
    return add_validation_context(base_fields, message)


def add_validation_context(base_fields: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
    """Add validation context to error base."""
    base_fields.update({
        "original_message": message,
        "validation_failed": True
    })
    return base_fields


def extract_error_fields(validation_error: WebSocketValidationError) -> Dict[str, Any]:
    """Extract error fields from validation error."""
    return {
        "error": validation_error.message,
        "error_type": validation_error.error_type,
        "field": validation_error.field
    }


def is_validation_error_result(result: Any) -> bool:
    """Check if result is a validation error."""
    return isinstance(result, WebSocketValidationError)