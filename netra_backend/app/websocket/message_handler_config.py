"""WebSocket Message Handler Configuration.

Configuration classes and initialization for the message handler.
"""

from typing import Dict, Optional, Any

from netra_backend.app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)
from netra_backend.app.websocket.validation import MessageValidator, default_message_validator
from netra_backend.app.websocket.error_handler import WebSocketErrorHandler, default_error_handler


class MessageHandlerConfig:
    """Configuration container for reliable message handler."""
    
    def __init__(
        self,
        validator: Optional[MessageValidator] = None,
        error_handler: Optional[WebSocketErrorHandler] = None
    ):
        self.validator = validator or default_message_validator
        self.error_handler = error_handler or default_error_handler
        self.reliability = self._create_reliability_wrapper()
        self.stats = self._create_default_stats()

    def _create_reliability_wrapper(self):
        """Create reliability wrapper for message handling."""
        circuit_config = self._create_circuit_breaker_config()
        retry_config = self._create_retry_config()
        return get_reliability_wrapper(
            "WebSocketMessageHandler", circuit_config, retry_config
        )

    def _create_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=30.0,
            name="WebSocketMessageHandler"
        )

    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(
            max_retries=2,
            base_delay=0.5,
            max_delay=5.0
        )

    def _create_default_stats(self) -> Dict[str, int]:
        """Create default statistics dictionary."""
        return {
            "messages_processed": 0,
            "messages_failed": 0,
            "validation_failures": 0,
            "circuit_breaker_opens": 0,
            "fallback_used": 0
        }