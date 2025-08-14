"""WebSocket message validation and sanitization.

Provides comprehensive validation and sanitization capabilities for WebSocket messages
to ensure security and data integrity.
"""

import json
from typing import Dict, Any, Union
from datetime import datetime

from pydantic import ValidationError

from app.logging_config import central_logger
from app.schemas.registry import (
    WebSocketMessage,
    WebSocketMessageType
)
from app.schemas.websocket_message_types import WebSocketValidationError

logger = central_logger.get_logger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class MessageValidator:
    """Validates and sanitizes WebSocket messages."""
    
    def __init__(self, max_message_size: int = 1024 * 1024, max_text_length: int = 10000, 
                 allow_unknown_types: bool = False):
        """Initialize message validator.
        
        Args:
            max_message_size: Maximum message size in bytes (default 1MB)
            max_text_length: Maximum text field length in characters (default 10KB)
            allow_unknown_types: Allow unknown message types with warning (default False)
        """
        self.max_message_size = max_message_size
        self.max_text_length = max_text_length
        self.allow_unknown_types = allow_unknown_types
    
    def validate_message(self, message: Dict[str, Any]) -> Union[bool, WebSocketValidationError]:
        """Validate incoming WebSocket message using strong types.
        
        Args:
            message: Message dictionary to validate
            
        Returns:
            True if valid, WebSocketValidationError if invalid
        """
        try:
            # Basic structure validation
            if not isinstance(message, dict):
                return WebSocketValidationError(
                    error_type="format_error",
                    message=f"Message is not a dictionary: {type(message)}",
                    received_data=message
                )
            
            # Required fields
            if "type" not in message:
                return WebSocketValidationError(
                    error_type="validation_error",
                    message="Message missing 'type' field",
                    field="type",
                    received_data=message
                )
            
            # SECURITY VALIDATION FIRST - Check for malicious content before anything else
            security_error = self._validate_payload_content(message)
            if security_error:
                return security_error
            
            # Validate message type using enum
            message_type = message.get("type")
            try:
                WebSocketMessageType(message_type)
            except ValueError:
                if self.allow_unknown_types:
                    logger.warning(f"Unknown message type allowed: {message_type}")
                else:
                    return WebSocketValidationError(
                        error_type="type_error",
                        message=f"Invalid message type: {message_type}",
                        field="type",
                        received_data=message
                    )
            
            # Validate using Pydantic model with flexible payload handling
            try:
                # If message doesn't have payload field, create one from the other fields
                if "payload" not in message:
                    # Extract type and create payload from remaining fields
                    payload_data = {k: v for k, v in message.items() if k != "type"}
                    flexible_message = {
                        "type": message["type"],
                        "payload": payload_data
                    }
                    validated_message = WebSocketMessage(**flexible_message)
                else:
                    validated_message = WebSocketMessage(**message)
            except ValidationError as e:
                return WebSocketValidationError(
                    error_type="validation_error",
                    message=f"Message validation failed: {str(e)}",
                    received_data=message
                )
            
            # Size validation (prevent large payloads)
            message_str = json.dumps(message, cls=DateTimeEncoder)
            if len(message_str) > self.max_message_size:
                return WebSocketValidationError(
                    error_type="validation_error",
                    message=f"Message too large: {len(message_str)} bytes",
                    received_data=message
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating message: {e}")
            return WebSocketValidationError(
                error_type="validation_error",
                message=f"Unexpected validation error: {str(e)}",
                received_data=message
            )
    
    def _validate_payload_content(self, message: Dict[str, Any]) -> Union[None, WebSocketValidationError]:
        """Validate payload content for security and size limits.
        
        Args:
            message: Message to validate
            
        Returns:
            WebSocketValidationError if invalid, None if valid
        """
        if "payload" not in message or not isinstance(message["payload"], dict):
            return None
        
        payload = message["payload"]
        
        # Validate text fields
        if "text" in payload:
            text = payload["text"]
            if isinstance(text, str):
                # Remove potential script injections
                if "<script" in text.lower() or "javascript:" in text.lower():
                    return WebSocketValidationError(
                        error_type="security_error",
                        message="Potential script injection detected in message",
                        field="payload.text",
                        received_data=message
                    )
                
                # Check for common XSS patterns
                dangerous_patterns = [
                    "onclick=", "onerror=", "onload=", "onmouseover=",
                    "<iframe", "<object", "<embed", "<form"
                ]
                text_lower = text.lower()
                for pattern in dangerous_patterns:
                    if pattern in text_lower:
                        return WebSocketValidationError(
                            error_type="security_error",
                            message=f"Potentially dangerous content detected: {pattern}",
                            field="payload.text",
                            received_data=message
                        )
                
                # Limit text length
                if len(text) > self.max_text_length:
                    return WebSocketValidationError(
                        error_type="validation_error",
                        message=f"Text too long: {len(text)} characters",
                        field="payload.text",
                        received_data=message
                    )
        
        return None
    
    def sanitize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize message content to prevent XSS and other attacks.
        
        Args:
            message: Message to sanitize
            
        Returns:
            Sanitized message copy
        """
        try:
            # Create a copy to avoid modifying original
            sanitized = message.copy()
            
            # Sanitize payload if present
            if "payload" in sanitized and isinstance(sanitized["payload"], dict):
                payload = sanitized["payload"].copy()
                
                # Sanitize text content first
                if "text" in payload and isinstance(payload["text"], str):
                    payload["text"] = self._sanitize_text(payload["text"])
                
                # Sanitize other string fields recursively (excluding "text" to avoid double sanitization)
                payload = self._sanitize_dict_strings_except_text(payload)
                
                sanitized["payload"] = payload
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Error sanitizing message: {e}")
            return message
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text content.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        # More robust check for already encoded text
        # If text contains HTML entities, assume it's already been sanitized
        html_entities = ["&lt;", "&gt;", "&amp;", "&quot;", "&#x27;"]
        if any(entity in text for entity in html_entities):
            return text  # Already encoded, don't double-encode
        
        # Basic HTML entity encoding for safety - encode dangerous characters
        # Order matters: do < and > first, then other chars to avoid conflicts
        text = text.replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace('"', "&quot;").replace("'", "&#x27;")
        # NOTE: Not encoding & to &amp; to avoid double-encoding issues
        
        # Remove null bytes and other control characters
        text = text.replace("\x00", "")
        
        # Remove other potentially dangerous characters
        dangerous_chars = ["\x08", "\x0c", "\x0e", "\x0f"]  # Backspace, form feed, etc.
        for char in dangerous_chars:
            text = text.replace(char, "")
        
        return text
    
    def _sanitize_dict_strings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize string values in a dictionary.
        
        Args:
            data: Dictionary to sanitize
            
        Returns:
            Sanitized dictionary
        """
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self._sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict_strings(value)
            elif isinstance(value, list):
                sanitized[key] = self._sanitize_list(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_dict_strings_except_text(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize string values in a dictionary, excluding 'text' field.
        
        Args:
            data: Dictionary to sanitize
            
        Returns:
            Sanitized dictionary with 'text' field unchanged
        """
        sanitized = {}
        
        for key, value in data.items():
            if key == "text":
                # Don't re-sanitize the text field
                sanitized[key] = value
            elif isinstance(value, str):
                sanitized[key] = self._sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict_strings_except_text(value)
            elif isinstance(value, list):
                sanitized[key] = self._sanitize_list(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_list(self, data: list) -> list:
        """Recursively sanitize string values in a list.
        
        Args:
            data: List to sanitize
            
        Returns:
            Sanitized list
        """
        sanitized = []
        
        for item in data:
            if isinstance(item, str):
                sanitized.append(self._sanitize_text(item))
            elif isinstance(item, dict):
                sanitized.append(self._sanitize_dict_strings(item))
            elif isinstance(item, list):
                sanitized.append(self._sanitize_list(item))
            else:
                sanitized.append(item)
        
        return sanitized
    
    def validate_message_type(self, message_type: str) -> bool:
        """Validate if message type is supported.
        
        Args:
            message_type: Message type to validate
            
        Returns:
            True if valid message type
        """
        try:
            WebSocketMessageType(message_type)
            return True
        except ValueError:
            return False
    
    def handle_unknown_message_type(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown message type by creating a fallback structure.
        
        Args:
            message: Message with unknown type
            
        Returns:
            Fallback message structure
        """
        fallback_message = {
            "type": "error",
            "payload": {
                "error": f"Unknown message type: {message.get('type', 'undefined')}",
                "original_type": message.get('type', 'undefined'),
                "original_payload": message.get('payload', {}),
                "fallback_applied": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        logger.warning(f"Applied fallback for unknown message type: {message.get('type')}")
        return fallback_message
    
    def create_graceful_validation_result(self, message: Dict[str, Any], 
                                        validation_error: WebSocketValidationError) -> Dict[str, Any]:
        """Create a graceful validation result for invalid messages.
        
        Args:
            message: Original message that failed validation
            validation_error: The validation error that occurred
            
        Returns:
            Graceful error message structure
        """
        return {
            "type": "error",
            "payload": {
                "error": validation_error.message,
                "error_type": validation_error.error_type,
                "field": validation_error.field,
                "original_message": message,
                "validation_failed": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        }


# Default validator instance
default_message_validator = MessageValidator()

# Flexible validator instance that allows unknown types for development
flexible_message_validator = MessageValidator(allow_unknown_types=True)