"""
WebSocket Notification Monitoring System - CRITICAL SILENT FAILURE DETECTION

This module implements comprehensive monitoring to detect and alert on silent WebSocket 
notification failures that could leave users without critical updates.

BUSINESS IMPACT:
- Prevents lost user notifications that break chat transparency
- Ensures real-time progress updates reach all users
- Provides early warning of system degradation
- Enables proactive remediation of WebSocket issues

MONITORING OBJECTIVES:
1. Detect silent failures (no errors but no delivery)
2. Track notification delivery success/failure rates  
3. Monitor WebSocket bridge initialization status
4. Alert on degraded user experience before users notice
5. Provide detailed diagnostics for remediation

CRITICAL METRICS:
- Bridge initialization failures (target: 0%)
- Notification success rate (target: >95%)
- Silent failures detected (target: 0)
- User-specific delivery rates (per-user isolation)
- Connection stability and recovery patterns
"""

import asyncio
import json
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set, Deque
from contextlib import asynccontextmanager

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.alert_notifications import NotificationDeliveryManager
from netra_backend.app.monitoring.alert_types import Alert, AlertLevel, NotificationChannel

logger = central_logger.get_logger(__name__)


class NotificationEventType(Enum):
    """Types of notification events to monitor."""
    BRIDGE_INITIALIZATION_STARTED = "bridge_initialization_started"
    BRIDGE_INITIALIZATION_SUCCESS = "bridge_initialization_success" 
    BRIDGE_INITIALIZATION_FAILED = "bridge_initialization_failed"
    NOTIFICATION_ATTEMPTED = "notification_attempted"
    NOTIFICATION_DELIVERED = "notification_delivered"
    NOTIFICATION_FAILED = "notification_failed"
    SILENT_FAILURE_DETECTED = "silent_failure_detected"
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"
    USER_ISOLATION_VIOLATION = "user_isolation_violation"
    MEMORY_LEAK_DETECTED = "memory_leak_detected"
    PERFORMANCE_DEGRADATION = "performance_degradation"


class HealthStatus(Enum):
    """Health status levels for monitoring."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class NotificationEvent:
    """Individual notification event for tracking."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: NotificationEventType = NotificationEventType.NOTIFICATION_ATTEMPTED
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = "unknown"
    thread_id: str = "unknown"
    run_id: str = "unknown"
    agent_name: str = "unknown"
    tool_name: Optional[str] = None
    connection_id: Optional[str] = None
    
    # Execution context
    duration_ms: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "run_id": self.run_id,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "connection_id": self.connection_id,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "metadata": self.metadata,
            "correlation_id": self.correlation_id
        }


