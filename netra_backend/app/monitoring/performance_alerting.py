"""
Performance-based alerting system.
Monitors performance metrics and triggers alerts based on thresholds.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, UTC
import asyncio

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.alert_models import Alert, AlertLevel, AlertRule

logger = central_logger.get_logger(__name__)


class PerformanceAlertManager:
    """Manages performance-based alerts and threshold monitoring."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._alert_rules: List[AlertRule] = []
        self._active_alerts: List[Alert] = []
        self._performance_history: List[Dict[str, Any]] = []
        self._alert_cooldown_seconds = self.config.get("alert_cooldown_seconds", 300)  # 5 minutes
        logger.debug("Initialized PerformanceAlertManager")
    
    async def initialize(self) -> None:
        """Initialize the performance alert manager."""
        self._setup_default_rules()
        logger.info("PerformanceAlertManager initialized with default rules")
    
    def _setup_default_rules(self) -> None:
        """Setup default performance alert rules."""
        default_rules = [
            AlertRule(
                rule_id="high_response_time",
                name="High Response Time",
                description="Response time exceeds acceptable threshold",
                threshold_value=5000.0,  # 5 seconds
                level=AlertLevel.WARNING
            ),
            AlertRule(
                rule_id="critical_response_time", 
                name="Critical Response Time",
                description="Response time critically high",
                threshold_value=10000.0,  # 10 seconds
                level=AlertLevel.CRITICAL
            ),
            AlertRule(
                rule_id="high_error_rate",
                name="High Error Rate",
                description="Error rate exceeds acceptable threshold",
                threshold_value=0.05,  # 5%
                level=AlertLevel.ERROR
            ),
            AlertRule(
                rule_id="low_throughput",
                name="Low Throughput",
                description="System throughput below expected level",
                threshold_value=10.0,  # requests per minute
                level=AlertLevel.WARNING
            )
        ]
        
        self._alert_rules.extend(default_rules)
    
    async def record_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Record performance metrics and check for alert conditions."""
        metrics_with_timestamp = {
            **metrics,
            "timestamp": datetime.now(UTC)
        }
        
        self._performance_history.append(metrics_with_timestamp)
        
        # Keep only last 1000 entries
        if len(self._performance_history) > 1000:
            self._performance_history = self._performance_history[-1000:]
        
        # Check for alert conditions
        await self._evaluate_alert_conditions(metrics_with_timestamp)
        
        logger.debug(f"Recorded performance metrics and evaluated alerts")
    
    async def _evaluate_alert_conditions(self, current_metrics: Dict[str, Any]) -> None:
        """Evaluate current metrics against alert rules."""
        for rule in self._alert_rules:
            if await self._should_trigger_alert(rule, current_metrics):
                await self._trigger_alert(rule, current_metrics)
    
    async def _should_trigger_alert(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """Check if alert rule should be triggered."""
        # Check if we're in cooldown period
        if self._is_in_cooldown(rule.rule_id):
            return False
        
        # Evaluate rule condition
        return self._evaluate_rule_condition(rule, metrics)
    
    def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if rule is in cooldown period."""
        cutoff_time = datetime.now(UTC) - timedelta(seconds=self._alert_cooldown_seconds)
        
        for alert in self._active_alerts:
            if (alert.rule_id == rule_id and 
                alert.timestamp > cutoff_time):
                return True
        
        return False
    
    def _evaluate_rule_condition(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """Evaluate if rule condition is met."""
        rule_evaluators = {
            "high_response_time": lambda m: m.get("response_time_ms", 0) > rule.threshold_value,
            "critical_response_time": lambda m: m.get("response_time_ms", 0) > rule.threshold_value,
            "high_error_rate": lambda m: m.get("error_rate", 0) > rule.threshold_value,
            "low_throughput": lambda m: m.get("throughput_rpm", float('inf')) < rule.threshold_value
        }
        
        evaluator = rule_evaluators.get(rule.rule_id)
        if evaluator:
            return evaluator(metrics)
        
        return False
    
    async def _trigger_alert(self, rule: AlertRule, metrics: Dict[str, Any]) -> None:
        """Trigger an alert based on rule and metrics."""
        import uuid
        
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            rule_id=rule.rule_id,
            title=rule.name,
            message=self._generate_alert_message(rule, metrics),
            level=rule.level,
            timestamp=datetime.now(UTC),
            agent_name=metrics.get("agent_name"),
            metric_name=rule.rule_id,
            current_value=self._extract_metric_value(rule, metrics),
            threshold_value=rule.threshold_value,
            metadata={"metrics": metrics}
        )
        
        self._active_alerts.append(alert)
        logger.warning(f"Performance alert triggered: {alert.title} - {alert.message}")
        
        # Here you would typically send the alert to notification channels
        await self._notify_alert(alert)
    
    def _generate_alert_message(self, rule: AlertRule, metrics: Dict[str, Any]) -> str:
        """Generate alert message based on rule and current metrics."""
        current_value = self._extract_metric_value(rule, metrics)
        
        return (
            f"{rule.description}. "
            f"Current value: {current_value}, "
            f"Threshold: {rule.threshold_value}"
        )
    
    def _extract_metric_value(self, rule: AlertRule, metrics: Dict[str, Any]) -> float:
        """Extract relevant metric value for rule."""
        metric_mappings = {
            "high_response_time": "response_time_ms",
            "critical_response_time": "response_time_ms", 
            "high_error_rate": "error_rate",
            "low_throughput": "throughput_rpm"
        }
        
        metric_key = metric_mappings.get(rule.rule_id, "value")
        return metrics.get(metric_key, 0.0)
    
    async def _notify_alert(self, alert: Alert) -> None:
        """Send alert notification (stub implementation)."""
        # In real implementation, this would integrate with notification system
        logger.info(f"Alert notification: {alert.title} - {alert.message}")
    
    async def get_performance_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get performance summary for specified time window."""
        cutoff_time = datetime.now(UTC) - timedelta(minutes=time_window_minutes)
        recent_metrics = [
            m for m in self._performance_history 
            if m.get("timestamp", datetime.min) > cutoff_time
        ]
        
        if not recent_metrics:
            return {
                "summary": "No recent metrics available",
                "metrics_count": 0,
                "time_window_minutes": time_window_minutes
            }
        
        return self._calculate_performance_stats(recent_metrics, time_window_minutes)
    
    def _calculate_performance_stats(self, metrics: List[Dict[str, Any]], time_window: int) -> Dict[str, Any]:
        """Calculate performance statistics from metrics."""
        response_times = [m.get("response_time_ms", 0) for m in metrics if "response_time_ms" in m]
        error_rates = [m.get("error_rate", 0) for m in metrics if "error_rate" in m]
        throughputs = [m.get("throughput_rpm", 0) for m in metrics if "throughput_rpm" in m]
        
        return {
            "metrics_count": len(metrics),
            "time_window_minutes": time_window,
            "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
            "max_response_time_ms": max(response_times) if response_times else 0,
            "avg_error_rate": sum(error_rates) / len(error_rates) if error_rates else 0,
            "avg_throughput_rpm": sum(throughputs) / len(throughputs) if throughputs else 0,
            "active_alerts_count": len(self._active_alerts)
        }
    
    async def add_alert_rule(self, rule: AlertRule) -> None:
        """Add a custom alert rule."""
        self._alert_rules.append(rule)
        logger.info(f"Added custom alert rule: {rule.rule_id}")
    
    async def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule by ID."""
        initial_count = len(self._alert_rules)
        self._alert_rules = [r for r in self._alert_rules if r.rule_id != rule_id]
        removed = len(self._alert_rules) < initial_count
        
        if removed:
            logger.info(f"Removed alert rule: {rule_id}")
        
        return removed
    
    async def clear_alert(self, alert_id: str) -> bool:
        """Clear an active alert."""
        initial_count = len(self._active_alerts)
        self._active_alerts = [a for a in self._active_alerts if a.alert_id != alert_id]
        cleared = len(self._active_alerts) < initial_count
        
        if cleared:
            logger.info(f"Cleared alert: {alert_id}")
        
        return cleared
    
    async def get_active_alerts(self) -> List[Alert]:
        """Get all currently active alerts."""
        return self._active_alerts.copy()
    
    async def get_alert_rules(self) -> List[AlertRule]:
        """Get all configured alert rules."""
        return self._alert_rules.copy()


__all__ = [
    "PerformanceAlertManager",
]