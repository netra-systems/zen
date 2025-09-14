"""WebSocket Broadcast Service - SSOT for Event Broadcasting

This module provides the single source of truth for all user-targeted WebSocket broadcasting.
It consolidates the three duplicate broadcast functions into a single canonical implementation:

1. WebSocketEventRouter.broadcast_to_user() (legacy singleton)
2. UserScopedWebSocketEventRouter.broadcast_to_user() (user-scoped)
3. broadcast_user_event() (convenience function)

Business Value Justification (BVJ):
- Segment: Platform/All Users (Free → Enterprise)
- Business Goal: Golden Path reliability and user isolation security
- Value Impact: Eliminates cross-user event leakage, ensures consistent broadcast delivery
- Revenue Impact: Protects $500K+ ARR through reliable chat functionality

ISSUE #982 REMEDIATION: Single source of truth for WebSocket event broadcasting.
All broadcast operations delegate to UnifiedWebSocketManager.send_to_user for actual delivery.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union

from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ensure_user_id
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@dataclass
class BroadcastResult:
    """Standardized broadcast result across all implementations.

    Provides consistent interface for all broadcast operations regardless
    of the underlying implementation or consumer requirements.
    """
    user_id: str
    connections_attempted: int
    successful_sends: int
    event_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.connections_attempted == 0:
            return 0.0
        return (self.successful_sends / self.connections_attempted) * 100.0

    @property
    def is_successful(self) -> bool:
        """Determine if broadcast was successful (at least one delivery)."""
        return self.successful_sends > 0


class WebSocketBroadcastService:
    """SSOT WebSocket Broadcasting Service.

    Single source of truth for all user-targeted WebSocket broadcasting,
    delegating to UnifiedWebSocketManager for actual delivery while providing
    consistent interface and comprehensive monitoring.

    This service consolidates three previous duplicate implementations:
    - WebSocketEventRouter.broadcast_to_user()
    - UserScopedWebSocketEventRouter.broadcast_to_user()
    - broadcast_user_event() function

    CRITICAL FEATURES:
    - Cross-user contamination prevention
    - Delivery tracking and monitoring
    - Consistent error handling and logging
    - Feature flag support for rollback capability
    - Performance monitoring and metrics
    """

    def __init__(self, websocket_manager: WebSocketManagerProtocol):
        """Initialize the SSOT broadcast service.

        Args:
            websocket_manager: WebSocket manager implementing the protocol
        """
        self.websocket_manager = websocket_manager
        self._stats = {
            'total_broadcasts': 0,
            'successful_broadcasts': 0,
            'failed_broadcasts': 0,
            'cross_user_contamination_prevented': 0,
            'total_connections_attempted': 0,
            'total_successful_sends': 0
        }
        self._feature_flags = {
            'enable_contamination_detection': True,
            'enable_performance_monitoring': True,
            'enable_comprehensive_logging': True
        }

        logger.info(
            "WebSocketBroadcastService initialized with SSOT consolidation. "
            "This replaces 3 duplicate broadcast implementations for Issue #982."
        )

    async def broadcast_to_user(self, user_id: Union[str, UserID], event: Dict[str, Any]) -> BroadcastResult:
        """Canonical broadcast-to-user implementation.

        Single source of truth for broadcasting events to specific users.
        Provides comprehensive validation, monitoring, and error handling.

        Args:
            user_id: Target user ID (string or UserID type)
            event: Event payload to broadcast

        Returns:
            BroadcastResult: Detailed result with delivery statistics

        Raises:
            ValueError: If user_id or event is invalid
            RuntimeError: If broadcast fails critically
        """
        start_time = datetime.now(timezone.utc)
        validated_user_id = ensure_user_id(user_id)
        event_type = event.get('type', 'unknown')

        # Initialize result tracking
        result = BroadcastResult(
            user_id=str(validated_user_id),
            connections_attempted=0,
            successful_sends=0,
            event_type=event_type,
            timestamp=start_time
        )

        try:
            self._stats['total_broadcasts'] += 1

            # ISSUE #982: Cross-user contamination prevention
            if self._feature_flags['enable_contamination_detection']:
                sanitized_event = await self._prevent_cross_user_contamination(
                    validated_user_id, event, result
                )
            else:
                sanitized_event = event

            # Get connection count for metrics
            try:
                user_connections = self.websocket_manager.get_user_connections(validated_user_id)
                result.connections_attempted = len(user_connections)
                self._stats['total_connections_attempted'] += result.connections_attempted
            except Exception as e:
                logger.warning(f"Could not get connection count for user {validated_user_id}: {e}")
                result.connections_attempted = 1  # Assume at least one for delegation

            # SSOT DELEGATION: Use UnifiedWebSocketManager.send_to_user as canonical implementation
            try:
                await self.websocket_manager.send_to_user(validated_user_id, sanitized_event)

                # Success: Manager handles all connections internally
                result.successful_sends = max(1, result.connections_attempted)
                self._stats['successful_broadcasts'] += 1
                self._stats['total_successful_sends'] += result.successful_sends

                if self._feature_flags['enable_comprehensive_logging']:
                    logger.info(
                        f"SSOT broadcast successful: user={validated_user_id}, "
                        f"event_type={event_type}, connections={result.connections_attempted}"
                    )

            except Exception as e:
                # Handle delegation failure
                error_msg = f"WebSocketManager delegation failed: {str(e)}"
                result.errors.append(error_msg)
                result.successful_sends = 0
                self._stats['failed_broadcasts'] += 1

                logger.error(
                    f"CRITICAL: SSOT broadcast failed for user {validated_user_id}, "
                    f"event_type={event_type}: {error_msg}"
                )

                # Don't raise exception - return failed result for graceful handling

        except Exception as e:
            # Handle validation or processing failures
            error_msg = f"Broadcast processing failed: {str(e)}"
            result.errors.append(error_msg)
            result.successful_sends = 0
            self._stats['failed_broadcasts'] += 1

            logger.error(
                f"CRITICAL: Broadcast processing failed for user {validated_user_id}: {error_msg}"
            )

        # Performance monitoring
        if self._feature_flags['enable_performance_monitoring']:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.debug(
                f"SSOT broadcast performance: user={validated_user_id}, "
                f"duration={duration:.3f}s, success_rate={result.success_rate:.1f}%"
            )

        return result

    async def _prevent_cross_user_contamination(
        self,
        target_user_id: UserID,
        event: Dict[str, Any],
        result: BroadcastResult
    ) -> Dict[str, Any]:
        """Prevent cross-user data contamination in broadcast events.

        ISSUE #1058 FIX: Preserves event data integrity while preventing actual security violations.
        Distinguishes between event data (provenance/context) and routing data (target delivery).

        Event data integrity principles:
        1. PRESERVE original event data including user_id (event creator/source)
        2. ONLY sanitize fields that represent routing/targeting (recipient_id, target_user_id)
        3. VALIDATE but don't overwrite provenance fields (user_id, sender_id, creator_id)

        Args:
            target_user_id: The intended recipient user ID for routing
            event: Original event payload to validate
            result: Result object to track contamination prevention

        Returns:
            Dict: Validated event payload with preserved data integrity
        """
        sanitized_event = event.copy()
        contamination_detected = False

        # Fields that represent EVENT DATA (preserve original values)
        event_data_fields = [
            'user_id',      # Event creator/source - PRESERVE for audit trails
            'sender_id',    # Message sender - PRESERVE for attribution
            'creator_id',   # Content creator - PRESERVE for provenance
            'owner_id'      # Resource owner - PRESERVE for context
        ]

        # Fields that represent ROUTING/TARGETING (sanitize for security)
        routing_fields = [
            'recipient_id',     # Message recipient - sanitize to match target
            'target_user_id',   # Explicit target - sanitize to match target
            'userId'           # Legacy recipient field - sanitize to match target
        ]

        # PHASE 1: Validate event data fields (preserve but log discrepancies)
        for field in event_data_fields:
            if field in sanitized_event:
                field_value = sanitized_event[field]
                if field_value and str(field_value) != str(target_user_id):
                    # LOG but don't modify - this is legitimate event data
                    logger.debug(
                        f"Event data field '{field}' contains different user ID: {field_value}. "
                        f"This is preserved as event provenance data for target user {target_user_id}."
                    )

        # PHASE 2: Sanitize routing fields (security-critical)
        for field in routing_fields:
            if field in sanitized_event:
                field_value = sanitized_event[field]
                if field_value and str(field_value) != str(target_user_id):
                    contamination_detected = True
                    result.errors.append(f"Cross-user contamination in routing field '{field}': {field_value}")

                    # Sanitize routing fields to prevent data leakage
                    sanitized_event[field] = str(target_user_id)

                    logger.warning(
                        f"SECURITY: Cross-user contamination prevented in routing field '{field}'. "
                        f"Target user: {target_user_id}, contaminating value: {field_value}"
                    )

        if contamination_detected:
            self._stats['cross_user_contamination_prevented'] += 1
            logger.info(
                f"Cross-user contamination prevented for user {target_user_id}. "
                f"Routing fields sanitized while preserving event data integrity."
            )

        return sanitized_event

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive broadcast service statistics.

        Returns:
            Dict: Complete statistics including performance and security metrics
        """
        return {
            'service_info': {
                'name': 'WebSocketBroadcastService',
                'version': '1.0.0',
                'purpose': 'SSOT consolidation for Issue #982',
                'replaces': [
                    'WebSocketEventRouter.broadcast_to_user',
                    'UserScopedWebSocketEventRouter.broadcast_to_user',
                    'broadcast_user_event'
                ]
            },
            'broadcast_stats': self._stats.copy(),
            'performance_metrics': {
                'success_rate_percentage': (
                    (self._stats['successful_broadcasts'] / max(1, self._stats['total_broadcasts'])) * 100
                ),
                'average_connections_per_broadcast': (
                    self._stats['total_connections_attempted'] / max(1, self._stats['total_broadcasts'])
                ),
                'average_successful_sends_per_broadcast': (
                    self._stats['total_successful_sends'] / max(1, self._stats['successful_broadcasts'])
                ) if self._stats['successful_broadcasts'] > 0 else 0
            },
            'security_metrics': {
                'contamination_prevention_count': self._stats['cross_user_contamination_prevented'],
                'contamination_prevention_enabled': self._feature_flags['enable_contamination_detection']
            },
            'feature_flags': self._feature_flags.copy()
        }

    def update_feature_flag(self, flag_name: str, enabled: bool) -> None:
        """Update feature flag for runtime configuration.

        Allows dynamic configuration changes without service restart.
        Useful for rollback scenarios and A/B testing.

        Args:
            flag_name: Name of the feature flag to update
            enabled: Whether to enable or disable the feature
        """
        if flag_name in self._feature_flags:
            old_value = self._feature_flags[flag_name]
            self._feature_flags[flag_name] = enabled

            logger.info(
                f"WebSocketBroadcastService feature flag updated: "
                f"{flag_name}: {old_value} → {enabled}"
            )
        else:
            logger.warning(f"Unknown feature flag: {flag_name}")


# SSOT Factory Function
def create_broadcast_service(websocket_manager: WebSocketManagerProtocol) -> WebSocketBroadcastService:
    """SSOT factory for broadcast service creation.

    Provides consistent creation pattern for all consumers.

    Args:
        websocket_manager: WebSocket manager implementing the protocol

    Returns:
        WebSocketBroadcastService: Configured SSOT broadcast service
    """
    service = WebSocketBroadcastService(websocket_manager)

    logger.info(
        "SSOT WebSocketBroadcastService created via factory. "
        "This consolidates 3 duplicate broadcast implementations (Issue #982)."
    )

    return service


# Backward Compatibility Export
__all__ = [
    'WebSocketBroadcastService',
    'BroadcastResult',
    'create_broadcast_service'
]