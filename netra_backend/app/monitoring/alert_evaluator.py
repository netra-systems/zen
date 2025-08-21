"""
Alert rule evaluation and condition checking.
Handles the logic for evaluating alert rules against metrics data.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, UTC

from app.logging_config import central_logger
from netra_backend.app.alert_models import AlertRule, AlertLevel, Alert
from app.services.metrics.agent_metrics import AgentMetrics, AgentMetricsCollector

logger = central_logger.get_logger(__name__)


class AlertEvaluator:
    """Evaluates alert rules against current metrics."""
    
    def __init__(self, metrics_collector: AgentMetricsCollector):
        self.metrics_collector = metrics_collector
    
    async def evaluate_rule(self, rule: AlertRule) -> Optional[Alert]:
        """Evaluate a specific alert rule and return alert if triggered."""
        try:
            return await self._process_rule_evaluation(rule)
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
            return None

    async def _process_rule_evaluation(self, rule: AlertRule) -> Optional[Alert]:
        """Process rule evaluation with metrics."""
        metrics_data = await self._get_metrics_for_rule(rule)
        triggered = await self._evaluate_condition(rule, metrics_data)
        return self._create_alert_if_triggered(rule, metrics_data, triggered)

    def _create_alert_if_triggered(
        self, rule: AlertRule, metrics_data: Dict[str, Any], triggered: bool
    ) -> Optional[Alert]:
        """Create alert if condition was triggered."""
        if triggered:
            return self._create_alert(rule, metrics_data)
        return None
    
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
            return self._check_rule_condition(rule, metrics_data)
        except Exception as e:
            logger.error(f"Error evaluating condition for rule {rule.rule_id}: {e}")
            return False

    def _check_rule_condition(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> bool:
        """Check rule condition based on rule type."""
        if "system_wide" in rule.rule_id:
            return self._evaluate_system_condition(rule, metrics_data)
        return self._evaluate_agent_condition(rule, metrics_data)
    
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
        return self._check_agents_against_rule(rule, agent_metrics, threshold_value)

    def _check_agents_against_rule(
        self, rule: AlertRule, agent_metrics: Dict[str, Any], threshold_value: float
    ) -> bool:
        """Check all agents against rule condition."""
        for agent_name, metrics in agent_metrics.items():
            if self._check_agent_against_rule(rule, metrics, threshold_value):
                return True
        return False
    
    def _check_agent_against_rule(self, rule: AlertRule, metrics: AgentMetrics, threshold: float) -> bool:
        """Check if individual agent metrics trigger the rule."""
        rule_mapping = self._build_rule_mapping(metrics, threshold)
        return rule_mapping.get(rule.rule_id, False)

    def _build_rule_mapping(self, metrics: AgentMetrics, threshold: float) -> Dict[str, bool]:
        """Build mapping of rule IDs to their condition results."""
        error_rules = self._build_error_rate_rules(metrics, threshold)
        performance_rules = self._build_performance_rules(metrics, threshold)
        return {**error_rules, **performance_rules}

    def _build_error_rate_rules(self, metrics: AgentMetrics, threshold: float) -> Dict[str, bool]:
        """Build error rate rule mappings."""
        return {
            "agent_high_error_rate": metrics.error_rate > threshold,
            "agent_critical_error_rate": metrics.error_rate > threshold,
            "agent_validation_error_spike": metrics.validation_error_count > threshold
        }

    def _build_performance_rules(self, metrics: AgentMetrics, threshold: float) -> Dict[str, bool]:
        """Build performance rule mappings."""
        return {
            "agent_timeout_spike": metrics.timeout_count > threshold,
            "agent_avg_execution_time_high": metrics.avg_execution_time_ms > threshold
        }
    
    def _create_alert(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> Alert:
        """Create alert instance from rule and metrics."""
        import uuid
        alert_id = str(uuid.uuid4())
        current_value, agent_name = self._extract_alert_values(rule, metrics_data)
        return self._build_alert_instance(alert_id, rule, current_value, agent_name)

    def _build_alert_instance(
        self, alert_id: str, rule: AlertRule, current_value: Optional[float], agent_name: Optional[str]
    ) -> Alert:
        """Build alert instance with all required fields."""
        alert_fields = self._gather_alert_fields(alert_id, rule, current_value, agent_name)
        return Alert(**alert_fields)

    def _gather_alert_fields(self, alert_id: str, rule: AlertRule, current_value: Optional[float], agent_name: Optional[str]) -> Dict[str, Any]:
        """Gather all alert fields from different sources."""
        basic_fields = self._get_alert_basic_fields(alert_id, rule, agent_name)
        metric_fields = self._get_alert_metric_fields(rule, current_value)
        message_fields = self._get_alert_message_fields(rule, current_value, agent_name)
        return {**basic_fields, **metric_fields, **message_fields}

    def _get_alert_basic_fields(self, alert_id: str, rule: AlertRule, agent_name: Optional[str]) -> Dict[str, Any]:
        """Get basic alert fields."""
        return {
            "alert_id": alert_id, "rule_id": rule.rule_id, "level": rule.level,
            "title": rule.name, "timestamp": datetime.now(UTC), "agent_name": agent_name
        }

    def _get_alert_metric_fields(self, rule: AlertRule, current_value: Optional[float]) -> Dict[str, Any]:
        """Get alert metric fields."""
        return {
            "metric_name": rule.rule_id, "current_value": current_value,
            "threshold_value": rule.threshold_value
        }

    def _get_alert_message_fields(self, rule: AlertRule, current_value: Optional[float], agent_name: Optional[str]) -> Dict[str, Any]:
        """Get alert message and metadata fields."""
        return {
            "message": self._generate_alert_message(rule, current_value, agent_name),
            "metadata": {"rule_description": rule.description}
        }
    
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
        """Find agent with values matching rule condition."""
        for agent_name, metrics in agent_metrics.items():
            if self._check_agent_against_rule(rule, metrics, rule.threshold_value):
                value = self._get_metric_value_for_rule(rule.rule_id, metrics)
                return value, agent_name
        return None, None
    
    def _get_metric_value_for_rule(self, rule_id: str, metrics: AgentMetrics) -> float:
        """Get specific metric value for rule."""
        mapping = self._build_metric_value_mapping(metrics)
        return mapping.get(rule_id, 0.0)

    def _build_metric_value_mapping(self, metrics: AgentMetrics) -> Dict[str, float]:
        """Build mapping of rule IDs to metric values."""
        error_mappings = self._build_error_metric_mappings(metrics)
        performance_mappings = self._build_performance_metric_mappings(metrics)
        return {**error_mappings, **performance_mappings}

    def _build_error_metric_mappings(self, metrics: AgentMetrics) -> Dict[str, float]:
        """Build error metric mappings."""
        return {
            "agent_high_error_rate": metrics.error_rate,
            "agent_critical_error_rate": metrics.error_rate,
            "agent_validation_error_spike": float(metrics.validation_error_count)
        }

    def _build_performance_metric_mappings(self, metrics: AgentMetrics) -> Dict[str, float]:
        """Build performance metric mappings."""
        return {
            "agent_timeout_spike": float(metrics.timeout_count),
            "agent_avg_execution_time_high": metrics.avg_execution_time_ms
        }
    
    def _generate_alert_message(self, rule: AlertRule, current_value: Optional[float], agent_name: Optional[str]) -> str:
        """Generate human-readable alert message."""
        base_msg = self._get_base_message(rule)
        return self._append_value_details(base_msg, current_value, agent_name, rule)

    def _get_base_message(self, rule: AlertRule) -> str:
        """Get base alert message from rule."""
        return rule.description

    def _append_value_details(
        self, base_msg: str, current_value: Optional[float], agent_name: Optional[str], rule: AlertRule
    ) -> str:
        """Append value details to base message."""
        if current_value is None:
            return base_msg
        return self._append_formatted_details(base_msg, current_value, agent_name, rule)

    def _append_formatted_details(
        self, base_msg: str, current_value: float, agent_name: Optional[str], rule: AlertRule
    ) -> str:
        """Append formatted details to message."""
        details = self._format_value_details(current_value, agent_name, rule.threshold_value)
        return base_msg + details

    def _format_value_details(self, current_value: float, agent_name: Optional[str], threshold: float) -> str:
        """Format value details for alert message."""
        if agent_name:
            return f" - Agent: {agent_name}, Current: {current_value:.3f}, Threshold: {threshold}"
        return f" - Current: {current_value:.3f}, Threshold: {threshold}"