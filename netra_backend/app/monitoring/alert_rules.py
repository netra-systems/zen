"""Alert rule definitions and evaluation logic.

Contains default alert rules, rule evaluation logic, and condition
checking for various system metrics and agent behaviors.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.alert_types import (
    AlertLevel,
    AlertRule,
    NotificationChannel,
)
from netra_backend.app.services.metrics.agent_metrics import AgentMetrics

logger = central_logger.get_logger(__name__)


def create_default_alert_rules() -> Dict[str, AlertRule]:
    """Create default alert rules for common scenarios."""
    default_rules = _get_all_default_rules()
    return {rule.rule_id: rule for rule in default_rules}

def _get_all_default_rules() -> List[AlertRule]:
    """Get list of all default alert rules."""
    rule_creators = [
        _create_high_error_rate_rule, _create_critical_error_rate_rule,
        _create_timeout_spike_rule, _create_high_execution_time_rule,
        _create_validation_error_spike_rule, _create_system_failure_rate_rule
    ]
    return [creator() for creator in rule_creators]


def _create_high_error_rate_rule() -> AlertRule:
    """Create high error rate alert rule."""
    config = _get_high_error_rate_rule_config()
    return _build_high_error_rate_rule(config)

def _get_high_error_rate_rule_config() -> Dict[str, Any]:
    """Get high error rate rule configuration."""
    base_config = _get_error_rate_base_config()
    specific_config = _get_high_error_specific_config()
    return {**base_config, **specific_config}

def _get_error_rate_base_config() -> Dict[str, Any]:
    """Get base error rate configuration."""
    return {
        "rule_id": "agent_high_error_rate",
        "name": "High Agent Error Rate",
        "description": "Agent error rate exceeds threshold"
    }

def _get_high_error_specific_config() -> Dict[str, Any]:
    """Get high error specific configuration."""
    return {"level": AlertLevel.ERROR, "threshold_value": 0.2}

def _build_high_error_rate_rule(config: Dict[str, Any]) -> AlertRule:
    """Build high error rate alert rule."""
    return AlertRule(
        rule_id=config["rule_id"], name=config["name"],
        description=config["description"], condition="error_rate > threshold_value",
        level=config["level"], threshold_value=config["threshold_value"],
        time_window_minutes=5, channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
    )


def _create_critical_error_rate_rule() -> AlertRule:
    """Create critical error rate alert rule."""
    channels = _get_critical_channels()
    rule_config = _get_critical_error_rule_config()
    return AlertRule(
        rule_id="agent_critical_error_rate", name="Critical Agent Error Rate",
        description="Agent error rate critically high", level=AlertLevel.CRITICAL,
        condition="error_rate > threshold_value", threshold_value=0.5,
        time_window_minutes=3, channels=channels
    )

def _get_critical_error_rule_config() -> Dict[str, Any]:
    """Get configuration for critical error rule."""
    return {
        "threshold_value": 0.5,
        "time_window_minutes": 3,
        "level": AlertLevel.CRITICAL
    }

def _get_critical_channels() -> List[NotificationChannel]:
    """Get notification channels for critical alerts."""
    return [NotificationChannel.LOG, NotificationChannel.EMAIL, NotificationChannel.SLACK]

def _create_base_rule_config() -> Dict[str, Any]:
    """Create base rule configuration."""
    return {
        "time_window_minutes": 5,
        "channels": [NotificationChannel.LOG]
    }

def _create_error_rule_config() -> Dict[str, Any]:
    """Create error-level rule configuration."""
    return {
        "time_window_minutes": 5,
        "channels": [NotificationChannel.LOG, NotificationChannel.SLACK]
    }


def _create_timeout_spike_rule() -> AlertRule:
    """Create timeout spike alert rule."""
    config = _get_timeout_rule_config()
    return AlertRule(
        rule_id="agent_timeout_spike", name="Agent Timeout Spike",
        description="High number of agent timeouts", level=AlertLevel.WARNING,
        condition="timeout_count > threshold_value", threshold_value=5,
        time_window_minutes=5, channels=[NotificationChannel.LOG]
    )

def _get_timeout_rule_config() -> Dict[str, Any]:
    """Get configuration for timeout rule."""
    return {
        "threshold_value": 5,
        "time_window_minutes": 5,
        "level": AlertLevel.WARNING
    }


def _create_high_execution_time_rule() -> AlertRule:
    """Create high execution time alert rule."""
    config = _get_execution_time_rule_config()
    return AlertRule(
        rule_id="agent_avg_execution_time_high", name="High Agent Execution Time",
        description="Average execution time exceeds threshold", level=AlertLevel.WARNING,
        condition="avg_execution_time_ms > threshold_value", threshold_value=30000,
        time_window_minutes=10, channels=[NotificationChannel.LOG]
    )

def _get_execution_time_rule_config() -> Dict[str, Any]:
    """Get configuration for execution time rule."""
    return {
        "threshold_value": 30000,
        "time_window_minutes": 10,
        "level": AlertLevel.WARNING
    }


def _create_validation_error_spike_rule() -> AlertRule:
    """Create validation error spike alert rule."""
    config = _get_validation_error_rule_config()
    return _build_validation_error_rule(config)

def _build_validation_error_rule(config: Dict[str, Any]) -> AlertRule:
    """Build validation error spike alert rule."""
    return AlertRule(
        rule_id="agent_validation_error_spike", name="Validation Error Spike",
        description="High number of validation errors", level=AlertLevel.ERROR,
        condition="validation_error_count > threshold_value", threshold_value=10,
        time_window_minutes=5, channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
    )

def _get_validation_error_rule_config() -> Dict[str, Any]:
    """Get configuration for validation error rule."""
    return {
        "threshold_value": 10,
        "time_window_minutes": 5,
        "level": AlertLevel.ERROR
    }


def _create_system_failure_rate_rule() -> AlertRule:
    """Create system-wide failure rate alert rule."""
    channels = _get_critical_channels()
    config = _get_system_failure_rule_config()
    return _build_system_failure_rule(channels, config)

def _build_system_failure_rule(channels: List[NotificationChannel], config: Dict[str, Any]) -> AlertRule:
    """Build system failure rate alert rule."""
    return AlertRule(
        rule_id="system_wide_failure_rate", name="System-wide High Failure Rate",
        description="Overall system failure rate is high", level=AlertLevel.CRITICAL,
        condition="system_error_rate > threshold_value", threshold_value=0.3,
        time_window_minutes=5, channels=channels
    )

def _get_system_failure_rule_config() -> Dict[str, Any]:
    """Get configuration for system failure rule."""
    return {
        "threshold_value": 0.3,
        "time_window_minutes": 5,
        "level": AlertLevel.CRITICAL
    }


class RuleEvaluator:
    """Evaluates alert rules against metrics data."""
    
    def evaluate_system_condition(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> bool:
        """Evaluate system-wide condition."""
        if rule.rule_id == "system_wide_failure_rate":
            return self._check_system_failure_rate(rule, metrics_data)
        return False

    def _check_system_failure_rate(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> bool:
        """Check system failure rate against threshold."""
        system_error_rate = metrics_data.get("system_error_rate", 0.0)
        return system_error_rate > rule.threshold_value
    
    def evaluate_agent_condition(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> bool:
        """Evaluate agent-specific condition."""
        agent_metrics = metrics_data.get("agent_metrics", {})
        return self._check_any_agent_triggers_rule(rule, agent_metrics)

    def _check_any_agent_triggers_rule(self, rule: AlertRule, agent_metrics: Dict[str, Any]) -> bool:
        """Check if any agent triggers the rule."""
        for agent_name, metrics in agent_metrics.items():
            if self._check_agent_against_rule(rule, metrics, rule.threshold_value):
                return True
        return False
    
    def _check_agent_against_rule(self, rule: AlertRule, metrics: AgentMetrics, threshold: float) -> bool:
        """Check if individual agent metrics trigger the rule."""
        rule_mapping = self._get_rule_mapping(metrics, threshold)
        return rule_mapping.get(rule.rule_id, False)

    def _get_rule_mapping(self, metrics: AgentMetrics, threshold: float) -> Dict[str, bool]:
        """Get rule mapping for agent metrics."""
        error_checks = self._get_error_rate_checks(metrics, threshold)
        performance_checks = self._get_performance_checks(metrics, threshold)
        return {**error_checks, **performance_checks}

    def _get_error_rate_checks(self, metrics: AgentMetrics, threshold: float) -> Dict[str, bool]:
        """Get error rate related checks."""
        return {
            "agent_high_error_rate": metrics.error_rate > threshold,
            "agent_critical_error_rate": metrics.error_rate > threshold,
            "agent_validation_error_spike": metrics.validation_error_count > threshold
        }

    def _get_performance_checks(self, metrics: AgentMetrics, threshold: float) -> Dict[str, bool]:
        """Get performance related checks."""
        return {
            "agent_timeout_spike": metrics.timeout_count > threshold,
            "agent_avg_execution_time_high": metrics.avg_execution_time_ms > threshold
        }
    
    def get_metric_value_for_rule(self, rule_id: str, metrics: AgentMetrics) -> float:
        """Get specific metric value for rule."""
        mapping = self._get_metric_value_mapping(metrics)
        return mapping.get(rule_id, 0.0)

    def _get_metric_value_mapping(self, metrics: AgentMetrics) -> Dict[str, float]:
        """Get metric value mapping for agent metrics."""
        error_values = self._get_error_rate_values(metrics)
        performance_values = self._get_performance_values(metrics)
        return {**error_values, **performance_values}

    def _get_error_rate_values(self, metrics: AgentMetrics) -> Dict[str, float]:
        """Get error rate related values."""
        return {
            "agent_high_error_rate": metrics.error_rate,
            "agent_critical_error_rate": metrics.error_rate,
            "agent_validation_error_spike": float(metrics.validation_error_count)
        }

    def _get_performance_values(self, metrics: AgentMetrics) -> Dict[str, float]:
        """Get performance related values."""
        return {
            "agent_timeout_spike": float(metrics.timeout_count),
            "agent_avg_execution_time_high": metrics.avg_execution_time_ms
        }


class CooldownManager:
    """Manages cooldown periods for alert rules."""
    
    def __init__(self):
        """Initialize cooldown manager."""
        self.cooldown_tracker: Dict[str, datetime] = {}
    
    def is_in_cooldown(self, rule_id: str, rule: AlertRule) -> bool:
        """Check if rule is in cooldown period."""
        if rule_id not in self.cooldown_tracker:
            return False
        
        return self._check_cooldown_duration(rule_id, rule)

    def _check_cooldown_duration(self, rule_id: str, rule: AlertRule) -> bool:
        """Check if cooldown duration has elapsed."""
        last_triggered = self.cooldown_tracker[rule_id]
        cooldown_duration = timedelta(minutes=rule.cooldown_minutes)
        return datetime.now(UTC) - last_triggered < cooldown_duration
    
    def set_cooldown(self, rule_id: str) -> None:
        """Set cooldown for a rule."""
        self.cooldown_tracker[rule_id] = datetime.now(UTC)
    
    def clear_cooldown(self, rule_id: str) -> None:
        """Clear cooldown for a rule."""
        self.cooldown_tracker.pop(rule_id, None)