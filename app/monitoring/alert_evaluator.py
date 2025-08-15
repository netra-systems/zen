"""
Alert rule evaluation and condition checking.
Handles the logic for evaluating alert rules against metrics data.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, UTC

from app.logging_config import central_logger
from .alert_models import AlertRule, AlertLevel, Alert
from app.services.metrics.agent_metrics import AgentMetrics, AgentMetricsCollector

logger = central_logger.get_logger(__name__)


class AlertEvaluator:
    """Evaluates alert rules against current metrics."""
    
    def __init__(self, metrics_collector: AgentMetricsCollector):
        self.metrics_collector = metrics_collector
    
    async def evaluate_rule(self, rule: AlertRule) -> Optional[Alert]:
        """Evaluate a specific alert rule and return alert if triggered."""
        try:
            # Get relevant metrics
            metrics_data = await self._get_metrics_for_rule(rule)
            
            # Evaluate condition
            triggered = await self._evaluate_condition(rule, metrics_data)
            
            if triggered:
                return self._create_alert(rule, metrics_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
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
    
    def _create_alert(self, rule: AlertRule, metrics_data: Dict[str, Any]) -> Alert:
        """Create alert instance from rule and metrics."""
        import uuid
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