"""WebSocket Message Validator - Extracted message validation and processing logic.

This module handles all message validation, cross-user contamination prevention,
message recovery, and business event processing for the WebSocket Manager.

Business Justification:
- Segment: Platform/Infrastructure
- Business Goal: Maintain system stability during refactoring
- Value Impact: Reduce WebSocket Manager complexity while preserving all functionality
- Strategic Impact: Enable maintainable WebSocket message handling
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Set, Any, List, Union
from dataclasses import dataclass

from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import UserID, ensure_user_id
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from netra_backend.app.websocket_core.types import _serialize_message_safely

logger = get_logger(__name__)


@dataclass
class MessageValidationResult:
    """Result of message validation operations."""
    is_valid: bool
    user_id: str
    message: Dict[str, Any]
    event_id: Optional[str] = None
    error_message: Optional[str] = None
    contamination_detected: bool = False
    sanitized_message: Optional[Dict[str, Any]] = None


@dataclass
class MessageDeliveryResult:
    """Result of message delivery operations."""
    successful_sends: int
    failed_connections: List[tuple]
    total_connections: int
    user_id: str
    message_type: str


class WebSocketMessageValidator:
    """Handles all WebSocket message validation and processing logic."""

    def __init__(self):
        """Initialize the message validator."""
        self._id_manager = UnifiedIDManager()
        self._event_delivery_tracking: Dict[str, Dict[str, Any]] = {}
        self._event_queue_stats = {
            'total_events_sent': 0,
            'contamination_prevented': 0
        }
        self._cross_user_detection: Dict[str, int] = {}
        self._message_recovery_queue: Dict[str, List[Dict[str, Any]]] = {}

    def validate_message_for_user(self, user_id: Union[str, UserID],
                                message: Dict[str, Any]) -> MessageValidationResult:
        """Validate message for a specific user and prevent cross-user contamination.

        Args:
            user_id: Target user ID for the message
            message: Message to validate

        Returns:
            MessageValidationResult with validation details
        """
        # Validate user_id
        validated_user_id = ensure_user_id(user_id)

        # Generate event ID for tracking
        event_id = self._id_manager.generate_id(IDType.WEBSOCKET, prefix="event", context={
            'user_id': validated_user_id,
            'purpose': 'cross_user_contamination_prevention'
        })

        contamination_detected = False
        sanitized_message = None

        # Validate message doesn't contain foreign user data
        if isinstance(message, dict):
            for key, value in message.items():
                if key.endswith('_user_id') and value != validated_user_id:
                    logger.error(
                        f"CROSS-USER CONTAMINATION DETECTED: Message for user {validated_user_id} "
                        f"contains foreign user_id in field '{key}': {value}"
                    )
                    self._event_queue_stats['contamination_prevented'] += 1
                    self._cross_user_detection[validated_user_id] = self._cross_user_detection.get(validated_user_id, 0) + 1

                    # Sanitize the message
                    if not sanitized_message:
                        sanitized_message = message.copy()
                    sanitized_message[key] = validated_user_id
                    contamination_detected = True
                    logger.warning(f"Sanitized contaminated field '{key}' for user {validated_user_id}")

        # Track event delivery
        self._event_delivery_tracking[event_id] = {
            'user_id': validated_user_id,
            'message_type': message.get('type', 'unknown'),
            'timestamp': datetime.now(timezone.utc),
            'delivery_status': 'pending',
            'contamination_checks': 'passed' if not contamination_detected else 'sanitized'
        }
        self._event_queue_stats['total_events_sent'] += 1

        return MessageValidationResult(
            is_valid=True,
            user_id=validated_user_id,
            message=sanitized_message if sanitized_message else message,
            event_id=event_id,
            contamination_detected=contamination_detected,
            sanitized_message=sanitized_message
        )

    def process_business_event(self, event_type: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process business events to ensure proper field structure for Golden Path validation.

        This method transforms generic WebSocket events into business-specific events
        with the required fields expected by mission-critical tests and client applications.

        Args:
            event_type: Type of event ('tool_executing', 'tool_completed', 'agent_started', etc.)
            data: Raw event data

        Returns:
            Dict with proper business event structure, or None if processing fails
        """
        try:
            # Handle tool_executing events
            if event_type == "tool_executing":
                payload = {
                    "tool_name": data.get("tool_name", data.get("name", "unknown_tool")),
                    "parameters": data.get("parameters", data.get("params", {})),
                    "timestamp": data.get("timestamp", time.time()),
                    "user_id": data.get("user_id"),
                    "thread_id": data.get("thread_id"),
                    # Preserve additional fields
                    **{k: v for k, v in data.items() if k not in ["tool_name", "parameters", "timestamp"]}
                }
                return {
                    "type": event_type,
                    "payload": payload
                }

            # Handle tool_completed events
            elif event_type == "tool_completed":
                payload = {
                    "tool_name": data.get("tool_name", data.get("name", "unknown_tool")),
                    "results": data.get("results", data.get("result", data.get("output", {}))),
                    "duration": data.get("duration", data.get("duration_ms", data.get("elapsed_time", 0))),
                    "timestamp": data.get("timestamp", time.time()),
                    "success": data.get("success", True),
                    "user_id": data.get("user_id"),
                    "thread_id": data.get("thread_id"),
                    # Preserve additional fields
                    **{k: v for k, v in data.items() if k not in ["tool_name", "results", "duration", "timestamp", "success"]}
                }
                return {
                    "type": event_type,
                    "payload": payload
                }

            # Handle agent_started events
            elif event_type == "agent_started":
                payload = {
                    "user_id": data.get("user_id"),
                    "thread_id": data.get("thread_id"),
                    "timestamp": data.get("timestamp", time.time()),
                    "agent_name": data.get("agent_name", data.get("name", "unknown_agent")),
                    "task_description": data.get("task_description", data.get("task", "Processing request")),
                    # Preserve additional fields
                    **{k: v for k, v in data.items() if k not in ["user_id", "thread_id", "timestamp", "agent_name", "task_description"]}
                }
                return {
                    "type": event_type,
                    "payload": payload
                }

            # Handle agent_thinking events
            elif event_type == "agent_thinking":
                payload = {
                    "reasoning": data.get("reasoning", data.get("thought", data.get("thinking", "Agent is processing..."))),
                    "timestamp": data.get("timestamp", time.time()),
                    "user_id": data.get("user_id"),
                    "thread_id": data.get("thread_id"),
                    # Preserve additional fields
                    **{k: v for k, v in data.items() if k not in ["reasoning", "timestamp"]}
                }
                return {
                    "type": event_type,
                    "payload": payload
                }

            # Handle agent_completed events
            elif event_type == "agent_completed":
                payload = {
                    "status": data.get("status", "completed"),
                    "final_response": data.get("final_response", data.get("response", data.get("result", "Task completed"))),
                    "timestamp": data.get("timestamp", time.time()),
                    "user_id": data.get("user_id"),
                    "thread_id": data.get("thread_id"),
                    # Preserve additional fields
                    **{k: v for k, v in data.items() if k not in ["status", "final_response", "timestamp"]}
                }
                return {
                    "type": event_type,
                    "payload": payload
                }

            # For other event types, wrap data in payload object
            else:
                payload = {
                    "timestamp": data.get("timestamp", time.time()),
                    **data
                }
                return {
                    "type": event_type,
                    "payload": payload
                }

        except Exception as e:
            logger.error(f"Failed to process business event {event_type}: {e}")
            return None

    async def store_failed_message(self, user_id: str, message: Dict[str, Any],
                                 failure_reason: str) -> None:
        """Store a failed message for potential recovery.

        Args:
            user_id: User ID for the failed message
            message: Message that failed to send
            failure_reason: Reason for the failure
        """
        # Create recovery entry
        recovery_msg = {
            **message,
            'failure_reason': failure_reason,
            'failed_at': datetime.now(timezone.utc).isoformat(),
            'recovery_attempts': 0
        }

        # Store in recovery queue
        if user_id not in self._message_recovery_queue:
            self._message_recovery_queue[user_id] = []

        self._message_recovery_queue[user_id].append(recovery_msg)

        # Limit queue size to prevent memory issues
        max_queue_size = 100
        if len(self._message_recovery_queue[user_id]) > max_queue_size:
            self._message_recovery_queue[user_id] = self._message_recovery_queue[user_id][-max_queue_size:]

        logger.warning(f"Stored failed message for user {user_id}: {failure_reason}")

    async def process_queued_messages(self, user_id: str, send_callback) -> None:
        """Process queued messages for a user after connection established.

        Args:
            user_id: User ID to process messages for
            send_callback: Callback function to send messages (should be send_to_user)
        """
        if user_id not in self._message_recovery_queue:
            return

        messages = self._message_recovery_queue.get(user_id, [])
        if not messages:
            return

        logger.info(f"Processing {len(messages)} queued messages for user {user_id}")

        # Clear the queue first to prevent re-processing
        self._message_recovery_queue[user_id] = []

        # Small delay to ensure connection is fully established
        await asyncio.sleep(0.1)

        # Send each queued message with timeout to prevent hanging
        for msg in messages:
            try:
                # Remove recovery metadata before sending
                clean_msg = {k: v for k, v in msg.items()
                           if k not in ['failure_reason', 'failed_at', 'recovery_attempts']}

                # Add a flag indicating this is a recovered message
                clean_msg['recovered'] = True

                # Add timeout to prevent infinite wait on send_to_user
                await asyncio.wait_for(
                    send_callback(user_id, clean_msg),
                    timeout=3.0  # Reasonable timeout per message
                )
                logger.debug(f"Successfully delivered queued message type '{clean_msg.get('type')}' to user {user_id}")

            except asyncio.TimeoutError:
                logger.error(f"Timeout delivering queued message to user {user_id}: {clean_msg.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"Failed to deliver queued message to user {user_id}: {e}")

        logger.info(f"Completed processing queued messages for user {user_id}")

    def validate_delivery_context(self, user_id: str, message: Dict[str, Any],
                                connection_ids: Set[str]) -> Dict[str, Any]:
        """Validate message delivery context and determine appropriate handling.

        Args:
            user_id: User ID for the message
            message: Message to be delivered
            connection_ids: Available connection IDs for the user

        Returns:
            Dictionary with validation context and recommendations
        """
        message_type = message.get('type', 'unknown')

        # Check if this is a startup/test scenario
        is_startup_test = (message_type == 'startup_test' or
                          user_id.startswith('startup_test_'))

        context = {
            'user_id': user_id,
            'message_type': message_type,
            'connection_count': len(connection_ids),
            'is_startup_test': is_startup_test,
            'should_store_for_recovery': True,
            'log_level': 'debug' if is_startup_test else 'critical',
            'description': 'Startup test scenario' if is_startup_test else 'No connections available'
        }

        return context

    def create_message_delivery_result(self, successful_sends: int,
                                     failed_connections: List[tuple],
                                     total_connections: int,
                                     user_id: str,
                                     message_type: str) -> MessageDeliveryResult:
        """Create a standardized message delivery result.

        Args:
            successful_sends: Number of successful message sends
            failed_connections: List of (connection_id, error) tuples for failed sends
            total_connections: Total number of connections attempted
            user_id: User ID for the delivery
            message_type: Type of message delivered

        Returns:
            MessageDeliveryResult with delivery details
        """
        return MessageDeliveryResult(
            successful_sends=successful_sends,
            failed_connections=failed_connections,
            total_connections=total_connections,
            user_id=user_id,
            message_type=message_type
        )

    def log_delivery_failure(self, result: MessageDeliveryResult) -> None:
        """Log message delivery failure with appropriate severity.

        Args:
            result: MessageDeliveryResult with failure details
        """
        if result.successful_sends == 0:
            logger.critical(
                f"COMPLETE MESSAGE DELIVERY FAILURE: All {result.total_connections} connections "
                f"failed for user {result.user_id}. Message type: {result.message_type}. "
                f"Failed connections: {[f'{conn_id}: {error}' for conn_id, error in result.failed_connections]}"
            )
        elif result.failed_connections:
            logger.warning(
                f"PARTIAL MESSAGE DELIVERY: {result.successful_sends}/{result.total_connections} "
                f"connections succeeded for user {result.user_id}. "
                f"Failed: {[f'{conn_id}: {error}' for conn_id, error in result.failed_connections]}"
            )

    def get_contamination_stats(self) -> Dict[str, Any]:
        """Get current cross-user contamination statistics.

        Returns:
            Dictionary with contamination prevention statistics
        """
        return {
            'total_events_sent': self._event_queue_stats['total_events_sent'],
            'contamination_prevented': self._event_queue_stats['contamination_prevented'],
            'users_with_contamination': len(self._cross_user_detection),
            'contamination_by_user': dict(self._cross_user_detection)
        }

    def get_recovery_queue_stats(self) -> Dict[str, Any]:
        """Get current message recovery queue statistics.

        Returns:
            Dictionary with recovery queue statistics
        """
        return {
            'users_with_queued_messages': len(self._message_recovery_queue),
            'total_queued_messages': sum(len(queue) for queue in self._message_recovery_queue.values()),
            'queue_by_user': {user_id: len(queue) for user_id, queue in self._message_recovery_queue.items()}
        }

    def create_safe_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Create a safely serialized message for WebSocket transmission.

        Args:
            message: Original message to serialize

        Returns:
            Safely serialized message
        """
        return _serialize_message_safely(message)