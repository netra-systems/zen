"""
Legacy to SSOT Adapter for Issue #1099

This adapter bridges the interface differences between legacy message handlers
and SSOT message handlers to enable progressive migration without breaking changes.

Interface Differences:
- Legacy: handle(user_id: str, payload: Dict[str, Any]) -> None
- SSOT: handle_message(user_id: str, websocket: WebSocket, message: WebSocketMessage) -> bool

Conversion Strategy:
1. Parameter Conversion: payload -> WebSocketMessage
2. Return Type Normalization: None -> bool (assumes success if no exception)
3. Error Handling: Exception-based -> return-code based
4. Message Type Mapping: string -> MessageType enum

Business Justification:
- Protects $500K+ ARR Golden Path during migration
- Enables gradual migration without disrupting production
- Maintains backward compatibility during transition period
"""

import asyncio
from typing import Dict, Any, Optional
from fastapi import WebSocket
from unittest.mock import Mock

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.types import (
    WebSocketMessage, 
    MessageType,
    create_standard_message
)

logger = central_logger.get_logger(__name__)


class ParameterConverter:
    """Utility class for converting between legacy and SSOT parameter formats."""
    
    @staticmethod
    def payload_to_websocket_message(payload: Dict[str, Any]) -> WebSocketMessage:
        """
        Convert legacy payload Dict to SSOT WebSocketMessage.
        
        Args:
            payload: Legacy message payload with 'type' and other fields
            
        Returns:
            WebSocketMessage object for SSOT handlers
        """
        try:
            # Extract message type from payload
            message_type_str = payload.get("type", "unknown")
            
            # Convert string to MessageType enum
            try:
                message_type = MessageType(message_type_str)
            except ValueError:
                logger.warning(f"Unknown message type: {message_type_str}, defaulting to USER_MESSAGE")
                message_type = MessageType.USER_MESSAGE
            
            # Extract thread ID if present
            thread_id = payload.get("thread_id")
            
            # Create payload copy without type field and without thread_id
            # Note: run_id stays in payload since WebSocketMessage doesn't have run_id field
            clean_payload = {k: v for k, v in payload.items() if k not in ["type", "thread_id"]}
            
            return create_standard_message(
                message_type=message_type,
                payload=clean_payload,
                thread_id=thread_id
            )
        except Exception as e:
            logger.error(f"Failed to convert payload to WebSocketMessage: {e}")
            # Fallback to basic message
            return create_standard_message(MessageType.USER_MESSAGE, payload)
    
    @staticmethod
    def create_mock_websocket() -> WebSocket:
        """
        Create a mock WebSocket for adapting legacy calls to SSOT interface.
        
        Note: This is a limitation of the adapter pattern - legacy interface
        doesn't provide WebSocket, so we must mock it. This loses connection context.
        """
        return Mock(spec=WebSocket)


class ReturnTypeNormalizer:
    """Utility class for normalizing return types between legacy and SSOT patterns."""
    
    @staticmethod
    def none_to_bool(result: None, exception_occurred: bool = False) -> bool:
        """
        Convert legacy None return to SSOT bool return.
        
        Legacy Pattern: Returns None on success, raises exception on failure
        SSOT Pattern: Returns True on success, False on failure
        
        Args:
            result: Always None from legacy handlers
            exception_occurred: Whether an exception was caught during execution
            
        Returns:
            True if no exception occurred (success), False if exception occurred (failure)
        """
        return not exception_occurred
    
    @staticmethod
    def bool_to_none(result: bool) -> None:
        """
        Convert SSOT bool return to legacy None return.
        
        SSOT Pattern: Returns True on success, False on failure
        Legacy Pattern: Returns None on success, raises exception on failure
        
        Args:
            result: Boolean result from SSOT handler
            
        Returns:
            None for success, raises exception for failure
        """
        if not result:
            raise RuntimeError("Handler returned failure")
        return None


