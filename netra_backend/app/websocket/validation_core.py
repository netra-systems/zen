"""Core WebSocket message validation micro-validators.

Focused micro-validators for basic message structure, type, and size validation.
Each function ≤8 lines for performance-critical WebSocket path.
"""

import json
from typing import Any, Dict, Union

from pydantic import ValidationError

from netra_backend.app.schemas.registry import WebSocketMessage, WebSocketMessageType
from netra_backend.app.schemas.websocket_message_types import WebSocketValidationError
from netra_backend.app.services.state_persistence import DateTimeEncoder


def validate_message_is_dict(message: Dict[str, Any]) -> Union[None, WebSocketValidationError]:
    """Validate message is dictionary-like type (duck typing)."""
    # Use duck typing - if it acts like a dict, treat it as one
    if not hasattr(message, 'get') or not hasattr(message, 'items'):
        return create_dict_type_error(message)
    return None


def validate_type_field_exists(message: Dict[str, Any]) -> Union[None, WebSocketValidationError]:
    """Validate message has required type field (flexible access)."""
    # Try multiple ways to access type field (be liberal in what we accept)
    type_value = message.get('type') or message.get('message_type') or message.get('msg_type')
    if not type_value:
        return create_missing_type_error(message)
    return None


def validate_message_type_enum(message_type: str, allow_unknown: bool = False) -> Union[None, WebSocketValidationError]:
    """Validate message type against enum (flexible matching)."""
    try:
        # Try exact match first
        WebSocketMessageType(message_type)
        return None
    except ValueError:
        # Try case-insensitive match (be liberal in what we accept)
        try:
            normalized_type = message_type.upper() if isinstance(message_type, str) else str(message_type).upper()
            for enum_value in WebSocketMessageType:
                if enum_value.value.upper() == normalized_type:
                    return None
        except:
            pass
        return handle_invalid_message_type(message_type, allow_unknown)


def create_type_error(message_type: str) -> WebSocketValidationError:
    """Create type validation error."""
    return WebSocketValidationError(
        error_type="type_error",
        message=f"Invalid message type: {message_type}",
        field="type",
        received_data={"type": message_type}
    )


def validate_with_pydantic_model(message: Dict[str, Any]) -> Union[None, WebSocketValidationError]:
    """Validate message using Pydantic WebSocketMessage model."""
    try:
        flexible_message = create_flexible_message_format(message)
        WebSocketMessage(**flexible_message)
        return None
    except ValidationError as e:
        return create_pydantic_error(e, message)


def create_flexible_message_format(message: Dict[str, Any]) -> Dict[str, Any]:
    """Create flexible message format for Pydantic validation (graceful handling)."""
    # Extract type from various possible field names
    msg_type = message.get('type') or message.get('message_type') or message.get('msg_type')
    
    if "payload" not in message and "data" not in message:
        # Create payload from all non-type fields
        payload_data = {k: v for k, v in message.items() 
                       if k not in ['type', 'message_type', 'msg_type']}
        return {"type": msg_type, "payload": payload_data}
    elif "data" in message and "payload" not in message:
        # Accept 'data' as equivalent to 'payload'
        return {"type": msg_type, "payload": message["data"]}
    
    return message


def create_pydantic_error(e: ValidationError, message: Dict[str, Any]) -> WebSocketValidationError:
    """Create Pydantic validation error."""
    return WebSocketValidationError(
        error_type="validation_error",
        message=f"Message validation failed: {str(e)}",
        received_data=message
    )


def validate_message_size(message: Dict[str, Any], max_size: int) -> Union[None, WebSocketValidationError]:
    """Validate message size against limit."""
    message_str = json.dumps(message, cls=DateTimeEncoder)
    if len(message_str) > max_size:
        return create_size_error(len(message_str), message)
    return None


def create_dict_type_error(message: Dict[str, Any]) -> WebSocketValidationError:
    """Create dictionary type validation error."""
    return WebSocketValidationError(
        error_type="format_error",
        message=f"Message is not a dictionary: {type(message)}",
        received_data=message
    )


def create_missing_type_error(message: Dict[str, Any]) -> WebSocketValidationError:
    """Create missing type field error."""
    return WebSocketValidationError(
        error_type="validation_error",
        message="Message missing 'type' field",
        field="type",
        received_data=message
    )


def handle_invalid_message_type(message_type: str, allow_unknown: bool) -> Union[None, WebSocketValidationError]:
    """Handle invalid message type validation."""
    if allow_unknown:
        return None
    return create_type_error(message_type)


def create_size_error(message_size: int, message: Dict[str, Any]) -> WebSocketValidationError:
    """Create message size validation error."""
    return WebSocketValidationError(
        error_type="validation_error",
        message=f"Message too large: {message_size} bytes",
        received_data=message
    )


def check_message_type_supported(message_type: str) -> bool:
    """Check if message type is supported."""
    try:
        WebSocketMessageType(message_type)
        return True
    except ValueError:
        return False