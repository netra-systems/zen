"""
WebSocket Authentication Monitoring - Enhanced Event Tracking

Business Value Justification (BVJ):
- Segment: Platform/Internal - Authentication Infrastructure
- Business Goal: Provide real-time monitoring and alerting for WebSocket authentication
- Value Impact: Prevent authentication failures that could disrupt $500K+ ARR chat functionality
- Revenue Impact: Ensure reliable authentication for all user interactions

This module implements comprehensive authentication event tracking for Issue #1300,
providing real-time monitoring of WebSocket authentication flows with detailed metrics
collection, alerting, and health monitoring.

Key Features:
1. Authentication event tracking (register, login, logout, failures, disconnections)
2. Real-time metrics collection for auth attempts, successes, failures
3. Token validation tracking and session management monitoring  
4. Connection upgrade monitoring and auth latency metrics
5. Integration with existing authentication monitoring infrastructure
6. Structured logging for all authentication events
7. Alert generation for authentication anomalies
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import defaultdict, deque
import threading

from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.monitoring.authentication_monitor_service import (
    get_authentication_monitor_service,
    AuthenticationStatus,
    record_auth_attempt
)
from netra_backend.app.websocket_core.websocket_metrics import (
    get_websocket_metrics_collector,
    record_websocket_event
)

logger = get_logger(__name__)

# Issue #1300: Import structured logging for auth events
try:
    from netra_backend.app.websocket_core.auth_structured_logger import (
        get_auth_structured_logger,
        log_auth_event,
        log_security_event,
        log_performance_event
    )
    _structured_logging_available = True
    logger.info("Issue #1300: Structured authentication logging imported successfully")
except ImportError as e:
    logger.warning(f"Issue #1300: Structured authentication logging not available: {e}")
    _structured_logging_available = False


class AuthEventType(Enum):
    """Types of authentication events to track."""
    # User lifecycle events
    REGISTER = "register"
    LOGIN = "login"
    LOGOUT = "logout"
    SESSION_REFRESH = "session_refresh"
    
    # Authentication flow events
    TOKEN_VALIDATION = "token_validation"
    JWT_DECODE = "jwt_decode"
    PERMISSION_CHECK = "permission_check"
    
    # Connection events
    CONNECTION_UPGRADE = "connection_upgrade"
    WEBSOCKET_HANDSHAKE = "websocket_handshake"
    CONNECTION_CLOSE = "connection_close"
    
    # Failure events
    AUTH_FAILURE = "auth_failure"
    TOKEN_EXPIRED = "token_expired"
    INVALID_TOKEN = "invalid_token"
    PERMISSION_DENIED = "permission_denied"
    CONNECTION_DROPPED = "connection_dropped"
    
    # Session management events
    SESSION_CREATE = "session_create"
    SESSION_INVALIDATE = "session_invalidate"
    SESSION_TIMEOUT = "session_timeout"


@dataclass
class AuthEvent:
    """Individual authentication event record."""
    event_type: AuthEventType
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    connection_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    latency_ms: float = 0.0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for logging/storage."""
        return {
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "connection_id": self.connection_id,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "latency_ms": self.latency_ms,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


@dataclass
class AuthMetrics:
    """Real-time authentication metrics."""
    # Core metrics
    auth_attempts: int = 0
    auth_successes: int = 0
    auth_failures: int = 0
    
    # Token metrics
    token_validations: int = 0
    token_validation_successes: int = 0
    token_validation_failures: int = 0
    
    # Session metrics
    session_creations: int = 0
    session_invalidations: int = 0
    session_timeouts: int = 0
    
    # Connection metrics
    connection_upgrades: int = 0
    connection_upgrade_successes: int = 0
    connection_upgrade_failures: int = 0
    
    # Latency tracking
    auth_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    # Event type counters
    event_counts: Dict[str, int] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)
    
    # Timing
    first_event_time: Optional[datetime] = None
    last_event_time: Optional[datetime] = None
    
    def record_event(self, event: AuthEvent):
        """Record an authentication event and update metrics."""
        now = datetime.now(timezone.utc)
        
        if not self.first_event_time:
            self.first_event_time = now
        self.last_event_time = now
        
        # Update event type counters
        event_type_str = event.event_type.value
        self.event_counts[event_type_str] = self.event_counts.get(event_type_str, 0) + 1
        
        # Update specific metrics based on event type
        if event.event_type in [AuthEventType.LOGIN, AuthEventType.REGISTER]:
            self.auth_attempts += 1
            if event.success:
                self.auth_successes += 1
                self.auth_latencies.append(event.latency_ms)
            else:
                self.auth_failures += 1
                if event.error_code:
                    self.error_counts[event.error_code] = self.error_counts.get(event.error_code, 0) + 1
        
        elif event.event_type == AuthEventType.TOKEN_VALIDATION:
            self.token_validations += 1
            if event.success:
                self.token_validation_successes += 1
            else:
                self.token_validation_failures += 1
                
        elif event.event_type == AuthEventType.SESSION_CREATE:
            self.session_creations += 1
            
        elif event.event_type == AuthEventType.SESSION_INVALIDATE:
            self.session_invalidations += 1
            
        elif event.event_type == AuthEventType.SESSION_TIMEOUT:
            self.session_timeouts += 1
            
        elif event.event_type == AuthEventType.CONNECTION_UPGRADE:
            self.connection_upgrades += 1
            if event.success:
                self.connection_upgrade_successes += 1
            else:
                self.connection_upgrade_failures += 1
    
    @property
    def auth_success_rate(self) -> float:
        """Calculate authentication success rate."""
        if self.auth_attempts == 0:
            return 100.0
        return (self.auth_successes / self.auth_attempts) * 100.0
    
    @property
    def token_validation_success_rate(self) -> float:
        """Calculate token validation success rate."""
        if self.token_validations == 0:
            return 100.0
        return (self.token_validation_successes / self.token_validations) * 100.0
    
    @property
    def connection_upgrade_success_rate(self) -> float:
        """Calculate connection upgrade success rate."""
        if self.connection_upgrades == 0:
            return 100.0
        return (self.connection_upgrade_successes / self.connection_upgrades) * 100.0
    
    def get_latency_percentiles(self) -> Dict[str, float]:
        """Calculate authentication latency percentiles."""
        if not self.auth_latencies:
            return {"p50": 0, "p90": 0, "p95": 0, "p99": 0}
        
        sorted_latencies = sorted(self.auth_latencies)
        n = len(sorted_latencies)
        
        return {
            "p50": sorted_latencies[int(n * 0.5)],
            "p90": sorted_latencies[int(n * 0.9)],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[int(n * 0.99)]
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "auth_attempts": self.auth_attempts,
            "auth_successes": self.auth_successes,
            "auth_failures": self.auth_failures,
            "auth_success_rate": round(self.auth_success_rate, 2),
            "token_validations": self.token_validations,
            "token_validation_successes": self.token_validation_successes,
            "token_validation_failures": self.token_validation_failures,
            "token_validation_success_rate": round(self.token_validation_success_rate, 2),
            "session_creations": self.session_creations,
            "session_invalidations": self.session_invalidations,
            "session_timeouts": self.session_timeouts,
            "connection_upgrades": self.connection_upgrades,
            "connection_upgrade_successes": self.connection_upgrade_successes,
            "connection_upgrade_failures": self.connection_upgrade_failures,
            "connection_upgrade_success_rate": round(self.connection_upgrade_success_rate, 2),
            "latency_percentiles": self.get_latency_percentiles(),
            "event_counts": dict(self.event_counts),
            "error_counts": dict(self.error_counts),
            "first_event_time": self.first_event_time.isoformat() if self.first_event_time else None,
            "last_event_time": self.last_event_time.isoformat() if self.last_event_time else None
        }


