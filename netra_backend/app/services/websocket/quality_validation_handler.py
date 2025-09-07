"""Quality validation WebSocket handler.

Handles on-demand content quality validation.
Follows 450-line limit with 25-line function limit.
"""

from typing import Any, Dict

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.quality_gate_service import (
    ContentType,
    QualityGateService,
)
from netra_backend.app.services.websocket.message_handler import BaseMessageHandler
from netra_backend.app.websocket_core import get_websocket_manager

logger = central_logger.get_logger(__name__)


class QualityValidationHandler(BaseMessageHandler):
    """Handler for on-demand quality validation."""
    
    def __init__(self, quality_gate_service: QualityGateService):
        """Initialize quality validation handler."""
        self.quality_gate_service = quality_gate_service
    
    def get_message_type(self) -> str:
        """Get the message type this handler processes."""
        return "validate_content"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle content validation request."""
        try:
            validation_params = self._extract_validation_params(payload)
            result = await self._validate_content_with_params(user_id, validation_params)
            await self._send_validation_result(user_id, result)
        except Exception as e:
            await self._handle_validation_error(user_id, e)

    def _extract_validation_params(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract validation parameters from payload."""
        content = payload.get("content", "")
        content_type_str = payload.get("content_type", "general")
        strict_mode = payload.get("strict_mode", False)
        content_type = self._map_content_type(content_type_str)
        return self._build_validation_params_dict(content, content_type, strict_mode)

    def _build_validation_params_dict(self, content: str, content_type, strict_mode: bool) -> Dict[str, Any]:
        """Build validation parameters dictionary."""
        return {
            "content": content,
            "content_type": content_type,
            "strict_mode": strict_mode
        }

    def _map_content_type(self, content_type_str: str) -> ContentType:
        """Map string to ContentType enum."""
        content_type_map = self._get_content_type_mapping()
        return content_type_map.get(content_type_str, ContentType.GENERAL)

    def _get_content_type_mapping(self) -> Dict[str, ContentType]:
        """Get content type string to enum mapping."""
        return {
            "optimization": ContentType.OPTIMIZATION,
            "data_analysis": ContentType.DATA_ANALYSIS,
            "action_plan": ContentType.ACTION_PLAN,
            "report": ContentType.REPORT,
            "triage": ContentType.TRIAGE,
            "error": ContentType.ERROR_MESSAGE,
            "general": ContentType.GENERAL
        }

    async def _validate_content_with_params(self, user_id: str, params: Dict[str, Any]):
        """Validate content using extracted parameters."""
        return await self.quality_gate_service.validate_content(
            params["content"],
            params["content_type"],
            params["strict_mode"]
        )

    async def _send_validation_result(self, user_id: str, result) -> None:
        """Send validation result to user."""
        message = self._build_validation_message(result)
        manager = get_websocket_manager()
        await manager.send_message(user_id, message)

    def _build_validation_message(self, result) -> Dict[str, Any]:
        """Build validation result message."""
        return {
            "type": "content_validation_result",
            "payload": result
        }

    async def _handle_validation_error(self, user_id: str, error: Exception) -> None:
        """Handle content validation error."""
        logger.error(f"Error validating content: {str(error)}")
        error_message = f"Failed to validate content: {str(error)}"
        manager = get_websocket_manager()
        await manager.send_error(user_id, error_message)