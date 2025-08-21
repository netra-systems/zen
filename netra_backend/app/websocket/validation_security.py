"""Security-focused WebSocket message validation micro-validators.

Micro-validators for XSS, script injection, and content security validation.
Each function ≤8 lines for performance-critical WebSocket security path.
"""

from typing import Dict, Any, Union, List

from netra_backend.app.schemas.websocket_message_types import WebSocketValidationError


def has_valid_payload_structure(message: Dict[str, Any]) -> bool:
    """Check if message has valid payload structure."""
    return "payload" in message and isinstance(message["payload"], dict)


def validate_payload_security(message: Dict[str, Any]) -> Union[None, WebSocketValidationError]:
    """Validate payload content for security threats."""
    if not has_valid_payload_structure(message):
        return None
    payload = message["payload"]
    if "text" in payload and isinstance(payload["text"], str):
        return validate_text_security(payload["text"], message)
    return None


def validate_text_security(text: str, message: Dict[str, Any]) -> Union[None, WebSocketValidationError]:
    """Validate text content for security threats."""
    security_checks = [
        lambda: check_script_injection_patterns(text, message),
        lambda: check_xss_attack_patterns(text, message),
        lambda: check_text_length_limit(text, message, 10000)
    ]
    return run_security_checks(security_checks)


def check_script_injection_patterns(text: str, message: Dict[str, Any]) -> Union[None, WebSocketValidationError]:
    """Check for script injection attack patterns."""
    text_lower = text.lower()
    if has_script_patterns(text_lower):
        return create_script_injection_error(message)
    return None


def create_security_error(error_msg: str, field: str, message: Dict[str, Any]) -> WebSocketValidationError:
    """Create security validation error."""
    return WebSocketValidationError(
        error_type="security_error",
        message=error_msg,
        field=field,
        received_data=message
    )


def get_dangerous_xss_patterns() -> List[str]:
    """Get list of dangerous XSS patterns to check."""
    return [
        "onclick=", "onerror=", "onload=", "onmouseover=",
        "<iframe", "<object", "<embed", "<form"
    ]


def check_xss_attack_patterns(text: str, message: Dict[str, Any]) -> Union[None, WebSocketValidationError]:
    """Check for XSS attack patterns in text."""
    text_lower = text.lower()
    dangerous_patterns = get_dangerous_xss_patterns()
    for pattern in dangerous_patterns:
        if pattern in text_lower:
            return create_xss_pattern_error(pattern, message)
    return None


def create_xss_pattern_error(pattern: str, message: Dict[str, Any]) -> WebSocketValidationError:
    """Create XSS pattern detection error."""
    return WebSocketValidationError(
        error_type="security_error",
        message=f"Potentially dangerous content detected: {pattern}",
        field="payload.text",
        received_data=message
    )


def check_text_length_limit(text: str, message: Dict[str, Any], max_length: int) -> Union[None, WebSocketValidationError]:
    """Check text length against security limit."""
    if len(text) > max_length:
        return create_text_length_error(len(text), message)
    return None


def run_security_checks(checks: list) -> Union[None, WebSocketValidationError]:
    """Run security validation checks sequentially."""
    for check in checks:
        error = check()
        if error:
            return error
    return None


def has_script_patterns(text_lower: str) -> bool:
    """Check if text contains script injection patterns."""
    return "<script" in text_lower or "javascript:" in text_lower


def create_script_injection_error(message: Dict[str, Any]) -> WebSocketValidationError:
    """Create script injection security error."""
    return create_security_error(
        "Potential script injection detected in message",
        "payload.text", message
    )


def create_text_length_error(text_len: int, message: Dict[str, Any]) -> WebSocketValidationError:
    """Create text length validation error."""
    return WebSocketValidationError(
        error_type="validation_error",
        message=f"Text too long: {text_len} characters",
        field="payload.text",
        received_data=message
    )


def is_text_already_encoded(text: str) -> bool:
    """Check if text is already HTML encoded."""
    html_entities = ["&lt;", "&gt;", "&amp;", "&quot;", "&#x27;"]
    return any(entity in text for entity in html_entities)