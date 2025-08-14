"""
Alert management system for agent failures and system issues.
Handles alert generation, notification routing, and alert suppression.
"""

import asyncio
import time
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json

from app.logging_config import central_logger
from app.services.metrics.agent_metrics import (
    AgentMetricsCollector, AgentMetrics, FailureType, agent_metrics_collector
)

logger = central_logger.get_logger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """Available notification channels."""
    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    DATABASE = "database"


@dataclass
class AlertRule:
    """Configuration for an alert rule."""
    rule_id: str
    name: str
    description: str
    condition: str  # Python expression string
    level: AlertLevel
    threshold_value: float
    time_window_minutes: int = 5
    evaluation_interval_seconds: int = 30
    cooldown_minutes: int = 15
    channels: List[NotificationChannel] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert instance."""
    alert_id: str
    rule_id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    agent_name: Optional[str] = None
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationConfig:
    """Configuration for notification channels."""
    channel: NotificationChannel
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    rate_limit_per_hour: int = 100
    min_level: AlertLevel = AlertLevel.INFO


class AlertManager:
    """Manages alerts, notifications, and alert suppression."""
    
    def __init__(
        self, 
        metrics_collector: Optional[AgentMetricsCollector] = None,
        evaluation_interval: int = 30
    ):
        self.metrics_collector = metrics_collector or agent_metrics_collector
        self.evaluation_interval = evaluation_interval
        
        # Alert storage
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history_size = 10000
        
        # Rules and configuration
        self.alert_rules: Dict[str, AlertRule] = {}
        self.notification_configs: Dict[NotificationChannel, NotificationConfig] = {}
        
        # Alert suppression
        self.suppressed_rules: Set[str] = set()
        self.cooldown_tracker: Dict[str, datetime] = {}
        
        # Notification tracking
        self.notification_history: List[Dict[str, Any]] = []
        self.notification_rate_limits: Dict[NotificationChannel, List[datetime]] = {}
        
        # Monitoring state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Notification handlers
        self.notification_handlers: Dict[NotificationChannel, Callable] = {}
        
        # Initialize default rules and configurations
        self._setup_default_alert_rules()
        self._setup_default_notification_configs()

    def _setup_default_alert_rules(self) -> None:
        """Setup default alert rules for common scenarios."""
        default_rules = [
            AlertRule(
                rule_id="agent_high_error_rate",
                name="High Agent Error Rate",
                description="Agent error rate exceeds threshold",
                condition="error_rate > threshold_value",
                level=AlertLevel.ERROR,
                threshold_value=0.2,  # 20% error rate
                time_window_minutes=5,
                channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
            ),
            AlertRule(
                rule_id="agent_critical_error_rate",
                name="Critical Agent Error Rate",
                description="Agent error rate critically high",
                condition="error_rate > threshold_value",
                level=AlertLevel.CRITICAL,
                threshold_value=0.5,  # 50% error rate
                time_window_minutes=3,
                channels=[NotificationChannel.LOG, NotificationChannel.EMAIL, NotificationChannel.SLACK]
            ),
            AlertRule(
                rule_id="agent_timeout_spike",
                name="Agent Timeout Spike",
                description="High number of agent timeouts",
                condition="timeout_count > threshold_value",
                level=AlertLevel.WARNING,
                threshold_value=5,  # 5 timeouts in window
                time_window_minutes=5,
                channels=[NotificationChannel.LOG]
            ),
            AlertRule(
                rule_id="agent_avg_execution_time_high",
                name="High Agent Execution Time",
                description="Average execution time exceeds threshold",
                condition="avg_execution_time_ms > threshold_value",
                level=AlertLevel.WARNING,
                threshold_value=30000,  # 30 seconds
                time_window_minutes=10,
                channels=[NotificationChannel.LOG]
            ),
            AlertRule(
                rule_id="agent_validation_error_spike",
                name="Validation Error Spike",
                description="High number of validation errors",
                condition="validation_error_count > threshold_value",
                level=AlertLevel.ERROR,
                threshold_value=10,  # 10 validation errors
                time_window_minutes=5,
                channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
            ),
            AlertRule(
                rule_id="system_wide_failure_rate",
                name="System-wide High Failure Rate",
                description="Overall system failure rate is high",
                condition="system_error_rate > threshold_value",
                level=AlertLevel.CRITICAL,
                threshold_value=0.3,  # 30% system-wide error rate
                time_window_minutes=5,
                channels=[NotificationChannel.LOG, NotificationChannel.EMAIL, NotificationChannel.SLACK]
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.rule_id] = rule

    def _setup_default_notification_configs(self) -> None:
        """Setup default notification channel configurations."""
        self.notification_configs = {
            NotificationChannel.LOG: NotificationConfig(
                channel=NotificationChannel.LOG,
                enabled=True,
                rate_limit_per_hour=1000,
                min_level=AlertLevel.INFO
            ),
            NotificationChannel.EMAIL: NotificationConfig(
                channel=NotificationChannel.EMAIL,
                enabled=False,  # Disabled by default, needs configuration
                rate_limit_per_hour=20,
                min_level=AlertLevel.ERROR,
                config={"smtp_server": "", "recipients": []}
            ),
            NotificationChannel.SLACK: NotificationConfig(
                channel=NotificationChannel.SLACK,
                enabled=False,  # Disabled by default, needs configuration
                rate_limit_per_hour=50,
                min_level=AlertLevel.WARNING,
                config={"webhook_url": "", "channel": "#alerts"}
            ),
            NotificationChannel.WEBHOOK: NotificationConfig(
                channel=NotificationChannel.WEBHOOK,
                enabled=False,  # Disabled by default, needs configuration
                rate_limit_per_hour=100,
                min_level=AlertLevel.WARNING,
                config={"url": "", "headers": {}}
            ),
            NotificationChannel.DATABASE: NotificationConfig(
                channel=NotificationChannel.DATABASE,
                enabled=True,
                rate_limit_per_hour=500,
                min_level=AlertLevel.INFO
            )
        }

    async def start_monitoring(self) -> None:
        """Start alert monitoring loop."""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Alert monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop alert monitoring loop."""
        if not self._running:
            return
        
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Alert monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop that evaluates alert rules."""
        while self._running:
            try:
                await self._evaluate_all_rules()
                await asyncio.sleep(self.evaluation_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}")
                await asyncio.sleep(5)

    async def _evaluate_all_rules(self) -> None:
        """Evaluate all enabled alert rules."""
        for rule_id, rule in self.alert_rules.items():
            if not rule.enabled or rule_id in self.suppressed_rules:
                continue
            
            try:
                await self._evaluate_rule(rule)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule_id}: {e}")

    async def _evaluate_rule(self, rule: AlertRule) -> None:
        """Evaluate a specific alert rule."""
        # Check cooldown
        if await self._is_in_cooldown(rule.rule_id):
            return
        
        # Get relevant metrics
        metrics_data = await self._get_metrics_for_rule(rule)
        
        # Evaluate condition
        triggered = await self._evaluate_condition(rule, metrics_data)
        
        if triggered:
            await self._trigger_alert(rule, metrics_data)

    async def _get_metrics_for_rule(self, rule: AlertRule) -> Dict[str, Any]:
        """Get metrics data needed for rule evaluation."""
        if "system_wide" in rule.rule_id:
            return await self.metrics_collector.get_system_overview()
        
        # For agent-specific rules, get metrics for all agents
        all_metrics = self.metrics_collector.get_all_agent_metrics()
        return {"agent_metrics": all_metrics, "all_agents": list(all_metrics.keys())}

    async def _evaluate_condition(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> bool:
        """Evaluate rule condition against metrics data."""
        try:
            if "system_wide" in rule.rule_id:
                return self._evaluate_system_condition(rule, metrics_data)
            else:
                return self._evaluate_agent_condition(rule, metrics_data)
        except Exception as e:
            logger.error(f"Error evaluating condition for rule {rule.rule_id}: {e}")
            return False

    def _evaluate_system_condition(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> bool:
        """Evaluate system-wide condition."""
        threshold_value = rule.threshold_value
        
        if rule.rule_id == "system_wide_failure_rate":
            system_error_rate = metrics_data.get("system_error_rate", 0.0)
            return system_error_rate > threshold_value
        
        return False

    def _evaluate_agent_condition(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> bool:
        """Evaluate agent-specific condition."""
        agent_metrics = metrics_data.get("agent_metrics", {})
        threshold_value = rule.threshold_value
        
        # Check each agent
        for agent_name, metrics in agent_metrics.items():
            if self._check_agent_against_rule(rule, metrics, threshold_value):
                return True
        
        return False

    def _check_agent_against_rule(self, rule: AlertRule, metrics: AgentMetrics, threshold: float) -> bool:
        """Check if individual agent metrics trigger the rule."""
        rule_mapping = {
            "agent_high_error_rate": metrics.error_rate > threshold,
            "agent_critical_error_rate": metrics.error_rate > threshold,
            "agent_timeout_spike": metrics.timeout_count > threshold,
            "agent_avg_execution_time_high": metrics.avg_execution_time_ms > threshold,
            "agent_validation_error_spike": metrics.validation_error_count > threshold
        }
        
        return rule_mapping.get(rule.rule_id, False)

    async def _trigger_alert(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> None:
        """Trigger an alert for a rule."""
        alert = self._create_alert(rule, metrics_data)
        
        # Store alert
        self.active_alerts[alert.alert_id] = alert
        self.alert_history.append(alert)
        
        # Trim history if needed
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size:]
        
        # Send notifications
        await self._send_notifications(alert, rule)
        
        # Set cooldown
        self.cooldown_tracker[rule.rule_id] = datetime.now(UTC)
        
        logger.info(f"Alert triggered: {alert.title}")

    def _create_alert(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> Alert:
        """Create alert instance from rule and metrics."""
        alert_id = str(uuid.uuid4())
        
        # Extract relevant values for the alert
        current_value, agent_name = self._extract_alert_values(rule, metrics_data)
        
        return Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            level=rule.level,
            title=rule.name,
            message=self._generate_alert_message(rule, current_value, agent_name),
            timestamp=datetime.now(UTC),
            agent_name=agent_name,
            metric_name=rule.rule_id,
            current_value=current_value,
            threshold_value=rule.threshold_value,
            metadata={"rule_description": rule.description}
        )

    def _extract_alert_values(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> tuple:
        """Extract current value and agent name for alert."""
        if "system_wide" in rule.rule_id:
            if rule.rule_id == "system_wide_failure_rate":
                return metrics_data.get("system_error_rate", 0.0), None
        
        # For agent rules, find the agent that triggered the alert
        agent_metrics = metrics_data.get("agent_metrics", {})
        for agent_name, metrics in agent_metrics.items():
            if self._check_agent_against_rule(rule, metrics, rule.threshold_value):
                value = self._get_metric_value_for_rule(rule.rule_id, metrics)
                return value, agent_name
        
        return None, None

    def _get_metric_value_for_rule(self, rule_id: str, metrics: AgentMetrics) -> float:
        """Get specific metric value for rule."""
        mapping = {
            "agent_high_error_rate": metrics.error_rate,
            "agent_critical_error_rate": metrics.error_rate,
            "agent_timeout_spike": float(metrics.timeout_count),
            "agent_avg_execution_time_high": metrics.avg_execution_time_ms,
            "agent_validation_error_spike": float(metrics.validation_error_count)
        }
        return mapping.get(rule_id, 0.0)

    def _generate_alert_message(
        self, 
        rule: AlertRule, 
        current_value: Optional[float], 
        agent_name: Optional[str]
    ) -> str:
        """Generate human-readable alert message."""
        base_msg = rule.description
        
        if current_value is not None:
            if agent_name:
                base_msg += f" - Agent: {agent_name}, Current: {current_value:.3f}, Threshold: {rule.threshold_value}"
            else:
                base_msg += f" - Current: {current_value:.3f}, Threshold: {rule.threshold_value}"
        
        return base_msg

    async def _send_notifications(self, alert: Alert, rule: AlertRule) -> None:
        """Send notifications through configured channels."""
        for channel in rule.channels:
            config = self.notification_configs.get(channel)
            
            if not config or not config.enabled:
                continue
            
            # Check minimum level
            if alert.level.value < config.min_level.value:
                continue
            
            # Check rate limits
            if not await self._check_rate_limit(channel, config):
                continue
            
            try:
                await self._send_notification(alert, channel, config)
                self._track_notification(alert, channel)
            except Exception as e:
                logger.error(f"Failed to send notification via {channel.value}: {e}")

    async def _check_rate_limit(self, channel: NotificationChannel, config: NotificationConfig) -> bool:
        """Check if notification channel is within rate limits."""
        now = datetime.now(UTC)
        hour_ago = now - timedelta(hours=1)
        
        if channel not in self.notification_rate_limits:
            self.notification_rate_limits[channel] = []
        
        # Clean old entries
        self.notification_rate_limits[channel] = [
            ts for ts in self.notification_rate_limits[channel] if ts > hour_ago
        ]
        
        # Check limit
        if len(self.notification_rate_limits[channel]) >= config.rate_limit_per_hour:
            return False
        
        # Add current notification
        self.notification_rate_limits[channel].append(now)
        return True

    async def _send_notification(
        self, 
        alert: Alert, 
        channel: NotificationChannel, 
        config: NotificationConfig
    ) -> None:
        """Send notification through specific channel."""
        handler = self.notification_handlers.get(channel)
        
        if handler:
            await handler(alert, config)
        else:
            # Default handlers
            if channel == NotificationChannel.LOG:
                await self._send_log_notification(alert)
            elif channel == NotificationChannel.DATABASE:
                await self._send_database_notification(alert)
            # Other channels would need custom handlers

    async def _send_log_notification(self, alert: Alert) -> None:
        """Send notification to log."""
        log_level_map = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }
        
        log_func = log_level_map.get(alert.level, logger.info)
        log_func(f"ALERT [{alert.level.value.upper()}] {alert.title}: {alert.message}")

    async def _send_database_notification(self, alert: Alert) -> None:
        """Store alert in database (placeholder for actual implementation)."""
        # This would store the alert in the database
        # Implementation depends on the database schema
        logger.debug(f"Storing alert {alert.alert_id} in database")

    def _track_notification(self, alert: Alert, channel: NotificationChannel) -> None:
        """Track sent notification for audit purposes."""
        self.notification_history.append({
            "alert_id": alert.alert_id,
            "channel": channel.value,
            "timestamp": datetime.now(UTC),
            "level": alert.level.value
        })
        
        # Keep only recent history
        if len(self.notification_history) > 1000:
            self.notification_history = self.notification_history[-1000:]

    async def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if rule is in cooldown period."""
        if rule_id not in self.cooldown_tracker:
            return False
        
        rule = self.alert_rules.get(rule_id)
        if not rule:
            return False
        
        last_triggered = self.cooldown_tracker[rule_id]
        cooldown_duration = timedelta(minutes=rule.cooldown_minutes)
        
        return datetime.now(UTC) - last_triggered < cooldown_duration

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add or update alert rule."""
        self.alert_rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove alert rule."""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
            return True
        return False

    def suppress_rule(self, rule_id: str, reason: str = "") -> None:
        """Suppress an alert rule."""
        self.suppressed_rules.add(rule_id)
        logger.info(f"Suppressed alert rule {rule_id}: {reason}")

    def unsuppress_rule(self, rule_id: str) -> None:
        """Remove suppression from alert rule."""
        self.suppressed_rules.discard(rule_id)
        logger.info(f"Unsuppressed alert rule: {rule_id}")

    async def resolve_alert(self, alert_id: str, resolved_by: str = "system") -> bool:
        """Mark alert as resolved."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now(UTC)
            alert.metadata["resolved_by"] = resolved_by
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert {alert_id} resolved by {resolved_by}")
            return True
        
        return False

    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by level."""
        alerts = list(self.active_alerts.values())
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert system status."""
        active_count = len(self.active_alerts)
        level_counts = {}
        
        for alert in self.active_alerts.values():
            level = alert.level.value
            level_counts[level] = level_counts.get(level, 0) + 1
        
        return {
            "active_alerts": active_count,
            "alerts_by_level": level_counts,
            "suppressed_rules": len(self.suppressed_rules),
            "total_rules": len(self.alert_rules),
            "enabled_rules": len([r for r in self.alert_rules.values() if r.enabled]),
            "notification_channels": len([c for c in self.notification_configs.values() if c.enabled])
        }

    def register_notification_handler(
        self, 
        channel: NotificationChannel, 
        handler: Callable
    ) -> None:
        """Register custom notification handler for a channel."""
        self.notification_handlers[channel] = handler
        logger.info(f"Registered notification handler for {channel.value}")


# Global alert manager instance
alert_manager = AlertManager()