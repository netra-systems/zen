"""
WebSocket Automated Alerting System

This module implements a comprehensive automated alerting system for WebSocket
notification monitoring that detects, escalates, and resolves silent failures.

CRITICAL OBJECTIVES:
1. Zero silent failures - detect and alert on any notification that doesn't reach users
2. Proactive alerting - warn before users notice issues
3. Intelligent escalation - escalate based on severity and business impact
4. Automated remediation - trigger automated recovery actions when possible
5. Executive visibility - ensure leadership is informed of critical issues

ALERT CATEGORIES:
- CRITICAL: Silent failures, isolation violations, bridge failures
- ERROR: High failure rates, connection instability  
- WARNING: Performance degradation, capacity issues
- INFO: Normal operational events, recovery notifications

ESCALATION TIERS:
1. Operations Team: Immediate notification for all failures
2. Engineering Team: Complex technical issues requiring code changes
3. Management: Business impact and service degradation  
4. Executive: Critical system failures affecting multiple users
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.alert_types import Alert, AlertLevel, NotificationChannel
from netra_backend.app.monitoring.alert_notifications import NotificationDeliveryManager
from netra_backend.app.monitoring.websocket_notification_monitor import (
    WebSocketNotificationMonitor,
    HealthStatus,
    NotificationEventType
)
from netra_backend.app.monitoring.websocket_health_checks import WebSocketHealthChecker

logger = central_logger.get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels with business impact."""
    CRITICAL = "critical"      # Immediate business impact, user-facing failures
    HIGH = "high"              # Significant impact, potential user disruption  
    MEDIUM = "medium"          # Performance degradation, capacity concerns
    LOW = "low"                # Informational, proactive warnings


class EscalationTier(Enum):
    """Alert escalation tiers."""
    OPERATIONS = "operations"    # First responder operations team
    ENGINEERING = "engineering"  # Technical engineering team
    MANAGEMENT = "management"    # Service management and coordination
    EXECUTIVE = "executive"      # Leadership and business impact


@dataclass
class AlertRule:
    """Configuration for an automated alert rule."""
    rule_id: str
    name: str
    description: str
    
    # Trigger conditions
    trigger_condition: str
    threshold_value: Any
    evaluation_window_minutes: int = 5
    
    # Alert configuration
    alert_severity: AlertSeverity = AlertSeverity.MEDIUM
    escalation_tier: EscalationTier = EscalationTier.OPERATIONS
    
    # Escalation settings
    escalation_delay_minutes: int = 15
    max_escalation_tier: EscalationTier = EscalationTier.MANAGEMENT
    
    # Rate limiting
    cooldown_minutes: int = 5
    max_alerts_per_hour: int = 10
    
    # Recovery settings
    auto_resolve: bool = True
    resolve_condition: Optional[str] = None
    
    # Metadata
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "trigger_condition": self.trigger_condition,
            "threshold_value": self.threshold_value,
            "evaluation_window_minutes": self.evaluation_window_minutes,
            "alert_severity": self.alert_severity.value,
            "escalation_tier": self.escalation_tier.value,
            "escalation_delay_minutes": self.escalation_delay_minutes,
            "max_escalation_tier": self.max_escalation_tier.value,
            "cooldown_minutes": self.cooldown_minutes,
            "max_alerts_per_hour": self.max_alerts_per_hour,
            "auto_resolve": self.auto_resolve,
            "resolve_condition": self.resolve_condition,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ActiveAlert:
    """Represents an active alert in the system."""
    alert_id: str
    rule_id: str
    severity: AlertSeverity
    current_tier: EscalationTier
    
    # Alert details
    title: str
    message: str
    triggered_at: datetime
    
    # Escalation tracking
    escalation_count: int = 0
    last_escalated_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    # Resolution
    resolved_at: Optional[datetime] = None
    resolution_reason: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_active(self) -> bool:
        """Check if alert is still active."""
        return self.resolved_at is None
    
    @property
    def is_acknowledged(self) -> bool:
        """Check if alert has been acknowledged."""
        return self.acknowledged_at is not None
    
    @property
    def duration_minutes(self) -> float:
        """Get alert duration in minutes."""
        end_time = self.resolved_at or datetime.now(timezone.utc)
        return (end_time - self.triggered_at).total_seconds() / 60
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "current_tier": self.current_tier.value,
            "title": self.title,
            "message": self.message,
            "triggered_at": self.triggered_at.isoformat(),
            "escalation_count": self.escalation_count,
            "last_escalated_at": self.last_escalated_at.isoformat() if self.last_escalated_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_reason": self.resolution_reason,
            "duration_minutes": self.duration_minutes,
            "is_active": self.is_active,
            "is_acknowledged": self.is_acknowledged,
            "metadata": self.metadata
        }