@dataclass
class UserNotificationMetrics:
    """Per-user notification metrics for isolation tracking."""
    user_id: str
    thread_id: str
    connection_id: Optional[str] = None
    
    # Success/failure tracking
    notifications_attempted: int = 0
    notifications_delivered: int = 0
    notifications_failed: int = 0
    silent_failures: int = 0
    
    # Timing metrics
    total_delivery_time_ms: float = 0.0
    min_delivery_time_ms: Optional[float] = None
    max_delivery_time_ms: Optional[float] = None
    avg_delivery_time_ms: float = 0.0
    
    # Connection health
    last_successful_notification: Optional[datetime] = None
    last_failed_notification: Optional[datetime] = None
    connection_drops: int = 0
    reconnection_attempts: int = 0
    
    # Recent event history (sliding window)
    recent_events: Deque[NotificationEvent] = field(default_factory=lambda: deque(maxlen=50))
    
    # Alert tracking
    last_alert_sent: Optional[datetime] = None
    consecutive_failures: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate notification success rate."""
        if self.notifications_attempted == 0:
            return 1.0
        return self.notifications_delivered / self.notifications_attempted
    
    @property
    def failure_rate(self) -> float:
        """Calculate notification failure rate."""
        return 1.0 - self.success_rate
    
    @property
    def silent_failure_rate(self) -> float:
        """Calculate silent failure rate."""
        if self.notifications_attempted == 0:
            return 0.0
        return self.silent_failures / self.notifications_attempted
    
    @property
    def is_healthy(self) -> bool:
        """Check if user metrics indicate healthy notifications."""
        return (
            self.success_rate >= 0.95 and 
            self.silent_failures == 0 and
            self.consecutive_failures < 3
        )
    
    @property
    def health_status(self) -> HealthStatus:
        """Get health status based on metrics."""
        if self.silent_failures > 0 or self.consecutive_failures >= 5:
            return HealthStatus.CRITICAL
        elif self.success_rate < 0.80 or self.consecutive_failures >= 3:
            return HealthStatus.UNHEALTHY
        elif self.success_rate < 0.95 or self.consecutive_failures >= 1:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def update_delivery_time(self, delivery_time_ms: float) -> None:
        """Update delivery time metrics."""
        self.total_delivery_time_ms += delivery_time_ms
        
        if self.min_delivery_time_ms is None or delivery_time_ms < self.min_delivery_time_ms:
            self.min_delivery_time_ms = delivery_time_ms
            
        if self.max_delivery_time_ms is None or delivery_time_ms > self.max_delivery_time_ms:
            self.max_delivery_time_ms = delivery_time_ms
        
        if self.notifications_delivered > 0:
            self.avg_delivery_time_ms = self.total_delivery_time_ms / self.notifications_delivered
    
    def add_event(self, event: NotificationEvent) -> None:
        """Add event to recent history."""
        self.recent_events.append(event)
        
        # Update metrics based on event type
        if event.event_type == NotificationEventType.NOTIFICATION_ATTEMPTED:
            self.notifications_attempted += 1
        elif event.event_type == NotificationEventType.NOTIFICATION_DELIVERED:
            self.notifications_delivered += 1
            self.consecutive_failures = 0
            self.last_successful_notification = event.timestamp
            if event.duration_ms:
                self.update_delivery_time(event.duration_ms)
        elif event.event_type == NotificationEventType.NOTIFICATION_FAILED:
            self.notifications_failed += 1
            self.consecutive_failures += 1
            self.last_failed_notification = event.timestamp
        elif event.event_type == NotificationEventType.SILENT_FAILURE_DETECTED:
            self.silent_failures += 1
            self.consecutive_failures += 1
        elif event.event_type == NotificationEventType.CONNECTION_LOST:
            self.connection_drops += 1
        elif event.event_type == NotificationEventType.CONNECTION_RESTORED:
            self.reconnection_attempts += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "connection_id": self.connection_id,
            "notifications_attempted": self.notifications_attempted,
            "notifications_delivered": self.notifications_delivered,
            "notifications_failed": self.notifications_failed,
            "silent_failures": self.silent_failures,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "silent_failure_rate": self.silent_failure_rate,
            "avg_delivery_time_ms": self.avg_delivery_time_ms,
            "min_delivery_time_ms": self.min_delivery_time_ms,
            "max_delivery_time_ms": self.max_delivery_time_ms,
            "last_successful_notification": self.last_successful_notification.isoformat() if self.last_successful_notification else None,
            "last_failed_notification": self.last_failed_notification.isoformat() if self.last_failed_notification else None,
            "connection_drops": self.connection_drops,
            "reconnection_attempts": self.reconnection_attempts,
            "consecutive_failures": self.consecutive_failures,
            "health_status": self.health_status.value,
            "is_healthy": self.is_healthy
        }


@dataclass
class SystemNotificationMetrics:
    """System-wide notification metrics."""
    # Overall counters
    total_bridge_initializations: int = 0
    successful_bridge_initializations: int = 0
    failed_bridge_initializations: int = 0
    
    total_notifications_attempted: int = 0
    total_notifications_delivered: int = 0
    total_notifications_failed: int = 0
    total_silent_failures: int = 0
    
    # Isolation tracking
    user_isolation_violations: int = 0
    cross_user_events: int = 0
    
    # Performance tracking
    memory_leaks_detected: int = 0
    performance_degradations: int = 0
    
    # Connection tracking
    active_connections: int = 0
    total_connection_drops: int = 0
    total_reconnections: int = 0
    
    # Timing metrics
    avg_bridge_init_time_ms: float = 0.0
    avg_notification_delivery_time_ms: float = 0.0
    
    @property
    def bridge_success_rate(self) -> float:
        """Calculate bridge initialization success rate."""
        if self.total_bridge_initializations == 0:
            return 1.0
        return self.successful_bridge_initializations / self.total_bridge_initializations
    
    @property
    def overall_success_rate(self) -> float:
        """Calculate overall notification success rate."""
        if self.total_notifications_attempted == 0:
            return 1.0
        return self.total_notifications_delivered / self.total_notifications_attempted
    
    @property
    def silent_failure_rate(self) -> float:
        """Calculate system-wide silent failure rate."""
        if self.total_notifications_attempted == 0:
            return 0.0
        return self.total_silent_failures / self.total_notifications_attempted
    
    @property 
    def system_health_status(self) -> HealthStatus:
        """Get overall system health status."""
        if (self.total_silent_failures > 0 or 
            self.bridge_success_rate < 1.0 or 
            self.user_isolation_violations > 0):
            return HealthStatus.CRITICAL
        elif self.overall_success_rate < 0.90:
            return HealthStatus.UNHEALTHY
        elif self.overall_success_rate < 0.95:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_bridge_initializations": self.total_bridge_initializations,
            "successful_bridge_initializations": self.successful_bridge_initializations,
            "failed_bridge_initializations": self.failed_bridge_initializations,
            "bridge_success_rate": self.bridge_success_rate,
            
            "total_notifications_attempted": self.total_notifications_attempted,
            "total_notifications_delivered": self.total_notifications_delivered,
            "total_notifications_failed": self.total_notifications_failed,
            "total_silent_failures": self.total_silent_failures,
            "overall_success_rate": self.overall_success_rate,
            "silent_failure_rate": self.silent_failure_rate,
            
            "user_isolation_violations": self.user_isolation_violations,
            "cross_user_events": self.cross_user_events,
            "memory_leaks_detected": self.memory_leaks_detected,
            "performance_degradations": self.performance_degradations,
            
            "active_connections": self.active_connections,
            "total_connection_drops": self.total_connection_drops,
            "total_reconnections": self.total_reconnections,
            
            "avg_bridge_init_time_ms": self.avg_bridge_init_time_ms,
            "avg_notification_delivery_time_ms": self.avg_notification_delivery_time_ms,
            
            "system_health_status": self.system_health_status.value
        }


class AlertThresholds:
    """Configurable thresholds for automated alerting."""
    
    def __init__(self):
        # Critical thresholds (immediate alerts)
        self.critical_bridge_failure_rate = 0.01  # 1% bridge failures
        self.critical_silent_failure_count = 1    # Any silent failure
        self.critical_user_isolation_violations = 1  # Any isolation violation
        self.critical_consecutive_failures = 5    # 5 consecutive failures
        
        # Unhealthy thresholds (urgent alerts)
        self.unhealthy_success_rate = 0.90        # 90% success rate
        self.unhealthy_delivery_latency_ms = 5000 # 5 second delivery latency
        self.unhealthy_connection_drops = 10      # 10 connection drops per hour
        
        # Degraded thresholds (warning alerts)
        self.degraded_success_rate = 0.95         # 95% success rate  
        self.degraded_delivery_latency_ms = 2000  # 2 second delivery latency
        self.degraded_consecutive_failures = 3    # 3 consecutive failures
        
        # Performance thresholds
        self.max_bridge_init_time_ms = 1000       # 1 second bridge init
        self.max_notification_latency_ms = 1000   # 1 second notification delivery
        self.max_memory_growth_mb = 100           # 100MB memory growth
        
        # Rate limiting
        self.alert_cooldown_minutes = 5           # 5 minutes between similar alerts
        self.max_alerts_per_hour = 20            # Maximum alerts per hour


class WebSocketNotificationMonitor:
    """
    Comprehensive WebSocket notification monitoring system.
    
    This class implements production-grade monitoring to detect and alert on:
    1. Silent notification failures (no errors but no delivery)
    2. Bridge initialization failures
    3. User isolation violations
    4. Performance degradations
    5. Connection stability issues
    
    CRITICAL FEATURES:
    - Real-time silent failure detection
    - Per-user metrics isolation
    - Automated alerting with configurable thresholds
    - Performance trend analysis
    - Memory leak detection
    - Connection health monitoring
    """
    
    def __init__(self, alert_manager: Optional[NotificationDeliveryManager] = None):
        """Initialize WebSocket notification monitor."""
        self.alert_manager = alert_manager or NotificationDeliveryManager()
        self.thresholds = AlertThresholds()
        
        # Metrics storage
        self.system_metrics = SystemNotificationMetrics()
        self.user_metrics: Dict[str, UserNotificationMetrics] = {}
        
        # Event tracking
        self.recent_events: Deque[NotificationEvent] = deque(maxlen=1000)
        self.pending_notifications: Dict[str, NotificationEvent] = {}
        
        # Health monitoring
        self.health_check_interval = 30.0  # 30 seconds
        self.silent_failure_detection_window = 60.0  # 60 seconds
        
        # Performance monitoring
        self.memory_baseline_mb: Optional[float] = None
        self.performance_samples: Deque[Dict[str, Any]] = deque(maxlen=100)
        
        # Alert management
        self.recent_alerts: Dict[str, datetime] = {}
        self.alert_suppression: Set[str] = set()
        
        # Background tasks
        self.monitor_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        
        logger.info(" SEARCH:  WebSocket Notification Monitor initialized")
    
    async def start_monitoring(self) -> None:
        """Start background monitoring tasks."""
        if self.monitor_task is None:
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info(" SEARCH:  WebSocket monitoring started")
        
        if self.health_check_task is None:
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info(" SEARCH:  Health check monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring tasks."""
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
            self.health_check_task = None
        
        logger.info(" SEARCH:  WebSocket monitoring stopped")
    
    # Event tracking methods
    
    def track_bridge_initialization_started(self, user_id: str, thread_id: str, connection_id: str) -> str:
        """Track bridge initialization start."""
        event = NotificationEvent(
            event_type=NotificationEventType.BRIDGE_INITIALIZATION_STARTED,
            user_id=user_id,
            thread_id=thread_id,
            connection_id=connection_id
        )
        
        self._add_event(event)
        self.system_metrics.total_bridge_initializations += 1
        
        logger.debug(f" SEARCH:  Bridge initialization started: {user_id}")
        return event.correlation_id
    
    def track_bridge_initialization_success(self, correlation_id: str, duration_ms: float) -> None:
        """Track successful bridge initialization."""
        event = NotificationEvent(
            event_type=NotificationEventType.BRIDGE_INITIALIZATION_SUCCESS,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            success=True
        )
        
        self._add_event(event)
        self.system_metrics.successful_bridge_initializations += 1
        self._update_avg_bridge_init_time(duration_ms)
        
        logger.debug(f" SEARCH:  Bridge initialization success: {duration_ms:.1f}ms")
    
    def track_bridge_initialization_failed(self, correlation_id: str, error: str, duration_ms: float) -> None:
        """Track failed bridge initialization."""
        event = NotificationEvent(
            event_type=NotificationEventType.BRIDGE_INITIALIZATION_FAILED,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            success=False,
            error_message=error
        )
        
        self._add_event(event)
        self.system_metrics.failed_bridge_initializations += 1
        
        # CRITICAL: Bridge initialization failure
        asyncio.create_task(self._alert_bridge_initialization_failed(event))
        
        logger.error(f" ALERT:  Bridge initialization FAILED: {error} ({duration_ms:.1f}ms)")
    
    def track_notification_attempted(self, user_id: str, thread_id: str, run_id: str, 
                                   agent_name: str, tool_name: Optional[str] = None,
                                   connection_id: Optional[str] = None) -> str:
        """Track notification attempt start."""
        event = NotificationEvent(
            event_type=NotificationEventType.NOTIFICATION_ATTEMPTED,
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            agent_name=agent_name,
            tool_name=tool_name,
            connection_id=connection_id
        )
        
        self._add_event(event)
        self.system_metrics.total_notifications_attempted += 1
        
        # Track as pending for silent failure detection
        self.pending_notifications[event.correlation_id] = event
        
        # Update user metrics
        user_key = self._get_user_key(user_id, thread_id)
        user_metrics = self._get_or_create_user_metrics(user_id, thread_id, connection_id)
        user_metrics.add_event(event)
        
        logger.debug(f" SEARCH:  Notification attempted: {user_id} -> {tool_name or agent_name}")
        return event.correlation_id
    
    def track_notification_delivered(self, correlation_id: str, delivery_time_ms: float) -> None:
        """Track successful notification delivery."""
        # Remove from pending
        pending_event = self.pending_notifications.pop(correlation_id, None)
        
        event = NotificationEvent(
            event_type=NotificationEventType.NOTIFICATION_DELIVERED,
            correlation_id=correlation_id,
            duration_ms=delivery_time_ms,
            success=True
        )
        
        # Copy context from pending event
        if pending_event:
            event.user_id = pending_event.user_id
            event.thread_id = pending_event.thread_id
            event.run_id = pending_event.run_id
            event.agent_name = pending_event.agent_name
            event.tool_name = pending_event.tool_name
            event.connection_id = pending_event.connection_id
        
        self._add_event(event)
        self.system_metrics.total_notifications_delivered += 1
        self._update_avg_delivery_time(delivery_time_ms)
        
        # Update user metrics
        if pending_event:
            user_key = self._get_user_key(event.user_id, event.thread_id)
            if user_key in self.user_metrics:
                self.user_metrics[user_key].add_event(event)
        
        logger.debug(f" SEARCH:  Notification delivered: {event.user_id} ({delivery_time_ms:.1f}ms)")
    
    def track_notification_failed(self, correlation_id: str, error: str, error_type: str) -> None:
        """Track failed notification delivery."""
        # Remove from pending
        pending_event = self.pending_notifications.pop(correlation_id, None)
        
        event = NotificationEvent(
            event_type=NotificationEventType.NOTIFICATION_FAILED,
            correlation_id=correlation_id,
            success=False,
            error_message=error,
            error_type=error_type
        )
        
        # Copy context from pending event
        if pending_event:
            event.user_id = pending_event.user_id
            event.thread_id = pending_event.thread_id
            event.run_id = pending_event.run_id
            event.agent_name = pending_event.agent_name
            event.tool_name = pending_event.tool_name
            event.connection_id = pending_event.connection_id
        
        self._add_event(event)
        self.system_metrics.total_notifications_failed += 1
        
        # Update user metrics
        if pending_event:
            user_key = self._get_user_key(event.user_id, event.thread_id)
            if user_key in self.user_metrics:
                user_metrics = self.user_metrics[user_key]
                user_metrics.add_event(event)
                
                # Check for alerting thresholds
                asyncio.create_task(self._check_user_failure_alerts(user_metrics))
        
        logger.warning(f" WARNING: [U+FE0F] Notification failed: {event.user_id} - {error}")
    
    def track_silent_failure_detected(self, user_id: str, thread_id: str, context: str) -> None:
        """Track detected silent failure."""
        event = NotificationEvent(
            event_type=NotificationEventType.SILENT_FAILURE_DETECTED,
            user_id=user_id,
            thread_id=thread_id,
            success=False,
            error_message=f"Silent failure detected: {context}",
            error_type="silent_failure"
        )
        
        self._add_event(event)
        self.system_metrics.total_silent_failures += 1
        
        # Update user metrics
        user_key = self._get_user_key(user_id, thread_id)
        user_metrics = self._get_or_create_user_metrics(user_id, thread_id)
        user_metrics.add_event(event)
        
        # CRITICAL: Silent failure detected
        asyncio.create_task(self._alert_silent_failure_detected(event))
        
        logger.critical(f" ALERT:  SILENT FAILURE DETECTED: {user_id} - {context}")
    
    def track_user_isolation_violation(self, user_a: str, user_b: str, event_type: str, context: str) -> None:
        """Track user isolation violation."""
        event = NotificationEvent(
            event_type=NotificationEventType.USER_ISOLATION_VIOLATION,
            user_id=user_a,
            success=False,
            error_message=f"Isolation violation: {user_a} -> {user_b} ({event_type})",
            error_type="isolation_violation",
            metadata={"target_user": user_b, "violation_type": event_type, "context": context}
        )
        
        self._add_event(event)
        self.system_metrics.user_isolation_violations += 1
        self.system_metrics.cross_user_events += 1
        
        # CRITICAL: User isolation violation
        asyncio.create_task(self._alert_isolation_violation(event))
        
        logger.critical(f" ALERT:  USER ISOLATION VIOLATION: {user_a} -> {user_b} ({event_type})")
    
    def track_connection_lost(self, user_id: str, thread_id: str, connection_id: str, reason: str) -> None:
        """Track WebSocket connection loss."""
        event = NotificationEvent(
            event_type=NotificationEventType.CONNECTION_LOST,
            user_id=user_id,
            thread_id=thread_id,
            connection_id=connection_id,
            success=False,
            error_message=f"Connection lost: {reason}"
        )
        
        self._add_event(event)
        self.system_metrics.total_connection_drops += 1
        self.system_metrics.active_connections = max(0, self.system_metrics.active_connections - 1)
        
        # Update user metrics
        user_key = self._get_user_key(user_id, thread_id)
        if user_key in self.user_metrics:
            self.user_metrics[user_key].add_event(event)
        
        logger.warning(f"[U+1F50C] Connection lost: {user_id} - {reason}")
    
    def track_connection_restored(self, user_id: str, thread_id: str, connection_id: str) -> None:
        """Track WebSocket connection restoration."""
        event = NotificationEvent(
            event_type=NotificationEventType.CONNECTION_RESTORED,
            user_id=user_id,
            thread_id=thread_id,
            connection_id=connection_id,
            success=True
        )
        
        self._add_event(event)
        self.system_metrics.total_reconnections += 1
        self.system_metrics.active_connections += 1
        
        # Update user metrics
        user_key = self._get_user_key(user_id, thread_id)
        if user_key in self.user_metrics:
            self.user_metrics[user_key].add_event(event)
        
        logger.info(f"[U+1F50C] Connection restored: {user_id}")
    
    # Monitoring and health check methods
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop for silent failure detection."""
        try:
            while True:
                await asyncio.sleep(self.silent_failure_detection_window)
                await self._check_silent_failures()
                await self._check_performance_degradation()
                await self._cleanup_stale_data()
                
        except asyncio.CancelledError:
            logger.info(" SEARCH:  Monitor loop cancelled")
            raise
        except Exception as e:
            logger.error(f" ALERT:  Monitor loop error: {e}", exc_info=True)
            # Continue monitoring despite errors
            await asyncio.sleep(10)
    
    async def _health_check_loop(self) -> None:
        """Health check monitoring loop."""
        try:
            while True:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_check()
                
        except asyncio.CancelledError:
            logger.info(" SEARCH:  Health check loop cancelled")
            raise
        except Exception as e:
            logger.error(f" ALERT:  Health check loop error: {e}", exc_info=True)
            await asyncio.sleep(10)
    
    async def _check_silent_failures(self) -> None:
        """Check for silent failures in pending notifications."""
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(seconds=self.silent_failure_detection_window)
        
        silent_failures = []
        for correlation_id, pending_event in list(self.pending_notifications.items()):
            if pending_event.timestamp < cutoff_time:
                silent_failures.append((correlation_id, pending_event))
        
        # Process detected silent failures
        for correlation_id, pending_event in silent_failures:
            del self.pending_notifications[correlation_id]
            
            context = f"Notification pending for {self.silent_failure_detection_window}s: {pending_event.tool_name or pending_event.agent_name}"
            self.track_silent_failure_detected(
                pending_event.user_id, 
                pending_event.thread_id, 
                context
            )
        
        if silent_failures:
            logger.critical(f" ALERT:  Detected {len(silent_failures)} silent failures")
    
    async def _check_performance_degradation(self) -> None:
        """Check for performance degradation indicators."""
        # Check memory usage
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if self.memory_baseline_mb is None:
                self.memory_baseline_mb = memory_mb
            else:
                memory_growth = memory_mb - self.memory_baseline_mb
                if memory_growth > self.thresholds.max_memory_growth_mb:
                    self.track_memory_leak_detected(memory_growth)
            
            # Store performance sample
            sample = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "memory_mb": memory_mb,
                "active_connections": self.system_metrics.active_connections,
                "pending_notifications": len(self.pending_notifications),
                "avg_delivery_time_ms": self.system_metrics.avg_notification_delivery_time_ms
            }
            self.performance_samples.append(sample)
            
        except Exception as e:
            logger.warning(f"Performance check failed: {e}")
    
    async def _perform_health_check(self) -> None:
        """Perform comprehensive health check."""
        health_status = self.get_system_health_status()
        
        # Log health status
        if health_status["status"] != HealthStatus.HEALTHY:
            logger.warning(f"[U+1F3E5] System health: {health_status['status'].value} - Issues: {health_status.get('issues', [])}")
        
        # Check for degraded users
        unhealthy_users = []
        for user_key, user_metrics in self.user_metrics.items():
            if not user_metrics.is_healthy:
                unhealthy_users.append((user_key, user_metrics))
        
        if unhealthy_users:
            logger.warning(f"[U+1F3E5] Unhealthy users detected: {len(unhealthy_users)}")
            for user_key, user_metrics in unhealthy_users:
                logger.warning(f"[U+1F3E5] User {user_metrics.user_id}: {user_metrics.health_status.value} (success_rate={user_metrics.success_rate:.3f})")
    
    def track_memory_leak_detected(self, growth_mb: float) -> None:
        """Track memory leak detection."""
        event = NotificationEvent(
            event_type=NotificationEventType.MEMORY_LEAK_DETECTED,
            success=False,
            error_message=f"Memory growth detected: {growth_mb:.1f}MB",
            metadata={"memory_growth_mb": growth_mb}
        )
        
        self._add_event(event)
        self.system_metrics.memory_leaks_detected += 1
        
        # Alert on significant memory growth
        asyncio.create_task(self._alert_memory_leak(event, growth_mb))
        
        logger.warning(f"[U+1F9E0] Memory leak detected: +{growth_mb:.1f}MB")
    
    # Alert management methods
    
    async def _alert_bridge_initialization_failed(self, event: NotificationEvent) -> None:
        """Send alert for bridge initialization failure."""
        if self._should_send_alert("bridge_init_failed"):
            alert = Alert(
                alert_id=f"bridge_init_failed_{event.correlation_id}",
                rule_id="websocket_bridge_init_failure",
                title="WebSocket Bridge Initialization Failed",
                message=f"Bridge initialization failed for user {event.user_id}: {event.error_message}",
                level=AlertLevel.CRITICAL,
                agent_name="WebSocketBridgeFactory",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "user_id": event.user_id,
                    "error": event.error_message,
                    "correlation_id": event.correlation_id,
                    "component": "websocket_monitor"
                }
            )
            
            await self._send_alert(alert)
            self._mark_alert_sent("bridge_init_failed")
    
    async def _alert_silent_failure_detected(self, event: NotificationEvent) -> None:
        """Send alert for silent failure detection."""
        alert_key = f"silent_failure_{event.user_id}"
        if self._should_send_alert(alert_key):
            alert = Alert(
                alert_id=f"silent_failure_{event.user_id}_{uuid.uuid4().hex[:8]}",
                rule_id="websocket_silent_failure",
                title="Silent WebSocket Notification Failure",
                message=f"Silent failure detected for user {event.user_id}: {event.error_message}",
                level=AlertLevel.CRITICAL,
                agent_name="SilentFailureDetector",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "user_id": event.user_id,
                    "thread_id": event.thread_id,
                    "context": event.error_message,
                    "component": "websocket_monitor"
                }
            )
            
            await self._send_alert(alert)
            self._mark_alert_sent(alert_key)
    
    async def _alert_isolation_violation(self, event: NotificationEvent) -> None:
        """Send alert for user isolation violation."""
        alert_key = "isolation_violation"
        if self._should_send_alert(alert_key):
            alert = Alert(
                alert_id=f"isolation_violation_{event.user_id}_{uuid.uuid4().hex[:8]}",
                rule_id="websocket_isolation_violation",
                title="User Isolation Violation Detected",
                message=f"Cross-user event detected: {event.error_message}",
                level=AlertLevel.CRITICAL,
                agent_name="IsolationMonitor",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "source_user": event.user_id,
                    "target_user": event.metadata.get("target_user"),
                    "violation_type": event.metadata.get("violation_type"),
                    "context": event.metadata.get("context"),
                    "component": "websocket_monitor"
                }
            )
            
            await self._send_alert(alert)
            self._mark_alert_sent(alert_key)
    
    async def _alert_memory_leak(self, event: NotificationEvent, growth_mb: float) -> None:
        """Send alert for memory leak detection."""
        if growth_mb > self.thresholds.max_memory_growth_mb * 2:  # Only alert on significant leaks
            alert_key = "memory_leak"
            if self._should_send_alert(alert_key):
                alert = Alert(
                    alert_id=f"memory_leak_{uuid.uuid4().hex[:8]}",
                    rule_id="websocket_memory_leak",
                    title="Memory Leak Detected in WebSocket System",
                    message=f"Significant memory growth detected: {growth_mb:.1f}MB increase",
                    level=AlertLevel.WARNING,
                    agent_name="MemoryMonitor",
                    timestamp=datetime.now(timezone.utc),
                    metadata={
                        "memory_growth_mb": growth_mb,
                        "component": "websocket_monitor"
                    }
                )
                
                await self._send_alert(alert)
                self._mark_alert_sent(alert_key)
    
    async def _check_user_failure_alerts(self, user_metrics: UserNotificationMetrics) -> None:
        """Check if user metrics warrant an alert."""
        alert_key = f"user_failures_{user_metrics.user_id}"
        
        if (user_metrics.consecutive_failures >= self.thresholds.critical_consecutive_failures and
            self._should_send_alert(alert_key)):
            
            alert = Alert(
                alert_id=f"user_notification_failures_{user_metrics.user_id}_{uuid.uuid4().hex[:8]}",
                rule_id="websocket_user_notification_failures",
                title="User Notification Failures",
                message=f"User {user_metrics.user_id} has {user_metrics.consecutive_failures} consecutive notification failures",
                level=AlertLevel.ERROR,
                agent_name="UserMetricsMonitor",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "user_id": user_metrics.user_id,
                    "consecutive_failures": user_metrics.consecutive_failures,
                    "success_rate": user_metrics.success_rate,
                    "health_status": user_metrics.health_status.value,
                    "component": "websocket_monitor"
                }
            )
            
            await self._send_alert(alert)
            self._mark_alert_sent(alert_key)
    
    async def _send_alert(self, alert: Alert) -> None:
        """Send alert through notification system."""
        try:
            channels = [NotificationChannel.LOG, NotificationChannel.DATABASE]
            configs = {
                NotificationChannel.LOG: self.alert_manager.rate_limit_manager.notification_rate_limits,
                NotificationChannel.DATABASE: {}
            }
            
            await self.alert_manager.deliver_notifications(alert, channels, {})
            logger.info(f" ALERT:  Alert sent: {alert.title}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def _should_send_alert(self, alert_key: str) -> bool:
        """Check if alert should be sent based on rate limiting."""
        now = datetime.now(timezone.utc)
        
        if alert_key in self.alert_suppression:
            return False
            
        last_sent = self.recent_alerts.get(alert_key)
        if last_sent:
            time_since_last = (now - last_sent).total_seconds()
            if time_since_last < self.thresholds.alert_cooldown_minutes * 60:
                return False
        
        return True
    
    def _mark_alert_sent(self, alert_key: str) -> None:
        """Mark alert as sent to manage rate limiting."""
        self.recent_alerts[alert_key] = datetime.now(timezone.utc)
    
    # Utility methods
    
    def _add_event(self, event: NotificationEvent) -> None:
        """Add event to tracking systems."""
        self.recent_events.append(event)
        
        # Log structured event for analysis
        logger.info(f" CHART:  WebSocket Event: {event.event_type.value} | {event.user_id} | {event.success} | {event.correlation_id}")
    
    def _get_user_key(self, user_id: str, thread_id: str) -> str:
        """Generate unique user key for metrics tracking."""
        return f"{user_id}:{thread_id}"
    
    def _get_or_create_user_metrics(self, user_id: str, thread_id: str, 
                                    connection_id: Optional[str] = None) -> UserNotificationMetrics:
        """Get or create user metrics instance."""
        user_key = self._get_user_key(user_id, thread_id)
        
        if user_key not in self.user_metrics:
            self.user_metrics[user_key] = UserNotificationMetrics(
                user_id=user_id,
                thread_id=thread_id,
                connection_id=connection_id
            )
        
        return self.user_metrics[user_key]
    
    def _update_avg_bridge_init_time(self, duration_ms: float) -> None:
        """Update average bridge initialization time."""
        total_time = (self.system_metrics.avg_bridge_init_time_ms * 
                     (self.system_metrics.successful_bridge_initializations - 1))
        self.system_metrics.avg_bridge_init_time_ms = (
            (total_time + duration_ms) / self.system_metrics.successful_bridge_initializations
        )
    
    def _update_avg_delivery_time(self, delivery_time_ms: float) -> None:
        """Update average notification delivery time."""
        total_time = (self.system_metrics.avg_notification_delivery_time_ms * 
                     (self.system_metrics.total_notifications_delivered - 1))
        self.system_metrics.avg_notification_delivery_time_ms = (
            (total_time + delivery_time_ms) / self.system_metrics.total_notifications_delivered
        )
    
    async def _cleanup_stale_data(self) -> None:
        """Clean up stale monitoring data."""
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=1)
        
        # Clean up old alert records
        expired_alerts = [
            key for key, timestamp in self.recent_alerts.items()
            if timestamp < cutoff_time
        ]
        for key in expired_alerts:
            del self.recent_alerts[key]
        
        # Clean up stale user metrics (no activity for 1 hour)
        stale_users = []
        for user_key, user_metrics in self.user_metrics.items():
            last_activity = (user_metrics.last_successful_notification or 
                           user_metrics.last_failed_notification)
            if last_activity and last_activity < cutoff_time:
                stale_users.append(user_key)
        
        for user_key in stale_users:
            logger.debug(f"[U+1F9F9] Cleaning up stale user metrics: {user_key}")
            del self.user_metrics[user_key]
    
    # Public API methods
    
    def get_system_health_status(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        issues = []
        
        # Check system metrics against thresholds
        if self.system_metrics.total_silent_failures > 0:
            issues.append(f"Silent failures detected: {self.system_metrics.total_silent_failures}")
        
        if self.system_metrics.bridge_success_rate < (1.0 - self.thresholds.critical_bridge_failure_rate):
            issues.append(f"Bridge failures: {self.system_metrics.failed_bridge_initializations}")
        
        if self.system_metrics.overall_success_rate < self.thresholds.unhealthy_success_rate:
            issues.append(f"Low success rate: {self.system_metrics.overall_success_rate:.3f}")
        
        if self.system_metrics.user_isolation_violations > 0:
            issues.append(f"Isolation violations: {self.system_metrics.user_isolation_violations}")
        
        if self.system_metrics.avg_notification_delivery_time_ms > self.thresholds.unhealthy_delivery_latency_ms:
            issues.append(f"High latency: {self.system_metrics.avg_notification_delivery_time_ms:.1f}ms")
        
        status = self.system_metrics.system_health_status
        
        return {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "issues": issues,
            "system_metrics": self.system_metrics.to_dict(),
            "active_users": len(self.user_metrics),
            "pending_notifications": len(self.pending_notifications),
            "recent_events": len(self.recent_events),
            "monitoring_active": self.monitor_task is not None and not self.monitor_task.done()
        }
    
    def get_user_metrics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get user-specific metrics."""
        if user_id:
            # Return specific user metrics
            user_metrics = {}
            for user_key, metrics in self.user_metrics.items():
                if metrics.user_id == user_id:
                    user_metrics[user_key] = metrics.to_dict()
            return user_metrics
        else:
            # Return all user metrics
            return {
                user_key: metrics.to_dict() 
                for user_key, metrics in self.user_metrics.items()
            }
    
    def get_recent_events(self, limit: int = 100, event_type: Optional[NotificationEventType] = None) -> List[Dict[str, Any]]:
        """Get recent monitoring events."""
        events = list(self.recent_events)
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        events = events[-limit:]  # Get most recent
        return [event.to_dict() for event in events]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance and trend metrics."""
        return {
            "performance_samples": list(self.performance_samples),
            "memory_baseline_mb": self.memory_baseline_mb,
            "thresholds": {
                "max_bridge_init_time_ms": self.thresholds.max_bridge_init_time_ms,
                "max_notification_latency_ms": self.thresholds.max_notification_latency_ms,
                "max_memory_growth_mb": self.thresholds.max_memory_growth_mb
            },
            "current_performance": {
                "avg_bridge_init_time_ms": self.system_metrics.avg_bridge_init_time_ms,
                "avg_delivery_time_ms": self.system_metrics.avg_notification_delivery_time_ms,
                "active_connections": self.system_metrics.active_connections
            }
        }
    
    @asynccontextmanager
    async def monitor_notification(self, user_id: str, thread_id: str, run_id: str, 
                                 agent_name: str, tool_name: Optional[str] = None,
                                 connection_id: Optional[str] = None):
        """Context manager for monitoring a notification lifecycle."""
        correlation_id = self.track_notification_attempted(
            user_id, thread_id, run_id, agent_name, tool_name, connection_id
        )
        
        start_time = time.time()
        
        try:
            yield correlation_id
            # If we reach here, notification was successful
            delivery_time_ms = (time.time() - start_time) * 1000
            self.track_notification_delivered(correlation_id, delivery_time_ms)
            
        except Exception as e:
            # Notification failed
            error_type = type(e).__name__
            self.track_notification_failed(correlation_id, str(e), error_type)
            raise


# Global monitor instance
_websocket_notification_monitor: Optional[WebSocketNotificationMonitor] = None


def get_websocket_notification_monitor() -> WebSocketNotificationMonitor:
    """Get or create the global WebSocket notification monitor."""
    global _websocket_notification_monitor
    if _websocket_notification_monitor is None:
        _websocket_notification_monitor = WebSocketNotificationMonitor()
    return _websocket_notification_monitor


async def start_websocket_monitoring() -> None:
    """Start global WebSocket monitoring."""
    monitor = get_websocket_notification_monitor()
    await monitor.start_monitoring()
    logger.info(" SEARCH:  Global WebSocket monitoring started")


async def stop_websocket_monitoring() -> None:
    """Stop global WebSocket monitoring."""
    global _websocket_notification_monitor
    if _websocket_notification_monitor:
        await _websocket_notification_monitor.stop_monitoring()
        logger.info(" SEARCH:  Global WebSocket monitoring stopped")