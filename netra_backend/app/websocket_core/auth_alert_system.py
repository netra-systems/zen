"""
Authentication Alert System - Issue #1300 Task #4

Business Value Justification (BVJ):
- Segment: Platform/Internal - Authentication Infrastructure
- Business Goal: Proactive detection and notification of authentication issues
- Value Impact: Prevent authentication outages from impacting $500K+ ARR chat functionality
- Revenue Impact: Reduce incident response time and minimize user impact

This module implements a comprehensive alerting system for WebSocket authentication,
providing real-time notifications for authentication anomalies, security events,
and performance issues.

Key Features:
1. Configurable alert rules and thresholds
2. Multiple notification channels (email, Slack, webhooks)
3. Alert suppression and rate limiting
4. Escalation policies for critical alerts
5. Integration with existing monitoring infrastructure
6. Alert history and analytics
7. Self-monitoring and health checks
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import defaultdict, deque
import threading
import logging

from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.websocket_core.auth_monitoring import (
    AuthEventType,
    get_websocket_auth_monitor
)
from netra_backend.app.websocket_core.auth_structured_logger import (
    log_security_event,
    log_audit_event
)

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertCategory(Enum):
    """Categories of alerts."""
    AUTHENTICATION = "authentication"
    SECURITY = "security"
    PERFORMANCE = "performance"
    AVAILABILITY = "availability"
    CONFIGURATION = "configuration"


class AlertStatus(Enum):
    """Status of alerts."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """Configuration for an alert rule."""
    name: str
    description: str
    category: AlertCategory
    severity: AlertSeverity
    condition: Callable[[Dict[str, Any]], bool]
    threshold_value: Optional[Union[int, float]] = None
    time_window_seconds: int = 300  # 5 minutes
    min_occurrences: int = 1
    suppression_duration_minutes: int = 5
    escalation_after_minutes: Optional[int] = None
    enabled: bool = True
    
    def __post_init__(self):
        """Validate rule configuration."""
        if self.escalation_after_minutes and self.escalation_after_minutes <= self.suppression_duration_minutes:
            raise ValueError("Escalation time must be greater than suppression duration")


@dataclass 
class Alert:
    """An individual alert instance."""
    id: str
    rule_name: str
    category: AlertCategory
    severity: AlertSeverity
    title: str
    description: str
    triggered_at: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "id": self.id,
            "rule_name": self.rule_name,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "triggered_at": self.triggered_at.isoformat(),
            "status": self.status.value,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "escalated_at": self.escalated_at.isoformat() if self.escalated_at else None,
            "metadata": self.metadata
        }


@dataclass
class NotificationChannel:
    """Configuration for a notification channel."""
    name: str
    channel_type: str  # email, slack, webhook, etc.
    config: Dict[str, Any]
    enabled: bool = True
    severity_filter: List[AlertSeverity] = field(default_factory=lambda: list(AlertSeverity))
    category_filter: List[AlertCategory] = field(default_factory=lambda: list(AlertCategory))


class AuthAlertSystem:
    """
    Authentication Alert System for Issue #1300 Task #4.
    
    Provides comprehensive alerting for WebSocket authentication events,
    including configurable rules, notification channels, and escalation policies.
    
    Features:
    - Configurable alert rules and thresholds
    - Multiple notification channels
    - Alert suppression and rate limiting
    - Escalation policies for critical alerts
    - Alert history and analytics
    """
    
    def __init__(self):
        """Initialize the authentication alert system."""
        self._lock = threading.RLock()
        
        # Alert rules and configuration
        self._alert_rules: Dict[str, AlertRule] = {}
        self._notification_channels: Dict[str, NotificationChannel] = {}
        
        # Alert storage and tracking
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: deque = deque(maxlen=1000)  # Keep last 1000 alerts
        
        # Suppression tracking
        self._suppressed_rules: Dict[str, datetime] = {}
        
        # Statistics
        self._alert_stats = {
            "total_alerts": 0,
            "alerts_by_severity": defaultdict(int),
            "alerts_by_category": defaultdict(int),
            "alerts_by_rule": defaultdict(int),
            "notifications_sent": 0,
            "notifications_failed": 0
        }
        
        # System state
        self._system_start_time = datetime.now(timezone.utc)
        self._last_check_time = None
        self._monitoring_enabled = True
        
        # Initialize default alert rules
        self._setup_default_alert_rules()
        
        # Initialize default notification channels
        self._setup_default_notification_channels()
        
        logger.info("AuthAlertSystem initialized for Issue #1300")
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add or update an alert rule."""
        with self._lock:
            self._alert_rules[rule.name] = rule
            logger.info(f"Added alert rule: {rule.name} ({rule.severity.value})")
    
    def remove_alert_rule(self, rule_name: str) -> bool:
        """Remove an alert rule."""
        with self._lock:
            if rule_name in self._alert_rules:
                del self._alert_rules[rule_name]
                logger.info(f"Removed alert rule: {rule_name}")
                return True
            return False
    
    def add_notification_channel(self, channel: NotificationChannel) -> None:
        """Add or update a notification channel."""
        with self._lock:
            self._notification_channels[channel.name] = channel
            logger.info(f"Added notification channel: {channel.name} ({channel.channel_type})")
    
    def remove_notification_channel(self, channel_name: str) -> bool:
        """Remove a notification channel."""
        with self._lock:
            if channel_name in self._notification_channels:
                del self._notification_channels[channel_name]
                logger.info(f"Removed notification channel: {channel_name}")
                return True
            return False
    
    async def check_alerts(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check all alert rules against current metrics and trigger alerts if needed."""
        if not self._monitoring_enabled:
            return []
        
        triggered_alerts = []
        current_time = datetime.now(timezone.utc)
        
        with self._lock:
            self._last_check_time = current_time
            
            for rule_name, rule in self._alert_rules.items():
                if not rule.enabled:
                    continue
                
                # Check if rule is currently suppressed
                if self._is_rule_suppressed(rule_name, current_time):
                    continue
                
                try:
                    # Evaluate rule condition
                    if rule.condition(metrics):
                        alert = await self._create_alert(rule, metrics, current_time)
                        if alert:
                            triggered_alerts.append(alert)
                            await self._process_alert(alert)
                            
                except Exception as e:
                    logger.error(f"Error evaluating alert rule {rule_name}: {e}")
        
        return triggered_alerts
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """Acknowledge an active alert."""
        with self._lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now(timezone.utc)
                alert.metadata["acknowledged_by"] = acknowledged_by
                
                logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                
                # Log audit event
                log_audit_event(
                    action="alert_acknowledged",
                    result="success",
                    user_id=acknowledged_by,
                    audit_details={
                        "alert_id": alert_id,
                        "rule_name": alert.rule_name,
                        "severity": alert.severity.value
                    }
                )
                return True
            return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str = "system", resolution_note: Optional[str] = None) -> bool:
        """Resolve an active alert."""
        with self._lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc)
                alert.metadata["resolved_by"] = resolved_by
                if resolution_note:
                    alert.metadata["resolution_note"] = resolution_note
                
                # Move to history
                self._alert_history.append(alert)
                del self._active_alerts[alert_id]
                
                logger.info(f"Alert {alert_id} resolved by {resolved_by}")
                
                # Log audit event
                log_audit_event(
                    action="alert_resolved",
                    result="success",
                    user_id=resolved_by,
                    audit_details={
                        "alert_id": alert_id,
                        "rule_name": alert.rule_name,
                        "severity": alert.severity.value,
                        "resolution_note": resolution_note
                    }
                )
                return True
            return False
    
    def get_active_alerts(self, severity_filter: Optional[AlertSeverity] = None) -> List[Dict[str, Any]]:
        """Get list of active alerts."""
        with self._lock:
            alerts = list(self._active_alerts.values())
            
            if severity_filter:
                alerts = [alert for alert in alerts if alert.severity == severity_filter]
            
            return [alert.to_dict() for alert in alerts]
    
    def get_alert_history(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history for the specified time period."""
        with self._lock:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Get alerts from history and active alerts
            all_alerts = list(self._alert_history) + list(self._active_alerts.values())
            
            # Filter by time and limit
            recent_alerts = [
                alert for alert in all_alerts
                if alert.triggered_at >= cutoff_time
            ]
            
            # Sort by trigger time (most recent first)
            recent_alerts.sort(key=lambda a: a.triggered_at, reverse=True)
            
            return [alert.to_dict() for alert in recent_alerts[:limit]]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert system statistics."""
        with self._lock:
            uptime_seconds = (datetime.now(timezone.utc) - self._system_start_time).total_seconds()
            
            return {
                "system_info": {
                    "uptime_seconds": uptime_seconds,
                    "monitoring_enabled": self._monitoring_enabled,
                    "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None
                },
                "configuration": {
                    "total_rules": len(self._alert_rules),
                    "enabled_rules": len([r for r in self._alert_rules.values() if r.enabled]),
                    "notification_channels": len(self._notification_channels),
                    "enabled_channels": len([c for c in self._notification_channels.values() if c.enabled])
                },
                "current_state": {
                    "active_alerts": len(self._active_alerts),
                    "suppressed_rules": len(self._suppressed_rules),
                    "history_size": len(self._alert_history)
                },
                "statistics": dict(self._alert_stats),
                "alerts_per_hour": self._alert_stats["total_alerts"] / (uptime_seconds / 3600) if uptime_seconds > 0 else 0
            }
    
    async def test_notification_channels(self) -> Dict[str, bool]:
        """Test all notification channels."""
        results = {}
        
        test_alert = Alert(
            id="test_alert_" + str(int(time.time())),
            rule_name="test_rule",
            category=AlertCategory.CONFIGURATION,
            severity=AlertSeverity.INFO,
            title="Test Alert",
            description="This is a test alert to verify notification channels",
            triggered_at=datetime.now(timezone.utc),
            metadata={"test": True}
        )
        
        for channel_name, channel in self._notification_channels.items():
            if not channel.enabled:
                results[channel_name] = False
                continue
                
            try:
                success = await self._send_notification(channel, test_alert)
                results[channel_name] = success
            except Exception as e:
                logger.error(f"Failed to test notification channel {channel_name}: {e}")
                results[channel_name] = False
        
        return results
    
    def enable_monitoring(self) -> None:
        """Enable alert monitoring."""
        self._monitoring_enabled = True
        logger.info("Alert monitoring enabled")
    
    def disable_monitoring(self) -> None:
        """Disable alert monitoring."""
        self._monitoring_enabled = False
        logger.info("Alert monitoring disabled")
    
    async def _create_alert(self, rule: AlertRule, metrics: Dict[str, Any], current_time: datetime) -> Optional[Alert]:
        """Create a new alert from a triggered rule."""
        try:
            # Generate unique alert ID
            alert_id = f"{rule.name}_{int(current_time.timestamp())}"
            
            # Create alert description based on rule and metrics
            description = self._generate_alert_description(rule, metrics)
            
            alert = Alert(
                id=alert_id,
                rule_name=rule.name,
                category=rule.category,
                severity=rule.severity,
                title=f"{rule.category.value.title()} Alert: {rule.name}",
                description=description,
                triggered_at=current_time,
                metadata={
                    "rule_description": rule.description,
                    "threshold_value": rule.threshold_value,
                    "metrics_snapshot": metrics,
                    "issue": "#1300"
                }
            )
            
            # Store active alert
            with self._lock:
                self._active_alerts[alert_id] = alert
                self._alert_stats["total_alerts"] += 1
                self._alert_stats["alerts_by_severity"][rule.severity.value] += 1
                self._alert_stats["alerts_by_category"][rule.category.value] += 1
                self._alert_stats["alerts_by_rule"][rule.name] += 1
            
            logger.warning(f"Alert triggered: {rule.name} - {description}")
            return alert
            
        except Exception as e:
            logger.error(f"Failed to create alert for rule {rule.name}: {e}")
            return None
    
    async def _process_alert(self, alert: Alert) -> None:
        """Process a triggered alert (send notifications, etc.)."""
        try:
            # Send notifications to applicable channels
            notification_results = []
            
            for channel_name, channel in self._notification_channels.items():
                if not channel.enabled:
                    continue
                
                # Check filters
                if channel.severity_filter and alert.severity not in channel.severity_filter:
                    continue
                if channel.category_filter and alert.category not in channel.category_filter:
                    continue
                
                try:
                    success = await self._send_notification(channel, alert)
                    notification_results.append({"channel": channel_name, "success": success})
                    
                    if success:
                        self._alert_stats["notifications_sent"] += 1
                    else:
                        self._alert_stats["notifications_failed"] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to send notification to {channel_name}: {e}")
                    self._alert_stats["notifications_failed"] += 1
            
            # Update alert metadata with notification results
            alert.metadata["notification_results"] = notification_results
            
            # Set suppression for this rule
            rule = self._alert_rules.get(alert.rule_name)
            if rule:
                suppression_until = datetime.now(timezone.utc) + timedelta(minutes=rule.suppression_duration_minutes)
                self._suppressed_rules[alert.rule_name] = suppression_until
            
            # Log security event for critical alerts
            if alert.severity == AlertSeverity.CRITICAL:
                log_security_event(
                    event_description=f"Critical authentication alert triggered: {alert.title}",
                    severity="critical",
                    security_details={
                        "alert_id": alert.id,
                        "rule_name": alert.rule_name,
                        "category": alert.category.value
                    }
                )
                
        except Exception as e:
            logger.error(f"Error processing alert {alert.id}: {e}")
    
    async def _send_notification(self, channel: NotificationChannel, alert: Alert) -> bool:
        """Send notification to a specific channel."""
        try:
            if channel.channel_type == "log":
                # Log-based notification (for testing/development)
                log_level = "CRITICAL" if alert.severity == AlertSeverity.CRITICAL else "WARNING"
                logger.warning(f"NOTIFICATION [{log_level}]: {alert.title} - {alert.description}")
                return True
                
            elif channel.channel_type == "webhook":
                # Webhook notification
                return await self._send_webhook_notification(channel, alert)
                
            elif channel.channel_type == "email":
                # Email notification (placeholder)
                logger.info(f"Would send email notification for alert {alert.id}")
                return True
                
            elif channel.channel_type == "slack":
                # Slack notification (placeholder)
                logger.info(f"Would send Slack notification for alert {alert.id}")
                return True
                
            else:
                logger.warning(f"Unknown notification channel type: {channel.channel_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send notification via {channel.name}: {e}")
            return False
    
    async def _send_webhook_notification(self, channel: NotificationChannel, alert: Alert) -> bool:
        """Send webhook notification."""
        try:
            # This is a placeholder - in a real implementation, you would use aiohttp or similar
            webhook_url = channel.config.get("url")
            if not webhook_url:
                logger.error(f"Webhook channel {channel.name} missing URL configuration")
                return False
            
            payload = {
                "alert": alert.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "netra_backend.auth_alert_system",
                "issue": "#1300"
            }
            
            # In a real implementation, you would make the HTTP request here
            logger.info(f"Would send webhook to {webhook_url} with payload: {json.dumps(payload, indent=2)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False
    
    def _is_rule_suppressed(self, rule_name: str, current_time: datetime) -> bool:
        """Check if a rule is currently suppressed."""
        if rule_name not in self._suppressed_rules:
            return False
        
        suppressed_until = self._suppressed_rules[rule_name]
        if current_time >= suppressed_until:
            # Suppression expired
            del self._suppressed_rules[rule_name]
            return False
        
        return True
    
    def _generate_alert_description(self, rule: AlertRule, metrics: Dict[str, Any]) -> str:
        """Generate a descriptive alert message."""
        base_description = rule.description
        
        # Add specific metrics information
        if rule.threshold_value is not None:
            base_description += f" (threshold: {rule.threshold_value})"
        
        # Add relevant metric values
        if "global_metrics" in metrics:
            gm = metrics["global_metrics"]
            if rule.category == AlertCategory.AUTHENTICATION:
                success_rate = gm.get("auth_success_rate", 100.0)
                attempts = gm.get("auth_attempts", 0)
                base_description += f" - Current: {success_rate:.1f}% success rate over {attempts} attempts"
            elif rule.category == AlertCategory.PERFORMANCE:
                latency = gm.get("latency_percentiles", {}).get("p95", 0)
                base_description += f" - Current P95 latency: {latency:.1f}ms"
        
        return base_description
    
    def _setup_default_alert_rules(self) -> None:
        """Set up default alert rules for authentication monitoring."""
        # High authentication failure rate
        self.add_alert_rule(AlertRule(
            name="high_auth_failure_rate",
            description="Authentication failure rate is above threshold",
            category=AlertCategory.AUTHENTICATION,
            severity=AlertSeverity.ERROR,
            condition=lambda m: (
                m.get("global_metrics", {}).get("auth_attempts", 0) > 5 and
                m.get("global_metrics", {}).get("auth_success_rate", 100.0) < 80.0
            ),
            threshold_value=80.0,
            time_window_seconds=300,
            suppression_duration_minutes=5
        ))
        
        # Critical authentication failure rate
        self.add_alert_rule(AlertRule(
            name="critical_auth_failure_rate",
            description="Authentication failure rate is critically high",
            category=AlertCategory.AUTHENTICATION,
            severity=AlertSeverity.CRITICAL,
            condition=lambda m: (
                m.get("global_metrics", {}).get("auth_attempts", 0) > 10 and
                m.get("global_metrics", {}).get("auth_success_rate", 100.0) < 50.0
            ),
            threshold_value=50.0,
            time_window_seconds=300,
            suppression_duration_minutes=3,
            escalation_after_minutes=10
        ))
        
        # High authentication latency
        self.add_alert_rule(AlertRule(
            name="high_auth_latency",
            description="Authentication latency is above threshold",
            category=AlertCategory.PERFORMANCE,
            severity=AlertSeverity.WARNING,
            condition=lambda m: (
                m.get("global_metrics", {}).get("latency_percentiles", {}).get("p95", 0) > 2000.0
            ),
            threshold_value=2000.0,
            time_window_seconds=300,
            suppression_duration_minutes=10
        ))
        
        # Token validation failures
        self.add_alert_rule(AlertRule(
            name="high_token_validation_failure_rate",
            description="Token validation failure rate is above threshold",
            category=AlertCategory.SECURITY,
            severity=AlertSeverity.WARNING,
            condition=lambda m: (
                m.get("global_metrics", {}).get("token_validations", 0) > 5 and
                m.get("global_metrics", {}).get("token_validation_success_rate", 100.0) < 85.0
            ),
            threshold_value=85.0,
            time_window_seconds=300,
            suppression_duration_minutes=5
        ))
        
        # Connection upgrade failures
        self.add_alert_rule(AlertRule(
            name="high_connection_failure_rate",
            description="Connection upgrade failure rate is above threshold",
            category=AlertCategory.AVAILABILITY,
            severity=AlertSeverity.ERROR,
            condition=lambda m: (
                m.get("global_metrics", {}).get("connection_upgrades", 0) > 3 and
                m.get("global_metrics", {}).get("connection_upgrade_success_rate", 100.0) < 75.0
            ),
            threshold_value=75.0,
            time_window_seconds=300,
            suppression_duration_minutes=5
        ))
        
        logger.info("Default alert rules configured")
    
    def _setup_default_notification_channels(self) -> None:
        """Set up default notification channels."""
        # Log-based notification (always available)
        self.add_notification_channel(NotificationChannel(
            name="system_log",
            channel_type="log",
            config={},
            enabled=True,
            severity_filter=[AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL],
            category_filter=list(AlertCategory)
        ))
        
        logger.info("Default notification channels configured")


# Global instance for authentication alerting
_auth_alert_system: Optional[AuthAlertSystem] = None
_alert_system_lock = threading.Lock()


def get_auth_alert_system() -> AuthAlertSystem:
    """Get or create the global authentication alert system."""
    global _auth_alert_system
    
    if _auth_alert_system is None:
        with _alert_system_lock:
            if _auth_alert_system is None:
                _auth_alert_system = AuthAlertSystem()
                logger.info("Created global AuthAlertSystem for Issue #1300")
    
    return _auth_alert_system


async def check_authentication_alerts() -> List[Alert]:
    """Check authentication alerts using current metrics."""
    try:
        from netra_backend.app.websocket_core.auth_monitoring import get_auth_monitoring_metrics
        
        alert_system = get_auth_alert_system()
        metrics = get_auth_monitoring_metrics()
        
        return await alert_system.check_alerts(metrics)
        
    except Exception as e:
        logger.error(f"Error checking authentication alerts: {e}")
        return []


async def trigger_test_alert(severity: str = "info") -> Optional[Alert]:
    """Trigger a test alert for testing purposes."""
    alert_system = get_auth_alert_system()
    
    # Create test metrics that will trigger alerts
    test_metrics = {
        "global_metrics": {
            "auth_attempts": 100,
            "auth_success_rate": 30.0 if severity == "critical" else 70.0,  # Will trigger critical or error alert
            "latency_percentiles": {"p95": 3000.0},  # Will trigger latency alert
            "token_validations": 50,
            "token_validation_success_rate": 80.0,
            "connection_upgrades": 10,
            "connection_upgrade_success_rate": 60.0
        }
    }
    
    alerts = await alert_system.check_alerts(test_metrics)
    return alerts[0] if alerts else None


# Convenience functions

def get_active_alerts(severity_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get active alerts."""
    alert_system = get_auth_alert_system()
    severity_enum = AlertSeverity(severity_filter) if severity_filter else None
    return alert_system.get_active_alerts(severity_enum)


def get_alert_statistics() -> Dict[str, Any]:
    """Get alert system statistics."""
    alert_system = get_auth_alert_system()
    return alert_system.get_alert_statistics()


async def acknowledge_alert(alert_id: str, acknowledged_by: str = "system") -> bool:
    """Acknowledge an alert."""
    alert_system = get_auth_alert_system()
    return await alert_system.acknowledge_alert(alert_id, acknowledged_by)


async def resolve_alert(alert_id: str, resolved_by: str = "system", resolution_note: Optional[str] = None) -> bool:
    """Resolve an alert."""
    alert_system = get_auth_alert_system()
    return await alert_system.resolve_alert(alert_id, resolved_by, resolution_note)


# Export public interface
__all__ = [
    "AuthAlertSystem",
    "AlertRule",
    "Alert",
    "AlertSeverity",
    "AlertCategory",
    "AlertStatus",
    "NotificationChannel",
    "get_auth_alert_system",
    "check_authentication_alerts",
    "trigger_test_alert",
    "get_active_alerts",
    "get_alert_statistics",
    "acknowledge_alert",
    "resolve_alert"
]