class WebSocketAlertSystem:
    """
    Comprehensive automated alerting system for WebSocket notifications.
    
    Features:
    - Real-time alert rule evaluation
    - Intelligent escalation with business context
    - Automated remediation triggers
    - Executive dashboards and reporting
    - Integration with external notification systems
    """
    
    def __init__(self,
                 monitor: WebSocketNotificationMonitor,
                 health_checker: WebSocketHealthChecker,
                 notification_manager: NotificationDeliveryManager):
        """Initialize alert system."""
        self.monitor = monitor
        self.health_checker = health_checker
        self.notification_manager = notification_manager
        
        # Alert rules and state
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, ActiveAlert] = {}
        self.alert_history: List[ActiveAlert] = []
        
        # Rate limiting and cooldowns
        self.rule_last_triggered: Dict[str, datetime] = {}
        self.rule_alert_counts: Dict[str, List[datetime]] = {}
        
        # Background tasks
        self.evaluation_task: Optional[asyncio.Task] = None
        self.escalation_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.evaluation_interval = 30  # 30 seconds
        self.escalation_check_interval = 60  # 1 minute
        
        # Initialize default alert rules
        self._initialize_default_alert_rules()
        
        logger.info(" ALERT:  WebSocket Alert System initialized")
    
    def _initialize_default_alert_rules(self) -> None:
        """Initialize default alert rules for critical WebSocket monitoring."""
        
        # CRITICAL: Silent failures detected
        self.add_alert_rule(AlertRule(
            rule_id="silent_failures_critical",
            name="Silent Notification Failures",
            description="Critical alert when any silent failures are detected",
            trigger_condition="system_metrics.total_silent_failures > 0",
            threshold_value=0,
            evaluation_window_minutes=1,
            alert_severity=AlertSeverity.CRITICAL,
            escalation_tier=EscalationTier.OPERATIONS,
            escalation_delay_minutes=5,
            max_escalation_tier=EscalationTier.EXECUTIVE,
            cooldown_minutes=1,
            max_alerts_per_hour=60
        ))
        
        # CRITICAL: User isolation violations
        self.add_alert_rule(AlertRule(
            rule_id="isolation_violations_critical",
            name="User Isolation Violations",
            description="Critical alert when user isolation is compromised",
            trigger_condition="system_metrics.user_isolation_violations > 0",
            threshold_value=0,
            evaluation_window_minutes=1,
            alert_severity=AlertSeverity.CRITICAL,
            escalation_tier=EscalationTier.ENGINEERING,
            escalation_delay_minutes=10,
            max_escalation_tier=EscalationTier.EXECUTIVE,
            cooldown_minutes=5
        ))
        
        # CRITICAL: Bridge initialization failures
        self.add_alert_rule(AlertRule(
            rule_id="bridge_failures_critical", 
            name="WebSocket Bridge Initialization Failures",
            description="Critical alert when WebSocket bridge initialization fails",
            trigger_condition="system_metrics.failed_bridge_initializations > 0",
            threshold_value=0,
            evaluation_window_minutes=2,
            alert_severity=AlertSeverity.CRITICAL,
            escalation_tier=EscalationTier.ENGINEERING,
            escalation_delay_minutes=10,
            max_escalation_tier=EscalationTier.MANAGEMENT
        ))
        
        # HIGH: Low notification success rate
        self.add_alert_rule(AlertRule(
            rule_id="low_success_rate_high",
            name="Low Notification Success Rate", 
            description="Alert when notification success rate drops below 95%",
            trigger_condition="system_metrics.overall_success_rate < 0.95",
            threshold_value=0.95,
            evaluation_window_minutes=10,
            alert_severity=AlertSeverity.HIGH,
            escalation_tier=EscalationTier.OPERATIONS,
            escalation_delay_minutes=20,
            max_escalation_tier=EscalationTier.MANAGEMENT
        ))
        
        # HIGH: Very low notification success rate 
        self.add_alert_rule(AlertRule(
            rule_id="very_low_success_rate_critical",
            name="Very Low Notification Success Rate",
            description="Critical alert when success rate drops below 90%", 
            trigger_condition="system_metrics.overall_success_rate < 0.90",
            threshold_value=0.90,
            evaluation_window_minutes=5,
            alert_severity=AlertSeverity.CRITICAL,
            escalation_tier=EscalationTier.OPERATIONS,
            escalation_delay_minutes=10,
            max_escalation_tier=EscalationTier.EXECUTIVE
        ))
        
        # MEDIUM: High notification latency
        self.add_alert_rule(AlertRule(
            rule_id="high_latency_medium",
            name="High Notification Latency",
            description="Alert when notification delivery latency exceeds 2 seconds",
            trigger_condition="system_metrics.avg_notification_delivery_time_ms > 2000",
            threshold_value=2000,
            evaluation_window_minutes=15,
            alert_severity=AlertSeverity.MEDIUM,
            escalation_tier=EscalationTier.OPERATIONS,
            escalation_delay_minutes=30
        ))
        
        # CRITICAL: Very high notification latency
        self.add_alert_rule(AlertRule(
            rule_id="very_high_latency_critical",
            name="Very High Notification Latency",
            description="Critical alert when latency exceeds 10 seconds",
            trigger_condition="system_metrics.avg_notification_delivery_time_ms > 10000", 
            threshold_value=10000,
            evaluation_window_minutes=5,
            alert_severity=AlertSeverity.CRITICAL,
            escalation_tier=EscalationTier.OPERATIONS,
            escalation_delay_minutes=10,
            max_escalation_tier=EscalationTier.MANAGEMENT
        ))
        
        # MEDIUM: High connection drop rate
        self.add_alert_rule(AlertRule(
            rule_id="connection_drops_medium",
            name="High Connection Drop Rate",
            description="Alert when connection drops exceed normal rates",
            trigger_condition="connection_drop_rate > 0.10",
            threshold_value=0.10,
            evaluation_window_minutes=20,
            alert_severity=AlertSeverity.MEDIUM,
            escalation_tier=EscalationTier.OPERATIONS
        ))
        
        # LOW: No active connections
        self.add_alert_rule(AlertRule(
            rule_id="no_connections_high",
            name="No Active WebSocket Connections",
            description="Alert when no active WebSocket connections exist",
            trigger_condition="system_metrics.active_connections == 0",
            threshold_value=0,
            evaluation_window_minutes=5,
            alert_severity=AlertSeverity.HIGH,
            escalation_tier=EscalationTier.OPERATIONS,
            escalation_delay_minutes=15
        ))
        
        # MEDIUM: Memory leak detection
        self.add_alert_rule(AlertRule(
            rule_id="memory_leak_medium",
            name="Memory Leak Detected",
            description="Alert when memory leaks are detected in WebSocket system",
            trigger_condition="system_metrics.memory_leaks_detected > 0",
            threshold_value=0,
            evaluation_window_minutes=30,
            alert_severity=AlertSeverity.MEDIUM,
            escalation_tier=EscalationTier.ENGINEERING
        ))
        
        logger.info(f" ALERT:  Initialized {len(self.alert_rules)} default alert rules")
    
    async def start_alerting(self) -> None:
        """Start automated alerting system."""
        if not self.evaluation_task:
            self.evaluation_task = asyncio.create_task(self._alert_evaluation_loop())
            logger.info(" ALERT:  Alert evaluation started")
        
        if not self.escalation_task:
            self.escalation_task = asyncio.create_task(self._escalation_loop())
            logger.info(" ALERT:  Alert escalation started")
    
    async def stop_alerting(self) -> None:
        """Stop automated alerting system."""
        if self.evaluation_task:
            self.evaluation_task.cancel()
            try:
                await self.evaluation_task
            except asyncio.CancelledError:
                pass
            self.evaluation_task = None
        
        if self.escalation_task:
            self.escalation_task.cancel()
            try:
                await self.escalation_task
            except asyncio.CancelledError:
                pass
            self.escalation_task = None
        
        logger.info(" ALERT:  Alert system stopped")
    
    async def _alert_evaluation_loop(self) -> None:
        """Main alert evaluation loop."""
        try:
            while True:
                await self._evaluate_all_alert_rules()
                await asyncio.sleep(self.evaluation_interval)
                
        except asyncio.CancelledError:
            logger.info(" ALERT:  Alert evaluation loop cancelled")
            raise
        except Exception as e:
            logger.error(f" ALERT:  Alert evaluation loop error: {e}", exc_info=True)
            await asyncio.sleep(5)
    
    async def _escalation_loop(self) -> None:
        """Alert escalation management loop."""
        try:
            while True:
                await self._check_alert_escalations()
                await self._check_alert_resolutions()
                await asyncio.sleep(self.escalation_check_interval)
                
        except asyncio.CancelledError:
            logger.info(" ALERT:  Escalation loop cancelled")
            raise
        except Exception as e:
            logger.error(f" ALERT:  Escalation loop error: {e}", exc_info=True)
            await asyncio.sleep(5)
    
    async def _evaluate_all_alert_rules(self) -> None:
        """Evaluate all enabled alert rules."""
        system_metrics = self.monitor.system_metrics
        health_summary = self.health_checker.get_health_summary()
        
        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue
            
            try:
                await self._evaluate_alert_rule(rule, system_metrics, health_summary)
            except Exception as e:
                logger.error(f" ALERT:  Error evaluating alert rule {rule.rule_id}: {e}")
    
    async def _evaluate_alert_rule(self, rule: AlertRule, system_metrics: Any, health_summary: Dict[str, Any]) -> None:
        """Evaluate a single alert rule."""
        # Check rate limiting
        if not self._check_rule_rate_limit(rule):
            return
        
        # Evaluate condition
        triggered = await self._evaluate_condition(rule, system_metrics, health_summary)
        
        if triggered:
            await self._trigger_alert(rule, system_metrics, health_summary)
        else:
            # Check for auto-resolution
            await self._check_rule_resolution(rule, system_metrics, health_summary)
    
    async def _evaluate_condition(self, rule: AlertRule, system_metrics: Any, health_summary: Dict[str, Any]) -> bool:
        """Evaluate if alert rule condition is met."""
        condition = rule.trigger_condition
        
        try:
            # Create evaluation context
            eval_context = {
                "system_metrics": system_metrics,
                "health_summary": health_summary,
            }
            
            # Handle special conditions
            if condition == "connection_drop_rate > 0.10":
                # Calculate connection drop rate
                if system_metrics.total_reconnections > 0:
                    drop_rate = system_metrics.total_connection_drops / system_metrics.total_reconnections
                    return drop_rate > 0.10
                return False
            
            # Evaluate basic system metrics conditions
            if condition.startswith("system_metrics."):
                metric_path = condition.split(" ")[0].replace("system_metrics.", "")
                metric_value = getattr(system_metrics, metric_path, None)
                
                if metric_value is None:
                    return False
                
                # Parse condition operator and threshold
                if " > " in condition:
                    threshold = float(condition.split(" > ")[1])
                    return metric_value > threshold
                elif " < " in condition:
                    threshold = float(condition.split(" < ")[1])
                    return metric_value < threshold  
                elif " == " in condition:
                    threshold = float(condition.split(" == ")[1])
                    return metric_value == threshold
                elif " >= " in condition:
                    threshold = float(condition.split(" >= ")[1])
                    return metric_value >= threshold
                elif " <= " in condition:
                    threshold = float(condition.split(" <= ")[1])
                    return metric_value <= threshold
            
            return False
            
        except Exception as e:
            logger.error(f" ALERT:  Error evaluating condition '{condition}': {e}")
            return False
    
    async def _trigger_alert(self, rule: AlertRule, system_metrics: Any, health_summary: Dict[str, Any]) -> None:
        """Trigger an alert based on rule."""
        alert_id = f"{rule.rule_id}_{int(time.time())}"
        
        # Create alert message
        alert_title = f"WebSocket Alert: {rule.name}"
        alert_message = self._format_alert_message(rule, system_metrics, health_summary)
        
        # Create active alert
        active_alert = ActiveAlert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            severity=rule.alert_severity,
            current_tier=rule.escalation_tier,
            title=alert_title,
            message=alert_message,
            triggered_at=datetime.now(timezone.utc),
            metadata={
                "rule_name": rule.name,
                "trigger_condition": rule.trigger_condition,
                "threshold_value": rule.threshold_value,
                "system_metrics": system_metrics.to_dict(),
                "health_status": health_summary.get("overall_status")
            }
        )
        
        self.active_alerts[alert_id] = active_alert
        
        # Send initial alert
        await self._send_alert_notification(active_alert, rule)
        
        # Update rate limiting
        self._update_rule_rate_limit(rule)
        
        logger.critical(f" ALERT:  ALERT TRIGGERED: {rule.name} (ID: {alert_id})")
    
    def _format_alert_message(self, rule: AlertRule, system_metrics: Any, health_summary: Dict[str, Any]) -> str:
        """Format alert message with context."""
        message_parts = [
            f"Alert: {rule.name}",
            f"Description: {rule.description}",
            f"Severity: {rule.alert_severity.value.upper()}",
        ]
        
        # Add specific metrics based on rule type
        if "silent_failures" in rule.rule_id:
            silent_count = system_metrics.total_silent_failures
            message_parts.append(f"Silent failures detected: {silent_count}")
            message_parts.append("CRITICAL: Users are not receiving notifications without error indication")
            
        elif "isolation_violations" in rule.rule_id:
            violations = system_metrics.user_isolation_violations
            message_parts.append(f"User isolation violations: {violations}")
            message_parts.append("CRITICAL: User notifications may be sent to wrong recipients")
            
        elif "bridge_failures" in rule.rule_id:
            failures = system_metrics.failed_bridge_initializations
            message_parts.append(f"Bridge initialization failures: {failures}")
            
        elif "success_rate" in rule.rule_id:
            success_rate = system_metrics.overall_success_rate
            attempted = system_metrics.total_notifications_attempted
            delivered = system_metrics.total_notifications_delivered
            failed = system_metrics.total_notifications_failed
            message_parts.extend([
                f"Success rate: {success_rate:.3f} ({success_rate*100:.1f}%)",
                f"Attempted: {attempted}, Delivered: {delivered}, Failed: {failed}"
            ])
            
        elif "latency" in rule.rule_id:
            avg_latency = system_metrics.avg_notification_delivery_time_ms
            message_parts.append(f"Average notification latency: {avg_latency:.1f}ms")
            
        elif "connections" in rule.rule_id:
            active_connections = system_metrics.active_connections
            message_parts.append(f"Active connections: {active_connections}")
        
        # Add system health context
        overall_status = health_summary.get("overall_status", "unknown")
        message_parts.append(f"System health: {overall_status}")
        
        return " | ".join(message_parts)
    
    async def _send_alert_notification(self, active_alert: ActiveAlert, rule: AlertRule) -> None:
        """Send alert notification through configured channels."""
        # Map alert severity to notification level
        if active_alert.severity == AlertSeverity.CRITICAL:
            alert_level = AlertLevel.CRITICAL
        elif active_alert.severity == AlertSeverity.HIGH:
            alert_level = AlertLevel.ERROR
        elif active_alert.severity == AlertSeverity.MEDIUM:
            alert_level = AlertLevel.WARNING
        else:
            alert_level = AlertLevel.INFO
        
        # Create alert for notification system
        alert = Alert(
            title=active_alert.title,
            message=active_alert.message,
            level=alert_level,
            component="websocket_alert_system",
            agent_name="AlertManager",
            metadata={
                "alert_id": active_alert.alert_id,
                "rule_id": active_alert.rule_id,
                "severity": active_alert.severity.value,
                "escalation_tier": active_alert.current_tier.value,
                "escalation_count": active_alert.escalation_count,
                **active_alert.metadata
            }
        )
        
        # Send through configured channels
        channels = self._get_notification_channels_for_tier(active_alert.current_tier)
        try:
            await self.notification_manager.deliver_notifications(alert, channels, {})
            logger.info(f" ALERT:  Alert notification sent: {active_alert.alert_id}")
        except Exception as e:
            logger.error(f" ALERT:  Failed to send alert notification: {e}")
    
    def _get_notification_channels_for_tier(self, tier: EscalationTier) -> List[NotificationChannel]:
        """Get notification channels for escalation tier."""
        base_channels = [NotificationChannel.LOG, NotificationChannel.DATABASE]
        
        if tier == EscalationTier.OPERATIONS:
            return base_channels + [NotificationChannel.SLACK]
        elif tier == EscalationTier.ENGINEERING:
            return base_channels + [NotificationChannel.SLACK, NotificationChannel.EMAIL]
        elif tier in [EscalationTier.MANAGEMENT, EscalationTier.EXECUTIVE]:
            return base_channels + [NotificationChannel.EMAIL, NotificationChannel.WEBHOOK]
        
        return base_channels
    
    async def _check_alert_escalations(self) -> None:
        """Check and process alert escalations."""
        now = datetime.now(timezone.utc)
        
        for alert in list(self.active_alerts.values()):
            if not alert.is_active or alert.is_acknowledged:
                continue
            
            rule = self.alert_rules.get(alert.rule_id)
            if not rule:
                continue
            
            # Check if escalation is due
            minutes_since_trigger = (now - alert.triggered_at).total_seconds() / 60
            minutes_since_last_escalation = 0
            
            if alert.last_escalated_at:
                minutes_since_last_escalation = (now - alert.last_escalated_at).total_seconds() / 60
                escalation_due = minutes_since_last_escalation >= rule.escalation_delay_minutes
            else:
                escalation_due = minutes_since_trigger >= rule.escalation_delay_minutes
            
            if escalation_due and alert.current_tier != rule.max_escalation_tier:
                await self._escalate_alert(alert, rule)
    
    async def _escalate_alert(self, alert: ActiveAlert, rule: AlertRule) -> None:
        """Escalate alert to next tier."""
        # Determine next escalation tier
        current_tier_order = {
            EscalationTier.OPERATIONS: 0,
            EscalationTier.ENGINEERING: 1, 
            EscalationTier.MANAGEMENT: 2,
            EscalationTier.EXECUTIVE: 3
        }
        
        current_order = current_tier_order[alert.current_tier]
        max_order = current_tier_order[rule.max_escalation_tier]
        
        if current_order >= max_order:
            return
        
        # Find next tier
        next_tier = None
        for tier, order in current_tier_order.items():
            if order == current_order + 1:
                next_tier = tier
                break
        
        if not next_tier:
            return
        
        # Update alert
        alert.current_tier = next_tier
        alert.escalation_count += 1
        alert.last_escalated_at = datetime.now(timezone.utc)
        
        # Update alert message for escalation
        escalation_message = f"ESCALATED TO {next_tier.value.upper()}: {alert.message}"
        escalated_alert = ActiveAlert(
            alert_id=f"{alert.alert_id}_escalation_{alert.escalation_count}",
            rule_id=alert.rule_id,
            severity=alert.severity,
            current_tier=next_tier,
            title=f"[ESCALATED] {alert.title}",
            message=escalation_message,
            triggered_at=alert.triggered_at,
            escalation_count=alert.escalation_count,
            metadata={
                **alert.metadata,
                "escalated_from": alert.current_tier.value,
                "escalation_reason": "Unresolved after escalation delay",
                "original_alert_id": alert.alert_id
            }
        )
        
        # Send escalation notification
        await self._send_alert_notification(escalated_alert, rule)
        
        logger.critical(f" ALERT:  ALERT ESCALATED: {alert.alert_id} -> {next_tier.value.upper()}")
    
    async def _check_alert_resolutions(self) -> None:
        """Check for automatic alert resolutions."""
        for alert_id, alert in list(self.active_alerts.items()):
            if not alert.is_active:
                continue
            
            rule = self.alert_rules.get(alert.rule_id)
            if not rule or not rule.auto_resolve:
                continue
            
            # Check if resolution condition is met
            if await self._check_resolution_condition(alert, rule):
                await self._resolve_alert(alert_id, "Condition resolved automatically")
    
    async def _check_resolution_condition(self, alert: ActiveAlert, rule: AlertRule) -> bool:
        """Check if alert resolution condition is met."""
        if not rule.resolve_condition:
            # Use inverse of trigger condition
            system_metrics = self.monitor.system_metrics
            health_summary = self.health_checker.get_health_summary()
            
            # For most rules, resolution means the condition is no longer true
            return not await self._evaluate_condition(rule, system_metrics, health_summary)
        
        # TODO: Implement custom resolution conditions
        return False
    
    async def _resolve_alert(self, alert_id: str, reason: str) -> None:
        """Resolve an active alert."""
        alert = self.active_alerts.get(alert_id)
        if not alert or not alert.is_active:
            return
        
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolution_reason = reason
        
        # Move to history
        self.alert_history.append(alert)
        del self.active_alerts[alert_id]
        
        # Send resolution notification
        await self._send_resolution_notification(alert)
        
        logger.info(f" ALERT:  ALERT RESOLVED: {alert_id} - {reason}")
    
    async def _send_resolution_notification(self, alert: ActiveAlert) -> None:
        """Send alert resolution notification."""
        resolution_alert = Alert(
            title=f"[RESOLVED] {alert.title}",
            message=f"Alert resolved: {alert.resolution_reason} | Duration: {alert.duration_minutes:.1f} minutes",
            level=AlertLevel.INFO,
            component="websocket_alert_system",
            agent_name="AlertManager",
            metadata={
                "alert_id": alert.alert_id,
                "rule_id": alert.rule_id,
                "resolution_reason": alert.resolution_reason,
                "duration_minutes": alert.duration_minutes,
                "escalation_count": alert.escalation_count
            }
        )
        
        channels = [NotificationChannel.LOG, NotificationChannel.DATABASE]
        try:
            await self.notification_manager.deliver_notifications(resolution_alert, channels, {})
        except Exception as e:
            logger.error(f"Failed to send resolution notification: {e}")
    
    # Rate limiting methods
    
    def _check_rule_rate_limit(self, rule: AlertRule) -> bool:
        """Check if rule is within rate limits."""
        now = datetime.now(timezone.utc)
        
        # Check cooldown
        last_triggered = self.rule_last_triggered.get(rule.rule_id)
        if last_triggered:
            minutes_since_last = (now - last_triggered).total_seconds() / 60
            if minutes_since_last < rule.cooldown_minutes:
                return False
        
        # Check hourly limit
        hour_ago = now - timedelta(hours=1)
        alerts_this_hour = self.rule_alert_counts.get(rule.rule_id, [])
        alerts_this_hour = [t for t in alerts_this_hour if t > hour_ago]
        
        if len(alerts_this_hour) >= rule.max_alerts_per_hour:
            return False
        
        return True
    
    def _update_rule_rate_limit(self, rule: AlertRule) -> None:
        """Update rate limiting counters for rule."""
        now = datetime.now(timezone.utc)
        
        self.rule_last_triggered[rule.rule_id] = now
        
        if rule.rule_id not in self.rule_alert_counts:
            self.rule_alert_counts[rule.rule_id] = []
        
        self.rule_alert_counts[rule.rule_id].append(now)
        
        # Clean up old entries
        hour_ago = now - timedelta(hours=1)
        self.rule_alert_counts[rule.rule_id] = [
            t for t in self.rule_alert_counts[rule.rule_id] if t > hour_ago
        ]
    
    # Rule management
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add new alert rule."""
        self.alert_rules[rule.rule_id] = rule
        logger.info(f" ALERT:  Added alert rule: {rule.name} ({rule.rule_id})")
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove alert rule."""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info(f" ALERT:  Removed alert rule: {rule_id}")
            return True
        return False
    
    def update_alert_rule(self, rule_id: str, updated_rule: AlertRule) -> bool:
        """Update existing alert rule."""
        if rule_id in self.alert_rules:
            self.alert_rules[rule_id] = updated_rule
            logger.info(f" ALERT:  Updated alert rule: {rule_id}")
            return True
        return False
    
    def enable_alert_rule(self, rule_id: str) -> bool:
        """Enable alert rule."""
        rule = self.alert_rules.get(rule_id)
        if rule:
            rule.enabled = True
            logger.info(f" ALERT:  Enabled alert rule: {rule_id}")
            return True
        return False
    
    def disable_alert_rule(self, rule_id: str) -> bool:
        """Disable alert rule."""
        rule = self.alert_rules.get(rule_id)
        if rule:
            rule.enabled = False
            logger.info(f" ALERT:  Disabled alert rule: {rule_id}")
            return True
        return False
    
    # Alert management
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an active alert."""
        alert = self.active_alerts.get(alert_id)
        if not alert or not alert.is_active:
            return False
        
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = acknowledged_by
        
        logger.info(f" ALERT:  Alert acknowledged: {alert_id} by {acknowledged_by}")
        return True
    
    async def resolve_alert_manually(self, alert_id: str, resolved_by: str, reason: str) -> bool:
        """Manually resolve an alert."""
        alert = self.active_alerts.get(alert_id)
        if not alert or not alert.is_active:
            return False
        
        resolution_reason = f"Manually resolved by {resolved_by}: {reason}"
        await self._resolve_alert(alert_id, resolution_reason)
        return True
    
    # Reporting and analytics
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get comprehensive alert system summary."""
        now = datetime.now(timezone.utc)
        
        # Count alerts by severity
        severity_counts = {severity.value: 0 for severity in AlertSeverity}
        tier_counts = {tier.value: 0 for tier in EscalationTier}
        
        for alert in self.active_alerts.values():
            severity_counts[alert.severity.value] += 1
            tier_counts[alert.current_tier.value] += 1
        
        # Calculate metrics for last 24 hours
        day_ago = now - timedelta(hours=24)
        recent_history = [a for a in self.alert_history if a.triggered_at > day_ago]
        
        return {
            "active_alerts_count": len(self.active_alerts),
            "active_alerts_by_severity": severity_counts,
            "active_alerts_by_tier": tier_counts,
            "alert_rules_count": len(self.alert_rules),
            "enabled_rules_count": sum(1 for r in self.alert_rules.values() if r.enabled),
            "alerts_last_24h": len(recent_history),
            "avg_resolution_time_minutes": self._calculate_avg_resolution_time(recent_history),
            "escalation_rate": self._calculate_escalation_rate(recent_history),
            "auto_resolution_rate": self._calculate_auto_resolution_rate(recent_history),
            "timestamp": now.isoformat(),
            "monitoring_active": self.evaluation_task is not None and not self.evaluation_task.done()
        }
    
    def _calculate_avg_resolution_time(self, alerts: List[ActiveAlert]) -> float:
        """Calculate average resolution time."""
        resolved_alerts = [a for a in alerts if a.resolved_at]
        if not resolved_alerts:
            return 0.0
        
        total_time = sum(a.duration_minutes for a in resolved_alerts)
        return total_time / len(resolved_alerts)
    
    def _calculate_escalation_rate(self, alerts: List[ActiveAlert]) -> float:
        """Calculate escalation rate."""
        if not alerts:
            return 0.0
        
        escalated_alerts = sum(1 for a in alerts if a.escalation_count > 0)
        return escalated_alerts / len(alerts)
    
    def _calculate_auto_resolution_rate(self, alerts: List[ActiveAlert]) -> float:
        """Calculate automatic resolution rate."""
        resolved_alerts = [a for a in alerts if a.resolved_at]
        if not resolved_alerts:
            return 0.0
        
        auto_resolved = sum(1 for a in resolved_alerts if "automatically" in (a.resolution_reason or ""))
        return auto_resolved / len(resolved_alerts)
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of all active alerts."""
        return [alert.to_dict() for alert in self.active_alerts.values()]
    
    def get_alert_rules(self) -> List[Dict[str, Any]]:
        """Get list of all alert rules."""
        return [rule.to_dict() for rule in self.alert_rules.values()]
    
    def get_alert_history(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_alerts = [a for a in self.alert_history if a.triggered_at > cutoff_time]
        recent_alerts.sort(key=lambda a: a.triggered_at, reverse=True)
        return [alert.to_dict() for alert in recent_alerts[:limit]]


# Global alert system instance
_websocket_alert_system: Optional[WebSocketAlertSystem] = None


def get_websocket_alert_system() -> WebSocketAlertSystem:
    """Get or create the global WebSocket alert system."""
    global _websocket_alert_system
    if _websocket_alert_system is None:
        from netra_backend.app.monitoring.websocket_notification_monitor import get_websocket_notification_monitor
        from netra_backend.app.monitoring.websocket_health_checks import get_websocket_health_checker
        from netra_backend.app.monitoring.alert_notifications import NotificationDeliveryManager
        
        monitor = get_websocket_notification_monitor()
        health_checker = get_websocket_health_checker()
        notification_manager = NotificationDeliveryManager()
        
        _websocket_alert_system = WebSocketAlertSystem(monitor, health_checker, notification_manager)
    
    return _websocket_alert_system


async def start_websocket_alerting() -> None:
    """Start global WebSocket alerting system."""
    alert_system = get_websocket_alert_system()
    await alert_system.start_alerting()
    logger.info(" ALERT:  Global WebSocket alerting started")


async def stop_websocket_alerting() -> None:
    """Stop global WebSocket alerting system."""
    global _websocket_alert_system
    if _websocket_alert_system:
        await _websocket_alert_system.stop_alerting()
        logger.info(" ALERT:  Global WebSocket alerting stopped")


async def trigger_emergency_alert(title: str, message: str, severity: AlertSeverity = AlertSeverity.CRITICAL) -> None:
    """Trigger an emergency alert outside of normal rule evaluation."""
    alert_system = get_websocket_alert_system()
    
    # Create emergency rule
    emergency_rule = AlertRule(
        rule_id=f"emergency_{int(time.time())}",
        name="Emergency Alert",
        description=title,
        trigger_condition="manual_trigger",
        threshold_value=None,
        alert_severity=severity,
        escalation_tier=EscalationTier.OPERATIONS,
        max_escalation_tier=EscalationTier.EXECUTIVE,
        cooldown_minutes=0
    )
    
    # Trigger immediately
    await alert_system._trigger_alert(emergency_rule, alert_system.monitor.system_metrics, {})
    
    logger.critical(f" ALERT:  EMERGENCY ALERT TRIGGERED: {title}")