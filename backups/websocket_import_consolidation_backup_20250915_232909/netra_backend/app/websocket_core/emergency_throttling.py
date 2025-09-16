"""WebSocket Emergency Throttling Module - P0 VPC Connector Capacity Remediation

This module provides WebSocket connection throttling and circuit breaker patterns
to reduce VPC connector load during capacity exhaustion emergencies.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure (ALL users impacted during emergency)
- Business Goal: Maintain WebSocket service availability during VPC emergencies
- Value Impact: Prevents complete WebSocket service outage during infrastructure emergencies
- Strategic Impact: Protects Golden Path chat functionality ($500K+ ARR)

P0 EMERGENCY CONTEXT:
- VPC connector capacity exhaustion in staging environment
- WebSocket connections contributing to VPC load
- Need connection throttling without service restart
- Circuit breaker patterns for overload protection

REMEDIATION APPROACH:
1. Connection counting and throttling per user and globally
2. Circuit breaker for overload protection
3. Graceful connection rejection with informative messages
4. Emergency mode configuration integration
5. Connection cleanup and monitoring
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import weakref

logger = logging.getLogger(__name__)


class ThrottleReason(Enum):
    """Reasons for connection throttling."""
    EMERGENCY_MODE = "emergency_mode"
    USER_LIMIT_EXCEEDED = "user_limit_exceeded"
    GLOBAL_LIMIT_EXCEEDED = "global_limit_exceeded"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    RATE_LIMITED = "rate_limited"


@dataclass
class ConnectionMetrics:
    """Metrics for connection monitoring."""
    total_connections: int = 0
    connections_per_user: Dict[str, int] = field(default_factory=dict)
    rejected_connections: int = 0
    rejected_by_reason: Dict[str, int] = field(default_factory=dict)
    circuit_breaker_trips: int = 0
    last_connection_attempt: Optional[datetime] = None
    last_rejection: Optional[datetime] = None


@dataclass
class ThrottleResult:
    """Result of connection throttle check."""
    allowed: bool
    reason: Optional[ThrottleReason] = None
    message: str = ""
    retry_after_seconds: Optional[int] = None
    current_user_connections: int = 0
    current_total_connections: int = 0
    max_user_connections: int = 0
    max_total_connections: int = 0


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Rejecting all connections
    HALF_OPEN = "half_open" # Testing limited connections


class WebSocketCircuitBreaker:
    """Circuit breaker for WebSocket connections during overload."""

    def __init__(self, failure_threshold: int = 10, recovery_timeout: int = 60):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitBreakerState.CLOSED
        self._lock = asyncio.Lock()

    async def record_success(self):
        """Record a successful connection."""
        async with self._lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("🔄 WebSocket circuit breaker CLOSED - Service recovered")

    async def record_failure(self):
        """Record a connection failure."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.state == CircuitBreakerState.CLOSED and self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.critical(f"⚡ WebSocket circuit breaker OPENED - {self.failure_count} failures detected")

    async def can_attempt_connection(self) -> bool:
        """Check if connections are allowed based on circuit breaker state."""
        async with self._lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            elif self.state == CircuitBreakerState.OPEN:
                if self.last_failure_time and (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info("🔄 WebSocket circuit breaker HALF-OPEN - Testing recovery")
                    return True
                return False
            elif self.state == CircuitBreakerState.HALF_OPEN:
                return True
            return False

    def get_state_info(self) -> Dict[str, Any]:
        """Get circuit breaker state information."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "recovery_timeout": self.recovery_timeout
        }


class WebSocketEmergencyThrottler:
    """Emergency throttling manager for WebSocket connections."""

    def __init__(self):
        """Initialize emergency throttler."""
        self.metrics = ConnectionMetrics()
        self.circuit_breaker = WebSocketCircuitBreaker()
        self.active_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
        self.connection_timestamps: Dict[str, datetime] = {}  # connection_id -> connection_time
        self._lock = asyncio.Lock()

        # Rate limiting for connection attempts
        self.rate_limit_window = 60  # seconds
        self.max_attempts_per_window = 10
        self.user_attempt_history: Dict[str, list] = {}  # user_id -> list of attempt timestamps

        logger.info("🛡️ WebSocket emergency throttler initialized")

    async def check_connection_allowed(self, user_id: str, connection_id: str) -> ThrottleResult:
        """Check if a new WebSocket connection should be allowed.

        Args:
            user_id: User attempting to connect
            connection_id: Unique connection identifier

        Returns:
            ThrottleResult: Whether connection is allowed and relevant metrics
        """
        async with self._lock:
            # Get emergency configuration
            from netra_backend.app.core.configuration.emergency import get_emergency_config
            emergency_config = get_emergency_config()

            # Update metrics
            self.metrics.last_connection_attempt = datetime.now()

            # Check circuit breaker first
            if not await self.circuit_breaker.can_attempt_connection():
                self.metrics.rejected_connections += 1
                self.metrics.rejected_by_reason["circuit_breaker"] = self.metrics.rejected_by_reason.get("circuit_breaker", 0) + 1
                return ThrottleResult(
                    allowed=False,
                    reason=ThrottleReason.CIRCUIT_BREAKER_OPEN,
                    message="WebSocket service temporarily unavailable due to overload. Please try again later.",
                    retry_after_seconds=30,
                    current_user_connections=len(self.active_connections.get(user_id, set())),
                    current_total_connections=self.metrics.total_connections
                )

            # Check rate limiting
            if not self._check_rate_limit(user_id):
                self.metrics.rejected_connections += 1
                self.metrics.rejected_by_reason["rate_limited"] = self.metrics.rejected_by_reason.get("rate_limited", 0) + 1
                return ThrottleResult(
                    allowed=False,
                    reason=ThrottleReason.RATE_LIMITED,
                    message="Too many connection attempts. Please wait before trying again.",
                    retry_after_seconds=self.rate_limit_window,
                    current_user_connections=len(self.active_connections.get(user_id, set())),
                    current_total_connections=self.metrics.total_connections
                )

            # Get current limits based on emergency mode
            if emergency_config.is_emergency_mode():
                ws_config = emergency_config.get_websocket_config()
                max_per_user = ws_config['max_connections_per_user']
                max_total = ws_config['max_total_connections']
            else:
                # Default limits for normal operation
                max_per_user = 10
                max_total = 1000

            current_user_connections = len(self.active_connections.get(user_id, set()))
            current_total_connections = self.metrics.total_connections

            # Check user-specific limit
            if current_user_connections >= max_per_user:
                self.metrics.rejected_connections += 1
                self.metrics.rejected_by_reason["user_limit"] = self.metrics.rejected_by_reason.get("user_limit", 0) + 1
                return ThrottleResult(
                    allowed=False,
                    reason=ThrottleReason.USER_LIMIT_EXCEEDED,
                    message=f"Maximum connections per user exceeded ({max_per_user}). Close existing connections to create new ones.",
                    retry_after_seconds=None,
                    current_user_connections=current_user_connections,
                    current_total_connections=current_total_connections,
                    max_user_connections=max_per_user,
                    max_total_connections=max_total
                )

            # Check global limit
            if current_total_connections >= max_total:
                self.metrics.rejected_connections += 1
                self.metrics.rejected_by_reason["global_limit"] = self.metrics.rejected_by_reason.get("global_limit", 0) + 1
                return ThrottleResult(
                    allowed=False,
                    reason=ThrottleReason.GLOBAL_LIMIT_EXCEEDED,
                    message=f"Server connection limit reached ({max_total}). Please try again later.",
                    retry_after_seconds=60,
                    current_user_connections=current_user_connections,
                    current_total_connections=current_total_connections,
                    max_user_connections=max_per_user,
                    max_total_connections=max_total
                )

            # Connection allowed
            return ThrottleResult(
                allowed=True,
                current_user_connections=current_user_connections,
                current_total_connections=current_total_connections,
                max_user_connections=max_per_user,
                max_total_connections=max_total
            )

    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limit for connection attempts."""
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.rate_limit_window)

        # Initialize user history if needed
        if user_id not in self.user_attempt_history:
            self.user_attempt_history[user_id] = []

        # Clean old attempts
        self.user_attempt_history[user_id] = [
            attempt_time for attempt_time in self.user_attempt_history[user_id]
            if attempt_time > cutoff_time
        ]

        # Add current attempt
        self.user_attempt_history[user_id].append(now)

        # Check if within limit
        return len(self.user_attempt_history[user_id]) <= self.max_attempts_per_window

    async def register_connection(self, user_id: str, connection_id: str):
        """Register a new WebSocket connection.

        Args:
            user_id: User who owns the connection
            connection_id: Unique connection identifier
        """
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()

            self.active_connections[user_id].add(connection_id)
            self.connection_timestamps[connection_id] = datetime.now()
            self.metrics.total_connections += 1
            self.metrics.connections_per_user[user_id] = len(self.active_connections[user_id])

            await self.circuit_breaker.record_success()

            logger.debug(f"🔌 Registered WebSocket connection {connection_id} for user {user_id} "
                        f"(user: {len(self.active_connections[user_id])}, total: {self.metrics.total_connections})")

    async def unregister_connection(self, user_id: str, connection_id: str):
        """Unregister a WebSocket connection.

        Args:
            user_id: User who owns the connection
            connection_id: Unique connection identifier
        """
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(connection_id)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    if user_id in self.metrics.connections_per_user:
                        del self.metrics.connections_per_user[user_id]
                else:
                    self.metrics.connections_per_user[user_id] = len(self.active_connections[user_id])

            if connection_id in self.connection_timestamps:
                connection_duration = datetime.now() - self.connection_timestamps[connection_id]
                del self.connection_timestamps[connection_id]
                logger.debug(f"🔌 Connection {connection_id} was active for {connection_duration.total_seconds():.1f}s")

            self.metrics.total_connections = max(0, self.metrics.total_connections - 1)

            logger.debug(f"📤 Unregistered WebSocket connection {connection_id} for user {user_id} "
                        f"(remaining total: {self.metrics.total_connections})")

    async def record_connection_failure(self, user_id: str, connection_id: str, error: Exception):
        """Record a connection failure for circuit breaker tracking.

        Args:
            user_id: User who attempted to connect
            connection_id: Connection identifier that failed
            error: Exception that caused the failure
        """
        await self.circuit_breaker.record_failure()
        logger.warning(f"⚠️ WebSocket connection failure for user {user_id}: {type(error).__name__}: {error}")

    async def cleanup_stale_connections(self, max_age_seconds: int = 3600):
        """Clean up connections that have been active too long.

        Args:
            max_age_seconds: Maximum age for connections before cleanup
        """
        async with self._lock:
            now = datetime.now()
            stale_connections = []

            for connection_id, timestamp in self.connection_timestamps.items():
                if (now - timestamp).total_seconds() > max_age_seconds:
                    stale_connections.append(connection_id)

            if stale_connections:
                logger.info(f"🧹 Cleaning up {len(stale_connections)} stale WebSocket connections")

                for connection_id in stale_connections:
                    # Find the user for this connection
                    user_id = None
                    for uid, conn_set in self.active_connections.items():
                        if connection_id in conn_set:
                            user_id = uid
                            break

                    if user_id:
                        await self.unregister_connection(user_id, connection_id)

    def get_throttling_metrics(self) -> Dict[str, Any]:
        """Get current throttling metrics."""
        # Get emergency configuration status
        from netra_backend.app.core.configuration.emergency import get_emergency_config
        emergency_config = get_emergency_config()

        return {
            "emergency_mode": emergency_config.is_emergency_mode(),
            "emergency_level": emergency_config.get_current_level().value if emergency_config.is_emergency_mode() else "normal",
            "circuit_breaker": self.circuit_breaker.get_state_info(),
            "connections": {
                "total": self.metrics.total_connections,
                "per_user": dict(self.metrics.connections_per_user),
                "rejected_total": self.metrics.rejected_connections,
                "rejected_by_reason": dict(self.metrics.rejected_by_reason)
            },
            "limits": emergency_config.get_websocket_config() if emergency_config.is_emergency_mode() else {
                "max_connections_per_user": 10,
                "max_total_connections": 1000
            },
            "rate_limiting": {
                "window_seconds": self.rate_limit_window,
                "max_attempts_per_window": self.max_attempts_per_window,
                "active_users_with_attempts": len(self.user_attempt_history)
            }
        }

    def get_user_connection_info(self, user_id: str) -> Dict[str, Any]:
        """Get connection information for a specific user."""
        user_connections = self.active_connections.get(user_id, set())
        recent_attempts = self.user_attempt_history.get(user_id, [])

        return {
            "user_id": user_id,
            "active_connections": len(user_connections),
            "connection_ids": list(user_connections),
            "recent_attempts": len(recent_attempts),
            "last_attempt": max(recent_attempts).isoformat() if recent_attempts else None
        }


