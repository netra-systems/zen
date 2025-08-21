"""WebSocket Message Handler Response System.

Handles error responses and status reporting for message handlers.
"""

from datetime import UTC, datetime
from typing import Any, Dict

from netra_backend.app.core.json_utils import prepare_websocket_message
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket.connection import ConnectionInfo
from netra_backend.app.websocket.message_handler_config import MessageHandlerConfig

logger = central_logger.get_logger(__name__)


class MessageHandlerResponseManager:
    """Manages error responses and status reporting."""
    
    def __init__(self, config: MessageHandlerConfig):
        self.config = config

    async def send_parse_error_response(self, conn_info: ConnectionInfo):
        """Send parse error response to client."""
        await self._send_error_response(
            conn_info, "INVALID_JSON", "Message must be valid JSON"
        )

    async def send_validation_error_response(self, conn_info: ConnectionInfo, validation_error: Any):
        """Send validation error response to client."""
        await self._send_error_response(
            conn_info, "VALIDATION_ERROR", validation_error.message
        )

    async def send_unexpected_error_response(self, conn_info: ConnectionInfo):
        """Send unexpected error response to client."""
        await self._send_error_response(
            conn_info,
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please try again."
        )

    async def send_fallback_error_response(self, conn_info: ConnectionInfo):
        """Send fallback error response to client."""
        await self._send_error_response(
            conn_info, "MESSAGE_PROCESSING_FAILED", 
            "Message could not be processed. Please try again."
        )

    async def _send_error_response(
        self, conn_info: ConnectionInfo, error_code: str, error_message: str
    ):
        """Send error response to client."""
        try:
            error_response = self._create_error_response(error_code, error_message)
            await self._send_if_connected(conn_info, error_response)
        except Exception as e:
            logger.error(f"Failed to send error response to {conn_info.connection_id}: {e}")

    def _create_error_response(self, error_code: str, error_message: str) -> Dict[str, Any]:
        """Create error response structure."""
        payload = self._create_error_payload(error_code, error_message)
        return self._create_response_structure(payload)

    def _create_error_payload(self, error_code: str, error_message: str) -> Dict[str, Any]:
        """Create error payload with timestamp."""
        return {
            "error_code": error_code,
            "message": error_message,
            "timestamp": datetime.now(UTC).isoformat()
        }

    def _create_response_structure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create response structure with type and sender."""
        return {
            "type": "error",
            "payload": payload,
            "sender": "system"
        }

    async def _send_if_connected(self, conn_info: ConnectionInfo, error_response: Dict[str, Any]) -> None:
        """Send error response if connection is still open."""
        from starlette.websockets import WebSocketState
        if conn_info.websocket.client_state == WebSocketState.CONNECTED:
            prepared_message = prepare_websocket_message(error_response)
            await conn_info.websocket.send_json(prepared_message)
        else:
            logger.debug(f"Cannot send error response to {conn_info.connection_id}: connection closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get message handling statistics."""
        reliability_stats = self.config.reliability.get_health_status()
        message_stats = self._build_message_stats()
        error_stats = self.config.error_handler.get_error_stats()
        return self._combine_all_stats(message_stats, reliability_stats, error_stats)

    def _combine_all_stats(self, message_stats, reliability_stats, error_stats) -> Dict[str, Any]:
        """Combine all statistics into single dict."""
        return {
            "message_handler": message_stats,
            "reliability": reliability_stats,
            "error_handler": error_stats
        }

    def _build_message_stats(self) -> Dict[str, Any]:
        """Build message handler statistics."""
        base_stats = self._get_base_stats()
        success_rate = self._calculate_success_rate()
        return {**base_stats, "success_rate": success_rate}

    def _get_base_stats(self) -> Dict[str, int]:
        """Get base message processing statistics."""
        return {
            "messages_processed": self.config.stats["messages_processed"],
            "messages_failed": self.config.stats["messages_failed"],
            "validation_failures": self.config.stats["validation_failures"],
            "fallback_used": self.config.stats["fallback_used"]
        }

    def _calculate_success_rate(self) -> float:
        """Calculate message processing success rate."""
        total_attempts = self.config.stats["messages_processed"] + self.config.stats["messages_failed"]
        return self.config.stats["messages_processed"] / max(1, total_attempts)

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        stats = self.get_stats()
        health_score = self._calculate_health_score(stats)
        status = self._determine_status(health_score)
        return self._build_health_response(health_score, status, stats)

    def _build_health_response(self, health_score: float, status: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Build health status response dictionary."""
        core_info = self._get_core_health_info(health_score, status, stats)
        system_info = self._get_system_health_info(stats)
        return {**core_info, **system_info}

    def _get_core_health_info(self, health_score: float, status: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Get core health status information."""
        return {
            "overall_health": health_score,
            "status": status,
            "message_processing": stats["message_handler"]
        }

    def _get_system_health_info(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Get system health status information."""
        validation_status = self._build_validation_status(stats)
        return {
            "circuit_breaker_status": self.config.reliability.circuit_breaker.get_status(),
            "validation_status": validation_status
        }

    def _calculate_health_score(self, stats: Dict[str, Any]) -> float:
        """Calculate overall health score."""
        success_rate = stats["message_handler"]["success_rate"]
        reliability_health = stats["reliability"]["health_score"]
        return (success_rate + reliability_health) / 2

    def _determine_status(self, health_score: float) -> str:
        """Determine health status from score."""
        if health_score > 0.8:
            return "healthy"
        elif health_score > 0.5:
            return "degraded"
        else:
            return "unhealthy"

    def _build_validation_status(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Build validation status information."""
        failures = stats["message_handler"]["validation_failures"]
        limits = self._get_validator_limits()
        return {"validation_failures": failures, "validator_limits": limits}

    def _get_validator_limits(self) -> Dict[str, int]:
        """Get validator limits configuration."""
        return {
            "max_message_size": self.config.validator.max_message_size,
            "max_text_length": self.config.validator.max_text_length
        }