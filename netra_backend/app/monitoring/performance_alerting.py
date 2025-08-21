"""Performance alerting and threshold management for Netra platform.

This module provides comprehensive performance alerting capabilities including:
- Alert rule definition and evaluation
- Threshold-based monitoring
- Alert cooldown management
- Callback notification system
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class PerformanceAlertManager:
    """Manages performance-related alerts and thresholds."""
    
    def __init__(self, metrics_collector):
        self.metrics_collector = metrics_collector
        self.alert_rules = self._initialize_alert_rules()
        self._alert_callbacks: List[Callable] = []
        self._last_alerts: Dict[str, datetime] = {}
        self._alert_cooldown = 300  # 5 minutes between same alerts
    
    def _initialize_alert_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize performance alert rules."""
        rule_creators = self._get_rule_creators()
        return self._build_rules_from_creators(rule_creators)

    def _get_rule_creators(self) -> Dict[str, Callable]:
        """Get alert rule creator functions."""
        resource_rules = self._get_resource_rule_creators()
        database_rules = self._get_database_rule_creators()
        return {**resource_rules, **database_rules}

    def _get_resource_rule_creators(self) -> Dict[str, Callable]:
        """Get resource-related rule creators."""
        return {
            "high_cpu": self._create_high_cpu_rule,
            "high_memory": self._create_high_memory_rule,
            "low_memory": self._create_low_memory_rule
        }

    def _get_database_rule_creators(self) -> Dict[str, Callable]:
        """Get database-related rule creators."""
        return {
            "database_pool_exhaustion": self._create_pool_exhaustion_rule,
            "low_cache_hit_ratio": self._create_cache_hit_rule
        }

    def _build_rules_from_creators(self, rule_creators: Dict[str, Callable]) -> Dict[str, Dict[str, Any]]:
        """Build alert rules from creator functions."""
        return {name: creator() for name, creator in rule_creators.items()}
    
    def _create_high_cpu_rule(self) -> Dict[str, Any]:
        """Create high CPU usage alert rule."""
        return {
            "metric": "system.cpu_percent",
            "threshold": 80.0,
            "operator": ">",
            "duration": 60,  # seconds
            "severity": "warning"
        }
    
    def _create_high_memory_rule(self) -> Dict[str, Any]:
        """Create high memory usage alert rule."""
        return {
            "metric": "system.memory_percent", 
            "threshold": 85.0,
            "operator": ">",
            "duration": 60,
            "severity": "warning"
        }
    
    def _create_low_memory_rule(self) -> Dict[str, Any]:
        """Create low available memory alert rule."""
        return {
            "metric": "system.memory_available_mb",
            "threshold": 512.0,
            "operator": "<",
            "duration": 30,
            "severity": "critical"
        }
    
    def _create_pool_exhaustion_rule(self) -> Dict[str, Any]:
        """Create database pool exhaustion alert rule."""
        return {
            "metric": "database.pool_utilization",
            "threshold": 0.9,
            "operator": ">",
            "duration": 30,
            "severity": "critical"
        }
    
    def _create_cache_hit_rule(self) -> Dict[str, Any]:
        """Create low cache hit ratio alert rule."""
        base_rule = self._get_cache_hit_base_rule()
        return {**base_rule, "min_samples": 10}

    def _get_cache_hit_base_rule(self) -> Dict[str, Any]:
        """Get base cache hit ratio rule parameters."""
        return {
            "metric": "database.cache_hit_ratio",
            "threshold": 0.5,
            "operator": "<",
            "duration": 300,
            "severity": "warning"
        }
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Add callback function for alert notifications."""
        self._alert_callbacks.append(callback)
    
    async def check_alerts(self) -> List[Dict[str, Any]]:
        """Check all alert rules and return triggered alerts."""
        triggered_alerts = []
        for alert_name, rule in self.alert_rules.items():
            alert_data = await self._process_single_alert_rule(alert_name, rule)
            self._add_alert_if_triggered(triggered_alerts, alert_data)
        return triggered_alerts

    def _add_alert_if_triggered(self, triggered_alerts: List, alert_data: Optional[Dict]) -> None:
        """Add alert data to list if it was triggered."""
        if alert_data:
            triggered_alerts.append(alert_data)

    async def _process_single_alert_rule(self, alert_name: str, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single alert rule and return alert data if triggered."""
        try:
            return await self._evaluate_and_notify_rule(alert_name, rule)
        except Exception as e:
            logger.error(f"Error evaluating alert rule {alert_name}: {e}")
        return None

    async def _evaluate_and_notify_rule(self, alert_name: str, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate rule and notify if triggered."""
        if await self._evaluate_alert_rule(alert_name, rule):
            alert_data = self._create_alert_data(alert_name, rule)
            self._notify_callbacks(alert_name, alert_data)
            return alert_data
        return None
    
    def _create_alert_data(self, alert_name: str, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Create alert data structure."""
        return {
            "name": alert_name,
            "rule": rule,
            "timestamp": datetime.now(),
            "metric_summary": self.metrics_collector.get_metric_summary(rule["metric"])
        }
    
    def _notify_callbacks(self, alert_name: str, alert_data: Dict[str, Any]) -> None:
        """Notify all registered callbacks about alert."""
        for callback in self._alert_callbacks:
            self._safe_callback_execution(callback, alert_name, alert_data)

    def _safe_callback_execution(self, callback, alert_name: str, alert_data: Dict[str, Any]) -> None:
        """Execute callback with error handling."""
        try:
            callback(alert_name, alert_data)
        except Exception as e:
            logger.error(f"Error in alert callback: {e}")
    
    async def _evaluate_alert_rule(self, alert_name: str, rule: Dict[str, Any]) -> bool:
        """Evaluate a single alert rule."""
        if not self._check_cooldown(alert_name):
            return False
        
        metrics = self._get_rule_metrics(rule)
        return self._validate_and_check_violations(metrics, rule, alert_name)

    def _validate_and_check_violations(self, metrics: List, rule: Dict[str, Any], alert_name: str) -> bool:
        """Validate metrics and check for threshold violations."""
        if not self._validate_metrics(metrics, rule):
            return False
        return self._check_threshold_violations(metrics, rule, alert_name)
    
    def _check_cooldown(self, alert_name: str) -> bool:
        """Check if alert is in cooldown period."""
        if alert_name in self._last_alerts:
            time_since_last = (datetime.now() - self._last_alerts[alert_name]).total_seconds()
            return time_since_last >= self._alert_cooldown
        return True
    
    def _get_rule_metrics(self, rule: Dict[str, Any]) -> List:
        """Get metrics for alert rule evaluation."""
        return self.metrics_collector.get_recent_metrics(
            rule["metric"], 
            rule.get("duration", 60)
        )
    
    def _validate_metrics(self, metrics: List, rule: Dict[str, Any]) -> bool:
        """Validate metrics meet minimum requirements."""
        if not metrics:
            return False
        
        min_samples = rule.get("min_samples", 0)
        return len(metrics) >= min_samples
    
    def _check_threshold_violations(self, metrics: List, rule: Dict[str, Any], alert_name: str) -> bool:
        """Check if threshold violations exceed trigger ratio."""
        threshold = rule["threshold"]
        operator = rule["operator"]
        violation_count = self._count_violations(metrics, threshold, operator)
        return self._check_violation_ratio(violation_count, len(metrics), alert_name)

    def _check_violation_ratio(self, violation_count: int, total_count: int, alert_name: str) -> bool:
        """Check if violation ratio exceeds threshold and update alert timestamp."""
        violation_ratio = violation_count / total_count
        
        if violation_ratio > 0.5:
            self._last_alerts[alert_name] = datetime.now()
            return True
        return False
    
    def _count_violations(self, metrics: List, threshold: float, operator: str) -> int:
        """Count threshold violations in metrics."""
        violation_count = 0
        for metric in metrics:
            violation_count += self._check_metric_violation(metric, threshold, operator)
        return violation_count

    def _check_metric_violation(self, metric, threshold: float, operator: str) -> int:
        """Check if single metric violates threshold."""
        return 1 if self._is_violation(metric.value, threshold, operator) else 0
    
    def _is_violation(self, value: float, threshold: float, operator: str) -> bool:
        """Check if a single value violates threshold."""
        operator_checks = self._get_operator_checks()
        return self._evaluate_operator_check(operator_checks, operator, value, threshold)

    def _get_operator_checks(self) -> Dict[str, Callable]:
        """Get operator check functions."""
        return {
            ">": lambda v, t: v > t,
            "<": lambda v, t: v < t,
            "==": lambda v, t: v == t
        }

    def _evaluate_operator_check(self, operator_checks: Dict, operator: str, value: float, threshold: float) -> bool:
        """Evaluate operator check for value and threshold."""
        check_func = operator_checks.get(operator)
        return check_func(value, threshold) if check_func else False