# Global throttler instance
_throttler: Optional[WebSocketEmergencyThrottler] = None


def get_websocket_throttler() -> WebSocketEmergencyThrottler:
    """Get the global WebSocket emergency throttler instance."""
    global _throttler
    if _throttler is None:
        _throttler = WebSocketEmergencyThrottler()
    return _throttler


async def check_connection_throttle(user_id: str, connection_id: str) -> ThrottleResult:
    """Check if a WebSocket connection should be throttled."""
    return await get_websocket_throttler().check_connection_allowed(user_id, connection_id)


async def register_websocket_connection(user_id: str, connection_id: str):
    """Register a new WebSocket connection."""
    await get_websocket_throttler().register_connection(user_id, connection_id)


async def unregister_websocket_connection(user_id: str, connection_id: str):
    """Unregister a WebSocket connection."""
    await get_websocket_throttler().unregister_connection(user_id, connection_id)


async def record_websocket_failure(user_id: str, connection_id: str, error: Exception):
    """Record a WebSocket connection failure."""
    await get_websocket_throttler().record_connection_failure(user_id, connection_id, error)


def get_websocket_throttling_metrics() -> Dict[str, Any]:
    """Get WebSocket throttling metrics."""
    return get_websocket_throttler().get_throttling_metrics()


# Export public interface
__all__ = [
    'ThrottleReason',
    'ThrottleResult',
    'WebSocketEmergencyThrottler',
    'get_websocket_throttler',
    'check_connection_throttle',
    'register_websocket_connection',
    'unregister_websocket_connection',
    'record_websocket_failure',
    'get_websocket_throttling_metrics'
]