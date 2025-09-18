"""WebSocket User Context Handler - Extracted user context and isolation management.

This module handles all user context management, user isolation validation,
event contamination prevention, and user-specific queue management for the WebSocket Manager.

Business Justification:
- Segment: Platform/Infrastructure
- Business Goal: Maintain system stability during refactoring
- Value Impact: Reduce WebSocket Manager complexity while preserving all functionality
- Strategic Impact: Enable maintainable WebSocket user isolation management
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Set, Any, List
from dataclasses import dataclass
import queue

from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import UserID

logger = get_logger(__name__)


@dataclass
class UserIsolationResult:
    """Result of user isolation validation."""
    is_valid: bool
    user_id: str
    operation: str
    manager_user_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class EventIsolationData:
    """Event isolation metadata for contamination prevention."""
    target_user_id: str
    manager_user_id: Optional[str]
    isolation_token: str
    timestamp: str


class UserIsolationViolation(Exception):
    """Exception raised when user isolation is violated."""
    pass


class WebSocketUserContextHandler:
    """Handles all WebSocket user context and isolation management."""

    def __init__(self, user_context=None):
        """Initialize the user context handler.

        Args:
            user_context: Optional user context for isolated mode
        """
        self.user_context = user_context
        self._cross_user_detection: Dict[str, int] = {}
        self._event_isolation_tokens: Dict[str, str] = {}  # connection_id -> isolation_token
        self._event_delivery_tracking: Dict[str, Dict[str, Any]] = {}
        self._user_event_queues: Dict[str, queue.Queue] = {}

    def validate_user_isolation(self, user_id: str, operation: str = "unknown") -> UserIsolationResult:
        """Validate user isolation for operations.

        This method enforces user isolation by ensuring operations are only
        performed on behalf of the user this manager was created for.

        Args:
            user_id: User ID requesting the operation
            operation: Description of operation for logging

        Returns:
            UserIsolationResult with validation details
        """
        try:
            manager_user_id = getattr(self.user_context, 'user_id', None)

            # If no user context is set, allow operation (unified mode)
            if not manager_user_id:
                return UserIsolationResult(
                    is_valid=True,
                    user_id=user_id,
                    operation=operation,
                    manager_user_id=None
                )

            # Validate user matches manager's user context
            if str(manager_user_id) != str(user_id):
                error_msg = f"User isolation violation: operation '{operation}' for user {user_id} != manager user {manager_user_id}"
                logger.error(error_msg)
                return UserIsolationResult(
                    is_valid=False,
                    user_id=user_id,
                    operation=operation,
                    manager_user_id=manager_user_id,
                    error_message=error_msg
                )

            return UserIsolationResult(
                is_valid=True,
                user_id=user_id,
                operation=operation,
                manager_user_id=manager_user_id
            )

        except Exception as e:
            error_msg = f"User isolation validation failed for {operation}: {e}"
            logger.error(error_msg)
            return UserIsolationResult(
                is_valid=False,
                user_id=user_id,
                operation=operation,
                error_message=error_msg
            )

    def prevent_cross_user_event_bleeding(self, event_data: Dict[str, Any], target_user_id: str) -> Dict[str, Any]:
        """Prevent cross-user event bleeding.

        This method ensures events are only delivered to the intended user
        and adds isolation metadata to prevent contamination.

        Args:
            event_data: Event data to be sent
            target_user_id: User ID that should receive this event

        Returns:
            Dict[str, Any]: Event data with isolation metadata

        Raises:
            UserIsolationViolation: If cross-user bleeding is detected
        """
        # Add user isolation metadata
        isolated_event = event_data.copy()
        isolation_data = EventIsolationData(
            target_user_id=target_user_id,
            manager_user_id=getattr(self.user_context, 'user_id', None),
            isolation_token=f"{target_user_id}_{time.time()}",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        isolated_event['_user_isolation'] = {
            'target_user_id': isolation_data.target_user_id,
            'manager_user_id': isolation_data.manager_user_id,
            'isolation_token': isolation_data.isolation_token,
            'timestamp': isolation_data.timestamp
        }

        # Validate user match in isolated mode
        if isolation_data.manager_user_id and str(isolation_data.manager_user_id) != str(target_user_id):
            logger.warning(f"Cross-user event bleeding prevented: manager_user={isolation_data.manager_user_id}, target_user={target_user_id}")
            raise UserIsolationViolation(f"Event targeting different user: {target_user_id} != {isolation_data.manager_user_id}")

        return isolated_event

    async def validate_event_isolation(self, user_id: str, connection_id: str) -> bool:
        """Validate event isolation for user and connection.

        Args:
            user_id: User ID to validate
            connection_id: Connection ID to validate

        Returns:
            bool: True if isolation is valid, False otherwise
        """
        if connection_id not in self._event_isolation_tokens:
            logger.warning(f"Connection {connection_id} has no isolation token")
            return False

        # Additional validation logic can be added here
        isolation_token = self._event_isolation_tokens[connection_id]

        # Basic validation that token exists and is not empty
        if not isolation_token:
            logger.warning(f"Empty isolation token for connection {connection_id}")
            return False

        return True

    async def force_cleanup_user_events(self, user_id: str) -> None:
        """Force cleanup of all event tracking for a specific user.

        Args:
            user_id: User ID to clean up events for
        """
        # Clear user event queue
        if user_id in self._user_event_queues:
            queue_obj = self._user_event_queues[user_id]
            while not queue_obj.empty():
                try:
                    queue_obj.get_nowait()
                except queue.Empty:
                    break
            del self._user_event_queues[user_id]

        # Clear cross-user detection for this user
        if user_id in self._cross_user_detection:
            del self._cross_user_detection[user_id]

        # Clear event delivery tracking for this user
        user_events = [
            event_id for event_id, data in self._event_delivery_tracking.items()
            if data.get('user_id') == user_id
        ]

        for event_id in user_events:
            del self._event_delivery_tracking[event_id]

        logger.info(f"Force cleaned up all event tracking for user {user_id}")

    def detect_queue_overflow(self, user_id: str) -> bool:
        """Detect if user's event queue is approaching overflow.

        Args:
            user_id: User ID to check queue for

        Returns:
            bool: True if queue is approaching overflow, False otherwise
        """
        if user_id not in self._user_event_queues:
            return False

        queue_obj = self._user_event_queues[user_id]

        # Consider overflow if queue has more than 1000 items
        max_queue_size = 1000
        current_size = queue_obj.qsize()

        return current_size > (max_queue_size * 0.8)  # 80% threshold

    async def cleanup_expired_event_tracking(self, max_age_hours: int = 24) -> None:
        """Clean up expired event tracking entries.

        Args:
            max_age_hours: Maximum age in hours for tracking entries
        """
        cutoff_time = datetime.now(timezone.utc) - timezone.timedelta(hours=max_age_hours)
        expired_events = []

        for event_id, tracking_data in self._event_delivery_tracking.items():
            event_timestamp = tracking_data.get('timestamp')
            if isinstance(event_timestamp, datetime) and event_timestamp < cutoff_time:
                expired_events.append(event_id)

        # Remove expired events
        for event_id in expired_events:
            del self._event_delivery_tracking[event_id]

        if expired_events:
            logger.info(f"Cleaned up {len(expired_events)} expired event tracking entries")

    def get_user_context_info(self) -> Dict[str, Any]:
        """Get information about the current user context.

        Returns:
            Dictionary with user context information
        """
        return {
            'has_user_context': self.user_context is not None,
            'user_id': getattr(self.user_context, 'user_id', None),
            'context_type': type(self.user_context).__name__ if self.user_context else None,
            'cross_user_detections': dict(self._cross_user_detection),
            'active_isolation_tokens': len(self._event_isolation_tokens),
            'active_event_tracking': len(self._event_delivery_tracking)
        }

    def get_contamination_stats(self) -> Dict[str, Any]:
        """Get cross-user contamination statistics.

        Returns:
            Dictionary with contamination statistics
        """
        total_detections = sum(self._cross_user_detection.values())
        return {
            'total_contamination_detections': total_detections,
            'affected_users': len(self._cross_user_detection),
            'detections_by_user': dict(self._cross_user_detection),
            'user_event_queues': {
                user_id: queue_obj.qsize()
                for user_id, queue_obj in self._user_event_queues.items()
            }
        }

    def register_isolation_token(self, connection_id: str, isolation_token: str) -> None:
        """Register an isolation token for a connection.

        Args:
            connection_id: Connection ID to register token for
            isolation_token: Isolation token to register
        """
        self._event_isolation_tokens[connection_id] = isolation_token
        logger.debug(f"Registered isolation token for connection {connection_id}: {isolation_token[:8]}...")

    def unregister_isolation_token(self, connection_id: str) -> None:
        """Unregister an isolation token for a connection.

        Args:
            connection_id: Connection ID to unregister token for
        """
        if connection_id in self._event_isolation_tokens:
            del self._event_isolation_tokens[connection_id]
            logger.debug(f"Unregistered isolation token for connection {connection_id}")

    def increment_cross_user_detection(self, user_id: str) -> int:
        """Increment cross-user detection count for a user.

        Args:
            user_id: User ID to increment count for

        Returns:
            New detection count for the user
        """
        self._cross_user_detection[user_id] = self._cross_user_detection.get(user_id, 0) + 1
        return self._cross_user_detection[user_id]

    def get_or_create_user_event_queue(self, user_id: str) -> queue.Queue:
        """Get or create an event queue for a user.

        Args:
            user_id: User ID to get/create queue for

        Returns:
            Queue object for the user
        """
        if user_id not in self._user_event_queues:
            self._user_event_queues[user_id] = queue.Queue(maxsize=1000)  # Limit queue size
        return self._user_event_queues[user_id]