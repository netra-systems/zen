"""
Compact alert management system using modular components.
Main orchestrator for alert generation, evaluation, and notification.
"""

import asyncio
import time
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Set

from app.logging_config import central_logger
from app.services.metrics.agent_metrics import AgentMetricsCollector, agent_metrics_collector
from .alert_models import (
    AlertRule, Alert, NotificationConfig, AlertLevel, NotificationChannel
)
from .alert_rules import create_default_alert_rules
from .alert_notifications import create_default_notification_configs
from .alert_evaluator import AlertEvaluator
from .alert_notifications import NotificationDeliveryManager

logger = central_logger.get_logger(__name__)


class CompactAlertManager:
    """Compact alert manager using modular components."""
    
    def __init__(
        self, 
        metrics_collector: Optional[AgentMetricsCollector] = None,
        evaluation_interval: int = 30
    ):
        self._setup_basic_config(metrics_collector, evaluation_interval)
        self._initialize_all_components()

    def _setup_basic_config(
        self, metrics_collector: Optional[AgentMetricsCollector], evaluation_interval: int
    ) -> None:
        """Setup basic configuration parameters."""
        self.metrics_collector = metrics_collector or agent_metrics_collector
        self.evaluation_interval = evaluation_interval

    def _initialize_all_components(self) -> None:
        """Initialize all manager components."""
        self._initialize_components()
        self._initialize_storage()
        self._initialize_configs()
        self._initialize_state()
        self._setup_defaults()
        
    def _initialize_components(self):
        """Initialize core alert manager components."""
        self.evaluator = AlertEvaluator(self.metrics_collector)
        self.notifier = NotificationDeliveryManager()
        
    def _initialize_storage(self):
        """Initialize alert storage containers."""
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history_size = 10000
        
    def _initialize_configs(self):
        """Initialize alert rules and configurations."""
        self.alert_rules: Dict[str, AlertRule] = {}
        self.notification_configs: Dict[NotificationChannel, NotificationConfig] = {}
        
    def _initialize_state(self):
        """Initialize monitoring and suppression state."""
        self.suppressed_rules: Set[str] = set()
        self.cooldown_tracker: Dict[str, datetime] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

    def _setup_defaults(self) -> None:
        """Setup default rules and configurations."""
        # Setup default alert rules
        default_rules = create_default_alert_rules()
        for rule_id, rule in default_rules.items():
            self.alert_rules[rule_id] = rule
        
        # Setup default notification configs
        self.notification_configs = create_default_notification_configs()

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
        await self._cancel_monitoring_task()
        logger.info("Alert monitoring stopped")

    async def _cancel_monitoring_task(self) -> None:
        """Cancel and wait for monitoring task completion."""
        if not self._monitoring_task:
            return
        
        self._monitoring_task.cancel()
        try:
            await self._monitoring_task
        except asyncio.CancelledError:
            pass

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop that evaluates alert rules."""
        while self._running:
            try:
                await self._execute_monitoring_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._handle_monitoring_error(e)

    async def _execute_monitoring_cycle(self) -> None:
        """Execute single monitoring cycle."""
        await self._evaluate_all_rules()
        await asyncio.sleep(self.evaluation_interval)

    async def _handle_monitoring_error(self, error: Exception) -> None:
        """Handle monitoring loop error."""
        logger.error(f"Error in alert monitoring loop: {error}")
        await asyncio.sleep(5)

    async def _evaluate_all_rules(self) -> None:
        """Evaluate all enabled alert rules."""
        for rule_id, rule in self.alert_rules.items():
            if await self._should_skip_rule(rule_id, rule):
                continue
            
            await self._evaluate_single_rule(rule_id, rule)

    async def _should_skip_rule(self, rule_id: str, rule: AlertRule) -> bool:
        """Check if rule should be skipped."""
        if not rule.enabled or rule_id in self.suppressed_rules:
            return True
        return await self._is_in_cooldown(rule_id)

    async def _evaluate_single_rule(self, rule_id: str, rule: AlertRule) -> None:
        """Evaluate a single alert rule."""
        try:
            alert = await self.evaluator.evaluate_rule(rule)
            if alert:
                await self._process_triggered_alert(alert, rule)
        except Exception as e:
            logger.error(f"Error evaluating rule {rule_id}: {e}")

    async def _process_triggered_alert(self, alert: Alert, rule: AlertRule) -> None:
        """Process a triggered alert."""
        self._store_alert(alert)
        await self._send_alert_notifications(alert, rule)
        self._set_rule_cooldown(rule.rule_id)
        logger.info(f"Alert triggered: {alert.title}")

    def _store_alert(self, alert: Alert) -> None:
        """Store alert in active and history collections."""
        self.active_alerts[alert.alert_id] = alert
        self.alert_history.append(alert)
        
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size:]

    async def _send_alert_notifications(self, alert: Alert, rule: AlertRule) -> None:
        """Send notifications for the alert."""
        await self.notifier.send_notifications(
            alert, rule.channels, self.notification_configs
        )

    def _set_rule_cooldown(self, rule_id: str) -> None:
        """Set cooldown timestamp for rule."""
        self.cooldown_tracker[rule_id] = datetime.now(UTC)

    async def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if rule is in cooldown period."""
        if rule_id not in self.cooldown_tracker:
            return False
        
        rule = self.alert_rules.get(rule_id)
        if not rule:
            return False
        
        return self._check_cooldown_time(rule_id, rule)

    def _check_cooldown_time(self, rule_id: str, rule: AlertRule) -> bool:
        """Check if cooldown time has elapsed."""
        last_triggered = self.cooldown_tracker[rule_id]
        cooldown_duration = timedelta(minutes=rule.cooldown_minutes)
        return datetime.now(UTC) - last_triggered < cooldown_duration

    # Rule management methods
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

    # Alert management methods
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
        return self._build_summary_data()

    def _build_summary_data(self) -> Dict[str, Any]:
        """Build alert summary data."""
        active_count = len(self.active_alerts)
        level_counts = self._calculate_level_counts()
        return self._build_alert_summary(active_count, level_counts)
        
    def _calculate_level_counts(self) -> Dict[str, int]:
        """Calculate count of alerts by level."""
        level_counts = {}
        for alert in self.active_alerts.values():
            level = alert.level.value
            level_counts[level] = level_counts.get(level, 0) + 1
        return level_counts
        
    def _build_alert_summary(self, active_count: int, level_counts: Dict[str, int]) -> Dict[str, Any]:
        """Build alert summary dictionary."""
        alert_stats = self._get_alert_stats(active_count, level_counts)
        rule_stats = self._get_rule_stats()
        channel_stats = self._get_channel_stats()
        return {**alert_stats, **rule_stats, **channel_stats}

    def _get_alert_stats(self, active_count: int, level_counts: Dict[str, int]) -> Dict[str, Any]:
        """Get alert statistics."""
        return {"active_alerts": active_count, "alerts_by_level": level_counts}

    def _get_rule_stats(self) -> Dict[str, Any]:
        """Get rule statistics."""
        enabled_count = len([r for r in self.alert_rules.values() if r.enabled])
        return {
            "suppressed_rules": len(self.suppressed_rules),
            "total_rules": len(self.alert_rules), "enabled_rules": enabled_count
        }

    def _get_channel_stats(self) -> Dict[str, Any]:
        """Get notification channel statistics."""
        enabled_channels = len([c for c in self.notification_configs.values() if c.enabled])
        return {"notification_channels": enabled_channels}

    # Notification handler registration
    def register_notification_handler(self, channel: NotificationChannel, handler) -> None:
        """Register custom notification handler."""
        self.notifier.register_notification_handler(channel, handler)


# Global alert manager instance
alert_manager = CompactAlertManager()