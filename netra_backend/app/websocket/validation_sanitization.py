"""WebSocket message sanitization micro-functions.

Focused micro-functions for sanitizing text, dictionaries, and lists.
Each function ≤8 lines for performance-critical WebSocket sanitization path.
"""

from typing import Dict, Any, List

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def sanitize_message_content(message: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize complete message content safely."""
    try:
        return safe_sanitize_message(message)
    except Exception as e:
        logger.error(f"Error sanitizing message: {e}")
        return message


def has_payload_to_sanitize(message: Dict[str, Any]) -> bool:
    """Check if message has payload structure to sanitize."""
    return "payload" in message and isinstance(message["payload"], dict)


def sanitize_payload_content(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize payload content with text-specific handling."""
    sanitized_payload = payload.copy()
    if "text" in sanitized_payload and isinstance(sanitized_payload["text"], str):
        sanitized_payload["text"] = sanitize_text_content(sanitized_payload["text"])
    return sanitize_dict_strings_skip_text(sanitized_payload)


def sanitize_text_content(text: str) -> str:
    """Sanitize text content for security."""
    from netra_backend.app.websocket.validation_security import is_text_already_encoded
    if is_text_already_encoded(text):
        return text
    text = encode_html_entities(text)
    text = remove_control_characters(text)
    return text


def encode_html_entities(text: str) -> str:
    """Encode dangerous HTML characters."""
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return text.replace('"', "&quot;").replace("'", "&#x27;")


def remove_control_characters(text: str) -> str:
    """Remove null bytes and control characters."""
    text = text.replace("\x00", "")
    dangerous_chars = ["\x08", "\x0c", "\x0e", "\x0f"]
    for char in dangerous_chars:
        text = text.replace(char, "")
    return text


def sanitize_dict_strings(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitize string values in dictionary."""
    sanitized = {}
    for key, value in data.items():
        sanitized[key] = sanitize_single_value(value)
    return sanitized


def sanitize_single_value(value: Any) -> Any:
    """Sanitize single value based on type."""
    type_handlers = get_sanitization_handlers()
    handler = type_handlers.get(type(value))
    return handler(value) if handler else value


def get_sanitization_handlers() -> dict:
    """Get sanitization handlers for each type."""
    return {
        str: sanitize_text_content,
        dict: sanitize_dict_strings,
        list: sanitize_list_content
    }


def sanitize_dict_strings_skip_text(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize dictionary strings, preserving 'text' field."""
    sanitized = {}
    for key, value in data.items():
        sanitized[key] = sanitize_value_skip_text(key, value)
    return sanitized


def sanitize_value_skip_text(key: str, value: Any) -> Any:
    """Sanitize value by type, skipping 'text' field."""
    if key == "text":
        return value
    return sanitize_single_value(value)


def sanitize_list_content(data: List[Any]) -> List[Any]:
    """Recursively sanitize string values in list."""
    return [sanitize_list_item(item) for item in data]


def safe_sanitize_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Safely sanitize message with payload handling."""
    sanitized = message.copy()
    if has_payload_to_sanitize(sanitized):
        sanitized["payload"] = sanitize_payload_content(sanitized["payload"])
    return sanitized


def sanitize_list_item(item: Any) -> Any:
    """Sanitize single list item by type."""
    return sanitize_single_value(item)