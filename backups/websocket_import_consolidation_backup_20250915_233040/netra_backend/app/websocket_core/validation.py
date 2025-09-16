"""WebSocket message validation module.

This is a stub module created to fix import errors after refactoring.
The actual validation logic has been moved to other modules.
"""

from typing import Any, Dict, Optional


class MessageValidator:
    """Stub MessageValidator for backward compatibility.
    
    The actual validation logic has been integrated into the WebSocket
    handlers and type system. This class exists only to prevent import
    errors in existing tests.
    """
    
    def __init__(self):
        """Initialize the validator."""
        self.max_message_size = 1024 * 1024  # 1MB default
    
    def validate_message(self, message: Any) -> Dict[str, Any]:
        """Validate a WebSocket message.
        
        Args:
            message: The message to validate
            
        Returns:
            A dictionary with validation results
        """
        # Basic validation stub
        if not message:
            return {"valid": False, "error": "Empty message"}
        
        if isinstance(message, dict):
            # Check message size
            import json
            try:
                message_str = json.dumps(message)
                if len(message_str) > self.max_message_size:
                    return {
                        "valid": False, 
                        "error": f"Message too large: {len(message_str)} bytes"
                    }
            except Exception as e:
                return {"valid": False, "error": f"Invalid message format: {e}"}
        
        # Basic security check
        if isinstance(message, str):
            dangerous_patterns = ["<script>", "javascript:", "onclick=", "onerror="]
            for pattern in dangerous_patterns:
                if pattern.lower() in message.lower():
                    return {
                        "valid": False,
                        "error": f"Potentially malicious pattern detected: {pattern}"
                    }
        
        return {"valid": True, "message": message}
    
    def validate_type(self, message: Dict[str, Any], expected_type: str) -> bool:
        """Validate message type.
        
        Args:
            message: The message to validate
            expected_type: The expected message type
            
        Returns:
            True if the message type matches
        """
        return message.get("type") == expected_type
    
    def sanitize_message(self, message: Any) -> Any:
        """Sanitize a message for safe processing.
        
        Args:
            message: The message to sanitize
            
        Returns:
            The sanitized message
        """
        # Basic sanitization
        if isinstance(message, str):
            # Remove any HTML/script tags
            import re
            message = re.sub(r'<[^>]+>', '', message)
        
        return message