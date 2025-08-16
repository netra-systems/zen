"""Core alert manager functionality.

Main coordination logic for alert monitoring, evaluation, and lifecycle management.
Orchestrates rule evaluation, alert creation, and notification delivery.
"""

import asyncio
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, Set

from .alert_types import Alert, AlertRule, AlertLevel, NotificationChannel, NotificationConfig
from .alert_rules import create_default_alert_rules, RuleEvaluator, CooldownManager
from .alert_notifications import create_default_notification_configs, NotificationDeliveryManager
from app.services.metrics.agent_metrics import AgentMetricsCollector, agent_metrics_collector
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AlertManager:
    """Manages alerts, notifications, and alert suppression."""
    
    def __init__(
        self, 
        metrics_collector: Optional[AgentMetricsCollector] = None,
        evaluation_interval: int = 30
    ):
        """Initialize alert manager."""
        self.metrics_collector = metrics_collector or agent_metrics_collector
        self.evaluation_interval = evaluation_interval
        
        # Alert storage
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history_size = 10000
        
        # Rules and configuration
        self.alert_rules: Dict[str, AlertRule] = create_default_alert_rules()
        self.notification_configs: Dict[NotificationChannel, NotificationConfig] = create_default_notification_configs()
        
        # Alert suppression
        self.suppressed_rules: Set[str] = set()
        
        # Monitoring state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Managers
        self.rule_evaluator = RuleEvaluator()
        self.cooldown_manager = CooldownManager()
        self.notification_delivery = NotificationDeliveryManager()

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
        if self.cooldown_manager.is_in_cooldown(rule.rule_id, rule):
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
                return self.rule_evaluator.evaluate_system_condition(rule, metrics_data)
            else:
                return self.rule_evaluator.evaluate_agent_condition(rule, metrics_data)
        except Exception as e:
            logger.error(f"Error evaluating condition for rule {rule.rule_id}: {e}")
            return False

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
        await self.notification_delivery.deliver_notifications(
            alert, rule.channels, self.notification_configs
        )
        
        # Set cooldown
        self.cooldown_manager.set_cooldown(rule.rule_id)
        
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
            if self.rule_evaluator._check_agent_against_rule(rule, metrics, rule.threshold_value):
                value = self.rule_evaluator.get_metric_value_for_rule(rule.rule_id, metrics)
                return value, agent_name
        
        return None, None

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
        handler
    ) -> None:
        """Register custom notification handler for a channel."""
        self.notification_delivery.register_notification_handler(channel, handler)
        logger.info(f"Registered notification handler for {channel.value}")


# Global alert manager instance
alert_manager = AlertManager()