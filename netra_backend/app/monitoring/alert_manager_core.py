"""Core alert manager functionality.

Main coordination logic for alert monitoring, evaluation, and lifecycle management.
Orchestrates rule evaluation, alert creation, and notification delivery.
"""

import asyncio
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, Set

from netra_backend.app.monitoring.alert_types import Alert, AlertRule, AlertLevel, NotificationChannel, NotificationConfig
from netra_backend.app.monitoring.alert_rules import create_default_alert_rules, RuleEvaluator, CooldownManager
from netra_backend.app.monitoring.alert_notifications import create_default_notification_configs, NotificationDeliveryManager
from netra_backend.app.services.metrics.agent_metrics import AgentMetricsCollector, agent_metrics_collector
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AlertManager:
    """Manages alerts, notifications, and alert suppression."""
    
    def __init__(
        self, 
        metrics_collector: Optional[AgentMetricsCollector] = None,
        evaluation_interval: int = 30
    ):
        """Initialize alert manager."""
        self._init_core_components(metrics_collector, evaluation_interval)
        self._init_remaining_components()

    def _init_core_components(
        self, 
        metrics_collector: Optional[AgentMetricsCollector], 
        evaluation_interval: int
    ) -> None:
        """Initialize core components."""
        self.metrics_collector = metrics_collector or agent_metrics_collector
        self.evaluation_interval = evaluation_interval

    def _init_storage(self) -> None:
        """Initialize alert storage."""
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history_size = 10000

    def _init_configuration(self) -> None:
        """Initialize rules and notification configuration."""
        self.alert_rules: Dict[str, AlertRule] = create_default_alert_rules()
        notification_configs = create_default_notification_configs()
        self.notification_configs: Dict[NotificationChannel, NotificationConfig] = notification_configs
        self.suppressed_rules: Set[str] = set()

    def _init_state_and_managers(self) -> None:
        """Initialize monitoring state and managers."""
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        self.rule_evaluator = RuleEvaluator()
        self.cooldown_manager = CooldownManager()
        self.notification_delivery = NotificationDeliveryManager()

    def _init_remaining_components(self) -> None:
        """Initialize remaining components."""
        self._init_storage()
        self._init_configuration()
        self._init_state_and_managers()

    async def _do_monitoring_cycle(self) -> None:
        """Execute one monitoring cycle."""
        await self._evaluate_all_rules()
        await asyncio.sleep(self.evaluation_interval)

    async def _check_and_trigger_rule(self, rule: AlertRule) -> None:
        """Check rule condition and trigger if needed."""
        metrics_data = await self._get_metrics_for_rule(rule)
        triggered = await self._evaluate_condition(rule, metrics_data)
        
        if triggered:
            await self._trigger_alert(rule, metrics_data)

    def _format_agent_details(self, agent_name: str, current_value: float, threshold_value: float) -> str:
        """Format agent-specific metric details."""
        return f" - Agent: {agent_name}, Current: {current_value:.3f}, Threshold: {threshold_value}"

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
        """Cancel monitoring task safely."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop that evaluates alert rules."""
        while self._running:
            await self._execute_monitoring_iteration()

    async def _execute_monitoring_iteration(self) -> None:
        """Execute single monitoring iteration."""
        try:
            await self._do_monitoring_cycle()
        except asyncio.CancelledError:
            return
        except Exception as e:
            await self._handle_monitoring_error(e)

    async def _handle_monitoring_error(self, error: Exception) -> None:
        """Handle monitoring loop error."""
        logger.error(f"Error in alert monitoring loop: {error}")
        await asyncio.sleep(5)

    async def _evaluate_all_rules(self) -> None:
        """Evaluate all enabled alert rules."""
        for rule_id, rule in self.alert_rules.items():
            if self._should_skip_rule(rule, rule_id):
                continue
            
            await self._safely_evaluate_rule(rule, rule_id)

    def _should_skip_rule(self, rule: AlertRule, rule_id: str) -> bool:
        """Check if rule should be skipped."""
        return not rule.enabled or rule_id in self.suppressed_rules

    async def _safely_evaluate_rule(self, rule: AlertRule, rule_id: str) -> None:
        """Safely evaluate rule with error handling."""
        try:
            await self._evaluate_rule(rule)
        except Exception as e:
            logger.error(f"Error evaluating rule {rule_id}: {e}")

    async def _evaluate_rule(self, rule: AlertRule) -> None:
        """Evaluate a specific alert rule."""
        if self.cooldown_manager.is_in_cooldown(rule.rule_id, rule):
            return
        
        await self._check_and_trigger_rule(rule)

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
            return self._get_condition_result(rule, metrics_data)
        except Exception as e:
            logger.error(f"Error evaluating condition for rule {rule.rule_id}: {e}")
            return False

    def _get_condition_result(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> bool:
        """Get condition evaluation result."""
        if "system_wide" in rule.rule_id:
            return self.rule_evaluator.evaluate_system_condition(rule, metrics_data)
        else:
            return self.rule_evaluator.evaluate_agent_condition(rule, metrics_data)

    async def _trigger_alert(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> None:
        """Trigger an alert for a rule."""
        alert = self._create_alert(rule, metrics_data)
        self._store_alert(alert)
        await self._deliver_alert_notifications(alert, rule)
        self._set_alert_cooldown(rule.rule_id)
        logger.info(f"Alert triggered: {alert.title}")

    def _store_alert(self, alert: Alert) -> None:
        """Store alert in active and history collections."""
        self.active_alerts[alert.alert_id] = alert
        self.alert_history.append(alert)
        self._trim_alert_history()

    def _trim_alert_history(self) -> None:
        """Trim alert history to max size."""
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size:]

    async def _deliver_alert_notifications(self, alert: Alert, rule: AlertRule) -> None:
        """Deliver notifications for alert."""
        await self.notification_delivery.deliver_notifications(
            alert, rule.channels, self.notification_configs
        )

    def _set_alert_cooldown(self, rule_id: str) -> None:
        """Set cooldown for alert rule."""
        self.cooldown_manager.set_cooldown(rule_id)

    def _create_alert(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> Alert:
        """Create alert instance from rule and metrics."""
        alert_id = str(uuid.uuid4())
        current_value, agent_name = self._extract_alert_values(rule, metrics_data)
        message = self._generate_alert_message(rule, current_value, agent_name)
        
        return self._build_alert_instance(
            alert_id, rule, current_value, agent_name, message
        )

    def _build_alert_instance(
        self, 
        alert_id: str, 
        rule: AlertRule, 
        current_value: Optional[float], 
        agent_name: Optional[str], 
        message: str
    ) -> Alert:
        """Build alert instance with all required fields."""
        alert_data = self._prepare_alert_data(alert_id, rule, current_value, agent_name, message)
        return Alert(**alert_data)

    def _prepare_alert_data(
        self, alert_id: str, rule: AlertRule, current_value: Optional[float], agent_name: Optional[str], message: str
    ) -> Dict[str, Any]:
        """Prepare alert data dictionary for Alert constructor."""
        return {
            "alert_id": alert_id, "rule_id": rule.rule_id, "level": rule.level,
            "title": rule.name, "message": message, "timestamp": datetime.now(UTC),
            "agent_name": agent_name, "metric_name": rule.rule_id,
            "current_value": current_value, "threshold_value": rule.threshold_value,
            "metadata": self._create_alert_metadata(rule)
        }

    def _create_alert_metadata(self, rule: AlertRule) -> Dict[str, str]:
        """Create metadata for alert."""
        return {"rule_description": rule.description}

    def _extract_alert_values(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> tuple:
        """Extract current value and agent name for alert."""
        if "system_wide" in rule.rule_id:
            return self._extract_system_alert_values(rule, metrics_data)
        
        return self._extract_agent_alert_values(rule, metrics_data)

    def _extract_system_alert_values(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> tuple:
        """Extract alert values for system-wide rules."""
        if rule.rule_id == "system_wide_failure_rate":
            return metrics_data.get("system_error_rate", 0.0), None
        return None, None

    def _extract_agent_alert_values(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> tuple:
        """Extract alert values for agent-specific rules."""
        agent_metrics = metrics_data.get("agent_metrics", {})
        return self._find_matching_agent_values(rule, agent_metrics)

    def _find_matching_agent_values(self, rule: AlertRule, agent_metrics: Dict[str, Any]) -> tuple:
        """Find agent metrics that match the rule condition."""
        for agent_name, metrics in agent_metrics.items():
            if self._check_agent_rule_match(rule, metrics):
                value = self.rule_evaluator.get_metric_value_for_rule(rule.rule_id, metrics)
                return value, agent_name
        return None, None

    def _check_agent_rule_match(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """Check if agent metrics match rule condition."""
        return self.rule_evaluator._check_agent_against_rule(
            rule, metrics, rule.threshold_value
        )

    def _generate_alert_message(
        self, 
        rule: AlertRule, 
        current_value: Optional[float], 
        agent_name: Optional[str]
    ) -> str:
        """Generate human-readable alert message."""
        base_msg = rule.description
        return self._append_metric_details(base_msg, current_value, agent_name, rule)

    def _append_metric_details(
        self, 
        base_msg: str, 
        current_value: Optional[float], 
        agent_name: Optional[str], 
        rule: AlertRule
    ) -> str:
        """Append metric details to base message."""
        if current_value is not None:
            details = self._format_metric_details(current_value, agent_name, rule.threshold_value)
            return base_msg + details
        return base_msg

    def _format_metric_details(
        self, 
        current_value: float, 
        agent_name: Optional[str], 
        threshold_value: float
    ) -> str:
        """Format metric details for alert message."""
        if agent_name:
            return self._format_agent_details(agent_name, current_value, threshold_value)
        return f" - Current: {current_value:.3f}, Threshold: {threshold_value}"

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
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        self._mark_alert_resolved(alert, resolved_by)
        self._remove_active_alert(alert_id, resolved_by)
        return True

    def _remove_active_alert(self, alert_id: str, resolved_by: str) -> None:
        """Remove alert from active collection and log."""
        del self.active_alerts[alert_id]
        logger.info(f"Alert {alert_id} resolved by {resolved_by}")

    def _mark_alert_resolved(self, alert: Alert, resolved_by: str) -> None:
        """Mark alert as resolved with metadata."""
        alert.resolved = True
        alert.resolved_at = datetime.now(UTC)
        alert.metadata["resolved_by"] = resolved_by

    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by level."""
        alerts = list(self.active_alerts.values())
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert system status."""
        active_count = len(self.active_alerts)
        level_counts = self._calculate_level_counts()
        return self._build_summary_dict(active_count, level_counts)

    def _build_summary_dict(self, active_count: int, level_counts: Dict[str, int]) -> Dict[str, Any]:
        """Build summary dictionary with all status information."""
        alert_info = {"active_alerts": active_count, "alerts_by_level": level_counts}
        system_info = self._get_system_summary_info()
        return {**alert_info, **system_info}

    def _get_system_summary_info(self) -> Dict[str, Any]:
        """Get system summary information for alert manager."""
        return {
            "suppressed_rules": len(self.suppressed_rules),
            "total_rules": len(self.alert_rules),
            "enabled_rules": self._count_enabled_rules(),
            "notification_channels": self._count_enabled_channels()
        }

    def _calculate_level_counts(self) -> Dict[str, int]:
        """Calculate alert counts by level."""
        level_counts = {}
        for alert in self.active_alerts.values():
            level = alert.level.value
            level_counts[level] = level_counts.get(level, 0) + 1
        return level_counts

    def _count_enabled_rules(self) -> int:
        """Count enabled alert rules."""
        return len([r for r in self.alert_rules.values() if r.enabled])

    def _count_enabled_channels(self) -> int:
        """Count enabled notification channels."""
        return len([c for c in self.notification_configs.values() if c.enabled])

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