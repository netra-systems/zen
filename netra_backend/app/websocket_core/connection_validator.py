"""WebSocket Connection Validator - Extracted validation logic for WebSocket Manager.

This module handles all connection validation, connection limit enforcement,
and connection isolation token management for the WebSocket Manager.

Business Justification:
- Segment: Platform/Infrastructure
- Business Goal: Maintain system stability during refactoring
- Value Impact: Reduce WebSocket Manager complexity while preserving all functionality
- Strategic Impact: Enable maintainable WebSocket connection management
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Set, Any
from dataclasses import dataclass

from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import (
    UserID, ConnectionID, ensure_user_id, ensure_connection_id
)
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from netra_backend.app.websocket_core.types import WebSocketConnection

logger = get_logger(__name__)

# Connection limits enforcement
MAX_CONNECTIONS_PER_USER = 10


@dataclass
class ConnectionValidationResult:
    """Result of connection validation operations."""
    is_valid: bool
    connection_id: str
    user_id: str
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    isolation_token: Optional[str] = None
    validation_duration_ms: Optional[float] = None


@dataclass
class ConnectionLimitCheckResult:
    """Result of connection limit validation."""
    within_limits: bool
    current_connections: int
    max_allowed: int
    user_id: str
    connection_id: str


class WebSocketConnectionValidator:
    """Handles all WebSocket connection validation logic."""

    def __init__(self):
        """Initialize the connection validator."""
        self._id_manager = UnifiedIDManager()
        self._connection_lock_creation_lock = asyncio.Lock()
        self._user_connection_locks: Dict[str, asyncio.Lock] = {}

    async def get_user_connection_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create user-specific connection lock for thread safety.

        Args:
            user_id: User identifier for connection lock isolation

        Returns:
            User-specific asyncio Lock for connection operations
        """
        if user_id not in self._user_connection_locks:
            async with self._connection_lock_creation_lock:
                # Double-check locking pattern
                if user_id not in self._user_connection_locks:
                    self._user_connection_locks[user_id] = asyncio.Lock()
                    logger.debug(f"Created user-specific connection lock for user: {user_id}")
        return self._user_connection_locks[user_id]

    def validate_connection_basic(self, connection: WebSocketConnection) -> ConnectionValidationResult:
        """Perform basic validation on a WebSocket connection.

        Args:
            connection: WebSocket connection to validate

        Returns:
            ConnectionValidationResult with validation details
        """
        validation_start = time.time()

        try:
            # Validate required fields
            if not connection.user_id:
                return ConnectionValidationResult(
                    is_valid=False,
                    connection_id=connection.connection_id or "unknown",
                    user_id="unknown",
                    error_message="Connection must have a valid user_id",
                    error_type="ValueError",
                    validation_duration_ms=round((time.time() - validation_start) * 1000, 2)
                )

            if not connection.connection_id:
                return ConnectionValidationResult(
                    is_valid=False,
                    connection_id="unknown",
                    user_id=connection.user_id,
                    error_message="Connection must have a valid connection_id",
                    error_type="ValueError",
                    validation_duration_ms=round((time.time() - validation_start) * 1000, 2)
                )

            # Log successful validation
            validation_duration = time.time() - validation_start
            logger.debug(f"CONNECTION VALIDATION: Connection {connection.connection_id} validated successfully")

            return ConnectionValidationResult(
                is_valid=True,
                connection_id=connection.connection_id,
                user_id=connection.user_id,
                validation_duration_ms=round(validation_duration * 1000, 2)
            )

        except Exception as e:
            validation_duration = time.time() - validation_start
            return ConnectionValidationResult(
                is_valid=False,
                connection_id=connection.connection_id or "unknown",
                user_id=connection.user_id or "unknown",
                error_message=str(e),
                error_type=type(e).__name__,
                validation_duration_ms=round(validation_duration * 1000, 2)
            )

    def check_connection_limits(self, connection: WebSocketConnection,
                              current_user_connections: int) -> ConnectionLimitCheckResult:
        """Check if connection is within user limits.

        Args:
            connection: WebSocket connection to check
            current_user_connections: Current number of connections for the user

        Returns:
            ConnectionLimitCheckResult with limit validation details
        """
        within_limits = current_user_connections < MAX_CONNECTIONS_PER_USER

        if not within_limits:
            # Log connection limit context
            connection_limit_context = {
                "user_id": connection.user_id[:8] + "..." if connection.user_id else "unknown",
                "current_connections": current_user_connections,
                "max_allowed": MAX_CONNECTIONS_PER_USER,
                "connection_id": connection.connection_id,
                "rejection_reason": "MAX_CONNECTIONS_PER_USER exceeded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "golden_path_impact": "CONNECTION_REJECTED - User exceeded connection limit"
            }

            logger.warning(f"CONNECTION REJECTED: User {connection.user_id[:8] if connection.user_id else 'unknown'} exceeded MAX_CONNECTIONS_PER_USER ({MAX_CONNECTIONS_PER_USER})")
            logger.warning(f"CONNECTION LIMIT CONTEXT: {json.dumps(connection_limit_context, indent=2)}")

        return ConnectionLimitCheckResult(
            within_limits=within_limits,
            current_connections=current_user_connections,
            max_allowed=MAX_CONNECTIONS_PER_USER,
            user_id=connection.user_id,
            connection_id=connection.connection_id
        )

    def generate_isolation_token(self, connection: WebSocketConnection) -> str:
        """Generate event isolation token for a connection.

        Args:
            connection: WebSocket connection to generate token for

        Returns:
            Unique isolation token string
        """
        return self._id_manager.generate_id(IDType.WEBSOCKET, prefix="isolation", context={
            'user_id': connection.user_id,
            'connection_id': connection.connection_id,
            'purpose': 'event_contamination_prevention'
        })

    def validate_isolation_token_uniqueness(self, connection: WebSocketConnection,
                                          isolation_token: str,
                                          existing_tokens: Dict[str, str],
                                          existing_connections: Dict[str, WebSocketConnection]) -> str:
        """Validate isolation token uniqueness and fix collisions if needed.

        Args:
            connection: WebSocket connection being validated
            isolation_token: Proposed isolation token
            existing_tokens: Dictionary of existing connection_id -> isolation_token mappings
            existing_connections: Dictionary of existing connections

        Returns:
            Valid isolation token (may be regenerated if collision detected)
        """
        # Check for token collisions with other users
        for existing_conn_id, existing_token in existing_tokens.items():
            if existing_conn_id in existing_connections:
                existing_user = existing_connections[existing_conn_id].user_id
                if existing_user != connection.user_id and existing_token == isolation_token:
                    # Critical isolation violation detected
                    logger.error(
                        f"CRITICAL ISOLATION VIOLATION: Token collision detected! "
                        f"User {connection.user_id} vs {existing_user}, "
                        f"Connection {connection.connection_id} vs {existing_conn_id}"
                    )

                    # Generate new token to fix collision
                    isolation_token = self._id_manager.generate_id(IDType.WEBSOCKET, prefix="isolation_fix", context={
                        'user_id': connection.user_id,
                        'connection_id': connection.connection_id,
                        'purpose': 'collision_recovery'
                    })
                    logger.info(f"Generated new isolation token to fix collision: {isolation_token[:8]}...")
                    break

        return isolation_token

    def create_connection_context_log(self, connection: WebSocketConnection,
                                    existing_connections_count: int,
                                    user_existing_connections: int,
                                    has_queued_messages: bool,
                                    manager_mode: str,
                                    stage: str) -> Dict[str, Any]:
        """Create standardized connection context for logging.

        Args:
            connection: WebSocket connection
            existing_connections_count: Total existing connections
            user_existing_connections: User's existing connections count
            has_queued_messages: Whether user has queued messages
            manager_mode: WebSocket manager mode
            stage: Current stage of connection processing

        Returns:
            Dictionary with connection context for logging
        """
        return {
            "connection_id": connection.connection_id,
            "user_id": connection.user_id[:8] + "..." if connection.user_id else "unknown",
            "websocket_available": connection.websocket is not None,
            "websocket_state": str(getattr(connection.websocket, 'client_state', 'unknown')) if hasattr(connection.websocket, 'client_state') else 'unknown',
            "existing_connections_count": existing_connections_count,
            "user_existing_connections": user_existing_connections,
            "has_queued_messages": has_queued_messages,
            "manager_mode": manager_mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "golden_path_stage": stage
        }

    def log_validation_failure(self, validation_result: ConnectionValidationResult) -> None:
        """Log connection validation failure with full context.

        Args:
            validation_result: Failed validation result to log
        """
        validation_failure_context = {
            "connection_id": validation_result.connection_id,
            "user_id": validation_result.user_id[:8] + "..." if validation_result.user_id else "unknown",
            "validation_error": validation_result.error_message,
            "error_type": validation_result.error_type,
            "validation_duration_ms": validation_result.validation_duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "golden_path_impact": "CRITICAL - Connection rejected due to validation failure"
        }

        logger.critical(f"GOLDEN PATH CONNECTION VALIDATION FAILURE: Connection {validation_result.connection_id} validation failed for user {validation_result.user_id[:8] if validation_result.user_id else 'unknown'}...")
        logger.critical(f"VALIDATION FAILURE CONTEXT: {json.dumps(validation_failure_context, indent=2)}")

    def log_connection_success(self, connection: WebSocketConnection,
                             total_connections: int,
                             user_total_connections: int,
                             connection_duration: float,
                             active_users: int,
                             manager_mode: str) -> None:
        """Log successful connection addition with full context.

        Args:
            connection: Successfully added connection
            total_connections: Total connections in manager
            user_total_connections: Total connections for this user
            connection_duration: Time taken to add connection
            active_users: Number of active users
            manager_mode: WebSocket manager mode
        """
        connection_success_context = {
            "connection_id": connection.connection_id,
            "user_id": connection.user_id[:8] + "..." if connection.user_id else "unknown",
            "total_connections": total_connections,
            "user_total_connections": user_total_connections,
            "connection_duration_ms": round(connection_duration * 1000, 2),
            "active_users": active_users,
            "manager_mode": manager_mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "golden_path_milestone": "Connection successfully added to manager"
        }

        logger.info(f"GOLDEN PATH CONNECTION ADDED: Connection {connection.connection_id} added for user {connection.user_id[:8] if connection.user_id else 'unknown'}... in {connection_duration*1000:.2f}ms")
        logger.info(f"CONNECTION SUCCESS CONTEXT: {json.dumps(connection_success_context, indent=2)}")