class WebSocketAuthMonitor:
    """
    WebSocket Authentication Monitor for Issue #1300.
    
    Provides comprehensive authentication event tracking, metrics collection,
    and real-time monitoring for WebSocket authentication flows.
    
    Integrates with existing authentication monitoring infrastructure while
    adding specific WebSocket authentication tracking capabilities.
    """
    
    def __init__(self):
        """Initialize the WebSocket authentication monitor."""
        self._lock = threading.RLock()
        
        # Per-user metrics tracking
        self._user_metrics: Dict[str, AuthMetrics] = {}
        self._global_metrics = AuthMetrics()
        
        # Event storage for recent events (last 1000 events)
        self._recent_events: deque = deque(maxlen=1000)
        
        # Active sessions tracking
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._active_connections: Dict[str, Dict[str, Any]] = {}
        
        # Alert thresholds
        self._alert_thresholds = {
            "auth_failure_rate": 20.0,  # Alert if >20% auth failures
            "token_failure_rate": 15.0,  # Alert if >15% token validation failures
            "connection_failure_rate": 25.0,  # Alert if >25% connection upgrade failures
            "high_latency_ms": 2000.0,  # Alert if latency >2 seconds
            "session_timeout_rate": 10.0  # Alert if >10% sessions timing out
        }
        
        # Integration with existing monitoring
        self._auth_monitor_service = get_authentication_monitor_service()
        self._websocket_metrics_collector = get_websocket_metrics_collector()
        
        # Health status
        self._monitor_start_time = datetime.now(timezone.utc)
        self._last_health_check = self._monitor_start_time
        self._health_status = "healthy"
        
        logger.info("WebSocketAuthMonitor initialized for Issue #1300 - authentication event tracking enabled")
    
    async def record_auth_event(
        self,
        event_type: AuthEventType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        success: bool = True,
        latency_ms: float = 0.0,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record an authentication event.
        
        Args:
            event_type: Type of authentication event
            user_id: Optional user ID
            session_id: Optional session ID  
            connection_id: Optional connection ID
            success: Whether the event was successful
            latency_ms: Event latency in milliseconds
            error_code: Optional error code for failures
            error_message: Optional error message for failures
            metadata: Optional additional metadata
        """
        try:
            # Create event record
            event = AuthEvent(
                event_type=event_type,
                user_id=user_id,
                session_id=session_id,
                connection_id=connection_id,
                success=success,
                latency_ms=latency_ms,
                error_code=error_code,
                error_message=error_message,
                metadata=metadata or {}
            )
            
            with self._lock:
                # Store recent event
                self._recent_events.append(event)
                
                # Update global metrics
                self._global_metrics.record_event(event)
                
                # Update per-user metrics if user_id provided
                if user_id:
                    if user_id not in self._user_metrics:
                        self._user_metrics[user_id] = AuthMetrics()
                    self._user_metrics[user_id].record_event(event)
            
            # Structured logging for the event
            await self._log_auth_event(event)
            
            # Integrate with existing monitoring systems
            await self._integrate_with_existing_monitoring(event)
            
            # Check for alerts
            await self._check_alerts(event)
            
            logger.debug(f"Recorded auth event: {event_type.value} for user {user_id[:8] if user_id else 'unknown'}... (success: {success})")
            
        except Exception as e:
            logger.error(f"Error recording auth event {event_type.value}: {e}")
    
    async def track_login_attempt(
        self,
        user_id: str,
        success: bool,
        latency_ms: float,
        connection_id: Optional[str] = None,
        error_details: Optional[str] = None
    ) -> None:
        """Track a login attempt."""
        await self.record_auth_event(
            event_type=AuthEventType.LOGIN,
            user_id=user_id,
            connection_id=connection_id,
            success=success,
            latency_ms=latency_ms,
            error_code="LOGIN_FAILED" if not success else None,
            error_message=error_details if not success else None,
            metadata={"auth_method": "websocket"}
        )
    
    async def track_logout(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> None:
        """Track a logout event."""
        await self.record_auth_event(
            event_type=AuthEventType.LOGOUT,
            user_id=user_id,
            session_id=session_id,
            connection_id=connection_id,
            success=True,
            metadata={"logout_reason": reason or "user_initiated"}
        )
    
    async def track_token_validation(
        self,
        user_id: Optional[str],
        success: bool,
        latency_ms: float,
        token_type: str = "jwt",
        error_details: Optional[str] = None
    ) -> None:
        """Track a token validation attempt."""
        await self.record_auth_event(
            event_type=AuthEventType.TOKEN_VALIDATION,
            user_id=user_id,
            success=success,
            latency_ms=latency_ms,
            error_code="TOKEN_VALIDATION_FAILED" if not success else None,
            error_message=error_details if not success else None,
            metadata={"token_type": token_type}
        )
    
    async def track_session_creation(
        self,
        user_id: str,
        session_id: str,
        connection_id: Optional[str] = None
    ) -> None:
        """Track session creation."""
        with self._lock:
            self._active_sessions[session_id] = {
                "user_id": user_id,
                "connection_id": connection_id,
                "created_at": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc)
            }
        
        await self.record_auth_event(
            event_type=AuthEventType.SESSION_CREATE,
            user_id=user_id,
            session_id=session_id,
            connection_id=connection_id,
            success=True,
            metadata={"session_type": "websocket"}
        )
    
    async def track_session_invalidation(
        self,
        user_id: str,
        session_id: str,
        reason: str = "logout"
    ) -> None:
        """Track session invalidation."""
        with self._lock:
            self._active_sessions.pop(session_id, None)
        
        await self.record_auth_event(
            event_type=AuthEventType.SESSION_INVALIDATE,
            user_id=user_id,
            session_id=session_id,
            success=True,
            metadata={"invalidation_reason": reason}
        )
    
    async def track_connection_upgrade(
        self,
        user_id: str,
        connection_id: str,
        success: bool,
        latency_ms: float,
        error_details: Optional[str] = None
    ) -> None:
        """Track WebSocket connection upgrade."""
        if success:
            with self._lock:
                self._active_connections[connection_id] = {
                    "user_id": user_id,
                    "connected_at": datetime.now(timezone.utc),
                    "last_activity": datetime.now(timezone.utc)
                }
        
        await self.record_auth_event(
            event_type=AuthEventType.CONNECTION_UPGRADE,
            user_id=user_id,
            connection_id=connection_id,
            success=success,
            latency_ms=latency_ms,
            error_code="CONNECTION_UPGRADE_FAILED" if not success else None,
            error_message=error_details if not success else None,
            metadata={"protocol": "websocket"}
        )
    
    async def track_connection_close(
        self,
        user_id: str,
        connection_id: str,
        reason: str = "client_disconnect"
    ) -> None:
        """Track connection closure."""
        # Calculate connection duration if we have the connection record
        duration_seconds = 0.0
        with self._lock:
            if connection_id in self._active_connections:
                conn_info = self._active_connections.pop(connection_id)
                duration_seconds = (datetime.now(timezone.utc) - conn_info["connected_at"]).total_seconds()
        
        await self.record_auth_event(
            event_type=AuthEventType.CONNECTION_CLOSE,
            user_id=user_id,
            connection_id=connection_id,
            success=True,
            metadata={
                "close_reason": reason,
                "duration_seconds": duration_seconds
            }
        )
    
    def get_metrics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get authentication metrics."""
        with self._lock:
            if user_id:
                # Return metrics for specific user
                user_metrics = self._user_metrics.get(user_id, AuthMetrics())
                return {
                    "user_id": user_id,
                    "metrics": user_metrics.to_dict(),
                    "active_sessions": [
                        session_id for session_id, info in self._active_sessions.items()
                        if info["user_id"] == user_id
                    ],
                    "active_connections": [
                        conn_id for conn_id, info in self._active_connections.items()
                        if info["user_id"] == user_id
                    ]
                }
            else:
                # Return global metrics
                return {
                    "global_metrics": self._global_metrics.to_dict(),
                    "total_users_tracked": len(self._user_metrics),
                    "active_sessions_count": len(self._active_sessions),
                    "active_connections_count": len(self._active_connections),
                    "monitor_uptime_seconds": (datetime.now(timezone.utc) - self._monitor_start_time).total_seconds(),
                    "recent_events_count": len(self._recent_events)
                }
    
    def get_recent_events(self, limit: int = 50, event_type: Optional[AuthEventType] = None) -> List[Dict[str, Any]]:
        """Get recent authentication events."""
        with self._lock:
            events = list(self._recent_events)
            
            # Filter by event type if specified
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            # Return most recent events (reverse chronological order)
            events.reverse()
            return [event.to_dict() for event in events[:limit]]
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get authentication monitoring health status."""
        with self._lock:
            current_time = datetime.now(timezone.utc)
            uptime_seconds = (current_time - self._monitor_start_time).total_seconds()
            
            # Calculate health indicators
            global_auth_failure_rate = 100.0 - self._global_metrics.auth_success_rate
            token_failure_rate = 100.0 - self._global_metrics.token_validation_success_rate
            connection_failure_rate = 100.0 - self._global_metrics.connection_upgrade_success_rate
            
            # Determine overall health status
            health_issues = []
            if global_auth_failure_rate > self._alert_thresholds["auth_failure_rate"]:
                health_issues.append(f"High auth failure rate: {global_auth_failure_rate:.1f}%")
            if token_failure_rate > self._alert_thresholds["token_failure_rate"]:
                health_issues.append(f"High token failure rate: {token_failure_rate:.1f}%")
            if connection_failure_rate > self._alert_thresholds["connection_failure_rate"]:
                health_issues.append(f"High connection failure rate: {connection_failure_rate:.1f}%")
            
            overall_status = "critical" if len(health_issues) >= 2 else "degraded" if health_issues else "healthy"
            
            self._last_health_check = current_time
            self._health_status = overall_status
            
            return {
                "overall_status": overall_status,
                "uptime_seconds": uptime_seconds,
                "last_health_check": current_time.isoformat(),
                "health_issues": health_issues,
                "metrics_summary": {
                    "auth_attempts": self._global_metrics.auth_attempts,
                    "auth_success_rate": self._global_metrics.auth_success_rate,
                    "token_validations": self._global_metrics.token_validations,
                    "token_validation_success_rate": self._global_metrics.token_validation_success_rate,
                    "connection_upgrades": self._global_metrics.connection_upgrades,
                    "connection_upgrade_success_rate": self._global_metrics.connection_upgrade_success_rate,
                    "active_sessions": len(self._active_sessions),
                    "active_connections": len(self._active_connections)
                },
                "integration_status": {
                    "auth_monitor_service": self._auth_monitor_service is not None,
                    "websocket_metrics_collector": self._websocket_metrics_collector is not None
                }
            }
    
    async def _log_auth_event(self, event: AuthEvent) -> None:
        """Log authentication event with structured logging."""
        try:
            # Issue #1300: Use structured logging if available
            if _structured_logging_available:
                try:
                    log_auth_event(
                        event_type=event.event_type,
                        success=event.success,
                        user_id=event.user_id,
                        connection_id=event.connection_id,
                        latency_ms=event.latency_ms,
                        error_code=event.error_code,
                        error_details=event.error_message,
                        session_id=event.session_id,
                        metadata=event.metadata,
                        component="WebSocketAuthMonitor",
                        issue="#1300"
                    )
                    return
                except Exception as e:
                    logger.warning(f"Issue #1300: Failed to use structured logging, falling back: {e}")
            
            # Fallback to traditional logging
            log_data = {
                "event_type": "websocket_auth_event",
                "auth_event": event.to_dict(),
                "component": "WebSocketAuthMonitor",
                "issue": "#1300"
            }
            
            if event.success:
                logger.info(f"AUTH EVENT: {event.event_type.value} - SUCCESS", extra=log_data)
            else:
                logger.warning(f"AUTH EVENT: {event.event_type.value} - FAILURE: {event.error_message}", extra=log_data)
                
        except Exception as e:
            logger.error(f"Error logging auth event: {e}")
    
    async def _integrate_with_existing_monitoring(self, event: AuthEvent) -> None:
        """Integrate with existing authentication monitoring systems."""
        try:
            # Integration with AuthenticationMonitorService
            if self._auth_monitor_service and event.event_type in [AuthEventType.LOGIN, AuthEventType.TOKEN_VALIDATION]:
                await record_auth_attempt(
                    success=event.success,
                    response_time_ms=event.latency_ms,
                    user_id=event.user_id,
                    error_details=event.error_message
                )
            
            # Integration with WebSocket metrics collector  
            if self._websocket_metrics_collector and event.user_id:
                record_websocket_event(
                    user_id=event.user_id,
                    event_type=f"auth_{event.event_type.value}",
                    latency_ms=event.latency_ms,
                    success=event.success
                )
                
        except Exception as e:
            logger.error(f"Error integrating with existing monitoring: {e}")
    
    async def _check_alerts(self, event: AuthEvent) -> None:
        """Check for alert conditions based on the event."""
        try:
            # High latency alert
            if event.latency_ms > self._alert_thresholds["high_latency_ms"]:
                logger.warning(f"HIGH LATENCY ALERT: {event.event_type.value} took {event.latency_ms:.1f}ms for user {event.user_id}")
                
                # Issue #1300: Log performance event for high latency
                if _structured_logging_available:
                    try:
                        log_performance_event(
                            operation=f"auth_{event.event_type.value}",
                            duration_ms=event.latency_ms,
                            user_id=event.user_id,
                            connection_id=event.connection_id,
                            performance_details={
                                "threshold_ms": self._alert_thresholds["high_latency_ms"],
                                "exceeded_by_ms": event.latency_ms - self._alert_thresholds["high_latency_ms"],
                                "event_type": event.event_type.value
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Issue #1300: Failed to log performance event: {e}")
            
            # Authentication failure pattern alerts
            if not event.success and event.event_type in [AuthEventType.LOGIN, AuthEventType.TOKEN_VALIDATION]:
                # Check for consecutive failures for this user
                if event.user_id and event.user_id in self._user_metrics:
                    user_metrics = self._user_metrics[event.user_id]
                    if user_metrics.auth_attempts > 3 and user_metrics.auth_success_rate < 50.0:
                        alert_msg = f"User {event.user_id} has {user_metrics.auth_success_rate:.1f}% success rate over {user_metrics.auth_attempts} attempts"
                        logger.critical(f"AUTH FAILURE PATTERN ALERT: {alert_msg}")
                        
                        # Issue #1300: Log security event for failure patterns
                        if _structured_logging_available:
                            try:
                                log_security_event(
                                    event_description=f"Authentication failure pattern detected: {alert_msg}",
                                    severity="critical",
                                    user_id=event.user_id,
                                    connection_id=event.connection_id,
                                    security_details={
                                        "pattern_type": "repeated_failures",
                                        "failure_count": user_metrics.auth_failures,
                                        "attempt_count": user_metrics.auth_attempts,
                                        "success_rate": user_metrics.auth_success_rate
                                    }
                                )
                            except Exception as e:
                                logger.warning(f"Issue #1300: Failed to log security event: {e}")
            
            # Session timeout alerts
            if event.event_type == AuthEventType.SESSION_TIMEOUT:
                session_timeout_rate = (self._global_metrics.session_timeouts / max(1, self._global_metrics.session_creations)) * 100
                if session_timeout_rate > self._alert_thresholds["session_timeout_rate"]:
                    logger.warning(f"SESSION TIMEOUT ALERT: {session_timeout_rate:.1f}% of sessions are timing out")
                    
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")


# Global instance for WebSocket authentication monitoring
_websocket_auth_monitor: Optional[WebSocketAuthMonitor] = None
_monitor_lock = threading.Lock()


def get_websocket_auth_monitor() -> WebSocketAuthMonitor:
    """Get or create the global WebSocket authentication monitor."""
    global _websocket_auth_monitor
    
    if _websocket_auth_monitor is None:
        with _monitor_lock:
            if _websocket_auth_monitor is None:
                _websocket_auth_monitor = WebSocketAuthMonitor()
                logger.info("Created global WebSocketAuthMonitor for Issue #1300")
    
    return _websocket_auth_monitor


# Convenience functions for authentication event tracking

async def track_auth_attempt(
    user_id: str,
    success: bool,
    latency_ms: float,
    connection_id: Optional[str] = None,
    error_details: Optional[str] = None
) -> None:
    """Track an authentication attempt."""
    monitor = get_websocket_auth_monitor()
    await monitor.track_login_attempt(user_id, success, latency_ms, connection_id, error_details)


async def track_token_validation(
    user_id: Optional[str],
    success: bool,
    latency_ms: float,
    error_details: Optional[str] = None
) -> None:
    """Track a token validation."""
    monitor = get_websocket_auth_monitor()
    await monitor.track_token_validation(user_id, success, latency_ms, "jwt", error_details)


async def track_session_event(
    event_type: str,
    user_id: str,
    session_id: str,
    connection_id: Optional[str] = None,
    **kwargs
) -> None:
    """Track a session-related event."""
    monitor = get_websocket_auth_monitor()
    
    if event_type == "create":
        await monitor.track_session_creation(user_id, session_id, connection_id)
    elif event_type == "invalidate":
        reason = kwargs.get("reason", "logout")
        await monitor.track_session_invalidation(user_id, session_id, reason)


async def track_connection_event(
    event_type: str,
    user_id: str,
    connection_id: str,
    success: bool = True,
    latency_ms: float = 0.0,
    **kwargs
) -> None:
    """Track a connection-related event."""
    monitor = get_websocket_auth_monitor()
    
    if event_type == "upgrade":
        error_details = kwargs.get("error_details")
        await monitor.track_connection_upgrade(user_id, connection_id, success, latency_ms, error_details)
    elif event_type == "close":
        reason = kwargs.get("reason", "client_disconnect")
        await monitor.track_connection_close(user_id, connection_id, reason)


def get_auth_monitoring_metrics(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get authentication monitoring metrics."""
    monitor = get_websocket_auth_monitor()
    return monitor.get_metrics(user_id)


def get_recent_auth_events(limit: int = 50, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get recent authentication events."""
    monitor = get_websocket_auth_monitor()
    auth_event_type = None
    if event_type:
        try:
            auth_event_type = AuthEventType(event_type)
        except ValueError:
            logger.warning(f"Invalid event type: {event_type}")
    
    return monitor.get_recent_events(limit, auth_event_type)


async def get_auth_monitoring_health() -> Dict[str, Any]:
    """Get authentication monitoring health status."""
    monitor = get_websocket_auth_monitor()
    return await monitor.get_health_status()


# Export public interface
__all__ = [
    "WebSocketAuthMonitor",
    "AuthEventType", 
    "AuthEvent",
    "AuthMetrics",
    "get_websocket_auth_monitor",
    "track_auth_attempt",
    "track_token_validation", 
    "track_session_event",
    "track_connection_event",
    "get_auth_monitoring_metrics",
    "get_recent_auth_events",
    "get_auth_monitoring_health"
]