class LegacyToSSOTAdapter:
    """
    Adapter to enable legacy message handlers to work with SSOT interfaces.
    
    This adapter allows gradual migration by wrapping legacy handlers with
    SSOT-compatible interfaces while preserving existing functionality.
    
    Usage:
        # Wrap legacy handler for SSOT compatibility
        legacy_handler = StartAgentHandler(supervisor, db_factory)
        adapter = LegacyToSSOTAdapter(legacy_handler)
        
        # Use adapter with SSOT interface
        success = await adapter.handle_message(user_id, websocket, message)
    """
    
    def __init__(self, legacy_handler):
        """
        Initialize adapter with legacy handler.
        
        Args:
            legacy_handler: Legacy handler implementing handle(user_id, payload) -> None
        """
        self.legacy_handler = legacy_handler
        self.parameter_converter = ParameterConverter()
        self.return_normalizer = ReturnTypeNormalizer()
    
    def can_handle(self, message_type: MessageType) -> bool:
        """
        Check if the wrapped legacy handler can handle this message type.
        
        Args:
            message_type: SSOT MessageType enum
            
        Returns:
            True if handler can process this message type
        """
        try:
            # Get legacy handler's message type
            if hasattr(self.legacy_handler, 'get_message_type'):
                legacy_type = self.legacy_handler.get_message_type()
                return legacy_type == message_type.value
            else:
                # If handler doesn't specify type, assume it can handle any message
                logger.warning(f"Legacy handler {type(self.legacy_handler).__name__} "
                             f"doesn't implement get_message_type()")
                return True
        except Exception as e:
            logger.error(f"Error checking handler compatibility: {e}")
            return False
    
    async def handle_message(self, user_id: str, websocket: WebSocket, 
                           message: WebSocketMessage) -> bool:
        """
        Handle message using SSOT interface by adapting to legacy interface.
        
        This method converts SSOT parameters to legacy format, calls the legacy
        handler, and converts the result back to SSOT format.
        
        Args:
            user_id: User identifier
            websocket: WebSocket connection (note: this context is lost in legacy interface)
            message: SSOT WebSocketMessage object
            
        Returns:
            True if message was handled successfully, False otherwise
        """
        try:
            # Convert WebSocketMessage to legacy payload format
            payload = self._convert_message_to_payload(message)
            
            # Log conversion for debugging
            logger.debug(f"Adapter converting SSOT message to legacy payload: "
                        f"type={message.type.value}, payload_keys={list(payload.keys())}")
            
            # Call legacy handler with converted parameters
            exception_occurred = False
            try:
                await self.legacy_handler.handle(user_id, payload)
            except Exception as e:
                exception_occurred = True
                logger.error(f"Legacy handler threw exception: {e}")
            
            # Convert legacy result (None) to SSOT result (bool)
            success = self.return_normalizer.none_to_bool(None, exception_occurred)
            
            logger.debug(f"Adapter conversion complete: "
                        f"exception_occurred={exception_occurred}, success={success}")
            
            return success
            
        except Exception as e:
            logger.error(f"Adapter failed to handle message: {e}")
            return False
    
    def _convert_message_to_payload(self, message: WebSocketMessage) -> Dict[str, Any]:
        """
        Convert WebSocketMessage to legacy payload format.
        
        Args:
            message: SSOT WebSocketMessage
            
        Returns:
            Legacy payload dictionary
        """
        payload = message.payload.copy() if message.payload else {}
        
        # Add message type to payload (legacy handlers expect this)
        payload["type"] = message.type.value
        
        # Add thread ID if present
        if message.thread_id:
            payload["thread_id"] = message.thread_id
        
        # Add run_id if it's in the message payload (since WebSocketMessage doesn't have run_id field)
        if "run_id" in payload:
            # run_id is already in payload, keep it there
            pass
        
        return payload
    
    def get_legacy_handler(self):
        """Get the wrapped legacy handler for direct access if needed."""
        return self.legacy_handler
    
    def get_message_type(self) -> str:
        """
        Get message type for backward compatibility with legacy systems.
        
        Returns:
            Message type string, or "unknown" if handler doesn't specify
        """
        if hasattr(self.legacy_handler, 'get_message_type'):
            return self.legacy_handler.get_message_type()
        else:
            return "unknown"


class SSOTToLegacyAdapter:
    """
    Adapter to enable SSOT message handlers to work with legacy interfaces.
    
    WARNING: This adapter has fundamental limitations due to information loss:
    - Legacy interface doesn't provide WebSocket connection
    - Single string message type vs multiple MessageType support
    - Return type conversion (bool -> None) loses success indication
    
    This adapter is provided for completeness but is not recommended for 
    production use due to these limitations.
    """
    
    def __init__(self, ssot_handler):
        """
        Initialize adapter with SSOT handler.
        
        Args:
            ssot_handler: SSOT handler implementing handle_message() -> bool
        """
        self.ssot_handler = ssot_handler
        self.parameter_converter = ParameterConverter()
        self.return_normalizer = ReturnTypeNormalizer()
    
    def get_message_type(self) -> str:
        """
        Get message type - LIMITED due to SSOT handlers supporting multiple types.
        
        Returns:
            "multiple_types" - Cannot accurately represent SSOT capabilities
        """
        return "multiple_types"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """
        Handle message using legacy interface by adapting to SSOT interface.
        
        LIMITATIONS:
        - WebSocket connection is mocked (loses connection context)
        - Success indication is lost (bool -> None conversion)
        
        Args:
            user_id: User identifier
            payload: Legacy payload dictionary
            
        Returns:
            None (legacy pattern), raises exception on failure
        """
        try:
            # Convert legacy payload to SSOT WebSocketMessage
            message = self.parameter_converter.payload_to_websocket_message(payload)
            
            # Create mock WebSocket (LIMITATION: loses connection context)
            mock_websocket = self.parameter_converter.create_mock_websocket()
            
            # Call SSOT handler
            success = await self.ssot_handler.handle_message(user_id, mock_websocket, message)
            
            # Convert SSOT result (bool) to legacy result (None/Exception)
            return self.return_normalizer.bool_to_none(success)
            
        except Exception as e:
            logger.error(f"SSOT-to-legacy adapter failed: {e}")
            raise RuntimeError(f"Handler adaptation failed: {e}")


# Backward compatibility function for existing code
def create_legacy_adapter(legacy_handler) -> LegacyToSSOTAdapter:
    """
    Create adapter for legacy handler to work with SSOT interfaces.
    
    This function provides a simple interface for wrapping legacy handlers
    during the migration period.
    
    Args:
        legacy_handler: Legacy handler to wrap
        
    Returns:
        Adapter that provides SSOT interface
    """
    return LegacyToSSOTAdapter(legacy_handler)