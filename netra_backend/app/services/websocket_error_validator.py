"""WebSocket Error Validator - Compatibility Module

This module provides error validation utilities for WebSocket operations.
Created for backward compatibility with test imports.

IMPORTANT: During SSOT consolidation (PR #214), WebSocketEventValidator was moved to
netra_backend.app.websocket_core.event_validator and renamed to UnifiedEventValidator.
This module provides backward compatibility imports.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test infrastructure stability
- Value Impact: Prevents test collection failures from missing imports
- Revenue Impact: Ensures CI/CD reliability for WebSocket validation
"""

from typing import Dict, Any, List, Optional
from netra_backend.app.logging_config import central_logger

# Import from SSOT consolidated implementation
from netra_backend.app.websocket_core.event_validator import (
    UnifiedEventValidator as WebSocketEventValidator,
    ValidationResult,
    EventCriticality,
    get_websocket_validator,
    reset_websocket_validator,
    CriticalAgentEventType
)

logger = central_logger.get_logger(__name__)


class WebSocketErrorValidator:
    """Validates WebSocket-related errors and responses."""
    
    def __init__(self):
        self.validation_rules = []
        
    def validate_error_response(self, error_data: Dict[str, Any]) -> bool:
        """
        Validate WebSocket error response format.
        
        Args:
            error_data: Error data dictionary
            
        Returns:
            bool: True if valid error format
        """
        required_fields = ['error_type', 'message', 'timestamp']
        return all(field in error_data for field in required_fields)
    
    def validate_websocket_message(self, message: Dict[str, Any]) -> List[str]:
        """
        Validate WebSocket message format.
        
        Args:
            message: WebSocket message dictionary
            
        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []
        
        if not isinstance(message, dict):
            errors.append("Message must be a dictionary")
            return errors
            
        if 'type' not in message:
            errors.append("Message must contain 'type' field")
            
        if 'data' not in message:
            errors.append("Message must contain 'data' field")
            
        return errors
    
    def is_valid_connection_state(self, state: str) -> bool:
        """
        Check if connection state is valid.
        
        Args:
            state: Connection state string
            
        Returns:
            bool: True if valid state
        """
        valid_states = ['connecting', 'connected', 'disconnecting', 'disconnected', 'error']
        return state in valid_states


# Module exports
__all__ = [
    'WebSocketErrorValidator',  # Original compatibility class
    'WebSocketEventValidator',  # SSOT consolidated import alias
    'ValidationResult',
    'EventCriticality', 
    'get_websocket_validator',
    'reset_websocket_validator'
]

logger.info("WebSocket Error Validator compatibility module loaded with SSOT imports")