"""Alert rule definitions and evaluation logic.

Contains default alert rules, rule evaluation logic, and condition
checking for various system metrics and agent behaviors.
"""

from typing import Dict, Any, List
from datetime import datetime, UTC, timedelta

from .alert_types import AlertRule, AlertLevel, NotificationChannel
from app.services.metrics.agent_metrics import AgentMetrics
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def create_default_alert_rules() -> Dict[str, AlertRule]:
    """Create default alert rules for common scenarios."""
    default_rules = [
        _create_high_error_rate_rule(),
        _create_critical_error_rate_rule(),
        _create_timeout_spike_rule(),
        _create_high_execution_time_rule(),
        _create_validation_error_spike_rule(),
        _create_system_failure_rate_rule()
    ]
    
    return {rule.rule_id: rule for rule in default_rules}


def _create_high_error_rate_rule() -> AlertRule:
    """Create high error rate alert rule."""
    return AlertRule(
        rule_id="agent_high_error_rate",
        name="High Agent Error Rate",
        description="Agent error rate exceeds threshold",
        condition="error_rate > threshold_value",
        level=AlertLevel.ERROR,
        threshold_value=0.2,  # 20% error rate
        time_window_minutes=5,
        channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
    )


def _create_critical_error_rate_rule() -> AlertRule:
    """Create critical error rate alert rule."""
    return AlertRule(
        rule_id="agent_critical_error_rate",
        name="Critical Agent Error Rate",
        description="Agent error rate critically high",
        condition="error_rate > threshold_value",
        level=AlertLevel.CRITICAL,
        threshold_value=0.5,  # 50% error rate
        time_window_minutes=3,
        channels=[NotificationChannel.LOG, NotificationChannel.EMAIL, NotificationChannel.SLACK]
    )


def _create_timeout_spike_rule() -> AlertRule:
    """Create timeout spike alert rule."""
    return AlertRule(
        rule_id="agent_timeout_spike",
        name="Agent Timeout Spike",
        description="High number of agent timeouts",
        condition="timeout_count > threshold_value",
        level=AlertLevel.WARNING,
        threshold_value=5,  # 5 timeouts in window
        time_window_minutes=5,
        channels=[NotificationChannel.LOG]
    )


def _create_high_execution_time_rule() -> AlertRule:
    """Create high execution time alert rule."""
    return AlertRule(
        rule_id="agent_avg_execution_time_high",
        name="High Agent Execution Time",
        description="Average execution time exceeds threshold",
        condition="avg_execution_time_ms > threshold_value",
        level=AlertLevel.WARNING,
        threshold_value=30000,  # 30 seconds
        time_window_minutes=10,
        channels=[NotificationChannel.LOG]
    )


def _create_validation_error_spike_rule() -> AlertRule:
    """Create validation error spike alert rule."""
    return AlertRule(
        rule_id="agent_validation_error_spike",
        name="Validation Error Spike",
        description="High number of validation errors",
        condition="validation_error_count > threshold_value",
        level=AlertLevel.ERROR,
        threshold_value=10,  # 10 validation errors
        time_window_minutes=5,
        channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
    )


def _create_system_failure_rate_rule() -> AlertRule:
    """Create system-wide failure rate alert rule."""
    return AlertRule(
        rule_id="system_wide_failure_rate",
        name="System-wide High Failure Rate",
        description="Overall system failure rate is high",
        condition="system_error_rate > threshold_value",
        level=AlertLevel.CRITICAL,
        threshold_value=0.3,  # 30% system-wide error rate
        time_window_minutes=5,
        channels=[NotificationChannel.LOG, NotificationChannel.EMAIL, NotificationChannel.SLACK]
    )


class RuleEvaluator:
    """Evaluates alert rules against metrics data."""
    
    def evaluate_system_condition(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> bool:
        """Evaluate system-wide condition."""
        threshold_value = rule.threshold_value
        
        if rule.rule_id == "system_wide_failure_rate":
            system_error_rate = metrics_data.get("system_error_rate", 0.0)
            return system_error_rate > threshold_value
        
        return False
    
    def evaluate_agent_condition(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> bool:
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
    
    def get_metric_value_for_rule(self, rule_id: str, metrics: AgentMetrics) -> float:
        """Get specific metric value for rule."""
        mapping = {
            "agent_high_error_rate": metrics.error_rate,
            "agent_critical_error_rate": metrics.error_rate,
            "agent_timeout_spike": float(metrics.timeout_count),
            "agent_avg_execution_time_high": metrics.avg_execution_time_ms,
            "agent_validation_error_spike": float(metrics.validation_error_count)
        }
        return mapping.get(rule_id, 0.0)


class CooldownManager:
    """Manages cooldown periods for alert rules."""
    
    def __init__(self):
        """Initialize cooldown manager."""
        self.cooldown_tracker: Dict[str, datetime] = {}
    
    def is_in_cooldown(self, rule_id: str, rule: AlertRule) -> bool:
        """Check if rule is in cooldown period."""
        if rule_id not in self.cooldown_tracker:
            return False
        
        last_triggered = self.cooldown_tracker[rule_id]
        cooldown_duration = timedelta(minutes=rule.cooldown_minutes)
        
        return datetime.now(UTC) - last_triggered < cooldown_duration
    
    def set_cooldown(self, rule_id: str) -> None:
        """Set cooldown for a rule."""
        self.cooldown_tracker[rule_id] = datetime.now(UTC)
    
    def clear_cooldown(self, rule_id: str) -> None:
        """Clear cooldown for a rule."""
        self.cooldown_tracker.pop(rule_id, None)