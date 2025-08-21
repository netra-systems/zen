"""WebSocket Broadcast Context and Operations

Defines context structures and operation types for broadcast operations.
Separates context management from agent implementation for modularity.

Business Value: Clean separation of concerns for maintainable broadcast system.
"""

from typing import Dict, List, Any, Union, Optional
from dataclasses import dataclass
from enum import Enum

from netra_backend.app.schemas.registry import WebSocketMessage
from netra_backend.app.schemas.websocket_message_types import ServerMessage


class BroadcastOperation(Enum):
    """WebSocket broadcast operation types."""
    ALL_CONNECTIONS = "all_connections"
    USER_CONNECTIONS = "user_connections"  
    ROOM_CONNECTIONS = "room_connections"


@dataclass
class BroadcastContext:
    """Context for broadcast operations."""
    operation: BroadcastOperation
    message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]
    user_id: Optional[str] = None
    room_id: Optional[str] = None
    connection_ids: Optional[List[str]] = None


class BroadcastContextValidator:
    """Validates broadcast operation contexts."""
    
    @staticmethod
    def validate_broadcast_operation(broadcast_ctx: BroadcastContext) -> bool:
        """Validate broadcast operation preconditions."""
        if not broadcast_ctx or not isinstance(broadcast_ctx, BroadcastContext):
            return False
        return BroadcastContextValidator._check_operation_requirements(
            broadcast_ctx.operation, broadcast_ctx
        )
    
    @staticmethod
    def _check_operation_requirements(operation: BroadcastOperation, 
                                    broadcast_ctx: BroadcastContext) -> bool:
        """Check specific operation requirements."""
        if operation == BroadcastOperation.USER_CONNECTIONS:
            return broadcast_ctx.user_id is not None
        if operation == BroadcastOperation.ROOM_CONNECTIONS:
            return broadcast_ctx.room_id is not None
        return operation == BroadcastOperation.ALL_CONNECTIONS


class BroadcastResultFormatter:
    """Formats broadcast execution results."""
    
    @staticmethod
    def format_execution_result(result: Union["BroadcastResult", Dict[str, Any]], 
                               operation: BroadcastOperation) -> Dict[str, Any]:
        """Format execution result for standardized return."""
        from netra_backend.app.schemas.websocket_message_types import BroadcastResult
        return BroadcastResultFormatter._process_result(result, operation, BroadcastResult)
    
    @staticmethod
    def _process_result(result: Union["BroadcastResult", Dict[str, Any]], 
                      operation: BroadcastOperation, BroadcastResult) -> Dict[str, Any]:
        """Process result based on type."""
        if isinstance(result, BroadcastResult):
            return BroadcastResultFormatter._format_broadcast_result(result, operation)
        else:
            return {**result, "operation": operation.value}
    
    @staticmethod
    def _format_broadcast_result(result: "BroadcastResult", 
                               operation: BroadcastOperation) -> Dict[str, Any]:
        """Format BroadcastResult into standardized dictionary."""
        base_data = {"broadcast_result": result, "operation": operation.value}
        result_data = BroadcastResultFormatter._extract_broadcast_result_data(result)
        return {**base_data, **result_data}
    
    @staticmethod
    def _extract_broadcast_result_data(result: "BroadcastResult") -> Dict[str, Any]:
        """Extract result data from BroadcastResult."""
        return {
            "total_connections": result.total_connections,
            "successful_sends": result.successful,
            "failed_sends": result.failed
        }


class BroadcastContextFactory:
    """Factory for creating broadcast contexts."""
    
    @staticmethod
    def create_all_broadcast_context(message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastContext:
        """Create broadcast context for all connections operation."""
        return BroadcastContext(
            operation=BroadcastOperation.ALL_CONNECTIONS,
            message=message
        )
    
    @staticmethod
    def create_user_broadcast_context(user_id: str, 
                                    message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastContext:
        """Create broadcast context for user connections operation."""
        return BroadcastContext(
            operation=BroadcastOperation.USER_CONNECTIONS,
            message=message,
            user_id=user_id
        )
    
    @staticmethod
    def create_room_broadcast_context(room_id: str, 
                                    message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastContext:
        """Create broadcast context for room connections operation."""
        return BroadcastContext(
            operation=BroadcastOperation.ROOM_CONNECTIONS,
            message=message,
            room_id=room_id
        )